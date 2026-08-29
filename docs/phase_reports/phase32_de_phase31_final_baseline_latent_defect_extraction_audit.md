# Phase32-DE — Phase31 Final Baseline Latent Defect Extraction Audit

## Executive Summary

This READ-ONLY audit extracts only the defects that were already present, or partially present, in the Phase31 final accepted baseline. It does not select Phase32 implementation for porting. It extracts root defects, violated contracts, reproduction conditions, and required invariants.

Authoritative Phase31 baseline:

- Best identifiable committed code baseline: `887a336 phase31 fix2`
- Accepted run: `runtime-test-historical-extended-smoke-20260825T235520054579Z`
- Accepted strategy status: `CURRENT_STRATEGY_BASELINE_ACCEPTED = YES`; `UNRESOLVED_MANDATORY_PERFORMANCE_DEFECT = NO`
- Phase32 purpose: Demo / Production readiness, not default performance tuning or high-resolution capital redesign
- Key Phase31 SoT: `runtime_architecture_v2.md`, `portfolio_construction_and_position_sizing_contract.md`, `momentum_follow_position_lifecycle_and_canonical_decision_architecture.md`, `strategy_intelligence_architecture_v1.md`, `dual_path_market_quality_and_capital_competition_contract.md`, `high_resolution_marginal_capital_value_and_portfolio_rotation_architecture.md`

The conservative extraction result is:

- Phase31-latent confirmed: 3
- Phase31-latent partial: 3
- Phase32-introduced: 12
- Phase32-amplified preexisting: 1
- Not proven against Phase31 baseline: 1

The most important Phase31 reconstruction requirements are provenance/campaign identity preservation, strict prior-exit context materialization, and Buy Quality adjusted-target authority preservation. Most active common-frontier, BF/PS switch, multi-lot, Cash-notional, blocked-value-class, one-lot representability, and PM entry-premise lifecycle defects are Phase32-created or Phase32-dependent and must not be blindly ported into a Phase31 reconstruction.

## Baseline Identification

Phase31 final closure documents identify the accepted baseline:

- `docs/phase_reports/phase31_g139_phase31_final_closure_performance_improvement_completion.md`
- `docs/phase_reports/phase31_final_summary_and_phase32_handoff.md`
- `docs/phase_reports/phase31_to_phase32_chatgpt_handoff.md`

The git log has no Phase32 commit after Phase31; the latest committed code is:

```text
887a336 phase31 fix2
```

That commit contains the Phase31 closure/handoff reports. No unique tag named `Phase31 final baseline` was found, so `887a336` is the best identifiable committed code baseline. The accepted artifact/run authority remains the Phase31 closure report and run identity, not the current dirty Phase32 worktree.

## Defect Inventory And Classification

| Defect | Phase32 discovery | Phase31 path exists? | Phase31 direct evidence | Phase32 parent dependency | Classification | Reconstruction requirement |
|---|---|---|---|---|---|---|
| D01 prior-exit PM reason loss / GENERIC prior context | K/L/P/W/Z | Yes | Phase32 K/L and later audits use the accepted Phase31 run and show PM detailed EXIT reason not materialized into strict-prior REENTRY context | No; strict bridge exposed it | P31_LATENT_CONFIRMED | Preserve detailed PM exit reason through prior-exit state for REENTRY without changing REENTRY thresholds |
| D02 pending/order/execution source decision and campaign provenance loss | P/Q/R/T/X/Y/AA | Yes | Q classifies persistent execution ledger provenance schema/projection field drop; X finds serialized strategy-origin pending/submit lineage loss | No; provenance was required by existing Runtime/ledger contracts | P31_LATENT_CONFIRMED | Preserve source decision id/type and campaign id losslessly from PM/PC through pending, order, execution, and ledger |
| D03 campaign identity split / multiple generators | AC/AD | Yes, partially | AC finds universal multiple campaign identity generators and incomplete campaign provenance persistence | Phase32 repairs changed the exact manifestation | P31_LATENT_PARTIAL | Use one canonical campaign identity authority; no symbol-only or latest-only lifecycle joins |
| D04 REENTRY safety reason-code collision | AF/AG/AH/AI | Yes, partially | Predicate existed in REENTRY safety path; false-positive support-code collision became visible once prior context was repaired | Earlier provenance defect hid/reduced reachability | P31_LATENT_PARTIAL | Safety predicates must use structured negative evidence, not substring collisions |
| D05 PM runtime adapter accepted hash mismatch | U/V | No | Caused by Phase32-T producer change without accepted-registry refresh | Phase32-T | P32_INTRODUCED | Do not port; only require registry refresh when code changes |
| D06 Cash weight used as Cash notional in active authority | BK/BL/BN | No | Active BG authority read `0.74` weight as notional | BG active frontier | P32_INTRODUCED | Do not port BG helper; general invariant: units must distinguish weight from notional |
| D07 missing future/historical outcome flags on BF/BG discrete quantity authority | BO | No | New BF/BG authority lacked required PIT flags | BF/BG | P32_INTRODUCED | Do not port; if new authority exists, PIT flags required |
| D08 ADD repeated-lot quantity progression inconsistency | BQ/BR | No | Multi-lot ADD used trading unit step instead of accepted incremental quantity | Phase32 multi-lot ADD | P32_INTRODUCED | Do not port multi-lot code; invariant only if multi-lot is rebuilt |
| D09 effective Strategy/Safety cap not propagated to marginal lots | BS/BT | No as observed | Actual defect requires Phase32 marginal lot candidates | Phase32 frontier | P32_INTRODUCED | Do not port; if lots are generated, effective cap must be authoritative |
| D10 legacy-zero/non-deployable NEW promoted by BG common frontier | BU/BV | No | Active BG made PC zero/non-deployable NEW PS-consumable | BG | P32_INTRODUCED | Do not port; preserve PC production admission boundary |
| D11 FAIL_CLOSED / non-PASS ADD accepted by frontier | BX/BY/BZ | No in this shape | Defect occurred in Phase32 ADD/frontier/BF path | Active frontier/BF | P32_INTRODUCED | Do not port; if ADD authority exists, PASS is necessary |
| D12 residual BUY_ADD without BF target | BZ | Yes, partially | Legacy/residual ADD path can bypass new BF-only authority; BUY_ADD actual-path issues existed in Phase31 G129 area | BF-only authority is Phase32, but residual ADD path is legacy | P31_LATENT_PARTIAL | Ensure BUY_ADD has explicit PC/PS order-increment authority; no residual positive quantity without authoritative target |
| D13 NEW one-lot / target magnitude compression | CA/CC | Mixed | Phase32-AN identified 100-share dominance before active rewrite, but CA compression boundary is Phase32 first-lot frontier | BG/CC amplified older lot granularity weakness | P32_AMPLIFIED_PREEXISTING | Extract only invariant: PS must preserve PC target magnitude when contractually authorized |
| D14 Adaptive Buy Quality reduced target re-expansion | CE/CF/CG/CH | Yes | CG explicitly found Buy Quality reduction re-expansion in OLD and CURRENT | No; Phase32 exposed and then repaired it | P31_LATENT_CONFIRMED | Final deployable target must not exceed Buy Quality-authorized target unless a separate PIT authority explicitly overrides |
| D15 PC lot-aware zero collapse after CH | CI/CJ | No | Caused by CH quality ceiling interacting with BF pre-frontier path | CH/CJ | P32_INTRODUCED | Do not port; only relevant if CH-style ceiling is active |
| D16 one-lot authority not materialized before zeroing | CP/CQ | No | Caused by CO/CH/CJ architecture order | CO/CQ | P32_INTRODUCED | Do not port; if explicit one-lot authority exists, it must materialize before zeroing |
| D17 COMPARABLE_MARGINAL categorical one-lot block | CR/CS | No | CR states STRONG/COMPARABLE_HIGH requirement is Phase32-CO semantic strengthening, not Phase30 as-is | CO | P32_INTRODUCED | Do not port; do not add this policy to Phase31 reconstruction |
| D18 entry-known caution vs fresh deterioration PM context gap | CU/CV/CW | Not proven as mandatory Phase31 defect | No direct Phase31 accepted-baseline proof that this violated a required contract | CW is new PM semantic extension | NOT_PROVEN | Do not treat as Phase31 must-fix without Phase31-path evidence |
| D19 campaign entry premise snapshot lineage missing / day-1 HALT | CX/CY | No | Snapshot contract was introduced by CW | CW | P32_INTRODUCED | Do not port unless CW-style PM context is chosen |
| D20 blocked marginal capital candidate accepted to BF/PS/runtime | CZ/DA/DB | No | Requires Phase32 active frontier value classes and BF consumer | Active frontier/BF | P32_INTRODUCED | Do not port; if frontier exists, blocked/non-PASS candidates cannot be accepted |

## Audit Hypotheses Not Promoted To Phase31 Must-Fix

These items remain important but are not directly proven as Phase31 final baseline defects:

- DC PM sell-led February exposure collapse as over-selling. PM exits may be hard failure, true fresh deterioration, or persistent deterioration.
- DC ADD evidence/admission suppression as a Phase31 defect. Phase31 had ADD scarcity and coarse capital value limits, but `expected_edge` / `incremental_value` as active Production acceptance requirements are Phase32 frontier semantics.
- DC NEW deployability scarcity as a Phase31 defect. Raw/new deployability scarcity existed in broad form, but current drop-off stack includes Phase32 Buy Quality hard ceiling, one-lot policy migration, active frontier desirability, and cap propagation.
- Cash optionality being too strong. Phase31 accepted Cash as first-class and no forced full investment.
- High-resolution marginal value / portfolio rotation absence. Phase31 explicitly classified these as deferred optional architecture, not mandatory defects.

## Reconstruction Requirement Extraction

### DEFECT_ID: P31-LATENT-001 Prior-Exit PM Reason Loss

ROOT_PROBLEM: PM detailed EXIT reasons did not survive into strict-prior REENTRY context, producing `GENERIC` prior-exit classes.

PHASE31_EVIDENCE: Phase32-K/L/P/W/Z audits against the Phase31 accepted run family identify `trend_and_opportunity_broken` and related PM reasons not materializing into REENTRY prior-exit state.

VIOLATED_CONTRACT: REENTRY recovery must be evaluated against PIT prior-exit semantic reason, not a lossy bare `EXIT`.

REQUIRED_INVARIANT: For a closed campaign, PM EXIT reason, reason codes, authority, business date, and campaign identity must be recoverable by later REENTRY evaluation from strict-prior artifacts.

MUST_PRESERVE: REENTRY thresholds and recovery logic; PM ownership of EXIT reason; PIT-only strict-prior lookup.

MUST_NOT_IMPORT_FROM_PHASE32: active common frontier, BF target authority, or new REENTRY performance thresholds.

ACCEPTANCE_TEST_REQUIRED: A historical closed campaign with a PM detailed EXIT reason later produces non-GENERIC prior-exit class in REENTRY context.

Investment semantic impact: correctness-only if thresholds are unchanged.

### DEFECT_ID: P31-LATENT-002 Provenance And Campaign Lineage Loss

ROOT_PROBLEM: source decision id/type and campaign id were dropped across pending, order, execution, persistent ledger, and observability boundaries.

PHASE31_EVIDENCE: Phase32-Q/X classify persistent execution ledger provenance field drop and serialized strategy-origin pending lineage loss; Phase31 itself had multiple runtime/pending/submit lineage repairs.

VIOLATED_CONTRACT: Runtime and ledger consumers must preserve canonical decision lineage; downstream lifecycle/PM/REENTRY must not infer identity from symbol-only or latest-only joins.

REQUIRED_INVARIANT: BUY_NEW, REENTRY, BUY_ADD, REDUCE, and EXIT decisions must carry source decision id/type and campaign id from authority producer through pending, order, execution, fill, ledger, and lifecycle artifacts.

MUST_PRESERVE: dedupe/idempotency semantics, partial reduce safety, legacy-reader compatibility where necessary.

MUST_NOT_IMPORT_FROM_PHASE32: Phase32-specific BF/common-frontier target schema unless rebuilding that architecture.

ACCEPTANCE_TEST_REQUIRED: One BUY_NEW and one SELL_EXIT round-trip through pending/order/execution/ledger with identical campaign and source decision lineage.

Investment semantic impact: no selection/sizing/SELL threshold change.

### DEFECT_ID: P31-PARTIAL-003 Campaign Identity Authority Split

ROOT_PROBLEM: multiple campaign id generators and incomplete persistence caused campaign identity splits.

PHASE31_EVIDENCE: Phase32-AC identifies universal multiple campaign identity generators; Phase31 had prior campaign identity and ADD event-history repairs.

VIOLATED_CONTRACT: A position campaign must have one canonical identity across Current, PM, pending/order/execution, positions, realized slices, and REENTRY prior context.

REQUIRED_INVARIANT: campaign id must be generated by one authority and propagated by identity, not symbol-only reconstruction.

MUST_PRESERVE: new campaign on full EXIT then REENTRY; ADD does not open a new campaign; partial reductions remain same campaign.

MUST_NOT_IMPORT_FROM_PHASE32: PM entry-premise snapshot schema unless separately justified.

ACCEPTANCE_TEST_REQUIRED: Initial BUY, ADD, REDUCE, EXIT, and later REENTRY preserve/transition campaign id exactly as specified.

Investment semantic impact: no capital allocation change.

### DEFECT_ID: P31-PARTIAL-004 Structured Safety Predicate

ROOT_PROBLEM: reason-code substring matching can classify supportive broker/safety context as a REENTRY safety block.

PHASE31_EVIDENCE: Phase32-AF/AG/AH/AI find safety taxonomy collision. Direct runtime impact before prior-exit repair was partly hidden, so this is partial rather than confirmed full P31 defect.

VIOLATED_CONTRACT: Safety blocks must be based on explicit negative safety/broker/corporate-action evidence.

REQUIRED_INVARIANT: supportive, informational, unknown, and hard-negative safety reason families must be distinguishable and fail closed when ambiguous.

MUST_PRESERVE: genuine safety/corporate-action/broker blocks.

MUST_NOT_IMPORT_FROM_PHASE32: REENTRY admission loosening beyond structured safety classification.

ACCEPTANCE_TEST_REQUIRED: positive support code does not block; explicit negative code blocks; unknown/missing evidence reviews/fails closed.

Investment semantic impact: limited to false-positive safety classification.

### DEFECT_ID: P31-PARTIAL-005 BUY_ADD Explicit Order-Increment Authority

ROOT_PROBLEM: BUY_ADD actual-path connectivity and residual positive quantity paths can exist without a single explicit PC/PS order-increment authority.

PHASE31_EVIDENCE: Phase31-G129 repaired BUY_ADD actual-path behavior; Phase32-BZ later found residual ADD path without BF target in the new architecture. The root need for explicit BUY_ADD authority is Phase31-relevant; BF-only enforcement is Phase32-specific.

VIOLATED_CONTRACT: ADD cannot reach order/runtime from residual or fallback quantity; it must have explicit PM intent plus PC/PS quantity authority.

REQUIRED_INVARIANT: A BUY_ADD fill requires campaign-scoped ADD intent and authoritative positive quantity/target lineage; absence of that authority yields zero/no-op or REVIEW_REQUIRED.

MUST_PRESERVE: ADD selective behavior, no-loss-averaging, PM ADD intent as necessary but not quantity authority.

MUST_NOT_IMPORT_FROM_PHASE32: BF-only common-frontier schema or expected_edge/incremental_value requirements unless separately adopted.

ACCEPTANCE_TEST_REQUIRED: ADD with authority reaches pending/order; ADD without authority cannot produce positive runtime quantity.

Investment semantic impact: prevents unsafe fallback, not a new ADD threshold.

### DEFECT_ID: P31-LATENT-006 Adaptive Buy Quality Target Authority Re-Expansion

ROOT_PROBLEM: Adaptive Buy Quality can reduce an allocation target, but later PC budget/lot/reallocation can re-expand the final deployable target back to the pre-quality/base target.

PHASE31_EVIDENCE: Phase32-CG explicitly found Buy Quality reduction re-expansion in OLD and CURRENT paths.

VIOLATED_CONTRACT: Buy Quality-adjusted allocation authority must be preserved through final deployable target unless another explicit PIT authority overrides it.

REQUIRED_INVARIANT: `final_deployable_target_weight <= quality_authorized_target_weight`, or any exception must have explicit same-run PIT authority and lineage.

MUST_PRESERVE: Candidate eligibility distinct from production deployability; Buy Quality action/score/band; PS quantity arithmetic.

MUST_NOT_IMPORT_FROM_PHASE32: Phase32 one-lot representability policy, active common frontier, or performance-derived thresholds.

ACCEPTANCE_TEST_REQUIRED: reduced-quality cases like 89180/76470/17570/37770 retain final targets no larger than quality-authorized targets.

Investment semantic impact: can change sizing; requires review if discrete one-lot treatment is not separately specified.

### DEFECT_ID: P31-AMPLIFIED-007 PC Target Magnitude / Lot Granularity Preservation

ROOT_PROBLEM: PC target magnitude and discrete lot realization can compress or distort intended allocation.

PHASE31_EVIDENCE: Phase32-AN identified target-weight compression / 100-share dominance as material but not mandatory; Phase32-CA/CC found a specific first-lot compression after BG.

VIOLATED_CONTRACT: PS should convert PC-authorized target magnitude to executable quantity without silently discarding the magnitude.

REQUIRED_INVARIANT: If PC has explicit positive target magnitude authority, PS/runtime should preserve it subject to lot, Cash, cap, Safety, and Risk Pacing.

MUST_PRESERVE: PS as quantity authority; no fixed position count; no forced full investment.

MUST_NOT_IMPORT_FROM_PHASE32: NEW/REENTRY multi-lot common-frontier machinery by default.

ACCEPTANCE_TEST_REQUIRED: representative PC target weights convert to bounded executable quantities with documented lot residuals.

Investment semantic impact: sizing-sensitive; review required.

## Explicit Do-Not-Port List

Do not port these Phase32-only items into a Phase31 reconstruction unless a separate architecture decision explicitly adopts them:

- active `canonical_marginal_capital_frontier_authority.v1` as Production PC-to-PS target authority;
- BF aggregated PS-boundary as sole target authority;
- Phase32 budget-bounded frontier acceptance sequence;
- Phase32 ADD `expected_edge` / `incremental_value` hard acceptance requirement;
- Phase32 multi-lot ADD repeated-lot implementation;
- Phase32 NEW/REENTRY multi-lot frontier implementation;
- Phase32 CH/CJ one-lot/quality hard-ceiling interaction without a Phase31-specific discrete-lot authority decision;
- Phase32 CO/CS one-lot representability policy;
- Phase32 CW/CY entry-premise snapshot and PM delta context;
- Phase32 DB blocked marginal value-class defensive invariants, except as a general invariant if a frontier is adopted;
- Phase32-created Cash resolver helpers for BG active authority, except the general unit invariant that weight is not notional.

## Phase31 Semantics Preservation Review

| Requirement | Candidate selection | BUY admission | Target magnitude | ADD policy | PM SELL semantics | Cash behavior | Review |
|---|---|---|---|---|---|---|---|
| P31-LATENT-001 prior-exit reason | No | REENTRY context only | No | No | No | No | PASS |
| P31-LATENT-002 provenance | No | No | No | No | No | No | PASS |
| P31-PARTIAL-003 campaign identity | No | No | No | No | No | No | PASS |
| P31-PARTIAL-004 safety taxonomy | No | May remove false block | No | No | No | No | PASS if genuine blocks preserved |
| P31-PARTIAL-005 ADD explicit authority | No | ADD execution only | ADD quantity authority | Yes if residual ADD previously existed | No | No | REVIEW_REQUIRED |
| P31-LATENT-006 Buy Quality target preservation | No | Possibly, when target below lot | Yes | No | No | Possible via less deployment | REVIEW_REQUIRED for one-lot interaction |
| P31-AMPLIFIED-007 target magnitude / lot preservation | No | Possibly | Yes | No | No | Possible | REVIEW_REQUIRED |

## Final Outputs

PHASE32_DE_PHASE31_BASELINE_IDENTIFIED = YES

PHASE32_DE_TOTAL_PHASE32_CONFIRMED_DEFECTS = 20

PHASE32_DE_P31_LATENT_CONFIRMED_COUNT = 3

PHASE32_DE_P31_LATENT_PARTIAL_COUNT = 3

PHASE32_DE_P32_INTRODUCED_COUNT = 12

PHASE32_DE_P32_AMPLIFIED_PREEXISTING_COUNT = 1

PHASE32_DE_NOT_PROVEN_COUNT = 1

PHASE32_DE_PHASE31_MUST_FIX_DEFECTS = P31-LATENT-001 prior-exit PM reason preservation; P31-LATENT-002 source decision/campaign provenance preservation; P31-PARTIAL-003 canonical campaign identity; P31-PARTIAL-004 structured safety predicate if REENTRY path reaches it; P31-PARTIAL-005 explicit BUY_ADD order-increment authority without BF schema; P31-LATENT-006 Adaptive Buy Quality target-authority preservation; P31-AMPLIFIED-007 PC target magnitude / lot granularity invariant for review.

PHASE32_DE_PHASE31_REPAIR_REQUIREMENTS_DEFINED = YES

PHASE32_DE_PHASE32_DO_NOT_PORT = active common marginal frontier Production consumer; BF-only target schema as sole authority; budget-bounded frontier sequence; Phase32 ADD expected_edge/incremental_value hard requirement; Phase32 multi-lot ADD/NEW/REENTRY implementations; Phase32 CO/CS one-lot representability policy; Phase32 CW/CY PM entry-premise snapshot/delta semantics; Phase32-created regression repairs that only defend those paths.

PHASE32_DE_PHASE31_INVESTMENT_SEMANTICS_PRESERVABLE = PARTIAL

PHASE32_DE_RECONSTRUCTION_READY = PARTIAL

PHASE32_DE_NEXT_STEP = For Phase31 reconstruction, implement only requirement-level latent correctness invariants with focused tests against the Phase31 final baseline; explicitly exclude Phase32 active frontier/capital-semantics migrations unless separately re-chartered.
