# Phase14-E12 Day1 Demo Operation Start Readiness Audit

作成日: 2026-07-07

## 最終判定

**PHASE14E12_READY_WITH_MANUAL_CHECK**

## 目的

2026-07-08からRuntime v2 Demo運用テストを開始できるか、launchd登録前/運用前の最終監査を実施した。

今回実施したのは確認のみである。
Submit、Broker API Write、Production注文、Notification実送信、launchd bootstrap/load、Current SoT変更は行っていない。

## Overall Readiness

**YELLOW**

理由:

- Runtime v2 Current SoTは100万円・保有0で整っている。
- 4つのlaunchd plistは存在し、構文PASS、Runtime v2正規CLIのみを呼ぶ。
- Demo Broker Capabilityはmodeから自動解決され、Demo cash 2,000万円をCurrent SoTにしない設計が確認できる。
- 9000番台はDemo Submit guardでBLOCKされる。
- ただし4つのlaunchd Jobは未登録である。
- さらに現行plistは全Job `--submit-enabled false` であり、Day1を注文ありで実施する場合はsubmit jobだけを明示的に有効化する判断と再確認が必要である。
- Planning側にはCapability filter用helperがあるが、正規Morning Jobで9000番台候補を次点繰り上げまで完全接続していることは、登録前の手動確認項目として残す。

## 1. launchd plist Audit

対象:

- `tools/launchd/com.aifundlab.runtime_v2.morning.plist`
- `tools/launchd/com.aifundlab.runtime_v2.submit.plist`
- `tools/launchd/com.aifundlab.runtime_v2.execution.plist`
- `tools/launchd/com.aifundlab.runtime_v2.market_refresh.plist`

確認結果:

| Job | Label | Schedule | CLI | Mode | Submit | Notification | Result |
| --- | --- | --- | --- | --- | --- | --- | --- |
| morning | `com.aifundlab.runtime_v2.morning` | Mon-Fri 08:45 | Runtime v2正規CLI | demo | false | payload-only | PASS |
| submit | `com.aifundlab.runtime_v2.submit` | Mon-Fri 08:58 | Runtime v2正規CLI | demo | false | payload-only | PASS with manual submit check |
| execution | `com.aifundlab.runtime_v2.execution` | Mon-Fri 09:05 | Runtime v2正規CLI | demo | false | payload-only | PASS |
| market_refresh | `com.aifundlab.runtime_v2.market_refresh` | Mon-Fri 15:30 | Runtime v2正規CLI | demo | false | payload-only | PASS |

plist構文:

- `python3 -m plistlib ...` で4 plistすべてPASS。

禁止entry確認:

- Phase9 Runtime: 未使用
- Phase9 writer: 未使用
- `run_phase14d` script: 未使用
- `.runtime/demo` Current path: 未使用

stdout/stderr:

- 各plistに `StandardOutPath` / `StandardErrorPath` あり。

launchd登録状態:

| Job | Registered |
| --- | --- |
| morning | false |
| submit | false |
| execution | false |
| market_refresh | false |

登録状態確認は `launchctl print gui/<uid>/<label>` の読み取りのみで実施した。
bootstrap/loadは実行していない。

## 2. Current SoT Audit

対象:

- `.runtime/persistent_ledger/state.json`

確認結果:

| Field | Expected | Actual | Result |
| --- | --- | --- | --- |
| cash | 1,000,000 | 1,000,000 | PASS |
| buying_power | 1,000,000 | 1,000,000 | PASS |
| market_value | 0 | 0 | PASS |
| total_equity | 1,000,000 | 1,000,000 | PASS |
| positions | [] | [] | PASS |
| source | `phase14e8_demo_operation_initial_state` | `phase14e8_demo_operation_initial_state` | PASS |
| environment | demo | demo | PASS |
| review_required | false | false | PASS |

D15/D22由来の汚染確認:

- `19999648`
- `23297648`
- `phase14d15_orderlist_position_cash_reflection`
- `6501`
- `6502`
- `9984`
- `9001`
- `9432`

上記はCurrent SoTおよびPublic Reportには検出されなかった。

## 3. Pending / Runtime State Audit

Pending:

- Path: `.runtime/pending_order_plan/pending_order_plan.json`
- State: `CONSUMED`
- Consumed: true
- Pending plan: Phase14-D15 SELL 7203由来
- Approval expires at: 2026-07-07T06:13:32.711954+00:00
- submitted/post_send_unknown/monitoring_fill: 残存なし

判定:

- `CONSUMED` であるため、Pending lifecycle guardが守られる限り明日そのままSubmit対象にはならない。
- ただしcanonical pending pathにD15由来の消費済みSELL planが残っているため、Day1で注文を有効化する場合は、Morning Jobで新しいPendingが生成されていること、またはSubmit前に手動でPending内容を確認することが必要。

Runtime State:

- Path: `.runtime/runtime_state/current_state.json`
- State: `CURRENT_STATE_LOADED`
- REVIEW_REQUIRED: 該当なし
- BLOCKED: 該当なし
- HALT: 該当なし

## 4. Demo Broker Capability Audit

確認対象:

- `src/ai_fund_lab_v2/runtime_v2/broker_adapter/capability.py`
- `tests/runtime_v2/test_phase14e8_demo_broker_capability_evaluation_capital_fix.py`

Demo capability:

```text
supports_daily_reset = true
cash_as_truth = false
buying_power_as_truth = false
positions_as_truth = false
executions_as_truth = true
order_status_as_truth = true
supports_9000_series_orders = false
default_evaluation_capital = 1000000
broker_cash_is_evidence_only = true
broker_positions_are_evidence_only_after_reset = true
```

Production capability:

```text
supports_daily_reset = false
cash_as_truth = true
buying_power_as_truth = true
positions_as_truth = true
executions_as_truth = true
order_status_as_truth = true
supports_9000_series_orders = true
default_evaluation_capital = null
broker_cash_is_evidence_only = false
broker_positions_are_evidence_only_after_reset = false
```

確認結果:

- mode=demoで自動解決: PASS
- mode=productionで自動解決: PASS
- unknown mode fail closed: PASS
- Demo cash 2,000万円をRuntime Current SoTへコピーしない: PASS
- Demo positions resetでCurrent positionsを自動消去しない: PASS
- Demoでは9000番台Submit候補をBLOCK: PASS
- Productionでは9000番台除外しない: PASS

## 5. Day1 Order Readiness

確認結果:

- Runtime評価資金100万円基準: PASS
- Broker Demo cash 2,000万円基準ではない: PASS
- Submitは`submit` Jobのみに隔離: PASS
- Production注文は禁止: PASS
- Current SoTは100万円・保有0: PASS
- 9000番台はDemo Submit guardでBLOCK: PASS

Manual check:

- 現行plistは `submit` Jobも `--submit-enabled false` である。
- Day1で実注文Demo Submitを許可する場合は、submit jobのみを対象に、別途 `--submit-enabled true` と安全guardの再確認が必要。
- Planningで9000番台候補が出た場合に、Morning Jobの正規経路でCapability filterにより除外され、次点繰り上げまたはBUYなしになることをSubmit有効化前に確認する。
- 全候補が9000番台の場合はBUYなしにする。

## 6. Public Report Audit

対象:

- `reports/public/runtime_v2/latest.md`

確認結果:

- Cash: JPY 1,000,000
- Buying power: JPY 1,000,000
- Market value: JPY 0
- Total equity: JPY 1,000,000
- Holdings: No active positions
- BUY orders: 0
- SELL orders: 0
- Reconcile: PASS
- Audit: PASS
- Notification: payload summary only

Public Reportは100万円・保有0を示している。

## Verification

実行した確認:

```text
python3 -m plistlib tools/launchd/com.aifundlab.runtime_v2.morning.plist tools/launchd/com.aifundlab.runtime_v2.submit.plist tools/launchd/com.aifundlab.runtime_v2.execution.plist tools/launchd/com.aifundlab.runtime_v2.market_refresh.plist
PASS

python3 -m pytest tests/runtime_v2/test_phase14e8_demo_broker_capability_evaluation_capital_fix.py tests/runtime_v2/test_phase14e11_daily_operation_scheduler.py
12 passed

python3 -m pytest tests/runtime_v2/test_phase14e11_daily_operation_scheduler.py
3 passed
```

## Blocker List

Technical blockers:

- None for no-submit Day1 launchd rehearsal.

Operational blockers before automatic launchd start:

- 4つのlaunchd Jobが未登録。

Operational blockers before Demo Submit:

- submit jobの `--submit-enabled false` を維持する限り注文は出ない。
- Demo SubmitをDay1に実行するなら、submit jobのみを有効化し、Production endpoint block、approval、pending-only、duplicate、9000番台BLOCKを再確認する必要がある。
- D15由来のCONSUMED Pendingが残っているため、Day1のSubmit前に新しいPendingが生成済みであることを確認する。

## Manual Check List

Day1開始前:

- 4 plistをlaunchdへ登録するか決める。
- 登録後に `launchctl print gui/<uid>/<label>` で4 Jobを確認する。
- stdout/stderr log pathが書き込み可能であることを確認する。
- `reports/public/runtime_v2/latest.md` が100万円・保有0を表示していることを再確認する。

Demo Submitを有効化する前:

- submit job以外は `--submit-enabled false` のままにする。
- submit jobのみを対象に有効化する。
- Morning Jobが作った当日Pendingを確認する。
- PendingがAPPROVEDであることを確認する。
- 9000番台が含まれていないことを確認する。
- 全候補が9000番台ならBUYなしにする。
- Production endpoint / production credentialへ到達しないことを確認する。

## Install or Hold Recommendation

Recommendation:

- **Install for no-submit Demo operation rehearsal: OK after manual launchd registration.**
- **Hold for live Demo Submit until submit job enablement and Day1 Pending are manually confirmed.**

登録前判断:

- plist・Current SoT・Capability・Public Reportは登録可能な状態。
- ただし現時点では未登録なので、2026-07-08朝の自動起動には登録作業が必要。

登録後判断:

- 登録後に4 Jobがlaunchctlで見えること、08:45 Morning Jobがmanifest/logを出すことを確認できれば、no-submit Demo operation rehearsalを開始可能。
- Demo Submitは、submit jobのみを明示的に有効化し、当日Pendingと9000番台除外を確認してから許可する。

## Acceptance Criteria

| Criteria | Result |
| --- | --- |
| 4 plistの時刻・引数が確認されている | PASS |
| Current SoTが100万円・保有0 | PASS |
| Demo特例が確認されている | PASS |
| 9000番台Demo除外が確認されている | PASS |
| 明日注文を投げる前提が危険でない | PASS with manual submit check |
| launchd登録前/登録後の判断が明記されている | PASS |
| Submitしていない | PASS |
| Broker API Writeしていない | PASS |
| launchd bootstrap/loadしていない | PASS |
| Current SoTを変更していない | PASS |

