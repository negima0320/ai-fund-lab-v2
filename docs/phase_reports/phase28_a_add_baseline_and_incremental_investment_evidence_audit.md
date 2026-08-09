# Phase28-A ADD Baseline and Incremental Investment Evidence Audit

## 1. Executive Summary

Primary Judgment:

```text
PHASE28_A_ADD_BASELINE_AUDIT_COMPLETE_WITH_EVIDENCE_GAPS_PHASE28_B_CONDITIONAL
```

Phase28-B Entry Decision:

```text
CONDITIONAL
```

Phase28-A was executed as a read-only audit of existing evidence. No Production Runtime, Strategy, PM, Position Sizing, Planning, Submit, Config, Schema, Contract, Legacy path, Runtime switch, or performance implementation was changed. Codex did not run fresh-run, resume, 10BD, 20BD, 100BD, 1-year, or long Historical validation.

Baseline source run:

```text
runtime-test-historical-smoke-20260804T074611098414Z
period: 2023-01-04 through 2023-05-31
business_days: 100
```

Core result:

| Metric | Count |
|---|---:|
| Existing-position rows audited | 364 |
| PM ADD intent | 145 |
| Runtime Planning BUY_ADD | 0 |
| ADD submit observed | 0 |
| ADD fill observed | 0 |
| ADD zero delta | 145 |
| ADD zero quantity | 145 |
| Rank1 existing-position rows | 86 |
| Rank1 PM ADD intent rows | 76 |
| Rank1 BUY_ADD rows | 0 |

Current ADD is observable as PM intent, but no executable BUY_ADD was observed. In the audited run, PM ADD rows all terminate as zero-delta / zero-quantity / Runtime Planning `NO_ACTION`. This confirms an evidence-backed gap between current PM ADD intent and executable canonical BUY_ADD, while also confirming that PM ADD alone is not a buy order.

## 2. Scope

This audit covers existing artifacts, code, Architecture SoT, Contract documents, and Phase27 reports. It does not propose or implement a performance change. Post-hoc outcomes are used only for audit/evaluation and are not Strategy inputs.

## 3. Documents Reviewed

- `docs/phase_reports/phase27_to_phase28_chatgpt_handoff.md`
- `docs/phase_reports/phase27_final_summary_and_phase28_handoff.md`
- `docs/phase_reports/phase27_d6e_d6d_100bd_before_after_causal_attribution_and_adoption_review.md`
- `docs/02_architecture/strategy_architecture_v1.md`
- `docs/02_architecture/momentum_follow_position_lifecycle_and_canonical_decision_architecture.md`
- `docs/02_architecture/position_management_decision_trace_contract.md`
- `docs/02_architecture/portfolio_construction_and_position_sizing_contract.md`
- `docs/02_architecture/runtime_architecture_v2.md`
- `docs/phase_reports/phase27_a9_canonical_buy_add_authority_unification_and_legacy_consumer_disposition_design_review.md`
- `docs/phase_reports/phase27_d6a_pm_implementation_gap_audit.md`
- `docs/01_requirements/phase_roadmap.md`

## 4. Runtime / Strategy Files Reviewed

- `src/ai_fund_lab_v2/position_management_ai/inference.py`
- `src/ai_fund_lab_v2/runtime_v2/position_management/producer.py`
- `src/ai_fund_lab_v2/runtime_v2/position_sizing_authority.py`
- `src/ai_fund_lab_v2/runtime_v2/planning_submit_feasibility.py`
- Strategy artifacts under `reports/runtime_tests/runs/runtime-test-historical-smoke-20260804T074611098414Z/daily/*/strategy/`
- PM snapshots under `reports/runtime_tests/runs/runtime-test-historical-smoke-20260804T074611098414Z/daily/*/position_management/`

## 5. Evidence Reviewed

Main evidence directory:

```text
reports/phase28_a_add_baseline_and_incremental_investment_evidence_audit/
```

Machine-readable summary:

```text
reports/phase_reports/phase28_a_add_baseline_and_incremental_investment_evidence_audit.json
```

Primary reused Phase27 evidence:

- `reports/phase27_a7_existing_position_position_management_decision_authority_audit/`
- `reports/phase27_a8_add_authority_contract_review/`
- `reports/phase27_a9_canonical_buy_add_authority_unification_and_legacy_consumer_disposition_design_review/`
- `reports/phase27_a6_incremental_investment_eligibility_and_fallback_selection_diagnosis/`
- `reports/phase27_d6e_d6d_100bd_before_after_causal_attribution_and_adoption_review/`

## 6. Canonical ADD Authority Map

Canonical chain:

```text
PM ADD
-> Canonical Position Decision / position_intent
-> Portfolio Construction target membership / target_weight
-> Position Sizing target_quantity_candidate / quantity_delta_candidate
-> Runtime Planning BUY_ADD when current position has positive delta
-> Strategy Planning Authority / Pending
-> Approval / Safety
-> Submit
-> Execution / Fill / Ledger
```

The SoT states that ADD is intent, not a direct order. `docs/02_architecture/strategy_architecture_v1.md:1479` to `1511` and `docs/02_architecture/runtime_architecture_v2.md:2778` to `2825` define that PM ADD is not quantity authority and that BUY_ADD requires a positive `quantity_delta_candidate`.

Legacy ADD disposition remains non-canonical. The SoT classifies `sell_pipeline -> add_consumer -> pm_add_order_plan -> pending` as non-decision compatibility only. Phase27-A9 still found the legacy consumer active by code/tests, but no executable legacy ADD was observed in the A7 baseline.

## 7. Current ADD Eligibility

Current PM ADD implementation is threshold based. The actual branch is:

```text
no earlier EXIT / REDUCE branch selected
AND add_score >= 0.72
AND current_return > 0
AND buy_rank <= 5
AND downside_risk_score < 0.50
-> ADD
```

Source references:

- `src/ai_fund_lab_v2/position_management_ai/inference.py:371`
- `src/ai_fund_lab_v2/position_management_ai/inference.py:416`
- `src/ai_fund_lab_v2/runtime_v2/position_management/producer.py:882`
- `src/ai_fund_lab_v2/runtime_v2/position_management/producer.py:893`

Classification:

| Input | Current role |
|---|---|
| Trend / add score | Eligibility evidence |
| Rank | Eligibility evidence, not Action Authority |
| Profit / current return | Eligibility gate for no-loss averaging |
| Downside risk | Risk gate |
| BUY Quality | Present elsewhere, not explicit PM ADD gate |
| Market Context | Present elsewhere, not explicit PM ADD gate |
| Portfolio Fit | Present elsewhere, not explicit PM ADD gate |
| Corporate Event | Present elsewhere, not explicit PM ADD gate |
| Cash / exposure / concentration | Downstream constraints, not PM ADD Action Authority |

Expected Edge improvement and Incremental Investment Value are not explicit current ADD gates.

## 8. Current ADD Quantity Flow

Quantity authority is downstream of PM:

```text
Portfolio Construction target_weight
-> Position Sizing target_notional
-> Position Sizing target_quantity_candidate
-> Position Sizing quantity_delta_candidate
-> Runtime Planning planned_quantity
```

Observed A7 result:

| Quantity stage | Result |
|---|---:|
| PM ADD intent | 145 |
| ADD rows with positive quantity delta | 0 |
| ADD rows with zero delta | 145 |
| ADD rows with zero quantity | 145 |
| Runtime Planning BUY_ADD | 0 |

The observed reason pattern is `membership_intent:UNRESOLVED;pm_action:UNRESOLVED` in sizing and `current_position_zero_delta_maps_to_no_action` in planning.

## 9. ADD Funnel

| Funnel stage | Count |
|---|---:|
| Existing-position rows | 364 |
| PM ADD intent | 145 |
| Canonical Portfolio Construction ADD proven | 0 |
| Position Sizing positive ADD delta | 0 |
| Runtime Planning BUY_ADD | 0 |
| Submit ADD | 0 |
| Fill ADD | 0 |

The funnel loss occurs before executable planning: current ADD intent does not produce positive target quantity delta.

## 10. Zero Delta Analysis

All 145 PM ADD rows have `quantity_delta = 0`. All 364 existing-position rows in the A7 evidence map to Runtime Planning `NO_ACTION`.

Evidence:

```text
reports/phase28_a_add_baseline_and_incremental_investment_evidence_audit/zero_delta_inventory.json
```

Primary taxonomy:

```text
F. Zero Delta
H. Sizing Suppression
I. Planning Suppression
P. Observability Gap
```

## 11. Zero Quantity Analysis

All 145 PM ADD rows also have zero desired quantity or zero PM requested quantity. PM ADD is a directional intent; PM does not own broker quantity.

Evidence:

```text
reports/phase28_a_add_baseline_and_incremental_investment_evidence_audit/zero_quantity_inventory.json
```

## 12. Rank1 Existing Position Analysis

Rank1 existing-position rows:

| Classification | Count |
|---|---:|
| ADD Intent exists but Zero Delta | 76 |
| HOLD | 5 |
| REDUCE | 2 |
| EXIT | 3 |
| BUY_ADD | 0 |

Rank1 alone is not ADD authority. However, the fact that 76 Rank1 existing-position rows had PM ADD intent but no executable BUY_ADD is the strongest Phase28-B design input.

Evidence:

```text
reports/phase28_a_add_baseline_and_incremental_investment_evidence_audit/rank1_existing_position_inventory.json
```

## 13. ADD Outcome Analysis

Actual ADD fill count is 0. Therefore ADD-after 1D / 3D / 5D / 10D performance, realized ADD PnL, and incremental ADD contribution cannot be computed from actual ADD fills.

For PM ADD intent rows only, the next PM decision distribution is:

| Next PM decision | Count |
|---|---:|
| ADD | 127 |
| HOLD | 14 |
| REDUCE | 2 |
| EXIT | 1 |
| No next PM decision in evidence | 1 |

This is campaign-continuation evidence for PM ADD intent, not proof that actual ADD would have improved performance.

## 14. Campaign Attribution

Campaign attribution for ADD is missing because no ADD fills exist and PM ADD requests zero quantity. Any counterfactual performance after hypothetical ADD would be post-hoc and is prohibited as Strategy input.

## 15. Cash Utilization

Baseline cash evidence from `performance_report/cash_exposure.csv`:

| Metric | Value |
|---|---:|
| Average cash ratio | 50.108% |
| Median cash ratio | 49.949% |
| Min cash ratio | 24.191% |
| Max cash ratio | 72.541% |
| Final cash ratio | 65.965% |
| Average cash JPY | 482,473.5 |
| Final cash JPY | 649,480 |

Unused cash is not a defect by itself. The relevant finding is narrower: the run had cash available on many days, while high-rank existing positions with PM ADD intent did not become positive delta BUY_ADD.

## 16. Invested Ratio

| Metric | Value |
|---|---:|
| Average invested ratio | 49.892% |
| Median invested ratio | 50.051% |
| Min invested ratio | 27.459% |
| Max invested ratio | 75.809% |
| Final invested ratio | 34.035% |

This is Capital Efficiency evidence, not a force-deployment rule.

## 17. Concentration

No official concentration artifact was found for the audited run. A limited derived concentration inventory was computed from A7 PM `current_market_value` plus performance cash.

| Metric | Value |
|---|---:|
| Average Top1 concentration | 17.867% |
| Max Top1 concentration | 25.780% |
| Average Top3 concentration | 43.914% |
| Max Top3 concentration | 60.840% |

Limitation: A7 `current_weight` is zero in rows, so this is derived evidence and should not be treated as official concentration authority.

## 18. Capital Efficiency

Capital Efficiency gap is confirmed as an evidence-backed design target, not as a forced deployment defect. The current system can hold significant cash and simultaneously produce PM ADD intent for top-ranked existing holdings, but the canonical downstream chain does not produce ADD delta.

## 19. Opportunity Cost

Opportunity cost cannot be fully resolved in Phase28-A because the current artifacts do not provide an explicit ADD-vs-newBUY portfolio expected-value comparison. Opportunity rank and runtime opportunity score are present as evidence, but they are not sufficient Action Authority and must not be reinterpreted as ADD permission.

## 20. Failure Taxonomy

Observed taxonomy:

| Taxonomy | Count / Status |
|---|---:|
| A. Correct ADD | 0 |
| E. Expected Edge Evidence Missing | 145 |
| F. Zero Delta | 145 |
| G. Zero Quantity | 145 |
| H. Sizing Suppression | 145 |
| I. Planning Suppression | 145 |
| J. Submit Rejection | 0 |
| K. Capital Unavailable | Not observed as direct ADD blocker |
| L. Concentration Constraint | Not observed as direct ADD blocker |
| M. Safety Constraint | Not observed as direct ADD blocker |
| N. Opportunity Cost Misallocation | Insufficient evidence |
| O. Campaign Attribution Missing | 145 |
| P. Observability Gap | 145 |
| Q. Comparability Gap | Present |
| R. Evidence Insufficient | Present |

## 21. Architecture Gaps

Architecture gap remains:

```text
PM ADD intent is observed.
Canonical BUY_ADD path is defined.
Runtime PM ADD reaching canonical Portfolio Construction target weight / positive delta is not proven in the baseline.
```

This matches Phase27-A9 and is not repaired in Phase28-A.

## 22. Observability Gaps

Required observability gaps:

- Actual ADD fill sample is absent.
- ADD-specific Expected Edge improvement is absent.
- Incremental Investment Value field is absent.
- ADD-vs-newBUY Opportunity Cost comparison is absent.
- Official concentration inventory is absent for the audited run.
- ADD campaign attribution is absent because ADD fills are absent.

## 23. Comparability Limitations

The D6-D After run is adopted with limitations but lacks baseline-style `performance_report` parity. Baseline and After profiles/source commits differ and both recorded dirty source. Therefore Phase28-A numeric ADD baseline uses the baseline/A7 run as primary evidence.

## 24. Required Additional Evidence

Required evidence for future BUY_ADD validation:

- `reports/runtime_tests/runs/<run_id>/daily/<business_date>/strategy/portfolio_construction.json`
- `reports/runtime_tests/runs/<run_id>/daily/<business_date>/strategy/position_sizing.json`
- `reports/runtime_tests/runs/<run_id>/daily/<business_date>/strategy/runtime_planning.json`
- `reports/runtime_tests/runs/<run_id>/daily/<business_date>/execution/fills.json`
- `reports/runtime_tests/runs/<run_id>/daily/<business_date>/positions/position_campaigns.json`
- `reports/runtime_tests/runs/<run_id>/performance_report/trade_history.csv`

Required fields: PM action, target membership, target weight, target notional, target quantity, quantity delta, planning intent, planned quantity, pending item id, fill side, fill quantity, campaign id, cash, invested ratio, and concentration.

## 25. Phase28-B Design Inputs

Phase28-B should design, but not yet implement, these items:

- Expected Edge Improvement: define PIT evidence showing edge improved versus prior/current baseline.
- Incremental Investment Value: define additional notional value after lot, minimum order, cash, and concentration.
- Portfolio Opportunity Cost: compare ADD to new BUY candidates under common Expected Value.
- Concentration Risk: project post-ADD single-name and top concentration.
- Capital Efficiency: identify unused cash only when high-edge ADD eligibility passed and downstream authority blocked.
- Existing Position Rank: use rank as evidence, not direct ADD authority.
- ADD target weight: decide how PM ADD should influence Portfolio Construction target weight.
- ADD trace: require trace from PM ADD through target_weight, quantity_delta, planning, pending, fill.
- Acceptance metrics: ADD count, BUY_ADD count, ADD fill count, ADD hit rate, ADD post-fill outcome, cash/invested ratio, concentration, re-entry, and campaign attribution.

## 26. Risks

- Implementing ADD eligibility before the canonical PM ADD to Portfolio Construction connection is proven may create another action authority gap.
- Treating Rank1 as ADD authority would violate Expected Edge SoT.
- Treating cash as forced deployment would violate Strategy SoT.
- Using post-hoc ADD outcome as training or decision input would violate PIT and performance-result separation.

## 27. Final Judgment

Primary Judgment:

```text
PHASE28_A_ADD_BASELINE_AUDIT_COMPLETE_WITH_EVIDENCE_GAPS_PHASE28_B_CONDITIONAL
```

Secondary Judgments:

```text
CANONICAL_BUY_ADD_PATH_DEFINED_BUT_NO_EXECUTABLE_ADD_OBSERVED
PM_ADD_TO_PORTFOLIO_CONSTRUCTION_RUNTIME_CONNECTION_NOT_PROVEN_IN_BASELINE
EXPECTED_EDGE_IMPROVEMENT_AND_INCREMENTAL_VALUE_INPUTS_MISSING_FOR_CURRENT_ADD
ADD_OUTCOME_ATTRIBUTION_BLOCKED_BY_ZERO_ADD_FILLS
```

## 28. Phase28-B Entry Decision

```text
CONDITIONAL
```

Phase28-B may start as a design task only. It should first design Incremental Investment Eligibility and the PM ADD to Portfolio Construction target-weight bridge. It should not implement a performance change until the design separates Evidence, Eligibility Gate, Action Authority, Sizing Constraint, Safety Constraint, and Execution Constraint.
