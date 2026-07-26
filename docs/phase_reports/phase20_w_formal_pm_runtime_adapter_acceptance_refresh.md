# Phase20-W Formal PM Runtime Adapter Acceptance Refresh

## Status

```text
PHASE20_W_FORMAL_PM_RUNTIME_ADAPTER_ACCEPTANCE_REFRESH_COMPLETE
```

Acceptance results:

```text
PM_RUNTIME_ADAPTER_ACCEPTANCE_REFRESH_COMPLETE
PM_AUTHORITY_PASS
CURRENT_HASH_EQUALS_ACCEPTED_HASH
REGISTRY_UPDATED
MANIFEST_UPDATED
HUMAN_REVIEW_COMPLETED
FALSE_PASS_FIX_PRESERVED
LONG_RUNNING_HISTORICAL_TEST_NOT_EXECUTED
USER_REVALIDATION_COMMANDS_READY
```

## Scope

Phase20-W performed the formal Acceptance Refresh for the Position Management Runtime Adapter after Phase20-V proved behavioral equivalence.

No PM threshold, score formula, decision order, REDUCE quantity rule, Sell Planning quantity authority, BUY logic, Risk logic, Broker logic, Runtime logic, Training, Calibration, Validation run, Accepted Generation model pointer, or long Historical run was changed or executed.

## Required Materials Reviewed

- `docs/phase_reports/phase20_v_pm_runtime_adapter_behavioral_equivalence_review.md`
- `docs/phase_reports/phase20_v_pm_runtime_adapter_acceptance_refresh_checklist.md`
- `docs/phase_reports/phase20_u_pm_authority_mismatch_and_runtime_test_false_pass_closure.md`
- `docs/02_architecture/autonomous_ai_operations_architecture.md`
- `docs/02_architecture/artifact_acceptance_contract.md`
- `docs/02_architecture/ai_artifact_registry_and_capital_allocation_contract.md`
- existing formal PM adapter acceptance writer implementation

The requested files `docs/02_architecture/accepted_generation_contract.md` and `docs/02_architecture/artifact_registry_contract.md` were not present under those exact names. The applicable local Source of Truth files are `artifact_acceptance_contract.md` and `ai_artifact_registry_and_capital_allocation_contract.md`.

## Candidate Identity

| Item | Value |
|---|---|
| Artifact set type | `POSITION_MANAGEMENT_POLICY_SET` |
| Artifact set id | `control.position_management.accepted_set` |
| Member | `RUNTIME_ADAPTER` |
| Member path | `src/ai_fund_lab_v2/runtime_v2/position_management/producer.py` |
| Authority mode | `ACCEPTED_CURRENT_PATH` |
| Old accepted hash | `93581111ae9b61facf669f8033d87e927f103d05483b4f212da4a592dbb15185` |
| Current / candidate hash | `ac2e7f6a3e9e184889551a8884a0e779ffb37292e8b26daf1e25e1610bba739c` |
| Accepted PM set before | `control.position_management.accepted_set@sha256-22f697341275a709` |
| Accepted PM set after | `control.position_management.accepted_set@sha256-cec533ce8c03de7f` |
| Accepted event after | `event-1c801648-a4ba-49a8-bc7f-9694d9ce9f60-47609547f5d5838c` |
| Accepted Generation ID retained | `phase19_aq_accepted_generation_641e6e313543f013` |
| Git commit | `f4f8dbf03355106f201174f6f68b86aac707b6ed` |

The current source was a working-tree source state; the accepted content hash is the SHA-256 of the runtime adapter source bytes.

## Human Review

Phase20-V checklist result used for formal review:

| Check | Result |
|---|---|
| Behavioral Equivalence | `PASS` |
| HOLD | `PASS` |
| REDUCE | `PASS` |
| EXIT | `PASS` |
| ADD | `PASS` |
| READY_EMPTY | `PASS` |
| Fail Closed | `PASS` |
| Decision Order | `PASS` |
| Score | `PASS` |
| Quantity Authority | `PASS` |
| Trace Only Difference | `PASS` |
| Phase20-U false-PASS regression | `PASS` |

## Formal Acceptance Procedure

Executed:

```bash
PYTHONPATH=src python3 scripts/phase20_w_pm_runtime_adapter_acceptance_refresh.py
```

This wrapper uses the existing formal append-only PM adapter acceptance writer. It produced DRAFT, VALIDATED, LEGACY, and ACCEPTED Registry events, regenerated the materialized Registry index, wrote a checkpoint, and ran authority validation. No manifest, pointer, Registry index, or hash was directly hand-edited.

Writer result:

```text
new_pm_set = control.position_management.accepted_set@sha256-cec533ce8c03de7f
source_hash = ac2e7f6a3e9e184889551a8884a0e779ffb37292e8b26daf1e25e1610bba739c
```

## Registry / Manifest Update

Evidence:

```text
.runtime/artifact_registry/evidence/manifests/control_position_management_accepted_current_path_v10/artifact_set_manifest.json
.runtime/artifact_registry/evidence/acceptance/control_position_management_accepted_current_path_v10/acceptance_report.json
.runtime/artifact_registry/evidence/bundles/control_position_management_accepted_current_path_v10/evidence_bundle.json
reports/phase20_w_formal_pm_runtime_adapter_acceptance_refresh/formal_writer_summary.json
```

Registry event result:

```text
DRAFT appended: PASS
VALIDATED appended: PASS
OLD ACCEPTED -> LEGACY: PASS
NEW VALIDATED -> ACCEPTED: PASS
atomic multi-event append: PASS
```

Validation:

```text
Registry event log: PASS
Registry index: PASS
Registry checkpoint: PASS
Exactly one active eligible PM set: PASS
```

## Authority Confirmation

Post-acceptance authority validation:

```text
accepted_path = src/ai_fund_lab_v2/runtime_v2/position_management/producer.py
accepted_hash = ac2e7f6a3e9e184889551a8884a0e779ffb37292e8b26daf1e25e1610bba739c
executing_source_hash = ac2e7f6a3e9e184889551a8884a0e779ffb37292e8b26daf1e25e1610bba739c
authority_mode = ACCEPTED_CURRENT_PATH
Authority PASS
```

The accepted member hash now equals the current `producer.py` hash.

## Short Validation

Executed by the formal writer:

```text
tests/runtime_v2/test_phase20_v_pm_runtime_adapter_equivalence.py: PASS
Phase20-U PM false-PASS regression tests: PASS
PM adapter Registry identity/input/consumer targeted tests: PASS
```

Additional validation:

```text
formal writer summary JSON validation: PASS
Registry index JSON validation: PASS
Authority validation: PASS
```

## Prohibited Operations Confirmation

Not executed:

```text
long Historical Smoke
fresh-run
run
resume
Broker connection
Training
Calibration
Validation run
Accepted Generation model pointer update
producer.py edit
PM threshold edit
score formula edit
decision order edit
Runtime logic edit
```

## User Revalidation Commands

Codex did not execute these commands.

### 5BD Fresh Run

```bash
cd /Users/negishi/work/ai-fund-lab-v2

PYTHONPATH=src python3 scripts/runtime_test.py fresh-run \
  --profile historical-extended-smoke \
  --business-days 5 \
  --start-date 2026-06-16 \
  --confirm \
  --yes-i-understand-this-mutates-trading-state \
  --json
```

### Phase20-T Analysis

```bash
PYTHONPATH=src python3 scripts/analyze_pm_cross_regime.py analyze-runs \
  --run-id <NEW_RUN_ID> \
  --output-json reports/phase_reports/phase20_t_post_w_validation.json \
  --print-json
```

Expected results:

```text
Authority PASS
PM HALTなし
decision_count > 0
decision_trace生成
dominant_cause生成
reason_codes生成
symbol_volatility取得
analysis decision_count > 0
```

## Final Judgment

```text
PHASE20_W_FORMAL_PM_RUNTIME_ADAPTER_ACCEPTANCE_REFRESH_COMPLETE
```
