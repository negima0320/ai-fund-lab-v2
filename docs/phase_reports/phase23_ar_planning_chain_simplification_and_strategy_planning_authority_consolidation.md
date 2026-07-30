# Phase23-AR Planning Chain Simplification and Strategy Planning Authority Consolidation

## Primary Judgment

```text
PHASE23_AR_PLANNING_CHAIN_CONSOLIDATION_SHORT_VALIDATION_PASS
```

## Secondary Judgments

```text
CAPITAL_DEPLOYMENT_STANDALONE_PUBLIC_STAGE_RETIRED
RUNTIME_PLANNING_PURE_MAPPER
STRATEGY_PLANNING_AUTHORITY_PENDING_MATERIALIZER
CANONICAL_QUANTITY_CONTRACT_ESTABLISHED
KNOWN_AQ_REGRESSION_RESOLVED
PRODUCTION_DEMO_HISTORICAL_COMMON_CONTRACT
READY_FOR_1BD_OPERATOR_VALIDATION_AFTER_REVIEW
```

## Scope

Phase23-AR simplified the planning chain only. No new Strategy module, score, allocation authority, Runtime switch, Broker write, J-Quants fetch, or Runtime rerun was performed.

## Consolidated Canonical Path

```text
Market Context
  -> Portfolio Policy
  -> Position Management
  -> Portfolio Construction
  -> Position Sizing
  -> Runtime Planning
  -> Strategy Planning Authority
  -> pending_order_plan
```

Capital Deployment is no longer a standalone public Strategy decision stage in the canonical Runtime path. Retained Capital Deployment code/artifacts are classified as noncanonical observability or legacy compatibility evidence.

## Runtime Planning Contract

Runtime Planning now consumes Position Sizing quantity authority:

```text
target_quantity_candidate
quantity_delta_candidate
quantity_status
```

It emits only execution intent mapping fields:

```text
planning_intent
order_side_intent
planned_quantity
no_order_reason
planning_reason
```

It does not recompute target count, exposure, cash reserve, target weight, target notional, opportunity score, quality, or quantity candidate.

## Strategy Planning Authority Contract

Strategy Planning Authority validates required artifacts, schema, temporal authority, lineage/hash, symbol-level plan, execution feasibility, and `planned_quantity`. It materializes `order_plan` and `pending_order_plan` without recomputing allocation, target notional, lot rounding, or quantity from price.

## Known Regression Resolution

The AQ-era failures in `tests/runtime_v2/test_phase23_i_strategy_planning_authority.py` were resolved by removing Capital Deployment as a required Runtime Planning upstream and by binding pending materialization to Runtime Planning `planned_quantity`.

## Validation

Targeted:

```text
py_compile: PASS
runtime_planning + strategy_planning_authority: 21 passed
```

Expanded gating regression:

```text
113 passed
```

A non-gating full morning CLI regression was also observed to BLOCK because of accepted-generation/bootstrap authority and an old stage-name assertion. It is recorded as out of AR acceptance scope; no Runtime rerun was executed.

## Architecture SoT Updates

Updated:

```text
docs/02_architecture/strategy_architecture_v1.md
docs/02_architecture/portfolio_construction_and_position_sizing_contract.md
docs/02_architecture/strategy_architecture_consolidation_review.md
```

## Existing Run Preservation

The required existing runs were not mutated. Read-only hash evidence was recorded for:

```text
runtime-test-historical-smoke-20260729T224044624059Z
runtime-test-historical-smoke-20260729T220208972293Z
```

## Evidence

Evidence directory:

```text
reports/phase23_ar_planning_chain_simplification_and_strategy_planning_authority_consolidation/
```

Machine report:

```text
reports/phase_reports/phase23_ar_planning_chain_simplification_and_strategy_planning_authority_consolidation.json
```

## Remaining Gaps

Fresh Runtime / 1BD validation was not executed by design. Legacy full morning CLI behavior still includes broader accepted-generation/bootstrap gates outside this AR consolidation.

## Next Operator Action

ChatGPT Evidence Review, then operator-controlled 1BD validation if review accepts the AR evidence.
