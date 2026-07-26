# Phase20-BN Bull Loss / Bear Profit / Range No-Trade Attribution Audit

## Status

```text
PHASE20_BN_THREE_REGIME_ATTRIBUTION_COMPLETE
```

Supporting judgments:

```text
PHASE20_BN_BULL_ATTRIBUTION_PASS
PHASE20_BN_BEAR_ATTRIBUTION_PASS
PHASE20_BN_RANGE_ATTRIBUTION_PASS
PHASE20_BN_FUNNEL_ANALYSIS_PASS
PHASE20_BN_PRIORITY_RANKING_COMPLETE
PHASE20_BN_AI_CHANGE_NOT_REQUIRED
```

This phase is read-only attribution. No PM, Candidate, Opportunity, Capital, threshold, Accepted Generation, Training, Calibration, Broker, or Historical rerun was executed or changed.

## Sources

Reviewed:

- `docs/phase_reports/phase20_bm_run_scoped_final_performance_authority.md`
- `docs/phase_reports/phase20_bl_historical_market_evidence_source_contract.md`
- `docs/phase_reports/phase20_bk_range_campaign_reselection.md`
- `docs/phase_reports/phase20_bj_corporate_action_guard_and_runtime_continuation_contract.md`
- `docs/phase_reports/phase20_bi_feature_lookback_contract.md`
- `docs/02_architecture/autonomous_ai_operations_architecture.md`
- `docs/01_requirements/phase_roadmap.md`
- `reports/phase_reports/phase20_y_pm_cross_regime_campaign_analysis.json`

Generated read-only analysis:

```text
reports/phase20_bn_three_regime_trading_attribution_audit/analysis.json
reports/phase_reports/phase20_bn_three_regime_trading_attribution_audit.json
```

## Performance Authority

Phase20-BM established the performance authority:

| Regime | Run | Return | BUY | SELL | Authority |
|---|---|---:|---:|---:|---|
| Bull | `runtime-test-historical-extended-smoke-20260723T215847198556Z` | -4.512% | 5 | 10 | run-scoped position campaigns |
| Bear | `runtime-test-historical-extended-smoke-20260723T225746889854Z` | +8.828% | 5 | 11 | run-scoped position campaigns |
| Range | `runtime-test-historical-extended-smoke-20260724T030527368584Z` | 0.000% | 0 | 0 | canonical current / no-trade evidence |

## Bull Loss Attribution

Bull total PnL:

```text
realized = -45,420
unrealized = +300
total = -45,120
```

Position Campaign evidence:

| Symbol | Entry | Status | BUY price | SELL price(s) | PM actions | PM reason evidence | Final PnL |
|---|---|---|---:|---|---|---|---:|
| 58560 | 2026-03-24 | CLOSED 2026-03-25 | 34.0 | 30.0 | EXIT 1 | `hard_stop_current_return` | -22,400 |
| 60850 | 2026-03-24 | CLOSED 2026-03-25 | 296.5 | 247.9 | EXIT 1 | `hard_stop_current_return|profit_retention_break` | -34,020 |
| 65220 | 2026-03-24 | CLOSED 2026-03-25 | 1117.0 | 988.0 | EXIT 1 | `hard_stop_current_return|profit_retention_break` | -12,900 |
| 67400 | 2026-03-24 | CLOSED 2026-03-25 | 60.0 | 65.0 | EXIT 1 | `profit_retention_break` | +13,500 |
| 89180 | 2026-03-24 | OPEN | 9.0 | 10.0, 9.0, 9.0, 10.0, 10.0, 10.0 | ADD 4 / HOLD 9 / REDUCE 6 | REDUCE mainly `peak_drawdown_warning`; HOLD positive edge / contained risk | +10,700 |

Evidence-based finding:

- The Bull loss was concentrated in the initial 2026-03-24 basket. Four names closed on 2026-03-25; three of those exits realized losses.
- `60850`, `58560`, and `65220` together contributed approximately `-69,320`, offset by `67400` and `89180`.
- PM evidence shows early EXITs were triggered by hard stop / profit retention rules, not Runtime failure.
- `89180` was profitable after repeated REDUCEs and remains open with small unrealized profit.

Candidate score and full BUY reason bodies are not retained in run-scoped evidence, so direct Candidate-score attribution is `MISSING`.

## Bear Profit Attribution

Bear total PnL:

```text
realized = +88,280
unrealized = 0
total = +88,280
```

Main contributors:

| Symbol | Entry | Status | BUY price | SELL price(s) | PM actions | PM reason evidence | Final PnL |
|---|---|---|---:|---|---|---|---:|
| 60850 | 2026-03-02 | CLOSED 2026-03-03 | 203.7 | 289.1 | EXIT 1 | `profit_retention_break` | +59,780 |
| 67400 | 2026-03-02 | CLOSED 2026-03-09 | 27.0 | 25.0, 47.0 | ADD 1 / HOLD 2 / REDUCE 1 / EXIT 1 | HOLD trend/edge continuation; REDUCE peak drawdown; EXIT profit retention | +74,200 |
| 45960 | 2026-03-02 | CLOSED 2026-03-04 | 232.0 | 161.0 | HOLD 1 / EXIT 1 | hard stop / profit retention | -49,700 |
| 60720 | 2026-03-02 | CLOSED 2026-03-05 | 1075.0 | 1080.0 | ADD 1 / HOLD 1 / EXIT 1 | profit retention / trend continuation | +500 |
| 89180 | 2026-03-02 | OPEN | 9.0 | 9.0, 9.0, 10.0, 10.0, 9.0, 10.0 | ADD 6 / HOLD 7 / REDUCE 6 | peak drawdown warning; positive edge | +3,500 |

Evidence-based finding:

- Bear profit was pushed mainly by `60850` and `67400`, whose combined contribution was about `+133,980`.
- The large profit was not broad-based; `45960` had a large loss.
- BUY/Opportunity selection placed `60850` and `67400` into the initial basket. PM then retained/added/partially reduced `67400` and exited profitable `60850`.
- Reproducibility is not proven: `60850` lost in Bull and profited in Bear under the same accepted legacy model authority, so the evidence indicates regime/timing sensitivity rather than stable symbol quality.

## Range No-Trade Attribution

Range 20BD result:

```text
BUY = 0
SELL = 0
PM Decision = 0
Return = 0
```

Range funnel totals:

| Stage | 20BD total | Average / day | Evidence |
|---|---:|---:|---|
| Candidate AI rows | 1000 | 50.0 | `morning_manifest.candidate_count` |
| Opportunity rows | 1000 | 50.0 | `morning_manifest.opportunity_count` |
| selected rank count | 47 | 2.35 | `morning_manifest.selected_rank_count` |
| Planning candidates | 47 | 2.35 | `planning_evidence.candidate_count` |
| Listed BUY eligible | 0 | 0.0 | `planning_evidence.buy_eligibility_evidence` |
| Opportunity BUY eligible | 0 | 0.0 | `planning_evidence.opportunity_buy_eligibility_evidence` |
| BUY selected | 0 | 0.0 | `planning_evidence.selected_count` |
| BUY executed | 0 | 0.0 | `fills.json` |

Range no-trade reasons:

| Reason | Days |
|---|---:|
| `NO_SIGNAL:no_affordable_candidates_with_reliable_price` | 15 |
| `NO_SIGNAL:demo_capability_filtered_all_9000_series` | 5 |

Additional evidence:

```text
price_missing_count total = 25
budget_excluded_count total = 0
safety_block_buy = false on sampled planning evidence
capital_deployment_policy_used_by_morning = true
pm_status = NO_POSITION
```

Evidence-based finding:

- Range did not fail at Market Refresh, Feature Lookback, Data Readiness, Safety, PM, or Execution.
- Candidate/Opportunity producers emitted 50 rows per day.
- The zero occurred in BUY Planning / eligibility: after planning filters, no candidate became BUY eligible and no order was selected.
- Since there were no positions, PM correctly had no decisions.

## Opportunity Bottleneck Audit

| Regime | Candidate AI rows | Opportunity rows | Planning candidates | Opportunity BUY eligible | BUY selected | BUY executed |
|---|---:|---:|---:|---:|---:|---:|
| Bull | 1000 | 1000 | 258 | 108 | 77 | 5 |
| Bear | 1000 | 1000 | 305 | 78 | 70 | 5 |
| Range | 1000 | 1000 | 47 | 0 | 0 | 0 |

Evidence-based finding:

- Bull/Bear low BUY count is not because Candidate/Opportunity produced too few rows. Both had 1000/1000 AI rows and 70+ selected planning opportunities.
- Bull/Bear executed only 5 BUY because the first day filled the max-position basket; later selected opportunities did not become new executions.
- Range is different: the bottleneck is before BUY selection, at eligibility/price reliability/capability filtering.

## PM Attribution

PM decision distribution:

| Regime | HOLD | ADD | REDUCE | EXIT |
|---|---:|---:|---:|---:|
| Bull | 9 | 4 | 6 | 4 |
| Bear | 11 | 8 | 7 | 4 |
| Range | 0 | 0 | 0 | 0 |

Reason evidence:

- Bull and Bear REDUCE decisions are concentrated in `peak_drawdown_warning`.
- Bull early losing exits include `hard_stop_current_return` and `profit_retention_break`.
- Bear profitable exits for `60850` / `67400` include `profit_retention_break`.
- Range has no PM decisions because no position ever opened.

Cross-regime PM analysis:

| Action / cause | Count | Mean return 1BD | Mean return 5BD | 5BD positive rate |
|---|---:|---:|---:|---:|
| ADD | 12 | +0.0302 | +0.1878 | 33.3% |
| HOLD | 20 | +0.0676 | +0.3038 | 45.0% |
| REDUCE | 13 | -0.0509 | +0.1183 | 15.4% |
| EXIT | 8 | +0.0803 | +0.1274 | 37.5% |
| HOLD_BY_STRONG_CONTINUATION | 3 | +0.2972 | +1.8529 | 66.7% |
| REDUCE_BY_PEAK_DRAWDOWN_WARNING | 13 | -0.0509 | +0.1183 | 15.4% |

These are post-decision analysis metrics only. They are not Runtime decision inputs.

## Responsibility Classification

| Area | Evidence classification | Responsibility |
|---|---|---|
| Candidate | Candidate rows existed in all regimes; Candidate score bodies not retained. | Observability gap; not proven direct blocker |
| Opportunity | Bull/Bear produced selected opportunities; Range opportunity BUY eligible count was 0. | Strong Range no-trade responsibility candidate |
| Capital | Bull/Bear executed 5 initial BUY then no new BUY despite later selected opportunities. | Strong low-trade-count responsibility candidate |
| PM | Bull/Bear PnL after initial entry is shaped by EXIT/REDUCE/HOLD; Range has no PM role. | Bull/Bear outcome responsibility candidate |

## Improvement Candidate Ranking

This is not an implementation plan.

| Rank | Candidate | Responsibility | Priority | Expected Gain | Evidence Strength | Estimated Risk |
|---:|---|---|---|---|---|---|
| 1 | Range BUY eligibility / price reliability observability and policy review candidate | Opportunity / BUY Planning | HIGH | Unknown, high for Range activation | HIGH | MEDIUM |
| 2 | Capital max-position and redeployment review candidate | Capital | HIGH | Medium-high for trade count/diversification | HIGH | MEDIUM |
| 3 | PM EXIT/REDUCE attribution review candidate | PM | MEDIUM | Medium | MEDIUM | MEDIUM |
| 4 | Initial BUY selection regime sensitivity review candidate | Candidate / Opportunity | MEDIUM | Medium | MEDIUM | MEDIUM |
| 5 | Candidate score retention observability candidate | Candidate / Evidence | LOW | Unknown | LOW | LOW |

## Do Not Change In This Phase

```text
PM thresholds
Candidate model / logic
Opportunity model / logic
Capital policy
Accepted Generation
Training / Calibration
Broker
Bull / Bear / Range rerun
```

## Residual Risks

- Candidate scores and full BUY reason bodies are not retained run-scoped, limiting direct Candidate attribution.
- Fees, tax, slippage, and lot-level PnL remain unavailable.
- Bear profit concentration in `60850` and `67400` may be regime/timing-specific; reproducibility is not established by three 20BD runs.
- Range no-trade evidence points to BUY Planning eligibility/price/capability filters, but a deeper row-level explanation requires retained candidate/opportunity bodies or a targeted read-only artifact probe.

## Acceptance

```text
BN-R1 PASS
BN-R2 PASS
BN-R3 PASS
BN-R4 PASS
BN-R5 PASS
BN-R6 PASS
BN-R7 PASS
BN-R8 PASS
BN-R9 PASS
BN-R10 PASS
```

## Final Judgment

```text
PHASE20_BN_THREE_REGIME_ATTRIBUTION_COMPLETE
```
