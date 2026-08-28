#!/usr/bin/env python3
"""Generate the static site from the local notice store."""
import html
import json
import os
import re
import shutil
from urllib.parse import urlparse
from collections import defaultdict
from datetime import datetime, timezone

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
    rows = [r for r in rows if deadline_bits(r["d"])[1] >= 0]
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

    by_country = defaultdict(list)
    by_sector = defaultdict(list)
    for n in rows:
        by_country[n.get("c") or "XXX"].append(n)
        for d in n.get("cpv", []):
            by_sector[d].append(n)

    urls = ["/", "/sectors.html", "/countries.html", "/alerts.html", "/about.html"]

    # ---- notice pages -------------------------------------------------
    for n in rows:
        dl, days = deadline_bits(n["d"])
        cpv_links = ", ".join(
            f'<a href="/s/{c}.html">{esc(meta.cpv_label(c))}</a>'
            for c in n.get("cpv", []))
        desc = (f'<div class="desc">{esc(n["desc"])}</div>' if n.get("desc") else "")
        body = f"""<div class="detail">
<div class="crumb"><a href="/">Home</a> / <a href="/c/{esc(n.get('c'))}.html">{esc(meta.country_name(n.get('c')))}</a></div>
<h1>{esc(n['t'])}</h1>
<p class="sub">Open call for tenders published in the EU Official Journal.
{('Closes in %d days.' % days) if 0 <= days < 400 else ''}</p>
{desc}
<dl>
<dt>Buyer</dt><dd>{esc(n.get('b')) or '&mdash;'}</dd>
<dt>Country</dt><dd><a href="/c/{esc(n.get('c'))}.html">{esc(meta.country_name(n.get('c')))}</a></dd>
<dt>Submission deadline</dt><dd class="{'due' if days<=7 else ''}">{esc(dl) or '&mdash;'}</dd>
<dt>Contract type</dt><dd>{esc(meta.CONTRACT_NATURE.get(n.get('nat'), n.get('nat') or '&mdash;'))}</dd>
<dt>Sector (CPV)</dt><dd>{cpv_links or '&mdash;'}</dd>
<dt>Main CPV code</dt><dd>{esc(n.get('cpvf')) or '&mdash;'}</dd>
<dt>Place of performance</dt><dd>{esc(n.get('nuts')) or '&mdash;'}</dd>
<dt>Published</dt><dd>{esc(n.get('p'))}</dd>
<dt>TED reference</dt><dd>{esc(n['id'])}</dd>
</dl>
<p><a class="btn" href="https://ted.europa.eu/en/notice/-/detail/{esc(n['id'])}" rel="nofollow noopener" target="_blank">Read the official notice on TED &rarr;</a></p>
<div class="note"><h2>Don't want to check this page every morning?</h2>
<p>Get the new tenders that match your sector and country in one daily email.</p>
<a class="btn" href="/alerts.html">Set up alerts</a></div>
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
              page(f"{n['t'][:110]} | {BRAND}", body,
                   extra_head=f'<script type="application/ld+json">{ld}</script>',
                   desc=f"{meta.country_name(n.get('c'))}: {n['t'][:130]}. Deadline {dl}.",
                   canonical=f"/n/{n['id']}.html"))
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
    smap = "".join(f"<url><loc>{BASE}{u}</loc><lastmod>{NOW.date()}</lastmod></url>"
                   for u in urls)
    write("/sitemap.xml",
          f'<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">{smap}</urlset>')
    write("/style.css", CSS)
    write("/.nojekyll", "")
    print(f"wrote {len(urls)} pages to {OUT}")


SEARCH_JS = """<script>
(function(){var D=null,q=document.getElementById('q');
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
document.getElementById('fs').addEventListener('change',run)});})();
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
