# Phase32-FS Next-Capital-Unit SHADOW Comparator Detailed Specification / Pre-Implementation Design Review

## Scope

- Work type: DESIGN / READ-ONLY specification.
- Inputs: Phase32-FQ / FR accepted SHADOW-only architecture, Phase32-FO / FP evidence, FC, FG/FH, FK, FL, FM/FN, PC / MCV / Cash / Rank / Runtime SoT.
- No source, SHADOW implementation, Production behavior, config, schema, runtime state, Pending, or Ledger mutation was performed.
- No fresh-run, resume, recover, or replay was executed.
- Historical outcome was not used to define comparator logic, thresholds, weights, ranks, or Production design.

Purpose: freeze what the future SHADOW comparator observes, groups, compares, emits, and refuses to decide before any implementation begins.

## Non-Authority Contract

The Next-Capital-Unit SHADOW comparator is not a decision engine.

It has no authority over:

- BUY / NO_BUY
- ADD / NO_ADD
- Cash allocation
- target weight
- quantity
- order / Pending
- Ledger
- campaign identity
- PM lifecycle action

Required row invariant:

```text
authoritative_consumer_count = 0
future_information_used = false
historical_outcome_used = false
action_authority = false
quantity_authority = false
order_authority = false
```

## Input Contract

`SHADOW_INPUT_CONTRACT_COMPLETE`: YES.

### BUY_NEW

| Field | Source / producer | Semantic |
|---|---|---|
| `symbol` | PC member / BQ decision | Security identity. |
| `business_date` | daily artifact | PIT date. |
| `opportunity_rank` | Opportunity Ranking -> BQ/PC `input_opportunity_rank` | Supporting monotonic opportunity evidence, not hard gate. |
| `opportunity_score` | Opportunity/BQ/PC source evidence | Uncalibrated relative score, not expected return. |
| `bq_band`, `bq_action` | BUY Quality | Admission/allocation quality evidence. |
| `entry_state`, `entry_action` | Strategy Intelligence Entry | Current entry/continuation evidence. |
| `continuation` | Strategy Intelligence | Current continuation quality where available. |
| `downside_risk` | Strategy Intelligence / BQ | Risk evidence; hard blocks remain hard. |
| `expected_edge` | Strategy Intelligence if available | Typed evidence only; do not force numeric comparison. |
| `liquidity`, `lot_feasibility` | PC / PS evidence | Feasibility, not alpha. |
| `market_regime`, `risk_pacing` | Market Context / Portfolio Policy | Market/risk context. |
| `pc_eligibility` | PC member | Existing Production eligibility/result. |
| `production_allocation` | PC/PS/Runtime | Current Production result for comparison only. |

### BUY_ADD

| Field | Source / producer | Semantic |
|---|---|---|
| `symbol` | PM / PC member | Security identity. |
| `campaign_id` | PM / PC / lifecycle | Current campaign identity. |
| `pm_action` | PM | ADD intent; not direct quantity. |
| `add_worthiness` | Strategy Intelligence / PM / PC | ADD hard/soft eligibility. |
| `continuation` | Strategy Intelligence | Current incumbent thesis evidence. |
| `downside_risk` | Strategy Intelligence | Risk gate/evidence. |
| `no_loss_averaging` | PM / ADD evidence | Hard ADD safety. |
| `expected_edge` | SI / MCV if available | Typed ADD evidence. |
| `current_weight` | PC / position lifecycle | Existing exposure. |
| `target/headroom` | PC / PS | Incremental feasibility and cap context. |
| `cap`, `liquidity`, `lot_feasibility` | PC / PS | Hard feasibility. |
| `accepted_incremental_weight` | PC | Current Production accepted ADD increment. |
| `production_allocation` | PC/PS/Runtime | Current Production result for comparison only. |

### CASH

| Field | Source / producer | Semantic |
|---|---|---|
| `business_date` | daily artifact | PIT date. |
| `available_cash` | Portfolio Policy / PC / valuation | Current deployable cash context. |
| `residual_budget` | PC | Remaining budget context. |
| `market_quality` | Market Context | Market-wide opportunity/risk state. |
| `risk_pacing` | Portfolio Policy | Deployment posture. |
| `cash_interaction` | PC Cash competitor | Cash-vs-security interaction. |
| `cash_preferred_status` | PC participation/deferral evidence | Cash optionality state. |
| `production_residual_cash` | valuation/PC | Observed Production residual cash only. |

## Evidence Provenance / Grouping

`EVIDENCE_PROVENANCE_COMPLETE`: YES.

`EVIDENCE_GROUPING_COMPLETE`: YES.

Evidence must be grouped by lineage so common source features are not counted twice.

| Group | Evidence | Producer lineage | Comparator use |
|---|---|---|---|
| Opportunity Quality | rank, score, BQ band/action, BQ components | Opportunity Ranking + BQ | One grouped opportunity-quality signal. |
| Entry / Continuation | Entry state/action, continuation, momentum/trend/tick | Strategy Intelligence / BQ components | One grouped current-entry/continuation signal. |
| Risk | downside, volatility, market/risk pacing | SI / Market Context / Portfolio Policy | Hard block first; otherwise contextual risk. |
| Incremental Feasibility | current weight, target/headroom, cap, liquidity, lot | PC / PS | Eligibility/feasibility, not alpha. |
| Action-Specific | BUY_NEW freshness/diversification, BUY_ADD no-loss/incumbent continuation, CASH optionality | Action owner / PC Cash | Preserved as typed reason, not bonus. |
| Production Result | accepted weight/increment/quantity/fill presence | PC / PS / Runtime | Baseline comparison only. |

No double counting matrix:

| Evidence | Producer | Derived from | Group | May influence comparator once? |
|---|---|---|---|---|
| opportunity rank | Opportunity Ranking | model/ranking artifact | Opportunity Quality | YES, once |
| opportunity score | Opportunity Ranking | same ranking artifact | Opportunity Quality | YES, once with rank |
| BQ band/action | BQ | rank/score/market/execution/portfolio components | Opportunity Quality | YES, grouped, not independent from rank |
| Entry state/action | Strategy Intelligence | trend/momentum/continuation | Entry / Continuation | YES, once |
| continuation | Strategy Intelligence | current campaign/security evidence | Entry / Continuation | YES, grouped |
| downside risk | Strategy Intelligence / BQ | risk/volatility evidence | Risk | YES, once |
| market/risk pacing | Market Context / Portfolio Policy | market breadth/trend/volatility | Risk | YES, contextual |
| ADD worthiness | PM/SI/PC | campaign, CQ, risk, add/reduce history | Action-Specific + Eligibility | YES, hard gate first |
| headroom/cap/liquidity/lot | PC/PS | portfolio/price/unit/cap evidence | Incremental Feasibility | YES, feasibility only |
| Cash interaction | PC | cash/risk/opportunity context | Action-Specific Cash | YES, once |

`DOUBLE_COUNTING_RISK_RESOLVED_BY_SPEC`: YES, if implemented as grouped typed evidence with lineage, not additive independent points.

## Output Semantics

`SINGLE_SCORE_AVOIDED`: YES.

The comparator must not emit a hidden weighted score. It emits typed classes and reasoned relations.

Recommended SHADOW-only output classes:

```text
NCU_STRONG_CURRENT_CAPITAL_OPTION
NCU_COMPARABLE_HIGH
NCU_COMPARABLE
NCU_WEAK_BUT_VALID
NCU_CASH_OPTIONALITY
NCU_BLOCKED
NCU_INSUFFICIENT_EVIDENCE
NCU_UNRESOLVED_COMPARISON
```

Prefix `NCU_` avoids collision with existing MCV Production classes.

Required per-row output:

```text
business_date
run_id
source_generation
option_type                  # BUY_NEW / BUY_ADD / CASH
symbol
campaign_id
hard_eligibility_status
hard_eligibility_reason_codes
evidence_groups
comparison_class
dominance_relation
binding_constraint
production_result
shadow_comparison_result
divergence_class
divergence_reason_codes
would_be_executable=false when hard blocked
authoritative_consumer_count=0
future_information_used=false
historical_outcome_used=false
```

`ACTION_SPECIFIC_SEMANTICS_PRESERVED`: YES.

`BUY_NEW_BONUS_AVOIDED`: YES.

`ADD_LABEL_BONUS_AVOIDED`: YES.

`CASH_DEFAULT_WINNER_AVOIDED`: YES.

## Ordered Comparison / Dominance

`UNRESOLVED_COMPARISON_SUPPORTED`: YES.

The comparator may explain dominance only when safe:

```text
A_DOMINATES_B
```

requires:

- same or stronger hard eligibility;
- stronger or equal opportunity quality;
- stronger or equal entry/continuation;
- no worse risk;
- no worse feasibility/headroom;
- no conflicting action-specific evidence.

If there is any meaningful tradeoff, output:

```text
NON_DOMINATED
NCU_UNRESOLVED_COMPARISON
```

Allowed ordering aids:

- monotonic supporting rank evidence;
- reason ordering;
- dominance relation;
- explicit unresolved state.

Forbidden:

- hidden weighted sum;
- Historical-calibrated score;
- fixed top-N;
- fixed threshold;
- forced single winner.

`FALSE_PRECISION_RISK_AVOIDED`: YES. Expected edge without economic units remains typed qualitative evidence.

## Hard Eligibility Visibility Without Revival

`HARD_BLOCK_VISIBILITY_WITHOUT_REVIVAL_FEASIBLE`: YES.

Production hard-blocked options may appear in SHADOW for diagnosis only:

```text
hard_eligibility_status = BLOCKED
comparison_class = NCU_BLOCKED
would_be_executable = false
blocking_reason_codes = [...]
current_strength_evidence = visible
```

This is required for cases like five-ADD cap incumbents. Showing current strength does not authorize ADD, target weight, quantity, order, or bypass.

`FIVE_ADD_CAP_BYPASS_AVOIDED`: YES. Five-ADD cap remains a hard upstream eligibility block in this task. The SHADOW may label `blocked_but_currently_strong_incumbent`, but must not recommend or execute bypass.

## Rank / Deep-Rank Semantics

`RANK_HARD_GATE_AVOIDED`: YES.

Rank is:

- supporting monotonic evidence;
- not a BUY/NO_BUY authority;
- not a fixed top-N gate;
- not an automatic winner.

Strong deep-rank case pattern, e.g. `2023-07-25 / 72770 rank39`:

```text
opportunity_rank_state = WEAK_OR_DEEP
entry_current_strength = STRONG
bq_state = LOW_REDUCED
mcv_current_class = ELIGIBLE_STRONG
dominance_relation = UNRESOLVED unless all groups dominate
divergence_reason = rank_entry_tradeoff_preserved
```

The comparator must preserve the tradeoff rather than declaring deep rank invalid.

## Strong Incumbent Zero-Increment

For incumbents such as `2023-07-25 / 94320` and `76470`:

```text
option_type = BUY_ADD_DIAGNOSTIC or BUY_ADD
campaign_id = current campaign
hard_eligibility_status = BLOCKED or NO_ACCEPTED_INCREMENT
current_strength_evidence = visible
accepted_incremental_weight = 0
would_be_executable = false
binding_constraint = add_worthiness/headroom/cap/five_add_cap/PC_zero
```

This enables FP problem diagnosis without converting held incumbents into BUY_NEW or bypassing ADD gates.

## Cash Semantics

Cash output classes should distinguish:

```text
CASH_VALID_DEFER
CASH_PARTICIPATION_VALID
CASH_WEAK_COMPETITOR
CASH_UNRESOLVED
CASH_INSUFFICIENT_AUTHORITY
```

Cash is a valid alternative to weak security options. It is not leftover-only and not default winner.

## Authority Duplication Matrix

`AUTHORITY_DUPLICATION_PREVENTED_BY_SPEC`: YES.

| Existing authority | Comparator role | Override allowed? |
|---|---|---|
| Candidate / Opportunity Ranking | observe rank/score lineage | NO |
| BQ | observe band/action/components | NO |
| Entry | observe state/action/sufficiency | NO |
| PM | observe ADD/HOLD/SELL intent and campaign | NO |
| PC | observe Production allocation and cash interaction | NO in SHADOW |
| MCV | extend diagnostic evidence only | NO Production override |
| PS | observe feasibility/quantity result | NO |
| Runtime / Pending / Ledger | observe Production result only | NO |

## Golden Case Expected SHADOW Output

`GOLDEN_CASE_EXPECTED_OUTPUT_COMPLETE`: YES.

| Case | Expected eligibility | Expected groups | Expected SHADOW class | Production unchanged |
|---|---|---|---|---|
| `2023-03-22 / 67750` Strong BUY_NEW | PASS | strong opportunity, healthy entry, risk acceptable | `NCU_STRONG_CURRENT_CAPITAL_OPTION` or `NCU_COMPARABLE_HIGH` | YES |
| `2023-04-24 / 69270` Fast risk-on BUY_NEW | PASS | strong current opportunity, fast deployment valid | `NCU_STRONG_CURRENT_CAPITAL_OPTION` | YES |
| `2023-03-30 / 43880` Strong BUY_ADD | PASS if current ADD gates pass | ADD continuation, no-loss, headroom, current campaign | `NCU_STRONG_CURRENT_CAPITAL_OPTION` or `NCU_COMPARABLE_HIGH` | YES |
| `2023-06-13 / 21340` G129-sensitive ADD | PASS if PS/G129 increment valid | ADD plus quantity-scoped lineage | `NCU_STRONG_CURRENT_CAPITAL_OPTION` / no quantity authority | YES |
| `83060` recent-exit / ADD related | depends on actual guard/gates | recent-exit hard block or ADD current evidence | block remains block; ADD remains scoped | YES |
| Cash defer case | PASS as Cash option | cash optionality, risk context | `NCU_CASH_OPTIONALITY` / `CASH_VALID_DEFER` | YES |
| hard risk block | BLOCKED | risk group hard block | `NCU_BLOCKED` | YES |
| lot/cap block | BLOCKED or infeasible | feasibility group | `NCU_BLOCKED` | YES |

Any golden expected-output mismatch is a zero-tolerance stop condition.

## Problem Case Expected Diagnostic Output

`PROBLEM_CASE_EXPECTED_OUTPUT_COMPLETE`: YES.

| Problem case | Expected diagnostic |
|---|---|
| `2023-06-05 / 31920 rank23` | BUY_NEW option with rank-depth evidence, BQ/Entry/MCV groups, and same-day higher-ranked incumbent/BUY_NEW/Cash comparisons. Result may be `NCU_COMPARABLE` or `NCU_UNRESOLVED_COMPARISON`. |
| `2023-07-25 / 72770 rank39` | Preserve `OPPORTUNITY_RANK_WEAK`, LOW BQ, HEALTHY Entry, MCV strong. Output should not auto-block; likely `NCU_UNRESOLVED_COMPARISON` if tradeoff remains. |
| `2023-07-25 / 94320` | Strong/current incumbent evidence visible, accepted increment zero, hard eligibility or no-increment constraint explicit, `would_be_executable=false`. |
| `2023-07-25 / 76470` | Same as incumbent zero-increment; if cap/NO_ADD applies, expose without bypass. |
| Cash same-date | Cash option row with available cash, risk pacing, PC cash interaction, and whether Production treated participation/defer. |

Problem Case divergence is not a regression by itself. It is the intended diagnostic surface.

## Divergence Semantics

`SHADOW_DIVERGENCE_CLASSES_COMPLETE`: YES.

Production vs SHADOW divergence classes:

```text
EXPLAINED_BY_HARD_ELIGIBILITY
EXPLAINED_BY_FEASIBILITY
EXPLAINED_BY_PRIORITY_COMPRESSION
EXPLAINED_BY_CASH_INTERACTION
EXPLAINED_BY_ACTION_SPECIFIC_SEMANTIC
UNEXPLAINED_PRIORITY_INVERSION
INSUFFICIENT_EVIDENCE
NO_DIVERGENCE
```

`UNEXPLAINED_PRIORITY_INVERSION` is not a Production recommendation; it is a review signal.

## Artifact Size / Performance / Run-Age Safety

`SHADOW_ARTIFACT_BOUNDED`: YES_BY_SPEC.

Design constraints:

- one daily artifact per business date;
- overwrite/recreate within the day's strategy artifact set, not append unbounded run history;
- row count bounded by same-day PC members plus one Cash row;
- no whole-run scan;
- no prior campaign outcome reconstruction;
- no future/later valuation;
- no campaign final PnL;
- no accumulated run-age statistics for priority.

Expected growth: `O(current_day_PC_members)`, usually around Top50 + current positions + Cash, not `O(run_age)` or `O(run_age * candidates)`.

`SHADOW_COMPARATOR_RUN_AGE_INVARIANT_BY_DESIGN`: YES.

Same PIT input must produce the same SHADOW comparison regardless of total run artifact volume.

## Source / Date Authority

`SOURCE_DATE_AUTHORITY_DEFINED`: YES.

Every row must carry:

- `run_id`;
- `business_date`;
- `feature_date` where applicable;
- source generation / source commit if available;
- producer;
- source artifact path/hash;
- PIT validation status;
- `future_information_used=false`;
- stale/mixed/cross-run evidence status.

If source/date/run authority is missing, stale, mixed in an unsafe way, or cross-run, output `NCU_INSUFFICIENT_EVIDENCE` or `NCU_UNRESOLVED_COMPARISON`; do not synthesize authority.

## Stop Conditions

`SHADOW_STOP_CONDITIONS_COMPLETE`: YES.

Stop before Production consideration if any count is nonzero:

- golden expected output mismatch;
- G129 semantic mismatch;
- REENTRY contamination or `semantic_buy_type=REENTRY` revival;
- hard-block revival;
- double counting unresolved;
- rank top-N behavior;
- Cash blanket dominance;
- ADD label dominance;
- PS/Runtime authority field introduced;
- run-age dependency;
- future data dependency;
- source/date/run authority stale but accepted;
- action/quantity/order authority leak.

## Acceptance Metrics

`SHADOW_ACCEPTANCE_METRICS_COMPLETE`: YES.

Required metrics after implementation:

```text
golden_case_shadow_mismatch_count
unexplained_priority_inversion_count
blocked_option_revived_count
strong_buy_new_suppression_signal_count
add_label_bonus_signal_count
cash_blanket_dominance_count
rank_hard_gate_signal_count
evidence_double_count_signal_count
recent_exit_semantic_regression_count
G129_semantic_regression_count
run_age_dependency_count
authority_leak_count
future_information_used_count
stale_source_date_authority_accepted_count
```

`ZERO_TOLERANCE_REGRESSION_METRICS_DEFINED`: YES.

Zero tolerance:

- golden mismatch;
- hard block revival;
- G129 regression;
- REENTRY regression;
- authority leak;
- future data use;
- run-age dependency;
- unresolved double counting;
- stale/cross-run evidence accepted as authority.

Problem Case divergence is allowed and expected.

## Implementation Surface Preview

`FUTURE_SHADOW_IMPLEMENTATION_SURFACE_MINIMAL`: YES.

Future likely source touch points, not changed in FS:

- `src/ai_fund_lab_v2/strategy/marginal_capital_value.py`
- `src/ai_fund_lab_v2/strategy/portfolio_construction.py`
- tests for PC/MCV SHADOW comparator
- possibly report/schema docs after implementation acceptance

Avoid touching:

- Candidate / Opportunity producer;
- BQ producer;
- Entry producer except consuming existing fields;
- PM action semantics;
- Position Sizing authority;
- Runtime Planning / Pending / Ledger;
- SELL / profit retention;
- 5-ADD cap behavior;
- recent-exit guard behavior.

## Focused Test Specification

`FOCUSED_TEST_SPEC_COMPLETE`: YES.

Future tests must prove:

1. same input deterministic;
2. run-age invariant;
3. strong BUY_NEW preserved as visible strong option;
4. strong BUY_ADD visible without label bonus;
5. blocked ADD not revived;
6. Cash valid option represented;
7. no Cash blanket dominance;
8. rank not hard gate;
9. deep-rank strong-current-evidence remains representable;
10. no double counting of rank/BQ/Entry shared lineage;
11. G129 untouched;
12. EW/EZ recent-exit/REENTRY removal untouched;
13. PS/Runtime receive no SHADOW consumer authority;
14. `future_information_used=false`;
15. `authoritative_consumer_count=0`;
16. hard-risk / CA / broker / lot / cap block remains block;
17. source/date/run binding mismatch produces insufficient/unresolved, not acceptance;
18. Problem Cases emit diagnostic divergence classes.

## Pre-Implementation Go / No-Go

- `SHADOW_SPEC_COMPLETE`: YES
- `EVIDENCE_GROUPING_SAFE`: YES
- `DOUBLE_COUNTING_RESOLVED`: YES_BY_SPEC
- `ACTION_SPECIFIC_SEMANTICS_PRESERVED`: YES
- `HARD_ELIGIBILITY_PRESERVED`: YES
- `GOLDEN_EXPECTATIONS_COMPLETE`: YES
- `PROBLEM_CASE_EXPECTATIONS_COMPLETE`: YES
- `RUN_AGE_INVARIANT`: YES
- `SHADOW_IMPLEMENTATION_SAFE_TO_START`: YES
- `PRODUCTION_IMPLEMENTATION_READY`: NO

## Required Answer Summary

- `SHADOW_INPUT_CONTRACT_COMPLETE`: `YES`
- `EVIDENCE_PROVENANCE_COMPLETE`: `YES`
- `EVIDENCE_GROUPING_COMPLETE`: `YES`
- `DOUBLE_COUNTING_RISK_RESOLVED_BY_SPEC`: `YES`
- `SINGLE_SCORE_AVOIDED`: `YES`
- `ACTION_SPECIFIC_SEMANTICS_PRESERVED`: `YES`
- `BUY_NEW_BONUS_AVOIDED`: `YES`
- `ADD_LABEL_BONUS_AVOIDED`: `YES`
- `CASH_DEFAULT_WINNER_AVOIDED`: `YES`
- `RANK_HARD_GATE_AVOIDED`: `YES`
- `HARD_BLOCK_VISIBILITY_WITHOUT_REVIVAL_FEASIBLE`: `YES`
- `FIVE_ADD_CAP_BYPASS_AVOIDED`: `YES`
- `UNRESOLVED_COMPARISON_SUPPORTED`: `YES`
- `FALSE_PRECISION_RISK_AVOIDED`: `YES`
- `GOLDEN_CASE_EXPECTED_OUTPUT_COMPLETE`: `YES`
- `PROBLEM_CASE_EXPECTED_OUTPUT_COMPLETE`: `YES`
- `SHADOW_DIVERGENCE_CLASSES_COMPLETE`: `YES`
- `SHADOW_ARTIFACT_BOUNDED`: `YES`
- `SHADOW_COMPARATOR_RUN_AGE_INVARIANT_BY_DESIGN`: `YES`
- `SOURCE_DATE_AUTHORITY_DEFINED`: `YES`
- `SHADOW_STOP_CONDITIONS_COMPLETE`: `YES`
- `SHADOW_ACCEPTANCE_METRICS_COMPLETE`: `YES`
- `ZERO_TOLERANCE_REGRESSION_METRICS_DEFINED`: `YES`
- `FUTURE_SHADOW_IMPLEMENTATION_SURFACE_MINIMAL`: `YES`
- `FOCUSED_TEST_SPEC_COMPLETE`: `YES`
- `SHADOW_SPEC_COMPLETE`: `YES`
- `SHADOW_IMPLEMENTATION_SAFE_TO_START`: `YES`
- `PRODUCTION_IMPLEMENTATION_READY`: `NO`

PRODUCTION_CHANGED: NO
SHADOW_IMPLEMENTED: NO
SOURCE_CHANGED: NO
CONFIG_CHANGED: NO
SCHEMA_CHANGED: NO
TARGET_RUN_MUTATED: NO
RUNTIME_STATE_MUTATED: NO
FRESH_RUN_EXECUTED: NO
RESUME_REPLAY_RECOVER_EXECUTED: NO
FUTURE_OUTCOME_USED_FOR_PRODUCTION_JUDGMENT: NO

Final Judgment: `PHASE32_FS_NEXT_CAPITAL_UNIT_SHADOW_COMPARATOR_SPEC_COMPLETE_IMPLEMENTATION_SAFE_TO_START_PRODUCTION_NOT_READY`
