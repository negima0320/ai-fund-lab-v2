# Phase17-AI PM Adapter Formal Registry Acceptance

## Status

`PHASE17_AI_PM_ADAPTER_FORMAL_REGISTRY_ACCEPTANCE_ACCEPTED`

## Objective

Phase17-AH confirmed that the Position Management Runtime Adapter path was correct but the accepted Registry hash was stale. Phase17-AI formally accepted the current PM Runtime Adapter source as the shared Production, Demo, and Historical Runtime authority.

Accepted authority:

```text
POSITION_MANAGEMENT_POLICY_SET:RUNTIME_ADAPTER
```

Accepted runtime adapter:

```text
src/ai_fund_lab_v2/runtime_v2/position_management/producer.py
```

## Identity

- Previous accepted adapter hash: `2924fa7e132e9602653cd1033a9b6b6925f8ef419accfafd673b05bdba4e71df`
- New accepted adapter hash: `2e6790f07cb3981fe0dbc575b059bbbc1abd6fb27f6c74b989b8bb8285951535`
- New PM artifact set: `control.position_management.accepted_set@sha256-eea7859b52fbbe60`
- Accepted event: `event-9239998c-801b-4c26-960a-6d4df29c5fc3-ad7d9b85c2387640`

The hash contract remains SHA256 over the PM Runtime Adapter source file bytes. Absolute paths, cwd, checkout location, timestamps, pyc/cache files, runtime-test identity, and environment mode are not hash material.

## Formal Tooling

The acceptance used the existing append-only Artifact Registry tooling:

- `RegistryEventLogWriter` for DRAFT and VALIDATED lifecycle events
- `AcceptanceEvidenceBundleValidator` for evidence and approval gates
- atomic append of LEGACY and ACCEPTED events
- `MaterializedRegistryIndexBuilder` for index rebuild
- `RegistryCheckpointWriter` for checkpoint rebuild

No manual Registry JSON hash edit, index-only edit, or checkpoint-only edit was performed.

## Scope

Updated authority:

```text
POSITION_MANAGEMENT_POLICY_SET:RUNTIME_ADAPTER
```

Not updated:

- Candidate model
- Opportunity model
- Position Management model
- Capital Deployment Policy
- Safety Policy
- Broker adapter
- Submit adapter
- Execution adapter
- Current Valuation adapter
- Other Registry authority

## Verification

Post-acceptance Registry resolution:

- Registry key resolution: `READY`
- authority count: `1`
- accepted path equals runtime path: `PASS`
- accepted hash equals current source hash: `PASS`
- canonical identity resolution: `READY`
- duplicate authority: `false`
- unknown schema: `false`
- repo-external path: `false`
- `.` source: `false`

Runtime consumers share the same authority:

- direct PM producer: `READY`
- sell planning: `READY`
- Data Readiness PM validation: `READY`
- Historical runtime: `READY`
- Demo runtime: `READY`
- Production runtime: `READY`

Fail-closed preservation was verified for source mismatch, wrong path, missing member, duplicate member, unknown schema, and missing source through the Phase17-AH and PM adapter authority regression tests.

## Regression

Passed:

```text
54 passed
```

Command scope:

```bash
PYTHONPATH=src python3 -m pytest -q \
  tests/runtime_v2/test_phase17_ah_pm_adapter_registry_identity_guard.py \
  tests/runtime_v2/test_phase17_b1i_b_pm_adapter_authority.py \
  tests/runtime_v2/test_phase15ap_position_management_input_contract.py \
  tests/runtime_v2/test_phase17_ag_day2_sell_planning_integration.py \
  tests/runtime_v2/test_phase17_af_day2_morning_temporal_authority.py \
  tests/runtime_v2/test_phase17_x_historical_sell_planning_authority.py \
  tests/artifact_registry/test_phase16av_runtime_lookup_adapter.py \
  tests/runtime_v2/test_phase16av_registry_consumer_cutover.py
```

Additional checks:

- `py_compile`: `PASS`
- `git diff --check`: `PASS`
- event chain validation: `PASS`
- index validation: `PASS`
- checkpoint validation: `PASS`
- accepted-current resolution: `READY`

## Runtime Mutation Audit

Allowed mutation performed:

- PM Adapter Artifact Registry acceptance only

Trading/runtime state not changed:

- Pending: unchanged
- Ledger: unchanged
- Current: unchanged
- Runtime run manifests: unchanged
- Demo PM state: unchanged
- Production PM state: unchanged

Not performed:

- `runtime_test.py run/resume/reset/rollback/backup/close`
- Frozen Run mutation
- Broker access
- Demo write
- Production access
- Submit
- Execution
- Current Valuation apply
- J-Quants fetch
- external notification
- AI retraining
- canonical market data mutation

## Evidence

Evidence directory:

```text
reports/phase17_ai_pm_adapter_formal_registry_acceptance/
```

Required evidence files:

- `pre_acceptance_identity.json`
- `source_diff_summary.json`
- `acceptance_request.json`
- `acceptance_event.json`
- `accepted_artifact.json`
- `registry_index_verification.json`
- `registry_checkpoint_verification.json`
- `accepted_current_resolution.json`
- `runtime_consumer_resolution.json`
- `regression_results.json`
- `rollback_metadata.json`
- `external_effect_audit.json`
- `final_judgment.json`

JSON summary:

```text
reports/phase_reports/phase17_ai_pm_adapter_formal_registry_acceptance.json
```

## Final Judgment

`PHASE17_AI_PM_ADAPTER_FORMAL_REGISTRY_ACCEPTANCE_ACCEPTED`

The PM Runtime Adapter Registry identity guard now resolves the current Runtime source as the formal accepted authority. The 5 business day Historical Smoke clean rerun may proceed, subject to any non-PM blockers discovered by the clean rerun itself.
