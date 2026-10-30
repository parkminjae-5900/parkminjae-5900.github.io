#!/usr/bin/env python3
"""Resume integration of real, separately generated and visually reviewed PNGs.

Dry-run by default. No pending asset is referenced by a public page or registry.
Example:
  python scripts/integrate_regional_thumbnails.py --build-dir /path/to/build --write
  python scripts/integrate_regional_thumbnails.py --build-dir /path/to/build --check

The build directory contains manifest.json, assets/, and receipts/{id}.json.
Native PNG originals remain untouched outside the repo. Website assets are
standard Q92 4:4:4 progressive JPEG exports with unchanged native dimensions.
"""
from __future__ import annotations

import argparse
import base64
from contextlib import contextmanager
import fcntl
import hashlib
import json
import math
import re
from pathlib import Path
from urllib.parse import urljoin, urlparse
import xml.etree.ElementTree as ET

from PIL import Image

import regional_image_registry as registry_module
import repair_search_images as repair_module
from regional_image_registry import BASE, ROOT, REGISTRY, Tags, load_registry, registered_image

IMAGE_NS = 'http://www.google.com/schemas/sitemap-image/1.1'
COS = [[math.cos(math.pi * (2 * x + 1) * u / 64) for x in range(32)] for u in range(8)]


def dump(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + '.tmp')
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    temporary.replace(path)


def sha256(raw):
    return hashlib.sha256(raw).hexdigest()


def public_provenance(record):
    """Keep useful provenance without executor paths or internal reviewer IDs."""
    result = json.loads(json.dumps(record))
    result['visual_review'] = {'passed': bool(record.get('visual_review', {}).get('passed')),
                             'status': 'completed',
                             'notes': 'Actual image pixels, readable Korean labels, regional context, and visible AI disclosure reviewed.'}
    encoder = result.get('encoding', {}).get('encoder', {})
    if encoder.get('executable'):
        encoder['executable'] = Path(encoder['executable']).name
    if 'administrative_approval' in result:
        approval = result['administrative_approval']
        result['administrative_approval'] = {
            'status': 'approved_historical_to_current_guidance',
            'official_source': approval['official_source'],
            'effective_date': '2026-07-01', 'canonical_preserved': True,
            'no_false_one_to_one_mapping': True}
    if 'display_label_note' in result:
        result['display_label_note'] = 'Image display label uses the documented locality; historical-to-current guidance is identified separately where applicable.'
    return result


@contextmanager
def integration_lock(build):
    """A second process must never recover a batch that is still running."""
    path = Path(build) / '.integration.lock'
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('a+') as handle:
        try:
            fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise ValueError('Another integration/export process is active; do not attempt recovery') from exc
        try:
            yield
        finally:
            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


def atomic_bytes(path, raw):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + '.regional-tmp')
    temporary.write_bytes(raw)
    temporary.replace(path)


def recover_transaction(root, build):
    """Rollback an interrupted batch only when no intervening edit is found."""
    root = Path(root).resolve()
    journal = Path(build) / 'integration-transaction.json'
    if not journal.exists():
        return False
    data = json.loads(journal.read_text(encoding='utf-8'))
    restored = []
    # Check every target before restoring any of them. A newer user edit must
    # never be overwritten by recovery of a previous integration attempt.
    for item in data['files']:
        target = (root / item['path']).resolve()
        if not target.is_relative_to(root) or '.git' in target.relative_to(root).parts:
            raise ValueError('Unsafe transaction recovery path')
        before = base64.b64decode(item['before_base64']) if item['before_base64'] is not None else None
        current = target.read_bytes() if target.exists() else None
        if current != before and (current is None or sha256(current) != item['after_sha256']):
            raise ValueError('Interrupted transaction conflicts with a newer edit: ' + item['path'])
        restored.append((target, before))
    for target, before in restored:
        if before is None: target.unlink(missing_ok=True)
        else: atomic_bytes(target, before)
        # A hard interruption can occur after writing the tool-owned temporary
        # file but before its atomic rename. It must not become a stray asset.
        target.with_name(target.name + '.regional-tmp').unlink(missing_ok=True)
    journal.unlink()
    return True


def apply_transaction(root, build, writes, verify, expected_before):
    """Journal all writes before touching pages, PNGs, registry, or sitemap."""
    root = Path(root).resolve()
    journal = Path(build) / 'integration-transaction.json'
    if journal.exists():
        raise ValueError('An interrupted integration must be recovered first')
    files = []
    for path, raw in writes.items():
        path = Path(path).resolve()
        if not path.is_relative_to(root) or '.git' in path.relative_to(root).parts:
            raise ValueError('Unsafe integration destination')
        before = path.read_bytes() if path.exists() else None
        if path not in expected_before or (sha256(before) if before is not None else None) != expected_before[path]:
            raise ValueError('File changed after integration planning: ' + str(path.relative_to(root)))
        if before == raw:
            continue
        files.append({'path': path.relative_to(root).as_posix(),
                      'before_base64': base64.b64encode(before).decode('ascii') if before is not None else None,
                      'after_sha256': sha256(raw)})
    dump(journal, {'schema_version': 1, 'files': files})
    try:
        for item in files:
            path = root / item['path']
            atomic_bytes(path, writes[path])
        verify()
    except Exception:
        recover_transaction(root, build)
        raise
    journal.unlink()


def phash(im):
    """64-bit luminance DCT hash (analysis only; source pixels never change)."""
    pixels = list(im.convert('L').resize((32, 32), Image.Resampling.LANCZOS).tobytes())
    rows = [[sum(pixels[y * 32 + x] * COS[u][x] for x in range(32))
             for u in range(8)] for y in range(32)]
    values = [sum(rows[y][u] * COS[v][y] for y in range(32))
              for v in range(8) for u in range(8)]
    median = sorted(values[1:])[31]
    return f'{sum((value > median) << i for i, value in enumerate(values)):016x}'


def dhash(im):
    pixels = list(im.convert('L').resize((9, 8), Image.Resampling.LANCZOS).tobytes())
    return f'{sum((pixels[y * 9 + x] > pixels[y * 9 + x + 1]) << (y * 8 + x) for y in range(8) for x in range(8)):016x}'


def fingerprint(path, cache=None):
    raw = Path(path).read_bytes()
    digest = sha256(raw)
    if cache is not None and digest in cache:
        return cache[digest]
    with Image.open(path) as source:
        source.load()
        im = source.convert('RGB')
        # Compare the photographic/illustrated scene separately from the
        # shared title/footer convention. Crops here are analysis, not assets.
        scene = im.crop((0, 0, im.width, round(im.height * .65)))
        result = {
            'sha256': digest, 'bytes': len(raw), 'width': im.width, 'height': im.height,
            'mime_type': Image.MIME[source.format],
            'pixel_sha256': sha256(f'{im.width}x{im.height}:RGB:'.encode() + im.tobytes()),
            'phash': phash(im), 'dhash': dhash(im),
            'scene_phash': phash(scene), 'scene_dhash': dhash(scene),
            'scene_luminance': list(scene.convert('L').resize((16, 16), Image.Resampling.LANCZOS).tobytes()),
        }
    if cache is not None:
        cache[digest] = result
    return result


def distance(a, b, key):
    return (int(a[key], 16) ^ int(b[key], 16)).bit_count()


def compare(a, b):
    result = {key + '_distance': distance(a, b, key)
              for key in ('phash', 'dhash', 'scene_phash', 'scene_dhash')}
    result['scene_rmse'] = round(math.sqrt(sum((x-y)**2 for x, y in zip(a['scene_luminance'], b['scene_luminance'])) / 256) / 255, 4)
    result['exact_file'] = a['sha256'] == b['sha256']
    result['exact_pixels'] = a['pixel_sha256'] == b['pixel_sha256']
    result['suspicious'] = (result['exact_file'] or result['exact_pixels']
        or (result['phash_distance'] <= 6 and result['dhash_distance'] <= 10)
        or (result['scene_phash_distance'] <= 6 and result['scene_dhash_distance'] <= 10)
        or result['scene_rmse'] <= .055)
    return result


def validate_receipt(receipt, request, build):
    if receipt.get('id') != request['id']:
        raise ValueError('Receipt ID does not match the requested page')
    if request.get('status') == 'blocked_label':
        raise ValueError('Regional creative or place-name review is pending')
    if request.get('status') == 'awaiting_administrative_page_update':
        raise ValueError('Approved administrative guidance must be applied before image integration')
    if receipt.get('generator') != 'image_gen' or receipt.get('independent_generation') is not True:
        raise ValueError('Independent native image generation evidence is required')
    if not receipt.get('generation_prompt') or not receipt.get('scene_summary'):
        raise ValueError('Generation prompt and independent scene summary are required')
    if receipt.get('status') in ('needs_revision', 'blocked_label', 'needs_label_mapping') or request.get('status') == 'blocked_label':
        raise ValueError('Regional creative or place-name review is pending')
    if request.get('approved_display_label') and receipt.get('display_label') != request['approved_display_label']:
        raise ValueError('Use the approved stable locality display label, not an obsolete province designation')
    if request.get('approved_display_label'):
        # A prompt may explicitly request the exact heading over multiple quoted
        # lines, e.g. "인천 옛 서구" then "권역". Preserve the real prompt verbatim.
        quoted_lines = ' '.join(re.findall(r'["“](.*?)["”]', receipt['generation_prompt']))
        if request['approved_display_label'] not in receipt['generation_prompt'] and request['approved_display_label'] not in quoted_lines:
            raise ValueError('Generation prompt must request the approved stable locality display label')
    # The user explicitly approved Gangnam, then requested recognizable local
    # landmarks/features for every remaining original. A generic concept scene
    # with a locality title alone no longer satisfies that creative brief.
    if request['id'] != 'gangnam':
        if not receipt.get('local_feature'):
            raise ValueError('Documented region-specific landmark/feature is required')
        source_url = receipt.get('source_url', '')
        if not isinstance(source_url, str) or urlparse(source_url).scheme != 'https' or not urlparse(source_url).netloc:
            raise ValueError('Official local-feature source URL is required')
    review = receipt.get('visual_review', {})
    if review.get('passed') is not True or not review.get('reviewer') or not review.get('notes'):
        raise ValueError('Actual-pixel visual review evidence is required')
    path = Path(receipt['source_path']).resolve()
    if not path.is_relative_to((build / 'assets').resolve()):
        raise ValueError('Receipt source must be inside this build assets directory')
    if path.suffix.lower() != '.png':
        raise ValueError('Retain the native generated PNG original')
    with Image.open(path) as im:
        im.load()
        if im.format != 'PNG' or min(im.size) < 600 or max(im.size) > 8192:
            raise ValueError('Invalid or undersized native PNG')
        if getattr(im, 'is_animated', False):
            raise ValueError('Thumbnail originals must be static')
    return path


def metadata_invariants(source):
    """Protect non-image identity/business metadata against integration changes."""
    tags = Tags(source).tags
    image_fields = {'twitter:card', 'twitter:image', 'twitter:image:alt'}
    metadata = [(tag, a) for tag, a in tags if (
        tag == 'link' and a.get('rel') == 'canonical') or (
        tag == 'meta' and not a.get('property', a.get('name', '')).startswith('og:image')
        and a.get('property', a.get('name', '')) not in image_fields)]
    prices = re.findall(r'\d[\d,]*(?:\.\d+)?\s*(?:만원|원)', source.split('</head>', 1)[-1])
    links = [(t, a.get('href')) for t, a in tags if t == 'a']
    headings = re.findall(r'<h[1-6]\b[^>]*>.*?</h[1-6]>', source, re.S | re.I)
    schemas = [json.loads(raw) for raw in re.findall(r'<script[^>]*type="application/ld\+json"[^>]*>(.*?)</script>', source, re.S)]
    def without_primary_image(value):
        if isinstance(value, dict):
            return {key: without_primary_image(item) for key, item in value.items() if key != 'primaryImageOfPage'}
        if isinstance(value, list): return [without_primary_image(item) for item in value]
        return value
    body = source.split('</head>', 1)[-1]
    body = re.sub(r'<img\b[^>]*>', '', body, flags=re.I)
    body = re.sub(r'<figcaption\b[^>]*>.*?</figcaption>', '', body, flags=re.I | re.S)
    body = re.sub(r'<div class="caption">.*?</div>', '', body, flags=re.S)
    body = re.sub(r'<p data-regional-image-caption="1"[^>]*>.*?</p>', '', body, flags=re.S)
    body = re.sub(r'<p class="caption"[^>]*>[^<]*AI 연출 이미지[^<]*</p>', '', body, flags=re.S)
    return metadata, prices, links, headings, body, without_primary_image(schemas)


def update_sitemap(source, replacements):
    """Rewrite image URLs only in the exact corresponding sitemap entries."""
    changed = set()
    def update(match):
        block = match[0]
        url = re.search(r'<loc>(.*?)</loc>', block)[1]
        if url not in replacements:
            return block
        if url in changed:
            raise ValueError('Duplicate target sitemap URL: ' + url)
        image = replacements[url]
        tag = f'<image:image><image:loc>{image}</image:loc></image:image>'
        if re.search(r'<image:image>.*?</image:image>', block, re.S):
            block = re.sub(r'<image:image>.*?</image:image>', tag, block, count=1, flags=re.S)
        else:
            block = block.replace('</url>', tag + '</url>')
        changed.add(url)
        return block
    result = re.sub(r'<url>.*?</url>', update, source, flags=re.S)
    if changed != set(replacements):
        raise ValueError('Missing or duplicate target sitemap URL')
    ET.fromstring(result)
    return result


def verify_registered(root=ROOT, require_count=None):
    root = Path(root)
    if not (root / REGISTRY).is_file():
        raise ValueError('Missing accepted-original registry; no coverage can be verified')
    entries = load_registry(root)
    if not entries:
        raise ValueError('Empty accepted-original registry; no coverage can be verified')
    eligible = {path.name for path in root.glob('area-*-funeral.html')
                if 'noindex' not in repair_module.metas(path.read_text(encoding='utf-8')).get('robots', '').lower()}
    if set(entries) - eligible:
        raise ValueError('Registry includes non-indexable or out-of-scope pages')
    if require_count is not None and len(entries) != require_count:
        raise ValueError(f'Expected {require_count} originals, found {len(entries)}')
    if require_count is not None and set(entries) != eligible:
        raise ValueError('Required complete regional image coverage has missing pages')
    sitemap = ET.parse(root / 'sitemap.xml')
    image_map = {entry.find('{*}loc').text: entry.find('{' + IMAGE_NS + '}image/{' + IMAGE_NS + '}loc').text
                 for entry in sitemap.getroot().findall('{*}url')
                 if entry.find('{' + IMAGE_NS + '}image/{' + IMAGE_NS + '}loc') is not None}
    fingerprints = {}
    for page, record in entries.items():
        entry = registered_image(BASE + page, root, entries)
        if entry.get('generator') != 'image_gen' or entry.get('independent_generation') is not True:
            raise ValueError(page + ': missing independent-generation evidence')
        if entry['id'] != 'gangnam' and (not entry.get('local_feature') or not entry.get('source_url')):
            raise ValueError(page + ': missing local-feature evidence')
        if entry['asset_path'].endswith('.jpg'):
            encoding = entry.get('encoding', {})
            settings = encoding.get('encoder', {})
            if (encoding.get('sha256') != entry['sha256']
                    or encoding.get('source_sha256') != entry.get('source_sha256')
                    or settings.get('quality') != 92 or settings.get('chroma_sampling') != '4:4:4'
                    or settings.get('progressive') is not True):
                raise ValueError(page + ': invalid source/export provenance or encoder settings')
            with Image.open(root / entry['asset_path']) as im:
                if not (im.info.get('progressive') or im.info.get('progression')) or [(x[1], x[2]) for x in im.layer] != [(1, 1)] * 3:
                    raise ValueError(page + ': production JPEG is not progressive 4:4:4')
        fp = fingerprint(root / entry['asset_path'])
        for other_page, other_fp in fingerprints.items():
            if compare(fp, other_fp)['suspicious']:
                raise ValueError(page + ': possible repeated scene with ' + other_page)
        fingerprints[page] = fp
        source = (root / page).read_text(encoding='utf-8')
        metadata = repair_module.metas(source)
        url = BASE + entry['asset_path']
        expected = {'og:image': url, 'og:image:secure_url': url,
                    'og:image:type': entry['mime_type'], 'og:image:width': str(entry['width']),
                    'og:image:height': str(entry['height']), 'og:image:alt': entry['alt'],
                    'twitter:image': url, 'twitter:image:alt': entry['alt']}
        for field, value in expected.items():
            if metadata.get(field) != value:
                raise ValueError(f'{page}: incorrect {field}')
        tags = Tags(source).tags
        imgs = [attrs for tag, attrs in tags if tag == 'img' and urljoin(BASE + page, attrs.get('src', '')) == url]
        if len(imgs) != 1 or any(imgs[0].get(k) != str(v) for k, v in {'width': entry['width'], 'height': entry['height'], 'alt': entry['alt']}.items()):
            raise ValueError(page + ': missing, duplicate, or incorrect representative body image')
        if entry['caption'] not in source:
            raise ValueError(page + ': missing explicit generated-image caption')
        if image_map.get(BASE + page) != url:
            raise ValueError(page + ': incorrect sitemap image')
        schemas = [json.loads(raw) for raw in re.findall(r'<script[^>]*type="application/ld\+json"[^>]*>(.*?)</script>', source, re.S)]
        found = []
        def walk(value):
            if isinstance(value, dict):
                kind = value.get('@type')
                if kind == 'WebPage' or (isinstance(kind, list) and 'WebPage' in kind):
                    found.append(value.get('primaryImageOfPage'))
                for sub in value.values(): walk(sub)
            elif isinstance(value, list):
                for sub in value: walk(sub)
        walk(schemas)
        if not found or any(v != {'@type': 'ImageObject', 'url': url, 'width': entry['width'], 'height': entry['height']} for v in found):
            raise ValueError(page + ': incorrect WebPage image schema')
    return {'registered_originals': len(entries), 'checked': len(entries),
            'indexable_regional_pages': len(eligible), 'coverage_complete': set(entries) == eligible,
            'unassigned_indexable_pages': len(eligible - set(entries)),
            'scope': 'accepted assets and their page links', 'result': 'PASS'}


def run(build, write=False, check=False, require_count=None):
    if check:
        return verify_registered(require_count=require_count)
    build = Path(build).resolve()
    if (build / 'integration-transaction.json').exists():
        if not write:
            raise ValueError('Interrupted integration found; run --write for guarded rollback and resume')
        recover_transaction(ROOT, build)
    manifest = json.loads((build / 'manifest.json').read_text(encoding='utf-8'))
    requests = {entry['id']: entry for entry in manifest['entries'] if entry['status'] != 'preserved'}
    registry_path = ROOT / REGISTRY
    registry_before = registry_path.read_bytes() if registry_path.exists() else None
    registry = load_registry()
    cache_path = build / 'fingerprint-cache.json'
    cache = json.loads(cache_path.read_text()) if cache_path.exists() else {}
    refs = {}
    # All old common and preserved originals are compared, not just new files.
    for request in manifest['entries']:
        local = ROOT / request['previous_image'].removeprefix(BASE)
        key = str(local.relative_to(ROOT))
        if key not in refs: refs[key] = fingerprint(local, cache)
    for page, entry in registry.items():
        registered_image(BASE + page, ROOT, registry)
        refs[entry['id']] = fingerprint(ROOT / entry['asset_path'], cache)
    candidates, blocked = [], []
    for receipt_path in sorted((build / 'receipts').glob('*.json')):
        try:
            receipt = json.loads(receipt_path.read_text(encoding='utf-8'))
        except (OSError, json.JSONDecodeError) as exc:
            blocked.append({'id': receipt_path.stem, 'reason': 'Receipt incomplete or unreadable; retry after producer finishes: ' + str(exc)})
            continue
        ident = receipt.get('id')
        if ident not in requests:
            blocked.append({'id': ident, 'reason': 'Unknown or preserved page receipt'})
            continue
        request = requests[ident]
        try:
            original = validate_receipt(receipt, request, build)
            target = (ROOT / request['asset_path']).resolve()
            if not target.is_relative_to((ROOT / 'assets/regional/originals').resolve()) or target.suffix != '.jpg':
                raise ValueError('Invalid manifest production JPEG destination')
            fp = fingerprint(original, cache)
            if request['page'] in registry:
                existing = registry[request['page']]
                if existing.get('source_sha256', existing['sha256']) != fp['sha256']:
                    raise ValueError('Existing accepted original differs; explicit replacement review required')
                continue
            raw_page = (ROOT / request['page']).read_bytes()
            if sha256(raw_page) != request['source_page_sha256']:
                raise ValueError('Page changed since inventory; rebase and review before integration')
            similar = []
            nearest = None
            for other, other_fp in refs.items():
                comparison = compare(fp, other_fp)
                pair = {'other': other, **comparison}
                if comparison['suspicious']: similar.append(pair)
                if nearest is None or comparison['scene_phash_distance'] < nearest['scene_phash_distance']:
                    nearest = pair
            if similar:
                raise ValueError('Potential repeated scene; independent review/regeneration required: ' + json.dumps(similar, ensure_ascii=False))
            from export_regional_thumbnail import export_thumbnail
            exported = build / 'exports' / Path(request['asset_path']).name
            exported.parent.mkdir(parents=True, exist_ok=True)
            encoding = export_thumbnail(original, exported)
            asset_fp = fingerprint(exported, cache)
            record = {key: request[key] for key in ('id', 'page', 'region_label', 'page_label', 'asset_path', 'previous_image', 'alt', 'caption', 'source_page_sha256')}
            record['display_label'] = receipt.get('display_label') or request['region_label']
            record['source_page_region_label'] = request['region_label']
            if receipt.get('display_label'):
                label = receipt['display_label']
                record['alt'] = label + ' 장례 안내를 위한 독립 AI 연출 이미지 · 실제 시설 사진 아님'
                record['caption'] = label + ' 장례 안내용 AI 연출 이미지이며, 특정 장례식장의 실제 모습이 아닙니다.'
                record['display_label_note'] = receipt.get('display_label_note', 'Stable locality used in image only; source page title and canonical are unchanged')
            if request.get('caption_context'):
                record['caption'] += ' ' + request['caption_context']
                record['administrative_context'] = request['caption_context']
                record['administrative_approval'] = request['label_validation']
            record.update({key: asset_fp[key] for key in ('sha256', 'pixel_sha256', 'bytes', 'width', 'height', 'mime_type', 'phash', 'dhash', 'scene_phash', 'scene_dhash')})
            record.update({'source_sha256': fp['sha256'], 'source_pixel_sha256': fp['pixel_sha256'],
                           'source_bytes': fp['bytes'], 'encoding': encoding})
            record.update({'status': 'accepted', 'generator': 'image_gen',
                           'generation_prompt': receipt['generation_prompt'], 'scene_summary': receipt['scene_summary'],
                           'independent_generation': True, 'visual_review': receipt['visual_review'],
                           'source_filename': original.name, 'nearest_scene_review': nearest})
            if ident == 'gangnam':
                record['creative_approval'] = 'User-approved Gangnam example; later regional-feature requirement applies to other pages'
            else:
                record['local_feature'] = receipt['local_feature']
                record['source_url'] = receipt['source_url']
            candidates.append((request, record, exported))
            refs[ident] = fp
        except (ValueError, OSError, KeyError) as exc:
            blocked.append({'id': ident, 'reason': str(exc)})
    dump(cache_path, cache)
    if write and candidates:
        writes, replacements, expected_before = {}, {}, {}
        for request, record, original in candidates:
            dest = ROOT / record['asset_path']
            before = dest.read_bytes() if dest.exists() else None
            if before is not None and sha256(before) != record['sha256']:
                raise ValueError('Refusing to overwrite unrelated asset: ' + str(dest))
            expected_before[dest] = sha256(before) if before is not None else None
            writes[dest] = original.read_bytes()
            if sha256(writes[dest]) != record['sha256']:
                raise ValueError('Generated source changed during integration: ' + record['id'])
            registry[record['page']] = record
            path = ROOT / record['page']
            source_raw = path.read_bytes()
            if sha256(source_raw) != request['source_page_sha256']:
                raise ValueError('Page changed before transaction planning: ' + record['page'])
            expected_before[path] = sha256(source_raw)
            source = source_raw.decode('utf-8')
            updated, image = repair_module.repair(source, BASE + record['page'], original_entry=record)
            if metadata_invariants(source) != metadata_invariants(updated):
                raise ValueError('Unexpected identity/content change: ' + record['page'])
            writes[path] = updated.encode('utf-8')
            replacements[BASE + record['page']] = image
        sitemap = ROOT / 'sitemap.xml'
        sitemap_raw = sitemap.read_bytes()
        expected_before[sitemap] = sha256(sitemap_raw)
        writes[sitemap] = update_sitemap(sitemap_raw.decode('utf-8'), replacements).encode('utf-8')
        for entry in registry.values():
            entry.setdefault('source_page_sha256', requests[entry['id']]['source_page_sha256'])
        writes[ROOT / REGISTRY] = (json.dumps({'schema_version': 1,
            'source_repository': manifest['source_repository'], 'source_commit': manifest['source_commit'],
            'expected_originals': len(requests),
            'production_encoding': 'JPEG quality 92, 4:4:4, progressive; native PNG originals preserved separately',
            'purpose': 'Accepted separate original images; pending requests are never published',
            'entries': sorted((public_provenance(e) for e in registry.values()), key=lambda x: x['page'])}, ensure_ascii=False, indent=2) + '\n').encode('utf-8')
        expected_before[registry_path] = sha256(registry_before) if registry_before is not None else None
        apply_transaction(ROOT, build, writes, verify_registered, expected_before)
    # Even a no-new-assets resume must not report success for stale metadata.
    if registry_before is not None and not (write and candidates):
        verify_registered()
    accepted_ids = {entry['id'] for entry in load_registry().values()}
    report = {'mode': 'write' if write else 'dry-run', 'new_ready': len(candidates),
              'accepted': len(accepted_ids), 'required': len(requests),
              'label_holds': sorted(ident for ident, request in requests.items() if request.get('status') == 'blocked_label'),
              'remaining': sorted(set(requests) - accepted_ids), 'blocked': blocked,
              'new_ids': [record['id'] for _, record, _ in candidates]}
    dump(build / 'coverage-ledger.json', report)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--build-dir', type=Path)
    parser.add_argument('--write', action='store_true')
    parser.add_argument('--check', action='store_true')
    parser.add_argument('--require-count', type=int)
    args = parser.parse_args()
    if args.write and args.check: parser.error('Choose --write or --check')
    if not args.check and not args.build_dir: parser.error('--build-dir is required for integration')
    try:
        if args.check:
            report = run(args.build_dir, args.write, args.check, args.require_count)
        else:
            with integration_lock(args.build_dir):
                report = run(args.build_dir, args.write, args.check, args.require_count)
    except (ValueError, OSError, KeyError) as exc:
        raise SystemExit(str(exc))
    print(json.dumps(report, ensure_ascii=False))
    if report.get('blocked'): raise SystemExit(1)


if __name__ == '__main__':
    main()
