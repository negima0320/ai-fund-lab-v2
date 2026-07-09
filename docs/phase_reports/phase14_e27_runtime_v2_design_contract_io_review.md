# Phase14-E27 Runtime v2 Design Contract Input/Output Review

## Summary

Phase14-E27 reviewed Runtime v2 as Input / Output / Consumer contracts, not as isolated components.

Final judgment: `PHASE14E27_RUNTIME_V2_IO_CONTRACT_REVIEW_COMPLETE`

Overall status: `IO_CONTRACT_GAPS_FOUND`

No code was changed. No additional Submit, Production order, Notification actual send, or launchd change was performed.

The main conclusion is that Runtime v2 core paths are now connected for BUY Demo operation, but several contracts remain incomplete or semantically unsafe:

1. Market / Feature -> Planning has no reliable executable price source contract.
2. Planning can use `estimated_price=1000` fallback in normal operation.
3. Next Planning can consume E25 `total_equity=1,928,800` unless valuation review blocks it.
4. Report reads canonical Current SoT correctly, but order summaries are cumulative ledger summaries rather than business-date scoped operation summaries.
5. `runtime_state/current_state.json` exists but does not carry the effective Current Asset state.
6. SELL path exists as guards/manual D15 proof, but daily SELL Planning -> Current projection is not fully connected.
7. Notification payload is connected; LINE / Discord sender and delivery result are not implemented.

## Evidence Sources

- `.runtime/operations/feature_artifacts/2026-07-07/candidate_features.parquet`
- `.runtime/runtime_state/morning_pipeline/2026-07-08/order_plan.json`
- `.runtime/pending_order_plan/pending_order_plan.json`
- `.runtime/runtime_state/run_manifest/2026-07-08/runtime-v2-submit-2026-07-08-20260708T062328.649239+0000.json`
- `.runtime/runtime_state/broker_readonly/2026-07-08/tachibana_snapshot.json`
- `.runtime/persistent_ledger/state.json`
- `.runtime/persistent_ledger/orders.jsonl`
- `.runtime/persistent_ledger/positions.jsonl`
- `.runtime/persistent_ledger/cash.jsonl`
- `.runtime/runtime_state/current_state.json`
- `reports/runtime_v2/2026-07-08/runtime_report.json`
- `reports/runtime_v2/2026-07-08/notification_payload.json`
- `reports/public/runtime_v2/latest.md`
- `reports/public/runtime_v2/latest.json`
- `reports/phase_reports/phase14_e14_notification_blog_delivery_readiness_audit.json`
- `reports/phase_reports/phase14_e25_runtime_v2_end_to_end_data_flow_contract_asset_projection_fix.json`

Code inspected:

- `src/ai_fund_lab_v2/runtime_v2/cli/run_daily_operation.py`
- `src/ai_fund_lab_v2/runtime_v2/planning/morning_pipeline.py`
- `src/ai_fund_lab_v2/runtime_v2/submit/pipeline.py`
- `src/ai_fund_lab_v2/runtime_v2/submit/guards.py`
- `src/ai_fund_lab_v2/broker/tachibana_order_request.py`
- `src/ai_fund_lab_v2/runtime_v2/execution/readonly_pipeline.py`
- `src/ai_fund_lab_v2/runtime_v2/asset/runtime_owned_fill_projection.py`
- `src/ai_fund_lab_v2/runtime_v2/report/markdown_writer.py`
- `src/ai_fund_lab_v2/runtime_v2/broker_adapter/capability.py`

## Flow A: Market Data / Feature Flow

Design purpose:

J-Quants raw and canonical market data should produce Feature Artifacts that AI / Planning can use for both signal selection and executable sizing.

Correct input:

- Candidate feature rows with symbol, market, signal features, and a reliable current or latest close price.
- Price unit: JPY per share.
- Symbol unit: internal 5-character J-Quants code is acceptable before Broker boundary.

Actual input:

- `candidate_features.parquet` has 4,370 rows.
- It has signal columns such as `price_momentum_return_20d`.
- It does not have `current_price`, `close`, `Close`, `adjusted_close`, or `close_price`.
- `position_feature_input.parquet` has a `current_price` column but zero rows.
- `capital_policy_input.parquet` is a placeholder and has no price.

Correct output:

- Feature artifacts should expose an executable sizing price or explicitly mark price unavailable.

Actual output:

- Candidate features are usable for ranking but not for order sizing.

Consumer:

- Morning Planning reads candidate rows and attempts to derive price from several price keys.

Judgment: `GAP`

Mismatch:

Feature output schema lacks the price columns Planning expects. Planning compensates with fallback, so the Consumer can proceed despite missing required economic input.

## Flow B: AI / Planning Flow

Design purpose:

Feature artifacts should produce AI signals, capital allocation, and an OrderPlan that reflects 1,000,000 JPY demo evaluation capital and realistic executable sizing.

Correct input:

- Feature signal rows.
- Current SoT.
- BrokerCapability.
- Reliable sizing price.

Actual input:

- Feature signal rows exist.
- Current SoT exists with E25 projected positions and `total_equity=1,928,800`.
- BrokerCapability demo returns `default_evaluation_capital=1,000,000`.
- Reliable sizing price is absent.

Correct output:

- OrderPlan with symbol, side, quantity, estimated_price, estimated_amount, price_source, price_confidence, and review state when price is missing.

Actual output:

- OrderPlan/Pending contains five BUY items:
  - `estimated_price=1000`
  - `quantity=100`
  - `estimated_amount=100000`
- No explicit `price_source` or `price_confidence`.
- Fallback is not marked as unsafe in the artifact.

Consumer:

- Pending / Approval treats this as normal order intent.
- Submit guard uses `estimated_amount` for max order amount.

Judgment: `GAP`

Value / unit issue:

`estimated_price=1000` is JPY/share fallback, not market evidence. The unit is syntactically correct but semantically unsafe.

## Flow C: Pending / Approval Flow

Design purpose:

OrderPlan should become Approval-linked Pending Current only after approval, with matching item IDs, target session date, and duplicate protections.

Correct input:

- OrderPlan items.
- Approval artifact tied to the Pending plan hash / approved item IDs.

Actual input:

- `.runtime/runtime_state/morning_pipeline/2026-07-08/order_plan.json`
- `.runtime/pending_order_plan/pending_order_plan.json`
- Approval embedded in Pending.

Correct output:

- `.runtime/pending_order_plan/pending_order_plan.json` as the only Submit source.
- Pending state APPROVED before Submit, then CONSUMED after Submit.

Actual output:

- Pending is now `CONSUMED`.
- `approved_item_ids` match the five items.
- `target_session_date=2026-07-08`.
- `consume.submitted_order_ids` and `ledger_order_record_ids` are present.

Consumer:

- Submit reads only fixed Current Pending.

Judgment: `PASS_WITH_UPSTREAM_PRICE_GAP`

Schema match:

Pending / Approval schema is compatible with Submit. The economic value inherited from Planning remains unsafe because `estimated_price` lacks a reliable source.

## Flow D: Submit Flow

Design purpose:

Pending should produce RuntimeV2SubmitCommand, Broker request, Broker response, and Ledger Order records with correct code boundary and no legacy Submit authority.

Correct input:

- APPROVED Pending Current.
- Approval link.
- Demo capability.
- Broker adapter.

Actual input:

- Fixed Current Pending.
- Demo mode.
- Tachibana Demo Submit Adapter.

Correct output:

- Broker request with Broker 4-digit issue code.
- MARKET order with `sOrderPrice=0`.
- Quantity in shares.
- Response classification propagated to manifest and Ledger.

Actual output:

- E22: `submitted_count=5`, `accepted_count=5`.
- Internal codes `65220`, `78780`, `68970`, `63270`, `45910` normalized to Broker codes `6522`, `7878`, `6897`, `6327`, `4591`.
- `sOrderPrice=0` by request builder for market orders.
- Ledger orders contain status and response classification.

Consumer:

- Execution ReadOnly and Report consume Ledger orders.

Judgment: `PASS_WITH_REPORT_SEMANTIC_GAP`

Semantic mismatch:

`reports/runtime_v2/2026-07-08/runtime_report.json` aggregates all ledger orders and shows old rejected attempts plus accepted and filled records. This is useful history, but it is not a clean business-date scoped operation result unless Report distinguishes current run, current business date, and cumulative history.

## Flow E: Execution / Asset Flow

Design purpose:

Broker OrderList + Position + Cash evidence should create Ledger records and Current SoT without copying unrelated Demo account reset data.

Correct input:

- Broker OrderList filled state.
- Broker Position evidence.
- Broker Cash / Buying Power evidence.
- Runtime-owned accepted Submit records.

Actual input:

- E22 Broker OrderList: all five filled.
- Broker Position: five Runtime-owned symbols with quantity 100 and average price 102.
- Broker Cash / Buying Power exists, but Demo cash is evidence-only.
- Runtime-owned accepted submit records exist.

Correct output:

- Ledger orders / positions / cash / events.
- Current SoT with only Runtime-owned positions.
- No unrelated Demo positions.
- No Broker Demo 20,000,000 cash copied.

Actual output:

- Ledger positions preserve Broker Position evidence.
- Current SoT has five Runtime-owned positions.
- Current SoT cash is `949,000` and broker reset cash is not copied.
- Current SoT market value is `979,800`.
- Current SoT total equity is `1,928,800`.

Consumer:

- Report and Next Planning can read Current SoT.

Judgment: `PASS_WITH_VALUATION_REVIEW_REQUIRED`

Mismatch:

The projection owner is now clear, but the valuation remains economically suspect because it combines demo execution average price `102` with broker market values, producing `total_equity=1,928,800` after a 1,000,000 JPY operation. This must not flow into Next Planning without a valuation policy gate.

Additional schema concern:

`.runtime/persistent_ledger/executions.jsonl` is empty even though execution-equivalent evidence exists through OrderList + Position + Cash. This matches the E23 optional detail policy, but Consumers expecting canonical execution records need a documented `execution_equivalent` model or they will miss fills.

## Flow F: Report Flow

Design purpose:

Current SoT should produce Runtime Report, Public Report, `latest.md`, and `latest.json`, with redaction.

Correct input:

- Canonical Current SoT paths only.
- No Phase9 artifacts.
- No phase artifacts as Current.

Actual input:

- Report writer reads:
  - `persistent_ledger/state.json`
  - `orders.jsonl`
  - `executions.jsonl`
  - `positions.jsonl`
  - `cash.jsonl`
  - `events.jsonl`
  - `pending_order_plan/pending_order_plan.json`
  - `runtime_state/current_state.json`

Correct output:

- Runtime Report and Public Report with clear current state and scoped operation result.
- No secrets, raw responses, broker IDs, or Phase9 sources.

Actual output:

- Public Report shows cash, buying power, market value, total equity, and five holdings.
- Redaction scan passes.
- Notification payload summary is generated.
- Runtime report order counts are cumulative and include historical rejected attempts.

Consumer:

- Human operator and future notification payload.

Judgment: `PASS_WITH_SCOPING_GAP`

Mismatch:

Report displays Current SoT correctly, but order summaries need scoping fields so a human can distinguish current business-date/run results from accumulated ledger history.

## Flow G: Next Planning Flow

Design purpose:

Current SoT should inform the next capital allocation so Runtime does not ignore exposure or repeatedly reinvest full evaluation capital.

Correct input:

- Current SoT positions.
- Current SoT cash / buying power.
- Price-source validated valuation.

Actual input:

- Current SoT has five positions and `total_equity=1,928,800`.
- Morning Planning loads asset state.
- Demo capability still provides default evaluation capital of `1,000,000`.

Correct output:

- Next OrderPlan should account for existing holdings and usable capital.
- It should not treat demo valuation distortion as free equity.
- It should not continue with missing price source.

Actual output:

- Not rerun in E27.
- Existing code can load positions but has no demonstrated exposure-aware allocation logic.
- E25 marked Current SoT -> Next Planning as connected, but E26 showed valuation must be reviewed before use.

Consumer:

- Morning Planning / Capital Allocation.

Judgment: `GAP`

Mismatch:

Current can be read, but the decision contract for exposure, valuation confidence, and fallback price rejection is incomplete.

## Flow H: SELL Flow Contract

Design purpose:

Current Position should support safe SELL planning, approval, submit, execution reflection, and Current SoT update.

Correct input:

- Current Position and available quantity.
- SELL plan quantity <= owned and available quantity.
- Approval.

Actual input:

- Submit guard supports SELL and requires broker position / available quantity.
- D15 manually proved a SELL path.
- Daily SELL Planning is not connected as normal operation.

Correct output:

- Pending SELL.
- Submit result.
- Position reduction or removal.
- Cash / buying power update.
- Ledger / Current / Report update.

Actual output:

- Current daily operation BUY path exists.
- SELL daily planning and Current projection after SELL are not fully implemented as normal operation.

Consumer:

- Submit guard, Execution, Current SoT, Report.

Judgment: `PARTIAL / NOT_CONNECTED`

Mismatch:

SELL is guarded at Submit and proven manually, but not a complete daily Runtime IO flow.

## Flow I: Notification Flow

Design purpose:

Runtime events should produce Notification Payload, optional LINE / Discord delivery, Delivery Result, and Audit.

Correct input:

- Runtime Report / Event summary.
- Notification mode.
- Delivery ledger idempotency.

Actual input:

- Runtime report generator emits `notification_payload.json`.
- CLI enforces `notification-mode=payload-only`.

Correct output:

- Payload-only for current demo launchd stage.
- Later, sender delivery results and audit entries.

Actual output:

- `reports/runtime_v2/2026-07-08/notification_payload.json` exists.
- `send_executed=false`.
- Delivery ledger file is missing.
- E14 confirms LINE and Discord Runtime v2 senders are `NOT_IMPLEMENTED`.

Consumer:

- Human/operator now.
- Future LINE / Discord sender later.

Judgment: `READY_PAYLOAD_ONLY / NOT_IMPLEMENTED_FOR_SEND`

Mismatch:

Payload contract exists, but delivery result and sender contracts are not connected.

## Cross-Flow Findings

### Input / Output Mismatches

| Flow | Producer Output | Consumer Expected | Mismatch |
| --- | --- | --- | --- |
| Feature -> Planning | candidate features without price | sizing price | Missing price source |
| Planning -> Pending | estimated price without source | approved executable order intent | Fallback indistinguishable from real price |
| Ledger -> Report | cumulative orders | current operation summary | Report scoping ambiguity |
| Execution -> Consumers | execution-equivalent evidence, empty executions.jsonl | canonical execution records | Consumer ambiguity |
| Current -> Next Planning | demo-distorted valuation | reliable available capital/exposure | Valuation confidence missing |
| Runtime Event -> Delivery | payload-only | sender delivery result | Sender not implemented |

### Schema Mismatches

- Price fields lack `price_source` and `price_confidence`.
- Report order rows lack clear `business_date/run_id/current_run_scope` in the public summary.
- `runtime_state/current_state.json` does not mirror the effective asset Current SoT and is not sufficient for Current asset consumers.
- `executions.jsonl` remains empty despite filled orders; an explicit execution-equivalent schema is needed if detail API remains optional.

### Unit Mismatches

- Internal symbol is 5-character J-Quants style before Broker boundary.
- Broker request correctly uses 4-digit issue code.
- Quantity is shares, not lots, but planning should make lot rounding explicit.
- `estimated_price=1000` is JPY/share fallback, but it is not tagged as fallback.
- Broker market values are JPY, but demo execution average price may not be production-equivalent.

### Fallback Usage

Normal operation fallback usage found:

- Morning Planning uses `fallback_budget / 100` when price columns are absent.
- This created `estimated_price=1000` and quantity 100 for all five E22 orders.

This fallback must be blocked or explicitly reviewed before any future submit-enabled cycle.

### Owner Ambiguities

Current SoT owner:

- Asset Current writer / runtime-owned fill projection owns `.runtime/persistent_ledger/state.json`.
- Report, Audit, Notification, and phase artifacts do not write Current.

Remaining ambiguity:

- `.runtime/runtime_state/current_state.json` exists but does not carry effective asset Current values.
- Consumers must be told whether to read `persistent_ledger/state.json` for asset state or `runtime_state/current_state.json` for runtime state only.

## Status Summary

| Area | Status |
| --- | --- |
| Market / Feature | `GAP` |
| AI / Planning | `GAP` |
| Pending / Approval | `PASS_WITH_UPSTREAM_PRICE_GAP` |
| Submit | `PASS_WITH_REPORT_SEMANTIC_GAP` |
| Execution / Asset | `PASS_WITH_VALUATION_REVIEW_REQUIRED` |
| Report | `PASS_WITH_SCOPING_GAP` |
| Next Planning | `GAP` |
| SELL | `PARTIAL_NOT_CONNECTED` |
| Notification | `READY_PAYLOAD_ONLY_NOT_IMPLEMENTED_FOR_SEND` |
| Mode Switch | `PASS_FOR_DEMO_CAPABILITY`, `PRODUCTION_NOT_VALIDATED` |

## Blocker List

Before next submit-enabled operation:

1. Price-source contract for Planning.
2. Block or review missing-price fallback.
3. Valuation confidence gate before Next Planning uses E25 `total_equity=1,928,800`.
4. Exposure-aware next allocation contract.
5. Report scoping fix to distinguish current run/day vs cumulative ledger.

Before production:

1. Production capability path validation.
2. Execution-equivalent schema or execution detail policy for consumers.
3. SELL daily planning and Current projection.
4. Notification sender / delivery ledger / audit connection if actual sending is required.

## Next Required Fixes

1. Phase14-E28: Planning Price Source Contract & Missing Price Block.
2. Phase14-E29: Next Planning Exposure / Valuation Confidence Gate.
3. Phase14-E30: Report Scope Contract for current run, business date, and ledger history.
4. Phase14-E31: Execution-equivalent Evidence Schema for optional detail API mode.
5. Phase14-E32: SELL Daily Operation IO Contract.
6. Phase14-E33: Notification Sender / Delivery Result Contract when send-enabled mode is allowed.

## Acceptance Review

| Acceptance Item | Result |
| --- | --- |
| Major Runtime v2 flows reviewed by Input / Output | PASS |
| Designed input vs actual input differences listed | PASS |
| Designed output vs actual output differences listed | PASS |
| Consumer schema and semantic fit reviewed | PASS |
| Fallback normal operation usage checked | PASS |
| Current SoT owner clarified | PASS |
| Price source contract clarified | PASS |
| BUY / SELL / Notification / Report / Next Planning reviewed | PASS |
| No code change | PASS |
| No additional Submit | PASS |
| No Production order | PASS |
| No Notification actual send | PASS |
| No launchd change | PASS |

## Final Judgment

`PHASE14E27_RUNTIME_V2_IO_CONTRACT_REVIEW_COMPLETE`
