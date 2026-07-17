# Phase17-BE Submit Exit 10 Root Cause

## 判定

`PHASE17_BE_SUBMIT_EXIT10_ROOT_CAUSE_IDENTIFIED`

本Phaseは調査のみ。Runtime Test `run` / `resume` / `rollback` / `reset` は実行していない。コード修正も実施していない。

## 対象Run

- Run ID: `runtime-test-historical-smoke-20260715T111433056797Z`
- 停止箇所: `2026-07-07:submit`
- Runtime Test run_state上のexit code: `10`
- Runtime CLI上の意味: `EXIT_BLOCKED = 10`
- Runtime Test Runner上の意味: `EXIT_REVIEW_REQUIRED = 10`

`reports/runtime_tests/runs/runtime-test-historical-smoke-20260715T111433056797Z/run_state.json` は、Day2 submit commandが実行され、exit code `10` でHALTしたことを記録している。

## 重要な観測事実

Run Evidence側には以下の通り `daily/2026-07-07/submit` ディレクトリが存在しない。

```text
reports/runtime_tests/runs/runtime-test-historical-smoke-20260715T111433056797Z/daily/2026-07-07/
  data_readiness/
  market_refresh/
  morning/
  sell_planning/
```

一方、実 `.runtime` 側にはsubmit manifest/logが存在する。

```text
.runtime/runtime_state/run_manifest/2026-07-07/runtime-v2-submit-2026-07-07-20260715T111719.096984+0000.json
.runtime/runtime_state/logs/2026-07-07/runtime-v2-submit-2026-07-07-20260715T111719.096984+0000.log
```

したがって、今回の停止は「submit CLI manifest生成前のexit」ではない。submit CLIは起動し、manifest/log生成まで到達し、その後Runtime Test RunnerがRun Evidenceの `daily/.../submit` へ収集する前にHALTしている。

## 実際に通ったコードパス

1. Runtime Test Runnerが以下のsubmit CLIを起動。
   - `--business-date 2026-07-07`
   - `--evaluation-time 2026-07-07T08:45:00+09:00`
   - `--job submit`
   - `--submit-enabled true`
   - `--runtime-test-run-id runtime-test-historical-smoke-20260715T111433056797Z`

2. `src/ai_fund_lab_v2/runtime_v2/cli/run_daily_operation.py` がsubmit jobを処理。

3. submit manifest上、以下のstageは完了。
   - `cli_start`: `PASS`
   - `environment_composition`: `PASS`
   - `operation_contract`: `PASS`
   - `non_trading_day_demo_acceptance_override`: `PASS`
   - `capital_deployment_policy`: `PASS`
   - `current_sot_preflight`: `PASS`
   - `runtime_state_refresh`: `READY`
   - `runtime_data_readiness_gate`: `READY`
   - `historical_safety_authority`: `PASS`

4. `runtime_data_readiness_gate` の重要フィールド。
   - `overall_status`: `READY`
   - `readiness_scope`: `submit`
   - `pending_status`: `READY`
   - `pending_slot_status`: `EMPTY`
   - `current_valuation_status`: `READY`
   - `current_valuation_temporal_authority`: `current_valuation_previous_trading_day_close`
   - `current_valuation_temporal_reason`: `previous_trading_day_close_is_latest_available_at_morning_evaluation`

5. `src/ai_fund_lab_v2/runtime_v2/submit/pipeline.py` の `run_submit_pipeline()` に到達。

6. `read_pending_order_plan_path()` が `.runtime/pending_order_plan/pending_order_plan.json` を読む。

7. Pendingは正式なno-signal/EMPTY状態。
   - `state`: `EMPTY`
   - `status`: `EMPTY`
   - `active_pending`: `false`
   - `items`: `[]`
   - `pending_plan_id`: `pending-order-plan-sell-no-signal-2026-07-07`
   - `target_session_date`: `2026-07-07`
   - `no_action_reason`: `NO_SIGNAL:exit_ai_no_sell_signal`

8. `pending.reader` は `EMPTY + active_pending=false` を以下として返す。
   - `valid=True`
   - `classification="EMPTY"`
   - `plan=None`
   - `errors=()`

9. `submit.pipeline` は `plan is None` を一律invalid扱いし、以下でBLOCKEDを返す。

```python
if not pending_read.valid or pending_read.plan is None:
    return _blocked_result(
        reason="pending current is missing or invalid: " + ",".join(pending_read.errors),
        runtime_root=runtime_root_path,
        pending_path=str(pending_read.path),
    )
```

10. `pending_read.errors` は空なので、reasonは末尾空のまま以下になる。

```text
pending current is missing or invalid: 
```

11. CLI側は `submit_result.status == "BLOCKED"` を受け、`EXIT_BLOCKED = 10` を返す。

## Root Cause

Root Causeは、Pending EMPTY/no-signal contractとSubmit Producer contractの不一致。

Data Readinessは `EMPTY + active_pending=false` を正式なno-signal PendingとしてREADYにしている。一方、Submit Pipelineは同じPendingを `read_pending_order_plan_path()` 経由で読んだ後、`classification="EMPTY"` を正常な注文0件として扱わず、`plan=None` のみを見てinvalid扱いしている。

分類:

- Integration Bug
- Pending Lifecycle Contract Bug
- Submit Producer Contract Bug

今回の停止原因ではないもの:

- Current Valuation Temporal Authorityではない
- Data Readiness Gateではない
- SELL Planningのartifact生成失敗ではない
- Ledger/Runtime State readinessではない
- submit CLI startup validation前のexitではない
- artifact resolution前のprocess起動失敗ではない

## Exit Code 10 を返す箇所

### Runtime CLI

`src/ai_fund_lab_v2/runtime_v2/cli/run_daily_operation.py`

- line 81: `EXIT_BLOCKED = 10`
- line 203: non-trading-day demo override BLOCKED
- line 252: safety evaluation result BLOCKED
- line 281: safety producer result BLOCKED
- line 341: data readiness result blocked with `--stop-on-blocked`
- line 444: broker readonly result BLOCKED
- line 593: morning capability decision not PASS
- line 625: morning pipeline BLOCKED
- line 651: sell planning capability decision not PASS
- line 705: sell planning pipeline BLOCKED
- line 737: sell-hold review-only morning BLOCKED
- line 770: submit pending promotion review BLOCKED
- line 802: authoritative pending apply review BLOCKED
- line 843: submit pipeline BLOCKED
- line 881: execution readonly pipeline BLOCKED
- line 926: market refresh pipeline BLOCKED

今回通ったのは line 843 のsubmit pipeline BLOCKED経路。

### Runtime Test Runner

`scripts/runtime_test.py`

- line 35: `EXIT_REVIEW_REQUIRED = 10`
- line 298: planのbaseline compatibilityがPASSでない場合
- line 626: close summary statusがPASSでない場合

今回の `completed_jobs[].exit_code=10` はRuntime CLI subprocessの戻り値であり、Runner自身のplan/close戻り値ではない。Runner側の10は名称上 `REVIEW_REQUIRED` だが、今回のCLI側10は `BLOCKED`。

## Evidence

- `reports/runtime_tests/runs/runtime-test-historical-smoke-20260715T111433056797Z/run_state.json`
- `.runtime/runtime_state/run_manifest/2026-07-07/runtime-v2-submit-2026-07-07-20260715T111719.096984+0000.json`
- `.runtime/runtime_state/logs/2026-07-07/runtime-v2-submit-2026-07-07-20260715T111719.096984+0000.log`
- `.runtime/pending_order_plan/pending_order_plan.json`
- `.runtime/runtime_state/sell_pipeline/2026-07-07/order_plan.json`
- `reports/runtime_tests/runs/runtime-test-historical-smoke-20260715T111433056797Z/daily/2026-07-07/data_readiness/data_readiness.json`
- `src/ai_fund_lab_v2/runtime_v2/pending/reader.py`
- `src/ai_fund_lab_v2/runtime_v2/submit/pipeline.py`
- `src/ai_fund_lab_v2/runtime_v2/cli/run_daily_operation.py`
- `scripts/runtime_test.py`

## 次フェーズでの修正対象

修正は本Phaseでは未実施。次フェーズで修正する場合は、Historical専用分岐ではなくRuntime共通契約として、Submit Pipelineが `classification="EMPTY"` / no-signal Pendingを正式な注文0件terminal状態として扱う必要がある。
