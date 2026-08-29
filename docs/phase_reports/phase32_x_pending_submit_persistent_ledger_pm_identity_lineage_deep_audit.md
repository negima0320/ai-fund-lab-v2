# Phase32-X Pending / Submit / Persistent-Ledger PM Identity Lineage Deep Audit

## Executive Summary

Phase32-X confirms a mandatory actual-path provenance defect in the Post-T/V fresh run. The real 2022-10-04 83060 PM EXIT decision exists and is detailed:

- `pm_decision_id = pm-2022-10-04-83060-exit`
- `decision_reason = trend_and_opportunity_broken`
- `position_campaign_id = pc-228f21b28c9b7664-83060-0001`

The daily fill / realized-slice artifacts preserve that identity, but the persistent ledger path does not. The first durable-loss boundary is the strategy-origin pending/order-plan materialization before submit: the actual pending item has top-level `source_pm_decision_id = ""`, no top-level or shallow lineage `position_campaign_id`, no nested real PM decision id, and a semantically wrong nested `strategy_authority_lineage.item.pm_decision_id = runtime-current-83060`.

Submit, historical broker snapshot normalization, and execution ledger projection then preserve the blank canonical provenance. They are downstream carriers, not the first loss point. The daily fill path is not using the same provenance path as the persistent ledger path; it is enriched separately enough to show the correct PM id/campaign and therefore masks the durable-ledger defect.

The defect is universal in the audited early sample through 2022-10-27: all sampled PM EXIT fills have correct daily provenance, while matching persistent order/execution ledger rows have blank PM id and blank campaign id.

Recommendation: stop relying on the current 650BD run for re-entry semantic acceptance. Perform a narrow production repair at pending/order-plan materialization for strategy-origin `SELL_EXIT` items, then require a new user-operated fresh validation. Do not broaden the repair into REENTRY/Cash/PC/MCC/Risk Pacing.

## Run Identity

- Current Post-T/V run: `runtime-test-historical-extended-smoke-20260827T035349208209Z`
- Evidence root: `reports/runtime_tests/runs/runtime-test-historical-extended-smoke-20260827T035349208209Z`
- Runtime root audited read-only: `.runtime`
- Focus lifecycle: `83060`, 2022-10-04 EXIT
- Audit window: 2022-10-04 through 2022-10-27 artifacts available at audit time

No fresh run, resume, replay, backtest, production code edit, config edit, schema edit, threshold edit, model edit, or runtime-state mutation was performed.

## 83060 PM Source Evidence

Source artifact:

- `reports/runtime_tests/runs/runtime-test-historical-extended-smoke-20260827T035349208209Z/daily/2022-10-04/position_management/pm_decisions.json`

Observed 83060 PM row:

| Field | Value |
|---|---|
| `decision_type` | `EXIT` |
| `decision_status` | `SELL_FULL_POSITION` |
| `pm_decision_id` | `pm-2022-10-04-83060-exit` |
| `decision_reason` | `trend_and_opportunity_broken` |
| `reason_codes` | `["trend_and_opportunity_broken"]` |
| `position_campaign_id` | `pc-228f21b28c9b7664-83060-0001` |

This is the authoritative PM identity expected downstream.

## Actual Lineage Table

| Boundary | 83060 observed identity | Campaign | Assessment |
|---|---:|---:|---|
| PM decision artifact | `pm-2022-10-04-83060-exit` | `pc-228f21b28c9b7664-83060-0001` | Correct source |
| Strategy runtime planning | `strategy_authority_lineage.item.pm_decision_id = runtime-current-83060` | no canonical PM campaign in shallow lineage | Wrong semantic alias appears before pending |
| Pending history item | top-level `source_pm_decision_id = ""`; nested real PM id absent | top-level absent/blank; nested campaign absent | First durable loss boundary |
| Submit command/provenance selection | command receives blank PM id/campaign from pending | blank | Downstream carrier |
| Submit ledger order record | `source_decision_id = ""`, `source_pm_decision_id = ""`, `source_decision_type = SELL_EXIT` | `""` | Blank canonical PM identity persisted |
| Historical broker order snapshot | `source_decision_id = ""`, `source_pm_decision_id = ""`, `source_decision_type = ""` | `""` | Snapshot preserves blank submit evidence |
| Normalized broker order | blank PM id/campaign | `""` | Normalizer preserves snapshot fields |
| Persistent ledger execution | `source_decision_id = ""`, `source_pm_decision_id = ""`, `source_decision_type = ""` | `""` | Strict-prior bridge cannot match PM evidence |
| Daily fill artifact | `source_decision_id = pm-2022-10-04-83060-exit`, `source_decision_type = EXIT` | `pc-228f21b28c9b7664-83060-0001` | Correct but separate/enriched path |
| Realized slice artifact | `source_decision_id = pm-2022-10-04-83060-exit`, `source_decision_type = EXIT` | `pc-228f21b28c9b7664-83060-0001` | Correct but separate/enriched path |

## Pending Serialization Audit

Actual pending artifact:

- `.runtime/pending_order_plan/history/2022-10-04/pending-order-plan-buy-review-sell-continuation-2022-10-04-14a07a492d44.json`

Actual 83060 pending item:

| Field | Value |
|---|---:|
| `pending_plan_id` | `pending-order-plan-buy-review-sell-continuation-2022-10-04-14a07a492d44` |
| `pending_item_id` | `strategy-a824b5d9f1be1680ea98` |
| `side` | `SELL` |
| `quantity` | `100.0` |
| `source_decision_type` | `SELL_EXIT` |
| `source_pm_decision_id` | `""` |
| `source_pm_business_date` | `2022-10-04` |
| `source_position_symbol` | `83060` |
| `position_campaign_id` | absent/null |
| `quantity_contract.source_decision_id` | absent/null |
| `quantity_contract.source_pm_decision_id` | absent/null |
| `quantity_contract.position_campaign_id` | absent/null |
| `strategy_authority_lineage.source_decision_id` | absent/null |
| `strategy_authority_lineage.source_pm_decision_id` | absent/null |
| `strategy_authority_lineage.position_campaign_id` | absent/null |
| `strategy_authority_lineage.item.pm_decision_id` | `runtime-current-83060` |

This establishes that the real PM decision id is not merely lost in submit serialization. It is already absent from the serialized pending/order-plan payload consumed by submit.

## Runtime-Current Identity Semantics

`runtime-current-83060` is not a PM decision id. In the 2022-10-04 strategy runtime-planning artifact it is produced as current position membership identity:

- `current_position_membership_authority.position_reference = runtime-current-83060`
- `current_position_membership_authority.authority = runtime_owned_current_position_membership`
- `position_state_as_of = 2022-10-03`

However the same value appears under `strategy_authority_lineage.item.pm_decision_id`. That is an alias collision: a current-position/current-membership identity is occupying a PM-decision-named field. The submit path did not propagate `runtime-current-83060` into `source_pm_decision_id` because its provenance lookup only inspects top-level and shallow mappings, not `strategy_authority_lineage.item`. That prevented a wrong durable PM id, but left the canonical id blank.

## Submit And Ledger Code Path

Relevant code boundaries:

- `src/ai_fund_lab_v2/runtime_v2/planning/strategy_authority.py:738` writes pending `source_decision_type = intent`.
- `src/ai_fund_lab_v2/runtime_v2/planning/strategy_authority.py:739` writes `source_pm_decision_id = plan.get("pm_position_reference") or ""`. In the actual 83060 strategy-origin SELL item this is blank.
- `src/ai_fund_lab_v2/runtime_v2/planning/sell_pipeline.py:2112` defines `_pending_item_with_sell_decision_lineage`, which would populate top-level `source_pm_decision_id`, shallow lineage, quantity contract, and campaign when called with a matching `SellExitDecision`.
- `src/ai_fund_lab_v2/runtime_v2/submit/guards.py:118` to `:122` builds submit command provenance from top-level pending item, shallow strategy lineage, and quantity contract.
- `src/ai_fund_lab_v2/runtime_v2/submit/pipeline.py:1624` to `:1677` builds submit-ledger provenance from pending item and command fields with the same shallow precedence.
- `src/ai_fund_lab_v2/runtime_v2/execution/ledger_projection.py:21` to `:59` and `:112` to `:128` project normalized broker orders/executions into ledger records by preserving broker snapshot provenance fields.

The intended Phase32-T helper exists, but the actual fresh-run pending item is strategy-origin (`pending_item_id = strategy-a824b5d9f1be1680ea98`) and does not show the helper's canonical overlay. Therefore the repair missed the production-equivalent path that materializes the pending order consumed by submit.

## Daily Fill Vs Persistent Ledger Path

Daily fill and realized-slice artifacts for 83060 are correct:

| Artifact | PM id | Decision type | Campaign |
|---|---:|---:|---:|
| `daily/2022-10-04/execution/fills.json` | `pm-2022-10-04-83060-exit` | `EXIT` | `pc-228f21b28c9b7664-83060-0001` |
| `daily/2022-10-04/execution/realized_slices.json` | `pm-2022-10-04-83060-exit` | `EXIT` | `pc-228f21b28c9b7664-83060-0001` |

Persistent ledger artifacts are not correct:

| Artifact | PM id | Decision type | Campaign |
|---|---:|---:|---:|
| `.runtime/persistent_ledger/orders.jsonl`, submit order | `""` | `SELL_EXIT` | `""` |
| `.runtime/persistent_ledger/orders.jsonl`, broker order projection | `""` | `""` | `""` |
| `.runtime/persistent_ledger/executions.jsonl` | `""` | `""` | `""` |

Conclusion: daily fill / realized slice and persistent ledger do not use the same authoritative provenance path. The strict-prior bridge depends on persistent execution/order ledger identity, so it sees `pm_exit_reason_matched_close_count = 0` despite correct daily fill enrichment.

## Campaign Lineage

The campaign id is present in the PM source and daily fill/slice artifacts, but absent from the pending item top-level, shallow strategy lineage, quantity contract, submit-ledger order, broker snapshot, normalized order, projected order, and execution ledger row.

First campaign drop boundary is the same as the PM id drop boundary: strategy-origin pending/order-plan materialization.

## Multi-Symbol Sample

The early sample through 2022-10-27 is systemic. Every sampled PM EXIT had a correct daily fill PM id/campaign and blank persistent ledger PM id/campaign.

| Date | Symbol | PM id | Daily fill PM id | Ledger order PM id | Ledger execution PM id |
|---|---:|---:|---:|---:|---:|
| 2022-10-04 | 83060 | `pm-2022-10-04-83060-exit` | correct | `""` | `""` |
| 2022-10-04 | 37820 | `pm-2022-10-04-37820-exit` | correct | `""` | `""` |
| 2022-10-04 | 89180 | `pm-2022-10-04-89180-exit` | correct | `""` | `""` |
| 2022-10-05 | 41650 | `pm-2022-10-05-41650-exit` | correct | `""` | `""` |
| 2022-10-07 | 44220 | `pm-2022-10-07-44220-exit` | correct | `""` | `""` |
| 2022-10-11 | 45750 | `pm-2022-10-11-45750-exit` | correct | `""` | `""` |
| 2022-10-12 | 33500 | `pm-2022-10-12-33500-exit` | correct | `""` | `""` |
| 2022-10-13 | 70640 | `pm-2022-10-13-70640-exit` | correct | `""` | `""` |
| 2022-10-13 | 92420 | `pm-2022-10-13-92420-exit` | correct | `""` | `""` |
| 2022-10-13 | 73590 | `pm-2022-10-13-73590-exit` | correct | `""` | `""` |
| 2022-10-17 | 76470 | `pm-2022-10-17-76470-exit` | correct | `""` | `""` |
| 2022-10-17 | 44870 | `pm-2022-10-17-44870-exit` | correct | `""` | `""` |
| 2022-10-17 | 17570 | `pm-2022-10-17-17570-exit` | correct | `""` | `""` |
| 2022-10-18 | 96100 | `pm-2022-10-18-96100-exit` | correct | `""` | `""` |
| 2022-10-19 | 73560 | `pm-2022-10-19-73560-exit` | correct | `""` | `""` |
| 2022-10-21 | 66190 | `pm-2022-10-21-66190-exit` | correct | `""` | `""` |
| 2022-10-24 | 48330 | `pm-2022-10-24-48330-exit` | correct | `""` | `""` |
| 2022-10-25 | 79220 | `pm-2022-10-25-79220-exit` | correct | `""` | `""` |
| 2022-10-26 | 62270 | `pm-2022-10-26-62270-exit` | correct | `""` | `""` |
| 2022-10-26 | 66630 | `pm-2022-10-26-66630-exit` | correct | `""` | `""` |
| 2022-10-27 | 93180 | `pm-2022-10-27-93180-exit` | correct | `""` | `""` |
| 2022-10-27 | 58200 | `pm-2022-10-27-58200-exit` | correct | `""` | `""` |

This is not isolated to 83060.

## Phase32-T Test Gap

`tests/runtime_v2/test_phase17_g_historical_submit_guard_and_fill.py` contains `test_phase32_t_actual_sell_path_populates_persistent_ledger_pm_and_campaign_provenance`. The fixture builds a synthetic pending item and explicitly applies `_pending_item_with_sell_decision_lineage(...)` before writing pending. That proves the downstream submit/execution path works when canonical fields are already attached to pending.

The fixture missed the real path because it did not reproduce the production-equivalent strategy-origin order plan where:

- pending item id starts with `strategy-...`
- top-level `source_pm_decision_id` is blank
- shallow lineage lacks `source_pm_decision_id`
- quantity contract lacks PM id/campaign
- nested `strategy_authority_lineage.item.pm_decision_id` contains `runtime-current-*`

The missing regression is therefore a real serialized pending/order-plan path test, not another unit test of the downstream projection after manual lineage overlay.

## Defect Boundary And Repair Readiness

First wrong/drop boundary:

- Component: strategy planning / sell-continuation pending materialization
- Artifact boundary: `.runtime/runtime_state/strategy_planning/2022-10-04/order_plan.json` and `.runtime/pending_order_plan/history/2022-10-04/...json`
- First wrong value: `strategy_authority_lineage.item.pm_decision_id = runtime-current-83060`
- First canonical drop: top-level `source_pm_decision_id = ""`; `position_campaign_id` absent/blank; no shallow lineage or quantity-contract PM id/campaign

Minimal repair boundary:

- Attach same-day canonical PM EXIT lineage before pending/order-plan serialization for strategy-origin `SELL_EXIT` items.
- Populate top-level `source_pm_decision_id`, `source_decision_id` if supported by the payload contract, `source_decision_type = EXIT` or maintain a clearly mapped submit value, `source_pm_business_date`, `source_position_symbol`, and `position_campaign_id`.
- Mirror canonical values into shallow `strategy_authority_lineage` and `quantity_contract` where existing submit/normalizer fallbacks already look.
- Do not infer PM identity from nested `strategy_authority_lineage.item.pm_decision_id` when it starts with `runtime-current-`; that value should be treated as current-position identity, not PM decision authority.
- Add regression using a real serialized strategy-origin `SELL_EXIT` pending item with nested `runtime-current-*` alias and blank top-level fields, asserting that submit, broker snapshot, persistent order ledger, persistent execution ledger, and strict-prior bridge all carry the real PM id/campaign.

Production repair is justified and implementation-ready within pending/order-plan materialization and focused test coverage only. No strategy logic changes are justified.

## Resume / Continuation Recommendation

The current 650BD run should not continue as semantic acceptance evidence. Because persistent ledger PM/campaign provenance is blank systemically, downstream strict-prior materialization remains unable to match detailed PM EXIT reasons even though daily fill artifacts look correct.

Next step is a narrow production repair at the pending materialization boundary, followed by user-operated short fresh validation from a clean run. Do not resume this run for acceptance.

## Final Judgments

PHASE32_X_REAL_PM_DECISION_ID = pm-2022-10-04-83060-exit

PHASE32_X_RUNTIME_CURRENT_ID = runtime-current-83060

PHASE32_X_RUNTIME_CURRENT_ID_SEMANTIC = CURRENT_POSITION_MEMBERSHIP_OR_POSITION_REFERENCE_NOT_PM_DECISION

PHASE32_X_FIRST_PM_ID_WRONG_VALUE_OR_DROP_BOUNDARY = STRATEGY_ORIGIN_SELL_EXIT_ORDER_PLAN_TO_PENDING_MATERIALIZATION

PHASE32_X_FIRST_CAMPAIGN_ID_DROP_BOUNDARY = STRATEGY_ORIGIN_SELL_EXIT_ORDER_PLAN_TO_PENDING_MATERIALIZATION

PHASE32_X_PENDING_TOP_LEVEL_PM_ID_POPULATED = NO

PHASE32_X_PENDING_NESTED_REAL_PM_ID_EXISTS = NO

PHASE32_X_SUBMIT_FIELD_PRECEDENCE_CORRECT = PARTIAL

PHASE32_X_DAILY_FILL_AND_LEDGER_USE_SAME_PROVENANCE_PATH = NO

PHASE32_X_RUNTIME_CURRENT_OVERWRITE_DEFECT = PARTIAL

PHASE32_X_ALIAS_COLLISION_DEFECT = YES

PHASE32_X_SERIALIZATION_DROP_DEFECT = PARTIAL

PHASE32_X_SUBMIT_PROVENANCE_SELECTION_DEFECT = PARTIAL

PHASE32_X_MULTI_SYMBOL_SCOPE = UNIVERSAL

PHASE32_X_PHASE32_T_TEST_MISSED_REAL_PATH_REASON = TEST_MANUALLY_APPLIED_SELL_DECISION_LINEAGE_TO_SYNTHETIC_PENDING_AND_DID_NOT_REPRODUCE_STRATEGY_ORIGIN_SERIALIZED_SELL_EXIT_PENDING_WITH_RUNTIME_CURRENT_ALIAS_AND_BLANK_TOP_LEVEL_PM_FIELDS

PHASE32_X_MANDATORY_DEFECT = YES

PHASE32_X_PRODUCTION_REPAIR_JUSTIFIED = YES

PHASE32_X_IMPLEMENTATION_READY = YES

PHASE32_X_MINIMAL_REPAIR_BOUNDARY = PENDING_ORDER_PLAN_MATERIALIZATION_FOR_STRATEGY_ORIGIN_SELL_EXIT_ITEMS_ATTACH_CANONICAL_PM_EXIT_ID_AND_POSITION_CAMPAIGN_BEFORE_SUBMIT

PHASE32_X_NEXT_STEP = IMPLEMENT_NARROW_PENDING_MATERIALIZATION_REPAIR_AND_ADD_REAL_SERIALIZED_PENDING_REGRESSION_THEN_USER_OPERATED_SHORT_FRESH_VALIDATION
