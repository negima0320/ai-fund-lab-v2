# Phase24-D Market-Weak High-Quality Opportunity Exploratory Entry Policy Implementation

## 1. Primary Judgment

`PHASE24_D_EXPLORATORY_ENTRY_POLICY_IMPLEMENTED_SHORT_VALIDATION_PASS`

Phase24-D implemented the single Strategy hypothesis `P24-HYP-01`: when Dynamic Position Count calculates zero only through the market-weak path, a canonical `BUY_ELIGIBLE` Opportunity exists, meaningful allocation capacity is at least one, and no severe risk / authority / safety exclusion is present, Portfolio Policy may expose one exploratory target position capacity.

No Runtime run, fresh-run, broker write, J-Quants fetch, threshold tuning, cash-ratio tuning, fixed maximum position cap, fixed buy count, 2022-07-specific branch, symbol-specific branch, or forced-buy logic was introduced.

## 2. Executive Summary

Phase24-B and Phase24-C identified that the 2022-07-07 zero-deployment case was caused by Dynamic Position Count resolving:

```text
BEAR base count = 1
WEAK breadth delta = -2
strategy_minimum_position_count = 0
meaningful capacity = 50
target_position_count = 0
```

This suppressed all new deployment even though canonical Opportunity evidence included `BUY_ELIGIBLE` opportunities.

Phase24-D preserves the original calculated value as `calculated_target_position_count`, then applies an exploratory floor only when the canonical conditions are satisfied. The final `target_position_count` can become `1`, but downstream Portfolio Construction, Position Sizing, Safety, Submit Policy, cash, exposure, lot size, and Runtime Planning can still produce zero orders.

## 3. Reviewed Design / Evidence

Reviewed required Phase24 materials:

```text
docs/phase_reports/phase24_a_performance_evaluation_contract.md
docs/phase_reports/phase24_b_p24_gap01_zero_deployment_root_cause_investigation.md
docs/phase_reports/phase24_c_low_opportunity_capacity_and_market_context_override_investigation.md
docs/phase_reports/phase23_to_phase24_chatgpt_handoff.md
docs/phase_reports/phase23_final_summary_and_phase24_handoff.md
docs/phase_reports/phase23_bv_phase21_design_conformance_full_architecture_runtime_evidence_closure_review.md
docs/01_requirements/phase_roadmap.md
docs/02_architecture/autonomous_ai_operations_architecture.md
docs/02_architecture/runtime_architecture_v2.md
docs/02_architecture/strategy_architecture_v1.md
docs/02_architecture/portfolio_construction_and_position_sizing_contract.md
docs/03_ai_design/market_context_design.md
docs/03_ai_design/portfolio_manager_policy_design.md
docs/03_ai_design/opportunity_ai_design.md
```

Reviewed implementation / config surface:

```text
src/ai_fund_lab_v2/strategy/portfolio_policy.py
src/ai_fund_lab_v2/strategy/dynamic_position_count.py
src/ai_fund_lab_v2/strategy/dynamic_cash_exposure.py
src/ai_fund_lab_v2/strategy/portfolio_construction.py
src/ai_fund_lab_v2/strategy/position_sizing.py
configs/strategy/portfolio_policy.json
configs/strategy/dynamic_position_count.json
configs/strategy/dynamic_cash_exposure.json
```

## 4. Confirmed Root Cause

The confirmed root cause remains a Performance policy gap, not a Runtime correctness defect:

```text
BUY_ELIGIBLE Opportunity exists
        |
        v
Dynamic Position Count computes BEAR + WEAK target = 0
        |
        v
Portfolio Policy exposes target_position_count = 0
        |
        v
Portfolio Construction has no new target membership capacity
        |
        v
Position Sizing receives no new position target
        |
        v
Runtime Planning emits NO_ORDER / planned_quantity = 0
```

Runtime Planning was consuming the upstream Policy result correctly.

## 5. Implemented Hypothesis

Implemented `P24-HYP-01` in `src/ai_fund_lab_v2/strategy/dynamic_position_count.py`.

Contract:

```text
exploratory_entry_eligible =
    calculated_target_position_count == 0
    AND canonical_buy_eligible_count >= 1
    AND meaningful_allocation_position_count >= 1
    AND severe_risk_exclusion == false
    AND authority_status == PASS
```

When eligible:

```text
target_position_count = 1
exploratory_entry_floor_applied = true
```

When not eligible:

```text
target_position_count = calculated_target_position_count
exploratory_entry_floor_applied = false
```

If the normal Dynamic Position Count output is `2`, `3`, `5`, `8`, or any other nonzero dynamic value, Phase24-D does not overwrite it.

## 6. Canonical Opportunity Eligibility Contract

The exploratory floor consumes canonical Opportunity BUY eligibility. The shadow summary now computes:

```text
buy_eligible_opportunity_count
buy_eligibility_policy_version = runtime_v2_opportunity_buy_eligibility_v1
```

using the existing runtime resolver:

```text
ai_fund_lab_v2.runtime_v2.buy_ai.opportunity_eligibility.evaluate_opportunity_buy_eligibility
```

No new 2022-07 score threshold, rank-1 shortcut, symbol-specific rule, future-return quality rule, or independent expected-edge threshold was added.

## 7. Severe Risk Exclusion Contract

The exploratory floor fails closed when upstream authority is not `PASS`, and remains blocked for canonical severe states currently available to this component:

```text
risk_posture = RISK_OFF
entry_posture = PAUSE
uncertainty = HIGH
uncertainty = UPSTREAM_REVIEW_REQUIRED
producer_status != PASS
```

The implementation did not invent unavailable taxonomy values such as unverified crash enums. Safety Guard, Submit Guard, PIT checks, future leakage checks, and authority gating remain unchanged and downstream authoritative.

## 8. Target Position Count Resolution

The payload now separates:

```text
calculated_target_position_count
target_position_count
exploratory_entry_floor_applied
exploratory_entry_floor_value
exploratory_entry_eligibility
exploratory_entry_buy_eligible_count
exploratory_entry_severe_risk_exclusion
exploratory_entry_reason_codes
```

Expected 2022-07-07-like input result:

```text
calculated_target_position_count = 0
buy_eligible_opportunity_count >= 1
meaningful_allocation_position_count >= 1
severe_risk_exclusion = false
authority_status = PASS
target_position_count = 1
```

## 9. Fixed Maximum Non-reintroduction Audit

Confirmed:

```text
strategy_fixed_position_cap_used = false
strategy_fixed_jpy_exposure_cap_used = false
legacy max_positions was not restored
safety_hard_maximum remains Safety Layer only
no max_positions field was introduced
no BEAR-specific maximum count was introduced
no fixed 5-position rule was restored
```

The value `1` is a conditional floor only when the dynamic count is zero. It is not a maximum position count, not a fixed buy count, and not a target membership cap.

## 10. Current Position Interaction

`target_position_count = 1` does not imply a new BUY order.

Observed test contract:

```text
current_position_count = 0
  -> one target membership slot may become available

current_position_count >= 1
  -> target capacity may already be satisfied
  -> position_count_posture can remain MAINTAIN
  -> no forced new BUY is created
```

## 11. Portfolio Construction / Sizing Boundary

Only the Dynamic Position Count / Portfolio Policy target capacity path was changed.

No exception branch was added to:

```text
Portfolio Construction
Position Sizing
Runtime Planning
Submit Policy
Safety Guard
```

Downstream components continue to consume Policy output normally and may still produce `NO_ORDER`.

## 12. Code and Config Changes

Updated:

```text
src/ai_fund_lab_v2/strategy/dynamic_position_count.py
src/ai_fund_lab_v2/strategy/shadow_runtime.py
schemas/strategy/dynamic_position_count.schema.json
tests/strategy/test_phase22_h_dynamic_position_count.py
tests/runtime_v2/test_phase22_p_strategy_shadow_wiring.py
```

Config files were inspected but not modified:

```text
configs/strategy/portfolio_policy.json
configs/strategy/dynamic_position_count.json
configs/strategy/dynamic_cash_exposure.json
```

## 13. Schema / Reason Code Changes

Schema observability fields were added as optional fields for compatibility:

```text
calculated_target_position_count
exploratory_entry_floor_applied
exploratory_entry_floor_value
exploratory_entry_eligibility
exploratory_entry_buy_eligible_count
exploratory_entry_severe_risk_exclusion
exploratory_entry_reason_codes
```

New reason codes include:

```text
market_context_zero_capacity
buy_eligible_opportunity_present
exploratory_entry_floor_applied
exploratory_entry_blocked_by_severe_risk
exploratory_entry_not_required_nonzero_target
exploratory_entry_unavailable_no_buy_eligible_opportunity
exploratory_entry_unavailable_buy_eligible_authority_missing
exploratory_entry_unavailable_no_meaningful_capacity
exploratory_entry_blocked_by_authority_status
exploratory_entry_blocked_by_unresolved_target
```

## 14. Tests Executed

Short tests only:

```text
python3 -m pytest tests/strategy/test_phase22_h_dynamic_position_count.py -q
python3 -m pytest tests/runtime_v2/test_phase22_p_strategy_shadow_wiring.py -q
python3 -m pytest tests/strategy/test_phase22_c_portfolio_policy.py tests/strategy/test_phase22_e_portfolio_construction.py tests/strategy/test_phase22_j_position_sizing.py tests/strategy/test_phase22_g_runtime_planning.py -q
python3 -m pytest tests/strategy/test_phase22_h_dynamic_position_count.py tests/runtime_v2/test_phase22_p_strategy_shadow_wiring.py tests/strategy/test_phase22_c_portfolio_policy.py tests/strategy/test_phase22_e_portfolio_construction.py tests/strategy/test_phase22_j_position_sizing.py tests/strategy/test_phase22_g_runtime_planning.py -q
PYTHONPYCACHEPREFIX=/private/tmp/ai-fund-lab-v2-pycache python3 -m compileall -q src/ai_fund_lab_v2/strategy/dynamic_position_count.py src/ai_fund_lab_v2/strategy/shadow_runtime.py
git diff --check
```

Note: `python -m pytest ...` was attempted first, but this environment has no `python` executable. The same validation was executed with `python3`.

## 15. Regression Results

Results:

```text
tests/strategy/test_phase22_h_dynamic_position_count.py: 29 passed
tests/runtime_v2/test_phase22_p_strategy_shadow_wiring.py: 11 passed
targeted combined regression: 139 passed in 3.77s
compileall with sandbox-local pycache: PASS
git diff --check: PASS
```

Added / updated test coverage:

```text
Case 1: BEAR + WEAK + BUY_ELIGIBLE >= 1 applies exploratory floor
Case 2: BUY_ELIGIBLE = 0 keeps target 0
Case 3: severe RISK_OFF keeps target 0
Case 4: nonzero dynamic target is preserved
Case 5: meaningful allocation capacity 0 keeps target 0
Case 6: opportunity authority REVIEW_REQUIRED fails closed
Case 7: dynamic target > 1 is not capped
Case 8: existing position does not force a new BUY
Canonical shadow summary counts BUY_ELIGIBLE through runtime resolver
```

## 16. Runtime / Strategy / Performance Impact

Runtime impact:

```text
Runtime execution not performed
Runtime Planning logic not changed
Submit / broker path not changed
Safety / authority gates not relaxed
```

Strategy impact:

```text
Market Context-only zero-capacity hard override is conditionally softened
normal nonzero Dynamic Position Count remains unchanged
zero remains valid when no BUY_ELIGIBLE opportunity, no meaningful capacity, severe risk, or non-PASS authority exists
```

Performance impact to be measured later:

```text
cash utilization
entry opportunity capture
return / drawdown / benchmark differential
holding period and turnover side effects
```

## 17. Remaining Gaps

Remaining gaps:

```text
P24-GAP-02 Cash Utilization still requires Runtime evidence
P24-GAP-03 Entry Quality still requires Before / After attribution
Dynamic Cash Exposure canonical opportunity_capacity_count field alignment remains a separate technical gap
long horizon performance impact is unknown until Operator Runtime validation
```

## 18. Operator Runtime Command

Codex did not run Operator Runtime. Formal execution order and exact command flags must be confirmed by ChatGPT Evidence Review.

Recommended Operator validation sequence:

```text
1. Same investigated 10BD window: 2022-07-01 to 2022-07-14
2. Alternate 10BD window in a different market context
3. 20BD window covering at least one weak-market segment
```

The review should compare Before / After:

```text
calculated_target_position_count
target_position_count
exploratory_entry_floor_applied
BUY_ELIGIBLE count
planned_quantity
planning_intent
cash utilization
trade count
drawdown
benchmark differential
```

## 19. Recommended Next Task

Recommended next task:

```text
Phase24-E: Operator Before / After Runtime Validation for P24-HYP-01
```

The first Runtime validation should be read-only historical simulation using the same 2022-07-01 to 2022-07-14 window, followed by an alternate 10BD and then 20BD validation only after evidence review.
