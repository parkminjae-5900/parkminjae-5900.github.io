#!/usr/bin/env python3
import json, os, urllib.parse, urllib.request, urllib.error, xml.etree.ElementTree as ET
from datetime import datetime, timezone

ENDPOINT = "https://apis.data.go.kr/1352000/ODMS_DATA_04_1"
KEY = os.environ["FUNERAL_API_KEY"]
PAGE_SIZE = 100
REGIONS = [
    ["서울특별시"],["부산광역시"],["대구광역시"],["인천광역시"],["광주광역시"],["대전광역시"],["울산광역시"],
    ["세종특별자치시"],["경기도"],["강원특별자치도","강원도"],["충청북도"],["충청남도"],
    ["전북특별자치도","전라북도"],["전라남도"],["경상북도"],["경상남도"],["제주특별자치도"]
]
FIELDS = ["ctpv","sigungu","fcltNm","addr","telno","fxno","homepageUrl","tpkct","gubun","mtaCnt","ehrCnt",
          "diningFclt","store","pklt","bereavedWaitRm","sdblsPfFclt","operType"]

def fetch_page(region, page_no):
    params = {
        "pageNo": str(page_no), "numOfRows": str(PAGE_SIZE),
        "apiType": "XML", "ctpv": region
    }
    # data.go.kr keys may be supplied already URL-encoded. Do not encode serviceKey twice.
    query = "serviceKey=" + KEY.strip() + "&" + urllib.parse.urlencode(params)
    url = ENDPOINT + "?" + query
    req = urllib.request.Request(url, headers={"User-Agent":"dahamsangjo-funeral-hall-sync/1.2"})
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            raw = r.read()
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8","replace")
        raise RuntimeError(f"HTTP {e.code}: {body[:500]}")
    root = ET.fromstring(raw)
    code = (root.findtext("./header/resultCode") or "").strip()
    if code != "00":
        raise RuntimeError(f"{region}: API resultCode={code} msg={root.findtext('./header/resultMsg')}")
    rows=[]
    for item in root.findall("./body/items/item"):
        rows.append({k:(item.findtext(k) or "").strip() for k in FIELDS})
    total=int(float(root.findtext("./body/totalCount") or len(rows)))
    return rows,total

def request_region(region):
    all_rows=[]
    page=1
    total=None
    while total is None or len(all_rows) < total:
        rows,total=fetch_page(region,page)
        if not rows:
            break
        all_rows.extend(rows)
        page += 1
        if page > 100:
            raise RuntimeError(f"{region}: paging safety limit exceeded")
    return all_rows,total or 0

def main():
    all_items=[]
    counts={}
    for aliases in REGIONS:
        rows=[]
        chosen=None
        last_error=None
        for region in aliases:
            try:
                candidate,total=request_region(region)
            except Exception as e:
                last_error=e
                print(f"WARN {region}: {e}")
                continue
            if candidate:
                rows=candidate
                chosen=region
                if len(rows) != total:
                    print(f"WARN {region}: fetched {len(rows)} / totalCount {total}")
                break
        if chosen:
            counts[chosen]=len(rows)
            all_items.extend(rows)
            print(f"OK {chosen}: {len(rows)}")
        else:
            print(f"WARN no data for {aliases}: {last_error}")

    dedup={}
    for x in all_items:
        key=(x.get("ctpv",""),x.get("sigungu",""),x.get("fcltNm",""),x.get("addr",""))
        dedup[key]=x

    items=sorted(dedup.values(),key=lambda x:(x.get("ctpv",""),x.get("sigungu",""),x.get("fcltNm","")))
    out={
        "updatedAt":datetime.now(timezone.utc).isoformat(),
        "count":len(items),
        "regions":counts,
        "items":items
    }
    os.makedirs("data",exist_ok=True)
    with open("data/funeral-halls.json","w",encoding="utf-8") as fp:
        json.dump(out,fp,ensure_ascii=False,separators=(",",":"))
    print(f"saved {len(items)} halls")

if __name__=="__main__":
    main()
