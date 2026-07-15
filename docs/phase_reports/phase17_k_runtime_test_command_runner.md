# Phase17-K Runtime Test Command Runner

Final judgment: `PHASE17_K_RUNTIME_TEST_COMMAND_RUNNER_ACCEPTED`

Recommended next prefix: `Phase17-L`

Recommended next work name: `Historical Runtime 5BD Smoke Test Command Execution`

## 1. 読み込んだ資料

- `docs/02_architecture/runtime_test_specification.md`
- `docs/02_architecture/runtime_test_specification.json`
- `docs/phase_reports/phase17_h_5bd_final_entry_gate.md`
- `docs/phase_reports/phase17_i_historical_test_logic_and_initial_state_final_review.md`
- `docs/phase_reports/phase17_j_mode_rooted_runtime_path_guard_closure.md`
- `docs/02_architecture/runtime_architecture_v2.md`
- `docs/02_architecture/historical_runtime_test_contract.md`
- `docs/02_architecture/operational_lifecycle_state_reset_and_environment_transition_contract.md`

## 2. Command Entrypoint

正式ユーザー向けコマンドは以下に統一した。

```bash
PYTHONPATH=src python3 scripts/runtime_test.py <subcommand> [options]
```

## 3. Subcommand一覧

- `status`
- `plan`
- `backup`
- `reset`
- `run`
- `validate`
- `resume`
- `rollback`
- `close`
- `show`
- `list-runs`
- `list-backups`

## 4. Profiles

作成したProfile:

- `config/runtime_tests/historical_smoke_5bd.json`
- `config/runtime_tests/historical_extended_smoke_10bd.json`

`historical-smoke` はPhase17 5BD accepted profile、`historical-extended-smoke` はPre-Continuity smokeであり、正式20BD continuity / performance testではない。

## 5. Status

`status` はread-onlyでRuntime root、環境、active run、Current、Ledger、Pending、Runtime State、Registry checkpoint、Accepted Artifact hash、latest backup、external effect policyを表示する。

## 6. Plan

`plan` はread-onlyでbusiness dates、feature dates、carryover、job sequence、evaluation times、Runtime CLI command、Data/PIT refs、fill model、initial state、reset/exclusion scope、evidence path、rollback policyを生成する。

## 7. Backup

`backup` はresettable Trading Stateのみを対象にする。Registry、Accepted Artifacts、Canonical Data、Raw Data、Feature Schema、AI Artifacts、Policy、Safety、Configs、Evidenceは除外する。

Actual backupは`--confirm --yes-i-understand-this-mutates-trading-state`必須。Phase17-Kでは通常`.runtime`のBackupは実行していない。

## 8. Reset

`reset` は有効Backup必須。初期状態はcash/buying_power 1,000,000 JPY、positions/pending/open_orders/executions/PnLは0。部分resetは禁止。

Phase17-Kでは通常`.runtime`のResetは実行していない。隔離fixtureでのみ検証した。

## 9. Run

`run` は通常Runtime v2 CLIを日別・job別に順次呼ぶ。Runner自身はAI判断、Feature計算、Pending生成、Fill生成、Ledger更新、Current更新を行わない。

## 10. 5BD Command

```bash
PYTHONPATH=src python3 scripts/runtime_test.py run \
  --profile historical-smoke \
  --business-days 5 \
  --start-date 2026-07-06 \
  --confirm \
  --yes-i-understand-this-mutates-trading-state
```

## 11. 10BD Command

```bash
PYTHONPATH=src python3 scripts/runtime_test.py run \
  --profile historical-extended-smoke \
  --business-days 10 \
  --start-date 2026-07-06 \
  --dry-run
```

Actual 10BDは正式20BD continuityではない。データ不足の手動補完は禁止。

## 12. Validate

`validate` はCurrent / Pending / Runtime State、external effect、run state、state hashesを確認する。状態修復は行わない。

## 13. Resume

`resume` はsource baseline、Registry hash、Accepted Artifact hashが一致しない場合にfail closedする。失敗jobのskipは禁止。

## 14. Rollback

`rollback` はBackupからresettable Trading State全体を復元する。部分restoreとOperational Foundation restoreは禁止。

Phase17-Kでは通常`.runtime`のRollbackは実行していない。隔離fixtureでのみ検証した。

## 15. Close

`close` はfinal validation、final state freeze、final summary、test validity judgment、acceptance gate judgmentを生成する。自動Resetはしない。

## 16. Dry-run

`backup`、`reset`、`run`、`resume`、`rollback` は`--dry-run`を提供する。Dry-runでは状態変更しない。

## 17. Exit Codes

| Code | Meaning |
|---:|---|
| 0 | PASS |
| 10 | REVIEW_REQUIRED |
| 20 | BLOCKED |
| 30 | HALT |
| 40 | VALIDATION_FAILURE |
| 50 | ROLLBACK_FAILURE |
| 60 | INVALID_ARGUMENT |
| 70 | PRECONDITION_FAILURE |
| 80 | TEST_INVALID |
| 90 | INTERNAL_ERROR |

## 18. Evidence Structure

```text
reports/runtime_tests/
reports/runtime_tests/runs/<run_id>/
reports/runtime_tests/backups/<backup_id>/
```

`runner_log.jsonl`相当の実行ログは今後拡張可能。Trading State / Registry / Canonical DataはログではなくAuthority dataとして扱う。

## 19. Runtime CLI Usage Evidence

Runnerが構築するRuntime commandは以下を含む。

```text
python -m ai_fund_lab_v2.runtime_v2.cli.run_daily_operation
--mode historical
--broker-environment historical_simulated
--runtime-root .runtime
--notification-mode payload-only
--market-refresh-allow-api-fetch false
--stop-on-review-required
--stop-on-blocked
```

隔離テストで`run_runtime_cli`呼び出しをmockし、`-m ai_fund_lab_v2.runtime_v2.cli.run_daily_operation`を検証した。

## 20. No Alternate Runtime Evidence

RunnerはRuntime v2 CLI invocation、argument construction、sequence control、manifest generation、evidence collection、backup/reset/rollback orchestrationだけを行う。Runner専用AI、Feature、Submit、Execution、State authorityは作成していない。

## 21. Lifecycle Safety

Mutating commandは`--confirm --yes-i-understand-this-mutates-trading-state`必須。Production profile/modeはHALT。mode-rooted runtime rootは`INVALID_ARGUMENT`。

## 22. Demo / Production Regression

Demo/Production Runtime codeは変更していない。RunnerはProduction profileを拒否し、Historical external effectsを無効化するProfileのみを受け入れる。

## 23. 作成・更新ファイル

- `scripts/runtime_test.py`
- `config/runtime_tests/historical_smoke_5bd.json`
- `config/runtime_tests/historical_extended_smoke_10bd.json`
- `docs/03_operations/runtime_test_command_guide.md`
- `docs/phase_reports/phase17_k_runtime_test_command_runner.md`
- `reports/phase_reports/phase17_k_runtime_test_command_runner.json`
- `tests/runtime_v2/test_phase17_k_runtime_test_runner.py`

## 24. 実行したテスト

```text
PYTHONPYCACHEPREFIX=/private/tmp/phase17_k_pycache PYTHONPATH=src python3 -m py_compile scripts/runtime_test.py
PYTHONPYCACHEPREFIX=/private/tmp/phase17_k_pycache PYTHONPATH=src python3 scripts/runtime_test.py status --json
PYTHONPYCACHEPREFIX=/private/tmp/phase17_k_pycache PYTHONPATH=src python3 scripts/runtime_test.py plan --profile historical-smoke --business-days 5 --start-date 2026-07-06 --json
PYTHONPYCACHEPREFIX=/private/tmp/phase17_k_pycache PYTHONPATH=src python3 -m pytest -q tests/runtime_v2/test_phase17_k_runtime_test_runner.py
PYTHONPYCACHEPREFIX=/private/tmp/phase17_k_pycache PYTHONPATH=src python3 -m pytest -q tests/runtime_v2/test_phase17_k_runtime_test_runner.py tests/runtime_v2/test_phase17_j_mode_rooted_path_guard.py tests/runtime_v2/test_phase17_g_historical_submit_guard_and_fill.py tests/runtime_v2/test_phase17_b1i_a_historical_environment_composition.py tests/runtime_v2/test_phase14d3_pure_submit_path.py tests/runtime_v2/test_phase15bm_safety_blocked_submit_path.py tests/runtime_v2/test_phase14e17_submit_pipeline_connection.py tests/runtime_v2/test_phase15i_submit_guard_buy_sell_policy_manifest.py tests/runtime_v2/test_phase14e21_execution_readonly_pipeline.py
```

Result:

```text
11 passed in 0.52s
61 passed in 2.24s
```

## 25. 実行していない操作

- 通常`.runtime`のBackup
- 通常`.runtime`のReset
- 通常`.runtime`のRestore
- 5BD Runtime実行
- 10BD Runtime実行
- Current / Ledger / Pending / Runtime State mutation
- Historical Submit / Execution実行
- Feature生成
- Canonical更新
- J-Quants fetch
- Tachibana API
- Demo submit
- Production access
- AI再学習

## 26. Blocking Findings

None.

## 27. Non-blocking Findings

`resume` は固定planから最後に成功したcheckpoint以降を再実行する。失敗jobはskipしない。baseline不一致時はfail closedする。

## 28. 最終判定

`PHASE17_K_RUNTIME_TEST_COMMAND_RUNNER_ACCEPTED`

## 29. Recommended Next Prefix

`Phase17-L`
