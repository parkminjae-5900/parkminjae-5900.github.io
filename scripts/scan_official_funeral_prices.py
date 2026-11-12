#!/usr/bin/env python3
import json, os, re, time, hashlib
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urljoin, urlparse, parse_qs
import requests
from bs4 import BeautifulSoup

HALLS=Path("data/funeral-halls.json")
OVERRIDES=Path("data/funeral-hall-prices.json")
STATE=Path("data/official-price-scan-state.json")
REPORT=Path("data/official-price-scan-report.json")
BATCH=int(os.environ.get("PRICE_SCAN_BATCH","45"))
TIMEOUT=6
PROMOTION_GUARD_VERSION=6
UA="Mozilla/5.0 (compatible; DahamSangjoPriceVerifier/1.0; +https://www.dahamsangjo.co.kr/)"

KEYWORDS=("장례","빈소","안치","염습","입관","시설","이용","요금","비용","가격","사용료","영결")
CATEGORY_RULES=[
 ("빈소",("빈소","분향실","접객실","임대료")),
 ("안치실",("안치","냉장고")),
 ("염습/입관",("염습","입관")),
 ("영결식장",("영결","예식실")),
 ("청소/관리",("청소","관리비")),
 ("주차",("주차",)),
]
PRICE_HEADER=("금액","가격","요금","사용료","임대료","단가")
MONEY=re.compile(r"(?<!\d)(\d{1,3}(?:,\d{3})+|\d{4,})(?:\s*원)?(?!\d)")
MONEY_WON=re.compile(r"(?<!\d)(\d{1,3}(?:,\d{3})+|\d{3,})\s*원(?![가-힣])")
UNIT=re.compile(r"(24시간|1일|일일|시간당|1시간|1회|회당|1실|실당|1구|구당|1대|대당)")

def now():
    return datetime.now(timezone.utc).isoformat()

def clean(s):
    return re.sub(r"\s+"," ",str(s or "").replace("\xa0"," ")).strip()

def norm(s):
    return re.sub(r"[^0-9A-Za-z가-힣]","",clean(s)).lower()

def canon_name(s):
    x=norm(s)
    for p in ("의료법인","사회복지법인","재단법인","학교법인","사단법인","주식회사","유한회사"):
        if x.startswith(p): x=x[len(p):]
    if x.endswith("장례식장"): x=x[:-4]
    return x

def source_identity(name,address):
    return hashlib.sha1((str(name or "")+"|"+str(address or "")).encode()).hexdigest()[:16]

def normalize_url(u):
    u=clean(u)
    if not u:return ""
    if not re.match(r"^https?://",u,re.I): u="https://"+u
    return u

def host(u):
    try:return urlparse(u).hostname.lower().replace("www.","")
    except:return ""

def same_host(a,b):
    ha,hb=host(a),host(b)
    return bool(ha and hb and (ha==hb or ha.endswith("."+hb) or hb.endswith("."+ha)))

def query_value(u,key):
    try:
        vals=parse_qs(urlparse(u).query).get(key,[])
        return clean(vals[0]) if vals else ""
    except:
        return ""

def same_address(a,b):
    return bool(a and b and norm(a)==norm(b))

def category_coverage(prices):
    return set(x.get("category","") for x in (prices or []) if x.get("category"))

def identity_guard(rec,old,homepage):
    """Return (ok, reason). Protect curated A records and multi-branch official sites."""
    if old and old.get("sourceReviewRequired"):
        return False,"facility_source_review_required"

    if sangbok_identity(rec.get("facilityName",""),rec.get("address","")) or any(
        host(u) in SANGBOK_HOSTS for u in (rec.get("sourceUrl",""),homepage)
    ):
        if not sangbok_identity(rec.get("facilityName",""),rec.get("address","")):
            return False,"facility_identity_unverifiable"
        if not sangbok_url_matches(rec.get("sourceUrl","")):
            return False,"facility_source_path_mismatch"
        prices=rec.get("prices",[])
        expected={(cat,label+" · "+area,unit) for label,cat,unit in SANGBOK_ROWS for area in ("관내","관외")}
        expected.update({("염습/입관","염습료 · 일반사",""),("염습/입관","염습료 · 사고사 (수습·봉합 별도)","")})
        if len(prices)!=8 or {(x.get("category"),x.get("label"),x.get("unit")) for x in prices}!=expected:
            return False,"reviewed_price_rows_changed"
        if any(x.get("sourceParser")!="sangbok_rows_v1" for x in prices):
            return False,"facility_price_table_review_required"
        if any(x.get("category")=="빈소" and x.get("requiresManualQuantity") is not True for x in prices):
            return False,"area_unit_review_required"

    if any(host(u)=="pcfmc.or.kr" for u in (rec.get("sourceUrl",""),homepage,(old or {}).get("sourceUrl",""))):
        target=pcfmc_target(rec.get("facilityName",""),rec.get("address",""))
        if not target:return False,"facility_identity_unverifiable"
        if not pcfmc_url_matches(rec.get("sourceUrl",""),target["path"]):
            return False,"facility_source_path_mismatch"
        prices=rec.get("prices",[])
        if not prices or any(x.get("sourceParser")!="pcfmc_facility_rows_v1" for x in prices):
            return False,"facility_price_table_review_required"
        expected={(category,label+" · "+area,unit) for label,category,unit in PCFMC_ROWS for area in ("관내","관외")}
        if len(prices)!=len(expected) or {(x.get("category"),x.get("label"),x.get("unit")) for x in prices}!=expected:
            return False,"reviewed_price_rows_changed"

    # A unit conflict cannot be resolved by the same generic extractor that
    # produced it. Keep the reviewed display until official rows are verified.
    if old and old.get("priceReviewRequired"):
        return False,"price_unit_review_required"

    if host(rec.get("sourceUrl","")) in ("nw4444.co.kr","dgsmfn.com"):
        if not rec.get("prices") or any(x.get("sourceParser")!="reviewed_room_rows_v1" for x in rec["prices"]):
            return False,"room_row_review_required"

    if any(host(u) in REVIEWED_UNIT_HOSTS for u in (rec.get("sourceUrl",""),homepage,(old or {}).get("sourceUrl",""))):
        if not rec.get("prices") or any(x.get("sourceParser")!="reviewed_units_v1" for x in rec["prices"]):
            return False,"explicit_unit_review_required"
        if old and any(x.get("sourceParser")=="reviewed_units_v1" for x in old.get("prices",[])):
            signature=lambda x:(x.get("category"),x.get("label"),x.get("unit"))
            if {signature(x) for x in rec["prices"]}!={signature(x) for x in old["prices"]}:
                return False,"reviewed_price_rows_changed"

    if old and old.get("sourceGrade")=="A":
        if not same_address(rec.get("address",""),old.get("address","")):
            return False,"address_mismatch_with_existing_A"

    source_code=query_value(rec.get("sourceUrl",""),"fnrCd")
    home_code=query_value(homepage or "","fnrCd")
    old_code=query_value((old or {}).get("sourceUrl",""),"fnrCd")
    expected=home_code or old_code
    if expected:
        if not source_code:
            return False,"branch_code_missing"
        if expected!=source_code:
            return False,"branch_code_mismatch"
    elif source_code:
        return False,"branch_code_unverifiable"

    if old and old.get("sourceGrade")=="A":
        old_cov=category_coverage(old.get("prices",[]))
        new_cov=category_coverage(rec.get("prices",[]))
        if not old_cov.issubset(new_cov):
            return False,"category_coverage_regression"
        if len(rec.get("prices",[])) < len(old.get("prices",[])):
            return False,"price_record_regression"

    return True,"guard_passed"

def session():
    s=requests.Session()
    s.headers.update({"User-Agent":UA,"Accept-Language":"ko-KR,ko;q=0.9,en;q=0.5"})
    return s

def get_html(s,u):
    try:
        r=s.get(u,timeout=TIMEOUT,allow_redirects=True)
        if r.status_code>=400:return None,None
        ct=(r.headers.get("content-type") or "").lower()
        if "html" not in ct and "text" not in ct:return None,None
        if not r.encoding or r.encoding.lower()=="iso-8859-1":r.encoding=r.apparent_encoding or "utf-8"
        return r.text,r.url
    except Exception:
        return None,None

def candidate_links(html,base):
    soup=BeautifulSoup(html,"html.parser")
    scored=[]
    for a in soup.find_all("a",href=True):
        href=urljoin(base,a.get("href",""))
        if not same_host(base,href):continue
        txt=clean(a.get_text(" ",strip=True))+" "+href
        score=sum(1 for k in KEYWORDS if k in txt)
        if score<=0:continue
        if any(x in href.lower() for x in ("javascript:","mailto:","tel:","#")):continue
        scored.append((score,href))
    out=[];seen=set()
    for _,u in sorted(scored,key=lambda x:-x[0]):
        key=u.split("#")[0]
        if key in seen:continue
        seen.add(key);out.append(key)
        if len(out)>=6:break
    return out

def classify(label):
    t=clean(label)
    if t in ("안치실","안치료"):return "안치실"
    if t in ("염습실","입관실","염습료","입관료"):return "염습/입관"
    if t in ("영결식장","예식실"):return "영결식장"
    if t in ("빈소","분향실","접객실"):return "빈소"
    # Only actual facility-use charges are accepted. Goods, food, ritual tables and transport are excluded.
    if any(w in t for w in ("장의차량","장의차","버스","리무진","입관부속품","장례용품","판매","기본상","성복상","발인상","제사","과일","음식","식사")):
        return None
    if any(w in t for w in ("안치료","안치실 사용료","안치실이용료","안치실 이용료")):return "안치실"
    if any(w in t for w in ("염습실 사용료","염습실이용료","염습료","입관실 사용료","입관실이용료","입관료")):return "염습/입관"
    if any(w in t for w in ("영결식장 사용료","영결식장 임대료","예식실 사용료","예식실 임대료")):return "영결식장"
    if any(w in t for w in ("관리비","청소비","청소료")):return "청소/관리"
    if any(w in t for w in ("빈소 임대료","빈소 사용료","빈소사용료","분향실료","분향실 사용료","접객실료","접객실 사용료")):return "빈소"
    # Some official tables use the room name + price without the word 임대료.
    if ("빈소" in t or "분향실" in t or "접객실" in t) and any(w in t for w in ("요금","가격","시간","24시간","1일")):return "빈소"
    return None

def amount_from_cell(v, require_won=False):
    s=clean(v)
    m=MONEY_WON.search(s) if ("원" in s or require_won) else None
    if not m and not require_won:
        # Numeric-only cells are allowed when the column header explicitly says price.
        if re.fullmatch(r"[\d,.\s]+",s):
            m=MONEY.search(s)
    if not m:return 0
    try:n=int(m.group(1).replace(",",""))
    except:return 0
    if n<1000 or n>20000000:return 0
    return n

def table_prices(soup):
    out=[]
    for table in soup.find_all("table"):
        rows=table.find_all("tr")
        if not rows:continue
        header_cells=rows[0].find_all(["th","td"])
        headers=[clean(x.get_text(" ",strip=True)) for x in header_cells]
        price_cols=[i for i,h in enumerate(headers) if any(k in h for k in PRICE_HEADER)]
        for tr in rows[1:] if headers else rows:
            cells=[clean(x.get_text(" ",strip=True)) for x in tr.find_all(["th","td"])]
            if len(cells)<2:continue
            label=" ".join(cells[:2])
            cat=classify(label)
            if not cat:continue
            candidates=price_cols[:] if price_cols else list(range(1,len(cells)))
            amt=0;used=""
            for i in candidates:
                if i>=len(cells):continue
                c=cells[i]
                # Even in an explicit price column, reject prose/phone-number cells.
                if "원" not in c and not re.fullmatch(r"[\d,.\s]+",c):continue
                a=amount_from_cell(c, require_won=(not price_cols))
                if a:amt=a;used=c;break
            if not amt:continue
            unit=""
            m=UNIT.search(" ".join(cells))
            if m:unit=m.group(1)
            out.append({"category":cat,"label":label[:160],"amount":amt,"unit":unit})
    return out

def expanded_table_rows(table):
    """Expand HTML rowspans without inferring missing values or column spans."""
    rows=[]; pending={}
    for tr in table.find_all("tr"):
        cells=tr.find_all(["th","td"],recursive=False)
        row={col:text for col,(text,left) in pending.items()}
        pending={col:(text,left-1) for col,(text,left) in pending.items() if left>1}
        col=0
        for cell in cells:
            if cell.get("colspan","1")!="1":return []
            while col in row:col+=1
            text=clean(cell.get_text(" ",strip=True))
            try:span=int(cell.get("rowspan","1"))
            except ValueError:return []
            if not 1<=span<=50:return []
            row[col]=text
            if span>1:pending[col]=(text,span-1)
            col+=1
        if row:rows.append([row.get(i,"") for i in range(max(row)+1)])
    if pending:return []
    return rows

def pyeongtaek_prices(soup,url):
    """Strict adapter for the verified Pyeongtaek facility tables only.

    None means not this source; [] means its evidence was incomplete. Never
    fall back to prose extraction on this source after a structural failure.
    """
    if (host(url)!="kyowonyeum.co.kr" or urlparse(url).path.lower()!="/site/funeral"
        or query_value(url,"fnrCd")!="1002"):
        return None
    heading=soup.find("h1")
    if not heading or clean(heading.get_text())!="평택장례식장":return []
    if "평택시 신평로 205" not in clean(soup.get_text(" ",strip=True)):return []
    out=[]; sections=set()
    for table in soup.find_all("table"):
        title=table.find_previous(["h1","h2","h3","h4","p"])
        title=clean(title.get_text(" ",strip=True)) if title else ""
        room=title in ("· 빈소 - VIP실","· 빈소 - 특실","· 빈소 - 일반실")
        if not room and title!="· 부대시설":continue
        if title in sections:return []
        sections.add(title)
        rows=expanded_table_rows(table)
        expected=["구분","크기 / 수용인원","구성","가격"] if room else ["구분","가격","기준"]
        if not rows or rows[0]!=expected:return []
        for cells in rows[1:]:
            if len(cells)!=len(expected):return []
            label=cells[0]
            if room:
                if not re.fullmatch(r"\d+호(?:\s*,\s*\d+호)*",label):return []
                category="빈소"; label=label.replace(", ","·")+" 빈소"
                money=cells[3]; unit="1시간"
                if not re.fullmatch(r"[\d,]+원\s*\(기준 1시간\)",money):return []
            else:
                if label=="주차장":continue
                category={"입관실/염습실":"염습/입관","안치실":"안치실"}.get(label)
                if not category:return []
                money=cells[1]; unit=cells[2]
                if not re.fullmatch(r"[\d,]+원",money):return []
                if unit not in ("1시간","1일","1회"):return []
            amount=amount_from_cell(money,require_won=True)
            if not amount:return []
            out.append({"category":category,"label":label,"amount":amount,"unit":unit})
    if sections!={"· 빈소 - VIP실","· 빈소 - 특실","· 빈소 - 일반실","· 부대시설"}:return []
    if category_coverage(out)!={"빈소","안치실","염습/입관"}:return []
    if len({x["label"] for x in out})!=len(out):return []
    return out

def gijang_prices(soup,url):
    """Read the official daily/one-use price column, never the hourly notes.

    Fail closed on this hospital's other pages or changed table structure.
    Expanding the two-column fee cells preserves header/amount alignment.
    """
    if host(url)!="gjhp.kr":return None
    if urlparse(url).path!="/location01_05.php":return []
    if not soup.title or clean(soup.title.get_text())!="기장병원":return []
    tables=[]
    for table in soup.find_all("table"):
        first=table.find("tr")
        if first and [clean(c.get_text(" ",strip=True)) for c in first.find_all(["th","td"])]==["구분","호실","요금","비고"]:
            tables.append(table)
    if len(tables)!=1:return []
    table=BeautifulSoup(str(tables[0]),"html.parser").table
    for tr in list(table.find_all("tr"))[1:]:
        cells=tr.find_all(["th","td"],recursive=False)
        if not cells:return []
        label=clean(cells[0].get_text(" ",strip=True))
        if label=="도우미":
            tr.decompose();continue
        for c in cells:
            if c.get("colspan","1")=="1":continue
            if label not in ("안치료","염습실 사용료") or c is not cells[1] or c.get("colspan")!="2":return []
            c.attrs.pop("colspan")
            empty=soup.new_tag("td")
            c.insert_before(empty)
    rows=expanded_table_rows(table)
    if not rows:return []
    out=[]
    for cells in rows[1:]:
        if len(cells)!=4:return []
        kind,room,money,notes=cells
        if kind=="빈소 임대료 (접객실 포함)":
            if not re.fullmatch(r"(?:특 )?\d+호실",room):return []
            category="빈소"; label=kind+" "+room; unit="1일"
        elif kind in ("안치료","염습실 사용료"):
            if room:return []
            category="안치실" if kind=="안치료" else "염습/입관"
            label=kind; unit="1일" if kind=="안치료" else "1회"
        elif kind=="청소, 쓰레기 처리비용":
            if not re.fullmatch(r"(?:특 )?\d+(?:,\d+)*호실",room):return []
            category="청소/관리";label=kind+" "+room;unit="1일"
        else:return []
        if not re.fullmatch(r"[\d,]+원\s*/\s*"+unit,money):return []
        amount=amount_from_cell(money,require_won=True)
        if not amount:return []
        out.append({"category":category,"label":label,"amount":amount,"unit":unit})
    if category_coverage(out)!={"빈소","안치실","염습/입관","청소/관리"}:return []
    if len({x["label"] for x in out})!=len(out):return []
    return out

def youngwol_page(soup,url):
    """Read named columns, never the bulletin number as a room specification."""
    if (host(url)!="youngwol.org" or urlparse(url).path!="/bbs/board.php"
        or query_value(url,"bo_table")!="funeral_01" or query_value(url,"wr_id")):
        return None
    if not soup.title or "영월의료원" not in soup.title.get_text():return None
    total_el=soup.select_one("#bo_list_total")
    total=re.search(r"Total\s+([\d,]+)건",clean(total_el.get_text())) if total_el else None
    current=soup.select_one(".pg_current")
    if not total or not current:return None
    page=query_value(url,"page") or "1"
    if clean(current.get_text())!=page:return None
    tables=[t for t in soup.find_all("table") if t.find("tr") and
            [clean(c.get_text(" ",strip=True)) for c in t.find("tr").find_all(["th","td"])]
            ==["번호","품목","규격","단위","금액","비고"]]
    if len(tables)!=1:return None
    rows=expanded_table_rows(tables[0]); out=[]; numbers=[]
    categories={"안치료":"안치실","분향실료":"빈소","접객실료":"빈소",
                "염습료":"염습/입관","염습실사용료":"염습/입관"}
    for cells in rows[1:]:
        if len(cells)!=6:return None
        number,kind,size,unit,money,notes=cells
        if not number.isdigit() or kind not in categories:return None
        if unit not in ("1시간당","1구당") or not re.fullmatch(r"[\d,]+",money):return None
        amount=amount_from_cell(money)
        if not amount:return None
        label=" ".join(x for x in (kind,size,notes) if x)
        out.append({"category":categories[kind],"label":label,"amount":amount,"unit":unit})
        numbers.append(int(number))
    pages={1}
    for a in soup.select(".pg a[href]"):
        u=urljoin(url,a["href"])
        if not same_host(url,u) or urlparse(u).path!="/bbs/board.php" or query_value(u,"bo_table")!="funeral_01":return None
        n=query_value(u,"page")
        if not n.isdigit() or not 1<=int(n)<=10:return None
        pages.add(int(n))
    pages.add(int(page))
    return int(total.group(1).replace(",","")),pages,numbers,out


def scan_youngwol(s,home):
    """Require all linked pages and the complete numbered inventory atomically."""
    base="https://youngwol.org/bbs/board.php?bo_table=funeral_01"
    pending=[1]; visited=set(); numbers=[]; prices=[]; total=None
    while pending:
        page=pending.pop(0)
        if page in visited:continue
        visited.add(page)
        url=base+("&page="+str(page) if page!=1 else "")
        html,final=get_html(s,url)
        parsed=youngwol_page(BeautifulSoup(html,"html.parser"),final) if html and final else None
        if not parsed:return {"status":"no_price_found","homepage":home}
        count,pages,ids,rows=parsed
        if total is not None and total!=count:return {"status":"no_price_found","homepage":home}
        total=count; numbers+=ids; prices+=rows
        pending+=sorted(pages-visited)
    if (not total or len(numbers)!=total or set(numbers)!=set(range(1,total+1))
        or len(dedupe(prices))!=total):
        return {"status":"no_price_found","homepage":home}
    return {"status":"priced","homepage":home,"sourceUrl":base,"prices":prices,"verifiedAt":now()}



def ewha_seoul_prices(soup,url):
    """Read each official room card once, excluding nested photo captions.

    Room identity includes both its name and area; equal prices (notably
    special rooms 3 and 5) are not evidence of duplicate rooms.
    """
    if host(url)!="seoul.eumc.ac.kr" or urlparse(url).path!="/funeral/guide/facility.do":
        return None
    cards=soup.select(".mortuary-info > .right")
    if not cards:return []
    out=[]; seen={}
    for card in cards:
        fields={}
        for title in card.select(".title"):
            value=title.find_next_sibling()
            if value is None or "txt" not in value.get("class",[]):return []
            name=clean(title.get_text(" ",strip=True)).rstrip(" :")
            if name in fields:return []
            fields[name]=clean(value.get_text(" ",strip=True))
        area=fields.get("평형",""); room=fields.get("빈소","")
        money=fields.get("빈소 임대료(1일)","")
        if not re.fullmatch(r"[0-9.]+㎡\s*\([0-9.]+평형\)",area):return []
        if not re.fullmatch(r"(?:특실\s*\d+|\d+호)(?:\s*,\s*(?:특실\s*\d+|\d+호))*",room):return []
        if not re.fullmatch(r"[\d,]+\s*원",money):return []
        amount=amount_from_cell(money,require_won=True)
        if not amount:return []
        identity=(clean(room),area)
        if identity in seen:
            if seen[identity]!=amount:return []
            continue
        seen[identity]=amount
        out.append({"category":"빈소","label":f"빈소 임대료 {room} · {area}","amount":amount,"unit":"1일"})
    return out


REVIEWED_UNIT_NOTES={'xn--9n2b47q9zbmiv5gca.kr': '공식 일/시간 요금을 각각 보존했습니다. 1일 기준: 12시간 초과~24시간 이하. 12시간 초과 시 1일, 36시간 이상 시 2일 요금. 특2호 일/시간 금액이 단순 24배와 달라 최종 확인 필요. 염습실/입관실 400,000원, 18시~08시 입관 500,000원은 부과 기준 확인 필요.', 'mokpomc.or.kr': '공식 일/시간 요금을 각각 보존했습니다. 24시간을 1일로 산정하며 12시간 이상은 1일, 미만은 시간으로 산정합니다. 안치료 일/시간 요금은 단순 24배가 아닙니다. 감면 대상 및 적용 여부는 공식 감면기준과 의료원에 확인하세요.', 'cmcdjfuneral.co.kr': '안치일시 기준 24시간을 1일로 산정합니다. 24시간 미만 사용 시 12시간 이상은 1일, 12시간 미만은 시간단위, 1시간 미만은 1시간입니다. 사산아 안치료는 12시간 미만 조건만 게시되어 있습니다. 염습료의 회당 등 부과 단위와 추가요금 여부는 확인이 필요합니다.'}

# Room-rate caveats must survive every scheduled scan and override rebuild.
REVIEWED_UNIT_NOTES.update({'nw4444.co.kr': '공식 홈페이지 게시 가격 대조. 시행일 미표기: 실제 이용 전 최종 확인 필요. 정상가와 할인가를 구분했으며 할인 적용 조건은 장례식장 확인 필요. 단위 미표기 항목은 부과 기준 확인 필요.', 'dgsmfn.com': '공식 홈페이지 게시 가격 대조. 시행일 미표기: 실제 이용 전 최종 확인 필요. VIP 501호 이용료만 확인. 3일장 기준이며 1일 요금이나 전체 장례비가 아님. 다른 호실 요금은 이 페이지로 확인할 수 없음.'})

REVIEWED_UNIT_HOSTS={
    "xn--9n2b47q9zbmiv5gca.kr":"/s2/s2_2.php",
    "mokpomc.or.kr":"/bbs/content.php?co_id=2_8",
    "cmcdjfuneral.co.kr":"/funeral-guide.jsp",
}

def reviewed_unit_prices(soup,url):
    """Read explicit price columns, preserving independent day/hour values.

    These hosts never fall back to prose extraction. Changed structure or
    conditions require review rather than silently replacing curated prices.
    """
    h=host(url)
    if h not in REVIEWED_UNIT_HOSTS:return None
    target=REVIEWED_UNIT_HOSTS[h]
    if urlparse(url).path!=target.split("?")[0]:return []
    if h=="mokpomc.or.kr" and query_value(url,"co_id")!="2_8":return []
    out=[]
    def add(category,label,amount,unit=""):
        out.append(dict(category=category,label=label,amount=amount,unit=unit,
                        sourceParser="reviewed_units_v1"))
    def money(text,suffix="원"):
        m=re.fullmatch(r"([\d,]+)"+re.escape(suffix),clean(text))
        if not m:raise ValueError("price format changed")
        value=int(m[1].replace(",",""))
        if value<=0:raise ValueError("invalid price")
        return value
    def rows(table):
        return [[clean(c.get_text(" ",strip=True)) for c in r.find_all(["th","td"],recursive=False)]
                for r in table.find_all("tr")]
    text=clean(soup.get_text(" ",strip=True))
    try:
        if h=="xn--9n2b47q9zbmiv5gca.kr":
            conditions=["1일 이용 기준은 12시간 초과 ~ 24시간 이하입니다.",
                        "12시간을 초과하여 이용할 경우 1일 요금이 부과됩니다.",
                        "이용시간이 36시간 이상인 경우에는 2일 요금이 부과됩니다."]
            if not all(c in text for c in conditions):return []
            tables=[t for t in soup.find_all("table") if rows(t)[0]==["","호실","좌석","평형","이용 요금(1일)","이용 요금(1시간)"]]
            if len(tables)!=1:return []
            rr=expanded_table_rows(tables[0])
            expected=["VIP실","특1호","특2호","3호","5호","6호","특7호","8호","9호","10호"]
            if len(rr)!=13 or [r[1] for r in rr[1:11]]!=expected:return []
            for r in rr[1:12]:
                if len(r)!=6 or r[0] not in ("빈소 임대료","안치료"):return []
                cat="빈소" if r[0]=="빈소 임대료" else "안치실"
                label=("빈소 "+r[1]) if cat=="빈소" else "안치료"
                if r[1]=="특2호":label+=" · 일/시간 요금 원문 상이, 최종 확인 필요"
                add(cat,label,money(r[4]),"1일")
                add(cat,label,money(r[5]),"1시간")
            r=rr[12]
            if len(r)!=6 or r[:2]!=["염습실 사용료","염습실/입관실"] or r[5]:return []
            m=re.fullmatch(r"18시~08시 입관시 ([\d,]+)",r[3])
            if not m:return []
            add("염습/입관","염습실/입관실 사용료 · 부과 기준 확인 필요",money(r[4]))
            add("염습/입관","염습실/입관실 · 18시~08시 입관 · 부과 기준 확인 필요",money(m[1],""))
        elif h=="mokpomc.or.kr":
            if "24시간 1일 산정(12시간 이상은 1일, 미만일 경우는 시간으로 산정 합니다.)" not in text:return []
            tables=[t for t in soup.find_all("table") if rows(t)[0]==["품명","규격","1일","시간당"]]
            if len(tables)!=1:return []
            rr=rows(tables[0])
            if len(rr)!=6 or rr[1][:2]!=["안치료","안치료"]:return []
            add("안치실","안치료",money(rr[1][2]),"1일")
            add("안치실","안치료",money(rr[1][3]),"1시간")
            expected=["1호실(55평)","2호실(55평)","3호실","1+2호실(110평)"]
            for i,r in enumerate(rr[2:]):
                if i==0:
                    if r[0]!="빈소 및 접객실 사용료":return []
                    r=r[1:]
                if len(r)!=4 or r[0]!=expected[i]:return []
                label="빈소 및 접객실 "+r[0]
                add("빈소",label,money(r[2]),"1일")
                add("빈소",label,money(r[3]),"1시간")
        else:
            if not all(c in text for c in ["안치일시 기준으로 24시간을 1일로 산정", "12시간 이상 = 1일", "12시간 미만 = 시간단위", "1시간 미만 = 1시간"]):return []
            expected=["VIP실","특1호실","특2호실","특3호실","5호실","6호실","7호실","8호실"]
            tables=[t for t in soup.find_all("table") if rows(t)[0]==expected]
            if len(tables)!=1:return []
            rr=rows(tables[0])
            if len(rr)!=5 or any(len(r)!=8 for r in rr):return []
            for i,name in enumerate(expected):
                add("빈소","빈소 및 접객실 "+name,money(rr[2][i],"원/시간"),"1시간")
                add("빈소","빈소 및 접객실 "+name,money(rr[3][i],"원/일"),"1일")
            matches=[]
            for li in soup.find_all("li"):
                m=re.fullmatch(r"안치료 : 1시간 기준 ([\d,]+)원\(1일 ([\d,]+)원\) / 사산아 \(12시간 미만 ([\d,]+)원\)",clean(li.get_text(" ",strip=True)))
                if m:matches.append(m)
            if len(matches)!=1:return []
            m=matches[0]
            add("안치실","안치료",money(m[1],""),"1시간")
            add("안치실","안치료",money(m[2],""),"1일")
            add("안치실","안치료 · 사산아",money(m[3],""),"12시간 미만")
            if "경당(영결식장) 사용료 무료" not in text:return []
            add("영결식장","경당(영결식장) · 무료",0)
            expected=["일반","자가입관","야간 및 사고사","사고사","소아","수시"]
            tables=[t for t in soup.find_all("table") if rows(t)[0]==expected]
            if len(tables)!=1:return []
            rr=rows(tables[0])
            if len(rr)!=3 or any(len(r)!=6 for r in rr) or rr[2]!=["","","18:00~06:00","","8세 미만","물품포함"]:return []
            for i,name in enumerate(expected):
                label="염습료 · "+name+(" · "+rr[2][i] if rr[2][i] else "")+" · 부과 기준 확인 필요"
                add("염습/입관",label,money(rr[1][i]))
    except (ValueError,IndexError,TypeError):return []
    return out

def reviewed_room_prices(soup,url):
    """Fail closed for these hosts: never interpret navigation/ancestor prose as prices."""
    h=host(url)
    if h not in ("nw4444.co.kr","dgsmfn.com"):return None
    out=[]
    def add(category,label,amount,unit):
        out.append({"category":category,"label":label,"amount":amount,"unit":unit,
                    "sourceParser":"reviewed_room_rows_v1"})
    if h=="dgsmfn.com":
        if urlparse(url).path!="/sub2_1_1.php":return []
        boxes=soup.select(".facility_info_box .facility_top")
        if len(boxes)!=1:return []
        box=boxes[0];title=box.find("h2");cells=box.select("li.price")
        if not title or clean(title.get_text())!="VIP 501호" or len(cells)!=1:return []
        cell=cells[0];money=cell.find("b")
        if not money or "3일장 기준" not in clean(cell.get_text(" ",strip=True)):return []
        value=clean(money.get_text())
        if not re.fullmatch(r"[\d,]+원",value):return []
        amount=amount_from_cell(value,require_won=True)
        if not amount:return []
        add("빈소","빈소 VIP 501호 · 장례 3일장 기준",amount,"3일장")
        return out
    if urlparse(url).path!="/sub/sub_13.php":return []
    tables=[]
    for table in soup.find_all("table"):
        rows=[r for r in table.find_all("tr") if r.find_parent("table") is table]
        if not rows:continue
        header=[clean(c.get_text(" ",strip=True)) for c in rows[0].find_all(["th","td"],recursive=False)]
        if header==["호 실","정상가","할인가","면 적(坪)","비 고"]:tables.append(rows)
    if len(tables)!=1:return []
    seen=set()
    extra={"안치실":("안치실","1일"),"폐기물 처리비":("청소/관리",""),
           "입관비":("염습/입관",""),"추가 입관실 사용료":("염습/입관",""),"일반 관리비":("청소/관리","")}
    for row in tables[0][1:]:
        cells=[clean(c.get_text(" ",strip=True)) for c in row.find_all(["th","td"],recursive=False)]
        if cells and re.fullmatch(r"\d+층",cells[0]):cells=cells[1:]
        if not cells:continue
        name=cells[0]
        if re.fullmatch(r"\d+호실",name):
            if len(cells)!=5 or name in seen:return []
            seen.add(name)
            for index,kind in [(1,"정상가"),(2,"할인가 · 적용 조건 확인 필요")]:
                m=re.fullmatch(r"([\d,]+)원 / 시간",cells[index])
                if not m:return []
                amount=amount_from_cell(m[1]+"원",require_won=True)
                if not amount:return []
                add("빈소",f"빈소 {name} · {kind}",amount,"1시간")
        elif name in extra:
            if len(cells)!=5:return []
            category,unit=extra[name]
            pattern=r"([\d,]+)원 / 일" if unit else r"([\d,]+)원"
            m=re.fullmatch(pattern,cells[1])
            if not m:return []
            amount=amount_from_cell(m[1]+"원",require_won=True)
            if not amount:return []
            add(category,name+(" · 부과 기준 확인 필요" if not unit else ""),amount,unit)
    if seen!={"1호실","2호실","3호실","5호실","6호실"} or len(out)!=15:return []
    return out


def text_prices(soup):
    out=[]
    for el in soup.find_all(["li","p","div","span"]):
        t=clean(el.get_text(" ",strip=True))
        if len(t)<4 or len(t)>180 or "원" not in t:continue
        if any(w in t for w in ("상담문의","고객센터","대표전화","전화문의")):continue
        matched=[]
        for cat,words in CATEGORY_RULES:
            if any(w in t for w in words):matched.append(cat)
        matched=list(dict.fromkeys(matched))
        if len(matched)!=1:continue
        monies=MONEY_WON.findall(t)
        if len(monies)!=1:continue
        a=int(monies[0].replace(",",""))
        if a<1000 or a>20000000:continue
        m=UNIT.search(t)
        out.append({"category":matched[0],"label":t[:160],"amount":a,"unit":m.group(1) if m else ""})
    return out

def dedupe(prices):
    seen=set();out=[]
    for x in prices:
        k=(x["category"],norm(x["label"]),x["amount"],x.get("unit",""))
        if k in seen:continue
        seen.add(k);out.append(x)
    # cap pathological pages
    return out[:80]

def branch_scan_start(h,old,home):
    """Reuse only an exact-identity, same-site curated branch URL."""
    if query_value(home,"fnrCd"):
        return home
    if (old and old.get("sourceGrade")=="A"
        and norm(h.get("fcltNm",""))==norm(old.get("facilityName",""))
        and same_address(h.get("addr",""),old.get("address",""))
        and same_host(home,old.get("sourceUrl",""))
        and query_value(old.get("sourceUrl",""),"fnrCd")):
        return old["sourceUrl"]
    return home

# The public facility feed still carries obsolete PCFMC paths. Pin both
# identity and path, then verify the page itself; navigation links are not
# evidence that another facility's price table belongs to the requested hall.
PCFMC_TARGETS={
    "진부장례식장":{"path":"/facilities09","address":"평창군 진부면 오대천로 1958-21","pageAddress":"평창군 진부면 오대천로 1958-21"},
    "평창장례식장":{"path":"/facilities08","address":"평창군 평창읍 종부로 61","pageAddress":"평창군 종부로 61"},
}
PCFMC_ROWS=[("분향실","빈소","1일"),("접객실(일반)","빈소","1일"),
            ("안치실","안치실","1일"),("염습료(1회)","염습/입관","1회")]

def pcfmc_address(address):
    # Only the province rename and trailing parenthetical building name vary.
    address=re.sub(r"^(강원특별자치도|강원도)\s*","",clean(address))
    return norm(address.split("(",1)[0])

def pcfmc_target(name,address):
    target=PCFMC_TARGETS.get(norm(name))
    return target if target and pcfmc_address(address)==norm(target["address"]) else None

def pcfmc_url_matches(url,path):
    parsed=urlparse(url)
    return (host(url)=="pcfmc.or.kr" and parsed.path.rstrip("/")==path
            and not parsed.query and parsed.scheme in ("http","https"))

def pcfmc_prices(soup,name,target):
    heading=soup.select_one("h3.ctit")
    content=soup.select_one(".facilities_c2")
    if heading is None or content is None or norm(heading.get_text())!=norm(name):
        return [],"facility_page_name_mismatch"
    locations=[]
    for row in content.select("table tr"):
        cells=row.find_all(["th","td"],recursive=False)
        if cells and clean(cells[0].get_text())=="위치":
            locations.append(clean(cells[1].get_text()) if len(cells)==2 else "")
    if len(locations)!=1 or pcfmc_address(locations[0])!=norm(target["pageAddress"]):
        return [],"facility_page_address_mismatch"
    captions=[x for x in content.select(".num_tit strong") if "사용료" in x.get_text()]
    if len(captions)!=1 or norm(captions[0].get_text())!=norm(name+" 사용료(2023년)"):
        return [],"facility_price_table_name_mismatch"
    table=captions[0].parent.find_next_sibling("table")
    if table is None:return [],"facility_price_table_structure_changed"
    headers=[[clean(c.get_text()) for c in row.find_all(["th","td"],recursive=False)] for row in table.select("thead tr")]
    if headers!=[["구분","금액(1일 사용료)","비고"],["관내","관외"]]:
        return [],"facility_price_table_structure_changed"
    if "오전12시부터다음날오전12시까지를1일로계산" not in norm(table.get_text()):
        return [],"facility_price_table_unit_changed"
    rows=table.select("tbody tr")
    if len(rows)!=len(PCFMC_ROWS):return [],"facility_price_table_structure_changed"
    out=[]
    for index,(row,(label,category,unit)) in enumerate(zip(rows,PCFMC_ROWS)):
        cells=row.find_all(["th","td"],recursive=False)
        if len(cells)!=(4 if index==0 else 3) or clean(cells[0].get_text())!=label:
            return [],"facility_price_table_structure_changed"
        for column,area in [(1,"관내"),(2,"관외")]:
            text=clean(cells[column].get_text())
            if not re.fullmatch(r"[\d,]+원",text):return [],"facility_price_table_amount_invalid"
            amount=amount_from_cell(text,require_won=True)
            if not amount:return [],"facility_price_table_amount_invalid"
            out.append({"category":category,"label":label+" · "+area,"amount":amount,
                        "unit":unit,"sourceParser":"pcfmc_facility_rows_v1"})
    return out,"guard_passed"

def scan_pcfmc(s,h,home):
    target=pcfmc_target(h.get("fcltNm",""),h.get("addr",""))
    result={"status":"no_price_found","homepage":home}
    if not target:return {**result,"reviewReason":"facility_identity_unverifiable"}
    start="https://www.pcfmc.or.kr"+target["path"]
    html,final=get_html(s,start)
    if not html:return {"status":"unreachable","homepage":home,"sourceUrl":start}
    if not pcfmc_url_matches(final,target["path"]):
        return {**result,"sourceUrl":final,"reviewReason":"facility_source_path_mismatch"}
    prices,reason=pcfmc_prices(BeautifulSoup(html,"html.parser"),h["fcltNm"],target)
    if not prices:return {**result,"sourceUrl":final,"reviewReason":reason}
    return {"status":"priced","homepage":home,"sourceUrl":final,"prices":prices,"verifiedAt":now(),
            "sourceNote":"공단 시설별 페이지의 2023년 사용료 표. 관내·관외 구분과 1일/1회 단위를 분리했으며 현행 적용 여부·감면 자격은 이용 전 시설 확인 필요."}

SANGBOK_URL="https://www.cwsisul.or.kr/_sangbok/_sub02/sub02_01_02.html"
SANGBOK_HOSTS={"cwsisul.or.kr","wwwcwsisulorkr"}
SANGBOK_ROWS=[("빈소·접객실","빈소","1㎡당(1일)"),("안치실","안치실","1구당(1일)"),("염습실","염습/입관","1회")]
SANGBOK_NOTE=("빈소·접객실은 1㎡당 1일 요금으로 빈소 총액이 아닙니다. 관내·관외 적용 자격을 확인하세요. "
              "공식 안내: 사망일 기준 1개월 전부터 계속 창원시에 주소를 둔 경우 등. "
              "1일은 오전 12시부터 다음 날 오전 12시까지이며 12시간 미만은 0.5일입니다. "
              "염습료와 염습실 사용료는 별도이고 사고사 수습·봉합비는 추가됩니다. "
              "염습료의 부과 단위와 현행 적용 여부는 시설 확인이 필요합니다.")

def sangbok_identity(name,address):
    return (norm(name)==norm("창원시립상복공원장례식장") and
            norm(clean(address).split("(",1)[0])==norm("경상남도 창원시 성산구 공단로474번길 160"))

def sangbok_url_matches(url):
    p=urlparse(url)
    return host(url)=="cwsisul.or.kr" and p.path==urlparse(SANGBOK_URL).path and not p.query and p.scheme in ("http","https")

def sangbok_prices(soup):
    heading=soup.select_one("h2.displayhidden")
    section=soup.select_one("h3.sub_title")
    content=soup.select_one(".finance1")
    if (heading is None or norm(heading.get_text())!=norm("창원시립상복공원") or section is None
        or clean(section.get_text())!="장례식장안내" or content is None):
        return [],"facility_page_name_mismatch"
    text=clean(content.get_text(" ",strip=True))
    if "055-712-0930" not in text:return [],"facility_page_phone_mismatch"
    # Reject altered qualification/charging conditions rather than reuse stale notes.
    required=("1일은 오전 12시부터 다음 날 오전 12시까지로 하며, 12시간 미만은 0.5일로 본다",
              "사망한 날을 기준으로 1개월 전부터 계속해서 창원시에 주소를 둔 경우",
              "염습료 : 염습실 사용료 별도금액")
    if any(norm(x) not in norm(text) for x in required):return [],"facility_price_conditions_changed"
    tables=[t for t in content.select("table") if t.caption and clean(t.caption.get_text())=="이용요금에 대한 구분, 이용료(관내, 관외), 비고"]
    if len(tables)!=1:return [],"facility_price_table_structure_changed"
    table=tables[0]
    headers=[[clean(c.get_text()) for c in r.find_all(["th","td"],recursive=False)] for r in table.select("thead tr")]
    if headers!=[["구분","이용료","비고"],["관내","관외"]]:return [],"facility_price_table_structure_changed"
    rows=table.select("tbody tr")
    if len(rows)!=5:return [],"facility_price_table_structure_changed"
    out=[]
    def add(category,label,value,unit,manual=False):
        if not re.fullmatch(r"[\d,]+원",value):return False
        amount=amount_from_cell(value,require_won=True)
        if not amount:return False
        record={"category":category,"label":label,"amount":amount,"unit":unit,"sourceParser":"sangbok_rows_v1"}
        if manual:record["requiresManualQuantity"]=True
        out.append(record)
        return True
    for i,(label,cat,unit) in enumerate(SANGBOK_ROWS):
        cells=[clean(c.get_text()) for c in rows[i].find_all("td",recursive=False)]
        if len(cells)!=(5 if i==0 else 4) or cells[:2]!=[label,unit]:return [],"facility_price_table_structure_changed"
        for col,area in [(2,"관내"),(3,"관외")]:
            if not add(cat,label+" · "+area,cells[col],unit,i==0):return [],"facility_price_table_amount_invalid"
    normal=[clean(c.get_text()) for c in rows[3].find_all("td",recursive=False)]
    accident=[clean(c.get_text()) for c in rows[4].find_all("td",recursive=False)]
    if len(normal)!=3 or normal[:2]!=["염습료","일반사"] or len(accident)!=2 or accident[0]!="사고사":
        return [],"facility_price_table_structure_changed"
    if not accident[1].endswith("(수습,봉합은 별도)"):return [],"facility_price_conditions_changed"
    if not add("염습/입관","염습료 · 일반사",normal[2],"") or not add("염습/입관","염습료 · 사고사 (수습·봉합 별도)",accident[1].replace("(수습,봉합은 별도)",""),""):
        return [],"facility_price_table_amount_invalid"
    return out,"guard_passed"

def scan_sangbok(s,h,home):
    result={"status":"no_price_found","homepage":home,"sourceUrl":SANGBOK_URL}
    if not sangbok_identity(h.get("fcltNm",""),h.get("addr","")):
        return {**result,"reviewReason":"facility_identity_unverifiable"}
    html,final=get_html(s,SANGBOK_URL)
    if not html:return {**result,"status":"unreachable"}
    if not sangbok_url_matches(final):return {**result,"reviewReason":"facility_source_path_mismatch"}
    prices,reason=sangbok_prices(BeautifulSoup(html,"html.parser"))
    if not prices:return {**result,"reviewReason":reason}
    return {**result,"status":"priced","sourceUrl":final,"prices":prices,"verifiedAt":now(),"sourceNote":SANGBOK_NOTE}

def scan_hall(h,old=None):
    home=normalize_url(h.get("homepageUrl",""))
    if not home:return {"status":"no_homepage"}
    start=branch_scan_start(h,old,home)
    if host(home) in REVIEWED_UNIT_HOSTS:
        start=urljoin(home,REVIEWED_UNIT_HOSTS[host(home)])
    expected_code=query_value(start,"fnrCd")
    s=session()
    # Preserve the public feed's raw URL. Correct only this verified identity,
    # never repair arbitrary dotless domains or follow another facility's links.
    if host(home) in SANGBOK_HOSTS:return scan_sangbok(s,h,home)
    if host(home)=="youngwol.org":return scan_youngwol(s,home)
    if host(home)=="pcfmc.or.kr":return scan_pcfmc(s,h,home)
    html,final=get_html(s,start)
    if not html:
        # retry http if https failed
        if start.startswith("https://"):
            html,final=get_html(s,"http://"+start[8:])
    if not html:return {"status":"unreachable","homepage":home}
    if host(home) in REVIEWED_UNIT_HOSTS and host(final)!=host(home):
        return {"status":"no_price_found","homepage":home}
    if expected_code and (not same_host(start,final) or query_value(final,"fnrCd")!=expected_code):
        return {"status":"no_price_found","homepage":home}
    pages=[final]
    if host(home) not in REVIEWED_UNIT_HOSTS:pages+=candidate_links(html,final)
    best=[];besturl=final
    visited=set()
    for i,u in enumerate(pages):
        if u in visited:continue
        visited.add(u)
        if expected_code and query_value(u,"fnrCd")!=expected_code:continue
        ph,pageurl=(html,final) if i==0 else get_html(s,u)
        if not ph:continue
        if expected_code and (not same_host(start,pageurl) or query_value(pageurl,"fnrCd")!=expected_code):continue
        soup=BeautifulSoup(ph,"html.parser")
        adapted=reviewed_unit_prices(soup,pageurl)
        if adapted is None:adapted=reviewed_room_prices(soup,pageurl)
        if adapted is None:adapted=ewha_seoul_prices(soup,pageurl)
        if adapted is None:adapted=gijang_prices(soup,pageurl)
        if adapted is None:adapted=pyeongtaek_prices(soup,pageurl)
        prices=dedupe(adapted if adapted is not None else table_prices(soup)+text_prices(soup))
        # facility-price page must contain at least one core category;
        # parking-only pages are not accepted as facility-price override.
        core=sum(1 for x in prices if x["category"] in ("빈소","안치실","염습/입관","영결식장","청소/관리"))
        if core and len(prices)>len(best):
            best,besturl=prices,pageurl
        time.sleep(.08)
    if not best:return {"status":"no_price_found","homepage":home}
    return {
      "status":"priced","homepage":home,"sourceUrl":besturl,
      "prices":best,"verifiedAt":now(),
      "sourceNote":REVIEWED_UNIT_NOTES.get(host(besturl),"")
    }

def load_json(path,default):
    try:return json.loads(path.read_text(encoding="utf-8"))
    except:return default

def summarize_promotions(results,merged,record_key):
    counts={"eligible":0,"rejected":0,"unchecked":0}
    reasons={}
    priced_record_keys=set()
    for v in results.values():
        if v.get("status")!="priced":
            continue
        priced_record_keys.add(record_key(v))
        promotion=v.get("promotion")
        if not isinstance(promotion,dict):
            counts["unchecked"]+=1
            reason="not_evaluated"
        elif promotion.get("eligible") is True:
            counts["eligible"]+=1
            reason=promotion.get("reason") or "guard_passed"
        else:
            counts["rejected"]+=1
            reason=promotion.get("reason") or "rejected"
        reasons[reason]=reasons.get(reason,0)+1
    override_record_keys={record_key(x) for x in merged}
    return counts,reasons,len(priced_record_keys & override_record_keys)

def reevaluate_saved_promotions(results,byname,record_key,batch):
    batch_ids={id(x) for x in batch}
    for res in results.values():
        if res.get("status")!="priced" or id(res) in batch_ids:
            continue
        rec={
          "facilityName":res.get("facilityName",""),
          "address":res.get("address",""),
          "verifiedAt":res.get("verifiedAt",""),
          "sourceName":"장례식장 공식 홈페이지 공개가격",
          "sourceUrl":res.get("sourceUrl",""),
          "sourceGrade":"A",
          "sourceNote":res.get("sourceNote") or "공식 홈페이지에서 확인된 게시 가격. 시행일이 별도 표기되지 않은 경우 실제 이용 전 최종 확인 필요.",
          "prices":res.get("prices",[])
        }
        old=byname.get(record_key(rec))
        ok,reason=identity_guard(rec,old,res.get("homepage",""))
        res["promotion"]={
          "eligible":ok,"reason":reason,"applied":False,
          "guardVersion":PROMOTION_GUARD_VERSION,"basis":"stored_scan_recheck"
        }

def main():
    hall_doc=load_json(HALLS,{})
    halls=hall_doc.get("items",[])
    db=load_json(OVERRIDES,{"schemaVersion":4,"items":[]})
    state=load_json(STATE,{"cursor":0,"completedCycles":0,"results":{}})
    cursor=int(state.get("cursor",0))
    if not halls:raise SystemExit("no halls")
    region_count=len(hall_doc.get("regions",{}))
    declared_count=int(hall_doc.get("count",0) or 0)
    if region_count!=17 or declared_count!=len(halls) or len(halls)<1000:
        raise SystemExit(
            f"incomplete funeral-hall source: regions={region_count}, declared={declared_count}, items={len(halls)}"
        )

    def record_key(x):
        return norm(x.get("facilityName",""))+"|"+norm(x.get("address",""))
    byname={record_key(x):x for x in db.get("items",[]) if x.get("facilityName")}
    results=state.get("results",{})
    batch=[]
    n=len(halls)
    current_source_ids={source_identity(h.get("fcltNm",""),h.get("addr","")) for h in halls}
    previous_result_count=len(results)
    results={k:v for k,v in results.items() if k in current_source_ids}
    stale_results_pruned=previous_result_count-len(results)
    for j in range(min(BATCH,n)):
        idx=(cursor+j)%n
        h=halls[idx]
        key=source_identity(h.get("fcltNm",""),h.get("addr",""))
        old=byname.get(record_key({"facilityName":h.get("fcltNm",""),"address":h.get("addr","")}))
        res=scan_hall(h,old)
        res.update({"facilityName":h.get("fcltNm",""),"address":h.get("addr",""),"index":idx})
        results[key]=res
        batch.append(res)
        if res["status"]=="priced":
            rec={
              "facilityName":h.get("fcltNm",""),
              "address":h.get("addr",""),
              "verifiedAt":res["verifiedAt"],
              "sourceName":"장례식장 공식 홈페이지 공개가격",
              "sourceUrl":res["sourceUrl"],
              "sourceGrade":"A",
              "sourceNote":res.get("sourceNote") or "공식 홈페이지에서 확인된 게시 가격. 시행일이 별도 표기되지 않은 경우 실제 이용 전 최종 확인 필요.",
              "prices":res["prices"]
            }
            key_rec=record_key(rec)
            old=byname.get(key_rec)
            ok,reason=identity_guard(rec,old,res.get("homepage",""))
            applied=False
            # Never replace a curated A record unless facility identity and data completeness are verified.
            if ok and (not old or old.get("sourceGrade")!="A" or len(rec["prices"])>=len(old.get("prices",[]))):
                byname[key_rec]=rec
                applied=True
            res["promotion"]={
              "eligible":ok,"reason":reason,"applied":applied,
              "guardVersion":PROMOTION_GUARD_VERSION,"basis":"live_scan"
            }
        print(idx,h.get("fcltNm"),res["status"],len(res.get("prices",[])))

    # Re-evaluate every saved priced row on each run. This prevents stale
    # decisions when the identity guard changes. Legacy rows are report-only:
    # only a freshly scanned row can write a replacement into the override DB.
    reevaluate_saved_promotions(results,byname,record_key,batch)

    newcursor=(cursor+len(batch))%n
    cycles=int(state.get("completedCycles",0))+(1 if cursor+len(batch)>=n else 0)
    state.update({"cursor":newcursor,"completedCycles":cycles,"updatedAt":now(),"results":results,
                  "totalFacilities":n,"staleResultsPruned":stale_results_pruned})

    merged=sorted(byname.values(),key=lambda x:canon_name(x.get("facilityName","")))
    db.update({"schemaVersion":5,"updatedAt":now(),"items":merged,
               "source":{"name":"최신 공식 홈페이지 가격 우선 DB","note":"A=장례식장 공식 홈페이지, B=검증된 2차 가격 미러. 미확인 시설은 2023 공시 기준값 사용."}})
    OVERRIDES.write_text(json.dumps(db,ensure_ascii=False,indent=2),encoding="utf-8")
    STATE.write_text(json.dumps(state,ensure_ascii=False,separators=(",",":")),encoding="utf-8")

    counts={}
    for v in state["results"].values():counts[v.get("status","unknown")]=counts.get(v.get("status","unknown"),0)+1
    promotion_counts,promotion_reasons,priced_override_overlap_count=summarize_promotions(
        state["results"],merged,record_key
    )
    current_record_keys={record_key({"facilityName":h.get("fcltNm",""),"address":h.get("addr","")}) for h in halls}
    current_name_counts={}
    for h in halls:
        name_key=norm(h.get("fcltNm",""))
        current_name_counts[name_key]=current_name_counts.get(name_key,0)+1
    override_current_exact=sum(1 for x in merged if record_key(x) in current_record_keys)
    override_current_name_only=sum(
        1 for x in merged
        if record_key(x) not in current_record_keys
        and current_name_counts.get(norm(x.get("facilityName","")),0)==1
    )
    override_not_in_source=len(merged)-override_current_exact-override_current_name_only
    report={"updatedAt":now(),"cursor":newcursor,"completedCycles":cycles,"total":n,
            "scannedUnique":len(state["results"]),"statusCounts":counts,
            "staleResultsPruned":stale_results_pruned,
            "pricedPromotionCounts":promotion_counts,
            "pricedPromotionReasons":promotion_reasons,
            "pricedOverrideOverlapCount":priced_override_overlap_count,
            "pricedMetricNote":"statusCounts.priced is discovery only. eligible means the current identity/completeness guard passed; stored_scan_recheck is report-only and does not write an override.",
            "overrideCount":len(merged),
            "overrideIdentityCounts":{
                "currentExact":override_current_exact,
                "currentNameOnly":override_current_name_only,
                "notInCurrentSource":override_not_in_source
            },
            "lastBatch":batch}
    REPORT.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf-8")
    print(json.dumps({k:report[k] for k in ("cursor","completedCycles","scannedUnique","statusCounts","overrideCount")},ensure_ascii=False))

if __name__=="__main__":
    main()






