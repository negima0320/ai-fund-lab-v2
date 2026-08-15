# Phase29-L21T-BK Post-BJ Day2 Current Valuation HALT Root Cause Audit

## Task

Phase29-L21T-BK

READ-ONLY audit. Phase29 continued. Phase30 was not entered.

Codex did not run fresh-run, resume, replay, recovery, or long Historical validation. The target run was not mutated.

## Target

- Run: `runtime-test-historical-extended-smoke-20260815T022202383846Z`
- HALT date: `2022-08-12`
- HALT stage: `current_valuation_refresh`
- Runtime CLI exit code: `20`
- Runtime Test stopped with next job: `2022-08-12:current_valuation_refresh`

## Direct HALT Evidence

`current_valuation_refresh/current_valuation_manifest.json` shows:

- `status = REVIEW_REQUIRED`
- `projection_status = REVIEW_REQUIRED`
- `position_count = 8`
- `valued_position_count = 0`
- `missing_evidence = ["current_valuation_quote_invalid:94320"]`
- `apply_executed = false`

Market evidence itself was present:

- `market_evidence_authority.status = PASS`
- `missing_symbols = []`
- `market_date = 2022-08-12`

## Day1 Contract Result

The actual post-BJ fresh run completed 2022-08-10 with the intended basis-consistent valuation:

- `status = READY`
- `apply_executed = true`
- `market_value = 250,040`
- `cash = 745,820`
- `total_equity = 995,860`

For the key adjusted-basis positions:

| Symbol | Quantity | Current Price | Market Value | Quantity Basis | Valuation Price Basis |
|---|---:|---:|---:|---|---|
| 94320 | 200 | 149.8 | 29,960 | ADJUSTED | ADJUSTED |
| 94340 | 100 | 151.8 | 15,180 | ADJUSTED | ADJUSTED |

Conclusion: BJ Day1 contract works.

## Day1 To Day2 State Trace

After 2022-08-12 execution, Current was rebuilt by `runtime_v2_runtime_owned_fill_projection`.

The Day2 pre-valuation position state lost explicit basis metadata for all 8 positions:

- `quantity_basis`: missing
- `valuation_price_basis`: missing
- `valuation_price_role`: missing
- `valuation_price_provenance`: missing
- `current_price`: missing

For 94320:

| Field | Value |
|---|---:|
| Quantity | 200 |
| Average price | 149.2 |
| Current price | missing |
| Market value / quantity | 149.8 |
| Adjusted close | 147.9 |
| Raw close | 3698.0 |
| Adjusted candidates | 147.9 / 150.3 / 151.1 / 147.8 |
| Raw candidates | 3698.0 / 3758.0 / 3778.0 / 3696.0 |
| Inferred quantity basis | UNKNOWN |
| Rejection reason | `position_quantity_basis_unresolved` |

94320 had been explicitly `ADJUSTED` on Day1, but Day2 Current no longer carried that metadata. Because the Day2 adjusted OHLC range moved away from the prior Day1 valuation/unit evidence, the fallback inference could not resolve the basis and correctly failed closed.

94340 did not halt because its stale unit evidence still matched the Day2 adjusted close (`151.4`) closely enough to infer `ADJUSTED`. That is incidental, not a durable authority.

## New Positions

2022-08-12 added new BUY positions:

- `30100`
- `36640`
- `91070`

They also lacked explicit basis metadata after fill projection. They did not trigger the HALT only because basis inference succeeded:

- `30100` and `36640`: raw and adjusted basis equivalent.
- `91070`: fill/unit evidence matched adjusted-basis price candidates.

This confirms a new-position basis materialization gap as well, although the direct HALT symbol was existing `94320`.

## Corporate Action

No evidence indicates that a Corporate Action caused the 2022-08-12 HALT. The failure occurred before any CA quantity adjustment question: explicit basis/provenance had already been dropped from runtime-owned Current projection.

## Root Cause Classification

Primary Judgment:

`POSITION_BASIS_METADATA_PROPAGATION_GAP`

Supporting classification:

- `QUANTITY_BASIS_PERSISTENCE_GAP`: YES
- `POSITION_BASIS_METADATA_PROPAGATION_GAP`: YES
- `BASIS_INFERENCE_AMBIGUITY`: NO
- `NEW_POSITION_BASIS_MATERIALIZATION_GAP`: PARTIAL / YES for metadata absence, not the direct halt
- `CORPORATE_ACTION_BASIS_GAP`: NO
- `BJ_REGRESSION`: NO

## Generated Audit Artifacts

- `reports/phase29_l21t_bk_post_bj_day2_current_valuation_halt_root_cause_audit/summary.json`
- `reports/phase29_l21t_bk_post_bj_day2_current_valuation_halt_root_cause_audit/day2_valuation_rejection_trace.csv`
- `reports/phase29_l21t_bk_post_bj_day2_current_valuation_halt_root_cause_audit/day1_to_day2_basis_trace.csv`
- `reports/phase29_l21t_bk_post_bj_day2_current_valuation_halt_root_cause_audit/position_basis_metadata_trace.csv`

## Required Judgment

- BJ Day1 contract works: YES
- Day2 quantity basis persistence gap: YES
- Day2 basis inference ambiguity: NO
- Position metadata propagation gap: YES
- New-position basis materialization gap: YES
- Corporate Action causal: NO
- Implementation repair required: YES

## Runtime Safety

- Runtime mutated: NO
- Strategy changed: NO
- Fresh-run executed by Codex: NO
- Resume/replay/recovery executed by Codex: NO
- Phase30 entered: NO

## Recommended Next Action

Create a Phase29-L21T-BL implementation repair to persist/materialize price and quantity basis metadata through runtime-owned fill projection and Current valuation transitions. Keep the BJ fail-closed contract intact; do not add raw/adjusted fixed fallback logic.
