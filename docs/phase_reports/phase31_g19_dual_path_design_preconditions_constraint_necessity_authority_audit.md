# Phase31-G19 - Dual-Path Design Preconditions / Constraint Necessity / Authority Audit

## Scope

Task type: READ-ONLY DESIGN-PRECONDITION / CONSTRAINT-NECESSITY / AUTHORITY AUDIT.

Target run:

`runtime-test-historical-extended-smoke-20260822T174358377089Z`

G19 did not implement code, change Strategy, Market Context, Portfolio Policy,
Portfolio Construction, Position Sizing, PM, BUY/SELL, ADD, Safety, config, or
production features. It did not tune thresholds, select exposure targets, run
fresh Historical, resume, replay, or execute long Historical.

The target run was still active. G19 uses the G18 fixed evidence snapshot
(`2023-07-14`, `194` completed business days) for design characterization. A
later read observed additional completed days, but G19 does not depend on that
progress.

## Prior Evidence And Architecture Sources

Required prior reports:

- `docs/phase_reports/phase31_g14_post_peak_performance_deceleration_root_cause_audit.md`
- `docs/phase_reports/phase31_g15_post_peak_loser_expansion_pit_separability_audit.md`
- `docs/phase_reports/phase31_g16_production_decision_temporal_data_lineage_integrity_audit.md`
- `docs/phase_reports/phase31_g17_pit_safe_market_structure_recovery_quality_separability_audit.md`
- `docs/phase_reports/phase31_g18_recovery_quality_bull_opportunity_capture_dual_path_root_cause_audit.md`

Architecture / source-of-truth documents and configs consulted:

- `docs/02_architecture/strategy_architecture_v1.md`
- `docs/02_architecture/portfolio_construction_and_position_sizing_contract.md`
- `configs/strategy/market_context.json`
- `configs/strategy/portfolio_policy.json`
- `configs/strategy/position_sizing.json`
- `configs/strategy/dynamic_position_count.json`
- `configs/strategy/regime_event_position_management.json`
- `configs/safety/portfolio_limits.json`
- `src/ai_fund_lab_v2/strategy/portfolio_construction.py`
- `src/ai_fund_lab_v2/strategy/position_sizing.py`
- `src/ai_fund_lab_v2/strategy/runtime_planning.py`
- `src/ai_fund_lab_v2/runtime_v2/safety/portfolio_limits.py`
- `src/ai_fund_lab_v2/runtime_v2/position_sizing_authority.py`
- `src/ai_fund_lab_v2/runtime_v2/planning/strategy_authority.py`
- `src/ai_fund_lab_v2/runtime_v2/submit/pipeline.py`

## Primary Judgment

`PHASE31_G19_DUAL_PATH_DESIGN_PRECONDITIONS_CONFIRMED_IMPLEMENTATION_PLANNING_READY`

Implementation is not authorized by this report. The judgment means design
preconditions are sufficiently mapped for a later implementation-planning task.

The minimum correct change surface is dual-path:

1. Market Context should own recovery-quality / fragility semantics as evidence
   separate from medium-horizon direction.
2. Portfolio Policy / Portfolio Construction / Position Sizing / ADD should
   receive a focused design review for composition effects among concentration,
   lot feasibility, reentry, residual cash, and ADD materialization.

Safety hard caps remain valid. The issue is not that constraints exist; the
issue is that individually valid constraints can compose into unintended capital
suppression and later abrupt re-risk.

## Authority Map

| Semantic | Current owner | Current producer | Current consumer | Authority type | Soft / hard | Second decision present | Legacy / duplicate |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Market Direction | Market Context | `strategy.market_context` | Portfolio Policy, BUY Quality, PC, PM | Evidence | Soft evidence | NO | NO |
| Market Regime | Market Context | `strategy/market_context.json` | Strategy graph | Evidence taxonomy | Soft evidence | NO | NO |
| Market Breadth | Market Context | J-Quants daily quote proxy | Market Context consumers | Evidence | Soft evidence | NO | NO |
| Market Risk | Market Context / Safety | Market Context volatility, Safety configs | PC, Sizing, Safety | Evidence plus hard guard | Mixed | YES, separated | NO |
| Recovery Quality / Fragility | Not currently explicit | Partially in Market Context metrics | Not currently direct | Missing semantic evidence | Soft evidence candidate | NO | UNRESOLVED |
| Candidate Eligibility | Candidate / BUY AI | Runtime BUY AI / candidate evidence | BUY Quality, PC | Candidate authority | Soft eligibility | NO | NO |
| Candidate Ranking | Opportunity AI | Opportunity rankings | BUY Quality, PC | Ranking evidence | Soft evidence | NO | NO |
| BUY Quality | Strategy BUY Quality | `strategy/buy_quality_decisions.json` | PC, Runtime Planning | BUY quality authority | Soft / fail-closed eligibility | NO | NO |
| Expected Edge | Opportunity / BUY evidence | Opportunity ranking fields | BUY Quality, PC, ADD bridge | Evidence | Soft evidence | NO | NO |
| Portfolio Budget | Portfolio Policy / PC | PC allocation reconciliation | PC, Sizing | Target portfolio authority | Strategy policy | NO | NO |
| Target Weight | Portfolio Construction | `strategy/portfolio_construction.json` | Position Sizing | Target Portfolio Decision Authority | Strategy policy | NO | NO |
| Discrete Quantity | Position Sizing | `strategy/position_sizing.json` | Runtime Planning | Quantity Candidate Authority | Mechanical | NO | NO |
| Lot Feasibility | Position Sizing / PC lot-aware bridge | lot preflight and final reallocation | PC, Sizing, Runtime Planning | Feasibility authority | Mechanical / safety-aware | PARTIAL | NO |
| Single-name Strategy Cap | Portfolio Policy / Sizing | `configs/strategy/portfolio_policy.json`, `configs/strategy/position_sizing.json` | PC, Sizing | Strategy policy | Soft cap | YES, with Safety hard cap | NO |
| Safety Hard Cap | Safety Layer | `configs/safety/portfolio_limits.json` | Sizing, Safety | Safety hard limit | Hard | YES, separated from strategy cap | NO |
| Max Positions | Dynamic Position Count / Portfolio Policy | `configs/strategy/dynamic_position_count.json` | PC / Sizing | Strategy policy | Soft | Legacy config exists | LEGACY RESIDUAL |
| Re-entry Eligibility | Portfolio Construction | semantic reentry authority in PC | PC, Sizing | Strategy semantic gate | Soft/fail-closed | NO | REVIEW |
| Re-entry Cooldown | Portfolio Construction / PM config | `regime_event_position_management.json`, PC constants/evidence | PC | Churn control | Soft/fail-closed | NO | REVIEW |
| ADD Eligibility | PM + PC ADD bridge | PM action and PC canonical ADD bridge | PC, Sizing | Existing-position increment authority | Strategy policy | NO | REVIEW |
| ADD Increment | PC then Sizing | accepted add increment / quantity delta | Runtime Planning | Target + quantity authority | Strategy/mechanical | NO | REVIEW |
| SELL / REDUCE / EXIT | PM | Position Management evidence | Sell Planning, Runtime Planning | Existing Position Intent Authority | Strategy intent | NO | NO |
| Submit Cash Feasibility | Strategy Planning / Submit | pending/order and submit evidence | Submit / Broker | Execution readiness | Hard operational | NO | NO |
| Broker Buying Power | Broker / Runtime | broker/current state | Submit | Broker execution authority | Hard operational | NO | NO |

`AUTHORITY_MAP_COMPLETE = PASS`

`DUPLICATE_BUSINESS_DECISION_COUNT = 0 confirmed duplicates`

No confirmed duplicate business decision was found where the same owner should
be removed outright. There are composition overlaps requiring design review:
strategy cap with safety cap, reentry gates with opportunity qualification, and
lot feasibility with residual cash behavior.

## Constraint Inventory And Classification

| Constraint | Owner | Purpose | SoT | Can zero quantity | Can leave cash idle | Can block replacement / ADD | Design match | Classification |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Strategy max positions / dynamic count | Portfolio Policy / dynamic count | express posture/opportunity capacity | `configs/strategy/dynamic_position_count.json` | YES | YES | YES | PARTIAL | KEEP_AS_STRATEGY_POLICY |
| Safety hard max positions removed | Safety | prevent routine fixed cap duplication | `configs/safety/portfolio_limits.json` | NO | NO | NO | YES | KEEP_AS_HARD_SAFETY |
| Single-name strategy cap | Portfolio Policy / Sizing | routine diversification | `configs/strategy/portfolio_policy.json`, `configs/strategy/position_sizing.json` | YES | YES | YES | YES | KEEP_AS_STRATEGY_POLICY |
| Safety hard single-name cap | Safety | non-negotiable concentration ceiling | `configs/safety/portfolio_limits.json` | YES | YES | YES | YES | KEEP_AS_HARD_SAFETY |
| Gross exposure no-leverage cap | Safety | prevent leverage | `configs/safety/portfolio_limits.json` | YES | YES | YES | YES | KEEP_AS_HARD_SAFETY |
| Generic fixed cash reserve removed | Safety | avoid obsolete cash drag | `configs/safety/portfolio_limits.json` | NO | NO | NO | YES | KEEP_AS_HARD_SAFETY |
| Lot-size feasibility | Position Sizing / PC | only executable discrete lots | `strategy/position_sizing.py` | YES | YES | YES | YES | KEEP_AS_STRATEGY_POLICY |
| Minimum-lot one-lot admission | PC / Sizing | allow minimum executable lot within safety | `portfolio_construction.py`, `position_sizing.py` | NO/YES | PARTIAL | PARTIAL | PARTIAL | REVIEW_SCOPE_OR_SEMANTICS |
| Residual capital handling | PC | preserve unallocated cash when not safely allocable | `position_sizing.json`, PC evidence | YES | YES | YES | PARTIAL | REVIEW_SCOPE_OR_SEMANTICS |
| Competition / marginal capital order | PC | rank already eligible marginal capital uses | B10 authority in PC | YES | YES | YES | YES | KEEP_AS_STRATEGY_POLICY |
| Re-entry semantic block | PC | prevent churn / repeated same-symbol thesis failure | PC semantic reentry authority | YES | YES | YES | PARTIAL | REVIEW_SCOPE_OR_SEMANTICS |
| Re-entry cooldown | PC / PM config | prevent immediate churn | `regime_event_position_management.json`, PC evidence | YES | YES | YES | PARTIAL | REVIEW_SCOPE_OR_SEMANTICS |
| Duplicate existing-position handling | PC | avoid duplicate membership/order | `portfolio_construction.py` | YES | PARTIAL | YES | YES | KEEP_AS_STRATEGY_POLICY |
| ADD eligibility bridge | PC | require economic justification for increments | PC canonical ADD bridge | YES | YES | YES | PARTIAL | REVIEW_SCOPE_OR_SEMANTICS |
| ADD quantity materialization | Position Sizing | convert accepted increment to lot quantity | `position_sizing.py` | YES | YES | YES | PARTIAL | REVIEW_SCOPE_OR_SEMANTICS |
| Broker eligibility / unsupported product | PC / Submit / Broker | avoid untradable instruments | broker eligibility authority | YES | YES | YES | YES | KEEP_AS_HARD_SAFETY |
| Submit cash / buying-power feasibility | Submit / Broker | avoid unavailable cash use | Submit evidence / Broker state | YES | YES | YES | YES | KEEP_AS_HARD_SAFETY |
| Legacy runtime max_positions config | Legacy Runtime config | old capital-deployment cap | `configs/runtime_v2/capital_deployment.json` | UNRESOLVED | UNRESOLVED | UNRESOLVED | REPLACED | REMOVE_IF_DUPLICATE_OR_LEGACY |

`CONSTRAINT_CLASSIFICATION_COUNTS =
KEEP_AS_HARD_SAFETY:5, KEEP_AS_STRATEGY_POLICY:5, REVIEW_SCOPE_OR_SEMANTICS:7, MIGRATE_AUTHORITY:1, REMOVE_IF_DUPLICATE_OR_LEGACY:1, UNRESOLVED:0`

`MIGRATE_AUTHORITY:1` refers to recovery-quality / fragility semantics becoming
explicit Market Context evidence rather than remaining implicit in downstream
PC/reentry/risk-pacing behavior.

## Concentration Necessity Audit

Strategy concentration policy and Safety hard cap are independently justified:

- Strategy cap: `0.18`, routine target-sizing / diversification policy.
- Safety hard cap: `0.25`, non-negotiable single-name concentration ceiling.
- Position-count hard cap is explicitly removed; concentration and opportunity
  eligibility now control capacity.

The layers are not duplicate authority because strategy cap expresses desired
portfolio construction, while safety cap prevents unacceptable concentration.
However, lot-size interaction can make the effective deployable capacity tighter
than the continuous target intended. The code contains explicit
`DISCRETE_LOT_EXCEEDS_STRATEGY_CAP_WITHIN_SAFETY_HARD_MAX`,
`MINIMUM_EXECUTABLE_LOT_EXCEEDS_SAFETY_HARD_MAX`, and one-lot overshoot evidence.

`CONCENTRATION_STRATEGY_POLICY_VALID = YES`

`CONCENTRATION_HARD_SAFETY_VALID = YES`

`CONCENTRATION_DUPLICATE_AUTHORITY = NO`

`LOT_CONCENTRATION_INTERACTION_MATCHES_DESIGN = PARTIAL`

`CONCENTRATION_CAUSES_UNINTENDED_CAPITAL_SUPPRESSION = PARTIAL`

The suppression is not caused by a bad hard cap alone. It arises from
composition: strategy cap + safety cap + discrete lot + marginal competition +
reentry / ADD gates.

## Lot / Residual Capital Necessity Audit

Cash left idle has several causes:

| Class | Evidence |
| --- | --- |
| STRUCTURALLY_UNAVOIDABLE_LOT_RESIDUAL | `CAPITAL_BELOW_NEXT_LOT`, `minimum_lot_exceeds_remaining_budget` |
| VALID_STRATEGY_RESERVE | `COMPETITION_EXHAUSTED`, no eligible marginal candidate |
| VALID_SAFETY_RESERVE | `minimum_lot_exceeds_safety_hard_cap` |
| MISSED_REALLOCATABLE_CAPITAL | suspected where full-eligible candidates coexist with residual cash and PC skips |
| BLOCKED_BY_OTHER_POLICY | semantic reentry / cooldown / ADD bridge failures |
| UNRESOLVED | cases where row-level reason composition is insufficient to prove reallocatability |

`LOT_RESIDUAL_CASH_DISTRIBUTION =
STRUCTURALLY_UNAVOIDABLE_LOT_RESIDUAL + VALID_STRATEGY_RESERVE + VALID_SAFETY_RESERVE + MISSED_REALLOCATABLE_CAPITAL_PARTIAL + BLOCKED_BY_OTHER_POLICY`

`REALLOCATABLE_CAPITAL_LEFT_IDLE = PARTIAL`

`LOT_AWARE_REPAIR_REGRESSION = NO`

Phase28/29 lot-aware behavior appears active. The new issue is not a regression
to old lot ignorance; it is the aggregate design interaction after lot-aware
repairs.

## Re-entry Necessity Audit

Re-entry logic is not a blanket ban. It distinguishes:

- non-reentry BUY_NEW,
- BUY_ADD,
- same-symbol REENTRY after a prior exit,
- cooldown status,
- opportunity requalification,
- BUY quality requalification,
- corporate-action status,
- capacity/liquidity,
- prior exit reason class,
- repeated churn evidence,
- trend/momentum recovery.

This is PIT-justified and architecture-justified in principle. But it can block
healthy replacement because it currently acts inside PC as a zero-weight gate
with multiple fail-closed conditions. G18 showed semantic reentry/cooldown
blocks were dominant in BULL cash drift.

`BLANKET_REENTRY_BAN_PRESENT = NO`

`REENTRY_CONSTRAINT_OVERBROAD = PARTIAL`

`REENTRY_CONSTRAINT_DESIGN_REVIEW_REQUIRED = YES`

Review should focus on scope and semantics, not removal.

## ADD Replacement / Winner Expansion Audit

G18 BULL cash-drift periods:

| Period | PM ADD intent | PC ADD accepted | Nonzero ADD quantity | ADD submit/fill | Primary drop |
| --- | ---: | ---: | ---: | ---: | --- |
| 2023-02-24 -> 2023-03-13 | 1 | 0 | 0 | 0 | `ADD_INCREMENTAL_VALUE_UNKNOWN`, `ADD_OPPORTUNITY_COST_FAIL` |
| 2023-04-14 -> 2023-04-20 | 0 | 0 | 0 | 0 | NO_PM_ADD |
| 2023-05-08 -> 2023-05-18 | 0 | 0 | 0 | 0 | NO_PM_ADD |
| 2023-06-12 -> 2023-07-07 | 7 | 0 | 0 | 0 | `ADD_INCREMENTAL_VALUE_UNKNOWN`, `ADD_OPPORTUNITY_COST_FAIL`, `ADD_EXPECTED_EDGE_WEAKENING`, `ADD_ENTRY_ADMISSION_NO_ADD` |

Totals:

- `PM_ADD_INTENT_COUNT = 8`
- `PC_ADD_ACCEPTED_COUNT = 0`
- `NONZERO_ADD_QUANTITY_COUNT = 0`
- `ADD_SUBMIT_COUNT = 0`
- `ADD_FILL_COUNT = 0`

`ADD_FUNNEL_PRIMARY_BLOCKER =
ADD_INCREMENTAL_VALUE_UNKNOWN / ADD_OPPORTUNITY_COST_FAIL leading to ADD_TARGET_WEIGHT_UNCHANGED`

`ADD_PIPELINE_SEMANTIC_GAP = YES`

`ADD_PIPELINE_MECHANICAL_GAP = PARTIAL`

More ADD is not assumed desirable. The design gap is that PM ADD intent rarely
becomes an accepted incremental capital competitor under the current bridge.

## SELL Removal / Replacement Independence

Architecture states BUY and SELL must remain independent. Runtime and planning
contracts preserve SELL as PM-owned intent and Runtime Planning as a mapper, not
as a BUY replacement optimizer.

G18 shows SELL can remove risk during BULL drift; BUY replacement then depends
on candidate/PC/sizing/reentry/lot constraints. No evidence was found that BUY
review suppresses legitimate SELL. No hidden global same-day BUY lockout was
confirmed. Freed capital appears available to PC/Sizing under the intended daily
contract, but composition constraints may still prevent redeployment.

`BUY_SELL_INDEPENDENCE = PASS`

`SELL_FREED_CAPITAL_AVAILABLE_AS_DESIGNED = YES`

`SELL_CAUSES_UNINTENDED_REPLACEMENT_LOCKOUT = NO`

## Recovery Quality Semantic Candidates

| Concept | PIT derivable | Existing data only | Materialized | Used | Philosophy fit | Empirical support | Overlap risk | Production ready |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| HEALTHY_EXPANSION | YES | YES | PARTIAL | NO | YES | WEAK | MODERATE | NO |
| HEALTHY_RECOVERY | YES | YES | PARTIAL | NO | YES | WEAK | MODERATE | NO |
| FRAGILE_RECOVERY | YES | YES | PARTIAL | NO | YES | MODERATE | MODERATE | NO |
| SHORT_TERM_NARROWING_WITH_MEDIUM_STRENGTH | YES | YES | PARTIAL | NO | YES | MODERATE | MODERATE | NO |
| SHORT_TERM_BREADTH_BREAKDOWN | YES | YES | PARTIAL | NO | YES | MODERATE | MODERATE | NO |
| SECTOR_PARTICIPATION_NARROWING | YES | YES | NO | NO | YES | MODERATE | MODERATE | NO |
| RECOVERY_CONFIRMATION_INCOMPLETE | YES | YES | PARTIAL | NO | YES | WEAK/MODERATE | MODERATE | NO |

`RECOVERY_QUALITY_SEMANTIC_CANDIDATES =
FRAGILE_RECOVERY, SHORT_TERM_NARROWING_WITH_MEDIUM_STRENGTH, SHORT_TERM_BREADTH_BREAKDOWN, SECTOR_PARTICIPATION_NARROWING, RECOVERY_CONFIRMATION_INCOMPLETE`

No production-ready semantic or threshold is selected.

## Direction vs Quality Separation

The design proposition is supported:

- Market Regime answers medium-horizon direction.
- Recovery / Opportunity Quality should answer health, breadth, persistence,
  participation, and internal consistency.

These should remain separate semantics inside Market Context. A second regime
classifier would duplicate and confuse regime ownership.

`MARKET_DIRECTION_AND_QUALITY_SHOULD_BE_SEPARATE = YES`

`SECOND_REGIME_CLASSIFIER_REQUIRED = NO`

`RECOVERY_QUALITY_OWNER = MARKET_CONTEXT`

## Static State vs Transition Evidence

| Evidence | Status |
| --- | --- |
| current regime | EXISTING_AND_USED |
| prior regime | DERIVABLE_NOT_MATERIALIZED |
| days since regime transition | DERIVABLE_NOT_MATERIALIZED |
| recent regime-change count | DERIVABLE_NOT_MATERIALIZED |
| 5D vs 20D breadth delta | EXISTING_NOT_USED |
| 5D vs 20D return disagreement | EXISTING_NOT_USED |
| sector 5D vs 20D participation disagreement | DERIVABLE_NOT_MATERIALIZED |
| exposure trough -> current exposure | DERIVABLE_NOT_MATERIALIZED |
| position-count recovery speed | DERIVABLE_NOT_MATERIALIZED |
| BUY deployment speed | DERIVABLE_NOT_MATERIALIZED |

`TRANSITION_EVIDENCE_GAP_CLASS =
EXISTING_NOT_USED_PLUS_DERIVABLE_NOT_MATERIALIZED`

## Sector And Volume Evidence

Sector participation lineage:

- source: J-Quants listed issues sector columns plus PIT daily quotes,
- as-of behavior: Historical as-of daily input paths scoped by business date,
- missing sector handling: currently not production-defined for participation,
- denominator/weighting: G18 diagnostic used available sectors with simple
  sector-positive shares; formula is not a settled policy.

`SECTOR_PARTICIPATION_DATA_LINEAGE = PASS`

`SECTOR_PARTICIPATION_SEMANTICS_UNAMBIGUOUS = NO`

`SECTOR_PARTICIPATION_PRODUCTION_READY = NO`

Volume participation:

- PIT-derivable from daily quote volume,
- G18 separability was weak,
- useful as future research but not a current design priority.

`VOLUME_PARTICIPATION_CURRENT_DESIGN_PRIORITY = LOW`

## Risk Pacing Semantic Contract Candidate

A semantic contract is feasible without numeric policy:

- `NORMAL_DEPLOYMENT`: normal candidate competition and normal PC behavior.
- `CAUTIOUS_DEPLOYMENT`: preserve optionality, allow qualified BUY, avoid
  abrupt aggregate re-risk.
- `FRAGILE_RECOVERY_DEPLOYMENT`: maintain independent SELL authority, allow
  high-conviction / executable BUY, but require gradual confirmation before
  rapid aggregate exposure restoration.

No percentages, exposure targets, per-day BUY caps, position counts, or
reentry durations are selected.

`RISK_PACING_SEMANTIC_CONTRACT_FEASIBLE = YES`

`NUMERIC_POLICY_SELECTED = NO`

## Constraint Interaction Graph

```text
Market Context
  -> Portfolio Policy / Dynamic Count
  -> BUY Quality modifier
  -> Portfolio Construction

Candidate / Opportunity / BUY Quality
  -> Portfolio Construction membership and marginal capital competition

PM SELL / REDUCE / EXIT
  -> SELL Planning / Runtime Planning
  -> cash freed after execution / current update

PM ADD
  -> PC ADD bridge
  -> accepted_add_increment
  -> Position Sizing quantity delta
  -> Runtime Planning BUY_ADD

Portfolio Construction
  -> strategy cap
  -> reentry/cooldown
  -> duplicate handling
  -> marginal capital priority
  -> lot-aware final reallocation
  -> residual cash

Position Sizing
  -> discrete quantity
  -> lot feasibility
  -> strategy cap overshoot authority
  -> safety hard cap preservation

Safety / Submit / Broker
  -> no leverage
  -> hard concentration
  -> cash/buying power
  -> execution availability
```

`CONSTRAINT_INTERACTION_COMPOSITION_DEFECT = PARTIAL`

`PRIMARY_COMPOSITION_RISK =
valid SELL removal + constrained BUY/ADD replacement + reentry/lot/concentration residual cash + later fast re-risk under short-term narrowing`

## Counterfactual Safety Review

Constraints marked REVIEW are not safe to remove blindly:

- Weakening strategy cap without safety review may increase concentration.
- Weakening reentry may increase churn and duplicate thesis re-entry.
- Weakening ADD bridge may allow unsafe averaging down or low-evidence ADD.
- Weakening lot handling may fabricate unexecutable orders.
- Weakening residual preservation may force capital into inferior candidates.

Existing Safety covers no-leverage, hard concentration, broker feasibility, and
submit/buying-power constraints. It does not fully cover strategy-level churn,
opportunity quality, ADD-worthiness, or recovery fragility.

`SAFETY_COVERAGE_IF_SOFT_CONSTRAINT_REMOVED = PARTIAL`

## Legacy / Historical Origin Audit

Confirmed legacy / replaced items:

- `configs/runtime_v2/capital_deployment.json#max_positions = 5`
- `configs/runtime_v2/capital_deployment_demo.json#max_positions = 5`
- `configs/strategy/dynamic_position_count.json` explicitly references the
  legacy active max positions and states the safety hard maximum is removed.

No active hard reuse of the legacy position cap was confirmed in the audited
Strategy path, but the legacy configs remain suspicious metadata / fallback
surface and should be tracked in design cleanup.

`LEGACY_CONSTRAINT_COUNT = 2`

`REPLACED_BUT_STILL_ACTIVE_COUNT = 0 confirmed`

`UNOWNED_CONSTRAINT_COUNT = 0`

## No Outcome-Driven Constraint Judgment

No constraint was classified for removal because a skipped candidate later won.
No re-risk action was classified as bad solely because subsequent return was
negative. Historical outcomes identify cohorts and interactions only.

`OUTCOME_DRIVEN_CONSTRAINT_SELECTION = NO`

`FUTURE_OUTCOME_USED_FOR_DESIGN_DECISION = NO`

## Design Readiness

`DESIGN_READINESS_DECISION =
DUAL_PATH_DESIGN_CONTRACT_READY_FOR_IMPLEMENTATION_PLANNING`

This does not authorize implementation. A later task must explicitly authorize
code/config changes.

## Required Summary Output

`PRIMARY_JUDGMENT =
PHASE31_G19_DUAL_PATH_DESIGN_PRECONDITIONS_CONFIRMED_IMPLEMENTATION_PLANNING_READY`

`TARGET_RUN_ID =
runtime-test-historical-extended-smoke-20260822T174358377089Z`

`AUTHORITY_MAP_COMPLETE = PASS`

`DUPLICATE_BUSINESS_DECISION_COUNT = 0 confirmed duplicates`

`CONSTRAINT_CLASSIFICATION_COUNTS =
KEEP_AS_HARD_SAFETY:5, KEEP_AS_STRATEGY_POLICY:5, REVIEW_SCOPE_OR_SEMANTICS:7, MIGRATE_AUTHORITY:1, REMOVE_IF_DUPLICATE_OR_LEGACY:1, UNRESOLVED:0`

`CONCENTRATION_STRATEGY_POLICY_VALID = YES`

`CONCENTRATION_HARD_SAFETY_VALID = YES`

`CONCENTRATION_DUPLICATE_AUTHORITY = NO`

`LOT_CONCENTRATION_INTERACTION_MATCHES_DESIGN = PARTIAL`

`CONCENTRATION_CAUSES_UNINTENDED_CAPITAL_SUPPRESSION = PARTIAL`

`LOT_RESIDUAL_CASH_DISTRIBUTION =
STRUCTURALLY_UNAVOIDABLE_LOT_RESIDUAL + VALID_STRATEGY_RESERVE + VALID_SAFETY_RESERVE + MISSED_REALLOCATABLE_CAPITAL_PARTIAL + BLOCKED_BY_OTHER_POLICY`

`REALLOCATABLE_CAPITAL_LEFT_IDLE = PARTIAL`

`LOT_AWARE_REPAIR_REGRESSION = NO`

`BLANKET_REENTRY_BAN_PRESENT = NO`

`REENTRY_CONSTRAINT_OVERBROAD = PARTIAL`

`REENTRY_CONSTRAINT_DESIGN_REVIEW_REQUIRED = YES`

`ADD_FUNNEL_PRIMARY_BLOCKER =
ADD_INCREMENTAL_VALUE_UNKNOWN / ADD_OPPORTUNITY_COST_FAIL leading to ADD_TARGET_WEIGHT_UNCHANGED`

`ADD_PIPELINE_SEMANTIC_GAP = YES`

`ADD_PIPELINE_MECHANICAL_GAP = PARTIAL`

`BUY_SELL_INDEPENDENCE = PASS`

`SELL_FREED_CAPITAL_AVAILABLE_AS_DESIGNED = YES`

`SELL_CAUSES_UNINTENDED_REPLACEMENT_LOCKOUT = NO`

`RECOVERY_QUALITY_SEMANTIC_CANDIDATES =
FRAGILE_RECOVERY, SHORT_TERM_NARROWING_WITH_MEDIUM_STRENGTH, SHORT_TERM_BREADTH_BREAKDOWN, SECTOR_PARTICIPATION_NARROWING, RECOVERY_CONFIRMATION_INCOMPLETE`

`MARKET_DIRECTION_AND_QUALITY_SHOULD_BE_SEPARATE = YES`

`SECOND_REGIME_CLASSIFIER_REQUIRED = NO`

`RECOVERY_QUALITY_OWNER = MARKET_CONTEXT`

`TRANSITION_EVIDENCE_GAP_CLASS =
EXISTING_NOT_USED_PLUS_DERIVABLE_NOT_MATERIALIZED`

`SECTOR_PARTICIPATION_DATA_LINEAGE = PASS`

`SECTOR_PARTICIPATION_SEMANTICS_UNAMBIGUOUS = NO`

`SECTOR_PARTICIPATION_PRODUCTION_READY = NO`

`VOLUME_PARTICIPATION_CURRENT_DESIGN_PRIORITY = LOW`

`RISK_PACING_SEMANTIC_CONTRACT_FEASIBLE = YES`

`NUMERIC_POLICY_SELECTED = NO`

`CONSTRAINT_INTERACTION_COMPOSITION_DEFECT = PARTIAL`

`PRIMARY_COMPOSITION_RISK =
valid SELL removal + constrained BUY/ADD replacement + reentry/lot/concentration residual cash + later fast re-risk under short-term narrowing`

`SAFETY_COVERAGE_IF_SOFT_CONSTRAINT_REMOVED = PARTIAL`

`LEGACY_CONSTRAINT_COUNT = 2`

`REPLACED_BUT_STILL_ACTIVE_COUNT = 0 confirmed`

`UNOWNED_CONSTRAINT_COUNT = 0`

`OUTCOME_DRIVEN_CONSTRAINT_SELECTION = NO`

`FUTURE_OUTCOME_USED_FOR_DESIGN_DECISION = NO`

`DESIGN_READINESS_DECISION =
DUAL_PATH_DESIGN_CONTRACT_READY_FOR_IMPLEMENTATION_PLANNING`

`FUTURE_INFORMATION_USED_AS_PRODUCTION_INPUT = NO`

`HISTORICAL_OUTCOME_USED_TO_SELECT_PRODUCTION_THRESHOLD = NO`

`HISTORICAL_OUTCOME_USED_TO_REMOVE_CONSTRAINT = NO`

`NEW_PRODUCTION_FEATURE_IMPLEMENTED = NO`

`NEW_PRODUCTION_THRESHOLD_SELECTED = NO`

`STRATEGY_CHANGED = NO`

`MARKET_CONTEXT_CHANGED = NO`

`PORTFOLIO_POLICY_CHANGED = NO`

`PORTFOLIO_CONSTRUCTION_CHANGED = NO`

`POSITION_SIZING_CHANGED = NO`

`PM_CHANGED = NO`

`BUY_LOGIC_CHANGED = NO`

`SELL_LOGIC_CHANGED = NO`

`ADD_LOGIC_CHANGED = NO`

`SAFETY_CHANGED = NO`

`FRESH_RUN_EXECUTED = NO`

`RESUME_EXECUTED = NO`

`REPLAY_EXECUTED = NO`

`LONG_HISTORICAL_EXECUTED = NO`

`GIT_DIFF_CHECK = PASS`

`NEXT_TASK_RECOMMENDATION =
Open an implementation-planning task, not direct implementation, for a dual-path
contract: Market Context recovery-quality semantics plus PC/Sizing/ADD
constraint-composition design. Keep Safety hard caps intact and do not select
numeric thresholds in the planning task.`

