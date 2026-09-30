#!/usr/bin/env python3
import json, os, urllib.parse, urllib.request, xml.etree.ElementTree as ET
from datetime import datetime, timezone

ENDPOINT = "https://apis.data.go.kr/1352000/ODMS_DATA_04_1"
KEY = os.environ["FUNERAL_API_KEY"]
REGIONS = [
    ["서울특별시"],["부산광역시"],["대구광역시"],["인천광역시"],["광주광역시"],["대전광역시"],["울산광역시"],
    ["세종특별자치시"],["경기도"],["강원특별자치도","강원도"],["충청북도"],["충청남도"],
    ["전북특별자치도","전라북도"],["전라남도"],["경상북도"],["경상남도"],["제주특별자치도"]
]

FIELDS = ["ctpv","sigungu","fcltNm","addr","telno","fxno","homepageUrl","tpkct","gubun","mtaCnt","ehrCnt",
          "diningFclt","store","pklt","bereavedWaitRm","sdblsPfFclt","operType"]

def request_region(region):
    params = {"serviceKey": KEY, "pageNo": "1", "numOfRows": "1000", "apiType": "XML", "ctpv": region}
    url = ENDPOINT + "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={"User-Agent":"dahamsangjo-funeral-hall-sync/1.0"})
    with urllib.request.urlopen(req, timeout=60) as r:
        raw = r.read()
    root = ET.fromstring(raw)
    code = (root.findtext("./header/resultCode") or "").strip()
    if code != "00":
        raise RuntimeError(f"{region}: API resultCode={code} msg={root.findtext('./header/resultMsg')}")
    items=[]
    for item in root.findall("./body/items/item"):
        row={k:(item.findtext(k) or "").strip() for k in FIELDS}
        items.append(row)
    total = int(float(root.findtext("./body/totalCount") or len(items)))
    return items, total

def main():
    all_items=[]
    counts={}
    for aliases in REGIONS:
        rows=[]
        chosen=None
        for region in aliases:
            try:
                candidate,total=request_region(region)
            except Exception as e:
                print(f"WARN {region}: {e}")
                continue
            if candidate:
                rows=candidate; chosen=region
                if len(rows) < total:
                    print(f"WARN {region}: got {len(rows)} of {total}; increase paging logic if this occurs")
                break
        if chosen:
            counts[chosen]=len(rows)
            all_items.extend(rows)
        else:
            print("WARN no data for", aliases)

    dedup={}
    for x in all_items:
        key=(x.get("ctpv",""),x.get("sigungu",""),x.get("fcltNm",""),x.get("addr",""))
        dedup[key]=x
    items=list(dedup.values())
    items.sort(key=lambda x:(x.get("ctpv",""),x.get("sigungu",""),x.get("fcltNm","")))
    out={"updatedAt":datetime.now(timezone.utc).isoformat(),"count":len(items),"regions":counts,"items":items}
    os.makedirs("data",exist_ok=True)
    with open("data/funeral-halls.json","w",encoding="utf-8") as f:
        json.dump(out,f,ensure_ascii=False,separators=(",",":"))
    print(f"saved {len(items)} halls")

if __name__=="__main__":
    main()
