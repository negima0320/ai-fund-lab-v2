# Phase23-AI Dynamic Position Count Candidate and Opportunity Capacity Contract Repair

## 1. Primary Judgment

`PHASE23_AI_DYNAMIC_POSITION_COUNT_CANDIDATE_OPPORTUNITY_CAPACITY_CONTRACT_REPAIR_SHORT_VALIDATION_PASS`

## 2. Phase23継続確認

Phase23-AHで確定したRoot Causeのみを修正した。Historical fresh-run、10BD再実行、Runtime Switch、Broker Write、J-Quants live fetch、canonical mutation、対象Run再分類は実施していない。

## 3. Confirmed Root Cause

`DYNAMIC_POSITION_COUNT_CANDIDATE_OPPORTUNITY_SUMMARY_FIELD_CONTRACT_MISMATCH_FORCES_ZERO_TARGET_POSITION_COUNT`

Candidate/Opportunityに `consumer_eligible_rows=50` が存在するのに、Dynamic Position Countが旧想定field欠損を0として扱い、target position countを0にしていた。

## 4. Producer Contract

`shadow_runtime.py` のcandidate/opportunity adapter summaryは `consumer_eligible_rows` に加え、canonical fieldとして `candidate_capacity_count` または `opportunity_capacity_count` を出力する。

## 5. Consumer Contract

`dynamic_position_count.py` は `resolve_capacity_count()` でtyped capacity resolutionを行う。missing、invalid、conflictはsilent zeroにせず `REVIEW_REQUIRED` へ倒す。

## 6. Canonical Capacity Fields

Candidate canonical: `candidate_capacity_count`。Opportunity canonical: `opportunity_capacity_count`。

## 7. Legacy Alias Policy

Legacy aliasは明示リストのみ許可。主要aliasは `consumer_eligible_rows`。旧fieldも互換対応するが、矛盾時は採用しない。

## 8. Capacity Resolution Priority

1. canonical field
2. explicitly supported legacy alias
3. missing/invalid/conflictは `REVIEW_REQUIRED`

## 9. Conflict Detection

`consumer_eligible_rows=50` と `available_candidate_count=0` のような矛盾は `CANDIDATE_CAPACITY_FIELD_CONFLICT` / `OPPORTUNITY_CAPACITY_FIELD_CONFLICT` としてReview化する。

## 10. Missing Field Handling

全supported field欠損時は `*_CAPACITY_FIELD_MISSING`。target position countは `None` / `UNRESOLVED` になり、0としてPASSしない。

## 11. Candidate Capacity Repair

AH相当入力 `consumer_eligible_rows=50,row_count=50` は `resolved_candidate_capacity=50`。

## 12. Opportunity Capacity Repair

AH相当入力 `consumer_eligible_rows=50,row_count=50` は `resolved_opportunity_capacity=50`。

## 13. Target Position Count Derivation

BULL/STRONG/NORMAL、RISK_ON/EXPAND、capacity 50/50、current positions 0のisolated reproductionでは、Production-common policyから `target_position_count > 0` を導出。強制BUYや固定position countは未使用。

## 14. Position Sizing Propagation

resolved target countが正数の場合、position sizingは `positions_sized > 0` を生成することをunitで確認。

## 15. Runtime Planning Propagation

SIZEDなADD_CANDIDATEはruntime planningで `BUY_NEW` / `BUY` のまま残り、zero allocation理由で全NO_ORDERへ落ちないことを確認。

## 16. Contradiction Guard

upstream positive rowsとcapacity zeroが矛盾する場合、Dynamic Position Countは `REVIEW_REQUIRED` で停止し、targetを0に確定しない。

## 17. Schema and Artifact Changes

schema_versionは `dynamic_position_count.v1` 維持。新規artifactにはcapacity resolution evidence fieldsを追加。legacy v1 artifact互換のため、新fieldはvalidatorで存在時検証とした。

## 18. Regression Matrix

12観点すべてPASS。詳細は `reports/phase23_ai_dynamic_position_count_candidate_opportunity_capacity_contract_repair/regression_matrix.json`。

## 19. Modified Files

- `src/ai_fund_lab_v2/strategy/dynamic_position_count.py`
- `src/ai_fund_lab_v2/strategy/shadow_runtime.py`
- `tests/strategy/test_phase22_h_dynamic_position_count.py`
- `tests/strategy/test_phase22_j_position_sizing.py`
- `tests/strategy/test_phase22_g_runtime_planning.py`

## 20. Short Validation

- py_compile: PASS
- `python3 -m pytest -q tests/strategy/test_phase22_h_dynamic_position_count.py tests/strategy/test_phase22_j_position_sizing.py tests/strategy/test_phase22_g_runtime_planning.py`: 50 passed

## 21. Existing Run Preservation

対象Run `runtime-test-historical-extended-smoke-20260729T210023562257Z` はread-only。主要artifact hashは前後一致。

## 22. 未実施事項

Historical fresh-run、10BD、20BD、1年、3年、4年、Runtime Switch、Broker Write、J-Quants live fetch、canonical mutation、resume/abandonは未実施。

## 23. Remaining Gaps

修正後のRuntime再実行は未実施。Evidence Review後にOperatorが短いHistorical Runtimeまたは10BD再実行を判断する。

## 24. Next Operator Action

ChatGPT Evidence Review後、Phase23-AIの修正を受理できる場合のみ、Operatorが短いHistorical Runtimeまたはproduction-equivalent 10BD再実行へ進む。
