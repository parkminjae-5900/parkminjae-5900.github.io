#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
다함상조 읍면동 SEO 정적 페이지 생성기.
입력:
  data/legal-dong.csv       행정표준코드관리시스템에서 내려받은 현존 법정동 자료
  data/funeral-halls.csv    장례식장 DB (name,address,region1,region2,dong,price_verified,...)
  data/estimate-cases.csv   검증된 견적 사례 (선택)
출력:
  local/<sigungu-slug>/<dong-slug>/index.html
중요: 동명만 바꾼 복제 페이지는 만들지 않는다.
"""

from __future__ import annotations
import csv, html, json, re, unicodedata
from pathlib import Path
from collections import defaultdict

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
OUT = ROOT / "local"

def slugify_kr(s: str) -> str:
    s = unicodedata.normalize("NFKC", (s or "").strip())
    s = re.sub(r"\s+", "-", s)
    s = re.sub(r"[^0-9A-Za-z가-힣-]", "", s)
    return s.lower().strip("-")

def read_csv(path: Path):
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))

def active_dongs(rows):
    """다양한 다운로드 열 이름을 허용하고 '폐지'는 제외."""
    out = []
    for r in rows:
        status = (r.get("폐지구분") or r.get("status") or "").strip()
        if status and status not in {"0","현존","존재","N","n"}:
            continue
        full = (r.get("법정동명") or r.get("지역주소명") or r.get("full_name") or "").strip()
        if not full:
            continue
        parts = full.split()
        if len(parts) < 3:
            continue
        # 동/읍/면 레벨만. 리는 동 페이지 내부 데이터로 흡수.
        leaf = parts[-1]
        if not leaf.endswith(("동","읍","면")):
            continue
        out.append({
            "full": full,
            "sido": parts[0],
            "sigungu": " ".join(parts[1:-1]),
            "dong": leaf,
            "code": r.get("법정동코드") or r.get("지역코드") or r.get("code") or ""
        })
    return out

def facility_index(rows):
    by_key = defaultdict(list)
    for r in rows:
        sido=(r.get("region1") or r.get("시도") or "").strip()
        sigungu=(r.get("region2") or r.get("시군구") or "").strip()
        dong=(r.get("dong") or r.get("읍면동") or "").strip()
        if sido and sigungu and dong:
            by_key[(sido,sigungu,dong)].append(r)
    return by_key

def estimate_index(rows):
    by_key = defaultdict(list)
    for r in rows:
        sido=(r.get("region1") or r.get("시도") or "").strip()
        sigungu=(r.get("region2") or r.get("시군구") or "").strip()
        dong=(r.get("dong") or r.get("읍면동") or "").strip()
        if sido and sigungu and dong:
            by_key[(sido,sigungu,dong)].append(r)
    return by_key

def score_page(facilities, estimates):
    signals = 0
    if facilities: signals += 1
    if any((x.get("price_verified") or x.get("가격검증") or "").lower() in {"1","true","y","yes","검증"} for x in facilities):
        signals += 1
    if any((x.get("cremation") or x.get("화장시설") or "").strip() for x in facilities):
        signals += 1
    if estimates: signals += 1
    if any((x.get("faq") or x.get("지역FAQ") or "").strip() for x in facilities):
        signals += 1
    return signals

def render(d, facilities, estimates, indexable):
    sigungu = html.escape(d["sigungu"])
    dong = html.escape(d["dong"])
    sido = html.escape(d["sido"])
    title = f"{sigungu} {dong} 무빈소·가족장 장례비용 | 가까운 장례식장·예상견적 | 다함상조"
    desc = f"{sigungu} {dong}에서 장례를 준비할 때 가까운 장례식장, 무빈소·가족장 선택, 시설비와 화장·장지 비용을 나눠 예상견적을 확인합니다."
    robots = "index,follow,max-image-preview:large,max-snippet:-1" if indexable else "noindex,follow"
    sig_slug=slugify_kr(d["sigungu"]); dong_slug=slugify_kr(d["dong"])
    canonical=f"https://www.dahamsangjo.co.kr/local/{sig_slug}/{dong_slug}/"

    cards=[]
    for f in facilities[:8]:
        name=html.escape(f.get("name") or f.get("장례식장명") or "장례식장")
        addr=html.escape(f.get("address") or f.get("주소") or "")
        cards.append(f"<article class='card'><h3>{name}</h3><p>{addr}</p><p>시설비·무빈소 가능 여부는 행사 시점 최종 확인</p></article>")
    if not cards:
        cards.append("<article class='card'><h3>인접권 장례식장 확인 중</h3><p>검증되지 않은 시설명과 가격은 검색용 문구로 임의 생성하지 않습니다.</p></article>")

    case_html=""
    if estimates:
        lis=[]
        for e in estimates[:5]:
            service=html.escape(e.get("service") or e.get("장례방식") or "")
            total=html.escape(e.get("total") or e.get("총액") or "")
            hall=html.escape(e.get("hall") or e.get("장례식장") or "")
            lis.append(f"<li>{hall} · {service} · 예상/실제 총액 {total}</li>")
        case_html="<ul>"+''.join(lis)+"</ul>"
    else:
        case_html="<p>검증된 견적 사례가 연결되기 전에는 임의 금액 사례를 공개하지 않습니다.</p>"

    return f"""<!doctype html><html lang='ko'><head>
<meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'>
<title>{html.escape(title)}</title><meta name='description' content='{html.escape(desc)}'>
<meta name='robots' content='{robots}'><link rel='canonical' href='{canonical}'>
<link rel='icon' href='/favicon.png' type='image/png'>
<style>body{{font-family:'Noto Sans KR','Malgun Gothic',sans-serif;margin:0;color:#211b17;background:#fbf7ef;line-height:1.75}}main{{max-width:1050px;margin:auto;padding:30px 18px}}header{{background:#211914;color:#fff;padding:55px 18px;text-align:center}}h1{{font-size:clamp(32px,5vw,50px)}}.panel{{background:#fff;border:1px solid #e6d8c2;border-radius:18px;padding:24px;margin:18px 0}}.grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(230px,1fr));gap:12px}}.card{{background:#fffaf1;border:1px solid #eadcc4;border-radius:14px;padding:18px}}a{{color:#79500b;font-weight:800}}</style>
<script type='application/ld+json'>{json.dumps({"@context":"https://schema.org","@type":"WebPage","name":title,"url":canonical,"description":desc,"inLanguage":"ko-KR"},ensure_ascii=False)}</script>
</head><body>
<header><p>{sido} · {sigungu}</p><h1>{dong}에서 장례를 준비할 때<br>가까운 장례식장과 예상비용</h1><p>지역명만 바꾼 광고 페이지가 아니라 실제 시설·비용·견적 데이터가 확인된 범위만 안내합니다.</p></header>
<main>
<section class='panel'><h2>30초 핵심답변</h2><p><strong>다함상조 상품가 + 실제 이용 장례식장 시설비 + 음식·접객비 + 화장·장지비 + 추가 선택비용</strong>으로 예상 총비용을 확인합니다. 무빈소 120만원·가족장 249만원은 대표 상품가이며 전체 장례비와 동일하지 않습니다.</p></section>
<section class='panel'><h2>{dong} 및 인접권 장례식장</h2><div class='grid'>{''.join(cards)}</div></section>
<section class='panel'><h2>무빈소와 가족장</h2><div class='grid'><article class='card'><h3>무빈소 120만원</h3><p>빈소 운영 없이 안치·입관·발인·화장 중심. 시설비·화장비 등 외부비용 별도.</p></article><article class='card'><h3>가족장 249만원</h3><p>가족·친지 중심의 소규모 빈소. 조문객 수와 음식·시설 사용량에 따라 총비용 변동.</p></article></div></section>
<section class='panel'><h2>{dong} 견적 사례</h2>{case_html}<p><a href='/funeral-cost-calculator.html'>내 조건으로 장례비용 계산 →</a></p></section>
<section class='panel'><h2>관련 지역</h2><p><a href='/area-funeral-seo-hub.html'>지역별 장례정보</a> · <a href='/nobinso.html'>무빈소 장례</a> · <a href='/family.html'>가족장</a> · <a href='/cost.html'>장례비용</a></p></section>
</main></body></html>"""

def main():
    legal = active_dongs(read_csv(DATA / "legal-dong.csv"))
    facilities = facility_index(read_csv(DATA / "funeral-halls.csv"))
    estimates = estimate_index(read_csv(DATA / "estimate-cases.csv"))
    created=indexable_count=0
    for d in legal:
        key=(d["sido"],d["sigungu"],d["dong"])
        fs=facilities.get(key,[])
        es=estimates.get(key,[])
        score=score_page(fs,es)
        indexable=score >= 3
        sig_slug=slugify_kr(d["sigungu"]); dong_slug=slugify_kr(d["dong"])
        out=OUT/sig_slug/dong_slug/"index.html"
        out.parent.mkdir(parents=True,exist_ok=True)
        out.write_text(render(d,fs,es,indexable),encoding="utf-8")
        created += 1
        if indexable: indexable_count += 1
    print(json.dumps({"created":created,"indexable":indexable_count,"noindex":created-indexable_count},ensure_ascii=False))

if __name__ == "__main__":
    main()
