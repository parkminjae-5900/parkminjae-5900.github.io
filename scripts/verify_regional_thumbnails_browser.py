#!/usr/bin/env python3
"""Read-only Chromium QA against checkout bytes, never deployed URLs.

Playwright's installed Chromium is the default; --chromium is an explicit override.
All HTTP requests are fulfilled locally or stubbed, service workers are blocked,
WebSockets are closed, and no production tracking/submission is performed.
Reports checkpoint after every page and survive missing dependencies/launch errors.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import mimetypes
from pathlib import Path
import re
import tempfile
from urllib.parse import unquote, urlparse

from regional_image_registry import ROOT, BASE, load_registry, registered_image

DEFAULT_WIDTHS = (360, 390, 430, 1280)
VIEWPORT_HEIGHT = 1000
ALLOWED_SUFFIXES = {'.html', '.css', '.js', '.mjs', '.json', '.png', '.jpg', '.jpeg',
                    '.gif', '.webp', '.avif', '.svg', '.ico', '.woff', '.woff2', '.ttf', '.txt'}


def local_path(url, root=ROOT):
    """Resolve only safe checkout resources; None means a non-local origin."""
    parsed = urlparse(url)
    if parsed.scheme not in ('http', 'https') or parsed.netloc != urlparse(BASE).netloc:
        return None
    root = Path(root).resolve()
    decoded = unquote(parsed.path)
    if '\\' in decoded or '\x00' in decoded or any(part.startswith('.') for part in decoded.split('/') if part):
        raise ValueError('Unsafe checkout resource path')
    path = (root / decoded.lstrip('/')).resolve()
    if path.is_dir():
        path = (path / 'index.html').resolve()
    if not path.is_relative_to(root) or path.suffix.lower() not in ALLOWED_SUFFIXES:
        raise ValueError('Resource is outside the permitted checkout files')
    return path


def template_key(source, asset_path):
    """Group representative captures by actual CSS and image styling, not region."""
    styles = re.findall(r'<style\b[^>]*>(.*?)</style>', source, re.I | re.S)
    image = next((tag for tag in re.findall(r'<img\b[^>]*>', source, re.I) if asset_path in tag), '')
    attributes = re.findall(r'\b(?:class|style)\s*=\s*([\"\'])(.*?)\1', image, re.I | re.S)
    value = '\n'.join(styles + [value for _, value in attributes])
    return hashlib.sha256(re.sub(r'\s+', ' ', value).encode()).hexdigest()[:12]


def measurement_failures(measurement, entry, width):
    failures = []
    if measurement.get('representativeCount') != 1:
        failures.append('representative image count is not one')
    if measurement.get('viewport') != width:
        failures.append('incorrect viewport width')
    if measurement.get('documentWidth', math.inf) > width + 1:
        failures.append('horizontal overflow')
    if (measurement.get('naturalWidth'), measurement.get('naturalHeight')) != (entry['width'], entry['height']):
        failures.append('wrong decoded image dimensions')
    w, h = measurement.get('imageWidth', 0), measurement.get('imageHeight', 0)
    if not all(isinstance(x, (int, float)) and math.isfinite(x) and x > 0 for x in (w, h)):
        failures.append('image is hidden or has invalid dimensions')
    else:
        if abs(w / h / (entry['width'] / entry['height']) - 1) > .01:
            failures.append('stretched or cropped image box')
        if w > entry['width'] + 1 or h > entry['height'] + 1:
            failures.append('image upscaled beyond native pixels')
    if measurement.get('imageLeft', -math.inf) < -1 or measurement.get('imageRight', math.inf) > width + 1:
        failures.append('image clipped horizontally')
    if measurement.get('imageVisibility') != 'visible' or measurement.get('imageOpacity', 0) <= 0:
        failures.append('representative image is not visible')
    if measurement.get('brokenImages') or measurement.get('pendingImages') or measurement.get('decodeTimedOut'):
        failures.append('broken or undecoded image')
    if measurement.get('h1Count') != 1:
        failures.append('H1 regression')
    return failures


def public_report(report, root, out):
    """Keep useful relative filenames/errors, not private executor path prefixes.

    Sanitization is recursive and non-mutating, including nested page/route and
    launch errors. Reports contain no agent/reviewer identity fields. Runtime
    home/temp prefixes also cover Playwright profile/cache paths in launch logs.
    """
    replacements = {}
    for path, marker in ((root, '<checkout>'), (out, '<artifacts>'),
                         (Path.home(), '<home>'), (Path.cwd(), '<working-directory>'),
                         (Path(tempfile.gettempdir()), '<temporary>')):
        absolute = str(Path(path).resolve())
        if absolute != '/':
            replacements.setdefault(absolute, marker)
    prefixes = sorted(replacements, key=len, reverse=True)
    def clean(value):
        if isinstance(value, str):
            for prefix in prefixes:
                # A boundary avoids redacting unrelated names such as /tmp2.
                value = re.sub(re.escape(prefix) + r'(?=$|[/\\\s\x27\x22:;,\)\]])',
                               lambda match: replacements[prefix], value)
            return value
        if isinstance(value, dict):
            return {clean(key): (str(item).replace('\\', '/').rsplit('/', 1)[-1]
                                 if key == 'screenshot' and item is not None else clean(item))
                    for key, item in value.items()}
        if isinstance(value, (list, tuple)):
            return [clean(item) for item in value]
        return value
    return clean(report)


def save_report(out, report, root=ROOT):
    temporary = out / 'report.json.tmp'
    temporary.write_text(json.dumps(public_report(report, root, out), ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    temporary.replace(out / 'report.json')


def _playwright_factory():
    # Lazy import makes pure contracts testable in the Pillow-only unit-test job.
    from playwright.sync_api import sync_playwright
    return sync_playwright()


MEASURE = r'''async (assetUrl) => {
    const images = [...document.images];
    images.forEach(img => { img.loading = 'eager'; });
    let timedOut = false;
    await Promise.race([
      Promise.all(images.map(img => img.decode().catch(() => null))),
      new Promise(resolve => setTimeout(() => {timedOut = true; resolve();}, 10000))
    ]);
    const matches = images.filter(img => (img.currentSrc || img.src) === assetUrl);
    const im = matches[0];
    if (im) im.scrollIntoView({block: 'center', inline: 'nearest'});
    await new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve)));
    const rect = im ? im.getBoundingClientRect() : {width:0,height:0,left:0,right:0};
    const style = im ? getComputedStyle(im) : null;
    return {
      representativeCount:matches.length, viewport:innerWidth,
      documentWidth:Math.max(document.documentElement.scrollWidth, document.body?.scrollWidth || 0),
      naturalWidth:im?.naturalWidth || 0, naturalHeight:im?.naturalHeight || 0,
      imageWidth:rect.width,imageHeight:rect.height,imageLeft:rect.left,imageRight:rect.right,
      imageVisibility:style?.visibility || 'missing',imageOpacity:Number(style?.opacity || 0),
      objectFit:style?.objectFit,decodeTimedOut:timedOut,
      brokenImages:images.filter(i=>i.complete&&!i.naturalWidth).map(i=>i.currentSrc||i.src),
      pendingImages:images.filter(i=>!i.complete).map(i=>i.currentSrc||i.src),
      h1Count:document.querySelectorAll('h1').length
    };
}'''


def check_page(context, name, entry, width, out, report, capture):
    row = {'page': name, 'width': width, 'template': entry['_template'],
           'measurement': None, 'exceptions': [], 'console_errors': [],
           'missing': [], 'request_failures': [], 'failures': [], 'screenshot': None}
    page = None
    try:
        page = context.new_page()
        page.set_default_timeout(15000)
        page.set_default_navigation_timeout(20000)
        page.on('pageerror', lambda error: row['exceptions'].append(str(error)))
        page.on('console', lambda message: row['console_errors'].append(message.text) if message.type == 'error' else None)
        page.on('response', lambda response: row['missing'].append({'url': response.url, 'status': response.status}) if response.status >= 400 else None)
        page.on('requestfailed', lambda request: row['request_failures'].append({'url': request.url, 'failure': request.failure}))
        page.on('dialog', lambda dialog: dialog.dismiss())
        response = page.goto(BASE + name, wait_until='load')
        if response is None or response.status != 200:
            row['failures'].append('main document failed')
        page.evaluate('() => document.fonts.ready')
        row['measurement'] = page.evaluate(MEASURE, BASE + entry['asset_path'])
        row['failures'].extend(measurement_failures(row['measurement'], entry, width))
    except Exception as exc:
        row['exceptions'].append(f'{type(exc).__name__}: {exc}')
        row['failures'].append('page check exception')
    finally:
        for key, label in [('exceptions', 'browser exception'), ('console_errors', 'console error'),
                           ('missing', 'missing resource'), ('request_failures', 'failed resource request')]:
            if row[key] and label not in row['failures']:
                row['failures'].append(label)
        pair = f'{entry["_template"]}:{width}'
        representative = pair not in report['captured_templates']
        # Reserve half the total budget for failures; no unbounded full-page PNGs.
        should_capture = bool(row['failures']) or (representative and report['representative_captures'] < capture // 2)
        if should_capture and page is not None and report['capture_count'] < capture:
            try:
                filename = f'{Path(name).stem}-{width}.jpg'
                page.screenshot(path=str(out / filename), type='jpeg', quality=80,
                                full_page=False, animations='disabled', timeout=10000)
                row['screenshot'] = filename
                report['capture_count'] += 1
                if not row['failures']:
                    report['representative_captures'] += 1
                    report['captured_templates'].append(pair)
            except Exception as exc:
                row['exceptions'].append(f'Screenshot: {type(exc).__name__}: {exc}')
                row['failures'].append('screenshot failed')
        elif should_capture or representative:
            row['screenshot_omitted'] = 'capture budget exhausted or page unavailable'
        if page is not None:
            try:
                page.close()
            except Exception as exc:
                row['exceptions'].append(f'Close: {exc}')
                row['failures'].append('page close failed')
    return row


def configure_context(context, root, report):
    def route_local(route):
        try:
            path = local_path(route.request.url, root)
            if path is None:
                report['external_requests_stubbed'] += 1
                resource_type = route.request.resource_type
                content_type = {'script': 'application/javascript', 'stylesheet': 'text/css',
                                'fetch': 'application/json', 'xhr': 'application/json'}.get(resource_type, 'text/plain')
                route.fulfill(status=200, body='{}' if resource_type in ('fetch', 'xhr') else '', content_type=content_type)
            elif route.request.method not in ('GET', 'HEAD'):
                route.fulfill(status=405, body='Read-only checkout QA')
            elif not path.is_file():
                route.fulfill(status=404, body='Missing local checkout resource')
            else:
                route.fulfill(status=200, body=path.read_bytes(),
                              content_type=mimetypes.guess_type(path.name)[0] or 'application/octet-stream')
        except Exception as exc:
            report['route_errors'].append(f'{route.request.url}: {exc}')
            route.fulfill(status=403, body='Disallowed checkout resource')
    context.route('**/*', route_local)
    context.route_web_socket('**/*', lambda socket: socket.close())


def run(out, executable=None, widths=DEFAULT_WIDTHS, capture=64, minimum_count=1, root=ROOT):
    out, root = Path(out), Path(root).resolve()
    out.mkdir(parents=True, exist_ok=True)
    report = {'scope': 'checkout bytes only; all nonlocal HTTP requests stubbed; service workers/WebSockets blocked',
              'result': 'RUNNING', 'widths': list(widths), 'accepted_pages': 0,
              'expected_viewports': 0, 'checked_viewports': 0, 'results': [], 'failures': [],
              'capture_limit': capture, 'capture_count': 0, 'representative_captures': 0,
              'captured_templates': [], 'external_requests_stubbed': 0, 'route_errors': []}
    save_report(out, report, root)
    try:
        if not widths or len(set(widths)) != len(widths) or any(not isinstance(w, int) or w < 320 for w in widths):
            raise ValueError('Widths must be unique integers of at least 320 pixels')
        if capture < 0 or minimum_count < 1:
            raise ValueError('Capture must be nonnegative and minimum-count at least one')
        entries = load_registry(root)
        report['accepted_pages'] = len(entries)
        report['expected_viewports'] = len(entries) * len(widths)
        if not entries:
            raise ValueError('Missing or empty accepted-original registry cannot pass browser QA')
        if len(entries) < minimum_count:
            raise ValueError(f'Only {len(entries)} accepted pages; minimum required is {minimum_count}')
        for name, entry in entries.items():
            try:
                page_path = local_path(BASE + name, root)
                if page_path is None or not page_path.is_file():
                    raise ValueError(f'Missing or unsafe registry page: {name}')
                registered_image(BASE + name, root=root, registry=entries)
                entry['_template'] = template_key(page_path.read_text(encoding='utf-8'), entry['asset_path'])
            except Exception as exc:
                # One missing/bad asset is a durable failure, not a reason to
                # abandon Chromium coverage for every other accepted page.
                entry['_template'] = 'preflight-failure'
                entry['_preflight_error'] = f'{type(exc).__name__}: {exc}'
        report['template_count'] = len({e['_template'] for e in entries.values()})
        save_report(out, report, root)
        with _playwright_factory() as pw:
            launch_options = {'headless': True}
            if executable:
                launch_options['executable_path'] = str(executable)
            browser = pw.chromium.launch(**launch_options)
            try:
                report['browser_version'] = browser.version
                for width in widths:
                    context = None
                    try:
                        context = browser.new_context(viewport={'width': width, 'height': VIEWPORT_HEIGHT},
                                                      device_scale_factor=1, service_workers='block')
                        configure_context(context, root, report)
                        for name, entry in sorted(entries.items()):
                            if entry.get('_preflight_error'):
                                row = {'page': name, 'width': width, 'stage': 'page preflight',
                                       'failures': [entry['_preflight_error']], 'screenshot': None}
                            else:
                                row = check_page(context, name, entry, width, out, report, capture)
                            report['results'].append(row)
                            report['checked_viewports'] = len(report['results'])
                            if row['failures']:
                                report['failures'].append(row)
                            save_report(out, report, root)
                    except Exception as exc:
                        report['failures'].append({'width': width, 'stage': 'context', 'error': f'{type(exc).__name__}: {exc}'})
                        save_report(out, report, root)
                    finally:
                        if context is not None:
                            try:
                                context.close()
                            except Exception as exc:
                                report['failures'].append({'width': width, 'stage': 'context close', 'error': str(exc)})
            finally:
                browser.close()
    except Exception as exc:
        report['failures'].append({'stage': 'setup/browser', 'error': f'{type(exc).__name__}: {exc}'})
    finally:
        if report['route_errors']:
            report['failures'].append({'stage': 'routing', 'errors': report['route_errors']})
        report['unchecked_viewports'] = report['expected_viewports'] - report['checked_viewports']
        if report['unchecked_viewports']:
            report['failures'].append({'stage': 'coverage', 'unchecked_viewports': report['unchecked_viewports']})
        report['result'] = 'FAIL' if report['failures'] or not report['checked_viewports'] else 'PASS'
        save_report(out, report, root)
    return public_report(report, root, out)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--chromium', default=None, help='Optional browser path; default uses Playwright-installed Chromium')
    parser.add_argument('--widths', nargs='+', type=int, default=list(DEFAULT_WIDTHS))
    parser.add_argument('--capture', type=int, default=64, help='Total viewport JPEG capture budget; failures stay in JSON even after the cap')
    parser.add_argument('--minimum-count', type=int, default=1)
    args = parser.parse_args()
    result = run(args.out, args.chromium, tuple(args.widths), args.capture, args.minimum_count)
    print(json.dumps({key: result[key] for key in ('result', 'accepted_pages', 'expected_viewports',
                                                'checked_viewports', 'unchecked_viewports', 'capture_count')}, ensure_ascii=False))
    raise SystemExit(result['result'] != 'PASS')
