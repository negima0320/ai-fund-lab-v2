# Phase19-BP Position Management EXIT / REDUCE Distribution Audit

- Phase: `Phase19-BP`
- Title: `Position Management EXIT / REDUCE Distribution Audit`
- Judgment: `PM_EXIT_REDUCE_REACHABLE_RUNTIME_COMMON__HISTORICAL_PROFILE_DID_NOT_TRIGGER_EXIT_REDUCE`
- JSON evidence: `reports/phase_reports/phase19_bp_position_management_exit_reduce_distribution_audit.json`

## Scope

This audit investigates why the Phase19 historical smoke Position Management decisions produced:

```text
HOLD   79
ADD    16
REDUCE 0
EXIT   0
```

The objective is not to force SELL output. The objective is to verify whether Production Runtime remains capable of producing SELL when Position Management policy legitimately emits EXIT / REDUCE.

Architecture and Contract inputs reviewed:

- `docs/02_architecture/autonomous_ai_operations_architecture.md`
- `docs/phase_reports/phase18_final_summary_and_phase19_handoff.md`
- `docs/phase_reports/phase18_to_phase19_chatgpt_handoff.md`
- `docs/01_requirements/phase_roadmap.md`
- `docs/02_architecture/runtime_architecture_v2.md`
- `docs/02_architecture/ai_artifact_registry_and_capital_allocation_contract.md`
- `docs/03_ai_design/position_management_ai_design.md`

Implementation and runtime evidence reviewed:

- `src/ai_fund_lab_v2/position_management_ai/inference.py`
- `src/ai_fund_lab_v2/runtime_v2/position_management/producer.py`
- `.runtime/runtime_state/position_management/<date>/position_management_decisions.json`
- `.runtime/runtime_state/position_management/<date>/current_holdings_snapshot.csv`
- `.runtime/runtime_state/position_management/<date>/position_management_opportunity_context.csv`
- `.runtime/operations/feature_artifacts/<date>/position_feature_input.parquet`

## Contract Findings

Position Management is responsible for hold / sell / reduce / add signals, not for BUY AI authority or capital allocation. The design states that PM should hold while upward continuation remains valid, sell when the scenario fails, and reduce when continuation remains but risk increases.

The artifact contract treats PM as a code-policy authority, not an external model artifact. PM Decision Artifacts are eligible for Sell Planning, and PM code-policy / runtime adapter artifacts must be accepted before Runtime consumption.

The Runtime adapter is common across `historical`, `demo`, and `production`; `produce_position_management_decisions` explicitly accepts only these three modes and calls the same PM inference path.

## Current Decision Logic

Score generation is in `build_position_management_output`:

- `hold_score = 0.35 * trend + 0.25 * opportunity + 0.20 * profit + 0.20 * (1 - risk_penalty)`
- `exit_score = calculate_exit_score(...)`
- `add_score = calculate_add_score(...)`
- `reduce_score = calculate_reduce_score(...)`

Decision priority in `classify_position_action`:

1. `EXIT` if hard exit reasons exist, or `exit_score >= 0.80`.
2. `REDUCE` if downside / drawdown / reduce / weak-hold conditions are met and trend or expected edge is still positive.
3. `EXIT` from the same risk block if trend and expected edge are not supportive.
4. `ADD` if `add_score >= 0.72`, current return is positive, rank is top 5, and downside risk is below 0.50.
5. Otherwise `HOLD`.

Important thresholds:

- Hard stop: `current_return <= -0.08`
- Profit retention break: `drawdown_from_peak <= -0.12`
- Trend and opportunity broken: `trend_score < 0.30 and expected_edge <= 0`
- Bad risk guard: `bad/ng/blocked/risk_bad/high_risk`
- Exit score threshold: `exit_score >= 0.80`
- Reduce risk block: `downside_risk_score >= 0.65`, `drawdown_from_peak <= -0.07`, `reduce_score >= 0.62`, or `hold_score < 0.42`
- ADD: `add_score >= 0.72`, positive current return, `buy_rank <= 5`, downside below 0.50

Runtime mapping:

- `EXIT` becomes `SELL_FULL_POSITION` with `runtime_sell_quantity = current position quantity`.
- `REDUCE` becomes `REVIEW_REQUIRED_REDUCE_QUANTITY_CONTRACT_MISSING`; partial sell quantity is not yet defined.
- `ADD` is outside SELL Planning scope.

## Historical Evidence

Artifacts inspected:

```text
20 business-date artifacts
19 PASS days with positions
1 NO_POSITION day
95 decisions
```

Decision distribution:

```text
HOLD 79
ADD 16
REDUCE 0
EXIT 0
```

Score distribution over the 95 decisions:

| Score | Min | Median | Max | Mean |
|---|---:|---:|---:|---:|
| hold_score | 0.53434595 | 0.61903508 | 0.66051769 | 0.61439992 |
| exit_score | 0.17543829 | 0.21033739 | 0.33676789 | 0.21897024 |
| reduce_score | 0.12840810 | 0.14715979 | 0.29439289 | 0.15994965 |
| add_score | 0.00000000 | 0.67234898 | 0.81051362 | 0.38680449 |

Threshold observations:

```text
exit_score >= 0.80: 0
reduce_score >= 0.62: 0
hold_score < 0.42: 0
exit_score >= 0.30: 6
reduce_score >= 0.30: 0
```

Reason distribution:

```text
positive_expected_edge|downside_risk_contained: 79
strong_trend_continuation|opportunity_rank_still_high|no_loss_averaging; ADD is outside SELL Planning scope: 16
```

## PM Feature Input Evidence

Input values were not static. Daily variation was confirmed from PM holding snapshots and PM feature artifacts.

Holding snapshot variation:

| Field | Min | Max | Unique values | Symbols with daily variation |
|---|---:|---:|---:|---:|
| holding_days | 1 | 27 | 19 | 5 |
| current_return | -0.044118 | 0.089744 | 75 | 5 |
| peak_return | 0.000000 | 0.089744 | 40 | 5 |
| current_price | 157.0 | 1319.0 | 71 | 5 |
| entry_price | 156.0 | 1284.0 | 5 | 0 |
| position_size | 100.0 | 1000.0 | 3 | 0 |

PM feature artifact variation:

| Field | Min | Max | Unique values | Symbols with daily variation |
|---|---:|---:|---:|---:|
| holding_days | 1 | 27 | 19 | 5 |
| unrealized_return | -0.044118 | 0.089744 | 75 | 5 |
| current_price | 157.0 | 1319.0 | 71 | 5 |

Opportunity context variation:

| Field | Min | Max | Unique values |
|---|---:|---:|---:|
| expected_edge_score | 11.785224 | 19408.606553 | 950 |
| buy_rank | 1 | 50 | 50 |
| downside_risk_score | 0.012825 | 0.693211 | 933 |
| candidate_score | 1.0 | 1.0 | 1 |
| candidate_rank | 1 | 50 | 50 |

All 950 Opportunity context rows had positive `expected_edge_score`.

Important note: the PM feature artifact currently contains Runtime position fields such as `holding_days`, `current_price`, and `unrealized_return`. Market technical features used by the PM scorer, such as `return_5d`, `return_20d`, `close_over_ma_20d`, `ma_5_20_ratio`, `volume_ratio_5d`, and `volatility_20d`, were not present in the observed PM feature artifacts. Therefore the PM scorer relied primarily on Runtime holding state plus Opportunity context.

## Root Cause

The 95 decisions were all HOLD / ADD because the historical smoke portfolio did not enter the PM policy's deterioration region.

Observed positions stayed within mild return and risk ranges:

- `current_return` min was `-4.4118%`, above the hard stop threshold of `-8%`.
- `exit_score` max was `0.33676789`, far below `0.80`.
- `reduce_score` max was `0.29439289`, far below `0.62`.
- `hold_score` min was `0.53434595`, above the weak-hold threshold of `0.42`.
- Risk guard status was empty / not bad.
- Opportunity expected edge was positive for every ranked row.

This is not evidence that EXIT is impossible. It is evidence that the 20BD historical smoke profile did not stress PM into EXIT / REDUCE conditions.

Secondary policy concern: the current Opportunity `expected_edge_score` values are large positive raw scores relative to the PM policy's original normalized expected-edge assumptions. This makes `positive_expected_edge` almost always true and saturates the Opportunity continuation contribution. However, hard EXIT conditions still override it, and REDUCE is still reachable when risk conditions are met.

## Production Commonality

The same Runtime PM adapter handles `historical`, `demo`, and `production`; no historical-specific PM logic was found or changed.

Counterfactual evidence using the unchanged common producer:

| Mode | Case | Decision | Runtime action | Sell quantity | Key scores |
|---|---|---|---|---:|---|
| historical | deterioration | EXIT | SELL_FULL_POSITION | 100 | exit 0.958, hold 0.0712 |
| demo | deterioration | EXIT | SELL_FULL_POSITION | 100 | exit 0.958, hold 0.0712 |
| production | deterioration | EXIT | SELL_FULL_POSITION | 100 | exit 0.958, hold 0.0712 |
| historical | high risk continuation | REDUCE | REVIEW_REQUIRED_REDUCE_QUANTITY_CONTRACT_MISSING | 0 | reduce 0.51006786, exit 0.31033333 |
| demo | high risk continuation | REDUCE | REVIEW_REQUIRED_REDUCE_QUANTITY_CONTRACT_MISSING | 0 | reduce 0.51006786, exit 0.31033333 |
| production | high risk continuation | REDUCE | REVIEW_REQUIRED_REDUCE_QUANTITY_CONTRACT_MISSING | 0 | reduce 0.51006786, exit 0.31033333 |

This confirms:

- EXIT is reachable in Production-common logic and maps to full SELL quantity.
- REDUCE is reachable in Production-common logic.
- REDUCE is not yet an automatic partial SELL because Runtime v2 lacks a reduce quantity contract.

## Classification

Runtime defect:

```text
NO for EXIT / full SELL reachability.
PARTIAL_GAP for REDUCE auto quantity contract.
```

AI Policy defect:

```text
REVIEW_REQUIRED.
PM consumes Opportunity expected_edge as a positive / normalized continuation signal, while current Runtime Opportunity values are large positive raw scores. This should be reviewed as a PM-Oppportunity score-scale contract issue, not patched by lowering SELL thresholds.
```

Test Profile defect:

```text
YES.
The 20BD smoke profile did not include deteriorating holdings sufficient to exercise EXIT / REDUCE.
```

## Fix Decision

No immediate runtime code fix is required for Phase19-BP.

Do not change thresholds just to produce SELL.
Do not add historical-only behavior.
Do not add ticker-specific behavior.

Recommended follow-ups:

1. Add a PM distribution audit/regression check that explains zero EXIT / REDUCE via input distribution.
2. Review the Opportunity-to-PM score-scale contract and decide whether PM should consume calibrated expected edge instead of raw Opportunity score.
3. Define a REDUCE quantity contract before enabling automatic partial SELL.

## Regression / Re-run

Regression targets if PM / Opportunity contract logic changes:

- `tests/runtime_v2/test_phase15af_position_management_runtime_connection.py`
- `tests/runtime_v2/test_phase15ap_position_management_input_contract.py`
- `tests/runtime_v2/test_phase19_bn_pm_opportunity_model_authority.py`

Historical Smoke re-run:

```text
Not required for this audit because no production/runtime code was changed.
Required only after a PM policy, PM input contract, Opportunity score contract, or REDUCE quantity contract change.
```
