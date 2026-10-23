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
Audit complete; repairing images and metadata.
