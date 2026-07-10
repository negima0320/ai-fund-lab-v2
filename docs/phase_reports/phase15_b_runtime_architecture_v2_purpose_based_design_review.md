# Phase15-B Runtime Architecture v2 Purpose-Based Design Review

## Summary

Phase15-B reviewed `docs/02_architecture/runtime_architecture_v2.md` from the Phase15-A purpose:

```text
年間50%の利益を目指し、安心・安全に自動売買を継続できる運用システムを実現すること
```

The review focused on whether Runtime v2, as the control center of AI Fund Lab v2, could accidentally obstruct the system purpose through hidden policy, hidden conservatism, BUY / SELL guard confusion, or weak review criteria.

Final judgment: **PHASE15B_RUNTIME_ARCHITECTURE_PURPOSE_BASED_REVIEW_COMPLETE**

This phase is documentation-only.

No Runtime implementation change, Submit, Broker Write, Production order, Notification real send, launchd/plist change, Current direct edit, Phase15-specific Runtime bypass, or fake-adapter Full Runtime PASS declaration was performed.

## Reviewed Document

Updated:

```text
docs/02_architecture/runtime_architecture_v2.md
```

Created:

```text
docs/phase_reports/phase15_b_runtime_architecture_v2_purpose_based_design_review.md
reports/phase_reports/phase15_b_runtime_architecture_v2_purpose_based_design_review.json
```

## Review Basis

Phase15-A defined Runtime v2 as the system control center:

```text
AI
↓
Capital Allocation
↓
Safety
↓
Runtime
↓
Broker
↓
Current
↓
Report
↓
Notification
```

Therefore, Runtime v2 must not silently replace AI / Capital Allocation / Risk Policy / Safety with local defaults. Runtime must execute explicit contracts, preserve evidence, and stop as `REVIEW_REQUIRED` when policy or evidence is missing.

## Findings

### 1. Existing Design Already Covered Many Phase15 Concerns

The architecture already stated:

- Runtime is not AI.
- Runtime must not block Capital Allocation / Risk Policy with hidden fixed values.
- Runtime has no hidden `max_positions` default.
- Runtime has no hidden order amount, cash buffer, or investment ratio default.
- Capital Deployment Contract must define target investment ratio, cash buffer, max position weight, max positions, min/max order amount, BUY notional guard, SELL liquidation guard, and Safety stop conditions.
- Submit Guard must not override Capital Allocation with hidden fixed caps.
- BUY notional guard and SELL liquidation guard must not be treated as the same guard without explicit design.
- SELL liquidation source is Runtime-owned Current only.
- `tests pass` is necessary but not sufficient for acceptance.
- Review levels must distinguish Level1 Component, Level2 Flow, and Level3 Full Runtime.

Judgment: `PARTIAL_READY_WITH_PHASE15_PURPOSE_CLARIFICATION_NEEDED`

### 2. Purpose-Based Hidden Policy Prohibition Needed Stronger Wording

The design prohibited hidden defaults, but Phase15-A requires the reason to be tied directly to the AI Fund Lab v2 purpose.

Added:

```text
12.3 Phase15-B 追補: Purpose-Based Runtime Control Contract
```

This section explicitly prohibits Runtime from using local fixed policies that would over-conservatize the system or silently change capital deployment.

Judgment: `AMENDED`

### 3. Capital Deployment Boundary Needed Clearer Operational Contract

The design already had Capital Deployment Contract, but Phase15-B required stronger separation between what Runtime executes and what Runtime must not decide.

Added explicit contract that Runtime does not decide:

- target investment ratio
- cash buffer
- max exposure
- max position weight
- position sizing
- buying power usage
- order size
- rebalance / replacement
- position count
- SELL-first / BUY-after-fill

Runtime must read these as explicit policy, emit policy source/version/effective mode, and stop as `REVIEW_REQUIRED` rather than filling gaps with hidden defaults.

Judgment: `AMENDED`

### 4. Position Count and Order Amount Contracts Needed More Manifest Requirements

The design already prohibited `max_positions=5` and hidden order amount caps. Phase15-B added stronger manifest/report/audit requirements for:

- active max positions policy
- max positions source/version
- post-trade position count
- manual review status
- violated policy
- policy source/version
- Planning amount
- Capital Allocation amount
- Submit estimated amount
- whether the issue should have been blocked at Planning

Judgment: `AMENDED`

### 5. BUY / SELL Guard Separation Was Present but Reinforced

The architecture already separated BUY and SELL after Phase14-E55. Phase15-B reinforced the purpose-based distinction:

- BUY is new risk deployment.
- SELL is risk reduction.
- SELL liquidation must not be stopped only by BUY notional cap.
- SELL liquidation must be controlled by Runtime-owned Current position, Current quantity, Broker available quantity, Broker issue code normalization, Safety / Operation Guard, and explicit SELL liquidation policy.

Judgment: `AMENDED`

### 6. Review Rules Needed to Be Embedded in Architecture Acceptance

The design already had Review Level and tests-pass caveats. Phase15-B added:

```text
22.3 Phase15 Review Rule
```

This embeds:

- Runtime Evidence First Rule
- Evidence Request Rule
- No Guess Rule
- PASS misclassification prohibition
- `Broker Accepted` is not Runtime PASS
- `Report generated` is not Report semantic PASS
- `Payload generated` is not Notification PASS

Judgment: `AMENDED`

## Architecture Amendments

Updated `docs/02_architecture/runtime_architecture_v2.md` with:

1. `12.3 Phase15-B 追補: Purpose-Based Runtime Control Contract`
2. `22.3 Phase15 Review Rule`

## Phase15-B Review Checklist

| Review Item | Judgment |
| --- | --- |
| Runtime purpose tied to AI Fund Lab v2 final purpose | AMENDED |
| Runtime hidden policy prohibition | AMENDED |
| `max_order_amount=100000` style fixed cap prohibited | ALREADY_DEFINED_AND_REINFORCED |
| `max_positions=5` style fixed count prohibited | ALREADY_DEFINED_AND_REINFORCED |
| Runtime-owned cash buffer / investment ratio prohibited | AMENDED |
| Capital Deployment Contract boundary clarified | AMENDED |
| BUY order amount derivation clarified | AMENDED |
| SELL liquidation contract separated from BUY | ALREADY_DEFINED_AND_REINFORCED |
| Capital Allocation vs Submit Guard boundary clarified | AMENDED |
| Manifest / report / audit requirements expanded | AMENDED |
| Runtime Evidence First Rule added | AMENDED |
| Evidence Request Rule added | AMENDED |
| No Guess Rule added | AMENDED |
| Review Level distinction retained | PASS |
| tests pass alone is not acceptance | ALREADY_DEFINED_AND_REINFORCED |
| Broker Accepted alone is not Runtime PASS | AMENDED |
| Report generated alone is not semantic PASS | AMENDED |
| Payload generated alone is not Notification PASS | AMENDED |

## Prohibited Actions Check

| Action | Performed |
| --- | --- |
| Runtime implementation change | No |
| Submit execution | No |
| Broker Write | No |
| Production order | No |
| Notification real send | No |
| launchd/plist change | No |
| Current direct edit | No |
| Phase15-specific Runtime bypass | No |
| fake adapter Full Runtime PASS declaration | No |

## Final Judgment

```text
PHASE15B_RUNTIME_ARCHITECTURE_PURPOSE_BASED_REVIEW_COMPLETE
```
