# Phase23-Q: Production-Common Daily Scheduler Historical Mode Alignment

## 1. Primary Judgment

`PHASE23_Q_PRODUCTION_COMMON_DAILY_SCHEDULER_HISTORICAL_MODE_ALIGNED_SHORT_VALIDATION_PASS`

## 2. Direct Root Cause

Historical `market_refresh` 停止の直接原因は、Production-common daily scheduler entrypointである `run_daily_operation.py` の引数検証が、Historical precheck後に古いDemo-only guardへfall throughしていたこと。

対象run:

```text
runtime-test-historical-smoke-20260729T002050794943Z
```

停止:

```text
2026-07-06:market_refresh
daily exit_code = 40
aggregate exit_code = 30
reason = Runtime v2 daily scheduler rehearsal allows --mode demo only
```

## 3. demo-only guardの場所

```text
src/ai_fund_lab_v2/runtime_v2/cli/run_daily_operation.py
function: _validate_rehearsal_args
```

旧条件:

```text
if args.mode != "demo":
    raise ValueError("Runtime v2 daily scheduler rehearsal allows --mode demo only")
```

呼出元:

```text
scripts/runtime_test.py
  -> resolve_run_job_command
  -> run_runtime_cli
  -> python -m ai_fund_lab_v2.runtime_v2.cli.run_daily_operation
```

渡されていたmode:

```text
historical
```

## 4. 元のguard目的

`ORIGINAL_INTENT_EVIDENCED_AS_PHASE14_DEMO_REHEARSAL_GUARD`

根拠:

- `docs/phase_reports/phase14_e7_launchd_full_daily_operation_rehearsal.md`
- `tests/runtime_v2/test_phase14e7_launchd_daily_operation_rehearsal.py`

Phase14-E7時点では launchd rehearsal が `--mode demo` 固定で、Productionを許可しない暫定安全guardだった。Historicalを禁止するための設計意図は確認されなかった。

## 5. 正式なProduction-common entrypoint

```text
python -m ai_fund_lab_v2.runtime_v2.cli.run_daily_operation
```

Historical専用schedulerは作成していない。

Runtime Test runnerは同一entrypointへ以下を渡す。

```text
--mode historical
--broker-environment historical_simulated
--business-date <historical business date>
--evaluation-time <explicit evaluation time>
--notification-mode payload-only
--market-refresh-allow-api-fetch false
--runtime-test-run-id <run_id>
--runtime-test-evidence-root reports/runtime_tests/runs/<run_id>
--historical-evaluation-authority reports/runtime_tests/runs/<run_id>/historical_evaluation_authority.json
```

## 6. Production/Demo/Historical差分

| 項目 | Production | Demo | Historical |
|---|---|---|---|
| Business date | operational business date | demo operational business date | explicit historical business date |
| J-Quants fetch | policy controlled | rehearsalではdisabled | false、trueは拒否 |
| Canonical source | operational canonical | operational canonical | historical as-of logical input |
| PIT/as-of | runtime freshness | runtime freshness | historical_asof_view / logical cutoff |
| Broker API | production boundary | demo boundary | disabled |
| Broker Write | scheduler rehearsalでは許可しない | demo policy / submit boundary | false |
| Notification | payload-only | payload-only | payload-only |
| Runtime chain | normal Runtime v2 CLI | same | same |

## 7. 修正内容

- `_validate_rehearsal_args()` をProduction-common environment contractへ整理。
- `production` / `demo` / `historical` を同一schedulerで扱うよう修正。
- Historicalでは以下を明示検証。
  - `--business-date` 必須
  - `--evaluation-time` 必須
  - `--broker-environment historical_simulated`
  - `--notification-mode payload-only`
  - `--market-refresh-allow-api-fetch false`
  - `--historical-evaluation-authority` は存在する場合のみ許可
- `simulation` は引き続き拒否。
- Production submitはscheduler rehearsalからBroker Writeを許可しない。

## 8. Phase23-P Authority回帰確認

維持:

```text
historical_evaluation_authority.json
run_authority_hash
fixed Accepted Generation
--historical-evaluation-authority伝播
Production/Demo date-local Accepted Generation contract
```

Regression:

```text
tests/runtime_v2/test_phase23_p_historical_evaluation_authority.py
tests/runtime_v2/test_phase19_ad_u1_a_accepted_generation_resolver.py
```

PASS。

## 9. External Effect Policy確認

Historical:

```text
broker_write: false
external_delivery: false
jquants_fetch: false
tachibana_api: false
notification_mode: payload-only
```

短時間 `market_refresh` validationで、`allow_api_fetch=false`、`jquants_api_fetch_executed=false`、`broker_write=false`、`external_delivery=false` を確認。

## 10. Status truthfulness

対象runは読み取りのみで確認した。abandon / resume / 削除はしていない。

```text
run_state.status = HALT
fresh_run_summary.status = HALT
fresh_run_summary.final_judgment = HALT
fresh_run_summary.exit_code = 30
daily manifest exit_code = 40
halt_summary.status = HALT
halt_summary.root_reason = Runtime v2 daily scheduler rehearsal allows --mode demo only
```

矛盾なし。

## 11. Short Validation

実施:

```text
py_compile
targeted unit tests
Production/Demo scheduler regression
Historical scheduler validation
Phase23-P authority regression
manifest / JSON validation
```

結果:

```text
4 passed  - Phase23-Q tests
17 passed - Historical environment + Phase23-P authority
9 passed  - Demo/Production scheduler safety
20 passed - Accepted Generation / Phase23-L/P authority regression
JSON validation PASS
```

## 12. 10BD Gate

`READY_FOR_OPERATOR_PRODUCTION_EQUIVALENT_10BD_RERUN`

条件:

- Historical daily scheduler path active
- market_refresh短時間検証PASS
- external effect policy維持
- Phase23-P fixed authority維持
- Production/Demo regression PASS
- known blockerなし

## 13. 未実施事項

```text
10BD
20BD
1年
3年
4年
Runtime Switch
Broker Write
Tachibana API
J-Quants fetch
Active Runのabandon / resume / 削除
```

## Evidence

Evidence directory:

```text
reports/phase23_q_production_common_daily_scheduler_historical_mode_alignment/
```

Machine report:

```text
reports/phase_reports/phase23_q_production_common_daily_scheduler_historical_mode_alignment.json
```
