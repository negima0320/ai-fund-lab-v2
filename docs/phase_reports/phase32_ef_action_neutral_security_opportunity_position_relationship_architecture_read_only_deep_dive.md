# Phase32-EF - Action-Neutral Security Opportunity / Position-Relationship Architecture READ-ONLY Deep Dive

## Scope

This is a READ-ONLY architecture audit. EF did not modify Production code,
SHADOW code, configuration, runtime state, Pending state, Ledger state, or the
target/source run artifacts. EF did not execute fresh-run, resume, recover,
replay, or long Historical.

Primary evidence:

- EE analysis output:
  `reports/runtime_tests/analysis/phase32_ee_unified_next_capital_unit_20260903T000003`
- Source run:
  `runtime-test-historical-extended-smoke-20260902T060955933565Z`
- Evidence window:
  `2022-10-03` through `2023-10-26`
- Current source commit inspected:
  `1f64f49ee9a8dd48280007e4df656e5f03e231ca`
- EE manifest source files:
  - `src/ai_fund_lab_v2/strategy/marginal_capital_value.py`
    sha256 `8282dabe3915f17ffc8ab916ca88428f519bb0658f4b99aeb77cf7f3c4fd5a56`
  - `src/ai_fund_lab_v2/strategy/portfolio_construction.py`
    sha256 `37a9cb6d93ce70260312138d7c5bd345a5c0e7c4ec11b23353798db0c522f5d7`
- EE manifest flags:
  `analysis_only=true`, `shadow_only=true`,
  `production_change_executed=false`, `runtime_state_mutated=false`,
  `source_run_artifact_mutated=false`, `future_information_used=false`

Mandatory prior reports read or carried forward:

- Phase32-EE unified next-capital-unit SHADOW audit.
- Phase32-ED NEW vs ADD marginal value evidence symmetry audit.
- Phase32-EC incumbent strength-to-increment target authority SHADOW audit.
- Phase32-EB PM ADD strength-to-position-size translation audit.
- Architecture SoT sections for Strategy Intelligence, Portfolio Construction,
  Position Sizing, PM, REENTRY, Expected Edge, and G129 BUY_ADD.

## Current Production Control

`CURRENT_PRODUCTION_CONTROL_PRESERVED = YES`

Current Production remains the control baseline. ADD infrequency by itself is
not treated as a defect. The existing Production authority split remains:

- Candidate / Opportunity provides relative current opportunity evidence.
- BUY Quality and Entry interpret current security evidence for BUY-side
  admissibility.
- Portfolio Construction owns target portfolio and marginal capital authority.
- Position Sizing owns target notional, target quantity, and discrete deltas.
- PM owns existing-position directional intent for ADD / HOLD / REDUCE / EXIT.
- Runtime Planning maps already-authorized strategy decisions and must not
  re-rank or re-optimize.
- G129 BUY_ADD remains order-increment scoped at Submit.

## Candidate / Opportunity Semantic Audit

`CANDIDATE_OPPORTUNITY_SEMANTIC_CLASSIFICATION = C_MIXTURE_BUT_PRIMARILY_CURRENT_SECURITY_ATTRACTIVENESS_EVIDENCE`

Current Candidate / Opportunity evidence primarily represents current security
attractiveness as an uncalibrated relative score/rank, but its Production use is
partly entangled with opening-new-position semantics. The Architecture SoT says
`runtime_opportunity_score` is an uncalibrated relative model score, not
expected return. It is allowed as Portfolio Construction input, but not as
direct target-weight or order authority.

Material evidence families contributing to current Candidate / Opportunity
ranking and selection include PIT technical features, momentum/trend evidence,
relative opportunity score/rank, BUY Quality component evidence, Entry
admission, liquidity/lot feasibility, portfolio constraints, and later
Portfolio Construction / Position Sizing feasibility. These are not all the same
kind of authority:

- Security-like evidence: rank, trend, momentum, relative strength,
  continuation quality, downside risk, quality, expected-edge evidence,
  liquidity, regime compatibility, tick-normalized confidence.
- Action-opening evidence: zero-position assumption, starter sizing,
  fresh-campaign identity, opening-entry admissibility, no-current-weight
  exposure treatment, diversification constraints.
- Lifecycle evidence: REENTRY prior EXIT context, PM campaign continuation,
  current weight, no-loss averaging, concentration/headroom.

Therefore Candidate evidence is usable as an input to a future action-neutral
Security Opportunity layer, but it should not be promoted unchanged as the
complete common authority. It needs normalization so current security quality is
separated from position relationship and action admissibility.

## NEW-Specific Assumptions

`NEW_SPECIFIC_CANDIDATE_ASSUMPTIONS`

| Assumption | Classification | Reason |
| --- | --- | --- |
| zero current position | PRESENT_BUT_SEPARABLE | It is needed to classify BUY_NEW, but not to score the security itself. |
| starter sizing | PRESENT_BUT_SEPARABLE | It belongs to PC/PS first-lot sizing, not intrinsic opportunity. |
| Entry-specific assumptions | PRESENT_BUT_SEPARABLE | Entry maps quality to BUY_NEW / ADD interpretations; the evidence can be shared, the action label cannot. |
| opening liquidity | PRESENT_BUT_SEPARABLE | Liquidity and lot notional are reusable; opening feasibility is action-specific. |
| fresh-campaign assumptions | PRESENT_BUT_SEPARABLE | BUY_NEW creates a new campaign; that should happen after opportunity evaluation. |
| no-current-weight assumptions | PRESENT_BUT_SEPARABLE | Current weight is position-relationship evidence, not security attractiveness. |
| new-position diversification | PRESENT_BUT_SEPARABLE | Diversification is PC portfolio context, not raw security quality. |
| existing-position exclusion | PRESENT_BUT_SEPARABLE | Held symbols are not cleanly absent from all downstream evidence, but treatment is not equivalent to flat candidates. |
| prior ownership exclusion | PRESENT_BUT_SEPARABLE | REENTRY must preserve prior context separately and must not become fake BUY_NEW. |
| REENTRY-specific treatment | PRESENT_BUT_SEPARABLE | REENTRY residual protection is lifecycle authority layered after current opportunity evidence. |

No audited assumption requires that current security attractiveness be computed
only for unheld symbols. The current implementation mixes interpretation
layers, but the mixture appears separable.

## Held-Symbol Candidate Universe Status

`HELD_SYMBOL_CANDIDATE_UNIVERSE_STATUS = PARTIALLY_REPRESENTED`

EF aggregation over the source run found:

- held Portfolio Construction rows: `3232`
- held rows with BUY Quality presence: `2148`
- held rows with candidate/opportunity rank or score references: `2148`

Representative held symbols with PC/BQ/rank evidence included `43880`,
`54010`, `83060`, `94320`, `94340`, and `99840`. This proves that held symbols
can retain useful candidate/opportunity evidence after ownership. It does not
prove that every held symbol is evaluated in exactly the same pre-ranking
universe as flat BUY_NEW candidates. The current state is partial
representation: incumbents are visible through PM/current-position/PC and often
through BQ/rank evidence, but there is no single action-neutral opportunity SoT
for every symbol.

## Same Security Before and After Ownership

`PRE_BUY_VS_POST_BUY_EVIDENCE_CONTINUITY = PARTIAL`

Representative controls show continuity:

- `94320`: rank/score evidence appears before and while held; later PM ADD
  evidence exists, including repeated positive ADD controls.
- `94340`: rank/score evidence appears before and after ownership; later held
  rows include HOLD/ADD PM states.
- `83060`, `99840`, `54010`, `43880`: held rows continue to carry PC/BQ/rank
  evidence on many dates, although many ADD rows remain blocked or insufficient.

Useful security evidence does not simply disappear because ownership status
changes. The gap is that the meaning becomes action-specific: the same security
rank is later consumed through current weight, campaign continuation, ADD
increment authority, no-loss averaging, concentration, and PC/PS executable
delta constraints.

## Incumbent Reusable Security Evidence

`INCUMBENT_REUSABLE_SECURITY_EVIDENCE`

The following evidence can be reused for held symbols with decision-time PIT
data:

- candidate/opportunity rank
- `runtime_opportunity_score` as uncalibrated relative evidence
- trend and momentum features
- relative strength where available
- continuation quality
- downside risk evidence
- BUY Quality component evidence
- Entry timing/admission evidence, before action-specific mapping
- expected-edge / opportunity-comparison evidence
- liquidity and lot notional
- regime compatibility
- tick-normalized trend / momentum confidence
- data-quality and evidence completeness diagnostics

These are reusable only as evidence. None should directly emit BUY_NEW,
BUY_ADD, REENTRY, HOLD, REDUCE, or EXIT.

## Action-Specific Evidence

`ACTION_SPECIFIC_POST_OPPORTUNITY_EVIDENCE`

Evidence that must remain position/action-specific:

- current quantity and current weight
- open campaign id and campaign continuity
- prior ADD history and accumulated exposure
- remaining headroom and concentration cost
- no-loss averaging and average-cost relation
- incremental ADD target above current exposure
- next executable ADD lot and order-increment authority
- PM continuation/deterioration/profit-protection state
- REDUCE / EXIT authority and SELL-side safety
- REENTRY prior campaign id, prior EXIT date, reason, reason codes, and
  provenance
- REENTRY residual churn/recovery protection
- BUY_NEW fresh campaign materialization and first-lot opening constraints
- Cash optionality as non-security capital competitor

This is the reason action-neutral opportunity should precede, not replace,
position relationship and action authority.

## Proposed Separation Feasibility

`SECURITY_OPPORTUNITY_POSITION_RELATIONSHIP_SEPARATION_FEASIBILITY = FEASIBLE_SHADOW_FIRST`

The proposed architecture is feasible if implemented as:

```text
Layer 1: Security Opportunity
  "How attractive is this security right now?"

Layer 2: Position Relationship
  currently flat / held / previously exited

Layer 3: Action Classification
  BUY_NEW / BUY_ADD / REENTRY / HOLD / no action

Layer 4: Portfolio-Aware Marginal Capital Competition
  next executable capital unit vs alternatives and Cash
```

The current code already contains partial ingredients. Strategy Intelligence
builds symbol-level rows from a union of candidate, opportunity, current,
technical, volatility, BQ, PC, sizing, PM, and plan symbols. It also materializes
lifecycle context from current position state and campaign identity. Entry
admission maps similar evidence to different actions depending on whether a
symbol is held. That is exactly the kind of separable layer boundary EF is
testing.

`EARLY_ACTION_CLASSIFICATION_STATUS = PARTIAL`

Current action classification sometimes happens before all security-level
opportunity evidence is normalized. BQ/Entry and PC use ownership state in the
same broad path that carries opportunity evidence. This is not a current
Production failure, but it is the architectural reason to prefer a SHADOW-first
common Security Opportunity record.

## PM Future Role

`PM_UNIQUE_AUTHORITY_INVENTORY`

PM uniquely owns:

- existing-position directional action intent
- HOLD / ADD / REDUCE / EXIT semantics
- campaign continuation context
- deterioration/profit-protection interpretation
- no-loss averaging
- incumbent-specific risk escalation
- prior/current campaign lifecycle state
- SELL/REDUCE candidate authority before PC/PS/runtime materialization

`PM_FUTURE_ROLE_FEASIBILITY = KEEP_PM_AS_EXISTING_POSITION_ACTION_AUTHORITY_AND_CONSUMER_OF_SHARED_SECURITY_EVIDENCE`

PM should not become the universal security opportunity scorer, and PC should
not infer incumbent lifecycle intent by itself. The clean future boundary is:

- Security Opportunity provides shared current attractiveness evidence.
- PM consumes it for existing-position lifecycle decisions.
- PC consumes PM intent plus opportunity evidence for target allocation.
- PS/runtime keep quantity and mapping roles.

`SELL_REDUCE_ARCHITECTURAL_ISOLATION = PRESERVE`

SELL / REDUCE must remain isolated from BUY-side refactoring. Shared evidence
may inform PM, but SELL/REDUCE action authority remains PM-owned and must not be
converted into a BUY-side marginal capital shortcut.

## BQ / Entry Layering

`BQ_ENTRY_LAYERING_AUDIT = MIXED_BUT_SEPARABLE`

BQ and Entry currently combine reusable security evidence with action-specific
interpretation. For example, a held symbol maps through ADD-oriented actions
such as `ADD_ALLOWED`, `ADD_REDUCED_ONLY`, or `NO_ADD`, while a flat symbol maps
through BUY_NEW-style admission. This is a proper consumer behavior, but it
should not be treated as the raw security opportunity authority.

Future architecture should normalize:

```text
Security Opportunity evidence
-> BQ / Entry action interpretation
-> Position Relationship
-> PC marginal capital
```

without letting BQ/Entry directly decide portfolio allocation.

## REENTRY Compatibility

`REENTRY_ACTION_NEUTRAL_ARCHITECTURE_COMPATIBILITY = PASS_WITH_LIFECYCLE_LAYER`

REENTRY is compatible with action-neutral Security Opportunity if prior EXIT
semantics remain a separate lifecycle/provenance layer. Once residual REENTRY
protection passes, current BUY authority owns current rank, BQ, Entry,
Continuation Quality, downside, PC/PS feasibility, Safety, broker,
corporate-action, and capital competition. Prior ownership alone must not create
a permanent rank, BQ, time, or capital penalty.

REENTRY must remain semantically distinct from BUY_NEW:

- flat and never held: BUY_NEW candidate
- flat with strict-prior closed campaign: REENTRY candidate
- currently held: HOLD / ADD / REDUCE / EXIT candidate

## Incumbent Control Cases

`INCUMBENT_SECURITY_RANK_CONTROL_CASES`

EF inspected incumbent controls where security evidence remains visible while
the action interpretation changes:

| Symbol | PC rows | BQ rows | rank present | score present | ADD candidate rows | held rows | PM ADD rows |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `43880` | 38 | 37 | 37 | 37 | 8 | 16 | 12 |
| `54010` | 149 | 149 | 149 | 149 | 65 | 53 | 6 |
| `83060` | 263 | 263 | 263 | 263 | 54 | 175 | 15 |
| `94320` | 264 | 264 | 264 | 264 | 30 | 230 | 50 |
| `94340` | 264 | 264 | 264 | 264 | 95 | 137 | 20 |
| `99840` | 183 | 183 | 183 | 183 | 69 | 105 | 26 |

Examples:

- `94320` retained rank/score while held and later produced positive ADD
  controls.
- `94340` appeared as an early ADD candidate and later as held HOLD/ADD rows.
- `83060` and `99840` retained opportunity evidence but often failed ADD
  materialization due to blocked/insufficient incremental authority.

`HELD_SYMBOL_OPPORTUNITY_VISIBILITY_GAP = PARTIAL_GAP`

Of `3232` held PC rows, `2148` had BQ/candidate opportunity references in the
aggregation. The remaining `1084` held rows did not show the same evidence via
the inspected PC/BQ paths. This supports a future common record, but not an
immediate Production promotion.

## One Security / One Opportunity Record

`ONE_SECURITY_ONE_OPPORTUNITY_RECORD_FEASIBILITY = YES_SHADOW_FIRST`

A single daily per-symbol Security Opportunity record is feasible if it is
strictly evidence-only and action-neutral. It should include current PIT
security attractiveness, evidence completeness, and reusable quality/risk
features. It must not carry a final action.

`SINGLE_SYMBOL_ACTION_EXCLUSIVITY_REQUIREMENT = REQUIRED`

For each business date and symbol, the position relationship layer must select
one mutually exclusive action family:

- currently held: HOLD / ADD / REDUCE / EXIT / no order
- currently flat with strict-prior closed campaign: REENTRY / no order
- currently flat without applicable prior campaign: BUY_NEW / no order

No later consumer may simultaneously treat the same symbol as BUY_NEW and
BUY_ADD, or as BUY_NEW and REENTRY.

`NEUTRAL_MARGINAL_CAPITAL_COMPETITION_BOUNDARY = PC_OWNS_NEXT_CAPITAL_UNIT_COMPETITION`

The capital competition boundary should be:

```text
Security Opportunity evidence
+ Position Relationship
+ action-specific admissibility
+ next executable lot / quantity
+ portfolio constraints / Cash optionality
-> PC-owned next marginal capital unit comparison
-> PS discrete quantity
-> Runtime mapper
```

`ACTION_NEUTRAL_OPPORTUNITY_TO_PC_CONTRACT = EVIDENCE_INPUT_ONLY_NOT_ALLOCATION_AUTHORITY`

The action-neutral record should be an input to PC. It must not replace PC
target allocation authority, PM action authority, PS sizing authority, or G129
Submit binding.

## Behaviors To Preserve

`CANDIDATE_BEHAVIORS_TO_PRESERVE`

- PIT-only candidate evidence.
- Relative opportunity rank/score as uncalibrated evidence, not expected return.
- BUY_WAIT as temporary non-Pending state.
- BUY_NEW first-lot opening through PC/PS/Safety feasibility.
- REENTRY provenance and residual protection.
- Fail-closed missing evidence behavior.
- No symbol-specific anecdote rules.

`PORTFOLIO_BEHAVIORS_TO_PRESERVE`

- PC ownership of target membership, target weights, marginal capital, and Cash
  optionality.
- PM ownership of incumbent lifecycle action.
- PS ownership of discrete target quantity and executable delta.
- Runtime Planning as mapper only.
- G129 order-increment-scoped BUY_ADD Submit validation.
- SELL/REDUCE independence from BUY-side experiments.
- Risk Pacing, Cash, cap, lot, broker, Safety, and corporate-action guardrails.

## Evidence Duplication Profile

`BUY_SIDE_EVIDENCE_DUPLICATION_PROFILE = MATERIAL_BUT_MANAGEABLE`

Current BUY-side evidence is duplicated or reinterpreted across Candidate,
BQ/Entry, PC, PM, and marginal-capital SHADOW artifacts. The duplication is
useful as audit evidence but weak as canonical design because it forces NEW,
ADD, and REENTRY to reconstruct comparable attractiveness through different
paths. EE improved next-capital-unit record symmetry, but its
`authoritative_consumer_count = 0` proves Production has not consumed it.

## Architecture Options

`ARCHITECTURE_OPTION_COMPARISON`

| Option | Summary | Benefit | Risk | EF judgment |
| --- | --- | --- | --- | --- |
| A. Minimal reuse | Keep current flow; expose more incumbent candidate refs. | Smallest change and lowest Production risk. | Leaves action-path asymmetry mostly intact. | Useful interim, not final architecture. |
| B. Shared Security Opportunity Authority | Create one action-neutral per-symbol evidence record, consumed by PM/PC/BQ/Entry. | Best balance of clarity, reversibility, and current behavior preservation. | Requires careful source-of-truth and consumer migration tests. | Recommended SHADOW-first direction. |
| C. Full BUY opportunity refactor | Rebuild BUY_NEW/ADD/REENTRY around the new common record. | Cleanest long-term conceptual model. | High blast radius; not justified now. | Defer until B is accepted. |
| D. Keep current permanently | No migration. | Zero implementation risk. | Does not resolve evidence symmetry or ADD/NEW comparison opacity. | Not recommended as strategic direction. |

`RECOMMENDED_BUY_ARCHITECTURE_DIRECTION = OPTION_B_SHARED_SECURITY_OPPORTUNITY_AUTHORITY_SHADOW_FIRST`

Option B best matches the Architecture SoT principle that shared intelligence is
not shared action authority. It lets the system ask the security question first,
then lets position relationship and PC decide action and capital.

## Migration Plan

`SAFE_MIGRATION_SEQUENCE`

1. Define a SHADOW-only `security_opportunity_evidence.v1` record with one row
   per symbol/date and no authoritative consumers.
2. Backfill over the accepted one-year source run and prove PIT/run/date binding,
   no future information, and no source-run mutation.
3. Compare existing Candidate/BQ/Entry/PC/PM evidence against the common record
   for flat, held, and REENTRY symbols.
4. Add SHADOW consumers in PC and PM to report divergences without changing
   target weights, actions, or order quantities.
5. Promote only a narrow read-side consumer after equality/acceptance gates pass.
6. Keep legacy evidence in parallel until all consumers prove deterministic
   equivalence or explicitly accepted improvement.
7. Remove legacy duplication only after consumer count migration and registry
   acceptance are complete.

`MIGRATION_REVERSIBILITY_REQUIREMENT = REQUIRED`

Every stage must be reversible: no Production target, action, or quantity may
depend on the new record until a formal acceptance phase approves that consumer.

`POST_ACCEPTANCE_LEGACY_CLEANUP_REQUIRED = YES_AFTER_CONSUMER_MIGRATION`

Legacy cleanup is required eventually to remove duplicated semantics, but only
after accepted consumers prove equivalence and no authoritative consumer still
depends on the old shape.

`ARCHITECTURE_PHILOSOPHY_ALIGNMENT = STRONG`

The proposed separation aligns with the SoT:

- shared evidence is not shared action authority;
- Expected Edge must compare existing holding, new BUY candidate, ADD
  candidate, and Cash;
- PM remains existing-position intent authority;
- PC remains allocation authority;
- Runtime remains a mapper.

`EXPECTED_IMPLEMENTATION_SCOPE = MODERATE_TO_LARGE_SHADOW_FIRST`

Likely affected areas in a future implementation:

- Strategy Intelligence row production and provenance.
- Candidate / Opportunity artifact normalization.
- BUY Quality and Entry consumer layering.
- Portfolio Construction evidence consumers.
- Position Management evidence consumers.
- Marginal capital SHADOW backfill and analysis.
- Tests for symbol exclusivity, REENTRY, ADD, G129, and PC/PS boundaries.

Position Sizing and Runtime should remain low-risk downstream consumers if the
contract is implemented correctly.

## Production Change Gate

`PRODUCTION_CHANGE_JUSTIFIED_NOW = NO`

The evidence supports SHADOW-first architecture work, not immediate Production
change. EE showed record symmetry improvements while preserving Production
neutrality, but did not rescue ADD UNKNOWN rows into complete positive
comparable ADD value. Therefore no Production allocation, threshold, weight,
rank, Entry, PM, PC, PS, Safety, or Runtime behavior should be changed in EF.

## Required Final Answers

1. `CURRENT_PRODUCTION_CONTROL_PRESERVED = YES`
2. `CANDIDATE_OPPORTUNITY_SEMANTIC_CLASSIFICATION = C_MIXTURE_BUT_PRIMARILY_CURRENT_SECURITY_ATTRACTIVENESS_EVIDENCE`
3. `NEW_SPECIFIC_CANDIDATE_ASSUMPTIONS = PRESENT_BUT_SEPARABLE_FOR_ALL_AUDITED_ASSUMPTIONS`
4. `HELD_SYMBOL_CANDIDATE_UNIVERSE_STATUS = PARTIALLY_REPRESENTED`
5. `PRE_BUY_VS_POST_BUY_EVIDENCE_CONTINUITY = PARTIAL`
6. `INCUMBENT_REUSABLE_SECURITY_EVIDENCE = RANK_SCORE_TREND_MOMENTUM_RELATIVE_STRENGTH_CONTINUATION_QUALITY_DOWNSIDE_RISK_BQ_ENTRY_EXPECTED_EDGE_LIQUIDITY_REGIME_TICK_NORMALIZED_EVIDENCE`
7. `ACTION_SPECIFIC_POST_OPPORTUNITY_EVIDENCE = CURRENT_WEIGHT_QUANTITY_CAMPAIGN_HEADROOM_CONCENTRATION_NO_LOSS_AVERAGING_INCREMENTAL_ADD_REENTRY_PRIOR_EXIT_BUY_NEW_FRESH_CAMPAIGN_SELL_REDUCE_PROTECTION`
8. `SECURITY_OPPORTUNITY_POSITION_RELATIONSHIP_SEPARATION_FEASIBILITY = FEASIBLE_SHADOW_FIRST`
9. `EARLY_ACTION_CLASSIFICATION_STATUS = PARTIAL`
10. `PM_UNIQUE_AUTHORITY_INVENTORY = EXISTING_POSITION_DIRECTIONAL_INTENT_HOLD_ADD_REDUCE_EXIT_CAMPAIGN_CONTINUATION_PROFIT_PROTECTION_NO_LOSS_AVERAGING`
11. `PM_FUTURE_ROLE_FEASIBILITY = KEEP_PM_AS_EXISTING_POSITION_ACTION_AUTHORITY_AND_CONSUMER_OF_SHARED_SECURITY_EVIDENCE`
12. `SELL_REDUCE_ARCHITECTURAL_ISOLATION = PRESERVE`
13. `BQ_ENTRY_LAYERING_AUDIT = MIXED_BUT_SEPARABLE`
14. `REENTRY_ACTION_NEUTRAL_ARCHITECTURE_COMPATIBILITY = PASS_WITH_LIFECYCLE_LAYER`
15. `INCUMBENT_SECURITY_RANK_CONTROL_CASES = 43880_54010_83060_94320_94340_99840`
16. `HELD_SYMBOL_OPPORTUNITY_VISIBILITY_GAP = PARTIAL_GAP_2148_OF_3232_HELD_PC_ROWS_WITH_BQ_CANDIDATE_OPPORTUNITY_REFS`
17. `ONE_SECURITY_ONE_OPPORTUNITY_RECORD_FEASIBILITY = YES_SHADOW_FIRST`
18. `SINGLE_SYMBOL_ACTION_EXCLUSIVITY_REQUIREMENT = REQUIRED`
19. `NEUTRAL_MARGINAL_CAPITAL_COMPETITION_BOUNDARY = PORTFOLIO_CONSTRUCTION_NEXT_CAPITAL_UNIT_AUTHORITY`
20. `ACTION_NEUTRAL_OPPORTUNITY_TO_PC_CONTRACT = EVIDENCE_INPUT_ONLY_NOT_ALLOCATION_AUTHORITY`
21. `CANDIDATE_BEHAVIORS_TO_PRESERVE = PIT_RELATIVE_SCORE_RANK_BUY_WAIT_FIRST_LOT_FEASIBILITY_REENTRY_PROVENANCE_FAIL_CLOSED_NO_SYMBOL_RULES`
22. `PORTFOLIO_BEHAVIORS_TO_PRESERVE = PC_TARGET_AUTHORITY_PM_INCUMBENT_AUTHORITY_PS_QUANTITY_RUNTIME_MAPPER_G129_SAFETY_RISK_CASH_LOT_BROKER_CA_GUARDS`
23. `BUY_SIDE_EVIDENCE_DUPLICATION_PROFILE = MATERIAL_BUT_MANAGEABLE`
24. `ARCHITECTURE_OPTION_COMPARISON = OPTION_B_BEST_BALANCE_OPTION_C_DEFER_OPTION_A_INTERIM_OPTION_D_NOT_STRATEGIC`
25. `RECOMMENDED_BUY_ARCHITECTURE_DIRECTION = OPTION_B_SHARED_SECURITY_OPPORTUNITY_AUTHORITY_SHADOW_FIRST`
26. `SAFE_MIGRATION_SEQUENCE = SHADOW_RECORD_BACKFILL_COMPARISON_SHADOW_CONSUMERS_NARROW_PROMOTION_PARALLEL_RUN_LEGACY_CLEANUP`
27. `MIGRATION_REVERSIBILITY_REQUIREMENT = REQUIRED`
28. `POST_ACCEPTANCE_LEGACY_CLEANUP_REQUIRED = YES_AFTER_CONSUMER_MIGRATION`
29. `ARCHITECTURE_PHILOSOPHY_ALIGNMENT = STRONG`
30. `EXPECTED_IMPLEMENTATION_SCOPE = MODERATE_TO_LARGE_SHADOW_FIRST`
31. `PRODUCTION_CHANGE_JUSTIFIED_NOW = NO`
32. `FUTURE_OUTCOME_USED = NO`
33. `HISTORICAL_PNL_USED_FOR_DESIGN_SELECTION = NO`
34. `PRODUCTION_CHANGE_EXECUTED = NO`
35. `SHADOW_CHANGE_EXECUTED = NO`
36. `TARGET_RUN_MUTATED = NO`
37. `RUNTIME_STATE_MUTATED = NO`
38. `LONG_RUNTIME_EXECUTED = NO`
39. `NEXT_RECOMMENDED_STEP = DESIGN_SECURITY_OPPORTUNITY_EVIDENCE_V1_SHADOW_ONLY_WITH_ZERO_AUTHORITY_CONSUMERS`
40. `FINAL_JUDGMENT = PHASE32_EF_ACTION_NEUTRAL_SECURITY_OPPORTUNITY_ARCHITECTURE_FEASIBLE_SHADOW_FIRST_SHARED_SECURITY_OPPORTUNITY_RECOMMENDED_NO_PRODUCTION_OR_SHADOW_CHANGE`

## Final Judgment

`PHASE32_EF_ACTION_NEUTRAL_SECURITY_OPPORTUNITY_ARCHITECTURE_FEASIBLE_SHADOW_FIRST_SHARED_SECURITY_OPPORTUNITY_RECOMMENDED_NO_PRODUCTION_OR_SHADOW_CHANGE`

The current Candidate / Opportunity path is not clean enough to become an
immediate Production-wide common authority unchanged, but it contains substantial
reusable current security attractiveness evidence. The correct next step is a
SHADOW-only shared Security Opportunity evidence record with zero authoritative
consumers, followed by backfill and consumer divergence analysis. Production
behavior remains the control and should not change in EF.
