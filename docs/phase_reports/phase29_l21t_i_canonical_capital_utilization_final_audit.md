# Phase29-L21T-I - Canonical Capital Utilization Final Audit

Task ID: `Phase29-L21T-I`

Audit mode: READ-ONLY source/artifact audit. No runtime mutation, code/config/schema change, fresh-run, resume-run, or long Historical run was performed.

Target run:

`reports/runtime_tests/runs/runtime-test-historical-smoke-20260812T051059691425Z`

Evaluation period: `2022-08-23` to `2022-09-16`, 19 business days, initial cash/equity `1,000,000` JPY.

## Primary Judgment

`PHASE29_L21T_I_CANONICAL_CAPITAL_UTILIZATION_FINAL_AUDIT_COMPLETE_RUNTIME_REPAIR_CONTINUATION_NOT_RECOMMENDED_STRATEGY_CAPITAL_DEPLOYMENT_REVIEW_RECOMMENDED`

The canonical runtime/accounting result is:

- Runtime execution: `PASS`
- Trading state: `PASS`
- Accounting state: `PASS`
- Close status: `REVIEW_REQUIRED`, caused by non-blocking strategy shadow review, not by a blocking runtime/accounting failure
- Canonical final equity: `970,360` JPY
- Canonical total PnL: `-29,640` JPY
- Canonical return: `-2.964%`
- Canonical final current position count: `4`
- Canonical final invested notional: `545,780` JPY
- Canonical final invested ratio: `56.2451%`
- Canonical final cash ratio: `43.7549%`

The previously observed ad-hoc aggregation result `final PV 987,090 / return -1.29% / final position count 19` is rejected as non-canonical for this audit. `987,090` is the `2022-09-15` end-of-day total equity, not the final `2022-09-16` equity. `19` is consistent with mixed campaign/history/nested evidence counting, not current holdings. Canonical current holdings are the ledger-owned `candidate_current.positions` at the final current valuation snapshot.

## Run Status Resolution

There are two different status surfaces:

- `fresh_run_summary.json`: `status=REVIEW_REQUIRED`, `exit_code=10`, `failed_step=close`, `run_result=PASS`, `completed_business_day_count=19`.
- `final_summary.json`: `status=REVIEW_REQUIRED`, `runtime_status=COMPLETED`, `runtime_execution_judgment=PASS`, `final_runtime_judgment=PASS`, `trading_state_judgment=PASS`, `accounting_state_judgment=PASS`, `block_rule=NO_BLOCKING_CLOSE_RULE_TRIGGERED`.
- `run_state.json`: currently records `status=COMPLETED` and all 19 completed business days.

Therefore the run is usable for canonical runtime/accounting capital utilization. The close `REVIEW_REQUIRED` is strategy-shadow/test-validity review, classified as `NON_MUTATING_STRATEGY_SHADOW_REVIEW_NON_BLOCKING`.

## Canonical Authority Resolution

| Metric | Canonical producer | Artifact / field | Date semantics / timing | Duplicate copies | Why authoritative |
| --- | --- | --- | --- | --- | --- |
| Portfolio equity | Runtime-owned current valuation refresh | `daily/<date>/current_valuation_refresh/current_valuation_manifest.json` -> `artifact.candidate_current.total_equity` | End-of-day current state after execution and current valuation refresh for that business date | `final_state_snapshot/persistent_ledger/state.json.total_equity` for final day; summarize output | Runtime-owned fill projection and valuation; `scripts/runtime_test.py` derives final equity from current state |
| Cash | Runtime-owned current valuation refresh | `artifact.candidate_current.cash` | Same as above | Submit guard snapshots use pre-submit current cash for that day | Direct current-state cash |
| Buying power | Runtime-owned current valuation refresh | `artifact.candidate_current.buying_power` | Same as above | Submit guard selected cash/buying power | Direct current-state buying power |
| Gross exposure | Daily evaluation capital contract | `market_value / total_equity` from `candidate_current` | EOD after execution/valuation | Daily evidence derives same value | Long-only current holdings in this run; gross ratio equals invested ratio |
| Net exposure | Daily evaluation capital contract | `market_value / total_equity` from `candidate_current` | EOD after execution/valuation | Daily evidence derives same value | No short exposure observed; net equals gross for current long holdings |
| Current holdings | Runtime-owned current valuation refresh | `artifact.candidate_current.positions` | EOD current holdings only | `final_state_snapshot/persistent_ledger/state.json.positions` | Current positions, not campaign count |
| Current position count | Runtime-owned current valuation refresh | `len(artifact.candidate_current.positions)` | EOD current holdings count | runtime_test `summarize --scope full` reports positions `4` | Prevents campaign/history/nested artifact overcount |
| Position market value | Runtime-owned current valuation refresh | `artifact.candidate_current.market_value` | EOD valuation | `final_state_snapshot` final-day copy | Sum of current position market values |
| Realized PnL | Run-scoped PnL reconciliation | `final_summary.json.pnl_reconciliation.realized` from `daily/*/execution/realized_slices.json` | Run-scoped realized slices across 19 days | `candidate_current.realized_pnl=8500` exists but is legacy | `legacy_current_realized_pnl_field_status=NOT_CANONICAL_NET_REALIZED_PNL_FOR_EVALUATION` |
| Unrealized PnL | Run-scoped PnL reconciliation | `final_summary.json.pnl_reconciliation.unrealized` from final current valuation unrealized | Final day current valuation | `candidate_current.new_unrealized_pnl` | Reconciles equity delta with realized slices |

Source-code authority checks:

- `scripts/runtime_test.py` `_summarize_performance()` uses `current_state.total_equity` or `cash + market_value` and `len(current_state.positions)` for final state.
- `scripts/runtime_test.py` `_run_scoped_pnl_reconciliation()` uses `daily/*/current_valuation_refresh/current_valuation_manifest.json`, `daily/*/execution/realized_slices.json`, and labels `candidate_current.realized_pnl` as non-canonical for evaluation.
- `performance_evaluation/daily_evidence.py` `_build_capital()` derives cash ratio, gross exposure ratio, net exposure ratio, and position count from `candidate_current`.
- `performance_evaluation/capital_trace.py` `_capital_authority()` checks that position sizing capital matches current total equity.

## Canonical Daily Capital Utilization

All rows are end-of-day after execution and current valuation refresh.

| Business date | Portfolio equity | Cash | Invested notional | Invested ratio | Cash ratio | Current positions | Gross exposure | Net exposure |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 2022-08-23 | 995,110 | 685,780 | 309,330 | 31.0850% | 68.9150% | 2 | 31.0850% | 31.0850% |
| 2022-08-24 | 945,950 | 399,780 | 546,170 | 57.7377% | 42.2623% | 3 | 57.7377% | 57.7377% |
| 2022-08-25 | 979,950 | 669,780 | 310,170 | 31.6516% | 68.3484% | 2 | 31.6516% | 31.6516% |
| 2022-08-26 | 970,920 | 621,180 | 349,740 | 36.0215% | 63.9785% | 3 | 36.0215% | 36.0215% |
| 2022-08-29 | 971,670 | 515,580 | 456,090 | 46.9388% | 53.0612% | 4 | 46.9388% | 46.9388% |
| 2022-08-30 | 974,040 | 634,380 | 339,660 | 34.8713% | 65.1287% | 3 | 34.8713% | 34.8713% |
| 2022-08-31 | 973,540 | 604,260 | 369,280 | 37.9317% | 62.0683% | 3 | 37.9317% | 37.9317% |
| 2022-09-01 | 966,930 | 604,260 | 362,670 | 37.5074% | 62.4926% | 3 | 37.5074% | 37.5074% |
| 2022-09-02 | 969,640 | 604,260 | 365,380 | 37.6820% | 62.3180% | 3 | 37.6820% | 37.6820% |
| 2022-09-05 | 971,050 | 329,560 | 641,490 | 66.0615% | 33.9385% | 5 | 66.0615% | 66.0615% |
| 2022-09-06 | 967,470 | 369,460 | 598,010 | 61.8117% | 38.1883% | 5 | 61.8117% | 61.8117% |
| 2022-09-07 | 959,320 | 488,860 | 470,460 | 49.0410% | 50.9590% | 4 | 49.0410% | 49.0410% |
| 2022-09-08 | 972,770 | 500,860 | 471,910 | 48.5120% | 51.4880% | 4 | 48.5120% | 48.5120% |
| 2022-09-09 | 974,690 | 509,860 | 464,830 | 47.6900% | 52.3100% | 4 | 47.6900% | 47.6900% |
| 2022-09-12 | 980,010 | 563,260 | 416,750 | 42.5251% | 57.4749% | 3 | 42.5251% | 42.5251% |
| 2022-09-13 | 981,910 | 579,860 | 402,050 | 40.9457% | 59.0543% | 3 | 40.9457% | 40.9457% |
| 2022-09-14 | 986,000 | 572,480 | 413,520 | 41.9391% | 58.0609% | 3 | 41.9391% | 41.9391% |
| 2022-09-15 | 987,090 | 416,080 | 571,010 | 57.8478% | 42.1522% | 4 | 57.8478% | 57.8478% |
| 2022-09-16 | 970,360 | 424,580 | 545,780 | 56.2451% | 43.7549% | 4 | 56.2451% | 56.2451% |

## Aggregate Metrics

Including `2022-08-23` EOD:

- Invested ratio: average `45.4761%`, median `42.5251%`, min `31.0850%`, max `66.0615%`, final `56.2451%`.
- Cash ratio: average `54.5239%`, median `57.4749%`, min `33.9385%`, max `68.9150%`, final `43.7549%`.
- Current position count: average `3.4211`, median `3`, min `2`, max `5`, final `4`.

Excluding `2022-08-23` EOD:

- Invested ratio: average `46.2756%`, median `44.7319%`, min `31.6516%`, max `66.0615%`, final `56.2451%`.
- Cash ratio: average `53.7244%`, median `55.2681%`, min `33.9385%`, max `68.3484%`, final `43.7549%`.
- Current position count: average `3.5000`, median `3`, min `2`, max `5`, final `4`.

Performance:

- Initial equity: `1,000,000`
- Final equity: `970,360`
- Total PnL: `-29,640`
- Total return: `-2.964%`
- Run-scoped realized PnL: `-46,666.6667`
- Final unrealized PnL: `17,026.6667`
- PnL reconciliation: `PASS`

Consistency with `runtime_test.py summarize`:

- `summarize --scope performance` reports `initial_equity=1000000.0`, `final_equity=970360.0`, `total_return=-29640.0`, `return_rate=-2.964`, and execution notional `BUY=1,289,420 / SELL=714,000`.
- `summarize --scope full` reports the same final equity and return, submitted/executed `BUY=11`, submitted/executed `SELL=13`, and current positions `4`.
- `summarize --scope full` also displays `realized_pnl=8500.0`; this is the legacy current-state field and must not override `pnl_reconciliation.realized=-46666.6667`.

## Initial Day Treatment

`2022-08-23` in the canonical daily table is not a pre-execution bootstrap row. It is the end-of-day current valuation row after that day's execution and valuation refresh. Therefore it is included in the primary 19-day daily-utilization average.

Because some comparisons may want to avoid first-day bootstrap effects, this audit also provides the excluding-first-day aggregate above. No pre-execution `100% cash` row was inferred.

## Compounding Audit

Judgment: `COMPOUNDING_CONFIRMED`

Evidence:

- For every day after the first, prior-day EOD total equity matched the next day's `strategy/position_sizing.json.portfolio_total_equity`.
- On days with submit items, submit guard `selected_capital_value` also matched the prior-day EOD total equity.
- Example `2022-08-24`: prior EOD equity `995,110` -> position sizing capital `995,110` -> `78780` target notional `241,999.81` -> one-lot authority consumed -> PS quantity `100` -> RP BUY quantity `100` -> Submit PASS -> Execution BUY -> same-day current reflected.
- Example `2022-09-14`: prior EOD equity `981,910` -> position sizing capital `981,910` -> `94320` incremental notional `15,510.25` -> one-lot authority consumed -> PS quantity `100` -> RP BUY quantity `100` -> Submit PASS -> Execution BUY -> same-day current reflected.
- Example `2022-09-15`: prior EOD equity `986,000` -> position sizing capital `986,000` -> `94340` target notional `177,480` -> PS quantity `1,100` -> RP BUY quantity `1,100` -> Submit PASS -> Execution BUY -> same-day current reflected.

The compounding authority chain is therefore operating through current equity, not a fixed initial capital base.

## Capital Deployment Funnel

Across 19 business days:

| Stage | Count |
| --- | ---: |
| Opportunity candidates | 950 |
| Buy Quality PASS decisions | 800 |
| PC accepted positive BUY allocation candidates | 13 |
| PS positive BUY quantity | 11 |
| Runtime Planning BUY quantity | 11 |
| Pending approved BUY visible to Submit | 11 |
| Submitted BUY | 11 |
| Executed BUY | 11 |
| Executed BUY reflected in same-day current positions | 11 |
| Pending approved SELL visible to Submit | 13 |
| Submitted SELL | 13 |
| Executed SELL | 13 |

Observed gaps:

| Gap | Count | Classification |
| --- | ---: | --- |
| PC accepted positive but PS zero | 2 | Fail-closed discrete safety/lot feasibility, not plumbing |
| PS positive but RP zero | 0 | No defect observed |
| RP BUY but Pending missing/rejected | 0 | No defect observed |
| Pending approved BUY but Submit missing | 0 | No defect observed |
| Submit BUY but Execution missing | 0 | No defect observed |
| Execution BUY but same-day Current not reflected | 0 | No defect observed |
| Pending approved SELL but Submit missing | 0 | No defect observed |
| Submit SELL but Execution missing | 0 | No defect observed |

The two PC-positive/PS-zero cases are both `78780`:

- `2022-08-23`: one lot notional `287,250`, one lot weight `28.7250%`, safety hard cap `25%`, `one_lot_feasibility_status=FAIL_CLOSED`, blocker `minimum_lot_exceeds_safety_hard_cap`.
- `2022-09-02`: one lot notional `251,250`, one lot weight `25.9843%`, safety hard cap `25%`, `one_lot_feasibility_status=FAIL_CLOSED`, blocker `minimum_lot_exceeds_safety_hard_cap`.

These are legitimate Production safety fail-closed outcomes. They must not be repaired by loosening hard caps, blind carry-forward, or hindsight allocation.

## Residual Cash Root Cause Attribution

Residual cash is real: final cash ratio is `43.7549%`, average cash ratio is `54.5239%`.

Attribution:

- Runtime/plumbing defect: not supported by this run. BUY and SELL submit-to-execution continuity is complete for observable positive items. BUY lineage validation is `PASS`, with `buy_fill_count=11` and `buy_fill_missing_lineage_count=0`.
- Discrete execution / safety feasibility: supported. Two PC-accepted `78780` cases fail closed because one lot exceeds the 25% safety hard cap.
- Strategy/opportunity/policy selection: supported. Only 11 BUY orders are ultimately authorized from 950 opportunity rows and 800 BQ PASS rows. High cash therefore reflects conservative selection/allocation plus discrete feasibility, not a proven runtime loss.
- Unexplained residual: limited to strategy review observability. Close review remains `REVIEW_REQUIRED` due to non-blocking strategy shadow review dates `2022-08-25`, `2022-08-30`, `2022-09-07`, and `2022-09-12`. This does not establish a capital-utilization runtime defect.

Cash being high is not itself a defect. This audit does not impose an 80% or 90% invested target.

## Phase29 Repair Effect

| Repair | Focused status from phase report | Reached this run | Audit classification |
| --- | --- | --- | --- |
| L19 cap-constrained lot floor / residual reallocation | Implemented, fresh Historical required | `phase29_l19_lot_resolution` present in PC/PS evidence | `IMPLEMENTED`, `REACHED_RUNTIME` |
| L21R3 re-entry capacity / prior-exit persistence | Focused regression PASS | Re-entry fields present and remain diagnostic/semantic where applicable | `IMPLEMENTED`, `REACHED_RUNTIME` |
| L21S one-lot capital expression | Focused regression PASS | One-lot expression evidence present, including fail-closed and pass cases | `IMPLEMENTED`, `REACHED_RUNTIME` |
| L21T-B one-lot soft-cap authority integration | Focused regression PASS | One-lot soft-cap authority consumed by Strategy/RP for valid cases | `IMPLEMENTED`, `REACHED_RUNTIME` |
| L21T-C one-lot discrete quantity materialization | Focused regression PASS | `78780` on `2022-08-24` materialized PS/RP quantity `100`; `94320` on `2022-09-14` materialized quantity `100` | `REACHED_RUNTIME` |
| L21T-F pending BUY preservation / BUY+SELL composition | Focused regression PASS | Current run has `BUY=11` pending/submit/execution and `SELL=13` pending/submit/execution; `2022-09-14` has BUY+SELL same-day submit/execution | `REACHED_SUBMIT`, `REACHED_EXECUTION` |
| L21T-H planning/submit feasibility authority integration | Focused regression PASS | Submit guard accepts one-lot authority using `selected_capital_value=current_total_equity`; no positive BUY lost at submit | `REACHED_SUBMIT`, `REACHED_EXECUTION`, `REFLECTED_IN_PORTFOLIO` |

Repair-effect conclusion:

The Phase29 runtime repair stack has reached Submit, Execution, and Current Portfolio reflection for positive BUYs in this run. The remaining high cash is not attributable to a currently proven runtime continuity defect.

## SELL Independence And Review Findings

BUY/SELL independence is preserved:

- BUY decision authority remains Strategy/PC/PS/RP/Pending.
- SELL decision authority remains PM/SELL planning/quantity contract.
- Submit guard handles BUY and SELL item feasibility separately.
- `2022-09-14` demonstrates BUY + SELL same-day execution without BUY suppression or SELL blocking.

The `runtime_test.py summarize --scope full` lifecycle review findings must be evaluated separately from capital utilization:

- `SELL_PLAN_SOURCE_DECISION_NOT_TRACEABLE`: lifecycle/lineage observability issue, not evidence of SELL submit/execution loss in this run.
- `PENDING_EMPTY_OR_EXPLAINED=False`: lifecycle consistency review issue, not evidence that approved BUY pending vanished in this run after L21T-F/H.

These findings justify strategy/lifecycle observability review, not further runtime BUY capital-deployment repair.

## Prohibited Interpretations

This audit does not recommend:

- unconditional BUY pending carry-forward
- SELL-side BUY quantity rewriting
- BUY/SELL decision-authority merge
- submit-side reconstruction of disappeared BUY
- Historical-only rescue
- weakening Production fail-closed behavior
- changing Safety hard caps based on hindsight
- strategy/backtest-hindsight tuning from individual stock outcomes
- treating current position count as campaign count

## Final Decisions

`Phase29 Runtime Repair Continuation Recommended: NO`

Reason: Positive BUY chain continuity is complete from PS/RP through Pending, Submit, Execution, and Current reflection. The observed residual cash is not explained by a proven remaining runtime plumbing defect.

`Phase30 / Next Phase Strategy Capital Deployment Review Recommended: YES`

Reason: The remaining question is strategy capital-deployment behavior under legitimate constraints: why only 11 BUYs were authorized from 950 opportunity rows and 800 BQ PASS decisions, how opportunity quality and allocation semantics should govern deployment, and whether capital should remain intentionally conservative under current policy. That belongs to strategy/policy review, not Phase29 runtime repair.

## Final Judgment

`PHASE29_L21T_I_CANONICAL_CAPITAL_UTILIZATION_FINAL_AUDIT_COMPLETE_RUNTIME_REPAIR_CONTINUATION_NOT_RECOMMENDED_STRATEGY_CAPITAL_DEPLOYMENT_REVIEW_RECOMMENDED`
