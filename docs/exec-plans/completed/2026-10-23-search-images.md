# Search image repair
## Goal
Repair favicon declarations and searchable photo thumbnails on the official Daham homepage.
## Current state
412 sitemap pages; 32 missing icon declarations, 65 using logo thumbnails, 168 missing image dimensions. Shared regional PNG fails full decode.
## Requirements
Preserve approved logo, page text, canonical URLs and robots policies. Valid absolute images, actual dimensions, body image and image sitemap; publish and verify live URLs.
## Non-goals
No price or business logic changes. Search engines choose final search appearance.
## Implementation steps
1. Audit sitemap and fully decode image files.
2. Recover broken shared image from a verified existing regional image, normalize metadata and body references.
3. Add reusable validation and generator follow-up.
4. Run existing gates and browser checks, publish and verify live assets.
## Verification plan
Existing SEO/conversion/security checks; strict Pillow decode; all sitemap metadata; desktop and mobile representative pages; browser console; live crawler HTTP checks. Static HTML site has no build, lint or typecheck configuration.
## Risks
Search recrawl delay; preserve concurrent uncommitted work by using a fresh checkout.
## Progress
Completed and deployed commit e2cbc39. Added the omitted public consultation-scenarios canonical URL to the sitemap (413 entries).
- 413 live HTML pages: icon, Open Graph image/dimensions, Twitter image and matching body image validated.
- 26 unique live assets including ICO/PNG: HTTP 200, valid image MIME and strict full image decode for Googlebot-Image and Yeti user agents; zero failures. Evidence: task outputs/daham-live-seo-image-audit.json.
- Existing SEO conversion gate: 356 pages passed. Search-content gate: 386 public root pages, 413 sitemap URLs, 25 synchronized FAQ answers passed. Public security gate passed. IndexNow unit tests: 4 passed; fixed Windows POSIX path comparison so seed submission works cross-platform.
- Repeated metadata repair run changed zero files. CI SEO verification and daily enrichment succeeded. IndexNow submission succeeded.
- Browser verified representative family page on live site; image decoded at 1200px, no relevant console errors. Mobile 390px iframe and desktop 1280px iframe rendered; 390px image display visually checked. Local wrapper removed after QA.
- Static HTML site has no application build, typecheck or lint command. Existing brand assets and business logic preserved. Shared damaged PNG rebuilt from existing verified regional photograph, with AI caption where embedded.
- Search result favicon/thumbnail selection and recrawl timing remain controlled by search engines; actual SERP visibility is not claimed.
