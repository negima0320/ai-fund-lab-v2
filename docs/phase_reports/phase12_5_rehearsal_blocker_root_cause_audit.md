# Phase12.5 Rehearsal Blocker Root Cause Audit

作成日: 2026-07-06

## Summary

Pending Plan Full Manual Runtime Rehearsal は最後まで到達していない。

判定: **REVIEW_REQUIRED**

主因は2系統ある。

1. Broker ReadOnly は `FAILED_LOGIN_SESSION`。設定・secret file は存在しているが、login/session取得が `BrokerTransportError` で3回失敗しており、snapshot / positions safe diagnosis まで進んでいない。
2. Market / Feature Refresh は `MARKET_DATA_NOT_YET_AVAILABLE` 表示だが、詳細を見ると単なる当日未配信だけではない。`.runtime/operations` 配下のJ-Quants履歴が空で、2026-02-16から2026-07-03まで `JQuantsClientError`、2026-07-06は `not_yet_available`、ログ上は `url_error` が連続している。

Phase C の fail-closed は正常で、pending が無い状態でSubmitへ進まなかった点は正しい。

## Read Artifacts / Logs / Code

Artifacts:

- `.runtime/operations/broker_readonly_reports/2026-07-06/broker_readonly_snapshot_report.json`
- `.runtime/operations/preflight/2026-07-06/preflight_result.json`
- `.runtime/operations/market_refresh/2026-07-06/market_refresh_manifest.json`
- `.runtime/operations/market_refresh/2026-07-06/market_data_refresh_detail.json`
- `.runtime/operations/feature_refresh/2026-07-06/feature_refresh_manifest.json`
- `.runtime/operations/feature_refresh/2026-07-06/feature_refresh_detail.json`
- `.runtime/operations/feature_refresh/2026-07-06/latest_features.json`
- `.runtime/operations/data_quality/2026-07-06/data_quality_result.json`
- `.runtime/operations/order_plan/2026-07-06/order_plan.json`
- `.runtime/operations/daily_plan/2026-07-06/daily_plan_result.json`

Logs / runtime state:

- `.runtime/logs/jquants_client.log`
- `/tmp/aifundlab.operations.*.out.log`: no matching files found
- `/tmp/aifundlab.operations.*.err.log`: no matching files found
- `.env` key presence only
- `~/.config/aifundlab/tachibana/demo/` file presence only

Code:

- `src/ai_fund_lab_v2/broker/tachibana_broker_snapshot.py`
- `src/ai_fund_lab_v2/broker/retry_policy.py`
- `src/ai_fund_lab_v2/broker/settings.py`
- `src/ai_fund_lab_v2/broker/secrets.py`
- `src/ai_fund_lab_v2/data_sources/jquants/client.py`
- `src/ai_fund_lab_v2/paper_trading/market_data_refresh.py`
- `src/ai_fund_lab_v2/paper_trading/market_data_readiness.py`
- `src/ai_fund_lab_v2/paper_trading/feature_refresh.py`
- `src/ai_fund_lab_v2/operations/market_refresh.py`
- `src/ai_fund_lab_v2/operations/operations.py`
- `scripts/run_preflight.py`
- `scripts/run_market_refresh.py`
- `scripts/run_daily_plan.py`

## Broker ReadOnly FAILED_LOGIN_SESSION

Observed artifact:

- report status: `FAILED_LOGIN_SESSION`
- preflight status: `REVIEW_REQUIRED`
- `failure_classification`: `login_session_error`
- `safe_diagnosis.final_failure_classification`: `FAILED_LOGIN_SESSION`
- `safe_diagnosis.failure_stage`: `login_session`
- `safe_diagnosis.safe_error_class`: `BrokerTransportError`
- retry attempts: `3`
- attempt 1: retryable `true`
- attempt 2: retryable `true`
- attempt 3: retryable `false`
- `login_result_code_present`: `false`
- `login_result_code_zero`: `null`
- `decrypt_attempted`: `false`
- `decrypt_success`: `false`
- logout: `NOT_EXECUTED`
- `raw_response_saved=false`
- `secret_saved=false`

Safe config presence check:

- `.env` exists.
- `TACHIBANA_API_ENV` key exists.
- `TACHIBANA_API_BASE_URL` key exists.
- `TACHIBANA_API_READONLY_SMOKE_ENABLED` key exists.
- `TACHIBANA_API_AUTH_ID` / `TACHIBANA_API_AUTH_ID_FILE` keys exist.
- `TACHIBANA_API_PRIVATE_KEY_FILE` / `TACHIBANA_API_PRIVATE_KEY_FORMAT` keys exist.
- `TACHIBANA_API_SECOND_PASSWORD_FILE` key exists.
- local config dir exists: `~/.config/aifundlab/tachibana/demo/`
- `e_api_authid.txt` exists and is non-empty.
- `e_api_private_key.der` exists and is non-empty.
- `e_api_private_key.pem` exists and is non-empty.
- loader check: `secret_loader_ok=true`
- resolved environment: `demo`
- resolved base URL is demo URL: `true`
- `readonly_smoke_enabled=true`
- second password file status: configured, exists, readable, non-empty.

Code basis:

- `run_tachibana_broker_snapshot()` loads settings and secrets before login.
- Missing config would raise `BrokerConfigurationError` and be classified as `FAILED_CONFIGURATION`.
- The observed failure is instead caught through `_login_with_retry()` as `BrokerSnapshotLoginSessionError`, then written as `FAILED_LOGIN_SESSION`.
- `positions_safe_diagnosis.json` is written only after successful login/session and cash/margin positions fetch. Therefore its absence is expected when login/session acquisition fails.

Classification:

- Not currently evidenced as file/path/secret missing.
- Not evidenced as demo/prod URL mismatch.
- Best current classification: **Tachibana demo login/session transport failure or unreachable login endpoint**.
- Diagnostic gap remains: `BrokerTransportError` is safe but coarse; artifact does not preserve safe transport subtype such as timeout vs URL/open failure.

Recent Submit success:

- Current `.runtime/operations/submitted_orders/` has no submitted_orders files after resets, so current artifact state cannot independently confirm prior Submit success.
- Existing phase reports state that 2026-07-03 morning Submit had 5 submitted orders, but this audit did not rely on a current submitted_orders artifact.

## Market / Feature MARKET_DATA_NOT_YET_AVAILABLE

Top-level artifact:

- `market_refresh_manifest.status=BLOCK`
- `feature_refresh_manifest.status=BLOCK`
- `feature_freshness_status=MARKET_DATA_NOT_YET_AVAILABLE`
- `candidate_feature_path=""`
- `candidate_features.parquet` under `.runtime/operations/feature_artifacts` does not exist.
- Daily Plan status: `BLOCK`
- `feature_buy_adapter.status=NO_FEATURE_ARTIFACT`
- `feature_buy_adapter.reason=candidate_feature_path_missing`
- pending promotion: `SKIPPED`, `blocked_reason=order_plan_status_block`

Market detail:

- `market_data_refresh_detail.status=API_PARAM_ERROR`
- `from_date=2026-02-16`
- `to_date=2026-07-06`
- `fetch_mode=per-date`
- `allow_api_fetch=true`
- `jquants_api_fetch_executed=true`
- `latest_successful_daily_quotes_date=""`
- `latest_normalized_daily_quotes_date=""`
- `latest_listed_info_date=""`
- `latest_trading_calendar_date=""`
- `data_until=""`
- `not_yet_available_dates=["2026-07-06"]`
- `failed_dates` includes every business date from 2026-02-16 through 2026-07-03 as `JQuantsClientError`.
- endpoint summaries for daily_quotes, listed_info, trading_calendar are all `FAILED`.
- blocked reasons: `api_fetch_failed:JQuantsClientError`, `missing_daily_quotes`, `missing_listed_info`.

Log evidence:

- `.runtime/logs/jquants_client.log` shows repeated:
  - endpoint `/v2/equities/bars/daily`
  - status `url_error`
  - pagination failed with `pages_fetched=0`
- It also shows `/v2/equities/master` status `url_error`.

J-Quants config presence:

- `.env` contains `JQUANTS_API_KEY`, `JQUANTS_BASE_URL`, `JQUANTS_RATE_LIMIT_PER_MINUTE`, and `JQUANTS_TIMEOUT_SECONDS` keys.
- Settings loader reports API key present, base URL present, timeout 30 seconds, rate limit 60/min.
- Secret value was not printed.

Code basis:

- `run_operations_market_refresh()` defaults `from_date` to `trade_date - 140 days`; for 2026-07-06 that is 2026-02-16.
- It writes Operations-specific data under `.runtime/operations/jquants/...`, not the older `.runtime/data/...` paths.
- `run_market_data_refresh(..., fetch_mode="per-date")` fetches daily quotes for each business date in the date range.
- Per-date fetch marks target date failures as `not_yet_available` only for the `to_date`. Earlier failures become `failed_dates`.
- `_refresh_status()` returns `API_PARAM_ERROR` when failed dates are all `JQuantsClientError`.
- `run_feature_refresh()` then fails because normalized daily quotes and listed info paths under `.runtime/operations` do not exist.
- Daily Plan fails closed because `_validate_market_refresh_gate()` sees market / feature refresh not PASS and feature candidates missing.

Classification:

- The 2026-07-06 date may indeed be too early for same-day market data depending on distribution timing.
- However, this run is **not explainable by same-day market data availability alone** because historical dates 2026-02-16 through 2026-07-03 also failed.
- Best current classification: **J-Quants connectivity/base URL/API reachability problem plus empty Operations-root market data**, with 2026-07-06 same-day availability as a secondary condition.

## Was Monday Morning Market Refresh Appropriate?

For pending_order_plan full rehearsal, running `run_market_refresh` / `run_daily_plan` on 2026-07-06 morning was not the normal production-equivalent path if the intent was Monday morning Submit.

Normal pending flow should be:

- prior market close / evening: Market Refresh
- prior market close / evening: Daily Plan
- prior market close / evening: Approval
- next session morning: Submit from already-approved `pending_order_plan`

Running Monday morning `run_market_refresh` with `trade_date=2026-07-06` tries to build a same-day 2026-07-06 decision set, and with `from_date` default it may fetch a long range. If 2026-07-06 data is not yet distributed, same-day refresh cannot produce a clean `FEATURE_READY` candidate artifact.

For a manual rehearsal of Phase A/B/C, there are two safe routes:

1. Use an already prepared pending plan whose `intended_submit_date` is the actual submit run date.
2. Run the plan-generation part after market data is available, then submit only when the pending dates and approval linkage match.

Do not weaken pending guards to force Submit.

## Next Full Rehearsal Conditions

Do not run Demo Submit until all conditions are true:

- Broker ReadOnly / Preflight reaches `PASS` or an explicitly accepted `PASS_WITH_WARNINGS` with snapshot written.
- `broker_readonly_snapshot_report.json` has no `FAILED_LOGIN_SESSION`.
- `positions_safe_diagnosis.json` is generated if positions fetch reaches that stage.
- Market Refresh is `PASS`.
- Feature Refresh is `PASS`.
- `candidate_features.parquet` exists and `candidate_feature_path` is non-empty.
- Daily Plan is `PASS`.
- `order_plan_generation_executed=true`.
- `pending_order_plan/pending_order_plan.json` exists.
- pending state is `APPROVED`.
- pending `intended_submit_date == submit_run_date`.
- pending `target_session_date == submit_run_date`.
- pending approval hash matches the approval artifact.
- pending source order_plan hash matches the dated order_plan artifact.
- `submit_constraints.allow_dated_order_plan_fallback=false`.

## Fix Now Or Wait?

Broker ReadOnly:

- Do not treat as simple wait-only yet.
- Config and local files look present, so a code/config mismatch is not proven.
- Because the safe error is only `BrokerTransportError`, a small diagnostic improvement may be warranted later to distinguish timeout, URL error, DNS, TLS, HTTP status, or broker maintenance without storing raw response or secrets.
- For immediate operations, retrying read-only later is reasonable, but repeated login attempts should stay bounded.

Market / Feature:

- Not wait-only.
- The 2026-07-06 same-day quote may be unavailable in the morning, but all prior business dates also failed with `url_error`.
- Re-running at a later time may fix the same-day availability part, but it will not fix URL/env/connectivity problems if they persist.
- The Operations root has no usable J-Quants raw/normalized history. Either refresh connectivity must be restored, or an approved Operations-runtime market data preparation path must populate `.runtime/operations/jquants/...`.

Operational timing:

- Morning `market_refresh` / `daily_plan` is not the correct path for Monday morning Submit.
- For production-equivalent pending flow, generate and approve pending after market close, then morning Submit consumes pending.
- Next retry for market refresh should be after J-Quants data availability for the target session is expected, preferably evening JST after market data distribution, not before morning Submit.

## Minimum Next Actions

1. Retry Broker ReadOnly once later with the existing bounded retry policy; if still `FAILED_LOGIN_SESSION`, add safe transport subtype diagnosis before further operational attempts.
2. Verify J-Quants base URL/connectivity outside full refresh with a small read-only smoke or existing diagnostic command, without storing raw response or secrets.
3. Avoid 140-day full fetch during rehearsal until connectivity is confirmed; use an approved narrow Operations Runtime refresh path or provide `--from-date` intentionally.
4. Run Market Refresh after data distribution, not during morning Submit window.
5. Proceed to Daily Plan / Approval / Pending only after candidate feature artifact exists.
6. Run Demo Submit only when pending precheck passes; do not use dated order_plan fallback.

## Prohibited Actions Confirmation

This audit did not:

- change implementation
- run Submit
- place Broker orders
- connect to Production
- submit Production orders
- delete artifacts
- send notifications
- retrain AI
- run a full backtest
- print secrets or raw request/response payloads

