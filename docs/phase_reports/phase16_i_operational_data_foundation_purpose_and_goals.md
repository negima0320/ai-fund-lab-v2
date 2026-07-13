# Phase16-I Operational Data Foundation Purpose and Goals

作成日: 2026-07-13

## Final Judgment

```text
PHASE16_I_OPERATIONAL_DATA_FOUNDATION_PURPOSE_AND_GOALS_ACCEPTED
```

This phase is documentation and architecture definition only.

Not executed:

- code change
- data move
- data regeneration
- feature regeneration
- AI retraining
- model change
- Runtime change
- Reset / Restore
- Historical Broker implementation
- Historical Simulation
- J-Quants API call

## Phase16 Official Name

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

The official name must not center:

- Historical
- Backtest
- Replay
- Phase16-only

## Phase16 Official Purpose

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

Historical Runtime Test is not the purpose. It is one quality verification method before Production operation.

Phase16 must not create Historical-only, Backtest-only, Replay-only, or Phase16-only Source of Truth or Runtime path.

## Top-level Project Purpose

```text
安心・安全に継続運用できる
日本株自動売買システムを作り、
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

Prohibited:

- reduce safety to improve return
- blur Runtime Authority to improve return
- break Canonical Data Contract to improve return
- overfit to backtest results

## Phase16 Goals

### 1. Canonical Data Source of Truth

Permanent Source of Truth must be accepted for:

- J-Quants Raw
- Normalized Market Data
- Trading Calendar
- Listed Issues
- Corporate Action
- Feature Source Data

Each source must define:

- formal path
- producer
- consumer
- schema
- manifest
- hash
- update method
- history retention method
- missing-data behavior
- legacy path

### 2. Feature Foundation

Required chain:

```text
Canonical Data
↓
existing Feature Producer
↓
formal Feature Artifact
```

Production, Demo, Paper, and Historical must use the same Feature Producer.

Do not change:

- feature calculation
- feature schema
- feature meaning
- feature cutoff
- future leakage guard

No mode-specific feature calculation logic is allowed.

### 3. AI Artifact Foundation

Freeze:

- Candidate AI
- Opportunity AI
- Position Management

Minimum fields:

- Runtime loaded path
- version
- hash
- training period
- feature schema
- metrics
- accepted status
- code-policy hash
- adapter hash
- retraining status

Position Management must be frozen by code-policy hash and Runtime adapter hash when no external model artifact exists.

### 4. Runtime Input Contract

Runtime v2 may use:

- Feature Artifact
- AI Decision Artifact
- Policy
- Safety
- Current
- Pending
- Broker Evidence

Runtime v2 must not directly read:

- AI Training Dataset
- Label Dataset
- Backtest Result
- Phase artifact
- Future Data

### 5. Operational State Management

Normal Runtime root:

```text
.runtime
```

Must formally manage:

- Backup
- Reset
- Restore
- Current
- Ledger
- Pending
- Runtime State
- Approval
- Execution
- Idempotency

Prohibited:

- Phase16-specific active Runtime root
- Historical-only Current
- Backtest-only Ledger
- Replay-only Pending
- Phase16-specific Mainline

### 6. Point-in-time Guarantee

Each business date may use only information available at that date.

Minimum targets:

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

Prevent future leakage and backtest result contamination.

### 7. Phase17 Start Readiness

Phase16 completion must allow Phase17 Historical Runtime Performance Test to start.

Phase16 does not perform long-term revenue evaluation.

Required state:

- Operational Data Foundation complete
- AI Freeze complete
- Runtime v2 fixed-engine readiness complete
- Historical Broker boundary complete
- Backup / Reset / Restore complete
- Point-in-time guard complete
- No real Broker Write guarantee
- No Notification Delivery guarantee
- Historical Runtime Readiness Acceptance PASS

## Phase16 Work Items

| ID | Work item | Summary |
|---|---|---|
| A | Operational Data Architecture Contract | Define Raw / Canonical / Feature / AI / Runtime responsibilities, SoT, producer, consumer, schema, manifest, hash, update policy. |
| B | Canonical Path Migration Design | Classify phase-numbered paths, operational paths, training artifacts, accepted model artifacts, legacy artifacts, and canonical candidates. |
| C | Canonical Market Data Foundation | Establish 2021+ J-Quants Raw / Normalized OHLCV as permanent canonical sources. |
| D | Calendar / Listed / Corporate Action Foundation | Establish Trading Calendar, Listed Issues, Delisting, Stock Split, Reverse Split, Adjusted OHLCV, and Corporate Action policy. |
| E | Feature Producer Connection | Use existing Feature Producer from Canonical Data to formal Feature Artifact. |
| F | AI and Policy Freeze | Freeze Candidate, Opportunity, PM, Policy, Safety, Capital Allocation, Feature Schema, metrics, code hashes, and loaded paths. |
| G | Operational Backup / Reset / Restore | Complete Backup, Clean Reset, and Restore for normal `.runtime`. |
| H | Historical Broker Boundary | Replace only the broker boundary with Historical Simulated Broker; Submit, Execution, Ledger, Current, Runtime State, and Report remain normal Runtime v2. |
| I | Point-in-time Guard | Evidence that each date's inputs, features, AI decisions, and fill prices are point-in-time consistent. |
| J | Final Readiness Acceptance | Decide whether Phase17 can start. |

## Out of Scope

Phase16 does not perform:

- Historical Runtime Performance Test
- 5BD revenue evaluation
- 20BD revenue evaluation
- 1-Year revenue evaluation
- full-period revenue evaluation from 2021 onward
- AI retraining
- AI improvement
- Feature improvement
- Policy optimization
- Safety threshold optimization
- Capital Allocation optimization
- backtest-result tuning
- Production Broker Write
- Tachibana Demo continuous operation
- Notification Delivery

Small smoke checks may be allowed only when required for connection or acceptance. They must not be treated as revenue evaluation.

## Phase Artifact Policy

Phase-numbered artifacts do not become Canonical Source of Truth merely because they exist.

Classifications:

- Training Artifact
- Accepted Model Artifact
- Historical Evidence
- Acceptance Fixture
- Legacy Artifact
- Canonical Candidate

Examples:

- `phase4be_long_history_dataset`: Training Artifact.
- `phase5p opportunity model`: Accepted Model Artifact candidate if Runtime formally uses it; not data Source of Truth.
- `.runtime/phase9/canonical_data/...`: content can be canonical, but permanent path requires migration design and acceptance.

## Completion Criteria

```text
Operational Data Architecture Contract accepted
Canonical Raw Source accepted
Canonical Normalized Source accepted
Trading Calendar Source accepted
Listed Issues Source accepted
Corporate Action policy accepted
Canonical Feature Producer connected
Feature Schema unchanged and accepted
AI / Policy Freeze Manifest accepted
Runtime input boundary accepted
Backup / Reset / Restore accepted
Historical Broker boundary accepted
Point-in-time guard accepted
Phase artifact dependency removed from Runtime inputs
No Phase16-specific active Runtime root
No Historical-specific Canonical Source
No AI retraining
No Runtime design change
Historical Runtime Readiness Acceptance PASS
Phase17 Handoff complete
```

## Design-change Stop Rule

Stop and request architecture review if implementation requires:

- Feature specification change
- AI model change
- Runtime Authority change
- State Machine change
- Current / Ledger / Pending Contract change
- normal Mainline change
- Canonical Data meaning change
- Production default change

Allowed classifications:

```text
DESIGN_CHANGE_REQUIRED
SPEC_CHANGE_REQUIRED
ARCHITECTURE_REVIEW_REQUIRED
```

## Updated Documents

- `docs/01_requirements/phase_roadmap.md`
- `docs/phase_reports/phase16_h_scope_revision_and_canonical_data_foundation.md`
- `docs/phase_reports/phase16_a_historical_runtime_v2_performance_test_design.md`
- `docs/02_architecture/historical_runtime_test_contract.md`
- `docs/02_architecture/operational_data_architecture.md`

## Next Prefix

The next prefix should be decided after reviewing this purpose and architecture definition.

Do not proceed to Canonical Path migration, data regeneration, feature connection implementation, Historical Simulation, or Runtime changes from this phase.

