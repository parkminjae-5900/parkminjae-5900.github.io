# Consultation intake
## Goal
Provide a real callback request with durable private storage and success-only GA4 conversion.
## Current state
GitHub Pages static site; consult.html is a local preparation helper. No intake backend. Global analytics currently mislabels a form submit attempt as consult_submit.
## Requirements
Keep existing helper and phone/Kakao links. Collect phone, optional name, preferred callback time and explicit consent. Never send contact data to analytics. Fail closed without configured backend. Persist before success. Prevent duplicate requests and protect intake with Turnstile. Private operator API, 30-day expiry enforced on reads and scheduled deletion.
## Non-goals
No campaigns, paid services, public customer lists, new CRM or invented notification recipient.
## Implementation steps
1. Add callback page, config, client and link from helper.
2. Implement Cloudflare Worker + D1 schema, validation, Turnstile, idempotency, retention, authenticated export.
3. Replace attempt-based consultation event with confirmed completion event.
4. Test backend storage/error/privacy paths and client success/failure paths.
5. Commit branch and create reviewable PR; deploy only after backend access/configuration exists.
## Verification plan
Node syntax and tests; existing SEO verification; mobile/desktop UI when preview is available; confirm links/assets and inspect no personal values in event payload.
## Risks
Static Pages cannot receive submissions. Cloudflare account, D1/Turnstile configuration and operator access are not available in this session. No production rollout with an unconnected form.
## Progress
- [x] Investigation
- [x] Implementation
- [x] Automated verification
- [ ] Desktop verification
- [ ] Mobile verification
- [x] Regression check
- [ ] Final review
## Discoveries
phone_click and kakao_click already implemented. Existing consult_submit fires before successful storage.
## Decisions
Use distinct new page; preserve existing working helper. Minimal non-sensitive context; no free-text bereavement details.
## Final verification
Node tests: 7 passed (persistence, idempotency, validation, abuse verification, authenticated reads, 205-row cursor pagination, configuration health, expiry, client failure/success and analytics privacy). JavaScript syntax passed for intake, worker and shared analytics. SEO conversion and search-content checks passed (385 public pages, 414 sitemap URLs). Local asset/semantic checks passed. No browser executable is available, so desktop/mobile rendered UI and live endpoint verification remain open; no production change. Static project has no package/build/typecheck command.

User additionally requested subsequent steps run in sequence after 상무 approval. Approver identity and approval channel unresolved; no messages or automation created.
## Remaining limitations
Live backend setup, live end-to-end verification and deployment.

## AI executive review — 2026-10-07
Read-only independent review returned HOLD for publication. Locally corrected cursor pagination for the 200-row operator list, storage/config readiness check, and retry copy scoped to the current screen. Five tests still pass; new pagination/rendered checks remain required. Outstanding: cleanup monitoring/backup policy, attribution URL/referrer privacy audit, operator workflow, production storage configuration and desktop/mobile/live verification. This review is not actual-person approval. Actual executive identity/channel remains unresolved. Automatic approval review rejected remote push; no alternate publication route attempted. No automation created.

## Automation continuation — 2026-10-07
Latest PR check reports mergeable against current main. Shared analytics now disables the automatic unsanitized page view, sends path and referrer origin only, removes search-term fields, drops arbitrary event values and never sends raw link text, telephone values or URL queries. The SEO funnel no longer propagates inbound attribution into the calculator URL. Worker cleanup now emits a PII-free deletion count with observability enabled in the example. Added health, 205-row pagination and analytics leakage tests; all 7 tests pass. Operator alert recipient, D1 recovery/backup retention decision, production resources, desktop/mobile browser rendering and live submission remain external gates.

## 2026-10-25 continuation
- Re-ran original 7 tests successfully before changes.
- Fetched current main and resolved conflicts in analytics-tracking.js, consult.html and sitemap.xml. Preserved main search images, new consultation-scenarios sitemap entry, memory lead ID fallback and QA marker support; preserved PR confirmed-only intake conversion and privacy filtering.
- Set sanitized page_location/page_referrer at GA4 config scope as well as page_view so later conversion events inherit the sanitized defaults.
- Added privacy-safe cleanup failure logging while preserving failed scheduler status, guarded Turnstile reset failure, and corrected required-consent wording.
- Added an intake CI job on Node 22.16 and ignored local Worker configuration/secrets.
- Expanded tests to 13: concurrent identical requests, fixed 30-day retention with no retry extension, malformed payloads/CORS/cursors, selective and repeated cleanup, private cleanup error handling, missing config and blocked analytics.
- Cloudflare plugin discovery returned no matches; no CF API credentials present in runtime. Cloud browser reached Cloudflare login (no authenticated account). No remote resources created or changed.
- Browser preview at localhost:8765 failed with ERR_CONNECTION_REFUSED because the available cloud browser cannot reach the local dev server. Desktop/mobile rendered QA remains unverified, not passed.
- Deployment remains held. Required: operating-account authentication; named operator and private access handover; cleanup alert recipient; approved storage/backup/privacy policy; live Worker/D1/Turnstile and GA4 end-to-end checks; desktop/mobile browser QA.
- Search-image regression initially failed for the new intake page. Added metadata using the existing official logo unchanged, and its matching sitemap image entry.
- Final local checks: 13/13 Node tests; syntax checks for four JS modules; SEO conversion PASS (356 funnel pages), search content PASS (387 public pages, 414 sitemap URLs), public security PASS. Image verification result recorded below after execution. No production data used.
