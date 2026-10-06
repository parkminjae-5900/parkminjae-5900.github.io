# Priority SEO capture: Bucheon Hue&You, Incheon, Seoul core

## Goal
Create high-intent funeral-home and regional landing pages that capture facility-name + cost + postpaid funeral + family funeral + no-wake funeral searches, while avoiding thin doorway pages.

## Current state
- Static GitHub Pages site on dahamsangjo.co.kr.
- Existing regional pages for Bucheon, Gangnam, Songpa, Incheon no-wake, and Yeongdeungpo no-wake.
- Existing hospital pages for Seoul Asan, Samsung Seoul, Incheon Medical Center, etc.
- Missing dedicated pages for Hue&You Hospital Funeral Hall, Incheon Sejong Hospital Funeral Hall, and a general Yeongdeungpo district funeral-cost hub.

## Requirements
- Prioritize conversion-intent queries over raw keyword count.
- Add unique facility/local information where verified.
- Separate Daham product prices from funeral-home facility/food/cremation/cemetery costs.
- Keep Daham official branding and telephone 1600-6131.
- Add canonical, robots, OG, WebPage/FAQ structured data where visible.
- Link new pages into existing regional hubs and sitemap.
- No fabricated reviews, ratings, or unsupported facility prices.

## Non-goals
- Do not mass-create near-identical keyword doorway pages.
- Do not alter official logo assets.
- Do not change product pricing or settlement logic.

## Implementation steps
1. Add bucheon-hueandyou-funeral.html.
2. Add incheon-sejong-funeral.html using current official hospital information.
3. Add area-yeongdeungpo-funeral.html and connect existing Yeongdeungpo pages.
4. Add internal links from Bucheon/Incheon/Seoul regional hubs.
5. Add URLs to sitemap.xml and update relevant lastmod dates.
6. Verify HTML, canonical URLs, links, mobile CSS, and live deploy response.

## Verification plan
- Static HTML structure review.
- Check canonical/OG/FAQ JSON-LD presence.
- Check linked files exist.
- Check no broken local asset references are introduced.
- Mobile layout: responsive grids and fixed CTA at 360-430 px.
- Desktop layout: max-width content at 1280+ px.
- Fetch deployed URLs after GitHub Pages deployment when available.

## Risks
- Search engines may take days/weeks to crawl and rank; deployment does not guarantee ranking.
- Facility fees can change; official-source timestamps and change notices are required.
- Excessive similar pages could be treated as doorway content; use hub + unique facility pages instead.

## Progress
- [x] Investigation
- [x] Implementation
- [x] Automated verification
- [x] Desktop verification
- [x] Mobile verification
- [x] Regression check
- [x] Final review

## Discoveries
- Competitors already target Hue&You with cost/no-wake/family-funeral intent.
- Incheon Sejong Hospital publishes current funeral-hall fees and parking guidance on its official site.
- Existing Daham pages already provide good regional infrastructure but lack dedicated pages for these two high-intent facilities.

## Decisions
- Use a small number of strong, information-rich pages instead of one page per keyword permutation.
- Treat facility fees as separate from Daham package prices.

## Final verification
Repository verification passed: all three new pages exist on main, canonical tags and 1600-6131 CTAs are present, existing regional hubs link to the new pages, and sitemap.xml contains all three URLs. Static responsive CSS uses fluid grids and a <=650px mobile rule. No new local image asset paths were introduced. External live fetch could not be completed because the web verification tool returned an accessibility error for dahamsangjo.co.kr, so production HTTP rendering remains an external verification dependency.

## Remaining limitations
Search ranking and exact user acquisition keywords cannot be guaranteed without search-console/ad-platform query data. Production HTTP rendering could not be independently fetched by the external web tool in this session.
