# Phase14-E28 Planning Price Source Contract & Missing Price Block

## Summary

Phase14-E28 fixed the most important E27 IO gap: Planning can no longer create normal BUY orders from a missing price source using `fallback_budget / 100`.

Final judgment: `PHASE14E28_PLANNING_PRICE_SOURCE_FIXED`

Implemented:

1. Defined the Planning Price Source Contract.
2. Selected one canonical price source for Runtime v2 Morning Planning:
   - `.runtime/operations/jquants/raw_normalized/jquants/equities_bars_daily/data.parquet`
   - fields: `Code`, `Date`, `Close`, `PriceSource`
3. Added price metadata to Planning / Pending artifacts:
   - `estimated_price`
   - `price_source`
   - `price_as_of`
   - `price_confidence`
   - `price_required`
4. Removed normal-operation fallback price sizing from Runtime v2 Planning.
5. Missing reliable price source now creates no executable Pending items.
6. Order sizing now uses real J-Quants normalized close and 100-share lot rounding.
7. Demo 9000-series filtering remains intact.
8. Production capability still does not block 9000-series symbols.

No additional Submit was executed. No Production order, Notification actual send, or launchd change was performed.

## Price Source Contract

Runtime v2 Morning Planning requires a reliable BUY sizing price before creating executable OrderPlan / Pending items.

Selected source:

| Contract Field | Value |
| --- | --- |
| selected_price_source | `jquants_raw_normalized_daily_quotes_close` |
| artifact | `.runtime/operations/jquants/raw_normalized/jquants/equities_bars_daily/data.parquet` |
| symbol key | `Code` |
| date key | `Date` |
| price key | `Close` |
| confidence key | `PriceSource` |
| unit | JPY per share |
| timing | previous feature date / market refresh date |
| fallback allowed in normal demo/production runtime | `false` |

Candidate feature rows may still be used for ranking and AI signal generation. They are not the canonical source for executable sizing price.

## Behavior When Price Is Missing

If the canonical price source file is missing:

- Morning status: `NO_SIGNAL`
- Pending state: `PENDING_APPROVAL`
- Pending items: `[]`
- reason: `NO_SIGNAL:reliable_price_source_missing`
- Submit source remains empty and cannot lead to Broker Submit.

If a candidate symbol has no price row:

- That symbol is skipped.
- `price_missing_count` is recorded in the Morning manifest.

If the price exists but the per-order budget cannot buy one 100-share lot:

- That symbol is skipped.
- `budget_excluded_count` is recorded.

If no affordable candidate remains:

- Morning status: `NO_SIGNAL`
- Pending items: `[]`
- reason: `NO_SIGNAL:no_affordable_candidates_with_reliable_price`

If all candidates are filtered by Demo 9000-series capability:

- reason: `NO_SIGNAL:demo_capability_filtered_all_9000_series`

## Code Changes

Changed:

- `src/ai_fund_lab_v2/runtime_v2/planning/models.py`
- `src/ai_fund_lab_v2/runtime_v2/planning/planner.py`
- `src/ai_fund_lab_v2/runtime_v2/planning/morning_pipeline.py`
- `src/ai_fund_lab_v2/runtime_v2/planning/order_plan_builder.py`
- `src/ai_fund_lab_v2/runtime_v2/pending/models.py`
- `src/ai_fund_lab_v2/runtime_v2/pending/reader.py`
- `tests/runtime_v2/planning_fixtures.py`
- `tests/runtime_v2/test_phase14e15_morning_ai_planning_pending_connection.py`

Key implementation detail:

- `CapitalAllocationSignal` now carries the price contract metadata.
- `OrderPlanItem` carries the same metadata.
- `PendingOrderItem` carries the same metadata.
- Generic planner no longer derives price as `cash_required / 100`.
- Morning pipeline loads J-Quants normalized daily quotes and skips candidates that lack reliable prices.

## Sample Order Sizing

Applying the E28 rules to 2026-07-07 feature inputs without writing new Current/Pending produced this read-only sample:

| Symbol | Price | Quantity | Estimated Amount | Price Source |
| --- | ---: | ---: | ---: | --- |
| `68970` | 669 | 100 | 66,900 | `jquants_raw_normalized_daily_quotes_close` |
| `45910` | 98 | 1000 | 98,000 | `jquants_raw_normalized_daily_quotes_close` |
| `39260` | 357 | 200 | 71,400 | `jquants_raw_normalized_daily_quotes_close` |
| `44460` | 853 | 100 | 85,300 | `jquants_raw_normalized_daily_quotes_close` |
| `49350` | 309 | 300 | 92,700 | `jquants_raw_normalized_daily_quotes_close` |

Read-only counters until five candidates were selected:

- Demo 9000-series filtered: `1`
- Budget-excluded because one 100-share lot exceeded per-order budget: `5`
- Price-missing before selection: `0`

This confirms that E28 no longer creates five uniform `estimated_price=1000 / quantity=100` orders.

## Affected Flows

| Flow | Result |
| --- | --- |
| Feature -> Planning | Price now comes from canonical J-Quants normalized daily quotes |
| Planning -> OrderPlan | Price metadata is written |
| OrderPlan -> Pending | Price metadata is preserved |
| Pending -> Submit | Submit still uses Pending-only source; market orders still send `sOrderPrice=0` |
| Report / Audit | Morning manifest now carries price source status and sample sizing details |
| Next Planning | Missing-price operation is blocked before new Pending can be generated |

## Prohibited Actions

| Action | Result |
| --- | --- |
| Additional Submit | Not executed |
| Production order | Not executed |
| Production Broker API Write | Not executed |
| Notification actual send | Not executed |
| launchd change | Not executed |
| Phase9 Runtime復活 | Not executed |
| Phase9 writer use | Not executed |

## Verification

Targeted tests:

```text
PYTHONPYCACHEPREFIX=/tmp/phase14e28_pycache python3 -m pytest tests/runtime_v2/test_phase14e15_morning_ai_planning_pending_connection.py tests/runtime_v2/test_phase13_s_planning_current_state_guard.py tests/runtime_v2/test_phase13_s_planning_to_pending_integration.py tests/runtime_v2/test_phase13_p_pending_reader_writer.py
```

Result:

```text
16 passed
```

Runtime v2 full tests:

```text
PYTHONPYCACHEPREFIX=/tmp/phase14e28_pycache python3 -m pytest tests/runtime_v2
```

Result:

```text
328 passed
```

Note:

`PYTHONPYCACHEPREFIX` was used because default macOS pycache attempted to write outside the workspace sandbox.

## Acceptance Review

| Acceptance Item | Result |
| --- | --- |
| Planning Price Source Contract documented | PASS |
| Reliable price required for normal BUY | PASS |
| Missing-price fallback removed from normal runtime | PASS |
| Real price used for quantity calculation | PASS |
| Missing price source creates no executable orders | PASS |
| OrderPlan / Pending preserve price metadata | PASS |
| Demo 9000-series exclusion preserved | PASS |
| Production 9000-series allowance preserved | PASS |
| tests/runtime_v2 PASS | PASS |
| Additional Submit not executed | PASS |
| Production order not executed | PASS |

## Final Judgment

`PHASE14E28_PLANNING_PRICE_SOURCE_FIXED`
