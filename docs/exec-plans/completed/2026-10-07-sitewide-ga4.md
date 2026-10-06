# Site-wide GA4

## Goal
Load analytics-config.js and analytics-tracking.js on every website page and verify production realtime collection.

## Current state
1461 website HTML pages; 1 Google verification text file. Shared config disabled; home alone uses inline GA4.

## Requirements
Measurement ID G-YD4K466F0B; root-absolute deferred script URLs in config-before-tracker order; no duplicate pageviews.

## Non-goals
No branding, prices, content, or layout changes. Google verification file unchanged.

## Implementation steps
1. Audit all HTML at fixed main commit.
2. Enable configuration; add initialization guard and retain advertising-signal opt-outs.
3. Replace home inline tag and inject common scripts in all 1461 pages.
4. Deploy atomically with expected branch-head lease.
5. Verify live root, regional, calculator, quote-app, SEO-combo and nested cafe pages; inspect GA4 realtime.

## Verification plan
Exact non-tracking-content preservation; script count/order across every page; Node VM syntax, initialization and duplicate guards; relevant repository checks where available; production DOM/console and viewport review. Static site has no package build/typecheck.

## Risks
Concurrent commits, caching, duplicate events, nested URL resolution, verification file corruption.

## Progress
- [x] Investigation
- [x] Implementation
- [x] Automated verification
- [x] Desktop verification
- [ ] Mobile verification (independent mobile-browser test not available; no layout/style changes)
- [x] Regression check (exact source preservation outside analytics)
- [x] Final review

## Discoveries
Only home had an inline tag. Google verification .html is not a web page and must remain unchanged.

## Decisions
Root-absolute script URLs work for nested pages. defer preserves execution order. Preserve existing event names; prevent repeat initialization.

## Final verification
Node VM initialization, ID, deduplication and phone-click checks passed. All injected page content otherwise unchanged. GitHub Verify SEO conversion funnel succeeded; Pages build/deployment succeeded. Live scripts confirmed on home, family.html, quote-app/index.html, seo-combos/f001-v0-p120.html and jangjunmo/mubinso/index.html; no horizontal overflow on sampled desktop pages. Console errors were browser-extension metadata only, no site script errors observed. GA4 realtime showed all five page titles, page_view events, family_funeral_page_view and mubinso_page_view, verifying post-deployment collection. Verification visits are not customer acquisition.

## Remaining limitations
No independent mobile-device viewport test; only analytics script tags changed, page layout/content preserved. No package production build/typecheck exists.
