import contextlib
import io
import shutil
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import enrich_seo
import public_page_paths as paths
import repair_search_images
import submit_indexnow
import verify_pages_output

HTML = '<html><head><title>Example</title></head><body>Source fixture</body></html>'


class PublicPagePathTests(unittest.TestCase):
    def test_public_paths_still_work(self):
        for path in ['index.html', 'area-ansan-funeral.html', 'funeral-halls/seoul.html']:
            with self.subTest(path=path):
                self.assertTrue(paths.is_public_html_path(path))
                self.assertIsNotNone(submit_indexnow.path_to_url(path))

    def test_test_inputs_and_non_public_paths_are_excluded(self):
        for path in ['tests/fixtures/anyang-units.html', 'fixtures/example.html',
                     'nested/tests/example.html', 'test/example.html',
                     '__tests__/example.html', '_site/index.html', '.git/example.html',
                     'node_modules/pkg/index.html',
                     '../index.html', '/index.html', r'tests\sample.html']:
            with self.subTest(path=path):
                self.assertFalse(paths.is_public_html_path(path))
                self.assertIsNone(submit_indexnow.path_to_url(path))

    def test_existing_public_staff_and_generator_app_rules_are_preserved(self):
        self.assertEqual(submit_indexnow.validate_url(submit_indexnow.BASE_URL + 'staff/'),
                         submit_indexnow.BASE_URL + 'staff/')
        self.assertTrue(paths.is_public_html_path('staff/index.html'))
        for directory in paths.ENRICHMENT_EXCLUDED_DIRECTORIES:
            self.assertFalse(paths.is_enrichment_path(directory + '/index.html'))

    def test_direct_enrichment_does_not_read_or_write_fixtures(self):
        with tempfile.TemporaryDirectory() as tmp, patch.object(enrich_seo, 'ROOT', Path(tmp)):
            path = Path(tmp) / 'tests/fixtures/source.html'
            path.parent.mkdir(parents=True)
            path.write_text(HTML)
            before = path.read_bytes()
            self.assertEqual(enrich_seo.process(path, write=True), 'skip-non-public')
            self.assertEqual(before, path.read_bytes())

    def test_full_write_pass_preserves_fixtures_and_is_idempotent(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            fixture = root / 'tests/fixtures/source.html'
            fixture.parent.mkdir(parents=True)
            fixture.write_text(HTML)
            public = root / 'index.html'
            public.write_text(HTML)
            before = fixture.read_bytes()
            with patch.object(enrich_seo, 'ROOT', root), patch.object(sys, 'argv', ['enrich_seo', '--write']), \
                 patch('subprocess.run'), contextlib.redirect_stdout(io.StringIO()):
                enrich_seo.main()
                enriched = public.read_bytes()
                enrich_seo.main()
            self.assertEqual(before, fixture.read_bytes())
            self.assertIn(b'data-daham-seo-automation="1"', enriched)
            self.assertEqual(enriched, public.read_bytes())

    def test_diff_collection_skips_changed_and_renamed_fixtures(self):
        lines = ['M\ttests/fixtures/anyang-units.html',
                 'A\ttests/fixtures/mokpo-units.html',
                 'D\tfixtures/deleted.html',
                 'R100\ttests/fixtures/old.html\ttests/fixtures/new.html',
                 'R100\told-public.html\ttests/fixtures/moved.html',
                 'M\tindex.html']
        self.assertEqual(submit_indexnow.collect_urls(lines), [
            submit_indexnow.BASE_URL, submit_indexnow.BASE_URL + 'old-public.html'])

    def test_fixture_urls_cannot_bypass_guard_via_seed_or_payload(self):
        for suffix in ['tests/fixtures/source.html', '%74ests/fixtures/source.html']:
            url = submit_indexnow.BASE_URL + suffix
            with self.subTest(url=url):
                with self.assertRaises(ValueError):
                    submit_indexnow.validate_url(url)
                with self.assertRaises(ValueError):
                    submit_indexnow.build_payload([url])
                with patch('pathlib.Path.read_text', return_value=url), self.assertRaises(ValueError):
                    submit_indexnow.collect_urls(['M\t.github/indexnow-seed.txt'])

    def test_sitemap_image_repair_cannot_write_fixtures(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            fixture = root / 'tests/fixtures/source.html'
            fixture.parent.mkdir(parents=True)
            fixture.write_text(HTML)
            (root / 'sitemap.xml').write_text(
                '<urlset><url><loc>https://www.dahamsangjo.co.kr/tests/fixtures/source.html'
                '</loc></url></urlset>')
            with patch.object(repair_search_images, 'ROOT', root), \
                 patch.object(repair_search_images, 'dimensions', return_value=((192, 192), 'image/png')), \
                 patch.object(repair_search_images, 'repair') as repair, \
                 patch.object(sys, 'argv', ['repair', '--write']), \
                 contextlib.redirect_stdout(io.StringIO()), self.assertRaises(SystemExit):
                repair_search_images.main()
            repair.assert_not_called()
            self.assertEqual(fixture.read_text(), HTML)

    def test_committed_fixtures_have_no_automated_production_metadata(self):
        for fixture in (ROOT / 'tests/fixtures').glob('*.html'):
            source = fixture.read_text(encoding='utf-8')
            with self.subTest(path=fixture.name):
                self.assertNotIn('data-daham-seo-automation="1"', source)
                self.assertNotIn('www.dahamsangjo.co.kr/tests/', source)

    def test_sitemap_and_seed_contain_only_public_pages(self):
        for item in ET.parse(ROOT / 'sitemap.xml').findall('{*}url/{*}loc'):
            submit_indexnow.validate_url(item.text)
        for line in submit_indexnow.SEED_FILE.read_text().splitlines():
            if line.strip() and not line.startswith('#'):
                submit_indexnow.validate_url(line)

    def test_pages_config_excludes_each_fixture_directory(self):
        # A simple YAML list is deliberate. The CI Jekyll build verifies semantics.
        config = (ROOT / '_config.yml').read_text()
        excluded = {line.strip()[2:].strip() for line in config.splitlines()
                    if line.strip().startswith('- ')}
        self.assertTrue(paths.FIXTURE_DIRECTORIES <= excluded)
        self.assertFalse((ROOT / '.nojekyll').exists(), 'Pages exclusions require Jekyll')

    def test_artifact_verifier_rejects_missing_output_and_fixture_leaks(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            with self.assertRaises(ValueError):
                verify_pages_output.verify_output(root / 'missing')
            leak = root / 'tests/fixtures/source.html'
            leak.parent.mkdir(parents=True)
            leak.write_text(HTML)
            with self.assertRaisesRegex(ValueError, 'Test inputs leaked'):
                verify_pages_output.verify_output(root)

    def test_artifact_verifier_preserves_nested_public_pages_too(self):
        with tempfile.TemporaryDirectory() as tmp:
            source, destination = Path(tmp) / 'source', Path(tmp) / 'output'
            names = ['index.html', 'staff/profiles/01.html', 'seo-combos/example.html',
                     'sitemap.xml', 'robots.txt', 'CNAME', 'assets/regional-funeral-base.png',
                     'data/funeral-hall-prices.json']
            for name in names:
                path = source / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(b'original')
            shutil.copytree(source, destination)
            self.assertEqual(verify_pages_output.verify_output(destination, source), len(names))
            (destination / 'staff/profiles/01.html').write_text('changed')
            with self.assertRaisesRegex(ValueError, 'Public file changed'):
                verify_pages_output.verify_output(destination, source)


if __name__ == '__main__':
    unittest.main()
