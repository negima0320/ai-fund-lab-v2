# Phase31-G39 — Opportunity Quality / True Cash Competition Implementation Planning

## Scope

Task type: IMPLEMENTATION PLANNING / MIGRATION PLANNING.

G39 did not implement code, change Strategy / Market Context / Portfolio Policy
/ Portfolio Construction / marginal capital value / Position Sizing / PM / ADD
/ Re-entry / SELL / Runtime behavior, change configuration, tune thresholds,
modify fixtures, run fresh Historical, resume, replay, or rerun Historical.

G39 plans implementation against the permanent G38 architecture SoT:

- `docs/02_architecture/dual_path_market_quality_and_capital_competition_contract.md`

## Primary Judgment

`PHASE31_G39_REFINED_CAPITAL_COMPETITION_IMPLEMENTATION_PLAN_READY`

The implementation plan is ready. Existing PIT evidence is sufficient to plan
the first migration slices without creating a duplicate alpha authority. The
smallest architecture-consistent owner for the refined opportunity-quality
continuum is the existing `strategy.marginal_capital_value` authority, extended
from `ELIGIBLE_STRONG / ELIGIBLE_COMPARABLE / ELIGIBLE_WEAK` into the G38
continuum:

- `STRONG`
- `COMPARABLE_HIGH`
- `COMPARABLE_MARGINAL`
- `WEAK_VALID`
- `INSUFFICIENT`
- `BLOCKED`

Portfolio Construction should consume that classification and perform the
pre-final NEW_BUY / ADD / Cash economic competition. Portfolio Construction
must not create new alpha features.

## Inputs Read

- `docs/02_architecture/dual_path_market_quality_and_capital_competition_contract.md`
- `docs/phase_reports/phase31_g37_risk_pacing_binding_candidate_comparison_effectiveness_root_cause_audit.md`
- `docs/phase_reports/phase31_g38_economically_binding_risk_pacing_market_candidate_cash_interaction_architecture_refinement.md`
- `src/ai_fund_lab_v2/strategy/marginal_capital_value.py`
- `src/ai_fund_lab_v2/strategy/portfolio_construction.py`
- `src/ai_fund_lab_v2/strategy/portfolio_policy.py`
- `src/ai_fund_lab_v2/strategy/market_context.py`
- `src/ai_fund_lab_v2/strategy/strategy_intelligence.py`
- `src/ai_fund_lab_v2/strategy/position_management.py`
- `src/ai_fund_lab_v2/strategy/position_sizing.py`
- `src/ai_fund_lab_v2/strategy/runtime_planning.py`

## Existing Evidence Inventory

| Evidence family | Producer | Current consumer | Schema / field surface | PIT / as-of authority | Missing behavior | Current role |
| --- | --- | --- | --- | --- | --- | --- |
| Runtime opportunity score | Opportunity / Strategy Intelligence bridge | Candidate quality, PC, marginal capital value | `runtime_opportunity_score`, `expected_edge_score` | Member-level PIT row / Strategy evidence date | Missing score can still use rank; if both missing, comparison insufficient | Relative opportunity support, not calibrated alpha. |
| Opportunity rank | Opportunity ranking / PC member fields | PC, marginal capital value, re-entry | `input_opportunity_rank`, `opportunity_rank`, `buy_rank` | PIT opportunity snapshot | Missing rank may use score; if both missing, insufficient | Ordering and evidence support. |
| Expected edge | Strategy Intelligence | Entry admission, ADD bridge, marginal capital value | `expected_edge`, `expected_edge_improvement_state` | `as_of_business_date`, source lineage | Missing / not PASS is insufficient or fail-closed for ADD | Supporting edge / ADD improvement evidence. |
| Entry admission action | Strategy Intelligence | PC, marginal capital value | `entry_admission_action`, nested `entry_admission.admission_action` | `entry_admission.v1` with `as_of_business_date` | Insufficient -> BUY_WAIT / NO_ADD / REVIEW_REQUIRED | Eligibility / quality gate for BUY_NEW and ADD. |
| Entry admission state | Strategy Intelligence | PC, marginal capital value, re-entry | `entry_admission_state`, nested `entry_state` | Same as entry admission | Insufficient/reversal/overheated -> wait/no-add | Semantic entry condition. |
| Entry evidence sufficiency | Strategy Intelligence | PC, re-entry, selection quality | `entry_admission_evidence_sufficiency`, nested `evidence_sufficiency` | Same as entry admission | `INSUFFICIENT` fails closed for refined incremental competition | Completeness boundary. |
| Quality bias | Strategy Intelligence | Candidate quality / PC | `allocation_quality_bias` | Same as entry admission | NONE means no positive allocation bias | Distinguishes full vs reduced quality without changing eligibility. |
| BUY Quality action | BUY Quality / current decision | PC, re-entry, selection quality | `quality_action`, `buy_quality_action` | BUY quality artifact / PIT member evidence | reject/wait/reduced/full as emitted | Candidate admission / allocation posture. |
| BUY Quality hard reasons | BUY Quality / opportunity reason families | PC selection quality | `no_buy_reasons`, hard reason sets | PIT row evidence | Hard reasons block or fail closed | Prevents invalid candidates from being rescued. |
| BUY Quality soft reasons | BUY Quality / opportunity reason families | PC selection quality | soft relative reasons, rank/score reason families | PIT row evidence | Soft reasons can contribute to marginal class | Candidate-quality nuance. |
| ADD expected-edge improvement | PC ADD bridge / ADD investment evidence | PC ADD competitor, marginal capital value | `expected_edge_improvement_state`, `add_investment_evidence.expected_edge` | ADD evidence business date and temporal authority | missing/not PASS -> ADD insufficient/fail-closed | ADD-specific incremental quality. |
| Incremental Investment Value | PC ADD bridge | PC ADD competitor, marginal capital value | `incremental_investment_value_state`, `add_investment_evidence.incremental_value` | ADD evidence business date | not POSITIVE/PASS -> fail closed | ADD value gate. |
| Opportunity Cost | PC ADD bridge | PC ADD competitor, marginal capital value | `opportunity_cost_status`, `add_investment_evidence.opportunity_cost` | ADD evidence business date | not PASS -> fail closed | ADD vs alternative capital evidence. |
| ADD worthiness | PM / Strategy Intelligence | PC ADD bridge, marginal capital value | `strategy_intelligence_add_worthiness_state`, `add_worthiness_state` | PM / Strategy Intelligence PIT state | NO_ADD blocks ADD | PM-owned ADD intent quality. |
| Re-entry eligibility | PC re-entry semantic gate | PC membership / target logic | `reentry_recovery_status`, `reentry_*` fields | PIT row + prior exit context available by date | unknown/fail -> fail-closed eligibility | Eligibility only, then normal competition. |
| Portfolio concentration | PC / policy constraints / sizing context | PC competition, sizing | `concentration_status`, weights, caps | Current PIT portfolio state | cap/fail -> blocked or reserve reason | Portfolio context, not alpha. |
| Current holdings | Portfolio state / PM | PC, PM, sizing | `current_position`, `current_weight`, campaign fields | PIT ledger/portfolio state | missing required ADD current weight -> fail-closed | ADD vs NEW_BUY context. |
| Lot feasibility | Position Sizing | PC reconsideration, Runtime | `canonical_sizing_evidence`, lot feasibility preflight | `quantity_authority_owner=POSITION_SIZING` | terminal/reconsiderable as emitted | Quantity / feasibility boundary. |
| Residual capital | PC + Position Sizing evidence | PC cash competitor | `remaining_cash_weight`, `residual_cash_reason`, incremental budget evidence | Same-day PC / sizing evidence | missing -> no fabricated deployment | Cash / reconsideration context. |

`OPPORTUNITY_EVIDENCE_INVENTORY_COMPLETE = YES`

## Evidence Owner Matrix

| Evidence family | Authoritative owner | PC role |
| --- | --- | --- |
| Market Quality | Market Context | consume only |
| Risk Pacing | Portfolio Policy | consume only |
| Opportunity quality class | marginal capital value authority | consume classification and lineage |
| Opportunity score / rank | existing opportunity / Strategy evidence producers | consume through opportunity-quality authority |
| Entry admission | Strategy Intelligence | consume through opportunity-quality authority and existing member fields |
| BUY Quality action / reasons | BUY Quality / Strategy Intelligence bridge | consume through opportunity-quality authority |
| ADD worthiness / ADD intent | PM / Strategy Intelligence | consume through opportunity-quality authority and ADD bridge |
| ADD expected edge / incremental value / opportunity cost | PC ADD bridge existing authority | consume and expose to opportunity-quality authority |
| Re-entry eligibility | PC re-entry semantic eligibility | eligibility only, then normal competition |
| Portfolio concentration / holdings / residual capital | PC / portfolio state | competition context |
| Lot feasibility / quantity | Position Sizing | consume for lot reconsideration; no PC quantity authority |
| Runtime lineage | Runtime Planning / Pending / Submit / Execution | preserve only |

`OPPORTUNITY_EVIDENCE_OWNER_MATRIX_COMPLETE = YES`

`PC_CREATES_NEW_ALPHA_FEATURE = NO`

## Opportunity Quality Producer Design

Chosen approach: A. extend the existing canonical `marginal_capital_value`
classifier.

Rationale:

- It already owns marginal capital comparison, candidate intent, source
  evidence capture, priority ordering, forbidden outcome fields, and authority
  hashes.
- It already consumes NEW_BUY and ADD evidence.
- Extending it avoids creating a duplicate candidate-quality or alpha
  authority.
- Portfolio Construction remains the capital competition owner and consumes
  the class rather than producing alpha features.

`OPPORTUNITY_QUALITY_OWNER = MARGINAL_CAPITAL_VALUE_AUTHORITY`

`OPPORTUNITY_QUALITY_PRODUCER_LOCATION = src/ai_fund_lab_v2/strategy/marginal_capital_value.py`

`DUPLICATE_QUALITY_AUTHORITY_CREATED = NO`

## Reachable Class Semantic Matrix

| Class | Semantic predicate using existing PIT evidence | Missing-data behavior | Notes |
| --- | --- | --- | --- |
| `STRONG` | Explicit positive evidence: allowed/full entry or ADD evidence PASS, complete sufficiency, supportive continuation/entry semantics, no hard risk/admission block, and rank/score support. Rank existence alone is insufficient. | If required evidence missing, not STRONG. | Symbol-specific exception path under caution. |
| `COMPARABLE_HIGH` | Valid candidate with complete evidence, positive rank/score support, no hard block, and high-quality or valid continuation evidence, but not enough explicit positive evidence for STRONG. | Missing evidence -> INSUFFICIENT. | Gradual can deploy selectively. |
| `COMPARABLE_MARGINAL` | Valid candidate with complete evidence and rank/score support, but reduced allocation bias, caution continuation, soft risk vote, or mixed quality makes Cash competitive under weak markets. | Missing evidence -> INSUFFICIENT. | Key same-candidate/different-market binding case. |
| `WEAK_VALID` | Eligible, complete enough, not hard-blocked, not missing, but only weakly supported or reduced-quality enough that optionality should dominate under caution/preserve. | Missing evidence -> INSUFFICIENT; hard block -> BLOCKED. | Not equivalent to invalid. |
| `INSUFFICIENT` | Required PIT comparison evidence is missing, stale, contradictory, or lineage-incomplete. | Fail closed for incremental deployment. | Does not mean bad investment; means cannot decide. |
| `BLOCKED` | Candidate admission, BUY Quality, ADD eligibility, re-entry eligibility, Safety/eligibility, or feasibility blocks deployment. | Blocked. | Risk Pacing must not rescue. |

Numeric thresholds, if later unavoidable, must be pre-registered from semantic
meaning and PIT distributions, then validated cross-period or walk-forward. G39
selects no values.

`OPPORTUNITY_CLASS_SEMANTIC_MATRIX_COMPLETE = YES`

`ALL_VALID_CLASSES_STRUCTURALLY_REACHABLE_BY_DESIGN = YES`

`WEAK_VALID_NOT_EQUIVALENT_TO_INVALID = YES`

`COMPARABLE_MARGINAL_DISTINCT = YES`

`STRONG_REQUIRES_EXPLICIT_POSITIVE_EVIDENCE = YES`

`MISSING_EVIDENCE_FAIL_CLOSED = YES`

## Cash Competitor Evidence Schema

Planned canonical schema:

```text
cash_competitor_evidence.v1
```

Required fields:

- `schema_version`
- `business_date`
- `owner = PORTFOLIO_CONSTRUCTION`
- `competitor_type = CASH_OPTIONALITY`
- `market_quality_state`
- `market_quality_as_of`
- `market_quality_evidence_hash`
- `risk_pacing_intent`
- `risk_pacing_as_of`
- `risk_pacing_evidence_hash`
- `portfolio_concentration_state`
- `current_gross_exposure`
- `current_cash_weight`
- `remaining_cash_weight`
- `residual_capital_classification`
- `available_deployable_competitor_count`
- `best_opportunity_quality_class`
- `candidate_quality_distribution`
- `lot_feasibility_summary`
- `evidence_completeness`
- `cash_preference_semantic`
- `reason_codes`
- `future_information_used = False`
- `historical_outcome_used = False`
- `fixed_exposure_target_created = False`
- `fixed_buy_count_created = False`
- `quantity_authority_owner = POSITION_SIZING`

`CASH_COMPETITOR_EVIDENCE_SCHEMA_DEFINED = YES`

`CASH_COMPARISON_METHOD = ORDERED_SEMANTIC_DOMINANCE_RULES`

The planned method is not a numeric cash score. Portfolio Construction compares
semantic opportunity classes against Risk Pacing intent using the G38 matrix,
then applies deterministic dominance / tie-break rules among NEW_BUY, ADD, and
Cash.

`OUTCOME_OPTIMIZED_CASH_SCORE = NO`

## Implementation Binding Matrix

| Risk Pacing intent | `STRONG` | `COMPARABLE_HIGH` | `COMPARABLE_MARGINAL` | `WEAK_VALID` | `INSUFFICIENT` | `BLOCKED` |
| --- | --- | --- | --- | --- | --- | --- |
| `NORMAL_DEPLOYMENT` | `DEPLOY_ELIGIBLE` | `DEPLOY_ELIGIBLE` | `DEPLOY_ELIGIBLE` | `SELECTIVE_COMPETITION` | `FAIL_CLOSED` | `BLOCKED` |
| `GRADUAL_REDEPLOYMENT` | `DEPLOY_ELIGIBLE` | `SELECTIVE_COMPETITION` | `CASH_PREFERRED` | `CASH_PREFERRED` | `FAIL_CLOSED` | `BLOCKED` |
| `CAUTIOUS_DEPLOYMENT` | `SELECTIVE_COMPETITION` | `SELECTIVE_COMPETITION` only with caution-sufficient evidence | `CASH_PREFERRED` | `CASH_PREFERRED` | `FAIL_CLOSED` | `BLOCKED` |
| `PRESERVE_OPTIONALITY` | `SELECTIVE_COMPETITION` only if exceptional and complete | `CASH_PREFERRED` | `CASH_PREFERRED` | `CASH_PREFERRED` | `FAIL_CLOSED` | `BLOCKED` |

`IMPLEMENTATION_BINDING_MATRIX_COMPLETE = YES`

`CAUTIOUS_GRADUAL_IMPLEMENTATION_DIFFERENCE_DEFINED = YES`

GRADUAL differs from CAUTIOUS economically: GRADUAL allows `COMPARABLE_HIGH`
selective redeployment by default, while CAUTIOUS requires caution-sufficient
symbol evidence and prefers Cash for marginal comparable candidates.

`PRESERVE_OPTIONALITY_IMPLEMENTATION_ROLE_DEFINED = YES`

PRESERVE may occur from missing/insufficient Market Quality, invalid temporal
authority, explicit conflicted/fallback policy states, or future refined
Market Quality states that semantically indicate optionality preservation. It
is not forced to occur and is not merely a dead missing-data state.

## Refined Flows

### NEW_BUY

```text
candidate eligibility / BUY Quality / entry admission
  -> marginal_capital_value opportunity-quality class
  -> Portfolio Construction market x candidate x Cash interaction
  -> NEW_BUY vs ADD vs Cash winner
  -> Position Sizing quantity
  -> Runtime lineage
```

`NEW_BUY_REFINED_FLOW_DEFINED = YES`

### ADD

```text
PM-owned ADD intent
  -> ADD worthiness / expected-edge improvement / incremental value / opportunity cost
  -> marginal_capital_value opportunity-quality class
  -> same PC market x candidate x Cash competition
  -> ADD vs NEW_BUY vs Cash winner
  -> Position Sizing quantity delta
```

`ADD_REFINED_FLOW_DEFINED = YES`

`ADD_VALUE_EVIDENCE_REUSED = YES`

### Re-entry

```text
symbol-local re-entry eligibility
  -> if eligible, normal NEW_BUY opportunity-quality classification
  -> same PC capital competition
```

`REENTRY_REFINED_FLOW_DEFINED = YES`

## Multi-Competitor Competition

When NEW_BUY A, NEW_BUY B, ADD C, and Cash are all present, implementation must
not run independent binary block tests. Planned flow:

1. Build all deployable competitors with opportunity-quality class and lineage.
2. Build Cash competitor evidence once from market, risk pacing, portfolio, and
   opportunity distribution.
3. Apply the Risk Pacing x Opportunity Quality matrix to each deployable
   competitor.
4. Partition competitors into deploy-eligible, selective, Cash-preferred,
   fail-closed, and blocked.
5. Select one canonical semantic capital winner or ordered winner set under PC
   rules before sizing.
6. Preserve defeated competitors with reason codes, including
   `LOST_TO_CASH`, `LOST_TO_STRONGER_NEW_BUY`, or `LOST_TO_STRONGER_ADD`.

`MULTI_COMPETITOR_CAPITAL_COMPETITION_DEFINED = YES`

`FINAL_CAPITAL_WINNER_OWNER = PORTFOLIO_CONSTRUCTION`

`SECOND_CAPITAL_WINNER_AUTHORITY = NO`

## Boundaries Preserved

`POSITION_SIZING_BOUNDARY_PRESERVED = YES`

Position Sizing receives selected deployment candidate(s) and remains quantity
owner. Risk Pacing and Cash competition do not set share quantity.

`LOT_RECONSIDERATION_CONTRACT_PRESERVED = YES`

If selected deployment is lot-infeasible, canonical Position Sizing evidence
flows back to PC for reconsideration among remaining NEW_BUY / ADD / Cash. No
second sizing engine is created.

`EXISTING_HOLDING_SELL_SEMANTICS_CHANGED = NO`

`BUY_SELL_INDEPENDENCE_PRESERVED = YES`

`SAFETY_AUTHORITY_CHANGED = NO`

`RUNTIME_CAPITAL_REDECISION = NO`

## Refined Capital Lineage Schema

Planned lineage fields:

- `capital_competition_schema_version`
- `business_date`
- `market_quality_state`
- `market_quality_as_of`
- `market_quality_authority_hash`
- `risk_pacing_intent`
- `risk_pacing_as_of`
- `risk_pacing_authority_hash`
- `opportunity_quality_authority_type`
- `opportunity_quality_contract_id`
- `opportunity_quality_class`
- `opportunity_quality_reason_codes`
- `opportunity_quality_source_evidence_hash`
- `cash_competitor_schema_version`
- `cash_competitor_reason_codes`
- `cash_preference_semantic`
- `capital_competition_winner_type`
- `capital_competition_winner_symbol`
- `capital_competition_winner_reason_codes`
- `defeated_competitor_summary`
- `position_sizing_authority_owner`
- `canonical_sizing_evidence_hash`
- `future_information_used`
- `historical_outcome_used`
- `downstream_capital_redecision_allowed = False`

`REFINED_CAPITAL_LINEAGE_SCHEMA_DEFINED = YES`

## Legacy Migration Matrix

| Current semantic | Migration action | Target |
| --- | --- | --- |
| unreachable `ELIGIBLE_WEAK` | MIGRATE | reachable `WEAK_VALID` / `COMPARABLE_MARGINAL` classes |
| broad `ELIGIBLE_COMPARABLE` | MIGRATE | split into `COMPARABLE_HIGH`, `COMPARABLE_MARGINAL`, and `WEAK_VALID` where appropriate |
| `ELIGIBLE_STRONG` from rank exists | MIGRATE | require explicit positive evidence; rank alone cannot imply STRONG |
| late Risk Pacing block | REMOVE | pre-final market x candidate x Cash interaction |
| Cash residual-only behavior | MIGRATE | true Cash competitor evidence and dominance rules |
| old CAUTIOUS/GRADUAL same truth table | REMOVE | economically distinct matrix |
| candidate admission hard blocks | KEEP | invalid candidates remain blocked |
| ADD value / opportunity cost evidence | KEEP | reused in opportunity-quality class |
| Re-entry eligibility | KEEP | eligibility only, then same competition |
| Position Sizing quantity authority | KEEP | no second quantity owner |
| temporary compatibility aliases | DEPRECATE | bounded migration only; final fallback count zero |

`LEGACY_MIGRATION_MATRIX_COMPLETE = YES`

`FINAL_PERMANENT_LEGACY_FALLBACK_COUNT = 0`

## Implementation Slice Plan

| Slice | Scope | Behavior change class | Acceptance gate |
| --- | --- | --- | --- |
| G40 | Opportunity-quality producer / reachable continuum in `marginal_capital_value`; no PC economic activation if possible | `EVIDENCE_ONLY` / `STRUCTURAL_ONLY` | Classes reachable, lineage complete, no outcome inputs, no PC winner change. |
| G41 | Cash competitor evidence schema and materialization in PC | `EVIDENCE_ONLY` | Cash evidence complete, no numeric outcome score, no fixed exposure target. |
| G42 | Pre-final market x candidate x Cash interaction skeleton | `LIMITED_DECISION_CHANGE` behind canonical path tests | Matrix encoded, no second alpha or quantity authority. |
| G43 | CAUTIOUS / GRADUAL / PRESERVE economic activation | `AUTHORITATIVE_DECISION_CHANGE` | Same-candidate/different-market tests pass; reason-code-only delta rejected. |
| G44 | ADD / Re-entry integration and lot reconsideration | `AUTHORITATIVE_DECISION_CHANGE` | ADD and NEW_BUY no automatic priority; re-entry eligibility only; lot reconsideration preserved. |
| G45 | Lineage persistence through Runtime boundary | `RUNTIME_LINEAGE_ONLY` | Runtime preserves final decision lineage and does not redo capital competition. |
| G46 | Synthetic binding acceptance suite | `STRUCTURAL_ONLY` test acceptance | All pre-registered synthetic cases pass. |
| G47 | Production E2E acceptance | `AUTHORITATIVE_ACCEPTANCE` | E2E evidence, PIT audit, no legacy fallback, no Historical profitability gate. |
| Post-G47 | Fresh Historical entry | `VALIDATION_ONLY` | Only after all gates pass. |

`IMPLEMENTATION_SLICE_PLAN_COMPLETE = YES`

`SLICE_BEHAVIOR_CHANGE_MATRIX_COMPLETE = YES`

## Per-Slice Acceptance Matrix

| Slice | Required acceptance |
| --- | --- |
| G40 | `STRONG`, `COMPARABLE_HIGH`, `COMPARABLE_MARGINAL`, `WEAK_VALID`, `INSUFFICIENT`, `BLOCKED` are structurally reachable; `WEAK_VALID` is valid not invalid; STRONG requires explicit positive evidence; missing evidence fail-closed. |
| G41 | Cash evidence schema materializes market, risk pacing, portfolio, opportunity distribution, residual, lot, and completeness fields; no outcome score; no fixed exposure target. |
| G42 | PC builds all competitors before final winner; Cash can participate before candidate failure; PC does not create alpha features. |
| G43 | CAUTIOUS and GRADUAL differ economically; PRESERVE has practical role; matrix results are persisted with reason codes. |
| G44 | ADD maps through same quality continuum; ADD value evidence reused; re-entry eligibility is not a priority/penalty; lot reconsideration still uses Position Sizing evidence. |
| G45 | Runtime lineage includes Market Quality, Risk Pacing, Opportunity Quality, Cash evidence, winner reason, and sizing evidence; downstream re-decision is impossible by test. |
| G46 | Pre-registered synthetic binding tests pass; no Historical profitability assertions. |
| G47 | Production E2E acceptance passes with no permanent legacy fallback, PIT lineage intact, Safety/SELL/PM/quantity boundaries unchanged. |

`PER_SLICE_ACCEPTANCE_MATRIX_COMPLETE = YES`

## Synthetic Binding Test Plan

Pre-registered mandatory tests:

| Case | Expected result |
| --- | --- |
| same candidate + NORMAL -> deploy | `DEPLOY_ELIGIBLE` / deployment may win |
| same candidate + CAUTIOUS -> Cash may win | `CASH_PREFERRED` or Cash winner |
| same candidate + PRESERVE -> Cash wins | Cash winner |
| CAUTIOUS + STRONG -> deploy may win | selective deployment allowed |
| GRADUAL + COMPARABLE_HIGH -> deploy may win | selective deployment allowed |
| GRADUAL + COMPARABLE_MARGINAL -> Cash may win | Cash preferred |
| NORMAL + WEAK_VALID -> may deploy | selective/deploy if best use of capital |
| missing evidence -> fail closed | `INSUFFICIENT` / no incremental deployment |

`SYNTHETIC_BINDING_TEST_PLAN_COMPLETE = YES`

## Non-Regression Test Plan

Pre-registered non-regression coverage:

- Candidate selection unchanged unless refined capital interaction applies.
- SELL unchanged.
- PM HOLD / REDUCE / EXIT unchanged.
- Safety unchanged.
- Position Sizing remains quantity authority.
- Lot reconsideration unchanged except for consuming refined winner set.
- PIT/as-of constraints unchanged.
- Basis/accounting unchanged.
- Runtime lineage preserved without capital re-decision.

`NON_REGRESSION_TEST_PLAN_COMPLETE = YES`

`HISTORICAL_PROFITABILITY_USED_AS_IMPLEMENTATION_GATE = NO`

## Historical Entry Gate

Fresh Historical remains forbidden until all are true:

- all implementation slices complete,
- synthetic binding tests pass,
- production E2E acceptance passes,
- PIT audit passes,
- lineage persistence passes,
- `FINAL_PERMANENT_LEGACY_FALLBACK_COUNT = 0`,
- Safety / SELL / PM / quantity boundaries pass non-regression.

`HISTORICAL_ENTRY_GATE_DEFINED = YES`

`CURRENT_150BD_RUN_ROLE = BASELINE_CHARACTERIZATION_ONLY`

## Required Summary Output

`PRIMARY_JUDGMENT = PHASE31_G39_REFINED_CAPITAL_COMPETITION_IMPLEMENTATION_PLAN_READY`

`OPPORTUNITY_EVIDENCE_INVENTORY_COMPLETE = YES`

`OPPORTUNITY_EVIDENCE_OWNER_MATRIX_COMPLETE = YES`

`PC_CREATES_NEW_ALPHA_FEATURE = NO`

`OPPORTUNITY_QUALITY_OWNER = MARGINAL_CAPITAL_VALUE_AUTHORITY`

`OPPORTUNITY_QUALITY_PRODUCER_LOCATION = src/ai_fund_lab_v2/strategy/marginal_capital_value.py`

`DUPLICATE_QUALITY_AUTHORITY_CREATED = NO`

`OPPORTUNITY_CLASS_SEMANTIC_MATRIX_COMPLETE = YES`

`ALL_VALID_CLASSES_STRUCTURALLY_REACHABLE_BY_DESIGN = YES`

`WEAK_VALID_NOT_EQUIVALENT_TO_INVALID = YES`

`COMPARABLE_MARGINAL_DISTINCT = YES`

`STRONG_REQUIRES_EXPLICIT_POSITIVE_EVIDENCE = YES`

`MISSING_EVIDENCE_FAIL_CLOSED = YES`

`CASH_COMPETITOR_EVIDENCE_SCHEMA_DEFINED = YES`

`CASH_COMPARISON_METHOD = ORDERED_SEMANTIC_DOMINANCE_RULES`

`OUTCOME_OPTIMIZED_CASH_SCORE = NO`

`IMPLEMENTATION_BINDING_MATRIX_COMPLETE = YES`

`CAUTIOUS_GRADUAL_IMPLEMENTATION_DIFFERENCE_DEFINED = YES`

`PRESERVE_OPTIONALITY_IMPLEMENTATION_ROLE_DEFINED = YES`

`NEW_BUY_REFINED_FLOW_DEFINED = YES`

`ADD_REFINED_FLOW_DEFINED = YES`

`ADD_VALUE_EVIDENCE_REUSED = YES`

`REENTRY_REFINED_FLOW_DEFINED = YES`

`MULTI_COMPETITOR_CAPITAL_COMPETITION_DEFINED = YES`

`FINAL_CAPITAL_WINNER_OWNER = PORTFOLIO_CONSTRUCTION`

`SECOND_CAPITAL_WINNER_AUTHORITY = NO`

`POSITION_SIZING_BOUNDARY_PRESERVED = YES`

`LOT_RECONSIDERATION_CONTRACT_PRESERVED = YES`

`EXISTING_HOLDING_SELL_SEMANTICS_CHANGED = NO`

`BUY_SELL_INDEPENDENCE_PRESERVED = YES`

`SAFETY_AUTHORITY_CHANGED = NO`

`RUNTIME_CAPITAL_REDECISION = NO`

`REFINED_CAPITAL_LINEAGE_SCHEMA_DEFINED = YES`

`LEGACY_MIGRATION_MATRIX_COMPLETE = YES`

`FINAL_PERMANENT_LEGACY_FALLBACK_COUNT = 0`

`IMPLEMENTATION_SLICE_PLAN_COMPLETE = YES`

`SLICE_BEHAVIOR_CHANGE_MATRIX_COMPLETE = YES`

`PER_SLICE_ACCEPTANCE_MATRIX_COMPLETE = YES`

`SYNTHETIC_BINDING_TEST_PLAN_COMPLETE = YES`

`NON_REGRESSION_TEST_PLAN_COMPLETE = YES`

`HISTORICAL_PROFITABILITY_USED_AS_IMPLEMENTATION_GATE = NO`

`HISTORICAL_ENTRY_GATE_DEFINED = YES`

`CURRENT_150BD_RUN_ROLE = BASELINE_CHARACTERIZATION_ONLY`

`IMPLEMENTATION_CHANGE_EXECUTED = NO`

`CONFIG_CHANGE_EXECUTED = NO`

`THRESHOLD_CHANGE_EXECUTED = NO`

`FIXTURE_CHANGE_EXECUTED = NO`

`FRESH_RUN_EXECUTED = NO`

`RESUME_EXECUTED = NO`

`REPLAY_EXECUTED = NO`

`HISTORICAL_RERUN_EXECUTED = NO`

`LONG_HISTORICAL_EXECUTED = NO`

`GIT_DIFF_CHECK = PASS`

`NEXT_TASK_RECOMMENDATION = PHASE31_G40_OPPORTUNITY_QUALITY_PRODUCER_REACHABLE_CONTINUUM_IMPLEMENTATION`
