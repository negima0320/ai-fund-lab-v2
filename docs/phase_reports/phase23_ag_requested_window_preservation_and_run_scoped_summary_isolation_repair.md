# Phase23-AG Requested Window Preservation and Run-Scoped Summary Isolation Repair

## 1. Primary Judgment

`PHASE23_AG_REQUESTED_WINDOW_PRESERVATION_AND_RUN_SCOPED_SUMMARY_ISOLATION_REPAIR_SHORT_VALIDATION_PASS`

## 2. Phase23継続確認

Phase23-AFで確定した2件だけを修正した。既存8BD Runはread-onlyで扱い、10BD PASSへ再分類していない。Historical Test、Runtime Switch、Broker Write、J-Quants live fetch、canonical promotion/copy/mutationは実施していない。

## 3. Confirmed Root Cause A

`PLAN_WINDOW_REQUEST_LOST_BY_RESOLVED_DATE_LIST_LENGTH_AND_CALENDAR_AUTHORITY_TRUNCATION`

旧PlanはOperator intentの10BDを保持せず、calendar authority最大日付 `2026-07-15` で解決できた8BDを `requested_business_days=8` として保存していた。

## 4. Confirmed Root Cause B

`SUMMARIZE_CURRENT_RUNTIME_NON_EXECUTABLE_SELL_DECISION_LEAKS_INTO_RUN_SCOPED_LIFECYCLE`

Run-scoped PM/SELL/fills/positionsが0件であるにもかかわらず、final hash matchにより `.runtime/runtime_state/sell_pipeline/2026-07-06/order_plan.json` の current non-executable SELL がLifecycleへ混入していた。

## 5. Requested Window Contract

Planは `requested_start_date`, `requested_end_date`, `requested_business_days`, `requested_window` をOperator requestとして保持する。`requested_business_days` を `len(resolved_business_dates)` で上書きしない。

## 6. Calendar Authority Contract

Plan window resolverはcanonical historical calendar baseに、validated incremental staging calendar overlayを論理合成する。canonical fileは変更しない。今回のread-only確認ではbase max `2026-07-15`、validated overlayによりlogical max `2026-07-17`、10BD windowは `2026-07-06` から `2026-07-17` まで解決された。

## 7. Plan Schema Changes

追加/分離した主要field: `resolved_business_dates`, `resolved_business_day_count`, `resolved_date_from`, `resolved_date_to`, `window_resolution_status`, `window_resolution_reason`, `calendar_authority`, `calendar_max_date`, `unresolved_requested_dates`, `request_conformance_status`。

## 8. Window Resolution Judgment

Full resolutionは `window_resolution_status=PASS`。Partial resolutionは `REVIEW_REQUIRED` とし、plan commandもbaseline互換性とwindow resolutionの両方がPASSでない限りPASSにしない。

## 9. Plan / Run / Summary Consistency

新Contractでは requested/resolved/completed を別々に保持し、summaryでも `requested_business_days`, `resolved_business_day_count`, `completed_business_day_count` を再掲する。既存legacy RunはPlanに10BD intentがないため、read-only recalculationで `overall_independent_judgment=REVIEW_REQUIRED` のままにした。

## 10. Summarize Authority Priority

Summary authorityはRun-scoped evidenceを優先する。current `.runtime` はfinal hash match時のfallbackだが、Run-scoped artifact classが存在する場合は同classのcurrent fallbackをLifecycle判定へ混ぜない。

## 11. Artifact-Class Isolation

`sell_planning` と `non_executable_sell_decisions` はartifact class単位でauthority matrixを持つ。Run-scoped sell manifestが採用されたclassでは、current runtime fallback pathをsource pathから除去する。

## 12. Non-Executable Sell Decision Repair

Run-scoped sell manifestでPM decision/reduce/exitが0件の場合、同日付のcurrent `sell` だけでなく `non_executable_sell_decisions` も除外する。既存Runのread-only再集計では `non_executable_reduce_terminal_count=0` となった。

## 13. Summary Authority Matrix

既存Run read-only再集計結果: `sell_planning.authority=RUN_SCOPED_EVIDENCE`, `non_executable_sell_decisions.authority=RUN_SCOPED_EVIDENCE`, `fallback_used=false`。PM/fills/position_campaignsもRun-scoped evidenceで評価された。

## 14. Lifecycle Recalculation

既存Run read-only再集計で `lifecycle_consistency.status=PASS`。`PM_REDUCE_TO_PARTIAL_SELL_PLAN`, `PM_EXIT_TO_SELL_PLAN`, `SELL_PLAN_TO_SUBMIT`, `SELL_SUBMIT_TO_EXECUTION`, `LEDGER_TO_CURRENT`, `PENDING_EMPTY_OR_EXPLAINED` は全てtrue。

## 15. Independent Acceptance Recalculation

既存Runは runtime execution PASS、summary evidence isolation PASS、lifecycle consistency PASS。一方、legacy planで10BD requestが保存されていないため requested window resolution/conformance はNOT_PASS、overallは `REVIEW_REQUIRED`。

## 16. Regression Matrix

12件のRegression観点を `reports/phase23_ag_requested_window_preservation_and_run_scoped_summary_isolation_repair/regression_matrix.json` に記録した。AG targeted regressionは4本PASS、summarize regression fileは19本PASS。

## 17. Modified Files

- `scripts/runtime_test.py`
- `tests/runtime_v2/test_phase17_k_runtime_test_runner.py`
- `tests/runtime_v2/test_phase19_bv_runtime_test_summarize.py`

## 18. Short Validation

- py_compile: PASS
- Phase23-AG targeted regression: 4 passed
- summarize regression file: 19 passed
- Existing run read-only summarize: PASS, artifact hashes preserved

`tests/runtime_v2/test_phase17_k_runtime_test_runner.py` 全体は 17 passed / 5 failed。失敗はminimal fixtureが現行のHistorical Evaluation Authority / Accepted Generation bootstrap preconditionでRuntime CLI mock到達前に止まる既存fixture gapで、AG対象の3 window testsはPASS。

## 19. Existing Run Preservation

Protected run: `reports/runtime_tests/runs/runtime-test-historical-extended-smoke-20260729T111715014852Z/`。read-only summarize前後で `plan.json`, `run_state.json`, `fresh_run_summary.json`, `final_summary.json` のhashは一致した。

## 20. 未実施事項

1BD fresh runtime、10BD、20BD、1年、3年、4年のHistorical Runtime Testは実施していない。Runtime Switch、Broker Write、J-Quants live fetch、canonical mutationも実施していない。

## 21. Remaining Gaps

Phase17-K full-fileの一部legacy testsは、AGとは別のAccepted Generation bootstrap前提をfixture化できていないため失敗する。Production-equivalent 10BD rerunの実行可否は、このAG evidence review後にOperator判断とする。

## 22. Next Operator Action

ChatGPT Evidence Reviewを実施する。ReviewでAG evidenceが受理され、known blockerなしと判断された場合のみ、Operatorがproduction-equivalent 10BD rerunへ進める。
