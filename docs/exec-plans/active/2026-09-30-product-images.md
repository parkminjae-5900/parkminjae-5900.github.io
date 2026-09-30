# Codex Task: 수의·관·유골함 이미지 전면 수정

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
