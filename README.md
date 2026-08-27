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

The site sets no cookies, runs no third-party scripts and collects no personal data.

## Licence

Code is MIT. The underlying procurement data belongs to its publishers and is redistributed
under the terms of the European Commission's open data policy.
