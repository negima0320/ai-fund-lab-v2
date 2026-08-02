# Phase24-II Position Sizing Aggregate Exposure and Strategy Planning Authority Repair

## 1. Primary Judgment

`PHASE24_II_POSITION_SIZING_AGGREGATE_EXPOSURE_PRECISION_REPAIRED_SHORT_VALIDATION_PASS_OPERATOR_RESUME_REQUIRED`

## 2. Repair Contract

Target weight aggregate validation uses the same Production-common precision contract across Portfolio Construction, Position Sizing, and Strategy Shadow validation.

Contract:

- serialized target weight precision: `6`
- absolute minimum tolerance: `0.000001`
- rounding tolerance: `selected_or_sized_member_count * 0.000001 / 2`
- effective tolerance: `max(absolute minimum, rounding tolerance)`

This accepts serialization-only overflow and preserves BLOCK for real policy overflow.

## 3. Implementation

Added:

- `src/ai_fund_lab_v2/strategy/target_weight_precision.py`

Updated:

- `src/ai_fund_lab_v2/strategy/portfolio_construction.py`
- `src/ai_fund_lab_v2/strategy/position_sizing.py`
- `src/ai_fund_lab_v2/strategy/runtime_planning.py`
- `src/ai_fund_lab_v2/strategy/shadow_runtime.py`
- `tests/strategy/test_phase22_j_position_sizing.py`
- `tests/strategy/test_phase22_g_runtime_planning.py`

## 4. Safety / Policy Preservation

Preserved:

- target gross exposure policy
- Position Sizing policy
- Strategy logic
- Ranking
- Eligibility
- PM decision logic
- Submit Guard
- Safety Guard
- BUY Review non-submittable contract
- Aggregate feasibility guard
- Phase24-IF tolerance contract
- Phase24-IH failed-attempt Pending quarantine contract

## 5. Validation

- `123 passed`
- compile PASS
- Runtime executed: `NO`

Operator resume is required.
