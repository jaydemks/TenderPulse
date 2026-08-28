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

## The CPV vocabulary, as actually used

`scripts/cpv_labels.json` maps every CPV code that TED has actually published a notice
under to its official English label — 3,365 of them at the time of writing. It is
harvested from the notice titles, which carry the authoritative label for each notice's
main code. The official vocabulary is a spreadsheet on SIMAP; this is the working subset,
in JSON, and it is regenerated as new codes appear.

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
