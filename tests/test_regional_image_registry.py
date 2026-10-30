"""Regression checks for accepted originals; generated test pixels are not assets."""
import copy
import hashlib
import json
import re
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import regional_image_registry as registry
import integrate_regional_thumbnails as integration
import repair_search_images as repair


class RegistryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        asset = self.root / 'assets/regional/originals/test.png'
        asset.parent.mkdir(parents=True)
        # A temporary unit-test fixture only, never a user-facing thumbnail.
        Image.new('RGB', (800, 800), '#eedddd').save(asset)
        self.entry = {
            'id': 'test', 'page': 'area-test-funeral.html', 'asset_path': 'assets/regional/originals/test.png',
            'status': 'accepted', 'sha256': hashlib.sha256(asset.read_bytes()).hexdigest(),
            'width': 800, 'height': 800, 'mime_type': 'image/png',
            'previous_image': registry.BASE + 'assets/regional/seoul.jpg',
            'alt': '지역 장례 안내 AI 연출 이미지',
            'caption': '지역 안내용 AI 연출 이미지이며 실제 시설 사진이 아닙니다.',
            'visual_review': {'passed': True, 'reviewer': 'test', 'notes': 'test'},
        }
        self.write_registry([self.entry])

    def tearDown(self):
        self.temp.cleanup()

    def write_registry(self, entries):
        path = self.root / registry.REGISTRY
        path.parent.mkdir(exist_ok=True)
        path.write_text(json.dumps({'schema_version': 1, 'entries': entries}))

    def test_valid_original(self):
        result = registry.registered_image(registry.BASE + self.entry['page'], self.root)
        self.assertEqual(result['width'], 800)

    def test_pending_not_registered(self):
        self.assertIsNone(registry.registered_image(registry.BASE + 'area-pending-funeral.html', self.root))

    def test_offsite_page_not_registered(self):
        self.assertIsNone(registry.registered_image('https://evil.example/' + self.entry['page'], self.root))

    def test_missing_original_fails_closed(self):
        (self.root / self.entry['asset_path']).unlink()
        with self.assertRaises(FileNotFoundError):
            registry.registered_image(registry.BASE + self.entry['page'], self.root)

    def test_changed_bytes_fail_closed(self):
        with (self.root / self.entry['asset_path']).open('ab') as handle:
            handle.write(b'changed')
        with self.assertRaisesRegex(ValueError, 'Changed original'):
            registry.registered_image(registry.BASE + self.entry['page'], self.root)

    def test_review_required(self):
        entry = copy.deepcopy(self.entry)
        entry['visual_review']['passed'] = False
        self.write_registry([entry])
        with self.assertRaisesRegex(ValueError, 'Unreviewed'):
            registry.registered_image(registry.BASE + entry['page'], self.root)

    def test_path_traversal_rejected(self):
        entry = {**self.entry, 'asset_path': '../outside.png'}
        self.write_registry([entry])
        with self.assertRaisesRegex(ValueError, 'Invalid original image location'):
            registry.registered_image(registry.BASE + entry['page'], self.root)

    def test_duplicate_page_rejected(self):
        self.write_registry([self.entry, self.entry])
        with self.assertRaisesRegex(ValueError, 'Duplicate regional page'):
            registry.load_registry(self.root)

    def test_reused_file_rejected(self):
        self.write_registry([self.entry, {**self.entry, 'page': 'area-other-funeral.html'}])
        with self.assertRaisesRegex(ValueError, 'cannot be shared'):
            registry.load_registry(self.root)

    def test_dimensions_measured_not_assumed(self):
        self.write_registry([{**self.entry, 'height': 675}])
        with self.assertRaisesRegex(ValueError, 'Incorrect original dimensions'):
            registry.registered_image(registry.BASE + self.entry['page'], self.root)

    def test_exact_body_image_replaced_not_other_images(self):
        source = ('<head></head><body><h1>지역</h1><p>120만원</p>'
                  '<img src="assets/daham_logo.jpg" alt="로고">'
                  '<img src="assets/regional/seoul.jpg" width="1200" height="675" alt="옛 이미지" loading="lazy">'
                  '<a href="tel:16006131">연락</a></body>')
        result = registry.apply_registered_body(source, registry.BASE + self.entry['page'], self.entry)
        self.assertIn('src="assets/daham_logo.jpg" alt="로고"', result)
        self.assertIn('width="800" height="800"', result)
        self.assertIn('loading="lazy"', result)
        self.assertIn(self.entry['caption'], result)
        self.assertEqual(integration.metadata_invariants(source), integration.metadata_invariants(result))
        self.assertEqual(result, registry.apply_registered_body(result, registry.BASE + self.entry['page'], self.entry))

    def test_noindex_not_mutated(self):
        source = '<head><meta name="robots" content="noindex,follow"></head><body></body>'
        with self.assertRaisesRegex(ValueError, 'noindex'):
            registry.apply_registered_body(source, registry.BASE + self.entry['page'], self.entry)

    def test_existing_paragraph_disclosure_reused_without_adjacent_duplicate(self):
        source = ('<head></head><body><h1>지역</h1><p>120만원</p>'
                  '<img src="assets/regional/seoul.jpg">'
                  '<p class="caption" style="font-size:13px;color:#ead7b4">'
                  'AI 연출 이미지이며 특정 장례식장 실제 사진이 아닙니다.</p></body>')
        for duplicate in ('', '<p data-regional-image-caption="1">' + self.entry['caption'] + '</p>'):
            candidate = source.replace('<p class="caption"', duplicate + '<p class="caption"')
            result = registry.apply_registered_body(candidate, registry.BASE + self.entry['page'], self.entry)
            self.assertEqual(result.count(self.entry['caption']), 1)
            self.assertNotIn('data-regional-image-caption', result)
            self.assertIn('color:#ead7b4', result)
            self.assertEqual(integration.metadata_invariants(source), integration.metadata_invariants(result))
            self.assertEqual(result, registry.apply_registered_body(result, registry.BASE + self.entry['page'], self.entry))

    def test_real_registered_pages_have_one_visible_image_disclosure(self):
        for entry in registry.load_registry().values():
            source = (registry.ROOT / entry['page']).read_text()
            notices = re.findall(r'<(?:p|div|figcaption)\b[^>]*>[^<]*AI 연출 이미지[^<]*</(?:p|div|figcaption)>', source)
            self.assertEqual(len(notices), 1, entry['page'])

    def test_noindex_attributes_in_reverse_order_not_mutated(self):
        source = '<head><meta content="noindex,follow" name="robots"></head><body></body>'
        with self.assertRaisesRegex(ValueError, 'noindex'):
            registry.apply_registered_body(source, registry.BASE + self.entry['page'], self.entry)

    def test_no_automatic_placeholder_for_new_page(self):
        with self.assertRaisesRegex(ValueError, 'Create and review'):
            registry.existing_or_registered_image('area-new-funeral.html', self.root)

    def test_legacy_image_survives_while_pending(self):
        (self.root / 'area-old-funeral.html').write_text('<meta property="og:image" content="' + self.entry['previous_image'] + '">')
        self.assertEqual(registry.existing_or_registered_image('area-old-funeral.html', self.root), self.entry['previous_image'])

    def test_full_repair_idempotence_and_measured_schema(self):
        source = ('<html><head><title>지역 장례</title><meta name="robots" content="index,follow,max-image-preview:large">'
                  '<meta property="og:image" content="' + self.entry['previous_image'] + '">'
                  '<script type="application/ld+json">{"@type":"WebPage","url":"' + registry.BASE + self.entry['page'] + '"}</script>'
                  '</head><body><img src="assets/regional/seoul.jpg"><p>120만원</p></body></html>')
        with patch.object(registry, 'ROOT', self.root), patch.object(repair, 'ROOT', self.root):
            result, image = repair.repair(source, registry.BASE + self.entry['page'])
            second, _ = repair.repair(result, registry.BASE + self.entry['page'])
        self.assertEqual(result, second)
        self.assertIn('"width":800,"height":800', result)
        self.assertEqual(image, registry.BASE + self.entry['asset_path'])
        self.assertEqual(integration.metadata_invariants(source), integration.metadata_invariants(result))

    def test_rebuilt_generator_page_gets_accurate_image_schema(self):
        source = ('<html><head><title>지역 장례</title><meta name="robots" content="index,follow,max-image-preview:large">'
                  '</head><body><img src="assets/regional/seoul.jpg"><p>120만원</p></body></html>')
        with patch.object(registry, 'ROOT', self.root), patch.object(repair, 'ROOT', self.root):
            result, _ = repair.repair(source, registry.BASE + self.entry['page'])
        self.assertIn('"@type":"WebPage"', result)
        self.assertIn('"width":800,"height":800', result)
        self.assertNotIn('"@type":"Service"', result)

    def test_webpage_array_type_not_duplicated(self):
        source = ('<html><head><title>지역 장례</title><meta name="robots" content="index,follow,max-image-preview:large">'
                  '<script type="application/ld+json">{"@type":["WebPage","FAQPage"]}</script>'
                  '</head><body><img src="assets/regional/seoul.jpg"></body></html>')
        with patch.object(registry, 'ROOT', self.root), patch.object(repair, 'ROOT', self.root):
            result, _ = repair.repair(source, registry.BASE + self.entry['page'])
        self.assertEqual(result.count('primaryImageOfPage'), 1)
        self.assertIn('"@type":["WebPage","FAQPage"]', result)

    def test_stable_display_label_acceptance_preserves_source_identity(self):
        request = {'id': 'test', 'approved_display_label': '순천시', 'region_label': '전라남도 순천시'}
        receipt = {'id': 'test', 'generator': 'image_gen', 'independent_generation': True,
                   'generation_prompt': '순천시 장례안내, 순천만 갈대의 지역 특징',
                   'scene_summary': 'Local reeds scene', 'display_label': '순천시',
                   'local_feature': '순천만 갈대', 'source_url': 'https://www.suncheon.go.kr/',
                   'visual_review': {'passed': True, 'reviewer': 'test', 'notes': 'test fixture'},
                   'source_path': str(self.root / self.entry['asset_path'])}
        path = integration.validate_receipt(receipt, request, self.root)
        self.assertTrue(path.is_file())
        self.assertEqual(request['region_label'], '전라남도 순천시')
        stale = {**receipt, 'display_label': '전라남도 순천시'}
        with self.assertRaisesRegex(ValueError, 'obsolete province'):
            integration.validate_receipt(stale, request, self.root)
        stale_prompt = {**receipt, 'generation_prompt': 'old generic prompt without approved locality'}
        with self.assertRaisesRegex(ValueError, 'prompt must request'):
            integration.validate_receipt(stale_prompt, request, self.root)
        wrapped_request = {**request, 'approved_display_label': '인천 옛 서구 권역'}
        wrapped_receipt = {**receipt, 'display_label': '인천 옛 서구 권역',
                           'generation_prompt': 'Exact heading in two lines: "인천 옛 서구" then "권역".'}
        self.assertTrue(integration.validate_receipt(wrapped_receipt, wrapped_request, self.root).is_file())
        with self.assertRaisesRegex(ValueError, 'guidance must be applied'):
            integration.validate_receipt(receipt, {**request, 'status': 'awaiting_administrative_page_update'}, self.root)


class IntegrationTests(unittest.TestCase):
    def test_public_provenance_omits_internal_reviewers_and_executor_paths(self):
        raw = {'visual_review': {'passed': True, 'reviewer': 'internal_agent', 'notes': 'private review note'},
               'source_sha256': 'abc', 'asset_path': 'assets/regional/originals/example.jpg',
               'encoding': {'encoder': {'executable': '/usr/bin/magick', 'quality': 92}},
               'administrative_approval': {'official_source': 'https://www.incheon.go.kr/IC01070101', 'approval_message_id': 'private-id'}}
        public = integration.public_provenance(raw)
        self.assertTrue(public['visual_review']['passed'])
        self.assertNotIn('reviewer', public['visual_review'])
        self.assertEqual(public['encoding']['encoder']['executable'], 'magick')
        self.assertNotIn('approval_message_id', public['administrative_approval'])
        self.assertEqual(public['source_sha256'], raw['source_sha256'])
        self.assertEqual(raw['encoding']['encoder']['executable'], '/usr/bin/magick')

    def test_empty_registry_is_not_a_pass(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            with self.assertRaisesRegex(ValueError, 'Missing accepted-original'):
                integration.verify_registered(root)
            (root / 'data').mkdir()
            (root / registry.REGISTRY).write_text('{"schema_version":1,"entries":[]}')
            with self.assertRaisesRegex(ValueError, 'Empty accepted-original'):
                integration.verify_registered(root)

    def test_interrupted_batch_recovers_before_resuming(self):
        with tempfile.TemporaryDirectory() as temp:
            root, build = Path(temp) / 'repo', Path(temp) / 'build'
            root.mkdir(); build.mkdir()
            page, asset = root / 'page.html', root / 'new.png'
            page.write_bytes(b'old page')
            original_write = integration.atomic_bytes
            calls = []
            def interrupt_after_one(path, raw):
                original_write(path, raw)
                calls.append(path)
                if len(calls) == 1: raise KeyboardInterrupt('simulated process interruption')
            with patch.object(integration, 'atomic_bytes', interrupt_after_one):
                with self.assertRaises(KeyboardInterrupt):
                    integration.apply_transaction(root, build, {page: b'new page', asset: b'new asset'}, lambda: None,
                                                  {page: integration.sha256(b'old page'), asset: None})
            self.assertTrue((build / 'integration-transaction.json').exists())
            self.assertEqual(page.read_bytes(), b'new page')
            self.assertTrue(integration.recover_transaction(root, build))
            self.assertEqual(page.read_bytes(), b'old page')
            self.assertFalse(asset.exists())
            self.assertFalse((build / 'integration-transaction.json').exists())

    def test_recovery_never_overwrites_newer_edit(self):
        with tempfile.TemporaryDirectory() as temp:
            root, build = Path(temp) / 'repo', Path(temp) / 'build'
            root.mkdir(); build.mkdir()
            page = root / 'page.html'; page.write_bytes(b'old page')
            with self.assertRaises(KeyboardInterrupt):
                integration.apply_transaction(root, build, {page: b'new page'}, lambda: (_ for _ in ()).throw(KeyboardInterrupt()),
                                              {page: integration.sha256(b'old page')})
            page.write_bytes(b'user edit after interruption')
            with self.assertRaisesRegex(ValueError, 'newer edit'):
                integration.recover_transaction(root, build)
            self.assertEqual(page.read_bytes(), b'user edit after interruption')
            self.assertTrue((build / 'integration-transaction.json').exists())

    def test_verification_failure_rolls_back_new_asset_and_page(self):
        with tempfile.TemporaryDirectory() as temp:
            root, build = Path(temp) / 'repo', Path(temp) / 'build'
            root.mkdir(); build.mkdir()
            page, asset = root / 'page.html', root / 'new.png'
            page.write_bytes(b'old page')
            with self.assertRaisesRegex(ValueError, 'bad metadata'):
                integration.apply_transaction(root, build, {page: b'new page', asset: b'new asset'},
                                              lambda: (_ for _ in ()).throw(ValueError('bad metadata')),
                                              {page: integration.sha256(b'old page'), asset: None})
            self.assertEqual(page.read_bytes(), b'old page')
            self.assertFalse(asset.exists())
            self.assertFalse((build / 'integration-transaction.json').exists())

    def test_planning_snapshot_detects_intervening_user_edit(self):
        with tempfile.TemporaryDirectory() as temp:
            root, build = Path(temp) / 'repo', Path(temp) / 'build'
            root.mkdir(); build.mkdir()
            page = root / 'page.html'; page.write_bytes(b'old page')
            expected = {page: integration.sha256(page.read_bytes())}
            page.write_bytes(b'newer user edit')
            with self.assertRaisesRegex(ValueError, 'after integration planning'):
                integration.apply_transaction(root, build, {page: b'stale planned page'}, lambda: None, expected)
            self.assertEqual(page.read_bytes(), b'newer user edit')
            self.assertFalse((build / 'integration-transaction.json').exists())

    def test_initial_dry_run_without_registry_is_a_preview_not_completion(self):
        with tempfile.TemporaryDirectory() as temp:
            root, build = Path(temp) / 'repo', Path(temp) / 'build'
            root.mkdir(); build.mkdir(); (build / 'receipts').mkdir()
            (build / 'manifest.json').write_text('{"entries":[]}')
            with patch.object(integration, 'ROOT', root), patch.object(registry, 'ROOT', root):
                result = integration.run(build)
            self.assertEqual(result['mode'], 'dry-run')
            self.assertEqual(result['accepted'], 0)
            self.assertFalse((root / registry.REGISTRY).exists())

    def test_sitemap_scope(self):
        source = ('<urlset xmlns:image="http://www.google.com/schemas/sitemap-image/1.1">'
                  '<url><loc>A</loc><image:image><image:loc>old-A</image:loc></image:image></url>'
                  '<url><loc>B</loc><image:image><image:loc>old-B</image:loc></image:image></url></urlset>')
        result = integration.update_sitemap(source, {'A': 'new-A'})
        self.assertEqual(result, source.replace('old-A', 'new-A'))
        self.assertEqual(result, integration.update_sitemap(result, {'A': 'new-A'}))

    def test_missing_sitemap_entry_rejected(self):
        with self.assertRaises(ValueError):
            integration.update_sitemap('<urlset><url><loc>B</loc></url></urlset>', {'A': 'new-A'})

    def test_duplicate_sitemap_entry_rejected(self):
        with self.assertRaisesRegex(ValueError, 'Duplicate'):
            integration.update_sitemap('<urlset><url><loc>A</loc></url><url><loc>A</loc></url></urlset>', {'A': 'new-A'})

    def test_duplicate_file_and_scene_detected(self):
        path = Path(__file__).resolve().parents[1] / 'assets/regional-funeral-base.png'
        same = integration.fingerprint(path)
        result = integration.compare(same, same)
        self.assertTrue(result['suspicious'])
        self.assertTrue(result['exact_file'])
        self.assertTrue(result['exact_pixels'])
        self.assertEqual(result['scene_phash_distance'], 0)

    def test_compressed_common_scene_detected(self):
        root = Path(__file__).resolve().parents[1]
        a = integration.fingerprint(root / 'assets/regional-funeral-base.png')
        b = integration.fingerprint(root / 'assets/regional/seoul.jpg')
        result = integration.compare(a, b)
        self.assertFalse(result['exact_file'])
        self.assertTrue(result['suspicious'])

    def test_receipt_requires_local_landmark_after_brief_change(self):
        receipt = {'id': 'test', 'generator': 'image_gen', 'independent_generation': True,
                   'generation_prompt': 'example', 'scene_summary': 'generic scene'}
        with self.assertRaisesRegex(ValueError, 'region-specific'):
            integration.validate_receipt(receipt, {'id': 'test'}, Path('/tmp'))

    def test_blocked_administrative_label_rejected(self):
        receipt = {'id': 'test', 'generator': 'image_gen', 'independent_generation': True,
                   'generation_prompt': 'example', 'scene_summary': 'example'}
        with self.assertRaisesRegex(ValueError, 'place-name review'):
            integration.validate_receipt(receipt, {'id': 'test', 'status': 'blocked_label'}, Path('/tmp'))


if __name__ == '__main__':
    unittest.main()
