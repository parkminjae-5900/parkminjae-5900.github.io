# Exclude source fixtures from production SEO and Pages

## Goal
Keep third-party HTML used in parser tests intact in Git and absent from the public website and search submission pipeline.

## Current state
Commit 13a50e7 added production OG/JSON-LD to two source fixtures because enrich_seo.py recursively selected all HTML outside its existing app/vendor exclusions. GitHub Pages uses Jekyll, with no _config.yml exclusion. Both fixture routes were observed returning source HTML with HTTP 200. Live responses did not contain the new Daham metadata. The associated Pages build succeeded, but deployment timed out while syncing files. This does not establish indexing or search damage.

## Requirements
Restore the two fixtures byte-for-byte from parent f6e3cb0. Exclude test inputs from SEO generation, sitemap image repair, IndexNow, and Pages publication. Preserve public pages, business data, assets, and concurrent automated updates.

## Non-goals
No source-site edits, search removals, pricing changes, photo substitutions, or changes to public page content. No claim that a publicly accessible URL was indexed.

## Implementation steps
1. Share public HTML path guardrails between enrichment, image repair and IndexNow.
2. Restore original fixture bytes and add Jekyll exclusions.
3. Add unit regressions and a real Pages artifact build/verification workflow.
4. Run tests and generation twice to check idempotence and fixture immutability.
5. Publish against the latest main with a lease and verify exact-commit CI and live fixture 404 responses.

## Verification plan
- Build: real actions/jekyll-build-pages artifact; reject test files and compare all public HTML and key assets/data byte-for-byte.
- Lint/type-check: Python compilation, git diff --check, existing Node verification scripts; no separate package lint/type-check configured.
- Automated tests: all Python tests with parser dependencies, IndexNow dry run, SEO/image checks.
- Desktop/mobile: no public layout changes; exact-byte public artifact comparison protects both layouts. Check fixture routes and a representative public page after deployment.
- Images/console: no public script/image changes; run existing asset/content gates. Browser-render regression remains the existing CI's responsibility.
- Data/calculation: parser regression suite and restored fixture hashes.

## Risks
Scheduled automation can move main. Publication must not overwrite it. Pages CDN cache or a deployment timeout may delay the observed removal. Robots blocking would not itself remove an indexed URL, so removal from the deployed artifact is the primary fix.

## Progress
- [x] Investigation
- [x] Implementation
- [x] Automated verification
- [ ] Desktop verification (unchanged public document bytes)
- [ ] Mobile verification (unchanged public document bytes)
- [x] Regression check
- [ ] Final review and live deployment verification

## Discoveries
Live sitemap and 1,514 non-test source HTML pages contained no fixture links. Search queries returned no fixture results, which is not proof of non-indexing. IndexNow's old path mapper accepted any HTML path and needs its own exclusion guard.

## Decisions
Keep fixture source HTML pristine rather than inserting noindex into parser inputs. Exclude it with Jekyll and search-pipeline guards. Do not add robots disallow that could obstruct a crawler from observing the removed route's 404.

## Final verification
- All 194 Python tests passed with requests and BeautifulSoup installed (zero skips).
- New 12 path/fixture/IndexNow/artifact regression tests passed; existing four IndexNow tests passed.
- Python compilation, YAML parsing and git diff --check passed.
- SEO dry run scanned 1,480 eligible HTML files: no changes; 457 managed public pages validated.
- Image verification passed for 452 sitemap pages and 279 images. All 273 registered regional originals passed full coverage.
- Existing search content, SEO conversion and public repository security checks passed.
- Target commit IndexNow dry run produced zero URLs after the guard was applied.
- Two enrichment writes left every fixture unchanged and the second write made no changes. The existing final family-guidance reconciliation restored the eight FAQ block-order changes from image repair; the full scheduled sequence preserved all 1,525 HTML/sitemap file hashes.
- Restored Git blob hashes match parent f6e3cb0 exactly: Anyang 66d447d10dbac08eff7011e063e1dcf3c1b22766; Mokpo e0ebaf9bcd328b674bb9ede16251b6d26a8cc07e.
- Local Ruby/Jekyll runtime is unavailable. Exact-commit Jekyll artifact CI and live deployment checks remain pending publication.

## Remaining limitations
No Search Console URL inspection was performed. Actual indexing and any past search impact are unknown.
