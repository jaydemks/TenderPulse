#!/usr/bin/env python3
"""Turn the award store into a CSV a person can actually open.

The store is newline-delimited JSON, gzipped, keyed by month — good for
appending, useless for anyone who wants to look at it in Excel or load it into
pandas. This writes one flat table with readable column names, the CPV code
spelled out, and the euro value already worked out.

    python scripts/export_awards.py                  # everything on disk
    MONTHS=12 python scripts/export_awards.py        # the last 12 months
    OUT=dist/sample.csv MONTHS=1 python scripts/export_awards.py
"""
import csv
import glob
import gzip
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import meta

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
AWARDS = os.path.join(ROOT, "data", "awards")

COLUMNS = [
    "notice_id", "published", "notice_type",
    "buyer", "buyer_country", "buyer_country_name",
    "cpv_main", "cpv_main_label", "cpv_divisions", "contract_nature",
    "winner", "winner_countries", "winner_count",
    "value", "currency", "value_eur", "value_source", "value_quality",
    "title", "ted_url",
]


def value_source(r):
    """Which of TED's three value fields the euro figure was taken from.

    Notices carry up to three: the tender value, the value stated on the notice
    as a whole, and the buyer's pre-tender estimate. They are not the same
    thing, and a reader comparing rows deserves to know which one they are
    looking at. The order below is the order enrich_awards.py falls back in.
    """
    for key, name in (("val", "tender_value"),
                      ("val_notice", "notice_value"),
                      ("val_est", "estimated_value")):
        v = r.get(key)
        if v is not None and v > 0:
            return name
    return ""


def rows(months=None):
    files = sorted(glob.glob(os.path.join(AWARDS, "*.jsonl.gz")))
    if months:
        files = files[-months:]
    for path in files:
        with gzip.open(path, "rt", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                r = json.loads(line)
                yield {
                    "notice_id": r["id"],
                    "published": r.get("p", ""),
                    "notice_type": r.get("ty", ""),
                    "buyer": r.get("b", ""),
                    "buyer_country": r.get("c", ""),
                    "buyer_country_name": meta.country_name(r.get("c")),
                    "cpv_main": r.get("cpvf", ""),
                    "cpv_main_label": meta.cpv_name(r["cpvf"]) if r.get("cpvf") else "",
                    "cpv_divisions": " ".join(r.get("cpv", [])),
                    "contract_nature": r.get("nat", ""),
                    "winner": r.get("w", ""),
                    "winner_countries": " ".join(r.get("wc", [])),
                    "winner_count": r.get("wn", 0),
                    "value": r.get("val") if r.get("val") is not None else "",
                    "currency": r.get("cur", ""),
                    "value_eur": r.get("val_eur") if r.get("val_eur") is not None else "",
                    "value_source": value_source(r),
                    "value_quality": r.get("q", ""),
                    "title": r.get("t", ""),
                    "ted_url": f"https://ted.europa.eu/en/notice/-/detail/{r['id']}",
                }


def main():
    months = int(os.environ["MONTHS"]) if os.environ.get("MONTHS") else None
    out = os.environ.get("OUT") or os.path.join(
        ROOT, "dist", f"eu-contract-awards{'-' + str(months) + 'm' if months else ''}.csv")
    os.makedirs(os.path.dirname(out), exist_ok=True)

    n = 0
    with open(out, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=COLUMNS)
        w.writeheader()
        for row in rows(months):
            w.writerow(row)
            n += 1

    size = os.path.getsize(out)
    print(f"{n:,} rows -> {out}  ({size/1e6:.0f} MB)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
