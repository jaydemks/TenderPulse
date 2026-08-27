#!/usr/bin/env python3
"""Pull open EU public procurement calls from the official TED Search API
and merge them into a local JSONL store.

TED Search API: https://docs.ted.europa.eu/api/latest/index.html
Anonymous access, no API key required.
"""
import json
import os
import time
import urllib.request
import urllib.error
from datetime import datetime, timezone, timedelta

API = "https://api.ted.europa.eu/v3/notices/search"
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STORE_DIR = os.path.join(ROOT, "data", "notices")
LEGACY = os.path.join(ROOT, "data", "notices.jsonl")

# Notice types that represent an open opportunity (validated against the API).
OPEN_TYPES = ["cn-standard", "cn-social", "cn-desg",
              "pin-cfc-standard", "pin-cfc-social", "qu-sy"]

FIELDS = ["publication-number", "notice-title", "buyer-name", "buyer-country",
          "classification-cpv", "deadline-receipt-request", "publication-date",
          "notice-type", "contract-nature", "place-of-performance",
          "description-proc"]

WINDOW_DAYS = int(os.environ.get("WINDOW_DAYS", "30"))
PAGE_SIZE = 250
MAX_PAGES = int(os.environ.get("MAX_PAGES", "400"))
USER_AGENT = "tender-radar/1.0 (open data reuse; TED Search API)"


def post(body, attempt=0):
    req = urllib.request.Request(
        API,
        data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json", "User-Agent": USER_AGENT},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=90) as r:
            return json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        if e.code in (429, 500, 502, 503, 504) and attempt < 6:
            wait = min(60, 2 ** attempt * 3)
            print(f"  HTTP {e.code} -> retry in {wait}s")
            time.sleep(wait)
            return post(body, attempt + 1)
        raise
    except urllib.error.URLError:
        if attempt < 6:
            time.sleep(min(60, 2 ** attempt * 3))
            return post(body, attempt + 1)
        raise


def pick_lang(value, prefer=("eng", "ENG")):
    """TED returns multilingual dicts; prefer English, fall back to anything."""
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    if isinstance(value, list):
        return pick_lang(value[0]) if value else ""
    if isinstance(value, dict):
        for k in prefer:
            if k in value:
                return pick_lang(value[k])
        for v in value.values():
            got = pick_lang(v)
            if got:
                return got
    return ""


def first_nuts(places):
    if not places:
        return ""
    for p in places:
        if isinstance(p, str) and len(p) > 3 and any(c.isdigit() for c in p):
            return p
    return places[0] if isinstance(places[0], str) else ""


def next_deadline(values):
    """Earliest deadline that is still in the future."""
    if not values:
        return ""
    now = datetime.now(timezone.utc)
    best = None
    for v in values:
        try:
            d = datetime.fromisoformat(str(v))
        except ValueError:
            continue
        if d.tzinfo is None:
            d = d.replace(tzinfo=timezone.utc)
        if d > now and (best is None or d < best):
            best = d
    return best.isoformat() if best else ""


def normalise(n):
    pid = n.get("publication-number")
    if not pid:
        return None
    cpvs = n.get("classification-cpv") or []
    cpvs = [c for c in cpvs if isinstance(c, str)]
    deadline = next_deadline(n.get("deadline-receipt-request") or [])
    if not deadline:
        return None
    desc = pick_lang(n.get("description-proc"))
    return {
        "id": pid,
        "t": pick_lang(n.get("notice-title")).strip()[:300],
        "b": pick_lang(n.get("buyer-name")).strip()[:160],
        "c": (n.get("buyer-country") or [""])[0] if isinstance(n.get("buyer-country"), list) else (n.get("buyer-country") or ""),
        "cpv": sorted({c[:2] for c in cpvs if len(c) >= 2}),
        "cpvf": cpvs[0] if cpvs else "",
        "nat": (n.get("contract-nature") or [""])[0] if isinstance(n.get("contract-nature"), list) else (n.get("contract-nature") or ""),
        "ty": n.get("notice-type") or "",
        "p": str(n.get("publication-date") or "")[:10],
        "d": deadline,
        "nuts": first_nuts(n.get("place-of-performance") or []),
        "desc": " ".join(desc.split())[:400],
    }


def fetch_all():
    query = (f"notice-type IN ({' '.join(OPEN_TYPES)}) "
             f"AND publication-date>=today(-{WINDOW_DAYS})")
    out, token, pages = {}, None, 0
    while pages < MAX_PAGES:
        body = {"query": query, "limit": PAGE_SIZE, "scope": "ACTIVE",
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
        total = data.get("totalNoticeCount")
        print(f"  page {pages}: +{len(notices)} (kept {len(out)} / {total} total)")
        token = data.get("iterationNextToken")
        if not token or not notices:
            break
        time.sleep(1.0)
    return out


def shard_key(rec):
    """Group by publication month: old shards stop changing, so daily diffs stay small."""
    return (rec.get("p") or rec.get("d") or "unknown")[:7] or "unknown"


def load_store():
    store = {}
    paths = []
    if os.path.exists(LEGACY):
        paths.append(LEGACY)
    if os.path.isdir(STORE_DIR):
        paths += [os.path.join(STORE_DIR, f) for f in sorted(os.listdir(STORE_DIR))
                  if f.endswith(".jsonl")]
    for path in paths:
        with open(path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    rec = json.loads(line)
                    store[rec["id"]] = rec
                except (ValueError, KeyError):
                    continue
    return store


def save_store(store):
    os.makedirs(STORE_DIR, exist_ok=True)
    shards = {}
    for rec in store.values():
        shards.setdefault(shard_key(rec), []).append(rec)
    for name, recs in shards.items():
        recs.sort(key=lambda r: r["id"])
        with open(os.path.join(STORE_DIR, f"{name}.jsonl"), "w", encoding="utf-8") as f:
            for rec in recs:
                f.write(json.dumps(rec, ensure_ascii=False, sort_keys=True) + "\n")
    # remove shards that no longer hold anything
    for f in os.listdir(STORE_DIR):
        if f.endswith(".jsonl") and f[:-6] not in shards:
            os.remove(os.path.join(STORE_DIR, f))
    if os.path.exists(LEGACY):
        os.remove(LEGACY)


def main():
    print(f"TED sync — window {WINDOW_DAYS} days")
    fresh = fetch_all()
    store = load_store()
    before = len(store)
    new = [k for k in fresh if k not in store]
    store.update(fresh)

    # Drop notices whose deadline has passed (keep the archive lean).
    cutoff = datetime.now(timezone.utc) - timedelta(days=7)
    kept = {}
    for k, v in store.items():
        try:
            d = datetime.fromisoformat(v["d"])
            if d.tzinfo is None:
                d = d.replace(tzinfo=timezone.utc)
        except (ValueError, KeyError):
            continue
        if d > cutoff:
            kept[k] = v

    save_store(kept)
    print(f"store: {before} -> {len(kept)}  (+{len(new)} new, "
          f"{len(store) - len(kept)} expired)")
    meta = {"generated": datetime.now(timezone.utc).isoformat(),
            "total": len(kept), "new": len(new)}
    with open(os.path.join(ROOT, "data", "last_run.json"), "w") as f:
        json.dump(meta, f, indent=2)


if __name__ == "__main__":
    main()
