# Competitor search and conversion improvements
## Goal
Improve Daham's existing pages for shared nonbrand search intents observed in official Ajd content; keep search placement claims evidence-based.
## Current state
Static GitHub Pages site. Existing cost, comparison, regional and calculator pages; conversion-funnel.js appends package selection. Ansan page incorrectly defaults to family. quote-app has a clearly disclosed mock consultation form but lacks prominent real contact options.
## Requirements
Preserve approved logo and 120/249/360/499 prices; no invented facility fees, availability, reviews or rankings. Distinguish monthly payment, total package price, balance and third-party fees. Publish useful existing-page improvements and competitor keyword baseline.
## Non-goals
No advertising purchase or budget change. No competitor content copying. No guarantee of adjacent ranks. No change to calculation rates or backend data collection.
## Implementation steps
1. Record dated first-party observations and keyword-to-existing-page mappings.
2. Improve postpaid-price and nobinso-cost comparison and regional entry links.
3. Correct Ansan default package and initial disabled guest count.
4. Add explicit real phone/chat paths alongside quote-app's demo state.
5. Synchronize structured data, run existing verification and focused behavior checks, publish atomic commit.
6. Extend existing daily/weekly SEO tasks with Ajd monitoring; distinguish unknown from zero.
## Verification plan
Static site: no package.json/build/lint/typecheck commands. Run verify-seo-conversion.mjs, verify-search-content.mjs, node --check, and focused package state test. Check desktop/mobile if browser capabilities permit; confirm live assets and deployment.
## Risks
Search rank and consultation performance are not available; current GSC Wizard has no connected properties. Local browser installation failed due invalid download. Existing public demo consultation is not operational and must remain labeled.
## Progress
- [x] Investigation
- [x] Implementation
- [x] Automated verification
- [x] Desktop verification
- [ ] Mobile verification
- [x] Regression check
- [x] Final review
## Discoveries
Ajd official pure plan separates monthly payments and event balance. General keywords found through public search are evidence of discoverability, not Naver/Google position. Direct engine-result fetches failed. Main repository confirmed by CNAME. Ansan image deployed in commit 428b8335f0bab1483817bb6edb06df90787aa240.
## Decisions
Strengthen existing pages rather than create near-duplicates. Treat site-wide analytics and competitor conversions as unknown. Keep external contact user-triggered.
## Final verification
verify-seo-conversion.mjs PASS (71 funnel pages); verify-search-content.mjs PASS (91 public pages, 92 sitemap URLs, 20 FAQ answers); node --check PASS; inline script syntax PASS on 4 changed pages; four default-package routing cases PASS; git diff --check PASS. Ansan live image loaded and desktop width 1363 had no overflow. GitHub Pages deployment and SEO workflow success for commit 2fb3975decba24c6b90b138c1e7f33d5e8003054. Live Ansan default nobinso and disabled guests verified; live comparison section and quote-app real phone link verified. Desktop width 1363 had no overflow on inspected routes. Captured console errors were browser-extension messages, not site scripts. Mobile browser verification remains unavailable.
## Remaining limitations
Search-result position, competitor ad spend and actual consultation conversions unavailable. Facilities require current confirmation. No autonomous position guarantee possible.

## 2026-10-05 regional expansion follow-up
- Generated 241 data-backed province/sigungu pages from `data/funeral-halls.json` and added the routes to `sitemap.xml`.
- Added 17 province representative JPG assets derived from a fictional AI-composite funeral-hall scene; every image is captioned as AI-generated and not an actual facility photo.
- Added a 241-link nationwide sigungu index to `area-funeral-seo-hub.html`.
- Patched the existing Songpa page with a page-specific `og:image` and visible representative image so the query shown in the user screenshot has a thumbnail candidate.
- Verification: `verify-search-content.mjs` PASS (332 public pages, 333 sitemap URLs), `verify-seo-conversion.mjs` PASS, `git diff --check` PASS, Pages build/deployment success for commit `909c5a52cb6b834347b26f0263d3b42f2938c519`.
- Live HTTP checks: Songpa HTML 200, sample regional HTML 200, Seoul regional JPG 200; both sampled pages expose `og:image` and one visible image.
- Limitation: Naver controls final crawl, thumbnail selection, and ordering; no ranking or adjacent placement is guaranteed. Mobile visual resize remains an external browser limitation.
