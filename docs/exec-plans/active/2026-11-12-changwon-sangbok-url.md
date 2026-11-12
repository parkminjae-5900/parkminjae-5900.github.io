# Restore Changwon Sangbok official price collection

## Goal
Correct the verified facility's malformed feed URL and show official area/eligibility-specific charges without treating square-metre rates as whole-room totals.

## Current state
The public facility feed contains https://wwwcwsisulorkr/_sangbok/indexphp for 창원시립상복공원장례식장. Generic URL normalization preserves this malformed host, resulting in unreachable scans. The official fee page and directions page identify the facility at 창원시 성산구 공단로474번길 160. Existing production overrides do not contain this facility.

## Requirements
Preserve raw feed data. Match name and address exactly. Pin the official funeral-hall fee path and validate page heading, phone, table structure, conditions, units and area columns. Retain unknown service units instead of guessing. Protect estimates from missing square-metre quantities. Preserve concurrent scan state and its cursor.

## Non-goals
No global domain typo repair, other-facility changes, fee invention, schedule changes, or branding/layout redesign.

## Implementation steps
1. Add the narrowly scoped Sangbok adapter and promotion guards to scripts/scan_official_funeral_prices.py.
2. Add area-rate quantity safety to assets/estimate/nationwide-prices.js.
3. Add official fixture, negative regression tests and display contract tests.
4. Patch only the verified facility into current state/override data and recalculate summary metrics.
5. Publish atomically against a verified current head, then verify Actions and production.

## Verification plan
Run Python price and unit tests, Node display tests and JavaScript syntax checking. Confirm a live official response and exact 8 rates. Check production desktop/mobile rendering, source link, console, assets and repeated searches. Static repository has no separate application build or type-check command.

## Risks
Concurrent automated commits, source table changes, mixed residence rates, area rates mistaken for room totals and ambiguous units. Exact head lease prevents overwrites. Unknown layouts/conditions fail closed. Area quantities default to zero and require manual verification.

## Progress
- [x] Investigation
- [x] Implementation
- [x] Automated verification
- [x] Desktop verification
- [ ] Mobile verification
- [x] Regression check
- [ ] Final review

## Discoveries
Official source https://www.cwsisul.or.kr/_sangbok/_sub02/sub02_01_02.html returned HTTP 200. Directions https://www.cwsisul.or.kr/_sangbok/_sub04/sub04_01.html matches the feed address. Fee table: 1,800/2,500 KRW per square metre per day, 40,000/70,000 per deceased per day, 80,000/140,000 per embalming-room use, and embalming 300,000/400,000 KRW with no explicit service unit. Accident recovery/suture charges are separate.

## Decisions
Keep malformed homepage in the raw record and stored homepage for traceability; sourceUrl records the corrected canonical target. Never infer that every cwsisul page belongs to this hall. Preserve the source's 12-hour billing note and eligibility qualification caveats.

## Final verification
76 Python price tests and 8 explicit-unit tests passed. PCFMC and Sangbok Node display contracts passed, including repeated searches and square-metre quantity defaults. JavaScript syntax passed. A live focused official scan returned all 8 verified rows and passed promotion guard version 6. Source cursor remains 585 at preparation. Live production browser verification passed after Pages deployed commit 9dbc492. All 8 rates, canonical source link, repeated searches, intact representative image and absence of horizontal overflow were verified at 1180 CSS pixels. Calculator area quantities start at zero, show an area/eligibility warning and calculate 1,800 × 200 = 360,000 only after explicit quantity entry. Changing billing days clears that manual area quantity back to zero. No site errors were observed; browser extension metadata errors were unrelated. The initial full guidance run exposed missing optional dependency stubs in the new tests; test-only fixes 891d2e9 and f480d99 now pass both with dependencies (76 tests) and without them (20 run, 56 skipped). The corrected full CI deterministic-generation step passed. The original scanner workflow 43172382524 completed successfully and its automated commit preserved the Sangbok record. An attempted unrelated four-region test suite lacked its unmaterialized content/image fixtures; it was not used as a gate for this change.

## Remaining limitations
Targeted mobile visual verification remains unavailable through the current browser surface; no mobile-specific layout code was changed. The full family-guidance and SEO browser workflows are still running, including their existing mobile/desktop calculator coverage. New test-only push Pages run was superseded by the automatic scan deployment; the functional production deployment already succeeded. No current fee effective date is published on the official table; source note asks users to verify current applicability and eligibility.
