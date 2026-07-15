# Phase17-J Mode-Rooted Runtime Path Guard Closure

Final judgment: `PHASE17_J_MODE_ROOTED_PATH_GUARD_ACCEPTED`

Recommended next prefix: `Phase17-K`

Recommended next work name: `Historical Runtime 5BD Smoke Test`

## 1. Loaded Materials

- Phase17-I historical test logic and initial state final review
- Phase17-H final entry gate and runbooks
- Phase17-G historical submit guard and fill model implementation
- Phase17-B1I-A historical environment composition
- Runtime Architecture v2
- Historical Runtime Contract
- Operational Lifecycle Contract
- Operational Data Architecture

## 2. Targeted Blocker

Phase17-I stopped on one environment isolation gap:

`submit_pipeline_mode_rooted_historical_path_not_halt`

The CLI and Execution Pipeline already rejected mode-rooted historical runtime paths, but direct Submit Pipeline invocation reached policy validation before path HALT.

## 3. Path Guard Contract

Runtime v2 Current root must remain fixed at `.runtime`.

The following runtime roots are forbidden:

- `.runtime/production`
- `.runtime/demo`
- `.runtime/historical`
- `.runtime/simulation`
- `.runtime/backtest`

The guard normalizes paths before checking, so equivalent forms with `.` / `..` / trailing segments are covered. Non-runtime documentation or report paths such as `reports/historical_evidence` and `docs/historical` are not blocked.

Evidence: `reports/phase17_j_mode_rooted_runtime_path_guard_closure/path_guard_contract.json`

## 4. Implementation

Added a common path guard in `storage/path_resolver.py`:

- `MODE_ROOTED_RUNTIME_ROOT_FORBIDDEN`
- `is_mode_rooted_runtime_root`
- `reject_mode_rooted_runtime_root`

Submit Pipeline, Execution Pipeline, and CLI validation now call this same helper.

## 5. Submit Pipeline Closure

Direct Submit Pipeline invocation with `.runtime/historical` now returns:

- status: `HALT`
- reason: `MODE_ROOTED_RUNTIME_ROOT_FORBIDDEN`

The new regression monkeypatches policy resolution to raise if reached. The test passes, proving the submit path returns before policy, safety, pending, adapter, or broker stages.

Evidence: `reports/phase17_j_mode_rooted_runtime_path_guard_closure/early_halt_evidence.json`

## 6. Execution Pipeline Equivalence

Execution Pipeline uses the same helper and reason code. This preserves the Phase17-I expected behavior and removes divergence between Submit and Execution path validation.

Evidence: `reports/phase17_j_mode_rooted_runtime_path_guard_closure/execution_path_guard_comparison.json`

## 7. CLI Equivalence

CLI validation now rejects mode-rooted runtime roots for historical, demo, and production modes through the same helper.

The historical fixed root `.runtime` remains accepted by validation.

## 8. Demo / Production Regression

No demo or production semantic relaxation was introduced.

Regression coverage included existing pure submit, safety-blocked submit, submit connection, buy/sell policy manifest, and readonly execution tests.

Evidence: `reports/phase17_j_mode_rooted_runtime_path_guard_closure/demo_production_historical_regression.json`

## 9. Runtime Core Diff

Phase17-J changed only path guard behavior, its shared helper, tests, and reports. It did not add:

- Historical-specific Runtime
- Historical-specific Feature Producer
- Historical-specific Current
- Historical-specific Ledger
- Historical-specific Pending
- Historical-specific State

Evidence: `reports/phase17_j_mode_rooted_runtime_path_guard_closure/runtime_core_diff.json`

## 10. Phase17-I Gate Revalidation

The Phase17-I blocker is closed.

Unchanged Phase17-I conditions:

- No reset has been executed.
- Initial state remains pre-reset.
- Baseline must be recaptured immediately before Phase17-K execution.
- 5BD data readiness remains based on Phase17-D/H/I artifacts.

Evidence: `reports/phase17_j_mode_rooted_runtime_path_guard_closure/phase17_i_gate_revalidation.json`

## 11. Tests

Executed:

```text
PYTHONPYCACHEPREFIX=/private/tmp/phase17_j_pycache PYTHONPATH=src python3 -m pytest -q tests/runtime_v2/test_phase17_j_mode_rooted_path_guard.py tests/runtime_v2/test_phase17_g_historical_submit_guard_and_fill.py tests/runtime_v2/test_phase17_b1i_a_historical_environment_composition.py tests/runtime_v2/test_phase14d3_pure_submit_path.py tests/runtime_v2/test_phase15bm_safety_blocked_submit_path.py tests/runtime_v2/test_phase14e17_submit_pipeline_connection.py tests/runtime_v2/test_phase15i_submit_guard_buy_sell_policy_manifest.py tests/runtime_v2/test_phase14e21_execution_readonly_pipeline.py
```

Result:

```text
50 passed in 1.81s
```

## 12. Created / Updated Files

- `src/ai_fund_lab_v2/runtime_v2/storage/path_resolver.py`
- `src/ai_fund_lab_v2/runtime_v2/submit/pipeline.py`
- `src/ai_fund_lab_v2/runtime_v2/execution/readonly_pipeline.py`
- `src/ai_fund_lab_v2/runtime_v2/cli/run_daily_operation.py`
- `tests/runtime_v2/test_phase17_j_mode_rooted_path_guard.py`
- `docs/phase_reports/phase17_j_mode_rooted_runtime_path_guard_closure.md`
- `reports/phase_reports/phase17_j_mode_rooted_runtime_path_guard_closure.json`
- `reports/phase17_j_mode_rooted_runtime_path_guard_closure/*.json`

## 13. Not Executed

- 5BD Runtime
- Backup
- Reset
- Restore
- Current mutation
- Ledger mutation
- Pending mutation
- Runtime State mutation
- Feature generation
- Canonical update
- J-Quants fetch
- Tachibana API
- Demo submit
- Production access
- AI retraining

## 14. Blocking

None for Phase17-J.

## 15. Non-blocking

The working tree already contains uncommitted Phase17-A through Phase17-I changes. Phase17-K must recapture source and state baselines immediately before any backup, reset, or 5BD execution.

## 16. Final Judgment

`PHASE17_J_MODE_ROOTED_PATH_GUARD_ACCEPTED`

## 17. Recommended Next Prefix

`Phase17-K`
