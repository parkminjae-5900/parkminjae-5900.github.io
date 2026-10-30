# Independent regional landmark thumbnails

## Goal
Give each of269 indexable regional landing pages its own independently generated image featuring local landmarks or characteristics. Keep URLs, approved logos, prices and facility facts stable; clearly disclose AI editorial imagery. The first Gangnam modern-city concept is the user-approved exception.

## Current state
Baseline: `ab9f8dfedb823ef6848d05207c62f55ca862b59e`. There are270 area pages:269 indexable pages and one excluded noindex migration page. All269 now have separate accepted originals, reviewed local-feature evidence and consistent body/OG/Twitter/WebPage/sitemap references. Source PNGs are preserved separately; production uses measured native-size JPEG exports.

## Requirements
- No filename-only, crop, tint, compression or text-only variants counted as originals.
- Preserve existing official logos and unrelated assets. Generated text is not a replacement logo.
- Describe imagery as AI editorial illustration, not documentary facility photography.
- Fail closed for missing/corrupt/unreviewed assets, repeated scenes or incomplete269-page coverage.
- Preserve source/export SHA256, dimensions, official reference URLs and measured encoding quality without publishing private executor paths or internal reviewer identities.
- Preserve page identity, prices, facilities and canonical URLs except the four explicitly approved administrative-guidance revisions below.

## Approved administrative guidance
The four legacy Incheon URLs keep their URLs/canonicals and now explain historical-to-current geography rather than claiming false one-to-one renames. Official source: https://www.incheon.go.kr/IC01070101 (effective2026-07-01).
- `area-incheon-jung-funeral.html`: old 중구 mainland belongs to part of 제물포구; old island territory is 영종구. The original four mainland facilities are not presented as an island list.
- `area-incheon-region-09f17808-funeral.html` and `area-incheon-seogu-funeral.html`: old 서구 covers current 서해구 and 검단구.
- `area-incheon-region-8fb2ce5a-funeral.html`: old 동구 is part of the larger 제물포구.
Original source-address strings, facility names, numbers, phones and prices remain intact. Old district address text is visibly marked as historical source data. Current-area guide links and an official reform source are provided. The seogu page's adjacent-area hospital reference is identified correctly using its official current address source. `area-incheon-junggu-funeral.html` remains byte-identical and noindex.

## Non-goals
Do not invent prices, operating conditions, ratings, facility availability or precise documentary landmark geometry. Do not alter unrelated business, privacy or account settings. Search-engine thumbnail selection cannot be guaranteed.

## Implementation steps
1. Inventory exact269 regional pages and baseline hashes.
2. Generate and visually review269 independent native PNGs with regional evidence.
3. Export same-dimension progressive JPEGs with ImageMagick7.1.1-43, quality92,4:4:4 sampling; no crop/resize/recolor/compositing.
4. Gate integration with source review, byte/pixel hashes, full/upper-scene pHash/dHash and luminance similarity checks.
5. Apply journaled atomic image/page/schema/sitemap updates, refusing newer edits and recovering interrupted writes safely.
6. Preserve approved images and four administrative transitions when generators run.
7. Run automated gates and isolated Chromium checks on the review branch before production integration.

## Verification plan
Static HTML project: Python syntax and unit tests, image/SEO/conversion/security gates, diff checks and deterministic scope comparisons against the baseline. Browser CI visits all269 accepted pages at360/390/430/1280, checks decode/dimensions/proportion/overflow/broken resources/console exceptions and records bounded representative screenshots. All network resources are checkout-local or stubbed; no analytics, submissions or external-link visits are sent. Incomplete browser coverage fails.

## Progress
- [x] Investigation
- [x] Implementation of all269 originals and four approved administrative transitions
- [x] Automated verification
- [ ] Desktop verification in isolated CI
- [ ] Mobile verification in isolated CI
- [x] Regression check
- [ ] Final review and authorized production verification

## Discoveries
The old regional generator explicitly made crop/tint variants; that fallback is removed. Some source facility records still use old district names despite a recent data-file date; historical labels are retained visibly rather than silently fabricating current addresses. Local browser execution was unavailable, so actual rendering verification is assigned to an isolated read-only CI runner, not inferred from static tests.

## Decisions
The registry contains only actual accepted assets. Pending assets are never referenced. Compression is solely a website export, not evidence of independent creation. Full269 coverage remains mandatory. Public provenance is neutral and relative-path based; original private generation receipts and unchanged PNGs are retained separately.

## Final local verification (2026-10-30)
All93 Python tests passed, including exporter fidelity, atomic recovery, conflict protection, administrative mappings and mocked browser contracts. Syntax,269-original strict coverage,414-page image check,387-page content/414-sitemap check,356-page conversion check, security scan, baseline scope guard and diff whitespace passed. All269 source and export hashes match. Native PNG total766,363,683bytes; website JPEG total179,485,191bytes. Minimum full-resolution luminanceSSIM0.98205, minimumPSNR36.29dB, maximum mean absolute channel error2.735/255. Original logo and pre-existing assets are retained. Mocked browser tests are not a runtime browser pass.

## Remaining limitations
Actual mobile/desktop Chromium results, review-branch publication and deployment verification are pending at this checkpoint. No production-completion claim is made before those results are established.
