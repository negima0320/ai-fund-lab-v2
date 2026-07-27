# Phase21-B Pending Composition and PM ADD Consumer Fix

## Primary Judgment

```text
PHASE21_B_PENDING_COMPOSITION_AND_ADD_CONSUMER_FIXED
```

Phase21-Aで確認した、Sell Planning `NO_SIGNAL` によるBUY Pending上書き、およびPM `ADD`がPending BUYへ到達しない問題を、Runtime共通経路で修正した。

## Design Memo

実装前設計メモ:

```text
reports/phase21_b_pending_composition_and_add_consumer_fix/design_memo.md
```

採用モデル:

```text
COMPOSITE_PENDING_PLAN
```

Submit authorityは引き続き以下のみである。

```text
pending_order_plan/pending_order_plan.json
```

Separate BUY/SELL Pending slot、History artifact直接Submit、Submitによる複数Pending探索は採用しない。

## Changes

- Sell Planning `NO_SIGNAL` は、同一business date / target session / environmentの有効な既存BUY Pendingを検出した場合、`EMPTY`で上書きせず保存する。
- Sell PlanningがSELL itemを生成し、既存BUY Pendingがある場合、BUY itemとSELL itemを1つのComposite Pending Planに合成する。
- PM `ADD`をPlanning candidateとして保持し、Capital Deployment policy、Current Position、cash / exposure、lot size、Safety、Submit Guardを通過した場合のみBUY Pending itemを生成する。
- ADD-derived Pending itemへlineageを追加した。
- ADD-derived Submit ledger order recordへlineageを転写する。
- 94320 / 9432 のような5桁末尾0と4桁broker codeを同一symbol identityとして扱う最小helperを追加した。

## ADD Lineage

ADD-derived Pending itemは以下を保持する。

- `source_decision_type=ADD`
- `source_pm_decision_id`
- `source_pm_business_date`
- `source_position_symbol`
- `add_candidate_signal=true`
- `capital_allocation_status`
- `capital_allocation_reason`
- `requested_add_notional`
- `approved_add_notional`
- `quantity`
- `rejected_reason`

ADD reject reason evidence:

- `MAX_POSITION_WEIGHT`
- `MAX_EXPOSURE`
- `INSUFFICIENT_CASH`
- `LOT_SIZE_NOT_VIABLE`
- `DUPLICATE_PENDING_ORDER`
- `NO_LOSS_AVERAGING_GUARD`
- `OPPORTUNITY_NO_LONGER_ELIGIBLE`
- `INVALID_CURRENT_POSITION`
- `AUTHORITY_NOT_ACCEPTED`

## Files Changed

- `src/ai_fund_lab_v2/runtime_v2/pending/composition.py`
- `src/ai_fund_lab_v2/runtime_v2/planning/add_consumer.py`
- `src/ai_fund_lab_v2/runtime_v2/symbol_identity.py`
- `src/ai_fund_lab_v2/runtime_v2/planning/sell_pipeline.py`
- `src/ai_fund_lab_v2/runtime_v2/planning/morning_pipeline.py`
- `src/ai_fund_lab_v2/runtime_v2/position_management/producer.py`
- `src/ai_fund_lab_v2/runtime_v2/pending/models.py`
- `src/ai_fund_lab_v2/runtime_v2/pending/reader.py`
- `src/ai_fund_lab_v2/runtime_v2/submit/pipeline.py`
- `src/ai_fund_lab_v2/runtime_v2/ledger/models.py`
- `tests/runtime_v2/test_phase21_b_pending_composition_add_consumer.py`
- `docs/02_architecture/runtime_architecture_v2.md`
- `docs/03_ai_design/position_management_ai_design.md`

## Verification

Executed targeted tests only. No long Historical Run was executed by Codex.

```text
PYTHONPYCACHEPREFIX=/Users/negishi/work/ai-fund-lab-v2/.pycache_tmp python3 -m pytest tests/runtime_v2/test_phase21_b_pending_composition_add_consumer.py -q
7 passed
```

```text
PYTHONPYCACHEPREFIX=/Users/negishi/work/ai-fund-lab-v2/.pycache_tmp python3 -m pytest tests/runtime_v2/test_phase14e32_sell_runtime_io_contract.py tests/runtime_v2/test_phase14e15_morning_ai_planning_pending_connection.py -q
10 passed
```

```text
PYTHONPYCACHEPREFIX=/Users/negishi/work/ai-fund-lab-v2/.pycache_tmp python3 -m py_compile ...
PASS
```

## Long Historical Run

```text
NO
```

Codex did not run 5BD / 20BD / 245BD / 1y / multi-year Historical Runtime.

## User-run 5BD Command

Example command should be executed by the user only, with the project’s current accepted runtime-test profile and evidence root.

```bash
python3 -m ai_fund_lab_v2.runtime_v2.cli.run_historical_runtime_test \
  --profile runtime-test-historical-smoke-5bd \
  --date-from 2022-09-01 \
  --business-days 5
```

## 5BD Acceptance Checks

- Morning BUY Pending is not overwritten by Sell Planning `NO_SIGNAL`.
- BUY+SELL mixed day produces one approved Composite Pending Plan.
- Submit reads only `pending_order_plan/pending_order_plan.json`.
- No duplicate order is submitted on rerun.
- PM ADD candidate creates BUY Pending only after policy / current / safety / submit guard checks.
- ADD-derived Pending and ledger order retain PM lineage.
- 94320 / 9432 identity gap does not block current position lookup or duplicate detection.

## Remaining Gaps

- Long-run performance impact is not evaluated in this phase by Codex.
- ADD sizing is intentionally conservative and policy-bound; no PM threshold, ranking, exposure cap, max position count, or target investment ratio was tuned.

## Strategy Design Return Status

```text
PHASE21_READY_TO_RETURN_TO_STRATEGY_ARCHITECTURE_DESIGN
```
