# Phase31-G137 - High-Resolution Capital Value Architecture Ambiguity Hardening

## Final Decision

`G137_HIGH_RESOLUTION_CAPITAL_VALUE_ARCHITECTURE_HARDENING_ACCEPTED`

G137 is a narrow architecture-document hardening task. It preserves the G136
architecture decision and only clarifies four ambiguity points in the permanent
SoT.

No implementation, schema implementation, producer, consumer, Strategy behavior,
Runtime behavior, parameter, threshold, weight, model, fresh-run, resume,
replay, long Historical, run mutation, or Phase advancement was performed.

## Source Basis

Read:

- `docs/02_architecture/high_resolution_marginal_capital_value_and_portfolio_rotation_architecture.md`
- `docs/phase_reports/phase31_g136_high_resolution_capital_value_rotation_permanent_architecture_sot_materialization.md`
- `docs/phase_reports/phase31_g135_high_resolution_marginal_value_portfolio_rotation_design_readiness_audit.md`
- `docs/02_architecture/portfolio_construction_and_position_sizing_contract.md`
- `docs/02_architecture/momentum_follow_position_lifecycle_and_canonical_decision_architecture.md`
- `docs/02_architecture/runtime_architecture_v2.md`

No G132-G136 conclusion was reopened. No contradiction requiring redesign was
found.

## SoT Sections Changed

Primary SoT updated:

`docs/02_architecture/high_resolution_marginal_capital_value_and_portfolio_rotation_architecture.md`

Exact sections amended:

- `8. Common Marginal-Value Semantic`
- `8.1 Marginal Desirability and Feasibility Separation`
- `10. ADD Next-Lot Semantics`
- `12. Explainability and Lineage`
- `14. Current HOLD Boundary`
- `15. Portfolio Rotation Future Responsibility`
- `24. Explicit Non-Goals`

Cross-reference files updated:

None. The G136 cross-references already point to the dedicated SoT, and G137
does not duplicate the full hardening contract into adjacent documents.

## Ambiguity A - Common Semantic vs Single Scalar

Before:

The G136 SoT defined a common marginal-value semantic and prohibited formulas,
weights, and thresholds, but did not explicitly state that a common semantic
does not require one scalar score.

Permanent contract after G137:

```text
COMMON_MARGINAL_VALUE_SEMANTIC_DOES_NOT_REQUIRE_SINGLE_SCALAR = YES
```

The SoT now permits future structured object, vector, ordinal, partial-order,
lexicographic, or numeric representations, subject to later design. It
explicitly rejects the inference that high resolution means more decimal places
in a weighted score.

## Ambiguity B - Marginal Desirability vs Feasibility

Before:

The G136 SoT said a high-value opportunity can still be infeasible, but it did
not make the value/feasibility separation an explicit future artifact
requirement.

Permanent contract after G137:

```text
MARGINAL_VALUE != EXECUTABLE_FEASIBILITY
MARGINAL_VALUE_AND_FEASIBILITY_SEPARATED = YES
```

The SoT now requires future evidence to preserve the distinction between
`HIGH_VALUE + INFEASIBLE` and `LOW_VALUE + FEASIBLE`. PS and Safety authority
remain unchanged.

## Ambiguity C - Rotation Funding / Redeployment Feasibility

Before:

The G136 SoT stated that Portfolio Rotation must not directly sell, but it did
not explicitly guard against assuming that a replacement can always be funded
after release.

Permanent contract after G137:

```text
ROTATION_REDEPLOYMENT_FEASIBILITY_MUST_BE_EXPLICIT = YES
ROTATION_EVIDENCE_MUST_NOT_ASSUME_ATOMIC_REPLACEMENT = YES
```

The SoT now requires future rotation design to represent release intent,
funding evidence, target feasibility, and fallback-to-Cash. It also documents
the risk that selling or reducing incumbent capital before target funding is
proven can leave Cash or alter portfolio state. G137 does not solve broker
atomicity.

## Ambiguity D - Security Quality / HOLD Retention / ADD Value

Before:

The G136 SoT distinguished security quality from marginal capital value, but it
did not explicitly define HOLD retention value as separate from ADD next-lot
value.

Permanent contract after G137:

```text
SECURITY_QUALITY != HOLD_RETENTION_VALUE
HOLD_RETENTION_VALUE != ADD_NEXT_LOT_MARGINAL_VALUE
SECURITY_QUALITY_HOLD_RETENTION_ADD_VALUE_SEPARATED = YES
PM_HOLD_DOES_NOT_IMPLY_ADD = YES
ADD_DOES_NOT_IMPLY_BEST_GLOBAL_ALTERNATIVE = YES
CURRENT_HOLD_EXTERNAL_OPPORTUNITY_COST_REMAINS_UNIMPLEMENTED = YES
HOLD_RETENTION_VALUE_STATUS = FUTURE_DESIGN_REQUIRED
```

The SoT now states that a security may simultaneously have high security
quality, high HOLD retention value, and low ADD next-lot marginal value. Future
Portfolio Rotation must not substitute security quality directly for HOLD
retention value.

## Explainability Hardening

The SoT now requires future value evidence to distinguish:

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

The contract remains type-specific. Not every semantic type must carry every
field.

## Authority-Boundary Confirmation

AUTHORITY_BOUNDARIES_UNCHANGED = `YES`

Preserved boundaries:

- Candidate AI = opportunity intelligence.
- PM = existing-position action authority.
- PC Capital Value = relative scarce-capital comparison.
- PC = capital allocation.
- Portfolio Policy / Risk Pacing = deployment budget / intensity.
- Safety = hard constraints.
- PS = discrete quantity.
- Runtime = execution consumer only.

## Required Judgments

COMMON_MARGINAL_VALUE_SEMANTIC_DOES_NOT_REQUIRE_SINGLE_SCALAR = `YES`

MARGINAL_VALUE_AND_FEASIBILITY_SEPARATED = `YES`

ROTATION_REDEPLOYMENT_FEASIBILITY_MUST_BE_EXPLICIT = `YES`

ROTATION_EVIDENCE_MUST_NOT_ASSUME_ATOMIC_REPLACEMENT = `YES`

SECURITY_QUALITY_HOLD_RETENTION_ADD_VALUE_SEPARATED = `YES`

PM_HOLD_DOES_NOT_IMPLY_ADD = `YES`

ADD_DOES_NOT_IMPLY_BEST_GLOBAL_ALTERNATIVE = `YES`

CURRENT_HOLD_EXTERNAL_OPPORTUNITY_COST_REMAINS_UNIMPLEMENTED = `YES`

AUTHORITY_BOUNDARIES_UNCHANGED = `YES`

CASH_FIRST_CLASS_PRESERVED = `YES`

PIT_ANTI_LEAKAGE_PRESERVED = `YES`

IMPLEMENTATION_PERFORMED = `NO`

PHASE_ADVANCED = `NO`

## Implementation Intentionally Deferred

Still not implemented:

- `canonical_high_resolution_marginal_capital_value.v1`
- `canonical_portfolio_rotation_opportunity_cost.v1`
- concrete JSON schema;
- scalar/vector/ordinal representation choice;
- marginal value equation;
- weights;
- thresholds;
- switching hurdle;
- churn penalty value;
- HOLD score;
- reservation / locking mechanism;
- broker-level atomic replacement;
- PM rotation consumer;
- PS / Runtime binding.

## Next-Phase Readiness Impact

G137 improves readiness by removing four predictable misreadings before future
design begins:

1. high resolution does not mean mandatory scalar score;
2. value and feasibility must remain separately explainable;
3. rotation cannot assume atomic replacement or guaranteed redeployment;
4. security quality, HOLD retention value, and ADD next-lot value are distinct.

Next design may proceed from G136/G137, but implementation remains deferred to
a later explicitly approved task.

## Validation

GIT_DIFF_CHECK = `PASS`
