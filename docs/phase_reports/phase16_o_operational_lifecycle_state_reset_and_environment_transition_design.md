# Phase16-O Operational Lifecycle, State Reset Boundary, and Environment Transition Design

Prefix: `Phase16-O`

Work name: `Operational Lifecycle, State Reset Boundary, and Environment Transition Contract`

Created at: 2026-07-13

## Final Judgment

`PHASE16_O_OPERATIONAL_LIFECYCLE_AND_STATE_RESET_DESIGN_ACCEPTED`

This phase creates a permanent design contract for lifecycle, reset boundary, and environment transition. No Reset, Backup, Restore, Registry, path, Runtime, AI, Feature, broker, Demo, Production, or Historical Simulation implementation was performed.

## Created / Updated Files

Created:

- `docs/02_architecture/operational_lifecycle_state_reset_and_environment_transition_contract.md`
- `docs/phase_reports/phase16_o_operational_lifecycle_state_reset_and_environment_transition_design.md`
- `reports/phase_reports/phase16_o_operational_lifecycle_state_reset_and_environment_transition_design.json`

Updated:

- `docs/02_architecture/operational_data_architecture.md`
- `docs/02_architecture/historical_runtime_test_contract.md`
- `docs/01_requirements/phase_roadmap.md`

## Purpose

Phase16-O defines what persists, what is run-scoped evidence, and what can be clean reset when moving through:

```text
Historical Runtime Test
↓
Tachibana Demo Operation
↓
Production Operation
```

The design preserves the top-level project purpose: safe and continuous Japanese equity auto-trading leading to Production operation.

## Persistent Operational Foundation

Persistent Operational Foundation is retained across Historical, Demo, and Production and is excluded from Trading State Reset.

Minimum retained foundation:

- J-Quants Raw
- Canonical Market Data
- Trading Calendar
- Listed Issues
- Corporate Action
- Feature Schema
- Accepted Candidate Artifact Set
- Accepted Opportunity Model / Metrics Artifact Set
- PM Code Policy / Runtime Adapter Artifact Set
- Policy Artifact
- Safety Artifact
- Capital Allocation Policy Artifact
- Artifact Registry event history
- Materialized Registry index
- Model / Policy Freeze Manifest
- Training / Validation Evidence
- Migration / Legacy history

The contract defines retention, immutability, backup, versioning, replacement/revoke procedure, and reset exclusion for each item.

## Run-scoped Artifacts

Run-scoped artifacts are generated per `run_id` / `environment_id` and preserved as evidence, but are not inherited as next-run authority.

Defined run-scoped artifacts:

- Feature Artifact
- Candidate Decision Artifact
- Opportunity Decision Artifact
- Position Management Decision Artifact
- Capital Allocation Signal / Decision Evidence
- Safety Decision
- Policy Decision
- Planning Artifact
- Runtime Report
- Audit Report
- Run Manifest
- Point-in-time Manifest
- Performance Report

Historical Feature / Decision Artifacts may be read for reproducibility comparison and audit, but must not become Demo or Production trading authority.

## Resettable Trading State

Resettable Trading and Runtime State includes:

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

Initial cash and buying power are environment configuration values. The contract gives a clean verification example of 1,000,000 JPY but does not hard-code Production initialization.

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

If reset targets include excluded items, the required behavior is `HALT`.

## Historical To Demo Transition

Required:

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

## Demo To Production Transition

Required:

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

## Environment / Run Identity

Required identity fields:

- `environment_id`
- `run_id`
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

Mode differences are represented by metadata, not separate Registries or Runtime mainlines.

## Backup / Restore Boundary

Trading State Backup:

- Current
- Ledger
- Pending
- Runtime State
- Approval
- Execution
- Idempotency
- Broker state

Operational Foundation Backup:

- Canonical Data manifests
- Accepted Artifact Sets
- Registry
- Freeze Manifests
- Schemas
- Policies

Trading State Backup is mandatory before reset. Operational Foundation is reset-excluded but independently backed up for Production and disaster recovery.

Restore is forbidden across environment boundaries, such as Historical to Demo or Demo to Production Trading State restore. Except for explicit disaster recovery acceptance, restore is limited to the same Environment / Run lineage.

## AI Continuity

Historical, Demo, and Production preserve:

- same accepted logical artifact identity
- same model hash
- same metrics hash
- same PM code-policy hash
- same feature schema hash
- same policy hash

Environment transition must not implicitly change models, retrain, overwrite Production-start artifacts, or mutate same-version artifacts based on backtest results.

## Feature / Decision Lifecycle

| Item | Lifecycle |
|---|---|
| Feature Artifact | run-scoped / business-date scoped |
| AI Decision Artifact | run-scoped / business-date scoped |
| Model Artifact | Persistent |
| Feature Schema | Persistent |
| Canonical Data | Persistent |

Historical run Feature / Decision Artifacts are evidence, not Demo or Production authority.

## Production Initialization

Production initialization distinguishes:

- new Production account with no holdings
- existing Production account with holdings
- open broker orders
- broker reconciliation difference

Production Current is confirmed by broker evidence and reconciliation. Historical or Demo Current is not a Production Source of Truth.

## Failure Handling

| Condition | Behavior |
|---|---:|
| Backup failure | `HALT` |
| Reset target includes reset-excluded path | `HALT` |
| Initial state validation failure | `REVIEW_REQUIRED` or `HALT` |
| `environment_id` mismatch | `HALT` |
| Freeze Manifest mismatch | `HALT` |
| Registry checkpoint mismatch | `HALT` |
| Production reconciliation mismatch | `REVIEW_REQUIRED` or `HALT` |
| Previous run not closed | `REVIEW_REQUIRED`; new Environment start prohibited |
| Pending remains | `REVIEW_REQUIRED` or `HALT` |
| Execution unsettled | `REVIEW_REQUIRED` or `HALT` |

Partial reset or partial initialization of Current / Ledger / Pending is prohibited.

## Current Document Gaps Closed

Phase16-O closes the lifecycle gap between existing Operational Data Foundation contracts and later Backup / Reset / Restore implementation:

- Persistent Foundation vs resettable Trading State is now explicit.
- Run-scoped evidence vs next-run authority is now explicit.
- Historical to Demo and Demo to Production state inheritance is prohibited.
- Production Current source is broker reconciliation, not Historical/Demo state.

## Remaining Design Work

- Concrete Backup / Reset / Restore CLI or accepted operational procedure.
- Registry inventory implementation after separate review.
- Model / Policy Freeze Manifest acceptance.
- Historical Broker boundary.
- Point-in-time Guard.
- Operational Data Foundation readiness acceptance.
- Production Broker authority acceptance.

## Implementation Readiness

Design readiness:

`ACCEPTED`

Implementation readiness:

`DESIGN_ACCEPTED_IMPLEMENTATION_REQUIRED`

Only later reviewed prefixes may implement Backup, Reset, Restore, Registry, path operations, broker transition, or simulation.

## Next Prefix

`REVIEW_REQUIRED_BEFORE_NEXT_PREFIX`
