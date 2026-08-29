# Phase32-BZ - ADD Admission / BF-Only Authority Narrow Repair

## Executive Summary

Phase32-BZ repaired the confirmed ADD semantic defect with two narrow production changes:

1. `ADD_NEXT_LOT` authority candidates now require authoritative ADD investment evidence PASS before they can receive a comparable marginal capital value or become an accepted target.
2. With the BG/BF production consumer switch active, BUY_ADD sizing is BF-only at the PS boundary. If no BF aggregated ADD target exists for the same symbol/campaign, PS emits zero ADD delta and a blocked PC discrete quantity authority instead of allowing residual legacy ADD quantity.

No PM, PS arithmetic, Runtime mapping, REDUCE/EXIT, Cash/budget, cap, Risk Pacing, or marginal value weights/thresholds were changed. No fresh-run, resume, replay, or backtest was executed.

## Inherited Evidence

Required inputs:

- `docs/phase_reports/phase32_by_add_breadth_funnel_admission_boundary_audit.md`
- `docs/phase_reports/phase32_bx_add_evidence_scale_requalification_semantic_audit.md`

Confirmed defects addressed:

- Accepted ADD contained `final_add_eligibility = FAIL_CLOSED`.
- WEAKENING / UNKNOWN / NEW_BUY_SUPERIOR / requalification-zero evidence could still be accepted by the common frontier.
- On 2022-10-28, 94320 had BF accepted ADD target = 0, but PS/Runtime still generated BUY_ADD +100 through residual non-BF authority.

## Repair A - ADD Admission

Changed file:

- `src/ai_fund_lab_v2/strategy/marginal_capital_frontier_authority.py`

The authority candidate builder now materializes `add_admission_authority` for every candidate. For non-ADD candidates it is not applicable and passes. For `ADD_NEXT_LOT`, it resolves the existing ADD investment evidence contract from the shadow/raw lineage:

- `final_add_eligibility`
- `final_add_eligibility_status`
- `add_allocation_eligibility_status`

Only `PASS` permits the candidate into marginal capital comparison. Any non-PASS state becomes:

- `authority_disposition = INELIGIBLE_ADD_ADMISSION_BLOCKED`
- `capital_value_status = NOT_COMPARABLE`
- no accepted incremental target

Missing ADD admission evidence remains fail-closed as `REVIEW_REQUIRED`.

This preserves the existing common frontier, but separates "PM has ADD intent" from "PC may allocate incremental ADD capital."

## Repair B - BF-Only ADD Authority

Changed file:

- `src/ai_fund_lab_v2/strategy/position_sizing.py`

BG/BF switch target lookup now keys ADD by symbol and campaign:

- NEW: `(NEW_BUY, symbol)`
- REENTRY: `(REENTRY, symbol)`
- ADD: `(ADD, symbol, position_campaign_id)`

If an active BG/BF authority has no ADD target for the same symbol/campaign, PS now emits a BF-only zero ADD lot resolution:

- `final_allocated_quantity = 0`
- `discrete_authorized_quantity = 0`
- `final_target_quantity = current_quantity`
- `pc_positive_executable_quantity_authority.status = BLOCK`
- `future_information_used = false`
- `historical_outcome_used = false`
- `legacy_target_gap_fallback_allowed = false`
- `legacy_zero_fallback_allowed = false`
- reason: `BG_BF_ADD_TARGET_REQUIRED_NO_LEGACY_ADD_FALLBACK`

This closes the 2022-10-28 94320 residual BUY_ADD path without changing PS quantity arithmetic or Runtime mapping.

## Legacy Path Classification

- PM ADD intent: KEEP
- ADD evidence production: KEEP
- Common NEW/REENTRY/ADD/Cash competition: KEEP
- BF aggregated PS boundary: KEEP as sole switched ADD target authority
- PS quantity arithmetic from valid BF target: KEEP
- Runtime mapping of PS BUY_ADD quantity: KEEP
- Legacy/residual ADD positive-quantity fallback while BG/BF switch is active and no BF ADD target exists: REMOVE at consumer boundary
- Legacy target-gap / zero fallback for switched rows: REMOVE
- REDUCE / EXIT paths: KEEP

## Regression Coverage

Added focused tests:

- `test_phase32_bz_fail_closed_add_evidence_cannot_be_accepted`
- `test_phase32_bz_same_day_multi_lot_pass_add_evidence_is_preserved`
- `test_phase32_bz_bf_absent_add_target_blocks_residual_buy_add`

Existing related regressions also remained green:

- NEW switched target consumption
- REENTRY switched target consumption
- ADD 3-lot and 200-share multi-lot net quantity
- Cash/no-deployment zeroing without legacy fallback
- missing/invalid authority fail-closed
- BO PIT flags through planning submit feasibility
- BR quantity progression
- BT cap preservation in existing focused coverage

## Verification

Commands run:

```bash
PYTHONPYCACHEPREFIX=/private/tmp/phase32_bz_pycache python3 -m py_compile src/ai_fund_lab_v2/strategy/marginal_capital_frontier_authority.py src/ai_fund_lab_v2/strategy/position_sizing.py
```

Result: PASS.

```bash
python3 -m pytest tests/strategy/test_phase32_az_marginal_capital_frontier_authority.py tests/strategy/test_phase32_bg_pc_to_ps_consumer_switch.py
```

Result: PASS, 49 passed.

## Boundary Confirmation

Preserved:

- PM ADD intent
- common NEW/REENTRY/ADD/Cash competition
- multi-lot ADD when ADD evidence is PASS
- BR quantity progression
- BT effective concentration cap behavior
- Cash/budget conservation
- PS quantity arithmetic
- Runtime mapping
- REDUCE/EXIT
- PIT flags and deterministic behavior

Not changed:

- rank/quality thresholds
- marginal value weights
- Cash policy
- Risk Pacing
- Safety caps
- Runtime/Pending/Orders/Execution

## Final Judgments

PHASE32_BZ_ADD_PASS_ADMISSION_ENFORCED = YES

PHASE32_BZ_FAIL_CLOSED_ADD_BLOCKED = YES

PHASE32_BZ_MULTI_LOT_ADD_PRESERVED = YES

PHASE32_BZ_BF_ONLY_ADD_AUTHORITY_ENFORCED = YES

PHASE32_BZ_2022_10_28_RESIDUAL_ADD_REMOVED = YES

PHASE32_BZ_LEGACY_ADD_FALLBACK_ZERO = YES

PHASE32_BZ_CAP_CASH_BUDGET_PRESERVED = YES

PHASE32_BZ_REGRESSION_STATUS = PASS

PHASE32_BZ_FRESH_VALIDATION_READY = YES

PHASE32_BZ_NEXT_STEP = User-operated short fresh validation of the BG/BF active path, with emphasis on ADD PASS-only acceptance and absence of residual BUY_ADD when BF has no ADD target.
