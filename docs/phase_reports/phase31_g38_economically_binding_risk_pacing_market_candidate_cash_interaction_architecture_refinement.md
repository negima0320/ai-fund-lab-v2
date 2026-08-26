# Phase31-G38 — Economically Binding Risk Pacing / Market-Candidate-Cash Interaction Architecture Refinement

## Scope

Task type: ARCHITECTURE DESIGN.

G38 did not implement code, change Strategy / Market Context / Portfolio Policy
/ Portfolio Construction / Position Sizing / Candidate Quality / BUY / ADD /
Re-entry / PM / SELL / Safety / Runtime behavior, change configuration, tune
thresholds, modify fixtures, run fresh Historical, resume, replay, or rerun
Historical.

The permanent architecture SoT was updated:

- `docs/02_architecture/dual_path_market_quality_and_capital_competition_contract.md`

## Primary Judgment

`PHASE31_G38_ECONOMICALLY_BINDING_RISK_PACING_ARCHITECTURE_REFINEMENT_DEFINED`

G38 defines a PIT-safe architecture refinement that makes Risk Pacing capable
of changing marginal capital deployment by construction. The design moves the
economic interaction to Portfolio Construction before final capital winner
selection, introduces a reachable graduated opportunity-quality continuum,
and makes Cash / Optionality a true competitor against marginal deployment.

No outcome-derived threshold, Historical-return optimization, fixed exposure
target, fixed BUY count, fixed position count, blanket market shutdown, second
quantity authority, or downstream Strategy re-decision is introduced.

## Inputs Read

- `docs/02_architecture/dual_path_market_quality_and_capital_competition_contract.md`
- `docs/phase_reports/phase31_g20_dual_path_production_architecture_contract_design.md`
- `docs/phase_reports/phase31_g21_dual_path_implementation_planning_migration_sequencing_acceptance_gates.md`
- `docs/phase_reports/phase31_g35_market_quality_risk_pacing_historical_activation_non_divergence_audit.md`
- `docs/phase_reports/phase31_g36_forward_pit_market_quality_risk_pacing_activation_search.md`
- `docs/phase_reports/phase31_g37_risk_pacing_binding_candidate_comparison_effectiveness_root_cause_audit.md`
- `src/ai_fund_lab_v2/strategy/market_context.py`
- `src/ai_fund_lab_v2/strategy/portfolio_policy.py`
- `src/ai_fund_lab_v2/strategy/portfolio_construction.py`
- `src/ai_fund_lab_v2/strategy/marginal_capital_value.py`
- Candidate / BUY quality / entry-admission and ADD investment evidence surfaces in `strategy_intelligence.py`, `position_management.py`, and `portfolio_construction.py`

## Authority Boundaries

The refinement preserves the existing owner map:

| Authority | Owner | G38 effect |
| --- | --- | --- |
| Market Quality | Market Context | Unchanged owner; evidence producer only. |
| Risk Pacing | Portfolio Policy | Unchanged owner; pacing intent only. |
| Capital competition / final no-deployable | Portfolio Construction | Refined to include pre-final market-candidate-cash interaction. |
| Candidate admission / BUY Quality | Existing candidate quality producers | Remain eligibility / quality evidence owners. |
| ADD / HOLD / REDUCE / EXIT intent | PM | Unchanged; ADD becomes competitor only after PM-owned intent/evidence. |
| Discrete quantity | Position Sizing | Unchanged. |
| Safety | Safety | Unchanged hard boundary. |
| Runtime / Pending / Submit / Execution | Runtime authorities | Consume lineage; no capital re-decision. |

`AUTHORITY_BOUNDARIES_PRESERVED = YES`

## Refined Decision Stage

Current defect from G37:

```text
candidate quality / accepted weight mostly decided
  -> Risk Pacing late binary block
  -> COMPARABLE and STRONG bypass non-normal pacing
```

Refined stage:

```text
Market Context Market Quality
  -> Portfolio Policy Risk Pacing
  -> Portfolio Construction pre-final interaction
  -> NEW_BUY / ADD / CASH final semantic winner
  -> Position Sizing discrete quantity
```

Portfolio Construction consumes authoritative evidence only. It does not create
Market Quality, Risk Pacing, alpha features, or PM intent.

`MARKET_CANDIDATE_INTERACTION_STAGE = BEFORE_FINAL_CAPITAL_WINNER`

`RISK_PACING_IS_SECOND_CANDIDATE_FILTER = NO`

## Opportunity Quality Continuum

The current `STRONG / COMPARABLE / WEAK / INSUFFICIENT / BLOCKED` scheme is
refined into a semantic continuum suitable for capital competition:

| Refined class | Meaning | Valid opportunity | Cash can beat under weak markets |
| --- | --- | --- | --- |
| `STRONG` | Explicit PIT evidence supports exceptional or high-conviction incremental deployment. | YES | Usually NO, unless other authorities block. |
| `COMPARABLE_HIGH` | Valid opportunity with above-normal but not exceptional evidence. | YES | Sometimes, especially under preserve optionality. |
| `COMPARABLE_MARGINAL` | Valid but close enough to optionality that market weakness can make Cash preferable. | YES | YES. |
| `WEAK_VALID` | Strategically eligible but marginal; not rejected, not missing, not hard blocked. | YES | YES. |
| `INSUFFICIENT` | Required comparison evidence is missing, stale, contradictory, or lineage-incomplete. | NO for incremental deployment. | YES / fail closed. |
| `BLOCKED` | Admission, PM, Safety, eligibility, or feasibility blocks deployment. | NO. | YES / blocked. |

`WEAK_VALID` and `COMPARABLE_MARGINAL` are the key repair. They are valid
investment opportunities, not invalid candidates. They create the state-space
where normal markets may deploy, caution may preserve Cash, and preserve mode
can defer.

`GRADUATED_WEAK_OPPORTUNITY_CLASS_DEFINED = YES`

`GRADUATED_WEAK_CLASS_STRUCTURALLY_REACHABLE = YES`

## Existing PIT Evidence Source of Truth

G38 reuses existing PIT evidence first:

- `runtime_opportunity_score`, opportunity rank, expected-edge evidence
- entry admission action, state, evidence sufficiency, and quality bias
- BUY Quality action and hard / soft reason families
- ADD expected-edge improvement, incremental investment value, opportunity cost, and add-worthiness
- re-entry eligibility once symbol-local eligibility is satisfied
- portfolio context, concentration, lot feasibility, residual capital, and current holdings as PC context

No new feature is mandated in G38. If later implementation cannot define the
continuum from existing PIT evidence without duplicating a producer, a later
design task may propose a new feature with lineage and acceptance tests.

`EXISTING_PIT_FEATURES_REUSED_FIRST = YES`

`NEW_FEATURE_REQUIRED = DEFERRED`

`PRODUCTION_THRESHOLD_VALUES_SELECTED_IN_G38 = NO`

`OUTCOME_TUNED_DESIGN = NO`

## Market x Candidate Interaction Matrix

| Risk Pacing intent | `STRONG` | `COMPARABLE_HIGH` | `COMPARABLE_MARGINAL` | `WEAK_VALID` | `INSUFFICIENT` | `BLOCKED` |
| --- | --- | --- | --- | --- | --- | --- |
| `NORMAL_DEPLOYMENT` | deploy may win | deploy may win | deploy may win | deploy may win if best valid use of capital | fail closed | blocked |
| `GRADUAL_REDEPLOYMENT` | deploy may win | selective deploy may win | Cash may win unless portfolio fit or ADD value is confirmed | Cash preferred | fail closed | blocked |
| `CAUTIOUS_DEPLOYMENT` | deploy may win with explicit symbol-specific evidence | Cash may win unless evidence is strong enough for caution | Cash preferred | Cash preferred | fail closed | blocked |
| `PRESERVE_OPTIONALITY` | deploy may win only if exceptional and complete | Cash preferred | Cash preferred | Cash preferred | fail closed | blocked |

This matrix proves by construction:

- NORMAL can allow a valid marginal opportunity.
- CAUTIOUS can prefer Cash over the same marginal opportunity.
- GRADUAL differs from CAUTIOUS by permitting selective re-risk for high-quality comparable evidence.
- PRESERVE makes Cash the default winner except against exceptional complete evidence.
- Strong opportunities can still deploy in weak markets.

`MARKET_CANDIDATE_INTERACTION_MATRIX_DEFINED = YES`

`CAUTIOUS_GRADUAL_ECONOMIC_DIFFERENCE_DESIGNED = YES`

`STRONG_OPPORTUNITY_CAN_OVERRIDE_CAUTION = YES`

`BLANKET_MARKET_BUY_BAN = NO`

## Cash as True Competitor

Cash / Optionality is redesigned as a pre-final economic competitor, not merely
the residual after candidate failure.

Cash value may derive from:

- Market Quality and Risk Pacing intent
- recovery confirmation, breadth weakness, and conflicted structure evidence
- portfolio concentration and existing exposure composition
- availability of stronger NEW_BUY or ADD alternatives
- opportunity quality class and evidence completeness
- lot and residual feasibility

Cash must not use later PnL, Historical outcome, MFE / MAE, performance-tuned
scores, or fixed exposure targets. Cash can win with reason evidence such as
`OPTIONALITY_PREFERRED_TO_MARGINAL_COMPETITOR` or
`CAUTIOUS_MARKET_CASH_BEATS_MARGINAL_OPPORTUNITY`.

`CASH_IS_TRUE_ECONOMIC_COMPETITOR_DESIGNED = YES`

`FIXED_EXPOSURE_TARGET_INTRODUCED = NO`

## Existing Holdings, ADD, and Re-entry

Risk Pacing governs incremental deployment preference. It does not
automatically liquidate existing winners. HOLD / REDUCE / EXIT remain PM-owned.

ADD competes in the same framework as NEW_BUY and Cash. A strong existing
winner may receive ADD during caution, while a marginal ADD may lose to Cash.
Neither ADD nor NEW_BUY has automatic priority.

Re-entry remains symbol-local eligibility. Once eligible, it competes under the
same current capital competition with no permanent discount or bonus merely
because it is a re-entry.

`RISK_PACING_FORCES_EXISTING_POSITION_EXIT = NO`

`ADD_MARKET_CANDIDATE_INTERACTION_DEFINED = YES`

`ADD_AUTOMATIC_PRIORITY = NO`

`NEW_BUY_AUTOMATIC_PRIORITY = NO`

`REENTRY_CAPITAL_COMPETITION_CONSISTENT = YES`

## Progressive Re-risking and Recovery Quality

Progressive re-risking is represented by marginal capital preference, not fixed
daily quotas or fixed waiting periods:

- `PRESERVE_OPTIONALITY`: Cash defeats most marginal deployment unless evidence is exceptional and complete.
- `GRADUAL_REDEPLOYMENT`: selective deployment can resume for strong or high-quality comparable opportunities; marginal comparable opportunities may defer.
- `NORMAL_DEPLOYMENT`: ordinary competition may deploy valid comparable and weak-valid candidates when they are the best current use of capital.

`RECOVERY_CONFIRMATION_INCOMPLETE` differs economically from `HEALTHY_RECOVERY`:
the same marginal candidate can defer under incomplete recovery and deploy
under healthy recovery.

The design also preserves:

- BULL direction with weak internals can reduce marginal deployment.
- BEAR direction with exceptional symbol evidence can still selectively deploy.

`PROGRESSIVE_RERISKING_WITHOUT_FIXED_HOLD_PERIOD = YES`

`RECOVERY_QUALITY_ECONOMIC_DIFFERENCE_DESIGNED = YES`

`BULL_WEAK_INTERNALS_CAN_REDUCE_DEPLOYMENT = YES`

`BEAR_STRONG_OPPORTUNITY_CAN_DEPLOY = YES`

## Fail-Closed and Downstream Boundary

Missing Market Quality or comparison evidence fails closed for incremental
deployment. Missing data must not silently become `COMPARABLE`.

Portfolio Construction selects the semantic capital winner. Position Sizing
remains the only discrete quantity owner. Runtime / Pending / Submit /
Execution preserve and consume lineage but cannot re-run capital competition.

`INCOMPLETE_EVIDENCE_INCREMENTAL_DEPLOYMENT_FAIL_CLOSED = YES`

`SECOND_DISCRETE_QUANTITY_AUTHORITY = NO`

`POSITION_SIZING_REMAINS_QUANTITY_OWNER = YES`

`DOWNSTREAM_CAPITAL_REDECISION_ALLOWED = NO`

## Economic Binding State Space

G38 defines both acceptance properties required to prove real binding:

| Proof | Required behavior |
| --- | --- |
| Same candidate / different market | A valid marginal candidate can deploy under NORMAL and lose to Cash under CAUTIOUS or PRESERVE. |
| Same market / different candidate | Under the same CAUTIOUS market, a strong candidate can deploy while a marginal candidate loses to Cash. |

`ECONOMIC_BINDING_STATE_SPACE_COMPLETE = YES`

`SAME_CANDIDATE_DIFFERENT_MARKET_CAN_CHANGE_DECISION = YES`

`SAME_MARKET_DIFFERENT_CANDIDATE_CAN_CHANGE_DECISION = YES`

## Synthetic PIT Acceptance Matrix

Mandatory future implementation tests:

| Case | Input | Expected semantic outcome |
| --- | --- | --- |
| A | `NORMAL_DEPLOYMENT + COMPARABLE_MARGINAL` | deploy allowed / may win |
| B | same marginal candidate + `CAUTIOUS_DEPLOYMENT` | Cash may win |
| C | `GRADUAL_REDEPLOYMENT + COMPARABLE_HIGH` | selective deploy may win |
| D | `PRESERVE_OPTIONALITY + COMPARABLE_MARGINAL` | Cash wins |
| E | `CAUTIOUS_DEPLOYMENT + STRONG` | deployment may still win |
| F | `RECOVERY_CONFIRMATION_INCOMPLETE + marginal candidate` | slower or Cash-preferred deployment |
| G | `HEALTHY_RECOVERY + same candidate` | stronger deployment preference |
| H | Market Quality missing | incremental fail-closed |

`SYNTHETIC_BINDING_ACCEPTANCE_MATRIX_DEFINED = YES`

## Migration Matrix

| Current semantic | Classification | Target |
| --- | --- | --- |
| Unreachable `ELIGIBLE_WEAK` | MODIFY | Replace or map to reachable `WEAK_VALID` / `COMPARABLE_MARGINAL` semantics. |
| Current CAUTIOUS/GRADUAL truth table | MODIFY | CAUTIOUS and GRADUAL must differ economically. |
| Cash residual-only behavior | MODIFY | Cash becomes a true pre-final competitor. |
| Post-selection Risk Pacing block | MODIFY | Move interaction before final capital winner. |
| Candidate prefilter interaction | KEEP/MODIFY | Keep eligibility authority; expose enough quality evidence for PC competition. |
| Candidate admission hard blocks | KEEP | Risk Pacing must not rescue invalid or blocked candidates. |
| ADD automatic priority absence | KEEP | ADD still competes; no automatic priority. |
| Re-entry symbol-local eligibility | KEEP | Eligible re-entry enters the same competition. |
| Position Sizing quantity ownership | KEEP | No second quantity authority. |
| Downstream lineage consumption | KEEP | Runtime does not reinterpret Strategy capital competition. |
| Permanent old non-binding path | REMOVE | No permanent parallel or fallback path after migration. |

`MIGRATION_MATRIX_COMPLETE = YES`

`PERMANENT_PARALLEL_RISK_PACING_PATH_ALLOWED = NO`

`PERMANENT_FALLBACK_TO_NON_BINDING_PATH_ALLOWED = NO`

## Staged Implementation Plan

Recommended follow-up sequence:

1. Repair opportunity-quality classification design so `COMPARABLE_HIGH`, `COMPARABLE_MARGINAL`, and `WEAK_VALID` are reachable from PIT evidence.
2. Design and implement Cash as a true economic competitor without fixed exposure targets.
3. Add Portfolio Construction market-candidate-cash interaction before final winner selection.
4. Differentiate CAUTIOUS and GRADUAL economic semantics.
5. Verify ADD and re-entry enter the same competition without automatic priority.
6. Add focused synthetic PIT binding acceptance tests.
7. Run production E2E acceptance.
8. Only after acceptance, run fresh Historical validation.

`STAGED_IMPLEMENTATION_PLAN_DEFINED = YES`

## Current 150BD Run Role

The active 150BD validation remains useful as baseline characterization of the
currently non-binding architecture. It must not be used to choose thresholds or
optimize the refined design.

`CURRENT_RUN_ROLE = BASELINE_CHARACTERIZATION_ONLY`

## Required Summary Output

`PRIMARY_JUDGMENT = PHASE31_G38_ECONOMICALLY_BINDING_RISK_PACING_ARCHITECTURE_REFINEMENT_DEFINED`

`AUTHORITY_BOUNDARIES_PRESERVED = YES`

`MARKET_CANDIDATE_INTERACTION_STAGE = BEFORE_FINAL_CAPITAL_WINNER`

`GRADUATED_WEAK_OPPORTUNITY_CLASS_DEFINED = YES`

`GRADUATED_WEAK_CLASS_STRUCTURALLY_REACHABLE = YES`

`RISK_PACING_IS_SECOND_CANDIDATE_FILTER = NO`

`MARKET_CANDIDATE_INTERACTION_MATRIX_DEFINED = YES`

`CAUTIOUS_GRADUAL_ECONOMIC_DIFFERENCE_DESIGNED = YES`

`STRONG_OPPORTUNITY_CAN_OVERRIDE_CAUTION = YES`

`BLANKET_MARKET_BUY_BAN = NO`

`CASH_IS_TRUE_ECONOMIC_COMPETITOR_DESIGNED = YES`

`FIXED_EXPOSURE_TARGET_INTRODUCED = NO`

`RISK_PACING_FORCES_EXISTING_POSITION_EXIT = NO`

`ADD_MARKET_CANDIDATE_INTERACTION_DEFINED = YES`

`ADD_AUTOMATIC_PRIORITY = NO`

`NEW_BUY_AUTOMATIC_PRIORITY = NO`

`REENTRY_CAPITAL_COMPETITION_CONSISTENT = YES`

`PROGRESSIVE_RERISKING_WITHOUT_FIXED_HOLD_PERIOD = YES`

`RECOVERY_QUALITY_ECONOMIC_DIFFERENCE_DESIGNED = YES`

`BULL_WEAK_INTERNALS_CAN_REDUCE_DEPLOYMENT = YES`

`BEAR_STRONG_OPPORTUNITY_CAN_DEPLOY = YES`

`INCOMPLETE_EVIDENCE_INCREMENTAL_DEPLOYMENT_FAIL_CLOSED = YES`

`EXISTING_PIT_FEATURES_REUSED_FIRST = YES`

`NEW_FEATURE_REQUIRED = DEFERRED`

`PRODUCTION_THRESHOLD_VALUES_SELECTED_IN_G38 = NO`

`ECONOMIC_BINDING_STATE_SPACE_COMPLETE = YES`

`SYNTHETIC_BINDING_ACCEPTANCE_MATRIX_DEFINED = YES`

`SAME_CANDIDATE_DIFFERENT_MARKET_CAN_CHANGE_DECISION = YES`

`SAME_MARKET_DIFFERENT_CANDIDATE_CAN_CHANGE_DECISION = YES`

`SECOND_DISCRETE_QUANTITY_AUTHORITY = NO`

`POSITION_SIZING_REMAINS_QUANTITY_OWNER = YES`

`DOWNSTREAM_CAPITAL_REDECISION_ALLOWED = NO`

`MIGRATION_MATRIX_COMPLETE = YES`

`PERMANENT_PARALLEL_RISK_PACING_PATH_ALLOWED = NO`

`PERMANENT_FALLBACK_TO_NON_BINDING_PATH_ALLOWED = NO`

`PERMANENT_SOT_UPDATED = YES`

`STAGED_IMPLEMENTATION_PLAN_DEFINED = YES`

`CURRENT_RUN_ROLE = BASELINE_CHARACTERIZATION_ONLY`

`OUTCOME_TUNED_DESIGN = NO`

`IMPLEMENTATION_CHANGE_EXECUTED = NO`

`CONFIG_CHANGE_EXECUTED = NO`

`THRESHOLD_CHANGE_EXECUTED = NO`

`FRESH_RUN_EXECUTED = NO`

`RESUME_EXECUTED = NO`

`REPLAY_EXECUTED = NO`

`HISTORICAL_RERUN_EXECUTED = NO`

`LONG_HISTORICAL_EXECUTED = NO`

`GIT_DIFF_CHECK = PASS`

`NEXT_TASK_RECOMMENDATION = PHASE31_G39_OPPORTUNITY_QUALITY_AND_TRUE_CASH_COMPETITION_IMPLEMENTATION_PLANNING`
