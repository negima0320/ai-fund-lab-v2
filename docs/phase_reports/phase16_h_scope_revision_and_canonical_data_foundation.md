# Phase16-H Scope Revision and Canonical Data Foundation

作成日: 2026-07-13

## Phase16-I Amendment

Phase16-I updates the official Phase16 name and purpose again to avoid the impression that Phase16 builds a Historical-only or Backtest-only foundation.

Phase16-H name and purpose are retained as historical amendment evidence.

Official Phase16 name after Phase16-I:

```text
Operational Data Foundation
```

日本語:

```text
運用データ基盤整備
```

Optional subtitle:

```text
Canonical Data, Feature, AI Artifact, and Runtime Input Foundation
```

Phase16 is not a Historical Runtime Test phase and does not build a Historical-only data path. Historical Runtime Test is a Phase17 quality verification method for eventual Production operation.

Phase16 completes the common operational data foundation used by Production, Demo, Paper, and Historical modes.

## Final Judgment

```text
PHASE16_H_SCOPE_REVISION_AND_CANONICAL_DATA_FOUNDATION_ACCEPTED
```

This phase performs documentation, roadmap, and contract amendment only.

Not executed:

- Data move
- Data regeneration
- Feature regeneration
- AI retraining
- Model change
- Runtime change
- Reset / Restore
- Historical Broker implementation
- Historical Simulation
- 5BD / 20BD / 1-Year test
- J-Quants API call

## Scope Revision

Old Phase16 objective:

```text
Historical Runtime v2 Performance Test
```

Phase16-H objective before Phase16-I:

```text
Canonical Data Foundation and Historical Runtime Readiness
```

日本語:

```text
Canonicalデータ基盤再整備およびHistorical Runtime実行準備
```

Phase16 does not run the Historical Runtime Performance Test. Phase17 runs it.

Phase16-I official objective:

```text
AI Fund Lab v2のProduction、Demo、Paper、Historicalが、
同一のCanonical Data Contract
同一のFeature Producer
同一のFeature Schema
同一のAI Artifact
同一のAI Decision Contract
同一のRuntime v2 Mainline
を利用できる恒久的な運用データ基盤を完成させる
```

## Reason

Phase16-A to Phase16-G confirmed:

- 2021+ J-Quants raw response JSON exists.
- 2021+ canonical normalized OHLCV exists.
- Candidate / Opportunity / PM AI state is mostly identified.
- Runtime v2 temporal contract bug has been fixed.

Phase16-A to Phase16-G also found unresolved prerequisites:

- Permanent Canonical Data Source of Truth and path contract.
- Historical Trading Calendar.
- Historical Listed Issues.
- Corporate Action policy.
- Runtime Feature generation from Canonical Historical Data.
- Model / Config Freeze Manifest.
- Historical Broker.
- Backup / Reset / Restore.
- Point-in-time guarantee.

Starting the Historical Runtime Test now would risk depending on Phase-numbered training artifacts or recent operational data.

## Top-Level Purpose

AI Fund Lab v2 remains:

```text
安心・安全に継続運用できる日本株自動売買システムを作る
```

Return target:

```text
年率50%
```

Priority after Phase16-I:

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

Phase16 does not perform revenue improvement.

## Phase16 Formal Objective

Phase16 completes the condition where Production, Demo, Paper, and Historical can use:

- same Canonical Data Contract
- same Feature Producer
- same Feature Schema
- same AI Artifact
- same AI Decision Contract
- same Runtime v2 Mainline

Historical Runtime Test is not the objective. It is one quality verification method before Production operation.

Phase16 must not create Historical-only, Backtest-only, Replay-only, or Phase16-only Source of Truth or Runtime route.

Formal logical structure:

```text
J-Quants Raw
↓
Canonical Market Data
↓
Canonical Feature Producer
↓
Feature Artifact
↓
Candidate AI / Opportunity AI / Position Management
↓
AI Decision Artifact
↓
Policy
↓
Safety
↓
Runtime v2
↓
Broker
↓
Execution
↓
Ledger
↓
Current
↓
Report
```

Runtime v2 must not read Training Datasets directly.

AI must not directly handle Raw Data or the Runtime State Machine.

## Phase16 Current Plan After Phase16-N Amendment

Phase16-N supersedes the earlier Phase16-H/I plan labels for Phase16-K through Phase16-N. The old K/L/M/N labels in this section are historical plan evidence only and must not be read as the current execution sequence.

| Phase | Name | Purpose |
|---|---|---|
| Phase16-H | Scope Revision and Canonical Data Foundation | Preserve scope-change evidence that led to Operational Data Foundation. |
| Phase16-I | Operational Data Foundation Purpose and Goal Definition | Define Phase16 as common Production / Demo / Paper / Historical operational data foundation. |
| Phase16-J | Operational Data Architecture Contract | Define Raw / Canonical / Feature / AI / Runtime responsibilities, SoT, Producer, Consumer, Schema, Manifest, Hash, update policy. |
| Phase16-K | AI Artifact Registry and Capital Allocation Contract Design | Define Artifact Identity / Runtime Eligibility Registry and Capital Allocation policy/decision artifact contract. |
| Phase16-L | Artifact Physical Path, Registry Integration, and Migration Sequence Design | Define physical path policy, Registry integration, migration sequence, rollback, and regression gates. |
| Phase16-M | Operational Data Foundation Executive Architecture Review | Review Phase16-I through L for purpose, scope, authority, SoT, migration, failure, complexity, and implementation readiness. |
| Phase16-N | Executive Architecture Review Minor Amendment Closure | Close Phase16-M minor amendments without changing Runtime, AI, Feature, Capital Allocation, or authority semantics. |
| Post Phase16-N | To be reviewed | Remaining data foundation, feature connection, freeze, backup/reset/restore, historical broker, point-in-time guard, and readiness acceptance require a new reviewed sequence. |
| Phase16 Final | Phase16 Final Review and Phase17 Handoff | Preserve evidence and hand off to Phase17. |

Superseded historical plan labels:

| Superseded phase label | Superseded name | Status |
|---|---|---:|
| Phase16-K | Canonical Path and Data Lineage Migration Design | Superseded / historical plan |
| Phase16-L | Canonical Market Data Foundation | Superseded / historical plan |
| Phase16-M | Calendar / Listed / Corporate Action Foundation | Superseded / historical plan |
| Phase16-N | Canonical Feature Producer Connection | Superseded / historical plan |

## Phase17 Objective

```text
Historical Runtime v2 Performance Test
```

Phase17 sequence:

```text
5 Business Day Smoke
↓
20 Business Day Continuity Test
↓
1-Year Performance Test
↓
Performance Attribution
↓
AI / Policy / Safety / PM / Capital Allocation Improvement Design
↓
1-Year Revalidation
↓
2021-07 to Latest Full Historical Test
↓
Final Performance Review
```

Phase17 is the first phase that evaluates revenue.

## Future Phases

Phase18:

```text
Broker-connected Continuous Operation Test
```

Scope:

- Tachibana Demo
- daily operation
- broker-connected multi-day
- notification delivery
- recovery
- monitoring

Phase19:

```text
Production Enablement
```

Scope:

- production credentials
- production account reconciliation
- production Broker Write
- emergency operation
- production runbook
- production unlock

## Canonical Data Policy

Phase16 formalizes this logical structure. Example paths must not be implemented blindly:

```text
.runtime/data/raw/jquants/
.runtime/data/canonical/market/
.runtime/data/canonical/calendar/
.runtime/data/canonical/listed/
.runtime/data/canonical/corporate_actions/
.runtime/data/feature_store/
.runtime/models/accepted/
```

Before path decisions, Phase16-I must inspect:

- existing Producer
- existing Consumer
- configuration files
- manifests
- hashes
- migration targets
- legacy targets
- backward compatibility

`.runtime/phase9/canonical_data/normalized_daily_quotes/data.parquet` is content-confirmed canonical normalized OHLCV, but its phase-numbered path requires migration design before it becomes a permanent path.

## Phase Artifact Policy

Phase-numbered artifacts must not be used as Canonical Source of Truth without explicit migration design and acceptance:

```text
phase4*
phase5*
phase6*
phase9*
```

They must be classified as one of:

- Training Artifact
- Historical Evidence
- Accepted Model Artifact
- Legacy Artifact
- Canonical Candidate

`phase4be_long_history_dataset` is a Training Artifact, not Historical Runtime input.

## AI Freeze Policy

```text
AI_RETRAINING=PROHIBITED
```

Prohibited:

- Candidate retraining
- Opportunity retraining
- PM change
- threshold optimization
- feature change
- backtest-result tuning
- model switch

Allowed:

- Model Freeze Manifest
- Runtime loaded path freeze
- model hash recording
- feature schema hash recording
- Opportunity metrics path freeze
- PM code-policy hash freeze

## Runtime Fixed Engine Policy

```text
RUNTIME_V2=FIXED_ENGINE
```

Allowed Runtime changes are limited to evidence-backed Runtime Core bug fixes.

Bug-fix evidence must record:

```text
Contract unchanged
Authority unchanged
State transition unchanged
Normal mainline unchanged
Default behavior unchanged
Performance logic unchanged
```

If any item is `NO`, stop as design change.

## Runtime Root Policy

Phase16 implementation and final acceptance use the normal Runtime root:

```text
.runtime
```

Allowed separate paths:

- backup storage
- evidence storage
- pytest `tmp_path`
- dry-run temporary root

Prohibited:

- Phase16-specific Current
- Phase16-specific Ledger
- Phase16-specific Pending
- Phase16-specific Mainline

## Phase16-A to G Evidence

Phase16-A to Phase16-G are retained as evidence:

| Phase | Evidence role |
|---|---|
| Phase16-A | Initial Historical Runtime Test Design |
| Phase16-B | Prerequisite Audit |
| Phase16-C | Temporal Bug Audit |
| Phase16-D | Temporal Bug Fix |
| Phase16-E | Prerequisite Re-Audit |
| Phase16-F | AI State and Data Lineage Audit |
| Phase16-G | Canonical Historical Data Audit |

## Updated Files

- `docs/01_requirements/phase_roadmap.md`
- `docs/phase_reports/phase16_a_historical_runtime_v2_performance_test_design.md`
- `docs/02_architecture/historical_runtime_test_contract.md`
- `docs/phase_reports/phase16_h_scope_revision_and_canonical_data_foundation.md`
- `reports/phase_reports/phase16_h_scope_revision_and_canonical_data_foundation.json`

## Open Items

- Permanent Canonical Data paths.
- Historical Calendar source and migration policy.
- Historical Listed Issues source and migration policy.
- Corporate Action source or adjusted-OHLCV-only policy.
- Runtime Feature Producer connection to canonical historical data.
- AI Model / Policy Freeze Manifest.
- Backup / Reset / Restore.
- Historical Broker and Execution Provider boundary.
- Point-in-time guards.

## Next Prefix

```text
Phase16-I
```

Historical note: this Phase16-H next-prefix statement was superseded by Phase16-I through Phase16-N. It is retained as historical evidence only and is not the current implementation sequence.
