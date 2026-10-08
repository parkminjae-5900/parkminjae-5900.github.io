#!/usr/bin/env python3
"""Conservative and idempotent metadata enhancement for Daham static HTML pages.
No generated testimonials, prices, logos or unverified facility-specific photographs.
"""
from pathlib import Path
from html import escape, unescape
from urllib.parse import quote
import re, json, argparse

ROOT = Path(__file__).resolve().parents[1]
BASE = "https://www.dahamsangjo.co.kr"
DEFAULT_IMAGE = BASE + "/assets/regional-funeral-base.png"
LOGO = BASE + "/assets/daham_logo.jpg"
PATTERN = re.compile(r"<head\\b[^>]*>", re.I)
def tag_content(s, name):
    m = re.search(r'<meta\\s+name=["\\']'+re.escape(name)+r'["\\']\\s+content=["\\']([^"\\']*)',s,re.I)
    return unescape(m.group(1)) if m else ""
def attr_meta(s, field, key):
    m = re.search(r'<meta\\s+'+field+r'=["\\']'+re.escape(key)+r'["\\']\\s+content=["\\']([^"\\']*)',s,re.I)
    return unescape(m.group(1)) if m else ""
def title_of(s):
    m = re.search(r'<title[^>]*>(.*?)</title>',s,re.I|re.S)
    return unescape(re.sub(r'<[^>]+>','',m.group(1)).strip()) if m else ""
def image_for(s, path):
    existing = attr_meta(s, 'property', 'og:image')
    if existing: return existing
    # Prefer proven local editorial image only; never mislabel generated assets as a real facility.
    for pattern in [r'<img\\b[^>]*\\bsrc=["\\']([^"\\']+)']:
        for m in re.finditer(pattern,s,re.I):
            src=m.group(1)
            if src.startswith('assets/') and (ROOT/src).is_file() and not any(x in src.lower() for x in ['logo','avatar','staff','icon']):
                return BASE+'/'+quote(src, safe='/')
    return DEFAULT_IMAGE if (ROOT/'assets/regional-funeral-base.png').is_file() else ''
def add_meta(out, name, value, attr='property'):
    if not value or attr_meta(out,attr,name): return out
    return out + '<meta '+attr+'="'+name+'" content="'+escape(value,quote=True)+'">\\n'
def process(path, write=False):
    raw=path.read_text(encoding='utf-8')
    if not re.search(r'</head>',raw,re.I): return 'skip-no-head'
    if 'data-daham-seo-automation="1"' in raw: return 'unchanged'
    title=title_of(raw)
    if not title: return 'skip-no-title'
    desc=tag_content(raw,'description')
    canonical_match=re.search(r'<link\\b[^>]*rel=["\\']canonical["\\'][^>]*href=["\\']([^"\\']+)',raw,re.I)
    canonical=canonical_match.group(1) if canonical_match else BASE+'/'+quote(path.relative_to(ROOT).as_posix(),safe='/')
    # Do not index utility, reports, applications or private pages automatically.
    robots=tag_content(raw,'robots')
    if 'noindex' in robots.lower(): return 'skip-noindex'
    page_image=image_for(raw,path)
    block='\\n<!-- data-daham-seo-automation="1": managed by scripts/enrich_seo.py -->\\n'
    block=add_meta(block,'og:site_name','다함상조')
    block=add_meta(block,'og:type','website')
    block=add_meta(block,'og:locale','ko_KR')
    if not attr_meta(raw,'property','og:title'): block=add_meta(block,'og:title',title)
    if desc and not attr_meta(raw,'property','og:description'): block=add_meta(block,'og:description',desc)
    if not attr_meta(raw,'property','og:url'): block=add_meta(block,'og:url',canonical)
    if not attr_meta(raw,'property','og:image'): block=add_meta(block,'og:image',page_image)
    if not attr_meta(raw,'name','twitter:card'): block=add_meta(block,'twitter:card','summary_large_image','name')
    if not attr_meta(raw,'name','twitter:image'): block=add_meta(block,'twitter:image',page_image,'name')
    if not re.search(r'<script[^>]*type=["\\']application/ld\\+json',raw,re.I):
        ld={'@context':'https://schema.org','@type':'WebPage','url':canonical,'name':title,'inLanguage':'ko-KR'}
        if desc: ld['description']=desc
        if page_image: ld['primaryImageOfPage']={'@type':'ImageObject','url':page_image}
        block += '<script type="application/ld+json">'+json.dumps(ld,ensure_ascii=False,separators=(',',':'))+'</script>\\n'
    updated=re.sub(r'</head>',lambda m:block+m.group(0),raw,count=1,flags=re.I)
    if updated==raw:return 'unchanged'
    if write:path.write_text(updated,encoding='utf-8')
    return 'changed'
def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--write',action='store_true')
    parser.add_argument('--limit',type=int,default=0)
    args=parser.parse_args()
    counts={}
    files=sorted(ROOT.rglob('*.html'))
    # Exclude vendor and build output; only public SEO-relevant HTML documents.
    files=[x for x in files if not any(p.startswith('.') or p in ('node_modules','vendor','dist','build') for p in x.relative_to(ROOT).parts)]
    # Avoid touching interactive apps, private reports, or authenticated flows.
    files=[x for x in files if not any(p in x.relative_to(ROOT).parts for p in ('quote-app','event-report','app','admin','staff','report'))]
    if args.limit:files=files[:args.limit]
    for path in files:
        try: result=process(path,args.write)
        except (OSError,UnicodeError) as exc:
            print('ERROR',path.relative_to(ROOT),exc);raise
        counts[result]=counts.get(result,0)+1
    print(json.dumps({'mode':'write' if args.write else 'dry-run','scanned':len(files),'results':counts},ensure_ascii=False))
if __name__=='__main__':main()
