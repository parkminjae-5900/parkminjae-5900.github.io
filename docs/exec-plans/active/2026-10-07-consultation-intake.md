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
- [ ] Regression check
- [ ] Final review
## Discoveries
phone_click and kakao_click already implemented. Existing consult_submit fires before successful storage.
## Decisions
Use distinct new page; preserve existing working helper. Minimal non-sensitive context; no free-text bereavement details.
## Final verification
Node tests: 5 passed (persistence, idempotency, validation, abuse verification, authenticated reads, expiry, client failure/success and analytics privacy). JavaScript syntax passed. SEO conversion and search-content checks passed after adding the sitemap URL. Existing product-catalog browser script could not run because its required Edge executable is unavailable. Desktop/mobile rendered UI and live endpoint verification remain open; no production change. Static project has no package/build/typecheck command.

User additionally requested subsequent steps run in sequence after 상무 approval. Approver identity and approval channel unresolved; no messages or automation created.
## Remaining limitations
Live backend setup, live end-to-end verification and deployment.

## AI executive review — 2026-10-07
Read-only independent review returned HOLD for publication. Locally corrected cursor pagination for the 200-row operator list, storage/config readiness check, and retry copy scoped to the current screen. Five tests still pass; new pagination/rendered checks remain required. Outstanding: cleanup monitoring/backup policy, attribution URL/referrer privacy audit, operator workflow, production storage configuration and desktop/mobile/live verification. This review is not actual-person approval. Actual executive identity/channel remains unresolved. Automatic approval review rejected remote push; no alternate publication route attempted. No automation created.
