# Phase27-D2-E Runtime Planning Canonical Quantity Delta Integration

## 1. Scope

Phase27-D2-E connects `position_sizing_plan.v1` to Runtime Planning as the canonical quantity delta source.

```text
Implementation Change: true
Runtime Planning: changed
PM fallback: legacy compatibility only
Pending / Approval / Submit / Execution: unchanged
Momentum / Quality / Opportunity / Incremental Eligibility: unchanged
Historical / fresh-run / resume / long regression: PROHIBITED_NOT_EXECUTED
```

## 2. Primary Judgment

```text
PHASE27_D2E_RUNTIME_PLANNING_CANONICAL_INTEGRATION_COMPLETE_D2F_READY
```

Supporting:

```json
{
  "canonical_priority": "CONFIRMED",
  "pm_fallback": "LEGACY_ONLY",
  "duplicate_authority": "ZERO",
  "degression": "PASS",
  "next": "D2-F_APPROVED"
}
```

## 3. Contract Implemented

Runtime Planning now accepts optional `position_sizing_plan.v1` input and selects quantity authority as follows:

```text
position_sizing_plan.v1 present
  -> canonical quantity delta authority
  -> PM fallback disabled for rows with canonical sizing lineage

position_sizing_plan.v1 absent
  -> legacy position_sizing.v1 / PM compatibility behavior remains available
```

Runtime Planning remains a mapper only. It maps `quantity_delta_candidate` to `BUY_NEW`, `BUY_ADD`, `NO_ACTION`, `SELL_REDUCE`, or `SELL_EXIT`; it does not recalculate Strategy decisions.

## 4. Runtime Mapping

| Position State | Delta | Target Quantity | Runtime Action |
|---|---:|---:|---|
| New | Positive | Positive | `BUY_NEW` |
| Existing | Positive | Positive | `BUY_ADD` |
| Existing | Zero | Current quantity | `NO_ACTION` |
| Existing | Negative partial | > 0 | `SELL_REDUCE` |
| Existing | Full negative | 0 | `SELL_EXIT` |

## 5. Fallback Retirement

- Canonical delta present: PM fallback not used.
- Canonical artifact absent: PM fallback allowed only as legacy compatibility.
- Canonical sizing lineage with missing delta plus PM fallback evidence: resolves to `REVIEW_REQUIRED`, not executable ADD/REDUCE/EXIT.

## 6. Non-change Proof

No changes were made to PM, Portfolio Construction, Position Sizing formula, Momentum, Quality, Opportunity, Incremental Eligibility, cash policy, Pending, Approval, Submit, Safety, or Execution. Common architecture docs were updated so this contract is not phase-local.

## 7. Evidence

Evidence files:

```text
reports/phase27_d2e_runtime_planning_canonical_quantity_delta_integration
```

## 8. Tests

```text
PYTHONPYCACHEPREFIX=/private/tmp/pycache_phase27_d2e python3 -m pytest -q tests/strategy/test_phase22_g_runtime_planning.py
39 passed in 0.40s

PYTHONPYCACHEPREFIX=/private/tmp/pycache_phase27_d2e python3 -m pytest -q tests/strategy/test_phase27_d2a_position_intent.py tests/strategy/test_phase27_d2b_target_portfolio_decision.py tests/strategy/test_phase22_g_runtime_planning.py tests/strategy/test_phase22_e_portfolio_construction.py tests/strategy/test_phase22_j_position_sizing.py tests/strategy/test_phase27_d2d_position_sizing_plan.py tests/runtime_v2/test_phase21_b_pending_composition_add_consumer.py
137 passed in 2.52s
```

No Historical, fresh-run, resume, 10BD, 100BD, 1year, or long regression was executed.

