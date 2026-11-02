# Family funeral / no-hall guidance and verified real facility photographs

## Goal
Preserve established search URLs while making family-funeral and no-hall preparation useful by area and by verified individual facility. Regional artwork remains distinct; individual facilities may show only identity-verified, rights-cleared actual photographs.

## Current state
Source main is `0e0f2db33d8d75196ccde90897bdf7cb711c5988`. There are 269 indexable regional canonical URLs and one noindex regional alias; this is not 269 current municipalities. The source dataset contains 1,080 records. Recovered identity evidence maps 75 existing primary pages plus one operational-status page. The 1,020 old product/visitor combination pages remain noindex and excluded from the sitemap. Existing 269 regional original assets are preserved byte-for-byte.

## Requirements
- Use existing regional and facility canonical URLs; do not generate thin individual pages from raw records alone.
- Preserve raw data, current price scan files, product prices, calculations, telephone numbers, and current indexing restrictions.
- Distinguish historical address labels from current administrative boundaries.
- Separate company service prices from facility/food/cremation/burial costs; never imply all facilities accept no-hall arrangements.
- Publish real photos only with exact facility identity, safe public provenance, commercial reuse permission, attribution, actual-pixel depiction review and privacy review.
- Missing/held photos remain explicit text, not AI substitutions or photos of another institution.
- Static no-JavaScript directory, honest source age/coverage, accessible links, mobile and desktop QA, synchronized metadata and sitemap.

## Non-goals
No changes to price engines, phones, package catalog, raw source records, old AI-photo branch, user data, or unknown facility operation status. No automatically promoted 1,020 combination pages. No fabricated reviews/availability/partnerships. No SEO ranking guarantee.

## Implementation steps
1. Recover only exact identity mappings, 69 display aliases, 43 conflict notes and seven holds into an audited sidecar; quarantine obsolete image registry.
2. Add fail-closed real-photo validation and remove AI fallback from photo-managed facility pages.
3. Add useful family/no-hall intent sections to established regional and primary facility pages; retain current operational-status page.
4. Add 22 static paginated directory pages; preserve the 76 existing facility canonical URLs. Reserve one canonical for every remaining exact facility identity and generate ten source-specific individual pilot pages. Five have independently sourced text sufficient for index-candidate review; five remain noindex for insufficient text evidence. The other 994 paths remain planned/unpublished pending meaningful facility-specific content review.
5. Apply independently sourced eight-page content pilot and approved actual photos when evidence is available.
6. Add deterministic generation checks, exact identity/rights/privacy tests, and browser CI for mobile/desktop and no-JavaScript navigation.
7. Review final diff, current-main lease, all CI and live source hashes before any publication claim.

## Verification plan
Python compilation/unittest, existing SEO/security/search checks, photo and image checks, full 269 regional-image gate, noindex/sitemap consistency, raw-price-source hash preservation. Real Chromium at 360/390/430/1280 widths, screenshot inspection, overflow, images, console, directory search and no-JavaScript links. CI must pass on exact submitted commit before deployment.

## Risks
Automated enrichment previously forced an AI image on every indexed page; it must respect explicit missing-photo state. Old local content can conflict with current official facility policies. Raw API sync date is not an individual record verification date. Municipality page count includes historical and city/district scope; do not claim exhaustive current coverage. Rights-cleared facility photos may require owner permission and remain pending.

## Progress
- [x] Investigation
- [x] Implementation
- [x] Automated verification
- [ ] Desktop verification
- [ ] Mobile verification
- [ ] Regression check
- [ ] Final review

## Discoveries
- Main is two commits ahead of the cancelled old AI-image baseline; preserve price-scan changes.
- Existing Incheon Medical Center parking statements conflict with newer facility-specific official guidance; pilot will replace conflicting claims, not append another competing figure.
- e하늘 photo availability does not establish commercial reuse rights; no such photos accepted.

## Decisions
The source directory is an auditable catalog, not a list of active partners or no-hall-compatible facilities. New individual facility pages require meaningful independently sourced facts and an explicit quality review before indexing; actual-photo coverage is reported independently. The ten new facility pilots include five text-index candidates and five source-review holds; no automatic keyword or photo-based index promotion is allowed. Four candidates have no actual photograph; Yongin has an accepted photograph but remains noindex because its current facility-specific text evidence is insufficient. Thus photography and text-quality gates are independent. The old 1,073 AI facility landscapes are not included in this implementation.

## Verification checkpoint
Local: 120 Python tests, deterministic build/idempotence, search content, SEO conversion, public-security check, Python compile and git diff checks pass. The full 269 regional-original gate and search-image gate pass; all regional image hashes and raw/prices/latest scan files are unchanged. Browser execution is blocked locally: default Playwright executable missing; supported download returned an invalid archive; installed system Chromium fails socket() with EPERM. Zero local browser viewports passed. Real GitHub browser CI is required. Independent read-only review identified and prompted fixes for origin-to-local browser routing, regeneration round trips, JSON-LD escaping, list-typed schema, photo rights/depiction validation, directory-card photo preservation, hero attribution contrast, and photo-specific visual samples.

## Photograph scope
Two exact, unmodified photographs are registered: a 2019-09-24 Yongin municipal archive photograph of the funeral building (KOGL1 attribution, publication-date caveat, unknown capture date, original630×354 dimensions), and the existing gallery9 photograph for the exact Myeonmok Green Hospital facility. The latter preserves the observed privacy flag and has a separate authorization judgment confined to this immutable original photograph, exact facility and existing site reuse; it does not authorize other images, facilities or purposes. Public metadata contains only provenance, license/attribution and factual depiction information; private authorization conversations and work paths remain outside the repository. Actual-photo coverage is2/1080, not completion of all facility photographs.

## Publication and expansion gate
First release:269 established regional canonicals,76 established facility/status pages,22 crawlable directory pages, and10 new individual pilots. Five new text candidates require exact-commit real-browser CI plus mobile/desktop visual review before release; the other five remain noindex and outside sitemap. All1080 identities have one canonical allocation, but994 remaining pages are planned, not empty generated/indexed templates.

Next batch:50 previously unpublished exact identities, selected without existing/pilot overlap, are researched in a separate content workspace. Each candidate needs official or otherwise reliable facility-specific evidence beyond name/address, meaningful visitor/space/access/operating-context guidance, source dates, identity/administrative-label checks, useful family/no-hall questions, honest unknowns, and current-page uniqueness. Promotion is per-page, not all-or-nothing; identity/closure holds cannot be promoted. Real-photo rights are reviewed independently and absence does not itself block useful text SEO. Further batches continue after the pilot review; do not index the old1,020 keyword-combination pages or publish hundreds of repeated name/address templates.

Remote objects are uploaded as small individually SHA-verified blobs with durable external journals, followed by SHA-only trees. An earlier inline regional tree request was interrupted and read-only checks found no expected tree or its271 blobs; it is not retried. No old AI publication is resumed. Keep aggregate GitHub write rates within documented limits, stop on approval/permission/rate-limit errors, and recheck main lease before branch publication.

## Remaining limitations
Only2 actual photos are accepted;1,078 remain pending. Source-specific content expansion is ongoing. Local Chromium restrictions are not a browser pass. Exact-commit real CI, screenshot review, deployment status and live source hashes remain mandatory before a publication/completion claim.
