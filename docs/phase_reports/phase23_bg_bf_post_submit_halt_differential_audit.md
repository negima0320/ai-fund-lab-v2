# Phase23-BG BF後 Submit HALT Differential Audit

## Primary Judgment

`PHASE23_BG_BF_POST_SUBMIT_DIFFERENTIAL_AUDIT_COMPLETE`

## Supporting Judgment

- `BF_MORNING_REGRESSION_RESOLVED = YES`
- `BD_OPPORTUNITY_AUTHORITY_PRESENT_IN_RUNTIME = YES`
- `SUBMIT_OPPORTUNITY_GUARD_STATUS = 8 PASS / 1 BLOCKED`
- `OPPORTUNITY_BLOCKER_RECURRED = NO`
- `NEW_DOWNSTREAM_BLOCKER_FOUND = YES`
- `HISTORICAL_ADAPTER_REACHED = YES`
- `REPAIR_REQUIRED = YES`
- `READY_FOR_1BD_RERUN = NO`

## Direct Root Cause

BF後Run `runtime-test-historical-smoke-20260730T063001897459Z` はMorningを通過し、Submit stageまで到達した。

Submit HALTの直接reasonは以下。

`submit completed with rejected/unknown/blocked items`

最下層reasonは、Submit item-level Opportunity BUY eligibility guardで、symbol `43780` が以下によりBLOCKされたこと。

`opportunity_no_buy_reason_present`

Canonical Opportunity row上の値は以下。

- `opportunity_no_buy_reason = high_downside_risk_score`
- `opportunity_row_id = opportunity-2026-07-06-43780-8-9e0dd3a8dd74dd04`
- `opportunity_artifact_hash = ee7abc999dd7ba786258e802da4cf9dce06740bb127ce2b70ba3c0d2653f1d3c`

## Opportunity Binding Result

BDのOpportunity Authority bindingは実Runtimeで成立した。

Runtime Planning:

- schema: `runtime_planning.v1`
- status: `PASS`
- plan count: `50`
- BUY count: `9`
- Opportunity authority fields: all 50 plans present

Submit Guard:

- item count: `9`
- Opportunity guard PASS: `8`
- Opportunity guard BLOCKED: `1`
- `opportunity_evidence_missing`: absent
- `opportunity_row_identity_missing`: absent
- `opportunity_row_identity_mismatch`: absent
- `opportunity_artifact_hash_mismatch`: absent
- `opportunity_business_date_mismatch`: absent
- `opportunity_symbol_mismatch`: absent

## Before / After

BD前Run `runtime-test-historical-smoke-20260730T050344341520Z`:

- Morning: PASS
- Runtime Planning: PASS / `runtime_planning.v1` / 50 plans
- Pending item count: 9
- Submit blocked count: 9
- Submitted count: 0
- Opportunity guard: 0 PASS / 9 BLOCKED

BF後Run `runtime-test-historical-smoke-20260730T063001897459Z`:

- Morning: PASS
- Runtime Planning: PASS / `runtime_planning.v1` / 50 plans
- Pending item count: 9
- Submit blocked count: 1
- Submitted count: 8
- Opportunity guard: 8 PASS / 1 BLOCKED

## Classification

- `BF_RUNTIME_PATH_RECOVERED`
- `BD_OPPORTUNITY_BINDING_PRESENT_IN_RUNTIME`
- `OPPORTUNITY_BLOCKER_RESOLVED`
- `NEW_ITEM_LEVEL_SUBMIT_BLOCKER`
- `HISTORICAL_ADAPTER_REACHED`
- `EXPECTED_FAIL_CLOSED`

同じSubmit HALTだが、BD前の `opportunity_evidence_missing` 再発ではない。

## Historical / As-of

Historical logical input manifest and as-of view are present and PASS.

- `historical_asof_view.json`: PASS
- `logical_input_manifest.json`: PASS
- `run_scoped_asof_authority_missing`: absent
- `historical_logical_source_manifest_missing`: absent

Historical simulated submission boundary reached for 8 items. Broker write is false.

## Canonical Repair Owner

次のrepair ownerはSubmit Guardではない。Submit Guardはcanonical Opportunity rowの `no_buy_reason` を見て正しくfail-closedしている。

Repair boundary candidate:

`Opportunity selection / Portfolio Construction / Strategy Planning boundary`

BUY pending itemとして出す前に、`opportunity_no_buy_reason` を持つrowを除外またはREVIEW_REQUIREDへ寄せるContract整合が必要。

## Deliverables

Human:

`docs/phase_reports/phase23_bg_bf_post_submit_halt_differential_audit.md`

Machine:

`reports/phase_reports/phase23_bg_bf_post_submit_halt_differential_audit.json`

Evidence:

`reports/phase23_bg_bf_post_submit_halt_differential_audit/`

## Existing Run Preservation

対象Run artifactはread-onlyで扱った。hash preservationは `existing_run_hash_preservation.json` に記録済み。

## Next Task Candidate

`Phase23-BH Opportunity no_buy_reason Planning-Submit Boundary Alignment Audit/Repair`
