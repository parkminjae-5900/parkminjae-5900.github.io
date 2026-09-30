#!/usr/bin/env python3
import json, os, re, sys, time
from datetime import datetime, timezone
from urllib.parse import urljoin, urlparse, parse_qs, urlencode
import requests
from bs4 import BeautifulSoup

BASE="https://web1.15774129.go.kr"
MENU="M0001000100000000"
GROUP="TBC0700001"
LIST=BASE+"/portal/esky/fnlfac/fac_list.do"
OUT="data/funeral-hall-prices.json"

UA="dahamsangjo-price-sync/1.0 (+https://www.dahamsangjo.co.kr/)"
S=requests.Session()
S.headers.update({"User-Agent":UA,"Accept-Language":"ko-KR,ko;q=0.9,en;q=0.5"})

MONEY_RE=re.compile(r"(?<!\d)(\d{1,3}(?:,\d{3})+|\d{4,})(?:\s*원)?(?!\d)")
SPACE_RE=re.compile(r"\s+")

def clean(s):
    return SPACE_RE.sub(" ", (s or "").replace("\xa0"," ")).strip()

def norm(s):
    return re.sub(r"[^0-9A-Za-z가-힣]","",clean(s)).lower()

def get(url, params=None):
    r=S.get(url,params=params,timeout=35)
    r.raise_for_status()
    if not r.encoding or r.encoding.lower()=="iso-8859-1":
        r.encoding=r.apparent_encoding or "utf-8"
    return r.text

def extract_detail_links(html):
    soup=BeautifulSoup(html,"html.parser")
    out={}
    for a in soup.find_all("a",href=True):
        href=a.get("href","")
        if "fac_view.do" not in href or "facilitycd=" not in href:
            continue
        u=urljoin(BASE,href)
        q=parse_qs(urlparse(u).query)
        fid=(q.get("facilitycd") or [""])[0]
        if not fid: continue
        name=clean(a.get_text(" ",strip=True))
        out[fid]={"facilityId":fid,"facilityName":name,"url":u}
    # some pages use javascript open functions instead of direct hrefs
    text=str(soup)
    for m in re.finditer(r"facilitycd(?:=|%3D|['\"\s,:]+)(\d{6,})",text,re.I):
        fid=m.group(1)
        out.setdefault(fid,{"facilityId":fid,"facilityName":"","url":""})
    return out

def discover_facilities():
    found={}
    # e하늘 list pagination has changed before; try common parameter names safely.
    modes=["pageIndex","pageNo","page","currentPage"]
    for mode in modes:
        local_new=0
        seen_signature=None
        for p in range(1,201):
            params={"menuId":MENU,"facilitygroupcd":GROUP,mode:str(p)}
            try:
                html=get(LIST,params)
            except Exception as e:
                if p==1: print(f"WARN list {mode}: {e}",file=sys.stderr)
                break
            links=extract_detail_links(html)
            signature=tuple(sorted(links))
            if p>1 and signature and signature==seen_signature:
                break
            seen_signature=signature
            before=len(found); found.update(links); local_new+=len(found)-before
            if not links:
                break
            if p>3 and len(found)==before:
                break
            time.sleep(0.12)
        if local_new:
            print(f"discover {mode}: +{local_new}, total={len(found)}")
        if len(found)>=500:
            break
    return found

def text_near_label(soup,label):
    rx=re.compile(label)
    n=soup.find(string=rx)
    if not n:return ""
    parent=n.parent
    if parent:
        nxt=parent.find_next(["td","dd","span","p"])
        if nxt:return clean(nxt.get_text(" ",strip=True))
    return ""

def classify(label):
    s=norm(label)
    if "빈소" in s or "분향실" in s:return "빈소"
    if "안치" in s:return "안치실"
    if "염습" in s or "입관" in s:return "염습/입관"
    if "영결" in s:return "영결식장"
    if "청소" in s or "관리" in s:return "청소/관리"
    if "주차" in s:return "주차"
    if "도우미" in s:return "접객도우미"
    if "제단" in s:return "제단"
    if "식사" in s or "음식" in s or "국" in s or "밥" in s:return "음식"
    return "기타"

def extract_prices(html,fid):
    soup=BeautifulSoup(html,"html.parser")
    title=clean((soup.find("h1") or soup.find("h2") or soup.find("h3") or soup.title or "").get_text(" ",strip=True) if (soup.find("h1") or soup.find("h2") or soup.find("h3") or soup.title) else "")
    facility_name=title
    for suffix in ["가격정보","시설정보","장사시설/장례용품가격","e하늘 장사정보시스템"]:
        facility_name=facility_name.replace(suffix,"")
    facility_name=clean(facility_name.strip(" |-"))
    address=text_near_label(soup,"주소")
    phone=text_near_label(soup,"전화|연락처")
    verified=datetime.now(timezone.utc).isoformat()

    items=[]
    for table in soup.find_all("table"):
        rows=table.find_all("tr")
        if not rows: continue
        headers=[clean(x.get_text(" ",strip=True)) for x in rows[0].find_all(["th","td"])]
        price_idx=None
        for i,h in enumerate(headers):
            nh=norm(h)
            if ("가격" in nh or "사용료" in nh or "금액" in nh) and "평균" not in nh:
                price_idx=i; break
        for tr in rows[1:] if headers else rows:
            cells=[clean(x.get_text(" ",strip=True)) for x in tr.find_all(["th","td"])]
            if len(cells)<2: continue
            rowtext=" ".join(cells)
            if any(x in rowtext for x in ["전국 평균가격","관내 평균가격"]):
                pass
            amount_txt=""
            if price_idx is not None and price_idx<len(cells):
                amount_txt=cells[price_idx]
            if not MONEY_RE.search(amount_txt):
                for c in cells[1:]:
                    if MONEY_RE.fullmatch(c.replace(" ","")) or ("원" in c and MONEY_RE.search(c)):
                        amount_txt=c; break
            m=MONEY_RE.search(amount_txt)
            if not m: continue
            amount=int(m.group(1).replace(",",""))
            if amount<=0: continue
            label=clean(" ".join(cells[:max(1, price_idx or 2)]))
            if not label or "평균" in label: continue
            unit=""
            for c in cells:
                if any(k in c for k in ["24시간","1일","시간","1회","1실","인분","kg","평"]):
                    unit=c if len(c)<=60 else ""
                    if unit: break
            items.append({"category":classify(label),"label":label[:180],"amount":amount,"unit":unit[:80]})

    # de-duplicate exact extracted rows
    seen=set(); uniq=[]
    for x in items:
        k=(x["label"],x["amount"],x["unit"])
        if k in seen: continue
        seen.add(k); uniq.append(x)
    return {
        "facilityId":fid,
        "facilityName":facility_name,
        "address":address,
        "telephone":phone,
        "verifiedAt":verified,
        "sourceName":"보건복지부 e하늘 장사정보서비스",
        "sourceUrl":f"{BASE}/portal/esky/fnlfac/fac_view.do?"+urlencode({"menuId":MENU,"facilitycd":fid,"facilitygroupcd":GROUP,"loc":"price","sanbundiv":"N"}),
        "prices":uniq
    }

def load_old():
    try:
        with open(OUT,encoding="utf-8") as f:return json.load(f)
    except Exception:return {"items":[]}

def main():
    facilities=discover_facilities()
    if len(facilities)<50:
        raise SystemExit(f"Safety stop: only {len(facilities)} e하늘 funeral-hall detail links discovered; existing DB left untouched")

    old=load_old()
    old_by_id={str(x.get("facilityId","")):x for x in old.get("items",[]) if x.get("facilityId")}
    result=[]
    ok=0
    for i,(fid,meta) in enumerate(sorted(facilities.items()),1):
        url=f"{BASE}/portal/esky/fnlfac/fac_view.do"
        params={"menuId":MENU,"facilitycd":fid,"facilitygroupcd":GROUP,"loc":"price","sanbundiv":"N"}
        try:
            html=get(url,params)
            rec=extract_prices(html,fid)
            if meta.get("facilityName") and (not rec["facilityName"] or "e하늘" in rec["facilityName"]):
                rec["facilityName"]=meta["facilityName"]
            if rec["prices"]:
                result.append(rec); ok+=1
            elif fid in old_by_id:
                result.append(old_by_id[fid])
        except Exception as e:
            print(f"WARN {fid}: {e}",file=sys.stderr)
            if fid in old_by_id: result.append(old_by_id[fid])
        if i%100==0: print(f"processed {i}/{len(facilities)}; priced={ok}")
        time.sleep(0.10)

    if ok<10 and not old_by_id:
        raise SystemExit(f"Safety stop: only {ok} facilities yielded prices; existing DB left untouched")

    out={
        "schemaVersion":2,
        "updatedAt":datetime.now(timezone.utc).isoformat(),
        "source":{
            "name":"보건복지부 e하늘 장사정보서비스",
            "listUrl":LIST+"?"+urlencode({"menuId":MENU,"facilitygroupcd":GROUP}),
            "note":"e하늘 공개 장례식장 가격정보를 자동 수집. 수집 실패 시 기존 검증값 유지, 임의 추정 금액 금지."
        },
        "discoveredFacilities":len(facilities),
        "pricedFacilities":len(result),
        "items":sorted(result,key=lambda x:(x.get("facilityName",""),x.get("facilityId","")))
    }
    os.makedirs(os.path.dirname(OUT),exist_ok=True)
    tmp=OUT+".tmp"
    with open(tmp,"w",encoding="utf-8") as f: json.dump(out,f,ensure_ascii=False,separators=(",",":"))
    os.replace(tmp,OUT)
    print(f"saved {len(result)} priced facilities from {len(facilities)} discovered")

if __name__=="__main__":
    main()
