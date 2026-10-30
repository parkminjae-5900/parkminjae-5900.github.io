"""Pure/mocked browser contracts. These tests never launch a browser process."""
import hashlib
import json
import os
from pathlib import Path
import re
import sys
import tempfile
import textwrap
import unittest
from unittest.mock import MagicMock, patch

from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import verify_regional_thumbnails_browser as qa


def measurement(width=390):
    return {'representativeCount': 1, 'viewport': width, 'documentWidth': width,
            'naturalWidth': 600, 'naturalHeight': 600, 'imageWidth': min(width - 32, 600),
            'imageHeight': min(width - 32, 600), 'imageLeft': 16,
            'imageRight': min(width - 16, 616), 'imageVisibility': 'visible',
            'imageOpacity': 1, 'brokenImages': [], 'pendingImages': [], 'h1Count': 1}


def fake_page(width=390, error=None):
    page = MagicMock()
    page.goto.return_value.status = 200
    if error:
        page.goto.side_effect = RuntimeError(error)
    page.evaluate.side_effect = lambda script, *args: measurement(width) if script == qa.MEASURE else None
    return page


class BrowserContracts(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.out = self.root / 'reports'
        self.entries = []
        for suffix in ('a', 'b'):
            asset = f'assets/regional/originals/{suffix}.png'
            path = self.root / asset
            path.parent.mkdir(parents=True, exist_ok=True)
            # Disposable fixture only, never a production thumbnail.
            Image.new('RGB', (600, 600), 'white').save(path)
            page = f'area-{suffix}-funeral.html'
            (self.root / page).write_text(f'<style>img{{width:100%;height:auto}}</style><h1>지역</h1><img src="{asset}">')
            self.entries.append({'id': suffix, 'page': page, 'asset_path': asset,
                                 'status': 'accepted', 'visual_review': {'passed': True},
                                 'sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
                                 'width': 600, 'height': 600, 'mime_type': 'image/png'})
        (self.root / 'data').mkdir()
        self.write_registry(self.entries)

    def tearDown(self):
        self.temporary.cleanup()

    def write_registry(self, entries):
        (self.root / 'data/regional-image-registry.json').write_text(json.dumps({'schema_version': 1, 'entries': entries}))

    def factory(self, fail_launch=False, fail_first_page=False):
        factory = MagicMock()
        pw = factory.return_value.__enter__.return_value
        browser = pw.chromium.launch.return_value
        browser.version = 'mocked browser; not a runtime result'
        if fail_launch:
            pw.chromium.launch.side_effect = RuntimeError('simulated launch failure')
        def make_context(**kwargs):
            context = MagicMock()
            pages = [fake_page(kwargs['viewport']['width'], 'simulated page failure' if fail_first_page else None),
                     fake_page(kwargs['viewport']['width'])]
            context.new_page.side_effect = pages
            return context
        browser.new_context.side_effect = make_context
        return factory

    def test_measurement_pass_and_regressions(self):
        self.assertEqual(qa.measurement_failures(measurement(), self.entries[0], 390), [])
        for change, expected in [({'documentWidth': 500}, 'horizontal overflow'),
                                 ({'imageHeight': 1}, 'stretched or cropped image box'),
                                 ({'imageWidth': 0}, 'image is hidden or has invalid dimensions'),
                                 ({'naturalWidth': 1}, 'wrong decoded image dimensions'),
                                 ({'representativeCount': 2}, 'representative image count is not one'),
                                 ({'pendingImages': ['missing.jpg']}, 'broken or undecoded image'),
                                 ({'decodeTimedOut': True}, 'broken or undecoded image'),
                                 ({'imageOpacity': 0}, 'representative image is not visible')]:
            with self.subTest(change=change):
                self.assertIn(expected, qa.measurement_failures({**measurement(), **change}, self.entries[0], 390))

    def test_checkout_route_rejects_escape_hidden_and_symlinks(self):
        self.assertEqual(qa.local_path(qa.BASE + self.entries[0]['asset_path'], self.root), self.root / self.entries[0]['asset_path'])
        self.assertIsNone(qa.local_path('https://analytics.example/collect', self.root))
        self.assertIsNone(qa.local_path('https://www.dahamsangjo.co.kr.evil.example/file.js', self.root))
        for path in ('%2e%2e/private.json', '.git/config', 'assets/%5csecret.txt', 'secret.env'):
            with self.subTest(path=path), self.assertRaises(ValueError):
                qa.local_path(qa.BASE + path, self.root)
        (self.root / 'escape.json').symlink_to(self.root.parent / 'outside.json')
        with self.assertRaises(ValueError):
            qa.local_path(qa.BASE + 'escape.json', self.root)

    def test_template_group_ignores_region_and_asset(self):
        a = '<style>img{height:auto}</style><img src="a.jpg" style="width:100%"><h1>서울</h1>'
        b = a.replace('a.jpg', 'b.jpg').replace('서울', '부산')
        self.assertEqual(qa.template_key(a, 'a.jpg'), qa.template_key(b, 'b.jpg'))
        self.assertNotEqual(qa.template_key(a, 'a.jpg'), qa.template_key(b.replace('width:100%', 'width:50%'), 'b.jpg'))

    def test_administrative_pages_have_dedicated_capture_slots(self):
        self.assertEqual(qa.representative_budget(64), 48)
        self.assertEqual(qa.representative_budget(2), 1)
        keys = {qa.capture_key(name, 'shared-css', width)
                for name in qa.ADMINISTRATIVE_CAPTURE_PAGES for width in qa.DEFAULT_WIDTHS}
        self.assertEqual(len(keys), 16)
        self.assertNotIn(qa.capture_key('other.html', 'shared-css', 390), keys)

    def test_empty_registry_fails_without_browser(self):
        self.write_registry([])
        with patch.object(qa, '_playwright_factory') as factory:
            report = qa.run(self.out, root=self.root)
        factory.assert_not_called()
        self.assertEqual(report['result'], 'FAIL')
        self.assertIn('empty', report['failures'][0]['error'])
        self.assertEqual(json.loads((self.out / 'report.json').read_text())['result'], 'FAIL')

    def test_minimum_count_does_not_silently_pass_partial_registry(self):
        with patch.object(qa, '_playwright_factory') as factory:
            report = qa.run(self.out, root=self.root, minimum_count=265)
        factory.assert_not_called()
        self.assertEqual(report['result'], 'FAIL')
        self.assertIn('265', report['failures'][0]['error'])

    def test_launch_failure_report_survives(self):
        with patch.object(qa, '_playwright_factory', self.factory(fail_launch=True)):
            report = qa.run(self.out, root=self.root)
        persisted = json.loads((self.out / 'report.json').read_text())
        self.assertEqual(persisted['result'], 'FAIL')
        self.assertEqual(persisted['checked_viewports'], 0)
        self.assertEqual(persisted['unchecked_viewports'], 8)
        self.assertIn('simulated launch failure', report['failures'][0]['error'])

    def test_default_bundled_browser_and_all_widths(self):
        factory = self.factory()
        with patch.object(qa, '_playwright_factory', factory):
            report = qa.run(self.out, root=self.root, capture=0)
        factory.return_value.__enter__.return_value.chromium.launch.assert_called_once_with(headless=True)
        self.assertEqual(report['result'], 'PASS')
        self.assertEqual(report['checked_viewports'], 8)
        self.assertEqual({row['width'] for row in report['results']}, {360, 390, 430, 1280})
        self.assertEqual(report['capture_count'], 0)

    def test_page_exception_does_not_skip_next_page(self):
        with patch.object(qa, '_playwright_factory', self.factory(fail_first_page=True)):
            report = qa.run(self.out, root=self.root, widths=(390,), capture=0)
        self.assertEqual(report['checked_viewports'], 2)
        self.assertTrue(report['results'][0]['failures'])
        self.assertEqual(report['results'][1]['failures'], [])
        self.assertEqual(report['result'], 'FAIL')

    def test_missing_asset_does_not_skip_other_page(self):
        (self.root / self.entries[1]['asset_path']).unlink()
        with patch.object(qa, '_playwright_factory', self.factory()):
            report = qa.run(self.out, root=self.root, widths=(390,), capture=0)
        self.assertEqual(report['checked_viewports'], 2)
        self.assertEqual(report['results'][0]['failures'], [])
        self.assertEqual(report['results'][1]['stage'], 'page preflight')
        self.assertEqual(report['result'], 'FAIL')

    def test_screenshot_total_budget_and_json_failure_retention(self):
        factory = self.factory(fail_first_page=True)
        with patch.object(qa, '_playwright_factory', factory):
            report = qa.run(self.out, root=self.root, capture=2)
        self.assertEqual(report['capture_count'], 2)
        self.assertEqual(report['checked_viewports'], 8)
        self.assertEqual(len(report['failures']), 4)
        self.assertTrue(any('screenshot_omitted' in row for row in report['results']))
        for row in report['results']:
            if row.get('screenshot'):
                self.assertEqual(row['screenshot'], Path(row['screenshot']).name)

    def test_public_report_redacts_paths_but_preserves_error_details(self):
        self.out.mkdir()
        raw = {'failures': [{'error': f"FileNotFoundError: '{self.root}/assets/missing.jpg'; status 404",
                             'screenshot': str(self.out / 'failure-390.jpg')}],
               'results': [{'console_errors': [f'Cannot write {self.out}/capture.jpg']}],
               'route_errors': [f'Cannot read {self.root}/data/registry.json'],
               'scope': 'No agent or reviewer identities are included'}
        qa.save_report(self.out, raw, self.root)
        serialized = (self.out / 'report.json').read_text()
        self.assertNotIn(str(self.root), serialized)
        self.assertNotIn(str(self.out), serialized)
        result = json.loads(serialized)
        self.assertEqual(result['failures'][0]['screenshot'], 'failure-390.jpg')
        self.assertIn("FileNotFoundError: '<checkout>/assets/missing.jpg'; status 404", serialized)
        self.assertIn('<artifacts>/capture.jpg', serialized)
        self.assertIn('<checkout>/data/registry.json', serialized)
        # Only the public copy is redacted, not the in-memory debugging object.
        self.assertIn(str(self.root), raw['failures'][0]['error'])

    def test_mocked_launch_failure_returns_and_persists_sanitized_report(self):
        factory = self.factory()
        factory.return_value.__enter__.return_value.chromium.launch.side_effect = RuntimeError(
            f'Cannot open {self.root}/browser-binary; artifact {self.out}/trace.json; status 127')
        with patch.object(qa, '_playwright_factory', factory):
            report = qa.run(self.out, root=self.root)
        returned = json.dumps(report)
        persisted = (self.out / 'report.json').read_text()
        for value in (returned, persisted):
            self.assertNotIn(str(self.root), value)
            self.assertIn('<checkout>/browser-binary', value)
            self.assertIn('<artifacts>/trace.json', value)
            self.assertIn('status 127', value)
        self.assertEqual(report['result'], 'FAIL')

    def test_route_fulfills_local_and_stubs_external_without_continue(self):
        context, report = MagicMock(), {'route_errors': [], 'external_requests_stubbed': 0}
        qa.configure_context(context, self.root, report)
        handler = context.route.call_args.args[1]
        route = MagicMock()
        route.request.url = qa.BASE + self.entries[0]['page']
        route.request.method = 'GET'
        handler(route)
        self.assertEqual(route.fulfill.call_args.kwargs['status'], 200)
        self.assertIn(b'<h1>', route.fulfill.call_args.kwargs['body'])
        route.request.url = 'https://analytics.example/collect'
        route.request.resource_type = 'fetch'
        route.request.method = 'POST'
        handler(route)
        self.assertEqual(report['external_requests_stubbed'], 1)
        self.assertEqual(route.fulfill.call_args.kwargs['body'], '{}')
        route.continue_.assert_not_called()
        context.route_web_socket.assert_called_once()

    def test_console_browser_and_resource_errors_are_reported(self):
        page = fake_page()
        handlers = {}
        page.on.side_effect = lambda event, handler: handlers.update({event: handler})
        def navigate(*args, **kwargs):
            handlers['console'](type('Console', (), {'type': 'error', 'text': 'fixture error'})())
            handlers['pageerror'](RuntimeError('fixture browser error'))
            handlers['response'](type('Response', (), {'url': qa.BASE + 'missing.js', 'status': 404})())
            handlers['requestfailed'](type('Request', (), {'url': qa.BASE + 'failed.jpg', 'failure': 'fixture failure'})())
            return type('Response', (), {'status': 200})()
        page.goto.side_effect = navigate
        context = MagicMock()
        context.new_page.return_value = page
        row = qa.check_page(context, self.entries[0]['page'], {**self.entries[0], '_template': 'fixture'},
                            390, self.out, {'captured_templates': [], 'capture_count': 0,
                                           'representative_captures': 0}, 0)
        for expected in ['console error', 'browser exception', 'missing resource', 'failed resource request']:
            self.assertIn(expected, row['failures'])

    def test_workflow_read_only_pr_isolated_and_pinned(self):
        text = (qa.ROOT / '.github/workflows/verify-regional-thumbnails-browser.yml').read_text()
        for expected in ['workflow_call:', 'contents: read', 'persist-credentials: false',
                         'playwright==1.58.0', '--with-deps chromium', 'if: always()',
                         '--widths 360 390 430 1280', '--minimum-count 269', '--capture 64']:
            self.assertIn(expected, text)
        self.assertNotIn('pull_request_target', text)
        self.assertNotIn('pages: write', text)
        self.assertNotIn('/usr/bin/chromium', text)
        caller = (qa.ROOT / '.github/workflows/verify-seo-conversion.yml').read_text()
        self.assertIn('pull_request:', caller)
        self.assertIn('uses: ./.github/workflows/verify-regional-thumbnails-browser.yml', caller)
        self.assertNotIn('secrets: inherit', caller)

    def test_workflow_job_environment_avoids_unavailable_runner_context(self):
        text = (qa.ROOT / '.github/workflows/verify-regional-thumbnails-browser.yml').read_text()
        job_environment = text.split('    env:\n', 1)[1].split('    steps:', 1)[0]
        # GitHub jobs.<job_id>.env cannot reference runner or env contexts.
        self.assertNotIn('${{', job_environment)
        self.assertIn('QA_OUT: regional-thumbnail-browser-output', job_environment)
        self.assertIn('fonts-noto-cjk', text)
        self.assertIn("fc-match ':lang=ko'", text)
        self.assertIn("fc-match 'Noto Sans CJK KR:lang=ko'", text)

    def test_workflow_setup_failure_report_is_valid_json(self):
        text = (qa.ROOT / '.github/workflows/verify-regional-thumbnails-browser.yml').read_text()
        match = re.search(r"python - <<'PY'\n(.*?)\n          PY", text, re.S)
        self.assertIsNotNone(match)
        with patch.dict(os.environ, {'QA_OUT': str(self.out)}):
            exec(compile(textwrap.dedent(match.group(1)), '<workflow-setup>', 'exec'), {})
        report = json.loads((self.out / 'report.json').read_text())
        self.assertEqual(report['result'], 'FAIL')
        self.assertEqual(report['checked_viewports'], 0)


if __name__ == '__main__':
    unittest.main()
