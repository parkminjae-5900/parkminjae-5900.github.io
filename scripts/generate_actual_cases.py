#!/usr/bin/env python3
import json, pathlib, re, html, unicodedata
from collections import Counter
from datetime import date
from urllib.parse import parse_qs, unquote, urlparse

ROOT=pathlib.Path(__file__).resolve().parents[1]
DATA=ROOT/"data"/"actual-cases"
REGISTRY=DATA/"facility-identities.json"
CASE_DIR=DATA/"cases"
PUBLIC=DATA/"public.json"
SITEMAP=ROOT/"sitemap.xml"
ORIGIN="https://www.dahamsangjo.co.kr/"
CASE_PREFIX="actual-case-"
INDEX_PAGE=ROOT/"actual-cases.html"

def money(v):
    return "-" if v in (None,"") else f"{int(v):,}원"

def load_cases():
    CASE_DIR.mkdir(parents=True,exist_ok=True)
    out=[]
    seen_ids={}
    for p in sorted(CASE_DIR.glob("*.json")):
        d=json.loads(p.read_text(encoding="utf-8"))
        d["_source"]=p.name
        validate(d)
        case_id=d["id"]
        if case_id in seen_ids:
            raise SystemExit(f"{p.name}: duplicate case id {case_id} already used by {seen_ids[case_id]}")
        seen_ids[case_id]=p.name
        if d["publication"]["publish"]:
            out.append(d)
    return out

def norm_identity(value):
    return re.sub(r"\s+"," ",unicodedata.normalize("NFC",str(value or "")).strip())

def identity_tuple(ident):
    return tuple(norm_identity(ident.get(key)) for key in ["facilityName","address","officialBranchName","sourceUrl","facilityCode"])

def validate_identity_fields(ident,label):
    required=["facilityName","address","officialBranchName","sourceUrl","facilityCode"]
    missing=[key for key in required if not norm_identity(ident.get(key))]
    if missing:
        raise SystemExit(f"{label}: missing facility identity fields {', '.join(missing)}")
    parsed=urlparse(ident["sourceUrl"])
    if parsed.scheme != "https" or not parsed.netloc:
        raise SystemExit(f"{label}: sourceUrl must be an absolute HTTPS URL")
    code=norm_identity(ident["facilityCode"])
    query_values={norm_identity(v) for values in parse_qs(parsed.query,keep_blank_values=True).values() for v in values}
    path_values={norm_identity(unquote(part)) for part in parsed.path.split("/") if part}
    if code not in query_values and code not in path_values:
        raise SystemExit(f"{label}: facilityCode is not an exact sourceUrl query/path value")

def load_facility_registry():
    try:
        payload=json.loads(REGISTRY.read_text(encoding="utf-8"))
    except Exception as exc:
        raise SystemExit(f"facility identity registry unavailable: {exc}")
    records={}
    ids=set()
    for record in payload.get("facilities",[]):
        facility_id=norm_identity(record.get("facilityId"))
        if not facility_id:
            raise SystemExit("facility identity registry: missing facilityId")
        if facility_id in ids:
            raise SystemExit(f"facility identity registry: duplicate facilityId {facility_id}")
        if record.get("sourceGrade")!="A":
            raise SystemExit(f"facility identity registry: {facility_id} is not sourceGrade A")
        validate_identity_fields(record,f"facility identity registry {facility_id}")
        key=identity_tuple(record)
        if key in records:
            raise SystemExit(f"facility identity registry: duplicate exact identity {facility_id}")
        ids.add(facility_id)
        records[key]=record
    return records

def validate_facility_identity(d):
    ident=d.get("facility_identity")
    if not isinstance(ident,dict):
        raise SystemExit(f"{d['id']}: publish requires facility_identity")
    validate_identity_fields(ident,d["id"])
    if norm_identity(ident["facilityName"]) != norm_identity(d["funeral_hall"]):
        raise SystemExit(f"{d['id']}: funeral_hall and facilityName mismatch")
    record=load_facility_registry().get(identity_tuple(ident))
    if not record:
        raise SystemExit(f"{d['id']}: facility identity is not an exact sourceGrade A registry record")
    return ident,record

def facility_identity_key(d):
    _,record=validate_facility_identity(d)
    return record["facilityId"]

def validate(d):
    req=["id","event_month","region","funeral_hall","funeral_type","publication"]
    for k in req:
        if not d.get(k): raise SystemExit(f"{d.get('_source','case')}: missing {k}")
    pub=d["publication"]
    if pub.get("publish"):
        validate_facility_identity(d)
        if not pub.get("privacy_reviewed"): raise SystemExit(f"{d['id']}: publish requires privacy_reviewed")
        if not pub.get("costs_verified"): raise SystemExit(f"{d['id']}: publish requires costs_verified")
        if d.get("photos") and not pub.get("explicit_photo_permission"):
            raise SystemExit(f"{d['id']}: photos require explicit_photo_permission")
        for ph in d.get("photos",[]):
            if not ph.get("privacy_checked"): raise SystemExit(f"{d['id']}: photo privacy check missing")
        if d.get("receipt_public_image") and not pub.get("privacy_reviewed"):
            raise SystemExit(f"{d['id']}: public receipt requires privacy review")
    banned=["resident_id","account_number","card_number","phone","signature","deceased_name","bereaved_name","home_address"]
    raw=json.dumps(d,ensure_ascii=False).lower()
    for key in banned:
        if f'"{key}"' in raw: raise SystemExit(f"{d['id']}: forbidden public field {key}")
    pii_patterns={
        "email": r"[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}",
        "phone": r"(?:01[016789]|0[2-6][1-5]?)[-. ]?\d{3,4}[-. ]?\d{4}",
        "resident registration number": r"\d{6}-[1-8]\d{6}",
        "payment or account number": r"(?<!\d)(?:\d{4}[- ]?){3}\d{4}(?!\d)|(?<!\d)\d{10,14}(?!\d)",
    }
    for label,pattern in pii_patterns.items():
        if re.search(pattern,raw,re.I): raise SystemExit(f"{d['id']}: possible {label} in public case data")

def page_url(case):
    return f"{ORIGIN}{CASE_PREFIX}{case['id']}.html"

def build_case(c):
    esc=html.escape
    title=f"{c['funeral_hall']} {c['funeral_type']} 실제 장례비용 사례 | 다함상조"
    desc=f"{c['event_month']} {c['region']} {c['funeral_hall']}에서 진행한 {c['funeral_type']} 실제 행사 사례입니다. 영수증으로 확인된 비용 항목과 공개 허용된 행사사진을 비식별화해 정리했습니다."
    package=c.get("package") or {}
    costs=c.get("costs") or {}
    line_rows="".join(f"<tr><td>{esc(x['label'])}</td><td>{money(x['amount'])}</td><td>{esc(x.get('source',''))}</td></tr>" for x in c.get("verified_line_items",[]))
    photos="".join(f'<figure><img src="{esc(p["path"])}" alt="{esc(p["alt"])}" loading="lazy"><figcaption>{esc(p["alt"])}</figcaption></figure>' for p in c.get("photos",[]))
    notes="".join(f"<li>{esc(x)}</li>" for x in c.get("notes_public",[]))
    hall_link=c.get("funeral_hall_page") or ""
    region_link=c.get("region_page") or ""
    refs="".join([
      f'<a href="{esc(hall_link)}">장례식장 안내</a>' if hall_link else "",
      f'<a href="{esc(region_link)}">지역 장례비용</a>' if region_link else "",
      '<a href="funeral-cost-calculator.html">내 조건으로 예상견적</a>'
    ])
    schema={"@context":"https://schema.org","@type":"Article","headline":title,"datePublished":c["event_month"]+"-01","dateModified":date.today().isoformat(),"mainEntityOfPage":page_url(c),"publisher":{"@id":ORIGIN+"#organization"}}
    return f'''<!doctype html><html lang="ko"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{esc(title)}</title><meta name="description" content="{esc(desc)}"><meta name="robots" content="index,follow,max-image-preview:large,max-snippet:-1">
<link rel="canonical" href="{page_url(c)}"><meta property="og:type" content="article"><meta property="og:title" content="{esc(title)}"><meta property="og:description" content="{esc(desc)}"><meta property="og:url" content="{page_url(c)}"><meta property="og:image" content="{ORIGIN}assets/daham_logo.jpg">
<script type="application/ld+json">{json.dumps(schema,ensure_ascii=False)}</script>
<style>*{{box-sizing:border-box}}body{{margin:0;background:#fffdf9;color:#211b17;font:18px/1.75 "Noto Sans KR","Malgun Gothic",sans-serif;word-break:keep-all}}a{{color:inherit;text-decoration:none}}.top{{background:#211914;color:#fff;padding:13px 20px}}.wrap{{width:min(1060px,calc(100% - 36px));margin:auto}}.hero{{background:linear-gradient(135deg,#241a14,#6d4b2d);color:#fff;text-align:center;padding:58px 20px}}h1{{font-size:clamp(34px,5vw,54px);line-height:1.2}}.panel{{background:#fff;border:1px solid #e6dbc9;border-radius:18px;padding:25px;margin:18px 0}}.grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(210px,1fr));gap:12px}}.card{{background:#fff9ef;border:1px solid #e6dbc9;border-radius:14px;padding:18px}}table{{width:100%;border-collapse:collapse}}th,td{{padding:12px;border-bottom:1px solid #eadfce;text-align:left}}.photos{{display:grid;grid-template-columns:repeat(auto-fit,minmax(240px,1fr));gap:14px}}figure{{margin:0}}figure img{{width:100%;height:260px;object-fit:cover;border-radius:14px}}figcaption{{font-size:14px;color:#6b625a}}.links{{display:flex;flex-wrap:wrap;gap:8px}}.links a{{padding:10px 14px;border:1px solid #d8bd82;border-radius:999px;background:#fffaf0;font-weight:850}}.verified{{display:inline-block;background:#eef7eb;color:#315d2b;padding:7px 12px;border-radius:999px;font-weight:900}}@media(max-width:650px){{body{{font-size:17px}}.panel{{padding:20px 16px}}}}</style></head><body>
<div class="top"><div class="wrap"><strong>다함상조 실제 장례 데이터</strong></div></div>
<header class="hero"><span class="verified">실제 행사 · 비용 검증</span><h1>{esc(c['funeral_hall'])}<br>{esc(c['funeral_type'])} 실제 장례비용 사례</h1><p>{esc(c['event_month'])} · {esc(c['region'])} · 개인정보 비식별화 공개본</p></header>
<main class="wrap">
<section class="panel"><h2>행사 조건</h2><div class="grid">
<div class="card"><b>장례식장</b><p>{esc(c['funeral_hall'])}</p></div>
<div class="card"><b>장례형태</b><p>{esc(c['funeral_type'])}</p></div>
<div class="card"><b>조문객</b><p>{esc(str(c.get('guest_count'))) + '명' if c.get('guest_count') is not None else '비공개/미확인'}</p></div>
<div class="card"><b>상품</b><p>{esc(package.get('name','미확인'))} {money(package.get('amount'))}</p></div>
</div></section>
<section class="panel"><h2>영수증으로 확인한 실제 비용</h2><table><thead><tr><th>항목</th><th>금액</th><th>확인근거</th></tr></thead><tbody>{line_rows or '<tr><td colspan="3">공개 가능한 세부항목 없음</td></tr>'}</tbody></table>
<p><strong>실제 최종 결제금액: {money(costs.get('total_paid'))}</strong></p><p>※ 이 금액은 해당 행사 시점의 실제 사례이며 현재 시설가격을 보장하는 견적이 아닙니다.</p></section>
{f'<section class="panel"><h2>실제 행사사진</h2><div class="photos">{photos}</div></section>' if photos else ''}
{f'<section class="panel"><h2>공개 참고사항</h2><ul>{notes}</ul></section>' if notes else ''}
<section class="panel"><h2>같은 조건으로 비교하기</h2><div class="links">{refs}</div></section>
</main><script src="conversion-funnel.js?v=20261007" defer></script></body></html>'''

def build_index(cases):
    cards="".join(f'''<a class="card" href="{CASE_PREFIX}{c['id']}.html"><b>{html.escape(c['funeral_hall'])}</b><span>{html.escape(c['event_month'])} · {html.escape(c['region'])} · {html.escape(c['funeral_type'])} · 실제 결제 {money((c.get('costs') or {}).get('total_paid'))}</span></a>''' for c in cases)
    return f'''<!doctype html><html lang="ko"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>실제 장례비용 사례 | 장례식장·지역별 실제 행사 데이터 | 다함상조</title><meta name="description" content="다함상조가 실제 진행한 장례행사의 비식별화된 사진과 영수증 기반 비용사례를 장례식장·지역·장례형태별로 확인하세요."><meta name="robots" content="index,follow,max-image-preview:large"><link rel="canonical" href="{ORIGIN}actual-cases.html"><style>*{{box-sizing:border-box}}body{{margin:0;background:#fffdf9;color:#211b17;font:18px/1.75 "Noto Sans KR","Malgun Gothic",sans-serif}}.wrap{{width:min(1080px,calc(100% - 36px));margin:auto}}.hero{{background:#211914;color:#fff;padding:58px 20px;text-align:center}}h1{{font-size:clamp(34px,5vw,54px)}}main{{padding:28px 0 100px}}.grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(260px,1fr));gap:14px}}.card{{display:block;background:#fff;border:1px solid #e5d8c5;border-radius:16px;padding:20px;color:inherit;text-decoration:none}}.card b{{display:block;font-size:20px;color:#704b15}}.card span{{font-size:15px;color:#665f57}}</style></head><body><header class="hero"><h1>실제 장례비용 사례</h1><p>실제 행사사진과 영수증을 개인정보 비식별화 후 비용 데이터로 공개합니다.</p></header><main class="wrap"><div class="grid">{cards}</div></main><script src="conversion-funnel.js?v=20261007" defer></script></body></html>'''

def update_sitemap(cases):
    if not SITEMAP.exists(): return
    s=SITEMAP.read_text(encoding="utf-8")
    s=re.sub(r'\s*<url><loc>'+re.escape(ORIGIN)+r'(?:actual-cases\.html|actual-case-[^<]+\.html)</loc>.*?</url>','',s)
    if cases:
        urls=[ORIGIN+"actual-cases.html"]+[page_url(c) for c in cases]
        block="\n".join(f'  <url><loc>{u}</loc><lastmod>{date.today().isoformat()}</lastmod><priority>0.92</priority></url>' for u in urls)
        s=s.replace("</urlset>",block+"\n</urlset>")
    SITEMAP.write_text(s,encoding="utf-8")

def cleanup_generated():
    for p in ROOT.glob(CASE_PREFIX+"*.html"): p.unlink()
    if INDEX_PAGE.exists(): INDEX_PAGE.unlink()

def main():
    cases=load_cases()
    cleanup_generated()
    public=[]
    for c in cases:
        path=ROOT/f"{CASE_PREFIX}{c['id']}.html"
        path.write_text(build_case(c),encoding="utf-8")
        item={k:c.get(k) for k in ["id","event_month","region","district","funeral_hall","funeral_hall_page","region_page","funeral_type","guest_count","package","costs","photos"]}
        item["facility_identity"]=c["facility_identity"]
        item["facility_key"]=facility_identity_key(c)
        public.append(item)
    identity_counts=Counter(item["facility_key"] for item in public)
    identity_rows={}
    for item in public:
        key=item["facility_key"]
        if key not in identity_rows:
            identity_rows[key]={**item["facility_identity"],"facilityKey":key,"eventCount":identity_counts[key]}
    summary={
        "publishedCaseCount":len(public),
        "uniqueFacilityCount":len(identity_counts),
        "repeatFacilityCount":sum(1 for count in identity_counts.values() if count > 1),
        "facilities":list(identity_rows.values()),
    }
    PUBLIC.write_text(json.dumps({"version":date.today().isoformat(),"summary":summary,"cases":public},ensure_ascii=False,indent=2),encoding="utf-8")
    if cases: INDEX_PAGE.write_text(build_index(cases),encoding="utf-8")
    update_sitemap(cases)
    print(json.dumps({"published_cases":len(cases),"unique_facilities":len(identity_counts),"repeat_facilities":summary["repeatFacilityCount"],"generated":[f"{CASE_PREFIX}{c['id']}.html" for c in cases]},ensure_ascii=False))

if __name__=="__main__": main()
