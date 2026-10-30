"""Approved historical-to-current guidance for four Incheon legacy URLs only.

This transformation does not rename URLs, rewrite source facility addresses,
change prices/phones, select images, or touch the excluded noindex migration.
Apply before image repair in generators; safe to apply repeatedly after repair.
"""
from __future__ import annotations

import json
from html import escape, unescape
from pathlib import Path
import re
from urllib.parse import urlparse

from regional_image_registry import BASE, ROOT, Tags, set_attributes

DATA_PATH = 'data/regional-administrative-transitions.json'
TARGET_PAGES = frozenset({
    'area-incheon-jung-funeral.html',
    'area-incheon-region-09f17808-funeral.html',
    'area-incheon-region-8fb2ce5a-funeral.html',
    'area-incheon-seogu-funeral.html',
})
EXCLUDED_PAGE = 'area-incheon-junggu-funeral.html'
ADDRESS_LABEL = '원자료 주소(개편 전 구명 표기)'
PANEL_START = '<!-- regional-administrative-transition:start -->'
PANEL_END = '<!-- regional-administrative-transition:end -->'


def load_transitions(root=None):
    data = json.loads((Path(root or ROOT) / DATA_PATH).read_text(encoding='utf-8'))
    if data.get('schema_version') != 1 or data.get('effective_date') != '2026-07-01':
        raise ValueError('Unsupported administrative transition data')
    entries = data['entries']
    if len(entries) != 4 or {entry['page'] for entry in entries} != TARGET_PAGES:
        raise ValueError('Administrative transitions must target exactly the four approved URLs')
    if data.get('excluded_pages') != [EXCLUDED_PAGE]:
        raise ValueError('The noindex migration page must remain excluded')
    return data


def _facility_articles(source):
    for match in re.finditer(r'<article\b[^>]*>.*?</article>', source, flags=re.I | re.S):
        attrs = Tags(re.match(r'<[^>]+>', match[0])[0]).tags[0][1]
        if 'facility' in attrs.get('class', '').split():
            yield match[0]


def _source_address(article, old_district):
    paragraph = re.search(r'<p\b[^>]*>(.*?)</p>', article, flags=re.I | re.S)
    if not paragraph:
        return None
    text = re.sub(r'<span\b[^>]*data-historical-address="1"[^>]*>.*?</span>\s*<br\s*/?>', '',
                  paragraph[1], flags=re.I | re.S)
    text = unescape(re.sub(r'<[^>]*>', '', text)).strip()
    return text if text.startswith(f'인천광역시 {old_district} ') else None


def source_addresses(source, old_district):
    """Original decoded address strings, without the added historical label."""
    return [address for article in _facility_articles(source)
            if (address := _source_address(article, old_district)) is not None]


def _body_copy(source, entry):
    """Change region guidance text, protecting all facility facts and tag attrs."""
    protected = []
    def protect(match):
        value = match[0]
        if value.lower().startswith('<article') and _source_address(value, entry['old_district']):
            if 'data-historical-address="1"' not in value:
                value = re.sub(r'(<p\b[^>]*>)', lambda m: m[0] +
                               '<span data-historical-address="1" style="font-size:13px;font-weight:700">'
                               + ADDRESS_LABEL + '</span><br>', value, count=1, flags=re.I)
        protected.append(value)
        return f'\x00REGIONAL_TRANSITION_{len(protected)-1}\x00'
    # Protect entire cards (including all names/numbers/prices), scripts, styles,
    # and comments. Image tags/attributes remain byte-for-byte untouched.
    source = re.sub(r'<article\b[^>]*>.*?</article>|<script\b[^>]*>.*?</script>|'
                    r'<style\b[^>]*>.*?</style>|<!--.*?-->', protect, source, flags=re.I | re.S)
    parts = re.split(r'(<[^>]*>)', source)
    for i in range(0, len(parts), 2):
        text = parts[i]
        text = re.sub(re.escape(entry['old_label']) + r' 장례식장 (\d+)곳',
                      lambda m: f'{entry["historical_label"]} 원자료 장례식장 {m[1]}곳', text)
        text = text.replace(entry['old_label'], entry['historical_label'])
        for phrase in ('장례비용 확인 순서', '가족장·무빈소 상담'):
            text = text.replace(f'{entry["old_district"]} {phrase}',
                                f'옛 {entry["old_district"]} 권역 {phrase}')
        parts[i] = text
    source = ''.join(parts)
    for i, value in enumerate(protected):
        source = source.replace(f'\x00REGIONAL_TRANSITION_{i}\x00', value)
    return source


def _schema(source, title, description):
    def rewrite(match):
        attrs = Tags(match[1]).tags[0][1]
        if attrs.get('type', '').lower() != 'application/ld+json':
            return match[0]
        data = json.loads(match[2])
        changed = False
        def visit(node):
            nonlocal changed
            if isinstance(node, list):
                for value in node:
                    visit(value)
            elif isinstance(node, dict):
                types = node.get('@type', [])
                if isinstance(types, str):
                    types = [types]
                if 'WebPage' in types:
                    if node.get('name') != title or node.get('description') != description:
                        node['name'], node['description'] = title, description
                        changed = True
                for value in node.values():
                    visit(value)
        visit(data)
        if not changed:
            return match[0]
        return match[1] + json.dumps(data, ensure_ascii=False, separators=(',', ':')).replace('</', '<\\/') + match[3]
    return re.sub(r'(<script\b[^>]*>)(.*?)(</script>)', rewrite, source, flags=re.I | re.S)


def _panel(data, entry, count):
    links = ' '.join(f'<a class="btn" href="{escape(link["page"], quote=True)}">'
                     f'{escape(link["label"])} 장례안내</a>' for link in entry['current_pages'])
    return (PANEL_START + '<section class="panel" data-regional-administrative-transition="1" '
            'aria-labelledby="regional-transition-heading" style="width:calc(100% - 40px);max-width:1040px;margin:20px auto">'
            '<h2 id="regional-transition-heading">2026-07-01 행정구역 개편 안내</h2>'
            f'<p>{escape(entry["explanation"])}</p>'
            f'<p>{escape(entry["facility_note"].format(facility_count=count))}</p>'
            '<p>기존 주소로 들어오신 분을 위해 이 안내 페이지의 URL은 유지합니다. '
            '현재 구별 안내와 원자료의 옛 구명을 구분해 확인해 주세요.</p>'
            f'<div class="links">{links}</div><p><a href="{escape(data["official_source_url"], quote=True)}">'
            f'{escape(data["official_source_title"])}</a> · 확인일 {escape(data["verified_on"])}</p>'
            '</section>' + PANEL_END + '\n')


def _adjacent_reference(source, entry):
    reference = entry.get('adjacent_reference')
    if not reference:
        return source
    def update(match):
        section = match[0]
        if f'href="{reference["guide_page"]}"' not in section:
            return section
        # Retain the existing facility guide link; stop presenting it as local
        # to old Seo-gu/Seo-hae/Geomdan. The current address has a primary source.
        section = re.sub(r'<h2\b[^>]*>.*?</h2>', '<h2>인접 지역 참고: 제물포구 인천의료원</h2>',
                         section, count=1, flags=re.I | re.S)
        section = re.sub(r'<p data-adjacent-region-reference="1">.*?</p>', '', section, flags=re.S)
        paragraph = ('<p data-adjacent-region-reference="1">인천의료원은 서해구·검단구 소재 시설이 아니라 '
                     '인접 지역인 제물포구의 참고 시설입니다. 의료원 공식 안내 주소는 '
                     f'{escape(reference["address"])}입니다. '
                     f'<a href="{escape(reference["official_source_url"], quote=True)}">의료원 공식 오시는 길</a>'
                     '에서 위치를 확인하세요.</p>')
        return section.replace('</section>', paragraph + '</section>')
    return re.sub(r'<section\b[^>]*>.*?</section>', update, source, flags=re.I | re.S)


def apply_transition(source, page):
    """Return a deterministic transition view; non-target/noindex sources unchanged."""
    parsed = urlparse(str(page))
    if parsed.netloc and parsed.netloc != urlparse(BASE).netloc:
        return source
    name = parsed.path.lstrip('/')
    if name not in TARGET_PAGES:
        return source
    if any(tag == 'meta' and attrs.get('name', '').lower() == 'robots'
           and 'noindex' in attrs.get('content', '').lower() for tag, attrs in Tags(source).tags):
        return source
    data = load_transitions()
    entry = next(item for item in data['entries'] if item['page'] == name)
    addresses = source_addresses(source, entry['old_district'])
    if 'mainland_snapshot_addresses' in entry and sorted(addresses) != sorted(entry['mainland_snapshot_addresses']):
        raise ValueError('Old Jung-gu facility snapshot changed; verify mainland/island scope before regeneration')
    description = entry['description'].format(facility_count=len(addresses))
    title = entry['title']
    if len(re.findall(r'<h1\b', source, re.I)) != 1 or len(re.findall(r'<title\b', source, re.I)) != 1:
        raise ValueError('Transition requires exactly one title and H1')
    head, body = re.split(r'</head>', source, maxsplit=1, flags=re.I)
    head = re.sub(r'(<title\b[^>]*>).*?(</title>)', lambda m: m[1] + escape(title) + m[2], head, flags=re.I | re.S)
    def meta(match):
        attrs = Tags(match[0]).tags[0][1]
        key = (attrs.get('name') or attrs.get('property') or '').lower()
        if key in ('description', 'og:description', 'twitter:description'):
            return set_attributes(match[0], {'content': description})
        if key in ('og:title', 'twitter:title'):
            return set_attributes(match[0], {'content': title})
        if key == 'keywords':
            keywords = [entry['historical_label'], *(link['label'] + ' 장례안내' for link in entry['current_pages']),
                        '가족장', '무빈소', '장례비용', '행정구역 개편']
            return set_attributes(match[0], {'content': ','.join(keywords)})
        return match[0]
    head = re.sub(r'<meta\b[^>]*>', meta, head, flags=re.I | re.S)
    head = _schema(head, title, description)
    body = re.sub(re.escape(PANEL_START) + r'.*?' + re.escape(PANEL_END) + r'\n?', '', body, flags=re.S)
    body = _adjacent_reference(body, entry)
    body = _body_copy(body, entry)
    body = re.sub(r'(<h1\b[^>]*>).*?(</h1>)', lambda m: m[1] + escape(entry['h1']) + m[2], body, flags=re.I | re.S)
    def hero(match):
        return re.sub(r'(<p\b[^>]*>).*?(</p>)', lambda m: m[1] + escape(entry['intro']) + m[2],
                      match[0], count=1, flags=re.I | re.S)
    body, hero_count = re.subn(r'<header\b[^>]*>.*?</header>', hero, body, count=1, flags=re.I | re.S)
    if hero_count != 1:
        raise ValueError('Transition requires a header for the top explanatory panel')
    body = re.sub(r'<header\b', lambda m: _panel(data, entry, len(addresses)) + m[0], body, count=1, flags=re.I)
    return head + '</head>' + body
