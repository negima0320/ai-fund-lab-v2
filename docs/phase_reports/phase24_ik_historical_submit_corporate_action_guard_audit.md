# Phase24-IK Historical Submit Corporate Action Guard Audit

## 1. Primary Judgment

`PHASE24_IK_CORPORATE_ACTION_GUARD_FAIL_CLOSED_VALID_OBSERVABILITY_REPAIRED_OPERATOR_CORPORATE_ACTION_AUTHORITY_REQUIRED`

## 2. Runtime Scope

- Runtime Run: `runtime-test-historical-extended-smoke-20260801T223117629647Z`
- Business Date: `2023-10-04`
- Job: `submit`
- Symbol: `65730`
- Side: `SELL`
- Quantity: `200`
- Pending Item ID: `opi-sell-exit-pm-65730-001`
- Runtime Executed In This Task: `NO`

## 3. Direct Halt

Submit halted at Historical Submit Adapter preflight:

- `preflight_status`: `HALT`
- `reason`: `corporate action guard failed`
- `corporate_action_status`: `IMPACT_DETECTED`
- `next_action`: `fix_historical_submit_preflight_input`

Submit Guard itself passed:

- `guard_decision`: `PASS`
- `sell_quantity_guard_status`: `PASS`
- `current_quantity`: `200`
- `broker_available_quantity`: `200`
- `broker_total_quantity`: `200`
- `broker_restricted_quantity`: `0`

Safety and PIT Universe also passed.

## 4. Call Path

The call path is:

```text
run_submit_pipeline
  -> run_submit_preflight
  -> HistoricalSubmitAdapter.preflight
  -> HistoricalSubmitAdapter._validate_command
  -> HistoricalSubmitAdapter._resolve_open_price
  -> _corporate_action_evidence / _corporate_action_status
```

The guard reads run-scoped Historical raw OHLCV:

`reports/runtime_tests/runs/runtime-test-historical-extended-smoke-20260801T223117629647Z/daily/2023-10-04/market_refresh/inputs/historical_asof/2023-10-04/raw/jquants/equities_bars_daily/data.parquet`

It returns `IMPACT_DETECTED` when the target business-date and target-symbol raw OHLCV row has `AdjFactor != 1.0`.

## 5. Corporate Action Evidence

For `65730` on `2023-10-04`, raw OHLCV contains:

- `AdjFactor`: `0.3333333333333333`
- `O/H/L/C`: `823.0 / 865.0 / 780.0 / 795.0`
- `AdjO/AdjH/AdjL/AdjC`: `823.0 / 865.0 / 780.0 / 795.0`
- Impact condition: `target_date_target_symbol_adjfactor_not_1`

The directly available artifact does not provide legal event type fields such as stock split, reverse split, merger, TOB, record date, or new symbol. Therefore the audited corporate action type is:

`UNKNOWN_ADJFACTOR_IMPACT`

The price/volume adjustment pattern is consistent with a split-like adjustment, but the report does not assert `株式分割` as a direct fact because standalone corporate action authority is missing.

## 6. Corporate Event Artifact Conflict

`strategy/corporate_event.json` reports `65730` as `KNOWN_NO_EVENT`, while its source coverage says:

- `jquants_corporate_actions`: `UNKNOWN_DUE_TO_MISSING_COVERAGE`
- reason: `jquants_corporate_actions_not_implemented_or_missing`

This means Corporate Event Artifact is not sufficient to override the Submit Corporate Action Guard. The Submit Guard's raw OHLCV `AdjFactor` impact is the stronger fail-closed signal at submit boundary.

## 7. Temporal Authority

| Field | Value |
|---|---|
| Business Date | `2023-10-04` |
| Submit evaluation time | `2023-10-04T08:45:00+09:00` |
| Current state business date | `2023-10-03` |
| Current position state as-of | `2023-09-29` |
| Current valuation as-of | `2023-10-03` |
| Current source market date | `2023-10-03` |
| Pending price as-of | `2023-09-05` |
| Corporate action effective date | `2023-10-04` |
| Corporate action source data as-of | `2023-10-04` |
| PIT listed snapshot date | `2023-10-04` |

`price_as_of=2023-09-05` is a valid carried current-SoT field for the Pending item provenance, but it is not sufficient submit valuation authority after a target-date `AdjFactor` impact. Submit correctly failed closed before fill.

## 8. Adjustment Status

- Current Position Quantity: `200`
- Current Valuation Price: `808.0`
- Current Valuation As Of: `2023-10-03`
- Pending Quantity: `200`
- Pending Price: `808.0`
- Pending Price As Of: `2023-09-05`
- Current Position Adjustment Status: `NOT_EVIDENCED`
- Current Valuation Adjustment Status: `PRE_EVENT_AS_OF_2023-10-03`
- Pending Quantity Adjustment Status: `NOT_ADJUSTED_FOR_2023-10-04_ADJFACTOR`
- Pending Price Adjustment Status: `PRE_EVENT_CURRENT_SOT`
- Corporate Action Already Applied: `NO_EVIDENCE`

The open 65730 campaign still had `current_quantity=200`. A quantity adjustment lineage for the `2023-10-04` adjustment was not found.

## 9. Resume Classification

Resume-specific defect: `NO`.

The same Runtime state in a continuous run would still reach the same Historical Submit Adapter preflight and see the same target-date raw OHLCV `AdjFactor=1/3`. This is not caused by a stale same-day Pending replay. It is a production runtime/historical model boundary gap around corporate action adjustment authority.

## 10. Defect Classification

- Production Runtime Defect: `YES`, because submit needs a formal corporate action adjustment authority before accepting adjusted/impacted positions.
- Historical Adapter Defect: `PARTIAL`, observability was insufficient before this repair.
- Corporate Action Guard Defect: `NO`, fail-closed behavior is correct.
- Temporal Authority Defect: `YES`, Current/Pending adjustment state is not proven for submit date.
- Observability Gap: `YES`, repaired by exposing AdjFactor evidence and artifact path.

## 11. Repair Performed

Updated `src/ai_fund_lab_v2/runtime_v2/historical_support/environment.py`:

- Added `_corporate_action_evidence`.
- Preserved `_corporate_action_status` compatibility.
- Added response classification details:
  - `corporate_action_artifact_path`
  - `corporate_action_guard_version`
  - `corporate_action_adjustment_factor`
  - `corporate_action_adjustment_factors`
  - `corporate_action_effective_date`
  - `corporate_action_type`
  - `corporate_action_type_authority`
  - `corporate_action_rows`
  - `corporate_action_impact_detected_condition`

No guard was weakened.

## 12. Validation

- Corporate Action / PIT / Historical Submit regression: `26 passed`
- Submit Guard related regression: `30 passed`
- Safety Guard direct regression: `2 passed`
- Python compile: `PASS`
- JSON validity: `PASS`
- `git diff --check`: `PASS`
- Runtime executed: `NO`

Note: an unrelated existing Phase15n morning integration fixture failed when run as part of a broader bundle; direct Safety Submit Guard tests passed.

## 13. Recommended Next Task

`Phase24-IL Corporate Action Adjustment Authority and Current/Pending Quantity Reconciliation Design`

The next task should define and implement a formal adjustment authority that can decide whether a target-date `AdjFactor` impact is already applied to Current/Pending quantity and valuation, or must block submit until adjusted.
