# Phase32-AZ Production-Shaped Marginal Capital Value Authority Implementation

## Executive Summary

Phase32-AZ implemented `canonical_marginal_capital_frontier_authority.v1` as a
Portfolio Construction-owned, production-shaped but consumer-disabled marginal
capital value authority.

The implementation is additive. It does not connect the authority artifact to
Position Sizing, Runtime Planning, Pending, Orders, Execution, Safety, PM,
REDUCE, EXIT, Cash policy, Risk Pacing, or production thresholds.

The artifact converts the already accepted shadow frontier candidate surface
into a bounded deterministic cardinal-value contract and emits future
PS-compatible target-gap fields:

- `current_weight`
- `target_weight`
- `accepted_incremental_weight`
- `target_gap`
- `target_minus_current`
- `accepted_incremental_notional`
- `accepted_frontier_candidate_ids`
- `capital_value_authority`
- `target_weight_reason_codes`

Production consumers remain disabled:

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

## Required Design Inputs

Read and incorporated:

- `docs/phase_reports/phase32_ay_marginal_capital_frontier_production_migration_design.md`
- `docs/phase_reports/phase32_ax_broad_fresh_run_shadow_frontier_acceptance.md`
- `docs/phase_reports/phase32_ar_shadow_common_marginal_capital_value_add_next_lot_architecture_design.md`
- `docs/02_architecture/high_resolution_marginal_capital_value_and_portfolio_rotation_architecture.md`
- `docs/02_architecture/portfolio_construction_and_position_sizing_contract.md`

## Implemented Artifact

Module:

```text
src/ai_fund_lab_v2/strategy/marginal_capital_frontier_authority.py
```

Schema:

```text
canonical_marginal_capital_frontier_authority.v1
```

Owner:

```text
PORTFOLIO_CONSTRUCTION_CAPITAL_VALUE_AUTHORITY
```

Mode:

```text
PRODUCTION_SHAPED_CONSUMER_DISABLED
```

The authority builder can be called directly from PC-shaped inputs or from an
already materialized shadow frontier payload. It preserves
`canonical_marginal_capital_frontier.v1` as non-authoritative source evidence
and emits a separate production-shaped result.

## Cardinal Value Contract

The implemented value contract is bounded and deterministic:

```text
value_min = 0.0
value_max = 1.0
higher_is_better = true
tie_tolerance = 1e-9
```

Security candidate value is derived only from decision-time fields already
materialized in the candidate surface:

- opportunity score
- quality score
- opportunity rank
- semantic requalification evidence
- remaining single-name headroom

Cash is a first-class candidate. If Cash is explicitly preferred by
decision-time evidence it receives top value; otherwise it remains a low but
present optionality baseline.

The contract explicitly records:

```text
semantic_type_multiplier_used = false
fixed_share_size_rule_used = false
fixed_add_multiplier_used = false
fixed_position_count_rule_used = false
historical_outcome_parameter_selection_used = false
```

Ambiguous top cross-type cardinal values fail closed as `REVIEW_REQUIRED`.

## Multi-Lot ADD Authority

ADD candidates are accepted sequentially by symbol/campaign:

```text
ADD lot #2 requires accepted ADD lot #1
ADD lot #3 requires accepted ADD lot #2
...
```

After each accepted increment the authority recomputes remaining Cash in the
target projection. Cap, Cash, Safety, Risk Pacing, and no-loss-averaging
guardrails remain inherited from the frontier candidate contract.

## Fail-Closed Behavior

The authority emits no accepted targets when any required decision-time
evidence is missing, ambiguous, or review-required at the candidate or cash
source level.

Covered fail-closed cases:

- missing campaign identity for ADD
- missing/review-required Cash
- ambiguous cross-type top value
- candidate observability review
- feasibility review
- constraint review

Forbidden future/outcome fields are recursively stripped from authority output.

## Architecture SoT Updates

Updated:

- `docs/02_architecture/high_resolution_marginal_capital_value_and_portfolio_rotation_architecture.md`
- `docs/02_architecture/portfolio_construction_and_position_sizing_contract.md`

The SoT now records the Phase32-AZ authority schema, bounded cardinal value
contract, PS-compatible target fields, disabled-consumer boundary, and the fact
that the shadow frontier remains non-authoritative.

## Changed Files

- `src/ai_fund_lab_v2/strategy/marginal_capital_frontier_authority.py`
- `tests/strategy/test_phase32_az_marginal_capital_frontier_authority.py`
- `docs/02_architecture/high_resolution_marginal_capital_value_and_portfolio_rotation_architecture.md`
- `docs/02_architecture/portfolio_construction_and_position_sizing_contract.md`
- `docs/phase_reports/phase32_az_production_shaped_marginal_capital_value_authority_implementation.md`

## Focused Verification

Commands:

```text
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3 -m pytest -q tests/strategy/test_phase32_az_marginal_capital_frontier_authority.py tests/strategy/test_phase32_as_common_marginal_capital_frontier_shadow.py tests/strategy/test_phase32_au_shadow_frontier_cash_source_resolver.py
```

Result:

```text
23 passed in 0.12s
```

Compile check:

```text
PYTHONPYCACHEPREFIX=/private/tmp/ai-fund-lab-v2-pycache PYTHONPATH=src python3 -m py_compile src/ai_fund_lab_v2/strategy/marginal_capital_frontier_authority.py tests/strategy/test_phase32_az_marginal_capital_frontier_authority.py
```

Result: PASS.

## Regression Coverage

Focused tests cover:

- NEW accepted target
- REENTRY accepted target
- ADD #1/#2/#N sequential acceptance and cap stop
- Cash win
- cap block
- insufficient Cash block
- Safety block
- Risk Pacing block
- missing campaign fail-closed
- missing Cash fail-closed
- ambiguous cross-type value fail-closed
- deterministic rerun
- future/outcome field rejection
- PS-compatible target fields
- production consumer disabled
- shadow production consumer count remains 0

## Production Boundary

No production consumer was enabled. No fresh-run, resume, replay, backtest, or
long Historical run was executed.

The new authority is ready for dual-read acceptance only. Production activation
still requires a separate migration task that explicitly switches consumers and
validates Position Sizing behavior.

## Final Judgments

```text
PHASE32_AZ_CARDINAL_VALUE_AUTHORITY_IMPLEMENTED = YES
PHASE32_AZ_ACCEPTED_TARGET_GAP_EMITTED = YES
PHASE32_AZ_MULTI_LOT_ADD_SUPPORTED = YES
PHASE32_AZ_GUARDRAILS_PRESERVED = YES
PHASE32_AZ_PIT_SAFE = YES
PHASE32_AZ_DETERMINISTIC = YES
PHASE32_AZ_PRODUCTION_CONSUMER_ENABLED = NO
PHASE32_AZ_SHADOW_PRODUCTION_CONSUMER_COUNT = 0
PHASE32_AZ_REGRESSION_STATUS = PASS
PHASE32_AZ_READY_FOR_DUAL_READ_ACCEPTANCE = YES
PHASE32_AZ_PRODUCTION_BEHAVIOR_CHANGED = NO
PHASE32_AZ_NEXT_STEP = Run a READ-ONLY dual-read acceptance on fresh artifacts, comparing existing production PC/PS outputs against canonical_marginal_capital_frontier_authority.v1 target-gap projections without enabling consumers.
```
