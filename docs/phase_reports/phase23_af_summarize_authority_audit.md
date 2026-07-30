# Phase23-AF Summarize Authority Audit

## Judgment

`PHASE23_AF_REPAIR_REQUIRED`

## Scope

Evidence Reviewのみ。実装修正、summarize evidence write、Historical Test、Runtime Switch、Broker Write、J-Quants取得、canonical mutation は実施していない。

## 対象Run

`reports/runtime_tests/runs/runtime-test-historical-extended-smoke-20260729T111715014852Z/`

## B-1: 今回RunのBUY / SELL / PM / Positions

Run-scoped evidenceで以下を確認した。

```text
BUY executions = 0
SELL executions = 0
fills = 0
PM decisions = 0
PM REDUCE = 0
PM EXIT = 0
position_campaigns = 0
run-scoped non_executable_sell_decisions = 0
```

代表例として `daily/2026-07-06/position_management/pm_decisions.json` は `decisions=[]`, `pm_decision_count=0`。`execution/fills.json` は `fills=[]`。`positions/position_campaigns.json` は `position_campaigns=[]`。

## B-2: なぜ `.runtime/runtime_state/sell_pipeline/2026-07-06/order_plan.json` が読まれたか

`scripts/runtime_test.py:634-640` で summarize は `final_state_hashes` と current `.runtime` の `state_hashes()` を比較する。

対象runでは current hashes と final_state_hashes が完全一致していた。そのため `runtime_state_available=True` となり、`_collect_order_plan_items(... available=True ...)` が呼ばれる。

`scripts/runtime_test.py:1156-1193` は `available=True` の場合、以下を読む。

```text
.runtime/runtime_state/morning_pipeline/*/order_plan.json
.runtime/runtime_state/sell_pipeline/*/order_plan.json
```

このため `.runtime/runtime_state/sell_pipeline/2026-07-06/order_plan.json` が読まれた。

## B-3: Run-scoped authority / Current runtime authority のどちらがContractか

運用ガイド上、summarizeは「Run-scoped post-run summary」であり、source authorityは `reports/runtime_tests/runs/<run_id>/` と `final-state hash match for current root reads` とされている。

したがって、current runtime参照は「final hash matchがある場合の補助的Contract」として存在する。ただし、run-scoped evidenceが存在する項目に current runtime artifact を混ぜて lifecycle判定を変えることは、Run-scoped summaryの意図と衝突する。

## B-4: Current runtime参照はContract通りか

参照開始条件そのものはContract通り。対象runでは final hash match が成立している。

ただし、参照した current runtime sell artifact の採用範囲がContract違反。今回runの run-scoped PM / fills / positions が全て0であるにもかかわらず、current runtime の `non_executable_sell_decisions` が lifecycle reduce_exit に混入した。

## B-5: Contract違反のRoot Cause

`scripts/runtime_test.py:1194-1203` は run-scoped `sell_planning_manifest` を見て、PM decision / reduce / exit が0件なら同日付の `result["sell"]` を除去する。

しかし、同じcurrent runtime artifactから読んだ `result["non_executable_sell_decisions"]` は除去していない。

`.runtime/runtime_state/sell_pipeline/2026-07-06/order_plan.json` には以下が存在する。

```text
status = NO_ACTION
reason = REDUCE_BELOW_MINIMUM_TRADABLE_QUANTITY
items = []
non_executable_sell_decisions = 1
source_decision = REDUCE
symbol = 43780
source_decision_id = pm-2026-07-06-43780-reduce
```

その結果、`_summarize_lifecycle()` は PM REDUCE 0件に対して non-executable REDUCE terminal 1件を受け取り、`PM_REDUCE_TO_PARTIAL_SELL_PLAN` を REVIEW_REQUIRED にした。

## Root Cause

`SUMMARIZE_CURRENT_RUNTIME_NON_EXECUTABLE_SELL_DECISION_LEAKS_INTO_RUN_SCOPED_LIFECYCLE`

## 修正要否

修正必要。Phase23-AGで、summarizeのauthority selectionをrun-scoped優先にし、current runtime fallbackをfinal hash matchだけでなく run_id / run-scoped absence / artifact class単位で制御する必要がある。

## Phase23-AG 修正提案

1. Plan window request preservation: `requested_business_days` と `resolved_business_days` を分離する。
2. Plan calendar authority composition: Historical source composition後の calendar overlay をplan window authorityにも反映、または truncation reasonをartifact化する。
3. Summarize authority isolation: run-scoped PM/sell evidenceが存在する日付では current runtime sell artifactを採用しない。
4. `non_executable_sell_decisions` も `result["sell"]` と同じ日付・run-scoped zero-PM除去ルールに従わせる。
5. Summary payloadへ order plan authority source matrix を出力する。

