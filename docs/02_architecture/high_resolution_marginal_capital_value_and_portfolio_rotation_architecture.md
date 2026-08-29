# High-Resolution Marginal Capital Value and Portfolio Rotation Architecture

## 1. Purpose

This document materializes the permanent architecture contract for two future
capabilities identified during Phase31:

1. `HIGH_RESOLUTION_MARGINAL_CAPITAL_VALUE`
2. `PORTFOLIO_WIDE_CAPITAL_ROTATION`

These capabilities are related but separate. High-resolution marginal capital
value must be designed before portfolio-wide capital rotation consumes it.

This document is an architecture SoT only. It does not implement a schema,
producer, consumer, threshold, weight, model, runtime behavior, or trading
behavior.

## 1.1 Implementation Status And Phase31 Deferral Decision

Implementation status:

```text
NOT_IMPLEMENTED
```

Current release status:

```text
DEFERRED / FUTURE_OPTIONAL
```

Phase31 designed this architecture and considered it as a possible future
implementation candidate. Implementation was intentionally deferred for the
current release because the accepted Phase31 Strategy baseline demonstrated
sufficiently strong performance for Demo / Production readiness entry, and no
mandatory performance defect required high-resolution marginal capital value or
portfolio-wide rotation for the current release.

This document is therefore a future architecture design SoT. It does not
describe an implemented current-production authority path. Reconsideration
requires new evidence that the current capital-allocation architecture imposes
a material performance ceiling or operational need.

## 2. Current Architecture Baseline

The current system already performs capital competition among:

```text
NEW_BUY
BUY_ADD
Cash / optionality
```

This is not a new concept introduced by this document. Portfolio Policy owns the
capital budget envelope and deployment intensity. Portfolio Construction owns
scarce-capital allocation and security/Cash competition. Position Sizing owns
discrete quantity. Runtime consumes the resulting executable decision and must
not re-decide capital priority.

The current architecture is SoT-conformant. The accepted Phase31 finding is:

```text
MANDATORY_REPAIR_FOUND = NO
```

Future work under this document is therefore an architecture capability
extension, not a bug fix to the existing capital competition contract.

## 3. Confirmed Phase31 Limitation

Phase31 G132 through G135 confirmed a general capital value resolution
limitation:

- upstream Candidate, PM, Strategy Intelligence, Market Quality, Risk Pacing,
  Cash, cap, and lot evidence contains more PIT-safe differentiation than
  survives into final capital classification;
- resolution loss is multi-causal;
- important compression boundaries include incremental value /
  opportunity-quality bucketing, Portfolio Construction aggregation, and G115
  final classification;
- NEW_BUY, BUY_ADD, and Cash do not yet share a common high-resolution marginal
  capital value unit;
- existing HOLD capital does not yet have portfolio-wide external opportunity
  cost authority against superior NEW_BUY or BUY_ADD opportunities.

The limitation is semantic resolution, not absence of capital competition.

## 4. Not a Candidate AI Failure

Candidate AI answers:

```text
Is this a valid / attractive security opportunity?
```

Candidate AI remains an opportunity producer. It is not the owner of portfolio
capital allocation, ADD action intent, Cash optionality, discrete quantity, or
rotation decisions.

High-resolution marginal capital value must consume Candidate AI evidence when
available, but it must not replace Candidate AI or mutate Candidate AI ranking.

## 5. Not a BULL-Specific Defect

The capital value resolution limitation is regime-independent.

BULL can amplify the limitation because:

- more valid opportunities may reach the allocation frontier;
- more competitors can share the same coarse final class;
- capital can become broadly distributed among opportunities whose upstream
  evidence is more differentiated than their final capital class;
- winner amplification and opportunity selection become more sensitive to
  marginal-value resolution.

This is not a BULL bug and must not be repaired by a BULL-specific multiplier,
override, or suppression rule.

```text
BULL_RETURN_IMPROVEMENT_GUARANTEED = NO
```

## 6. High-Resolution Marginal Capital Value Responsibility

High-Resolution Marginal Capital Value answers:

```text
Relative to competing alternatives, how valuable is the next executable
increment of scarce portfolio capital here?
```

It is not:

- a replacement for Candidate AI;
- a replacement for Position Management;
- a replacement for Market Quality;
- a replacement for Risk Pacing;
- a new BUY filter;
- a Historical-return optimizer;
- a fixed exposure target;
- a fixed position-count rule.

The recommended owner is:

```text
PORTFOLIO_CONSTRUCTION owned Capital Value Authority
```

Portfolio Construction owns the scarce-capital comparison boundary. Other
domains remain evidence or constraint authorities.

## 7. Existing Evidence Reuse

The first implementation must preferentially reuse existing PIT-safe evidence.
Available evidence families include:

- candidate score / rank;
- BUY Quality;
- Entry Quality;
- Expected Edge;
- PM continuation evidence;
- campaign identity / lifecycle;
- Market Quality;
- Risk Pacing;
- Market-Candidate-Cash interaction;
- current weight;
- target weight;
- remaining headroom;
- concentration constraints;
- lot / trading-unit feasibility;
- Cash optionality;
- ADD opportunity-cost evidence.

These are available evidence families, not mandatory inputs for every future
row. A later schema may define required inputs only after accepted design and
validation establish the minimal safe contract.

## 8. Common Marginal-Value Semantic

The future common semantic is:

```text
The relative decision-time desirability of deploying one executable increment
of scarce portfolio capital into this opportunity, considering opportunity
attractiveness, continuation/durability where applicable, incremental portfolio
cost/risk, competing opportunities, Cash optionality, and execution feasibility.
```

This document defines no numeric formula, coefficients, thresholds, or weights.
Historical performance must not be used to choose the value representation,
feature weights, thresholds, ranking rules, or rotation rules.

The common marginal-value semantic does not require a single scalar score:

```text
COMMON_MARGINAL_VALUE_SEMANTIC_DOES_NOT_REQUIRE_SINGLE_SCALAR = YES
```

Permitted future representations may include, subject to later design and
acceptance:

- structured value object;
- vector representation;
- ordinal representation;
- partial ordering;
- lexicographic comparison;
- numeric representation.

This architecture does not pre-commit to one representation. In particular,
`high resolution` must not be interpreted as `more decimal places in one
weighted score`. If a future scalar representation is introduced, it must
preserve explainable raw evidence and must not recreate the information
compression problem identified in Phase31 G132 through G134.

## 8.1 Marginal Desirability and Feasibility Separation

Marginal capital value and executable feasibility are distinct concepts:

```text
MARGINAL_VALUE != EXECUTABLE_FEASIBILITY
MARGINAL_VALUE_AND_FEASIBILITY_SEPARATED = YES
```

A high-value opportunity may be infeasible because of:

- lot granularity;
- insufficient capital;
- concentration cap;
- Safety hard constraint;
- trading constraint;
- temporal / readiness constraint.

The future artifact contract must preserve, conceptually, separate evidence
for:

1. marginal desirability / relative capital value;
2. execution / allocation feasibility.

An infeasible opportunity must not have its economic value collapsed to zero or
LOW merely because it cannot currently execute. The explainable distinction:

```text
HIGH_VALUE + INFEASIBLE
```

is different from:

```text
LOW_VALUE + FEASIBLE
```

Position Sizing and Safety authority remain unchanged. Position Sizing owns
discrete quantity and Safety remains hard constraint authority.

## 9. NEW Marginal Semantics

NEW_BUY value starts from valid opportunity, score/rank, BUY Quality, Entry
Quality, Market Quality context, Risk Pacing context, Cash competition, cap /
headroom, and lot feasibility.

Security quality is not equal to marginal capital value. A security can be a
valid and attractive NEW_BUY while the next executable capital increment is
less valuable than Cash or another opportunity under the same decision-time
portfolio context.

## 10. ADD Next-Lot Semantics

BUY_ADD value starts from PM ADD intent, campaign continuation, expected-edge
evidence, incremental investment evidence, opportunity-cost evidence, no-loss
averaging, current position state, cap / headroom, Cash competition, and lot
feasibility.

ADD must be evaluated as executable marginal increments. A strong campaign may
remain a strong HOLD while the next ADD lot is less attractive than a fresh
NEW_BUY opportunity, another ADD, or Cash.

Repeated ADD increments must be independently evaluable. For example, these are
separate marginal capital decisions:

```text
1200 -> 1300
1300 -> 1400
1600 -> 1700
```

The quantities above are explanatory examples only. They do not create hardcoded
rules.

PM `ADD` is directional intent. It does not imply the ADD increment beats every
NEW_BUY, other ADD, Cash, or residual alternative:

```text
ADD_DOES_NOT_IMPLY_BEST_GLOBAL_ALTERNATIVE = YES
```

## 11. Cash Semantics

Cash / optionality remains a first-class capital alternative.

High-resolution comparison must not mean:

```text
always rank securities and fully invest
```

Future states must continue to allow:

- Cash preferred;
- security preferred;
- near-comparable / shoulder participation;
- deferral;
- legitimate residual Cash.

Cash must not become residual bookkeeping after security deployment has already
been decided. Cash may win before candidate failure when PIT evidence supports
optionality.

## 12. Explainability and Lineage

The future Capital Value layer must not collapse producer evidence into an
opaque score without traceability.

Future evidence should preserve:

- raw producer evidence references;
- semantic type: NEW_BUY, BUY_ADD, Cash, and later HOLD-capital reference;
- executable increment;
- marginal value representation;
- strongest competing alternative;
- relative opportunity-cost evidence;
- portfolio / risk context;
- final disposition;
- rejected or deferred alternatives;
- PIT and temporal safety metadata.

If a numeric representation is later introduced, raw evidence lineage must
remain available.

Explainability must preserve type-specific evidence. A future value artifact
should be able to distinguish:

- raw security / opportunity evidence;
- security quality;
- PM action state;
- HOLD retention semantics where applicable;
- ADD next-lot marginal value;
- NEW next-lot marginal value;
- Cash alternative semantics;
- marginal desirability;
- feasibility;
- strongest competing alternative;
- final allocation / action disposition.

Not every semantic type must carry every field. Missing type-specific fields
must remain explicit rather than being silently replaced by another producer's
semantics.

## 13. Responsibility Ownership

The authority split is:

| Responsibility | Owner |
| --- | --- |
| Candidate opportunity validity / attractiveness | Candidate AI / BUY Quality |
| Existing-position action intent | Position Management |
| Market structure context | Market Quality / Market Context |
| Deployment intensity / available capital budget | Portfolio Policy / Risk Pacing |
| High-resolution marginal capital comparison | Portfolio Construction owned Capital Value Authority |
| Capital allocation and security/Cash frontier | Portfolio Construction |
| Discrete quantity | Position Sizing |
| Safety hard constraints | Safety authorities |
| Execution consumption | Runtime |

Runtime must not recompute ranking, Cash preference, target weight, or quantity.

## 14. Current HOLD Boundary

Current HOLD capital is incumbent allocated state. It is not currently an active
competitor in the first authoritative NEW_BUY / BUY_ADD / Cash allocation
frontier.

Position Management remains the authority for:

```text
HOLD
ADD
REDUCE
EXIT
```

An existing HOLD position can remain valid in isolation while still having a
portfolio-relative opportunity cost. The current architecture does not yet own a
complete portfolio-wide external opportunity-cost authority for that case.

The current status is:

```text
CURRENT_HOLD_EXTERNAL_OPPORTUNITY_COST_REMAINS_UNIMPLEMENTED = YES
```

Future architecture may introduce `HOLD_RETENTION_VALUE` or equivalent
semantics as part of Portfolio Rotation design, but this document does not
define a formula, producer, schema, or authoritative consumer for it:

```text
HOLD_RETENTION_VALUE_STATUS = FUTURE_DESIGN_REQUIRED
```

Security quality, HOLD retention value, and ADD next-lot marginal value are
distinct:

```text
SECURITY_QUALITY != HOLD_RETENTION_VALUE
HOLD_RETENTION_VALUE != ADD_NEXT_LOT_MARGINAL_VALUE
SECURITY_QUALITY_HOLD_RETENTION_ADD_VALUE_SEPARATED = YES
```

Definitions:

- `SECURITY_QUALITY`: how attractive / valid the security opportunity is
  according to its relevant Candidate / Strategy evidence.
- `HOLD_RETENTION_VALUE`: the decision-time value of continuing to keep
  already-deployed capital in an existing position or campaign, considering
  PM-owned continuation / risk evidence and later portfolio-relative evidence
  where applicable.
- `ADD_NEXT_LOT_MARGINAL_VALUE`: the relative value of deploying one additional
  executable increment into that existing position now.

A security may simultaneously have high security quality, high HOLD retention
value, and low ADD next-lot marginal value without contradiction. PM `HOLD`
does not imply PM `ADD`:

```text
PM_HOLD_DOES_NOT_IMPLY_ADD = YES
```

A future Portfolio Rotation comparison must not substitute security quality
directly for HOLD retention value.

## 15. Portfolio Rotation Future Responsibility

Portfolio-wide Capital Rotation is the future ability to reason about:

```text
retain existing HOLD capital
vs release part of that capital and fund superior NEW_BUY
vs release part of that capital and fund superior BUY_ADD
vs release to Cash
```

Portfolio Rotation must not directly sell securities.

The future conceptual path is:

```text
High-Resolution Marginal Capital Value
  -> portfolio-wide external opportunity-cost evidence
  -> PM consumes evidence
  -> PM decides HOLD / REDUCE / EXIT
  -> released capital becomes available
  -> PC allocates to NEW_BUY / BUY_ADD / Cash
  -> PS quantity
  -> Runtime execution
```

Rotation evidence is decision support for PM action authority, not a Runtime
shortcut and not a direct replacement order generator.

Portfolio Rotation evidence must not imply guaranteed redeployment merely
because a superior alternative has been identified. Before an authoritative
future rotation action can release incumbent capital, the relevant planning
architecture must establish sufficient decision-time evidence for:

- target opportunity still being valid;
- target executable feasibility;
- expected released-capital availability;
- applicable lot / cap / Safety constraints;
- no Runtime-side synthetic replacement assumption.

The architectural risk is:

```text
SELL / REDUCE of incumbent capital
-> intended redeployment blocked or infeasible
-> unintended Cash or altered portfolio state
```

This document does not solve transaction atomicity and does not define
broker-level atomic execution. Later implementation design must explicitly
define how release intent, funding evidence, target feasibility, and
fallback-to-Cash are represented.

```text
ROTATION_REDEPLOYMENT_FEASIBILITY_MUST_BE_EXPLICIT = YES
ROTATION_EVIDENCE_MUST_NOT_ASSUME_ATOMIC_REPLACEMENT = YES
```

Cash remaining after a valid failed or blocked redeployment is not
automatically an error. The system must not sell based on a fictitious
guaranteed replacement.

## 16. PM / PC / PS / Runtime Boundary

Future rotation must preserve:

- PM action ownership for HOLD / ADD / REDUCE / EXIT;
- PC ownership of capital allocation and high-resolution capital value;
- PS ownership of discrete quantity;
- Runtime as consumer only;
- SELL / BUY semantic independence;
- campaign identity and re-entry correctness.

Runtime must never synthesize rotation, sell a HOLD because another score is
higher, or turn residual capital into lower-priority orders.

## 17. Anti-Churn and Winner Retention

Future rotation must preserve:

- Winner retention;
- momentum-follow philosophy;
- campaign identity;
- re-entry correctness;
- lot granularity;
- switching / churn cost semantics;
- concentration and Safety caps;
- PIT safety;
- Cash as first-class alternative.

Explicitly prohibited rules:

- sell lowest score, buy highest score;
- replace whenever another score is slightly larger;
- rotate every day to rank 1;
- fixed holding-period replacement;
- Historical-best threshold switching.

## 18. Risk Pacing Separation

Risk Pacing determines how much capital may prudently be deployed. Capital Value
determines where allowed marginal capital is most valuable.

Risk Pacing must not become security ranking, security admission, or a second
Candidate filter.

## 19. Safety Separation

Safety remains hard constraint authority.

Capital Value may never override:

- hard concentration limits;
- executable lot constraints;
- trading safety;
- temporal safety;
- broker / runtime safety contracts.

A high-value opportunity can still be infeasible.

## 20. PIT and Anti-Leakage Requirements

High-Resolution Marginal Capital Value and Portfolio Rotation must be
decision-time PIT-only.

Forbidden production inputs include:

- future prices;
- later return;
- campaign final outcome;
- later MFE / MAE;
- later SELL;
- Paper Ledger result;
- Historical profitability;
- selected / bought outcome;
- future regime.

Historical results may validate architecture behavior after the fact, but must
not choose features, weights, thresholds, ranking rules, or rotation rules.

## 21. Future Canonical Artifacts

Future artifact placeholder:

```text
canonical_high_resolution_marginal_capital_value.v1
```

Status:

```text
NOT_IMPLEMENTED
```

Recommended initial deployment:

```text
SHADOW_NON_AUTHORITATIVE
```

Future artifact placeholder:

```text
canonical_portfolio_rotation_opportunity_cost.v1
```

Status:

```text
NOT_IMPLEMENTED
```

Purpose:

```text
Provide PM with portfolio-relative evidence that capital currently deployed in
a HOLD position has a materially superior alternative.
```

This document intentionally does not define a concrete JSON schema.

## 22. Implementation Sequencing

Future sequencing:

1. High-Resolution Marginal Capital Value design.
2. `SHADOW_NON_AUTHORITATIVE` materialization.
3. Decision-time evidence validation and lineage validation.
4. Authoritative NEW_BUY / BUY_ADD / Cash integration only after acceptance.
5. Portfolio Rotation opportunity-cost design.
6. Shadow Portfolio Rotation evidence.
7. PM consumption design.
8. Authoritative rotation only after focused acceptance.

Portfolio Rotation depends on High-Resolution Marginal Capital Value.

## 23. Validation Principles

Validation must prove:

- decision-time evidence lineage is complete;
- producer evidence is preserved and explainable;
- Candidate AI ranking is not mutated;
- PM action authority is preserved;
- Cash remains first-class;
- Risk Pacing remains deployment intensity;
- Safety remains hard authority;
- PS remains quantity owner;
- Runtime does not re-decide priority;
- no future or Historical outcome input is used;
- existing current behavior changes only after explicit future implementation
  and focused acceptance.

## 24. Explicit Non-Goals

This architecture does not imply:

- more BULL exposure;
- fewer positions by fixed rule;
- concentrated portfolio by fixed rule;
- fixed Top-N selection;
- fixed security count;
- unconditional ADD preference;
- unconditional NEW_BUY preference;
- mandatory full investment;
- BULL-specific score multiplier;
- BEAR-specific suppression;
- Historical-return-based weighting;
- automatic HOLD replacement.
- single-scalar marginal value implementation;
- marginal value equation;
- switching hurdle;
- churn penalty value;
- HOLD score;
- execution atomicity;
- reservation or locking mechanisms.

Capital concentration and Cash level must remain endogenous to decision-time
opportunity evidence, capital budget, risk context, lot feasibility, and Safety
constraints.

## 25. Phase31 Evidence Provenance

This SoT materializes accepted findings from:

- Phase31-G132 unified frontier value-quality characterization;
- Phase31-G133 BULL internal opportunity-quality audit;
- Phase31-G134 capital value resolution-loss localization;
- Phase31-G135 high-resolution marginal value / portfolio rotation design
  readiness audit.

Phase reports are provenance. This document is the enduring architecture
contract.

## 26. Phase32-AS Shadow Common Marginal Frontier Materialization

Phase32-AS materializes the first shadow-only implementation of the high
resolution marginal capital frontier:

```text
canonical_marginal_capital_frontier.v1
```

Implementation module:

```text
src/ai_fund_lab_v2/strategy/common_marginal_capital_frontier_shadow.py
```

Status:

```text
SHADOW_NON_AUTHORITATIVE
```

The artifact places `NEW_FIRST_LOT`, `REENTRY_FIRST_LOT`, `ADD_NEXT_LOT`, and
`CASH_OPTIONALITY` candidates on one structured partial-order frontier. ADD is
represented as one object per executable next lot, with hypothetical post-lot
quantity, weight, Cash, and headroom recomputed for each increment.

The artifact preserves the permanent boundary:

```text
feeds_position_sizing = false
feeds_runtime_planning = false
feeds_pending = false
feeds_orders = false
feeds_execution = false
feeds_safety_authority = false
production_behavior_changed = false
```

`canonical_marginal_capital_frontier.v1` must not become production target
weight, quantity, order, Cash, Runtime, or Safety authority without a later
explicit acceptance and authority-migration phase.

Phase32-AU adds the shadow day-level Cash source resolver for this artifact.
The resolver is PIT-safe and deterministic: it reads only same-day artifacts
available to the shadow materializer and records the selected source plus all
cash-source lineage in the shadow artifact. The required source priority is:

```text
strategy/portfolio_policy.json#current_cash_summary
strategy/portfolio_policy.json#portfolio_policy_allocation_authority.cash_context
strategy/portfolio_policy.json#portfolio_policy_allocation_authority.available_cash_context
current_valuation_refresh/valuation_projection.json
strategy/portfolio_policy.json#top_level
strategy/portfolio_construction.json#top_level
strategy/portfolio_construction.json#capital_competition.canonical_multi_allocation_deployment_set
```

Missing or ambiguous selected-priority Cash evidence must fail closed as
`REVIEW_REQUIRED`. It must not be converted to zero Cash, because that creates
false `INFEASIBLE_INSUFFICIENT_CASH` dispositions and makes Cash appear to win
for the wrong reason. Lower-priority fallback observations are lineage only when
a higher-priority source resolves cleanly.

## 27. Phase32-AZ Production-Shaped Capital Value Authority

Phase32-AZ adds the consumer-disabled, production-shaped Portfolio
Construction authority artifact:

```text
canonical_marginal_capital_frontier_authority.v1
```

Implementation module:

```text
src/ai_fund_lab_v2/strategy/marginal_capital_frontier_authority.py
```

Status:

```text
PRODUCTION_SHAPED_CONSUMER_DISABLED
```

This artifact is owned by:

```text
PORTFOLIO_CONSTRUCTION_CAPITAL_VALUE_AUTHORITY
```

It converts the accepted shadow candidate surface into a bounded deterministic
cardinal marginal-capital-value contract and emits future Position
Sizing-compatible target fields:

```text
current_weight
target_weight
accepted_incremental_weight
target_gap
target_minus_current
accepted_incremental_notional
accepted_frontier_candidate_ids
capital_value_authority
target_weight_reason_codes
```

The authority evaluates `NEW_FIRST_LOT`, `REENTRY_FIRST_LOT`,
`ADD_NEXT_LOT`, and `CASH_OPTIONALITY` on one common frontier. ADD remains a
sequence of next-lot candidates; each accepted ADD lot requires the previous
lot for the same symbol/campaign to have been accepted first, and remaining
Cash is recomputed after each accepted increment.

The cardinal value contract is bounded in `[0.0, 1.0]`, deterministic, and
derived only from decision-time evidence already present in the candidate
surface: opportunity, quality, rank, requalification evidence, and remaining
headroom. It does not use fixed share-size rules, fixed ADD multipliers, fixed
position count, semantic-type multipliers, or Historical outcome parameter
selection. Ambiguous cross-type top values fail closed as `REVIEW_REQUIRED`.

The production-shaped artifact is deliberately not active production authority
until a later migration phase explicitly enables consumption. Permanent AZ
boundary:

```text
production_consumer_enabled = false
production_consumer_count = 0
feeds_position_sizing = false
feeds_runtime_planning = false
feeds_pending = false
feeds_orders = false
feeds_execution = false
feeds_safety_authority = false
production_behavior_changed = false
```

`canonical_marginal_capital_frontier.v1` remains shadow-only and
non-authoritative. Phase32-AZ does not migrate PM, Position Sizing, Runtime,
Safety, REDUCE, EXIT, Cash policy, Risk Pacing, or threshold ownership.

## 28. Phase32-BC Budget-Bounded Acceptance Boundary

Phase32-BC extends `canonical_marginal_capital_frontier_authority.v1` with a
consumer-disabled allocation boundary:

```text
allocation_budget_authority
frontier_acceptance_sequence[]
authorized_cash_allocation
capital_conservation
budget_stop_reasons
```

Budget source priority must reuse existing authorities:

```text
1. strategy/portfolio_construction.json#available_incremental_budget
2. strategy/portfolio_construction.json#capital_competition.canonical_multi_allocation_deployment_set.available_incremental_budget
3. strategy/portfolio_construction.json#incremental_budget_reconciliation.available_incremental_budget
4. embedded Portfolio Policy incremental_capital_budget_envelope exposure headroom
```

Missing or conflicting budget evidence is fail-closed `REVIEW_REQUIRED`.

The acceptance loop allocates the finite decision-time budget one lot at a time
across `NEW_FIRST_LOT`, `REENTRY_FIRST_LOT`, `ADD_NEXT_LOT`, and
`CASH_OPTIONALITY`. A security lot is accepted only while it is feasible under
remaining budget, strictly above Cash optionality, non-ambiguous versus the
next alternative, and still valid under cap, Cash, Safety, Risk Pacing, and
no-loss-averaging constraints.

ADD lot #2/#3+ must re-enter common competition after prior accepted lots
recompute remaining budget, Cash, weight, headroom, and concentration. Later
ADD lots do not inherit acceptance from earlier ADD lots.

Any unallocated budget is explicitly assigned to Cash optionality and verified
by `capital_conservation`. Position count remains an output of accepted lots.
No fixed target count, fixed ADD lot count, fixed share count, fixed ADD
multiplier, fixed position count, or Historical-outcome-selected threshold is
introduced.

The Phase32-BC boundary remains:

```text
production_consumer_enabled = false
production_consumer_count = 0
production_behavior_changed = false
```

## 29. Phase32-BF PC-to-PS Aggregated Target Boundary

Phase32-BF adds a deterministic switch-boundary validator to
`canonical_marginal_capital_frontier_authority.v1`:

```text
pc_to_ps_consumer_switch_boundary
```

This boundary is still owned by Portfolio Construction and remains consumer
disabled. Its job is to prove the future handoff shape from PC to Position
Sizing without changing current production behavior.

The boundary aggregates accepted security lots into PS-compatible final target
rows:

- `NEW_FIRST_LOT` and `REENTRY_FIRST_LOT`: one first-lot row per symbol.
- `ADD_NEXT_LOT`: accepted lot #1/#2/#N for the same symbol and position
  campaign are netted into one final target quantity delta.

The validator preserves campaign and decision lineage, checks that final target
quantity equals current quantity plus net delta, and verifies that aggregated
security allocation equals the source BC accepted allocation. It fails closed
as `REVIEW_REQUIRED` for missing or invalid authority, duplicate identities,
non-contiguous ADD sequences, missing ADD campaign identity, or allocation
conservation mismatches.

Legacy fallback is forbidden for switched rows:

```text
legacy_target_gap_input_used = false
legacy_target_gap_fallback_allowed = false
legacy_zero_fallback_allowed = false
fallback_policy = FAIL_CLOSED_REVIEW_REQUIRED_NO_LEGACY_ZERO_FALLBACK
```

BF does not connect the authority to PS, Runtime Planning, Pending, Orders, or
Execution. A later consumer switch must explicitly enable those consumers and
must treat invalid BF boundary rows as review-required rather than reverting to
the old target-gap or ADD zero path.

## 30. Phase32-BG Explicit PC-to-PS Consumer Switch

Phase32-BG promotes the production-shaped authority to the explicit PC-to-PS
consumer source:

```text
canonical_marginal_capital_frontier_authority.v1
pc_to_ps_production_consumer_switch.v1
```

The switch enables exactly one production consumer:

```text
production_consumers = [strategy.position_sizing]
production_consumer_count = 1
feeds_position_sizing = true
feeds_runtime_planning = false
feeds_pending = false
feeds_orders = false
feeds_execution = false
feeds_safety_authority = false
```

The shadow frontier remains non-authoritative:

```text
canonical_marginal_capital_frontier.v1 production_consumer_count = 0
```

Position Sizing must consume BF aggregated target rows as the only switched
target authority. ADD multi-lot rows are passed as one net quantity delta per
symbol/campaign. Position Sizing remains the discrete quantity authority and
Runtime remains a consumer of Position Sizing quantity deltas; neither may
recompute marginal capital priority.

Missing or invalid BG authority must fail closed as `REVIEW_REQUIRED`. It must
not route back to old target-gap, old ADD compression, or ADD zero fallback.

## 31. Phase32-CO Bounded Minimum Executable One-Lot Authority Migration

Phase32-CO migrates the Phase30 PC-owned minimum executable one-lot authority
into the current CH/CJ/CC/BF marginal capital frontier path.

Normal entry sizing remains quality-bounded:

```text
one_lot_weight <= quality_authorized_target_weight
-> CC NEW/REENTRY multi-lot expansion up to the quality-authorized target
```

For reduced-quality sub-lot `BUY_NEW` / `REENTRY` rows:

```text
quality_authorized_target_weight > 0
one_lot_weight > quality_authorized_target_weight
-> minimum_executable_one_lot_authority.v1
-> ADMIT_ONE_LOT | BLOCK | REVIEW_REQUIRED
```

`ADMIT_ONE_LOT` authorizes exactly one `NEW_FIRST_LOT` or
`REENTRY_FIRST_LOT` candidate to enter common frontier competition. It does not
force a BUY and does not authorize second-lot-plus expansion. The candidate
must still compete against other NEW, REENTRY, ADD, and Cash candidates under
the budget-bounded frontier acceptance sequence.

The authority is owned by Portfolio Construction. Position Sizing remains
quantity authority, and submit feasibility must validate the authority handoff.
PS and Runtime must not independently round a reduced sub-lot target up to one
lot.

Required authority evidence includes quality-authorized target, one-lot
weight/notional, overshoot weight and ratio, Buy Quality action/score/band,
opportunity/rank evidence, entry state, regime/risk evidence, Strategy cap,
Safety hard cap, Risk Pacing, Cash/budget status, source lineage,
`future_information_used=false`, and `historical_outcome_used=false`.

Safety pass, Cash availability, or low position count alone is not sufficient
to admit one lot. Missing, ambiguous, stale, or conflicting required evidence
must fail closed as `REVIEW_REQUIRED`. Strategy cap and Safety hard cap remain
separate guardrails. ADD, REDUCE, EXIT, PS arithmetic, Runtime mapping, and
legacy fallback policy are unchanged.
