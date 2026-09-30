#!/usr/bin/env python3
"""Normalize supplied public rows without inventing billing units or current rates."""
import csv, json, pathlib, sys, collections
source = pathlib.Path(sys.argv[1])
def read(pattern):
    b=next(source.glob(pattern)).read_bytes()
    for enc in ('utf-8-sig','cp949'):
        try: return list(csv.DictReader(b.decode(enc).splitlines()))
        except UnicodeDecodeError: pass
    raise ValueError('Unsupported source encoding')
out=pathlib.Path('data'); halls=collections.defaultdict(list)
for r in read('2.*'):
    if r['항목']!='시설임대료': continue
    try: amount=int(r['금액'])
    except ValueError: continue
    if amount<0: continue
    halls[r['장례식장명']].append(dict(category=r['품종'],label=r['품명'],detail=r['세부내용'],amount=amount))
crem=collections.defaultdict(list)
for r in read('3.*'):
    if r['시설종류']!='화장시설': continue
    try: amount=int(r['금액'])
    except ValueError: continue
    if amount<0: continue
    crem[r['장사시설명']].append(dict(category=r['품목분류'],label=r['품목'],detail=r['규격'],amount=amount))
# Optional facility metadata export; price-only builds remain reproducible.
meta=json.loads(pathlib.Path(sys.argv[2]).read_text()) if len(sys.argv)>2 else {'facilities':[]}
common=dict(sourceDate='2023-06-01',sourceName='한국장례문화진흥원 · e하늘 공개자료',sourceUrl='https://www.data.go.kr/data/15021763/fileData.do',note='2023년 공시 참고자료. 현재 요금·운영·자격을 시설에 확인해야 합니다.')
for name,data in [('funeral-hall-price-baseline.json',dict(halls=halls)),('cremation-prices.json',dict(facilities=[dict(f,prices=crem.get(f['name'],[])) for f in meta['facilities']]+[dict(name=n,prices=p) for n,p in crem.items() if n not in {f['name'] for f in meta['facilities']}]))]:
    (out/name).write_text(json.dumps(dict(common,**data),ensure_ascii=False,separators=(',',':')))
print(json.dumps({'halls':len(halls),'hallRows':sum(map(len,halls.values())),'cremationFacilitiesWithPrices':len(crem),'cremationRows':sum(map(len,crem.values()))}))
