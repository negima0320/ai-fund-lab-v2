# Phase24-B P24-GAP-01 Zero Deployment Root Cause Investigation

Task ID: `Phase24-B`

Task Name: `P24-GAP-01 Zero Deployment Root Cause Investigation`

Report date: 2026-07-31

Target run: `reports/runtime_tests/runs/runtime-test-historical-smoke-20260730T211110605880Z`

Target period: `2022-07-01` to `2022-07-07`

Focus symbol: `94320`

## 1. Primary Judgment

`PHASE24_B_P24_GAP01_ROOT_CAUSE_IDENTIFIED`

Root cause:

`94320` was `Opportunity Rank 1` and `BUY_ELIGIBLE`, but `Portfolio Policy` set `target_position_count = 0` under BEAR/CORRECTION and WEAK breadth conditions. `Portfolio Construction` therefore preserved the candidate as an `ADD_CANDIDATE` but assigned `target_membership = false` and `target_weight = 0.0` with `zero_weight_reason = no_investable_capacity`. `Position Sizing` converted this zero allocation into `quantity_delta_candidate = 0`, and `Runtime Planning` correctly emitted `planning_intent = NO_ORDER` with `no_order_reason = zero_quantity_delta`.

This is not evidence of Runtime malfunction. It is a design-consistent zero-deployment outcome and a Phase24 performance gap centered on Portfolio Policy aggressiveness/capacity calibration.

## 2. Executive Summary

The investigation confirms that the no-buy path for `94320` on `2022-07-07` is caused upstream of Position Sizing and Runtime Planning.

The direct decision point is `Portfolio Policy.target_position_count = 0`. The upstream context is conservative market state evidence: `trend_regime = BEAR` or `CORRECTION` across the target window, `market_breadth = WEAK`, and `deployment_posture = PAUSE`. Once target capacity was zero, downstream components correctly propagated the zero capacity:

```text
BUY_ELIGIBLE signal
-> Portfolio Policy target_position_count = 0
-> Portfolio Construction target_weight = 0.0
-> Position Sizing quantity_delta_candidate = 0
-> Runtime Planning NO_ORDER
-> Strategy Planning Authority NO_ORDER_AUTHORIZED
```

The root cause classification is:

| Case | Judgment | Evidence summary |
|---|---|---|
| Case A: design-consistent normal judgment | Yes | Zero BUY is valid when target weights or quantities are zero with explicit reasons. |
| Case B: Market Context conservative judgment | Yes, upstream | BEAR/CORRECTION and WEAK breadth fed policy reasons. |
| Case C: Portfolio Policy set Position Count to 0 | Yes, primary direct cause | `target_position_count = 0`, `deployment_posture = PAUSE`. |
| Case D: Capital Deployment suppressed capital | No standalone canonical cause | Capital Deployment is noncanonical after AQ; no separate capital artifact changed planning output. |
| Case E: Position Sizing lot/weight/cash constraint made zero | No as independent cause | Sizing zero came from `target_weight = 0.0`, not lot/cash binding. |
| Case F: Runtime Planning converted to NO_ORDER | Yes, downstream propagation | `no_order_reason = zero_quantity_delta`. |
| Case G: multiple-component normal zero result | Yes | Components propagated the policy zero-capacity decision. |
| Case H: design-unintended suppression | Not proven | Evidence supports design-consistent suppression, not Runtime defect. |

## 3. Reviewed Evidence

Required handoff and SoT:

- `docs/phase_reports/phase23_to_phase24_chatgpt_handoff.md`
- `docs/phase_reports/phase23_final_summary_and_phase24_handoff.md`
- `docs/phase_reports/phase23_bv_phase21_design_conformance_full_architecture_runtime_evidence_closure_review.md`
- `docs/phase_reports/phase24_a_performance_evaluation_contract.md`
- `docs/01_requirements/phase_roadmap.md`
- `docs/03_ai_design/market_context_design.md`
- `docs/03_ai_design/portfolio_manager_policy_design.md`
- `docs/03_ai_design/capital_deployment_design.md`
- `docs/02_architecture/portfolio_construction_and_position_sizing_contract.md`

Runtime evidence:

- `reports/runtime_tests/runs/runtime-test-historical-smoke-20260730T211110605880Z/daily/2022-07-07/strategy/market_context.json`
- `reports/runtime_tests/runs/runtime-test-historical-smoke-20260730T211110605880Z/daily/2022-07-07/strategy/portfolio_policy.json`
- `reports/runtime_tests/runs/runtime-test-historical-smoke-20260730T211110605880Z/daily/2022-07-07/strategy/portfolio_construction.json`
- `reports/runtime_tests/runs/runtime-test-historical-smoke-20260730T211110605880Z/daily/2022-07-07/strategy/position_sizing.json`
- `reports/runtime_tests/runs/runtime-test-historical-smoke-20260730T211110605880Z/daily/2022-07-07/strategy/runtime_planning.json`
- `reports/runtime_tests/runs/runtime-test-historical-smoke-20260730T211110605880Z/daily/2022-07-07/morning/planning_evidence.json`
- `reports/runtime_tests/runs/runtime-test-historical-smoke-20260730T211110605880Z/daily/2022-07-07/morning/strategy_planning_authority_evidence.json`

Design authority highlights:

- Market Context provides market posture/reasons to Portfolio Policy, PM, Portfolio Construction; it does not directly decide symbol BUY/SELL.
- Portfolio Policy owns target cash/exposure/position count and BUY/ADD/REDUCE/EXIT bias.
- Portfolio Construction owns target membership and `target_weight`.
- Position Sizing consumes `target_weight`; it must not reinterpret raw opportunity score into weight or quantity.
- Runtime Planning consumes `target_quantity_candidate`, `quantity_delta_candidate`, and `quantity_status`; it does not recompute quantity from opportunity score or notional.
- Capital Deployment is no longer a standalone canonical Strategy decision stage after AQ; retained artifacts are noncanonical observability only.

## 4. Market Context Analysis

### 2022-07-07 Evidence

| Field | Value |
|---|---|
| Authority | Market Context artifact |
| Producer | Market Context Engine |
| Consumer | Portfolio Policy, Portfolio Construction, Position Management, Attribution |
| Input | PIT market price/volume/features through `2022-07-07` |
| Judgment | Conservative market context |
| Output | `trend_regime = BEAR`, `volatility_regime = NORMAL`, `market_breadth = WEAK`, `confidence = 0.981132542038` |

Interpretation:

`2022-07-07` was not an aggressive deployment day. The artifact was high confidence but classified the market as `BEAR` with `WEAK` breadth. This did not directly forbid buying `94320`; instead it became policy input.

### Period Pattern

| Date | Trend regime | Breadth | Volatility | Confidence |
|---|---:|---:|---:|---:|
| 2022-07-01 | BEAR | WEAK | NORMAL | 0.976660903927 |
| 2022-07-04 | CORRECTION | WEAK | NORMAL | 0.982228247474 |
| 2022-07-05 | CORRECTION | WEAK | NORMAL | 0.977413793103 |
| 2022-07-06 | BEAR | WEAK | NORMAL | 0.980507210343 |
| 2022-07-07 | BEAR | WEAK | NORMAL | 0.981132542038 |

## 5. Portfolio Policy Analysis

### 2022-07-07 Evidence

| Field | Value |
|---|---|
| Authority | Portfolio Policy artifact |
| Producer | Portfolio Policy Engine |
| Consumer | Portfolio Construction, Position Management, downstream planning |
| Input | Market Context, policy config, current portfolio/capacity evidence |
| Judgment | Deployment pause with zero target position capacity |
| Output | `target_position_count = 0`, `target_gross_exposure_ratio = 0.46`, `cash_reserve = 0.5`, `risk_posture = BALANCED`, `deployment_posture = PAUSE` |

Reason codes:

```text
internal_dynamic_cash_exposure:BEAR
internal_dynamic_cash_exposure:NORMAL
internal_dynamic_cash_exposure:WEAK
internal_dynamic_cash_exposure:low_opportunity_capacity
internal_dynamic_position_count:fixed_position_count_safety_hard_maximum_removed
internal_dynamic_position_count:market_breadth:WEAK
internal_dynamic_position_count:market_or_policy_risk_constrained
internal_dynamic_position_count:trend_regime:BEAR
internal_dynamic_position_count:volatility_regime:NORMAL
```

`target_position_count = 0` is the direct root cause of the zero-deployment path. The Policy output treated the day as a pause day even though BUY_ELIGIBLE opportunities existed.

### Period Pattern

| Date | Policy target_position_count | Deployment posture | Cash reserve | Target gross exposure ratio |
|---|---:|---|---:|---:|
| 2022-07-01 | 0 | PAUSE | 0.50 | 0.46 |
| 2022-07-04 | 0 | PAUSE | 0.46 | 0.54 |
| 2022-07-05 | 0 | PAUSE | 0.46 | 0.54 |
| 2022-07-06 | 0 | PAUSE | 0.50 | 0.46 |
| 2022-07-07 | 0 | PAUSE | 0.50 | 0.46 |

Contrast:

On `2022-07-08`, Market Context moved to `trend_regime = RANGE`, and Portfolio Policy emitted `target_position_count = 1`, `cash_reserve = 0.36`, `target_gross_exposure_ratio = 0.64`, and `deployment_posture = DEFENSIVE_DEPLOYMENT`. Phase23 handoff evidence records the first `BUY_NEW` for `94320` on that date.

## 6. Capital Deployment Analysis

| Field | Value |
|---|---|
| Authority | No standalone canonical Capital Deployment decision after AQ |
| Producer | Not canonical for this final planning path |
| Consumer | Runtime Planning must not be changed by noncanonical retained Capital Deployment artifacts |
| Input | Policy target, target weight, execution feasibility inputs when present |
| Judgment | No independent capital suppression identified |
| Output | No canonical capital-deployment output caused `94320` to be zero |

The current boundary contract states that Capital Deployment is no longer a standalone canonical Strategy decision stage. The relevant capital-like values are visible through Portfolio Policy and Target Weight Authority:

- `cash_reserve = 0.5`
- `target_gross_exposure = 0.46`
- `single_name_weight_cap = 0.18`
- `resolved_target_member_count = 0`

The observed zero was not caused by deployable cash shortage, single-name cap, or broker feasibility. It was caused before sizing by zero investable membership capacity.

## 7. Portfolio Construction Analysis

### `94320` on 2022-07-07

| Field | Value |
|---|---|
| Authority | Target Weight Authority |
| Producer | Portfolio Construction |
| Consumer | Position Sizing |
| Input | Candidate, Opportunity Ranking, current portfolio, Portfolio Policy |
| Judgment | Preserve candidate/rank but assign zero target allocation |
| Output | `membership_intent = ADD_CANDIDATE`, `target_membership = false`, `target_weight = 0.0` |

Key evidence:

| Field | Value |
|---|---|
| `input_opportunity_rank` | `1` |
| `runtime_opportunity_score` | `0.4255533` |
| `membership_intent` | `ADD_CANDIDATE` |
| `membership_reason` | `candidate_eligible;opportunity_rank_preserved` |
| `target_membership` | `false` |
| `target_weight` | `0.0` |
| `target_weight_resolution.status` | `PASS` |
| `target_weight_resolution.reason` | `no_investable_capacity` |
| `target_weight_resolution.zero_weight_reason` | `no_investable_capacity` |
| `target_weight_authority.target_position_count` | `0` |
| `target_weight_authority.resolved_target_member_count` | `0` |

Interpretation:

Portfolio Construction did not discard the opportunity evidence. It preserved rank and eligibility lineage, then applied Policy capacity. Since resolved target member count was zero, target membership and target weight were zero.

## 8. Position Sizing Analysis

### `94320` on 2022-07-07

| Field | Value |
|---|---|
| Authority | Position Sizing artifact |
| Producer | Position Sizing |
| Consumer | Runtime Planning |
| Input | `target_weight = 0.0`, equity/capital context, reference price, trading unit, current position |
| Judgment | Zero allocation becomes zero quantity delta |
| Output | `target_quantity_candidate = 0`, `quantity_delta_candidate = 0` |

Key evidence:

| Field | Value |
|---|---:|
| `positions_sized` | `0` |
| `total_target_weight` | `0.0` |
| `target_weight` | `0.0` |
| `target_notional` | `0.0` |
| `incremental_buy_notional` | `0.0` |
| `target_quantity_candidate` | `0` |
| `quantity_delta_candidate` | `0` |
| `quantity_status` | `RESOLVED_ZERO_DELTA` |
| `sizing_status` | `RESOLVED_ZERO_ALLOCATION` |
| `reference_price` | `153.9` |
| `trading_unit` | `100` |
| `minimum_meaningful_notional` | `50000.0` |

Reason codes:

```text
actual_target_position_count_zero
zero_allocation_authorized
```

Interpretation:

Position Sizing did not independently suppress a positive allocation because of lot size, minimum notional, or cash. It received `target_weight = 0.0`, and therefore correctly emitted a zero notional and zero quantity delta.

## 9. Runtime Planning Analysis

### `94320` on 2022-07-07

| Field | Value |
|---|---|
| Authority | Runtime Planning artifact |
| Producer | Runtime Planning |
| Consumer | Strategy Planning Authority / pending writer |
| Input | Position Sizing quantity candidate and Opportunity authority lineage |
| Judgment | Zero quantity delta maps to no order |
| Output | `planning_intent = NO_ORDER`, `planned_quantity = 0` |

Key evidence:

| Field | Value |
|---|---|
| `opportunity_authority.opportunity_rank` | `1` |
| `opportunity_authority.opportunity_eligibility` | `BUY_ELIGIBLE` |
| `opportunity_authority.opportunity_expected_edge_score` | `0.4255533` |
| `target_quantity_candidate` | `0` |
| `quantity_delta_candidate` | `0` |
| `quantity_status` | `RESOLVED_ZERO_DELTA` |
| `quantity_required` | `false` |
| `planning_intent` | `NO_ORDER` |
| `planned_quantity` | `0` |
| `no_order_reason` | `zero_quantity_delta` |
| `order_side_intent` | `NONE` |
| `pending_eligibility` | `NOT_REQUIRED` |
| `pending_candidate_contract.pending_candidate_generated` | `false` |
| `pending_candidate_contract.submit_allowed` | `false` |

Reason codes:

```text
no_order_zero_quantity_delta
portfolio_add_candidate_maps_to_buy_new
```

Morning evidence:

| Artifact | Status | Pending item count |
|---|---|---:|
| `morning/planning_evidence.json` | `NO_ORDER_AUTHORIZED` | `0` |
| `morning/strategy_planning_authority_evidence.json` | `NO_ORDER_AUTHORIZED` | `0` |

Interpretation:

Runtime Planning did not override a positive order into zero. It consumed a zero quantity delta and emitted the expected `NO_ORDER` state.

## 10. Root Cause Tree

```text
BUY_ELIGIBLE
94320 Opportunity Rank 1, expected_edge_score 0.4255533

↓

Market Context
BEAR / WEAK / NORMAL, confidence 0.981132542038
Conservative input to policy, not direct BUY prohibition

↓

Portfolio Policy
target_position_count = 0
deployment_posture = PAUSE
reason: market_breadth:WEAK + trend_regime:BEAR + market_or_policy_risk_constrained + low_opportunity_capacity

↓

Capital Deployment
No standalone canonical suppression
capital-like policy values propagate as capacity/equity constraints

↓

Portfolio Construction
candidate preserved as ADD_CANDIDATE
target_membership = false
target_weight = 0.0
zero_weight_reason = no_investable_capacity

↓

Position Sizing
target_notional = 0.0
target_quantity_candidate = 0
quantity_delta_candidate = 0
reason: actual_target_position_count_zero; zero_allocation_authorized

↓

Runtime Planning
planning_intent = NO_ORDER
planned_quantity = 0
no_order_reason = zero_quantity_delta

↓

NO_ORDER
Strategy Planning Authority status = NO_ORDER_AUTHORIZED
pending_item_count = 0
```

## 11. Root Cause Classification

Primary classification:

```text
Case C: Portfolio PolicyがPosition Countを0にした
```

Supporting classifications:

```text
Case B: Market Contextが保守判断を出した
Case A: 設計どおり正常判断
Case G: 複数Componentの結果として正常に0株となった
Case F: Runtime PlanningがNO_ORDERへ変換した
```

Rejected or not primary:

```text
Case D: Capital Deploymentが資金利用を抑制した
Case E: Position Sizingが単元・Weight・Cash制約により0株にした
Case H: 設計意図と異なる抑制
```

`Case E` is only mechanically true in the sense that Position Sizing emitted zero quantity. It is not the root cause because the evidence reason is zero target allocation from Policy capacity, not lot/cash/minimum-unit binding.

## 12. Runtime Correctness vs Performance

Runtime correctness:

- PASS for the investigated path.
- Authority lineage exists from Opportunity Ranking through Portfolio Construction, Position Sizing, Runtime Planning, and Strategy Planning Authority.
- `NO_ORDER` is explicitly authorized by `zero_quantity_delta`.
- No evidence of HALT, authority missing, cash inconsistency, ledger inconsistency, future leakage, or safety violation causing the zero deployment.

Performance gap:

- P24-GAP-01 is real because investable-looking `BUY_ELIGIBLE` opportunities existed while deployment stayed at zero.
- The performance question is not whether Runtime should have forced a buy.
- The performance question is whether Portfolio Policy's conservative capacity rule is too restrictive for this regime/opportunity mix.

## 13. Improvement Candidates

No implementation was performed.

Candidate hypotheses for future controlled experiments:

| Candidate | Hypothesis | Component | Expected effect | Main risk | Regression scope |
|---|---|---|---|---|---|
| P24-B-IC-01 | Allow minimum exploratory position count when high-ranked opportunities exist under non-crash BEAR/RANGE-like conditions. | Portfolio Policy | Reduce zero deployment and cash drag. | Higher drawdown in weak markets. | 10BD, 20BD, 60BD, 200BD, 1Y. |
| P24-B-IC-02 | Separate market-breadth weakness from absolute no-buy capacity. | Portfolio Policy | Preserve defensive posture while allowing limited deployment. | Overtrading low-quality breadth periods. | Regime-segment attribution. |
| P24-B-IC-03 | Add diagnostic attribution fields explaining target_position_count=0 contributors. | Observability only | Faster performance diagnosis without changing behavior. | Report/schema churn. | Artifact compatibility and contract tests. |
| P24-B-IC-04 | Compare target_position_count=0 days against subsequent opportunity returns post-hoc. | Evaluation only | Quantify opportunity cost of zero deployment. | Must avoid using Runtime PnL as learning input. | Phase24 evaluation contract. |

Future implementation must follow Phase24-A:

```text
1 hypothesis
1 change
before/after baseline preserved
no Runtime correctness changes mixed with performance changes
```

## 14. Recommended Next Task

Recommended next task:

```text
Phase24-C P24-GAP-02 Cash Utilization and Target Position Count Attribution
```

Purpose:

Quantify how many days and how much opportunity notional were lost to `target_position_count = 0`, `deployment_posture = PAUSE`, cash reserve, and zero target allocation across the 10BD baseline before proposing any Strategy parameter experiment.

