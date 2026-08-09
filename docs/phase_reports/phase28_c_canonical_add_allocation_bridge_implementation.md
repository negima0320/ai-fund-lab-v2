# Phase28-C: Canonical ADD Allocation Bridge Implementation

## 1. Judgment

`PHASE28_C_CANONICAL_ADD_ALLOCATION_BRIDGE_IMPLEMENTED_SHORT_VALIDATION_PASS_PHASE28_D_READY`

## 2. Implemented Scope

Implemented one performance change: Portfolio Construction now connects PM `ADD` for existing positions to an ADD-specific eligibility bridge. When Expected Edge Improvement, Incremental Investment Value, Opportunity Cost, campaign continuation, concentration, capital availability, and execution feasibility pass, the row receives `post_add_target_weight > current_weight`.

## 3. Explicit Non-Scope

No BUY Quality threshold, Market Context threshold, Portfolio Fit formula, Corporate Event gate, HOLD/REDUCE/EXIT behavior, BUY Entry behavior, forced cash deployment, new concentration cap, pending writer, submit path, runtime action recomputation, model, training, or feature changes were made.

## 4. Portfolio Construction

Changed `src/ai_fund_lab_v2/strategy/portfolio_construction.py`.

ADD rows now include:

- `current_weight`
- `current_target_weight`
- `desired_incremental_weight`
- `post_add_target_weight`
- `normalized_target_weight`
- `target_weight_change`
- `target_weight_reason_codes`
- `add_allocation_eligibility_status`
- `target_weight_resolution.add_allocation_bridge`

## 5. Expected Edge Improvement

The implementation uses explicit baseline fields when supplied and otherwise compares current `runtime_opportunity_score` with `expected_edge_baseline_score` or `previous_expected_edge_score`. Missing or incomparable evidence becomes `UNKNOWN_FAIL_CLOSED`.

## 6. Incremental Value

ADD requires `incremental_investment_value_state=POSITIVE`, or a derived positive state only when Expected Edge Improvement passes.

## 7. Opportunity Cost

Explicit `opportunity_cost_status=PASS` is honored. Without it, the ADD score is compared with same-construction new BUY candidates; a superior new BUY fails ADD closed.

## 8. Target Weight Bridge

Eligibility PASS sets `target_weight` to the post-ADD target bounded by the existing equal-weight/cap policy. Fail-closed rows keep target at observed `current_weight` and record reason codes.

## 9. Position Sizing

Changed `src/ai_fund_lab_v2/strategy/position_sizing.py`.

Position Sizing still owns target notional, target quantity, current quantity, and quantity delta. ADD rows now expose `ADD_POSITIVE_QUANTITY_DELTA` or explicit zero reasons such as `ADD_LOT_ROUNDING_ZERO`.

## 10. Runtime Planning

Runtime Planning mapping was not changed. Existing positive canonical quantity delta maps to `BUY_ADD`; zero delta maps to `NO_ACTION`.

## 11. Legacy ADD

Legacy ADD executable behavior was not revived. PM still has no target weight, quantity, pending, submit, or fill authority.

## 12. Validation

- py_compile: PASS
- Phase28-C focused fixtures: 6 passed
- short regression: 102 passed
- Long Historical validation: not executed

## 13. Deliverables

Evidence directory:

`reports/phase28_c_canonical_add_allocation_bridge_implementation/`

Summary:

`reports/phase_reports/phase28_c_canonical_add_allocation_bridge_implementation.json`

## 14. Phase28-D Entry

Phase28-D is approved for operator-owned production-equivalent validation.
