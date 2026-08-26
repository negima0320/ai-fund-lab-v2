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
