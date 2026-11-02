"""Four independently sourced regional additions, without replacing old artwork."""
import hashlib
import json
from pathlib import Path
import unittest
import xml.etree.ElementTree as ET
ROOT = Path(__file__).resolve().parents[1]
NEW = {'area-seoul-mapo-funeral.html','area-incheon-ongjin-funeral.html','area-gyeonggi-gwacheon-funeral.html','area-chungnam-gyeryong-funeral.html'}
class FourRegions(unittest.TestCase):
    def test_new_pages_are_individual_indexable_guides(self):
        data=json.loads((ROOT/'data/family-nohall-content.json').read_text())
        entries={e['page']:e for e in data['entries']}
        urls={n.find('{*}loc').text for n in ET.parse(ROOT/'sitemap.xml').getroot()}
        hub=(ROOT/'area-funeral-seo-hub.html').read_text()
        for page in NEW:
            self.assertIn(page,entries)
            self.assertIn('https://www.dahamsangjo.co.kr/'+page,urls)
            self.assertIn('/'+page,hub)
            self.assertIn('conversion-funnel.js',(ROOT/page).read_text())
            self.assertGreaterEqual(len(entries[page]['evidence']),3)
    def test_new_originals_have_no_private_paths_or_prompts(self):
        entries=json.loads((ROOT/'data/regional-image-registry.json').read_text())['entries']
        self.assertEqual(len(entries),273)
        for e in entries:
            if e['page'] in NEW:
                self.assertTrue(e['visual_review']['passed'])
                self.assertEqual(e['status'],'accepted')
                self.assertNotIn('native_path',json.dumps(e))
                self.assertNotIn('generation_prompt',e)
                self.assertEqual(hashlib.sha256((ROOT/e['asset_path']).read_bytes()).hexdigest(),e['sha256'])
    def test_nonghyup_rechecked_citation(self):
        data=(ROOT/'data/family-nohall-content.json').read_text()
        self.assertNotIn('6220224',data)
        self.assertNotIn('6220224',(ROOT/'area-chungnam-gyeryong-funeral.html').read_text())
        self.assertIn('https://gyeryong.nonghyup.com/sites/gyeryong/index.do',data)
        self.assertIn('rechecked_at',data)

    def test_original_269_registry_and_assets_preserved(self):
        entries=json.loads((ROOT/'data/regional-image-registry.json').read_text())['entries']
        original=[e for e in entries if e['page'] not in NEW]
        self.assertEqual(len(original),269)
        digest=hashlib.sha256(json.dumps(original,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()).hexdigest()
        self.assertEqual(digest, 'bdd6eaeb36579ad28d72c7c8f386bfae0f429708dfde836a6be8cc4b3c2ef94a')
        for e in original:
            self.assertEqual(hashlib.sha256((ROOT/e['asset_path']).read_bytes()).hexdigest(), e['sha256'])

    def test_automatic_writers_serialize_and_checkout_current_main(self):
        for name in ('daham-seo-enrich.yml','sync-funeral-halls.yml'):
            workflow=(ROOT/'.github/workflows'/name).read_text()
            self.assertIn('group: daham-validated-content-refresh',workflow)
            self.assertIn('cancel-in-progress: false',workflow)
            self.assertIn('ref: main',workflow)
            self.assertNotIn('git push --force',workflow)

    def test_existing_jemulpo_contact_is_static(self):
        page=(ROOT/'area-incheon-jemulpo-funeral.html').read_text()
        self.assertIn('href="tel:16006131"',page)
        self.assertIn('aria-label="장례 상담"',page)
