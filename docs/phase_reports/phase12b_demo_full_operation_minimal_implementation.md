# Phase12-B Demo Full Operation Minimal Implementation

作成日: 2026-06-29

## Status

```text
PHASE12B_DEMO_FULL_OPERATION_MINIMAL_IMPLEMENTATION_COMPLETE
DEMO_OPERATION_CLI_READY
DEMO_ORDER_SEND_NOT_EXECUTED_BY_CODEX
PRODUCTION_ORDER_EXECUTION_REMAINS_BLOCKED
LINE_SEND_NOT_EXECUTED
AI_RETRAINING_NOT_EXECUTED
```

## Scope

Phase12-A設計に基づき、Demo Full OperationをMacから手動またはlaunchdで開始するための最小実装一式を追加した。

重要な制約:

- 既存の Tachibana request/client 層は read-only CLMID allowlist を前提にしている。
- 既存の Phase10 demo order foundation も `CLMKabuNewOrder` の本送信は未実装である。
- そのため Phase12-B の `run_phase12_demo_submit.py` は、Demo注文の送信前 guard / approval / MAX_EXPOSURE / artifact 保存までを実装し、実Broker wire callは安全スタブのまま維持した。
- 実Demo注文の本送信を有効化するには、次フェーズで CLMKabuNewOrder 専用allowlist、第二暗証番号注入境界、redacted response normalizer、transport実行テストを別レビューで開く必要がある。

実装した流れ:

```text
Preflight
Daily Plan
Approval Prepare
Demo Submit
Fill Monitor
Reconcile
Daily Report
Audit
```

## Implemented Components

- `src/ai_fund_lab_v2/phase12/`
  - Phase12 artifact IO
  - Demo environment guard
  - MAX_EXPOSURE adapter
  - AI feature contamination audit
  - Approval artifact generation
  - Demo submit guard
  - Fill monitor orchestration
  - Reconciliation
  - Audit aggregation
- `scripts/run_phase12_preflight.py`
- `scripts/run_phase12_daily_plan.py`
- `scripts/run_phase12_approval_prepare.py`
- `scripts/run_phase12_demo_submit.py`
- `scripts/run_phase12_fill_monitor.py`
- `scripts/run_phase12_reconcile.py`
- `scripts/run_phase12_daily_report.py`
- `scripts/run_phase12_audit.py`
- `tools/launchd/com.aifundlab.phase12.*.plist`
- `tests/phase12/`

## Safety Decisions

- `--env demo` 以外は fail closed。
- Production注文は常に禁止。
- Production unlockは実装しない。
- 信用取引は `CASH_EQUITY` guard で拒否。
- LINE実送信は実装しない。
- AI再学習とBacktest再実行は実装しない。
- raw broker responseとsecret平文はartifactへ保存しない。
- Demo submit CLIは、明示承認とSafety/Exposure guardを通った場合でも、現時点では安全なdry-run/stub pathとして保存する。
- Codex実行中にDemo注文送信は行っていない。

## MAX_EXPOSURE

Phase11仕様をPhase12へ接続した。

```text
max_total_exposure_ratio = 0.85
base_equity = broker_actual_equity if available else buying_power else fail closed
```

BUY:

```text
projected_exposure > base_equity * 0.85
```

なら `BLOCK / MAX_EXPOSURE_EXCEEDED`。

SELL / exposure reducing order は MAX_EXPOSURE では止めない。

## Validation

```text
PYTHONPATH=src python3 -m pytest tests/phase12 -q
10 passed
```

```text
PYTHONPYCACHEPREFIX=/private/tmp/phase12_pycache python3 -m py_compile ...
PASS
```

CLI smokeは `/private/tmp/phase12_cli_check2` をrootにして実行した。

- `run_phase12_preflight.py`: `REVIEW_REQUIRED`。理由は一時環境でrequired env varsが未設定のため。secret値は出力していない。
- `run_phase12_daily_plan.py`: `PASS`
- `run_phase12_approval_prepare.py`: `PASS`
- `run_phase12_demo_submit.py`: `PASS`
- `run_phase12_fill_monitor.py`: `PASS`
- `run_phase12_daily_report.py`: `PASS`
- `run_phase12_reconcile.py`: `PASS`
- `run_phase12_audit.py`: `PASS`

## Forbidden Actions Confirmation

- demo_order_executed_by_codex: false
- production_order_executed: false
- production_unlock_executed: false
- margin_trading_executed: false
- line_send_executed: false
- auto_recovery_executed: false
- unconditional_auto_sell_executed: false
- ai_retraining_executed: false
- one_year_backtest_rerun: false
- five_year_backtest_rerun: false
- raw_response_saved: false
- plaintext_secret_saved: false

## Remaining Implementation Gap

```text
DEMO_ORDER_WIRE_EXECUTION_REMAINS_STUBBED
```

Phase12-Bで追加したのは、Demo注文送信前の運用線とguardである。実際の `CLMKabuNewOrder` transport execution は未解禁であり、Production禁止・raw response禁止・secret redactionを維持するため、別設計レビュー後に実装する。

## Manual Operation Commands

```bash
python3 scripts/run_phase12_preflight.py --env demo --trade-date YYYY-MM-DD
python3 scripts/run_phase12_daily_plan.py --env demo --trade-date YYYY-MM-DD
python3 scripts/run_phase12_approval_prepare.py --env demo --trade-date YYYY-MM-DD
python3 scripts/run_phase12_approval_prepare.py --env demo --trade-date YYYY-MM-DD --approve --approver-label operator --max-notional 100000
python3 scripts/run_phase12_demo_submit.py --env demo --trade-date YYYY-MM-DD
python3 scripts/run_phase12_fill_monitor.py --env demo --trade-date YYYY-MM-DD
python3 scripts/run_phase12_daily_report.py --env demo --trade-date YYYY-MM-DD
python3 scripts/run_phase12_reconcile.py --env demo --trade-date YYYY-MM-DD
python3 scripts/run_phase12_audit.py --env demo
```
