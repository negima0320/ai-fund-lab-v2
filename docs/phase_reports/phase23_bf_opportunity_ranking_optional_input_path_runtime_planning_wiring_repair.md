# Phase23-BF Opportunity Ranking Optional Input Path Runtime Planning Wiring Repair

## Primary Judgment

`PHASE23_BF_OPPORTUNITY_OPTIONAL_PATH_WIRING_SHORT_VALIDATION_PASS`

## Secondary Judgment

`READY_FOR_1BD_RUNTIME_RERUN = YES`

Supporting:

- `OPPORTUNITY_SOURCE_PATH_CANONICALLY_RESOLVED`
- `OPTIONAL_INPUT_CONTRACT_PRESERVED`
- `KEYERROR_REGRESSION_RESOLVED`
- `RUNTIME_PLANNING_CANONICAL_SCHEMA_RESTORED`
- `BD_OPPORTUNITY_AUTHORITY_BINDING_PRESERVED`
- `SUBMIT_OPPORTUNITY_GUARD_PASS`
- `NEGATIVE_FAIL_CLOSED_PRESERVED`

## Root Cause

Phase23-BDで、Runtime PlanningへOpportunity Ranking authorityを渡す際に、optional input sourceをoutput artifact mapから取得していた。

`opportunity_artifact_path=artifact_paths["opportunity"]`

しかし `ARTIFACT_FILENAMES` に `opportunity` keyは存在しない。Opportunity RankingはRuntime Planningのoutput artifactではなく、Runtime root上のoptional input authorityである。

## Repair

`src/ai_fund_lab_v2/strategy/shadow_runtime.py` に `_optional_opportunity_artifact_path()` を追加した。

Rules:

- Opportunity summary statusが `PASS`
- payload business dateがRuntime business dateと一致
- physical pathが存在

この場合のみ `Path` を返す。欠損、Business Date不一致、非PASSでは `None` を返す。

Runtime Planning wiringは `artifact_paths["opportunity"]` ではなく、このoptional resolver結果を渡す。

`ARTIFACT_FILENAMES` へ `opportunity` は追加していない。latest lookup、dummy artifact生成、Historical専用分岐も追加していない。

## Canonical Reproduction

Fresh-run / 1BD runtime rerunは禁止のため未実施。代わりに `/private/tmp/phase23_bf_shadow_repro` へ targeted Strategy Shadow generation を実施した。

Observed:

- KeyError `'opportunity'`: absent
- Opportunity source path: `.runtime/runtime_state/buy_ai/2026-07-06/opportunity_rankings.json`
- Opportunity source hash: `ee7abc999dd7ba786258e802da4cf9dce06740bb127ce2b70ba3c0d2653f1d3c`
- Runtime Planning schema: `runtime_planning.v1`
- plan count: `50`
- BUY plans with Opportunity Authority: `50/50`

この一時再現では現在の `.runtime` 状態由来のquantity/source statusによりRuntime Planning status自体はBLOCKだが、BF対象のKeyError regressionは解消し、canonical schemaとOpportunity Authority propagationは復旧している。

## Validation

- `py_compile`: PASS
- BF optional path targeted: `3 passed, 4 deselected`
- BD opportunity authority binding: `2 passed, 9 deselected`
- Shadow Runtime regression: `7 passed`
- Runtime Planning regression: `16 passed`
- Submit opportunity eligibility regression: `7 passed`
- BB Submit Policy regression: `15 passed`
- Strategy Authority regression: `11 passed`
- Pending Safety/Data Readiness targeted: `1 passed, 9 deselected`
- Historical Submit targeted: `8 passed, 1 deselected`
- `git diff --check`: PASS

## Existing Run Preservation

No existing run artifact mutation was performed.

Preserved:

- `runtime-test-historical-smoke-20260730T054102824494Z`
- `runtime-test-historical-smoke-20260730T050344341520Z`
- `runtime-test-historical-smoke-20260730T042431441297Z`

## Modified Files

- `src/ai_fund_lab_v2/strategy/shadow_runtime.py`
- `tests/runtime_v2/test_phase22_p_strategy_shadow_wiring.py`

## Deliverables

Machine report:

`reports/phase_reports/phase23_bf_opportunity_ranking_optional_input_path_runtime_planning_wiring_repair.json`

Evidence:

`reports/phase23_bf_opportunity_ranking_optional_input_path_runtime_planning_wiring_repair/`

## Next Operator Action

Operator 1BD runtime rerun after Evidence Review.
