#!/usr/bin/env python3
"""Useful family/no-hall layers on existing URLs; no keyword-combination pages.

--write produces deterministic static HTML. --check detects drift. No network,
price, phone, raw dataset, canonical, or regional artwork changes are performed.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import math
import re
from html import escape, unescape
from pathlib import Path
import xml.etree.ElementTree as ET
from funeral_hall_photos import (ROOT, BASE, load_inputs, load_photos, identity_key,
                                facility_id, figure, safe_url, repair_photo_page, load_aliases)
from regional_image_registry import Tags, set_attributes

BEGIN = '<!-- family-nohall-guide:start -->'
END = '<!-- family-nohall-guide:end -->'
SM = 'http://www.sitemaps.org/schemas/sitemap/0.9'
IM = 'http://www.google.com/schemas/sitemap-image/1.1'
PAGE_SIZE = 50


def e(value):
    return escape(str(value), quote=True)


def jsonld(value):
    # External source fields must never terminate a script element.
    return json.dumps(value, ensure_ascii=False, separators=(',', ':')).replace('<', '\\u003c').replace('>', '\\u003e').replace('&', '\\u0026')


def plain(value):
    return unescape(re.sub('<[^>]+>', ' ', value))


def put_block(source, content):
    block = BEGIN + '\n' + content + '\n' + END
    if BEGIN in source:
        return re.sub(re.escape(BEGIN) + '.*?' + re.escape(END), lambda m: block, source, flags=re.S)
    if '</main>' not in source:
        raise ValueError('Managed page needs a main landmark')
    return source.replace('</main>', block + '\n</main>', 1)


def css(source):
    if 'href="/assets/family-nohall-guide.css"' not in source:
        source = source.replace('</head>', '<link rel="stylesheet" href="/assets/family-nohall-guide.css">\n</head>', 1)
    return source


def meta(source, key, value, attr='name'):
    matches = [m for m in re.finditer(r'<meta\b[^>]*>', source) if dict(Tags(m[0]).tags[0][1]).get(attr) == key]
    tag = f'<meta {attr}="{e(key)}" content="{e(value)}">'
    if len(matches) > 1:
        raise ValueError('Duplicate metadata: ' + key)
    if matches:
        m = matches[0]; return source[:m.start()] + tag + source[m.end():]
    return source.replace('</head>', tag + '\n</head>', 1)


def metadata(source, title, description):
    source = re.sub(r'<title>.*?</title>', lambda m: '<title>' + e(title) + '</title>', source, flags=re.S)
    for key, value, attr in [('description', description, 'name'), ('og:title', title, 'property'),
                             ('og:description', description, 'property'), ('twitter:title', title, 'name'),
                             ('twitter:description', description, 'name')]:
        source = meta(source, key, value, attr)
    # Existing WebPage names must agree with the new visible document title.
    def fix(m):
        data = json.loads(m[1])
        def walk(node):
            if isinstance(node, list):
                for x in node: walk(x)
            elif isinstance(node, dict):
                if node.get('@type') == 'WebPage':
                    node.update(name=title, description=description)
                for value in node.values(): walk(value)
        walk(data)
        return '<script type="application/ld+json">' + jsonld(data) + '</script>'
    return re.sub(r'<script(?![^>]*\bid=)[^>]*type="application/ld\+json"[^>]*>(.*?)</script>', fix, source, flags=re.S)


def source_links(urls):
    urls = list(dict.fromkeys(urls))
    return '<p class="evidence-note">확인자료: ' + ' · '.join(f'<a href="{e(safe_url(u))}" rel="noopener">출처 {i+1}</a>' for i, u in enumerate(urls)) + '</p>' if urls else ''


def section(item):
    out = '<section><h3>' + e(item['heading']) + '</h3>'
    out += ''.join('<p>' + e(x) + '</p>' for x in item.get('paragraphs', []))
    if item.get('bullets'):
        out += '<ul>' + ''.join('<li>' + e(x) + '</li>' for x in item['bullets']) + '</ul>'
    return out + source_links(item.get('source_urls', [])) + '</section>'


def intent_block(label, facility=False, links=None, draft=None):
    if draft:
        lead = draft['lead']
    elif facility:
        lead = f'{label}에서 가족장이나 무빈소를 검토할 때는 먼저 시설의 접수 조건을 확인하세요. 이 안내는 해당 시설의 무빈소 허용이나 빈소 예약 가능 여부를 보장하지 않습니다.'
    else:
        lead = f'{label}에서 가족장·무빈소를 준비한다면 조문객 범위와 빈소 사용 여부를 먼저 정한 뒤, 실제 이용할 시설의 조건을 각각 확인하세요.'
    out = f'<section class="family-nohall-guide"><h2>{e(label)} 가족장·무빈소, 무엇부터 확인할까요?</h2><p>{e(lead)}</p>'
    if draft and draft.get('current_address'):
        out += '<p><strong>공식 안내 주소:</strong> ' + e(draft['current_address']) + '</p>'
        if draft.get('address_note'):
            out += '<p class="evidence-note">' + e(draft['address_note']) + '</p>'
    out += '<div class="intent-grid"><article class="intent-card"><h3>가족장: 가족의 모임 방식부터</h3><ul><li>참석할 가족·친지와 조문객 범위를 정합니다.</li><li>작은 빈소의 실제 수용 인원과 이용 시간을 확인합니다.</li><li>음식·접객 최소 주문 조건과 시설 이용료를 따로 확인합니다.</li></ul><a href="/family.html">가족장 준비 안내</a></article>'
    out += '<article class="intent-card"><h3>무빈소: 시설의 접수 조건부터</h3><ul><li>일반 조문용 빈소 없이 안치·입관·발인이 가능한지 묻습니다.</li><li>안치실·입관실 사용 조건과 가족의 작별 공간을 확인합니다.</li><li>화장 예약과 이송·발인 시간을 함께 조율합니다.</li></ul><a href="/nobinso.html">무빈소 절차 안내</a></article></div>'
    out += '<p><strong>비용을 한 금액으로 합쳐 단정하지 않습니다.</strong> 다함상조 상품비와 장례식장 사용료·음식비·화장료·장지비는 구분해서 확인해야 합니다. 시설별 금액과 무빈소 가능 여부는 확인 전까지 미확인입니다.</p>'
    if draft:
        replaced = {s['heading'] for s in draft.get('replace_sections', [])}
        out += ''.join(section(s) for s in draft.get('sections', []) if s['heading'] not in replaced)
        if draft.get('faqs'):
            out += '<section><h3>자주 확인하는 질문</h3>'
            for q in draft['faqs']:
                out += f'<details><summary>{e(q["question"])}</summary><p>{e(q["answer"])}</p>{source_links(q.get("source_urls", []))}</details>'
            out += '</section>'
        out += '<p class="evidence-note">자료 확인일: ' + e(draft.get('checked_at', '2026-10-31')[:10]) + ' · 실제 운영·예약·요금은 이용 전 재확인하세요.</p>'
        out += '<p class="evidence-note">' + e(draft.get('publisher_disclosure', '다함상조가 작성한 장례 준비 안내이며 시설의 공식 홈페이지가 아닙니다.')) + '</p>'
        if draft.get('related_links'):
            out += '<div class="intent-links">' + ''.join(f'<a href="/{e(x["href"].lstrip("/"))}">{e(x["label"])}</a>' for x in draft['related_links']) + '</div>'
    if links:
        out += '<h3>원자료와 연결된 시설별 안내</h3><p class="evidence-note">시설명과 원자료 주소가 이 지역 페이지에 함께 수록된 기록만 연결합니다. 협약 또는 무빈소 이용 가능 시설을 뜻하지 않습니다.</p><div class="intent-links">'
        out += ''.join(f'<a href="/{e(p)}">{e(n)}</a>' for n, p in links) + '</div>'
    out += '<div class="intent-links"><a href="/funeral-halls/">전국 장례식장 원자료 목록</a><a href="/area-funeral-seo-hub.html">시·군·구별 안내</a><a href="/funeral-cost-calculator.html">항목별 예상비용 확인</a></div></section>'
    return out


def apply_draft(source, draft):
    if not draft:
        return source
    source = metadata(source, draft['title'], draft['description'])
    if draft.get('h1'):
        source = re.sub(r'<h1\b[^>]*>.*?</h1>', lambda m: '<h1>' + e(draft['h1']) + '</h1>', source, count=1, flags=re.S)
    for item in draft.get('replace_sections', []):
        heading = item['match_heading']
        pattern = r'<section\b[^>]*>\s*<h2[^>]*>(?:' + re.escape(heading) + '|' + re.escape(item['heading']) + r')</h2>.*?</section>'
        if len(re.findall(pattern, source, re.S)) != 1:
            raise ValueError('Replacement section must identify exactly one section: ' + heading)
        rendered = section(item).replace('<section>', '<section class="panel">', 1).replace('<h3>', '<h2>', 1).replace('</h3>', '</h2>', 1)
        source = re.sub(pattern, lambda m: rendered, source, flags=re.S)
    source = re.sub(r'<script id="family-nohall-faq" type="application/ld\+json">.*?</script>\n?', '', source, flags=re.S)
    if draft.get('faqs'):
        faq = {'@context':'https://schema.org','@type':'FAQPage','mainEntity':[{'@type':'Question','name':q['question'],'acceptedAnswer':{'@type':'Answer','text':q['answer']}} for q in draft['faqs']]}
        block = '<script id="family-nohall-faq" type="application/ld+json">' + jsonld(faq) + '</script>\n'
        source = source.replace('</head>', block + '</head>', 1)
    return source


def dir_path(number):
    return 'funeral-halls/index.html' if number == 1 else f'funeral-halls/page-{number}.html'


def dir_url(number):
    return BASE + ('funeral-halls/' if number == 1 else dir_path(number))


def pagination(number, total):
    return '<nav class="pagination" aria-label="장례식장 목록 페이지">' + ''.join(f'<a href="{dir_url(i)}"' + (' aria-current="page"' if i == number else '') + f'>{i}</a>' for i in range(1, total+1)) + '</nav>'


def card(row, evidence, holds, photos, pilots=()):
    ident = facility_id(row); ev = evidence.get(ident, {}); alias = ev.get('display_name_review', {})
    name = alias.get('display_name', row['fcltNm']); current = ev.get('current_info_review', {})
    out = f'<article class="hall-card" id="{ident}" data-facility-id="{ident}"><p class="locality">원자료 구분: {e(row["ctpv"])} · {e(row["sigungu"])}</p><h2>{e(name)}</h2>'
    if name != row['fcltNm']:
        out += f'<p class="record-note">원자료 명칭: {e(row["fcltNm"])}</p>' + source_links(alias.get('sources', []))
    if ident in photos:
        out += figure(photos[ident])
    else:
        out += '<p class="record-note">실제 시설 사진 확인 중</p>'
    out += f'<dl><dt>원자료 주소</dt><dd>{e(row["addr"])}</dd></dl>'
    if current.get('address_unconfirmed') or current.get('suppress_phone') or current.get('homepage_invalid') or current.get('secondary_source_variance'):
        out += '<p class="status-note">출처 사이에 주소·연락처 또는 명칭 차이가 있어 재확인이 필요합니다. 원자료를 자동으로 수정하지 않았으며 확인되지 않은 전화 연결은 제공하지 않습니다.</p>' + source_links(current.get('sources', []))
    if ident in holds:
        out += '<p class="status-note">시설 식별 또는 운영 상태 재확인 대상입니다. 현재 이용 가능한 장례식장으로 추천하지 않습니다.</p>'
        notice = ev.get('public_notice')
        if notice:
            out += '<p class="status-note">' + e(notice['text']) + '</p>' + source_links([notice['source_url']])
    else:
        out += '<p class="record-note">수집된 원자료의 기록입니다. 현재 운영·예약·요금·무빈소 가능 여부는 별도 확인이 필요합니다.</p>'
    for p in ev.get('pages', []):
        if ident not in holds or p['page_kind'] == 'status':
            label = '운영상태 확인 안내' if p['page_kind'] == 'status' else '가족장·무빈소 준비와 시설별 안내'
            out += f'<a class="detail-link" href="/{e(p["page"])}">{label} →</a>'
    if ident in pilots:
        out += f'<a class="detail-link" href="/funeral-halls/{ident}.html">시설별 원자료·확인사항 →</a>'
    return out + '</article>'


def directory(number, chunks, raw, evidence, holds, photos, province_pages, pilots=()):
    rows = chunks[number-1]; total = len(chunks)
    start = (number-1)*PAGE_SIZE+1; end = start+len(rows)-1
    title = f'전국 장례식장 목록 {number}/{total} · 원자료 {start}–{end}번 | 다함상조'
    desc = f'{rows[0]["ctpv"]} {rows[0]["sigungu"]}부터 {rows[-1]["ctpv"]} {rows[-1]["sigungu"]}까지 수집된 장례식장 {len(rows)}개 기록. 시설별 가족장·무빈소 준비 안내와 현재 운영 확인 항목을 구분합니다.'
    schema = {'@context': 'https://schema.org', '@type': 'CollectionPage', 'url': dir_url(number), 'name': title, 'description': desc, 'inLanguage': 'ko-KR'}
    out = f'<!doctype html><html lang="ko"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{e(title)}</title><meta name="description" content="{e(desc)}"><meta name="robots" content="index,follow,max-snippet:-1"><meta name="daham-directory" content="source-records"><link rel="canonical" href="{dir_url(number)}"><meta property="og:type" content="website"><meta property="og:title" content="{e(title)}"><meta property="og:description" content="{e(desc)}"><meta property="og:url" content="{dir_url(number)}"><meta name="twitter:card" content="summary"><link rel="icon" href="{BASE}favicon.png"><link rel="stylesheet" href="/assets/family-nohall-guide.css"><script src="/assets/funeral-hall-directory.js" defer></script><script type="application/ld+json">{jsonld(schema)}</script></head><body class="directory-page"><header class="directory-hero"><div class="directory-wrap"><a href="/">다함상조</a> / <a href="/area-funeral-seo-hub.html">지역별 안내</a><h1>전국 장례식장 원자료 목록</h1><p>가족장·무빈소를 준비할 때, 시설의 이름보다 실제 이용 조건부터 확인하세요.</p><p>목록 {number}/{total} · {start}–{end}번 기록</p></div></header><main class="directory-wrap">'
    out += f'<section><h2>목록의 기준과 확인 범위</h2><p>전국 장사시설 공공데이터 수집본 {raw["count"]:,}개 기록을 보여 드립니다. 수집 시각은 {e(raw["updatedAt"])}이며, 개별 시설의 정보 확인일이나 실시간 운영 현황을 뜻하지 않습니다. 옛 행정구역 명칭은 원자료 표기로 남아 있을 수 있습니다.</p><p>이 목록은 다함상조 협약 시설 목록이 아닙니다. 무빈소 가능 여부·시설비·예약 상황을 보장하지 않으며, 확인되지 않은 시설 사진과 가격은 만들지 않습니다. 원자료에만 있는 시설은 상세 안내를 검증한 뒤 별도 페이지로 연결합니다.</p><p><a href="/family.html">가족장 준비</a> · <a href="/nobinso.html">무빈소 준비</a> · <a href="/funeral-cost-calculator.html">항목별 비용 확인</a></p></section>'
    out += '<h2>원자료 시·도별 시작 페이지</h2><nav class="directory-index" aria-label="원자료 시도별 목록">' + ''.join(f'<a href="{dir_url(n)}#{fid}">{e(prov)}</a>' for prov, (n, fid) in province_pages.items()) + '</nav>'
    out += '<section><h2>이 페이지에서 찾기</h2><label for="hall-filter">시설명·주소 검색</label><input id="hall-filter" type="search" placeholder="예: 인천의료원, 송파" autocomplete="off"><p id="filter-status" role="status" aria-live="polite">검색은 현재 페이지의 기록을 필터링합니다. 전국 탐색은 지역·페이지 링크를 이용하세요.</p><noscript><p>자바스크립트 없이도 모든 기록과 상세 안내·페이지 링크를 볼 수 있습니다. 브라우저의 페이지 내 찾기를 이용하세요.</p></noscript></section>'
    out += pagination(number, total) + '<div class="hall-grid">' + ''.join(card(r, evidence, holds, photos, pilots) for r in rows) + '</div>' + pagination(number, total)
    out += '</main><footer><div class="directory-wrap"><strong>다함상조</strong> · <a href="tel:16006131">24시간 상담 1600-6131</a><p>장례식장 운영 주체와 다함상조는 구분됩니다. 실제 시설 사용 조건은 해당 시설에서 확인하세요.</p></div></footer></body></html>\n'
    out = out.replace('</head>', '<!-- data-daham-seo-automation="1": managed by scripts/build_family_nohall_seo.py -->\n</head>', 1)
    return repair_photo_page(out, dir_url(number), {'facility_id':None,'photo':None,'directory':True})[0]


def provisional_page(row, raw, ev, photo, draft=None):
    """One identity/canonical; text quality and photo rights are separate gates."""
    ident = facility_id(row); path = f'funeral-halls/{ident}.html'; url = BASE + path
    alias = ev.get('display_name_review', {}); name = alias.get('display_name', row['fcltNm'])
    title = f'{name} 원자료와 가족장·무빈소 확인사항 | 다함상조'
    desc = f'{row["ctpv"]} {row["sigungu"]} 원자료에 수록된 {name}의 주소·시설 항목과 가족장·무빈소 상담 전 확인할 질문입니다. 현재 운영·이용 조건은 별도 확인이 필요합니다.'
    schema = {'@context':'https://schema.org','@type':'WebPage','url':url,'name':title,'description':desc,'inLanguage':'ko-KR'}
    out = f'<!doctype html><html lang="ko"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{e(title)}</title><meta name="description" content="{e(desc)}"><meta name="robots" content="noindex,follow"><meta name="daham-facility-id" content="{ident}"><meta name="daham-content-status" content="source-record-review-pending"><link rel="canonical" href="{url}"><meta property="og:type" content="website"><meta property="og:title" content="{e(title)}"><meta property="og:description" content="{e(desc)}"><meta property="og:url" content="{url}"><link rel="icon" href="{BASE}favicon.png"><link rel="stylesheet" href="/assets/family-nohall-guide.css"><script type="application/ld+json">{jsonld(schema)}</script></head><body class="directory-page"><header class="directory-hero"><div class="directory-wrap"><a href="/">다함상조</a> / <a href="/funeral-halls/">장례식장 목록</a><h1>{e(name)}</h1><p>{e(row["ctpv"])} · {e(row["sigungu"])} 원자료와 가족장·무빈소 확인사항</p></div></header><main class="directory-wrap">'
    eligible = bool(draft and draft.get('index_candidate'))
    if eligible:
        out += '<p class="status-note">공식 자료를 바탕으로 시설별 준비 질문을 정리했습니다. 공개 시설 정보는 현재 빈소 예약·무빈소 허용·다함상조와의 제휴를 보장하지 않습니다.</p>'
    else:
        out += '<p class="status-note"><strong>시설별 정보 보강 중</strong> · 확인된 출처와 수집된 원자료를 구분해 안내합니다. 현재 운영·예약·무빈소 허용이나 다함상조와의 제휴를 뜻하지 않습니다.</p>'
    if draft:
        out += intent_block(name, facility=True, draft=draft)
    out += '<section class="hall-card"><h2>이 시설을 구분하는 원자료</h2><dl>'
    fields = [('원자료 시설명','fcltNm'),('원자료 주소','addr'),('원자료 시·도','ctpv'),('원자료 시·군·구','sigungu'),('원자료 시설 유형','gubun'),('원자료 운영 형태','operType'),('원자료 빈소 수','mtaCnt'),('원자료 안치 수','ehrCnt'),('원자료 주차대수','tpkct')]
    out += ''.join(f'<dt>{e(label)}</dt><dd>{e(row.get(key) or "미수록·확인 필요")}</dd>' for label,key in fields)
    out += '</dl><p>빈소·안치·주차 숫자는 원자료 값이며 현재 공실·예약 가능 인원·무료 주차 조건이 아닙니다. 옛 구명이나 주소가 남아 있을 수 있어 시설의 최신 안내와 대조해야 합니다.</p>'
    if name != row['fcltNm']:
        out += '<p>표시명은 별도 확인자료를 기준으로 하되 원자료 명칭을 함께 보존합니다. 법인 승계나 현재 운영을 보증하는 표시가 아닙니다.</p>' + source_links(alias.get('sources', []))
    out += f'<p class="record-note">수집 시각: {e(raw["updatedAt"])}. 개별 시설 정보의 유효일 또는 현재 운영 확인일이 아닙니다.</p><p><a href="/data/funeral-halls.json">수집된 전국 장사시설 원자료 JSON</a></p></section>'
    out += '<section class="family-nohall-guide"><h2>이름이 비슷한 시설과 혼동하지 않으려면</h2>'
    out += f'<p>문의할 때 <strong>{e(name)}</strong>이라는 이름뿐 아니라 <strong>{e(row["addr"])}</strong> 주소를 함께 대조하세요. 병원 본관과 장례식장 출입구가 다를 수 있으며, 비슷한 이름의 다른 지역 시설 사진을 같은 시설로 보지 마세요.</p>'
    out += '<h3>시설에 확인할 질문</h3><ul><li>현재 장례식장 운영 여부와 고인 안치 가능 여부</li><li>가족 인원에 맞는 빈소의 실제 면적·이용 시간·최소 계약 조건</li><li>일반 조문용 빈소 없이 안치·입관·가족 작별·발인을 진행할 수 있는지</li><li>안치실·입관실·음식·화장·장지 비용 중 포함·별도·미확정 항목</li><li>출입 위치, 주차 등록과 차량 이송·발인 동선</li></ul><p>답변을 확인하기 전에는 가능 여부를 추정하거나 미공개 요금을 0원으로 처리하지 않습니다.</p></section>'
    if not draft:
        out += intent_block(name, facility=True)
    out += '<section class="family-nohall-guide"><h2>정리한 조건으로 장례 상담을 이어가세요</h2><p>참석할 가족 수, 조문을 받을지, 빈소를 사용할지와 고인이 계신 곳을 정리해 알려주세요. 시설의 답변과 다함상조 상품의 포함 범위를 나누어 필요한 절차와 비용 항목을 함께 점검합니다.</p><div class="intent-links"><a href="tel:16006131">다함상조 24시간 상담 1600-6131</a><a href="/consult.html">조건 정리 후 상담하기</a><a href="/funeral-cost-calculator.html">항목별 예상비용 확인</a></div></section>'
    out += '</main><footer><div class="directory-wrap"><p>다함상조가 작성한 원자료 안내입니다. 해당 시설의 공식 홈페이지가 아닙니다.</p><a href="/funeral-halls/">장례식장 목록으로</a> · <a href="tel:16006131">다함상조 상담 1600-6131</a></div></footer></body></html>\n'
    out = out.replace('</head>', '<!-- data-daham-seo-automation="1": managed by scripts/build_family_nohall_seo.py -->\n</head>',1)
    if draft:
        out = apply_draft(out,draft)
    if eligible:
        out = meta(out,'robots','index,follow,max-image-preview:large')
        out = meta(out,'daham-content-status','source-reviewed-text-guide')
    return repair_photo_page(out, url, {'facility_id':ident,'photo':photo,'directory':False})[0]


def build(root=ROOT):
    root = Path(root); inputs = load_inputs(root); raw, records, evidence, pages, holds = inputs
    photos = load_photos(root, inputs)
    pilot_data = json.loads((root/'data/funeral-hall-page-pilot.json').read_text())
    initial_pilots = pilot_data['facility_ids']
    additional_photo_pilots = pilot_data.get('additional_photo_facility_ids', [])
    pilots = initial_pilots + additional_photo_pilots
    if len(initial_pilots) != 8 or len(set(pilots)) != len(pilots) or any(i not in records or i in holds or evidence.get(i,{}).get('pages') for i in pilots):
        raise ValueError('The first eight provisional facility pages require unique, non-held source identities without an existing canonical')
    reviews = json.loads((root/'data/funeral-hall-content-reviews.json').read_text())['entries']
    review_map = {x['facility_id']:x for x in reviews}
    if len(review_map) != len(reviews) or set(review_map) != set(pilots):
        raise ValueError('Every new pilot requires one explicit content quality review')
    for ident, review in review_map.items():
        if review['identity_key'] != identity_key(records[ident]) or review['page'] != f'funeral-halls/{ident}.html' or review['canonical'] != BASE+review['page']:
            raise ValueError('New content review changed exact facility/canonical')
        if review.get('index_candidate'):
            # Photographs are intentionally NOT a text-index prerequisite.
            if (review.get('quality_recommendation') != 'eligible_for_text_review' or len(review.get('sections',[])) < 3
                    or not review.get('evidence') or not review.get('quality_reasons') or not review.get('unconfirmed')
                    or len(' '.join(p for s in review['sections'] for p in s.get('paragraphs',[]))) < 500):
                raise ValueError('Insufficient unique, sourced facility content for indexing')
        for ev in review.get('evidence',[]):
            safe_url(ev['url'])
            if not ev.get('supported_facts') or not ev.get('checked_at'): raise ValueError('Unsubstantiated facility source')
    drafts_path = root / 'data/family-nohall-content.json'
    drafts = json.loads(drafts_path.read_text()) if drafts_path.exists() else {'entries': []}
    draft_map = {x['page']: x for x in drafts['entries']}
    if len(draft_map) != len(drafts['entries']): raise ValueError('Duplicate content canonical')
    regions = json.loads((root / 'data/regional-image-registry.json').read_text())['entries']
    region_pages = {r['page']: r for r in regions}
    transitions = {x['page']: x for x in json.loads((root / 'data/regional-administrative-transitions.json').read_text())['entries']}
    if set(draft_map) - set(pages) - set(region_pages): raise ValueError('Content draft targets a new/unverified URL')
    for page, draft in draft_map.items():
        if draft.get('canonical') != BASE + page: raise ValueError('Content draft changes canonical')
        if page in pages and (draft.get('facility_id') != pages[page] or draft.get('identity_key') != identity_key(records[pages[page]])):
            raise ValueError('Curated content refers to a different facility')
    outputs = {}; links_by_id = {i: ev.get('pages', []) for i, ev in evidence.items()}
    for page, entry in region_pages.items():
        source = (root / page).read_text()
        # Replace only the exact old generated boilerplate; retain original local
        # records, bespoke guidance, cost panels and all approved artwork.
        old_generic = (r'<section class="panel"><h2>[^<]+ 가족장·무빈소 상담</h2>'
                       r'<p>가족장은 가까운 가족·친지 중심으로 빈소를 운영하고, 무빈소는 일반 조문용 빈소 없이 안치·입관·발인·화장 절차 중심으로 진행합니다. 시설별 허용 조건이 다르므로 예약 전에 확인해야 합니다.</p>.*?</section>')
        source = re.sub(old_generic, '', source, flags=re.S)
        content = re.sub(re.escape(BEGIN) + '.*?' + re.escape(END), '', source, flags=re.S)
        text = plain(content); linked = []
        for ident, row in records.items():
            if ident in holds: continue
            if row['fcltNm'] in text and row['addr'] in text:
                for p in links_by_id.get(ident, []):
                    if p['page_kind'] == 'primary': linked.append((row['fcltNm'], p['page']))
        draft = draft_map.get(page); label = draft.get('label') if draft else transitions.get(page, {}).get('historical_label', entry['region_label'])
        source = apply_draft(source, draft)
        outputs[page] = css(put_block(source, intent_block(label, links=linked, draft=draft)))
    for page, ident in pages.items():
        source = (root / page).read_text()
        ev = evidence[ident]; row = records[ident]; draft = draft_map.get(page)
        name = ev.get('display_name_review', {}).get('display_name', row['fcltNm'])
        source = meta(css(source), 'daham-facility-id', ident)
        if ident not in holds:
            title = f'{name} 가족장·무빈소 준비 | 비용·이용 확인 | 다함상조'
            desc = f'{name}에서 가족장·무빈소를 검토할 때 확인할 시설 이용 조건, 안치·입관·발인 절차와 비용 항목을 안내합니다. 실제 접수·예약·무빈소 가능 여부는 시설 확인이 필요합니다.'
            source = metadata(source, title, desc)
            source = apply_draft(source, draft)
            source = put_block(source, intent_block(name, facility=True, draft=draft))
        source, _ = repair_photo_page(source, BASE + page, {'facility_id': ident, 'photo': photos.get(ident), 'directory': False})
        outputs[page] = source
    aliases = load_aliases(root)
    for alias in aliases:
        page, ident, target = alias['page'], alias['facility_id'], alias['canonical_page']
        source = (root / page).read_text()
        source = source.replace(BASE + page, BASE + target)
        source = meta(css(source), 'daham-facility-id', ident)
        source, _ = repair_photo_page(source, BASE + page, {'facility_id': ident, 'photo': photos.get(ident), 'directory': False})
        if 'data-canonical-guide="1"' not in source:
            source = source.replace('<main', '<p data-canonical-guide="1" class="photo-pending">같은 장례식장의 안내를 <a href="/'+target+'">기존 대표 페이지</a>에서 함께 확인할 수 있습니다.</p><main', 1)
        outputs[page] = source
    rows = sorted(raw['items'], key=lambda r: tuple(r[k] for k in ('ctpv','sigungu','fcltNm','addr')))
    chunks = [rows[n:n+PAGE_SIZE] for n in range(0, len(rows), PAGE_SIZE)]
    province_pages = {}
    for n, row in enumerate(rows): province_pages.setdefault(row['ctpv'], (n//PAGE_SIZE+1, facility_id(row)))
    for number in range(1, len(chunks)+1):
        outputs[dir_path(number)] = directory(number, chunks, raw, evidence, holds, photos, province_pages, pilots)
    for ident in pilots:
        outputs[f'funeral-halls/{ident}.html'] = provisional_page(records[ident], raw, evidence.get(ident,{}), photos.get(ident),review_map.get(ident))
    allocation = []
    for ident, row in sorted(records.items()):
        existing = evidence.get(ident,{}).get('pages', [])
        page = existing[0]['page'] if existing else f'funeral-halls/{ident}.html'
        text_eligible = bool(review_map.get(ident,{}).get('index_candidate'))
        state = 'existing_canonical' if existing else ('source_reviewed_text_pilot' if text_eligible else ('source_record_pilot_noindex' if ident in pilots else 'planned_not_published'))
        allocation.append({'facility_id':ident,'identity_key':identity_key(row),'page':page,'canonical':BASE+page,'publication_state':state,'indexable':bool(existing) or text_eligible,'verification_hold':ident in holds,'photo_status':'accepted' if ident in photos else 'pending','index_quality_gate':{'unique_source_identity':True,'existing_index_status_preserved':bool(existing),'independent_current_source_content_review':'curated_pilot' if page in draft_map or text_eligible else 'pending','text_quality_candidate':text_eligible,'publication_requires_exact_commit_browser_and_visual_review':True,'missing_photo_is_not_an_automatic_noindex_reason':True}})
    outputs['data/funeral-hall-page-plan.json'] = json.dumps({'schema_version':1,'note':'One canonical per exact facility identity. Planned paths are not published. Meaningful source-reviewed text may qualify independently of photographs; weak or unresolved pages remain noindex. Exact-commit browser and visual review are release gates.','entries':allocation},ensure_ascii=False,indent=2)+'\n'
    for page in ('funeral-hospital-guide.html', 'area-funeral-seo-hub.html'):
        source = outputs.get(page, (root / page).read_text())
        content = '<section class="family-nohall-guide"><h2>가족장·무빈소, 시설별로 확인하세요</h2><p>지역별 준비 안내와 실제 장례식장 기록을 구분했습니다. 시설명·주소·운영 상태를 확인하고, 해당 시설에서 무빈소 또는 작은 빈소 이용이 가능한지 직접 확인하세요.</p><div class="intent-links"><a href="/funeral-halls/">전국 장례식장 원자료 목록</a><a href="/family.html">가족장 준비</a><a href="/nobinso.html">무빈소 준비</a></div></section>'
        if page == 'area-funeral-seo-hub.html':
            regional_links = ''.join('<a href="/'+d['page']+'">'+escape(d['label'])+' 가족장·무빈소</a>' for d in drafts['entries'] if d.get('kind') == 'regional')
            content += '<section class="family-nohall-guide"><h2>지역별 가족장·무빈소 준비</h2><div class="intent-links">'+regional_links+'</div></section>'
        outputs[page] = css(put_block(source, content))
    tree = ET.parse(root / 'sitemap.xml'); uris = {u.find('{*}loc').text: u for u in tree.getroot().findall('{*}url')}
    for entry in regions:
        url = BASE + entry['page']
        if url not in uris:
            node = ET.SubElement(tree.getroot(), '{'+SM+'}url')
            ET.SubElement(node, '{'+SM+'}loc').text = url
            uris[url] = node
        node = uris[url]
        for image in node.findall('{'+IM+'}image'): node.remove(image)
        ET.SubElement(ET.SubElement(node, '{'+IM+'}image'), '{'+IM+'}loc').text = BASE + entry['asset_path']
    for number in range(1, len(chunks)+1):
        url = dir_url(number)
        if url not in uris:
            node = ET.SubElement(tree.getroot(), '{'+SM+'}url'); ET.SubElement(node, '{'+SM+'}loc').text = url; uris[url] = node
    for alias in aliases:
        if BASE + alias['page'] in uris:
            tree.getroot().remove(uris.pop(BASE + alias['page']))
    for page, ident in pages.items():
        node = uris[BASE + page]
        for x in node.findall('{'+IM+'}image'): node.remove(x)
        if ident in photos:
            ET.SubElement(ET.SubElement(node, '{'+IM+'}image'), '{'+IM+'}loc').text = BASE + photos[ident]['asset_path']
    for ident, review in review_map.items():
        url = BASE+review['page']
        if review.get('index_candidate'):
            if url not in uris:
                node=ET.SubElement(tree.getroot(),'{'+SM+'}url'); ET.SubElement(node,'{'+SM+'}loc').text=url; uris[url]=node
            node=uris[url]
            for x in node.findall('{'+IM+'}image'):node.remove(x)
            if ident in photos:ET.SubElement(ET.SubElement(node,'{'+IM+'}image'),'{'+IM+'}loc').text=BASE+photos[ident]['asset_path']
        elif url in uris:
            tree.getroot().remove(uris[url])
    ET.register_namespace('', SM); ET.register_namespace('image', IM)
    outputs['sitemap.xml'] = ET.tostring(tree.getroot(), encoding='unicode', xml_declaration=True)
    new_indexable=sum(bool(r.get('index_candidate')) for r in reviews)
    stats = {'schema_version':1, 'regional_canonical_pages':len(regions), 'existing_facility_pages':len(pages), 'primary_facility_pages':sum(ident not in holds for ident in pages.values()), 'directory_source_records':len(records), 'directory_pages':len(chunks), 'new_source_reviewed_index_candidates':new_indexable, 'new_individual_noindex_pilots':len(pilots)-new_indexable, 'planned_unpublished_facility_pages':len(records)-len(set(pages.values()))-len(pilots), 'accepted_actual_photos':len(photos), 'photo_pending_records':len(records)-len(photos), 'held_records':len(holds), 'curated_content_pages':len(drafts['entries'])+len(reviews), 'raw_source_sha256':hashlib.sha256((root/'data/funeral-halls.json').read_bytes()).hexdigest(), 'note':'Regional URL count is not a count of current municipalities. Text quality is reviewed independently of photographs; release requires actual browser CI and visual review. Existing keyword-combination pages remain noindex.'}
    outputs['data/family-nohall-coverage.json'] = json.dumps(stats, ensure_ascii=False, indent=2)+'\n'
    return outputs, stats


def main():
    parser = argparse.ArgumentParser(); parser.add_argument('--write', action='store_true'); parser.add_argument('--check', action='store_true'); args = parser.parse_args()
    outputs, stats = build(); changed = []
    for name, content in outputs.items():
        path = ROOT / name
        if not path.exists() or path.read_text() != content:
            changed.append(name)
            if args.write:
                path.parent.mkdir(parents=True, exist_ok=True); path.write_text(content)
    print(json.dumps({'stats':stats,'changed':len(changed),'files':changed}, ensure_ascii=False))
    if args.check and changed: raise SystemExit(1)


if __name__ == '__main__': main()
