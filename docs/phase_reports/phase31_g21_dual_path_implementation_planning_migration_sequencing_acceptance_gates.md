# Phase31-G21 - Dual-Path Implementation Planning / Migration Sequencing / Acceptance Gates

## Scope

Task type: DESIGN-ONLY IMPLEMENTATION PLANNING / MIGRATION SEQUENCING /
ACCEPTANCE CONTRACT.

G21 did not implement production code, change configuration, execute schema
migration, tune thresholds, tune parameters, run fresh Historical, resume,
replay, rerun Historical, or execute long Historical.

Normative target architecture:

- `docs/02_architecture/dual_path_market_quality_and_capital_competition_contract.md`

Supporting SoT / evidence:

- `docs/02_architecture/strategy_architecture_v1.md`
- `docs/02_architecture/portfolio_construction_and_position_sizing_contract.md`
- `docs/02_architecture/adaptive_buy_quality_authority.md`
- `docs/02_architecture/position_management_decision_trace_contract.md`
- `docs/02_architecture/runtime_submit_order_condition_authority_contract.md`
- `docs/phase_reports/phase31_g19_dual_path_design_preconditions_constraint_necessity_authority_audit.md`
- `docs/phase_reports/phase31_g20_dual_path_production_architecture_contract_design.md`

No contradiction requiring G20 canonical SoT amendment was found.

## Primary Judgment

```text
PRIMARY_JUDGMENT =
PHASE31_G21_STAGED_IMPLEMENTATION_PLAN_READY
```

The implementation program should proceed as staged, reviewable migration. The
first implementation slice should be Market Quality evidence-only
materialization with no Production behavior change.

## Fixed Architecture Invariants

The implementation plan must preserve:

```text
MARKET_REGIME_AUTHORITY_CHANGED = NO
SECOND_REGIME_CLASSIFIER_CREATED = NO
MARKET_DIRECTION_AND_MARKET_QUALITY_SEPARATED = YES
MARKET_QUALITY_OWNER = MARKET_CONTEXT
RISK_PACING_OWNER = PORTFOLIO_POLICY
CONSTRAINT_COMPOSITION_OWNER = PORTFOLIO_CONSTRUCTION
FINAL_NO_DEPLOYABLE_OPPORTUNITY_AUTHORITY =
PORTFOLIO_CONSTRUCTION_TARGET_PORTFOLIO_DECISION_AUTHORITY
DISCRETE_QUANTITY_OWNER = POSITION_SIZING
STRATEGY_SAFETY_CAP_SEPARATION_PRESERVED = YES
LOT_FIRST_CONTRACT_PRESERVED = YES
BUY_SELL_INDEPENDENCE_PRESERVED = YES
SELL_AUTHORITY_CHANGED = NO
SAFETY_AUTHORITY_CHANGED = NO
SUBMIT_AUTHORITY_CHANGED = NO
CASH_REMAINS_VALID_ALLOCATION = YES
PERMANENT_LEGACY_FALLBACK_ALLOWED = NO
NEW_DUPLICATE_AUTHORITY_COUNT = 0
```

## Current-State Dependency Graph

| Producer | Artifact / field / API | Consumer | Current authority | Target authority | Migration required | Breakage risk | Test required |
| --- | --- | --- | --- | --- | --- | --- | --- |
| J-Quants PIT data | daily quotes, listed info, calendar | Market Context, Candidate, features | PIT data | unchanged | NO | LOW | PIT freshness / no future data |
| Market Context | `strategy.market_context`, regime, metrics | Portfolio Policy, BUY Quality, PC, PM evidence | Market Context Evidence Authority | Direction + Market Quality evidence | YES | MEDIUM | direction unchanged; quality materialized |
| Market Regime | regime field | Strategy graph consumers | medium-horizon direction | unchanged | NO | LOW | no second regime |
| Candidate / Opportunity | ranking, `runtime_opportunity_score` | BUY Quality, PC | Candidate / Opportunity Evidence | unchanged evidence | NO | MEDIUM | no score reinterpretation |
| BUY Quality | `buy_quality_decision.v1` | PC, Runtime Planning | BUY quality authority | optional Market Quality consumer | YES, deferred | MEDIUM | weak opportunity not rescued |
| Portfolio Policy | portfolio policy artifact | PC | Portfolio posture | Risk Pacing producer plus existing posture | YES | MEDIUM | no fixed exposure/count |
| PM | PM decisions / ADD / HOLD / REDUCE / EXIT | PC, Sell Planning | Existing Position Intent Authority | unchanged; ADD competes downstream | NO for PM action; YES for ADD consumption | MEDIUM | SELL/ADD lineage |
| PC | target portfolio, target weights, ADD bridge, re-entry gates | Position Sizing, Runtime Planning | Target Portfolio Decision Authority | capital competition + composition authority | YES | HIGH | target authority, residual, re-entry, ADD |
| Position Sizing | target quantity, quantity delta, lot evidence | Runtime Planning, PC diagnostics | Quantity Candidate Authority | unchanged plus residual evidence API | YES | HIGH | no duplicate quantity decision |
| Re-entry gates | PC semantic gates / cooldown evidence | PC | Strategy semantic gate | explicit semantic API inside PC | YES | MEDIUM | no blanket ban/permission |
| ADD bridge | PM ADD -> PC accepted increment | PC, Sizing | Strategy increment bridge | capital competitor | YES | HIGH | ADD can win/lose |
| Safety | portfolio limits, safety decisions | Runtime / Submit | Safety Block / Review Authority | unchanged | NO | LOW | safety unchanged |
| Runtime Planning | planned intent / planned quantity | Strategy Planning Authority | pure mapper | unchanged | NO | MEDIUM | no strategy recomputation |
| Submit | pending/order submit pipeline | Broker / Ledger | Submit / broker feasibility | unchanged | NO | LOW | no implicit fallback |
| Execution | broker adapter result | Ledger / Current | Broker Execution Authority | unchanged | NO | LOW | side-effect integrity |

```text
CURRENT_DEPENDENCY_GRAPH_COMPLETE = PASS
```

## Target-State Dependency Graph

Target chain:

```text
J-Quants PIT
  -> Market Context Direction + Market Quality
  -> Portfolio Policy Risk Pacing
  -> Portfolio Construction NEW_BUY / ADD / CASH competition
  -> Position Sizing discrete quantity / lot feasibility
  -> PC residual reconsideration if applicable
  -> Runtime Planning
  -> Submit
  -> Execution
```

SELL / REDUCE / EXIT remains independently operable:

```text
PM SELL / REDUCE / EXIT
  -> Sell Planning / Runtime Planning
  -> Safety / Submit / Execution
```

```text
TARGET_DEPENDENCY_GRAPH_COMPLETE = PASS
TARGET_GRAPH_MATCHES_G20_SOT = YES
```

## Stage Order

The G20 dependency order is valid with one operational refinement: Stage 2
should initially materialize Risk Pacing in temporary non-authoritative shadow
mode before PC behavior consumes it authoritatively. This avoids a big-bang
Market Quality plus PC behavior change.

| Stage | Title | Purpose | Starts after | Behavior change |
| ---: | --- | --- | --- | --- |
| 1 | Market Quality evidence producer | Materialize quality state and reasons, no consumer behavior | G21 | NO |
| 2 | Risk Pacing shadow producer | Portfolio Policy materializes semantic intent, no PC behavior | Stage 1 | NO |
| 3 | PC capital competition framework | Introduce NEW_BUY / ADD / CASH abstraction and final no-deployable authority | Stage 2 accepted | YES, limited framework |
| 4 | Sizing residual evidence / PC reconsideration | Let PC consume residual evidence without quantity authority duplication | Stage 3 accepted | YES |
| 5 | Re-entry semantic API | Refactor PC re-entry gates into explicit semantic eligibility | Stage 4 accepted | YES |
| 6 | ADD capital competition | Connect ADD intent through PC competition to quantity delta | Stage 5 accepted | YES |
| 7 | Legacy consumer / fallback removal | Remove temporary shadow/compatibility paths and legacy decision surfaces | Stage 6 accepted | YES, cleanup |
| 8 | Integrated focused acceptance | Cross-component focused acceptance only | Stage 7 accepted | NO new behavior |
| 9 | User-operated fresh Historical validation | Validate behavior, not tune parameters | Stage 8 accepted | validation only |

```text
BIG_BANG_IMPLEMENTATION_REQUIRED = NO
```

## Stage 1 - Market Quality Producer Plan

Files / modules:

- `src/ai_fund_lab_v2/strategy/market_context.py`
- optional schema/config extension in `configs/strategy/market_context.json`
- tests under `tests/strategy/test_phase22_a_market_context.py` and
  `tests/strategy/test_phase22_l_market_context_resolution.py`

Inputs:

- existing 5D return
- existing 20D return
- existing 5D breadth
- existing 20D breadth
- existing volatility / downside-risk proxy
- existing confidence / uncertainty / coverage

Deferred inputs:

- short/medium disagreement if additional schema is needed
- transition path / days since transition
- transition churn
- sector participation

Outputs:

- `market_quality_state`
- `market_quality_reason_codes`
- `market_quality_evidence_completeness`
- `market_quality_component_evidence`
- `market_quality_as_of`

Missing state:

- `INSUFFICIENT_EVIDENCE`

Reason code families:

- `MARKET_QUALITY_HEALTHY`
- `MARKET_QUALITY_FRAGILE`
- `MARKET_STRUCTURE_CONFLICTED`
- `SHORT_TERM_PARTICIPATION_NARROWING`
- `RECOVERY_CONFIRMATION_INCOMPLETE`
- `MARKET_QUALITY_INSUFFICIENT_EVIDENCE`

Temporal requirements:

- input market date `<= business_date`
- explicit as-of
- no current-snapshot-only source for Historical
- no Paper Ledger, PnL, future return, fill outcome, or later campaign label

No-op migration strategy:

- materialize new fields as evidence-only
- existing consumers continue to read Market Direction and existing metrics
- no PC, BUY Quality, PM, Safety, Submit, or Execution behavior changes

Acceptance:

- Market Direction unchanged
- Market Quality materializes independently
- missing evidence -> `INSUFFICIENT_EVIDENCE`
- no implicit BULL / HEALTHY fallback
- future data impossible
- Historical-result feedback impossible
- no quantity / exposure decision produced

```text
STAGE1_MARKET_QUALITY_EVIDENCE_ONLY_FEASIBLE = YES
STAGE1_PRODUCTION_BEHAVIOR_CHANGE_REQUIRED = NO
STAGE1_INPUT_SCOPE =
EXISTING_5D_RETURN, EXISTING_20D_RETURN, EXISTING_5D_BREADTH,
EXISTING_20D_BREADTH, EXISTING_VOLATILITY_DOWNSIDE_RISK,
EXISTING_CONFIDENCE_COVERAGE
SECTOR_PARTICIPATION_INCLUDED_IN_INITIAL_IMPLEMENTATION = NO
```

Sector participation is deferred because G19 found lineage pass but semantics
not production-ready.

## Stage 2 - Risk Pacing Plan

Files / modules:

- `src/ai_fund_lab_v2/strategy/portfolio_policy.py`
- Portfolio Policy artifact writer / reader tests
- existing `tests/strategy/test_phase22_c_portfolio_policy.py`

Input:

- Market Direction
- Market Quality
- existing policy evidence

Output:

- `risk_pacing_intent`
- `risk_pacing_reason_codes`
- `risk_pacing_evidence_completeness`
- `risk_pacing_authority = PORTFOLIO_POLICY`

Initial transition strategy:

- materialize Risk Pacing without changing PC behavior
- mark as temporary non-authoritative shadow evidence
- remove shadow designation when Stage 3 consumes it authoritatively

Acceptance:

- semantic only
- no direct quantity calculation
- no direct exposure target
- no BUY count / position count
- SELL unaffected
- Safety unchanged
- missing Market Quality cannot become `NORMAL_DEPLOYMENT`

```text
STAGE2_RISK_PACING_BEHAVIORAL_CHANGE = NO
STAGE2_ACCEPTANCE_GATE_DEFINED = YES
TEMPORARY_NON_AUTHORITATIVE_SHADOW_ALLOWED = YES
PERMANENT_SHADOW_PATH_ALLOWED = NO
SHADOW_REMOVAL_STAGE = STAGE7_LEGACY_CONSUMER_FALLBACK_REMOVAL
```

## Stage 3 - PC Capital Competition Framework Plan

Files / modules:

- `src/ai_fund_lab_v2/strategy/portfolio_construction.py`
- `tests/strategy/test_phase22_e_portfolio_construction.py`
- relevant Phase29/30 PC regression tests

Framework:

- canonical competitor kinds: `NEW_BUY`, `ADD`, `CASH_OPTIONALITY`
- PC owns eligibility integration, competition ordering, blocked reasons,
  residual cash reason, and final no-deployable judgment
- Position Sizing keeps quantity authority
- downstream Runtime Planning receives already-decided quantity candidates only

Stage 3 should establish the abstraction and current NEW_BUY/CASH competition
without fully changing ADD semantics. ADD can enter as a typed placeholder until
Stage 6.

```text
PC_COMPETITOR_FRAMEWORK_STAGE_DEFINED = YES
PC_FINAL_NO_DEPLOYABLE_AUTHORITY_MIGRATION_REQUIRED = YES
```

## Constraint Migration Matrix

| Constraint | Current location | Target location | Action | Authority owner | Consumer | Migration stage | Temporary compatibility | Final removal stage |
| --- | --- | --- | --- | --- | --- | ---: | --- | ---: |
| strategy position cap / dynamic count | Portfolio Policy / PC config | Portfolio Policy -> PC competition | MIGRATE | Portfolio Policy / PC | PC | 3 | YES | 7 |
| safety hard position cap | Safety config, currently removed/null | Safety | KEEP | Safety | Runtime / Submit / PC as boundary evidence | n/a | NO | n/a |
| strategy single-name cap | Portfolio Policy / Sizing / PC | Portfolio Policy / PC target, Sizing consumer | KEEP | Portfolio Policy / PC | Sizing | 3 | NO | n/a |
| safety hard single-name cap | Safety | Safety boundary | KEEP | Safety | Sizing / Submit / Safety | n/a | NO | n/a |
| lot feasibility | Position Sizing / PC lot-aware bridge | Position Sizing evidence, PC reconsideration | MIGRATE | Position Sizing for quantity; PC for competitor loop | PC / Runtime Planning | 4 | YES | 7 |
| residual capital | PC/Sizing reason evidence | PC residual classes | MIGRATE | PC | PC / reports | 4 | YES | 7 |
| cash policy / reserve | Portfolio Policy / PC | Risk Pacing + PC Cash competitor | MIGRATE | Portfolio Policy / PC | PC | 3 | YES | 7 |
| re-entry | PC semantic gates / cooldown config | PC semantic eligibility API | MIGRATE | PC | PC / Sizing | 5 | YES | 7 |
| ADD | PM ADD + PC bridge | PC capital competitor | MIGRATE | PM intent; PC competitiveness | PC / Sizing | 6 | YES | 7 |
| candidate competition | Opportunity / BUY Quality -> PC | PC competitor framework | KEEP/MIGRATE | PC | Sizing | 3 | YES | 7 |
| replacement after SELL | cash/current after execution -> PC | PC competition and residual classes | MIGRATE | PC | PC / reports | 3-4 | YES | 7 |

```text
CONSTRAINT_MIGRATION_MATRIX_COMPLETE = PASS
```

## Stage 4 - Position Sizing / Residual Evidence Plan

Files / modules:

- `src/ai_fund_lab_v2/strategy/position_sizing.py`
- `src/ai_fund_lab_v2/strategy/position_sizing_plan.py`
- `src/ai_fund_lab_v2/runtime_v2/position_sizing_authority.py`
- `tests/strategy/test_phase22_j_position_sizing.py`
- `tests/strategy/test_phase30_s_position_sizing_production_handoff.py`
- `tests/runtime_v2/test_phase26_step4_position_sizing_authority.py`

Position Sizing exposes:

- executable quantity
- minimum lot failure
- residual amount
- strategy-cap-bound evidence
- safety-bound evidence when applicable
- unallocatable lot residual

Position Sizing must not:

- choose the next candidate
- recreate Portfolio Policy
- decide Cash vs BUY
- reinterpret PC membership

PC alone decides whether residual capital triggers another competitor.

```text
POSITION_SIZING_AUTHORITY_CHANGED = NO
RESIDUAL_EVIDENCE_API_REQUIRED = YES
PC_RESIDUAL_RECONSIDERATION_LOOP_REQUIRED = YES
```

Residual loop invariants:

- deterministic ordering
- finite competitor set
- max one terminal disposition per competitor
- no duplicate candidate
- no duplicate order
- no cap bypass
- no Safety bypass
- no cash double-use
- no Strategy membership expansion outside PC
- terminal `NO_VALID_COMPETITOR`

```text
RESIDUAL_LOOP_TERMINATION_PROOF_REQUIRED = YES
RESIDUAL_LOOP_DUPLICATE_EXECUTION_RISK = NO
```

## Stage 5 - Re-entry Migration Plan

Current gate inventory:

- same-symbol prior EXIT identity
- re-entry / non-re-entry distinction
- cooldown status
- renewed opportunity qualification
- BUY Quality requalification
- corporate-action status
- capacity / liquidity
- prior exit reason class
- repeated churn evidence
- technical recovery

Target API:

- `reentry_identity`
- `prior_exit_context`
- `churn_protection_status`
- `renewed_current_evidence_status`
- `market_quality_context`
- `candidate_eligibility_status`
- `safety_restriction_status`
- `reentry_semantic_state`
- `reentry_reason_codes`

No numeric cooldown change is required for the initial migration; existing
parameters are carried as existing evidence until a later authorized tuning task
exists.

```text
REENTRY_CURRENT_GATE_INVENTORY_COMPLETE = YES
REENTRY_TARGET_SEMANTIC_API_DEFINED = YES
REENTRY_NUMERIC_PARAMETER_CHANGE_REQUIRED_FOR_INITIAL_MIGRATION = NO
REENTRY_ACCEPTANCE_GATE_DEFINED = YES
```

Acceptance:

- no blanket ban
- no blanket permission
- same-symbol renewed evidence path
- churn protection path
- no future outcome
- no later PnL
- no hidden global replacement lockout
- BUY/SELL independence

## Stage 6 - ADD Capital Competition Plan

| Pipeline step | Current producer | Target owner | Schema / API | Implementation stage | Test |
| --- | --- | --- | --- | ---: | --- |
| `ADD_INTENT` | PM / `position_management.py` | PM | PM decision artifact | existing | PM ADD intent lineage |
| `ADD_ELIGIBILITY` | PC ADD bridge | PC | competitor eligibility status | 6 | eligible/ineligible ADD |
| `ADD_INCREMENTAL_INVESTMENT_VALUE` | PC bridge evidence, partial | PC | incremental value class + reasons | 6 | no future PnL; can pass/fail |
| `ADD_OPPORTUNITY_COST` | PC bridge evidence, partial | PC | opportunity cost class + competitor reference | 6 | ADD can lose to NEW_BUY/CASH |
| `ADD_TARGET_WEIGHT_CHANGE` | PC target portfolio | PC | target weight delta | 6 | ADD can produce positive target delta |
| `ADD_DISCRETE_QUANTITY_DELTA` | Position Sizing | Position Sizing | quantity delta | 6 | positive delta and zero terminal |
| `ADD_SUBMIT` | Runtime Planning / Submit | Runtime Planning / Submit | pending / submit item | existing consumer | existing submit tests |

```text
ADD_MIGRATION_GAP_MATRIX_COMPLETE = PASS
ADD_INCREMENTAL_VALUE_AUTHORITY = PORTFOLIO_CONSTRUCTION
ADD_OPPORTUNITY_COST_AUTHORITY = PORTFOLIO_CONSTRUCTION
INITIAL_ADD_SCOPE = CONNECTIVITY_AND_AUTHORITY_ONLY
NEW_ADD_ALPHA_FEATURE_REQUIRED = NO
```

No outcome-trained ADD score is introduced. Existing positions do not receive
automatic priority over NEW BUY.

## BUY Quality, SELL / PM, Safety / Submit / Execution Surfaces

BUY Quality:

- deferred consumer migration
- may consume Market Quality as evidence after Stage 2/3
- must not rescue weak opportunity
- must not become duplicate BUY authority
- no fixed G18/G19-derived threshold

```text
BUY_QUALITY_MIGRATION_PRIORITY = DEFERRED
```

SELL / PM:

```text
SELL_IMPLEMENTATION_CHANGE_REQUIRED = NO
PM_IMPLEMENTATION_CHANGE_REQUIRED = NO
```

PM ADD intent already exists; Stage 6 changes downstream ADD consumption, not
PM action authority or winner-retention semantics.

Safety / Submit / Execution:

```text
SAFETY_LOGIC_CHANGE_REQUIRED = NO
SUBMIT_LOGIC_CHANGE_REQUIRED = NO
EXECUTION_LOGIC_CHANGE_REQUIRED = NO
```

Any schema plumbing needed downstream must be non-authoritative consumer
adaptation only.

## Artifact / Schema Migration Plan

| Artifact | Current schema | Target fields | Backward compatibility | Stage | Reader updates | Writer updates | Missing field behavior |
| --- | --- | --- | --- | ---: | --- | --- | --- |
| `market_context.v1` / `strategy.market_context` | direction + metrics | `market_quality_state`, reasons, completeness, components, as-of | old readers ignore fields | 1 | Portfolio Policy later | Market Context | `INSUFFICIENT_EVIDENCE`, no healthy fallback |
| Portfolio Policy artifact | posture / exposure fields | `risk_pacing_intent`, reasons, completeness | shadow until Stage 3 | 2 | PC later | Portfolio Policy | not `NORMAL_DEPLOYMENT` |
| PC target / allocation artifact | target weights, reasons | competitor records, final no-deployable state, residual cash class | compatibility fields retained until Stage 7 | 3-4 | Sizing / Runtime Planning | PC | REVIEW / no-deployable explicit |
| Position Sizing evidence | quantity, lot reasons | residual evidence API and lot failure classes | old runtime quantity fields preserved | 4 | PC / Runtime Planning | Sizing | no quantity fabrication |
| Re-entry evidence | PC reasons / cooldown status | semantic re-entry API | existing reasons mapped | 5 | PC / reports | PC | fail closed |
| ADD bridge evidence | PM ADD / PC accepted increment | ADD competitor path fields | compatibility until Stage 7 | 6 | PC / Sizing | PC | ADD loses / no positive delta |
| reason codes | component-local reasons | canonical families from G20 | aliases allowed temporarily | 1-7 | reports / tests | all producers | unknown preserved, not remapped silently |
| residual Cash classification | scattered reasons | residual classes | compatibility until Stage 7 | 4 | reports / PC | PC / Sizing | explicit unresolved / no valid competitor |

```text
SCHEMA_MIGRATION_PLAN_COMPLETE = PASS
```

## Backward Compatibility Policy

Temporary compatibility is allowed only when:

- old path is non-authoritative
- target owner is unambiguous
- cutover criteria are explicit
- removal stage is defined

Temporary compatibility paths:

1. Stage 2 Risk Pacing shadow materialization before PC consumption.
2. PC target/allocation compatibility fields until Stage 7.
3. Position Sizing residual evidence compatibility alongside existing quantity
   fields until Stage 7.
4. ADD bridge compatibility until Stage 7.
5. Re-entry reason alias compatibility until Stage 7.

```text
TEMPORARY_COMPATIBILITY_PATH_COUNT = 5
PERMANENT_COMPATIBILITY_FALLBACK_COUNT = 0
```

## Stage-by-Stage Acceptance Gates

Every stage requires:

- code review
- focused unit tests
- focused regression tests
- authority invariant checks
- temporal / PIT tests
- no-future-data tests
- no evidence feedback tests
- no duplicate authority tests
- `git diff --check`

| Stage | Gate |
| ---: | --- |
| 1 | `MARKET_DIRECTION_UNCHANGED=YES`; `MARKET_QUALITY_MATERIALIZED=YES`; `MARKET_QUALITY_FAIL_CLOSED=YES`; `FUTURE_INPUT_COUNT=0`; `HISTORICAL_RESULT_INPUT_COUNT=0`; `BEHAVIOR_CHANGE=NO` |
| 2 | `RISK_PACING_OWNER=PORTFOLIO_POLICY`; `NO_FIXED_EXPOSURE_TARGET=YES`; `NO_FIXED_BUY_COUNT=YES`; `SELL_INDEPENDENCE=PASS`; `SAFETY_UNCHANGED=PASS`; `MISSING_QUALITY_NORMAL_DEPLOYMENT=NO` |
| 3 | `PC_OWNS_CAPITAL_COMPETITION=YES`; `PC_OWNS_FINAL_NO_DEPLOYABLE=YES`; no downstream Strategy re-decision |
| 4 | `POSITION_SIZING_OWNS_QUANTITY=YES`; `LOT_FIRST=PASS`; `RESIDUAL_RECONSIDERATION=PASS`; `NO_DUPLICATE_QUANTITY_DECISION=PASS`; `STRATEGY_SAFETY_CAP_SEPARATION=PASS`; `VALID_CASH_PRESERVATION=PASS` |
| 5 | `BLANKET_REENTRY_BAN=NO`; `BLANKET_REENTRY_PERMISSION=NO`; `RENEWED_EVIDENCE_PATH=PASS`; `CHURN_PROTECTION=PASS`; `BUY_SELL_INDEPENDENCE=PASS` |
| 6 | `PM_ADD_INTENT_CAN_REACH_PC_COMPETITION=PASS`; `ADD_CAN_WIN=PASS`; `ADD_CAN_LOSE_TO_NEW_BUY=PASS`; `ADD_CAN_LOSE_TO_CASH=PASS`; `ADD_AUTOMATIC_PRIORITY=NO`; `ADD_AUTOMATIC_REJECTION=NO`; `FUTURE_OUTCOME_INPUT=NO` |
| 7 | all temporary compatibility paths removed or made non-authoritative with explicit removal completed; no permanent fallback |
| 8 | integrated focused acceptance across Market Quality, Risk Pacing, PC, Sizing, Residual, Re-entry, ADD, BUY/SELL independence, Safety, Submit no-op authority, Execution no-op authority, PIT, and feedback |
| 9 | user-operated fresh Historical only after Stage 8 passes |

```text
STAGE_ACCEPTANCE_GATE_COUNT = 9
ALL_STAGES_HAVE_ACCEPTANCE_GATE = YES
INTEGRATED_FOCUSED_ACCEPTANCE_REQUIRED = YES
LONG_HISTORICAL_ALLOWED_BEFORE_INTEGRATED_ACCEPTANCE = NO
```

## Historical Validation Entry Gate

Historical validation is allowed only after integrated focused acceptance.

Allowed evaluation:

- Return
- PF
- MDD
- average loser
- short loser frequency / magnitude
- exposure behavior
- cash behavior
- risk-off / re-risk transitions
- qualified opportunity deployment
- ADD funnel
- re-entry behavior
- regime / Market Quality cohorts

Forbidden:

- threshold tuning
- weight selection
- exposure target selection
- cooldown selection
- BUY count selection

```text
HISTORICAL_VALIDATION_ROLE = VALIDATION_ONLY
HISTORICAL_PARAMETER_SELECTION_ALLOWED = NO
PRE_CHANGE_BASELINE_RUN_ID =
runtime-test-historical-extended-smoke-20260822T174358377089Z
BASELINE_ROLE = VALIDATION_REFERENCE_ONLY
```

Use only fully completed canonical days from the baseline. Do not require the
baseline run to finish if it is already stopped.

## Roll-Forward Policy

If a stage fails acceptance:

- fix the stage
- revert incomplete implementation patch if necessary
- do not keep both business-authority paths live
- do not retain permanent legacy fallback

```text
DUAL_AUTHORITY_ROLLBACK_MODE_ALLOWED = NO
PERMANENT_LEGACY_FAILOVER_ALLOWED = NO
```

## Future Implementation Task Sequence

| Task ID | Title | Scope | Files | Authority change | Test gate | Dependency | User long run required |
| --- | --- | --- | --- | --- | --- | --- | --- |
| G22 | Market Quality Evidence Producer | Add evidence-only Market Quality fields and reason codes | `market_context.py`, market context tests, optional config/schema | Market Context evidence only | Stage 1 gate | G21 | NO |
| G23 | Portfolio Policy Risk Pacing Shadow | Materialize non-authoritative Risk Pacing intent | `portfolio_policy.py`, policy tests | Portfolio Policy shadow evidence | Stage 2 gate | G22 | NO |
| G24 | PC Capital Competitor Framework | Add `NEW_BUY` / `ADD` / `CASH_OPTIONALITY` framework and final no-deployable state | `portfolio_construction.py`, PC tests | PC composition authority | Stage 3 gate | G23 | NO |
| G25 | Position Sizing Residual Evidence Bridge | Expose residual / lot evidence and PC reconsideration loop | `position_sizing.py`, `position_sizing_plan.py`, PC/Sizing tests | Sizing evidence, PC loop | Stage 4 gate | G24 | NO |
| G26 | Re-entry Semantic Eligibility Integration | Refactor re-entry gates into explicit semantic API | `portfolio_construction.py`, re-entry tests | PC re-entry semantics | Stage 5 gate | G25 | NO |
| G27 | ADD Capital Competition Integration | Connect PM ADD intent to ADD competitor and quantity delta path | `portfolio_construction.py`, `position_sizing.py`, runtime planning regression | PC ADD competitiveness; Sizing quantity unchanged | Stage 6 gate | G26 | NO |
| G28 | Legacy Compatibility Removal | Remove temporary shadow/compatibility authority surfaces | affected strategy modules / tests | no duplicate authority | Stage 7 gate | G27 | NO |
| G29 | Integrated Focused Acceptance | Cross-component focused regression suite | tests only unless defects found in later task | acceptance only | Stage 8 gate | G28 | NO |
| G30 | User-Operated Fresh Historical Validation Readiness | Prepare exact command and validation scorecard | docs/report only | validation only | Stage 9 gate | G29 | YES, user-operated |

```text
FUTURE_IMPLEMENTATION_TASK_SEQUENCE_DEFINED = YES
FIRST_IMPLEMENTATION_TASK =
G22_MARKET_QUALITY_EVIDENCE_PRODUCER_SCHEMA_REASON_CODES
FIRST_IMPLEMENTATION_TASK_BEHAVIOR_CHANGE = NO
```

## Stop Conditions

Implementation progression must halt if any of these occur:

- future / PIT violation
- Evidence feedback loop
- duplicate business authority
- Strategy cap and Safety cap collapse into one authority
- SELL blocked by BUY state
- quantity authority duplicated
- implicit healthy fallback
- implicit BULL fallback
- permanent legacy fallback
- unresolved temporal lineage
- sector participation promoted without settled semantics
- Stage tests fail
- `git diff --check` fails
- behavior-changing stage proceeds before its prerequisite gate passes
- Historical return/PF/MDD is used to tune a stage

```text
IMPLEMENTATION_STOP_CONDITIONS_DEFINED = YES
PERFORMANCE_IMPROVEMENT_REQUIRED_FOR_STAGE_ACCEPTANCE = NO
```

## Documentation Migration

Each implementation stage that reveals a necessary contract clarification must
update canonical SoT. Phase reports are supporting evidence only.

```text
CANONICAL_SOT_MAINTENANCE_REQUIRED = YES
PHASE_REPORT_ONLY_DOCUMENTATION_ALLOWED = NO
```

## Required Summary Output

```text
PRIMARY_JUDGMENT =
PHASE31_G21_STAGED_IMPLEMENTATION_PLAN_READY

TARGET_ARCHITECTURE_SOT =
docs/02_architecture/dual_path_market_quality_and_capital_competition_contract.md

CURRENT_DEPENDENCY_GRAPH_COMPLETE = PASS

TARGET_DEPENDENCY_GRAPH_COMPLETE = PASS

TARGET_GRAPH_MATCHES_G20_SOT = YES

STAGE1_MARKET_QUALITY_EVIDENCE_ONLY_FEASIBLE = YES

STAGE1_PRODUCTION_BEHAVIOR_CHANGE_REQUIRED = NO

STAGE1_INPUT_SCOPE =
EXISTING_5D_RETURN, EXISTING_20D_RETURN, EXISTING_5D_BREADTH,
EXISTING_20D_BREADTH, EXISTING_VOLATILITY_DOWNSIDE_RISK,
EXISTING_CONFIDENCE_COVERAGE

SECTOR_PARTICIPATION_INCLUDED_IN_INITIAL_IMPLEMENTATION = NO

STAGE2_RISK_PACING_BEHAVIORAL_CHANGE = NO

TEMPORARY_NON_AUTHORITATIVE_SHADOW_ALLOWED = YES

PERMANENT_SHADOW_PATH_ALLOWED = NO

PC_COMPETITOR_FRAMEWORK_STAGE_DEFINED = YES

PC_FINAL_NO_DEPLOYABLE_AUTHORITY_MIGRATION_REQUIRED = YES

CONSTRAINT_MIGRATION_MATRIX_COMPLETE = PASS

BIG_BANG_IMPLEMENTATION_REQUIRED = NO

POSITION_SIZING_AUTHORITY_CHANGED = NO

RESIDUAL_EVIDENCE_API_REQUIRED = YES

PC_RESIDUAL_RECONSIDERATION_LOOP_REQUIRED = YES

RESIDUAL_LOOP_DUPLICATE_EXECUTION_RISK = NO

REENTRY_CURRENT_GATE_INVENTORY_COMPLETE = YES

REENTRY_TARGET_SEMANTIC_API_DEFINED = YES

REENTRY_NUMERIC_PARAMETER_CHANGE_REQUIRED_FOR_INITIAL_MIGRATION = NO

ADD_MIGRATION_GAP_MATRIX_COMPLETE = PASS

ADD_INCREMENTAL_VALUE_AUTHORITY = PORTFOLIO_CONSTRUCTION

ADD_OPPORTUNITY_COST_AUTHORITY = PORTFOLIO_CONSTRUCTION

INITIAL_ADD_SCOPE = CONNECTIVITY_AND_AUTHORITY_ONLY

NEW_ADD_ALPHA_FEATURE_REQUIRED = NO

BUY_QUALITY_MIGRATION_PRIORITY = DEFERRED

SELL_IMPLEMENTATION_CHANGE_REQUIRED = NO

PM_IMPLEMENTATION_CHANGE_REQUIRED = NO

SAFETY_LOGIC_CHANGE_REQUIRED = NO

SUBMIT_LOGIC_CHANGE_REQUIRED = NO

EXECUTION_LOGIC_CHANGE_REQUIRED = NO

SCHEMA_MIGRATION_PLAN_COMPLETE = PASS

TEMPORARY_COMPATIBILITY_PATH_COUNT = 5

PERMANENT_COMPATIBILITY_FALLBACK_COUNT = 0

STAGE_ACCEPTANCE_GATE_COUNT = 9

ALL_STAGES_HAVE_ACCEPTANCE_GATE = YES

INTEGRATED_FOCUSED_ACCEPTANCE_REQUIRED = YES

LONG_HISTORICAL_ALLOWED_BEFORE_INTEGRATED_ACCEPTANCE = NO

HISTORICAL_VALIDATION_ROLE = VALIDATION_ONLY

HISTORICAL_PARAMETER_SELECTION_ALLOWED = NO

PRE_CHANGE_BASELINE_RUN_ID =
runtime-test-historical-extended-smoke-20260822T174358377089Z

BASELINE_ROLE = VALIDATION_REFERENCE_ONLY

DUAL_AUTHORITY_ROLLBACK_MODE_ALLOWED = NO

PERMANENT_LEGACY_FAILOVER_ALLOWED = NO

FUTURE_IMPLEMENTATION_TASK_SEQUENCE_DEFINED = YES

FIRST_IMPLEMENTATION_TASK =
G22_MARKET_QUALITY_EVIDENCE_PRODUCER_SCHEMA_REASON_CODES

FIRST_IMPLEMENTATION_TASK_BEHAVIOR_CHANGE = NO

IMPLEMENTATION_STOP_CONDITIONS_DEFINED = YES

PERFORMANCE_IMPROVEMENT_REQUIRED_FOR_STAGE_ACCEPTANCE = NO

CANONICAL_SOT_MAINTENANCE_REQUIRED = YES

PHASE_REPORT_ONLY_DOCUMENTATION_ALLOWED = NO

IMPLEMENTATION_EXECUTED = NO

PRODUCTION_CODE_CHANGED = NO

CONFIG_CHANGED = NO

SCHEMA_MIGRATION_EXECUTED = NO

FRESH_RUN_EXECUTED = NO

RESUME_EXECUTED = NO

REPLAY_EXECUTED = NO

LONG_HISTORICAL_EXECUTED = NO

GIT_DIFF_CHECK = PASS

NEXT_TASK_RECOMMENDATION =
G22 Market Quality evidence-only producer / schema / reason-code implementation.
No Production behavior change, no sector participation initial scope, no
Historical run.
```
