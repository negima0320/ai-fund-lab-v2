# Phase20-Q: Position Management Design Review

## 1. Executive Summary

This is a read-only design review of Position Management.

No implementation changes were made. The review compares architecture documents, implementation, and 20BD evidence for:

- Position Management Architecture
- REDUCE / HOLD / EXIT decisions
- `decision_reason` generation
- thresholds, input features, confidence, state, and transition behavior

Conclusion: current Position Management is a deterministic rule / score policy, exposed as `Position Management AI` but not a trained model inference in the reviewed Runtime path. The Runtime adapter validates Current / Feature / Opportunity inputs, calls the Phase6-A policy inference, and emits a Runtime decision artifact consumed by Sell Planning.

## 2. Reviewed Sources

- `docs/03_ai_design/position_management_ai_design.md`
- `docs/02_architecture/position_management_feature_input_contract.md`
- `docs/02_architecture/position_management_reduce_quantity_contract.md`
- `docs/02_architecture/runtime_architecture_v2.md`
- `src/ai_fund_lab_v2/position_management_ai/inference.py`
- `src/ai_fund_lab_v2/runtime_v2/position_management/producer.py`
- `.runtime/runtime_state/position_management/*/position_management_decisions.json`
- `reports/runtime_tests/runs/runtime-test-historical-extended-smoke-20260722T082906704807Z/daily/*/position_management/pm_decisions.json`

## 3. Architecture

Position Management owns the investment decision for already-held positions:

```text
HOLD / ADD / REDUCE / EXIT
```

It does not decide new BUY candidates, BUY ranking, BUY amount, or broker execution. The Runtime adapter prepares held-position input, validates feature/opportunity/current contracts, calls the Phase6-A PM policy, and writes `.runtime/runtime_state/position_management/<business_date>/position_management_decisions.json`.

Implementation path:

```text
Runtime Current positions
Position Feature artifact
Opportunity context
↓
runtime_v2/position_management/producer.py
↓
position_management_ai/inference.py
↓
position_management_decisions.json
↓
Sell Planning
```

Evidence: adapter path resolution and inference call are in [producer.py](/Users/negishi/work/ai-fund-lab-v2/src/ai_fund_lab_v2/runtime_v2/position_management/producer.py:324) and [producer.py](/Users/negishi/work/ai-fund-lab-v2/src/ai_fund_lab_v2/runtime_v2/position_management/producer.py:290). Score / action generation is in [inference.py](/Users/negishi/work/ai-fund-lab-v2/src/ai_fund_lab_v2/position_management_ai/inference.py:312).

## 4. Rule Based Or AI

Current reviewed behavior is rule based.

The module is named `position_management_ai`, but the live decision logic computes deterministic scores and applies threshold rules. I did not find a trained model load / predictor call in the Runtime PM path. The accepted PM identity is a Runtime adapter / policy set, and the adapter verifies accepted source authority before producing decisions.

## 5. Input Features

PM consumes three input groups.

Current / holding state:

```text
symbol/code
quantity / position_size
average_price / entry_price
current_price
current_return
peak_return
holding_days
market_value
```

Opportunity context:

```text
expected_edge_score
buy_rank
downside_risk_score
risk_guard_status
candidate_score / candidate_rank where available
buy_reason / no_buy_reason where available
```

Technical features:

```text
price_momentum_return_5d
price_momentum_return_20d
trend_close_over_ma_20d
trend_ma_5_20_ratio
volume_momentum_ratio_5d
volatility_return_std_20d
```

The feature input contract forbids future/result/leakage fields. The inference code joins holding, opportunity, and feature rows by `target_date` and `code`.

## 6. Score Formulas

The policy calculates:

```text
trend_score
opportunity_score
profit_score
risk_penalty
hold_score
exit_score
add_score
reduce_score
```

Important formulas:

```text
hold_score =
0.35 * trend_score
+ 0.25 * opportunity_score
+ 0.20 * profit_score
+ 0.20 * (1 - risk_penalty)
```

`exit_score` weights weak trend, MA break, drawdown, negative current return, and downside risk.

`reduce_score` weights trend, risk, drawdown from peak, and downside risk:

```text
0.30 * trend_score
+ 0.30 * risk_score
+ 0.25 * normalized drawdown
+ 0.15 * downside_risk_score
```

Evidence: score construction is in [inference.py](/Users/negishi/work/ai-fund-lab-v2/src/ai_fund_lab_v2/position_management_ai/inference.py:328), and score helper formulas are in [inference.py](/Users/negishi/work/ai-fund-lab-v2/src/ai_fund_lab_v2/position_management_ai/inference.py:491).

## 7. Decision Flow

Decision order is strict:

```text
1. EXIT rules
2. REDUCE rules
3. ADD rules
4. HOLD fallback
```

This means an EXIT trigger dominates REDUCE and HOLD. REDUCE is considered only after no EXIT trigger has fired. HOLD is the final fallback after EXIT / REDUCE / ADD are not selected.

Evidence: `classify_position_action()` in [inference.py](/Users/negishi/work/ai-fund-lab-v2/src/ai_fund_lab_v2/position_management_ai/inference.py:355).

## 8. State Machine

The implemented state machine is implicit and recomputed daily from Current and feature context:

```text
OPEN POSITION
↓
HOLD when risk / exit / add rules do not trigger
↓
REDUCE when risk has increased but trend/opportunity is not broken
↓
EXIT when hard stop, profit retention break, or trend/opportunity break fires
↓
CLOSED POSITION
```

There is no durable PM-internal per-position state machine found in the reviewed code. Persistent state is held outside PM:

- Runtime Current / Persistent Ledger
- Position Feature context, including `holding_days` and `peak_return`
- Position Campaign observability generated later by Runtime Test summarize/observability

## 9. EXIT Conditions

EXIT is generated when any of the following is true:

```text
current_return <= -0.08
drawdown_from_peak <= -0.12
trend_score < 0.30 and expected_edge <= 0
risk_guard_status in bad/ng/blocked/risk_bad/high_risk
exit_score >= 0.80
```

Reasons:

- `hard_stop_current_return`: `current_return <= -0.08`
- `profit_retention_break`: `drawdown_from_peak <= -0.12`
- `trend_and_opportunity_broken`: `trend_score < 0.30 and expected_edge <= 0`
- `risk_guard_status_bad`: bad risk guard status
- `exit_score_high`: score-only fallback when `exit_score >= 0.80`
- `weak_hold_score`: REDUCE branch would otherwise fire, but trend/opportunity is also weak

Runtime adapter emits:

```text
runtime_action = SELL_FULL_POSITION
runtime_sell_quantity = current position quantity
runtime_quantity_authority = PM_EXIT_FULL_POSITION_QUANTITY
```

Evidence: EXIT rule block is in [inference.py](/Users/negishi/work/ai-fund-lab-v2/src/ai_fund_lab_v2/position_management_ai/inference.py:371), and Runtime payload mapping is in [producer.py](/Users/negishi/work/ai-fund-lab-v2/src/ai_fund_lab_v2/runtime_v2/position_management/producer.py:523).

## 10. REDUCE Conditions

REDUCE is generated only if no EXIT rule has fired and any risk/reduction trigger is true:

```text
downside_risk_score >= 0.65
or drawdown_from_peak <= -0.07
or reduce_score >= 0.62
or hold_score < 0.42
```

Then PM chooses REDUCE only if:

```text
trend_score >= 0.35
or expected_edge > 0
```

Otherwise it returns EXIT with `weak_hold_score`.

Reasons:

- `peak_drawdown_warning`: `drawdown_from_peak <= -0.07`
- `risk_increased_but_trend_not_broken`: fallback when risk/reduction trigger fires but no explicit risk reason was added and trend/opportunity remains alive
- `high_downside_risk_score`: generated internally when downside risk is very high; not observed in the reviewed 20BD PM evidence

Runtime adapter emits:

```text
runtime_action = SELL_PARTIAL_POSITION_REDUCE_QUANTITY_BY_SELL_PLANNING
runtime_sell_quantity = 0
runtime_quantity_authority = SELL_PLANNING_REDUCE_QUANTITY_CONTRACT
```

PM emits reduce intent and intensity; Sell Planning owns executable quantity. Evidence: [producer.py](/Users/negishi/work/ai-fund-lab-v2/src/ai_fund_lab_v2/runtime_v2/position_management/producer.py:533), and REDUCE authority contract [position_management_reduce_quantity_contract.md](/Users/negishi/work/ai-fund-lab-v2/docs/02_architecture/position_management_reduce_quantity_contract.md:7).

## 11. REDUCE Quantity Decision

PM does not decide broker-final REDUCE quantity.

PM emits `reduce_intensity`:

```text
STRONG if reduce_score >= 0.60 or reason includes high_downside
MEDIUM if reduce_score >= 0.50 or reason includes peak_drawdown_warning
LIGHT otherwise
```

Sell Planning converts intensity to target ratio:

```text
LIGHT = 0.25
MEDIUM = 0.33
STRONG = 0.50
```

Sell Planning then applies:

```text
raw_reduce_quantity = min(position_quantity_before, sellable_quantity) * target_reduce_ratio
rounded_reduce_quantity = floor(raw_reduce_quantity / tradable_unit) * tradable_unit
final_sell_quantity = rounded_reduce_quantity
```

Default tradable unit is `100`. If rounded quantity is zero, the formal outcome is non-executable terminal, not HOLD, EXIT, or a zero-share order.

Evidence: intensity mapping is in [producer.py](/Users/negishi/work/ai-fund-lab-v2/src/ai_fund_lab_v2/runtime_v2/position_management/producer.py:580); quantity contract is in [position_management_reduce_quantity_contract.md](/Users/negishi/work/ai-fund-lab-v2/docs/02_architecture/position_management_reduce_quantity_contract.md:32).

## 12. HOLD Conditions

HOLD is fallback when EXIT, REDUCE, and ADD do not trigger.

HOLD reason components:

- `trend_continuation`: `trend_score >= 0.50`
- `positive_expected_edge`: `expected_edge > 0`
- `downside_risk_contained`: `downside_risk_score < 0.50`
- `hold_score_above_exit_threshold`: fallback when no reason component is added

HOLD means the position remains open and no SELL order is requested.

Evidence: HOLD block in [inference.py](/Users/negishi/work/ai-fund-lab-v2/src/ai_fund_lab_v2/position_management_ai/inference.py:414).

## 13. Confidence

Confidence is not a calibrated probability in the reviewed implementation.

The Runtime adapter maps confidence directly to the selected action score:

```text
HOLD -> hold_score
EXIT -> exit_score
REDUCE -> reduce_score
ADD -> add_score
```

Evidence: [producer.py](/Users/negishi/work/ai-fund-lab-v2/src/ai_fund_lab_v2/runtime_v2/position_management/producer.py:1455).

## 14. Evidence Summary

For `runtime-test-historical-extended-smoke-20260722T082906704807Z`, run-scoped PM evidence contains:

```text
decision_count = 44
HOLD = 23
REDUCE = 10
EXIT = 9
ADD = 2
```

Reason distribution:

```text
hard_stop_current_return = 7
positive_expected_edge = 23
downside_risk_contained = 22
risk_increased_but_trend_not_broken = 7
trend_and_opportunity_broken = 3
peak_drawdown_warning = 3
profit_retention_break = 1
trend_continuation = 5
strong_trend_continuation = 2
opportunity_rank_still_high = 2
no_loss_averaging = 2
```

Examples:

```text
2026-06-18 50310 REDUCE
reason = risk_increased_but_trend_not_broken
hold_score = 0.19584299
exit_score = 0.67572355
reduce_score/confidence = 0.32732983
reduce_intensity = LIGHT

2026-07-03 67400 REDUCE
reason = peak_drawdown_warning
hold_score = 0.37511568
exit_score = 0.45524761
reduce_score/confidence = 0.48865071
reduce_intensity = MEDIUM

2026-06-22 66590 EXIT
reason = hard_stop_current_return|profit_retention_break|trend_and_opportunity_broken
exit_score/confidence = 0.91477083
runtime_sell_quantity = 1300
```

## 15. Strength

- Clear authority split: PM decides investment action; Sell Planning decides executable REDUCE quantity.
- Rule reasons are inspectable and mostly traceable to concrete thresholds.
- EXIT dominates REDUCE, preventing an obvious weak position from being partially reduced instead of exited.
- Input contract is fail-closed for missing/stale PM feature and opportunity evidence.
- Future/leakage fields are explicitly prohibited and audited.
- REDUCE below minimum tradable quantity has a formal non-executable terminal path after Phase20-M/P.

## 16. Weakness

- The system is named AI, but the reviewed path is deterministic rule/scoring policy; this can mislead performance interpretation.
- `confidence` is an action score, not calibrated probability or uncertainty.
- `risk_increased_but_trend_not_broken` is a broad fallback reason; it can hide which trigger actually fired, especially `hold_score < 0.42` or `reduce_score >= 0.62`.
- HOLD is fallback after other branches. A HOLD can mean genuinely strong continuation or merely no stronger rule fired.
- PM does not retain its own durable per-position state; it depends on Current / features to provide `holding_days` and `peak_return`.
- `REDUCE` intensity thresholds are separate from REDUCE decision thresholds and are not obviously performance-calibrated in current evidence.
- Some inputs default in scoring code when absent (`expected_edge_score=0`, `buy_rank=999`, `downside_risk_score=0.50`), although Runtime contract attempts to prevent missing required runtime inputs.

## 17. Improvement Candidates

No implementation change is proposed or performed in this phase. Candidate items for later experiment/design phases:

- Rename or document current PM as `policy/scoring adapter` unless or until a trained model is used.
- Separate confidence from score by adding calibration or uncertainty evidence.
- Split `risk_increased_but_trend_not_broken` into explicit reason codes for each trigger.
- Add a decision trace artifact containing raw trigger booleans and score components.
- Review REDUCE thresholds and intensity mapping against realized post-decision evidence.
- Review HOLD fallback cases separately from high-quality continuation HOLDs.
- Add explicit per-campaign state inputs if future design requires memory beyond Current / feature-derived state.

## 18. Final Status

```text
PHASE20_Q_POSITION_MANAGEMENT_DESIGN_REVIEW_COMPLETE
```

This phase was investigation only. No code, Runtime behavior, PM behavior, Sell Planning behavior, Risk behavior, Opportunity behavior, AI artifact, Broker behavior, Training, Calibration, Validation, or historical run was changed.
