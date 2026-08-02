# Phase24-HT Planning Submit Feasibility Contract

## Primary Contract

Planning Submit Feasibility is a Production Runtime control contract between Planning and APPROVED Pending.

```text
Planning
  -> Submit Feasibility Preflight
  -> APPROVED Pending
  -> Submit Guard
```

Planning must not advance an order to APPROVED Pending when deterministic Submit feasibility is known to fail.

## Planning Responsibility

Planning must verify deterministic feasibility using the same canonical authorities consumed by Submit Guard:

```text
cash
buying_power
market_value
current_exposure
remaining_exposure
active max_exposure
position weight
Safety
Pending duplicate / reservation evidence
BUY feasibility
```

Planning must preserve Strategy and Position Sizing intent. It must not silently change BUY quantity or resize the order.

## Submit Responsibility

Submit Guard remains the final hard pre-broker guard.

Submit Guard must:

```text
repeat all checks
fail closed when active policy is violated
record violated policy/source/version/reason
preserve broker boundary authority
```

Submit Guard must not be skipped because Planning preflight passed.

## Preflight Contract

For BUY items:

```text
current_exposure = sum(Runtime Current positions[].market_value)
remaining_exposure = active max_exposure - current_exposure
PASS when current_exposure + planned BUY estimated_amount <= active max_exposure
```

For SELL items:

```text
SELL is exposure-reducing and is not blocked by BUY max_exposure.
SELL remains subject to quantity, available quantity, Safety, and broker boundary checks.
```

Same-day SELL proceeds or exposure reduction are not pre-credited to BUY capacity unless a later explicit contract approves that behavior.

## Authority

Canonical owner:

```text
CapitalDeploymentPolicy + Runtime Current / Persistent Ledger as consumed by Submit Guard
```

Producer:

```text
Planning Submit Feasibility preflight
```

Consumers:

```text
Pending approval link
Operator reports
Submit Guard observability
```

## Failure State

PASS:

```text
Pending may become APPROVED if all other approval evidence passes.
```

REVIEW_REQUIRED:

```text
Pending must not become APPROVED.
The failed item must remain non-submittable.
Evidence must include current exposure, remaining exposure, planned amount,
violated policy, source, version, and reason.
```

HALT:

```text
Reserved for Safety halt or structurally invalid required Runtime authority
after expected materialization.
```

## Mode Contract

Historical:

```text
Uses historical Runtime Current / Persistent Ledger and historical Safety authority.
No historical-only branch.
```

Demo:

```text
Uses demo Runtime Current / Persistent Ledger and demo Safety/Broker read-only evidence.
```

Production:

```text
Uses production Runtime Current / Persistent Ledger, production Safety, and broker boundary evidence.
```

## Prohibited Changes

```text
Strategy change
PM change
Opportunity Ranking change
Portfolio Policy change
Capital Deployment Policy change
Position Sizing change
BUY quantity change
Submit Guard weakening
max_exposure change
cash reserve change
target exposure change
historical-only branch
test-only branch
```
