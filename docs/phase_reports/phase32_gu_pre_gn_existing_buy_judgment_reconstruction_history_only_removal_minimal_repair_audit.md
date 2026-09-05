# Phase32-GU — Pre-GN Existing BUY Judgment Reconstruction / History-Only Removal Minimal Repair Audit

Date: 2026-09-05 JST

Scope: READ-ONLY / DESIGN-ONLY. No source/config/schema/runtime state changes were made. The running 650BD run `runtime-test-historical-extended-smoke-20260905T002804721163Z` was not stopped or changed. Historical outcome/PnL was not used for design selection.

## Executive Judgment

The original repair intent was not “invent a new rank-first BUY logic.” It was: preserve existing Production Current-PIT BUY judgment as much as possible, while removing old ownership/campaign/history, held/flat priority effects, and accepted-increment dependency.

Source reconstruction shows that pre-GN MCV already had a Current-PIT quality-class-first comparator:

```text
COMPARISON_CLASSES.get(marginal_capital_value_class, 99)
-> opportunity/input opportunity rank
-> insufficiency fallback marker
-> symbol
```

GN correctly removed the accepted-increment prerequisite and added explicit history-neutral audit flags, but also changed the first two sort keys to absolute rank-first. That rank-first change was not required for history-neutrality or NEW/ADD parity. The minimal intended repair is Option C: pre-GN existing Current-PIT comparator minus forbidden history/relationship/accepted-increment dependencies.

## Pre-GN Comparator Reconstruction

PRE_GN_COMPARATOR_RECONSTRUCTED: `YES`

Evidence source: `git show HEAD:src/ai_fund_lab_v2/strategy/marginal_capital_value.py`

PRE_GN_SORT_KEY:

```text
1. marginal_capital_value_class via COMPARISON_CLASSES
2. opportunity_rank / input_opportunity_rank / opportunity_buy_rank
3. fallback_only where comparison_sufficiency == INSUFFICIENT
4. symbol
```

Pre-GN `COMPARISON_CLASSES`:

```text
ELIGIBLE_STRONG = 1
ELIGIBLE_COMPARABLE = 2
ELIGIBLE_WEAK = 3
REVIEW_REQUIRED = 4
BLOCKED_OR_NOT_ELIGIBLE = 5
COMPARISON_INSUFFICIENT = 6
```

Pre-GN candidate admission:

```text
if not intent or accepted_increment(row) <= 0:
    continue
```

Pre-GN role map:

| item | pre-GN role |
|---|---|
| rank | second sort key after MCV comparison class |
| MCV class | first sort key |
| BQ / Entry | feeds `classify_opportunity_quality()` and MCV class |
| Momentum / Trend / Continuation | feeds BQ/Entry/strategy-intelligence evidence copied into source evidence |
| NCU | existing marginal/next-capital evidence path; not a new separate comparator here |
| accepted increment | prerequisite for receiving any canonical BUY priority |
| relationship | `candidate_intent()` depends on current_position + PM ADD or flat + ADD_CANDIDATE |
| history | ADD evidence may include campaign continuation and existing-position lineage; old history was not explicitly flagged out in priority audit fields pre-GN |

## Input Classification

PRE_GN_CURRENT_PIT_INPUTS:

- `runtime_opportunity_score`
- `input_opportunity_rank` / `opportunity_rank` / `opportunity_buy_rank`
- `quality_action` / `buy_quality_action`
- `entry_admission_action`
- `entry_admission_state`
- `entry_admission_evidence_sufficiency`
- `selection_quality_tier`
- `continuation_quality_status`
- `downside_risk_status`
- `momentum_state`
- `trend_state`
- `expected_edge_improvement_state` when PIT-scoped
- `incremental_investment_value_state` when PIT-scoped
- `opportunity_cost_status` when PIT-scoped
- MCV comparison class

PRE_GN_RELATIONSHIP_INPUTS:

- `current_position`
- `pm_action == ADD`
- `membership_intent == ADD_CANDIDATE`
- `lifecycle_intent` as BUY_NEW / BUY_ADD
- held/flat branch inside `candidate_intent()`

PRE_GN_HISTORY_INPUTS:

- `current_position_campaign_id`
- `position_campaign_id`
- `same_campaign_continuation_status`
- campaign continuation evidence
- prior/old campaign lineage where present in ADD evidence
- old ownership / prior EXIT / prior ADD were not explicitly protected by audit flags pre-GN

SAFETY_EXECUTION inputs:

- accepted/lot-aware accepted increments
- target/current weight delta
- lot feasibility
- cap/headroom
- liquidity
- buying power
- ADD Safety / G129 / Recent Exit Guard

## GN Semantic Diff

GN_SEMANTIC_DIFF_DECOMPOSED: `YES`

GN changes in semantic units:

| change | classification | judgment |
|---|---|---|
| remove `accepted_increment(row) > 0` prerequisite before priority | REQUIRED_FOR_CORRECTNESS | keep |
| add explicit `accepted_increment_required_for_priority = false` | REQUIRED_FOR_CORRECTNESS | keep |
| add history-neutral audit flags for old ownership, campaign, prior ADD/EXIT, average cost, realized PnL | REQUIRED_FOR_HISTORY_NEUTRALITY | keep |
| state `relationship_materialized_after_priority = true` | REQUIRED_FOR_NEW_ADD_PARITY | keep |
| switch sort key from class-first/rank-second to rank-first/class-second | OVERREACH | do not keep as final intended repair |
| use construction priority only if rank missing | REQUIRED_FOR_CORRECTNESS as fail-soft fallback | keep only as missing-rank fallback, not main authority |
| remove PC fallback from MCV priority to quality/construction order when any comparison insufficient | REQUIRED_FOR_CORRECTNESS | keep, provided MCV comparator is corrected |
| propagate canonical priority through PC/PS/runtime without redecision | REQUIRED_FOR_CORRECTNESS | keep |

GN_HISTORY_NEUTRAL_REQUIRED_CHANGES:

- explicit exclusion of old ownership/campaign/prior ADD/prior EXIT/average cost/realized PnL from priority
- priority formation before relationship materialization
- Recent Exit Guard remains bounded safety/guard exception, not old-history penalty

GN_NEW_ADD_PARITY_REQUIRED_CHANGES:

- compute common BUY priority before BUY_NEW vs BUY_ADD relationship
- prevent held/flat status from boosting or penalizing priority
- materialize relationship after priority for sizing/safety path

GN_INCIDENTAL_CHANGES:

- added observability fields that are useful but not themselves investment semantics
- construction-priority fallback only for missing rank

GN_OVERREACH_CHANGES:

- absolute Current Opportunity rank-first comparator
- demotion of existing Current-PIT MCV quality class from primary comparator key to secondary after rank

## Was Absolute Rank-First Required?

ABSOLUTE_RANK_FIRST_REQUIRED_FOR_HISTORY_NEUTRALITY: `NO`

ABSOLUTE_RANK_FIRST_REQUIRED_FOR_NEW_ADD_PARITY: `NO`

Reason: history-neutrality requires removing forbidden history/relationship inputs from the comparator. It does not require reordering valid Current-PIT inputs. NEW/ADD parity requires common pre-relationship priority formation. It does not require rank to outrank MCV class.

The pre-GN class-first comparator can be retained if:

- MCV class is generated only from Current-PIT evidence.
- candidate admission no longer depends on accepted increment.
- relationship labels are applied after priority.
- old campaign/ownership/prior ADD/prior EXIT/cost/PnL are explicitly excluded.

## Current-PIT Quality Preservation

PRE_GN_CURRENT_PIT_QUALITY_SEMANTICS_PRESERVABLE: `YES`

PRE_GN_MCV_CLASS_AUTHORITY_VALID_CURRENT_PIT: `YES, when generated from BQ/Entry/momentum/trend/continuation/NCU evidence and not old history`

PRE_GN_NCU_AUTHORITY_PRESERVABLE: `YES`

MCV’s responsibility is to compare marginal capital value. The pre-GN quality-class-first ordering is consistent with that responsibility when the class is based on same-day Current-PIT evidence. NCU can remain the existing single next-capital-unit comparator; no extra comparator is needed.

## Existing Comparator Minus History

EXISTING_COMPARATOR_MINUS_HISTORY_FEASIBLE: `YES`

Conceptual minimal comparator:

```text
Pre-GN existing Current-PIT comparator:
  MCV class -> Current Opportunity rank -> insufficiency -> symbol

MINUS:
  old ownership / old campaign / prior ADD / old EXIT / average cost / realized PnL
  held/flat priority effect
  accepted-increment prerequisite

PLUS KEEP:
  priority before relationship
  relationship materialization after priority
  canonical priority propagation through PC/PS/runtime
```

This is not a new investment strategy; it is the original comparator with invalid preconditions and history effects removed.

NEW_ADD_PARITY_PRESERVABLE: `YES`

ACCEPTED_INCREMENT_INDEPENDENCE_PRESERVABLE: `YES`

## 50250 Classification

50250_PRE_GN_PRIORITY_SEMANTIC_CLASSIFICATION: `A_VALID_CURRENT_PIT_INVESTMENT_JUDGMENT`

GR evidence showed 2023-06-16 `50250`:

- rank: `23`
- MCV class: `ELIGIBLE_STRONG`
- BQ/Entry: `REDUCED_ALLOCATION_ONLY`, `BUY_NEW_ALLOWED`
- momentum/trend: `BUY_ELIGIBLE`, `HEALTHY_CONTINUATION`
- pre-GN MCV priority: `2`
- GN MCV priority: `12`

This was not evidenced as history contamination, relationship contamination, or accepted-increment contamination. It was the pre-GN Current-PIT class-first comparator doing what it was designed to do: allow a lower-ranked but stronger-quality same-day opportunity to outrank weaker class rows.

## Rank / Quality Conflict

GS observed `219` post-GN rank-quality conflicts. Under the reconstructed pre-GN comparator, lower-ranked `ELIGIBLE_STRONG` rows would outrank higher-ranked `ELIGIBLE_COMPARABLE` rows, then rank would order within class.

That behavior is valid only if the class is Current-PIT. It is invalid if the class is elevated by old campaign, held-state, prior ADD/EXIT, average cost, or realized PnL.

## Options

### Option A — Current GN rank-first

OPTION_A_JUDGMENT: `KEEP_AS_RUNNING_BASELINE / REJECT_AS_MINIMAL_REPAIR`

It preserves history-neutrality and auditability, but it does not preserve existing Current-PIT class-first BUY judgment.

### Option B — Full rollback to pre-GN

OPTION_B_JUDGMENT: `REJECT`

Full rollback would restore:

- accepted-increment prerequisite
- possible held/flat priority dependence
- weaker audit proof against old history/campaign/ownership
- PC fallback behavior that can bypass canonical MCV priority

### Option C — Pre-GN Current-PIT comparator minus history/relationship/accepted-increment

OPTION_C_JUDGMENT: `ACCEPT_AS_RECOMMENDED`

This best matches the original user intent:

- keep existing Current-PIT MCV class-first judgment
- keep rank as second key inside existing comparator
- remove only invalid history/relationship/accepted-increment priority dependencies
- keep downstream sizing/safety/cash/SELL unchanged

### Option D — New GT quality-aware semantic redesign

OPTION_D_JUDGMENT: `DEFER`

Option D may be useful later, but GU shows it is not necessary as the next repair. The minimal next step should not invent a new score, weight, threshold, cutoff, or comparator semantics when the pre-GN Current-PIT comparator can be preserved.

RECOMMENDED_OPTION: `Option C`

## Minimal Diff Feasibility

Option C from current GN source would minimally:

1. Restore `sort_key()` order to:

```text
COMPARISON_CLASSES.get(comparison_class, 99)
-> rank
-> fallback_only
-> symbol
```

2. Keep GN’s removal of the accepted-increment admission gate:

```text
if not intent:
    continue
```

3. Keep GN’s explicit flags:

```text
current_position_relationship_used_for_priority = false
old_ownership_used_for_priority = false
closed_campaign_used_for_priority = false
prior_exit_used_for_priority = false
prior_add_count_used_for_priority = false
average_cost_used_for_priority = false
realized_pnl_used_for_priority = false
accepted_increment_required_for_priority = false
relationship_materialized_after_priority = true
```

4. Keep PC canonical priority consumption and no PS/runtime priority redecision.

OPTION_C_NEW_MODULE_COUNT: `0`

OPTION_C_NEW_AUTHORITY_COUNT: `0`

OPTION_C_NEW_COMPARATOR_COUNT: `0`

OPTION_C_NEW_SCHEMA_FAMILY_COUNT: `0`

## Preserve GN Good Parts

GN_GOOD_PARTS_PRESERVED: `YES`

Keep:

- priority before relationship
- explicit history-neutrality flags
- NEW/ADD parity
- accepted-increment independence
- canonical priority propagation
- PC/PS/runtime no-redecision
- Recent Exit Guard separation
- SELL/Winner/Sizing/Cash/ADD Safety/G129 isolation

EXISTING_CURRENT_PIT_SEMANTICS_RESTORED_ONLY: `YES`

NEW_NUMERIC_WEIGHTING_REQUIRED: `NO`

No new score, blend, threshold, weighting, rank cutoff, or quality cutoff is needed.

## Isolation

- SELL_CHANGE_REQUIRED: `NO`
- WINNER_CHANGE_REQUIRED: `NO`
- SIZING_CHANGE_REQUIRED: `NO`
- CASH_CHANGE_REQUIRED: `NO`
- ADD_SAFETY_CHANGE_REQUIRED: `NO`
- REENTRY_CHANGE_REQUIRED: `NO`

Option C touches only the BUY priority comparator ordering inside existing MCV/PC flow. HOLD, REDUCE, EXIT, Winner Protection, Profit Retention, Position Sizing, target weight formulas, Cash semantics, lot, cap, liquidity, ADD Safety, G129, Recent Exit Guard, Runtime Planning, Pending, Submit, Execution, Safety, and broker boundaries remain unchanged.

## Adversarial Cases

| case | Option C expected behavior |
|---|---|
| rank1 comparable vs rank3 strong | rank3 strong can outrank rank1 comparable because MCV class is valid Current-PIT evidence |
| rank3 strong vs rank5 strong | rank3 wins within same class |
| rank1 strong vs rank2 comparable | rank1 strong wins |
| same evidence NEW vs ADD | same priority; relationship applied after priority |
| old campaign | no priority effect |
| prior ADD | no priority effect |
| old EXIT | no priority effect outside bounded Recent Exit Guard |
| recent EXIT | bounded guard may block/release as guard, not old-history rank penalty |
| accepted increment zero | still receives priority if BUY intent exists |
| ADD Safety blocked | downstream ADD safety blocks allocation/order, not priority formation |
| lot infeasible | downstream lot/PS skip; no implicit priority rewrite |
| Winner unaffected | PM/Winner authority untouched |

## Information Preservation Matrix

INFORMATION_PRESERVATION_MATRIX_COMPLETE: `YES`

| Evidence | Pre-GN | GN | Minimal Option C |
|---|---|---|---|
| rank | second key | first key | second key after MCV class |
| BQ/Entry | feeds MCV class | feeds MCV class but after rank in priority | feeds MCV class as pre-GN |
| MCV class | first key | second key | first key |
| momentum | PIT quality evidence | carried but rank-dominated | preserved as PIT quality evidence |
| trend | PIT quality evidence | carried but rank-dominated | preserved as PIT quality evidence |
| continuation | PIT quality evidence | carried but rank-dominated | preserved as PIT quality evidence |
| NCU | existing comparison evidence | preserved but rank-dominated in priority | preserved without new comparator |
| old ownership | not sufficiently flagged out | explicitly excluded | explicitly excluded |
| campaign | ADD evidence / contamination risk | explicitly excluded as old-history priority | only same-day PIT ADD validity allowed; old campaign excluded |
| prior ADD | contamination risk | explicitly excluded | explicitly excluded |
| old EXIT | contamination risk except bounded guard | explicitly excluded except bounded guard | explicitly excluded except bounded guard |
| accepted increment | prerequisite | not prerequisite | not prerequisite |
| held/flat | intent branch before priority | flagged as not priority input | relationship after priority |

## Original Intent Match

OPTION_C_MATCHES_ORIGINAL_USER_INTENT: `YES`

Option C is exactly:

```text
existing BUY judgment preserved
minus history-dependent authority
minus relationship-dependent priority
minus accepted-increment dependency
```

It is therefore closer to the original intent than both current GN rank-first and a new quality-aware redesign.

## Gate

CONTINUE_650BD_UNCHANGED: `YES`

PRODUCTION_CHANGE_JUSTIFIED_NOW: `NO`

ADDITIONAL_SHADOW_DIFFERENTIAL_REQUIRED: `YES`

Reason: this phase is read-only/design-only. Even if Option C is the correct minimal repair, the next phase must define focused shadow/differential acceptance before implementation.

NEXT_STEP: `Create a focused Option C shadow/differential spec: restore pre-GN MCV class-first/rank-second comparator only as a proposed shadow, keep GN history-neutral and accepted-increment-independent guards, and test 50250/rank-quality conflicts/NEW-ADD parity/accepted-zero/SELL-Winner-Sizing-Cash-ADD-G129-REENTRY isolation before any production code change.`

Final Judgment: GN前の既存Current-PIT BUY判断は、MCV class-first / rank-second comparatorを保ったまま、old ownership/campaign/history・held/flat priority effect・accepted-increment dependencyだけを除去することで、新しい投資ロジックなしにhistory-neutral BUY判断として実現できる。
