# Phase31-G20 - Dual-Path Production Architecture / Contract Design

## Scope

Task type: DESIGN-ONLY ARCHITECTURE / CONTRACT SPECIFICATION.

G20 did not implement code, change production configuration, tune thresholds,
tune parameters, run fresh Historical, resume, replay, or rerun Historical.

Target design problem:

```text
Path A:
PREMATURE_RE_RISK under fragile / internally inconsistent market structure

Path B:
PARTIAL_BULL_OPPORTUNITY_CAPTURE_FAILURE caused by composition of otherwise
legitimate PC / Sizing / ADD / Re-entry constraints
```

## Sources Read

Prior reports:

- `docs/phase_reports/phase31_g14_post_peak_performance_deceleration_root_cause_audit.md`
- `docs/phase_reports/phase31_g15_post_peak_loser_expansion_pit_separability_audit.md`
- `docs/phase_reports/phase31_g16_production_decision_temporal_data_lineage_integrity_audit.md`
- `docs/phase_reports/phase31_g17_pit_safe_market_structure_recovery_quality_separability_audit.md`
- `docs/phase_reports/phase31_g18_recovery_quality_bull_opportunity_capture_dual_path_root_cause_audit.md`
- `docs/phase_reports/phase31_g19_dual_path_design_preconditions_constraint_necessity_authority_audit.md`

Architecture / design SoT:

- `docs/02_architecture/strategy_architecture_v1.md`
- `docs/02_architecture/portfolio_construction_and_position_sizing_contract.md`
- `docs/02_architecture/adaptive_buy_quality_authority.md`
- `docs/02_architecture/position_management_decision_trace_contract.md`
- `docs/02_architecture/runtime_submit_order_condition_authority_contract.md`
- `configs/strategy/market_context.json`
- `configs/strategy/portfolio_policy.json`
- `configs/strategy/position_sizing.json`
- `configs/strategy/dynamic_position_count.json`
- `configs/strategy/regime_event_position_management.json`
- `configs/safety/portfolio_limits.json`

## Canonical Architecture Document

G20 classifies the design as system-wide architecture because Market Context,
Portfolio Policy, BUY Quality, Portfolio Construction, Position Sizing, Safety,
Submit, ADD, and Re-entry boundaries are all affected.

Canonical SoT created:

- `docs/02_architecture/dual_path_market_quality_and_capital_competition_contract.md`

The Phase report is only the adoption and task summary. The normative
specification lives in the architecture document above.

```text
DESIGN_SCOPE = SYSTEM_WIDE_ARCHITECTURE
CANONICAL_ARCHITECTURE_DOC_UPDATED = YES
CANONICAL_ARCHITECTURE_PATHS =
docs/02_architecture/dual_path_market_quality_and_capital_competition_contract.md
```

## Primary Judgment

```text
PRIMARY_JUDGMENT =
PHASE31_G20_DUAL_PATH_SYSTEM_WIDE_ARCHITECTURE_CONTRACT_DEFINED_IMPLEMENTATION_NOT_STARTED
```

The design is ready for a later implementation-planning task. G20 itself does
not authorize implementation or parameter selection.

## Established Root-Cause Interpretation Preserved

G20 preserves the G14-G19 evidence interpretation:

- The issue is not future-data leakage.
- It is not simple Candidate quality collapse.
- It is not simple BUY ranking failure.
- It is not simple "BULL was wrong".
- It is not simple lot regression.
- SELL remains independently capable of reducing risk.
- Market Regime captures medium-horizon direction reasonably well.
- The missing design surface is Market Quality / recovery fragility evidence
  plus explicit Portfolio Construction capital-competition and constraint
  composition semantics.

## Market Direction / Market Quality Split

```text
MARKET_REGIME_AUTHORITY_CHANGED = NO
SECOND_REGIME_CLASSIFIER_CREATED = NO
MARKET_DIRECTION_AND_MARKET_QUALITY_SEPARATED = YES
MARKET_QUALITY_OWNER = MARKET_CONTEXT
```

Market Direction remains the canonical medium-horizon directional environment.
Market Quality is a separate Market Context evidence semantic for quality,
breadth, persistence, participation, internal agreement, and fragility.

## Market Quality Contract

The canonical architecture document defines Market Quality semantic states:

- `HEALTHY_EXPANSION`
- `HEALTHY_RECOVERY`
- `RECOVERY_CONFIRMATION_INCOMPLETE`
- `FRAGILE_RECOVERY`
- `SHORT_TERM_NARROWING_WITH_MEDIUM_STRENGTH`
- `SHORT_TERM_BREADTH_BREAKDOWN`
- `SECTOR_PARTICIPATION_NARROWING`
- `CONFLICTED_MARKET_STRUCTURE`
- `INSUFFICIENT_EVIDENCE`

For each state the design defines meaning, owner, producer, PIT input
requirements, allowed inputs, forbidden inputs, consumers, influence boundaries,
and fail-closed behavior.

```text
MARKET_QUALITY_SEMANTIC_CONTRACT_DEFINED = YES
```

## Evidence Inputs vs Decisions

G20 separates:

```text
DATA
EVIDENCE
SEMANTIC STATE
POLICY DECISION
EXECUTION QUANTITY
```

Market Context may produce evidence and semantic state. It must not directly
choose quantity, exposure target, BUY count, position count, or cash amount.

```text
MARKET_CONTEXT_DIRECTLY_SETS_QUANTITY = NO
MARKET_CONTEXT_DIRECTLY_SETS_EXPOSURE_TARGET = NO
```

## PIT Evidence Contract

Input classes:

| Input | Classification |
| --- | --- |
| 5D return / 20D return | `EXISTING_PRODUCTION_EVIDENCE` |
| 5D breadth / 20D breadth | `EXISTING_PRODUCTION_EVIDENCE` |
| short/medium disagreement | `DERIVABLE_PIT_EVIDENCE_REQUIRING_DESIGN` |
| regime transition path / days since transition | `DERIVABLE_PIT_EVIDENCE_REQUIRING_DESIGN` |
| transition churn | `DERIVABLE_PIT_EVIDENCE_REQUIRING_DESIGN` |
| volatility / downside-risk evidence | `EXISTING_PRODUCTION_EVIDENCE` |
| confidence / uncertainty / coverage | `EXISTING_PRODUCTION_EVIDENCE` |
| sector participation | `DERIVABLE_PIT_EVIDENCE_REQUIRING_DESIGN` |
| G17/G18 diagnostic cohorts | `DIAGNOSTIC_ONLY_NOT_PRODUCTION_READY` |
| future return / later PnL / later campaign label | `OUT_OF_SCOPE` |

```text
FUTURE_DATA_ALLOWED = NO
HISTORICAL_OUTCOME_ALLOWED_AS_RUNTIME_INPUT = NO
```

## Internal Agreement Model

The design defines a semantic agreement model:

- medium strong + short strong + broad participation -> healthy
- medium strong + short weak + narrowing -> fragile / conflicted
- recovery label + incomplete breadth / churn -> confirmation incomplete
- contradictory or missing evidence -> conflicted / insufficient evidence

No G17/G18 cohort thresholds or outcome-optimized weights were selected.

```text
OUTCOME_OPTIMIZED_COMPOSITE_SCORE_CREATED = NO
MARKET_INTERNAL_AGREEMENT_SEMANTIC_DEFINED = YES
```

## Risk Pacing Contract

```text
RISK_PACING_OWNER = PORTFOLIO_POLICY
RISK_PACING_CONSUMER =
PORTFOLIO_CONSTRUCTION / BUY_QUALITY / POSITION_SIZING_AS_CONSUMER_OF_PC_TARGETS
```

Risk pacing intents:

- `NORMAL_DEPLOYMENT`
- `CAUTIOUS_DEPLOYMENT`
- `GRADUAL_REDEPLOYMENT`
- `PRESERVE_OPTIONALITY`

Risk pacing may influence marginal deployment pace and capital competition. It
must not encode fixed exposure, fixed BUY count, fixed position count, fixed
cooldown days, or fixed cash target.

```text
FIXED_EXPOSURE_TARGET_DEFINED = NO
FIXED_BUY_COUNT_DEFINED = NO
FIXED_POSITION_COUNT_DEFINED = NO
```

## Gradual Re-Risk

```text
GRADUAL_RERISK_CONTRACT_DEFINED = YES
BOTTOM_PREDICTION_REQUIRED = NO
```

Designed transition:

```text
risk reduced
  -> initial recovery evidence
  -> confirmation incomplete / conflicted structure
  -> confirmed healthier participation
  -> normal deployment
```

Ownership remains separated:

- Market Context: recovery / fragility / participation evidence
- Portfolio Policy: risk pacing
- Portfolio Construction: capital competition
- Position Sizing: discrete quantity
- Safety: hard protection
- Submit / Execution: execution authority

## Constraint Composition Contract

```text
CONSTRAINT_COMPOSITION_OWNER = PORTFOLIO_CONSTRUCTION
FINAL_NO_DEPLOYABLE_OPPORTUNITY_AUTHORITY =
PORTFOLIO_CONSTRUCTION_TARGET_PORTFOLIO_DECISION_AUTHORITY
CONSTRAINT_COMPOSITION_CONTRACT_DEFINED = YES
```

Portfolio Construction owns final Strategy judgment after consuming Strategy
cap, Safety boundaries, lot feasibility, residual capital, re-entry, ADD,
candidate competition, BUY replacement, broker/cash feasibility, and policy
posture evidence.

Residual classes:

- `UNAVOIDABLE_LOT_RESIDUAL`
- `POLICY_RESERVE`
- `SAFETY_RESERVE`
- `REALLOCATABLE_RESIDUAL`
- `NO_VALID_COMPETITOR`

## Strategy Cap / Safety Cap

```text
STRATEGY_SAFETY_CAP_SEPARATION_PRESERVED = YES
SECOND_CAP_DECISION_CREATED = NO
```

Strategy cap expresses desired allocation. Safety hard cap remains the final
protection boundary. They are not merged.

## Lot / Residual Reallocation

```text
LOT_FIRST_CONTRACT_PRESERVED = YES
RESIDUAL_REALLOCATION_CONTRACT_DEFINED = YES
LOT_AWARE_ARCHITECTURE_REPLACED = NO
```

The contract preserves Phase28/29 lot-aware behavior and adds explicit residual
reallocation semantics.

## Re-entry

```text
BLANKET_REENTRY_BAN = NO
BLANKET_REENTRY_PERMISSION = NO
REENTRY_SEMANTIC_CONTRACT_DEFINED = YES
FIXED_REENTRY_COOLDOWN_SELECTED = NO
```

Re-entry is designed as semantic eligibility using PIT prior exit context,
renewed evidence, churn protection, current Market Quality, and explicit Safety
restrictions. No fixed cooldown was selected.

## ADD Capital Competition

```text
ADD_CAPITAL_COMPETITION_CONTRACT_DEFINED = YES
ADD_AUTOMATIC_PRIORITY = NO
ADD_AUTOMATIC_REJECTION = NO
```

ADD participates in capital competition through:

```text
ADD_INTENT
  -> ADD_ELIGIBILITY
  -> ADD_INCREMENTAL_INVESTMENT_VALUE
  -> ADD_OPPORTUNITY_COST
  -> ADD_TARGET_WEIGHT_CHANGE
  -> ADD_DISCRETE_QUANTITY_DELTA
  -> ADD_SUBMIT
```

ADD may compete with `NEW_BUY` and `CASH / OPTIONALITY`, and may legitimately
win or lose based on contemporaneous evidence.

## BUY / ADD / Cash

```text
CASH_REMAINS_VALID_ALLOCATION = YES
FIXED_MINIMUM_INVESTMENT = NO
FIXED_TARGET_POSITION_COUNT = NO
```

The canonical competition set is:

- `NEW_BUY`
- `ADD`
- `CASH / OPTIONALITY`

Market Quality may affect deployment willingness through Risk Pacing, but must
not rewrite Candidate alpha semantics.

## BUY / SELL Independence

```text
BUY_SELL_INDEPENDENCE_PRESERVED = YES
SELL_AUTHORITY_CHANGED = NO
WINNER_RETENTION_PHILOSOPHY_CHANGED = NO
FIXED_HOLDING_PERIOD_CREATED = NO
```

SELL / REDUCE / EXIT remains able to reduce risk when BUY is blocked,
review-required, absent, zero quantity, or no-action.

## Missing Evidence / Fail-Closed

```text
MARKET_QUALITY_FAIL_CLOSED = YES
IMPLICIT_HEALTHY_FALLBACK = NO
IMPLICIT_BULL_FALLBACK = NO
```

Missing Market Quality evidence becomes `INSUFFICIENT_EVIDENCE` or an
architecture-equivalent explicit missing state. It does not become healthy or
BULL by fallback.

## Temporal Authority

```text
TEMPORAL_CONTRACT_EXPLICIT = YES
CURRENT_SNAPSHOT_NON_PIT_SOURCE_ALLOWED_FOR_HISTORICAL_DECISION = NO
```

Every input must be decision-time PIT with explicit `as_of`, market date,
known-at / effective-date, quote cutoff, sector membership, and source lineage
semantics.

## Evidence Materialization / Reason Codes

Artifacts should materialize Market Direction, Market Quality, components,
semantic reasons, confidence/completeness, Risk Pacing intent, allocation
outcome, blocked reasons, and residual Cash reason. These are evidence outputs,
not future feedback sources.

```text
EVIDENCE_ARTIFACT_FEEDBACK_LOOP_ALLOWED = NO
CANONICAL_REASON_CODES_DEFINED = YES
REASON_CODE_CONTRACT_DEFINED = YES
```

Reason families include Market Quality, participation, risk pacing, residual
cash, re-entry, and ADD competitiveness.

## Duplicate Authority

```text
NEW_DUPLICATE_AUTHORITY_COUNT = 0
```

Owner map:

| Semantic / decision | Owner |
| --- | --- |
| Market Quality | Market Context |
| Risk Pacing | Portfolio Policy |
| Re-entry eligibility integration | Portfolio Construction |
| ADD competitiveness | Portfolio Construction |
| Discrete quantity | Position Sizing |
| Safety cap | Safety |
| Submit feasibility | Submit / Broker Capability / Strategy Planning Authority as applicable |

## Legacy Compatibility / Migration

```text
PERMANENT_LEGACY_FALLBACK_ALLOWED = NO
```

Migration targets:

| Producer / consumer | Current state | Target state | Migration required | Final consumer | Legacy consumer to remove |
| --- | --- | --- | --- | --- | --- |
| Market Context | Direction exists; Quality not explicit | Direction + Quality evidence | YES | Portfolio Policy, BUY Quality, PC | none; Direction remains |
| Portfolio Policy | Posture from Market Context | Risk Pacing intent | YES | PC, BUY Quality | exposure-only shortcuts |
| Portfolio Construction | Target portfolio and partial reasons | Capital competition + composition authority | YES | Sizing, Runtime Planning | legacy capital-deployment membership decisions |
| Position Sizing | Quantity and lot feasibility | Quantity plus residual evidence | YES | PC, Runtime Planning | target-weight recreation |
| ADD bridge | PM ADD to PC | ADD as competitor | YES | PC / Sizing | automatic ADD priority/rejection |
| Re-entry | semantic gates / cooldowns | semantic eligibility contract | YES | PC | blanket/unowned behavior |
| Safety | hard guards | unchanged | NO | Runtime / Submit | n/a |
| Submit / Execution | execution authority | unchanged | NO | Ledger / Current | n/a |

## Implementation Surface Map

| File / module | Current responsibility | Target responsibility | Change type | Authority impact | Migration dependencies | Test requirement |
| --- | --- | --- | --- | --- | --- | --- |
| `configs/strategy/market_context.json` | Market Direction config | Optional Market Quality schema/config | CONFIG DESIGN | Market Context evidence only | lineage definition | PIT / missing evidence |
| `src/ai_fund_lab_v2/strategy/market_context*` | Direction and metrics | Market Quality semantic state | PRODUCER | new evidence, no new regime | schema/config | direction/quality separation |
| `src/ai_fund_lab_v2/strategy/portfolio_policy*` | Portfolio posture | Risk Pacing intent | CONSUMER/PRODUCER | policy intent, no fixed exposure | Market Quality artifact | no fixed exposure/count |
| `src/ai_fund_lab_v2/strategy/buy_quality.py` | BUY Quality | Market Quality evidence consumer | CONSUMER | no action authority | Market Quality schema | weak opportunity not rescued |
| `src/ai_fund_lab_v2/strategy/portfolio_construction.py` | Target portfolio, ADD, re-entry | explicit composition and competition | PRODUCER/CONSUMER | final Strategy target authority | risk pacing, lot evidence | residual / ADD / re-entry |
| `src/ai_fund_lab_v2/strategy/position_sizing.py` | quantity and lot feasibility | preserve quantity; expose residual evidence | PRODUCER | no membership authority | PC contract | lot-first / no duplicate quantity |
| `src/ai_fund_lab_v2/strategy/runtime_planning.py` | map quantity to runtime intent | unchanged consumer | CONSUMER | no Strategy decision | sizing output | no recomputation |
| `src/ai_fund_lab_v2/runtime_v2/safety/*` | hard guards | unchanged | NONE | hard cap preserved | n/a | safety unchanged |
| `src/ai_fund_lab_v2/runtime_v2/submit/*` | Submit feasibility | unchanged | NONE | submit authority preserved | n/a | no implicit fallback |

```text
IMPLEMENTATION_SURFACE_MAP_COMPLETE = PASS
```

## Test Contract

Required future tests:

- Market Quality PIT boundary, missing evidence fail-closed, direction/quality
  separation, short/medium conflict, sector lineage if used.
- Risk Pacing no fixed exposure assumption, cautious deployment does not block
  SELL, healthy deployment does not bypass Safety.
- PC constraints: Strategy cap vs Safety cap, lot-first allocation, residual
  reallocation, no duplicate quantity decision, valid Cash, competitor
  reconsideration.
- Re-entry: no blanket ban, no blanket permission, renewed eligibility, churn
  protection.
- ADD: PM intent can become nonzero ADD, ADD competes but does not always win,
  ADD can lose to BUY/Cash, no future outcome.
- Temporal/evidence: no Historical-result feedback, no Paper Ledger/PnL input,
  no future data.

```text
TEST_CONTRACT_COMPLETE = PASS
```

## Acceptance Invariants

```text
MARKET_REGIME_AUTHORITY_CHANGED = NO
SECOND_REGIME_CLASSIFIER_CREATED = NO
MARKET_DIRECTION_AND_MARKET_QUALITY_SEPARATED = YES
MARKET_QUALITY_OWNER = MARKET_CONTEXT
MARKET_QUALITY_SEMANTIC_CONTRACT_DEFINED = YES
MARKET_CONTEXT_DIRECTLY_SETS_QUANTITY = NO
MARKET_CONTEXT_DIRECTLY_SETS_EXPOSURE_TARGET = NO
FUTURE_DATA_ALLOWED = NO
HISTORICAL_OUTCOME_ALLOWED_AS_RUNTIME_INPUT = NO
OUTCOME_OPTIMIZED_COMPOSITE_SCORE_CREATED = NO
MARKET_INTERNAL_AGREEMENT_SEMANTIC_DEFINED = YES
RISK_PACING_OWNER = PORTFOLIO_POLICY
RISK_PACING_CONSUMER =
PORTFOLIO_CONSTRUCTION / BUY_QUALITY / POSITION_SIZING_AS_CONSUMER_OF_PC_TARGETS
FIXED_EXPOSURE_TARGET_DEFINED = NO
FIXED_BUY_COUNT_DEFINED = NO
FIXED_POSITION_COUNT_DEFINED = NO
GRADUAL_RERISK_CONTRACT_DEFINED = YES
BOTTOM_PREDICTION_REQUIRED = NO
CONSTRAINT_COMPOSITION_OWNER = PORTFOLIO_CONSTRUCTION
FINAL_NO_DEPLOYABLE_OPPORTUNITY_AUTHORITY =
PORTFOLIO_CONSTRUCTION_TARGET_PORTFOLIO_DECISION_AUTHORITY
CONSTRAINT_COMPOSITION_CONTRACT_DEFINED = YES
STRATEGY_SAFETY_CAP_SEPARATION_PRESERVED = YES
SECOND_CAP_DECISION_CREATED = NO
LOT_FIRST_CONTRACT_PRESERVED = YES
RESIDUAL_REALLOCATION_CONTRACT_DEFINED = YES
LOT_AWARE_ARCHITECTURE_REPLACED = NO
BLANKET_REENTRY_BAN = NO
BLANKET_REENTRY_PERMISSION = NO
REENTRY_SEMANTIC_CONTRACT_DEFINED = YES
FIXED_REENTRY_COOLDOWN_SELECTED = NO
ADD_CAPITAL_COMPETITION_CONTRACT_DEFINED = YES
ADD_AUTOMATIC_PRIORITY = NO
ADD_AUTOMATIC_REJECTION = NO
CASH_REMAINS_VALID_ALLOCATION = YES
FIXED_MINIMUM_INVESTMENT = NO
FIXED_TARGET_POSITION_COUNT = NO
BUY_SELL_INDEPENDENCE_PRESERVED = YES
SELL_AUTHORITY_CHANGED = NO
WINNER_RETENTION_PHILOSOPHY_CHANGED = NO
FIXED_HOLDING_PERIOD_CREATED = NO
MARKET_QUALITY_FAIL_CLOSED = YES
IMPLICIT_HEALTHY_FALLBACK = NO
IMPLICIT_BULL_FALLBACK = NO
TEMPORAL_CONTRACT_EXPLICIT = YES
CURRENT_SNAPSHOT_NON_PIT_SOURCE_ALLOWED_FOR_HISTORICAL_DECISION = NO
EVIDENCE_ARTIFACT_FEEDBACK_LOOP_ALLOWED = NO
CANONICAL_REASON_CODES_DEFINED = YES
REASON_CODE_CONTRACT_DEFINED = YES
NEW_DUPLICATE_AUTHORITY_COUNT = 0
PERMANENT_LEGACY_FALLBACK_ALLOWED = NO
IMPLEMENTATION_SURFACE_MAP_COMPLETE = PASS
TEST_CONTRACT_COMPLETE = PASS
```

## Guardrails

```text
IMPLEMENTATION_CHANGED = NO
PRODUCTION_CODE_CHANGED = NO
CONFIG_CHANGED = NO
THRESHOLD_TUNING_DONE = NO
PARAMETER_TUNING_DONE = NO
HISTORICAL_OPTIMIZATION_DONE = NO
FRESH_RUN_EXECUTED = NO
RESUME_EXECUTED = NO
REPLAY_EXECUTED = NO
HISTORICAL_RERUN_EXECUTED = NO
LONG_HISTORICAL_EXECUTED = NO
FUTURE_INFORMATION_USED = NO
```

## Next Task Recommendation

Proceed to implementation planning only after accepting the canonical
architecture contract. The next task should remain scoped and should not select
numeric Market Quality thresholds or tune against the observed 2023 window.
