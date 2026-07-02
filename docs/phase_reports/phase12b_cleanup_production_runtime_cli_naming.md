# Phase12-B Cleanup: Production Runtime CLI Naming

作成日: 2026-06-29

## Status

```text
PHASE12B_CLEANUP_PRODUCTION_RUNTIME_CLI_NAMING_COMPLETE
REFACTOR_ONLY
NO_DEMO_ORDER_EXECUTION
NO_PRODUCTION_ORDER_EXECUTION
NO_LINE_SEND
NO_AI_RETRAINING
NO_BACKTEST_RERUN
```

## Scope

Phase12-Bで追加した運用CLIを、Phase専用ではなくProduction Runtimeでも使える名前へ整理した。

Phase9の以下を参考にした。

- `scripts/run_phase9_*.py`
- `src/ai_fund_lab_v2/paper_trading/`

確認観点:

- CLI scriptは薄く保つ。
- 実処理は `src/ai_fund_lab_v2/...` 配下へ寄せる。
- artifact rootはCLIから薄く渡し、実際のpath生成はmoduleで行う。
- daily flowはmodule側のrunner関数に寄せる。
- Mac手動実行とlaunchd実行の両方で使える引数にする。
- 引数を増やしすぎない。

## Rename

```text
scripts/run_phase12_preflight.py -> scripts/run_preflight.py
scripts/run_phase12_daily_plan.py -> scripts/run_daily_plan.py
scripts/run_phase12_approval_prepare.py -> scripts/run_approval_prepare.py
scripts/run_phase12_demo_submit.py -> scripts/run_demo_submit.py
scripts/run_phase12_fill_monitor.py -> scripts/run_fill_monitor.py
scripts/run_phase12_reconcile.py -> scripts/run_reconcile.py
scripts/run_phase12_daily_report.py -> scripts/run_daily_report.py
scripts/run_phase12_audit.py -> scripts/run_operation_audit.py
```

## Module Layout

```text
src/ai_fund_lab_v2/phase12/
```

を

```text
src/ai_fund_lab_v2/operations/
```

へ整理した。

CLIは `ai_fund_lab_v2.operations.operations` のrunner関数を呼び出す薄い構成を維持する。

## Environment

`--env` CLI引数を廃止した。

環境判定は次の順に寄せた。

```text
.env / Runtime Config
↓
Broker Environment
↓
demo or production
```

`TACHIBANA_API_ENV` が未設定、不正値、またはBroker設定と矛盾する場合は fail closed。

`run_demo_submit.py` は demo 環境以外では fail closed。

## Runtime Artifact

保存先を変更した。

```text
.runtime/phase12/
```

から

```text
.runtime/operations/
```

へ変更。

過去Phase成果物である `docs/phase_reports/` と `reports/phase_reports/` は変更対象外。

## launchd

launchd sampleを更新した。

```text
tools/launchd/com.aifundlab.phase12.*.plist
```

から

```text
tools/launchd/com.aifundlab.operations.*.plist
```

へ変更。

ProgramArgumentsは新CLI名に更新し、`--env demo` を削除した。

## Validation

```text
PYTHONPATH=src python3 -m pytest tests/phase12 -q
10 passed
```

```text
PYTHONPYCACHEPREFIX=/private/tmp/operations_pycache python3 -m py_compile ...
PASS
```

```text
python3 -m json.tool reports/phase_reports/phase12b_demo_full_operation_minimal_implementation.json
PASS
```

CLI help確認:

```text
run_preflight.py
run_daily_plan.py
run_approval_prepare.py
run_demo_submit.py
run_fill_monitor.py
run_reconcile.py
run_daily_report.py
run_operation_audit.py
```

いずれも `--env` を表示しないことを確認。

CLI smoke root:

```text
/private/tmp/operations_cli_check
```

結果:

- `run_preflight.py`: `REVIEW_REQUIRED`
- `run_daily_plan.py`: `PASS`
- `run_approval_prepare.py`: `PASS`
- `run_demo_submit.py`: `PASS`
- `run_fill_monitor.py`: `PASS`
- `run_daily_report.py`: `PASS`
- `run_reconcile.py`: `PASS`
- `run_operation_audit.py`: `PASS`

Preflightの `REVIEW_REQUIRED` は、一時実行時のrequired env不足によるもので、secret値は出力していない。

## Forbidden Actions Confirmation

- demo_order_executed: false
- production_order_executed: false
- production_unlock_executed: false
- line_send_executed: false
- ai_retraining_executed: false
- one_year_backtest_rerun: false
- five_year_backtest_rerun: false
- broker_api_spec_changed: false
- runtime_spec_changed: false

