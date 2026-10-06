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
- [ ] Desktop verification
- [ ] Mobile verification
- [x] Regression check (exact source preservation outside analytics)
- [ ] Final review

## Discoveries
Only home had an inline tag. Google verification .html is not a web page and must remain unchanged.

## Decisions
Root-absolute script URLs work for nested pages. defer preserves execution order. Preserve existing event names; prevent repeat initialization.

## Final verification
Node VM initialization, ID, deduplication and phone-click checks passed. All injected page content otherwise unchanged.

## Remaining limitations
Production deployment and realtime verification pending.
