# Phase31-G73 — Focused ADD Zero-Delta Semantic Audit

## PRIMARY_JUDGMENT

PHASE31_G73_ADD_ZERO_DELTA_ROOT_CAUSE_CONFIRMED

The three audited ADD zero-delta cases were resolved from existing artifacts only.
No run was stopped or modified. No fresh-run, resume, replay, or Historical
execution was performed.

## Scope

TARGET_RUN_ID =
`runtime-test-historical-extended-smoke-20260823T140946562431Z`

RUN_STATUS_AT_SNAPSHOT = RUNNING

RUN_NEXT_JOB_AT_SNAPSHOT = `2023-07-13:submit`

Audited cases:

| Date | Symbol |
|---|---:|
| 2022-10-21 | 94320 |
| 2022-11-10 | 99840 |
| 2023-06-20 | 40520 |

Primary evidence:

- `reports/runtime_tests/runs/runtime-test-historical-extended-smoke-20260823T140946562431Z/daily/<date>/strategy/position_management.json`
- `reports/runtime_tests/runs/runtime-test-historical-extended-smoke-20260823T140946562431Z/daily/<date>/strategy/portfolio_construction.json`
- `reports/runtime_tests/runs/runtime-test-historical-extended-smoke-20260823T140946562431Z/daily/<date>/strategy/position_sizing.json`
- `reports/runtime_tests/runs/runtime-test-historical-extended-smoke-20260823T140946562431Z/daily/<date>/strategy/runtime_planning.json`
- `reports/runtime_tests/runs/runtime-test-historical-extended-smoke-20260823T140946562431Z/daily/<date>/morning/planning_evidence.json`

Code boundary evidence:

- `src/ai_fund_lab_v2/strategy/portfolio_construction.py`
  - `_resolve_canonical_add_allocation_bridge()` is invoked when target weight
    is materialized for PC members.
  - It consumes `strategy_intelligence_add_worthiness_state`,
    `entry_admission_action`, and `entry_admission_state` as ADD increment
    eligibility conditions.
  - It requires `add_worthiness_allows_increment`,
    `entry_admission_allows_increment`, and `add_increment_request > 0` before
    target weight can increase.
- `src/ai_fund_lab_v2/strategy/add_investment_evidence.py`
  - `add_investment_evidence.v1` produces campaign continuation, expected edge,
    incremental value, opportunity cost, and no-loss averaging evidence.

## Executive Conclusion

94320 and 99840 are the same root cause class:

ADD evidence itself passed, and same-date opportunity cost showed the ADD score
above the best NEW_BUY score. The first zeroization occurred inside
`CANONICAL_ADD_ALLOCATION_BRIDGE_AUTHORITY`, because PC target-weight
materialization used Strategy Intelligence entry/add-worthiness fields as hard
ADD increment gates:

- `strategy_intelligence_add_worthiness_state = NO_ADD`
- `entry_admission_action = NO_ADD`
- `entry_admission_state = OVERHEATED_DECELERATING_ENTRY`

Those fields were generated from decision-time evidence, but their source
contract says the Strategy Intelligence interpretation is not action authority.
The PC bridge nevertheless consumed them as ADD target-weight authority. That is
the focused semantic boundary.

40520 is a different class:

The same SI entry/add-worthiness gates also fail, but incremental value was not
positive. Same-date ADD expected edge weakened from `0.15523374` on
2023-06-19 to `0.15478216` on 2023-06-20, so
`add_investment_evidence.v1` produced `ADD_EXPECTED_EDGE_WEAKENING` and
`ADD_INCREMENTAL_VALUE_UNKNOWN`. That part is not missing evidence; it is the
producer's fail-closed expected-edge cascade.

PS and Runtime did not introduce a new ADD defect. They consumed upstream
zero-delta correctly:

- Position Sizing canonical sizing evidence classified
  `NO_POSITIVE_QUANTITY_DELTA`.
- Runtime Planning mapped the current-position zero delta to `NO_ACTION`.

## Case Results

| Case | PM_ADD_INTENT | INCREMENTAL_VALUE_STATE | INCREMENTAL_VALUE_STATUS | OPPORTUNITY_COST_RESULT | ADD_SCORE | BEST_NEW_BUY_SCORE | PROPOSED_INCREMENTAL_TARGET_WEIGHT | PC_ACCEPTED_WEIGHT | PS_QUANTITY_DELTA | RUNTIME_BUY_ADD | FIRST_ZEROIZATION_STAGE | ZEROIZATION_REASON |
|---|---|---|---|---|---:|---:|---:|---:|---:|---|---|---|
| 2022-10-21 94320 | YES | POSITIVE | PASS | PASS | 0.40629465 | 0.08364030 | 0.0 | 0.0 | 0 | NO | PC target-weight materialization / canonical ADD allocation bridge | `ADD_ENTRY_ADMISSION_NO_ADD`, `ADD_WORTHINESS_NO_ADD` |
| 2022-11-10 99840 | YES | POSITIVE | PASS | PASS | 0.21849110 | 0.17880795 | 0.0 | 0.0 | 0 | NO | PC target-weight materialization / canonical ADD allocation bridge | `ADD_ENTRY_ADMISSION_NO_ADD`, `ADD_WORTHINESS_NO_ADD` |
| 2023-06-20 40520 | YES | UNKNOWN | FAIL_CLOSED | PASS | 0.15478216 | 0.10296784 | 0.0 | 0.0 | 0 | NO | ADD incremental investment evidence, then PC target-weight materialization | `ADD_EXPECTED_EDGE_WEAKENING`, `ADD_INCREMENTAL_VALUE_UNKNOWN`, plus `ADD_ENTRY_ADMISSION_NO_ADD`, `ADD_WORTHINESS_NO_ADD` |

## Case A — 2022-10-21 / 94320

PM_ADD_INTENT = YES

PM evidence:

- PM action = `ADD`
- PM reason codes =
  `no_loss_averaging`, `opportunity_rank_still_high`,
  `strong_trend_continuation`

ADD investment evidence:

- producer = `phase28_d55_a_add_investment_evidence_resolver.v1`
- `producer_result_status = PASS`
- campaign continuation = `PASS`
- expected edge = `IMPROVING / PASS`
  - baseline date = `2022-10-20`
  - baseline score = `0.35367951`
  - current date = `2022-10-21`
  - current score = `0.40629465`
- incremental value = `POSITIVE / PASS`
- opportunity cost = `PASS`
  - ADD score = `0.40629465`
  - best NEW_BUY score = `0.08364030`
- no-loss averaging = `PASS`

PC target materialization:

- current_weight = `0.046884`
- base_weight = `0.031724`
- quality_action = `REDUCED_ALLOCATION_ONLY`
- final target_weight = `0.046884`
- requested_incremental_weight = `0.0`
- accepted_incremental_weight = `0.0`
- `add_allocation_eligibility_status = FAIL_CLOSED`
- `zero_weight_reason = ADD_TARGET_WEIGHT_UNCHANGED`
- bridge eligibility checks:
  - `pm_add = PASS`
  - `expected_edge_improvement = PASS`
  - `incremental_investment_value = PASS`
  - `opportunity_cost = PASS`
  - `campaign_continuation = PASS`
  - `no_loss_averaging = PASS`
  - `concentration = PASS`
  - `capital_availability = PASS`
  - `execution_feasibility = PASS`
  - `add_worthiness = FAIL_CLOSED`
  - `entry_admission = FAIL_CLOSED`

Strategy Intelligence fields consumed by PC:

- `strategy_intelligence_add_worthiness_state = NO_ADD`
- `entry_admission_action = NO_ADD`
- `entry_admission_state = OVERHEATED_DECELERATING_ENTRY`
- entry admission reason =
  `strong_trend_short_reversal_decelerating_risk_interaction`
- entry evidence uses same-date PIT inputs and reports
  `future_information_used = false`

Capital competition / PC deployment:

- ADD competitor status = `COMPETITOR_REJECTED_RECONSIDERABLE`
- canonical ADD competitor:
  - `eligibility_state = FAIL_CLOSED`
  - `proposed_incremental_target_weight = 0.0`
  - `accepted_incremental_weight = 0.0`
  - reason codes =
    `ADD_INSUFFICIENT_EVIDENCE`, `ADD_LOST_TO_NEW_BUY`,
    `ADD_NO_POSITIVE_DELTA`

The `ADD_LOST_TO_NEW_BUY` code is downstream classification noise for this
case. The ADD score was higher than the best NEW_BUY score. The actual first
zeroization was already present before capital competition as
`requested_incremental_weight = 0.0`.

PS / Runtime:

- Position Sizing canonical sizing evidence:
  - `evidence_class = NO_POSITIVE_QUANTITY_DELTA`
  - `requested_weight = 0.0`
  - `quantity_delta = 0`
  - `executable_quantity = 0`
- Runtime plan:
  - `planning_intent = NO_ACTION`
  - `planned_quantity = 0`
  - reason codes =
    `current_position_membership_resolved:current_portfolio_member`,
    `current_position_zero_delta_maps_to_no_action`

Case A direct cause:

TARGET_WEIGHT_MATERIALIZATION_DEFECT at PC ADD allocation bridge. Positive ADD
investment evidence did not become a positive target increment because SI
entry/add-worthiness fields were treated as hard ADD increment authority.

## Case B — 2022-11-10 / 99840

PM_ADD_INTENT = YES

PM evidence:

- PM action = `ADD`
- PM reason codes =
  `no_loss_averaging`, `opportunity_rank_still_high`,
  `strong_trend_continuation`

ADD investment evidence:

- producer = `phase28_d55_a_add_investment_evidence_resolver.v1`
- `producer_result_status = PASS`
- campaign continuation = `PASS`
- expected edge = `IMPROVING / PASS`
  - baseline date = `2022-11-09`
  - baseline score = `0.21049026`
  - current date = `2022-11-10`
  - current score = `0.21849110`
- incremental value = `POSITIVE / PASS`
- opportunity cost = `PASS`
  - ADD score = `0.21849110`
  - best NEW_BUY score = `0.17880795`
- no-loss averaging = `PASS`

PC target materialization:

- current_weight = `0.157211`
- base_weight = `0.029412`
- quality_action = `REDUCED_ALLOCATION_ONLY`
- final target_weight = `0.157211`
- requested_incremental_weight = `0.0`
- accepted_incremental_weight = `0.0`
- `add_allocation_eligibility_status = FAIL_CLOSED`
- `zero_weight_reason = ADD_TARGET_WEIGHT_UNCHANGED`
- bridge eligibility checks:
  - `pm_add = PASS`
  - `expected_edge_improvement = PASS`
  - `incremental_investment_value = PASS`
  - `opportunity_cost = PASS`
  - `campaign_continuation = PASS`
  - `no_loss_averaging = PASS`
  - `concentration = PASS`
  - `capital_availability = PASS`
  - `execution_feasibility = PASS`
  - `add_worthiness = FAIL_CLOSED`
  - `entry_admission = FAIL_CLOSED`

Strategy Intelligence fields consumed by PC:

- `strategy_intelligence_add_worthiness_state = NO_ADD`
- `entry_admission_action = NO_ADD`
- `entry_admission_state = OVERHEATED_DECELERATING_ENTRY`
- entry admission reason =
  `strong_trend_short_reversal_decelerating_risk_interaction`
- entry evidence uses same-date PIT inputs and reports
  `future_information_used = false`

Capital competition / PC deployment:

- ADD competitor status = `COMPETITOR_REJECTED_RECONSIDERABLE`
- canonical ADD competitor:
  - `eligibility_state = FAIL_CLOSED`
  - `proposed_incremental_target_weight = 0.0`
  - `accepted_incremental_weight = 0.0`
  - reason codes =
    `ADD_INSUFFICIENT_EVIDENCE`, `ADD_LOST_TO_NEW_BUY`,
    `ADD_NO_POSITIVE_DELTA`

As with 94320, `ADD_LOST_TO_NEW_BUY` is not the first cause. Same-date
opportunity cost says the ADD candidate beat best NEW_BUY. The ADD was already
zero before competition via target-weight materialization.

PS / Runtime:

- Position Sizing canonical sizing evidence:
  - `evidence_class = NO_POSITIVE_QUANTITY_DELTA`
  - `requested_weight = 0.0`
  - `quantity_delta = 0`
  - `executable_quantity = 0`
- Runtime plan:
  - `planning_intent = NO_ACTION`
  - `planned_quantity = 0`
  - reason codes =
    `current_position_membership_resolved:current_portfolio_member`,
    `current_position_zero_delta_maps_to_no_action`

Case B direct cause:

Same as Case A. TARGET_WEIGHT_MATERIALIZATION_DEFECT at PC ADD allocation bridge.

## Case C — 2023-06-20 / 40520

PM_ADD_INTENT = YES

PM evidence:

- PM action = `ADD`
- PM reason codes =
  `no_loss_averaging`, `opportunity_rank_still_high`,
  `strong_trend_continuation`

ADD investment evidence:

- producer = `phase28_d55_a_add_investment_evidence_resolver.v1`
- `producer_result_status = REVIEW_REQUIRED`
- campaign continuation = `PASS`
- expected edge = `WEAKENING / FAIL_CLOSED`
  - baseline date = `2023-06-19`
  - baseline score = `0.15523374`
  - current date = `2023-06-20`
  - current score = `0.15478216`
  - reason code = `ADD_EXPECTED_EDGE_WEAKENING`
- incremental value = `UNKNOWN / FAIL_CLOSED`
  - authority = `existing_pc_expected_edge_cascade_contract`
  - reason code = `ADD_INCREMENTAL_VALUE_UNKNOWN`
- opportunity cost = `PASS`
  - ADD score = `0.15478216`
  - best NEW_BUY score = `0.10296784`
- no-loss averaging = `PASS`

The same-date inputs needed for expected-edge comparison existed and were
temporally valid. The UNKNOWN incremental value was not caused by missing
baseline evidence; it was produced because the expected-edge comparison failed
closed on weakening.

PC target materialization:

- current_weight = `0.087036`
- base_weight = `0.034483`
- quality_action = `FULL_ALLOCATION_ELIGIBLE`
- final target_weight = `0.087036`
- requested_incremental_weight = `0.0`
- accepted_incremental_weight = `0.0`
- `add_allocation_eligibility_status = FAIL_CLOSED`
- `zero_weight_reason = ADD_TARGET_WEIGHT_UNCHANGED`
- bridge eligibility checks:
  - `pm_add = PASS`
  - `expected_edge_improvement = FAIL_CLOSED`
  - `incremental_investment_value = FAIL_CLOSED`
  - `opportunity_cost = PASS`
  - `campaign_continuation = PASS`
  - `no_loss_averaging = PASS`
  - `concentration = PASS`
  - `capital_availability = PASS`
  - `execution_feasibility = PASS`
  - `add_worthiness = FAIL_CLOSED`
  - `entry_admission = FAIL_CLOSED`

Strategy Intelligence fields consumed by PC:

- `strategy_intelligence_add_worthiness_state = NO_ADD`
- `entry_admission_action = NO_ADD`
- `entry_admission_state = OVERHEATED_DECELERATING_ENTRY`
- entry admission reason =
  `strong_trend_short_reversal_decelerating_risk_interaction`
- entry evidence uses same-date PIT inputs and reports
  `future_information_used = false`

Capital competition / PC deployment:

- ADD competitor status = `COMPETITOR_REJECTED_RECONSIDERABLE`
- canonical ADD competitor:
  - `eligibility_state = FAIL_CLOSED`
  - `proposed_incremental_target_weight = 0.0`
  - `accepted_incremental_weight = 0.0`
  - reason codes =
    `ADD_INSUFFICIENT_EVIDENCE`, `ADD_LOST_TO_NEW_BUY`,
    `ADD_NO_POSITIVE_DELTA`

PS / Runtime:

- Position Sizing canonical sizing evidence:
  - `evidence_class = NO_POSITIVE_QUANTITY_DELTA`
  - `requested_weight = 0.0`
  - `quantity_delta = 0`
  - `executable_quantity = 0`
- Runtime plan:
  - `planning_intent = NO_ACTION`
  - `planned_quantity = 0`
  - reason codes =
    `current_position_membership_resolved:current_portfolio_member`,
    `current_position_zero_delta_maps_to_no_action`

Case C direct cause:

First cause is ADD incremental investment evidence fail-closed due to
same-campaign expected-edge weakening. A second independent blocker is the same
PC consumption of SI `NO_ADD` / overheated-decelerating entry fields as hard ADD
increment gates.

## Mandatory Questions

### 1. Did PM explicitly issue ADD authority?

YES for all three cases.

All three PM rows carry action `ADD` and PM reason codes:

- `no_loss_averaging`
- `opportunity_rank_still_high`
- `strong_trend_continuation`

### 2. What is the incremental investment value producer?

`add_investment_evidence.v1`, producer version
`phase28_d55_a_add_investment_evidence_resolver.v1`.

It is embedded in each PC member under `add_investment_evidence` and consumed by
the PC `CANONICAL_ADD_ALLOCATION_BRIDGE_AUTHORITY`.

### 3. Did required same-date inputs exist?

94320 and 99840: YES.

- Same-campaign baseline score existed.
- Current runtime opportunity score existed.
- Baseline business date was before the current business date.
- Campaign identity matched.
- PM no-loss evidence existed.
- Opportunity-cost comparison had same-date NEW_BUY comparator scores.

40520: YES for the expected-edge comparison inputs.

The inputs existed and produced a weakening classification. Therefore the
incremental UNKNOWN was not a data-missing result; it was fail-closed semantics
from expected-edge weakening.

### 4. What does opportunity-cost PASS mean?

Opportunity-cost PASS means that, within the same-date PC member set, the ADD
candidate's `runtime_opportunity_score` was not inferior to the best NEW_BUY
score.

It is a relative capital competition comparison. It does not by itself grant a
positive target-weight increment. Incremental value is a separate responsibility
that depends on expected-edge/campaign/no-loss/opportunity-cost evidence.

### 5. Who owns proposed_incremental_target_weight?

PORTFOLIO_CONSTRUCTION owns it.

The concrete value is emitted in the PC canonical ADD competitor evidence:
`portfolio_construction.add_capital_competitor.v1`.

The value originates from PC target-weight materialization:

`_resolve_canonical_add_allocation_bridge()`
→ member `requested_incremental_weight`
→ lot-aware final reallocation request
→ canonical ADD competitor `proposed_incremental_target_weight`.

### 6. Where did positive evidence first become zero?

94320 / 99840:

`CANONICAL_ADD_ALLOCATION_BRIDGE_AUTHORITY`, at PC target-weight materialization.

40520:

`add_investment_evidence.v1` first failed incremental value due to expected-edge
weakening, then PC target-weight materialization preserved zero.

### 7. What zeroization class applies?

94320 / 99840:

TARGET_WEIGHT_MATERIALIZATION_DEFECT / evidence authority gap.

Positive ADD evidence and opportunity-cost PASS were overridden by SI
entry/add-worthiness fields that are not the ADD target-weight authority.

40520:

Intended fail-closed incremental evidence for expected-edge weakening, plus the
same target-weight materialization authority gap.

Not primary causes for the three rows:

- cap / concentration = NO
- lot / residual = NO
- NEW_BUY competition = NO as first cause
- missing evidence = NO for the audited required expected-edge inputs

### 8. Did PS / Runtime create a downstream issue?

NO.

PS saw `requested_weight = 0.0` and emitted
`NO_POSITIVE_QUANTITY_DELTA`. Runtime then emitted `NO_ACTION` with
`current_position_zero_delta_maps_to_no_action`.

## Cross-Case Contract Audit

SAME_ROOT_CAUSE_FOR_94320_99840 = YES

94320 and 99840 share the same direct cause:

1. PM ADD intent exists.
2. ADD investment evidence is PASS.
3. Opportunity-cost evidence says ADD score exceeds best NEW_BUY score.
4. PC ADD target-weight bridge fails on `ADD_WORTHINESS_NO_ADD` and
   `ADD_ENTRY_ADMISSION_NO_ADD`.
5. The requested increment becomes `0.0`.

40520_DIFFERENT_FAILURE_CLASS = YES

40520 additionally has a legitimate same-date expected-edge weakening:

- current score `0.15478216`
- baseline score `0.15523374`
- result `WEAKENING / FAIL_CLOSED`

ADD_SPECIFIC_BUSINESS_RULE_UNFAIRLY_STRICT = PARTIAL

There is evidence of an ADD-specific strictness/authority problem for 94320 and
99840, because a Strategy Intelligence interpretation field that is documented
as not action authority became a hard ADD increment blocker. This is not a
NEW_BUY-vs-ADD score issue in those cases.

POSITIVE_INCREMENTAL_VALUE_TO_TARGET_WEIGHT_CONTRACT_EXISTS = PARTIAL

The code has a canonical ADD allocation bridge that can convert positive ADD
evidence into a target increment, but the contract also requires SI
add-worthiness and entry-admission fields. The artifact does not show a clean
contract explaining why `add_investment_evidence.final_add_eligibility = PASS`
plus opportunity-cost PASS must still become zero when SI entry admission says
`NO_ADD`.

EVIDENCE_PRODUCER_TARGET_WEIGHT_OWNER_AUTHORITY_GAP = YES

`add_investment_evidence.v1` says ADD is eligible for 94320/99840, while PC
target-weight owner says not eligible because of separate SI entry/add-worthiness
fields. The boundary is inside PC, not in PM, PS, or Runtime.

## Required Output

ADD_ZERO_DELTA_ROOT_CAUSE =
`PC_ADD_TARGET_WEIGHT_MATERIALIZATION_CONSUMES_SI_NO_ADD_AS_HARD_ADD_INCREMENT_GATE_FOR_PASS_ADD_EVIDENCE`

ADD_SEMANTIC_BIAS_CONFIRMED = PARTIAL

TARGET_WEIGHT_MATERIALIZATION_DEFECT = YES

EVIDENCE_PROPAGATION_GAP = YES

INCREMENTAL_VALUE_PRODUCER_DEFECT = NO

CAP_OR_RESIDUAL_CAUSE = NO

LOT_CAUSE = NO

NEW_BUY_COMPETITION_CAUSE = NO

PS_RUNTIME_CONNECTIVITY_ISSUE = NO

REPAIR_REQUIRED = YES

## Acceptance

CODE_CHANGED = NO

CONFIG_CHANGED = NO

RUN_MODIFIED = NO

FRESH_RUN_EXECUTED = NO

RESUME_EXECUTED = NO

REPLAY_EXECUTED = NO

LONG_HISTORICAL_EXECUTED = NO

MARKET_QUALITY_CHANGED = NO

RISK_PACING_CHANGED = NO

PM_ADD_THRESHOLD_CHANGED = NO

FUTURE_INPUT_COUNT = 0

HISTORICAL_OUTCOME_PARAMETER_SELECTION_COUNT = 0

## Highest-Value Next Action

Repair only the PC ADD target-weight materialization boundary:

`CANONICAL_ADD_ALLOCATION_BRIDGE_AUTHORITY`

The repair should clarify that PM ADD + canonical ADD investment evidence PASS
is the ADD increment action path, and Strategy Intelligence entry/admission
fields marked as interpretation/not-action authority must not hard-block ADD
target increment unless an explicit ADD authority contract says so.

Do not change Market Quality, Risk Pacing, PM ADD thresholds, Candidate ranking,
or PS/Runtime connectivity for this issue.
