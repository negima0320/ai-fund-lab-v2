# Operational Data Architecture

作成日: 2026-07-13

## Purpose

This document is a permanent architecture contract for AI Fund Lab v2 operational data.

It is not Phase16-only, Historical-only, Backtest-only, or Replay-only.

The goal is to let Production, Demo, Paper, and Historical modes use the same:

- Canonical Data Contract
- Feature Producer
- Feature Schema
- AI Artifact
- AI Decision Contract
- Runtime v2 Mainline

Top-level project purpose:

```text
安心・安全に継続運用できる日本株自動売買システムを作り、
最終的にProduction運用すること
```

Return target:

```text
年率50%
```

Priority:

```text
安全性
↓
正確性
↓
継続運用性
↓
監査可能性
↓
説明可能性
↓
収益性
```

Historical Runtime Test is a quality verification method for Production readiness. It is not the purpose of this architecture.

Lifecycle, state reset boundary, and Historical / Demo / Production environment transitions are defined in:

```text
docs/02_architecture/operational_lifecycle_state_reset_and_environment_transition_contract.md
```

That contract separates Persistent Operational Foundation, Run-scoped Reproducible Artifacts, and Resettable Trading State. Trading State Reset must not delete or initialize Canonical Data, Feature Schema, accepted AI artifacts, Policy/Safety definitions, Capital Allocation Policy, Registry history, or phase evidence.

## Layer Responsibilities

```text
Raw Data
↓
Canonical Data
↓
Feature Artifact
↓
AI Artifact
↓
AI Decision Artifact
↓
Runtime v2 Input
↓
Runtime State / Ledger / Current / Report
```

Layer boundaries:

- Raw Data preserves provider-origin evidence.
- Canonical Data is the accepted point-in-time market data contract.
- Feature Artifact is the only market-derived input Runtime AI should read.
- AI Artifact is frozen model or code-policy identity.
- AI Decision Artifact is Runtime-readable AI output.
- Runtime v2 owns state transition, authority, Pending, Execution, Ledger, Current, and Report.

Runtime v2 must not directly read:

- AI training datasets
- label datasets
- backtest results
- phase-numbered training artifacts
- future data

AI must not directly own:

- Raw provider ingestion
- Runtime State Machine
- Current authority
- Ledger authority
- Pending authority

## Raw Data Contract

Scope:

- J-Quants raw daily quotes
- J-Quants raw trading calendar
- J-Quants raw listed issues
- J-Quants raw financial disclosure inputs, if used
- provider response manifests and request evidence

Required metadata:

- formal path
- producer
- consumer
- schema or raw endpoint contract
- manifest path
- hash or directory inventory hash
- update method
- retention policy
- missing-data behavior
- legacy path mapping

Raw Data is never an AI Runtime input. It is a canonical reconstruction and audit input.

## Canonical Data Contract

Canonical Data includes:

- Normalized Market Data
- Trading Calendar
- Listed Issues
- Corporate Action
- Feature Source Data

Each source must define:

```text
formal_path
producer
consumer
schema
manifest
hash
update_method
history_retention_method
missing_data_behavior
legacy_path
```

Canonical paths must be permanent operational paths. Phase-numbered paths may be Canonical Candidates, but they are not permanent Canonical paths until migration design and acceptance are complete.

Known example:

```text
.runtime/phase9/canonical_data/normalized_daily_quotes/data.parquet
```

This artifact is content-confirmed canonical normalized OHLCV, but its phase-numbered path requires migration design before permanent adoption.

## Feature Artifact Contract

Feature generation must follow:

```text
Canonical Data
↓
existing Feature Producer
↓
formal Feature Artifact
```

Required artifacts:

- Candidate Feature
- Opportunity Feature
- Position Management Feature
- Capital Policy Input

Prohibited during Operational Data Foundation:

- Feature calculation change
- Feature schema change
- Feature meaning change
- Feature cutoff change
- Future leakage guard weakening
- Production/Demo/Paper/Historical mode-specific feature logic

Feature Artifact metadata must include:

- feature date
- data cutoff
- source canonical data refs
- producer version
- schema version
- schema hash
- artifact hash
- row count
- point-in-time guard result
- missing-data decision

## AI Artifact Contract

AI Artifact identity must be frozen before Runtime execution that relies on it.

Required AI identities:

- Candidate AI
- Opportunity AI
- Position Management

Required fields:

```text
runtime_loaded_path
version
hash
training_period
feature_schema
metrics
accepted_status
code_policy_hash
adapter_hash
retraining_status
```

Position Management has no external model artifact in the current Runtime. It must be frozen by code-policy hash and Runtime adapter hash.

AI retraining is prohibited during Operational Data Foundation unless a later explicit phase authorizes it.

## AI Decision Contract

Runtime v2 consumes AI Decision Artifacts, not training datasets.

AI Decision Artifacts must record:

- business date
- feature date
- source feature artifact refs
- source model / policy refs
- model hash or code-policy hash
- decision schema version
- decision artifact hash
- row count
- generated time
- point-in-time evidence

Candidate, Opportunity, and Position Management decisions must be reproducible from accepted Feature Artifacts and frozen AI Artifacts.

## Runtime Input Boundary

Runtime v2 may use:

- Feature Artifact
- AI Decision Artifact
- Policy
- Safety
- Current
- Pending
- Broker Evidence

Runtime v2 must not use:

- AI Training Dataset
- Label Dataset
- Backtest Result
- Phase成果物 as Runtime input
- Future Data
- Historical-only Source of Truth
- Backtest-only Source of Truth

Runtime root policy:

```text
.runtime
```

Prohibited:

- Phase-specific active Runtime root
- Historical-only Current
- Backtest-only Ledger
- Replay-only Pending
- Phase-specific mainline

Allowed separate paths:

- backup storage
- evidence storage
- pytest `tmp_path`
- dry-run temporary root

## Producer / Consumer Policy

Every operational data source must have exactly documented producer and consumer boundaries.

Minimum fields:

```text
source_name
producer
producer_mode
consumer
consumer_mode
input_paths
output_paths
manifest_paths
hash_policy
failure_behavior
```

No component may silently substitute a phase artifact or fixture for a missing Canonical Source.

## Path Policy

Path classes:

- Canonical Source
- Canonical Candidate
- Accepted Runtime Input
- Accepted Model Artifact
- Training Artifact
- Historical Evidence
- Acceptance Fixture
- Legacy Artifact

Phase-numbered artifacts are not Canonical Source merely because they exist.

Examples:

- `phase4be_long_history_dataset`: Training Artifact.
- `phase5p opportunity model`: Accepted Model Artifact candidate if Runtime loads it; not a data Source of Truth.
- `.runtime/phase9/canonical_data/...`: Canonical Candidate / content-confirmed canonical; permanent path requires migration design.

## Manifest / Hash Policy

Every accepted operational source must have:

- manifest file
- source refs
- schema version
- data period
- generated time
- producer version
- file hash
- row count
- missing-data handling
- retention policy
- legacy mapping, if applicable

Directory sources must have a directory inventory hash or manifest hash that identifies all included files.

## Retention Policy

Operational data must preserve:

- provider raw evidence
- canonical reconstruction inputs
- canonical outputs
- feature artifacts used by Runtime
- AI artifacts and freeze manifests
- Runtime decision artifacts
- reports and audit evidence

Retention must support restore, audit, and deterministic rerun where required.

## Point-in-time Policy

Each business date may use only information available at that date's decision cutoff.

Minimum guard targets:

- Market Data
- Feature
- Listed Status
- Universe Membership
- Financial Disclosure
- Corporate Action
- AI Input
- Fill Price
- Current
- Safety
- Policy

Prohibited:

- future label leakage
- future listed status leakage
- future corporate action misuse
- backtest result contamination
- applying full-period knowledge to historical dates

## Historical / Paper / Demo / Production Common Use

Production, Demo, Paper, and Historical modes must use the same operational contracts.

Mode differences are allowed only at external boundary adapters, such as:

- Broker Write enabled or disabled
- Historical Simulated Broker at broker boundary
- Notification delivery enabled or disabled
- Production credential access

Mode differences must not create:

- separate Canonical Source of Truth
- separate Feature logic
- separate AI Artifact
- separate Runtime mainline
- separate Current/Ledger/Pending authority

## Design-change Stop Rule

If implementation requires any of the following, stop and request architecture review:

```text
Feature仕様変更
AIモデル変更
Runtime Authority変更
State Machine変更
Current / Ledger / Pending Contract変更
通常Mainline変更
Canonical Dataの意味変更
Production default変更
```

Allowed classifications:

```text
DESIGN_CHANGE_REQUIRED
SPEC_CHANGE_REQUIRED
ARCHITECTURE_REVIEW_REQUIRED
```
