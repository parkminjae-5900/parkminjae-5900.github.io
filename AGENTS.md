# DAHAM Project Agent Rules

This file defines the mandatory working rules for Codex and other coding agents working in this repository.

## 1. Core operating rule

Do not stop after editing code.

For every task:
1. Inspect the existing implementation before changing it.
2. Preserve existing working behavior unless the requested change requires otherwise.
3. Implement the requested change completely.
4. Run the relevant build, lint, type-check, and tests available in the repository.
5. Verify the affected UI on both desktop and mobile layouts where applicable.
6. Check for broken images, missing assets, console errors, broken links, and layout regressions.
7. If verification fails, diagnose and fix the issue before reporting completion.
8. Do not claim completion unless the changed feature has been verified.

When requirements are clear from the repository or this file, do not repeatedly ask the user for confirmation. Make the safest reasonable implementation and verify it.

## 2. Brand protection

### Daham Sangjo
- Use only the officially supplied Daham Sangjo logo asset already approved in this repository.
- Never redraw, reinterpret, recolor, crop, stretch, trace, regenerate, stylize, simplify, or replace the official logo unless explicitly instructed.
- Never create an AI-generated substitute logo.
- Keep the original aspect ratio.
- Do not use SVG for newly produced user-facing assets unless explicitly requested.
- Prefer PNG or JPG for visual assets.

### Hyundai Jungang Protocol
- Use the approved HJ emblem asset already designated by the project.

### Flower Star / 꽃별천지
- Treat 꽃별천지 as a separate brand.
- Do not replace its logo with Daham Sangjo branding.
- Where receipts require company naming, preserve the configured company name exactly.

## 3. Product naming and prices

The following names and base prices are canonical unless explicitly changed:
- 무빈소 120 = 1,200,000 KRW
- 꽃나라 199 = 1,990,000 KRW
- 별나라 299 = 2,990,000 KRW

Do not silently rename products or alter prices.

## 4. Funeral event settlement rules

Canonical fixed rules:
- Funeral director allowance:
  - 무빈소 120 = 300,000 KRW
  - 꽃나라 199 / 별나라 299 = 400,000 KRW
- Encoffining assistant = 100,000 KRW

Settlement sections:
1. Collections / 수금내역
2. Product-cost expenses and margin / 상품원가 지출 및 마진
3. Additional sales excluding cost / 원가 제외 추가매출

Rules:
- Product price must NOT be inserted into section 3.
- Negative amounts in section 3 must not be included in calculations.
- Do not display negative amounts in totals that are intended to represent eligible additional sales.
- Representative allocation:
  representative = section1 - section2 - (section3 / 2)
- Team leader allocation:
  teamLeader = teamLeaderAllowance + (section3 / 2)

If the current code differs, preserve existing data compatibility while bringing new calculations into compliance.

## 5. Receipt and report rules

Where applicable:
- Automatically prefix deceased names with "故" without duplicating it.
- Event date supports consultation date through departure/funeral date.
- Team leader name, photo, and signature should resolve from configured staff data.
- Signature output must remain readable in print/PDF.
- Avoid overlapping or duplicated signature labels.
- Output should fit cleanly on A4 with appropriate one-page/two-page behavior.
- Mobile layouts must remain usable without tiny text or clipped fields.

## 6. Image quality rules

For product imagery such as shrouds, coffins, urns, staff photos, and funeral supplies:
- Never ship broken image paths.
- Never use a missing placeholder when a valid local asset exists.
- Preserve source image quality.
- Avoid blur caused by scaling a low-resolution thumbnail beyond its native quality.
- Use object-fit / container rules consistently.
- Product cards must have consistent visible object scale, not merely identical outer image boxes.
- White-space-heavy source images may require controlled crop/contain behavior so the actual product appears visually consistent.
- Do not stretch images.
- Do not alter staff faces or original staff photos unless explicitly requested.
- Verify each catalog item individually after bulk changes.

### Product catalog conventions
- Shrouds: S1–S15 when those assets exist in the provided catalog.
- Coffins: F1–F10 when those assets exist in the provided catalog.
- Remove supplier branding text such as "성원장재" from the public-facing UI when the product requirement says it must not appear.
- Pre-popup selection cards should show the product itself cleanly, without unnecessary document-page framing.
- Detail popups may contain richer information, but must remain readable on mobile.

## 7. Responsive UI verification

Every user-facing change must be checked at minimum for:
- Mobile width around 360–430 px
- Tablet / medium layout where relevant
- Desktop width around 1280 px or larger

Verify:
- No horizontal overflow
- No clipped text
- No overlapping buttons
- No hidden primary actions
- No broken sticky/fixed navigation
- Images remain sharp and proportional
- Dialogs/popups fit viewport and can scroll if needed
- Font size remains readable for older users

## 8. Navigation rules

For the Event Report app, preserve the four primary categories:
1. 상담보고서
2. 정산보고서
3. 행사사진보고서
4. 고객전송 영수증

Navigation must not unexpectedly return to company selection unless the user intentionally chooses to reset/change the company.

## 9. PWA and notification rules

For PWA features:
- Preserve installability.
- Validate manifest and service-worker behavior when touched.
- Avoid changes that break offline/static asset loading.
- If push/notification code changes, test foreground and supported background flows.
- Keep company-specific notification text separated.
- Do not merge 다함상조 and 꽃별천지 notification configuration accidentally.

## 10. External API integration

For cemetery, crematorium, funeral-home, map, geocoding, or public-data APIs:
- Never hard-code secrets into client-side source.
- Keep API keys in environment variables or secret storage.
- Validate API response shape.
- Handle empty/null/error responses.
- Add graceful fallback messaging.
- Do not fabricate unavailable prices or facilities.
- Record source timestamp where data freshness matters.
- Separate raw source data from normalized application data.

## 11. Cemetery estimate rules

Unless explicitly changed, use these canonical rules:
- 1 grave = 1,400,000 KRW
- 2 graves = 2,600,000 KRW
- 3 graves = 3,200,000 KRW
- 4 graves = 4,000,000 KRW

Distance surcharge from Jamsil reference:
- 0–50 km: no surcharge
- 50–100 km: +10%
- 100–200 km: +20%
- 200 km+: +30%

Additional remains:
- Base assumption: 1 person per grave mound
- Additional person: +250,000 KRW each

Funeral vehicle:
- In-district: 300,000 KRW
- Out-of-district: 250,000 KRW + 3,000 KRW/km
- 100 km+: separate consultation rule where configured

Cremation fee:
- Keep separate from the main grave-work total unless explicitly requested otherwise.

Address input should support partial locality input and resolve the missing upper-level administrative area when reliable geocoding/reference data permits it.

## 12. SEO implementation rules

SEO changes must prioritize useful, non-duplicative pages.

For generated regional pages:
- Do not mass-produce near-identical doorway pages.
- Ensure region-specific content is based on real data where possible.
- Include unique local funeral-home / access / cost / procedure context when available.
- Set canonical URLs correctly.
- Avoid duplicate titles/descriptions.
- Add structured data only when it accurately represents visible page content.
- Do not invent reviews, ratings, prices, facility facts, or service coverage.

## 13. Accessibility and usability

Where practical:
- Use semantic HTML.
- Buttons must be real interactive controls.
- Images need meaningful alt text where appropriate.
- Form inputs need labels.
- Preserve keyboard access for dialogs and primary actions.
- Maintain adequate contrast.
- Avoid tiny touch targets.

## 14. Build and regression gate

Before reporting completion:
- Install dependencies only if needed and permitted.
- Run the repository's standard lint command.
- Run type-check if available.
- Run unit/integration tests if available.
- Run production build.
- Inspect browser console for relevant errors.
- Verify changed routes.
- Verify all changed image URLs return successfully or resolve locally.
- Verify both mobile and desktop rendering.
- Re-run checks after any fix.

If no automated test exists for a critical business rule touched by the change, add one when feasible.

## 15. Completion report

A completion report should be concise and factual:
- What changed
- What files/components were changed
- What verification was run
- Any remaining limitation or external dependency

Do not report "done" if:
- build is failing,
- assets are missing,
- major responsive issues remain,
- the requested behavior was not verified,
- or an external dependency prevented verification.

## 16. Complex work / ExecPlan

For a feature spanning multiple modules, a major refactor, data migration, large API integration, or any task likely to require multiple implementation phases:
- Create or update an ExecPlan following PLANS.md.
- Keep the plan updated as implementation progresses.
- Record discoveries, blockers, decisions, tests, and final verification.
- Continue through implementation and verification rather than stopping at the plan.

## 17. Repository hygiene

- Do not commit secrets.
- Do not delete working assets merely because they appear unused without checking references.
- Avoid unnecessary dependency additions.
- Prefer existing project patterns and utilities.
- Keep diffs focused on the requested task.
- Do not overwrite user data or production data during testing.
- Backward compatibility is preferred where persisted records already exist.

## 18. Priority order when rules conflict

1. Explicit instruction in the current task
2. Safety / security / data integrity
3. This AGENTS.md
4. Existing verified business logic
5. Existing code style and conventions

If a current task explicitly changes one of these canonical business rules, update the implementation and, when appropriate, update this file so future tasks use the new rule.
