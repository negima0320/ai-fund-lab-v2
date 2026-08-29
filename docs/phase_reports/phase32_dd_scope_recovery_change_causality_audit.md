# Phase32-DD — Phase32 Scope Recovery / Change Causality Audit

## Executive Summary

This READ-ONLY audit reconstructs Phase32 from Phase31 closure through Phase32-DC. No production code, config, runtime state, threshold, weight, rank, Cash policy, exposure target, fresh-run, resume, replay, or backtest was changed or executed.

Phase31 closed with the Strategy/performance baseline accepted and Phase32 explicitly handed off as Demo / Production readiness. The Phase31 closure documents are clear that high-resolution marginal value and portfolio rotation were `DEFERRED_OPTIONAL`, and that performance tuning was not a default Phase32 objective.

Phase32 initially pursued plausible production-correctness work: REENTRY prior-exit context, campaign identity, pending/order/execution provenance, safety taxonomy, and accepted-artifact authority. Those belong in Production readiness because they fix PIT, lineage, fail-closed, and authority-consumption defects.

The primary scope drift starts when the Phase31-deferred high-resolution / common marginal capital frontier became a Phase32 shadow implementation and then a production-shaped, budget-bounded, active PC-to-PS consumer path. That migration produced real correctness benefits, but it also changed investment behavior: NEW/REENTRY admission, target magnitude, one-lot treatment, ADD admission, Cash competition, and PM lifecycle context. Much of the later Phase32 work is a regression tree rooted in that active frontier migration.

Phase32 should not blanket-roll back. Several fixes are mandatory to keep: PIT provenance, campaign identity, REENTRY context materialization, safety taxonomy, BF-only target authority, Cash unit correctness, PIT flags, quantity/cap invariants, entry-premise lineage, and blocked-candidate acceptance invariants. The scope recovery action is to freeze correctness, classify new strategy/capital semantics for review, and defer further performance-oriented redesign out of Phase32 unless a concrete Production correctness defect is proven.

## Original Phase32 Scope

Authoritative source:

- `docs/phase_reports/phase31_g139_phase31_final_closure_performance_improvement_completion.md`
- `docs/phase_reports/phase31_final_summary_and_phase32_handoff.md`
- `docs/phase_reports/phase31_to_phase32_chatgpt_handoff.md`

Phase31 final state:

- `CURRENT_STRATEGY_BASELINE_ACCEPTED = YES`
- `PERFORMANCE_IMPROVEMENT_TRACK_STATUS = COMPLETED_FOR_CURRENT_RELEASE_BASELINE`
- `UNRESOLVED_MANDATORY_PERFORMANCE_DEFECT = NO`
- `HIGH_RESOLUTION_VALUE_STATUS = DEFERRED_OPTIONAL`
- `PORTFOLIO_ROTATION_STATUS = DEFERRED_OPTIONAL`
- `NEXT_PRIMARY_OBJECTIVE = DEMO_AND_PRODUCTION_READINESS`

Phase32 entry contract:

- prepare Demo / production-equivalent operation;
- validate broker connectivity, account/cash/position authority, order planning, submit/cancel/fill lifecycle, reconciliation, corporate actions, restart/resume idempotency, pending-order safety, observability, daily workflow, alerts, manual intervention, production configuration separation, secrets, audit trail, rollback, and migration gates;
- preserve canonical Runtime / Strategy / Safety authorities;
- do not reopen performance optimization by default;
- Strategy modifications require real defect evidence or an explicitly approved new performance initiative;
- long Historical execution remains user-operated;
- no production activation or real order submission without explicit approval.

Therefore the original Phase32 purpose was not to redesign capital allocation or investment semantics. Correctness repairs were allowed when actual artifacts proved an authority, PIT, ledger, campaign, safety, or operational defect.

## Scope Judgment

Phase32 current status: `SCOPE_REPURPOSED`.

Rationale:

- Early Phase32 correctness work remained compatible with Production readiness.
- Phase32-A through M reopened performance/capital-causality questions that Phase31 had closed or deferred.
- Phase32-AQ through BG moved a deferred optional high-resolution marginal-capital concept into production-shaped and then active Production authority.
- Phase32-BU through DC then spent many tasks repairing or characterizing behavior changes caused by that migration.

This is stronger than ordinary `SCOPE_EXPANDED`: the dominant Phase32 workstream became investment-behavior architecture migration, not Demo / Production operational readiness.

## Change Ledger

| Unit | Task(s) | Triggering evidence | Change summary | Affected authority | Production behavior changed | Classification | Downstream regressions / current status |
|---|---|---|---|---|---|---|---|
| Prior-exit context bridge | K-L | REENTRY rows saw bare `EXIT` / `GENERIC` instead of PM reason | Materialize strict-prior PM exit reason context | REENTRY / PC prior-exit state | Partial / intended semantic repair | A | Initially missed actual path due ledger provenance gaps; kept |
| Persistent execution/order provenance | Q/R/T/X/Y/AA | PM reason/campaign lineage dropped before strict-prior bridge | Preserve source decision ids and campaign ids through pending/order/execution | Pending / Submit / Ledger / PM bridge | No Strategy threshold change | A | Required several actual-path repairs; kept |
| PM runtime adapter registry refresh | U/V | accepted artifact hash mismatch halted day-0 | Formal registry refresh for changed PM adapter | Accepted Artifact Registry | No behavior change | A | Kept |
| Canonical campaign identity unification | AC/AD | multiple campaign id generators and split Current/PM/execution identities | Unify canonical campaign identity propagation | Campaign lifecycle / PM / ledger | No intended Strategy change | A | Kept |
| REENTRY safety taxonomy | AF/AG/AH/AI | positive broker/safety support codes treated as safety blocks | Replace substring collision with structured safety taxonomy | REENTRY safety predicate | Yes, removes false blocks | A | Actual 83060 REENTRY accepted; kept |
| Shadow common frontier | AQ/AR/AS | ADD scarcity and capital-value resolution loss | Implement `canonical_marginal_capital_frontier.v1` shadow-only | PC shadow research | No | C | Useful diagnostic, but optional architecture; keep non-authoritative |
| Shadow Cash resolver | AT/AU | shadow Cash read as 0 / false insufficient Cash | PIT-safe shadow cash source resolver | Shadow frontier | No | D | Repair caused by shadow implementation; kept for diagnostics |
| Production-shaped marginal authority | AY/AZ | desire to migrate shadow frontier toward PS-compatible target gap | Create `canonical_marginal_capital_frontier_authority.v1`, consumer disabled | PC capital value / target gap | No at AZ | C | Created migration path beyond original scope |
| Budget-bounded authority | BA/BB/BC/BD | unbounded dual-read produced 490 targets / 374 production-zero authority-positive cases | Add allocation budget, acceptance sequence, explicit Cash allocation | PC allocation budget | No at BC | C | Became basis for active switch |
| PC-to-PS boundary validator | BE/BF | need dry-run aggregation and no legacy fallback | Aggregate accepted lots to PS-compatible symbol/campaign targets | PC-to-PS boundary | No at BF | C | Basis for active switch |
| Active BG consumer switch | BG | explicit switch of BF rows as sole Production target authority | PS consumes BF aggregated targets | PC / PS boundary | Yes | C | Root parent for zero-buy, NEW drift, ADD/value-class, sizing cascades |
| Cash/budget notional repair | BK/BL/BN | active path used weight `0.74` as cash notional | Resolve actual Cash notional from runtime payload | PC authority Cash source | Yes, restores deployment | D | Regression from BG active path; kept |
| Discrete quantity PIT flags | BO | submit feasibility blocked all BUY due missing PIT flags | Add `future_information_used=false`, `historical_outcome_used=false` | PC discrete quantity authority / submit feasibility | Yes, restores submit eligibility | D | Regression from BF/BG authority materialization; kept |
| ADD repeated-lot quantity consistency | BQ/BR | ADD lots advanced by trading unit not accepted incremental quantity | Enforce `pre_quantity(N+1)=post_quantity(N)` | ADD lot authority / BF aggregation | Yes for ADD targets | D | Regression from multi-lot ADD; kept |
| Effective concentration cap propagation | BS/BT | ADD used Safety 25% fallback, missing Strategy 18% effective cap | Resolve min(strategy cap, safety hard cap) per lot | PC feasibility / cap | Yes for cap-crossing ADD | D | Regression from multi-lot frontier; kept |
| NEW/REENTRY admission restoration | BU/BV | active BG promoted legacy zero/non-deployable NEW rows | Require existing PC production admission before BF/PS target | NEW/REENTRY admission | Yes, restores old boundary | D | Keep |
| ADD admission and BF-only authority | BX/BY/BZ | FAIL_CLOSED ADD accepted; residual ADD filled without BF target | Require ADD evidence PASS and BF target for BUY_ADD | ADD admission / PS Runtime boundary | Yes | A | Correctness fix; kept |
| NEW/REENTRY target magnitude multi-lot | CA/CB/CC | one-lot compression of PC target magnitude | Expand PC-authorized NEW/REENTRY target into lots | NEW/REENTRY sizing | Yes | D | Restores magnitude but led to early reductions and quality ceiling work |
| Adaptive Buy Quality target preservation | CE/CF/CG/CH | Buy Quality reduced targets re-expanded to base targets | Make quality-authorized target a hard upper bound | Buy Quality / PC target | Yes | A | Correctness by authority preservation; caused two-buy collapse |
| Lot-aware zero-collapse repair | CI/CJ | quality-feasible 89180/76470 zeroed before BF | Prevent legacy lot-aware stage from zeroing >=1-lot quality target | PC lot-aware / BF | Yes | D | Regression from CH; kept |
| One-lot authority migration | CK/CL/CM/CN/CO | high-price sub-lot targets blocked after CH/CJ; Phase30 authority partially existed | Migrate explicit minimum executable one-lot authority | PC one-lot authority | Yes | B | Required CQ/CS repair |
| One-lot pre-zero materialization | CP/CQ | sub-lot rows zeroed before one-lot authority object existed | Evaluate one-lot authority before zeroing | PC one-lot / CC | Yes | D | Regression from CO integration; kept |
| One-lot representability repair | CR/CS | `COMPARABLE_MARGINAL` categorically blocked before common frontier | Separate representability from final competition | PC one-lot / frontier | Yes | D | Repairs CO overstrictness; keep under review |
| Entry premise PM context | CT/CU/CV/CW | PM reused entry-known caution as fresh deterioration in some paths | Add campaign entry premise snapshot and PM delta context | PM lifecycle | Yes | C | New semantic improvement; caused lineage HALT |
| Entry premise lineage persistence | CX/CY | all day-1 campaign snapshots REVIEW_REQUIRED due sparse fill lineage | Build snapshot from authoritative same-run entry lineage | Campaign lifecycle / PM prerequisite | Yes, restores continuity | D | Regression from CW; kept |
| Blocked candidate acceptance invariant | CZ/DA/DB | BLOCKED / desirability REVIEW_REQUIRED ADD reached BF/PS/runtime/fill | Reject blocked/non-PASS value-class candidates at frontier/BF/runtime | PC frontier / BF / runtime defensive invariant | Yes | A | Mandatory correctness; kept |

## Classification Counts

Counts are by the major change units in the ledger above, not by every audit-only report.

| Class | Count | Meaning in Phase32-DD |
|---|---:|---|
| A — `PRODUCTION_CORRECTNESS_REQUIRED` | 8 | Must keep; repairs unsafe authority, PIT, lineage, fail-open, or blocked-decision execution defects |
| B — `REQUIRED_ARCHITECTURE_MIGRATION` | 1 | Existing accepted architecture required migration into the new path; should keep with semantic review |
| C — `NEW_PHASE32_STRATEGY_OR_CAPITAL_SEMANTICS` | 7 | New or newly-active strategy/capital semantics beyond original Phase32 Production-readiness scope |
| D — `REGRESSION_REPAIR_CAUSED_BY_PHASE32_CHANGE` | 11 | Repairs caused by the C/B migration chain, especially active frontier/BF/PS/PM lifecycle integration |

## Dependency / Regression Tree

### REENTRY / Prior-Exit

Prior-exit context defect:

```text
K/L strict-prior PM reason bridge
  -> actual path still GENERIC because persistent provenance was dropped
  -> Q/R/T/X/Y/AA ledger/pending/order provenance repairs
  -> AC/AD campaign identity convergence
  -> AF/AG/AH/AI safety taxonomy false-positive repairs
  -> AJ actual 83060 REENTRY accepted
```

Root classification: correctness. Keep.

### Common Marginal Frontier / BF-PS Switch

Deferred architecture became production-active:

```text
Phase31 G136/G139 high-resolution marginal value = DEFERRED_OPTIONAL
  -> AQ/AR/AS shadow common frontier
  -> AY/AZ production-shaped authority, consumer disabled
  -> BA/BB/BC budget-bounded acceptance
  -> BE/BF PS boundary aggregation
  -> BG active PC-to-PS consumer switch
     -> BI/BK zero-buy actual path
        -> BL Cash notional unit repair
        -> BO PIT flag repair
     -> BQ/BR ADD multi-lot quantity repair
     -> BS/BT effective cap repair
     -> BU/BV NEW admission restoration
     -> BX/BY/BZ ADD PASS-only / BF-only repair
     -> DA/DB blocked value-class acceptance invariant
```

Root classification: C for the active migration, D/A for repairs. This is the primary scope drift branch.

### NEW/REENTRY Sizing / Buy Quality / One-Lot

```text
BG active frontier uses BF lots as Production target authority
  -> CA finds one-lot compression of PC target magnitude
  -> CB/CC restores NEW/REENTRY multi-lot target magnitude
  -> CE/CF/CG find Buy Quality reduction re-expansion
  -> CH enforces quality-authorized target upper bound
     -> CI two-buy collapse
     -> CJ repairs >=1-lot quality target zero-collapse
     -> CK/CL identify sub-lot one-lot semantic gap
     -> CM/CN/CO migrate Phase30 one-lot authority
        -> CP/CQ repair pre-zero materialization
        -> CR/CS remove COMPARABLE_MARGINAL categorical pre-frontier block
```

This tree mixes correctness and new semantics. Buy Quality authority preservation is a correctness repair, but the active common-frontier representation forced old discrete-lot behavior to be reinterpreted.

### PM Lifecycle / Entry Premise

```text
CT/CU show early capital exits and entry-known caution reuse
  -> CV/CW add entry premise snapshot and PM delta context
     -> CX day-1 HALT because snapshots lacked authoritative lineage
     -> CY connects same-run entry lineage and restores snapshot PASS
```

CW is new PM semantic context, not part of original Demo/Production readiness by default. CY is a necessary repair once CW exists.

## Phase31 Accepted Behavior Vs Current Post-DB Behavior

| Axis | Phase31 accepted behavior | Current Post-DB behavior | Preservation |
|---|---|---|---|
| Candidate selection | Momentum-follow, credible decision-time strength | Candidate universe still broad; not main loss point | Preserved |
| Production admission | PC owns deployability; no forced full investment | BV restored admission boundary after BG drift | Partial |
| Initial target magnitude | PC target / PS quantity chain accepted; some coarse resolution | CC multi-lot restores magnitude, CH bounds by Buy Quality, one-lot path explicit | Partially migrated |
| One-lot treatment | Phase30 explicit authority existed; implicit behavior also present in old path | CO/CQ/CS migrate explicit one-lot authority into common frontier | Partial |
| NEW breadth | Accepted baseline could deploy broader Day-0 capital | Current DC raw NEW remains broad but BF NEW sparse | Drifted |
| ADD intent | Selective ADD when incremental opportunity valid | PM ADD intent persists, but ADD evidence often non-PASS | Partially lost at capital acceptance |
| ADD acceptance | G129 repaired BUY_ADD actual path; contribution unproven but accepted | BZ/DB make ADD stricter; DC accepted ADD near zero in window | Drifted / review |
| Winner capitalization | Accepted philosophy: retain and selectively ADD winners | DC shows 94320 PM ADD intent not capitalized | Partial |
| PM retention | REDUCE/EXIT on deterioration, retain continuation | CW/CY add entry premise context; DC still shows sell-led exposure collapse | Partial |
| REDUCE/EXIT | Keep hard stop / true breakdown / deterioration exits | Preserved; no evidence to weaken by default | Preserved |
| Cash optionality | First-class, no forced full investment | Preserved, but residual Cash dominates when security funnel sparse | Preserved with side effect |
| Capital recycling | PC-owned capital budget and allocation | Active frontier recycles through BF but often leaves residual Cash | Partial |
| Exposure behavior | No fixed exposure target; could be high when valid opportunities exist | DC persistent avg exposure 16.91% despite BULL display and large budget | Drifted / under review |

PHASE31 investment semantics are therefore `PARTIAL`, not `NO`: core PIT/authority/fail-closed philosophy is stronger, but capital deployment behavior is materially changed.

## DC Underdeployment Root Mapping

| DC root | Pre-Phase32? | Phase32 relation | Current interpretation |
|---|---|---|---|
| PM REDUCE/EXIT wave | PM sell behavior pre-existed; CW/CY later changed context availability | Not clearly caused by BG/DB; must classify exits as hard/fresh/persistent before calling defect | `PM_RETENTION_MATERIAL`, but not proven over-sell |
| Production-deployable NEW scarcity | Some admission/cash/lot scarcity pre-existed; BG/CH/CJ/CO/CS changed boundaries | Strengthened/migrated by active frontier, Buy Quality hard cap, explicit one-lot authority, cap propagation | Material current drift; review required |
| ADD evidence/admission suppression | ADD scarcity existed in Phase31/AQ; Phase32 BZ/DB made PASS/value-class invariants stricter | PM intent now clearly not sufficient; expected_edge/incremental_value non-PASS blocks 94320 | Review ADD evidence bridge, not threshold tuning |
| Buy Quality / lot / cap filtering | Buy Quality and Phase30 one-lot existed; CH/CO made semantics stricter and explicit | Partly correctness, partly new strictness | Review discrete-lot authority semantics |
| Residual Cash | Cash first-class pre-existed and was accepted | BG/BC explicit Cash allocation makes residual visible; not direct hard blocker | Cash mostly residual after sparse accepted securities |

## ADD Suppression History

Phase31 accepted selective ADD and G129 repaired BUY_ADD actual-path mechanics, but Phase31 also left high-resolution ADD/new/cash value as deferred optional architecture. Phase32 AQ found the ADD first major drop-off at PM ADD intent to positive accepted incremental target / target gap and did not classify it as a new mandatory defect.

The expected-edge / incremental-value requirement enters the current path through the Phase32 common marginal frontier and ADD investment evidence integration. In DC, 94320 had PM `ADD` with `strong_trend_continuation`, `opportunity_rank_still_high`, and `no_loss_averaging`, but each ADD lot was `INELIGIBLE_ADD_ADMISSION_BLOCKED` because `expected_edge` and `incremental_value` were missing or non-PASS.

This means the current requirement is not merely the old Phase31 G129 execution repair. It is a Phase32 capital-value semantic requirement attached to the active Production target authority. The requirement is architecturally plausible, but its evidence bridge appears under-materialized for persistent ADD campaigns. That should be reviewed as an authority/materialization gap before changing ADD thresholds.

## NEW Deployability Scarcity History

| Gate | Origin classification | Notes |
|---|---|---|
| Production admission blocked | PRE_EXISTING + REGRESSION_REPAIR | BV restored old zero/non-deployable protection after BG promoted too many rows |
| Quality target below lot | PHASE32_STRENGTHENED + MIGRATED | CH made Buy Quality target a hard upper bound; CO/CQ/CS migrated explicit one-lot treatment |
| Cap blocked | PRE_EXISTING + PHASE32_STRENGTHENED | BT propagated effective Strategy cap instead of Safety fallback |
| Infeasible lot | PRE_EXISTING + MIGRATED | Discrete-lot reality pre-existed, now exposed in common frontier |
| Desirability REVIEW/BLOCK | PHASE32_NEW / STRENGTHENED | DB makes non-PASS desirability fatal before acceptance |
| Buy Quality WAIT | PRE_EXISTING | Correctly blocks; not a new Phase32 defect by itself |

Some candidates are suppressed by overlapping gates: reduced/caution evidence can feed production admission, quality target, one-lot authority, desirability class, and Cash comparison. DD does not prove double-counting as a formal bug, but this is the main semantic reconsideration area.

## PM Retention History

CW/CY improved PM context by making entry premise and fresh deterioration separable. DC still found a February sell-led exposure collapse. That does not automatically mean PM is over-sensitive:

- `hard_stop_current_return` exits remain valid.
- true breakdown / persistent deterioration remain valid.
- CW/CY were not present in Phase31 baseline and should be treated as new semantic context plus required lineage repair.
- DC needs a follow-up classification of February exits into hard failure, fresh deterioration, persistent deterioration, known-at-entry-only, and ambiguous.

Current classification: PM retention is material to exposure, but its defect status is unresolved.

## What Must Be Kept

Keep all A-class correctness fixes:

- strict-prior PM reason and REENTRY context materialization;
- pending/order/execution/campaign provenance preservation;
- accepted artifact registry authority;
- canonical campaign identity;
- structured safety taxonomy;
- ADD PASS-only and BF-only target authority;
- Cash notional unit correctness;
- explicit PIT / historical-outcome flags;
- ADD quantity progression and PS delta consistency;
- effective Strategy/Safety cap propagation;
- blocked/non-PASS marginal candidate cannot reach BF/PS/runtime;
- no legacy fallback to unsafe target-gap or residual ADD paths;
- entry premise authoritative lineage once PM delta context exists.

These are Production correctness, not performance preferences.

## What Requires Reconsideration

| Area | Current disposition | Reason |
|---|---|---|
| Active common marginal frontier as Production target authority | REVIEW | Root of major behavior drift; may still be valid, but should not keep expanding Phase32 around performance behavior |
| ADD expected_edge / incremental_value requirement | REVIEW | Plausible authority, but DC shows PM ADD intent cannot materialize accepted ADD; evidence bridge may be incomplete |
| Buy Quality hard ceiling plus one-lot representability | REVIEW | Correctly prevents silent re-expansion, but exposure behavior now depends heavily on explicit one-lot policy |
| NEW/REENTRY multi-lot magnitude preservation | KEEP / REVIEW | Restores PC target magnitude, but must remain bounded by quality/admission and not reintroduce broad low-quality deployment |
| PM entry-premise delta | REVIEW | Semantically useful, but it is new PM behavior context and should be validated as Production readiness necessity |
| Cash optionality explicit residual allocation | KEEP | Cash first-class was already accepted; review only if it wins despite valid strong alternatives |
| Further high-resolution value / rotation work | DEFER_TO_PERFORMANCE_PHASE | Phase31 explicitly deferred it; do not continue inside Phase32 without a new charter |

## Scope Recovery Plan

1. Freeze the A-class correctness repairs as the Production-readiness floor.
2. Stop expanding Phase32 into new capital/performance semantics unless a P0/P1 correctness defect is proven.
3. For the active frontier path, run only scope-recovery audits that decide whether current behavior preserves Phase31 accepted semantics; do not tune thresholds.
4. Reconsider C-class semantics as a group, especially active frontier production ownership, ADD value evidence requirements, Buy Quality/one-lot interaction, and PM entry-premise lifecycle.
5. If a C-class behavior is retained, document it as an explicit post-Phase31 strategy architecture migration, not as implicit Demo readiness.
6. If a C-class behavior is not required for Production correctness, defer it to a new performance/capital-allocation phase.
7. Resume original Phase32 readiness gates: broker/account/cash/position authority, order lifecycle, reconciliation, restart/resume, corporate actions, observability, manual intervention, secrets, rollback, and operational approval boundaries.

## Required Outputs

PHASE32_DD_ORIGINAL_PHASE32_PURPOSE = Demo / Production readiness for the accepted Phase31 Strategy baseline: operational broker/account/order/reconciliation/restart/observability readiness, not default performance tuning or high-resolution capital redesign.

PHASE32_DD_SCOPE_STATUS = SCOPE_REPURPOSED

PHASE32_DD_CLASS_A_COUNT = 8

PHASE32_DD_CLASS_B_COUNT = 1

PHASE32_DD_CLASS_C_COUNT = 7

PHASE32_DD_CLASS_D_COUNT = 11

PHASE32_DD_PRIMARY_SCOPE_DRIFT_TASK = Phase32-AQ/AR/AS, becoming production-migration drift at Phase32-AY/AZ and active Production behavior change at Phase32-BG

PHASE32_DD_PRIMARY_SCOPE_DRIFT_CHANGE = Phase31-deferred optional high-resolution/common marginal capital frontier was moved from shadow research into production-shaped and then active PC-to-PS target authority.

PHASE32_DD_DC_ROOT_NEW = Raw NEW candidates remain broad, but production-deployable BF NEW is sparse after migrated/strengthened production admission, Buy Quality hard ceiling, one-lot/lot feasibility, cap/headroom, and marginal-capital desirability gates.

PHASE32_DD_DC_ROOT_ADD = PM ADD intent persists, especially 94320, but active frontier ADD acceptance requires ADD investment evidence PASS for expected_edge/incremental_value; that bridge is missing/non-PASS, so accepted ADD remains zero.

PHASE32_DD_DC_ROOT_PM = February exposure collapse is sell-led via PM REDUCE/EXIT wave; defect status unresolved because exits must still be classified as hard failure, fresh deterioration, persistent deterioration, or entry-known caution.

PHASE32_DD_PHASE31_INVESTMENT_SEMANTICS_PRESERVED = PARTIAL

PHASE32_DD_CORRECTNESS_FIXES_KEEP = prior-exit PM reason bridge; persistent provenance; campaign identity; accepted registry authority; REENTRY safety taxonomy; Cash notional/PIT flags; ADD quantity and cap invariants; BF-only target authority; Buy Quality authority preservation; blocked/non-PASS candidate acceptance invariant; authoritative entry premise lineage.

PHASE32_DD_STRATEGY_CHANGES_REVIEW = active common marginal frontier Production target authority; ADD expected_edge/incremental_value acceptance semantics; NEW/REENTRY deployability under Buy Quality/one-lot/cap gates; one-lot representability policy; PM entry-premise delta behavior; further high-resolution value/rotation work.

PHASE32_DD_BLANKET_ROLLBACK_JUSTIFIED = NO

PHASE32_DD_PRODUCTION_READINESS_RECOVERABLE = YES

PHASE32_DD_NEXT_STEP = Freeze correctness fixes, stop further Phase32 performance/capital redesign, and perform narrow scope-recovery reviews of the active frontier/new-add/one-lot/PM semantic changes to decide KEEP versus defer before returning to the original Demo / Production readiness gate list.
