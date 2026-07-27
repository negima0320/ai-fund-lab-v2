# Phase21-A PM ADD / Capital Deployment Execution Gap Investigation

## 1. Executive Summary

Primary Judgment:

```text
PHASE21_A_ADD_EXECUTION_PATH_PARTIALLY_BROKEN
```

Secondary Judgments:

```text
PHASE21_A_ADD_INTENT_CONTRACT_MISMATCH
PHASE21_A_ADD_CONSUMER_MISSING_FOR_BUY_ORDER_CONVERSION
PHASE21_A_BUY_PENDING_OVERWRITTEN_BY_SELL_NO_SIGNAL_PENDING
```

Phase21-A investigated the completed 245BD Historical Run:

```text
runtime-test-historical-extended-smoke-20260726T053732539035Z
```

The observed low BUY execution is not explained by missing BUY eligibility, missing Opportunity edge, Safety block, or Submit preflight rejection. The root cause is a combination of two execution-chain gaps:

1. PM `ADD` is documented and implemented as a candidate signal / PM state, not a direct buy order. No formal PM ADD -> BUY order consumer is present in the current Runtime path.
2. Morning Planning generated BUY pending items on every business day, but on 238 days Sell Planning no-signal wrote an `EMPTY` pending plan into the same authoritative Pending slot before Submit. Submit therefore saw no submitted orders.

This task made no Production, Runtime, Strategy, PM, Capital, Safety, Broker, Training, Calibration, or Accepted Generation code changes. No long-running Historical Run was executed by Codex.

## 2. Observed Facts

Run-scoped evidence:

```text
reports/runtime_tests/runs/runtime-test-historical-extended-smoke-20260726T053732539035Z
```

Final run facts:

| Item | Value | Evidence |
|---|---:|---|
| Runtime Judgment | PASS | `final_summary.json` |
| Business days | 245 | `daily/<DATE>/...` inventory |
| Initial equity | 1,000,000 | user-provided Phase21-A handoff / run summary |
| Final equity | 1,018,520 | user-provided Phase21-A handoff / run summary |
| Return rate | +1.852% | user-provided Phase21-A handoff / run summary |
| BUY fills | 4 | `daily/*/execution/fills.json` |
| SELL fills | 6 | `daily/*/execution/fills.json` |
| Submit days with no submitted orders | 238 | `daily/*/submit/runtime_manifest.json` |

PM decision distribution from run-scoped `pm_decisions.json`:

| PM Decision | Count |
|---|---:|
| HOLD | 32 |
| ADD | 228 |
| REDUCE | 4 |
| EXIT | 3 |

All 228 ADD decisions were for `94320`. ADD reason codes were:

| Reason code | Count |
|---|---:|
| `strong_trend_continuation` | 228 |
| `opportunity_rank_still_high` | 228 |
| `no_loss_averaging` | 228 |

Machine-readable evidence:

```text
reports/phase21_a_pm_add_capital_deployment_execution_gap_investigation/phase21_a_evidence.json
```

## 3. Current ADD Contract

The PM design document defines ADD as:

```text
強い上昇継続
追加購入候補
```

It explicitly states:

```text
ADD は買い増し命令ではない。
ADD は買い増し候補シグナルである。
最終的な購入可否、購入金額、保有上限判定は Capital Allocation Engine が行う。
```

Evidence:

```text
docs/03_ai_design/position_management_ai_design.md:348-365
```

Implementation preserves this as SELL-scope exclusion:

```text
src/ai_fund_lab_v2/runtime_v2/position_management/producer.py:595-597
runtime_action = "NO_SELL_ORDER_ADD_OUT_OF_SELL_SCOPE"
reason += "; ADD is outside SELL Planning scope"
```

The producer summary also records:

```text
src/ai_fund_lab_v2/runtime_v2/position_management/producer.py:1048-1050
add_auto_sell_used = False
add_scope_reason = "ADD is a Position Management AI decision but is outside SELL Planning auto-order scope."
```

Interpretation:

`ADD is outside SELL Planning scope` means ADD is not a SELL order and is not consumed by Sell Planning as an auto-order. It does not prove that a separate BUY-side consumer exists.

Current code review found no formal PM ADD -> BUY order consumer in Morning Planning. `run_morning_ai_planning_pending_pipeline()` accepts `ai_signals` and `buy_ai_context`, but not PM decisions:

```text
src/ai_fund_lab_v2/runtime_v2/planning/morning_pipeline.py:326-328
```

Morning Planning loops over `candidate_rows = ai_signals` and applies price, Opportunity eligibility, listed-issue BUY eligibility, budget, and policy constraints:

```text
src/ai_fund_lab_v2/runtime_v2/planning/morning_pipeline.py:577-623
```

Therefore ADD is currently:

| Question | Finding |
|---|---|
| Formal meaning | Buy-add candidate signal, not a command |
| Has execution quantity? | No |
| Quantity owner | Intended design says Capital Allocation |
| Morning Planning input? | Not as PM ADD; Morning consumes BUY AI / Opportunity `ai_signals` |
| SELL Planning scope? | Explicitly outside |
| Formal ADD -> BUY consumer exists? | Not found |
| Production/Demo/Historical common? | The same Runtime Core code path is shared; impact is not Historical-only |

## 4. End-to-End Trace

### PM

PM generated 228 ADD decisions, all for existing position `94320`.

Representative ADD day:

```text
2022-09-02
PM: ADD 1 / HOLD 3
ADD symbol: 94320
ADD reasons: strong_trend_continuation, opportunity_rank_still_high, no_loss_averaging
Evidence: daily/2022-09-02/position_management/pm_decisions.json
```

### Planning

Morning Planning generated selected BUY items on all 245 days:

```text
morning_pass_days = 245
morning_selected_days = 245
morning_selected_total = 799
```

But these were generated from BUY AI / Opportunity `ai_signals`, not from PM ADD decisions. ADD-derived BUY plan count is therefore:

```text
ADD-derived BUY plan items = 0 confirmed
```

### Pending

On 2022-09-01, there were no current positions. Sell Planning preserved the existing BUY pending:

```text
daily/2022-09-01/sell_planning/pending_continuity_evidence.json
status = NO_POSITION
no_position_preserved_existing_pending = true
pending_path_written_by_sell_planning = false
```

Submit then saw:

```text
pending_classification = VALID
pending_item_count = 4
submitted_count = 4
```

On 238 later days, Sell Planning no-signal wrote an EMPTY pending:

```text
status = NO_SIGNAL
reason = NO_SIGNAL:exit_ai_no_sell_signal
pending_path_written_by_sell_planning = true
```

Submit then saw:

```text
pending_classification = EMPTY
pending_item_count = 0
submitted_count = 0
no_action_reason = NO_SIGNAL:exit_ai_no_sell_signal
```

Code path:

```text
src/ai_fund_lab_v2/runtime_v2/planning/sell_pipeline.py:510-536
```

For no-signal SELL, `_write_no_signal_pending()` promotes an empty SELL order plan to pending and writes it to the canonical `pending_order_plan/pending_order_plan.json`.

### Submit

Submit did not reject ADD-derived orders; it did not receive them. It received `EMPTY` pending on 238 days.

Submitted days:

| Date | Submitted count | Interpretation |
|---|---:|---|
| 2022-09-01 | 4 | Initial BUY basket |
| 2022-09-06 | 1 | SELL |
| 2022-09-07 | 1 | SELL |
| 2022-09-08 | 1 | SELL |
| 2022-09-09 | 1 | SELL |
| 2022-09-12 | 1 | SELL |
| 2022-09-20 | 1 | SELL |

### Execution

Execution fills:

| Source decision type | Count |
|---|---:|
| BUY | 4 |
| EXIT | 3 |
| REDUCE | 3 |
| ADD | 0 |

All BUY fills were on 2022-09-01 and had `source_decision_type = BUY`, not ADD.

## 5. Drop-off Attribution

| Stage | Count / Status | Finding |
|---|---:|---|
| PM ADD | 228 | ADD decisions exist |
| PM ADD recognized as BUY input | 0 confirmed | No formal Morning ADD consumer found |
| Morning selected BUY items | 799 | BUY AI / Opportunity selections exist daily |
| Morning selected ADD-derived BUY items | 0 confirmed | No ADD lineage in plan/fill evidence |
| Sell Planning overwrote pending with EMPTY | 238 days | Main observed Submit drop-off |
| Submit `EMPTY` no-order days | 238 days | No submitted order by the time Submit ran |
| BUY fills | 4 | Initial day only |
| ADD-derived BUY fills | 0 | No ADD execution path completed |

Primary drop-off for PM ADD:

```text
PM ADD -> BUY planning consumer
```

Primary drop-off for daily BUY execution after Morning selection:

```text
Morning BUY pending -> Sell Planning no-signal EMPTY pending -> Submit no-action
```

This is why BUY fills concentrated on 2022-09-01: there were no positions, so Sell Planning preserved the Morning BUY pending. Once positions existed, no-signal Sell Planning wrote EMPTY pending and Submit saw no orders.

## 6. Capital Constraint Inventory

Formal policy file:

```text
configs/runtime_v2/capital_deployment.json
```

Policy values:

| Constraint | Value | Source |
|---|---:|---|
| evaluation capital | 1,000,000 | `configs/runtime_v2/capital_deployment.json:4` |
| target investment ratio | 0.85 | `configs/runtime_v2/capital_deployment.json:5` |
| cash buffer | 0.05 | `configs/runtime_v2/capital_deployment.json:6` |
| max exposure | 850,000 | `configs/runtime_v2/capital_deployment.json:7` |
| max position weight | 0.20 | `configs/runtime_v2/capital_deployment.json:8` |
| max positions | 5 | `configs/runtime_v2/capital_deployment.json:9` |
| min order amount | 0 | `configs/runtime_v2/capital_deployment.json:10` |
| max BUY order amount | null | `configs/runtime_v2/capital_deployment.json:11` |
| max SELL liquidation amount | null | `configs/runtime_v2/capital_deployment.json:12` |

Policy loader requires these fields explicitly:

```text
src/ai_fund_lab_v2/runtime_v2/policy/capital_deployment.py:16-30
```

Morning Planning derives:

```text
remaining_slots = max(policy.max_positions - current_position_count, 0)
target_exposure = evaluation_capital * target_investment_ratio
cash_buffer_amount = evaluation_capital * cash_buffer
planning_budget = min(target_remaining, exposure_remaining, cash_capacity)
per_order_budget = min(planning_budget / effective_order_limit, evaluation_capital * max_position_weight, max_buy_order_amount?)
```

Code evidence:

```text
src/ai_fund_lab_v2/runtime_v2/planning/morning_pipeline.py:1244-1282
```

Classification:

| Constraint | Responsibility | Finding |
|---|---|---|
| max positions 5 | Capital Deployment / Risk Policy | Explicit policy, not hidden in loader |
| 850,000 max exposure | Capital Deployment / Risk Policy | Explicit policy |
| cash buffer 5% | Capital Deployment / Risk Policy | Explicit policy |
| 20% per-position cap | Capital Deployment / Risk Policy | Explicit policy |
| ADD quantity | Missing consumer / Capital Allocation design gap | Not produced from PM ADD |

Important nuance:

The 5-position and 850,000-yen constraints are explicit in policy. They are not the main reason for the 238 no-order Submit days, because Morning still selected BUY items on all 245 days. The observed drop-off occurs after Morning pending generation, when Sell Planning writes EMPTY pending before Submit.

## 7. Production Impact

This is not Historical-only.

Reasons:

- ADD producer semantics are common PM Runtime code.
- Morning Planning input contract is common Runtime code.
- Sell Planning writes to the same canonical pending path used by Runtime Core.
- Submit consumes only `pending_order_plan/pending_order_plan.json`.

Historical adapter differences do not explain the missing ADD consumer. Historical evidence simply made the gap observable at 245BD scale.

Production impact assessment:

```text
PRODUCTION_IMPACT_REVIEW_REQUIRED
```

If Production operation runs Morning BUY planning and Sell Planning sequentially against the same single pending slot, BUY pending can be overwritten by SELL no-signal pending before Submit unless an orchestration or pending-composition contract prevents it. If PM ADD is expected to drive real add-on buys, Production also needs a formal ADD -> Capital Allocation -> BUY Pending consumer.

## 8. Architecture Gaps

### Gap 1: ADD Intent Consumer Missing

The design says ADD is a buy-add candidate signal and Capital Allocation decides final purchase. Current Runtime code does not show a formal ADD consumer that converts PM ADD into BUY intent, sizing, pending, approval, submit, and execution.

### Gap 2: Pending Slot Collision Between BUY and SELL Planning

Runtime Architecture v2 says Submit source is the canonical pending plan. Current evidence shows Morning can create BUY pending, then Sell Planning no-signal can write EMPTY pending into that same slot before Submit.

This creates a lifecycle mismatch:

```text
BUY Planning created executable pending
SELL Planning no-signal overwrote canonical pending
Submit correctly no-ops because pending is EMPTY
```

### Gap 3: Existing Position Symbol Normalization Review

Morning attempts to exclude existing positions:

```text
if broker_symbol in current_position_symbols: continue
```

But `_broker_symbol("94320")` returns `"9432"` while `current_position_symbols` in evidence are `"94320"`. On representative days, `94320` was selected even when already held and `existing_position_excluded_count = 0`.

Code evidence:

```text
src/ai_fund_lab_v2/runtime_v2/planning/morning_pipeline.py:577-582
src/ai_fund_lab_v2/runtime_v2/planning/morning_pipeline.py:1597-1602
```

This is not the main Submit drop-off because those selected items were later overwritten by Sell Planning, but it is a real architecture/implementation review item before ADD/rebuy semantics are changed.

## 9. Recommended Phase21 Design Actions

Priority 1:

Define a formal Pending Composition Contract for BUY and SELL planning. Decide whether the daily authoritative pending should support:

- separate BUY and SELL pending slots,
- a merged composite pending plan,
- SELL-first / BUY-after-fill sequencing,
- or explicit no-signal preservation rules that never overwrite active BUY pending.

Priority 2:

Define PM ADD consumption semantics:

- ADD remains advisory only, or
- ADD becomes a formal input to Capital Allocation,
- ADD sizing source,
- ADD max additional weight,
- ADD cool-down / minimum holding days,
- ADD no-loss-averaging guard,
- ADD order lineage fields.

Priority 3:

Add evidence fields for ADD lineage:

```text
source_decision_type = ADD
source_pm_decision_id
add_candidate_signal = true
add_sizing_policy
add_rejected_reason
add_to_buy_consumer_status
```

Priority 4:

Review symbol normalization for existing-position exclusion before relying on Morning Planning to prevent duplicate/add-on BUY selection.

Priority 5:

Only after the above contracts are accepted, design controlled experiments for ADD policy and Capital Deployment. Do not tune thresholds directly from this 245BD result.

## 10. Phase21-B Entry Decision

Phase21-B can proceed, but not directly into performance-tuning implementation.

Recommended entry:

```text
PHASE21_B_READY_FOR_CONTRACT_DESIGN_AND_METRIC_COMPLETION
```

Required Phase21-B scope:

- Performance metric completion remains needed.
- Pending Composition Contract should be treated as a Runtime/Architecture design prerequisite.
- PM ADD -> Capital Allocation contract should be defined before any ADD strategy experiment.
- 245BD evidence remains diagnostic only; it must not become training input or direct threshold imitation.

## Acceptance Criteria Review

| Criterion | Status |
|---|---|
| ADD 228件の意味確認 | PASS |
| ADD consumer特定 | PASS: formal BUY consumer missing |
| ADDからBUY Executionまでの経路追跡 | PASS |
| 245BD段階別件数集計 | PASS |
| 238日のno_submitted_orders主要原因 | PASS: Submit saw EMPTY after Sell Planning no-signal |
| BUY Fill初日集中理由 | PASS |
| 5銘柄・85万円・現金制約Authority | PASS |
| Production影響判定 | PASS: REVIEW_REQUIRED |
| Evidence Path提示 | PASS |
| Productionコード未変更 | PASS |
| 長時間Historical Run未実行 | PASS |

## Non-Mutation Statement

This investigation created only:

```text
docs/phase_reports/phase21_a_pm_add_capital_deployment_execution_gap_investigation.md
reports/phase21_a_pm_add_capital_deployment_execution_gap_investigation/phase21_a_evidence.json
```

No Production, Demo, Historical Runtime, Strategy, PM, Capital Deployment, Safety, Broker, Training, Calibration, Accepted Generation, or model code was changed.
