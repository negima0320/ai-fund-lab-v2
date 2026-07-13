# Operational Lifecycle, State Reset Boundary, and Environment Transition Contract

Status: Phase16-O accepted design draft

This document defines the permanent lifecycle contract for moving AI Fund Lab v2 through:

```text
Historical Runtime Test
↓
Tachibana Demo Operation
↓
Production Operation
```

It defines what is retained, what is regenerated per run, what can be reset, what must never be inherited across environments, and how transitions are closed and initialized. It is not a reset implementation, backup implementation, Registry implementation, path creation plan, broker connection, or simulation runner.

## Purpose

AI Fund Lab v2 exists to build a Japanese equity auto-trading system that can be operated safely and continuously, and eventually in Production.

Historical Runtime Test and Demo Operation are verification stages toward Production. They must not create:

- Historical-only AI
- Demo-only AI
- Production-only Feature schema
- Backtest-only Canonical Data
- environment-specific Runtime mainlines

All stages use the same:

- Canonical Data Contract
- Feature Producer
- Feature Schema
- Accepted AI Artifact
- Policy / Safety Contract
- Runtime v2 Mainline
- Artifact Registry

Trading state may be reset at the start of each environment. Operational foundation must be retained across environments.

## Lifecycle Domains

| Domain | Scope | Environment transition behavior |
|---|---|---|
| Persistent Operational Foundation | Canonical data, schema, accepted artifacts, policy, registry, freeze/evidence history | Retain across Historical, Demo, and Production. |
| Run-scoped Reproducible Artifacts | Features, decisions, manifests, reports, audit/performance evidence | Preserve as evidence; regenerate for each new run; do not inherit as authority. |
| Resettable Trading and Runtime State | Current, Ledger, Pending, approval, execution, broker/trading state, cash, positions | Backup then clean reset or initialize for each environment. |

## Persistent Operational Foundation

Persistent Operational Foundation must not be deleted, initialized, or rewritten by Trading State Reset.

| Item | Retention | Immutability | Backup | Versioning | Replacement / revoke | Reset exclusion |
|---|---|---|---|---|---|---:|
| J-Quants Raw | Retain provider-origin evidence and manifests | Append-only / immutable raw evidence | Operational Foundation Backup | endpoint/date/request manifest | supersede by new raw artifact; never overwrite accepted evidence | Yes |
| Canonical Market Data | Retain accepted canonical outputs and manifests | Immutable per artifact hash | Operational Foundation Backup | canonical artifact id/hash/schema | replace by new accepted artifact; old artifact becomes legacy/read-only | Yes |
| Trading Calendar | Retain accepted calendar versions | Immutable per version/hash | Operational Foundation Backup | calendar version/as_of/hash | revoke unsafe version; accept new version | Yes |
| Listed Issues | Retain listed/universe evidence versions | Immutable per version/hash | Operational Foundation Backup | listed data version/as_of/hash | revoke/supersede with accepted version | Yes |
| Corporate Action | Retain split/reverse split/delisting/adjustment evidence | Immutable per version/hash | Operational Foundation Backup | corporate-action version/as_of/hash | revoke/supersede with accepted version | Yes |
| Feature Schema | Retain accepted schema and hash | Immutable per schema version | Operational Foundation Backup | schema id/version/hash | schema change requires separate acceptance | Yes |
| Accepted Candidate Artifact Set | Retain model, manifest, schema, validation evidence | Immutable accepted set | Operational Foundation Backup | set id/model hash/schema hash | revoke/supersede by accepted set | Yes |
| Accepted Opportunity Model / Metrics Artifact Set | Retain model and metrics as a matched accepted set | Immutable accepted set | Operational Foundation Backup | set id/model hash/metrics hash | revoke/supersede by accepted set | Yes |
| PM Code Policy / Runtime Adapter Artifact Set | Retain code-policy and adapter hash identity | Immutable accepted set | Operational Foundation Backup | set id/code hash/adapter hash | revoke/supersede by accepted set | Yes |
| Policy Artifact | Retain policy versions and hashes | Immutable accepted policy | Operational Foundation Backup | policy version/hash | revoke/supersede through policy acceptance | Yes |
| Safety Artifact / Contract | Retain safety definitions and accepted runtime decision schema | Immutable per version/hash | Operational Foundation Backup | safety version/hash | revoke/supersede through safety acceptance | Yes |
| Capital Allocation Policy Artifact | Retain accepted allocation policy | Immutable per version/hash | Operational Foundation Backup | allocation policy version/hash | revoke/supersede through policy acceptance | Yes |
| Artifact Registry event history | Retain complete append-only event history | Append-only; no deletion | Operational Foundation Backup | event ids/checkpoints/index hash | append revoke/supersede event; do not delete history | Yes |
| Materialized Registry index | Retain rebuildable current index | Rebuildable from event log | Operational Foundation Backup | checkpoint/index hash | rebuild from accepted event history | Yes |
| Model / Policy Freeze Manifest | Retain accepted freeze manifests | Immutable per manifest hash | Operational Foundation Backup | freeze manifest id/hash | supersede with new accepted freeze | Yes |
| Training / Validation Evidence | Retain lineage evidence | Read-only evidence | Operational Foundation Backup | evidence id/hash | mark legacy/revoked when invalid; do not use as Runtime authority | Yes |
| Migration / Legacy history | Retain migration manifests and legacy classifications | Append-only / read-only | Operational Foundation Backup | migration id/checkpoint/hash | supersede/revoke; deletion requires separate acceptance | Yes |

Reset tools must treat every Persistent Operational Foundation item as out of scope. If a reset target includes these items, reset must stop with `HALT`.

## Run-scoped Reproducible Artifacts

Run-scoped artifacts are generated by a specific run and remain audit evidence after the run closes. They must not become implicit authority for the next run or next environment.

| Artifact | Scope | Retention | Regeneration rule | Next-run authority |
|---|---|---|---|---:|
| Feature Artifact | run-scoped / business-date scoped | Preserve as evidence | regenerate from accepted Canonical Data, Feature Producer, Feature Schema, run metadata | No implicit authority |
| Candidate Decision Artifact | run-scoped / business-date scoped | Preserve as evidence | regenerate from accepted Feature Artifact and Candidate Artifact Set | No implicit authority |
| Opportunity Decision Artifact | run-scoped / business-date scoped | Preserve as evidence | regenerate from accepted Candidate Decision, Feature Artifact, Opportunity set | No implicit authority |
| Position Management Decision Artifact | run-scoped / business-date scoped | Preserve as evidence | regenerate from accepted PM set, Current, feature/opportunity inputs | No implicit authority |
| Capital Allocation Signal / Decision Evidence | run-scoped / business-date scoped | Preserve as evidence | regenerate from policy, safety, current, opportunity inputs | No implicit authority |
| Safety Decision | run-scoped / freshness scoped | Preserve as evidence | regenerate or revalidate for each run/date | No implicit authority unless freshness and run scope match |
| Policy Decision | run-scoped / business-date scoped | Preserve as evidence | regenerate or bind to accepted policy for each run | No implicit authority |
| Planning Artifact | run-scoped | Preserve as evidence | regenerate from accepted inputs and current run trading state | No implicit authority |
| Runtime Report | run-scoped | Preserve as evidence | generate per run | No authority |
| Audit Report | run-scoped | Preserve as evidence | generate per run | No authority |
| Run Manifest | run-scoped | Preserve as evidence | generate per run | No authority except identity evidence |
| Point-in-time Manifest | run-scoped / business-date scoped | Preserve as evidence | generate per run/date | No implicit authority |
| Performance Report | run-scoped / environment scoped | Preserve as evidence | generate after closed run | No trading authority |

New runs must use new `run_id` and `environment_id` metadata. Historical-run Feature / Decision Artifacts may be read for reproducibility comparison or audit, but must not become Demo or Production decision authority.

## Resettable Trading State

Resettable Trading and Runtime State may be clean reset or initialized at an environment boundary after required backup.

Minimum resettable scope:

- Current
- Persistent Ledger
- Pending
- Runtime State
- Approval state
- Execution state
- Idempotency state
- Open orders
- Broker simulation state
- Cash
- Buying power
- Positions
- Realized PnL
- Unrealized PnL
- Operational transient state

Initial values are environment configuration, not hard-coded contract values. Example for a clean verification environment:

```text
cash=1,000,000 JPY
buying_power=1,000,000 JPY
positions=0
pending=0
open_orders=0
executions=0
realized_pnl=0
unrealized_pnl=0
```

Production initialization may differ and must be reconciled from broker evidence.

## Reset Exclusion

Reset must not touch:

- Canonical Data
- Feature Schema
- Accepted Model / Metrics
- PM Code Policy
- Policy / Safety definitions
- Capital Allocation Policy
- Artifact Registry history
- Model Freeze Manifest
- Training / Validation Evidence
- Legacy Artifact
- Architecture documents
- Phase evidence

If a reset plan or tool target includes reset-excluded items, behavior is:

```text
HALT
```

Partial reset is prohibited. Current-only reset, Ledger-only reset, Pending-only reset, or mismatched Current/Ledger/Pending initialization must not proceed.

## Environment Identity

Environment identity separates Historical, Demo, and Production lifecycle boundaries without creating separate Canonical Data or Registry authorities.

Required fields:

- `environment_id`
- `run_type`
- `broker_environment`
- `started_at`
- `closed_at`
- `initial_state_hash`
- `final_state_hash`
- `model_freeze_manifest_ref`
- `policy_freeze_manifest_ref`
- `canonical_data_manifest_ref`
- `feature_schema_ref`
- `registry_checkpoint_ref`
- `previous_run_ref`
- `transition_reason`

Allowed `run_type` values:

- `HISTORICAL`
- `DEMO`
- `PRODUCTION`

Mode differences must be represented by environment/run metadata, not by separate Registries or separate Runtime mainlines.

## Run Identity

Required run fields:

- `run_id`
- `environment_id`
- `run_type`
- `broker_environment`
- `business_date`
- `started_at`
- `closed_at`
- `initial_state_hash`
- `final_state_hash`
- `model_freeze_manifest_ref`
- `policy_freeze_manifest_ref`
- `canonical_data_manifest_ref`
- `feature_schema_ref`
- `registry_checkpoint_ref`
- `previous_run_ref`
- `transition_reason`

Every generated Feature, Decision, Planning, Report, Audit, and Performance artifact must be traceable to `run_id` and `environment_id`.

## Historical To Demo Transition

Required sequence:

1. Freeze Historical final evidence.
2. Backup Historical Trading State.
3. Mark Historical Run as `CLOSED`.
4. Clean reset normal Runtime Trading State.
5. Generate Demo initial state from Demo configuration and broker environment settings.
6. Preserve AI, Canonical Data, Feature Schema, Policy/Safety Contract, and Registry.
7. Explicitly set Demo `broker_environment`.

Forbidden:

- inherit Historical Position into Demo
- use Historical Ledger as Demo authority
- submit Historical Pending in Demo
- reflect Historical PnL into Demo Current
- use Historical Feature / Decision Artifact as Demo trading authority

Historical evidence may be read only for audit, reproducibility, and transition review.

## Demo To Production Transition

Required sequence:

1. Freeze Demo final evidence.
2. Backup Demo Trading State.
3. Mark Demo Run as `CLOSED`.
4. Perform Production account reconciliation.
5. Clean initialize normal Runtime Trading State for Production.
6. Determine Production initial Current from broker evidence and reconciliation.
7. Preserve AI, Canonical Data, Feature Schema, Policy/Safety Contract, and Registry.
8. Enable Production Broker authority only by separate Acceptance.

Forbidden:

- reuse Demo Position as Production Position
- use Demo Ledger as Production authority
- submit Demo Pending in Production
- reuse Demo execution id in Production
- use Demo PnL as Production Current

## Backup / Restore Boundary

### Trading State Backup

Trading State Backup includes:

- Current
- Ledger
- Pending
- Runtime State
- Approval
- Execution
- Idempotency
- Broker state

Trading State Backup is mandatory before Trading State Reset.

### Operational Foundation Backup

Operational Foundation Backup includes:

- Canonical Data manifests
- Accepted Artifact Sets
- Registry
- Freeze Manifests
- Schemas
- Policies

Operational Foundation is reset-excluded, but must still be backed up independently for Production operations and disaster recovery.

### Restore Rules

Forbidden:

- restore Historical Trading State into Demo
- restore Demo Trading State into Production
- restore Trading State into a different `environment_id`
- restore Trading State across unrelated run lineage
- partial restore of Current/Ledger/Pending

Except for explicit disaster recovery acceptance, Trading State restore is limited to the same Environment / Run lineage.

## AI Continuity

Historical, Demo, and Production must preserve:

- same accepted logical artifact identity
- same model hash
- same metrics hash
- same PM code-policy hash
- same feature schema hash
- same policy hash

AI changes must be separated from environment transition and require separate Artifact Acceptance and version update.

Forbidden:

- implicit model change during environment transition
- retraining at Demo start
- overwriting model at Production start
- changing an artifact under the same version based on backtest result

## Feature / Decision Lifecycle

Classification:

| Item | Lifecycle |
|---|---|
| Feature Artifact | run-scoped / business-date scoped |
| AI Decision Artifact | run-scoped / business-date scoped |
| Model Artifact | Persistent |
| Feature Schema | Persistent |
| Canonical Data | Persistent |

Historical Feature / Decision Artifacts must not be reused as Demo or Production decision authority. They may be read as evidence for deterministic reproduction, comparison, and audit.

## Production Initialization

Production initialization must distinguish:

- new Production account with no holdings
- existing Production account with holdings
- open broker orders
- broker reconciliation difference

Production Current is confirmed by broker evidence and reconciliation. Historical or Demo Current must never be the Source of Truth for Production initial Current.

Production Broker authority requires separate Acceptance before broker writes are enabled.

## Failure Handling

| Condition | Behavior |
|---|---:|
| Backup failure | `HALT`; do not start new Environment. |
| Reset target includes reset-excluded path | `HALT`; do not modify any state. |
| Initial state validation failure | `REVIEW_REQUIRED` or `HALT`; no partial initialization. |
| `environment_id` mismatch | `HALT`; restore/transition prohibited. |
| Freeze Manifest mismatch | `HALT`; accepted artifacts are not continuous. |
| Registry checkpoint mismatch | `HALT`; artifact eligibility cannot be trusted. |
| Production reconciliation mismatch | `REVIEW_REQUIRED` or `HALT`; Production Current not accepted. |
| Previous run not closed | `REVIEW_REQUIRED`; new Environment start prohibited. |
| Pending remains | `REVIEW_REQUIRED` or `HALT`; no environment transition until resolved. |
| Execution unsettled | `REVIEW_REQUIRED` or `HALT`; no environment transition until resolved. |

Current, Ledger, and Pending must never be partially initialized. If validation fails after backup but before reset completion, restore or review must preserve all-or-nothing state consistency.

## Acceptance Criteria

This contract is accepted when:

- Persistent Operational Foundation is defined.
- Run-scoped artifacts are defined.
- Resettable Trading State is defined.
- Reset exclusion is defined.
- Historical to Demo transition is defined.
- Demo to Production transition is defined.
- Cross-environment Trading State inheritance is prohibited.
- AI / Canonical Data / Registry continuity is required.
- Feature / Decision Artifact run scope is defined.
- Environment ID and Run ID are defined.
- Backup / Restore boundaries are defined.
- Production Current is confirmed by broker reconciliation.
- Partial reset is prohibited.
- Historical / Demo / Production use the same accepted AI artifacts unless a separate acceptance changes them.
