# Phase24-ID Aggregate Portfolio Constraint and Execution Reconciliation Contract

## Primary Judgment

`PHASE24_ID_AGGREGATE_PORTFOLIO_CONSTRAINT_AND_NEGATIVE_CASH_PROJECTION_CONTRACT_FROZEN`

## Scope

This contract covers Planning Submit Feasibility, Submit Guard, runtime-owned
fill projection, and Execution Reconciliation for one approved Pending batch.

It does not change Strategy, Ranking, Portfolio Policy, PM, Position Sizing
policy, BUY quantity, max_exposure, max_positions, cash buffer, or target
exposure.

## Aggregate Pending Batch Feasibility

Planning Submit Feasibility and Submit Guard must evaluate approved Pending
items as one ordered feasibility set before a plan becomes submittable.

BUY items reserve:

```text
cash
buying_power
current_exposure
active max_positions slot when the BUY creates a new symbol position
```

Later BUY items in the same Pending batch must see the reserved state left by
earlier BUY items.

SELL items remain liquidation actions. Same-day SELL proceeds or exposure
reduction are not pre-credited to BUY capacity without a later explicit
contract.

## Failure State

If aggregate feasibility fails:

```text
status = REVIEW_REQUIRED
broker/adapter boundary = not crossed for the invalid batch
pending approved BUY ids = empty or blocked according to review scope
evidence = item-level violated policy and pre/post reservation values
```

The condition is not `HALT` unless Safety requires runtime halt or a required
authority is structurally invalid after expected materialization.

## Submit Responsibility

Submit Guard remains the final hard guard. It must re-run the same aggregate
authority before item submission and must not trust Planning evidence as a
replacement for its own validation.

## Projection Responsibility

Runtime-owned fill projection must preserve impossible cash states as
REVIEW_REQUIRED evidence. It must not clamp negative projected cash or buying
power to zero and mark the projection PASS.

## Reconciliation Responsibility

Execution Reconciliation compares broker/historical execution snapshot cash and
buying_power against Runtime Current. Exact finding objects must be
materialized or reproducible from source inputs. Missing serialized finding
detail is an observability gap.

## Authority

Canonical authorities:

```text
CapitalDeploymentPolicy
Runtime Current / Persistent Ledger
Pending approved item set
Historical/Demo/Production execution snapshot
Runtime-owned fill projection
Execution Reconciliation checks
```

Historical, Demo, and Production share this contract.
