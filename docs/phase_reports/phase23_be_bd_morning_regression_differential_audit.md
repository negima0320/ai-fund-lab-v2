# Phase23-BE BD Morning Regression Differential Audit

## Primary Judgment

`PHASE23_BE_BD_MORNING_REGRESSION_AUDIT_COMPLETE`

## Supporting Judgment

- `BD_REGRESSION_CONFIRMED = YES`
- `LOWEST_LEVEL_REASON = KeyError: 'opportunity'`
- `FIRST_INVALID_ARTIFACT = reports/runtime_tests/runs/runtime-test-historical-smoke-20260730T054102824494Z/daily/2026-07-06/strategy/runtime_planning.json`
- `REPAIR_REQUIRED = YES`
- `READY_FOR_REPAIR = YES`
- `READY_FOR_1BD_RERUN = NO`

## Direct Root Cause

BD後RunはMorningでHALTした。

Direct reasonはMorning manifest上の以下。

`morning pipeline review required: strategy_runtime_planning_artifact_invalid:...`

最下層reasonは、Strategy ShadowのRuntime Planning producerで発生した例外。

`KeyError: 'opportunity'`

BD後Runの最初のinvalid artifactは以下。

`reports/runtime_tests/runs/runtime-test-historical-smoke-20260730T054102824494Z/daily/2026-07-06/strategy/runtime_planning.json`

内容は `schema_version = runtime_planning_shadow_error.v1`, `producer_result_status = BLOCK`, `error = "'opportunity'"`, `reason_codes = ["strategy_shadow_generation_error"]`。

## Before / After

BD前Run `runtime-test-historical-smoke-20260730T050344341520Z`:

- Morning exit_code: `0`
- Runtime Planning: `PASS`
- Runtime Planning plan count: `50`
- Strategy Planning Authority: `PASS`
- Pending generation: `PASS`
- Final pending item count: `9`

BD後Run `runtime-test-historical-smoke-20260730T054102824494Z`:

- Morning exit_code: `20`
- Runtime Planning: `BLOCK`
- Runtime Planning plan count: `0`
- Strategy Planning Authority: `REVIEW_REQUIRED`
- Pending generation: `REVIEW_REQUIRED`
- Final pending artifact: absent

Opportunity source itselfは両Runで存在し、同一hashだった。

- path: `.runtime/runtime_state/buy_ai/2026-07-06/opportunity_rankings.json`
- sha256: `ee7abc999dd7ba786258e802da4cf9dce06740bb127ce2b70ba3c0d2653f1d3c`
- status: `PASS`

## Code Evidence

`src/ai_fund_lab_v2/strategy/shadow_runtime.py:27` の `ARTIFACT_FILENAMES` には `opportunity` keyがない。

一方、BD実装で `src/ai_fund_lab_v2/strategy/shadow_runtime.py:253` に以下が追加されている。

`opportunity_artifact_path=artifact_paths["opportunity"]`

このためRuntime Planning artifact生成時に `KeyError: 'opportunity'` が発生し、正規のRuntime Planning schemaではなくerror artifactが出力された。

## Classification

- `BD_RUNTIME_BINDING_REGRESSION`
- `OPPORTUNITY_AUTHORITY_GENERATION_FAILURE`
- `MISSING_PRODUCER`
- `AUTHORITY_UNRESOLVED`

`BD_SCHEMA_REGRESSION`, `BD_SERIALIZATION_REGRESSION`, `BD_HASH_OR_IDENTITY_REGRESSION` ではない。Submit item-level resolverまでは到達していない。

## Previous Blocker Check

`historical_pending_safety_authority_mismatch` はBD後Run内に文字列として存在するが、Data Readiness総合はREADYであり、Morning HALTのprimary reasonではない。

以下はBD後Runのprimary halt reasonとしてはabsent。

- `target_weight_authority_unresolved`
- `invalid_quality_score`
- `review_required_quantity_authority`
- `REVIEW_REQUIRED_MISSING_PRICE`
- `strategy_plan_quantity_unresolved`
- `historical_trading_calendar_authority_missing`
- `current_valuation_previous_trading_date_missing`
- `historical_safety_temporal_authority_missing`
- `pending_safety_evidence_missing`
- `policy_mismatch`
- `opportunity_evidence_missing`
- `opportunity_row_identity_mismatch`

## Production Contract Review

BD設計、つまりOpportunity Ranking row authorityをPending itemへ運びSubmit Guardで再検証する方針は妥当。

ただし実装は、Strategy ShadowのRuntime Planning wiringでOptionalなOpportunity sourceを `artifact_paths` の必須output artifactとして参照してしまった。修正ownerは `src/ai_fund_lab_v2/strategy/shadow_runtime.py` のRuntime Planning wiring。

推奨修正境界は、Opportunity artifactを `ARTIFACT_FILENAMES` の必須出力にすることではなく、Source Manifest / runtime_root上の `.runtime/runtime_state/buy_ai/<business_date>/opportunity_rankings.json` からoptional input pathとして解決し、存在しない場合は `None` を渡すこと。

## Deliverables

Human:

`docs/phase_reports/phase23_be_bd_morning_regression_differential_audit.md`

Machine:

`reports/phase_reports/phase23_be_bd_morning_regression_differential_audit.json`

Evidence:

`reports/phase23_be_bd_morning_regression_differential_audit/`

## Existing Run Preservation

対象Run artifactはread-onlyで扱った。hash preservationは `existing_run_hash_preservation.json` に記録した。

## Next Task Candidate

`Phase23-BF Opportunity Ranking Path Optional Runtime Planning Wiring Repair`
