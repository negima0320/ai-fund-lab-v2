# Phase23-AJ Quantity Authority Root Cause Evidence Audit

## 1. Primary Judgment

`PHASE23_AJ_QUANTITY_AUTHORITY_ROOT_CAUSE_CONFIRMED_REPAIR_REQUIRED`

Root Cause is confirmed and repair is required.

Primary Root Cause:

`PORTFOLIO_CONSTRUCTION_SCORE_FIELD_TO_POSITION_SIZING_QUALITY_AUTHORITY_CONTRACT_MISMATCH_FORCES_ALL_ALLOCATIONS_TO_ZERO`

Mandatory Classification:

`ALLOCATION_AMOUNT_MISSING_OR_UNRESOLVED` for 50 / 50 symbols.

## 2. Phase23継続確認

Phase23-AI after-state is preserved. Candidate / Opportunity capacity is no longer the observed zero-trade blocker in the target run artifact: `resolved_candidate_capacity=50`, `resolved_opportunity_capacity=50`, `target_position_count=10`.

## 3. Target Run Identity

- Run ID: `runtime-test-historical-smoke-20260729T220208972293Z`
- Business Date: `2026-07-06`
- Run Path: `reports/runtime_tests/runs/runtime-test-historical-smoke-20260729T220208972293Z`

## 4. Existing Run Preservation

The target run was treated read-only. Protected hash preservation status: `True`.

Protected files checked:

- `plan.json`
- `run_state.json`
- `historical_evaluation_authority.json`
- `daily/2026-07-06/morning/runtime_manifest.json`
- `daily/2026-07-06/strategy/dynamic_position_count.json`
- `daily/2026-07-06/strategy/capital_deployment.json`
- `daily/2026-07-06/strategy/position_sizing.json`
- `daily/2026-07-06/strategy/runtime_planning.json`
- `daily/2026-07-06/strategy/strategy_decision_trace.json`

## 5. Morning Halt Reconstruction

- `run_state.status`: `HALT`
- `completed_business_days`: `[]`
- `manifest.exit_code`: `20`
- `manifest.reason`: `morning pipeline review required: strategy_planning_authority_unresolved`
- `strategy_planning_authority.status`: `REVIEW_REQUIRED`
- `strategy_planning_authority.reason`: `strategy_planning_authority_unresolved`
- `strategy_plan_quantity_unresolved_count`: `50`

## 6. Dynamic Position Count Runtime Output

DPC is not the current direct blocker.

- `producer_result_status`: `PASS`
- `resolved_candidate_capacity`: `50`
- `resolved_opportunity_capacity`: `50`
- `target_position_count`: `10`
- `current_position_count`: `0`

## 7. Capital Deployment and Allocation

CapitalDeployment has 50 members and `producer_result_status=PASS`, but it does not provide concrete per-symbol allocation amount. Every member carries `no_concrete_allocation_in_phase22_f`.

- `portfolio_value`: `1000000.0`
- `target_gross_exposure_ratio`: `0.79`
- implied deployable capital: `790000.0`
- implied per-position budget if quality/allocation resolved: `79000.0`
- concrete allocation amount fields present: `0`

## 8. Position Sizing Artifact

Position Sizing withholds all 50 symbols.

- `producer_result_status`: `REVIEW_REQUIRED`
- `positions_sized`: `0`
- `positions_withheld`: `50`
- status distribution: `{'QUALITY_UNAVAILABLE': 50}`
- reason distribution: `{'membership_intent:ADD_CANDIDATE': 50, 'pm_action:NEW': 50, 'quality_missing_fail_closed': 50}`

## 9. Per-Symbol Quantity Reconstruction

All 50 symbols have the same pattern:

- Portfolio Construction has `input_score`.
- Portfolio Construction does not have `opportunity_score`.
- Position Sizing expects `opportunity_score`.
- `quality_adjustment=0.0`.
- `sizing_status=QUALITY_UNAVAILABLE`.
- `target_notional=0.0` and `incremental_buy_notional=0.0`.
- Runtime Planning sets `quantity_status=REVIEW_REQUIRED_AUTHORITY_UNRESOLVED`.
- Strategy Authority lineage records `strategy_plan_quantity_unresolved:<symbol>`.

Full table: `reports/phase23_aj_quantity_authority_root_cause_evidence_audit/per_symbol_quantity_reconstruction.json`.

## 10. Reference Price Authority

Reference price is not the primary blocker.

- source: `.runtime/operations/jquants/raw_normalized/jquants/equities_bars_daily/data.parquet`
- target symbols with price: `50 / 50`
- missing symbols: `[]`

Strategy Authority reached zero quantity because notional was zero, not because price was missing.

## 11. Trading Unit Authority

Strategy Authority uses `ROUND_LOT=100` from `src/ai_fund_lab_v2/runtime_v2/planning/strategy_authority.py:23`. Listed-issue trading unit is not consumed in this path. This is a non-primary authority gap because all target notionals are already zero before lot rounding.

## 12. Quantity Math

Formula from implementation:

`quantity = floor(notional / price / 100) * 100`

Observed:

- strategy notional zero count: `50 / 50`
- positive price count: `50 / 50`
- rounded positive quantity count: `0 / 50`

## 13. Quantity Status and Reason

Runtime Planning maps `QUALITY_UNAVAILABLE` to `REVIEW_REQUIRED_AUTHORITY_UNRESOLVED` through `runtime_planning.py:738-757`. The observed reason is `position_sizing_status_unresolved:QUALITY_UNAVAILABLE` for all plans.

## 14. Position Sizing Producer Contract

Current producer emits target weights/notionals but forbids final share quantity / lot fields. For this run, it never reaches positive target notional because quality authority is missing.

## 15. Runtime Planning Consumer Contract

Runtime Planning consumes `positions[].sizing_status`; for `SIZED` / `CAPPED` plus positive notional it would emit `RESOLVED_EXECUTABLE`. For `QUALITY_UNAVAILABLE`, it emits `REVIEW_REQUIRED_AUTHORITY_UNRESOLVED`. This mapping is consistent with the current code.

## 16. Exact Producer / Consumer Boundary

Exact boundary:

- Producer: `portfolio_construction._member` emits `input_score` at `src/ai_fund_lab_v2/strategy/portfolio_construction.py:755-769`.
- Consumer: `position_sizing._quality_multiplier` reads `opportunity_score` at `src/ai_fund_lab_v2/strategy/position_sizing.py:644-654`.
- Result: 50 / 50 rows have `input_score`, 0 / 50 rows have `opportunity_score`.

## 17. Model Health Review Causality

`MODEL_HEALTH_REVIEW_REQUIRED` is present, but it is not the direct quantity blocker. Quantity failure is already fully reconstructed from Position Sizing, Runtime Planning, and Strategy Planning Authority lineage.

Judgment: `MODEL_HEALTH_REVIEW_IS_PARALLEL_NON_PRIMARY_REVIEW`.

## 18. Cross-Component Authority Map

See `cross_component_authority_map.json`.

## 19. Classification Distribution

`{'ALLOCATION_AMOUNT_MISSING_OR_UNRESOLVED': 50}`

## 20. Exact Root Cause

The exact Root Cause is a production-common field contract mismatch between Portfolio Construction and Position Sizing. The upstream artifact carries a usable opportunity score as `input_score`, but Position Sizing only accepts `opportunity_score`; therefore quality authority is treated as missing, all target allocation/notional is zeroed, and all BUY_NEW plans become quantity-unresolved.

## 21. Independent System Objective Judgment

The system correctly avoided forcing trades. However, the objective of converting accepted candidate/opportunity authority into concrete planning fails because allocation quality authority is disconnected.

## 22. Repair Required or No Repair Required

Repair Required.

## 23. Proposed Phase23-AK Scope

- Production-common repair for Portfolio Construction -> Position Sizing score/quality authority contract.
- Define canonical per-symbol quality score field and preserve lineage from candidate/opportunity artifacts.
- Ensure concrete allocation/notional can be produced only when quality authority is resolved; maintain fail-closed behavior for true missing quality.
- Add targeted regression for input_score/opportunity_score contract and all-QUALITY_UNAVAILABLE prevention when upstream score exists.
- Do not force minimum quantity or force BUY; keep price, lot, cash, safety gates authoritative.

## 24. Modified Files

Audit deliverables only:

- `docs/phase_reports/phase23_aj_quantity_authority_root_cause_evidence_audit.md`
- `reports/phase_reports/phase23_aj_quantity_authority_root_cause_evidence_audit.json`
- `reports/phase23_aj_quantity_authority_root_cause_evidence_audit/`

No implementation files were modified for Phase23-AJ.

## 25. Tests Executed

- Read-only JSON artifact extraction.
- Read-only parquet price authority extraction.
- Existing Run hash before/after preservation.
- Evidence JSON validation.

## 26. 未実施事項

- Implementation repair.
- Historical fresh-run.
- 10BD / 20BD / long runtime.
- resume / abandon.
- Runtime Switch.
- Broker Write.
- J-Quants live fetch.
- Canonical mutation.
- Existing Run artifact mutation or reclassification.

## 27. Remaining Gaps

- Trading unit authority currently uses a code constant `ROUND_LOT=100`; this is not the primary blocker here, but should be formalized separately if Phase23-AK touches final quantity authority.
- CapitalDeployment still records posture/priority rather than concrete allocation amount; Phase23-AK should decide whether Position Sizing owns concrete allocation or consumes it from a capital allocation authority.

## 28. Next Operator Action

Submit Phase23-AJ evidence for review. If accepted, proceed to Phase23-AK repair scope. Do not run 10BD until the repair is implemented and short validation passes.
