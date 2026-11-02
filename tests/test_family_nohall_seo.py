import copy
import hashlib
import json
import re
import sys
import unittest
from pathlib import Path
from unittest.mock import patch
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import funeral_hall_photos as photos
import build_family_nohall_seo as build
import repair_search_images as repair
import enrich_seo


class FamilyNoHallTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.inputs = photos.load_inputs(ROOT)

    def test_exact_source_identities(self):
        raw, records, evidence, pages, holds = self.inputs
        self.assertGreaterEqual(len(records), 1000)
        self.assertEqual(len(records), raw['count'])
        self.assertEqual(len(pages), 82)
        self.assertEqual(len(holds), 7)
        self.assertEqual(sum('display_name_review' in e for e in evidence.values()), 69)
        self.assertEqual(sum('current_info_review' in e for e in evidence.values()), 43)
        row = next(iter(records.values()))
        other = dict(row, addr=row['addr'] + ' 다른 주소')
        self.assertNotEqual(photos.facility_id(row), photos.facility_id(other))
        self.assertEqual(photos.identity_key(row), photos.identity_key(dict(row, fcltNm=' '+row['fcltNm']+' ')))

    def test_curated_content_is_exact_and_source_backed(self):
        data = json.loads((ROOT/'data/family-nohall-content.json').read_text())
        self.assertEqual(len(data['entries']), 8)
        for entry in data['entries']:
            self.assertEqual(entry['canonical'], photos.BASE + entry['page'])
            self.assertTrue(entry['evidence'])
            for evidence in entry['evidence']:
                photos.safe_url(evidence['url'])
                self.assertTrue(evidence['supported_facts'])
            source = (ROOT/entry['page']).read_text()
            self.assertIn(entry['h1'], source)
            self.assertIn('family-nohall-faq', source)
            for item in entry.get('replace_sections', []):
                self.assertNotIn('<h2>'+item['match_heading']+'</h2>', source)
                self.assertEqual(source.count(item['heading']), 1)

    def test_no_generic_ai_substitution(self):
        accepted = photos.load_photos(ROOT, self.inputs)
        for page, ident in self.inputs[3].items():
            source = (ROOT/page).read_text()
            self.assertEqual(photos.page_identity(source), ident)
            self.assertNotIn('regional-funeral-base.png', source)
            self.assertNotIn('/assets/regional/', source)
            metadata = repair.metas(source)
            if ident not in accepted:
                self.assertNotIn('og:image', metadata)
                self.assertNotIn('twitter:image', metadata)
                self.assertEqual(metadata['twitter:card'], 'summary')
                self.assertIn('실제 시설 사진 확인 중', source)
                self.assertNotIn('primaryImageOfPage', source)

    def test_directory_static_coverage_and_links(self):
        ids = []
        pages = sorted(p for p in (ROOT/'funeral-halls').glob('*.html') if not p.name.startswith('fh-'))
        self.assertEqual(len(pages), 22)
        for path in pages:
            source = path.read_text()
            self.assertIn('<noscript>', source)
            self.assertEqual(source.count('<h1>'), 1)
            ids.extend(re.findall(r'data-facility-id="([^"]+)"', source))
            for ref in re.findall(r'href="(/[^"#?]*)', source):
                target = ROOT / ref.lstrip('/')
                self.assertTrue(target.exists(), str(target))
        self.assertEqual(len(ids), self.inputs[0]['count'])
        self.assertEqual(len(set(ids)), len(ids))
        self.assertEqual(set(ids), set(self.inputs[1]))

    def test_sitemap_and_combo_index_gate(self):
        tree = ET.parse(ROOT/'sitemap.xml')
        nodes = tree.getroot().findall('{*}url')
        urls = [n.find('{*}loc').text for n in nodes]
        self.assertEqual(len(urls), len(set(urls)))
        self.assertEqual(sum('/funeral-halls/' in url for url in urls), 27)
        self.assertFalse(any('/seo-combos/' in url for url in urls))
        self.assertNotIn(photos.BASE+'area-incheon-junggu-funeral.html', urls)
        combos = list((ROOT/'seo-combos').glob('*.html'))
        self.assertEqual(len(combos), 1020)
        for path in combos:
            self.assertRegex(path.read_text(), r'name="robots"[^>]+noindex')

    def test_private_workflow_is_not_public_metadata(self):
        for name in (photos.EVIDENCE, photos.REGISTRY, 'data/family-nohall-content.json','data/funeral-hall-content-reviews.json'):
            data = (ROOT/name).read_text()
            self.assertNotRegex(data, r'(?i)/workspace/|sentinel_|generation_prompt|completion_token|library_file_id|\bparent\b')

    def test_unsafe_source_urls_rejected(self):
        for url in ('http://example.com/photo', 'https://u:p@example.com/x', 'https://x.test/a?token=private', 'javascript:alert(1)', 'https://x.test/with space','https://127.0.0.1/photo','https://localhost/photo'):
            with self.assertRaises(ValueError): photos.safe_url(url)

    def test_external_source_cannot_end_jsonld_script(self):
        row = dict(next(iter(self.inputs[1].values())))
        row['sigungu'] = '</script><script>alert(1)</script>'
        output = build.directory(1,[[row]],self.inputs[0],{}, {}, {}, {})
        self.assertNotIn('</script><script>alert(1)</script>',output)
        blocks = re.findall(r'<script[^>]*type="application/ld\+json"[^>]*>(.*?)</script>',output,re.S)
        self.assertTrue(blocks)
        for block in blocks: json.loads(block)
        self.assertIn('\\u003c/script\\u003e',output)

    def test_list_typed_and_id_bearing_schema_loses_ai_fallback(self):
        source = '<html><head><script id="page-schema" type="application/ld+json">'+json.dumps({'@type':['WebPage'],'primaryImageOfPage':{'url':'https://www.dahamsangjo.co.kr/assets/regional/a.jpg'}})+'</script></head><body><header></header></body></html>'
        output,image = photos.repair_photo_page(source,photos.BASE+'x.html',{'photo':None,'directory':False})
        self.assertNotIn('primaryImageOfPage',output)
        self.assertIn('id="page-schema"',output)
        self.assertIsNone(image)

    def test_wrong_facility_marker_rejected(self):
        page, ident = next(iter(self.inputs[3].items()))
        source = (ROOT/page).read_text().replace(ident, 'fh-0000000000000000')
        with self.assertRaises(ValueError): photos.photo_policy(source, photos.BASE+page)

    def test_photo_rights_and_identity_fail_closed(self):
        ident = next(i for i in self.inputs[1] if i not in self.inputs[4])
        base = {'facility_id':ident, 'identity_key':photos.identity_key(self.inputs[1][ident]), 'status':'accepted', 'content_kind':'actual_facility_photo', 'license':{'name':'unknown','attribution':'Unknown','commercial_use':False}}
        old_read = Path.read_text
        for changed in ({}, {'content_kind':'ai_illustration'}, {'identity_key':'different identity'}, {'facility_id':next(iter(self.inputs[4]))}):
            entry = dict(base, **changed)
            def read(path, *args, **kwargs):
                if path == ROOT/photos.REGISTRY: return json.dumps({'schema_version':1,'entries':[entry]})
                return old_read(path,*args,**kwargs)
            with patch.object(Path,'read_text',read), self.assertRaises(ValueError):
                photos.load_photos(ROOT, self.inputs)

    def test_current_medical_center_conflicting_parking_claims_removed(self):
        source = (ROOT/'incheon-medical-center-funeral.html').read_text()
        self.assertNotIn('5대까지 무료', source)
        self.assertNotIn('24시간 이내 무료', source)
        self.assertIn('공식 안내', source)

    def test_generator_is_idempotent(self):
        outputs, stats = build.build(ROOT)
        for path, content in outputs.items():
            self.assertEqual((ROOT/path).read_text(), content, path)
        self.assertEqual(stats['regional_canonical_pages'], 269)

    def test_directory_enrichment_roundtrip(self):
        for path in (ROOT/'funeral-halls').glob('*.html'):
            source = path.read_text()
            self.assertEqual(enrich_seo.process(path,False),'unchanged',str(path))
            url = photos.BASE + ('funeral-halls/' if path.name == 'index.html' else 'funeral-halls/'+path.name)
            policy=photos.photo_policy(source,url)
            self.assertEqual(photos.repair_photo_page(source,url,policy)[0],source)

    def test_one_facility_one_canonical_and_provisional_noindex(self):
        plan = json.loads((ROOT/'data/funeral-hall-page-plan.json').read_text())['entries']
        self.assertEqual(len(plan),self.inputs[0]['count'])
        self.assertEqual(len({p['canonical'] for p in plan}),len(plan))
        pilots = [p for p in plan if p['publication_state'] in ('source_record_pilot_noindex','source_reviewed_text_pilot')]
        self.assertEqual(len(pilots),10)
        self.assertEqual(sum(p['indexable'] for p in pilots),5)
        sitemap = (ROOT/'sitemap.xml').read_text()
        for item in pilots:
            source = (ROOT/item['page']).read_text()
            if not item['indexable']:
                self.assertIn('content="noindex,follow"',source)
                self.assertNotIn(item['canonical'],sitemap)
            else:
                self.assertNotIn('content="noindex,follow"',source)
                self.assertIn(item['canonical'],sitemap)
            self.assertEqual(photos.page_identity(source),item['facility_id'])
            policy = photos.photo_policy(source,item['canonical'])
            self.assertEqual(policy['facility_id'],item['facility_id'])
            self.assertIn(self.inputs[1][item['facility_id']]['addr'],source)

    def test_actual_photo_identity_scope_and_original_bytes(self):
        accepted=photos.load_photos(ROOT,self.inputs)
        self.assertEqual(len(accepted),2)
        gallery=accepted[photos.EXISTING_REUSE_ID]
        self.assertFalse(gallery['visual_review']['privacy_clear'])
        self.assertTrue(gallery['visual_review']['privacy_reviewed_for_authorized_existing_site_reuse'])
        self.assertTrue(photos.authorized_existing_site_reuse(gallery))
        self.assertFalse(photos.authorized_existing_site_reuse(dict(gallery,facility_id='fh-0000000000000000')))
        self.assertFalse(photos.authorized_existing_site_reuse(dict(gallery,asset_path='gallery8.jpg')))
        self.assertFalse(photos.authorized_existing_site_reuse(dict(gallery,sha256='0'*64)))
        self.assertEqual(hashlib.sha256((ROOT/'gallery9.jpg').read_bytes()).hexdigest(),photos.EXISTING_REUSE_SHA)
        yongin=accepted['fh-0a587ca685529890']
        self.assertEqual((yongin['width'],yongin['height']),(630,354))
        self.assertIn('2019-09-24',yongin['caption'])
        self.assertIn('촬영일 미상',yongin['caption'])
        self.assertIn('현재 모습과 다를 수',yongin['caption'])
        self.assertIn('max-width:630px',photos.figure(yongin))

    def test_accepted_directory_card_photos_survive_repair(self):
        accepted=photos.load_photos(ROOT,self.inputs)
        for ident,photo in accepted.items():
            matches=[p for p in (ROOT/'funeral-halls').glob('*.html') if not p.name.startswith('fh-') and f'data-facility-id="{ident}"' in p.read_text()]
            self.assertEqual(len(matches),1)
            source=matches[0].read_text()
            card=re.search(r'<article[^>]*data-facility-id="'+ident+r'".*?</article>',source,re.S)[0]
            self.assertEqual(card.count('data-facility-photo="1"'),1)
            self.assertIn(photos.BASE+photo['asset_path'],card)
            url=photos.BASE+str(matches[0].relative_to(ROOT))
            repaired,image=photos.repair_photo_page(source,url,photos.photo_policy(source,url))
            self.assertEqual(repaired,source)
            self.assertIsNone(image)
            self.assertNotIn('property="og:image"',source)

    def test_public_photo_metadata_rejects_private_fields(self):
        entry=next(iter(photos.load_photos(ROOT,self.inputs).values()))
        for field in ('library_file_id','download_url','local_asset_path','authorization_message_id'):
            with self.assertRaises(ValueError):photos.public_photo_metadata(dict(entry,**{field:'private'}))
            nested=copy.deepcopy(entry);nested['license'][field]='private'
            with self.assertRaises(ValueError):photos.public_photo_metadata(nested)

    def test_photo_missing_is_not_an_index_block(self):
        reviews=json.loads((ROOT/'data/funeral-hall-content-reviews.json').read_text())['entries']
        accepted=photos.load_photos(ROOT,self.inputs)
        self.assertEqual(sum(r['index_candidate'] and r['facility_id'] not in accepted for r in reviews),4)
        yongin=next(r for r in reviews if r['facility_id']=='fh-0a587ca685529890')
        self.assertFalse(yongin['index_candidate'])


if __name__ == '__main__': unittest.main()
