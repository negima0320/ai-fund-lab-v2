# Phase15-AZ Current Valuation-Only / No-Fill Producer Implementation

## Purpose

Phase15-AZ implements the Runtime v2 Current Valuation-Only / No-Fill Producer.

The goal is to refresh valuation evidence for Runtime-owned Current positions without creating or implying fills. This phase closes the contract:

```text
AY Current Temporal State
+
AW Market / Quote Evidence
+
Temporal Context
↓
Current Valuation Refresh
↓
Current valuation candidate / artifact
↓
Optional explicit apply
↓
Data Readiness / Report / Notification evidence
```

This phase does not implement Market producer changes, Broker API access, Submit, Execution, Broker Write, Demo orders, Production orders, real notification send, launchd changes, or direct editing of the real Runtime Current.

## Implementation Summary

Added `src/ai_fund_lab_v2/runtime_v2/current_state/valuation.py`.

The producer:

- reads AY temporal Current from `.runtime/persistent_ledger/state.json`
- reads canonical AW Market / Quote Evidence from `.runtime/runtime_state/market/latest.json` or dated `market_evidence.json`
- updates valuation fields only
- writes an artifact to `.runtime/runtime_state/current_valuation/<business_date>/current_valuation_refresh.json`
- writes idempotent valuation history under `.runtime/persistent_ledger/history/valuation/<valuation_as_of>/<hash>.json`
- leaves Current unchanged by default
- applies Current only when `--apply-current-valuation` is explicitly set and status is `READY`

## No-Fill Contract

The valuation producer may update:

```text
current_price
market_value
unrealized_pnl
valuation_as_of
source_market_date
valuation_source
valuation_generated_at
no_fill
```

The valuation producer must not update:

```text
quantity
average_price
ownership
position_state_as_of
last_execution_date
realized_pnl
```

Regression coverage confirms these fields are preserved.

## Controlled Review Behavior

The producer returns `REVIEW_REQUIRED` and does not partially update valuation when:

- Market evidence is stale or not allowed
- required quote evidence is missing
- quote price is invalid
- Current has not been migrated to AY temporal schema

If Current has no Runtime-owned positions, the producer returns `READY` with:

```text
no_position=true
no_position_reason=current_has_no_runtime_owned_positions
```

No quote is required in that case.

## CLI Connection

Updated `python3 -m ai_fund_lab_v2.runtime_v2.cli.run_daily_operation` with:

```text
--job current_valuation_refresh
--apply-current-valuation
```

Default behavior is dry-run / artifact-only. Current write requires explicit `--apply-current-valuation`.

The runtime manifest now includes Current valuation evidence fields such as:

```text
current_valuation_refresh_status
current_valuation_refresh_reason
current_valuation_market_evidence_path
current_valuation_market_date
current_valuation_as_of
current_valuation_no_fill
current_valuation_apply_requested
current_valuation_apply_executed
current_position_status
current_valuation_status
```

## Data Readiness Integration

Updated Data Readiness so Current position freshness and valuation freshness are separated:

```text
current_position_status
current_valuation_status
position_state_as_of
valuation_as_of
source_market_date
current_legacy_as_of_used
```

This prevents position state carryover and valuation freshness from being treated as the same condition.

## Report / Notification Integration

Report and notification payload evidence now include Current valuation refresh summary:

```text
current_valuation_status
current_valuation_reason
```

Notification remains payload-only when used in Phase15 acceptance flows; this phase did not perform real notification send.

## Regression Coverage

Added:

```text
tests/runtime_v2/test_phase15az_current_valuation_no_fill_producer.py
```

Coverage includes:

- valuation-only update preserves quantity / average price / position state / execution date
- non-trading-day carryover remains valid
- stale Market evidence returns `REVIEW_REQUIRED`
- missing quote returns `REVIEW_REQUIRED` with no partial valuation update
- invalid quote price returns `REVIEW_REQUIRED`
- stale quote freshness returns `REVIEW_REQUIRED`
- quote market date mismatch returns `REVIEW_REQUIRED`
- missing quote source returns `REVIEW_REQUIRED`
- feature artifact or previous price is not used as fallback
- no Runtime-owned positions returns `READY` without quotes
- dry-run does not modify Current
- explicit apply writes backup and Current atomically
- valuation history is idempotent
- corrupt Current returns `HALT`
- legacy Current requires AY migration first
- broker-only positions are not added to Current
- regular CLI job writes artifact in dry-run mode

## Verification

Executed:

```text
python3 -m pytest tests/runtime_v2/test_phase15az_current_valuation_no_fill_producer.py
```

Result:

```text
17 passed
```

Executed retention suite:

```text
python3 -m pytest \
  tests/runtime_v2/test_phase15az_current_valuation_no_fill_producer.py \
  tests/runtime_v2/test_phase15ay_current_temporal_schema_migration.py \
  tests/runtime_v2/test_phase15av_runtime_temporal_contract_foundation.py \
  tests/runtime_v2/test_phase15aw_market_quote_evidence_producer.py \
  tests/runtime_v2/test_phase15ap_position_management_input_contract.py \
  tests/runtime_v2/test_phase15aq_runtime_data_readiness_gate.py \
  tests/runtime_v2/test_phase15as_data_readiness_semantic_consistency.py \
  tests/runtime_v2/test_phase15ad_runtime_safety_evaluation_regular_path.py \
  tests/runtime_v2/test_phase14e21_execution_readonly_pipeline.py \
  tests/runtime_v2/test_phase14e25_runtime_owned_fill_projection.py \
  tests/runtime_v2/test_phase15r_report_notification_reason_propagation.py
```

Result:

```text
96 passed
```

## Prohibited Actions Check

Not performed:

- Market Refresh real operation
- Broker API connection
- Submit
- Execution
- Broker Write
- Demo order
- Production order
- real notification send
- launchd change
- direct edit of real Runtime Current

## Final Judgment

```text
PHASE15AZ_CURRENT_VALUATION_NO_FILL_PRODUCER_COMPLETE
```
