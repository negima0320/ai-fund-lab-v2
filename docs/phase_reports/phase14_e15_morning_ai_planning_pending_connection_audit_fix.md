# Phase14-E15 Morning AI / Planning / Pending Connection Audit & Fix

作成日: 2026-07-08

## 最終判定

**PHASE14E15_MORNING_PIPELINE_CONNECTED**

## 目的

Day1 Demo運用の08:45 Morning Jobが、CHECKPOINT記録だけで終わらず、AI inference相当 / Planning / Approval / Pending生成まで接続されることを確認し、必要な軽量実装を行った。

今回、Submit、Broker API Write、Production注文、Notification実送信、launchd load/unloadは行っていない。
Asset Current SoTは変更していない。

## Audit Result

E15開始時点の `src/ai_fund_lab_v2/runtime_v2/cli/run_daily_operation.py` では、Morning JobのAI / Planning / Approval / Pendingは以下のようなCHECKPOINT記録のみだった。

```text
Morning AI inference checkpoint recorded.
Morning Planning checkpoint recorded.
Morning Approval checkpoint recorded.
Morning Pending generation checkpoint recorded.
```

この状態では08:58 Submit Jobが対象にする当日Pendingが生成されないため、実運用接続としては不足だった。

## Implemented Fix

### 1. Runtime v2 Morning Pipeline追加

追加:

- `src/ai_fund_lab_v2/runtime_v2/planning/morning_pipeline.py`

責務:

- 最新Feature inputを読む
- Candidate / Opportunity / Position / Capital inputの存在を確認する
- Candidate featureから軽量AI inference相当のBUY signalを生成する
- Runtime評価資金100万円を基準にCapital allocationを作る
- Demo Capability filterを適用する
- Demoでは9000番台候補を除外する
- Planning Result / Order Planを生成する
- Approval Artifactを生成する
- ApprovalをPendingへ紐づける
- `.runtime/pending_order_plan/pending_order_plan.json` へCurrent Pendingを書く
- MorningではSubmitしない

### 2. CLI接続

更新:

- `src/ai_fund_lab_v2/runtime_v2/cli/run_daily_operation.py`

追加引数:

- `--feature-root`
- `--feature-date`
- `--max-orders`

接続:

- `--job morning` かつpreflight PASS時のみ `run_morning_ai_planning_pending_pipeline(...)` を実行する。
- manifest stage `morning_ai_planning_pending_pipeline` を追加する。
- Feature不足や全候補除外時は `NO_SIGNAL` としてreasonをmanifestに記録する。

維持:

- `--submit-enabled true` は `--job submit` のみ許可。
- MorningでSubmitは行わない。
- Notificationはpayload-only。
- `.runtime/demo` Current pathは拒否。

### 3. Planner数量算出

更新:

- `src/ai_fund_lab_v2/runtime_v2/planning/planner.py`

変更:

- `CapitalAllocationSignal.cash_required` から概算価格を算出する。
- 100株単位のquantityを算出する。
- これによりOrderPlanItemがquantity > 0を持てる。

## Real Morning Run Result

実行:

```text
PYTHONPATH=src python3 -m ai_fund_lab_v2.runtime_v2.cli.run_daily_operation \
  --mode demo \
  --job morning \
  --business-date 2026-07-08 \
  --feature-date 2026-07-07 \
  --feature-root .runtime/operations/feature_artifacts \
  --submit-enabled false \
  --notification-mode payload-only \
  --stop-on-review-required \
  --stop-on-blocked \
  --runtime-root .runtime \
  --reports-root reports/runtime_v2 \
  --public-reports-root reports/public/runtime_v2 \
  --manifest-root .runtime/runtime_state/run_manifest \
  --log-root .runtime/runtime_state/logs
```

結果:

- exit_code: 0
- manifest: `.runtime/runtime_state/run_manifest/2026-07-08/runtime-v2-morning-2026-07-08-20260707T215640.650840+0000.json`
- Pending state: `APPROVED`
- Pending target_session_date: `2026-07-08`
- Pending items: 5
- Approval linked: yes
- Estimated total amount: 500,000
- Runtime evaluation capital: 1,000,000
- 9000番台Pending: none
- Submit executed: false
- Broker API Write: false
- Notification sent: false

Generated Pending:

```text
65220 BUY 100 amount=100,000
78780 BUY 100 amount=100,000
68970 BUY 100 amount=100,000
63270 BUY 100 amount=100,000
45910 BUY 100 amount=100,000
```

Approval:

- `.runtime/runtime_state/morning_pipeline/2026-07-08/approval_artifact.json`
- status: `APPROVED`
- approved_item_ids: 5

Order Plan:

- `.runtime/runtime_state/morning_pipeline/2026-07-08/order_plan.json`
- status: `CREATED`
- target_session_date: `2026-07-08`

## Current SoT Safety

Asset Current SoT:

- Path: `.runtime/persistent_ledger/state.json`
- cash: 1,000,000
- buying_power: 1,000,000
- market_value: 0
- total_equity: 1,000,000
- positions: []
- source: `phase14e8_demo_operation_initial_state`
- review_required: false

Asset Current SoTは変更していない。
E15で更新したCurrentはPendingのみである。

## Demo Capability

確認:

- Demo capabilityはmode=demoから自動解決。
- `supports_9000_series_orders = false`
- Submit前にも `run_submit_preflight` で9000番台がBLOCKされる。
- E15 testでは9432を含むfixtureで9000番台除外を確認済み。
- Production capabilityでは9000番台除外しない設計を維持。

## NO_SIGNAL Behavior

Feature inputが存在しない場合、候補が空の場合、または全候補がDemo Capabilityで除外された場合は、Morning JobはSubmit可能なPendingを作らず、manifestへNO_SIGNAL reasonを記録する。

確認済みreason:

- `NO_SIGNAL:demo_capability_filtered_all_9000_series`

この場合:

- Pending state: `PENDING_APPROVAL`
- items: []
- approval: null
- Submit対象なし

## Tests

追加:

- `tests/runtime_v2/test_phase14e15_morning_ai_planning_pending_connection.py`

実行結果:

```text
python3 -m pytest tests/runtime_v2/test_phase14e15_morning_ai_planning_pending_connection.py
2 passed

python3 -m pytest tests/runtime_v2
314 passed
```

## Important Operational Note

通常シェルで以下を実行した場合、src-layoutのimport pathが通らず失敗した。

```text
python3 -m ai_fund_lab_v2.runtime_v2.cli.run_daily_operation ...
ModuleNotFoundError: No module named 'ai_fund_lab_v2'
```

`PYTHONPATH=src` を付けるとMorning Jobは正常実行できた。
これはMorning pipeline自体の接続問題ではないが、launchd登録前にPython import pathまたはpackage install状態を確認する必要がある。
E15ではlaunchd変更は禁止のため、plist変更は行っていない。

## Acceptance

| Criteria | Result |
| --- | --- |
| run_daily_operation.py の morning job がCHECKPOINTだけで終わらない | PASS |
| Morning実行テストでPending itemsが生成される、またはNO_SIGNAL理由が明確 | PASS |
| Pending生成時にapprovalが紐づく | PASS |
| Pending target_session_date が 2026-07-08 | PASS |
| Demo 9000番台除外が効く | PASS |
| Runtime資金100万円基準 | PASS |
| submit job以外では submit-enabled=true を拒否 | PASS |
| tests/runtime_v2 PASS | PASS |

