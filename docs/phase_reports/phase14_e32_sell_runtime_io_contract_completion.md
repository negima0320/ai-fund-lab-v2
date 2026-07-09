# Phase14-E32 Runtime v2 SELL Daily Operation IO Contract Completion

## Summary

Phase14-E32では、手動SELLではなく、日次Runtime v2のSELL FlowをInput / Output / Consumer単位で完成させた。

BUY Flowで発生した未接続問題を繰り返さないため、SELL Planning、Pending、Submit、Execution-equivalent、Ledger、Current SoT、Report、Notification Payloadまでを同一のRuntime v2通常pipeline上で検証した。

実Broker Submit、Production注文、Notification実送信、launchd変更は行っていない。

Final judgment: **PHASE14E32_SELL_RUNTIME_FLOW_COMPLETE**

## Implemented Scope

- Current Positionを唯一のSELL sourceとするSELL Planning pipelineを追加
- PlannerにSELL数量guardを追加
- Submit pipelineでSELL preflightにCurrent Position quantityを渡すよう修正
- SELL full-fill / full-exitでもexecution-equivalent recordを生成可能に修正
- Runtime-owned Asset ProjectionをBUY/SELL execution cash effectでCurrentへ投影可能に修正
- Report / Public Report / Notification summaryにBUY/SELL side別countを追加
- SELL IO contract testを追加

## Sell Flow Matrix

| Flow | Purpose | Input | Output | Consumer | Owner | PASS | REVIEW_REQUIRED / BLOCK |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Current Position | SELL可能銘柄の唯一source | `.runtime/persistent_ledger/state.json` | active current positions | SELL Candidate Selection | Asset Projection | quantity > 0 position exists | no current position |
| SELL Candidate Selection | 売却候補をCurrentから選ぶ | Current positions + Exit decisions | SELL AI signals | Capital Allocation | SELL Planning pipeline | symbol exists in Current | BUY candidate mixed into SELL / no current match |
| Exit AI | Exit判断をSELL signal化 | exit decisions | `AIPlanningSignal(side=SELL)` | Planner | Exit AI boundary | explicit SELL signal | missing/ambiguous exit signal |
| Capital Allocation | 売却数量と評価額を決める | Current valuation + SELL quantity | `CapitalAllocationSignal(side=SELL)` | Planner | SELL Planning pipeline | quantity * current price | price missing / quantity missing |
| SELL OrderPlan | SELL計画を作る | AI / Allocation / Safety / Current | `OrderPlanItem(side=SELL)` | Approval / Pending | Planner | quantity <= Current position | quantity exceeds Current position |
| Approval | SELL Pendingを承認する | OrderPlan | Approval artifact | Pending | Approval policy | approved item ids match | approval missing/mismatch |
| Pending | Submit対象Current | OrderPlan + Approval | `pending_order_plan.json` | Submit pipeline | Pending writer | APPROVED SELL item | BUY/SELL混在誤解、stale、consumed |
| Submit | Broker SELL requestへ接続 | Pending SELL + Current quantity | Ledger order + broker result | Execution / Report | Submit pipeline | accepted fake adapter path | oversell / duplicate / non-submit job |
| Broker Accepted | Broker応答分類 | RuntimeV2SubmitResult | order ledger | Execution | Broker adapter boundary | ACCEPTED | REJECTED / UNKNOWN |
| OrderList | 約定状態確認 | Broker ReadOnly snapshot | broker order evidence | Execution-equivalent | Execution readonly | filled / remaining=0 | missing/unfilled/partial unresolved |
| Position | SELL後Position確認 | Broker Position evidence | position ledger | Asset Projection | Execution readonly | decreased or zero | unavailable when required |
| Cash | SELL後資金確認 | Broker Cash evidence | cash ledger | Execution / Reconcile | Execution readonly | cash evidence present | cash evidence missing |
| Execution-equivalent | 詳細APIなしでも約定証跡化 | OrderList + Position/Cash | executions.jsonl | Reconcile / Report / Projection | Execution readonly | SELL execution_equivalent generated | orderlist/cash missing |
| Ledger | append-only history | orders/executions/positions/cash | JSONL records | Current / Report | Ledger writers | side=SELL preserved | missing side/schema |
| Current SoT | SELL後資産状態 | ledger + runtime-owned execution | state.json | Report / Next Planning | Asset Projection | position reduced, cash increased | broker cash copied / missing runtime evidence |
| Public Report | 人間確認 | Current + Ledger summaries | latest/public report | Operator | Report writer | SELL counts and current holdings visible | Today/History混在 |
| Next Planning | 継続運用 | Current SoT | next OrderPlan | Morning/Sell Planning | Planning | sold symbol not treated as held | stale holding/exposure |
| Notification Payload | 通知summary | Report summary | payload-only JSON | Sender/Audit | Notification/report writer | SELL filled count included | sender not connected is NOT_IMPLEMENTED |

## Input / Output Contracts

- SELL source is Current Position only.
- Current Position missing means SELL is not possible.
- SELL quantity must be less than or equal to Current Position quantity.
- SELL Planning does not consume BUY candidates.
- SELL Pending preserves `side=SELL`, `quantity`, `estimated_price`, `estimated_amount`, and price source metadata.
- Submit accepts SELL only from canonical Pending Current.
- Submit preflight reads Current Position quantity before allowing SELL.
- Execution-equivalent is generated from filled OrderList plus Position/Cash evidence.
- Full SELL can result in quantity 0 / no active Current position.
- Current SoT is updated by Runtime-owned Asset Projection only.
- Report and Notification Payload consume Current / Ledger summaries; they do not write Current or act as Submit source.

## Owner Matrix

| Data | Owner |
| --- | --- |
| Current positions / cash | Asset Projection |
| SELL decision | Exit AI boundary |
| SELL quantity guard | Planner + Submit preflight |
| Pending Current | Pending writer |
| Broker request/response boundary | Submit adapter |
| Execution-equivalent | Execution readonly pipeline |
| Ledger append | Ledger writers |
| Public report | Report writer |
| Notification payload | Report/Notification payload builder |

## Consumer Matrix

| Output | Consumers |
| --- | --- |
| SELL OrderPlan | Approval, Pending |
| SELL Pending | Submit pipeline |
| Ledger order | Execution, Report, Reconcile |
| Execution-equivalent | Reconcile, Report, Asset Projection, Notification |
| Current SoT | Report, Next Planning, SELL Planning |
| Public Report | Operator |
| Notification payload | Sender/Audit |

## Verification

- `python3 -m pytest tests/runtime_v2/test_phase14e32_sell_runtime_io_contract.py`
  - 3 passed
- `python3 -m pytest tests/runtime_v2/test_phase14e17_submit_pipeline_connection.py tests/runtime_v2/test_phase14e23_execution_acceptance_policy.py tests/runtime_v2/test_phase14e25_runtime_owned_fill_projection.py tests/runtime_v2/test_phase14e6_runtime_v2_public_report_output.py`
  - 10 passed
- `python3 -m pytest tests/runtime_v2`
  - 332 passed

## Prohibited Actions Check

- Production注文: not executed
- Production Broker API Write: not executed
- Notification実送信: not executed
- launchd変更: not executed
- Phase9 Runtime / Phase9 writer: not used
- Current初期化: not executed
- Demo Broker 2,000万円copy: not performed
- Test-only SELL / recovery-only SELL path: not added

## Known Gaps

- Actual Demo Broker SELL daily run is not executed in E32.
- Exit AI is represented as an explicit Runtime v2 boundary input; production-grade Exit AI logic remains a later AI strategy concern.
- LINE / Discord sender remains send-disabled / payload-only in this phase.

## Final Judgment

**PHASE14E32_SELL_RUNTIME_FLOW_COMPLETE**
