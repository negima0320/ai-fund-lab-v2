# Phase32-DZ - Post-DY Source-Commit Resume Precondition Read-Only Audit

## Scope

- Target run: `runtime-test-historical-extended-smoke-20260902T060955933565Z`
- Current failure: `resume rejected; baseline changed: source_commit`
- Exit code: `70`
- Mode: READ-ONLY audit
- Runtime/source/run-state/Pending/Ledger mutation: none
- Resume/recover/replay/fresh-run: not executed

## Evidence Inspected

- `scripts/runtime_test.py`
- `docs/03_operations/runtime_test_command_guide.md`
- `docs/02_architecture/runtime_test_specification.md`
- `tests/runtime_v2/test_phase17_k_runtime_test_runner.py`
- `reports/runtime_tests/runs/runtime-test-historical-extended-smoke-20260902T060955933565Z/run_state.json`
- `reports/runtime_tests/runs/runtime-test-historical-extended-smoke-20260902T060955933565Z/plan.json`
- `reports/runtime_tests/runs/runtime-test-historical-extended-smoke-20260902T060955933565Z/strategy_shadow_manifest.json`
- `reports/runtime_tests/runs/runtime-test-historical-extended-smoke-20260902T060955933565Z/historical_evaluation_authority.json`
- `reports/runtime_tests/runs/runtime-test-historical-extended-smoke-20260902T060955933565Z/daily/2023-12-11/*`
- Git metadata and read-only diffs.

## Exit Code 70 Contract

The Runtime Test Specification maps exit code `70` to:

`PRECONDITION_FAILURE`

Procedure:

`Stop; satisfy missing Backup/Reset/Baseline/Gate precondition.`

The Runtime Test Command Guide states:

`Resume validates source baseline, Registry hash, and accepted artifact hash. If any baseline changed, resume is rejected. Failed jobs are never skipped.`

In `scripts/runtime_test.py`, `resume_command()` enforces this before dry-run handling, confirmation, plan validation, or job execution:

```python
baseline = run_state.get("source_baseline") or {}
current = source_baseline(runtime_root)
mismatches = [key for key in ("source_commit", "source_dirty", "registry_hash") if baseline.get(key) != current.get(key)]
if mismatches:
    raise RuntimeTestError(
        f"resume rejected; baseline changed: {', '.join(mismatches)}",
        status="PRECONDITION_FAILURE",
        exit_code=EXIT_PRECONDITION_FAILURE,
    )
```

Therefore the current failure is a resume entry-gate precondition failure, not a Runtime morning failure, not a new strategy artifact failure, and not a trading-state mutation failure.

## Baseline Comparison

Run-created source baseline from `run_state.json`:

- `source_commit`: `a56f2bc26105eb14fd67322b7cd53c0d6ef1b1bd`
- `source_dirty`: `true`
- `registry_hash`: `4c07b5647425b32653e3e0a0e1a1164130133cc0db2c22881dcef5b7c97a35ba`
- `accepted_artifact_hash`: `5451016e490214f81440f0d4fd154dc89cd76a86f84dd7daed5e8fb383e144a5`
- `captured_at`: `2026-09-02T06:11:18.173383Z`

Current source baseline:

- `source_commit`: `1f64f49ee9a8dd48280007e4df656e5f03e231ca`
- `source_dirty`: `true`
- `registry_hash`: `4c07b5647425b32653e3e0a0e1a1164130133cc0db2c22881dcef5b7c97a35ba`
- `accepted_artifact_hash`: `5451016e490214f81440f0d4fd154dc89cd76a86f84dd7daed5e8fb383e144a5`

Mismatched resume keys:

- `source_commit`

Matched:

- `source_dirty`
- `registry_hash`
- accepted artifact hash, although `resume_command()` does not include it in the three-key mismatch list.

## DW/DY Difference Classification

This is not only a DY diff.

Git shows:

- baseline run source commit: `a56f2bc phase32 co実装後`
- current HEAD: `1f64f49 phase32 購入済み銘柄買えない問題解消`

`git diff a56f2bc..HEAD` includes broad post-CO changes across CW/DG/DL and related docs/tests/source, including:

- `scripts/runtime_test.py`
- `src/ai_fund_lab_v2/runtime_v2/buy_ai/producer.py`
- `src/ai_fund_lab_v2/runtime_v2/corporate_action_adjustment.py`
- `src/ai_fund_lab_v2/runtime_v2/planning/strategy_authority.py`
- `src/ai_fund_lab_v2/strategy/buy_quality.py`
- `src/ai_fund_lab_v2/strategy/input_materialization.py`
- `src/ai_fund_lab_v2/strategy/minimum_tick_authority.py`
- `src/ai_fund_lab_v2/strategy/portfolio_construction.py`
- `src/ai_fund_lab_v2/strategy/position_sizing.py`
- `src/ai_fund_lab_v2/strategy/shadow_runtime.py`
- `src/ai_fund_lab_v2/strategy/strategy_intelligence.py`
- `src/ai_fund_lab_v2/strategy/tick_quantization.py`
- many phase reports and tests.

The current uncommitted working-tree diff after DW/DY additionally includes:

- `docs/03_operations/runtime_test_command_guide.md`
- `scripts/runtime_test.py`
- `src/ai_fund_lab_v2/strategy/marginal_capital_value.py`
- `src/ai_fund_lab_v2/strategy/portfolio_construction.py`

DY itself is a source-content change, but because it is currently uncommitted it does not by itself change `git rev-parse HEAD`. The exact failing precondition key is `source_commit`, and that mismatch comes from the run baseline `a56f2bc...` versus current HEAD `1f64f49...`. DY contributes to the dirty source content currently desired for continuation, but the rejected key is not uniquely attributable to DY.

## Existing Run Evidence Integrity

The existing run evidence remains intact:

- `run_state.status`: `HALT`
- `run_state.next_job`: `2023-12-11:morning`
- `completed_business_days`: `293`
- last completed day: `2023-12-08`
- `plan.json` exists
- requested business days: `650`
- job sequence exists and is standard:
  - `market_refresh`
  - `data_readiness`
  - `morning`
  - `sell_planning`
  - `submit`
  - `execution`
  - `current_valuation_refresh`
  - `runtime_state_refresh`
- `strategy_shadow_manifest.hash_validation`: `PASS`
- historical evaluation authority: `PASS`
- accepted generation: `phase19_aq_accepted_generation_641e6e313543f013`

For `2023-12-11`:

- `market_refresh` evidence exists and passed with exit code `0`
- `data_readiness` evidence exists and passed with exit code `0`
- `morning` evidence exists and stopped with exit code `10`
- no `sell_planning` directory exists
- no `submit` directory exists
- no `execution` directory exists

Therefore there is no inspected `2023-12-11` submit/execution side effect that must be preserved or unwound.

## Design Reason for Strict Source-Commit Matching

The strict source baseline guard protects historical run comparability and provenance:

- completed-day evidence is tied to the source implementation that generated it
- failed jobs are retried only when the runtime source, dirty-state classification, and registry baseline still match
- a resumed run must not silently mix different source generations without reviewer-visible provenance
- the guard prevents a code repair from being smuggled into a same-run continuation without an explicit source-transition record

This is intentional fail-closed behavior at the runtime_test orchestration layer.

## Existing Canonical Continuation Mechanism

No existing supported command was found that formally refreshes or transitions a halted run's source baseline while preserving completed days.

Inspected command set includes:

- `resume`
- `recover-failed-execution`
- `recover-stale-pending`
- `recover-partial-submit`
- `replay-recovered-day`
- `finalize-partial-submit-day`
- `resolve-ca-adjustment-authority`
- `validate`
- `close`
- `abandon`
- `fresh-run`

These commands do not provide a canonical source-baseline transition for:

`HALT at 2023-12-11:morning after source repair, no submit/execution side effect, completed 293BD preserved`

The Runtime Test Specification says:

`Baseline refresh must not hide unexpected diffs. Any baseline update requires a reason, hash, authority, and reviewer-visible evidence.`

That establishes requirements for a baseline update, but the current runner does not expose an existing command that performs such a source transition for a halted run.

## Same-Run Continuation Without Baseline Edit

Baseline manual edit is not acceptable and is explicitly prohibited.

Guard bypass is not acceptable and is explicitly prohibited.

With the current toolset, same-run continuation under current source is blocked before the failed job can be retried. The `resume` command will continue to reject the run until either:

1. the working tree/HEAD is returned to the original run baseline, or
2. a canonical source-transition/baseline-refresh mechanism is implemented and applied with explicit reviewer-visible provenance.

Option 1 would lose the DY repair needed for the previous DW SHADOW failure, so it is not a valid continuation path for the repaired current source.

## Required Provenance for Current-Source Resume Permission

To permit current-source same-run continuation without bypass, the system would need a formal source-transition artifact and command that records at minimum:

- target run id
- halted business date and job: `2023-12-11:morning`
- old source baseline:
  - source commit
  - source dirty flag
  - registry hash
  - accepted artifact hash
- new source baseline:
  - source commit
  - source dirty flag
  - registry hash
  - accepted artifact hash
- explicit source diff inventory
- repair reason referencing DX/DY
- proof that no completed-day runtime evidence is rewritten
- proof that no target-date submit/execution side effect exists
- proof that restart point is the failed job, not a skipped job
- focused validation results for the repair
- reviewer/operator approval
- immutable audit evidence path
- run_state update performed only by that canonical command

No such accepted artifact/command exists in the inspected current implementation.

## Fresh-Run Necessity

Fresh-run is not inherently required by the target run's trading state:

- completed 293BD evidence is intact
- `2023-12-11` has not reached sell planning, submit, or execution
- no target-date side effect was found
- safe technical continuation point remains `2023-12-11:morning`

However, with the existing runner commands and strict baseline guard, fresh-run is the only currently available canonical way to validate the current source without manually editing the halted run baseline.

Therefore:

- same-run continuation is conceptually possible after a future canonical source-transition mechanism
- same-run continuation is not currently possible with existing commands
- fresh-run is required only if no source-transition/baseline-refresh repair is added

## Required Final Answers

- `DIRECT_PRECONDITION_CAUSE`: `runtime_test resume` compares `run_state.source_baseline` to current `source_baseline(runtime_root)` and rejects because `source_commit` changed from `a56f2bc26105eb14fd67322b7cd53c0d6ef1b1bd` to `1f64f49ee9a8dd48280007e4df656e5f03e231ca`.
- `SOURCE_COMMIT_CHANGE_EXPECTED_FROM_DY`: `PARTIAL/NUANCED` - source-content change is expected after DY, but the rejected `source_commit` mismatch is not uniquely caused by DY because DY is uncommitted and the HEAD mismatch spans broad post-CO changes from `a56f2bc` to `1f64f49`.
- `EXISTING_RUN_EVIDENCE_INTACT`: `YES`
- `CANONICAL_POST_SOURCE_CHANGE_CONTINUATION_PATH`: `NONE_EXISTING`; required future path is a canonical source-transition/baseline-refresh command with reviewer-visible provenance.
- `SAME_RUN_CONTINUATION_POSSIBLE`: `NOT_WITH_EXISTING_COMMANDS`; `YES_CONCEPTUALLY_AFTER_CANONICAL_SOURCE_TRANSITION_TOOLING`
- `BASELINE_MANUAL_EDIT_REQUIRED`: `NO`
- `GUARD_BYPASS_REQUIRED`: `NO`
- `FRESH_RUN_REQUIRED`: `CONDITIONAL` - required with current existing toolset; not inherently required if canonical source-transition tooling is implemented.
- `SAFE_USER_COMMAND`: no safe same-run continuation command exists now. Do not run `resume` again until a canonical source-transition mechanism exists or the source is restored to the original baseline. If choosing current existing tooling only, the safe validation path is a new `fresh-run`, but that does not preserve the 293BD run.
- `TARGET_RUN_MUTATED`: `NO`

## Final Judgment

`PHASE32_DZ_SOURCE_COMMIT_RESUME_PRECONDITION_CONFIRMED_NO_EXISTING_CANONICAL_SAME_RUN_SOURCE_TRANSITION_PATH`

