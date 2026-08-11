# Phase29-I Fixed Cash Reserve Removal and Opportunity-Driven Capital Deployment Design

## Status

COMPLETE

READ_ONLY Architecture / Authority Audit and Production-common Repair Design. No implementation was performed.

Primary Judgment:

```text
PHASE29_I_FIXED_CASH_RESERVE_REMOVAL_ACTIVE_AUTHORITY_CONFIRMED_MULTI_CAUSAL_REPAIR_DESIGN_COMPLETE
```

Implementation gate:

```text
MULTI_CAUSAL_DESIGN_REQUIRED
```

## Executive Summary

An active fixed cash reserve / exposure ceiling authority is present in the Production-common Strategy path.

The authoritative producer is:

```text
configs/strategy/dynamic_cash_exposure.json
src/ai_fund_lab_v2/strategy/dynamic_cash_exposure.py::_decide
```

The authoritative consumer path is:

```text
src/ai_fund_lab_v2/strategy/portfolio_policy.py
-> Portfolio Construction
-> Position Sizing
-> Runtime Planning
```

Current active policy starts from:

```text
baseline_target_cash_ratio = 0.20
baseline_target_gross_exposure_ratio = 0.80
minimum_cash_ratio = 0.12
maximum_gross_exposure_ratio = 0.88
```

Independent Safety also contains:

```text
minimum_cash_ratio = 0.10
maximum_gross_exposure_ratio = 0.90
```

This means the current architecture cannot express user-authoritative near-100% risk-on deployment. Even before Safety, Strategy DCE caps at 88%; Safety caps at 90%. Both must be handled explicitly in a staged repair, not removed blindly.

## Why Final Target Exposure Was 72%

Final 2023-08-25 Portfolio Policy emitted:

```text
target_gross_exposure = 0.72
cash_reserve_ratio = 0.28
```

The producer trace is:

```text
0.80 baseline_target_gross_exposure_ratio
+ RANGE market regime delta 0.00
+ NEUTRAL breadth delta 0.00
+ NORMAL volatility delta 0.00
+ BALANCED risk posture delta 0.00
+ LOW uncertainty delta 0.00
- low_opportunity_capacity delta 0.08
= 0.72
```

This is not solely Market Context defensive cash. It is baseline reserve plus a low-opportunity adjustment.

Important anomaly:

```text
low_opportunity_capacity emitted on 100 / 100 days
Portfolio Policy resolved_opportunity_capacity = 50 on final day
meaningful_allocation_position_count = 50 on final day
```

The current DCE code reads `available_opportunity_count` or `valid_opportunity_count`; the integrated Portfolio Policy evidence reports capacity under other field names. Therefore low-opportunity capacity appears to be at least partly a field-contract mismatch, not a true lack of opportunities.

## 100BD Evidence

Target gross exposure buckets:

```text
0.46 = 3 days
0.54 = 6 days
0.62 = 6 days
0.72 = 20 days
0.75 = 21 days
0.77 = 11 days
0.79 = 33 days
>= 0.80 = 0 days
```

Phase29-H actual exposure:

```text
average actual exposure = 60.8911%
final actual exposure = 67.3503%
exposure >= 80% days = 0 / 100
```

Post-hoc policy ceiling estimate:

```text
average stranded capital vs configured 0.88 ceiling = 155,535.94 JPY/day
```

This is attribution only:

```text
(0.88 - daily target_gross_exposure) * daily portfolio_value
```

It is not proof every yen was executable; lot, concentration, broker, Safety, and quality gates still apply.

## Residual Cash Causality

Residual causes remain multi-causal:

```text
POLICY_EXPOSURE_CEILING = 64 days
LOW_OPPORTUNITY_CAPACITY_AUTHORITY = 64 days with material unused deployable capital
NO_LOT_FEASIBLE_OPPORTUNITY = 57 days
CONCENTRATION_LIMIT = 54 days
BROKER_LIMIT = 64 days
NO_MATERIAL_UNUSED_DEPLOYABLE_CAPITAL = 36 days
```

Conclusion:

```text
Fixed reserve / exposure ceiling is active, but removing it alone is insufficient.
Low-opportunity capacity mapping, lot feasibility, concentration, and broker gates must remain visible and must not be bypassed.
```

## Authority Classification

| Item | Classification | Producer | Consumer | Judgment |
|---|---|---|---|---|
| `baseline_target_cash_ratio=0.20` | ACTIVE_DYNAMIC_POLICY | DCE config / `_decide` | Portfolio Policy / PC / PS | Active fixed reserve starting point |
| `baseline_target_gross_exposure_ratio=0.80` | ACTIVE_DYNAMIC_POLICY | DCE config / `_decide` | Portfolio Policy / PC / PS | Active exposure baseline |
| `minimum_cash_ratio=0.12` | ACTIVE_DYNAMIC_POLICY | DCE config / `_decide` | Portfolio Policy | Active cash floor |
| `maximum_gross_exposure_ratio=0.88` | ACTIVE_DYNAMIC_POLICY | DCE config / `_decide` | Portfolio Policy | Active Strategy ceiling |
| Safety `minimum_cash_ratio=0.10` | ACTIVE_SAFETY_AUTHORITY | Safety limits | DCE clamp | Active hard Safety cash floor |
| Safety `maximum_gross_exposure_ratio=0.90` | ACTIVE_SAFETY_AUTHORITY | Safety limits | DCE clamp | Active hard Safety exposure ceiling |
| Legacy `0.85 / 850000` | DEPRECATED_METADATA_ONLY | DCE shadow comparison / Runtime legacy docs | Observability | Not active PC/PS authority |
| `evaluation_capital=1000000` | DEPRECATED_METADATA_ONLY | Runtime capital deployment metadata | Submit/observability | Not active sizing authority per Phase29-H |
| Test 0.8/0.85 values | TEST_FIXTURE_ONLY | tests | tests | Fixture-only |

## Proposed Contract

Replace fixed reserve semantics with:

```text
authoritative_current_equity
- pending_reserved_cash
= available_capital
```

Then derive:

```text
dynamic_defensive_cash_requirement
```

only from legitimate risk and authority signals:

- Market Context risk-off / stress
- opportunity quality and breadth
- unresolved authority fail-closed
- Safety / Broker / Corporate Action
- Pending reserve
- lot and minimum executable notional
- concentration exhaustion

Deployable capital:

```text
max(0, available_capital - dynamic_defensive_cash_requirement)
```

Deployment continues until:

- deployable exhausted
- no quality opportunity
- no lot-feasible opportunity
- concentration exhausted
- Safety exhausted
- Broker / Corporate Action blocks
- competition exhausted
- unknown authority fail-closed

The contract must explicitly allow:

```text
risk-on + high-quality executable opportunities => cash ratio may approach 0%
```

and must also allow:

```text
risk-off / weak opportunity / infeasible lots => cash remains
```

## Design Options

### Design A — Remove Fixed Baseline/Floor, Retain Dynamic Market Context

Change Dynamic Cash Exposure from baseline reserve semantics to dynamic defensive cash requirement semantics.

Pros:

- Cleanest authority owner.
- Preserves PC/PS as consumers.
- Makes fixed reserve removal explicit.

Cons:

- Must handle Safety cash floor explicitly.
- Requires careful regression.

### Design B — Opportunity-Driven Exposure Ceiling Expansion

Allow target exposure to rise toward near-100 when qualified opportunity capacity, lot feasibility, concentration, Safety, Broker, Corporate Action, and Pending constraints permit.

Pros:

- Best match to user policy.
- Keeps no-forced-investment semantics.

Cons:

- Needs opportunity capacity field repair.
- Requires new observability around dynamic defensive cash and residual cash reasons.

### Design C — PC-Level Residual Capital Expansion

Keep DCE target as-is, but let Portfolio Construction consume residual reserve when high-quality feasible opportunities remain.

Pros:

- Smaller apparent DCE change.

Cons:

- Creates double authority.
- Risks bypassing Market Context / Safety.
- Harder to reason about and test.

Recommendation:

```text
Design A + B staged.
Do not use Design C.
```

## Implementation Design

Future implementation should be staged:

1. Repair opportunity capacity field contract so DCE consumes the same capacity fields Portfolio Policy exposes.
2. Replace fixed `baseline_target_cash_ratio` / `minimum_cash_ratio` semantics with dynamic defensive cash requirement semantics.
3. Expand risk-on upper exposure permission toward near-100 only through explicit policy and Safety review.
4. Preserve all residual cash reason codes.
5. Add regression tests I-R1 through I-R10.

Safety cash floor:

```text
configs/safety/portfolio_limits.json#cash_exposure.minimum_cash_ratio = 0.10
```

must be an explicit future implementation decision. It is an active Safety authority and cannot be silently bypassed. The Phase29-I design keeps concentration Safety `0.25` unchanged.

## Required Regression Contract

Future implementation must cover:

```text
I-R1 risk-on + enough high-quality opportunities + executable lots => cash can approach zero
I-R2 risk-on + no eligible opportunities => cash remains
I-R3 risk-off => dynamic defensive cash remains
I-R4 concentration blocked => no cap bypass
I-R5 lot infeasible => recycle or cash remains
I-R6 pending BUY reserve exists => reserved cash not reused
I-R7 unresolved authority => fail-closed
I-R8 current equity > initial 1M => current equity remains sizing base
I-R9 loss reduces equity => deployment shrinks naturally
I-R10 planned SELL proceeds not executed => not deployable
```

Cross-phase preservation:

```text
Phase28 D55-A
D61
D63
D69
D70B
Phase29-E
Phase29-E2
Phase29-G
PC / PS / Runtime Planning
SELL / REDUCE / EXIT
Pending / Submit
Safety / Broker / Corporate Action / Temporal
```

## Implementation Gate

```text
MULTI_CAUSAL_DESIGN_REQUIRED
```

Not a blind one-line config change.

Implementation readiness:

```text
NO for one-shot implementation.
YES only as a staged Phase29-J repair that first resolves Safety cash-floor policy and opportunity-capacity field mapping.
```

## Deliverables

```text
reports/phase29_i_fixed_cash_reserve_removal_opportunity_driven_capital_deployment_design/cash_authority_inventory.json
reports/phase29_i_fixed_cash_reserve_removal_opportunity_driven_capital_deployment_design/capital_flow_authority_map.json
reports/phase29_i_fixed_cash_reserve_removal_opportunity_driven_capital_deployment_design/daily_policy_vs_actual_exposure.csv
reports/phase29_i_fixed_cash_reserve_removal_opportunity_driven_capital_deployment_design/cash_residual_causality.json
reports/phase29_i_fixed_cash_reserve_removal_opportunity_driven_capital_deployment_design/hidden_exposure_ceiling_audit.json
reports/phase29_i_fixed_cash_reserve_removal_opportunity_driven_capital_deployment_design/market_context_cash_policy_audit.json
reports/phase29_i_fixed_cash_reserve_removal_opportunity_driven_capital_deployment_design/opportunity_capacity_audit.json
reports/phase29_i_fixed_cash_reserve_removal_opportunity_driven_capital_deployment_design/legacy_cash_constraint_audit.json
reports/phase29_i_fixed_cash_reserve_removal_opportunity_driven_capital_deployment_design/design_options.json
reports/phase29_i_fixed_cash_reserve_removal_opportunity_driven_capital_deployment_design/regression_contract.json
reports/phase29_i_fixed_cash_reserve_removal_opportunity_driven_capital_deployment_design/risk_register.json
reports/phase29_i_fixed_cash_reserve_removal_opportunity_driven_capital_deployment_design/implementation_gate.json
```
