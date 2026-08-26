# Phase31-G91 — Profit Burst Participation Loss Root-Cause Audit

## PRIMARY_JUDGMENT

PHASE31_G91_PROFIT_BURST_PARTICIPATION_LOSS_ROOT_CAUSE_PARTIAL_G90_REDEPLOYMENT_DEFERRAL_WITH_SELL_AND_PATH_DEPENDENCE_REPAIR_REQUIRED

## Scope

READ-ONLY audit only.

Reference run:

```text
runtime-test-historical-extended-smoke-20260823T140946562431Z
```

Post-G90 run:

```text
runtime-test-historical-extended-smoke-20260824T055234719725Z
```

Audited window:

```text
2023-03-20 through 2023-04-06
```

No code, config, threshold, weight, run state, fresh-run, resume, replay, or Historical execution was changed or executed for G91. Historical performance was used only to identify the symptom window and missing participation inventory, not to tune or judge production parameters.

## Executive Conclusion

The post-G90 run loses Profit Burst participation beginning materially on `2023-03-23`.

The first divergence is not a Market Quality hard BUY gate, Risk Pacing zero-budget event, Position Sizing disconnect, or Runtime priority redecision. It is a combined exposure-loss and failed-redeployment boundary:

```text
PM SELL / EXIT liquidation
plus
PC/G90 CASH_PREFERRED redeployment deferral
plus
path-dependent missing winner inventory
```

Through `2023-03-22`, the two runs remain close:

```text
2023-03-22 pre-G81 return  = +43.60%
2023-03-22 post-G90 return = +42.14%
```

On `2023-03-23`, the post-G90 run sells four positions, buys only one replacement security, and drops exposure from `74.85%` to `43.69%`. The reference run remains at `77.43%` exposure. From that point onward, post-G90 repeatedly has positive capital budget but defers replacement `NEW_BUY` candidates to Cash, preventing exposure rebuild.

By `2023-04-06`, the post-G90 run reaches:

```text
equity = 1,444,780
cash = 1,444,780
market_value = 0
positions = 0
exposure = 0.00%
```

while the reference run holds three positions:

```text
59350
67310
97340
```

This must not be classified as simply a `BEAR` or Market Quality state result. On `2023-04-06`, the post-G90 run still has positive capital budget (`0.740`) and six same-day security candidates, but all are deferred and no security allocation remains.

## Required Judgments

```text
PROFIT_BURST_PARTICIPATION_LOSS = YES
FIRST_PROFIT_BURST_DIVERGENCE_DATE = 2023-03-23
FIRST_PROFIT_BURST_DIVERGENCE_BOUNDARY = COMBINED_PM_SELL_EXIT_AND_PC_G90_CASH_PREFERRED_REDEPLOYMENT_DEFERRAL
G90_DIRECT_CAUSE = PARTIAL
G90_PROFIT_BURST_OVERDEFENSE = PARTIAL
SELL_AUTHORITY_DIRECT_CAUSE = PARTIAL
MISSED_NEW_BUY_CAUSE = YES
MISSED_ADD_CAUSE = NO
OPPORTUNITY_SET_CONTEXT_CAUSE = PARTIAL
MARKET_QUALITY_CAUSE = NO
RISK_PACING_CAUSE = NO
CAPITAL_BUDGET_CAUSE = NO
PATH_DEPENDENCE_MATERIAL = YES
EXISTING_EVIDENCE_SUFFICIENT_FOR_REPAIR = PARTIAL
REPAIR_REQUIRED = YES
```

## Daily Capital Participation Diff

Current valuation evidence was taken from each run's `current_valuation_refresh/current_valuation_manifest.json` candidate current artifact. Portfolio Construction allocation and deferral evidence was taken from the same-date PC artifacts. Submit/fill evidence was used only to characterize actual materialization.

| Date | Pre Exposure | Post Exposure | Pre Positions | Post Positions | Post Allocations | Post Deferrals | Post Cash Auth | Post BUY | Post SELL |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 2023-03-20 | 71.47% | 70.20% | 10 | 9 | 2 / 0.184 | 1 / 0.031 | 0.083 | 1 | 1 |
| 2023-03-22 | 71.87% | 74.85% | 10 | 10 | 4 / 0.366 | 2 / 0.107 | 0.161 | 2 | 1 |
| 2023-03-23 | 77.43% | 43.69% | 10 | 7 | 3 / 0.442 | 3 / 0.159 | 0.253 | 1 | 4 |
| 2023-03-24 | 77.42% | 62.27% | 10 | 10 | 3 / 0.193 | 2 / 0.319 | 0.388 | 3 | 0 |
| 2023-03-27 | 56.58% | 50.47% | 8 | 8 | 1 / 0.118 | 1 / 0.083 | 0.549 | 1 | 3 |
| 2023-03-28 | 83.00% | 46.34% | 10 | 6 | 2 / 0.227 | 2 / 0.164 | 0.530 | 1 | 3 |
| 2023-03-29 | 77.39% | 36.67% | 8 | 5 | 2 / 0.075 | 4 / 0.432 | 0.595 | 1 | 2 |
| 2023-03-30 | 72.80% | 52.45% | 6 | 5 | 2 / 0.274 | 4 / 0.430 | 0.473 | 1 | 1 |
| 2023-03-31 | 78.02% | 48.14% | 8 | 4 | 2 / 0.228 | 4 / 0.437 | 0.463 | 1 | 2 |
| 2023-04-03 | 76.53% | 48.13% | 7 | 4 | 1 / 0.038 | 3 / 0.358 | 0.534 | 0 | 0 |
| 2023-04-04 | 91.00% | 44.08% | 7 | 3 | 1 / 0.038 | 3 / 0.374 | 0.567 | 0 | 1 |
| 2023-04-05 | 72.34% | 21.78% | 5 | 1 | 0 / 0.000 | 4 / 0.340 | 0.522 | 0 | 2 |
| 2023-04-06 | 56.02% | 0.00% | 3 | 0 | 0 / 0.000 | 6 / 0.573 | 0.740 | 0 | 1 |

The exposure collapse is therefore a cumulative participation failure, not a one-day valuation anomaly or one-day Market Quality label.

## First Material Divergence

`2023-03-23` is the first material divergence date.

Post-G90 state on `2023-03-22`:

```text
equity = 1,421,380
exposure = 74.85%
positions = 10
BUY fills = 2
SELL fills = 1
```

Post-G90 state on `2023-03-23`:

```text
equity = 1,438,310
exposure = 43.69%
positions = 7
BUY fills = 1
SELL fills = 4
```

Post-G90 `2023-03-23` fills:

```text
BUY  52400 100
SELL 51370 100
SELL 57810 100
SELL 64240 100
SELL 58200 100
```

Post-G90 `2023-03-23` PC evidence:

```text
Market Quality = CONFLICTED_MARKET_STRUCTURE
Risk Pacing = CAUTIOUS_DEPLOYMENT
available incremental budget = 0.695
security_allocations = 3
security_allocation_weight = 0.442
cash_preferred_security_deferrals = 3
deferred_requested_weight = 0.159
authorized_cash_allocation = 0.253
```

Deferred post-G90 symbols:

```text
37870
39040
23450
```

This is the first boundary where liquidation and insufficient replacement combine into a durable participation gap.

## G90 Deferral Inventory

Across the audited window, post-G90 evidence contains:

```text
CASH_PREFERRED_DEFER rows = 39
deferred requested weight = 3.809
actions = NEW_BUY 39
quality_class = COMPARABLE_MARGINAL 39
row_evidence_complete = 39 / 39
frontier = false 37, true 2
```

Dominant reason-code families:

```text
CASH_PREFERRED_SAME_DAY_RELATIVE_SUPPORT_INSUFFICIENT
CASH_PREFERRED_AGGREGATE_PRESSURE_AFTER_WEAK_TAIL_BOUNDARY
CASH_PREFERRED_RELATIVE_STRENGTH_WEAK_DEFERRAL
CASH_PREFERRED_CLASS_FRONTIER_NOT_CREDIBLE_DEFERRAL
```

On `2023-04-05` and `2023-04-06`, the frontier row itself is weak, so the entire same-class set collapses to Cash:

```text
2023-04-05 allocations = 0, deferrals = 4, authorized_cash_allocation = 0.522
2023-04-06 allocations = 0, deferrals = 6, authorized_cash_allocation = 0.740
```

This supports `G90_DIRECT_CAUSE = PARTIAL`: G90 is not the sole cause of missing Profit Burst participation, but it is the direct same-date boundary that prevents redeployment after positions are sold.

It also supports `G90_PROFIT_BURST_OVERDEFENSE = PARTIAL`: many deferred rows do have weak or low-confidence evidence and may be legitimate optional-Cash decisions, but the positive-budget all-security-zero behavior on `2023-04-05` and `2023-04-06` shows that the resolver can over-defend in a burst/recovery participation window.

## Missing Winner Inventory

The reference run's `2023-04-06` holdings were:

```text
59350
67310
97340
```

These symbols were selected because they explain the participation inventory difference. Their later return was not used as a production decision label.

### 59350

Reference run:

```text
held 100 shares throughout the G91 window
2023-04-06 market value = 549,000
```

Post-G90 run:

```text
BUY 100 on 2023-03-06
SELL 100 on 2023-03-13
PM reason = hard_stop_current_return
absent throughout 2023-03-20 through 2023-04-06
```

Classification:

```text
59350_MISSING_CAUSE = PATH_DEPENDENT_PRIOR_SELL_WINNER_RETENTION_LOSS
G90_SAME_DATE_CAUSE = NO
```

This is a material path-dependence component. G90 did not directly defer `59350` during the audited window, but the post-G90 portfolio entered the window without this reference holding.

### 97340

Reference run:

```text
allocated 2023-03-27 and 2023-03-28
BUY 100 on 2023-03-28
held through 2023-04-06
```

Post-G90 run:

```text
CASH_PREFERRED_DEFER on 2023-03-24
CASH_PREFERRED_DEFER on 2023-03-27
CASH_PREFERRED_DEFER on 2023-03-28
CASH_PREFERRED_DEFER on 2023-03-29
no BUY fill
no position
```

Classification:

```text
97340_MISSING_CAUSE = PC_G90_CASH_PREFERRED_REDEPLOYMENT_DEFERRAL
G90_SAME_DATE_CAUSE = YES
```

This is the clearest direct G90 participation-loss example in the Profit Burst lead-in.

### 67310

Reference run:

```text
BUY 100 on 2023-04-04
held through 2023-04-06
```

Post-G90 run:

```text
no allocation / deferral / fill / holding found in the audited event search
```

Classification:

```text
67310_MISSING_CAUSE = OPPORTUNITY_SET_OR_PATH_DEPENDENT_PRODUCER_DIFFERENCE
G90_SAME_DATE_CAUSE = UNPROVEN
```

This is not direct evidence of G90 deferral for `67310`. It indicates a path-dependent opportunity-set difference or upstream candidate/PC producer difference that should not be repaired by assuming a fixed symbol outcome.

## SELL / Winner Retention

SELL authority is a partial direct cause of participation loss because post-G90 removes exposure faster than the reference run and replacement BUYs do not compensate.

Representative post-G90 SELL events:

```text
2023-03-23 SELL 51370, 57810, 64240, 58200
2023-03-28 SELL 48920, 39040, 72710
2023-03-29 SELL 43340, 67750
2023-03-31 SELL 52470, 70420
2023-04-05 SELL 54010, 51360
2023-04-06 SELL 68980
```

Observed authority pattern includes PM-owned liquidation reasons such as:

```text
full_liquidation_authority = PM_EXIT
hard_stop_current_return
profit_retention_break
peak_drawdown_warning
risk_increased_but_trend_not_broken
trend_and_opportunity_broken
```

G91 does not judge these SELL decisions as wrong from future return. The evidence only supports that SELL liquidation is a direct exposure-loss boundary and that post-G90 redeployment did not rebuild participation afterward.

## Market Quality / Risk Pacing / Capital Budget

Market Quality and Risk Pacing are not the direct cause.

The post-G90 run remains in cautious or recovery-confirmation states, but the capital budget is not zero:

```text
2023-03-23 capital budget = 0.695
2023-03-27 capital budget = 0.667
2023-03-28 capital budget = 0.757
2023-03-29 capital budget = 0.671
2023-03-31 capital budget = 0.692
2023-04-03 capital budget = 0.571
2023-04-04 capital budget = 0.604
2023-04-05 capital budget = 0.522
2023-04-06 capital budget = 0.740
```

The causal boundary is therefore downstream of Portfolio Policy budget authorization:

```text
Market Quality / Risk Pacing
-> positive capital budget
-> PC/G90 security/Cash partition
-> security allocations reduced or zero
```

## ADD

The audited G90 deferrals are all `NEW_BUY`, not `BUY_ADD`.

No direct ADD connectivity failure was identified in the Profit Burst divergence boundary. ADD underuse remains an important Phase31 theme from G71-G74, but in G91 the direct missed participation path is:

```text
missing / sold reference holdings
plus
missed NEW_BUY replacement
```

not a same-window Runtime BUY_ADD materialization defect.

## Root-Cause Decomposition

Top causal components:

1. `PC/G90 CASH_PREFERRED redeployment deferral`

   Post-G90 repeatedly has positive capital budget but defers `NEW_BUY` candidates to Cash, including direct missing-reference case `97340`. This prevents replacement after SELL liquidation.

2. `SELL / EXIT exposure loss`

   Post-G90 sells materially more holdings beginning `2023-03-23` and continues liquidating through `2023-04-06`. G91 does not classify SELL as incorrect, but it is a direct exposure-loss boundary.

3. `Path-dependent missing winner inventory`

   `59350` was sold before the audited window in the post-G90 run and held throughout the window in the reference run. This makes the Profit Burst gap path-dependent and not fully attributable to G90 same-date deferrals.

4. `Opportunity-set / producer context difference`

   `67310` appears as reference inventory but does not appear in post-G90 allocation or deferral evidence in the audited search. This is not enough to call G90 the direct cause for that symbol.

5. `Market Quality / Risk Pacing as context, not hard gate`

   Cautious states shape capital pacing context, but positive budget remains available. The hard participation loss occurs in PC final security/Cash resolution.

## Repair Boundary

The evidence is sufficient to say a repair is required, but only partially sufficient to define the exact safe repair in this task.

Do not revert G90 wholesale. G80/G81/G86 weak-tail Cash preference remains valid: weak opportunity tails should not consume capital merely because Cash is residual.

The next repair/audit should focus on a minimal boundary:

```text
PC/G90 cash_preferred_participation_deferral_resolution.v1
```

and specifically separate:

```text
weak-tail optional Cash deferral
from
positive-budget Profit Burst / recovery redeployment participation
from
path-dependent SELL / winner-retention inventory loss
```

The repair must not use future returns, symbol blacklists, fixed exposure targets, fixed position counts, or performance-tuned thresholds.

## Required Output

```text
PROFIT_BURST_PARTICIPATION_LOSS = YES
FIRST_PROFIT_BURST_DIVERGENCE_DATE = 2023-03-23
FIRST_PROFIT_BURST_DIVERGENCE_BOUNDARY = COMBINED_PM_SELL_EXIT_AND_PC_G90_CASH_PREFERRED_REDEPLOYMENT_DEFERRAL
G90_DIRECT_CAUSE = PARTIAL
G90_PROFIT_BURST_OVERDEFENSE = PARTIAL
SELL_AUTHORITY_DIRECT_CAUSE = PARTIAL
MISSED_NEW_BUY_CAUSE = YES
MISSED_ADD_CAUSE = NO
OPPORTUNITY_SET_CONTEXT_CAUSE = PARTIAL
MARKET_QUALITY_CAUSE = NO
RISK_PACING_CAUSE = NO
CAPITAL_BUDGET_CAUSE = NO
PATH_DEPENDENCE_MATERIAL = YES
EXISTING_EVIDENCE_SUFFICIENT_FOR_REPAIR = PARTIAL
REPAIR_REQUIRED = YES
```

## Integrity

```text
CODE_CHANGED = NO
CONFIG_CHANGED = NO
THRESHOLD_WEIGHT_TUNING = NO
RUN_MODIFIED = NO
FRESH_RUN_EXECUTED = NO
RESUME_EXECUTED = NO
REPLAY_EXECUTED = NO
LONG_HISTORICAL_EXECUTED = NO
FUTURE_INPUT_COUNT = 0
HISTORICAL_OUTCOME_PARAMETER_SELECTION_COUNT = 0
G90_REVERT_RECOMMENDED = NO
```

## Highest-Value Next Action

Perform a focused repair/design task for the PC-owned G90 resolver boundary that preserves weak-tail Cash deferral while preventing positive-budget recovery/profit-burst redeployment from collapsing to all Cash solely because every available `CASH_PREFERRED` row is `COMPARABLE_MARGINAL`.
