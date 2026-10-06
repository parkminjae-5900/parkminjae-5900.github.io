# Actual Funeral Case Data Engine V1

## Goal
Turn user-supplied real funeral photos and receipts into privacy-safe, verifiable public case-study assets that strengthen facility, regional, cost, SEO/GEO/AEO pages.

## Current state
- Static GitHub Pages site with regional/facility landing pages.
- Conversion funnel and Search Console measurement are already wired.
- No standardized real-case ingestion schema or case generator exists yet.

## Requirements
- Preserve originals privately; never publish originals automatically.
- Remove/withhold deceased/bereaved names, phone numbers, account/card numbers, signatures, exact home addresses, resident IDs/birthdates, QR/barcodes, and other personal identifiers.
- Treat faces of mourners/staff/deceased as non-public by default unless explicit publication permission is supplied.
- Extract only verifiable costs from receipts and user-provided event facts.
- Separate Sangjo package price from funeral-home, food/reception, cremation, vehicle, cemetery/columbarium and optional costs.
- Generate one canonical case page per real event, not doorway duplicates.
- Link each case to the corresponding funeral-home and regional hubs when those pages exist.
- Add Article structured data only for visible, verified content.
- Keep real-case pages noindex until privacy review and publish=true.

## Non-goals
- No invented review, rating, attendee count, testimonial, or cost.
- No automatic public upload of unredacted receipts/photos.
- No mass duplicate pages for keyword permutations.

## Implementation steps
1. Add normalized case schema and empty case index.
2. Add generator script that validates privacy/publication gates and produces canonical case HTML.
3. Add public case index page that only lists publish=true cases.
4. Add documented ChatGPT upload workflow for photos + receipt.
5. Extend SEO verification to ensure unpublished cases cannot be indexed.
6. Add first real case only when the user supplies source files.

## Verification plan
- JSON validation.
- Generator dry run with a synthetic non-public fixture.
- Confirm unpublished fixture is not emitted/indexed.
- Confirm published fixture requires privacy_reviewed=true and verified costs.
- Check generated canonical, H1, conversion funnel, sitemap behavior.
- Run existing SEO/search verification.

## Risks
- Privacy leakage from receipts/photos.
- Misclassification of costs.
- Duplicate or thin case pages.
- Facility pricing changes being confused with historical case cost.

## Progress
- [x] Investigation
- [ ] Implementation
- [ ] Automated verification
- [ ] Final review

## Decisions
- Chat upload is the intake surface: user supplies photos and receipt, assistant creates sanitized structured data and public assets.
- Public case pages use historical-event wording, not current facility-price claims.
- Raw originals are never stored in the public GitHub repository.

## Remaining limitations
A static public repository cannot safely hold private originals. Originals must remain in the conversation/private storage; only sanitized derivatives and structured public data can be committed.
