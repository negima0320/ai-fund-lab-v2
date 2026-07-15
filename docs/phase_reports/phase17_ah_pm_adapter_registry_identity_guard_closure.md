# Phase17-AH PM Adapter Registry Identity Guard Closure

## Status

`PHASE17_AH_PM_ADAPTER_REGISTRY_IDENTITY_GUARD_ACCEPTED`

## Scope

This phase investigated and closed the remaining direct Position Management producer regression:

```text
POSITION_MANAGEMENT_POLICY_SET:RUNTIME_ADAPTER accepted-current-path hash mismatch
```

Frozen runtime runs, real `.runtime` operational state, pending state, ledger state, broker/external integrations, and runtime test runner state were not mutated. The real Artifact Registry was also not re-accepted in this phase.

## Root Cause

Classification:

- A. Legitimate Runtime Code Change
- D. Stale Test Fixture

The accepted Registry member and the runtime execution target use the same formal adapter path:

```text
src/ai_fund_lab_v2/runtime_v2/position_management/producer.py
```

This is not a wrong-path issue. It is a content identity mismatch.

- Accepted hash: `2924fa7e132e9602653cd1033a9b6b6925f8ef419accfafd673b05bdba4e71df`
- Current runtime hash: `2e6790f07cb3981fe0dbc575b059bbbc1abd6fb27f6c74b989b8bb8285951535`
- Paths match: `true`
- Content matches: `false`

The hash material is SHA256 over the runtime adapter source file bytes. Absolute paths, cwd, checkout location, timestamps, cache files, pyc files, generated artifacts, runtime test identity, and environment/mode are not hash material.

## Runtime Contract Closed

Position Management Runtime Adapter authority remains a single Registry authority:

```json
{
  "registry_key": "POSITION_MANAGEMENT_POLICY_SET:RUNTIME_ADAPTER",
  "authority_type": "ARTIFACT_REGISTRY",
  "hash_algorithm": "sha256"
}
```

The canonical identity is now:

```text
repo_relative_posix_path + sha256(source_file_bytes)
```

This makes the identity independent of cwd and repository checkout location while still changing whenever the executing runtime adapter source changes. Comments are included because the contract hashes source file bytes.

Fail-closed conditions preserved or added:

- missing Registry member
- duplicate `RUNTIME_ADAPTER` authority
- unknown resolver schema version
- missing executing adapter source
- repo-external executing path
- empty or `.` artifact source
- wrong repo-relative path
- hash mismatch

## Production Impact

Production, Demo, and Historical now use the same PM adapter identity contract. No Historical-specific, Runtime-Test-specific, phase-number-specific, or profile-specific bypass was added.

The real `.runtime` Registry still contains the old accepted hash. Therefore, default production PM adapter resolution correctly remains fail-closed until a formal Registry acceptance is performed. This is intentional and prevents an unreviewed source change from being used for real trading.

Before Production PM runtime execution, the formal registry acceptance procedure must generate a new accepted artifact set through registry tooling, including old/new hashes, reviewer-facing diff evidence, regression evidence, acceptance reason, event append, index rebuild, checkpoint rebuild, and rollback path. Manual JSON hash editing remains rejected.

## Implementation Summary

- `src/ai_fund_lab_v2/runtime_v2/artifact_lookup.py`
  - Runtime artifact lookup now derives repo root from source location instead of cwd when no explicit root is provided.

- `src/ai_fund_lab_v2/runtime_v2/position_management/producer.py`
  - PM adapter guard now compares canonical repo-relative path identity.
  - PM adapter guard validates SHA256 source bytes.
  - PM adapter guard rejects unknown resolver schema, duplicate adapter authority, missing files, repo-external paths, and `.` sources.

- `tests/runtime_v2/test_phase15ap_position_management_input_contract.py`
  - Direct PM producer regression uses an isolated accepted-current adapter fixture that still exercises the real strict guard.

- `tests/runtime_v2/test_phase17_ah_pm_adapter_registry_identity_guard.py`
  - Added focused identity guard tests for pass/fail, wrong path, missing key, missing artifact, unknown schema, checkout independence, timestamp independence, shared mode identity, `.` rejection, and duplicate authority.

- Registry consumer tests now expect the stale real PM adapter Registry entry to halt until formal acceptance is performed.

## Evidence

Evidence directory:

```text
reports/phase17_ah_pm_adapter_registry_identity_guard_closure/
```

Key files:

- `root_cause.json`
- `registry_identity_before.json`
- `registry_identity_after.json`
- `hash_materials.json`
- `runtime_adapter_resolution.json`
- `registry_acceptance_procedure.json`
- `regression_results.json`

JSON summary:

```text
reports/phase_reports/phase17_ah_pm_adapter_registry_identity_guard_closure.json
```

## Verification

Passed:

```bash
PYTHONPATH=src python3 -m pytest -q tests/runtime_v2/test_phase17_ah_pm_adapter_registry_identity_guard.py tests/runtime_v2/test_phase17_b1i_b_pm_adapter_authority.py
```

Result: `15 passed`

Passed:

```bash
PYTHONPATH=src python3 -m pytest -q tests/runtime_v2/test_phase15ap_position_management_input_contract.py tests/runtime_v2/test_phase17_ag_day2_sell_planning_integration.py tests/runtime_v2/test_phase17_af_day2_morning_temporal_authority.py tests/runtime_v2/test_phase17_x_historical_sell_planning_authority.py
```

Result: `27 passed`

Passed:

```bash
PYTHONPATH=src python3 -m pytest -q tests/artifact_registry/test_phase16av_runtime_lookup_adapter.py tests/runtime_v2/test_phase16av_registry_consumer_cutover.py
```

Result: `12 passed`

Combined regression executed:

```text
54 passed
```

The requested glob `tests/runtime_v2/test_phase15_ap*.py` has no matching files in this repository under zsh. The actual Phase15AP regression file, `tests/runtime_v2/test_phase15ap_position_management_input_contract.py`, was executed and passed.

`py_compile` passed for the changed runtime and test files.
