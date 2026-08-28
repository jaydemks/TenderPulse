#!/usr/bin/env python3
"""Pull the record of who won EU public contracts, and for how much.

`sync.py` deals with what is open. This deals with what is finished. TED's
search API will serve past notices when asked with `scope: ALL`, and award
notices carry the two fields nothing else does: the winning company and the
value it was awarded. That record cannot be reconstructed later — TED serves
what is current — so it is worth pulling once and keeping.

    python scripts/awards.py                    # the last 24 months
    MONTHS=6 python scripts/awards.py           # a shorter run
    FROM=2024-01 TO=2024-06 python scripts/awards.py

Each month lands in data/awards/YYYY-MM.jsonl.gz and is never rewritten, so a
run that is interrupted picks up where it stopped and the git history stays
small. Pass REFRESH=1 to redo months already on disk.
"""
import gzip
import json
import os
import sys
import time
import urllib.error
import urllib.request
from datetime import date

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sync import pick_lang  # the same multilingual flattening the site uses

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT_DIR = os.path.join(ROOT, "data", "awards")
API = "https://api.ted.europa.eu/v3/notices/search"
USER_AGENT = "tenderpulse/1.0 (open data reuse; TED Search API)"

# Contract award notices: the ones that name a winner.
AWARD_TYPES = ["can-standard", "can-social", "can-desg", "can-tran"]

FIELDS = [
    "publication-number", "publication-date", "notice-type", "notice-title",
    "buyer-name", "buyer-country", "classification-cpv", "contract-nature",
    "winner-name", "winner-country", "tender-value", "tender-value-cur",
    "estimated-value-proc", "result-value-notice",
]

PAGE_SIZE = 250
MAX_PAGES_PER_MONTH = 400
PAUSE = float(os.environ.get("PAUSE", "0.4"))   # be a polite guest


def post(body, attempt=0):
    req = urllib.request.Request(
        API, data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json", "User-Agent": USER_AGENT},
        method="POST")
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            return json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        if e.code in (429, 500, 502, 503, 504) and attempt < 6:
            wait = min(90, 2 ** attempt * 4)
            print(f"    HTTP {e.code} — retry in {wait}s")
            time.sleep(wait)
            return post(body, attempt + 1)
        raise
    except (urllib.error.URLError, TimeoutError):
        if attempt < 6:
            time.sleep(min(90, 2 ** attempt * 4))
            return post(body, attempt + 1)
        raise


def one(value):
    """TED returns most things as a list, even when there is only ever one."""
    if isinstance(value, list):
        return value[0] if value else ""
    return value or ""


def money(value):
    """Values arrive as strings, sometimes as lists, sometimes not at all."""
    v = one(value)
    if v in ("", None):
        return None
    try:
        return round(float(str(v).replace(",", ".")), 2)
    except (TypeError, ValueError):
        return None


def normalise(n):
    pid = n.get("publication-number")
    if not pid:
        return None
    cpvs = [c for c in (n.get("classification-cpv") or []) if isinstance(c, str)]
    # Several winners can share one notice, one per lot. Keep the first name
    # and record how many countries were involved, so a reader can tell a
    # single award from a framework split across suppliers.
    winners = n.get("winner-name")
    winner = pick_lang(winners).strip()[:160] if winners else ""
    wcountries = n.get("winner-country") or []
    if isinstance(wcountries, str):
        wcountries = [wcountries]
    return {
        "id": pid,
        "p": str(n.get("publication-date") or "")[:10],
        "ty": one(n.get("notice-type")),
        "t": pick_lang(n.get("notice-title")).strip()[:300],
        "b": pick_lang(n.get("buyer-name")).strip()[:160],
        "c": one(n.get("buyer-country")),
        "cpv": sorted({c[:2] for c in cpvs if len(c) >= 2}),
        "cpvf": cpvs[0] if cpvs else "",
        "nat": one(n.get("contract-nature")),
        "w": winner,
        "wc": sorted(set(x for x in wcountries if isinstance(x, str))),
        "wn": len(set(wcountries)) if wcountries else 0,
        "val": money(n.get("tender-value")),
        "cur": one(n.get("tender-value-cur")),
        "val_est": money(n.get("estimated-value-proc")),
        "val_notice": money(n.get("result-value-notice")),
    }


def months_back(n):
    today = date.today().replace(day=1)
    out = []
    y, m = today.year, today.month
    for _ in range(n):
        m -= 1
        if m == 0:
            y, m = y - 1, 12
        out.append(f"{y:04d}-{m:02d}")
    return list(reversed(out))


def month_range(first, last):
    y, m = (int(x) for x in first.split("-"))
    ly, lm = (int(x) for x in last.split("-"))
    out = []
    while (y, m) <= (ly, lm):
        out.append(f"{y:04d}-{m:02d}")
        m += 1
        if m == 13:
            y, m = y + 1, 1
    return out


def last_day(month):
    y, m = (int(x) for x in month.split("-"))
    if m == 12:
        return date(y, 12, 31)
    return date.fromordinal(date(y, m + 1, 1).toordinal() - 1)


def fetch_month(month):
    start = month.replace("-", "") + "01"
    end = last_day(month).strftime("%Y%m%d")
    query = (f"notice-type IN ({' '.join(AWARD_TYPES)}) "
             f"AND publication-date>={start} AND publication-date<={end}")
    out, token, pages = {}, None, 0
    while pages < MAX_PAGES_PER_MONTH:
        body = {"query": query, "limit": PAGE_SIZE, "scope": "ALL",
                "fields": FIELDS, "paginationMode": "ITERATION"}
        if token:
            body["iterationNextToken"] = token
        else:
            body["page"] = 1
        data = post(body)
        notices = data.get("notices") or []
        for n in notices:
            rec = normalise(n)
            if rec:
                out[rec["id"]] = rec
        pages += 1
        token = data.get("iterationNextToken")
        if not token or not notices:
            break
        time.sleep(PAUSE)
    return out, pages


def write_month(month, records):
    os.makedirs(OUT_DIR, exist_ok=True)
    path = os.path.join(OUT_DIR, f"{month}.jsonl.gz")
    tmp = path + ".tmp"
    with gzip.open(tmp, "wt", encoding="utf-8", compresslevel=9) as f:
        for rid in sorted(records):
            f.write(json.dumps(records[rid], ensure_ascii=False,
                               sort_keys=True) + "\n")
    os.replace(tmp, path)
    return os.path.getsize(path)


def main():
    if os.environ.get("FROM") and os.environ.get("TO"):
        months = month_range(os.environ["FROM"], os.environ["TO"])
    else:
        months = months_back(int(os.environ.get("MONTHS", "24")))
    refresh = os.environ.get("REFRESH") == "1"

    print(f"awards: {len(months)} months, {months[0]} to {months[-1]}")
    total = bytes_ = skipped = 0
    started = time.time()
    for month in months:
        path = os.path.join(OUT_DIR, f"{month}.jsonl.gz")
        if os.path.exists(path) and not refresh:
            with gzip.open(path, "rt", encoding="utf-8") as f:
                have = sum(1 for line in f if line.strip())
            total += have
            bytes_ += os.path.getsize(path)
            skipped += 1
            continue
        recs, pages = fetch_month(month)
        size = write_month(month, recs)
        total += len(recs)
        bytes_ += size
        withval = sum(1 for r in recs.values() if r["val"] or r["val_est"])
        print(f"  {month}  {len(recs):>6,} awards  {pages:>3} pages  "
              f"{size/1e6:>5.1f} MB  {100*withval/max(1,len(recs)):>3.0f}% priced")

    mins = (time.time() - started) / 60
    print(f"\n{total:,} awards across {len(months)} months, "
          f"{bytes_/1e6:.0f} MB on disk, {skipped} months already had")
    print(f"took {mins:.1f} min")


if __name__ == "__main__":
    main()
