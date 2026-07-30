# Phase23-BU Close Authority Strategy Shadow Review Classification Repair

## Primary Judgment

`PHASE23_BU_CLOSE_AUTHORITY_STRATEGY_SHADOW_REVIEW_CLASSIFICATION_SHORT_VALIDATION_PASS`

Production-commonのClose Authority分類を修正し、Non-mutating EOD Strategy Shadow `REVIEW_REQUIRED` が、Trading / Accounting / Production Planningの運用完了判定を上書きしない契約に分離した。Runtime rerun、fresh-run、resume、Broker Write、Runtime Switch、J-Quants取得、既存Run mutationは実施していない。

## Root Cause

Phase23-BTで確認されたRoot Causeは、`strategy_shadow_judgment = REVIEW_REQUIRED` が `close_command()` のStrategy acceptance gateを通じて、そのままFinal Runtime Judgmentへ伝播したこと。

対象Run `runtime-test-historical-smoke-20260730T211110605880Z` では、10/10営業日完了、Trading state PASS、Accounting state PASS、SELL lifecycle到達済みだった。一方、2022-07-14のEOD Strategy Shadow `runtime_planning.json` が、消費済みPending `existing_pending_conflict:23880` を検出し `REVIEW_REQUIRED` になった。

このレビューはStrategy Shadowの観測・設計レビューとして保持すべきだが、取引状態不整合ではない。

## 修正内容

`scripts/runtime_test.py` にClose Authority分類を追加した。

- `_production_planning_authority_gate_status()`
- `_strategy_shadow_blocks_operational_close()`
- `_strategy_review_status()`
- `_strategy_shadow_close_review_classification()`
- `_close_authority_classification()`

`close_command()` は以下をFinal Summaryへ出力する。

- `trading_state_judgment`
- `accounting_state_judgment`
- `runtime_execution_judgment`
- `production_planning_judgment`
- `strategy_shadow_judgment`
- `strategy_shadow_review_required`
- `close_authority_judgment`
- `final_runtime_judgment`
- `operational_status`
- `strategy_review_status`
- `close_authority_classification`

`summarize` もRun-scoped `final_summary.json` から新しいClose Authority fieldsを透過する。

## Contract

Trading / Accounting / Runtime execution / Production Planning / Historical Authority が非PASSの場合、Final Runtime Judgmentは非PASSを維持する。

Non-mutating EOD Strategy Shadow `REVIEW_REQUIRED` のみの場合は、Operational completionは `PASS` とし、`strategy_review_status = REVIEW_REQUIRED` と `strategy_shadow_review_required = true` で保持する。

Strategy Shadowでも以下は引き続きBlocking。

- `strategy_shadow_judgment = BLOCK`
- broker write
- runtime switch
- runtime mutation
- `REVIEW_REQUIRED` ShadowがActive Production Consumerとして分類されている場合

## 2022-07-14 再分類

Evidence上の再分類結果:

- `TRADING_STATE_VALID`
- `ACCOUNTING_STATE_VALID`
- `RUNTIME_EXECUTION_VALID`
- `STRATEGY_SHADOW_REVIEW_REQUIRED`
- `OBSERVABILITY_CONFLICT`
- `NON_BLOCKING_FOR_OPERATIONAL_COMPLETION`

理由 `existing_pending_conflict:23880` は削除せず、Strategy reviewとして残す。

## 短時間テスト

PASS:

- `PYTHONPYCACHEPREFIX=/Users/negishi/work/ai-fund-lab-v2/.pytest_cache/pycache python3 -m py_compile scripts/runtime_test.py`
- `python3 -m pytest -q tests/runtime_v2/test_phase23_j_strategy_authority_gate.py` -> 7 passed
- `python3 -m pytest -q tests/runtime_v2/test_phase19_bv_runtime_test_summarize.py` -> 19 passed
- `python3 -m pytest -q tests/runtime_v2/test_phase23_bi_buy_ai_import_boundary.py tests/runtime_v2/test_phase21_b_pending_composition_add_consumer.py tests/runtime_v2/test_phase17_x_historical_sell_planning_authority.py` -> 25 passed
- `python3 -m pytest -q tests/runtime_v2/test_phase15l_submit_policy_hash_consistency_guard.py tests/runtime_v2/test_phase19_bt_reduce_quantity_contract.py` -> 17 passed
- BU関連combined 7 files -> 68 passed

Observed but out of BU scope:

- `tests/runtime_v2/test_phase17_k_runtime_test_runner.py tests/runtime_v2/test_phase19_bv_runtime_test_summarize.py` -> 38 passed, 5 failed
- 5件はRun/Resume入口で `PRECONDITION_FAILURE`。古いfixtureが現在のHistorical Evaluation Authority preconditionを満たさず、Close classification pathへ到達していない。

## 修正対象ファイル

- `scripts/runtime_test.py`
- `tests/runtime_v2/test_phase23_j_strategy_authority_gate.py`

## 成果物

- Human: `docs/phase_reports/phase23_bu_close_authority_strategy_shadow_review_classification_repair.md`
- Machine: `reports/phase_reports/phase23_bu_close_authority_strategy_shadow_review_classification_repair.json`
- Evidence: `reports/phase23_bu_close_authority_strategy_shadow_review_classification_repair/`

## Gate

- `PRODUCTION_COMMON_CLOSE_CONTRACT = PASS`
- `PRODUCTION_CONSUMER_AND_SHADOW_CONSUMER_SEPARATED = PASS`
- `TRADING_STATE_INVALIDITY_REMAINS_BLOCKING = PASS`
- `NON_MUTATING_STRATEGY_SHADOW_REVIEW_NON_BLOCKING = PASS`
- `CONSUMED_PENDING_OBSERVABILITY_CONFLICT_NON_BLOCKING = PASS`
- `EXISTING_RUN_PRESERVED = PASS`
- `READY_FOR_OPERATOR_1BD_OR_10BD_CLOSE_REVALIDATION = YES`

長時間Runtime Testは未実施。次はOperatorによる1BD/10BD Close再検証、またはChatGPT Evidence Review。
