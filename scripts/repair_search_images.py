"""Repair and validate search images on sitemap pages; preserve page content and brand.

Run after page generators: python scripts/repair_search_images.py --write
CI gate: python scripts/repair_search_images.py --check
"""
from pathlib import Path
from html.parser import HTMLParser
from urllib.parse import urlparse, unquote, urljoin
from html import escape, unescape
import argparse
import json
import re
import xml.etree.ElementTree as ET
from PIL import Image
from regional_image_registry import registered_image, apply_registered_body

ROOT = Path(__file__).resolve().parents[1]
BASE = 'https://www.dahamsangjo.co.kr/'
DEFAULT = BASE + 'assets/regional/seoul.jpg'
IMAGE_NS = 'http://www.google.com/schemas/sitemap-image/1.1'
SM_NS = 'http://www.sitemaps.org/schemas/sitemap/0.9'


class Tags(HTMLParser):
    def __init__(self, source):
        super().__init__()
        self.tags = []
        self.feed(source)

    def handle_starttag(self, tag, attrs):
        self.tags.append((tag, dict(attrs)))


def local(url):
    parsed = urlparse(url)
    if parsed.netloc and parsed.netloc != urlparse(BASE).netloc:
        raise ValueError('Off-site image: ' + url)
    p = (ROOT / unquote(parsed.path).lstrip('/')).resolve()
    if not p.is_relative_to(ROOT):
        raise ValueError('Invalid local image: ' + url)
    return p


def dimensions(url):
    with Image.open(local(url)) as im:
        im.load()  # Header dimensions alone do not detect corrupt/truncated files.
        return im.size, Image.MIME[im.format]


def metas(source):
    return {a.get('property', a.get('name')): a.get('content', '')
            for t, a in Tags(source).tags if t == 'meta'}


def primary_image(source, page_url):
    original = registered_image(page_url)
    if original:
        return BASE + original['asset_path']
    existing = metas(source).get('og:image', '')
    if existing and 'logo' not in existing.lower():
        dimensions(existing)
        return existing
    for tag, attrs in Tags(source.split('</head>', 1)[-1]).tags:
        if tag != 'img' or not attrs.get('src'):
            continue
        url = urljoin(page_url, attrs['src'])
        if any(x in url.lower() for x in ('logo', 'icon', 'avatar')):
            continue
        try:
            size, _ = dimensions(url)
            if size[0] >= 600:
                return url
        except (OSError, ValueError):
            continue
    return DEFAULT


def repair(source, page_url, original_entry=None):
    original = original_entry if original_entry is not None else registered_image(page_url)
    source = apply_registered_body(source, page_url, original)
    image = BASE + original['asset_path'] if original else primary_image(source, page_url)
    if original_entry is not None:
        # The integration transaction validates the actual native file before
        # planning writes; its destination may not exist until atomic commit.
        width, height, mime = original['width'], original['height'], original['mime_type']
    else:
        (width, height), mime = dimensions(image)
    title = re.search(r'<title[^>]*>(.*?)</title>', source, re.I | re.S).group(1)
    alt = '다함상조 장례안내 · AI 연출 이미지' if ('/regional/' in image or 'regional-funeral-base' in image) else re.sub('<[^>]+>', '', title)
    if original:
        alt = original['alt']
    head, body = re.split(r'</head>', source, maxsplit=1, flags=re.I)
    if original:
        # Generators may rebuild an HTML page before the enrichment task runs.
        # Keep the accepted representative in accurate WebPage schema even in
        # that intermediate output, without inventing facility/service facts.
        schemas = [json.loads(raw) for raw in re.findall(r'<script[^>]*type="application/ld\+json"[^>]*>(.*?)</script>', head, re.S)]
        def has_webpage(node):
            if isinstance(node, list): return any(has_webpage(item) for item in node)
            if isinstance(node, dict):
                kind = node.get('@type')
                return kind == 'WebPage' or (isinstance(kind, list) and 'WebPage' in kind) or any(has_webpage(value) for value in node.values())
            return False
        if not has_webpage(schemas):
            page_schema = {'@context': 'https://schema.org', '@type': 'WebPage',
                           '@id': page_url + '#webpage', 'url': page_url,
                           'name': unescape(re.sub('<[^>]+>', '', title)), 'inLanguage': 'ko-KR'}
            head += '\n<script type="application/ld+json">' + json.dumps(page_schema, ensure_ascii=False, separators=(',', ':')) + '</script>\n'

    def keep_tag(match):
        tag, attrs = Tags(match.group()).tags[0]
        field = attrs.get('property', attrs.get('name', ''))
        if tag == 'meta' and (field.startswith('og:image') or field in ('twitter:card', 'twitter:image', 'twitter:image:alt')):
            return ''
        if tag == 'link' and any('icon' in x for x in attrs.get('rel', '').split()):
            return ''
        return match.group()

    head = re.sub(r'<(?:meta|link)\b[^>]*>', keep_tag, head, flags=re.I)
    block = '\n<!-- Search icons and representative image: scripts/repair_search_images.py -->\n'
    block += '<link rel="shortcut icon" href="' + BASE + 'favicon.ico" type="image/x-icon">\n'
    block += '<link rel="icon" href="' + BASE + 'favicon.png" type="image/png" sizes="192x192">\n'
    block += '<link rel="apple-touch-icon" href="' + BASE + 'favicon.png">\n'
    values = {'og:image': image, 'og:image:secure_url': image, 'og:image:type': mime,
              'og:image:width': str(width), 'og:image:height': str(height), 'og:image:alt': alt}
    for key, value in values.items():
        block += f'<meta property="{key}" content="{escape(value, quote=True)}">\n'
    for key, value in {'twitter:card': 'summary_large_image', 'twitter:image': image, 'twitter:image:alt': alt}.items():
        block += f'<meta name="{key}" content="{escape(value, quote=True)}">\n'
    head = re.sub(r'\n?<!-- Search icons and representative image: scripts/repair_search_images.py -->\n?', '', head)
    # Allow large previews without overriding noindex or other crawling policy.
    if 'max-image-preview:large' not in head:
        if re.search(r'<meta\b[^>]*name="robots"', head, re.I):
            head = re.sub(r'(<meta\b[^>]*name="robots"[^>]*content=")([^"]*)',
                          lambda m: m[1] + m[2] + ',max-image-preview:large', head, count=1, flags=re.I)
        else:
            block += '<meta name="robots" content="max-image-preview:large">\n'
    # Use an actual body image so search crawlers can associate it with the page.
    body_urls = {urljoin(page_url, a.get('src', '')) for t, a in Tags(body).tags if t == 'img'}
    if image not in body_urls:
        figure = (f'\n<figure data-search-image="1" style="max-width:900px;margin:24px auto;padding:0 16px">'
                  f'<img src="{escape(image, quote=True)}" alt="{escape(alt, quote=True)}" width="{width}" height="{height}"'
                  ' loading="lazy" decoding="async" style="display:block;width:100%;height:auto;border-radius:12px">')
        if ('/regional/' in image or 'regional-funeral-base' in image):
            caption = original['caption'] if original else '장례 준비를 돕는 AI 연출 이미지입니다.'
            figure += '<figcaption style="font-size:13px;line-height:1.6;color:#665f58">' + escape(caption) + '</figcaption>'
        figure += '</figure>\n'
        body = re.sub(r'</main>|</body>', lambda m: figure + m.group(), body, count=1, flags=re.I)
    # Update existing WebPage metadata rather than creating competing page entities.
    def update_schema(match):
        data = json.loads(match[1])
        def walk(node):
            if isinstance(node, list):
                for item in node: walk(item)
            elif isinstance(node, dict):
                kind = node.get('@type')
                if kind == 'WebPage' or (isinstance(kind, list) and 'WebPage' in kind):
                    node['primaryImageOfPage'] = {'@type': 'ImageObject', 'url': image, 'width': width, 'height': height}
                for value in node.values(): walk(value)
        walk(data)
        return '<script type="application/ld+json">' + json.dumps(data, ensure_ascii=False, separators=(',', ':')) + '</script>'
    # Only rewrite blocks that contain WebPage (avoid unrelated schema churn).
    head = re.sub(r'<script(?![^>]*\bid=)[^>]*type="application/ld\+json"[^>]*>(.*?)</script>',
                  lambda m: update_schema(m) if 'WebPage' in m[1] else m.group(), head, flags=re.S)
    head = re.sub(r'[ \t]+(?=\n)', '', head)
    head = re.sub(r'\n{3,}', '\n\n', head)
    result = head.rstrip() + '\n' + block + '</head>' + body
    return re.sub(r'[ \t]+(?=\n)', '', result), image


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--write', action='store_true')
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    tree = ET.parse(ROOT / 'sitemap.xml')
    urls = tree.getroot().findall('{*}url')
    failures = []
    images = set()
    changed = 0
    for entry in urls:
        page_url = entry.find('{*}loc').text
        path = local(page_url)
        if path.is_dir(): path /= 'index.html'
        source = path.read_text(encoding='utf-8-sig')
        if args.write:
            updated, image = repair(source, page_url)
            if updated != source or b'\r\n' in path.read_bytes():
                path.write_text(updated, encoding='utf-8', newline='\n')
                changed += 1
            source = updated
            for old in entry.findall('{' + IMAGE_NS + '}image'): entry.remove(old)
            ET.SubElement(ET.SubElement(entry, '{' + IMAGE_NS + '}image'), '{' + IMAGE_NS + '}loc').text = image
        metadata = metas(source)
        try:
            image = metadata['og:image']
            images.add(image)
            (width, height), mime = dimensions(image)
            assert metadata['og:image:width'] == str(width)
            assert metadata['og:image:height'] == str(height)
            assert metadata['og:image:type'] == mime
            assert metadata['og:image:secure_url'] == image
            assert metadata['og:image:alt']
            assert metadata['twitter:image'] == image
            assert metadata['twitter:card'] == 'summary_large_image'
            tags = Tags(source).tags
            assert sum(t == 'meta' and a.get('property') == 'og:image' for t, a in tags) == 1
            assert any(t == 'link' and a.get('rel') == 'icon' and a.get('href') == BASE + 'favicon.png' for t, a in tags)
            assert any(t == 'img' and urljoin(page_url, a.get('src', '')) == image for t, a in Tags(source.split('</head>', 1)[-1]).tags)
            assert entry.find('{' + IMAGE_NS + '}image/{' + IMAGE_NS + '}loc').text == image
        except (KeyError, AssertionError, OSError, AttributeError) as exc:
            failures.append(str(path.relative_to(ROOT)) + ': ' + str(exc))
    assert dimensions(BASE + 'favicon.png')[0] == (192, 192)
    dimensions(BASE + 'favicon.ico')
    if args.write:
        ET.register_namespace('', SM_NS)
        ET.register_namespace('image', IMAGE_NS)
        tree.write(ROOT / 'sitemap.xml', encoding='utf-8', xml_declaration=True)
    print(json.dumps({'pages': len(urls), 'changed': changed, 'uniqueImages': len(images), 'failures': failures}, ensure_ascii=False))
    if failures: raise SystemExit(1)


if __name__ == '__main__':
    main()
