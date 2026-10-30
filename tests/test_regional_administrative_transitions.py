"""Historical guidance contracts; no production writes or browser launches."""
import contextlib
import io
import json
from pathlib import Path
import re
import runpy
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import regional_administrative_transitions as transition
import regional_image_registry as registry
import repair_search_images as image_repair


ROOT = Path(__file__).resolve().parents[1]
DATA = transition.load_transitions()
ENTRIES = {entry['page']: entry for entry in DATA['entries']}
HALLS = json.loads((ROOT / 'data/funeral-halls.json').read_text())


def fixtures(entry):
    return [item for item in HALLS['items']
            if item.get('ctpv') == '인천광역시' and item.get('sigungu') == entry['old_district']]


def legacy(entry):
    rows = fixtures(entry) if 'adjacent_reference' not in entry else []
    cards = ''.join('<article class="facility"><h2>' + item['fcltNm'] + '</h2><p>' + item['addr'] +
                    '</p><dl><dt>빈소/안치</dt><dd>' + str(item.get('mtaCnt')) + '/' + str(item.get('ehrCnt')) +
                    '</dd><dt>전화</dt><dd>' + item.get('telno', '') + '</dd></dl></article>' for item in rows)
    page_url = registry.BASE + entry['page']
    schema = {'@graph': [{'@type': ['WebPage', 'CreativeWork'], 'url': page_url, 'name': '옛 제목',
                         'description': '옛 설명', 'primaryImageOfPage': {'url': 'unchanged.png', 'width': 1200}},
                        {'@type': 'FuneralHome', 'name': '고정 시설명', 'address': {'streetAddress': '인천광역시 서구 원주소'}}]}
    adjacent = ('<section><h2>인천 서구 주요 장례식장 안내</h2><p>시설료와 상품비는 별도입니다.</p>'
                '<a href="incheon-medical-center-funeral.html">인천의료원 장례 안내</a></section>') if 'adjacent_reference' in entry else ''
    return ('<!doctype html><html lang="ko"><head><title>옛 제목</title>'
            '<meta name="description" content="옛 설명"><meta property="og:title" content="옛 제목">'
            '<meta property="og:description" content="옛 설명"><meta name="twitter:title" content="옛 제목">'
            '<meta name="twitter:description" content="옛 설명"><meta name="keywords" content="옛 키워드">'
            '<meta name="robots" content="index,follow"><link rel="canonical" href="' + page_url + '">'
            '<meta property="og:url" content="' + page_url + '">'
            '<meta property="og:image" content="unchanged.png"><meta name="twitter:image" content="unchanged.png">'
            '<script type="application/ld+json">' + json.dumps(schema, ensure_ascii=False) + '</script></head>'
            '<body><strong>다함상조 ' + entry['old_label'] + ' 장례안내</strong>'
            '<header class="hero"><h1>' + entry['old_label'] + ' 장례안내</h1><p>이전 지역 안내문</p>'
            '<img src="unchanged.png" alt="' + entry['old_label'] + ' 이미지" width="1200" height="675"></header>'
            '<main><section><h2>' + entry['old_label'] + ' 장례식장 ' + str(len(rows)) + '곳</h2>' + cards + '</section>'
            '<p>무빈소 120만원, 가족장 249만원, 일반장 360만원, 프리미엄 499만원</p>'
            '<a href="tel:16006131">1600-6131</a>' + adjacent + '</main></body></html>')


def protected_tags(source):
    return [(tag, attrs) for tag, attrs in registry.Tags(source).tags
            if tag == 'img' or (tag == 'link' and attrs.get('rel') == 'canonical')
            or (tag == 'meta' and ((attrs.get('name') or attrs.get('property')) in
                                   ('robots', 'og:url', 'og:image', 'twitter:image')))]


def remove_address_labels(article):
    return re.sub(r'<span data-historical-address="1"[^>]*>.*?</span><br>', '', article)


class TransitionTests(unittest.TestCase):
    def test_exact_four_mappings_and_current_links(self):
        self.assertEqual(set(ENTRIES), transition.TARGET_PAGES)
        self.assertEqual(DATA['effective_date'], '2026-07-01')
        self.assertEqual(DATA['official_source_url'], 'https://www.incheon.go.kr/IC01070101')
        expected = {'incheon-jung': ('인천 옛 중구 권역', ['제물포구', '영종구']),
                    'incheon-region-09f17808': ('서해구·검단구', ['서해구', '검단구']),
                    'incheon-region-8fb2ce5a': ('제물포구 옛 동구 권역', ['제물포구']),
                    'incheon-seogu': ('인천 옛 서구 권역', ['서해구', '검단구'])}
        for entry in ENTRIES.values():
            self.assertEqual((entry['display_label'], [link['label'] for link in entry['current_pages']]), expected[entry['id']])
            for link in entry['current_pages']:
                self.assertTrue((ROOT / link['page']).is_file())
        self.assertEqual(DATA['excluded_pages'], ['area-incheon-junggu-funeral.html'])

    def test_preserves_facility_names_addresses_counts_prices_phones_and_images(self):
        for page, entry in ENTRIES.items():
            with self.subTest(page=page):
                before = legacy(entry)
                after = transition.apply_transition(before, page)
                self.assertEqual(protected_tags(before), protected_tags(after))
                old_cards = list(transition._facility_articles(before))
                new_cards = list(transition._facility_articles(after))
                self.assertEqual(old_cards, [remove_address_labels(card) for card in new_cards])
                self.assertEqual(transition.source_addresses(before, entry['old_district']),
                                 transition.source_addresses(after, entry['old_district']))
                expected_count = len(transition.source_addresses(before, entry['old_district']))
                self.assertEqual(after.count('data-historical-address="1"'), expected_count)
                for text in ('무빈소 120만원', '가족장 249만원', '일반장 360만원', '프리미엄 499만원',
                             'href="tel:16006131"', '1600-6131'):
                    self.assertEqual(before.count(text), after.count(text))
                self.assertIn(f'원자료 장례식장 {expected_count}곳', after) if old_cards else None

    def test_metadata_visible_guidance_schema_and_idempotence(self):
        for page, entry in ENTRIES.items():
            with self.subTest(page=page):
                after = transition.apply_transition(legacy(entry), page)
                self.assertEqual(after, transition.apply_transition(after, registry.BASE + page))
                self.assertIn('<title>' + entry['title'] + '</title>', after)
                self.assertIn('<h1>' + entry['h1'] + '</h1>', after)
                self.assertEqual(after.count('data-regional-administrative-transition="1"'), 1)
                self.assertLess(after.index(transition.PANEL_START), after.index('<header'))
                metas = {attrs.get('name') or attrs.get('property'): attrs.get('content')
                         for tag, attrs in registry.Tags(after).tags if tag == 'meta'}
                self.assertEqual(metas['description'], metas['og:description'])
                self.assertEqual(metas['description'], metas['twitter:description'])
                graph = json.loads(re.search(r'<script type="application/ld\+json">(.*?)</script>', after)[1])['@graph']
                self.assertEqual(graph[0]['name'], entry['title'])
                self.assertEqual(graph[0]['description'], metas['description'])
                self.assertEqual(graph[0]['primaryImageOfPage'], {'url': 'unchanged.png', 'width': 1200})
                self.assertEqual(graph[1], {'@type': 'FuneralHome', 'name': '고정 시설명', 'address': {'streetAddress': '인천광역시 서구 원주소'}})

    def test_no_false_one_to_one_or_island_facility_claim(self):
        jung = transition.apply_transition(legacy(ENTRIES['area-incheon-jung-funeral.html']), 'area-incheon-jung-funeral.html')
        self.assertIn('옛 중구의 내륙 지역은 옛 동구와 합쳐 제물포구', jung)
        self.assertIn('옛 중구의 섬 지역은 영종구로 분리', jung)
        self.assertIn('4곳은 모두 옛 중구 내륙 주소', jung)
        self.assertIn('영종구 시설 목록이 아닙니다', jung)
        for page in ('area-incheon-region-09f17808-funeral.html', 'area-incheon-seogu-funeral.html'):
            result = transition.apply_transition(legacy(ENTRIES[page]), page)
            self.assertIn('남쪽의 서해구와 북쪽의 검단구', result)
            self.assertIn('옛 서구 전체가 서해구로 바뀐 것으로 해석하면 안 됩니다', result)
        dong = transition.apply_transition(legacy(ENTRIES['area-incheon-region-8fb2ce5a-funeral.html']), 'area-incheon-region-8fb2ce5a-funeral.html')
        self.assertIn('옛 동구 전역은 옛 중구의 내륙 지역과 합쳐', dong)
        self.assertIn('제물포구의 일부', dong)

    def test_noindex_and_unrelated_pages_are_byte_preserved(self):
        excluded = (ROOT / transition.EXCLUDED_PAGE).read_text()
        self.assertEqual(excluded, transition.apply_transition(excluded, transition.EXCLUDED_PAGE))
        arbitrary = '<not-even-html>unchanged'
        self.assertEqual(arbitrary, transition.apply_transition(arbitrary, 'area-seoul-jung-funeral.html'))
        page = next(iter(ENTRIES))
        source = legacy(ENTRIES[page]).replace('name="robots" content="index,follow"', 'content="NOINDEX,follow" name="robots"')
        self.assertEqual(source, transition.apply_transition(source, page))
        self.assertEqual(source, transition.apply_transition(source, 'https://other.example/' + page))

    def test_changed_mainland_snapshot_fails_closed(self):
        page = 'area-incheon-jung-funeral.html'
        source = legacy(ENTRIES[page]).replace(ENTRIES[page]['mainland_snapshot_addresses'][0], '인천광역시 중구 공항로 1')
        with self.assertRaisesRegex(ValueError, 'mainland/island'):
            transition.apply_transition(source, page)

    def test_adjacent_hospital_address_has_official_source_and_old_link(self):
        page = 'area-incheon-seogu-funeral.html'
        result = transition.apply_transition(legacy(ENTRIES[page]), page)
        self.assertIn('인접 지역 참고: 제물포구 인천의료원', result)
        self.assertIn('인천광역시 제물포구 방축로 217', result)
        self.assertIn('https://www.icmc.or.kr/guide/guide1.php?msort=44&amp;tsort=4', result)
        self.assertIn('href="incheon-medical-center-funeral.html">인천의료원 장례 안내</a>', result)
        self.assertNotIn('서구 주요 장례식장 안내', result)

    def test_checked_in_pages_are_applied_and_keep_source_dataset(self):
        counts = {'중구': 4, '서구': 5, '동구': 2}
        for page, entry in ENTRIES.items():
            source = (ROOT / page).read_text()
            self.assertEqual(source, transition.apply_transition(source, page))
            if 'adjacent_reference' in entry:
                continue
            addresses = transition.source_addresses(source, entry['old_district'])
            self.assertEqual(len(addresses), counts[entry['old_district']])
            for item in fixtures(entry):
                self.assertIn(item['addr'], addresses)
                self.assertIn(item['fcltNm'], source)
                self.assertIn(item['telno'], source)

    def test_generators_call_transition_before_image_repair(self):
        for filename in ('generate_sigungu_pages.py', 'generate_priority_area_pages.py'):
            code = (ROOT / 'scripts' / filename).read_text()
            self.assertIn('from regional_administrative_transitions import apply_transition', code)
            self.assertLess(code.index('= apply_transition('), code.index(', _ = repair('))

    def test_sigungu_regeneration_carries_transition_without_writes(self):
        # Capture generated HTML in memory, with a three-group source fixture.
        subset = {**HALLS, 'items': [item for item in HALLS['items']
                  if item.get('ctpv') == '인천광역시' and item.get('sigungu') in ('중구', '서구', '동구')]}
        actual_read = Path.read_text
        outputs = {}
        repaired = []
        def read(path, *args, **kwargs):
            if path == ROOT / 'data/funeral-halls.json':
                return json.dumps(subset, ensure_ascii=False)
            return actual_read(path, *args, **kwargs)
        def write(path, value, *args, **kwargs):
            outputs[path.name] = value
            return len(value)
        def repair(source, url):
            repaired.append(url)
            self.assertIn('data-regional-administrative-transition="1"', source)
            return source, 'unchanged.png'
        with patch.object(Path, 'read_text', read), patch.object(Path, 'write_text', write), \
                patch.object(registry, 'existing_or_registered_image', return_value=registry.BASE + 'unchanged.png'), \
                patch.object(image_repair, 'repair', repair), contextlib.redirect_stdout(io.StringIO()):
            runpy.run_path(str(ROOT / 'scripts/generate_sigungu_pages.py'))
        self.assertEqual(len(repaired), 3)
        for page in set(ENTRIES) - {'area-incheon-seogu-funeral.html'}:
            self.assertIn(page, outputs)
            self.assertIn(ENTRIES[page]['h1'], outputs[page])
            self.assertEqual(outputs[page], transition.apply_transition(outputs[page], page))


if __name__ == '__main__':
    unittest.main()
