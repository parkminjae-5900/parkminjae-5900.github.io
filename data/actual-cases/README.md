# Actual Funeral Case Data

Public case data lives here only after privacy review.

Rules:
- Never store original receipts or unredacted photos in this public repository.
- Names, phone numbers, account/card numbers, signatures, resident IDs, exact home addresses, QR/barcodes and other identifiers must be removed.
- Faces are non-public by default. Publish only sanitized derivatives and only when the case publication object confirms review.
- Historical event costs must be described as the cost of that event, not as today's guaranteed facility price.
- publish=true requires privacy_reviewed=true and costs_verified=true.
- Published cases also require facility_identity with facilityName, address, officialBranchName, sourceUrl and facilityCode.
- facilityName must match funeral_hall, and facilityCode must appear as an exact HTTPS sourceUrl query/path value. This prevents same-brand branch cross-matching.
- Public aggregates count cases by the full facility identity; repeat facilities are grouped instead of summed as separate facilities.
