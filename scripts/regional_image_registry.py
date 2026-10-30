"""Only reviewed, materialized regional originals may override existing imagery.

This module never generates, crops, recolors, or substitutes images. Pending
generation requests live outside this repository's accepted-image registry.
"""
from __future__ import annotations

import hashlib
import json
import re
from html import escape
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlparse, urljoin

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
BASE = 'https://www.dahamsangjo.co.kr/'
REGISTRY = 'data/regional-image-registry.json'


class Tags(HTMLParser):
    def __init__(self, source):
        super().__init__()
        self.tags = []
        self.feed(source)

    def handle_starttag(self, tag, attrs):
        self.tags.append((tag, dict(attrs)))


def load_registry(root=None):
    root = Path(root or ROOT)
    path = root / REGISTRY
    if not path.exists():
        return {}
    data = json.loads(path.read_text(encoding='utf-8'))
    if data.get('schema_version') != 1:
        raise ValueError('Unsupported regional image registry')
    entries = data['entries']
    if len({entry['page'] for entry in entries}) != len(entries):
        raise ValueError('Duplicate regional page in image registry')
    if len({entry['asset_path'] for entry in entries}) != len(entries):
        raise ValueError('An original cannot be shared between regional pages')
    return {entry['page']: entry for entry in entries}


def registered_image(page_url, root=None, registry=None):
    root = Path(root or ROOT).resolve()
    parsed = urlparse(page_url)
    if parsed.netloc and parsed.netloc != urlparse(BASE).netloc:
        return None
    page = parsed.path.lstrip('/')
    entry = (registry if registry is not None else load_registry(root)).get(page)
    if entry is None:
        return None
    if entry.get('status') != 'accepted' or not entry.get('visual_review', {}).get('passed'):
        raise ValueError('Unreviewed regional image: ' + page)
    path = (root / entry['asset_path']).resolve()
    if not path.is_relative_to(root / 'assets' / 'regional' / 'originals'):
        raise ValueError('Invalid original image location: ' + page)
    raw = path.read_bytes()  # Missing files fail closed; never silently fall back.
    if hashlib.sha256(raw).hexdigest() != entry['sha256']:
        raise ValueError('Changed original image bytes: ' + page)
    with Image.open(path) as im:
        im.load()
        if im.format not in ('PNG', 'JPEG') or min(im.size) < 600:
            raise ValueError('Invalid original raster: ' + page)
        if list(im.size) != [entry['width'], entry['height']]:
            raise ValueError('Incorrect original dimensions: ' + page)
        if Image.MIME[im.format] != entry['mime_type']:
            raise ValueError('Incorrect original MIME type: ' + page)
    return entry


def set_attributes(tag, changes):
    """Change only the requested HTML attributes, preserving surrounding markup."""
    for name, value in changes.items():
        encoded = escape(str(value), quote=True)
        pattern = r'(\s' + re.escape(name) + r'\s*=\s*)([\"\'])(.*?)\2'
        if re.search(pattern, tag, flags=re.I | re.S):
            tag = re.sub(pattern, lambda m: m[1] + '"' + encoded + '"', tag,
                         count=1, flags=re.I | re.S)
        else:
            tag = re.sub(r'\s*/?>$', lambda m: f' {name}="{encoded}"' + m[0], tag)
    return tag


def apply_registered_body(source, page_url, entry):
    """Replace the previous representative only; retain all unrelated page text."""
    if entry is None:
        return source
    if any(tag == 'meta' and attrs.get('name', '').lower() == 'robots'
           and 'noindex' in attrs.get('content', '').lower() for tag, attrs in Tags(source).tags):
        raise ValueError('Do not assign originals to noindex pages')
    head, body = re.split(r'</head>', source, maxsplit=1, flags=re.I)
    current = BASE + entry['asset_path']
    previous = entry['previous_image']

    def update_img(match):
        attrs = Tags(match[0]).tags[0][1]
        if urljoin(page_url, attrs.get('src', '')) not in (previous, current):
            return match[0]
        # Keep responsive CSS, loading, and priority behavior intact.
        return set_attributes(match[0], {'src': current, 'alt': entry['alt'],
                                        'width': entry['width'], 'height': entry['height']})

    body = re.sub(r'<img\b[^>]*>', update_img, body, flags=re.I)
    caption = escape(entry['caption'])
    def update_figure(match):
        figure = match[0]
        if current not in figure or not re.search(r'<figcaption\b', figure, re.I):
            return figure
        figure = re.sub(r'(<figcaption\b[^>]*>).*?(</figcaption>)',
                        lambda m: m[1] + caption + m[2], figure, flags=re.I | re.S)
        # Prefer the existing semantic caption to a second adjacent notice.
        return re.sub(r'<p data-regional-image-caption="1"[^>]*>.*?</p>', '', figure, flags=re.S)
    body = re.sub(r'<figure\b[^>]*>.*?</figure>', update_figure, body, flags=re.I | re.S)
    # Existing generator captions are exactly identified rather than replacing
    # arbitrary text about facilities or prices.
    body = re.sub(r'(<div class="caption">)AI 연출 이미지이며 특정 장례식장 실제 사진이 아닙니다\.(</div>)',
                  lambda m: m[1] + caption + m[2], body)
    body = re.sub(r'(<figcaption\b[^>]*>)장례 준비를 돕는 AI 연출 이미지입니다\.(</figcaption>)',
                  lambda m: m[1] + caption + m[2], body)
    # Songpa's approved template already has a paragraph caption directly after
    # the hero. Reuse that styled notice, removing only our adjacent duplicate.
    paragraph_caption = (r'(<img\b[^>]*src="' + re.escape(current) + r'"[^>]*>)\s*'
                         r'(?:<p data-regional-image-caption="1"[^>]*>.*?</p>\s*)?'
                         r'(<p class="caption"[^>]*>)'
                         r'AI 연출 이미지이며 특정 장례식장 실제 사진이 아닙니다\.(</p>)')
    body = re.sub(paragraph_caption, lambda m: m[1] + m[2] + caption + m[3],
                  body, flags=re.S)
    # Some original templates have no adjacent AI notice. Add one to the
    # representative figure/image only, without falsely describing real photos.
    if entry['caption'] not in body and caption not in body:
        pattern = r'(<img\b[^>]*src="' + re.escape(current) + r'"[^>]*>)'
        notice = '<p data-regional-image-caption="1" style="font-size:13px;line-height:1.6">' + caption + '</p>'
        body = re.sub(pattern, lambda m: m[1] + notice, body, count=1)
    return head + '</head>' + body


def existing_or_registered_image(page, root=None):
    """Generators preserve originals and never create tinted/cropped copies."""
    root = Path(root or ROOT)
    entry = registered_image(BASE + page, root)
    if entry:
        return BASE + entry['asset_path']
    path = root / page
    if path.exists():
        for tag, attrs in Tags(path.read_text(encoding='utf-8')).tags:
            if tag == 'meta' and attrs.get('property') == 'og:image':
                image = attrs.get('content', '')
                if image and 'logo' not in image.lower():
                    return image
    raise ValueError('Create and review an independent image before generating ' + page)
