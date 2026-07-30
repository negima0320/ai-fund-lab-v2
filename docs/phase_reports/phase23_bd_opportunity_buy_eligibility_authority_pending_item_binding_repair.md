# Phase23-BD Opportunity BUY Eligibility Authority Pending Item Binding Repair

## Primary Judgment

`PHASE23_BD_OPPORTUNITY_AUTHORITY_PENDING_ITEM_BINDING_SHORT_VALIDATION_PASS`

## Secondary Judgment

`READY_FOR_1BD_RUNTIME_RERUN = YES`

Supporting judgments:

- `OPPORTUNITY_RANKING_AUTHORITY_IDENTIFIED`
- `OPPORTUNITY_ROW_LINEAGE_BOUND`
- `RUNTIME_PLANNING_PRESERVES_OPPORTUNITY_AUTHORITY`
- `PENDING_ITEM_PRESERVES_OPPORTUNITY_AUTHORITY`
- `PENDING_SERIALIZATION_PRESERVES_OPPORTUNITY_AUTHORITY`
- `SUBMIT_ITEM_GUARD_OPPORTUNITY_PASS`
- `NEGATIVE_FAIL_CLOSED_PRESERVED`
- `PRODUCTION_DEMO_HISTORICAL_CONTRACT_PRESERVED`

## Root Cause

Phase23-BC後のSubmit blockerは、Opportunity Ranking authority自体の欠損ではなく、item-level authority binding欠損だった。

Runtime upstreamには `.runtime/runtime_state/buy_ai/2026-07-06/opportunity_rankings.json` が存在する一方、Strategy Planning order itemからPendingOrderItemへ以下がmaterializeされていなかった。

- `opportunity_artifact_path`
- `opportunity_artifact_hash`
- `opportunity_business_date`
- `opportunity_symbol`
- `opportunity_row_id`
- `opportunity_authority`
- `listed_info`

Submit Guardはitem単位でOpportunity BUY eligibilityを再検証できず、正しくfail-closedして `opportunity_evidence_missing` を返していた。

## Repair

Runtime Planningに `opportunity_artifact_path` を追加し、Opportunity Ranking artifactからBusiness Date / Feature Date / Symbol / Row identity / Artifact hashを含む `opportunity_authority` をplan itemへ明示伝播した。

Strategy Planning Authority adapterは、plan itemの `opportunity_authority` からPendingOrderItemの `listed_info` をmaterializeする。ここではsymbol一致、business date一致、artifact path/hash、row idが揃わない場合はauthorityを作らない。

Submit Guard側では、Opportunity artifact pathがある場合にrow identityを必須化し、artifact内の同一symbol・同一row identityと照合する。row identity mismatchは `opportunity_row_identity_mismatch` としてBLOCKする。

Shadow RuntimeはOpportunity Ranking artifactをRuntime Planningへ渡すようにし、Production / Demo / Historicalで同一Runtime Contractを使う。

## Canonical Fields

Canonical item-level fields:

- `opportunity_artifact_path`
- `opportunity_artifact_hash`
- `opportunity_business_date`
- `opportunity_feature_date`
- `opportunity_symbol`
- `opportunity_row_id`
- `opportunity_rank`
- `opportunity_buy_rank`
- `opportunity_status`
- `opportunity_eligibility`
- `opportunity_authority`
- `opportunity_source`
- `opportunity_row_authority_hash`
- `ranking_schema_version`
- `ranking_schema_name`
- `ranking_artifact_role`

`listed_info` は上場情報だけでなく、Submit item-level guardがBUY可否を再検証するためのOpportunity eligibility authority carrierとして扱う。

## Fail-closed

維持したBLOCK条件:

- opportunity evidence missing
- artifact hash mismatch
- business date mismatch
- future feature date
- symbol mismatch
- row identity missing
- row identity mismatch
- ranking authority missing
- eligibility not approved

BUY強制、minimum保証、latest lookup、symbolだけの後段推測、Historical専用fallbackは追加していない。

## Validation

Short validation only. Fresh-run / 1BD / 10BD / Broker Write / J-Quants fetchは実施していない。

- `py_compile`: PASS
- `tests/runtime_v2/test_phase23_i_strategy_planning_authority.py -k phase23_bd`: 2 passed
- `tests/runtime_v2/test_phase17_bv15_opportunity_buy_eligibility_contract.py`: 7 passed
- `tests/strategy/test_phase22_g_runtime_planning.py`: 16 passed
- `tests/runtime_v2/test_phase23_i_strategy_planning_authority.py`: 11 passed
- Pending / Submit policy regression: 15 passed
- Historical submit targeted regression: 8 passed, 1 deselected
- Combined submit/opportunity regression: 10 passed, 8 deselected
- Data Readiness pending/safety targeted regression: 1 passed, 9 deselected
- `git diff --check`: PASS

## Existing Run Preservation

No existing run artifact mutation was performed.

Preserved runs:

- `runtime-test-historical-smoke-20260730T050344341520Z`
- `runtime-test-historical-smoke-20260730T042431441297Z`
- `runtime-test-historical-smoke-20260730T033913848127Z`

Tree hashes are recorded in `existing_run_hash_preservation.json`.

## Modified Files

- `src/ai_fund_lab_v2/strategy/runtime_planning.py`
- `src/ai_fund_lab_v2/strategy/shadow_runtime.py`
- `src/ai_fund_lab_v2/runtime_v2/planning/strategy_authority.py`
- `src/ai_fund_lab_v2/runtime_v2/buy_ai/opportunity_eligibility.py`
- `src/ai_fund_lab_v2/runtime_v2/submit/pipeline.py`
- `tests/runtime_v2/test_phase23_i_strategy_planning_authority.py`
- `tests/strategy/test_phase22_g_runtime_planning.py`

## Evidence

Evidence directory:

`reports/phase23_bd_opportunity_buy_eligibility_authority_pending_item_binding_repair/`

Machine report:

`reports/phase_reports/phase23_bd_opportunity_buy_eligibility_authority_pending_item_binding_repair.json`

## Remaining Gap

Runtime fresh-run / 1BD validation is intentionally not executed in this task. Operator can run the next 1BD runtime validation after ChatGPT Evidence Review.
