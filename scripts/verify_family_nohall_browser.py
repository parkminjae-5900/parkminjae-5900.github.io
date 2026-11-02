#!/usr/bin/env python3
"""Real Chromium QA. Never replace a failed launch with a static PASS."""
import argparse
import base64
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import re
import sys
import threading
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'scripts'))
from funeral_hall_photos import load_inputs, load_photos, load_aliases


class Quiet(SimpleHTTPRequestHandler):
    def log_message(self, *args): pass


def main():
    parser = argparse.ArgumentParser(); parser.add_argument('--out', default='family-nohall-browser-output'); parser.add_argument('--chromium-executable'); args = parser.parse_args()
    out = Path(args.out); out.mkdir(parents=True, exist_ok=True)
    report = {'result':'FAIL','checked_viewports':0,'no_javascript_pages':0,'failures':[],'screenshots':[],'visual_samples':[]}
    server = None
    try:
        from playwright.sync_api import sync_playwright
        inputs = load_inputs(ROOT); photos = load_photos(ROOT, inputs)
        curated = [e['page'] for e in json.loads((ROOT/'data/family-nohall-content.json').read_text())['entries']]
        directories = sorted(str(x.relative_to(ROOT)) for x in (ROOT/'funeral-halls').glob('*.html') if not x.name.startswith('fh-'))
        provisional = sorted(str(x.relative_to(ROOT)) for x in (ROOT/'funeral-halls').glob('fh-*.html'))
        reviews = {r['page']:r for r in json.loads((ROOT/'data/funeral-hall-content-reviews.json').read_text())['entries']}
        photo_pages = {f'funeral-halls/{ident}.html' for ident in photos}
        index_candidates = {rel for rel,review in reviews.items() if review['index_candidate']}
        pages = sorted(set(inputs[3]) | set(curated) | set(directories) | set(provisional) | {a['page'] for a in load_aliases(ROOT, inputs)})
        server = ThreadingHTTPServer(('127.0.0.1', 0), partial(Quiet, directory=str(ROOT)))
        threading.Thread(target=server.serve_forever, daemon=True).start()
        origin = f'http://127.0.0.1:{server.server_port}'
        def local_route(route):
            url = urlparse(route.request.url)
            if route.request.url.startswith(origin) or url.scheme == 'data':
                route.continue_()
            elif url.hostname == 'www.dahamsangjo.co.kr':
                # Test the checkout, not the live deployment, including absolute
                # representative images and production-canonical navigation.
                response = route.fetch(url=origin + url.path + ('?' + url.query if url.query else ''))
                route.fulfill(response=response)
            else:
                # Do not pollute analytics or depend on third-party networks.
                route.fulfill(status=204, body='')
        with sync_playwright() as pw:
            browser = pw.chromium.launch(headless=True, executable_path=args.chromium_executable)
            for width in (360, 390, 430, 1280):
                context = browser.new_context(viewport={'width':width,'height':900}, device_scale_factor=1)
                context.route('**/*', local_route)
                for rel in pages:
                    if width in (390, 430) and rel not in curated and rel not in photo_pages and rel != 'funeral-halls/index.html': continue
                    page = context.new_page(); errors = []; failed_local = []
                    page.on('pageerror', lambda error: errors.append(str(error)))
                    page.on('console', lambda message: errors.append(message.text) if message.type == 'error' else None)
                    page.on('response', lambda response: failed_local.append(response.url) if (response.url.startswith(origin) or urlparse(response.url).hostname == 'www.dahamsangjo.co.kr') and response.status >= 400 else None)
                    try:
                        page.goto(origin+'/'+rel, wait_until='networkidle')
                        page.locator('h1').wait_for()
                        page.evaluate('document.fonts.ready')
                        page.locator('img').evaluate_all("imgs => Promise.all(imgs.map(img => {img.loading='eager'; return img.decode();}))")
                        result = page.evaluate('''() => ({
                          h1:document.querySelectorAll('h1').length,
                          overflow:document.documentElement.scrollWidth>innerWidth+1,
                          images:[...document.images].map(i=>({src:i.src,ok:i.complete&&i.naturalWidth>0,rect:i.getBoundingClientRect().width})),
                          tiny:[...document.querySelectorAll('.family-nohall-guide p,.hall-card p')].filter(x=>parseFloat(getComputedStyle(x).fontSize)<14).length
                        })''')
                        assert result['h1'] == 1, 'H1 count'
                        assert not result['overflow'], 'Horizontal overflow'
                        assert not result['tiny'], 'Unreadable body text'
                        assert all(i['ok'] and i['rect'] <= width for i in result['images']), 'Broken/overflow image'
                        assert not errors, str(errors)
                        assert not failed_local, 'Missing assets '+str(failed_local)
                        if rel in inputs[3]:
                            ident = inputs[3][rel]
                            if ident not in photos:
                                assert page.locator('[data-facility-photo-pending="1"]').count() == 1
                                assert page.locator('meta[property="og:image"]').count() == 0
                            else:
                                assert page.locator('[data-facility-photo="1"] img').count() == 1
                        if rel in provisional:
                            robots=page.locator('meta[name="robots"]').get_attribute('content')
                            assert ('noindex' not in robots) == bool(reviews[rel]['index_candidate'])
                            assert page.locator('meta[name="daham-facility-id"]').count() == 1
                            if rel in photo_pages:
                                assert page.locator('[data-facility-photo="1"] img').count() == 1
                                assert page.locator('[data-facility-photo-pending="1"]').count() == 0
                            else:
                                assert page.locator('[data-facility-photo-pending="1"]').count() == 1
                        if rel in directories:
                            expected_photos = len(re.findall(r'data-facility-photo="1"', (ROOT/rel).read_text()))
                            assert page.locator('[data-facility-photo="1"] img').count() == expected_photos
                        if rel == 'funeral-halls/index.html':
                            field = page.locator('#hall-filter')
                            field.fill('일치하지않는검색어999xyz')
                            assert page.locator('[data-facility-id]:visible').count() == 0
                            field.fill('')
                            assert page.locator('[data-facility-id]:visible').count() == 50
                        if width in (360, 1280) and (rel in curated or rel in index_candidates or rel in photo_pages or rel == 'funeral-halls/index.html'):
                            filename = rel.replace('/','-')+f'-{width}.png'
                            page.screenshot(path=str(out/filename), full_page=True)
                            report['screenshots'].append(filename)
                        sample_pages = {'area-seoul-songpa-funeral.html','incheon-medical-center-funeral.html','funeral-halls/index.html',provisional[0]} | photo_pages | index_candidates
                        if width in (360,1280) and rel in sample_pages:
                            selector = '[data-facility-photo="1"]' if rel in photo_pages else ('.family-nohall-guide' if rel in index_candidates else ('.hall-card' if rel.startswith('funeral-halls/') else '.family-nohall-guide'))
                            page.locator(selector).first.evaluate("el => el.scrollIntoView({block:'start'})")
                            filename = rel.replace('/','-')+f'-{width}-detail.jpg'
                            page.screenshot(path=str(out/filename),type='jpeg',quality=55)
                            report['visual_samples'].append(filename)
                        report['checked_viewports'] += 1
                    except Exception as exc:
                        report['failures'].append({'page':rel,'width':width,'error':str(exc)})
                    finally: page.close()
                context.close()
            context = browser.new_context(java_script_enabled=False, viewport={'width':390,'height':900})
            context.route('**/*', local_route)
            for rel in directories:
                page = context.new_page()
                page.goto(origin+'/'+rel, wait_until='load')
                expected = len(re.findall(r'data-facility-id="', (ROOT/rel).read_text()))
                assert page.locator('[data-facility-id]:visible').count() == expected, 'Records require JavaScript'
                assert page.locator('.pagination a').count() == 44, 'Static pagination missing'
                report['no_javascript_pages'] += 1; page.close()
            page = context.new_page()
            page.goto(origin+'/funeral-halls/', wait_until='load')
            page.locator('.pagination a', has_text=re.compile('^2$')).first.click()
            page.wait_for_load_state('load')
            assert '/funeral-halls/page-2.html' in page.url, 'No-JS pagination did not navigate'
            detail = page.locator('.detail-link').first
            # Every reviewed facility is crawlable; choose the first directory
            # page containing a detail link if this chunk contains no mapping.
            if not detail.count():
                for rel in directories:
                    page.goto(origin+'/'+rel, wait_until='load')
                    detail = page.locator('.detail-link').first
                    if detail.count(): break
            assert detail.count(), 'No static facility detail links'
            expected = detail.get_attribute('href')
            detail.click(); page.wait_for_load_state('load')
            assert urlparse(page.url).path == expected, 'No-JS detail link did not navigate'
            assert page.locator('meta[name="daham-facility-id"]').count() == 1, 'Wrong facility detail destination'
            page.close()
            context.close(); browser.close()
        assert report['checked_viewports'] >= 220, 'Insufficient actual browser coverage'
        assert report['no_javascript_pages'] == 22, 'Incomplete no-JavaScript coverage'
        if not report['failures']: report['result'] = 'PASS'
    except Exception as exc:
        report['failures'].append({'stage':'browser execution','error':str(exc)})
    finally:
        if server: server.shutdown(); server.server_close()
        (out/'report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(report,ensure_ascii=False))
    # Bounded current-site-only visual samples in CI logs permit exact-pixel
    # review even when the client cannot download binary workflow artifacts.
    for filename in report['visual_samples']:
        encoded = base64.b64encode((out/filename).read_bytes()).decode()
        for offset in range(0,len(encoded),4000):
            print('VISUAL_QA:'+filename+':'+encoded[offset:offset+4000])
    if report['result'] != 'PASS': raise SystemExit(1)


if __name__ == '__main__': main()
