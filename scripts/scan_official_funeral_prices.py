#!/usr/bin/env python3
import json, os, re, time, hashlib
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urljoin, urlparse
import requests
from bs4 import BeautifulSoup

HALLS=Path("data/funeral-halls.json")
OVERRIDES=Path("data/funeral-hall-prices.json")
STATE=Path("data/official-price-scan-state.json")
REPORT=Path("data/official-price-scan-report.json")
BATCH=int(os.environ.get("PRICE_SCAN_BATCH","45"))
TIMEOUT=6
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
    for cat,words in CATEGORY_RULES:
        if any(w in label for w in words):return cat
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

def scan_hall(h):
    home=normalize_url(h.get("homepageUrl",""))
    if not home:return {"status":"no_homepage"}
    s=session()
    html,final=get_html(s,home)
    if not html:
        # retry http if https failed
        if home.startswith("https://"):
            html,final=get_html(s,"http://"+home[8:])
    if not html:return {"status":"unreachable","homepage":home}
    pages=[final]
    pages+=candidate_links(html,final)
    best=[];besturl=final
    visited=set()
    for i,u in enumerate(pages):
        if u in visited:continue
        visited.add(u)
        ph=html if i==0 else get_html(s,u)[0]
        if not ph:continue
        soup=BeautifulSoup(ph,"html.parser")
        prices=dedupe(table_prices(soup)+text_prices(soup))
        # facility-price page must contain at least one core category;
        # parking-only pages are not accepted as facility-price override.
        core=sum(1 for x in prices if x["category"] in ("빈소","안치실","염습/입관","영결식장","청소/관리"))
        if core and len(prices)>len(best):
            best,besturl=prices,u
        time.sleep(.08)
    if not best:return {"status":"no_price_found","homepage":home}
    return {
      "status":"priced","homepage":home,"sourceUrl":besturl,
      "prices":best,"verifiedAt":now()
    }

def load_json(path,default):
    try:return json.loads(path.read_text(encoding="utf-8"))
    except:return default

def main():
    halls=load_json(HALLS,{}).get("items",[])
    db=load_json(OVERRIDES,{"schemaVersion":4,"items":[]})
    state=load_json(STATE,{"cursor":0,"completedCycles":0,"results":{}})
    cursor=int(state.get("cursor",0))
    if not halls:raise SystemExit("no halls")

    byname={norm(x.get("facilityName","")):x for x in db.get("items",[]) if x.get("facilityName")}
    results=state.get("results",{})
    batch=[]
    n=len(halls)
    for j in range(min(BATCH,n)):
        idx=(cursor+j)%n
        h=halls[idx]
        key=hashlib.sha1((h.get("fcltNm","")+"|"+h.get("addr","")).encode()).hexdigest()[:16]
        res=scan_hall(h)
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
              "sourceNote":"공식 홈페이지에서 확인된 게시 가격. 시행일이 별도 표기되지 않은 경우 실제 이용 전 최종 확인 필요.",
              "prices":res["prices"]
            }
            old=byname.get(norm(rec["facilityName"]))
            # Preserve manually curated A record if it is same or newer verified date with richer data.
            if not old or old.get("sourceGrade")!="A" or len(rec["prices"])>len(old.get("prices",[])):
                byname[norm(rec["facilityName"])]=rec
        print(idx,h.get("fcltNm"),res["status"],len(res.get("prices",[])))

    newcursor=(cursor+len(batch))%n
    cycles=int(state.get("completedCycles",0))+(1 if cursor+len(batch)>=n else 0)
    state.update({"cursor":newcursor,"completedCycles":cycles,"updatedAt":now(),"results":results,"totalFacilities":n})
    # keep scan history bounded to all current facilities
    if len(results)>n*2:
        items=sorted(results.items(),key=lambda kv:kv[1].get("index",0))
        state["results"]=dict(items[-n:])

    merged=sorted(byname.values(),key=lambda x:canon_name(x.get("facilityName","")))
    db.update({"schemaVersion":5,"updatedAt":now(),"items":merged,
               "source":{"name":"최신 공식 홈페이지 가격 우선 DB","note":"A=장례식장 공식 홈페이지, B=검증된 2차 가격 미러. 미확인 시설은 2023 공시 기준값 사용."}})
    OVERRIDES.write_text(json.dumps(db,ensure_ascii=False,indent=2),encoding="utf-8")
    STATE.write_text(json.dumps(state,ensure_ascii=False,separators=(",",":")),encoding="utf-8")

    counts={}
    for v in state["results"].values():counts[v.get("status","unknown")]=counts.get(v.get("status","unknown"),0)+1
    report={"updatedAt":now(),"cursor":newcursor,"completedCycles":cycles,"total":n,
            "scannedUnique":len(state["results"]),"statusCounts":counts,
            "overrideCount":len(merged),"lastBatch":batch}
    REPORT.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf-8")
    print(json.dumps({k:report[k] for k in ("cursor","completedCycles","scannedUnique","statusCounts","overrideCount")},ensure_ascii=False))

if __name__=="__main__":
    main()
