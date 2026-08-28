#!/usr/bin/env python3
"""Generate the static site from the local notice store."""
import html
import json
import os
import re
import shutil
from urllib.parse import urlparse
from collections import defaultdict
from datetime import datetime, timedelta, timezone

import meta

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STORE_DIR = os.path.join(ROOT, "data", "notices")
LEGACY = os.path.join(ROOT, "data", "notices.jsonl")
OUT = os.path.join(ROOT, "site")
CFG = json.load(open(os.path.join(ROOT, "config.json"), encoding="utf-8"))

BRAND = CFG["brand"]
BASE = (os.environ.get("SITE_URL") or CFG["base_url"]).rstrip("/")
NOW = datetime.now(timezone.utc)
# GitHub Pages serves project sites under /<repo>/, so every in-page link
# needs that prefix. Derived from SITE_URL; empty for a root domain.
PREFIX = urlparse(BASE).path.rstrip("/") if BASE else ""
ARCHIVE_DAYS = int(CFG.get("archive_days") or 90)

CSS = """
:root{
  --paper:#f6f5f0; --ink:#14201c; --mut:#5d6b65; --line:#d8d8cf;
  --card:#fffefa; --seal:#1f5c4a; --seal-soft:#e4ece7; --flag:#9a5a12; --rule:#25342e;
}
:root:not([data-theme="light"]){}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]){
  --paper:#11150f; --ink:#e6e8e0; --mut:#98a39a; --line:#2a2f28;
  --card:#171c15; --seal:#7fc0a5; --seal-soft:#17251f; --flag:#d9a25a; --rule:#3a4239;
}}
:root[data-theme="dark"]{
  --paper:#11150f; --ink:#e6e8e0; --mut:#98a39a; --line:#2a2f28;
  --card:#171c15; --seal:#7fc0a5; --seal-soft:#17251f; --flag:#d9a25a; --rule:#3a4239;
}
*{box-sizing:border-box;margin:0;padding:0}
html{-webkit-text-size-adjust:100%}
body{background:var(--paper);color:var(--ink);
  font-family:"IBM Plex Sans",-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;
  font-size:16px;line-height:1.55;-webkit-font-smoothing:antialiased}
a{color:var(--seal);text-decoration:none}
a:hover{text-decoration:underline;text-underline-offset:2px}
:focus-visible{outline:2px solid var(--seal);outline-offset:2px}
.wrap{max-width:1000px;margin:0 auto;padding:0 24px}
.mast{border-bottom:2px solid var(--rule);background:var(--paper)}
.mast .wrap{display:flex;align-items:baseline;gap:26px;padding:18px 24px 14px}
.logo{font-family:"Newsreader",Georgia,serif;font-weight:600;font-size:23px;
  letter-spacing:-.015em;color:var(--ink)}
.logo em{font-style:normal;color:var(--seal)}
.mast nav{margin-left:auto;display:flex;gap:20px;font-size:13px;letter-spacing:.02em}
.mast nav a{color:var(--mut)}
.mast nav a:hover{color:var(--ink)}
h1{font-family:"Newsreader",Georgia,serif;font-weight:600;font-size:clamp(28px,4.2vw,42px);
  line-height:1.12;letter-spacing:-.02em;margin:38px 0 10px;text-wrap:balance;max-width:20ch}
h2{font-family:"IBM Plex Sans",sans-serif;font-size:12px;font-weight:600;
  text-transform:uppercase;letter-spacing:.14em;color:var(--mut);
  margin:44px 0 14px;padding-bottom:7px;border-bottom:1px solid var(--line)}
.sub{color:var(--mut);max-width:60ch;font-size:16.5px}
.band{display:flex;gap:0;flex-wrap:wrap;margin:26px 0 30px;
  border-top:1px solid var(--line);border-bottom:1px solid var(--line)}
.band div{padding:13px 26px 13px 0;margin-right:26px;border-right:1px solid var(--line)}
.band div:last-child{border-right:0}
.band b{display:block;font-family:"IBM Plex Mono",ui-monospace,monospace;
  font-size:21px;font-weight:500;letter-spacing:-.02em;font-variant-numeric:tabular-nums}
.band span{font-size:10.5px;text-transform:uppercase;letter-spacing:.13em;color:var(--mut)}
#q{width:100%;padding:14px 16px;font-size:16px;font-family:inherit;
  border:1px solid var(--rule);border-radius:2px;background:var(--card);color:var(--ink)}
#q::placeholder{color:var(--mut)}
.filters{display:flex;gap:10px;flex-wrap:wrap;margin:10px 0 6px}
.filters select{padding:9px 11px;border:1px solid var(--line);border-radius:2px;
  background:var(--card);color:var(--ink);font-family:inherit;font-size:13.5px}
.row{display:grid;grid-template-columns:104px 1fr 132px;gap:20px;align-items:start;
  padding:15px 0;border-bottom:1px solid var(--line)}
.row .ref{font-family:"IBM Plex Mono",ui-monospace,monospace;font-size:12px;
  color:var(--mut);padding-top:2px;font-variant-numeric:tabular-nums}
.row .ttl{font-size:15.5px;line-height:1.45}
.row .ttl a{color:var(--ink);font-weight:500}
.row .ttl a:hover{color:var(--seal)}
.row .meta{color:var(--mut);font-size:13px;margin-top:3px}
.row .when{text-align:right;font-family:"IBM Plex Mono",ui-monospace,monospace;
  font-size:12.5px;color:var(--mut);font-variant-numeric:tabular-nums;padding-top:2px}
.row .when b{display:block;color:var(--ink);font-weight:500}
.row .when.soon b{color:var(--flag)}
.chip{display:inline-block;font-family:"IBM Plex Mono",monospace;font-size:10.5px;
  letter-spacing:.04em;background:var(--seal-soft);color:var(--seal);
  padding:2px 7px;border-radius:2px;margin-right:5px}
.index{display:grid;grid-template-columns:repeat(auto-fill,minmax(268px,1fr));gap:0 34px}
.cpv{border-top:1px solid var(--line);margin:18px 0}
.cpv a{display:grid;grid-template-columns:96px 1fr auto;gap:8px 18px;align-items:baseline;
  padding:11px 4px;border-bottom:1px solid var(--line);color:var(--ink)}
.cpv a:hover{background:var(--seal-soft);text-decoration:none}
.cpv b{font-family:"IBM Plex Mono",monospace;font-size:13px;font-weight:500;color:var(--seal)}
.cpv i{font-style:normal}
.cpv u{text-decoration:none;font-family:"IBM Plex Mono",monospace;font-size:12px;
  color:var(--mut);white-space:nowrap}
.cpv em{font-style:normal;background:var(--seal-soft);border-radius:2px}
.closed{display:inline-block;font-family:"IBM Plex Mono",monospace;font-size:11px;
  letter-spacing:.08em;text-transform:uppercase;color:var(--flag);
  border:1px solid var(--flag);border-radius:2px;padding:2px 7px;margin-top:26px}
@media(max-width:560px){.cpv a{grid-template-columns:1fr auto}.cpv b{grid-column:1/-1}}
.index a{display:flex;align-items:baseline;gap:8px;padding:7px 0;
  border-bottom:1px dotted var(--line);color:var(--ink);font-size:14px}
.index a:hover{color:var(--seal);text-decoration:none}
.index a i{font-style:normal;flex:1;border-bottom:1px dotted var(--line);
  transform:translateY(-3px)}
.index a u{text-decoration:none;font-family:"IBM Plex Mono",monospace;font-size:12px;
  color:var(--mut);font-variant-numeric:tabular-nums}
.note{border-left:3px solid var(--seal);background:var(--card);padding:20px 22px;margin:38px 0}
.note h2{margin-top:0;border:0;padding:0}
.note p{max-width:58ch;color:var(--mut)}
.btn{display:inline-block;background:var(--seal);color:var(--paper);padding:10px 20px;
  border-radius:2px;font-size:14px;font-weight:600;margin-top:14px;letter-spacing:.01em}
.btn:hover{text-decoration:none;filter:brightness(1.08)}
.crumb{font-family:"IBM Plex Mono",monospace;font-size:11.5px;color:var(--mut);
  letter-spacing:.05em;text-transform:uppercase;margin-top:26px}
.detail dl{display:grid;grid-template-columns:200px 1fr;gap:0;margin:26px 0;font-size:15px}
.detail dt{color:var(--mut);font-size:12px;text-transform:uppercase;letter-spacing:.1em;
  padding:11px 0;border-bottom:1px solid var(--line)}
.detail dd{padding:11px 0;border-bottom:1px solid var(--line)}
.desc{background:var(--card);border:1px solid var(--line);padding:18px 20px;
  margin:22px 0;font-size:15px;max-width:66ch}
footer{border-top:2px solid var(--rule);margin-top:64px;padding:26px 0 52px;
  font-size:12.5px;color:var(--mut);line-height:1.7}
footer a{color:var(--mut);text-decoration:underline}
@media(max-width:660px){
  .row{grid-template-columns:1fr;gap:5px}
  .row .when{text-align:left}.row .ref{padding-top:0}
  .detail dl{grid-template-columns:1fr}.detail dt{border:0;padding-bottom:0}
  .band div{padding-right:18px;margin-right:18px}
  .mast .wrap{flex-wrap:wrap;gap:10px}
}
@media(prefers-reduced-motion:reduce){*{animation:none!important;transition:none!important}}
"""


def esc(s):
    return html.escape(str(s or ""))


def slug(s):
    return re.sub(r"[^a-z0-9]+", "-", str(s).lower()).strip("-")


def page(title, body, desc="", canonical="", extra_head=""):
    return f"""<!doctype html><html lang="en"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{esc(title)}</title>
<meta name="description" content="{esc(desc)}">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500&family=IBM+Plex+Sans:wght@400;500;600&family=Newsreader:opsz,wght@6..72,500;6..72,600&display=swap">
{f'<link rel="canonical" href="{BASE}{canonical}">' if BASE and canonical else ''}
<link rel="stylesheet" href="/style.css">{extra_head}</head><body>
<header class="mast"><div class="wrap"><a class="logo" href="/">Tender<em>Pulse</em></a>
<nav><a href="/sectors.html">Sectors</a><a href="/countries.html">Countries</a>
<a href="/cpv.html">CPV codes</a>
<a href="/alerts.html">Daily alerts</a><a href="/about.html">About</a></nav></div></header>
<div class="wrap">{body}</div>
<footer><div class="wrap">
Data source: <a href="https://ted.europa.eu/">Tenders Electronic Daily (TED)</a>, the official
journal of EU public procurement, re-used under the European Commission's open data policy.
{BRAND} is an independent service and is not affiliated with the European Union.<br>
Rebuilt automatically every day &middot; last update {NOW.strftime('%d %b %Y %H:%M UTC')}
</div></footer></body></html>"""


def deadline_bits(iso):
    try:
        d = datetime.fromisoformat(iso)
        if d.tzinfo is None:
            d = d.replace(tzinfo=timezone.utc)
    except (ValueError, TypeError):
        return "", 9999
    days = (d - NOW).days
    return d.strftime("%d %b %Y"), days


def card(n):
    dl, days = deadline_bits(n["d"])
    chips = "".join(f'<span class="chip">{esc(meta.cpv_label(c))[:26]}</span>'
                    for c in n.get("cpv", [])[:2])
    soon = " soon" if days <= 7 else ""
    left = f"{days} days left" if days >= 0 else ""
    return f"""<div class="row">
<div class="ref">{esc(n['id'])}</div>
<div class="ttl"><a href="/n/{esc(n['id'])}.html">{esc(n['t'])}</a>
<div class="meta">{esc(meta.country_name(n.get('c')))} &middot; {esc(n.get('b'))[:64]}</div>
<div style="margin-top:6px">{chips}</div></div>
<div class="when{soon}"><b>{esc(dl)}</b>{esc(left)}</div></div>"""


def load():
    rows, seen = [], set()
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
                rec = json.loads(line)
                if rec["id"] in seen:
                    continue
                seen.add(rec["id"])
                rows.append(rec)
    rows.sort(key=lambda r: r["d"])
    return rows


def write(path, content):
    if PREFIX and path.endswith((".html", ".xml")):
        content = (content
                   .replace('href="/', f'href="{PREFIX}/')
                   .replace('src="/', f'src="{PREFIX}/')
                   .replace("fetch('/api/", f"fetch('{PREFIX}/api/"))
    full = os.path.join(OUT, path.lstrip("/"))
    os.makedirs(os.path.dirname(full), exist_ok=True)
    with open(full, "w", encoding="utf-8") as f:
        f.write(content)


def rss(title, link, items):
    entries = "".join(f"""<item><title>{esc(i['t'])}</title>
<link>{BASE}/n/{esc(i['id'])}.html</link>
<guid isPermaLink="false">{esc(i['id'])}</guid>
<pubDate>{esc(i.get('p'))}</pubDate>
<description>{esc(meta.country_name(i.get('c')))} &mdash; {esc(i.get('b'))} &mdash; deadline {esc(deadline_bits(i['d'])[0])}</description>
</item>""" for i in items[:60])
    return f"""<?xml version="1.0" encoding="UTF-8"?><rss version="2.0"><channel>
<title>{esc(title)}</title><link>{BASE}{link}</link>
<description>Open EU public tenders &mdash; {esc(title)}</description>
{entries}</channel></rss>"""


def main():
    rows = load()
    print(f"building {len(rows)} live notices")
    if os.path.isdir(OUT):
        shutil.rmtree(OUT)
    os.makedirs(OUT, exist_ok=True)

    # A call that has closed keeps its page for ARCHIVE_DAYS instead of
    # becoming a 404: the URL is already indexed, people go on searching for
    # tenders after they close, and deleting the page throws away the only
    # thing this site accumulates. Archived pages are marked as closed, kept
    # out of every listing, and left out of the sitemap.
    everything, rows, archive = rows, [], []
    for n in everything:
        d = deadline_bits(n["d"])[1]
        if d >= 0:
            rows.append(n)
        elif d > -ARCHIVE_DAYS:
            archive.append(n)
    print(f"{len(rows)} open, {len(archive)} recently closed")

    by_country = defaultdict(list)
    by_sector = defaultdict(list)
    for n in rows:
        by_country[n.get("c") or "XXX"].append(n)
        for d in n.get("cpv", []):
            by_sector[d].append(n)

    urls = ["/", "/sectors.html", "/countries.html", "/alerts.html", "/about.html"]

    # ---- notice pages -------------------------------------------------
    for n, closed in [(x, False) for x in rows] + [(x, True) for x in archive]:
        dl, days = deadline_bits(n["d"])
        cpv_links = ", ".join(
            f'<a href="/s/{c}.html">{esc(meta.cpv_label(c))}</a>'
            for c in n.get("cpv", []))
        desc = (f'<div class="desc">{esc(n["desc"])}</div>' if n.get("desc") else "")
        div = (n.get("cpv") or ["00"])[0]
        if closed:
            lede = (f'<p class="sub"><b>This call has closed.</b> The deadline for '
                    f'submissions was {esc(dl)}. The page is kept as a record; for '
                    f'contracts still accepting bids, see '
                    f'<a href="/s/{esc(div)}.html">{esc(meta.cpv_label(div))}</a>.</p>')
            follow = (f'<div class="note"><h2>Looking for something like this?</h2>'
                      f'<p>{esc(meta.cpv_label(div))} tenders that are still open are '
                      f'listed here, and refreshed every morning.</p>'
                      f'<a class="btn" href="/s/{esc(div)}.html">Open tenders in this sector</a></div>')
        else:
            lede = (f'<p class="sub">Open call for tenders published in the EU Official '
                    f'Journal. {("Closes in %d days." % days) if 0 <= days < 400 else ""}</p>')
            follow = ('<div class="note"><h2>Rather not check this page every morning?</h2>'
                      '<p>Get the new tenders that match your sector and country in one '
                      'daily email.</p>'
                      '<a class="btn" href="/alerts.html">Set up alerts</a></div>')
        body = f"""<div class="detail">
<div class="crumb"><a href="/">Home</a> / <a href="/c/{esc(n.get('c'))}.html">{esc(meta.country_name(n.get('c')))}</a></div>
{'<p class="closed">Closed</p>' if closed else ''}
<h1>{esc(n['t'])}</h1>
{lede}
{desc}
<dl>
<dt>Buyer</dt><dd>{esc(n.get('b')) or '&mdash;'}</dd>
<dt>Country</dt><dd><a href="/c/{esc(n.get('c'))}.html">{esc(meta.country_name(n.get('c')))}</a></dd>
<dt>Submission deadline</dt><dd class="{'due' if 0 <= days <= 7 else ''}">{esc(dl) or '&mdash;'}</dd>
<dt>Contract type</dt><dd>{esc(meta.CONTRACT_NATURE.get(n.get('nat'), n.get('nat') or '&mdash;'))}</dd>
<dt>Sector (CPV)</dt><dd>{cpv_links or '&mdash;'}</dd>
<dt>Main CPV code</dt><dd>{f'<a href="/cpv/{esc(n["cpvf"])}.html">{esc(n["cpvf"])}</a>' if n.get('cpvf') else '&mdash;'}</dd>
<dt>Place of performance</dt><dd>{esc(n.get('nuts')) or '&mdash;'}</dd>
<dt>Published</dt><dd>{esc(n.get('p'))}</dd>
<dt>TED reference</dt><dd>{esc(n['id'])}</dd>
</dl>
<p><a class="btn" href="https://ted.europa.eu/en/notice/-/detail/{esc(n['id'])}" rel="nofollow noopener" target="_blank">Read the official notice on TED &rarr;</a></p>
{follow}
</div>"""
        ld = json.dumps({
            "@context": "https://schema.org", "@type": "GovernmentService",
            "name": n["t"][:200],
            "serviceType": "Public procurement notice",
            "provider": {"@type": "GovernmentOrganization", "name": n.get("b") or "Contracting authority"},
            "areaServed": meta.country_name(n.get("c")),
            "identifier": n["id"],
            "url": f"{BASE}/n/{n['id']}.html" if BASE else "",
        }, ensure_ascii=False)
        write(f"/n/{n['id']}.html",
              page(f"{'Closed: ' if closed else ''}{n['t'][:110]} | {BRAND}", body,
                   extra_head=f'<script type="application/ld+json">{ld}</script>',
                   desc=(f"Closed call: {n['t'][:120]}. The deadline was {dl}." if closed
                         else f"{meta.country_name(n.get('c'))}: {n['t'][:130]}. Deadline {dl}."),
                   canonical=f"/n/{n['id']}.html"))
        if not closed:
            urls.append(f"/n/{n['id']}.html")


    # ---- sector pages -------------------------------------------------
    for d, items in sorted(by_sector.items()):
        label = meta.cpv_label(d)
        cards = "".join(card(n) for n in items[:200])
        body = f"""<div class="crumb"><a href="/">Home</a> / <a href="/sectors.html">Sectors</a></div>
<h1>{esc(label)}</h1>
<p class="sub">{len(items)} open public tenders across the EU in CPV division {esc(d)},
sorted by closing date. Updated daily from the EU Official Journal.</p>
<p><a href="/feed/s-{esc(d)}.xml">RSS feed for this sector</a></p>
{cards}"""
        write(f"/s/{d}.html",
              page(f"Open EU public tenders: {label} | {BRAND}", body,
                   desc=f"{len(items)} open EU public tenders in {label}. Updated daily.",
                   canonical=f"/s/{d}.html"))
        write(f"/feed/s-{d}.xml", rss(f"{label} tenders", f"/s/{d}.html", items))
        urls.append(f"/s/{d}.html")

    # ---- country pages ------------------------------------------------
    for c, items in sorted(by_country.items()):
        name = meta.country_name(c)
        cards = "".join(card(n) for n in items[:200])
        body = f"""<div class="crumb"><a href="/">Home</a> / <a href="/countries.html">Countries</a></div>
<h1>Public tenders in {esc(name)}</h1>
<p class="sub">{len(items)} open calls for tenders from contracting authorities in
{esc(name)}, published in the EU Official Journal and sorted by closing date.</p>
<p><a href="/feed/c-{esc(c)}.xml">RSS feed for {esc(name)}</a></p>
{cards}"""
        write(f"/c/{c}.html",
              page(f"Open public tenders in {name} | {BRAND}", body,
                   desc=f"{len(items)} open public tenders in {name}, updated daily.",
                   canonical=f"/c/{c}.html"))
        write(f"/feed/c-{c}.xml", rss(f"{name} tenders", f"/c/{c}.html", items))
        urls.append(f"/c/{c}.html")

    # ---- CPV explorer --------------------------------------------------
    # A reference tool for the vocabulary itself: every CPV code TED actually
    # uses, searchable, with the number of tenders open against it right now.
    by_code = defaultdict(list)
    for n in rows:
        if n.get("cpvf"):
            by_code[n["cpvf"]].append(n)

    cpv_rows = sorted(
        ((c, lbl, len(by_code.get(c, []))) for c, lbl in meta.CPV_LABELS.items()),
        key=lambda r: r[0])
    write("/api/cpv.json",
          json.dumps(cpv_rows, ensure_ascii=False, separators=(",", ":")))

    live_codes = sum(1 for r in cpv_rows if r[2])
    div_grid = "".join(
        f'<a href="/s/{d}.html"><i>{esc(meta.cpv_label(d))}</i><u>{len(v)}</u></a>'
        for d, v in sorted(by_sector.items(), key=lambda kv: kv[0]))
    cpv_body = f"""<h1>CPV code explorer</h1>
<p class="sub">Every Common Procurement Vocabulary code in use across the EU Official
Journal &mdash; {len(cpv_rows):,} of them &mdash; searchable by code or by what it
means, each showing how many tenders are open against it right now.</p>
<input id="q" type="search" autocomplete="off"
 placeholder="Search a code or a description &mdash; e.g. 45000000, catering, servers, asphalt&hellip;">
<div id="res"></div>
<div class="note"><h2>What a CPV code is</h2>
<p>Every contract notice published in the EU Official Journal is tagged with codes from
the <b>Common Procurement Vocabulary</b>, an eight-digit classification that says what is
being bought, independently of the language it is bought in. It is the only reliable way
to follow one kind of work across twenty-seven countries: a road resurfacing contract is
<b>45233220</b> whether the notice is written in Portuguese, Estonian or Greek.</p>
<p>The digits narrow from left to right. The first two are the <i>division</i>
&mdash; 45 is construction work. The third adds the <i>group</i>, the fourth the
<i>class</i>, the fifth the <i>category</i>; the remaining digits refine further, and the
final digit is a check digit. A buyer picks one main code and may add others.</p>
<p>Suppliers use them to filter: pick the codes that describe what you sell, and you can
watch the whole single market instead of one national portal.</p></div>
<h2>The {len(by_sector)} divisions</h2>
<div class="index">{div_grid}</div>"""
    write("/cpv.html", page(f"CPV code explorer — all {len(cpv_rows):,} codes | {BRAND}",
          cpv_body, extra_head=CPV_JS, canonical="/cpv.html",
          desc=f"Search all {len(cpv_rows):,} CPV procurement codes and see how many EU "
               f"tenders are open against each one. Updated daily."))
    urls.append("/cpv.html")

    # ---- one page per code that has something open ----------------------
    # Every open call has a main CPV code, so paginating these pages is what
    # makes the whole store reachable by following links. Left unpaginated,
    # two thirds of the notices are in the sitemap and nowhere else, and a
    # site with no authority does not get those crawled.
    PER = 100
    for code, items in sorted(by_code.items()):
        label = meta.cpv_name(code)
        div = code[:2]
        group = meta.cpv_group(code)
        siblings = [(c, lbl) for c, lbl, k in cpv_rows
                    if k and meta.cpv_group(c) == group and c != code][:14]
        sib = "".join(f'<a href="/cpv/{c}.html"><b>{esc(c)}</b><i>{esc(lbl)}</i></a>'
                      for c, lbl in siblings)
        countries = sorted({meta.country_name(n.get("c")) for n in items})
        pages = max(1, -(-len(items) // PER))
        for pg in range(1, pages + 1):
            slice_ = items[(pg - 1) * PER: pg * PER]
            path = f"/cpv/{code}.html" if pg == 1 else f"/cpv/{code}-{pg}.html"
            nav = ""
            if pages > 1:
                prev_ = ("" if pg == 1 else
                         f'<a href="/cpv/{code}.html">&larr; first</a> '
                         if pg == 2 else
                         f'<a href="/cpv/{code}-{pg-1}.html">&larr; previous</a> ')
                next_ = ("" if pg == pages else
                         f'<a href="/cpv/{code}-{pg+1}.html">next &rarr;</a>')
                nav = (f'<p class="sub">Page {pg} of {pages} &middot; {prev_}{next_}</p>')
            head_extra = ""
            if pages > 1:
                if pg > 1:
                    p_url = (f"{BASE}/cpv/{code}.html" if pg == 2
                             else f"{BASE}/cpv/{code}-{pg-1}.html")
                    head_extra += f'<link rel="prev" href="{p_url}">'
                if pg < pages:
                    head_extra += f'<link rel="next" href="{BASE}/cpv/{code}-{pg+1}.html">'
            body = f"""<div class="crumb"><a href="/">Home</a> / <a href="/cpv.html">CPV codes</a>
 / <a href="/s/{esc(div)}.html">{esc(meta.cpv_label(div))}</a></div>
<h1>CPV {esc(code)} &mdash; {esc(label)}</h1>
<p class="sub">{len(items)} open call{'s' if len(items) != 1 else ''} for tenders across the
EU are classified under this code right now, from
{len(countries)} countr{'ies' if len(countries) != 1 else 'y'}. Sorted by closing date and
rebuilt every day from the EU Official Journal.</p>
<dl>
<dt>Code</dt><dd>{esc(code)}</dd>
<dt>Description</dt><dd>{esc(label)}</dd>
<dt>Division</dt><dd><a href="/s/{esc(div)}.html">{esc(div)} &mdash; {esc(meta.cpv_label(div))}</a></dd>
<dt>Open tenders</dt><dd>{len(items)}</dd>
<dt>Countries</dt><dd>{esc(", ".join(countries)) or '&mdash;'}</dd>
</dl>
{nav}
{"".join(card(n) for n in slice_)}
{nav}
{f'<h2>Related codes in group {esc(group)}</h2><div class="cpv">{sib}</div>' if sib and pg == 1 else ''}
<div class="note"><h2>Follow this code</h2>
<p>New tenders under {esc(code)} appear here the morning they are published.
The {esc(meta.cpv_label(div))} feed carries them as they land.</p>
<a class="btn" href="/feed/s-{esc(div)}.xml">RSS for this sector</a></div>"""
            title = (f"CPV {code}: {label} — open EU tenders | {BRAND}" if pg == 1
                     else f"CPV {code}: {label} — page {pg} | {BRAND}")
            write(path, page(title, body, extra_head=head_extra,
                             desc=f"{len(items)} open EU public tenders under CPV code "
                                  f"{code} ({label}). Updated daily.",
                             canonical=path))
            urls.append(path)


    # ---- index pages --------------------------------------------------
    sec_grid = "".join(
        f'<a href="/s/{d}.html"><i>{esc(meta.cpv_label(d))}</i><u>{len(v)}</u></a>'
        for d, v in sorted(by_sector.items(), key=lambda kv: -len(kv[1])))
    write("/sectors.html", page(f"Tenders by sector | {BRAND}",
        f'<h1>Browse by sector</h1><p class="sub">EU procurement is classified with CPV codes. '
        f'Pick the division that matches what you sell.</p><div class="index">{sec_grid}</div>',
        desc="Open EU public tenders grouped by CPV sector.", canonical="/sectors.html"))

    cnt_grid = "".join(
        f'<a href="/c/{c}.html"><i>{esc(meta.country_name(c))}</i><u>{len(v)}</u></a>'
        for c, v in sorted(by_country.items(), key=lambda kv: -len(kv[1])))
    write("/countries.html", page(f"Tenders by country | {BRAND}",
        f'<h1>Browse by country</h1><p class="sub">Contracting authorities across the EU '
        f'and associated countries.</p><div class="index">{cnt_grid}</div>',
        desc="Open EU public tenders grouped by country.", canonical="/countries.html"))

    # search index (compact)
    idx = [[n["id"], n["t"][:130], n.get("c", ""), n.get("cpv", []), n["d"][:10]]
           for n in rows]
    write("/api/index.json", json.dumps(idx, ensure_ascii=False, separators=(",", ":")))

    closing = sorted(rows, key=lambda r: r["d"])[:12]
    home = f"""<h1>Every open EU public tender, in one place.</h1>
<p class="sub">{len(rows):,} live calls for tenders from {len(by_country)} countries,
pulled every day from the EU Official Journal and made searchable. Free, no account.</p>
<div class="band">
<div><b>{len(rows):,}</b><span>open tenders</span></div>
<div><b>{len(by_country)}</b><span>countries</span></div>
<div><b>{len(by_sector)}</b><span>sectors</span></div>
<div><b>daily</b><span>refresh</span></div>
</div>
<input id="q" type="search" placeholder="Search tenders — e.g. software, catering, road works, Italy…" autocomplete="off">
<div class="filters">
<select id="fc"><option value="">All countries</option>{''.join(f'<option value="{c}">{esc(meta.country_name(c))}</option>' for c in sorted(by_country, key=lambda k: meta.country_name(k)))}</select>
<select id="fs"><option value="">All sectors</option>{''.join(f'<option value="{d}">{esc(meta.cpv_label(d))}</option>' for d in sorted(by_sector))}</select>
</div>
<div id="res"><h2>Closing soonest</h2>{''.join(card(n) for n in closing)}</div>
<div class="note"><h2>Get them by email instead</h2>
<p>One short email a day with the new tenders in your sector and country.
No dashboard to remember, no account to create.</p>
<a class="btn" href="/alerts.html">Set up daily alerts</a></div>
<h2>Browse by sector</h2><div class="index">{sec_grid}</div>"""
    write("/index.html", page(f"{BRAND} — {CFG['tagline']}", home,
          desc=CFG["tagline"], canonical="/", extra_head=SEARCH_JS))

    write("/alerts.html", page(f"Daily tender alerts | {BRAND}", ALERTS_BODY,
          desc="Get new EU public tenders matching your sector by email, every morning.",
          canonical="/alerts.html"))
    write("/about.html", page(f"About | {BRAND}", ABOUT_BODY,
          desc=f"What {BRAND} is, where the data comes from, and how often it updates.",
          canonical="/about.html"))

    write("/robots.txt", f"User-agent: *\nAllow: /\nSitemap: {BASE}/sitemap.xml\n")
    # ---- sitemap index --------------------------------------------------
    # One file per section rather than one 3 MB blob: Search Console reports
    # coverage per sitemap, so a section that stops being indexed shows up
    # instead of being averaged away. Chunked well under the 50,000 URL limit.
    def section(u):
        for pre, name in (("/n/", "notices"), ("/cpv/", "cpv"),
                          ("/s/", "sectors"), ("/c/", "countries")):
            if u.startswith(pre):
                return name
        return "core"

    groups = defaultdict(list)
    for u in urls:
        groups[section(u)].append(u)

    parts = []
    for name in ("core", "sectors", "countries", "cpv", "notices"):
        chunk = groups.get(name) or []
        for i in range(0, len(chunk), 10000):
            piece = chunk[i:i + 10000]
            fname = (f"/sitemap-{name}.xml" if len(chunk) <= 10000
                     else f"/sitemap-{name}-{i // 10000 + 1}.xml")
            body = "".join(
                f"<url><loc>{BASE}{u}</loc><lastmod>{NOW.date()}</lastmod></url>"
                for u in piece)
            write(fname, '<?xml version="1.0" encoding="UTF-8"?>'
                  '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
                  f'{body}</urlset>')
            parts.append(fname)

    write("/sitemap.xml", '<?xml version="1.0" encoding="UTF-8"?>'
          '<sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
          + "".join(f"<sitemap><loc>{BASE}{f}</loc>"
                    f"<lastmod>{NOW.date()}</lastmod></sitemap>" for f in parts)
          + '</sitemapindex>')
    print(f"sitemap: {len(urls)} urls across {len(parts)} files")
    write("/style.css", CSS)
    write("/.nojekyll", "")

    # ---- IndexNow ------------------------------------------------------
    # Search engines that support IndexNow (Bing, Yandex, Seznam, Naver) are
    # told about the day's new notices instead of waiting for a crawl. The key
    # file proves we own the site. The request body is written ready to POST;
    # the workflow sends it after the deploy, so the pages are already live.
    key = CFG.get("indexnow_key") or ""
    if key and BASE:
        write(f"/{key}.txt", key)
        cutoff = (NOW.date() - timedelta(days=2)).isoformat()
        fresh = ["/", "/sectors.html", "/countries.html"]
        fresh += [f"/n/{n['id']}.html" for n in rows if (n.get("p") or "") >= cutoff]
        fresh = fresh[:9000]
        body = {
            "host": urlparse(BASE).netloc,
            "key": key,
            "keyLocation": f"{BASE}/{key}.txt",
            "urlList": [BASE + u for u in fresh],
        }
        with open(os.path.join(ROOT, "indexnow.json"), "w", encoding="utf-8") as f:
            json.dump(body, f, ensure_ascii=False)
        print(f"indexnow: {len(fresh)} urls published since {cutoff}")

    print(f"wrote {len(urls)} pages to {OUT}")


CPV_JS = """<script>
document.addEventListener('DOMContentLoaded',function(){var D=null,q=document.getElementById('q'),res=document.getElementById('res');
function esc(s){return String(s).replace(/[&<>"]/g,function(c){return{'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]})}
function mark(s,t){if(!t)return esc(s);var i=s.toLowerCase().indexOf(t);if(i<0)return esc(s);
return esc(s.slice(0,i))+'<em>'+esc(s.slice(i,i+t.length))+'</em>'+esc(s.slice(i+t.length))}
function draw(list,t){if(!list.length){res.innerHTML='<p class="sub">No CPV code matches that. Try a shorter word, or the first digits of a code.</p>';return}
var more=list.length>400?list.length-400:0;
res.innerHTML='<h2>'+list.length+' matching code'+(list.length==1?'':'s')+'</h2><div class="cpv">'+
list.slice(0,400).map(function(r){
return '<a href="/cpv/'+r[0]+'.html"><b>'+mark(r[0],t)+'</b><i>'+mark(r[1],t)+'</i><u>'+
(r[2]?r[2]+(r[2]==1?' open':' open'):'&mdash;')+'</u></a>'}).join('')+'</div>'+
(more?'<p class="sub">'+more+' more &mdash; narrow the search to see them.</p>':'')}
function run(){var t=q.value.trim().toLowerCase();
if(!t){res.innerHTML='';return}
if(!D){fetch('/api/cpv.json').then(function(r){return r.json()}).then(function(j){D=j;run()});
res.innerHTML='<p class="sub">Loading the vocabulary&hellip;</p>';return}
var out=[];for(var i=0;i<D.length;i++){var r=D[i];
if(r[0].indexOf(t)===0||r[1].toLowerCase().indexOf(t)>=0)out.push(r)}
out.sort(function(a,b){return b[2]-a[2]});draw(out,t)}
var tmr;q.addEventListener('input',function(){clearTimeout(tmr);tmr=setTimeout(run,140)});
});
</script>"""

SEARCH_JS = """<script>
document.addEventListener('DOMContentLoaded',function(){var D=null,q=document.getElementById('q');
function esc(s){return String(s).replace(/[&<>"]/g,function(c){return{'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]})}
function load(cb){if(D)return cb();fetch('/api/index.json').then(function(r){return r.json()}).then(function(j){D=j;cb()})}
function fmt(d){try{return new Date(d).toLocaleDateString('en-GB',{day:'2-digit',month:'short',year:'numeric'})}catch(e){return ''}}
function run(){load(function(){
var t=q.value.trim().toLowerCase(),c=document.getElementById('fc').value,s=document.getElementById('fs').value;
if(!t&&!c&&!s){location.reload();return}
var w=t.split(/\\s+/).filter(Boolean),out=[];
for(var i=0;i<D.length&&out.length<300;i++){var n=D[i];
if(c&&n[2]!==c)continue;if(s&&n[3].indexOf(s)<0)continue;
if(w.length){var h=n[1].toLowerCase(),ok=true;
for(var k=0;k<w.length;k++){if(h.indexOf(w[k])<0){ok=false;break}}if(!ok)continue}
out.push(n)}
document.getElementById('res').innerHTML='<h2>'+out.length+(out.length>=300?'+':'')+' matching tenders</h2>'+
out.map(function(n){return '<div class="row"><div class="ref">'+n[0]+'</div><div class="ttl"><a href="/n/'+n[0]+'.html">'+esc(n[1])+'</a></div><div class="when"><b>'+fmt(n[4])+'</b></div></div>'}).join('')||
'<p class="sub">No open tender matches that. Try a broader term.</p>'})}
var tmr;['input','change'].forEach(function(ev){
document.getElementById('q').addEventListener(ev,function(){clearTimeout(tmr);tmr=setTimeout(run,180)});
document.getElementById('fc').addEventListener('change',run);
document.getElementById('fs').addEventListener('change',run)});});
</script>"""

ALERTS_BODY = f"""<h1>Daily tender alerts</h1>
<p class="sub">Checking a procurement portal every morning is the part nobody actually
does. These alerts do it for you.</p>
<h2>Free — RSS, right now</h2>
<p>Every sector and every country page has its own RSS feed. Drop it into your
reader, your Slack, or your Teams channel and you get new tenders as they are published.
No sign-up, no email address, nothing to cancel.</p>
<p><a href="/sectors.html">Pick your sector &rarr;</a></p>
<div class="note"><h2>Pro — the email version</h2>
<p>One email each morning with only the new tenders that match your keywords,
CPV codes and countries &mdash; plus CSV export and the full 12-month archive.
Currently in private beta.</p>
<p><a class="btn" href="{CFG['alerts_url'] or '#'}">Join the beta list</a></p></div>
<h2>Why this exists</h2>
<p>EU tender data is public and free, but it is published in a format built for
lawyers, not for the small companies that could win the work. {BRAND} does one thing:
it takes that firehose and makes it readable, searchable and pushable.</p>"""

ABOUT_BODY = f"""<h1>About {BRAND}</h1>
<p class="sub">{CFG['tagline']}</p>
<h2>Where the data comes from</h2>
<p>Every notice on this site comes from
<a href="https://ted.europa.eu/">Tenders Electronic Daily</a>, the supplement to the
Official Journal of the European Union, through its official public API. TED is the
legally authoritative source; this site is a faster, more readable front door to it.
For anything binding &mdash; specifications, annexes, deadlines &mdash; always open the
official notice, which we link from every page.</p>
<h2>How often it updates</h2>
<p>A scheduled job pulls new notices from TED once a day and rebuilds every page on
this site. Notices are removed once their submission deadline has passed.</p>
<h2>What it covers</h2>
<p>Open calls for competition: contract notices, social and special services notices,
design contests, qualification systems, and prior information notices used as a call
for competition. Contract award notices &mdash; the ones announcing who already won
&mdash; are deliberately left out.</p>
<h2>Independence</h2>
<p>{BRAND} is an independent project. It is not affiliated with, endorsed by, or
operated by the European Union or any contracting authority. Data is re-used under the
European Commission's open data policy.</p>"""

if __name__ == "__main__":
    main()
