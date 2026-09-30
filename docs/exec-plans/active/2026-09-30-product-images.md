# Codex Task: 수의·관·유골함 이미지 전면 수정

## Current state
Implemented on `codex/product-images-20260930`; PR is awaiting ChatGPT review before merge. All 115 products use individual local photos shared between cards and dialogs. The original requirements below remain the acceptance criteria.

## Requirements
Match S1–S15, F1–F10 and all 90 urns by product code; normalize visible subject scale and whitespace; preserve names, prices, estimator behavior and official logo. Inspect every image and every selection at the requested responsive widths.

## Non-goals
No logo edits, new SVG, price changes, unrelated estimator changes or merge/deployment to main.

## Implementation steps
1. Restore S2 from valid historical asset, extract single shrouds and normalize coffin orientation.
2. Compare all 90 urn codes against the supplied manufacturer catalog and supplementary exact-code catalog.
3. Extract individual photos, remove page text/price badges and normalize white canvases without stretching.
4. Use stable code-based urn keys and the same image URL for cards/dialogs; retain selection amounts.
5. Verify all products across mobile/tablet/desktop and document the sources.

## Verification plan
This repository has no package manifest or standard build, lint or type-check commands. Validate the static HTML in Edge, decode every catalog image, check viewport overflow, popup title/image matching, selection state and total changes. Check browser errors, popup navigation, keyboard containment and Escape. Compare calculation function sources and logo markup with HEAD. Review image contact sheets and screenshots.

## Risks
Historical product labels differ from current supplier labels; product codes, existing names and prices are preserved. Repeated supplier photos cannot establish material differences visually. Local individual assets avoid runtime supplier availability and sprite-position errors. Cache query version is updated for modified photos.

## Progress
- [x] Investigation
- [x] Implementation
- [x] Automated verification
- [x] Desktop verification
- [x] Mobile verification
- [x] Regression check
- [ ] Final review — ChatGPT PR review pending; do not merge.

## Discoveries
- S2 was a 93-byte invalid image. A valid 109,054-byte historical source was recovered from commit `51f3d22`; final single-photo asset is 79,603 bytes.
- F1/F2, F3/F5 and S6/S8 are duplicated both in individual supplied files and source catalog composites. Shared photography was retained with each product's separate specification; no replacement material photo was invented.
- The old 900×810 urn sprite contained 90 very small blurred cells. The UI no longer uses this sprite. Existing legacy assets remain for other potential references.
- Index-based urn mapping was unreliable after price sorting; stable code keys now determine both card and popup image.
- 86 urns were extracted from the manufacturer's sheets at the user-supplied `http://www.xn--4y2b62voyh.kr/product/product01-01/` site. Four TA-1 through TA-4 images were matched by exact code at `https://hankook-sj.com/`. Full source URLs and crop rectangles are in `product-image-sources.json`.
- Historical CCG-1 corresponds to the catalog's CG-1; EFM-1/EFM-2 correspond to EM-1/EM-2. Existing public names/codes and prices remain compatible; code aliases were used only to find source photography.
- Visual inspection caught wrong sheet assignments and stray catalog price/size text; these were corrected before the final full test run.

## Decisions
Use JPEGs on white canvases: shrouds 700×1000, coffins 1000×500 and urns 600×600. Fit the detected subject within about 90% of the canvas, preserving aspect ratio. Use contain presentation, a scrollable viewport-sized dialog, scroll reset on opening and keyboard focus restoration. The active plan stays active until external PR review finishes.

The user's subsequent authorized request adds three photorealistic category showroom banners using marble, warm indirect lighting and wood slats. AI images are category atmosphere examples, never SKU replacements. Generated banners contain no invented logo; the exact approved `assets/daham_logo.jpg` is overlaid separately with a sign shadow. Every photograph on this estimator, including dynamically opened detail photographs, receives a separate logo watermark without changing source pixels or product shape. Official logo file remains unchanged. Scope is this requested estimator page; unrelated site pages were not edited.

## Final verification
- `node scripts/verify-product-catalog.cjs` with Playwright and installed Edge: 115 products at each of 360, 390, 430, 768 and 1280px, 575 real card/popup/select flows. Every image decoded, title and image matched, selected value/price matched, and total changed by exactly the replaced group's price delta. No horizontal overflow or JavaScript page errors.
- Previous/next navigation, close, Escape, keyboard wrap and popup image viewport bounds are covered by the browser script. Run with Playwright resolvable through Node and optional `PRODUCT_QA_OUTPUT` to choose screenshot/result output.
- Static audit: all 115 images decode and exceed 1KB; all 90 manifest entries resolve. `calcData` and `recalc` sources and logo markup are unchanged. No public supplier-name text remains.
- Individually reviewed all 90 urns in labeled contact sheets against source product codes; checked normalized S/F imagery and mobile/desktop screenshots. Mobile dialogs scroll to their selection action.
- Standard build/lint/type-check: not applicable to this static repository; no package-based commands are available. `git diff --check` is the final whitespace gate.
- Full 575-flow browser regression was repeated after branding overlays. Additional 360/390/430/1280px showroom screenshots, category filters and all-image watermark coverage passed. Generated category images were inspected for realism, complete subjects and absence of erroneous lettering.

## Remaining limitations
ChatGPT PR review remains pending. Some distinct shroud/coffin specifications share the original supplier photo as documented above; their material difference cannot be verified from photography alone.

## Goal
다함상조 장례비용 견적 페이지의 수의, 관, 유골함 이미지를 실제 상품 중심으로 선명하고 일관되게 표시하고, 선택 카드와 상세 팝업 모두 모바일/PC에서 정상 작동하게 한다.

## Mandatory project rules
- 루트의 AGENTS.md와 PLANS.md를 최우선으로 따른다.
- 다함상조 공식 로고는 수정하지 않는다.
- SVG 신규 제작 금지.
- 성원장재 표시는 공개 UI에서 제거한다.
- 작업 완료 선언 전에 직접 검수한다.

## Main page
- funeral-cost-calculator.html

## Asset area
- assets/estimate/products/
- assets/estimate/

## Current findings that must be investigated
1. assets/estimate/products/s2.jpg is only 93 bytes. Treat this as suspicious/corrupt until proven otherwise.
2. f1.jpg and f2.jpg currently share the same blob SHA.
3. f3.jpg and f5.jpg currently share the same blob SHA.
4. s6.jpg and s8.jpg currently share the same blob SHA.
5. Urn UI currently depends on a sprite-based image implementation using urn-taerimwon.jpg / urn-products.jpg.
6. The current page contains overlapping legacy CSS rules and newer catalog CSS rules. Consolidate only where safe; avoid regression in unrelated estimator steps.

## Functional requirements

### 수의
- S1 through S15 must all be represented.
- The pre-popup card must show the actual shroud product, not a full catalog/document page.
- Actual visible product scale should be visually consistent across cards.
- Do not stretch images.
- Remove excessive white margin when it makes one product appear much smaller than another.
- Clicking a card must open a readable detail popup.
- Detail popup must show the corresponding item and not a mismatched image.

### 관
- F1 through F10 must all be represented.
- The pre-popup card must show the actual coffin only.
- Actual visible coffin scale should be visually consistent across cards.
- The popup must map to the correct item.
- Verify duplicated source files; if duplicate mappings are intentional, document why. If accidental, fix using the correct available repository assets.

### 유골함
- Rebuild the urn presentation if necessary rather than preserving a broken sprite structure.
- Every visible urn card must render an actual urn image.
- No blank card, broken crop, tiny object, or off-canvas sprite.
- Each item should use an individual image asset where feasible.
- Detail popup must show the selected urn correctly.
- Preserve product selection/calculation behavior.

## Visual requirements
- Desktop: verify around 1280px+.
- Mobile: verify around 360px, 390px, 430px.
- No horizontal overflow.
- Cards should be aligned.
- Product objects should look approximately consistent in visual scale.
- Text must not overlap images.
- Popup must fit the viewport and scroll if needed.
- Images must remain sharp at normal display size.

## Validation requirements
1. Verify all referenced image paths exist.
2. Detect suspicious tiny files and invalid image files.
3. Check for duplicate blobs and confirm whether they are intended.
4. Verify every S1-S15 and F1-F10 mapping.
5. Verify every urn item.
6. Check browser console for relevant errors.
7. Verify selection behavior still works.
8. Verify popup open/close and item navigation.
9. Verify estimator calculations remain unchanged.
10. Re-run the checks after each fix.

## Output
- Commit changes only to branch codex/product-images-20260930.
- Update this plan with findings and verification results.
- Do not merge to main.
- Open a pull request to main after validation so ChatGPT can review the diff before merge.
