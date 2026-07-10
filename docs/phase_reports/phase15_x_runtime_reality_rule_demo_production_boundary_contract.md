# Phase15-X Runtime Reality Rule / Demo-Production Boundary Contract

Date: 2026-07-10

## Objective

Phase15-X defines the Demo / Production boundary before entering Demo Runtime Evidence Review.

This phase does not execute Demo Runtime, Broker Write, orders, notification real send, launchd changes, Current edits, or Runtime bypasses.

The objective is to make the following contract explicit:

```text
Runtime v2 is a production-baseline control system.
Demo environment differences are Broker Environment / Broker Capability / Broker Evidence.
Demo differences must not become Runtime Core behavior.
```

## Runtime Reality Rule

```text
Runtimeは常にProduction Realityを基準として設計する。

Demo環境の制約はRuntime仕様ではなく、
Broker Environment / Broker Capability / Broker Evidenceとして扱う。

Demo専用Runtime、Phase専用Runtime、Fake Runtime、
Demo専用Current、Demo専用Ledger、Demo専用Policyは作らない。

Demo / Productionの差異はBroker LayerまたはCapability Layerで表現し、
Runtime Coreの制御契約は共通に保つ。
```

Runtime Core remains common across Demo and Production:

```text
Policy
↓
Safety
↓
Planning
↓
Pending
↓
Approval
↓
Submit Guard
↓
Broker Boundary
↓
Execution
↓
Ledger
↓
Current
↓
Report
↓
Notification
```

## Demo / Production Boundary Contract

| Boundary | Contract |
|---|---|
| Runtime Core | Production Reality baseline. No Demo-only trading logic, Current, Ledger, Policy, Submit, Execution, Report, or bypass. |
| Broker Environment | Holds mode, endpoint, login window, order window, maintenance status, and environment classification. |
| Broker Capability | Holds Demo/Production differences such as execution restriction, symbol availability, available quantity, and capability mismatch. |
| Broker Evidence | Carries environment/capability evidence into Manifest / Report / Notification where available. |
| Acceptance | Demo can validate Runtime control behavior under Demo evidence, but cannot be inflated into Production readiness. |

Demo constraints are not Runtime仕様. They are evidence that can produce `REVIEW_REQUIRED`, `production_equivalent=false`, or a Broker capability finding.

## Demo API Error Triage

When a Runtime / Broker API error occurs during Demo Review, triage in the following order:

```text
1. Broker login window
2. Broker order/execution window
3. Broker maintenance
4. Demo-specific execution restriction
5. Demo reset / account state reset
6. Broker capability mismatch
7. Runtime bug
8. Broker API behavior change
```

Do not immediately classify a Demo API error as Runtime bug. If the triage cannot be completed, the result is `REVIEW_REQUIRED`, not PASS.

## Required Demo Evidence

Demo Runtime Review must retain the following evidence fields when Broker boundary or Broker evidence is involved:

```text
broker_environment
broker_mode
broker_capability
login_window_status
order_window_status
maintenance_status
demo_execution_restriction_detected
demo_reset_detected
production_equivalent
review_required
```

These fields are not hidden Runtime branches. They are Broker Evidence used to explain whether Demo evidence is production-equivalent and whether Operator review is required.

## Forbidden Demo-Specific Implementation Matrix

| Pattern | Allowed? | Reason | Replacement |
|---|---:|---|---|
| `if demo: special trading logic` | No | Changes Runtime Core behavior for Demo. | Broker capability evidence and `REVIEW_REQUIRED` when needed. |
| `if phase15: special Runtime path` | No | Creates phase-only acceptance that cannot support ongoing operation. | Regular Runtime CLI path only. |
| `demo_current.json` as Current SoT | No | Creates Demo-only asset truth. | `persistent_ledger/state.json` with environment evidence. |
| `demo_ledger.json` as Runtime v2 SoT | No | Reintroduces legacy/demo state as asset truth. | Persistent ledger / Current SoT contract. |
| Demo-only Policy | No | Makes capital deployment unreviewable against Production Reality. | Capital Deployment Policy with source/version/hash. |
| Demo-only Safety | No | Hides safety behavior behind environment. | Runtime Safety Decision evidence. |
| Demo-only Submit | No | Hides Broker boundary behavior. | Common Submit Guard plus Broker capability/evidence. |
| Demo-only Execution | No | Makes fill/current projection non-production-like. | Common Execution / Ledger / Current projection with `production_equivalent`. |
| Demo-only Current projection | No | Makes Current trust invalid. | Runtime-owned fill projection with Broker evidence classification. |
| Demo-only Report | No | Lets Demo explainability diverge from real operation. | Common Report reading Runtime evidence. |
| Runtime bypass to avoid Demo constraints | No | Avoids the control contract being reviewed. | Stop with `REVIEW_REQUIRED` and classify Broker limitation. |
| `broker_environment=demo` | Yes | Explicit environment evidence, not a Runtime branch. | Keep in Manifest / Report. |
| `broker_capability` | Yes | Proper place for Demo/Production differences. | Keep source/version/evidence. |
| `production_equivalent=false` | Yes | Honest evidence classification. | Pair with reason and review status. |
| `review_required=true` | Yes | Safe stop / operator review path. | Pair with `next_operator_action`. |

## Static Risk Scan Result

Static scan scope:

```text
src/ai_fund_lab_v2/runtime_v2
docs/02_architecture/runtime_architecture_v2.md
docs/phase_reports/phase15_u_demo_runtime_review_plan.md
docs/phase_reports/phase15_w_demo_runtime_review_plan_amendment.md
```

| Pattern | Finding | Classification | Follow-up |
|---|---|---|---|
| `production_equivalent` | Present in Submit, Execution, Asset, Broker ReadOnly, Reconcile, Current, Planning. | Allowed Broker / Evidence classification when used as evidence. | Demo review must verify it is reported, not silently converted to PASS. |
| `mode == "demo"` / `mode != "demo"` | Present in Submit, CLI, Reconcile, Planning, Asset projection, Execution, Broker capability. | Mixed: allowed environment/capability checks; risk if used as Runtime Core branch. | Review Demo evidence paths before acceptance. |
| `broker_adapter/fake_demo_submit.py` | Fake demo submit adapter exists. | Test/demo adapter risk; not Full Runtime evidence. | Must not be used to declare Full Runtime PASS. |
| `demo_buy/guarded_test.py` | Demo guarded test path exists. | Phase/demo helper; not regular Runtime Core acceptance path. | Treat as supporting test only. |
| `demo_ledger/` | Documented as legacy; architecture forbids SoT usage. | Legacy artifact risk. | Continue to prevent Current SoT use. |
| `runtime_owned_fill_projection.py` sets demo `production_equivalent=false` | Demo projection explicitly marks non-production-equivalent. | Allowed evidence classification if surfaced. | Demo Review must ensure reason and review status are visible. |
| `planning/morning_pipeline.py` filters Demo 9000-series style candidates | Demo broker capability-like behavior risk. | Needs classification as Broker Capability, not hidden investment policy. | Demo Review must verify filtered/unused capital reason is explained. |
| `bypass` | Found in docs/prohibited wording, not as regular Runtime code path in scan output. | Prohibition documented. | Keep as acceptance stop gate. |
| `phase15` | Found in docs/reports and phase helper context. | Documentation / phase context. | No Phase15-only Runtime PASS allowed. |

## Phase15-U/W Amendment Summary

Updated `docs/phase_reports/phase15_u_demo_runtime_review_plan.md` with:

- Runtime Reality Rule
- Demo / Production Boundary
- Broker Environment / Broker Capability evidence fields
- Demo API Error Triage
- Demo-specific implementation prohibition
- additional Demo Acceptance Stop Gates
- PASS / REVIEW_REQUIRED / FAIL rule amendments

Updated `docs/02_architecture/runtime_architecture_v2.md` with:

- Phase15-X Runtime Reality Rule
- Demo / Production Boundary Contract
- Required Broker Environment Evidence
- Demo API Error Triage
- forbidden and allowed Demo boundary patterns

## Acceptance Impact

Phase15 Demo Review can only pass when:

- Production-baseline Runtime Core behavior is preserved.
- Demo constraints are visible as Broker Evidence.
- Broker API errors are triaged before being classified.
- Demo-specific paths are not used as acceptance evidence.
- `production_equivalent=false` and `review_required=true` are treated as honest evidence, not failures to hide.

Phase15-X does not grant Full Runtime PASS and does not authorize Demo execution. It only fixes the design and review contract before Demo Evidence Review.

## Prohibited Actions Confirmation

This phase did not perform:

- Runtime implementation change
- Demo Runtime execution
- Broker Write
- Demo order
- Production order
- Notification real send
- launchd/plist change
- Current edit
- Runtime bypass creation
- Demo-only Runtime creation
- Phase-only Runtime creation

## Final Judgment

```text
PHASE15X_RUNTIME_REALITY_RULE_DEMO_PRODUCTION_BOUNDARY_CONTRACT_COMPLETE
```
