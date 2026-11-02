"""Exact facility identities and rights-cleared real photographs; fail closed.

Raw source records and existing canonicals are immutable inputs. A source URL
is not a reuse license, and a hospital exterior is not a funeral-hall exterior.
"""
from __future__ import annotations
import hashlib
import ipaddress
import json
import re
import unicodedata
from html import escape
from pathlib import Path
from urllib.parse import urlparse
from PIL import Image
from regional_image_registry import Tags

ROOT = Path(__file__).resolve().parents[1]
BASE = 'https://www.dahamsangjo.co.kr/'
FIELDS = ('ctpv', 'sigungu', 'fcltNm', 'addr')
EVIDENCE = 'data/funeral-hall-evidence.json'
REGISTRY = 'data/funeral-hall-photo-registry.json'
PILOT = 'data/funeral-hall-page-pilot.json'
EXISTING_REUSE_ID = 'fh-2a32c8a884fc1574'
EXISTING_REUSE_SHA = 'dfef826107815c881541a8c551000f853444a639abca5ac666ffeeed6a3220a8'


def authorized_existing_site_reuse(entry):
    """Narrow exception for one unchanged existing asset and its exact facility.

This is not a public license or permission for other photos/sites/facilities.
Private permission evidence is retained outside the public repository.
"""
    scope = entry.get('reuse_scope', {})
    return (entry.get('facility_id') == EXISTING_REUSE_ID and entry.get('sha256') == EXISTING_REUSE_SHA
            and entry.get('source_sha256') == EXISTING_REUSE_SHA and entry.get('asset_path') == 'gallery9.jpg'
            and entry.get('source_url') == BASE + 'gallery9.jpg'
            and entry.get('license', {}).get('kind') == 'existing_site_authorization'
            and scope == {'site':BASE,'facility_id':EXISTING_REUSE_ID,'sha256':EXISTING_REUSE_SHA,'source_asset_path':'gallery9.jpg'})


def public_photo_metadata(entry):
    allowed = {'facility_id','identity_key','status','content_kind','asset_path','sha256','source_sha256','modifications',
               'width','height','mime_type','alt','caption','source_url','license','depiction','visual_review',
               'publication_date','photo_date','author','reuse_scope'}
    if set(entry) - allowed:
        raise ValueError('Unrecognized/private photo metadata fields')
    encoded = json.dumps(entry,ensure_ascii=False)
    if re.search(r'(?i)/workspace/|/home/agent/|library_file_id|libfile_|sentinel_|completion_token|download_url|local_asset_path|workspace_path|authorization_message_id|private_evidence|\bparent\b',encoded):
        raise ValueError('Private photo workflow data must not be published')


def identity_key(row):
    values = [unicodedata.normalize('NFC', str(row.get(k) or '')).strip() for k in FIELDS]
    if not all(values):
        raise ValueError('Incomplete facility identity')
    return json.dumps(values, ensure_ascii=False, separators=(',', ':'))


def facility_id(row):
    return 'fh-' + hashlib.sha256(identity_key(row).encode()).hexdigest()[:16]


def safe_url(url):
    p = urlparse(url)
    if p.scheme != 'https' or not p.hostname or p.username or p.password or any(c.isspace() for c in url):
        raise ValueError('Evidence needs a public HTTPS URL')
    if re.search(r'(?:token|signature|credential|x-amz|x-goog|sig)=', p.query, re.I):
        raise ValueError('Signed/private source URL is not publishable')
    if p.hostname == 'localhost' or p.hostname.endswith('.local'):
        raise ValueError('Private host is not public evidence')
    try:
        address = ipaddress.ip_address(p.hostname)
    except ValueError:
        address = None
    if address is not None and not address.is_global:
        raise ValueError('Private address is not public evidence')
    return url


def load_inputs(root=ROOT):
    root = Path(root)
    raw = json.loads((root / 'data/funeral-halls.json').read_text())
    rows = raw['items']
    records = {facility_id(x): x for x in rows}
    if len(records) != len(rows) or raw['count'] != len(rows):
        raise ValueError('Duplicate or inconsistent facility source records')
    evidence = json.loads((root / EVIDENCE).read_text())
    if evidence.get('schema_version') != 1:
        raise ValueError('Unsupported identity evidence schema')
    by_id, pages, holds = {}, {}, {}
    for item in evidence['entries']:
        ident = item['facility_id']
        if ident in by_id or ident not in records or item['identity_key'] != identity_key(records[ident]):
            raise ValueError('Stale or duplicate facility evidence: ' + ident)
        by_id[ident] = item
        for p in item.get('pages', []):
            page = p['page']
            if not re.fullmatch(r'[a-z0-9-]+\.html', page) or page in pages:
                raise ValueError('Unsafe/duplicate facility canonical mapping')
            if p.get('page_kind') not in ('primary', 'status') or p.get('indexable') is not True:
                raise ValueError('Only reviewed existing canonical pages may be linked')
            source = (root / page).read_text()
            tags = Tags(source).tags
            canonical = [a.get('href') for t, a in tags if t == 'link' and a.get('rel') == 'canonical']
            if canonical != [BASE + page] or p.get('canonical') != BASE + page:
                raise ValueError('Facility canonical changed: ' + page)
            if any('noindex' in a.get('content', '') for t, a in tags if t == 'meta' and a.get('name') == 'robots'):
                raise ValueError('Facility indexing policy changed: ' + page)
            pages[page] = ident
    for item in evidence['holds']:
        ident = item['facility_id']
        if ident in holds or ident not in records or item['identity_key'] != identity_key(records[ident]):
            raise ValueError('Stale/duplicate facility hold')
        holds[ident] = item
    return raw, records, by_id, pages, holds


def load_photos(root=ROOT, inputs=None):
    root = Path(root).resolve()
    raw, records, evidence, pages, holds = inputs or load_inputs(root)
    data = json.loads((root / REGISTRY).read_text())
    if data.get('schema_version') != 1:
        raise ValueError('Unsupported real-photo registry')
    accepted, assets, digests = {}, set(), set()
    for entry in data['entries']:
        public_photo_metadata(entry)
        ident = entry['facility_id']
        if ident in accepted or ident not in records or ident in holds:
            raise ValueError('Duplicate, unknown, or held photo identity')
        if entry.get('identity_key') != identity_key(records[ident]):
            raise ValueError('Photo identifies a different facility')
        if entry.get('status') != 'accepted' or entry.get('content_kind') != 'actual_facility_photo':
            raise ValueError('Only reviewed actual photographs may be published')
        license = entry.get('license', {})
        if license.get('commercial_use') is not True or not license.get('name') or not license.get('attribution'):
            raise ValueError('Photo commercial reuse permission/attribution is missing')
        if not isinstance(license.get('derivatives'), bool) or not isinstance(entry.get('modifications'), list):
            raise ValueError('Photo adaptation rights and modification history are required')
        if not re.fullmatch(r'[0-9a-f]{64}', entry.get('source_sha256', '')):
            raise ValueError('Original source byte hash is required')
        if not license['derivatives'] and (entry['modifications'] or entry['source_sha256'] != entry.get('sha256')):
            raise ValueError('No-derivatives license requires unchanged source bytes')
        if not authorized_existing_site_reuse(entry):
            safe_url(license['url'])
        elif license.get('url') is not None:
            raise ValueError('Scoped owner permission must not masquerade as a public license')
        safe_url(entry['source_url'])
        depiction = entry.get('depiction', {})
        if depiction.get('kind') not in ('funeral_hall_exterior', 'funeral_hall_interior'):
            raise ValueError('Only the actual funeral-hall exterior/interior is in scope; hospital campus images are not substitutes')
        safe_url(depiction['evidence_url'])
        if not depiction.get('notes'):
            raise ValueError('Photo depiction evidence is missing')
        review = entry.get('visual_review', {})
        privacy_ok = review.get('privacy_clear') is True or (review.get('privacy_clear') is False
                      and review.get('privacy_reviewed_for_authorized_existing_site_reuse') is True
                      and authorized_existing_site_reuse(entry))
        if any(review.get(k) is not True for k in ('passed', 'exact_facility')) or not privacy_ok or not review.get('reviewed_at'):
            raise ValueError('Actual-pixel identity/privacy review is incomplete')
        if not all(entry.get(k) for k in ('alt', 'caption', 'sha256')):
            raise ValueError('Missing public photo metadata')
        asset = entry['asset_path']
        existing_reuse = authorized_existing_site_reuse(entry)
        if not existing_reuse and not re.fullmatch(r'assets/funeral-halls/photos/[a-z0-9-]+\.(?:jpg|jpeg|png)', asset):
            raise ValueError('Unsafe photo asset path')
        path = (root / asset).resolve()
        if not existing_reuse and not path.is_relative_to(root / 'assets/funeral-halls/photos'):
            raise ValueError('Photo escapes allowed asset directory')
        blob = path.read_bytes()
        if hashlib.sha256(blob).hexdigest() != entry['sha256'] or asset in assets or entry['sha256'] in digests:
            raise ValueError('Changed or reused photo asset')
        with Image.open(path) as im:
            im.load()
            if im.format not in ('JPEG', 'PNG') or im.width < 600 or min(im.size) < 300:
                raise ValueError('Photo is not a useful static raster')
            if list(im.size) != [entry['width'], entry['height']] or Image.MIME[im.format] != entry['mime_type']:
                raise ValueError('Incorrect photo dimensions/MIME')
            if im.getexif().get(34853):
                raise ValueError('Public photo contains GPS EXIF')
        accepted[ident] = entry; assets.add(asset); digests.add(entry['sha256'])
    return accepted


def page_identity(source):
    ids = [a.get('content') for t, a in Tags(source).tags if t == 'meta' and a.get('name') == 'daham-facility-id']
    if len(ids) > 1:
        raise ValueError('Multiple facility identities on one page')
    return ids[0] if ids else None


def load_aliases(root=ROOT, inputs=None):
    root = Path(root)
    inputs = inputs or load_inputs(root)
    aliases = json.loads((root / EVIDENCE).read_text()).get('aliases', [])
    seen = set()
    for alias in aliases:
        page, target, ident = alias['page'], alias['canonical_page'], alias['facility_id']
        if not re.fullmatch(r'[a-z0-9-]+\.html', page) or page in seen or page in inputs[3] or inputs[3].get(target) != ident:
            raise ValueError('Unsafe or duplicate facility alias')
        seen.add(page)
    return aliases


def photo_policy(source, page_url, root=ROOT):
    """None = unrelated page; dict = exact photo-managed page (possibly pending)."""
    ident = page_identity(source)
    directory = '<meta name="daham-directory" content="source-records">' in source
    if not ident and not directory:
        return None
    inputs = load_inputs(root)
    photos = load_photos(root, inputs)
    page = urlparse(page_url).path.lstrip('/')
    pilot_data = json.loads((Path(root)/PILOT).read_text()) if (Path(root)/PILOT).exists() else {}
    pilots = pilot_data.get('facility_ids', []) + pilot_data.get('additional_photo_facility_ids', [])
    provisional_match = ident in pilots and page == f'funeral-halls/{ident}.html' and ident in inputs[1]
    alias_match = any(a['page'] == page and a['facility_id'] == ident for a in load_aliases(root, inputs))
    if ident and inputs[3].get(page) != ident and not provisional_match and not alias_match:
        raise ValueError('Page marker does not match exact facility canonical')
    if directory and not re.fullmatch(r'funeral-halls/(?:index\.html|page-[2-9]\d*\.html|page-1\d+\.html)?', page):
        raise ValueError('Directory marker cannot bypass another page image policy')
    return {'facility_id': ident, 'photo': photos.get(ident), 'directory': directory}


def figure(entry):
    e = lambda value: escape(str(value), quote=True)
    license = entry['license']
    license_text = (f'<a href="{e(license["url"])}" rel="license noopener">{e(license["name"])}</a>'
                    if license.get('url') else e(license['name']))
    return ('<figure data-facility-photo="1" class="facility-photo">'
            f'<img src="{BASE + e(entry["asset_path"])}" alt="{e(entry["alt"])}" '
            f'width="{entry["width"]}" height="{entry["height"]}" loading="lazy" decoding="async" style="max-width:{entry["width"]}px;margin:auto">'
            f'<figcaption>{e(entry["caption"])} <a href="{e(entry["source_url"])}" rel="noopener">사진 출처</a> · '
            f'{license_text} · {e(license["attribution"])}</figcaption></figure>')


def repair_photo_page(source, page_url, policy):
    """Never substitute regional AI art for an unavailable facility photograph."""
    photo = policy['photo']
    head, body = source.split('</head>', 1)
    def remove_meta(m):
        tag, a = Tags(m[0]).tags[0]
        key = a.get('property', a.get('name', ''))
        return '' if key.startswith('og:image') or key in ('twitter:image', 'twitter:image:alt', 'twitter:card') else m[0]
    head = re.sub(r'<meta\b[^>]*>', remove_meta, head, flags=re.I)
    # Remove only the previous managed representative and new photo slots.
    body = re.sub(r'<figure\b[^>]*data-search-image="1"[^>]*>.*?</figure>', '', body, flags=re.S)
    # Collection cards own their exact registry-backed photographs. They are not
    # the representative image of the directory page and must survive repair.
    if not policy['directory']:
        body = re.sub(r'<figure\b[^>]*data-facility-photo="1"[^>]*>.*?</figure>', '', body, flags=re.S)
    body = re.sub(r'<p\b[^>]*data-facility-photo-pending="1"[^>]*>.*?</p>', '', body, flags=re.S)
    image = BASE + photo['asset_path'] if photo else None
    block = '<meta name="twitter:card" content="summary_large_image">' if photo else '<meta name="twitter:card" content="summary">'
    if photo:
        vals = {'og:image': image, 'og:image:secure_url': image, 'og:image:type': photo['mime_type'],
                'og:image:width': photo['width'], 'og:image:height': photo['height'], 'og:image:alt': photo['alt']}
        block += ''.join(f'<meta property="{k}" content="{escape(str(v), quote=True)}">' for k, v in vals.items())
        block += f'<meta name="twitter:image" content="{image}"><meta name="twitter:image:alt" content="{escape(photo["alt"], quote=True)}">'
        visual = figure(photo)
    elif not policy['directory']:
        visual = '<p data-facility-photo-pending="1" class="photo-pending">실제 시설 사진 확인 중 · 시설 식별과 이용 권한을 확인한 사진만 제공합니다. AI 이미지나 다른 시설의 사진으로 대체하지 않습니다.</p>'
    else:
        visual = ''
    if visual:
        body = re.sub(r'</header>', lambda m: visual + m[0], body, count=1)
    def schema(m):
        data = json.loads(m[2])
        def walk(node):
            if isinstance(node, list):
                for x in node: walk(x)
            elif isinstance(node, dict):
                kind = node.get('@type')
                kinds = kind if isinstance(kind, list) else [kind]
                if any(t in kinds for t in ('WebPage', 'Article', 'FuneralHome', 'LocalBusiness')):
                    node.pop('primaryImageOfPage', None); node.pop('image', None)
                    if photo and 'WebPage' in kinds:
                        node['primaryImageOfPage'] = {'@type': 'ImageObject', 'url': image, 'width': photo['width'], 'height': photo['height']}
                for value in node.values(): walk(value)
        walk(data)
        encoded = json.dumps(data, ensure_ascii=False, separators=(',', ':')).replace('<', '\\u003c').replace('>', '\\u003e').replace('&', '\\u0026')
        return m[1] + encoded + '</script>'
    head = re.sub(r'(<script\b[^>]*type="application/ld\+json"[^>]*>)(.*?)</script>', schema, head, flags=re.S)
    head = re.sub(r'\n{3,}', '\n\n', head).rstrip()
    return head + '\n' + block + '\n</head>' + body, image
