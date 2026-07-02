# Phase12-AS Dynamic Approval Max Notional Fix

## Status

`PHASE12AS_DYNAMIC_APPROVAL_MAX_NOTIONAL_FIX_COMPLETE`

Phase12 Demo Auto Approval の暫定固定値 `600000` を通常運用パスから外し、Production-equivalent な 85% Exposure Rule に基づく動的計算へ変更した。

Demo追加注文、Production注文、LINE/Discord送信、AI再学習、Backtestは実行していない。

## Fix Summary

Approval Max Notional は以下で計算する。

```text
approval_max_notional =
min(
  equity_basis * max_total_exposure_ratio - current_exposure,
  available_buying_power_or_cash,
  capital_allocation_total_buy_budget if available
)
```

通常運用では `approval_max_notional_source=dynamic_max_exposure` を使う。

`--max-notional` がCLIで明示指定された場合だけ manual override として扱い、artifactに `approval_max_notional_source=manual_override` を残す。

## Demo Equity Basis

Demoでは立花Demo口座の2000万円を評価資金に使わない。

```text
equity_basis=1000000
equity_basis_source=demo_evaluation_equity
max_total_exposure_ratio=0.85
```

current exposure が0円の場合:

```text
approval_max_notional=850000
```

## Current Exposure

current exposure は以下の順に解決する。

```text
1. broker_positions market value
2. Persistent Demo Ledger position exposure
3. submitted accepted BUY exposure
4. 取得不能なら reason付き0 または Fail Closed
```

Persistent Demo Ledger に `net_quantity=0` のDemo Special Fill済みpositionがある場合、現在保有は0円として扱い、過去のaccepted order notionalを単純合算しない。

## Updated Files

- `src/ai_fund_lab_v2/operations/operations.py`
  - Approval Max Notional動的計算を追加
  - Demo評価資金100万円をequity basisとして使用
  - submit側が `approval_max_notional` を使用
  - Persistent Demo Ledgerのnet positionをcurrent exposureへ反映
- `scripts/run_approval_prepare.py`
  - `--max-notional` defaultを廃止し、指定時のみmanual override化
- `scripts/run_demo_daily_operation.py`
  - `--auto-approval-max-notional` defaultを廃止し、指定時のみmanual override化
- `tools/launchd/com.aifundlab.operations.auto_approval.plist`
  - `--max-notional 600000` を削除
- `docs/operations/demo_daily_operation_runbook.md`
  - Dynamic Approval Max Notionalと再登録手順を明記
- `tests/phase12/test_phase12_approval.py`
  - Demo 100万円 -> 850000、current exposure反映、manual override、launchd固定値除去を追加
- `tests/phase12/test_phase12_demo_submit_guard.py`
  - 2026-07-02相当5候補が850000予算では全件Approval予算内になることを追加

## 2026-07-02 Case

想定notional:

```text
4265  45,600
4179  60,000
2962 199,000
2393 429,500
6166  76,600
```

```text
first_three_notional=304600
with_2393=734100
with_6166=810700
approval_max_notional=850000
```

したがって、Approval予算上は5件すべて通る。

ただし、Phase12-ASでは追加注文は禁止のため、2393の追加発注はしていない。2026-07-02の既存submitted_ordersは4件accepted、1件blockedの履歴として維持した。

## Runtime Re-evaluation

2026-07-01 Approval artifactを再評価した。

```text
status=APPROVED
approval_max_notional=850000
approval_max_notional_source=dynamic_max_exposure
equity_basis=1000000
equity_basis_source=demo_evaluation_equity
current_exposure=0
current_exposure_source=persistent_demo_ledger
approved_item_count=5
```

2026-07-02 Reconcileは追加注文なしで再評価し、`PASS_WITH_BLOCKED_ITEMS` を維持した。

Operation Auditは `PASS`。

Daily Reportは2026-07-02分を再生成した。

## launchd

`com.aifundlab.operations.auto_approval.plist` から `--max-notional 600000` を削除した。

launchctl操作は禁止のため実行していない。

再登録する場合は、ユーザー側でplist確認後に以下を実行する。

```bash
cp tools/launchd/com.aifundlab.operations.auto_approval.plist ~/Library/LaunchAgents/
launchctl bootout gui/$(id -u) ~/Library/LaunchAgents/com.aifundlab.operations.auto_approval.plist 2>/dev/null || true
launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/com.aifundlab.operations.auto_approval.plist
```

## Tests

```text
python3 -m py_compile src/ai_fund_lab_v2/operations/operations.py scripts/run_approval_prepare.py scripts/run_demo_daily_operation.py
PASS

python3 -m pytest tests/phase12/test_phase12_approval.py tests/phase12/test_phase12_demo_submit_guard.py -q
19 passed

python3 -m pytest tests/phase12 -q
97 passed
```

通常運用対象ファイルから `600000` 固定値が残っていないことも確認した。

## Safety Notes

- Demo追加注文は実行していない
- Production注文は実行していない
- Production Unlockは実行していない
- LINE/Discord送信は実行していない
- AI再学習は実行していない
- Backtestは実行していない
- raw request / raw response / secretは保存していない
- Phase9は変更していない
