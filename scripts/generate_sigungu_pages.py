#!/usr/bin/env python3
"""Generate data-backed 시·군·구 pages from the public funeral-facility snapshot."""
from __future__ import annotations
import html, json, re, unicodedata
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageEnhance

ROOT=Path(__file__).resolve().parents[1]
BASE="https://www.dahamsangjo.co.kr/"
DATA=json.loads((ROOT/'data/funeral-halls.json').read_text(encoding='utf-8'))
items=DATA['items']; updated=DATA['updatedAt'][:10]
PROVINCE={
'서울특별시':'seoul','부산광역시':'busan','대구광역시':'daegu','인천광역시':'incheon','광주광역시':'gwangju','대전광역시':'daejeon','울산광역시':'ulsan','세종특별자치시':'sejong','경기도':'gyeonggi','강원특별자치도':'gangwon','충청북도':'chungbuk','충청남도':'chungnam','전북특별자치도':'jeonbuk','전라남도':'jeonnam','경상북도':'gyeongbuk','경상남도':'gyeongnam','제주특별자치도':'jeju'}
SIG={
'강남구':'gangnam','강동구':'gangdong','강북구':'gangbuk','강서구':'gangseo','관악구':'gwanak','광진구':'gwangjin','구로구':'guro','금천구':'geumcheon','노원구':'nowon','도봉구':'dobong','동대문구':'dongdaemun','동작구':'dongjak','마포구':'mapo','서대문구':'seodaemun','서초구':'seocho','성동구':'seongdong','성북구':'seongbuk','송파구':'songpa','양천구':'yangcheon','영등포구':'yeongdeungpo','용산구':'yongsan','은평구':'eunpyeong','종로구':'jongno','중구':'jung','중랑구':'jungnang'}
def slug(v):
    v=v.strip()
    known=SIG.get(v)
    if known:
        return known
    import hashlib
    return 'region-' + hashlib.sha1(v.encode('utf-8')).hexdigest()[:8]
def esc(v): return html.escape(str(v or '미확인'), quote=True)
def font(size):
    for p in ['/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc','/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc','/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf']:
        if Path(p).exists(): return ImageFont.truetype(p,size)
    return ImageFont.load_default()

def image_for(prov, sigungu, path, idx):
    out=ROOT/'assets'/'regional'
    out.mkdir(exist_ok=True)
    # One authoritative image per province keeps the asset set light while each
    # page still exposes a proper image URL instead of the site-wide logo.
    dest=out/(PROVINCE.get(prov, 'region') + '.jpg')
    if dest.exists(): return f'{BASE}assets/regional/{dest.name}'
    im=Image.open(ROOT/'assets/regional-funeral-base.png').convert('RGB').resize((1200,675))
    # Small deterministic crop/tonal variation keeps each regional asset distinct while preserving the scene.
    if idx%3==1: im=im.crop((12,0,1188,675)).resize((1200,675))
    elif idx%3==2: im=ImageEnhance.Color(im).enhance(0.92)
    # Keep the representative image free of rasterized Korean text.
    # The page title and caption are rendered as HTML, preventing missing-glyph boxes.
    im.save(dest,'JPEG',quality=88,optimize=True)
    return f'{BASE}assets/regional/{dest.name}'

groups={}
for x in items:
    p=x.get('ctpv') or ''; s=x.get('sigungu') or ''
    if p and s: groups.setdefault((p,s),[]).append(x)
rows=[]
for (prov,sigungu), vals in sorted(groups.items()):
    code=f"{PROVINCE.get(prov,slug(prov))}-{slug(sigungu)}"
    path=f'area-{code}-funeral.html'
    rows.append((prov,sigungu,vals,path))
for idx,(prov,sigungu,vals,path) in enumerate(rows):
    label=f'{prov} {sigungu}'
    vals=sorted(vals,key=lambda x:(x.get('fcltNm') or ''))
    cards=[]
    for x in vals:
        park=x.get('tpkct'); park=f"{int(float(park)):,}대" if park and str(park) not in ('0','0.0') else '등록값 미확인'
        cards.append(f'<article class="facility"><h2>{esc(x.get("fcltNm"))}</h2><p>{esc(x.get("addr"))}</p><dl><div><dt>유형</dt><dd>{esc(x.get("gubun"))} · {esc(x.get("operType"))}</dd></div><div><dt>빈소·안치</dt><dd>{esc(x.get("mtaCnt"))}실 · {esc(x.get("ehrCnt"))}구</dd></div><div><dt>주차</dt><dd>{park}</dd></div><div><dt>전화</dt><dd>{esc(x.get("telno"))}</dd></div></dl></article>')
    image=image_for(prov,sigungu,path,idx)
    desc=f'{label} 장례식장 {len(vals)}곳의 주소·빈소·안치·주차·연락처와 가족장·무빈소 장례비용 확인 항목을 안내합니다.'
    html_page=f'''<!doctype html><html lang="ko"><head>
<link rel="shortcut icon" href="https://www.dahamsangjo.co.kr/favicon.ico" type="image/x-icon">
<link rel="icon" href="https://www.dahamsangjo.co.kr/favicon.png" type="image/png" sizes="192x192">
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{esc(label)} 장례식장·가족장·무빈소 비용 | 다함상조</title><meta name="description" content="{esc(desc)}"><meta name="keywords" content="{esc(sigungu)} 무빈소,{esc(sigungu)} 가족장,{esc(sigungu)} 장례식장,{esc(sigungu)} 장례비용,{esc(prov)} 후불상조"><meta name="robots" content="index,follow,max-image-preview:large,max-snippet:-1"><link rel="canonical" href="{BASE}{path}"><meta property="og:type" content="website"><meta property="og:title" content="{esc(label)} 장례식장·가족장·무빈소 비용 | 다함상조"><meta property="og:description" content="{esc(desc)}"><meta property="og:url" content="{BASE}{path}"><meta property="og:image" content="{image}"><meta property="og:image:width" content="1200"><meta property="og:image:height" content="675"><meta property="og:image:alt" content="{esc(label)} 장례안내 대표 이미지"><meta name="twitter:card" content="summary_large_image"><meta name="twitter:image" content="{image}"><style>*{{box-sizing:border-box}}body{{margin:0;background:#faf6ef;color:#29231f;font:17px/1.75 'Malgun Gothic','Noto Sans KR',sans-serif;word-break:keep-all}}a{{color:inherit}}.top,footer{{background:#211914;color:#fff;padding:14px 20px}}.inner,.wrap{{max-width:1080px;margin:auto}}.top .inner{{display:flex;justify-content:space-between}}.top a,footer a{{color:#f2c968}}.hero{{padding:48px 20px;background:linear-gradient(135deg,#2b1d14,#725035);color:#fff;text-align:center}}h1{{font-size:clamp(30px,5vw,48px);line-height:1.25;margin:8px 0 14px}}.hero p{{max-width:820px;margin:0 auto 20px;font-size:19px}}.hero img{{display:block;width:min(100%,900px);height:auto;margin:24px auto 0;border-radius:16px;box-shadow:0 10px 30px #1b110b77}}.caption{{font-size:13px;color:#ead7b4;margin-top:7px}}.wrap{{padding:26px 20px}}.panel{{background:#fff;border:1px solid #e4d5bd;border-radius:18px;padding:25px;margin:20px 0}}.grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(280px,1fr));gap:15px}}.facility{{background:#fffaf1;border:1px solid #e4d5bd;border-radius:14px;padding:18px}}.facility h2{{font-size:21px;color:#744f18;margin:0 0 7px}}dl{{margin:0}}dl div{{display:flex;gap:12px;border-top:1px solid #eee0ca;padding:6px 0}}dt{{font-weight:800;min-width:76px}}dd{{margin:0}}.btn{{display:inline-block;background:#b68115;color:#fff;text-decoration:none;font-weight:900;border-radius:10px;padding:13px 18px;margin:5px}}.btn.alt{{background:#fff;color:#2b241f}}.sticky{{position:fixed;left:0;right:0;bottom:0;display:flex;z-index:10}}.sticky a{{flex:1;text-align:center;padding:14px;background:#211914;color:#fff;text-decoration:none;font-weight:900}}.sticky a:first-child{{background:#b68115}}@media(max-width:640px){{.top .inner{{display:block}}.panel{{padding:20px 16px}}.hero{{padding:40px 16px}}}}</style></head><body><div class="top"><div class="inner"><strong>다함상조 {esc(label)} 장례안내</strong><a href="tel:16006131">24시간 1600-6131</a></div></div><header class="hero"><h1>{esc(label)} 장례식장·가족장·무빈소 비용 안내</h1><p>{esc(label)} 시설 정보를 공공데이터 기준으로 확인하고, 상조 상품비와 장례식장·음식·화장·장지 비용을 나누어 상담하세요.</p><a class="btn" href="tel:16006131">24시간 상담</a><a class="btn alt" href="funeral-cost-calculator.html">예상비용 계산</a><img src="{image}" alt="{esc(label)} 장례안내 대표 이미지"><div class="caption">AI 연출 이미지이며 특정 장례식장 실제 사진이 아닙니다.</div></header><main class="wrap"><section class="panel"><h2>{esc(label)} 장례식장 {len(vals)}곳</h2><p>전국 장사시설 공공데이터 {updated} 갱신본 기준입니다. 실제 운영·예약·가격과 무빈소 가능 여부는 이용 전 해당 시설에 최종 확인해야 합니다.</p><div class="grid">{''.join(cards)}</div></section><section class="panel"><h2>{esc(sigungu)} 장례비용 확인 순서</h2><div class="grid"><article class="facility"><h2>상조 상품비</h2><p>무빈소 120만원, 가족장 249만원, 일반장 360만원, 프리미엄 499만원의 포함 품목을 확인합니다.</p></article><article class="facility"><h2>시설·접객비</h2><p>빈소·안치실·입관실과 음식·접객비는 시설과 조문객 수에 따라 달라집니다.</p></article><article class="facility"><h2>화장·장지비</h2><p>화장장 예약, 관내 자격, 봉안·자연장과 이동거리를 따로 확인합니다.</p></article></div><p>공개되지 않은 금액은 추정하지 않습니다. 실제 날짜와 시설을 정한 뒤 최신 견적을 확인하세요.</p></section><section class="panel"><h2>{esc(sigungu)} 가족장·무빈소 상담</h2><p>가족장은 가까운 가족·친지 중심으로 빈소를 운영하고, 무빈소는 일반 조문용 빈소 없이 안치·입관·발인·화장 절차 중심으로 진행합니다. 시설별 허용 조건이 다르므로 예약 전에 확인해야 합니다.</p><a class="btn" href="family.html">가족장 249만원</a><a class="btn" href="nobinso.html">무빈소 120만원</a><a class="btn" href="area-funeral-seo-hub.html">지역별 안내</a></section></main><footer><div class="wrap">다함상조 · {esc(label)} 장례상담 1600-6131 · <a href="/">공식 홈페이지</a></div></footer><div class="sticky"><a href="tel:16006131">전화상담</a><a href="funeral-cost-calculator.html">비용계산</a></div><script src="conversion-funnel.js?v=20261005" defer></script></body></html>'''
    (ROOT/path).write_text(html_page,encoding='utf-8')
# Add generated URLs without duplicates.
smap=ROOT/'sitemap.xml'; text=smap.read_text(encoding='utf-8'); additions=[]
for _,_,_,path in rows:
    url=BASE+path
    if url not in text: additions.append(f'  <url><loc>{url}</loc><lastmod>2026-10-05</lastmod></url>\n')
if additions:
    stext=text.replace('</urlset>',''.join(additions)+'</urlset>'); smap.write_text(stext,encoding='utf-8')
print(f'generated {len(rows)} sigungu pages and {len(rows)} regional images; {len(additions)} sitemap URLs added')
