# Phase29-L21J - 23880 Immediate Re-entry Authority / Regression Audit

## 1. Executive Summary

Primary Judgment:

```text
PHASE29_L21J_REENTRY_AUTHORITY_MATERIALIZED_BUT_NOT_CONSUMED_GAP_CONFIRMED
```

This read-only audit confirms that `23880` re-entered after a loss-making full EXIT, but not on the immediate next business day. The first campaign fully exited on `2022-08-30`; `2022-08-31` evaluated `23880` but produced zero target weight and no BUY fill; `2022-09-01` produced a new `BUY_NEW` fill of `1300 @ 136`.

The previous EXIT was materialized in `positions/position_campaigns.json` before or at the `2022-09-01` daily evidence boundary, but Portfolio Construction consumed the `23880` row with `prior_exit_business_date=""`, `business_days_since_exit=null`, `semantic_buy_type=BUY_NEW`, and re-entry checks `NOT_APPLICABLE`. Therefore the L16 re-entry guard exists only for rows where prior EXIT state is already injected; this run did not inject campaign-derived prior EXIT state into the BUY_NEW candidate/PC row.

Required classifications:

| Item | Judgment |
|---|---|
| Re-entry occurred | YES |
| Immediate next-business-day re-entry | NO |
| Previous EXIT awareness | AVAILABLE_BUT_NOT_CONSUMED |
| Re-entry qualification evidence | NOT_EVALUATED |
| Existing re-entry contract | PARTIAL |
| Regression confirmed | NOT_PROVEN |
| L21I causal | EXPOSURE_ONLY |

## 2. 23880 Campaign Timeline

Target run:

```text
reports/runtime_tests/runs/runtime-test-historical-smoke-20260811T152905733571Z
```

Observed campaign and execution timeline:

| Date | Evidence | Action | Quantity | Price | Campaign result |
|---|---|---:|---:|---:|---|
| 2022-08-23 | `execution/fills.json` | BUY | 1200 | 148 | campaign `...0001` OPEN |
| 2022-08-29 | `execution/fills.json` / `realized_slices.json` | SELL / REDUCE | 300 | 133 | campaign `...0001` OPEN, realized PnL `-4500` |
| 2022-08-30 | `execution/fills.json` / `realized_slices.json` | SELL / EXIT | 900 | 132 | campaign `...0001` CLOSED, realized PnL `-18900` |
| 2022-08-31 | Strategy artifacts | no BUY fill | 0 | n/a | closed prior campaign visible |
| 2022-09-01 | `execution/fills.json` | BUY_NEW | 1300 | 136 | campaign `...0002` OPEN |
| 2022-09-06 | `execution/fills.json` / `realized_slices.json` | SELL / REDUCE | 300 | 133 | campaign `...0002` OPEN, realized PnL `-900` |
| 2022-09-07 | `execution/fills.json` / `realized_slices.json` | SELL / EXIT | 1000 | 129 | campaign `...0002` CLOSED, realized PnL `-7900` |

`2022-08-31` exists as a daily run directory, so the `2022-09-01` BUY_NEW is not the immediate next-business-day re-entry after the `2022-08-30` EXIT. It is still a short-horizon same-symbol re-entry after one intervening business day.

## 3. First EXIT Root Cause

The first EXIT was PM-authorized, not a submit or execution accident.

`2022-08-30/position_management/pm_decisions.json` for `23880` records:

```text
decision_type = EXIT
decision_status = SELL_FULL_POSITION
dominant_cause = EXIT_BY_HARD_STOP
secondary_causes = [EXIT_BY_TREND_AND_EDGE_BREAK]
reason_codes = [hard_stop_current_return, trend_and_opportunity_broken]
quantity_requested = 900
current_price = 133
average_cost = 148
unrealized_pnl = -13500
```

Execution then filled `900 SELL @ 132`, closing the first campaign. The realized slice for the final leg was `gross_realized_pnl = -14400`, and the campaign-level realized PnL became `-18900`.

## 4. 9/1 BUY_NEW Decision Trace

On `2022-09-01`, `23880` passed the normal BUY_NEW path:

| Stage | Evidence |
|---|---|
| Opportunity | rank `5`, `runtime_opportunity_score = 0.00797852`, no `no_buy_reason` |
| Buy Quality | `quality_status=PASS`, `quality_action=FULL_ALLOCATION_ELIGIBLE`, `quality_score=0.773148` |
| Portfolio Construction | `membership_intent=ADD_CANDIDATE`, `target_membership=true`, `target_weight=0.18` |
| Position Sizing | `current_quantity=0`, `quantity_delta_candidate=1300` |
| Runtime Planning | `planning_intent=BUY_NEW`, `planned_quantity=1300` |
| Execution | `BUY 1300 @ 136` |

The decisive PC/PS/RP chain was therefore intact. The issue is not a lost BUY_NEW after positive sizing; the issue is that this BUY_NEW was not classified as semantic REENTRY before allocation.

## 5. Previous EXIT Awareness

Judgment:

```text
AVAILABLE_BUT_NOT_CONSUMED
```

`2022-09-01/positions/position_campaigns.json` contains the closed first `23880` campaign:

```text
position_campaign_id = pc-e08d7089ada8550f-23880-0001
campaign_status = CLOSED
opened_business_date = 2022-08-23
current_quantity = 0
realized_pnl = -18900
events include 2022-08-30 SELL 900 @ 132
```

The same file also contains the newly opened `2022-09-01` campaign. Despite that materialized campaign evidence, `2022-09-01/strategy/portfolio_construction.json` for the BUY_NEW row records:

```text
prior_exit_business_date = ""
business_days_since_exit = null
semantic_buy_type = BUY_NEW
reentry_cooldown_status = NOT_APPLICABLE
reentry_recovery_status = NOT_APPLICABLE
reentry_recovery_reason = not_reentry
```

So previous EXIT state existed in run artifacts, but it was not consumed by the Strategy BUY_NEW row.

## 6. Re-entry Qualification Evidence

Judgment:

```text
NOT_EVALUATED
```

PIT evidence available on `2022-09-01` was mixed:

| Dimension | 2022-09-01 evidence |
|---|---|
| Rank | `5`, within L16 recovery rank threshold `<=10` |
| Runtime opportunity score | `0.00797852`, below L16 re-entry recovery hurdle `>=0.10` |
| Buy Quality action | `FULL_ALLOCATION_ELIGIBLE`, allowed by L16 recovery contract |
| Technical trend | `trend_close_over_ma_20d = 0.9709452004`, below `1.0` |
| 20d momentum | `price_momentum_return_20d = 0.2222222222`, non-negative |
| Corporate action status in PC row | `UNKNOWN` |
| Liquidity/capacity fields in re-entry authority | not consumed as REENTRY |

Because the row was never classified as `REENTRY`, these fields were not evaluated under the re-entry cooldown/recovery contract. If prior EXIT state had been injected, the existing L16 recovery hurdle would not have been cleanly satisfied by the observed `reentry_expected_edge = 0.00797852` and `reentry_corporate_action_status = UNKNOWN`; however, this audit does not convert that counterfactual into a runtime outcome.

## 7. Existing Re-entry Contract Audit

Judgment:

```text
PARTIAL
```

The existing code has an implemented PC-side guard when prior EXIT state is already present in the row:

- [portfolio_construction.py](/Users/negishi/work/ai-fund-lab-v2/src/ai_fund_lab_v2/strategy/portfolio_construction.py:1033) blocks `BUY_NEW` rows classified as `REENTRY` when cooldown or recovery does not pass.
- [portfolio_construction.py](/Users/negishi/work/ai-fund-lab-v2/src/ai_fund_lab_v2/strategy/portfolio_construction.py:1145) classifies semantic re-entry from a non-current-position BUY_NEW row plus prior EXIT date.
- [portfolio_construction.py](/Users/negishi/work/ai-fund-lab-v2/src/ai_fund_lab_v2/strategy/portfolio_construction.py:1289) only reads `prior_exit_business_date`, `last_exit_business_date`, or `previous_exit_business_date` from the row itself.
- [test_phase22_e_portfolio_construction.py](/Users/negishi/work/ai-fund-lab-v2/tests/strategy/test_phase22_e_portfolio_construction.py:1944) covers cooldown and recovery when test opportunity rows explicitly provide `prior_exit_business_date`.

Phase29-L16 documents the same contract: semantic REENTRY requires current quantity zero/absent plus explicit prior same-symbol EXIT business date already present in Strategy input. The missing piece in this run is not the PC predicate; it is campaign-history-to-BUY_NEW-input materialization.

## 8. Phase27/28/29 Regression Analysis

Regression confirmed:

```text
NOT_PROVEN
```

Phase28-D20 had already found re-entry loss concentration and stated that the BUY_NEW path did not consume previous campaign close date, exit reason, recent-loss state, or cooldown/state-change evidence. Phase28-D21 then designed campaign-aware state-change gated re-entry eligibility. Phase29-L16 implemented a narrower semantic REENTRY guard, but only for explicit prior EXIT fields already present in Strategy input.

The `23880` case is consistent with that known architecture gap: prior EXIT exists in campaign artifacts, while BUY_NEW PC input has `prior_exit_business_date=""`. The audit does not prove this gap was newly introduced in Phase27/28/29. It shows a current-run manifestation of a previously identified and only partially repaired contract.

## 9. L21I Causality

Judgment:

```text
EXPOSURE_ONLY
```

L21I changed Opportunity / Buy Quality score semantics so uncalibrated relative scores are not treated as calibrated expected-return sign gates. It did not add forced BUY_NEW, change re-entry authority, or wire campaign history into PC rows.

For `23880` on `2022-09-01`, the score was already positive:

```text
runtime_opportunity_score = 0.00797852
quality_reason_codes include uncalibrated_relative_score_eligible
quality_action = FULL_ALLOCATION_ELIGIBLE
```

Therefore L21I is not the direct cause of the missing previous-EXIT consumption. At most, L21I increases exposure to candidate rows passing Buy Quality under corrected score semantics, which can reveal the pre-existing re-entry authority gap.

## 10. Final Judgment

Final classification:

```text
PHASE29_L21J_REENTRY_AUTHORITY_MATERIALIZED_BUT_NOT_CONSUMED_GAP_CONFIRMED
```

`23880` did re-enter after the `2022-08-30` loss EXIT. It did not re-enter on the immediate next business day (`2022-08-31`), but it did re-enter on `2022-09-01`. The previous EXIT campaign was materialized in run evidence, yet Portfolio Construction treated the row as ordinary `BUY_NEW` because `prior_exit_business_date` was empty. As a result, cooldown and recovery were never evaluated.

This is a Strategy authority integration gap, not an execution lifecycle defect and not a post-hoc PnL conclusion. The later `2022-09-07` loss is excluded from judging whether the `2022-09-01` decision was qualified.

## 11. Recommended Next Step

Recommended next task:

```text
Phase29-L21K - Campaign-Derived Prior EXIT State Materialization for BUY_NEW Semantic REENTRY
```

Scope should remain narrow:

- read prior same-symbol closed campaign state before the current decision date;
- materialize `prior_exit_business_date` and prior EXIT reason context into the Strategy BUY_NEW row or a dedicated PC input authority;
- fail closed or review when campaign context is expected but missing;
- preserve BUY_ADD, REDUCE, EXIT, submit, execution, and ledger semantics;
- avoid fixed cooldown-only logic and keep D21 state-change evidence separate from future PnL.
