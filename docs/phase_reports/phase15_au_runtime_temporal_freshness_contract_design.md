# Phase15-AU Runtime Temporal / Freshness Contract Design

## Purpose

Phase15-AU records the design decision created from the Phase15 Runtime Acceptance freshness gaps.

The formal Source of Truth is:

```text
docs/02_architecture/runtime_temporal_freshness_contract.md
```

This phase report is only the Phase15 decision record.

## Background

Phase15-AT found that Step0 / Step1 Recovery cannot safely proceed with a simple rule:

```text
Current.as_of == runtime_business_date
```

The specific observed issue was:

```text
runtime_business_date=2026-07-10
Current.as_of=2026-07-09
```

That may be stale, but in real operation it can also be valid when there is no fill and only valuation must refresh. The design therefore separates Position State freshness from Valuation freshness.

## Created / Updated Files

Created:

- `docs/02_architecture/runtime_temporal_freshness_contract.md`
- `docs/phase_reports/phase15_au_runtime_temporal_freshness_contract_design.md`
- `reports/phase_reports/phase15_au_runtime_temporal_freshness_contract_design.json`

Updated:

- `docs/02_architecture/runtime_architecture_v2.md`

## Key Decisions

```text
CURRENT_FRESHNESS_CONTRACT_REDESIGN_REQUIRED
MARKET_QUOTE_EVIDENCE_CONTRACT_REQUIRED
RUNTIME_STATE_CONTRACT_REQUIRED
READY_FOR_TEMPORAL_CONTRACT_IMPLEMENTATION
```

## Contract Summary

Runtime v2 must distinguish:

```text
runtime_business_date
calendar_date
trading_session_date
latest_expected_trading_date
latest_available_market_date
market_data_as_of
feature_date
broker_snapshot_at
broker_business_date
position_state_as_of
valuation_as_of
last_execution_date
last_reconciled_at
safety_generated_at
safety_expires_at
pending_target_session_date
artifact_generated_at
```

Freshness statuses:

```text
READY
VALID_CARRYOVER
DATA_NOT_YET_AVAILABLE
STALE
MISSING
DATE_MISMATCH
EXPIRED
REVIEW_REQUIRED
HALT
NOT_REQUIRED
```

## Implementation Impact

Required later implementation areas:

- Market Evidence producer
- Quote Evidence producer
- Current schema split
- No-fill / valuation-only Current refresh
- Safety temporal dependency hash
- Data Readiness temporal component statuses
- Report / Notification temporal summary
- Regression matrix

No implementation was performed in this phase.

## Prohibited Actions Confirmation

Not executed:

- Runtime implementation change
- Current schema migration
- Market Refresh
- Feature Refresh
- Broker API connection
- Safety execution
- Data Readiness execution
- Morning / SELL Planning
- Submit
- Execution
- Broker Write
- Orders
- Notification real send
- launchd change
- Current direct edit
- Artifact date rewrite
- Phase15-specific freshness exception

## Final Judgment

```text
RUNTIME_TEMPORAL_FRESHNESS_CONTRACT_DESIGN_COMPLETE
PHASE15AU_RUNTIME_TEMPORAL_FRESHNESS_CONTRACT_DESIGN_COMPLETE
```

