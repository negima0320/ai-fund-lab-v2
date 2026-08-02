# Phase24-G Performance Reconciliation, PM Profit Retention, and Re-entry Control Design Contract

## 1. Executive Summary

Phase24-G reconciled the Phase24-F performance attribution result and defined Production-common contracts for PM Profit Retention and same-symbol re-entry control.

No Runtime, Strategy, PM threshold, Exit condition, Ranking, Sizing, Portfolio Construction, or Capital Deployment implementation was changed. No new 20BD, 1Y, or long-running Runtime Test was executed.

The 51,960 yen difference is explained. `final_equity - initial_equity` reconciles exactly, but reported `realized_pnl + unrealized_pnl` uses an open-position cost basis that does not match execution-basis open notional. This is an accounting contract gap in PnL cost-basis authority, not a cash/equity reconciliation failure.

## 2. Primary Judgment

Phase24-G Primary Judgment:

`PHASE24_G_REVIEW_REQUIRED_PERFORMANCE_ACCOUNTING_GAP`

Performance Reconciliation Judgment:

`PERFORMANCE_RECONCILIATION_REVIEW_REQUIRED_ACCOUNTING_CONTRACT_GAP`

Design Freeze Status:

`PM_PROFIT_RETENTION_AND_REENTRY_CONTRACT_FROZEN_AFTER_ACCOUNTING_REPAIR_GATE`

## 3. Scope and Constraints

| Item | Value |
| --- | --- |
| Run ID | `runtime-test-historical-extended-smoke-20260731T033807973583Z` |
| Period | 2022-07-01 to 2022-07-29 |
| Business days | 20 |
| Initial equity | 1,000,000 |
| Final equity | 935,780 |
| Total return | -64,220 |
| BUY executions | 15 |
| SELL executions | 10 |
| Position campaigns | 14 |

This task is design and audit only. Historical result, realized PnL, unrealized PnL, campaign PnL, selected/bought results, cash, portfolio value, future return, MFE, and MAE remain attribution/accounting/operator-review data only. They must not become AI, Opportunity Ranking, Strategy, or PM decision inputs.

## 4. Phase24-F Findings Carried Forward

Phase24-F judgment:

`PHASE24_F_ENTRY_QUALITY_AUDIT_COMPLETE_MULTI_LAYER_PERFORMANCE_GAPS`

Carried-forward classification:

| Layer | Classification |
| --- | --- |
| Position Management | Primary |
| Exit Timing | Primary |
| Repeated re-entry into volatile losers | Primary |
| Opportunity / Entry Selection Quality | Secondary |
| Portfolio Construction | Contributing |
| Capital Deployment | Contributing |
| Position Sizing / single-name concentration | Contributing |
| Observability gaps | Contributing |

Phase24-G does not implement those improvements. It freezes the contract and gates later one-hypothesis/one-change experiments.

## 5. Performance Authority Reconciliation

Canonical total return authority is Current / Persistent Ledger equity:

```text
 final_cash        282,130
+ final_market     653,650
= final_equity     935,780
- initial_equity 1,000,000
= total_return     -64,220
```

Execution cash also reconciles:

```text
BUY notional       -2,271,870
SELL notional      +1,554,000
net cash effect      -717,870
initial cash       1,000,000
final cash           282,130
```

Execution-basis PnL reconciles to total return:

```text
closed realized PnL                 -58,800
final market value                  653,650
open execution-basis notional       659,070
expected open unrealized PnL         -5,420
execution-basis PnL total           -64,220
```

Reported PnL does not reconcile:

```text
reported realized PnL               -58,800
reported current/campaign unrealized -57,380
reported realized + unrealized      -116,180
total return                         -64,220
difference                           -51,960
```

## 6. Explanation of the 51,960 Yen Difference

The 51,960 yen difference is caused by open-position cost basis mismatch:

```text
final ledger open cost basis         711,030
open execution/campaign buy notional 659,070
difference                            51,960
```

By symbol:

| Symbol | Ledger Cost Basis | Open Execution Notional | Difference | Judgment |
| --- | ---: | ---: | ---: | --- |
| `66590` | 232,000 | 166,400 | +65,600 | PnL cost-basis accounting gap |
| `24370` | 123,500 | 137,000 | -13,500 | PnL cost-basis accounting gap |
| `94320` | 186,240 | 186,380 | -140 | PnL cost-basis accounting gap |
| `94340` | 169,290 | 169,290 | 0 | Match |

Fees, taxes, deposits, withdrawals, corporate actions, carry-in positions, and non-campaign cash effects are not evidenced as causal. The reset evidence shows clean initial cash of 1,000,000 and no initial positions.

Judgment: total equity authority is valid, but realized/unrealized/campaign PnL reporting has a cost-basis contract gap. Performance implementation must not proceed until this is reviewed or repaired.

## 7. Performance Authority Ownership

| Responsibility | Canonical Owner | Artifact | Judgment |
| --- | --- | --- | --- |
| Total return | Current / Persistent Ledger equity | `final_state_snapshot/persistent_ledger/state.json` | Reconciled |
| Cash effects | Execution fills | `daily/*/execution/fills.json` | Reconciled |
| Realized PnL | Persistent Ledger realized slices | `persistent_ledger/state.json`, campaigns | Reconciled to closed campaigns |
| Unrealized PnL | Persistent Ledger open valuation | `persistent_ledger/state.json` | Accounting contract gap |
| Campaign PnL | Position campaign materializer | `positions/position_campaigns.json` | Includes same open cost-basis gap |
| Fees / taxes | Execution accounting future extension | `fills.json` | `NOT_AVAILABLE`, not causal |

## 8. PM Canonical Observability Contract

Canonical PM observability should extend the existing PM Decision Trace Contract instead of creating a historical-only artifact.

Required fields include:

`symbol`, `position_campaign_id`, `business_date`, `entry_business_date`, `entry_average_price`, `current_price`, `current_return`, `peak_price_since_entry`, `peak_return_since_entry`, `peak_business_date`, `drawdown_from_peak`, `holding_business_days`, `opportunity_rank_current`, `opportunity_rank_at_entry`, `expected_edge_current`, `expected_edge_at_entry`, `market_regime`, `market_context_confidence`, `position_quantity`, `position_market_value`, `portfolio_weight`, `previous_pm_action`, `current_pm_action`, `pm_reason_codes`, `source_decision_id`, `runtime_planning_item_id`, `pending_item_id`, `order_id`, `execution_id`.

Failure behavior:

| Failure | Behavior |
| --- | --- |
| Entry price missing | `REVIEW_REQUIRED` |
| Current valuation missing | `REVIEW_REQUIRED`; `HALT` if mutation would proceed unsafely |
| Campaign ID missing | `REVIEW_REQUIRED` for attribution |
| Peak state missing | `REVIEW_REQUIRED`; bootstrap only from valid entry/current state |
| Rank missing | `SAFE_DEFAULT` for HOLD/EXIT; `REVIEW_REQUIRED` for ADD/re-entry |
| Market context missing | `SAFE_DEFAULT` defensive posture or `REVIEW_REQUIRED` |
| Business date mismatch | `HALT` |
| Future-dated artifact | `HALT` |
| Stale artifact | `REVIEW_REQUIRED` or `HALT` if mutation would use it |
| Duplicated campaign | `HALT` |
| Position quantity mismatch | `HALT` |

Fail-open is forbidden.

## 9. Profit Retention State Machine

Production-common states:

| State | Semantics | Allowed PM Action |
| --- | --- | --- |
| `PROFIT_RETENTION_INACTIVE` | Position open but retention not armed | HOLD, safety/hard-stop EXIT |
| `PROFIT_RETENTION_ARMED` | Valid favorable excursion has armed retention | HOLD, REDUCE, EXIT |
| `PROFIT_RETENTION_WARNING` | Profit giveback or context deterioration is observed | HOLD, REDUCE |
| `PROFIT_RETENTION_REDUCE` | Partial de-risk is required while trend remains partly alive | REDUCE |
| `PROFIT_RETENTION_EXIT` | Profit retention break or safety/hard-stop condition requires close | EXIT |
| `PROFIT_RETENTION_REVIEW_REQUIRED` | Required evidence missing or conflicting | No fail-open mutation |

The contract uses generalized dimensions only: peak return, drawdown from peak, current return, holding duration, market regime, confidence, rank/edge deterioration, volatility, liquidity, corporate event proximity, position size, portfolio concentration, unrealized gain/loss, hard-stop relationship, minimum holding period, and REDUCE/EXIT boundary.

No Phase24-G threshold is optimized to `66590`, `23880`, `24370`, or the 20BD run.

## 10. Profit Retention Priority and Interaction Rules

Priority:

```text
liquidity safety
corporate event risk
hard stop
profit retention EXIT / REDUCE
market regime deterioration
opportunity rank deterioration
portfolio exposure reduction
ADD
HOLD
```

Rules:

- If hard stop and profit retention are both true, hard stop / safety EXIT has priority; profit retention remains a secondary reason.
- ADD is forbidden by default while profit retention is armed unless ADD evidence, concentration safety, liquidity, and requalification all pass.
- Peak update alone does not force REDUCE.
- Safety EXIT and hard stop override minimum holding period.
- Market regime shock may escalate warning to REDUCE/EXIT with evidence.
- Rank recovery can support HOLD only when drawdown remains within policy and evidence is fresh.

## 11. Re-entry Definition and Classification

Required re-entry classes:

- `SAME_CAMPAIGN_ADD`
- `NEW_CAMPAIGN_REENTRY`
- `SAME_DAY_REENTRY`
- `NEXT_DAY_REENTRY`
- `POST_HARD_STOP_REENTRY`
- `POST_PROFIT_RETENTION_EXIT_REENTRY`
- `POST_REGIME_EXIT_REENTRY`
- `POST_CORPORATE_EVENT_EXIT_REENTRY`
- `POST_SAFETY_EXIT_REENTRY`

Re-entry is not globally forbidden. Momentum Strategy may legitimately re-enter after a symbol requalifies.

## 12. Re-entry Control State Machine

| State | Semantics |
| --- | --- |
| `REENTRY_NOT_APPLICABLE` | No prior closed campaign or action is same-campaign ADD |
| `REENTRY_COOLDOWN_ACTIVE` | Minimum no-immediate-reentry safety boundary active |
| `REENTRY_REQUALIFICATION_REQUIRED` | Safety boundary elapsed but strategy requalification not proven |
| `REENTRY_ELIGIBLE` | Safety and strategy evidence requalify |
| `REENTRY_REVIEW_REQUIRED` | Lineage or exit-history evidence missing/conflicting |
| `REENTRY_BLOCKED_BY_SAFETY` | Safety/corporate/stale/quantity authority blocks |

Required state includes last exit date/reason/price/return, last campaign PnL, recent exit/loss/hard-stop/re-entry counts, cooldown and requalification state, latest rank, latest edge, latest regime, and latest corporate event state.

## 13. Requalification Contract

Requalification must separate:

| Layer | Role |
| --- | --- |
| Safety Layer | Hard no-immediate-reentry boundary, stale/corporate/quantity/safety blocks |
| Strategy Layer | Rank, edge, regime, volatility, liquidity, price structure, concentration requalification |

Phase24-G does not freeze numeric thresholds. It explicitly rejects simplified rules such as unconditional 3-day ban, never-buy-after-loss, one-symbol-once, unconditional reject after loss, or unconditional re-entry on high rank.

## 14. ADD vs Re-entry Boundary

| Case | Classification |
| --- | --- |
| BUY into existing open campaign | `SAME_CAMPAIGN_ADD` |
| BUY after full SELL / closed campaign | `NEW_CAMPAIGN_REENTRY` |
| Partial SELL then BUY while campaign remains open | `SAME_CAMPAIGN_ADD` |
| Submit says NEW but symbol was recently closed | Business re-entry |
| Apparent campaign split | `REENTRY_REVIEW_REQUIRED` until lifecycle reconciles |

Campaign lifecycle ownership belongs to the Position Campaign materializer. Runtime Current / Persistent Ledger remains quantity authority. Portfolio Construction owns re-entry conflict policy. Runtime Pending/Submit owns duplicate-order protection.

## 15. Architecture Ownership Matrix

| Responsibility | Proposed Owner | Artifact |
| --- | --- | --- |
| Peak return | PM Decision Trace using Runtime Current | `position_management_decision_trace.json` |
| Drawdown from peak | PM Decision Trace derived from canonical current/peak return | `position_management_decision_trace.json` |
| Campaign lifecycle | Position Campaign materializer | `positions/position_campaigns.json` |
| Re-entry history | Portfolio Construction conflict policy | Portfolio construction trace / future chain-state extension |
| Exit reason | PM Decision Trace and Sell Pending item | PM trace / pending item |
| Performance accounting | Persistent Ledger / Performance reporting | `persistent_ledger/state.json` |
| Total return | Current / Persistent Ledger | `persistent_ledger/state.json` |
| Realized PnL | Persistent Ledger realized slice accounting | Ledger / campaign realized slices |
| Unrealized PnL | Persistent Ledger open position valuation | `persistent_ledger/state.json` |

No unnecessary new authority envelope is recommended. Existing PM trace, campaign, ledger, and portfolio construction artifacts should be extended where needed.

## 16. One-Hypothesis / One-Change Experiment Contract

Recommended order:

1. Experiment A: PM peak/drawdown observability only
2. Accounting cost-basis repair/review gate
3. Experiment B: Profit Retention only
4. Experiment C: Re-entry Safety Cooldown only
5. Experiment D: Strategy Requalification only
6. Experiment E: Single-name concentration control only

Required metrics:

`total return`, `max drawdown`, `realized pnl`, `unrealized pnl`, `MFE giveback`, `profit retention activation count`, `profit retention exit count`, `hard stop count`, `re-entry count`, `post-loss re-entry count`, `same-symbol campaign count`, `average holding period`, `turnover`, `BUY count`, `SELL count`, `position count`, `cash utilization`, `top-ranked candidate selection rate`.

Results must not be fed back into AI/Strategy/PM learning inputs.

## 17. Observability Gaps

| Gap | Classification | Blocking |
| --- | --- | --- |
| Open cost basis does not reconcile to execution-basis open notional | `ACCOUNTING_CONTRACT_GAP` | Blocks performance implementation gate |
| Stable order/pending/source IDs absent in campaign observability | `OBSERVABILITY_GAP` | Partial |
| PM peak/drawdown incomplete in runtime evidence | `OBSERVABILITY_GAP` | Partial |
| Closed campaign `closed_business_date` incomplete | `OBSERVABILITY_GAP` | Non-blocking for 51,960 |
| Benchmark source missing | `OBSERVABILITY_GAP` | Non-blocking for PM contract |

## 18. Design Freeze Decision

PM Observability, Profit Retention, Re-entry Control, ADD vs Re-entry, and One-Hypothesis/One-Change experiment contracts are frozen for review.

Implementation is blocked until the performance accounting cost-basis gap is reviewed or repaired. This avoids evaluating PM/re-entry improvements against inconsistent unrealized PnL authority.

## 19. Recommended Next Task

`Phase24-H Performance Accounting Cost Basis Authority Repair / Review Gate`

Purpose:

- Reconcile open position cost basis after full close and re-entry.
- Decide whether current unrealized PnL or campaign open PnL requires repair.
- Keep PM/Strategy behavior unchanged.
- After acceptance, run Experiment A as observability-only.

## 20. Validation Performed

Validation performed:

- JSON validity for machine report and all Phase24-G evidence JSON files
- Cross-file reconciliation against `persistent_ledger/state.json`, `fills.json`, and `position_campaigns.json`
- Path existence for required deliverables
- `git diff --check`

Not performed:

- Runtime Test
- Long Historical Runtime
- Strategy/PM/sizing/threshold change

## 21. Files Created or Updated

Created:

- `docs/phase_reports/phase24_g_performance_reconciliation_pm_profit_retention_and_reentry_control_design_contract.md`
- `reports/phase_reports/phase24_g_performance_reconciliation_pm_profit_retention_and_reentry_control_design_contract.json`
- `reports/phase24_g_performance_reconciliation_pm_profit_retention_and_reentry_control_design_contract/performance_reconciliation.json`
- `reports/phase24_g_performance_reconciliation_pm_profit_retention_and_reentry_control_design_contract/performance_authority_matrix.json`
- `reports/phase24_g_performance_reconciliation_pm_profit_retention_and_reentry_control_design_contract/pm_observability_contract.json`
- `reports/phase24_g_performance_reconciliation_pm_profit_retention_and_reentry_control_design_contract/profit_retention_state_machine.json`
- `reports/phase24_g_performance_reconciliation_pm_profit_retention_and_reentry_control_design_contract/reentry_control_state_machine.json`
- `reports/phase24_g_performance_reconciliation_pm_profit_retention_and_reentry_control_design_contract/add_vs_reentry_boundary.json`
- `reports/phase24_g_performance_reconciliation_pm_profit_retention_and_reentry_control_design_contract/experiment_contract.json`
- `reports/phase24_g_performance_reconciliation_pm_profit_retention_and_reentry_control_design_contract/architecture_ownership_matrix.json`
- `reports/phase24_g_performance_reconciliation_pm_profit_retention_and_reentry_control_design_contract/observability_gaps.json`
- `reports/phase24_g_performance_reconciliation_pm_profit_retention_and_reentry_control_design_contract/phase24g_evidence.json`

Updated:

- `docs/01_requirements/phase_roadmap.md`

