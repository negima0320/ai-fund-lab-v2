# Phase31-F1 — PM-Owned Unrepresentable REDUCE -> EXIT Escalation Design

Status: COMPLETE
Task type: DESIGN + PIT EVIDENCE AUDIT ONLY

## PRIMARY_JUDGMENT

```text
PHASE31_F1_ALTERNATIVE_G_REQUIRES_REFINEMENT_PM_OWNED_PIT_ESCALATION_CONTRACT_DEFINED
```

F1 re-read the C0 Alternative G design and audited the current F0 run evidence. The correct next step is not mutating implementation. Alternative G remains the right architecture family, but it requires refinement before mutation because the current run confirms three important limits:

- current-run Alternative G shadow artifacts are not materialized;
- all current REDUCE rows have supportive `continuation_quality_status = PASS` and `downside_risk_status = PASS`, so deterioration sufficiency is not yet resolved;
- minimum-notional zero REDUCE rows are adjacent to, but not identical with, one-lot discrete-lot unrepresentability.

The F1 contract is therefore: PM owns escalation, PC/PS only materialize quantity, Runtime never invents EXIT, and `REDUCE_UNREPRESENTABLE` alone never becomes EXIT.

## Evidence Scope

```text
TARGET_RUN_OR_ARTIFACT = reports/runtime_tests/runs/runtime-test-historical-extended-smoke-20260820T120909096218Z
TARGET_WINDOW = 2022-08-10 through 2022-10-12
SOURCE_REPORTS_READ = C0A, C0B, C0C, C0D, C0E, F0
FRESH_RUN_EXECUTED = NO
```

Existing C0 semantics still valid:

- Alternative G Hybrid remains preferred over blind REDUCE -> EXIT.
- PM owns final HOLD / ADD / REDUCE / EXIT semantics.
- PC/PS/Sell Planning expose representability and materialize quantity only.
- Runtime Planning must not convert REDUCE into EXIT.
- Persistence is repeated fresh PM evidence, not hidden reduce debt.
- Recovery evidence must reset, decay, or block escalation pressure.
- Parameters remain unresolved unless canonical semantics already define them.

F0 revisions:

- current window: `PM_REDUCE_COUNT = 154`, `ZERO_REDUCE_QUANTITY_COUNT = 154`;
- discrete-lot and minimum-notional must be separated;
- current SELL/PM does not consume canonical Market Context as authority;
- current-run shadow materialization is required before any mutation review.

## Ownership

```text
ESCALATION_OWNER = PM
```

PM owns:

- deterioration state;
- recovery state;
- persistence interpretation;
- final REDUCE versus EXIT decision.

PC/PS own:

- target quantity materialization;
- tradable-unit evidence;
- raw / rounded / final REDUCE quantity;
- representability reason.

Runtime owns:

- faithful mapping of upstream Strategy decisions;
- no-order preservation;
- no invented escalation.

## Eligible Scope

```text
DISCRETE_LOT_SCOPE = PM action REDUCE + reduce_final_sell_quantity = 0 + reduce_execution_semantic = REDUCE_UNEXECUTABLE_DUE_TO_DISCRETE_LOT + open position + PIT deterioration evidence
MINIMUM_NOTIONAL_SCOPE = SEPARATE_ADJACENT_SCOPE_REQUIRING_NOTIONAL_FEASIBILITY_REVIEW
```

Discrete-lot unrepresentability is the core Alternative G scope. It includes one-lot positions where partial REDUCE is impossible by definition.

Minimum-notional unrepresentability remains a zero-quantity REDUCE problem but should not be merged blindly. In the current run it appears in 15 rows:

| Family | Count | Notes |
|---|---:|---|
| DISCRETE_LOT | 139 | 131 one-lot cases; primary F1 scope |
| MINIMUM_NOTIONAL | 15 | rounded sell quantity can be positive, but notional feasibility sets final sell quantity to zero |

Minimum-notional cases may need either the same PM-owned escalation contract or a separate materiality/notional feasibility treatment. F1 does not authorize either mutation.

## PIT State Model

The proposed state model uses current Production-visible PIT fields only.

| State | Current field support |
|---|---|
| HEALTHY / RECOVERING | PM action `HOLD` or `ADD`; PM reasons `structured_hold_worthiness_pass`, `trend_continuation`, `downside_risk_contained`, `positive_expected_edge`; SI `continuation_quality_status = PASS`; SI `downside_risk_status = PASS`; SI ADD/HOLD evidence `status = PASS` |
| WEAKENING_BUT_INTACT | PM action `REDUCE`; PM reason `risk_increased_but_trend_not_broken`; SI connected; SI continuation/downside still PASS |
| PERSISTENT_DETERIORATION | repeated same-campaign fresh PM `REDUCE` rows that remain unrepresentable, no intervening recovery reset, and current PIT sell-side evidence still weakens; final sufficiency is `PARAMETER_UNRESOLVED` |
| BREAKDOWN / EXIT_WORTHY | PM action `EXIT`; PM reasons `trend_and_opportunity_broken`, `weak_hold_score`, `profit_retention_break`, `hard_stop_current_return`; this can seed immediate-branch semantics but does not allow Runtime conversion |

```text
PIT_DETERIORATION_FIELDS = PM action; PM reason_codes; PM intensity; PM confidence; strategy_intelligence_continuation_quality_status; strategy_intelligence_downside_risk_status; strategy_intelligence_current_campaign_relative_return; strategy_intelligence_observed_campaign_mfe; strategy_intelligence_observed_giveback; strategy_intelligence_profit_protection_status; PS reduce_execution_semantic; PS current_quantity; PS trading_unit; PS target_reduce_ratio; PS raw_reduce_quantity; PS rounded_reduce_quantity; PS reduce_final_sell_quantity; campaign-scoped prior PM actions
```

Market Context is intentionally excluded from the F1 contract because F0 found no SELL-authority consumption.

## Persistence

```text
PERSISTENCE_DEFINITION = campaign-scoped repeated fresh PM REDUCE decisions where each current decision remains unrepresentable, current PIT deterioration evidence is still present, no recovery reset/interruption has occurred, no hidden reduce debt is accumulated, and final escalation is blocked unless deterioration sufficiency is resolved by canonical fields or later validation
```

Persistence is not merely `REDUCE count >= N`. Count is diagnostic evidence. Production escalation requires:

- same campaign identity;
- fresh PM reevaluation on each business date;
- same-day representability failure;
- no intervening HOLD/ADD with recovery evidence;
- current PIT deterioration still present;
- representation error still material;
- no future price / outcome input.

Unresolved persistence parameters:

```text
PARAMETER_UNRESOLVED = persistence minimum; recent-window length; deterioration sufficiency; recovery reset strength; recovery decay semantics; representation-error materiality; minimum-notional materiality; sample sufficiency for validation
```

## Recovery Guard

```text
RECOVERY_GUARD_FIELDS = PM action HOLD/ADD; PM reasons structured_hold_worthiness_pass, trend_continuation, downside_risk_contained, positive_expected_edge, opportunity_rank_still_high, strong_trend_continuation; SI continuation_quality_status = PASS; SI downside_risk_status = PASS; SI ADD/HOLD evidence status = PASS; current_campaign_relative_return and observed_giveback as PIT context only
RECOVERY_GUARD_COMPLETE = PARTIAL
```

The guard is strong enough to prevent obvious premature EXIT in current recovery controls, but incomplete because current REDUCE rows often still show SI `PASS` fields while PM emits REDUCE. That means recovery evidence can block blind escalation, but final persistence thresholds still require validation.

Current-run controls:

```text
RECOVERY_CONTROL_COUNT = 17
RECOVERY_CONTROL_FALSE_ESCALATION_COUNT = 0
```

The 17 recovery-control campaigns were identified because they later transitioned from REDUCE to HOLD/ADD, but the guard judgment uses only PIT fields on and before each candidate date. Under the strict F1 guard, no recovery-control REDUCE row would be escalated solely from unrepresentability.

Representative controls:

| Symbol | PIT recovery evidence before/at recovery | Design result |
|---|---|---|
| 54010 | `structured_hold_worthiness_pass`, `trend_continuation`, SI PASS fields after REDUCE interruption | block premature EXIT |
| 40800 | REDUCE on peak warning, then HOLD with strong positive relative return and SI PASS fields | block immediate blind EXIT |
| 27880 | repeated REDUCE interruptions but multiple HOLD recoveries with SI PASS fields | reset/decay pressure |
| 32710 | REDUCE sequence followed by HOLD with trend continuation before later EXIT | block until fresh EXIT-grade evidence |
| 92420 | REDUCE then HOLD sequence with trend continuation and positive relative return | block premature EXIT |

## Escalation Branches

```text
IMMEDIATE_ESCALATION_SUPPORTED = PARTIAL
PERSISTENT_ESCALATION_SUPPORTED = PARTIAL
```

Immediate branch:

```text
REDUCE unrepresentable
+ STRONG/high-confidence de-risk semantics
+ current PIT EXIT-grade evidence
+ no recovery guard
=> PM may emit EXIT directly
```

The current run has 17 STRONG REDUCE rows, but their PM reasons are `peak_drawdown_warning` or `risk_increased_but_trend_not_broken`, while canonical EXIT-grade reason codes appear on PM EXIT rows. Therefore the branch is structurally valid from C0D/C0E, but current-run immediate production criteria remain unresolved.

Persistent branch:

```text
REDUCE unrepresentable
+ repeated fresh same-campaign REDUCE
+ no recovery reset
+ current PIT deterioration still present
+ EXIT-grade confidence increases or deterioration sufficiency resolves
=> PM may emit EXIT directly
```

The current run has 29 persistent zero-REDUCE campaigns. This supports the branch structurally, but F1 does not choose persistence counts or thresholds from Historical results.

## 61750 Control

```text
61750_ESCALATION_JUDGMENT = PERSISTENT_BRANCH_STRUCTURALLY_ELIGIBLE_BUT_FINAL_EXIT_UNRESOLVED
61750_FIRST_PIT_ESCALATION_DATE = UNRESOLVED
```

61750 is a clean one-lot control but not an allowed fitted threshold source. In the current window, every REDUCE row was:

- `current_quantity = 100`
- `trading_unit = 100`
- `target_reduce_ratio = 0.25`
- `raw_reduce_quantity = 25`
- `rounded_reduce_quantity = 0`
- `reduce_final_sell_quantity = 0`
- `reduce_execution_semantic = REDUCE_UNEXECUTABLE_DUE_TO_DISCRETE_LOT`
- PM reason `risk_increased_but_trend_not_broken`
- SI `continuation_quality_status = PASS`
- SI `downside_risk_status = PASS`

61750 trace under the proposed contract:

| Date | PM reason | Deterioration state | Recovery state | Escalation state |
|---|---|---|---|---|
| 2022-09-13 | risk_increased_but_trend_not_broken | WEAKENING_BUT_INTACT | PASS_GUARD_PRESENT | UNREPRESENTABLE_PRESERVE |
| 2022-09-14 | risk_increased_but_trend_not_broken | WEAKENING_BUT_INTACT | PASS_GUARD_PRESENT | PERSISTENT_STRUCTURAL_UNRESOLVED |
| 2022-09-15 | risk_increased_but_trend_not_broken | WEAKENING_BUT_INTACT | PASS_GUARD_PRESENT | PERSISTENT_STRUCTURAL_UNRESOLVED |
| 2022-09-16 | risk_increased_but_trend_not_broken | WEAKENING_BUT_INTACT | PASS_GUARD_PRESENT | PERSISTENT_STRUCTURAL_UNRESOLVED |
| 2022-09-20 | risk_increased_but_trend_not_broken | WEAKENING_BUT_INTACT | PASS_GUARD_PRESENT | PERSISTENT_STRUCTURAL_UNRESOLVED |
| 2022-09-21 | risk_increased_but_trend_not_broken | WEAKENING_BUT_INTACT | PASS_GUARD_PRESENT | PERSISTENT_STRUCTURAL_UNRESOLVED |
| 2022-09-22 | risk_increased_but_trend_not_broken | WEAKENING_BUT_INTACT | PASS_GUARD_PRESENT | PERSISTENT_STRUCTURAL_UNRESOLVED |
| 2022-09-26 | risk_increased_but_trend_not_broken | WEAKENING_BUT_INTACT | PASS_GUARD_PRESENT | PERSISTENT_STRUCTURAL_UNRESOLVED |
| 2022-09-27 | risk_increased_but_trend_not_broken | WEAKENING_BUT_INTACT | PASS_GUARD_PRESENT | PERSISTENT_STRUCTURAL_UNRESOLVED |
| 2022-09-28 | risk_increased_but_trend_not_broken | WEAKENING_BUT_INTACT | PASS_GUARD_PRESENT | PERSISTENT_STRUCTURAL_UNRESOLVED |
| 2022-09-29 | risk_increased_but_trend_not_broken | WEAKENING_BUT_INTACT | PASS_GUARD_PRESENT | PERSISTENT_STRUCTURAL_UNRESOLVED |
| 2022-09-30 | risk_increased_but_trend_not_broken | WEAKENING_BUT_INTACT | PASS_GUARD_PRESENT | PERSISTENT_STRUCTURAL_UNRESOLVED |
| 2022-10-03 | risk_increased_but_trend_not_broken | WEAKENING_BUT_INTACT | PASS_GUARD_PRESENT | PERSISTENT_STRUCTURAL_UNRESOLVED |
| 2022-10-04 | risk_increased_but_trend_not_broken | WEAKENING_BUT_INTACT | PASS_GUARD_PRESENT | PERSISTENT_STRUCTURAL_UNRESOLVED |
| 2022-10-05 | risk_increased_but_trend_not_broken | WEAKENING_BUT_INTACT | PASS_GUARD_PRESENT | PERSISTENT_STRUCTURAL_UNRESOLVED |
| 2022-10-06 | risk_increased_but_trend_not_broken | WEAKENING_BUT_INTACT | PASS_GUARD_PRESENT | PERSISTENT_STRUCTURAL_UNRESOLVED |
| 2022-10-07 | risk_increased_but_trend_not_broken | WEAKENING_BUT_INTACT | PASS_GUARD_PRESENT | PERSISTENT_STRUCTURAL_UNRESOLVED |
| 2022-10-11 | risk_increased_but_trend_not_broken | WEAKENING_BUT_INTACT | PASS_GUARD_PRESENT | PERSISTENT_STRUCTURAL_UNRESOLVED |
| 2022-10-12 | risk_increased_but_trend_not_broken | WEAKENING_BUT_INTACT | PASS_GUARD_PRESENT | PERSISTENT_STRUCTURAL_UNRESOLVED |

The first structural persistence date is 2022-09-14, but F1 does not permit final EXIT on that date because the deterioration sufficiency and recovery guard thresholds are unresolved. This judgment does not use later delisting, later price, or later PnL.

## Breakdown Controls

Current PM EXIT rows show the EXIT-grade reason family already exists:

| EXIT-grade reason | Count |
|---|---:|
| trend_and_opportunity_broken | 22 |
| weak_hold_score | 18 |
| profit_retention_break | 15 |
| hard_stop_current_return | 11 |

The proposed contract should allow PM to emit EXIT directly when current PIT evidence reaches these families. It should not force Runtime or PS to reinterpret REDUCE rows.

## One-Lot Semantics

```text
ONE_LOT_POSITION = current_quantity <= trading_unit
ONE_LOT_ESCALATION_REQUIRES_DERIORATION_EVIDENCE = YES
```

For one-lot positions, partial REDUCE is impossible when the requested partial quantity floors to zero. The contract should explicitly recognize this representation problem and avoid endless impossible partial REDUCE. However:

```text
REDUCE_UNREPRESENTABLE alone != EXIT
ONE_LOT alone != EXIT
```

One-lot escalation requires current PIT deterioration evidence plus no recovery guard, and persistent-branch parameters must be validated before mutation.

## Minimum-Notional Semantics

The 15 minimum-notional rows differ from discrete-lot rows because `rounded_reduce_quantity` may already be positive while final sell quantity is zero. Examples include:

- 89180 with rounded quantities from 100 to 1900;
- 36640 with rounded quantity 100;
- 33500 with rounded quantity 100.

F1 classification:

```text
MINIMUM_NOTIONAL_SCOPE = SEPARATE_FROM_DISCRETE_LOT; INCLUDE_IN_NEXT_SHADOW_AS_ADJACENT_FAMILY_WITH_DISTINCT_REASON
```

They should be exposed in the next shadow artifact, but escalation semantics may require notional materiality and order-feasibility review before sharing the discrete-lot policy.

## Winner Protection

```text
WINNER_PROTECTION_CONTRACT = PASS
```

The proposed contract protects winners by requiring all of:

- current PM REDUCE;
- current unrepresentability;
- current PIT deterioration;
- no recovery guard;
- persistence or immediate EXIT-grade evidence;
- PM-owned final action.

It rejects:

- one-lot automatic EXIT;
- count-only persistence;
- magnitude-only escalation;
- Runtime-side conversion;
- outcome-selected thresholds.

## Market Context

```text
MARKET_CONTEXT_LOGIC_CHANGED = NO
```

F0 found `MARKET_CONTEXT_SELL_AUTHORITY = NONE`. F1 does not solve that. The contract can operate without Market Context because PM/SI already provide PIT SELL states, but Market Context propagation should be handled as separate F2 work if SELL authority wants regime-sensitive behavior.

## Shadow Design For F1A

Next shadow artifact:

```text
diagnostic_shadow/unrepresentable_reduce_exit_shadow.json
```

Reuse C0D structure and add current-run coverage for both discrete-lot and minimum-notional families. Required row fields:

- current PM action;
- PM action source id;
- campaign id;
- current quantity;
- trading unit;
- one-lot flag;
- target reduce ratio;
- raw reduce quantity;
- rounded reduce quantity;
- final reduce sell quantity;
- representability reason;
- representation error;
- deterioration state;
- recovery state;
- persistence state;
- immediate branch state;
- persistent branch state;
- final shadow action;
- parameter resolution state;
- PIT proof;
- `future_information_used = false`;
- `later_pnl_used = false`;
- `final_campaign_outcome_used = false`.

F1A should materialize this on the current run non-mutatingly and validate structural counts before any mutating implementation review.

## Required Output

```text
PRIMARY_JUDGMENT = PHASE31_F1_ALTERNATIVE_G_REQUIRES_REFINEMENT_PM_OWNED_PIT_ESCALATION_CONTRACT_DEFINED
ESCALATION_OWNER = PM
DISCRETE_LOT_SCOPE = PM REDUCE + zero final sell quantity + REDUCE_UNEXECUTABLE_DUE_TO_DISCRETE_LOT + open position + PIT deterioration evidence
MINIMUM_NOTIONAL_SCOPE = separate adjacent zero-REDUCE family; expose in shadow separately; do not merge blindly with discrete-lot
PIT_DETERIORATION_FIELDS = PM action/reason_codes/intensity/confidence; SI continuation/downside/current relative return/MFE/giveback/profit protection; PS representability fields; campaign-scoped PM history
PERSISTENCE_DEFINITION = repeated fresh same-campaign unrepresentable PM REDUCE with current PIT deterioration, no recovery reset, no hidden reduce debt, and unresolved validation parameters
RECOVERY_GUARD_FIELDS = PM HOLD/ADD and hold/add-compatible reason codes; SI continuation_quality_status PASS; SI downside_risk_status PASS; SI ADD/HOLD evidence PASS; current relative return/giveback as PIT context
RECOVERY_GUARD_COMPLETE = PARTIAL
IMMEDIATE_ESCALATION_SUPPORTED = PARTIAL
PERSISTENT_ESCALATION_SUPPORTED = PARTIAL
PARAMETER_UNRESOLVED = persistence minimum; recent-window length; deterioration sufficiency; recovery reset strength; recovery decay; representation-error materiality; minimum-notional materiality; validation sample sufficiency
ONE_LOT_ESCALATION_REQUIRES_DERIORATION_EVIDENCE = YES
61750_ESCALATION_JUDGMENT = PERSISTENT_BRANCH_STRUCTURALLY_ELIGIBLE_BUT_FINAL_EXIT_UNRESOLVED
61750_FIRST_PIT_ESCALATION_DATE = UNRESOLVED
RECOVERY_CONTROL_COUNT = 17
RECOVERY_CONTROL_FALSE_ESCALATION_COUNT = 0
WINNER_PROTECTION_CONTRACT = PASS
ALTERNATIVE_G_DISPOSITION = REFINE
MARKET_CONTEXT_LOGIC_CHANGED = NO
FUTURE_INFORMATION_USED_FOR_POLICY_DESIGN = NO
OUTCOME_USED_FOR_THRESHOLD_SELECTION = NO
MUTATING_IMPLEMENTATION_AUTHORIZED = NO
LONG_HISTORICAL_EXECUTED = NO
```

## NEXT_TASK_RECOMMENDATION

```text
Phase31-F1A current-run non-mutating Alternative G shadow materialization / validation
```

Only after F1A structural validation should a separate mutating implementation authorization review be considered.

## FINAL QUESTIONS

1. REDUCE不能をEXITへ昇格する条件をPITだけで定義できるか？

   Partially. 所有権・scope・state modelはPITだけで定義できますが、persistence/deterioration thresholds are unresolved.

2. 回復中Winnerを誤EXITしないguardを作れるか？

   Yes for the current structural guard. `REDUCE_UNREPRESENTABLE alone != EXIT` and HOLD/ADD-compatible SI evidence blocks escalation. Current recovery-control false escalation count is 0.

3. one-lot positionはどう扱うべきか？

   One-lot is an explicit representability state: partial REDUCE is impossible, but EXIT requires current PIT deterioration and no recovery guard.

4. 61750はPIT上どの時点ならEXITへ昇格可能だったか？

   Final EXIT date is unresolved. Structural persistence begins on 2022-09-14, but current PIT fields remain WEAKENING_BUT_INTACT with PASS recovery guards, so F1 does not authorize an EXIT date.

5. C0 Alternative Gをそのまま再利用できるか？

   No. Reuse and refine. Minimum-notional scope and current-run shadow validation must be added.

6. numeric thresholdの過学習なしに設計できるか？

   Yes. F1 defines semantic gates and explicitly leaves numeric parameters unresolved.

7. 次にcurrent run shadow validationへ進める状態か？

   Yes. Proceed to F1A non-mutating current-run shadow materialization / validation.
