# Phase23-AN Opportunity Score -> Target Weight -> Position Sizing Boundary Design Closure

## Primary Judgment

`PHASE23_AN_OPPORTUNITY_TO_TARGET_WEIGHT_BOUNDARY_DESIGN_CLOSED`

## Selected Responsibility Model

Selected: Option A.

```text
Opportunity Ranking
  -> runtime_opportunity_score / rank / lineage

Portfolio Construction
  -> target membership
  -> target_weight
  -> target_weight_authority

Position Sizing
  -> target_notional
  -> target_quantity_candidate
  -> quantity_delta_candidate
```

## runtime_opportunity_score Contract

`runtime_opportunity_score` is a signful, finite, higher-is-better relative opportunity signal produced by Opportunity Ranking Authority. It is not allocation quality, target weight, target notional, quantity, BUY authorization, or Submit authorization. Negative values are schema-valid raw evidence.

## Portfolio Construction Responsibility

Portfolio Construction owns Target Portfolio Decision Authority: target membership, target weight, target portfolio delta, and reason evidence. It may use Opportunity score as one input, but must explain the result through target weight authority and reason codes.

## Target Weight Contract

Canonical fields:

```text
target_weight
target_weight_authority
target_weight_resolution
```

`target_weight` is the target holding ratio for the symbol relative to the whole portfolio.

Constraints:

```text
0.0 <= target_weight <= single_name_weight_cap
sum(target_weight) <= target_gross_exposure
```

Zero weight is valid with explicit reason evidence.

## Position Sizing Responsibility

Position Sizing consumes target weight and converts it to target notional and quantity candidates using portfolio capital, reference price, trading unit, current quantity/notional, caps, and minimum executable notional policy. It must not reinterpret raw opportunity score to decide membership or target weight.

## Existing Position Boundary

Position Management owns HOLD / ADD / REDUCE / EXIT intent. Portfolio Construction integrates that intent into target membership and target weight. Position Sizing compares current quantity/notional/weight to target and emits quantity delta candidate.

## Negative Score Behavior

Negative `runtime_opportunity_score` is not a schema error. It can lead to exclusion, zero weight, REVIEW_REQUIRED, or rare adoption only through explicit Portfolio Construction method and reason evidence. It must not be clamped, shifted, made absolute, or silently converted into quality or weight.

## Zero-trade Behavior

BUY 0 is a valid Strategy outcome when target weights or executable quantities are zero with explicit reasons. The system must not force BUY count or position count.

## Fail-closed Behavior

Missing target weight authority results in REVIEW_REQUIRED and fail-closed downstream behavior. Silent zero-as-success and forced BUY are forbidden.

## Rejected Design Options

- Option B rejected: Position Sizing deriving weight from raw Opportunity score would concentrate Strategy judgment in Position Sizing.
- Option C deferred: Separate allocation-quality authority may be introduced later, but is not required to close this boundary.

## Architecture SoT Updates

Updated `docs/02_architecture/strategy_architecture_v1.md` with section `3.3.1 Opportunity Score -> Target Weight -> Position Sizing Boundary`.

Created detailed architecture document: `docs/02_architecture/portfolio_construction_and_position_sizing_contract.md`.

## Superseded Contracts

Superseded:

```text
input_score/opportunity_score as quality alias
raw opportunity score -> allocation_quality_score promotion
Position Sizing deriving strategic weight from raw opportunity score
```

Retained:

```text
Ranking上位 != BUY
PM ADD != BUY
BUY 0 allowed
Production/Demo/Historical common contract
fail-closed on missing authority
```

## Implementation Impact

No Production code was changed in Phase23-AN. A future implementation task should update Portfolio Construction to emit target weight authority and Position Sizing to consume that authority.

## Existing Run Preservation

- hash preserved: `true`
- artifact mutation detected: `false`
- reclassification performed: `false`

## Created / Updated Files

- `docs/02_architecture/strategy_architecture_v1.md`
- `docs/02_architecture/portfolio_construction_and_position_sizing_contract.md`
- `docs/phase_reports/phase23_an_opportunity_score_target_weight_position_sizing_boundary_design_closure.md`
- `reports/phase_reports/phase23_an_opportunity_score_target_weight_position_sizing_boundary_design_closure.json`
- `reports/phase23_an_opportunity_score_target_weight_position_sizing_boundary_design_closure/`

## Remaining Gaps

Implementation is not done in AN. The concrete target weight method/version and schema/runtime wiring must be implemented in the next task without inventing score-normalization shortcuts.

## Implementation Readiness

`IMPLEMENTATION_READY = YES`

## Runtime Rerun Readiness

`READY_FOR_RUNTIME_RERUN = NO`

Phase23-AN is a design task and did not run 1BD / 10BD / 20BD.

## Next Recommended Task

Phase23-AO: Production-common Portfolio Construction Target Weight Authority and Position Sizing Boundary Implementation.
