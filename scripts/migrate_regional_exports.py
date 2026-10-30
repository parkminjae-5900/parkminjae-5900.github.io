#!/usr/bin/env python3
"""Switch accepted native PNG page links to reviewed lightweight JPEG exports.

Native image_gen PNG originals and receipts remain untouched outside the repo.
Only this task's newly-added, unreferenced production PNG copies are pruned.
No unrelated or pre-existing image asset is removed.
"""
import argparse
import copy
import json
import subprocess
from pathlib import Path

from export_regional_thumbnail import export_thumbnail, ENCODER_VERSION, ENCODER_ARGUMENTS
from regional_image_registry import ROOT, BASE, REGISTRY, load_registry
from repair_search_images import repair
from integrate_regional_thumbnails import (apply_transaction, recover_transaction, fingerprint,
    sha256, metadata_invariants, update_sitemap, verify_registered, dump, integration_lock, public_provenance)


def migrate(build):
    build = Path(build).resolve()
    recover_transaction(ROOT, build)
    manifest_path = build / 'manifest.json'
    manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
    registry_path = ROOT / REGISTRY
    registry_raw = registry_path.read_bytes()
    data = json.loads(registry_raw)
    entries = load_registry()
    writes, expected, replacements = {}, {}, {}
    converted = []
    for record in data['entries']:
        old_path = ROOT / record['asset_path']
        if old_path.suffix == '.jpg':
            continue
        if old_path.suffix != '.png':
            raise ValueError('Unsupported migration source: ' + record['asset_path'])
        native = build / 'assets' / record['source_filename']
        if sha256(native.read_bytes()) != record.get('source_sha256', record['sha256']):
            raise ValueError('Native original changed: ' + record['id'])
        if sha256(old_path.read_bytes()) != record['sha256']:
            raise ValueError('Current production original changed: ' + record['id'])
        exported = build / 'exports' / (Path(record['asset_path']).stem + '.jpg')
        exported.parent.mkdir(parents=True, exist_ok=True)
        info = export_thumbnail(native, exported)
        source_fp = fingerprint(native)
        fp = fingerprint(exported)
        old_url = BASE + record['asset_path']
        record['asset_path'] = str(Path(record['asset_path']).with_suffix('.jpg'))
        record['source_sha256'] = source_fp['sha256']
        record['source_pixel_sha256'] = source_fp['pixel_sha256']
        record['source_bytes'] = source_fp['bytes']
        record['encoding'] = info
        for key in ('sha256', 'pixel_sha256', 'bytes', 'width', 'height', 'mime_type', 'phash', 'dhash', 'scene_phash', 'scene_dhash'):
            record[key] = fp[key]
        target = ROOT / record['asset_path']
        current = target.read_bytes() if target.exists() else None
        if current is not None and sha256(current) != fp['sha256']:
            raise ValueError('Refusing to overwrite a different export: ' + record['asset_path'])
        expected[target] = sha256(current) if current is not None else None
        writes[target] = exported.read_bytes()
        page = ROOT / record['page']
        raw = page.read_bytes(); source = raw.decode('utf-8')
        expected[page] = sha256(raw)
        transition = copy.deepcopy(record)
        transition['previous_image'] = old_url
        updated, image = repair(source, BASE + record['page'], original_entry=transition)
        if metadata_invariants(source) != metadata_invariants(updated):
            raise ValueError('Unexpected non-image change: ' + record['page'])
        writes[page] = updated.encode('utf-8')
        replacements[BASE + record['page']] = image
        converted.append(record['id'])
    if converted:
        sitemap = ROOT / 'sitemap.xml'; raw = sitemap.read_bytes()
        expected[sitemap] = sha256(raw)
        writes[sitemap] = update_sitemap(raw.decode('utf-8'), replacements).encode('utf-8')
        expected[registry_path] = sha256(registry_raw)
        data['production_encoding'] = 'JPEG quality 92, 4:4:4, progressive; native PNG originals preserved separately'
        data['entries'] = [public_provenance(entry) for entry in data['entries']]
        writes[registry_path] = (json.dumps(data, ensure_ascii=False, indent=2) + '\n').encode('utf-8')
        apply_transaction(ROOT, build, writes, verify_registered, expected)
    # Resume-safe pruning after all references have been verified. Only this
    # task's PNG copy of a registered JPEG may be removed, never old site assets.
    accepted = load_registry()
    text_paths = [p for p in ROOT.rglob('*') if p.is_file() and '.git' not in p.parts
                  and p.suffix in ('.html', '.json', '.xml', '.css', '.js', '.mjs')]
    text_values = [(p, p.read_text(encoding='utf-8', errors='replace')) for p in text_paths]
    removed = []
    for record in accepted.values():
        if not record['asset_path'].endswith('.jpg'):
            continue
        path = (ROOT / record['asset_path']).with_suffix('.png')
        if not path.exists():
            continue
        if not path.is_relative_to(ROOT / 'assets/regional/originals'):
            raise ValueError('Unsafe PNG prune location')
        if sha256(path.read_bytes()) != record['source_sha256']:
            raise ValueError('PNG copy changed; do not prune: ' + str(path))
        relative = path.relative_to(ROOT).as_posix()
        if subprocess.run(['git', 'cat-file', '-e', manifest['source_commit'] + ':' + relative], cwd=ROOT,
                          stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).returncode == 0:
            raise ValueError('PNG existed before this task; do not remove: ' + relative)
        if any(relative in text for _, text in text_values):
            raise ValueError('PNG is still referenced; do not remove: ' + relative)
        # The unmodified native source must still exist before removing a copy.
        native = build / 'assets' / record['source_filename']
        if sha256(native.read_bytes()) != record['source_sha256']:
            raise ValueError('Native original preservation failed: ' + record['id'])
        path.unlink(); removed.append(relative)
    for request in manifest['entries']:
        request['asset_path'] = str(Path(request['asset_path']).with_suffix('.jpg'))
    manifest['production_export'] = {
        'format': 'JPEG', 'quality': 92, 'sampling': '4:4:4', 'progressive': True,
        'encoder': 'ImageMagick', 'encoder_version': ENCODER_VERSION,
        'encoder_arguments': list(ENCODER_ARGUMENTS),
        'geometry': 'unchanged native dimensions', 'source_originals': 'assets/{id}-funeral.png retained outside repo',
        'benchmark': 'export-benchmark/results.json', 'approved_by': 'parent technical production-export instruction'}
    dump(manifest_path, manifest)
    result = {'converted_to_jpeg': len(converted), 'converted_ids': converted,
              'task_owned_png_copies_removed': len(removed), 'native_png_originals_preserved': True,
              'current_production_bytes': sum(x['bytes'] for x in accepted.values()),
              'native_original_bytes': sum(x.get('source_bytes', x['bytes']) for x in accepted.values()),
              'verification': verify_registered()}
    dump(build / 'export-migration-result.json', result)
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--build-dir', required=True, type=Path)
    args = parser.parse_args()
    with integration_lock(args.build_dir):
        print(json.dumps(migrate(args.build_dir), ensure_ascii=False))
