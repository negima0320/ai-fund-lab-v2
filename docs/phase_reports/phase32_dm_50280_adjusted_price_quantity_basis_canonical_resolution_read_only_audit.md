# Phase32-DM 50280 Adjusted-Price / Quantity-Basis Canonical Resolution READ-ONLY Audit

## Scope

- Target run: `runtime-test-historical-extended-smoke-20260902T060955933565Z`
- Current boundary: `2023-10-11:sell_planning`
- Source commit recorded by the run: `a56f2bc26105eb14fd67322b7cd53c0d6ef1b1bd`
- Execution mode: READ-ONLY audit
- CA resolution executed: NO
- Resume / recover / replay / fresh-run executed: NO
- Strategy / Corporate Action resolver / config change: NO
- Target run mutated: NO

References read:

- `docs/phase_reports/phase32_dk_50280_corporate_action_canonical_resolution_safe_continuation_read_only_audit.md`
- `docs/phase_reports/phase32_dl_corporate_action_operator_resolution_sell_campaign_identity_production_repair.md`
- `docs/phase_reports/phase24_il_corporate_action_adjustment_authority_and_quantity_reconciliation_design.md`
- `docs/02_architecture/runtime_architecture_v2.md`
- `docs/02_architecture/autonomous_ai_operations_architecture.md`
- current target-run artifacts, `.runtime/persistent_ledger/state.json`, `.runtime/pending_order_plan/pending_order_plan.json`, and `.runtime/runtime_state/corporate_action_adjustments/2023-10-11/50280.json`

## 50280 Position Lineage

`50280_POSITION_LINEAGE`: Runtime owns one open 50280 campaign:

- campaign id: `pc-d468aca3b9d6da8f-50280-0001`
- first BUY date: `2023-10-04`
- BUY side/quantity: `BUY 100`
- BUY fill price: `438.0`
- source decision id: `rp-2023-10-04-50280-buy_new-57b3183f98f1da41`
- execution id: `execution-equivalent:sha256:f96e618bfa57e6146e4cbebaec7b26363d70c71735d764d8ceec478840f627a6`
- campaign quantity through `2023-10-10`: `100.0`
- average price through `2023-10-10`: `438.0`
- cost basis through `2023-10-10`: `43800.0`
- valuation basis: `quantity_basis = ADJUSTED`, `valuation_price_basis = ADJUSTED`
- pre-`2023-10-11` quantity transformations: none observed; campaign quantity remained `100.0`

PM and Runtime Planning on `2023-10-11` intend a full exit of the Runtime-owned 100-unit position:

- PM decision id: `pm-2023-10-11-50280-reduce`
- PM decision type: `REDUCE`
- Strategy PM action materialized to Runtime Planning: `SELL_EXIT`
- Runtime Planning id: `rp-2023-10-11-50280-sell_exit-ef85562eee72162f`
- planned/pending quantity: `100`
- Pending state: `REVIEW_REQUIRED`, reason `corporate_action_event_not_resolved`

## Raw vs Adjusted Price Trace

`50280_RAW_VS_ADJUSTED_PRICE_TRACE`:

| Date | Raw O/H/L/C | Adjusted O/H/L/C | AdjFactor | Runtime normalized O/C | Runtime role |
| --- | --- | --- | --- | --- | --- |
| 2023-10-04 | 1314 / 1437 / 1313 / 1370 | 438.0 / 479.0 / 437.7 / 456.7 | 1.0 | 438.0 / 456.7 | BUY fill used `438.0`, matching adjusted/normalized open, not raw open |
| 2023-10-05 | 1385 / 1405 / 1357 / 1373 | 461.7 / 468.3 / 452.3 / 457.7 | 1.0 | 461.7 / 457.7 | campaign valuation close `457.7` |
| 2023-10-10 | 1360 / 1435 / 1360 / 1391 | 453.3 / 478.3 / 453.3 / 463.7 | 1.0 | 453.3 / 463.7 | current valuation close `463.7` |
| 2023-10-11 | 456 / 474 / 455 / 461 | 456 / 474 / 455 / 461 | 0.3333333333333333 | 456 / 461 | CA impact detected from target-date AdjFactor |

The fill arithmetic is decisive: `2023-10-04` raw open was `1314.0`, but the actual historical fill was `438.0`, exactly the adjusted/normalized open. Current valuation likewise uses adjusted/normalized close.

## Runtime Price / Quantity Convention

`HISTORICAL_RUNTIME_PRICE_QUANTITY_CONVENTION`: `ADJUSTED_PRICE_ADJUSTED_RUNTIME_QUANTITY`.

This is not inferred from field labels alone. The observed arithmetic is:

- fill price = adjusted open, not raw open: `438.0`, not `1314.0`
- cost basis = `100 x 438.0 = 43800.0`
- `2023-10-10` valuation = `100 x 463.7 = 46370.0`
- ledger state explicitly records `execution_price_basis = ADJUSTED`, `fill_price_basis = ADJUSTED`, `quantity_basis = ADJUSTED`, `valuation_price_basis = ADJUSTED`

The Runtime is operating a normalized historical backtest unit convention. It is not carrying raw-market shares at raw-market prices for this campaign.

## Cost Basis Reconciliation

`50280_COST_BASIS_RECONCILIATION`: PASS under the Runtime adjusted convention.

- Runtime campaign: `100 x 438.0 = 43800.0`
- Ledger state: `cost_basis = 43800.0`
- `2023-10-10` valuation: `100 x 463.7 = 46370.0`
- Unrealized PnL: `46370.0 - 43800.0 = 2570.0`

The equivalent raw-price/raw-share entry would have been `100 x 1314.0 = 131400.0`, which is not the Runtime cash deployment, ledger cost basis, or campaign basis. Therefore raw-market share economics cannot be substituted into this Runtime campaign without rewriting its historical fill/cash/ledger basis.

## Corporate Action Event Evidence

`50280_EVENT_TYPE_EVIDENCE_STATUS`: `STILL_UNKNOWN_FOR_RUNTIME_AUTHORITY`.

Canonical Runtime evidence proves:

- target date: `2023-10-11`
- symbol: `50280`
- `AdjFactor = 0.3333333333333333`
- source artifact: `reports/runtime_tests/runs/runtime-test-historical-extended-smoke-20260902T060955933565Z/daily/2023-10-11/market_refresh/inputs/historical_asof/2023-10-11/raw/jquants/equities_bars_daily/data.parquet`
- PIT validation: `PASS`
- CA event status: `IMPACT_DETECTED`

Canonical Runtime evidence does not prove:

- actual corporate action event type
- whether the adjustment has already been applied to every Runtime quantity component
- pre/post market-share quantity relationship

The active CA authority correctly remains:

- status: `REVIEW_REQUIRED`
- event type: `UNKNOWN_ADJFACTOR_IMPACT`
- event type authority: `not_available_from_adjfactor_only`
- reason: `corporate_action_event_type_or_adjustment_application_unresolved`

## Quantity Hypotheses

`H1_QUANTITY_100_RECONCILIATION`: PASS for Runtime economic continuity.

If post-CA Runtime quantity remains `100`:

- cost basis remains `43800.0`
- `2023-10-10` value: `100 x 463.7 = 46370.0`
- `2023-10-11` normalized close value: `100 x 461.0 = 46100.0`
- boundary change: `-270.0`, about `-0.58%`
- campaign quantity, ledger quantity, current position quantity, Pending quantity, and PM SELL_EXIT quantity all remain aligned at `100`
- no unobserved ledger/cash/campaign rewrite is required
- no double adjustment is introduced

`H2_QUANTITY_300_RECONCILIATION`: FAIL for current Runtime evidence.

If post-CA Runtime quantity is changed to `300` while using already adjusted/normalized prices:

- `2023-10-11` normalized close value becomes `300 x 461.0 = 138300.0`
- this creates an unexplained near-3x value jump from `46370.0`
- if average price remains `438.0`, cost basis becomes `300 x 438.0 = 131400.0`, contradicting the ledger cost basis `43800.0`
- if average price is rewritten to keep cost basis constant, that rewrite is not present in the Runtime ledger/campaign/current evidence
- Pending `SELL 100` would no longer represent a full exit, contradicting PM/Runtime Planning's `SELL_EXIT` of the Runtime-owned position

## Economic Continuity Result

`50280_ECONOMIC_CONTINUITY_RESULT`: `100` preserves Runtime economic continuity; `300` creates a double-application artifact under the current adjusted-price Runtime convention.

The CA boundary should be reconciled on the Runtime's internal normalized basis, not on raw-market share intuition alone. The adjusted price series already embeds the historical price transformation. Multiplying Runtime quantity by three would apply the transformation a second time unless there were a separate canonical ledger/cash/campaign rewrite, and no such rewrite exists.

`DOUBLE_ADJUSTMENT_RISK_IF_100_TO_300`: `CONFIRMED`.

## Quantity Basis Field Semantics

`QUANTITY_BASIS_FIELD_SEMANTICS`:

- `quantity_basis = ADJUSTED` is used consistently as a Runtime-owned normalized quantity basis paired with adjusted historical fills and adjusted valuation prices.
- `valuation_price_basis = ADJUSTED` means valuation uses normalized adjusted OHLCV prices.
- `fill_price_basis = ADJUSTED` / `execution_price_basis = ADJUSTED` in ledger state prove the original campaign was funded on adjusted price, not raw price.
- The fields are more than descriptive labels in this case because the ledger also records `quantity_basis_provenance = runtime_execution_price_authority:adjusted_reference_price_basis` and `valuation_price_authority_reason = valuation_price_basis_matches_adjusted_quantity_basis`.
- The fields do not by themselves prove the external corporate action event type; they only prove the Runtime basis convention.

## Historical Fill Basis

`HISTORICAL_FILL_BASIS`: adjusted price with normalized Runtime quantity.

Architecture says the historical fill model uses the target business date canonical OHLCV open. In this run, the canonical normalized OHLCV open for `50280` on `2023-10-04` is `438.0`. The actual fill used `438.0`; raw open was `1314.0`. Therefore the campaign originated from adjusted-price historical execution.

No transformed quantity was materialized at entry. The entry quantity was `100`, persisted as campaign/current Runtime quantity.

## Comparable CA Cases

`COMPARABLE_CA_CASES`: no usable resolved comparable case was found in current Runtime CA authority evidence.

Observed CA authority files:

| Artifact | Symbol | Factor | Status | Quantity result |
| --- | --- | --- | --- | --- |
| `.runtime/runtime_state/corporate_action_adjustments/2022-10-28/76920.json` | 76920 | 0.3333333333333333 | REVIEW_REQUIRED | unresolved |
| `.runtime/runtime_state/corporate_action_adjustments/2023-03-15/76920.json` | 76920 | 0.25 | REVIEW_REQUIRED | unresolved |
| `.runtime/runtime_state/corporate_action_adjustments/2023-10-04/65730.json` | 65730 | 0.3333333333333333 | REVIEW_REQUIRED | unresolved |
| `.runtime/runtime_state/corporate_action_adjustments/2023-10-11/50280.json` | 50280 | 0.3333333333333333 | REVIEW_REQUIRED | unresolved |

These are useful as evidence that the guard consistently refuses to infer event type/quantity from `AdjFactor` alone. They are not usable as accepted examples of a resolved post-CA quantity transformation.

## Canonical Post-CA Quantity

`POST_CA_RUNTIME_QUANTITY`: `100`.

This is the canonical Runtime-owned adjusted-basis quantity that preserves existing ledger, campaign, valuation, Pending, and PM/Runtime Planning continuity.

`OPERATOR_PRE_ADJUSTMENT_QUANTITY`: `100` under Runtime adjusted-basis convention.

`OPERATOR_POST_ADJUSTMENT_QUANTITY`: `100` under Runtime adjusted-basis convention.

These values do not assert raw-market pre/post share counts. They assert the Runtime-owned adjusted quantity before and after the detected impact, consistent with the existing adjusted-price historical campaign basis.

## Already-Applied Component Status

`CA_ALREADY_APPLIED_COMPONENT_STATUS`:

| Component | Status | Evidence |
| --- | --- | --- |
| Price series | APPLIED | raw adjusted fields and raw_normalized prices use adjusted basis; entry fill and valuation use adjusted prices |
| Runtime fill/ledger price basis | APPLIED | fill price `438.0` equals adjusted open; ledger records adjusted fill/execution price basis |
| Ledger quantity basis | APPLIED | ledger quantity `100.0`, `quantity_basis = ADJUSTED`, cost basis `43800.0` |
| Campaign quantity basis | APPLIED | campaign quantity `100.0`, `quantity_basis = ADJUSTED` through `2023-10-10` |
| Current position quantity basis | APPLIED | persistent ledger current position quantity `100.0`, adjusted valuation basis |
| Pending quantity basis | APPLIED for Runtime quantity continuity; REVIEW_REQUIRED for CA authority | Pending SELL quantity is `100`, but item remains unapproved because CA event type/already-applied authority is unresolved |
| CA authority artifact | UNKNOWN | active artifact still records `already_applied_status = UNKNOWN`, `quantity_reconciliation_status = REVIEW_REQUIRED`, `price_reconciliation_status = REVIEW_REQUIRED` |
| External event type | UNKNOWN | not proven by Runtime PIT evidence |

The audit can prove the Runtime basis and safe internal quantity. It does not mutate the CA authority artifact from `UNKNOWN` to `PASS`.

## Safe Sell Quantity

`50280_CANONICAL_SAFE_SELL_QUANTITY`: `100`.

This quantity is safe with respect to Runtime price/quantity basis reconciliation. It is the full Runtime-owned adjusted-basis campaign quantity and matches PM/Runtime Planning's `SELL_EXIT`.

It is not yet submittable because the canonical CA operator authority still requires explicit resolution of event type and already-applied/idempotency evidence.

## Operator Resolution Readiness

`50280_OPERATOR_RESOLUTION_READY`: `CONDITIONAL`.

DM proves these operator-resolution fields:

- effective date: `2023-10-11`
- adjustment factor: `0.3333333333333333`
- pre-adjustment Runtime quantity: `100`
- post-adjustment Runtime quantity: `100`
- current Runtime quantity: `100`
- broker-equivalent Runtime quantity for historical simulated run: `100`
- pending quantity: `100`
- submit quantity: `100`
- price-series-adjusted: `true`
- quantity-adjusted: `true`, meaning Runtime-owned quantity is already on the adjusted basis and no numeric multiplication is required
- adjustment-already-applied: `true` for the Runtime basis components above

DM does not prove:

- non-unknown corporate action event type
- external/operator reviewer identity
- audit id
- operator resolution reason
- operator-reviewed evidence source beyond the existing J-Quants AdjFactor impact artifact

`50280_DRY_RUN_COMMAND`: WITHHELD.

The DL command requires a non-unknown `--event-type`, reviewer, audit id, and resolution reason. Because event type remains `STILL_UNKNOWN_FOR_RUNTIME_AUTHORITY`, DM must not emit a fully populated dry-run command as if operator authority were complete.

Once the operator supplies a non-unknown event type and audit metadata, the quantity fields should be populated with the Runtime-proven values above, not `300`.

## Campaign Identity Readiness

`50280_CAMPAIGN_ID_READY_FOR_RESOLVED_SELL`: YES.

The canonical open campaign is `pc-d468aca3b9d6da8f-50280-0001`. DL repaired SELL campaign identity propagation so regenerated/materialized SELL Pending can inherit the existing open current-position campaign instead of producing empty or deterministic replacement ids.

The stale target Pending still shows empty `position_campaign_id` / `campaign_id`, but that is the pre-resolution/pre-regeneration artifact. It was not mutated in DM.

## 76920 Scope

`76920_CHANGED`: NO.

76920 was inspected only to confirm comparable CA authority status and remains outside the DM resolution scope.

## Required Final Answers

1. `50280_POSITION_LINEAGE`: BUY_NEW `100` on `2023-10-04` at adjusted fill price `438.0`; campaign `pc-d468aca3b9d6da8f-50280-0001`; quantity stayed `100`; average price `438.0`; cost basis `43800.0`; adjusted valuation basis.
2. `50280_RAW_VS_ADJUSTED_PRICE_TRACE`: raw entry open `1314.0`, adjusted/normalized entry open `438.0`, fill `438.0`; `2023-10-10` adjusted close `463.7`, valuation `46370.0`; `2023-10-11` normalized close `461.0`, AdjFactor `0.3333333333333333`.
3. `HISTORICAL_RUNTIME_PRICE_QUANTITY_CONVENTION`: `ADJUSTED_PRICE_ADJUSTED_RUNTIME_QUANTITY`.
4. `50280_COST_BASIS_RECONCILIATION`: PASS, `100 x 438.0 = 43800.0`.
5. `50280_EVENT_TYPE_EVIDENCE_STATUS`: `STILL_UNKNOWN_FOR_RUNTIME_AUTHORITY`.
6. `H1_QUANTITY_100_RECONCILIATION`: PASS; preserves ledger/campaign/valuation/Pending continuity and avoids double adjustment.
7. `H2_QUANTITY_300_RECONCILIATION`: FAIL; creates unexplained near-3x value/cost-basis discontinuity without a canonical rewrite.
8. `50280_ECONOMIC_CONTINUITY_RESULT`: `100` preserves continuity; `300` does not.
9. `DOUBLE_ADJUSTMENT_RISK_IF_100_TO_300`: `CONFIRMED`.
10. `QUANTITY_BASIS_FIELD_SEMANTICS`: adjusted Runtime quantity paired with adjusted fill and valuation price; proves Runtime basis, not event type.
11. `HISTORICAL_FILL_BASIS`: adjusted open price `438.0` with normalized Runtime quantity `100`.
12. `COMPARABLE_CA_CASES`: no resolved comparable case; current CA authority files are all `REVIEW_REQUIRED`.
13. `POST_CA_RUNTIME_QUANTITY`: `100`.
14. `OPERATOR_PRE_ADJUSTMENT_QUANTITY`: `100`.
15. `OPERATOR_POST_ADJUSTMENT_QUANTITY`: `100`.
16. `CA_ALREADY_APPLIED_COMPONENT_STATUS`: price series, fill/ledger price basis, ledger/campaign/current quantity basis APPLIED; CA authority event type/already-applied artifact remains UNKNOWN/REVIEW_REQUIRED.
17. `50280_CANONICAL_SAFE_SELL_QUANTITY`: `100`.
18. `50280_OPERATOR_RESOLUTION_READY`: `CONDITIONAL`.
19. `50280_DRY_RUN_COMMAND`: WITHHELD until non-unknown event type and operator audit metadata are supplied.
20. `50280_CAMPAIGN_ID_READY_FOR_RESOLVED_SELL`: YES, canonical campaign `pc-d468aca3b9d6da8f-50280-0001`.
21. `76920_CHANGED`: NO.
22. `PRODUCTION_CHANGE_EXECUTED`: NO.
23. `TARGET_RUN_MUTATED`: NO.
24. `NEXT_RECOMMENDED_STEP`: operator should supply/confirm the non-unknown 50280 corporate action event type and audit metadata, then run DL's dry-run resolver using Runtime quantity values `pre=100`, `post=100`, `current=100`, `broker=100`, `pending=100`, `submit=100`; do not use `300`.
25. `FINAL_JUDGMENT`: `PHASE32_DM_50280_CANONICAL_RUNTIME_QUANTITY_100_PROVEN_OPERATOR_EVENT_TYPE_STILL_REQUIRED`

## Final Judgment

`PHASE32_DM_50280_CANONICAL_RUNTIME_QUANTITY_100_PROVEN_OPERATOR_EVENT_TYPE_STILL_REQUIRED`

The current Historical Runtime campaign for 50280 is internally adjusted-price/adjusted-Runtime-quantity based. The canonical post-CA Runtime-owned quantity is `100`, and `SELL_EXIT 100` is the correct quantity once CA authority is explicitly resolved. Changing Runtime quantity to `300` would double-apply the adjustment under this run's existing normalized price/quantity convention.

The real CA authority remains unresolved because `AdjFactor` proves impact but not event type. No production state was changed, and the target run was not mutated.
