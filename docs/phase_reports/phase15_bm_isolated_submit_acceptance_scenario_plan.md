# Phase15-BM Isolated Submit Acceptance Scenario Plan

## Decision

Normal Submit Acceptance must not use the existing `.runtime` root that contains the 4591 Safety-blocked evidence.

Assessment:

```text
ISOLATED_SUBMIT_ACCEPTANCE_ROOT_REQUIRED
```

Recommended root:

```text
.runtime_acceptance_phase15_submit
```

BM does not create or run this root. It only defines the scenario.

## Recommended Scenario

Use an isolated temporary Runtime Root first, then optionally materialize `.runtime_acceptance_phase15_submit` in Phase15-BN.

Preferred option:

```text
A. 隔離temporary Runtime Root
```

Reason:

- Existing `.runtime` keeps 4591 Safety-blocked evidence intact.
- Safety Event, Current, Pending, Ledger, and Broker Evidence are not rewritten.
- Normal Submit can be validated with internally consistent fixtures.
- Broker Write can remain disabled until a later explicit scope.

## Required Evidence

The isolated normal Submit scenario must include:

- Safety `SAFE` or action permission `sell_submit=ALLOWED`
- `broker_write` permission explicitly defined for the intended scope
- Market / Quote `READY`
- Broker ReadOnly `READY`
- Current `READY`
- Policy `READY`
- Valid Human Approval
- Valid Promotion Candidate
- Valid Apply Candidate
- Pending Slot `EMPTY` before Apply
- Authoritative Pending `APPROVED` after explicit Apply
- Order conditions resolved by formal authority
- Broker available quantity check available for SELL
- Target Session valid

## Required Boundaries

Phase15-BN should prepare the isolated root and evidence only. Broker Write should remain out of scope unless a later prefix explicitly authorizes it.

The scenario must not:

- Clear the 4591 Safety Event
- Modify existing `.runtime`
- Reuse existing `.runtime` Current / Pending / Ledger as write targets
- Infer order conditions from Runtime scaffolding
- Treat Human Approval as Safety override

## Open Contract

Before normal Submit Acceptance:

```text
ORDER_CONDITION_AUTHORITY_CONTRACT_REQUIRED
```

This contract must define whether order conditions come from Policy, Human Approval, Submit Pending Producer, or Broker capability evidence.

## Recommended Next Prefix

```text
Phase15-BN Runtime Acceptance Step2 Isolated Normal Submit Scenario Preparation
```
