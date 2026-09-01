# Phase32-BW — Post-BQ/BV Actual Reconsidered FULL EXIT Early-Run READ-ONLY Audit

## Scope

- Target run: `runtime-test-historical-extended-smoke-20260831T234344371102Z`
- Audit mode: READ-ONLY
- Snapshot audited: completed business days through `2022-11-16`
- Run status at snapshot: `RUNNING`
- Next job observed at snapshot: `2022-11-17:sell_planning`
- Baseline comparison run: `runtime-test-historical-extended-smoke-20260831T003243720082Z`

No code, config, model, threshold, weight, runtime state, Pending, Ledger, resume, recover, replay, or fresh-run mutation was performed for this audit. The target Historical run was not interrupted.

## Evidence Coverage

Evidence inspected:

- `reports/runtime_tests/runs/runtime-test-historical-extended-smoke-20260831T234344371102Z/run_state.json`
- target daily artifacts through `2022-11-16`
- `.runtime/runtime_state/sell_pipeline/<business_date>/order_plan.json`
- target `daily/<business_date>/execution/fills.json`
- target PM and Strategy artifacts under `daily/<business_date>/position_management` and `daily/<business_date>/strategy`
- target valuation artifacts for portfolio comparison
- old baseline valuation/position artifacts for common completed dates

Because the target run was still running while audited, this report intentionally fixes the audited window at the snapshot read through `2022-11-16`.

## Actual Reconsidered FULL EXIT Events

`ACTUAL_RECONSIDERED_FULL_EXIT_COUNT = 8`

All eight promoted events satisfy the actual Production shape:

PM `REDUCE` -> lot-blocked reduce (`REDUCE_UNEXECUTABLE_DUE_TO_DISCRETE_LOT`) -> BO/BQ `SHADOW_FULL_EXIT` -> `PM_REDUCE_LOT_BLOCKED_RECONSIDERED_FULL_EXIT` -> ordinary `SELL_EXIT` order materialization -> one SELL fill.

| Date | Symbol | Campaign ID | PM decision | Raw REDUCE | Unit | Executable REDUCE | BO/BQ result | Production action | SELL qty | Order/Pending item | Fill count |
|---|---:|---|---|---:|---:|---:|---|---|---:|---|---:|
| 2022-10-07 | 45750 | `pc-225e8fad91f72551-45750-0001` | `pm-2022-10-07-45750-reduce` | 25 | 100 | 0 | `SHADOW_FULL_EXIT` | `EXIT` | 100 | `opi-sell-exit-pm-45750-002` | 1 |
| 2022-10-24 | 92540 | `pc-91b32ced93dbc97f-92540-0001` | `pm-2022-10-24-92540-reduce` | 25 | 100 | 0 | `SHADOW_FULL_EXIT` | `EXIT` | 100 | `opi-sell-exit-pm-92540-001` | 1 |
| 2022-10-25 | 65500 | `pc-0b3e43dadaf2b6fb-65500-0001` | `pm-2022-10-25-65500-reduce` | 33 | 100 | 0 | `SHADOW_FULL_EXIT` | `EXIT` | 100 | `opi-sell-exit-pm-65500-002` | 1 |
| 2022-11-02 | 47810 | `pc-06be4af76c862087-47810-0001` | `pm-2022-11-02-47810-reduce` | 25 | 100 | 0 | `SHADOW_FULL_EXIT` | `EXIT` | 100 | `opi-sell-exit-pm-47810-001` | 1 |
| 2022-11-10 | 89380 | `pc-df2e4c700cbf6ff6-89380-0001` | `pm-2022-11-10-89380-reduce` | 25 | 100 | 0 | `SHADOW_FULL_EXIT` | `EXIT` | 100 | `opi-sell-exit-pm-89380-002` | 1 |
| 2022-11-14 | 15180 | `pc-8c7bcd6dc57e6a44-15180-0001` | `pm-2022-11-14-15180-reduce` | 25 | 100 | 0 | `SHADOW_FULL_EXIT` | `EXIT` | 100 | `opi-sell-exit-pm-15180-003` | 1 |
| 2022-11-16 | 63350 | `pc-2740a964888cc8ad-63350-0001` | `pm-2022-11-16-63350-reduce` | 25 | 100 | 0 | `SHADOW_FULL_EXIT` | `EXIT` | 100 | `opi-sell-exit-pm-63350-001` | 1 |
| 2022-11-16 | 35280 | `pc-f5dbb4a94a8f0bc3-35280-0001` | `pm-2022-11-16-35280-reduce` | 25 | 100 | 0 | `SHADOW_FULL_EXIT` | `EXIT` | 100 | `opi-sell-exit-pm-35280-002` | 1 |

For every promoted event, `future_information_used=false`, `later_pnl_used=false`, and `final_campaign_outcome_used=false` in the BO/BQ PIT evidence. No promotion relied on later outcomes.

## Mandatory 45750 Trace

`2022_10_07_45750_BQ_TRIGGER_CONFIRMED = YES`

Observed path:

- `2022-10-06`: 45750 BUY_NEW evidence exists with campaign `pc-225e8fad91f72551-45750-0001`.
- `2022-10-07`: PM authored `pm-2022-10-07-45750-reduce`.
- PM action: `REDUCE`.
- Raw desired reduce quantity: `25`.
- Trading unit: `100`.
- Executable reduce quantity: `0`.
- Lot block reason: `REDUCE_UNEXECUTABLE_DUE_TO_DISCRETE_LOT`.
- BO/BQ semantic result: `SHADOW_FULL_EXIT`.
- Production reconsideration reason: `PM_REDUCE_LOT_BLOCKED_RECONSIDERED_FULL_EXIT`.
- Ordinary SELL_EXIT order materialized as `opi-sell-exit-pm-45750-002`.
- SELL quantity: `100`.
- Fill: exactly one SELL fill, order `sha256:e326f0886581d33a18c9d327bd03bc6c3f26a92e6eedc163cfc11af1748cf487`.
- Fill campaign: `pc-225e8fad91f72551-45750-0001`.
- Fill source decision: `pm-2022-10-07-45750-reduce`.

`45750_FULL_QUANTITY_EXIT_CONFIRMED = YES`

The 45750 disappearance from holdings is explained by the intended BQ Production FULL EXIT path. No duplicate REDUCE/EXIT order or duplicate fill was observed.

`45750_CAMPAIGN_PROVENANCE_PRESERVED = YES`

45750 preserved campaign/provenance through order plan, Pending item identity, historical broker evidence, execution/fill, and current valuation evidence.

## 88480 Path

`88480_ACTUAL_EXIT_PATH = NATIVE_PM_EXIT_NOT_BQ_RECONSIDERED_FULL_EXIT`

Observed:

- `2022-11-04`: 88480 BUY fill, quantity `100`, campaign `pc-e999f2012370df67-88480-0001`, source decision `rp-2022-11-04-88480-buy_new-2efffe766aa78221`.
- `2022-11-07`: PM reason codes include `trend_and_opportunity_broken`.
- `2022-11-07`: SELL_EXIT fill, quantity `100`, campaign `pc-e999f2012370df67-88480-0001`, source decision `rp-2022-11-07-88480-sell_exit-63ac4729ae1e1ff7`.

Therefore 88480 was not a lot-blocked REDUCE reconsideration. It exited by ordinary/native PM EXIT logic.

## Additional BQ Events

`ADDITIONAL_NEW_RUN_BQ_EVENTS_FOUND = YES`

Beyond the mandatory 45750 case, seven additional promoted BQ Production FULL EXIT events were observed by `2022-11-16`: 92540, 65500, 47810, 89380, 15180, 63350, and 35280.

This confirms that the new run diverged from the old BR episode list after the first BQ action, so BW did not rely on the old BR list as an event source.

## Non-Promoted Lot-Blocked REDUCE

`ACTUAL_NON_PROMOTED_LOT_BLOCKED_REDUCE_COUNT = 50`

Classification:

- `SHADOW_INSUFFICIENT_EVIDENCE`: 47
- `SHADOW_HOLD`: 2
- no explicit BO record found in the paired reconsideration list: 1

All 50 non-promoted lot-blocked REDUCE decisions preserved:

- `effective_action = NO_SELL_ORDER`
- `intentional_no_order = true`
- `pending_order_generated = false`

No order-plan item was found tied to a non-promoted source PM decision.

`NON_PROMOTED_NO_ORDER_PRESERVED = YES`

`BT_REAL_PATH_ACCEPTANCE = PASS`

The earlier BT failure mode, where non-promoted HOLD/INSUFFICIENT paths could leak into fail-closed or malformed promoted paths, was not reproduced through the audited window.

## Campaign and Provenance

Order-plan campaign propagation is accepted for all promoted FULL EXIT events:

- Every promoted order-plan item had a non-empty `position_campaign_id`.
- Every promoted order-plan campaign matched its PM campaign authority.
- Every promoted fill had exactly one matching campaign ID.
- No promoted fill created a different campaign family.

Duplicate/idempotency:

- Each promoted event produced exactly one SELL fill.
- No promoted symbol/date produced duplicate BQ SELL fills.
- No duplicate REDUCE plus FULL EXIT pair was observed.

`DUPLICATE_SELL_OBSERVED = NO`

`CAMPAIGN_REGENERATION_OBSERVED = NO`

`SYMBOL_ONLY_REATTACHMENT_OBSERVED = NO_CONCRETE_EVIDENCE`

Important nuance:

Some strategy-sourced SELL_EXIT fills after the BQ promotion carry a Strategy runtime-planning `source_decision_id` in execution/fill evidence while preserving the PM campaign ID and PM source decision in order-plan evidence. For 45750 and 15180 the fill source decision remains the PM reduce id; for 92540, 65500, 47810, 89380, and 63350 the fill source decision is a Strategy `rp-...-sell_exit...` id while the fill campaign ID still matches the PM/open campaign authority. This did not produce a wrong campaign or duplicate order, but it means strict end-to-end source-decision provenance is not uniform across all promoted fills.

`BV_CAMPAIGN_PROPAGATION_REAL_PATH_ACCEPTANCE = PASS_FOR_CAMPAIGN_IDENTITY / PARTIAL_FOR_SOURCE_DECISION_UNIFORMITY`

## PIT Semantic Correctness

Promoted event classifications:

| Date | Symbol | Classification | Notes |
|---|---:|---|---|
| 2022-10-07 | 45750 | `SEMANTICALLY_JUSTIFIED` | risk vote count 3; weak/elevated-risk dimensions; no future/outcome use |
| 2022-10-24 | 92540 | `SEMANTICALLY_JUSTIFIED` | trend weak, participation weak, downside/reversal elevated; no future/outcome use |
| 2022-10-25 | 65500 | `SEMANTICALLY_JUSTIFIED` | risk vote count 3; relative return about -6.76%; no future/outcome use |
| 2022-11-02 | 47810 | `SEMANTICALLY_JUSTIFIED` | BO artifact PASS; weaker mixed/supportive components exist but accepted contract still records decisive FULL_EXIT |
| 2022-11-10 | 89380 | `SEMANTICALLY_JUSTIFIED` | trend weak, participation weak, downside/reversal elevated; no future/outcome use |
| 2022-11-14 | 15180 | `QUESTIONABLE` | BO artifact PASS, but risk vote count 1 with supportive participation and manageable downside; this is a semantic threshold review candidate, not a correctness failure |
| 2022-11-16 | 63350 | `SEMANTICALLY_JUSTIFIED` | participation weak and downside elevated; no future/outcome use |
| 2022-11-16 | 35280 | `SEMANTICALLY_JUSTIFIED` | reversal elevated and risk vote count 3; no future/outcome use |

`PROMOTED_EVENTS_SEMANTICALLY_JUSTIFIED = 7/8`

`QUESTIONABLE_PROMOTION_COUNT = 1`

The 15180 case should be reviewed in later design analysis if the team wants tighter evidence-tier semantics. It is not classified as an implementation defect in this audit because the recorded BO/BQ contract returned `SHADOW_FULL_EXIT` with PIT validation PASS and no future-information use.

## Early Descriptive Outcome

Outcome use here is descriptive only and was not used to judge correctness or Production eligibility.

Early avoided-loss-like cases observed from available post-exit prices:

- 92540: sell at `1811.0`; later available close through early November was lower.
- 65500: sell at `198.0`; later available close through early November was lower.

Early false-exit/rebound-like or too-short cases:

- 45750: later early closes rebounded above the 2022-10-07 sell price.
- 89380: later early movement was near flat/slightly above sell.
- 47810: later valuation evidence was incomplete/insufficient in the short horizon.
- 15180, 63350, 35280: too little post-event evidence at the snapshot.

`EARLY_AVOIDED_LOSS_CASES = 2_DESCRIPTIVE`

`EARLY_FALSE_EXIT_CASES = 2_DESCRIPTIVE_PLUS_SHORT_HORIZON_CASES`

`OUTCOME_HORIZON_SUFFICIENT = NO`

## Portfolio Divergence Versus Old Baseline

`FIRST_ACTUAL_PORTFOLIO_DIVERGENCE_DATE = 2022-10-07`

This matches Phase32-BR's expected first BQ divergence date.

Common-date comparison:

| Date | New cash | New market value | New total equity | Old cash | Old market value | Old total equity | Notes |
|---|---:|---:|---:|---:|---:|---:|---|
| 2022-10-06 | 80,840 | 991,260 | 1,072,100 | 80,840 | 991,260 | 1,072,100 | no divergence |
| 2022-10-07 | 147,240 | 921,400 | 1,068,640 | 79,440 | 986,700 | 1,066,140 | new run exits 45750; old baseline still holds 45750 |
| 2022-11-16 | 254,480 | 838,080 | 1,092,560 | 111,670 | 971,080 | 1,082,750 | early divergence accumulated |

`CURRENT_EQUITY_VS_OLD_BASELINE = HIGHER_BY_9,810_ON_2022_11_16`

`CURRENT_CASH_EXPOSURE_VS_OLD_BASELINE = CASH_HIGHER_BY_142,810_AND_MARKET_VALUE_LOWER_BY_133,000_ON_2022_11_16`

## Runtime Safety

Through `2022-11-16`:

- The target run was still `RUNNING`.
- No BQ/BV-related HALT was observed.
- The previously repaired 2022-10-07 BQ FULL EXIT boundary completed sell planning, submit, execution, current valuation, and day completion.
- All promoted FULL EXIT events had one fill and no duplicate.
- All non-promoted lot-blocked REDUCE events remained NO_ORDER.
- No `MISSING_CAMPAIGN_ID` halt was observed.

`BQ_BV_RUNTIME_SAFETY_ACCEPTED_SO_FAR = YES_WITH_SOURCE_DECISION_UNIFORMITY_NOTE`

## Repair/Change Assessment

`PRODUCTION_CHANGE_REQUIRED_FROM_THIS_AUDIT = NO_FOR_BQ_BV_RUNTIME_SAFETY_AND_CAMPAIGN_IDENTITY`

There is no evidence in this audited window that BQ/BV Production FULL EXIT requires an immediate correctness repair. The core behavior is active on actual fresh-run artifacts, exits full 100-share positions when promoted, preserves campaign identity, avoids duplicate side effects, and leaves non-promoted lot-blocked REDUCE as NO_ORDER.

One follow-up should be tracked outside this READ-ONLY audit:

- Source-decision provenance is not uniform in fills for all promoted events. Some fills use PM reduce ids, while others use Strategy `rp-...-sell_exit...` ids despite campaign identity remaining correct. This is not an observed campaign split, but it is a provenance consistency item to keep on the integration checklist.

`LONGER_EVIDENCE_REQUIRED = YES`

Reasons:

- The audited window is early: only through `2022-11-16`.
- Several promoted events have insufficient post-event horizon for economic characterization.
- The 15180 promotion is semantically questionable enough to deserve more examples before changing any policy.
- Accepted long-run judgment should wait for broader regime coverage.

## Required Final Answers

1. `LATEST_COMPLETED_BUSINESS_DATE = 2022-11-16`
2. `ACTUAL_RECONSIDERED_FULL_EXIT_COUNT = 8`
3. `ACTUAL_RECONSIDERED_FULL_EXIT_EVENTS = 2022-10-07/45750, 2022-10-24/92540, 2022-10-25/65500, 2022-11-02/47810, 2022-11-10/89380, 2022-11-14/15180, 2022-11-16/63350, 2022-11-16/35280`
4. `45750_BQ_ACTUAL_PATH_CONFIRMED = YES`
5. `45750_FULL_QUANTITY_EXIT_CONFIRMED = YES`
6. `45750_CAMPAIGN_PROVENANCE_PRESERVED = YES`
7. `88480_ACTUAL_EXIT_PATH = NATIVE_PM_EXIT_NOT_BQ_RECONSIDERED_FULL_EXIT`
8. `ADDITIONAL_NEW_RUN_BQ_EVENTS_FOUND = YES`
9. `ACTUAL_NON_PROMOTED_LOT_BLOCKED_REDUCE_COUNT = 50`
10. `NON_PROMOTED_NO_ORDER_PRESERVED = YES`
11. `BT_REAL_PATH_ACCEPTANCE = PASS`
12. `BV_CAMPAIGN_PROPAGATION_REAL_PATH_ACCEPTANCE = PASS_FOR_CAMPAIGN_IDENTITY / PARTIAL_FOR_SOURCE_DECISION_UNIFORMITY`
13. `DUPLICATE_SELL_OBSERVED = NO`
14. `CAMPAIGN_REGENERATION_OBSERVED = NO`
15. `SYMBOL_ONLY_REATTACHMENT_OBSERVED = NO_CONCRETE_EVIDENCE`
16. `PROMOTED_EVENTS_SEMANTICALLY_JUSTIFIED = 7/8`
17. `QUESTIONABLE_PROMOTION_COUNT = 1`
18. `EARLY_AVOIDED_LOSS_CASES = 2_DESCRIPTIVE`
19. `EARLY_FALSE_EXIT_CASES = 2_DESCRIPTIVE_PLUS_SHORT_HORIZON_CASES`
20. `OUTCOME_HORIZON_SUFFICIENT = NO`
21. `FIRST_ACTUAL_PORTFOLIO_DIVERGENCE_DATE = 2022-10-07`
22. `CURRENT_EQUITY_VS_OLD_BASELINE = NEW_RUN_HIGHER_BY_9,810_ON_2022_11_16`
23. `CURRENT_CASH_EXPOSURE_VS_OLD_BASELINE = NEW_CASH_HIGHER_BY_142,810_AND_MARKET_VALUE_LOWER_BY_133,000_ON_2022_11_16`
24. `BQ_BV_RUNTIME_SAFETY_ACCEPTED_SO_FAR = YES_WITH_SOURCE_DECISION_UNIFORMITY_NOTE`
25. `PRODUCTION_CHANGE_REQUIRED_FROM_THIS_AUDIT = NO_IMMEDIATE_BQ_BV_CORRECTNESS_REPAIR`
26. `LONGER_EVIDENCE_REQUIRED = YES`
27. `NEXT_RECOMMENDED_STEP = Continue the current user-operated Historical run and re-audit after broader completed coverage; keep source-decision uniformity as an integration checklist item.`
28. `FINAL_JUDGMENT = PHASE32_BW_POST_BQ_BV_ACTUAL_FULL_EXIT_EARLY_RUN_ACCEPTED_WITH_LONGER_EVIDENCE_AND_SOURCE_DECISION_UNIFORMITY_WATCH`

