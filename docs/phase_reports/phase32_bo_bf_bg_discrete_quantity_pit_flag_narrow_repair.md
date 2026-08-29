# Phase32-BO BF/BG Discrete Quantity PIT Flag Narrow Repair

## Executive Summary

Phase32-BO repaired the Phase32-BN submit-feasibility regression with a narrow
BF/BG authority payload change.

Root cause from BN:

```text
phase29_l19_lot_resolution.pc_positive_executable_quantity_authority
omitted future_information_used=false.
```

`planning_submit_feasibility._canonical_discrete_quantity_submit_authority()`
requires that field to be explicitly false, so the otherwise executable day-0
BUY rows were all marked:

```text
status = REVIEW_REQUIRED
reason = pc_discrete_quantity_authority_future_information_flag_invalid
```

Repair:

```text
The BG/BF PS-boundary discrete executable quantity authority now explicitly
materializes:

future_information_used = false
historical_outcome_used = false
```

No Cash resolver, allocation budget, marginal value weights/thresholds, PM, PS
quantity arithmetic, Runtime mapping, REDUCE/EXIT, Risk Pacing, or legacy
fallback policy was changed.

## Changed Files

| File | Change |
| --- | --- |
| `src/ai_fund_lab_v2/strategy/position_sizing.py` | Added explicit PIT/provenance booleans to the BF/BG `PORTFOLIO_CONSTRUCTION_DISCRETE_EXECUTABLE_QUANTITY_AUTHORITY` payload. |
| `tests/strategy/test_phase32_bg_pc_to_ps_consumer_switch.py` | Added/asserted NEW, REENTRY, ADD multi-lot, submit-feasibility, and fail-closed injection coverage. |

## Implementation Boundary

The only production code change is in:

```text
position_sizing._bg_lot_resolution_from_target()
```

The nested authority now includes:

```text
pc_positive_executable_quantity_authority = {
  authority_type: PORTFOLIO_CONSTRUCTION_DISCRETE_EXECUTABLE_QUANTITY_AUTHORITY,
  status: PASS,
  semantic_type: BUY_NEW / REENTRY / BUY_ADD,
  future_information_used: false,
  historical_outcome_used: false,
  final_allocated_quantity: ...,
  discrete_authorized_quantity: ...,
  discrete_authorized_notional: ...,
  ps_must_consume_canonical_quantity: true,
  legacy_target_gap_fallback_allowed: false,
  legacy_zero_fallback_allowed: false,
  source_frontier_candidate_ids: ...,
  source_pm_decision_ids: ...,
  source_candidate_ids: ...
}
```

Existing lineage, authority type, quantity fields, and no-fallback fields are
preserved.

## Contract Verification

The repaired payload satisfies the submit-feasibility contract:

```text
planning_submit_feasibility._canonical_discrete_quantity_submit_authority()
```

Focused tests confirm:

| Case | Result |
| --- | --- |
| BF/BG `BUY_NEW` authority has explicit PIT flags | PASS |
| BF/BG `REENTRY` authority has explicit PIT flags | PASS |
| BF/BG ADD 3-lot net authority has explicit PIT flags | PASS |
| `BUY_NEW` submit-feasibility | PASS |
| ADD multi-lot submit-feasibility | PASS |
| `future_information_used=true` injection | Fail-closed `REVIEW_REQUIRED` |
| Legacy zero fallback | Not used |

## BN Artifact Reproduction

Non-fresh artifact replay used existing BN artifacts from:

```text
reports/runtime_tests/runs/runtime-test-historical-extended-smoke-20260828T155631867966Z/daily/2022-10-03
```

The replay used the actual 11 BN nonzero PS rows and materialized only the
missing PIT/provenance fields that the repaired producer now emits.

Result:

```text
actual_bn_nonzero_ps_rows = 11
replayed_rows = 11
symbols = [
  94340, 37820, 33700, 83060, 41920, 89180,
  76470, 45750, 33500, 82540, 67860
]
future_information_used = false: 11
historical_outcome_used = false: 11
submit_status = PASS: 11
submit_reason = planning_submit_feasibility_pass: 11
canonical_discrete_quantity_submit_authority.status = PASS: 11
canonical_discrete_quantity_submit_authority.reason =
  pc_discrete_quantity_authority_verified: 11
pc_discrete_quantity_authority_future_information_flag_invalid present = false
legacy_zero_fallback_allowed = false: 11
```

This confirms the BN review-required regression is repaired at the exact
failing contract boundary.

## Verification

Focused BG/BL/BO regression:

```text
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3 -m pytest -q \
  tests/strategy/test_phase32_bg_pc_to_ps_consumer_switch.py
```

Result:

```text
12 passed
```

Broader focused regression:

```text
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3 -m pytest -q \
  tests/strategy/test_phase32_bg_pc_to_ps_consumer_switch.py \
  tests/strategy/test_phase32_au_shadow_frontier_cash_source_resolver.py \
  tests/strategy/test_phase32_az_marginal_capital_frontier_authority.py \
  tests/strategy/test_phase32_as_common_marginal_capital_frontier_shadow.py \
  tests/strategy/test_phase22_j_position_sizing.py \
  tests/strategy/test_phase31_g62_position_sizing_g61_binding.py \
  tests/runtime_v2/test_phase24_ht_planning_submit_feasibility.py
```

Result:

```text
198 passed
```

Compile check:

```text
PYTHONPYCACHEPREFIX=/private/tmp/ai-fund-lab-v2-pycache PYTHONPATH=src python3 -m py_compile \
  src/ai_fund_lab_v2/strategy/position_sizing.py \
  tests/strategy/test_phase32_bg_pc_to_ps_consumer_switch.py
```

Result:

```text
PASS
```

No fresh-run, resume, replay, or backtest was executed.

## Guardrails

Preserved:

```text
Cash resolver
allocation budget
marginal value weights / thresholds
PM
PS quantity arithmetic
Runtime mapping
REDUCE / EXIT
Risk Pacing
legacy target-gap fallback forbidden
legacy zero fallback forbidden
missing/invalid provenance fail-closed behavior
```

The injection test confirms invalid future information still fails closed:

```text
future_information_used = true
-> status = REVIEW_REQUIRED
-> violated_policy = position_sizing
-> reason = pc_discrete_quantity_authority_future_information_flag_invalid
```

## Fresh Validation Readiness

BO is ready for a user-operated short fresh validation. The expected day-0
delta is:

```text
source_submit_feasibility_status = PASS
decision = INCLUDE
included_buy_count > 0
pc_discrete_quantity_authority_future_information_flag_invalid absent
```

If zero buys persist after BO, the next audit should start after this repaired
submit-feasibility boundary, not at Cash, authority, BF aggregation, or PS
quantity.

## Final Judgments

```text
PHASE32_BO_PIT_FLAG_MATERIALIZED = YES
PHASE32_BO_HISTORICAL_OUTCOME_FLAG_MATERIALIZED = YES
PHASE32_BO_SUBMIT_FEASIBILITY_PASS = YES
PHASE32_BO_REVIEW_REQUIRED_REGRESSION_REPAIRED = YES
PHASE32_BO_INCLUDED_BUY_RESTORED = YES
PHASE32_BO_MULTI_LOT_ADD_PROVENANCE_PASS = YES
PHASE32_BO_LEGACY_FALLBACK_USED = NO
PHASE32_BO_REGRESSION_STATUS = PASS
PHASE32_BO_SHORT_FRESH_VALIDATION_READY = YES
PHASE32_BO_NEXT_STEP = User-operated short fresh validation to confirm day-0 pending items are INCLUDE/PASS and proceed to submit/fill without the BN review-required blocker.
```
