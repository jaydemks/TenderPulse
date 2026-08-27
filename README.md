# TenderPulse

A daily-refreshed, searchable front door to every open public tender in the EU.

Data comes from **TED (Tenders Electronic Daily)**, the official journal of EU public
procurement, through its public Search API (anonymous, no key). The site is fully static:
a scheduled GitHub Action pulls new notices once a day, rebuilds every page, and deploys
to GitHub Pages. Nothing runs on anybody's laptop and hosting costs nothing.

```
scripts/sync.py    pull open calls from TED  -> data/notices.jsonl  (committed, grows daily)
scripts/build.py   data/notices.jsonl        -> site/               (regenerated, not committed)
scripts/meta.py    CPV division + country lookup tables
config.json        brand name, canonical URL, links
.github/workflows/daily.yml   the whole machine, once a day at 05:17 UTC
```

## One-time setup

1. **Create the repo and push this folder.**

   ```bash
   git init
   git add .
   git commit -m "TenderPulse: initial machine"
   git branch -M main
   git remote add origin https://github.com/<you>/tenderpulse.git
   git push -u origin main
   ```

2. **Turn on Pages**: repo → *Settings* → *Pages* → *Source: GitHub Actions*.

3. **Set the canonical URL** (needed for the sitemap and `<link rel=canonical>`):
   repo → *Settings* → *Secrets and variables* → *Actions* → *Variables* → **New variable**
   `SITE_URL` = `https://<you>.github.io/tenderpulse` (or the custom domain later).

4. **Run it once by hand**: *Actions* → *Daily sync and deploy* → *Run workflow*.
   The first run pulls ~30 days of notices (a few minutes) and publishes the site.

That is the whole setup. From then on it runs itself every morning.

## Local run

```bash
WINDOW_DAYS=3 python scripts/sync.py     # small pull, for testing
cd scripts && python build.py            # writes ../site
python -m http.server -d ../site 8000
```

## Notes

- `data/notices.jsonl` is the asset that compounds: one line per notice, sorted by id,
  so daily commits are small line-level diffs. Notices are dropped 7 days after their
  deadline passes.
- Only *calls for competition* are kept (contract notices, social services, design
  contests, qualification systems, PINs used as a call). Award notices are excluded.
- Every page links back to the authoritative TED notice. TED is the legal source;
  this site is a faster way in.
- Data re-use follows the European Commission's open data policy. The site states
  clearly that it is independent and not affiliated with the EU.
