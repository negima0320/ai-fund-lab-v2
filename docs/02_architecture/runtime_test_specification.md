# Runtime Test Specification

Version: 1.0

Status: `ACCEPTED`

Authority:

- Project-wide Runtime Test Standard
- Test Scope Authority
- Test Validity Authority
- Test Acceptance Authority
- Environment Difference Authority

Final judgment: `RUNTIME_TEST_SPECIFICATION_ACCEPTED`

## 1. Document Purpose

This specification defines the project-wide Runtime Test Standard for AI Fund Lab v2. It is not a Phase Report and is not limited to Phase17. It is the Single Source of Truth for test scope, validity, acceptance, and environment differences across Historical, Backtest, Tachibana Demo, Production Readiness, and Production Acceptance tests.

Target readers are Runtime implementers, test operators, reviewers, and production acceptance authorities.

This specification does not replace the existing architecture and lifecycle contracts. The authority chain is:

```text
Runtime Architecture / Data / Lifecycle / Registry Contracts
                    ↓
        Runtime Test Specification
                    ↓
5BD / 20BD / 1-Year / Full / Demo / Production Test Plans
                    ↓
            Test Reports / Evidence
```

If this specification conflicts with an upstream contract, the upstream contract remains authoritative and the issue must be recorded as `CONTRACT_ALIGNMENT_REQUIRED`. This version records no known contract contradiction.

Primary contract references:

- [Runtime Architecture v2](runtime_architecture_v2.md)
- [Historical Runtime Test Contract](historical_runtime_test_contract.md)
- [Runtime Temporal Freshness Contract](runtime_temporal_freshness_contract.md)
- [Operational Data Architecture](operational_data_architecture.md)
- [Operational Lifecycle State Reset and Environment Transition Contract](operational_lifecycle_state_reset_and_environment_transition_contract.md)
- [AI Input / Output and Artifact Contract](ai_input_output_and_artifact_contract.md)
- [AI Artifact Registry and Capital Allocation Contract](ai_artifact_registry_and_capital_allocation_contract.md)
- [Artifact Registry Event and Acceptance Evidence Contract](artifact_registry_event_and_acceptance_evidence_contract.md)
- [Materialized Registry Index and Event Replay Contract](materialized_registry_index_and_event_replay_contract.md)
- [Artifact Acceptance Contract](artifact_acceptance_contract.md)
- [Artifact Acceptance Authority and Promotion Workflow Contract](artifact_acceptance_authority_and_promotion_workflow_contract.md)

Phase17 design evidence is referenced as supporting rationale, not as the permanent authority itself.

## 2. Test Philosophy

Normative requirements:

- The system under test is the production Runtime v2 that will be used for live operation.
- Tests must fail closed when authority, temporal, state, data, or environment evidence is incomplete.
- Evidence is mandatory. A passing outcome without evidence is not accepted.
- Silent fallback is prohibited.
- Future data is prohibited.
- Manual state repair is prohibited.
- Result-driven implementation is prohibited. Runtime behavior must not be changed merely to make a test pass.
- Test validity has priority over test PASS.

Profit does not validate a test. If a run bypasses Runtime v2, Submit Guard, Execution Processor, Registry authority, temporal constraints, or state lifecycle, the test is `INVALID` regardless of PnL.

## 3. System Under Test

The system under test is the normal Runtime v2 mainline, including:

- Market / Data Readiness
- Feature Date Contract
- Feature Producer
- Candidate AI
- Opportunity AI
- Position Management
- Safety
- Policy
- Capital Allocation
- Planning
- Pending
- Approval
- Submit Guard
- Submit Pipeline
- Broker Boundary
- Execution Processor
- Ledger
- Current
- Runtime State
- Report / Audit
- Registry / Acceptance / Artifact Resolver

All Runtime tests must use the same logical Runtime components as Production unless an approved environment difference in this specification explicitly permits substitution at the broker boundary, clock, external effect boundary, or test evidence boundary.

Forbidden:

- Historical-only Runtime
- Test-only mainline
- Test-only Current / Ledger / Pending
- Test-only State Machine
- Test-only Feature Producer
- Submit Guard bypass
- Execution Processor bypass
- Direct Ledger or Current mutation
- Profit-only backtest as a substitute for Runtime Test
- Runtime behavior changes made only to satisfy a test

## 4. Environment Model

| Environment | Runtime Mainline | Runtime Root | Clock | Market Data | Broker Adapter | Execution Source | External Delivery | Broker Write | Trading State | Registry / Accepted Artifact | Production Equivalent Scope |
|---|---|---|---|---|---|---|---|---|---|---|---|
| Historical | Normal Runtime v2 CLI / mainline | `.runtime` | Explicit historical `business_date` and `evaluation_time` | Canonical / PIT data as-of manifest | `HistoricalSubmitAdapter` only | `HistoricalExecutionSnapshotProvider` / accepted historical fill evidence | Disabled | Disabled | Resettable Runtime trading state | Same accepted Registry / artifacts | Mainline, state transitions, authority, temporal and evidence validity |
| Tachibana Demo | Normal Runtime v2 CLI / mainline | `.runtime` | Real operation time | Operational market data | Tachibana Demo API boundary | Demo broker snapshots, order status, execution evidence | Allowed only by configured demo delivery policy | Demo boundary only | Runtime-owned demo trading state plus demo broker evidence | Same accepted Registry / artifacts | Broker boundary, session, submit, recovery, operational behavior |
| Production | Normal Runtime v2 CLI / mainline | `.runtime` | Real production time | Production operational data | Tachibana Production API boundary | Production broker evidence | Controlled production delivery | Explicit Production acceptance only | Production Current initialized from broker evidence | Same accepted Registry / artifacts with release freeze | Full production authority after acceptance |
| Paper | Normal Runtime v2 CLI / mainline when used | `.runtime` | Explicit or operational test time | Accepted data source for the paper test profile | Paper adapter if formally accepted | Paper execution evidence | Disabled unless accepted | Disabled | Resettable test trading state | Same accepted Registry / artifacts | Planning and state transition rehearsal only |
| Backtest | Not a Runtime Test unless it enters normal Runtime v2 | `.runtime` when promoted to Runtime Test | Historical or scenario clock | Canonical / PIT data | Simulation boundary only if accepted as broker boundary | Simulation evidence only | Disabled | Disabled | Resettable test trading state | Same accepted Registry / artifacts | Research evidence; does not replace Runtime Test |

Paper and Backtest outputs may be evidence, but they are not Production acceptance authority unless the run uses the normal Runtime v2 mainline and satisfies this specification.

## 5. Approved Environment Differences

Historical may replace or fix only:

- Historical Clock
- Canonical Data as-of
- PIT Manifest
- `HistoricalSubmitAdapter`
- `HistoricalExecutionSnapshotProvider`
- External effect blocking
- Smoke-limited execution assumption
- Initial Trading State Reset

Demo may replace only:

- Tachibana Demo API boundary
- Real-time Demo broker snapshot
- Demo credentials and capability
- Demo-specific broker exceptions defined in section 21

Production may replace only:

- Tachibana Production API boundary
- Production broker reconciliation
- Production credentials / capability / approval
- Production release and rollback authority

Everything else remains normal Runtime v2.

## 6. Test Levels

| Level | Name | Entry Gate | Purpose | Guarantee Scope | Non-goals | Next Level Condition |
|---|---|---|---|---|---|---|
| 1 | 5BD Historical Runtime Smoke Test | 5BD window PIT, accepted Historical environment, reset ready, no external effect, path guards, baseline ready | Runtime mainline connection, state transition, authority, temporal, submit/execution, Current/Ledger/Pending consistency | Smoke validity of Runtime v2 through Historical broker boundary | Investment performance, fees/tax/slippage realism, partial fill realism, full Corporate Action | No invalidity, no unclassified HALT, evidence complete |
| 2 | 20BD Historical Runtime Continuity Test | Level 1 accepted plus continuity data and execution model extensions | Continuity state, unfilled orders, Partial Fill, fees, slippage, Corporate Action coverage, performance attribution | Multi-week lifecycle continuity | Annual robustness, full PIT coverage | Continuity evidence accepted and failure classes stable |
| 3 | 1-Year Historical Runtime Test | Level 2 accepted plus 1-year PIT and tax/execution policy | Annual continuity, tax, PIT coverage, strategy performance, drawdown, Safety effectiveness | One-year operational and performance validity | Full-period coverage and all delisting/suspension cases | Year-level evidence and attribution accepted |
| 4 | Full Historical Runtime Test | Level 3 accepted plus full-period data coverage | Full period, reproducibility, long-term performance, Corporate Action, delisting, suspension, missing data | Full historical readiness evidence | Live broker behavior | Full historical evidence accepted |
| 5 | Tachibana Demo Operational Test | Historical levels sufficient for Runtime confidence plus Demo credentials / capability / safe approval | API auth, session, real broker boundary, submit, order status, execution, timeout, recovery, scheduler, human review | Demo operational readiness | Production broker authority | Demo evidence accepted and production delta documented |
| 6 | Production Readiness Test | Demo accepted plus production reconciliation plan, freeze, rollback, human approval | Environment transition, broker reconciliation, production capability, release freeze, rollback, operational readiness | Production readiness, not final enablement | Uncontrolled production trading | Readiness approval and release checkpoint freeze |
| 7 | Production Acceptance | Production readiness accepted plus final human release approval | Final production enablement, initial Current generation, broker SoT, controlled operation | Production authority | Future performance guarantee | Controlled production operation begins |

## 7. Runtime Mainline Contract

The formal Runtime test call graph is:

```text
Normal CLI
→ Market Refresh
→ Data Readiness
→ Feature Date Contract
→ Candidate / Opportunity
→ PM / Sell Planning
→ Safety / Policy / Capital
→ Pending
→ Approval
→ Submit Guard
→ Submit Pipeline
→ Environment-specific Broker Boundary
→ Execution Processor
→ Ledger
→ Current
→ Runtime State
→ Report / Audit
```

Only the broker boundary and explicitly approved environment composition points may differ by environment. Broker Boundary differences must still produce Runtime-compatible evidence for the normal Submit Pipeline and Execution Processor.

## 8. Runtime Root and State Authority

The formal Runtime root is:

```text
.runtime
```

Forbidden Runtime roots:

```text
.runtime/demo
.runtime/production
.runtime/historical
.runtime/simulation
.runtime/backtest
```

Current, Ledger, Pending, and Runtime State are normal Runtime authority. They must be read and written only by normal Runtime components. Tests must not create mode-rooted Current, mode-rooted Ledger, mode-rooted Pending, or mode-rooted Runtime State.

Mode-rooted path attempts must fail closed with a path-guard reason such as `MODE_ROOTED_RUNTIME_ROOT_FORBIDDEN`.

## 9. Trading State Lifecycle

Runtime tests that mutate trading state must follow this lifecycle:

```text
Backup
Freeze
Reset
Initialize
Validate
Run
Close
Evidence Freeze
Reset / Transition
Rollback
```

Reset targets:

- Current
- Ledger
- Pending
- Runtime State
- Approval state
- Execution state
- Idempotency state
- Open orders
- Environment-specific transient broker state
- Cash / Position / PnL

Reset-excluded targets:

- Registry Event Store
- Registry Index
- Registry Checkpoint
- Accepted Artifact records
- Canonical Data
- Raw Data
- Feature Schema
- AI Artifact
- Policy / Safety definitions
- Configs
- Evidence

Partial reset and partial restore are prohibited. A rollback must restore the complete resettable Trading State bundle to a verified backup point. Registry recovery is governed by Registry recovery contracts and must not be treated as ordinary state reset.

## 10. Initial State Contract

The accepted Level 1 Historical Smoke initial state is:

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

Initial state authority is the reset manifest plus validation manifest produced immediately before the test run. The initial state is valid only if every reset target is initialized consistently and every reset-excluded target remains untouched.

Demo and Production initial states are not inherited from Historical. Production Current must be initialized from Production broker evidence and reconciliation.

## 11. Data Authority and Point-in-time

Minimum data authority dimensions:

- OHLCV
- Trading Calendar
- Listed Issues
- PIT Universe
- Corporate Action
- Valuation Price
- Fill Price
- Feature Date

Every test plan must identify:

- logical identity
- physical path
- manifest
- hash
- as-of
- cutoff
- missing-data policy
- future-data prohibition

Level 1 may use a window-level PIT authority limited to the accepted 5BD window. Level 2 and later must increase PIT coverage according to the test horizon. Full Historical Runtime requires full-period PIT completeness, including listed status, universe, corporate action, delisting, suspension, missing data, and fill/valuation cutoffs.

Missing authority must not be silently filled from current data or future data.

## 12. Carryover Contract

Carryover must use the normal Feature Date Contract. Historical-only Carryover logic is prohibited.

Accepted Phase17 5BD profile examples:

```text
2026-07-08 → feature_date 2026-07-07
2026-07-09 → feature_date 2026-07-08
```

Feature hole filling, manual copying, and future-data fallback are prohibited. Carryover is valid only when the Runtime feature date marker and PIT evidence support it.

## 13. Historical Fill and Execution Model

Level 1 5BD Smoke uses a smoke-limited execution model:

```text
Market order only
target session Open
all-or-none
fees=0
tax=0
slippage=0
partial fill disabled
no fallback
smoke_limited_execution_model=true
official_long_term_performance_model=false
```

Required failure handling:

| Condition | Level 1 Behavior |
|---|---|
| Missing Open | `NO_FILL` / `HALT` according to runbook severity |
| Missing OHLCV | `NO_FILL` / `HALT` |
| PIT Universe外 | `HALT` |
| Source hash mismatch | `HALT` |
| Wrong session | `HALT` |
| Corporate Action impact | `HALT` |
| Duplicate | Block by normal duplicate / idempotency guards |
| LIMIT order | `HALT` / `REVIEW_REQUIRED` until accepted |
| Insufficient cash | Block by normal Submit Guard |
| Insufficient quantity | Block by normal Submit Guard |

Execution realism progression:

- Level 1: all-or-none market-open smoke model.
- Level 2: fees, slippage, Partial Fill, and Corporate Action coverage are required before continuity acceptance.
- Level 3: tax and annual execution assumptions are required before performance acceptance.
- Level 4: long-period realism must cover delisting, suspension, missing data, and Corporate Action impacts.
- Demo / Production: real broker evidence supersedes simulated fill assumptions.

## 14. External Effect Policy

Historical Runtime tests prohibit:

- Tachibana API access
- Broker external write
- LINE send
- Discord send
- Blog publish
- Notification delivery
- J-Quants fetch
- Production or Demo credentials

Historical output is payload / evidence generation only.

Demo may access Tachibana Demo APIs and configured demo delivery only when the Demo test plan explicitly permits it. Production may access Tachibana Production APIs only after Production readiness, capability, approval, and release gates pass.

## 15. Entry Gates

Common gates:

- Normal Runtime Mainline
- Normal Runtime Root
- Registry Integrity
- Accepted Artifact Authority
- Temporal Integrity
- Data Authority
- State Lifecycle
- External Effect Policy
- Regression Baseline
- Rollback
- No Alternate Runtime

Level 1 5BD gates:

- Historical Environment
- Registry
- PM Authority
- Runtime Mainline
- Submit Guard
- Execution Processor
- Historical Fill Model
- Canonical OHLCV
- Trading Calendar
- Listed Issues
- Window PIT
- Corporate Action Guard
- Historical Clock
- Reset ready
- Regression Baseline
- External Effect Blocking
- Path Guard closure

Any gate failure stops the test before runtime execution.

## 16. Test Validity Contract

A test is valid only if all conditions hold:

- Normal Runtime v2 Mainline used.
- No alternate path.
- No external effect violation.
- No future data.
- No manual state repair.
- No duplicate submit / execution / ledger.
- Authority matches accepted artifacts and manifests.
- Temporal identity matches business date, evaluation time, feature date, fill date, and cutoffs.
- State remains internally consistent.
- Evidence is complete.

Invalid conditions:

- Runtime bypass
- Guard bypass
- Execution bypass
- Feature manual patch
- Data fallback
- Training artifact fallback
- State manual repair
- Partial reset
- Unexpected API access
- Authority mismatch
- Temporal violation
- Test-only Runtime / State Authority

Invalidity overrides PnL and all other success indicators.

## 17. Acceptance Criteria

Common acceptance criteria:

- No crash
- No unclassified HALT
- No double submit
- No double execution
- No double ledger
- No double PnL
- Current consistency
- Ledger consistency
- Pending consistency
- Runtime State consistency
- Cash consistency
- Quantity consistency
- Idempotency
- Temporal consistency
- Authority consistency
- External effect compliance
- Evidence completeness

Additional criteria by level:

- Level 1: mainline continuity and state consistency for 5BD.
- Level 2: continuity handling, unfilled orders, partial fills, fees, slippage, and attribution.
- Level 3: annual continuity, tax, PIT coverage, drawdown, and Safety effectiveness.
- Level 4: full-period reproducibility, long-term performance, missing data and corporate event handling.
- Level 5: Tachibana Demo session, order, execution, timeout, recovery, scheduler, and human review behavior.
- Level 6: production reconciliation, release freeze, rollback, and operational readiness.
- Level 7: final production enablement, broker SoT, and controlled production operation.

## 18. Regression and Degradation Prevention

Regression coverage must include:

- Runtime Core
- Submit Guard
- Execution Processor
- Ledger
- Current
- Pending
- Safety
- Policy
- Capital Allocation
- Registry Resolver
- PM Authority
- Feature Schema
- Environment Composition
- Path Guards

Required baselines:

- pre-reset source baseline
- post-reset initial state baseline
- daily state baseline
- final state
- post-close / post-reset baseline

Baseline refresh must not hide unexpected diffs. Any baseline update requires a reason, hash, authority, and reviewer-visible evidence.

## 19. Evidence Requirements

Minimum evidence:

- Environment Manifest
- Runtime Manifest
- Data / PIT Manifest
- Registry Freeze
- Accepted Artifact Set IDs / Hashes
- Backup Manifest
- Reset Manifest
- Initial State Manifest
- Daily Run Manifest
- Submit Evidence
- Execution Evidence
- Ledger / Current Evidence
- State Consistency Report
- Regression Baseline
- Final Test Summary
- Rollback Evidence

Logs, evidence, and operational data are distinct. Registry Event Store, Registry Index, Checkpoints, Accepted Artifact records, Canonical Data, and Raw Data are operational data, not disposable logs.

## 20. Failure Classification

| Classification | Stop Policy | Fix Policy | Retest Policy |
|---|---|---|---|
| `TEST_ENVIRONMENT_FAILURE` | Stop affected test | Fix environment setup | Re-run from clean baseline |
| `TEST_SUPPORT_IMPLEMENTATION_GAP` | Stop if evidence validity is affected | Implement support outside Runtime Core unless approved | Re-run failed gates |
| `DATA_DEFECT` | Stop affected dates | Repair data through data authority process | Revalidate manifests / hashes |
| `CANONICAL_DATA_GAP` | Stop level requiring that data | Complete canonical authority | Re-run data gates |
| `FEATURE_DEFECT` | Stop dependent jobs | Fix producer/schema under acceptance | Re-run feature and downstream jobs |
| `BROKER_ADAPTER_DEFECT` | Stop submit/execution | Fix adapter boundary | Re-run broker-boundary tests |
| `ARTIFACT_AUTHORITY_GAP` | Stop consumers | Registry / acceptance correction | Re-run authority gates |
| `RUNTIME_CORE_DEFECT` | Stop | Runtime fix with regression evidence | Re-run full impacted sequence |
| `TEMPORAL_CONTRACT_VIOLATION` | Stop | Fix date/cutoff authority | Re-run from valid state |
| `AUTHORITY_CONTRACT_VIOLATION` | Stop | Align contract / implementation | Re-run authority and runtime tests |
| `STATE_CONSISTENCY_FAILURE` | Stop | Diagnose Current/Ledger/Pending/Runtime State | Restore and re-run |
| `REGRESSION` | Stop release progression | Fix or explicitly accept with authority | Re-run regression baseline |
| `ARCHITECTURE_REVIEW_REQUIRED` | Stop progression | Architecture review | Resume only after accepted decision |
| `DESIGN_CHANGE_REQUIRED` | Stop progression | Contract/design amendment | Re-run from amended gates |
| `UNKNOWN` | Stop | Classify before fix | No acceptance until classified |

## 21. Demo-specific Rules

Tachibana Demo may contain pre-existing holdings. Runtime-owned positions and the entire Demo broker snapshot are not required to match globally.

Demo exception boundaries:

- The exception applies only to Tachibana Demo.
- It must not be carried into Production.
- Runtime-owned orders, executions, and positions must still be tracked strictly.
- Broker evidence for Runtime-owned activity remains required.

Production must not ignore broker snapshot and Runtime-owned state mismatches without explicit reconciliation and acceptance.

## 22. Production-specific Rules

Production requirements:

- Production Current is initialized from broker evidence.
- Historical / Demo Trading State must not be inherited.
- Production reconciliation is mandatory.
- Production credentials / capabilities / approval are mandatory.
- Release checkpoint freeze is mandatory.
- Rollback plan is mandatory.
- Human approval is mandatory.
- Production broker writes require explicit Production Acceptance.

## 23. Non-goals

Level 1 5BD does not guarantee:

- annualized return
- profit performance
- fees realism
- tax realism
- slippage realism
- Partial Fill realism
- full Corporate Action handling
- long-term strategy robustness
- Tachibana API behavior
- Production readiness

Each later level must declare its own non-goals in its test plan. No level may claim guarantees outside its accepted evidence.

## 24. Phase17 5BD Concrete Profile

This profile is an accepted concrete test profile under this specification. It is not the whole standard.

```text
Window:
2026-07-06 ～ 2026-07-10

Runtime root:
.runtime

Mode:
historical

Broker:
historical_simulated

Feature carryover:
2026-07-08 → 2026-07-07
2026-07-09 → 2026-07-08

External delivery:
false

J-Quants fetch:
false

Initial capital:
1,000,000 JPY
```

The profile must use the normal Runtime v2 CLI and mainline, with explicit `business_date`, explicit `evaluation_time`, `--mode historical`, `--broker-environment historical_simulated`, `--runtime-root .runtime`, and payload-only external delivery.

## 25. Change Management

This specification must be updated when:

- an upstream contract changes;
- a Test Level is added or removed;
- an execution model changes;
- an environment is added;
- Production operation changes;
- a major postmortem identifies a test validity, evidence, or acceptance gap.

Change records must include:

- version
- date
- change summary
- related phase / report
- contract impact
- approval status

## 26. Standard Runtime Test Procedure

This section is normative. The Runtime Test Specification is the formal authority for Runtime Test execution order. Operation guides and phase runbooks may provide examples, but they must not contradict this procedure.

### 26.1 Basic Execution Flow

Standard flow:

```text
Status
  │
  ▼
Plan
  │
  ▼
Backup
  │
  ▼
Reset
  │
  ▼
Run
  │
  ▼
Validate
  │
  ▼
Close
```

Failure flow:

```text
HALT / REVIEW_REQUIRED / BLOCKED / VALIDATION_FAILURE
  │
  ▼
Classify Failure
  │
  ├── Resume allowed only if baselines and checkpoints match
  │
  └── Rollback required if state validity or lifecycle safety is uncertain
          │
          ▼
        Rollback
          │
          ▼
        Validate
          │
          ▼
        Evidence Freeze
```

The standard flow must not be reordered. A test run that skips Backup, skips Reset where a reset is required, bypasses Validate, or closes without evidence is invalid.

### 26.2 Runtime Test Command

The formal user-facing command entrypoint is:

```bash
PYTHONPATH=src python3 scripts/runtime_test.py <subcommand> [options]
```

Standard 5BD command sequence:

```bash
PYTHONPATH=src python3 scripts/runtime_test.py status

PYTHONPATH=src python3 scripts/runtime_test.py plan \
  --profile historical-smoke \
  --business-days 5 \
  --start-date 2026-07-06

PYTHONPATH=src python3 scripts/runtime_test.py backup \
  --profile historical-smoke \
  --confirm \
  --yes-i-understand-this-mutates-trading-state

PYTHONPATH=src python3 scripts/runtime_test.py reset \
  --profile historical-smoke \
  --backup-id <BACKUP_ID> \
  --initial-cash 1000000 \
  --confirm \
  --yes-i-understand-this-mutates-trading-state

PYTHONPATH=src python3 scripts/runtime_test.py run \
  --profile historical-smoke \
  --business-days 5 \
  --start-date 2026-07-06 \
  --confirm \
  --yes-i-understand-this-mutates-trading-state

PYTHONPATH=src python3 scripts/runtime_test.py validate \
  --run-id <RUN_ID>

PYTHONPATH=src python3 scripts/runtime_test.py close \
  --run-id <RUN_ID>
```

Rollback command:

```bash
PYTHONPATH=src python3 scripts/runtime_test.py rollback \
  --backup-id <BACKUP_ID> \
  --confirm \
  --yes-i-understand-this-mutates-trading-state
```

All mutating commands must require explicit mutation confirmation. Ambiguous `--force`-style flags are prohibited.

### 26.3 Historical 5BD

The formal Historical 5BD Runtime Smoke Test procedure is:

```text
status
↓
plan
↓
backup
↓
reset
↓
run
↓
validate
↓
close
```

Required profile:

```text
historical-smoke
```

Required window:

```text
2026-07-06 through 2026-07-10
```

Historical 5BD must use the normal Runtime v2 CLI, `.runtime`, `mode=historical`, `broker_environment=historical_simulated`, payload-only external delivery, and J-Quants fetch disabled.

Carryover must be resolved by the normal Feature Date Contract. Profile-level expected values may be used only as acceptance checks, not as an alternate feature-date resolver.

### 26.4 Historical Extended Smoke

Historical 10BD is classified as:

```text
Extended Smoke
Pre-Continuity Test
Not the formal 20BD Continuity Test
```

It uses the same command order as 5BD:

```text
status → plan → backup → reset → run → validate → close
```

If it uses the Level 1 smoke execution model, the run must declare:

```text
official_continuity_test=false
official_performance_test=false
fees=0
tax=0
slippage=0
partial_fill=false
```

The 10BD window must be selected from Calendar / PIT / Listed Issues / OHLCV / Feature Date Contract readiness. Manual data补完 is prohibited.

### 26.5 Historical 20BD

Historical 20BD is the formal Continuity Test. It uses the same basic command sequence, with additional entry conditions:

- continuity-ready Trading Calendar / PIT / Listed Issues / OHLCV coverage;
- unfilled order and pending lifecycle evidence;
- Partial Fill policy accepted or explicitly blocked;
- fees, slippage, and Corporate Action coverage accepted for the 20BD scope;
- performance attribution evidence enabled;
- daily state baseline and final continuity summary required.

20BD acceptance must not reuse Level 1 smoke assumptions as if they were continuity assumptions.

### 26.6 Historical 1-Year

Historical 1-Year uses the same basic command sequence, with additional entry conditions:

- 1-year PIT coverage;
- tax model or tax exclusion policy accepted;
- annual drawdown and Safety effectiveness evidence;
- long-horizon Runtime State, Current, Ledger, Pending, and Registry baseline continuity;
- annual performance attribution.

The 1-Year test may evaluate strategy performance, but invalid Runtime execution still invalidates the test regardless of performance.

### 26.7 Full Historical

Full Historical Runtime Test uses the same basic command sequence, with additional entry conditions:

- full target-period Calendar / PIT / Listed Issues / OHLCV readiness;
- Corporate Action, delisting, suspension, missing data, and no-fill policies accepted;
- reproducibility evidence for the full period;
- long-term performance and failure classification evidence;
- final full-period acceptance review.

Full Historical must not silently skip unavailable periods or repair data manually.

### 26.8 Tachibana Demo

Tachibana Demo Runtime Test uses the normal Runtime v2 CLI and mainline. The approved environment difference is the broker boundary:

```text
broker_environment=tachibana_demo
```

Demo tests must still use normal Current, Ledger, Pending, Runtime State, Feature Producer, AI, PM, Safety, Policy, Capital Allocation, Approval, Submit Guard, Submit Pipeline, Execution Processor, and Registry authority.

Demo-specific broker snapshot exceptions are limited to Demo and must not be promoted into Production rules.

### 26.9 Production Readiness

Production Readiness Test uses the same test philosophy and evidence requirements, but Production broker write is not enabled by this procedure alone.

Additional requirements:

- Production Current initialized from broker evidence;
- Production reconciliation complete;
- Production credentials and capability checked;
- release checkpoint frozen;
- rollback plan accepted;
- human approval recorded;
- Production Acceptance gate remains separate.

Historical or Demo Trading State must not be inherited into Production.

### 26.10 Rollback

Standard rollback procedure:

```text
Rollback Target Selection
  ↓
Backup Manifest Validation
  ↓
Current State Freeze
  ↓
Restore Scope Validation
  ↓
All-or-nothing Restore
  ↓
Post-restore Validation
  ↓
Rollback Evidence Freeze
```

Rollback target is the full resettable Trading State bundle:

- Current
- Ledger
- Pending
- Runtime State
- Approval state
- Execution state
- Idempotency state
- Open orders
- environment-specific transient broker state

Partial restore is prohibited. Current-only restore, Ledger-only restore, Pending-only restore, and manual state edits are test-invalidating actions. Operational Foundation, Registry, Accepted Artifacts, Canonical Data, Raw Data, Feature Schema, Policy, Safety definitions, Configs, and Evidence must not be restored by Runtime Test rollback.

### 26.11 Command Execution Order

| Command | State Change | Responsibility |
|---|---:|---|
| `status` | No | Read-only Runtime Test state summary. |
| `plan` | No | Build execution plan, job sequence, dates, evidence paths, and expected commands. |
| `backup` | Yes | Backup resettable Trading State before reset/run. |
| `reset` | Yes | Initialize the test Trading State all-or-nothing from an accepted backup. |
| `run` | Yes | Invoke the normal Runtime v2 CLI by business date and job. |
| `validate` | No | Validate run, state, temporal, authority, and evidence consistency; never repair. |
| `resume` | Yes | Continue from the last valid checkpoint if baselines match; never skip failed jobs. |
| `rollback` | Yes | Restore the full resettable Trading State bundle from backup. |
| `close` | No | Freeze final evidence, validity judgment, acceptance gate judgment, and lifecycle recommendation. |

### 26.12 Dry Run

Dry Run is a mandatory safety mechanism for mutating commands. Dry Run means:

- no state mutation;
- no Runtime execution;
- no Submit or Execution;
- no Backup/Reset/Restore applied to `.runtime`;
- execution plan, target files, excluded files, commands, evidence paths, and failure policy are displayed and may be saved as evidence.

Dry Run does not replace actual Backup, Reset, Run, Validate, or Close.

### 26.13 Prohibited Procedure Deviations

The following are prohibited:

- Run before Backup when the test requires resettable Trading State protection;
- Run before Reset when the test profile requires an initialized state;
- manual Feature generation during a run;
- manual Feature copy or data補完;
- Ledger repair after a run;
- Current-only restore;
- Ledger-only restore;
- Pending-only restore;
- Runtime State manual修正;
- Runtime bypass;
- Submit Guard bypass;
- Execution Processor bypass;
- alternate Runtime;
- mode-rooted Runtime root;
- automatic approval of `REVIEW_REQUIRED`.

Any prohibited deviation makes the test invalid unless a formal upstream contract amendment explicitly reclassifies the action before the run.

### 26.14 Test Invalid Runbook

The following conditions are test-invalidating:

- Future Data;
- Manual Repair;
- State Repair;
- Authority mismatch;
- Runtime bypass;
- Guard bypass;
- Execution bypass;
- Unexpected API access;
- Feature patch;
- data fallback;
- training artifact fallback;
- partial reset or partial restore;
- missing evidence for a required acceptance gate.

Invalidity overrides PnL, completion status, and apparent operational success.

### 26.15 Exit Codes

| Code | Meaning | Procedure |
|---:|---|---|
| 0 | `PASS` | Continue to the next standard step. |
| 10 | `REVIEW_REQUIRED` | Stop; classify and obtain review before resume or rollback. |
| 20 | `BLOCKED` | Stop; resolve blocker or rollback according to lifecycle policy. |
| 30 | `HALT` | Stop immediately; classify failure and protect state. |
| 40 | `VALIDATION_FAILURE` | Stop; do not repair state manually; classify and rollback if needed. |
| 50 | `ROLLBACK_FAILURE` | Stop; do not perform additional changes without recovery review. |
| 60 | `INVALID_ARGUMENT` | Stop; correct command/profile arguments; no state action accepted. |
| 70 | `PRECONDITION_FAILURE` | Stop; satisfy missing Backup/Reset/Baseline/Gate precondition. |
| 80 | `TEST_INVALID` | Stop; test cannot be accepted from this run. |
| 90 | `INTERNAL_ERROR` | Stop; classify before retry. |

### 26.16 Common Execution Examples

Status only:

```bash
PYTHONPATH=src python3 scripts/runtime_test.py status
```

Validate only:

```bash
PYTHONPATH=src python3 scripts/runtime_test.py validate --run-id <RUN_ID>
```

5BD dry run:

```bash
PYTHONPATH=src python3 scripts/runtime_test.py run \
  --profile historical-smoke \
  --business-days 5 \
  --start-date 2026-07-06 \
  --dry-run
```

10BD dry run:

```bash
PYTHONPATH=src python3 scripts/runtime_test.py run \
  --profile historical-extended-smoke \
  --business-days 10 \
  --start-date 2026-07-06 \
  --dry-run
```

Resume dry run:

```bash
PYTHONPATH=src python3 scripts/runtime_test.py resume \
  --run-id <RUN_ID> \
  --dry-run
```

Rollback:

```bash
PYTHONPATH=src python3 scripts/runtime_test.py rollback \
  --backup-id <BACKUP_ID> \
  --confirm \
  --yes-i-understand-this-mutates-trading-state
```

### 26.17 FAQ

Q: What happens if the run stops midway?

A: Stop the sequence. Classify the failure. Use `validate` and `resume --dry-run` to determine whether the run can continue. If source, Registry, artifact, PIT, or state baselines changed, resume is prohibited and rollback/re-plan is required.

Q: When is Rollback required?

A: Rollback is required when state validity, lifecycle safety, or evidence integrity is uncertain, or when a failure policy/runbook requires restoring the pre-test Trading State bundle.

Q: What if Close is forgotten?

A: The run remains unclosed and must not be accepted. Run `validate --run-id <RUN_ID>` and then `close --run-id <RUN_ID>` before using the run as evidence.

Q: Can Resume skip the failed job?

A: No. Resume may continue only from the last valid checkpoint and must not skip failed jobs.

Q: What is Dry Run?

A: Dry Run displays the plan, target files, excluded files, commands, evidence paths, and failure policy without mutating state or executing Runtime jobs.

Q: Can this be used in Production?

A: Not by itself. Production use requires Production Readiness and Production Acceptance, including broker reconciliation, credentials/capability, release freeze, rollback plan, and human approval.

## Supporting Phase17 Evidence

This specification consolidates accepted outcomes from:

- [Phase17-A Integrated System Test and Production Readiness Strategy](../phase_reports/phase17_a_integrated_system_test_and_production_readiness_strategy.md)
- [Phase17-B Historical Runtime Readiness Revalidation and 5BD Preparation](../phase_reports/phase17_b_historical_runtime_readiness_revalidation_and_5bd_preparation.md)
- [Phase17-B1 Historical Runtime Test Support and 5BD Smoke](../phase_reports/phase17_b1_historical_runtime_test_support_and_5bd_smoke.md)
- [Phase17-B1R Historical Mainline and PM Adapter Authority Architecture Review](../phase_reports/phase17_b1r_historical_mainline_and_pm_adapter_authority_architecture_review.md)
- [Phase17-B1I-A Historical Environment Composition](../phase_reports/phase17_b1i_a_historical_environment_composition.md)
- [Phase17-B1I-B PM Adapter Authority Resolution](../phase_reports/phase17_b1i_b_pm_adapter_authority_resolution.md)
- [Phase17-B1I-BR Registry Recovery Architecture Review](../phase_reports/phase17_b1i_br_registry_recovery_architecture_review.md)
- [Phase17-B1I-C Canonical Point-in-time Feature Readiness](../phase_reports/phase17_b1i_c_canonical_point_in_time_feature_readiness.md)
- [Phase17 Test Scope and Readiness Review](../phase_reports/phase17_test_scope_and_readiness_review.md)
- [Phase17-D 5BD Smoke Minimum Readiness](../phase_reports/phase17_d_5bd_smoke_minimum_readiness.md)
- [Phase17-E Historical Fill Price and Execution Model Acceptance](../phase_reports/phase17_e_historical_fill_price_and_execution_model_acceptance.md)
- [Phase17-F Historical Submit Guard Runtime Core Review](../phase_reports/phase17_f_historical_submit_guard_runtime_core_review.md)
- [Phase17-G Historical Submit Guard and Fill Model Implementation](../phase_reports/phase17_g_historical_submit_guard_and_fill_model_implementation.md)
- [Phase17-H 5BD Final Entry Gate](../phase_reports/phase17_h_5bd_final_entry_gate.md)
- [Phase17-I Historical Test Logic and Initial State Final Review](../phase_reports/phase17_i_historical_test_logic_and_initial_state_final_review.md)
- [Phase17-J Mode-Rooted Runtime Path Guard Closure](../phase_reports/phase17_j_mode_rooted_runtime_path_guard_closure.md)

## Acceptance Gates

| Gate | Status |
|---|---:|
| `PROJECT_WIDE_SCOPE` | PASS |
| `PHASE_INDEPENDENT` | PASS |
| `RUNTIME_V2_IS_SYSTEM_UNDER_TEST` | PASS |
| `ENVIRONMENT_DIFFERENCES_EXPLICIT` | PASS |
| `TEST_LEVELS_DEFINED` | PASS |
| `STATE_LIFECYCLE_DEFINED` | PASS |
| `DATA_PIT_CONTRACT_DEFINED` | PASS |
| `EXECUTION_MODELS_DEFINED` | PASS |
| `ENTRY_GATES_DEFINED` | PASS |
| `TEST_VALIDITY_DEFINED` | PASS |
| `ACCEPTANCE_CRITERIA_DEFINED` | PASS |
| `REGRESSION_POLICY_DEFINED` | PASS |
| `EVIDENCE_REQUIREMENTS_DEFINED` | PASS |
| `DEMO_EXCEPTION_DEFINED` | PASS |
| `PRODUCTION_RULES_DEFINED` | PASS |
| `NON_GOALS_DEFINED` | PASS |
| `PHASE17_5BD_PROFILE_INCLUDED` | PASS |
| `CONTRACT_REFERENCES_COMPLETE` | PASS |
| `NO_CONTRACT_CONTRADICTION` | PASS |
| `NO_RUNTIME_CHANGE` | PASS |
| `STANDARD_PROCEDURE_DEFINED` | PASS |
| `COMMAND_SEQUENCE_DEFINED` | PASS |
| `ALL_TEST_LEVELS_DEFINED` | PASS |
| `ROLLBACK_DEFINED` | PASS |
| `COMMAND_REFERENCE_COMPLETE` | PASS |
| `NO_SPEC_CONTRADICTION` | PASS |

## Change History

| Version | Date | Change Summary | Related Phase / Report | Contract Impact | Approval Status |
|---|---|---|---|---|---|
| 1.2 | 2026-07-14 | Added Historical logical as-of consumer-input and Feature Date Contract PASS entry-gate requirements. | Phase17-M | Clarifies Runtime Test entry validity and Historical consumer wiring; Runtime Core semantics unchanged. | REVIEWED |
| 1.1 | 2026-07-14 | Added Standard Runtime Test Procedure as normative execution authority. | Documentation-02 | No upstream contract meaning changed. | ACCEPTED |
| 1.0 | 2026-07-14 | Initial project-wide Runtime Test Specification consolidating Phase17-A through Phase17-J and architecture contracts. | Documentation-01 | No upstream contract meaning changed. | ACCEPTED |

## Phase17-M Amendment: Historical Consumer Input Gate

Historical Runtime Test may use physical canonical market data that contains rows after the replay business date, but the Runtime consumer input must be an accepted logical as-of view. The logical input must carry the physical source path/hash, cutoff, logical max date, future rows excluded count, run identity, and manifest hash. A Historical run is invalid if Market Refresh, Data Readiness, Feature Refresh, or feature artifact resolution consumes the unbounded physical dataset for a replay business date.

Feature artifacts must not be selected from a date after the selected Feature Date or after the consumer business date. Future Feature Artifact use is a temporal contract violation and must halt or block the test.

Runtime Test `plan` and `run` must fail closed before Runtime job invocation when any business date has a Feature Date Contract that is not `PASS`, is missing, lacks a hash/path, uses profile values as authority, or has a selected date that differs from the profile expected value. The Runner remains a thin orchestrator: it may validate accepted plan evidence and pass identity/path arguments, but it must not filter data, generate features, decide feature dates, or override Runtime results.
