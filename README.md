# TenderPulse

A searchable, daily-refreshed index of open public tenders across the European Union.

The European Union publishes every public contract above threshold in *Tenders Electronic
Daily* (TED), the supplement to the Official Journal. The data is public and free, but it
is formatted for legal completeness rather than for the small companies that could win the
work. TenderPulse takes the same feed and turns it into something you can search in ten
seconds: one page per notice, per sector and per country, sorted by closing date, with an
RSS feed for anything you want to follow.

**Live site:** https://jaydemks.github.io/TenderPulse

## How it works

```
scripts/sync.py    TED Search API  ->  data/notices/YYYY-MM.jsonl
scripts/build.py   the store       ->  site/  (notice, sector and country pages, RSS, sitemap)
scripts/meta.py    CPV division and country lookup tables
scripts/preview.py a single self-contained page, for sharing a snapshot
config.json        brand, canonical URL, outbound links
```

A scheduled job runs once a day at 05:17 UTC: it pulls the notices published since the
last run, drops the ones whose deadline has passed, rewrites the affected pages and
deploys. The store is sharded by publication month so that historic files stop changing
and each day's commit stays small.

Only *calls for competition* are indexed — contract notices, social and special services
notices, design contests, qualification systems, and prior information notices used as a
call for competition. Award notices, which announce a winner after the fact, are excluded.

## A free API

Every collection on the site is also a JSON file, served by GitHub Pages with
`Access-Control-Allow-Origin: *`. No key, no sign-up, no rate limit — you can call it
from a browser.

| Endpoint | What it returns |
|---|---|
| `/api/stats.json` | Counts and the build timestamp |
| `/api/countries.json` | Countries, with open tender counts |
| `/api/sectors.json` | The 45 CPV divisions, with counts |
| `/api/cpv.json` | Every CPV code in use: `[code, label, open]` |
| `/api/c/<ISO3>.json` | Open tenders in one country |
| `/api/s/<division>.json` | Open tenders in one CPV division |
| `/api/index.json` | Compact search index of every open tender |

```bash
# how many open construction tenders are there in Italy right now?
curl -s https://jaydemks.github.io/TenderPulse/api/c/ITA.json | jq '[.[] | select(.cpv_divisions[]=="45")] | length'
```

Full documentation, with the shape of a notice object:
https://jaydemks.github.io/TenderPulse/api.html

There is no query language — it is a static site, so you fetch a collection and filter it
yourself. Everything is rebuilt once a day; cache it rather than polling.

## The contract awards dataset

Open tenders are half the record. The other half is who won them. Every contract
award published in the Official Journal over the last twelve months — 374,443 of
them, with the winning company, the buyer, the sector and the value converted to
euro at the ECB rate of the day — is published as a free dataset:

**https://huggingface.co/datasets/jaydem/eu-contract-awards**

It is built by `scripts/awards.py`, `scripts/enrich_awards.py` and
`scripts/export_awards.py` from the same TED API this site uses, asked with
`scope: ALL` so it returns the past rather than only what is open. The dataset
card documents the three traps in the source data — framework ceilings that make
cross-country sums meaningless, TED's `-1` sentinel for "not disclosed", and 168
values that are plainly typing mistakes — because a number quoted from this
without knowing them is a wrong number.

## The CPV vocabulary, as actually used

`scripts/cpv_labels.json` is the whole Common Procurement Vocabulary — all 9,454 codes
with their official English labels — as JSON, keyed by the eight-digit code without the
check digit.

It comes from the European Commission's own spreadsheet, `cpv_2008_ver_2013.xlsx`. That
file used to sit on SIMAP, which has since been retired, so it is no longer downloadable
from the URL most references still cite. The copy used here was cross-checked against the
3,365 codes that TED has actually published notices under, whose labels can be read
straight out of the notice titles: all 3,365 match the spreadsheet exactly, and none is
missing from it.

The site does not build a page for every code. Only the codes with tenders open against
them get one; the rest are answered by the explorer at `/cpv.html`, which searches the
full vocabulary in the browser. Thousands of near-empty pages would cost more in crawl
budget than they could ever return.

## Running it locally

```bash
WINDOW_DAYS=3 python scripts/sync.py     # a small pull, for testing
cd scripts && python build.py            # writes ../site
python -m http.server -d ../site 8000
```

## Deployment

The repository deploys itself to GitHub Pages through `.github/workflows/daily.yml`.
Two settings are required:

- *Settings → Actions → General → Workflow permissions*: **Read and write**
- *Settings → Secrets and variables → Actions → Variables*: `SITE_URL`, the canonical
  origin used for the sitemap and `<link rel="canonical">`

## Data, attribution and scope

Notices come from the [TED Search API](https://docs.ted.europa.eu/api/latest/index.html),
accessed anonymously, and are re-used under the European Commission's open data policy.
TED remains the authoritative source: every page here links back to the official notice,
and anything binding — specifications, annexes, exact deadlines — should be read there.

TenderPulse is an independent project. It is not affiliated with, endorsed by, or
operated by the European Union or by any contracting authority.

The site sets no cookies, collects no personal data, has no analytics or tracking of
any kind, and makes no third-party requests at all: the typefaces are served from this
domain, so reading a page tells nobody but GitHub that you were here. The fonts are in
`assets/fonts/` under the SIL Open Font License.

## Licence

Code is MIT. The underlying procurement data belongs to its publishers and is redistributed
under the terms of the European Commission's open data policy.
