# Phase19-BS Post-Fix Position Management Decision and Trading Distribution Audit

- Phase: `Phase19-BS`
- Run ID: `runtime-test-historical-smoke-20260721T102119329463Z`
- Target: Phase19-BR post-fix 20 business day Historical Smoke
- Judgment: `MIXED__BR_SCALE_FIX_EFFECTIVE__PM_EXIT_SELL_OCCURRED__PM_FEATURE_CONTRACT_GAP_REMAINS__20BD_PROFILE_LIMITED`
- JSON evidence: `reports/phase_reports/phase19_bs_post_fix_pm_decision_and_trading_distribution_audit.json`

## Executive Summary

Phase19-BR fixed the Runtime BUY AI Accepted Generation path. The post-fix Opportunity Runtime artifacts now use the generation-bound preprocessing and StandardScaler:

```text
transformation_stage = accepted_generation_bound_imputer_scaler_model
legacy_fallback_used = false
accepted_generation_id = phase19_aq_accepted_generation_641e6e313543f013
opportunity_scaler_hash = 820e17c08c9844aa953c9bcce880ffd671a900cbc3dac062eddd7dafcc6c7548
```

The pre-fix `expected_edge_score` scale of `11` to `20000` is gone. The BR post-fix 20BD Opportunity artifact distribution is:

| Metric | Value |
|---|---:|
| rows | 1000 |
| min | -0.42747597 |
| p05 | -0.351704748 |
| p25 | -0.2524290825 |
| median | -0.12735459 |
| mean | -0.08088520142 |
| p75 | 0.041122725 |
| p95 | 0.424820033 |
| max | 0.68264543 |
| std | 0.2286993567 |
| positive / zero / negative | 312 / 0 / 688 |
| unique | 1000 |

Position Management did not remain all HOLD / ADD. The post-fix PM distribution over 47 held-position decisions was:

```text
HOLD   29
ADD    11
REDUCE  4
EXIT    3
```

The 3 EXIT decisions mapped to `SELL_FULL_POSITION`, produced SELL Planning items, were approved, submitted, and recorded as 3 SELL executions. The 4 REDUCE decisions did not become partial SELL orders because Runtime v2 still lacks a REDUCE Quantity Contract; they correctly emitted `REVIEW_REQUIRED_REDUCE_QUANTITY_CONTRACT_MISSING`.

Final classification is `Mixed`: the BQ Runtime score-scale defect is fixed, EXIT/SELL lifecycle is working, PM remains continuation-biased by design, PM technical feature input completeness remains a contract gap, and 20BD is too short to make a strategy-level turnover conclusion.

## Audit Scope

Required Architecture / Contract / Design documents reviewed:

- `docs/02_architecture/autonomous_ai_operations_architecture.md`
- `docs/02_architecture/runtime_architecture_v2.md`
- `docs/02_architecture/ai_input_output_and_artifact_contract.md`
- `docs/02_architecture/ai_generation_artifact_contract.md`
- `docs/02_architecture/ai_artifact_registry_and_capital_allocation_contract.md`
- `docs/03_ai_design/opportunity_ai_design.md`
- `docs/03_ai_design/position_management_ai_design.md`
- `docs/phase_reports/phase19_bp_position_management_exit_reduce_distribution_audit.md`
- `docs/phase_reports/phase19_bq_pm_opportunity_score_scale_contract_audit.md`
- `docs/phase_reports/phase19_br_accepted_generation_bound_runtime_inference_fix.md`

Implementation reviewed:

- `src/ai_fund_lab_v2/runtime_v2/buy_ai/generation_bound_inference.py`
- `src/ai_fund_lab_v2/runtime_v2/buy_ai/producer.py`
- `src/ai_fund_lab_v2/runtime_v2/position_management/producer.py`
- `src/ai_fund_lab_v2/position_management_ai/inference.py`
- `src/ai_fund_lab_v2/runtime_v2/planning/sell_pipeline.py`

Runtime evidence reviewed:

- `.runtime/runtime_state/buy_ai/<date>/opportunity_rankings.json`
- `.runtime/runtime_state/position_management/<date>/position_management_opportunity_context.csv`
- `.runtime/runtime_state/position_management/<date>/current_holdings_snapshot.csv`
- `.runtime/runtime_state/position_management/<date>/position_management_decisions.json`
- `.runtime/runtime_state/sell_pipeline/<date>/order_plan.json`
- `.runtime/runtime_state/morning_pipeline/<date>/order_plan.json`
- `.runtime/persistent_ledger/orders.jsonl`
- `.runtime/persistent_ledger/executions.jsonl`
- `.runtime/runtime_state/current_valuation/<date>/current_valuation_refresh.json`
- `.runtime/operations/feature_artifacts/<date>/position_feature_input.parquet`

The BR run completed 20 business days from `2026-06-17` through `2026-07-14`, with `registry_unchanged=true`, `accepted_artifact_unchanged=true`, `broker_write_performed=false`, and `external_delivery_performed=false`.

## Contract Basis

Architecture SoT states that production-equivalent Runtime BUY AI must use one accepted generation and must not resolve latest/manual/legacy fallbacks. The AI Generation Artifact Contract requires scaler artifacts whenever the model declares scaled preprocessing, and Runtime may use them only through the Accepted Generation Manifest binding model, scaler, feature order, and hashes.

Runtime Architecture v2 states that Runtime is a control layer and must not embed AI investment logic. It consumes AI Decision Artifacts and moves them through planning, approval, submit, execution, ledger, and current-state transitions.

Position Management design states that PM manages held positions only. Its philosophy is to hold while upward continuation remains valid, sell when the scenario fails, and reduce when risk rises without full scenario failure.

## Opportunity Score Distribution

All 20 Opportunity artifacts were `PASS`; all used:

```text
model_version = phase19_aq_accepted_generation_641e6e313543f013:opportunity:48f469dddc739d85
model_hash = 48f469dddc739d85a544ddeda5682ef0f5c8b3c9ece889cdc8fe5d9f54643966
transformation_stage = accepted_generation_bound_imputer_scaler_model
legacy_fallback_used = false
scaler_hash = 820e17c08c9844aa953c9bcce880ffd671a900cbc3dac062eddd7dafcc6c7548
```

`expected_edge_score`, `opportunity_score`, and `expected_return` matched for every row:

```text
alias_mismatch_count = 0 / 1000
```

This confirms the BQ defect is not reproduced. The post-fix output is a decimal model-prediction scale with both positive and negative values, not the pre-fix oversized raw unscaled range.

## Opportunity To PM Trace

Data flow:

```text
Runtime Opportunity Artifact
-> position_management_opportunity_context.csv
-> held-position joined PM input
-> Position Management Decision
```

For the 950 PM opportunity-context rows, Date/Symbol joins matched the Runtime Opportunity artifact exactly:

| Field | Compared | Max abs diff | Mismatches > 1e-12 |
|---|---:|---:|---:|
| expected_edge_score | 950 | 0.0 | 0 |
| buy_rank | 950 | 0.0 | 0 |
| downside_risk_score | 950 | 0.0 | 0 |
| candidate_score | 950 | 0.0 | 0 |
| candidate_rank | 950 | 0.0 | 0 |

The 50 `right_only_opportunity` rows are the `2026-06-17` Opportunity rows when PM had `NO_POSITION`; they are not join mismatches. No clipping, multiply, divide, log transform, re-normalization, sign conversion, or Historical-only transform was found between Opportunity artifact and PM context.

## PM Internal Opportunity Contribution

PM implementation uses:

```text
edge_score = normalize_range(expected_edge_score, -0.10, 0.20)
opportunity_continuation = 0.65 * edge_score + 0.35 * rank_score
```

Post-fix held-position `expected_edge_score` distribution over 47 decisions:

| Metric | Value |
|---|---:|
| min | -0.1836869 |
| p05 | 0.07369449 |
| median | 0.47295441 |
| mean | 0.4394255234 |
| p95 | 0.65168819 |
| max | 0.68264543 |
| positive / negative | 45 / 2 |

PM edge normalization distribution:

| Metric | Value |
|---|---:|
| min | 0.0 |
| median | 1.0 |
| mean | 0.9335851993 |
| max | 1.0 |
| saturation at 0 | 1 |
| saturation at 1 | 39 |
| non-saturated | 7 |

Important judgment: full saturation was fixed, but saturation remains high for held positions because the BR-selected holdings are concentrated in high-ranked Opportunity names with `expected_edge_score > 0.20`. This is not a recurrence of the BQ Runtime defect; it is the interaction of accepted model output distribution, top-ranked portfolio selection, and PM's `[-0.10, 0.20]` continuation normalization range.

## PM Decision Distribution

PM status:

```text
PASS        19 days
NO_POSITION 1 day
```

Decision distribution:

| Decision | Count | Ratio |
|---|---:|---:|
| HOLD | 29 | 61.70% |
| ADD | 11 | 23.40% |
| REDUCE | 4 | 8.51% |
| EXIT | 3 | 6.38% |

Runtime action distribution:

| Runtime action | Count |
|---|---:|
| NO_SELL_ORDER | 29 |
| NO_SELL_ORDER_ADD_OUT_OF_SELL_SCOPE | 11 |
| REVIEW_REQUIRED_REDUCE_QUANTITY_CONTRACT_MISSING | 4 |
| SELL_FULL_POSITION | 3 |

Reason distribution:

| Reason | Count |
|---|---:|
| positive_expected_edge\|downside_risk_contained | 29 |
| strong_trend_continuation\|opportunity_rank_still_high\|no_loss_averaging; ADD is outside SELL Planning scope | 11 |
| peak_drawdown_warning; reduce quantity contract is not defined in Runtime v2 | 3 |
| risk_increased_but_trend_not_broken; reduce quantity contract is not defined in Runtime v2 | 1 |
| hard_stop_current_return\|profit_retention_break | 2 |
| profit_retention_break | 1 |

Score and feature distributions:

| Field | Min | Median | Mean | Max |
|---|---:|---:|---:|---:|
| hold_score | 0.23054745 | 0.61627883 | 0.58749297 | 0.68851844 |
| add_score | 0.0 | 0.0 | 0.19135399 | 0.78681775 |
| reduce_score | 0.17908449 | 0.21152532 | 0.26383783 | 0.63256840 |
| exit_score | 0.20037785 | 0.24132727 | 0.28770595 | 0.63416667 |
| downside_risk_score | 0.22047188 | 0.26926875 | 0.32759519 | 0.70000000 |
| current_return | -0.174757 | 0.0 | 0.00592472 | 0.105263 |
| drawdown_from_peak | -0.20000036 | 0.0 | -0.01312241 | 0.105263 |
| holding_days | 1 | 6 | 7.53191489 | 21 |

EXIT was triggered by hard deterioration:

- `2026-06-19` / `81050`: `hard_stop_current_return|profit_retention_break`, quantity `800`
- `2026-06-22` / `43780`: `hard_stop_current_return|profit_retention_break`, quantity `200`
- `2026-06-23` / `66590`: `profit_retention_break`, quantity `2900`

REDUCE was triggered 4 times but remained non-executing:

- `2026-06-18` / `81050`: `peak_drawdown_warning`
- `2026-06-19` / `66590`: `risk_increased_but_trend_not_broken`
- `2026-06-22` / `66590`: `peak_drawdown_warning`
- `2026-06-30` / `89180`: `peak_drawdown_warning`

## BUY / SELL / PM Lifecycle

Trading ledger summary for the 20BD run:

```text
Submit orders: BUY 5, SELL 3
Executions:    BUY 5, SELL 3
Final pending order items: 0
```

Lifecycle consistency:

- `2026-06-17`: PM `NO_POSITION`; Morning BUY plan created and approved 5 BUY items; 5 BUY executions recorded.
- `2026-06-19`: PM `EXIT 1`; Sell Planning created 1 SELL item; approval `APPROVED`; 1 SELL execution recorded.
- `2026-06-22`: PM `EXIT 1`; Sell Planning created 1 SELL item; approval `APPROVED`; 1 SELL execution recorded.
- `2026-06-23`: PM `EXIT 1`; Sell Planning created 1 SELL item; approval `APPROVED`; 1 SELL execution recorded.
- All non-EXIT days: Sell Planning `NO_ACTION` / `NO_SIGNAL:exit_ai_no_sell_signal`.

No PM/SELL lifecycle defect was found. EXIT decisions are connected to Sell Planning, Submit, Execution, Ledger, and Current State. REDUCE does not route to partial SELL because the Runtime action is explicitly review-required until quantity semantics are defined.

## Portfolio Activity

Portfolio summary:

| Metric | Value |
|---|---:|
| initial valuation equity reference | 1,018,800 |
| final equity | 979,300 |
| return from first valuation | -3.8771% |
| max drawdown | -7.5579% |
| realized PnL final | -29,200 |
| unrealized PnL final | 8,500 |
| position count min / median / max | 2 / 2 / 5 |
| cash utilization min / median / max | 31.90% / 33.08% / 77.31% |

Daily position count moved from 5 after initial BUY to 4, then 3, then 2 after the three EXIT SELLs. Cash rose from `231,200` to `655,300` after the exits. Market value ended at `324,000`.

No existing SoT turnover definition was found for this audit. As a reference only, turnover was computed as:

```text
sum(abs(execution cash_effect or price * quantity)) / same-day total_equity
```

Reference turnover:

| Metric | Value |
|---|---:|
| active turnover days | 4 / 20 |
| median daily turnover | 0.0 |
| mean daily turnover | 0.05979286 |
| max daily turnover | 0.75461327 |

This is audit evidence only and must not be treated as a new Contract definition.

## Before / After Comparison

The comparison is mostly directly comparable for Runtime score-scale, PM input, PM decisions, and lifecycle because both audits used 20BD Historical Smoke evidence over the same date range and the same Accepted Generation authority. Portfolio/trading outcomes are partially comparable because BR changed BUY AI runtime scores and therefore portfolio path.

| Category | Metric | Before BP/BQ | After BR | Comparability |
|---|---|---:|---:|---|
| Opportunity | expected_edge min | 11.78522441 | -0.42747597 | Direct |
| Opportunity | expected_edge median | 675.340566745 | -0.12735459 | Direct |
| Opportunity | expected_edge mean | 2297.7138219916 | -0.08088520 | Direct |
| Opportunity | expected_edge max | 20212.96186064 | 0.68264543 | Direct |
| PM Input | held-position expected_edge median | 7067.29309122 | 0.47295441 | Direct |
| PM Internal | normalized edge saturation at 1 | 95 / 95 | 39 / 47 | Direct |
| PM Internal | non-saturated edge contribution | 0 / 95 | 7 / 47 | Direct |
| PM Decision | HOLD / ADD / REDUCE / EXIT | 79 / 16 / 0 / 0 | 29 / 11 / 4 / 3 | Direct |
| PM Reason | positive_expected_edge | 95 / 95 | 45 / 47 | Direct |
| Trading | BUY / SELL executions | 5 / 0 | 5 / 3 | Partially comparable |
| Portfolio | final position count | 5 | 2 | Partially comparable |
| Capital | final cash utilization | not primary BQ metric | 33.08% | Partially comparable |
| Risk | max drawdown | not primary BQ metric | -7.56% | Partially comparable |
| Activity | active turnover days | not primary BQ metric | 4 / 20 | Partially comparable |
| Holding | median holding days | 13? not SoT in BQ table | 6 | Partially comparable |

The key causal comparison is direct: once Opportunity score scale was fixed, PM no longer saw every edge as massively positive, EXIT/REDUCE became naturally reachable in the real 20BD run, and EXIT led to actual SELL executions.

## HOLD Bias Re-evaluation

Runtime defect candidates:

| Candidate | Judgment | Evidence |
|---|---|---|
| PM Feature not updating | Not primary defect | Holding state values changed daily; PM row counts changed with positions. Technical market features remain absent, but this is a feature contract gap, not a stale-file failure. |
| Opportunity score abnormal scale | Fixed | Post-fix range `-0.427` to `0.683`, 688 negative rows in 1000. |
| PM input join failure | No | 950 PM context rows matched Opportunity artifact values exactly. |
| drawdown/current_return calculation failure | No | EXIT/REDUCE were triggered by current return and drawdown deterioration. |
| PM Decision artifact generation failure | No | 47 decisions generated, including EXIT and REDUCE. |
| Sell Planning connection failure | No for EXIT | 3 EXIT decisions became 3 SELL plans and 3 SELL executions. |

AI Policy / strategy candidates:

| Candidate | Judgment | Evidence |
|---|---|---|
| HOLD condition too dominant | Review required, not proven defect | 29 HOLD reasons still use `positive_expected_edge|downside_risk_contained`; PM design explicitly favors holding while continuation remains valid. |
| EXIT threshold unreachable | No | 3 EXIT occurred in production-common logic. |
| REDUCE threshold unreachable | No | 4 REDUCE occurred. |
| positive_expected_edge overly supports HOLD | Partial policy concern | 45 / 47 held decisions had positive edge; held names are top-ranked and 39 / 47 edge normalizations still saturated at 1. |
| ADD favors adding over rotation | Review required | 11 ADD decisions occurred but ADD is outside SELL scope. Strategy turnover requirements are not yet defined. |

Test profile candidates:

| Candidate | Judgment | Evidence |
|---|---|---|
| 20BD period short | Yes | Only 47 PM decisions after exits; long-run turnover cannot be concluded. |
| Position sample small | Yes | Portfolio falls to 2 positions from `2026-06-23` onward. |
| Market regime / holdings path limited | Yes | Early deterioration caused 3 exits, then remaining positions were mostly HOLD/ADD. |

## PM Feature Completeness

The observed PM feature artifacts still do not contain the technical fields consumed by PM scorer fallbacks:

```text
return_5d
return_20d
close_over_ma_20d
ma_5_20_ratio
volume_ratio_5d
volatility_20d
```

No alias equivalents were present either. This was true for all 20 dates.

Contract judgment:

- PM design expects market/technical information.
- Current Runtime PM input contract requires `target_date` and `code`, while implementation treats these technical fields as optional with defaults.
- Therefore this is not an immediate Runtime defect under the current artifact contract.
- It is a real `Contract mismatch / PM Feature Input Contract Completion` gap because the PM policy's trend/risk components are partially default-driven rather than market-feature-driven.

This should be fixed by completing the Production-common PM Feature Input Contract, not by Historical-only fixtures and not by threshold tuning.

## Production Commonality

No Historical-only score conversion or PM policy branch was found:

- BUY AI normal path resolves the Accepted Generation and applies manifest-bound model/scaler/feature order/hash validation.
- PM producer accepts only `historical`, `demo`, and `production` modes and calls the same inference path.
- PM Opportunity context copies Opportunity values without re-scaling.
- PM decision logic is shared.
- Sell Planning consumes only EXIT decisions as SELL sources; REDUCE remains review-required because quantity semantics are missing.

Historical mode affects external effects and execution simulation, not the AI score scale or PM decision policy. `broker_write_performed=false` confirms no real broker write occurred.

## Root Cause Classification

Final classification:

```text
Mixed
```

Detailed classification:

| Class | Judgment |
|---|---|
| Runtime defect | No for BR score scale and EXIT/SELL lifecycle. The prior BQ Runtime defect is fixed. |
| AI Policy defect | Review required, not proven. PM remains continuation-biased by design and may still saturate top-held Opportunity edge contributions. |
| Contract mismatch | Partial gap remains: PM technical feature input completeness and REDUCE quantity contract. Opportunity score-scale mismatch is fixed. |
| Test Profile limitation | Yes. 20BD and small post-exit portfolio are insufficient for turnover strategy conclusions. |
| No defect | Not the full classification because feature and REDUCE contract gaps remain. |

User expectation gap classification:

```text
E. 複数要因が存在する
```

Reason:

- BR naturally improved SELL occurrence: 3 EXIT SELLs were produced and executed.
- Runtime is now normal for Opportunity score scale and EXIT lifecycle.
- PM policy still favors continuation when expected edge is positive and downside risk is contained.
- PM technical feature contract is incomplete.
- 20BD is too short and the portfolio becomes too small to judge strategic turnover adequacy.

## Fix Need

Do not change PM thresholds or normalize `expected_edge_score` again for SELL volume. The audit does not identify a Runtime behavior defect requiring immediate code change.

Required next work:

1. Define and implement a Production-common `Position Management Feature Input Contract Completion` for the technical features PM already consumes.
2. Define `Position Management REDUCE Quantity Contract` before allowing REDUCE to become automatic partial SELL.
3. Evaluate `Position Management Strategy / Turnover Requirement Contract` with longer historical evidence before changing HOLD/EXIT/REDUCE thresholds.

## Regression And Smoke Decision

Regression targets if the next phase changes code:

- BUY AI Accepted Generation inference parity / fail-closed tests
- Opportunity artifact schema and PM context value-equality tests
- PM feature input contract tests
- PM decision distribution smoke
- Sell Planning EXIT lifecycle tests
- REDUCE quantity contract tests if implemented
- Historical Smoke after any Runtime behavior change

Historical Smoke rerun for Phase19-BS:

```text
Not required
```

BS is audit-only and used the BR 20BD run. No Runtime behavior change was made in BS.

## Final Judgment

Phase19-BR fixed the Opportunity score-scale Contract violation. With correct inputs, Position Management generated HOLD, ADD, REDUCE, and EXIT decisions, and EXIT decisions produced SELL executions through the Production-common lifecycle. Therefore the earlier all-HOLD/ADD state was not a permanent SELL incapability.

The remaining work is not to force SELL. It is to complete PM feature input semantics, define REDUCE quantity behavior, and separately decide whether the desired investment strategy requires a more active turnover policy.
