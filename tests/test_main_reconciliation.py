import json
from pathlib import Path
import re
import sys
import unittest
import xml.etree.ElementTree as ET
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'scripts'))
import funeral_hall_photos as photos
import build_family_nohall_seo as build

NEW = ('major-hospital-funeral-guide.html','st-vincent-funeral.html','hallym-sacredheart-funeral.html','sanggye-paik-funeral.html','dongguk-ilsan-funeral.html','nowon-eulji-funeral.html','eunpyeong-stmary-funeral.html','gangnam-sacredheart-funeral.html')

class MainReconciliationTests(unittest.TestCase):
    def test_main_urls_and_candidate_urls_preserved(self):
        urls=[n.find('{*}loc').text for n in ET.parse(ROOT/'sitemap.xml').getroot()]
        self.assertEqual(len(urls),448)
        self.assertEqual(len(set(urls)),448)
        for name in NEW:
            self.assertTrue((ROOT/name).exists())
            self.assertEqual(photos.BASE+name in urls, name != 'gangnam-sacredheart-funeral.html')
        self.assertIn('2026-11-02',(ROOT/'sitemap.xml').read_text())

    def test_new_facilities_use_exact_identity_photo_policy(self):
        inputs=photos.load_inputs(ROOT)
        for name in NEW[1:]:
            source=(ROOT/name).read_text()
            ident=photos.page_identity(source)
            self.assertEqual(ident, inputs[3].get(name, 'fh-a1cdec8ec8c1f991'))
            self.assertIsNone(photos.photo_policy(source,photos.BASE+name)['photo'])
            self.assertNotIn('assets/regional-funeral-base.png',source)
            self.assertIn('data-facility-photo-pending="1"',source)

    def test_hanyang_current_body_preserved_without_reopening_claim(self):
        source=(ROOT/'hanyang-funeral-status.html').read_text()
        for phrase in ('02-2290-9442~3','서관 1층','실제 빈소 사용 가능 여부와 당일 운영상황','major-hospital-funeral-guide.html','data-facility-photo-pending="1"'):
            self.assertIn(phrase,source)
        self.assertIn('fh-2b9afdfceab26e79',photos.load_inputs(ROOT)[4])
        self.assertNotIn('다시 안내되고', source)
        self.assertIn('현재 운영 재개 여부는 별도로 확인', source)

    def test_duplicate_existing_urls_use_established_canonical(self):
        inputs=photos.load_inputs(ROOT)
        entry=inputs[2]['fh-a1cdec8ec8c1f991']
        self.assertEqual(entry['canonical_reconciliation']['status'],'consolidated_to_established_url')
        self.assertEqual(len(entry['pages']),1)
        alias = (ROOT/'gangnam-sacredheart-funeral.html').read_text()
        self.assertIn('rel="canonical" href="'+photos.BASE+'yeongdeungpo-kangnam-hallym-funeral.html"', alias)
        self.assertNotIn('http-equiv="refresh"', alias)
        self.assertIn('공식 확인 정보', (ROOT/'yeongdeungpo-kangnam-hallym-funeral.html').read_text())
        plan=json.loads((ROOT/'data/funeral-hall-page-plan.json').read_text())['entries']
        self.assertEqual(sum(x['facility_id']==entry['facility_id'] for x in plan),1)
        _,stats=build.build(ROOT)
        self.assertEqual(stats['planned_unpublished_facility_pages'],988)

    def test_guide_preserves_navigation_without_literal_separators(self):
        source=(ROOT/'funeral-hospital-guide.html').read_text()
        for name in NEW[:-1]:self.assertIn(name,source)
        self.assertIn('yeongdeungpo-kangnam-hallym-funeral.html',source)
        self.assertNotIn('\\n<a',source)
        self.assertEqual(source.count('<!-- family-nohall-guide:start -->'),1)
