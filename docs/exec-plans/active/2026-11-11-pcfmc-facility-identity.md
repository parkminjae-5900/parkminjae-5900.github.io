# Verify PCFMC facility identity

## Goal
Stop Pyeongchang prices being published as Jinbu prices and show an explicit review notice when facility-specific evidence conflicts.

## Current state
The public hall feed points Jinbu to `/facilities07` (now a cemetery) and Pyeongchang to `/facilities06`. Generic same-host crawling selected `/facilities08`, the Pyeongchang funeral hall. Jinbu's older production override also used that page. Jinbu's current `/facilities09` matches its name and address, but its price table is titled Pyeongchang (2023).

## Requirements
Match the feed name/address, canonical path, page heading/location, and table title before extracting. Preserve resident/nonresident columns and explicit daily/per-use units. Block generic fallback and saved legacy promotions for this operator. Quarantine the ambiguous Jinbu override without inventing a price. Preserve all unrelated current scan data.

## Non-goals
Do not infer that matching amounts mean the same rates apply to both facilities. Do not alter upstream facility-feed records or unrelated pricing logic.

## Implementation steps
1. Add a fail-closed PCFMC adapter and promotion checks in `scripts/scan_official_funeral_prices.py`.
2. Add structural source fixtures, identity/unit/regression tests, and the display contract test.
3. Clear Jinbu's unverified numeric override and record its exact source-review reason; restore all eight explicit Pyeongchang rows.
4. Show source-review notices before any numeric rows in `funeral-hall-cost.html`.
5. Refresh main, publish with a branch-head lease, and inspect exact-commit CI and production output.

## Verification plan
Run Python compile, price regression tests, explicit unit tests, Node display contract, JSON/amount validation, and compressed-baseline validation. Verify the deployed facility search and console; inspect desktop and mobile presentation if the available browser permits it. No image assets or layouts are changed, and no production build command exists for this static page.

## Risks
The official source title remains inconsistent; Jinbu stays on manual source review. Automated scans may advance main while this work is underway. Changes must be based on the latest tree without replacing unrelated scan-state/results.

## Progress
- [x] Investigation
- [x] Implementation
- [x] Automated verification
- [ ] Desktop verification
- [ ] Mobile verification
- [x] Regression check
- [ ] Final review

## Discoveries
Official pages verified on 2026-11-11: https://www.pcfmc.or.kr/facilities08 (Pyeongchang, Jongbu-ro 61) and https://www.pcfmc.or.kr/facilities09 (Jinbu, Odaecheon-ro 1958-21). The latter's table title remains `평창장례식장 사용료(2023년)`. Both sources explicitly show resident/nonresident columns, daily rates, and per-use encoffining. Only Pyeongchang's identity and table title agree.

## Decisions
Keep Jinbu's source record with `sourceReviewRequired: true` and no numeric prices, so a legacy or generic candidate cannot restore the wrong rates. Retain the upstream public feed unchanged and route through a reviewed identity mapping. Do not rewrite scan cursor/state during the repair; subsequent workflow runs re-evaluate stored promotion decisions.

## Final verification
64 Python price tests, 8 explicit-unit tests, Python compilation, and Node display-contract checks passed. Fresh live source reads returned `no_price_found` with `facility_price_table_name_mismatch` for Jinbu and 8 explicit rows for Pyeongchang. Local browser navigation could not reach the separate execution workspace (connection refused); production browser and CI checks are pending publication.

## Remaining limitations
Jinbu's facility-specific current price cannot be certified from the conflicting public page. Source publication year is 2023, not a guarantee of present applicability. Desktop/mobile visual checks and production CI will be recorded in the completion report after publication.
