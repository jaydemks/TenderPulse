#!/usr/bin/env python3
"""Put every award into euro, and mark the ones that cannot be true.

Two things stop the raw award data from being usable as it comes:

1. Values arrive in the buyer's own currency. Ten billion is a large contract
   in euro and a medium one in Hungarian forint, so nothing can be summed,
   ranked or compared until it is converted.
2. Buyers mistype. One German notice in this run carries a value of
   74,654,684,654,465,482,752 EUR. Those entries are real records of a real
   notice, so they are kept exactly as published — but they are marked, because
   a single one of them ruins any total.

Rates come from the European Central Bank's daily reference series, which is
free to reuse. Each award is converted at the rate published on or before the
day the notice appeared.

    python scripts/enrich_awards.py            # enrich every month on disk
    python scripts/enrich_awards.py --rates    # refresh the ECB rates first
"""
import csv
import gzip
import io
import json
import os
import sys
import urllib.request
import zipfile
from bisect import bisect_right

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
AWARDS = os.path.join(ROOT, "data", "awards")
RATES = os.path.join(ROOT, "data", "reference", "ecb-rates.json")
ECB = "https://www.ecb.europa.eu/stats/eurofxref/eurofxref-hist.zip"

# No single public contract in the EU has ever been worth this much. Anything
# above it is a typo at the source, not a mega-project.
IMPLAUSIBLE_EUR = 5_000_000_000
FIRST_YEAR = "2019"


def refresh_rates():
    print("fetching ECB reference rates…")
    with urllib.request.urlopen(ECB, timeout=120) as r:
        z = zipfile.ZipFile(io.BytesIO(r.read()))
    rows = list(csv.reader(io.TextIOWrapper(z.open(z.namelist()[0]), encoding="utf-8")))
    head = [h.strip() for h in rows[0]]
    out = {}
    for row in rows[1:]:
        day = row[0].strip()
        if not day or day < FIRST_YEAR:
            continue
        day_rates = {}
        for i, cur in enumerate(head[1:], start=1):
            cur = cur.strip()
            if not cur or i >= len(row):
                continue
            v = row[i].strip()
            if v and v != "N/A":
                try:
                    day_rates[cur] = float(v)
                except ValueError:
                    pass
        if day_rates:
            out[day] = day_rates
    os.makedirs(os.path.dirname(RATES), exist_ok=True)
    with open(RATES, "w", encoding="utf-8") as f:
        json.dump(out, f, separators=(",", ":"), sort_keys=True)
    print(f"  {len(out):,} days, {os.path.getsize(RATES)/1e6:.1f} MB")
    return out


def load_rates():
    if not os.path.exists(RATES):
        return refresh_rates()
    with open(RATES, encoding="utf-8") as f:
        return json.load(f)


class Converter:
    """Convert to euro at the rate in force on the day a notice was published.

    The ECB publishes on working days only, so a notice dated on a weekend or a
    holiday takes the most recent rate before it.
    """

    def __init__(self, rates):
        self.rates = rates
        self.days = sorted(rates)
        self.misses = set()

    def to_eur(self, amount, currency, day):
        if amount is None:
            return None
        cur = (currency or "EUR").upper()
        if cur == "EUR":
            return round(amount, 2)
        i = bisect_right(self.days, day) - 1
        while i >= 0:
            r = self.rates[self.days[i]].get(cur)
            if r:
                return round(amount / r, 2)
            i -= 1
        self.misses.add(cur)
        return None


def enrich_file(path, conv):
    records = []
    with gzip.open(path, "rt", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                records.append(json.loads(line))

    counts = {"ok": 0, "implausible": 0, "none": 0}
    for r in records:
        raw = r.get("val")
        if raw is None:
            raw = r.get("val_notice")
        if raw is None:
            raw = r.get("val_est")
        # TED uses -1 and 0 to mean "not disclosed", which is an absent value,
        # not a wrong one. Only a number too large to be a real contract is a
        # mistake worth flagging.
        if raw is not None and raw <= 0:
            raw = None
        eur = conv.to_eur(raw, r.get("cur"), r.get("p") or "")
        r["val_eur"] = eur
        if eur is None:
            r["q"] = "none"
        elif eur > IMPLAUSIBLE_EUR:
            r["q"] = "implausible"
        else:
            r["q"] = "ok"
        counts[r["q"]] += 1

    tmp = path + ".tmp"
    with gzip.open(tmp, "wt", encoding="utf-8", compresslevel=9) as f:
        for r in sorted(records, key=lambda x: x["id"]):
            f.write(json.dumps(r, ensure_ascii=False, sort_keys=True) + "\n")
    os.replace(tmp, path)
    return len(records), counts


def main():
    rates = refresh_rates() if "--rates" in sys.argv else load_rates()
    conv = Converter(rates)
    files = sorted(f for f in os.listdir(AWARDS) if f.endswith(".jsonl.gz"))
    if not files:
        print("nothing in data/awards — run scripts/awards.py first")
        return 1

    total = {"ok": 0, "implausible": 0, "none": 0}
    n = 0
    for name in files:
        count, counts = enrich_file(os.path.join(AWARDS, name), conv)
        n += count
        for k in total:
            total[k] += counts[k]
        print(f"  {name[:7]}  {count:>6,}  priced {counts['ok']:>6,}  "
              f"flagged {counts['implausible']:>3}")

    print(f"\n{n:,} awards in euro")
    print(f"  usable value      {total['ok']:>8,}  ({100*total['ok']/n:.1f}%)")
    print(f"  flagged as wrong  {total['implausible']:>8,}")
    print(f"  no value at all   {total['none']:>8,}")
    if conv.misses:
        print(f"  currencies with no ECB rate: {sorted(conv.misses)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
