# Phase17-B1 Historical Runtime Test Support Integration and 5BD Smoke Test Start

## Final Judgment

Final judgment: `PHASE17_B1_DESIGN_CHANGE_REQUIRED`

Recommended next prefix: `Phase17-B1R`

Recommended next work:

```text
Historical Mainline Exposure Architecture Review
```

Phase17-B1 added read-only / non-mutating Historical Runtime test support modules and re-evaluated the 5BD entry gates. The 5BD Smoke Test was not started because the required Entry Gates did not all pass.

No Runtime v2 Core, State Machine, Current, Ledger, Pending, Submit Guard, Execution Processor, Safety, Registry, accepted artifacts, canonical data, feature artifacts, or Trading State files were changed.

## Materials Reviewed

Required materials reviewed:

- `docs/phase_reports/phase17_a_integrated_system_test_and_production_readiness_strategy.md`
- `reports/phase_reports/phase17_a_integrated_system_test_and_production_readiness_strategy.json`
- `docs/phase_reports/phase17_b_historical_runtime_readiness_revalidation_and_5bd_preparation.md`
- `reports/phase_reports/phase17_b_historical_runtime_readiness_revalidation_and_5bd_preparation.json`
- `docs/phase_reports/phase16_final_summary_and_phase17_handoff.md`
- `reports/phase_reports/phase16_final_summary_and_phase17_handoff.json`
- `docs/phase_reports/phase16_ax_operational_data_foundation_final_conformance_and_ai_integrity_audit.md`
- `reports/phase_reports/phase16_ax_operational_data_foundation_final_conformance_and_ai_integrity_audit.json`
- `docs/02_architecture/historical_runtime_test_contract.md`
- `docs/02_architecture/runtime_temporal_freshness_contract.md`
- `docs/02_architecture/operational_data_architecture.md`
- `docs/02_architecture/operational_lifecycle_state_reset_and_environment_transition_contract.md`
- `docs/02_architecture/runtime_architecture_v2.md`

## Implemented Support Modules

Added a Core-external support package:

- `src/ai_fund_lab_v2/runtime_v2/historical_support/common.py`
- `src/ai_fund_lab_v2/runtime_v2/historical_support/reset_plan.py`
- `src/ai_fund_lab_v2/runtime_v2/historical_support/baseline.py`
- `src/ai_fund_lab_v2/runtime_v2/historical_support/gates.py`
- `src/ai_fund_lab_v2/runtime_v2/historical_support/__init__.py`

Added focused tests:

- `tests/runtime_v2/test_phase17_b1_historical_support.py`

The support package can:

- build a non-mutating Trading State reset plan;
- validate reset scope and reset-excluded scope;
- collect a read-only regression baseline and Registry / artifact hashes;
- detect PM Runtime Adapter authority drift;
- evaluate Phase17-B1 Entry Gates before any 5BD execution.

It does not execute reset, restore, submit, execution, feature generation, broker simulation, or external API access.

## Runtime Core Change Evidence

Protected-area diff was checked for:

```text
src/ai_fund_lab_v2/runtime_v2/core
src/ai_fund_lab_v2/runtime_v2/state_machine
src/ai_fund_lab_v2/runtime_v2/current_state
src/ai_fund_lab_v2/runtime_v2/ledger
src/ai_fund_lab_v2/runtime_v2/pending
src/ai_fund_lab_v2/runtime_v2/submit
src/ai_fund_lab_v2/runtime_v2/execution
src/ai_fund_lab_v2/runtime_v2/safety
```

Result: no diff.

No new test-only Runtime root was created. Normal Runtime root remains:

```text
.runtime
```

## Reset Scope

Reset plan support status: `PASS`

Reset execution status: `NOT_EXECUTED`

Reset execution was not run because Entry Gates did not all pass.

Resettable scope in the generated plan includes:

- `persistent_ledger/state.json`
- `persistent_ledger/orders.jsonl`
- `persistent_ledger/executions.jsonl`
- `persistent_ledger/positions.jsonl`
- `persistent_ledger/cash.jsonl`
- `persistent_ledger/events.jsonl`
- `pending_order_plan/pending_order_plan.json`
- `pending_order_plan/history`
- `runtime_state/current_state.json`
- Runtime approval / review / broker evidence / data readiness / run manifest / logs state
- `broker/sync_results`

Reset-excluded prefixes:

- `artifact_registry`
- `artifacts`
- `operations/jquants`
- `phase9/canonical_data`
- `data/raw`
- `candidate_ai`
- `opportunity_ai`
- `configs`

The validator returns `HALT` if a reset plan includes reset-excluded targets.

## Historical Clock

Status: `REVIEW_REQUIRED`

Classification: `CLOCK_CONFIGURATION_GAP`

Result:

- normal CLI has `--business-date` and `--evaluation-time`;
- B1 did not relax omitted-date fallback behavior;
- the exact 5BD job-sequence clock audit remains unaccepted;
- no historical execution was started.

## Historical Broker

Status: `DESIGN_CHANGE_REQUIRED`

Classification: `BROKER_ADAPTER_DEFECT`

Evidence:

- `SimulationBroker` exists and is broker-boundary-only in isolation.
- `run_submit_pipeline()` has an adapter seam, but blocks `mode != "demo"`.
- `run_execution_readonly_pipeline()` has a `snapshot_provider` seam, but blocks modes outside `demo` / `production`.
- CLI simulation validation remains not exposable for official 5BD submit/execution.

B1 did not relax Submit validation or add a test-only mainline. The correct classification is:

```text
NORMAL_MAINLINE_NOT_EXPOSABLE
DESIGN_CHANGE_REQUIRED
```

## Canonical Data / Point-in-Time / Feature Generation

Canonical data input status: `IMPLEMENTATION_REQUIRED`

Point-in-time status: `IMPLEMENTATION_REQUIRED`

Feature generation status: `IMPLEMENTATION_REQUIRED`

The candidate 5BD window remains:

```text
2026-07-06
2026-07-07
2026-07-08
2026-07-09
2026-07-10
```

It was not selected for execution because feature artifacts are incomplete for:

```text
2026-07-09
```

B1 did not hand-create missing feature files and did not run feature regeneration.

## PM Adapter Authority

Status: `ARCHITECTURE_REVIEW_REQUIRED`

Classification: `ARTIFACT_AUTHORITY_GAP`

Evidence:

| Item | SHA-256 |
|---|---|
| Current executed PM source | `0e238f497dbc4b558cf4e955450ac0d63feb71d3f656f958b92d222f9086b8e5` |
| Accepted PM Runtime Adapter snapshot | `6ffa7da2b91f5fd5cfa76aa4c487e6e6cf5e1293ba929fe374abd61aaadb7d1b` |

The files are not byte-identical. B1 did not monkey patch, rewrite imports, copy over source, or mutate acceptance records.

Allowed resolution still requires one of:

- accept current source through the formal Artifact Acceptance workflow;
- use an existing approved method for Runtime to execute the frozen accepted adapter;
- formally approve semantic equality / gate-only behavior as an architecture and acceptance decision.

## External Effects

Status: `REVIEW_REQUIRED`

Classification: `OPTIONAL_COMPONENT_CONFIGURATION_GAP`

B1 performed no Tachibana API ReadOnly, Tachibana Demo Write, Tachibana Production Write, Production API access, Discord send, LINE send, Blog publish, or notification delivery.

Historical command-level network and delivery guard remains unaccepted, so this Gate cannot be marked PASS.

## Regression Baseline

Status: `PASS`

A formal read-only baseline manifest was generated in:

```text
reports/phase_reports/phase17_b1_historical_runtime_test_support_and_5bd_smoke.json
```

It includes Git commit, Registry hashes, accepted set summaries, Current/Ledger/Pending/Runtime State hashes, market state, canonical/operational data refs, and PM adapter authority status.

## Entry Gates

| Gate | Status | Classification | Blocking |
|---|---|---|---:|
| `NORMAL_MAINLINE_READY` | `DESIGN_CHANGE_REQUIRED` | `NORMAL_MAINLINE_NOT_EXPOSABLE` | true |
| `RESET_READY` | `PASS` | `PASS` | false |
| `HISTORICAL_CLOCK_READY` | `REVIEW_REQUIRED` | `CLOCK_CONFIGURATION_GAP` | true |
| `HISTORICAL_BROKER_READY` | `DESIGN_CHANGE_REQUIRED` | `BROKER_ADAPTER_DEFECT` | true |
| `CANONICAL_DATA_INPUT_READY` | `IMPLEMENTATION_REQUIRED` | `CANONICAL_DATA_GAP` | true |
| `POINT_IN_TIME_READY` | `IMPLEMENTATION_REQUIRED` | `CANONICAL_DATA_GAP` | true |
| `FEATURE_GENERATION_READY` | `IMPLEMENTATION_REQUIRED` | `FEATURE_DEFECT` | true |
| `REGISTRY_FREEZE_READY` | `PASS` | `PASS` | false |
| `PM_ADAPTER_AUTHORITY_READY` | `ARCHITECTURE_REVIEW_REQUIRED` | `ARTIFACT_AUTHORITY_GAP` | true |
| `EXTERNAL_EFFECTS_DISABLED` | `REVIEW_REQUIRED` | `OPTIONAL_COMPONENT_CONFIGURATION_GAP` | true |
| `REGRESSION_BASELINE_READY` | `PASS` | `PASS` | false |
| `TEST_WINDOW_READY` | `NOT_READY` | `FEATURE_DEFECT` | true |

Because at least one Entry Gate is not PASS, 5BD Smoke Test was not started.

## 5BD Execution

Status: `NOT_RUN`

Daily results: none

Runtime Integrity result: `NOT_RUN`

Reason:

```text
ENTRY_GATE_NOT_ALL_PASS
```

## Tests

Executed:

```text
PYTHONPATH=src python3 -m pytest -q tests/runtime_v2/test_phase17_b1_historical_support.py
```

Result:

```text
4 passed
```

## Blocking Findings

1. `NORMAL_MAINLINE_NOT_EXPOSABLE`
   - Classification: `DESIGN_CHANGE_REQUIRED`
   - Normal CLI / submit / execution paths do not expose a simulation historical path without changing currently blocked behavior.

2. `BROKER_ADAPTER_DEFECT`
   - Classification: `DESIGN_CHANGE_REQUIRED`
   - Historical broker and execution snapshot provider cannot be selected by official normal CLI for 5BD.

3. `ARTIFACT_AUTHORITY_GAP`
   - Classification: `ARCHITECTURE_REVIEW_REQUIRED`
   - PM current executed source and accepted adapter snapshot are not byte-identical.

4. `CANONICAL_DATA_GAP`
   - Classification: `IMPLEMENTATION_REQUIRED`
   - Accepted canonical historical input and point-in-time chain are not connected for official historical Runtime execution.

5. `FEATURE_DEFECT`
   - Classification: `IMPLEMENTATION_REQUIRED`
   - `2026-07-09` feature artifacts remain missing.

6. `OPTIONAL_COMPONENT_CONFIGURATION_GAP`
   - Classification: `REVIEW_REQUIRED`
   - External effect disabling is not proven at command level for historical mode.

## Non-Blocking Findings

1. Reset plan support and scope validator are implemented and pass.
2. Regression baseline collection is implemented and pass.
3. Registry freeze evidence collection is pass.
4. No protected Runtime v2 Core diff was detected.

## Commands Executed

- Required document reads with `cat` / `sed`.
- Runtime and test inventory with `rg`.
- Targeted code inspection with `sed` / `rg`.
- `PYTHONPATH=src python3 -m pytest -q tests/runtime_v2/test_phase17_b1_historical_support.py`
- Protected path diff check with `git diff -- ...`
- Phase17-B1 Entry Gate evaluation via `historical_support`.
- JSON syntax validation with `jq empty`.

## Operations Not Executed

- 5BD Historical Runtime execution.
- Trading State reset.
- Trading State restore.
- Current / Ledger / Pending / Runtime State mutation.
- Historical broker order simulation execution.
- Tachibana API ReadOnly.
- Tachibana Demo Write.
- Tachibana Production Write.
- Production API access.
- Discord / LINE / Blog external delivery.
- AI retraining.
- Feature regeneration.
- Canonical data regeneration.
- Registry mutation.
- Artifact acceptance mutation.
