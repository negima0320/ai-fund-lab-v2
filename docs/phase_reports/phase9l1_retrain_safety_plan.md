# Phase9-L1 Retrain Safety Plan

## Purpose

Candidate AI and Opportunity AI are not ready for Phase9 daily inference because Phase9-K found incomplete model metadata and missing Phase9-specific leakage / forbidden-source audit fields.

This phase prepares a safe retrain path only. It does not run training, inference, OrderPlan generation, Paper Ledger fills, virtual fills, or Broker operations.

## Allowed Data Sources

- J-Quants raw daily_quotes
- J-Quants canonical normalized daily_quotes
- J-Quants listed_info
- J-Quants trading_calendar
- J-Quants-derived official data only

## Prohibited Data Sources

- Backtest results
- Paper Ledger
- Realized / unrealized PnL
- OrderPlan
- Human Review
- selected / bought symbols
- cash / portfolio value
- Broker Snapshot
- PF / DD / win rate / trade_count / turnover
- Public Confidence Score / blog drafts / reports / tests
- Future prices beyond the allowed label horizon

Any detected use of prohibited data must fail closed.

## Training Boundary

- data_until: `2026-06-15`
- label_horizon: `20 business days`
- safe_train_until: `2026-05-18`
- train_until: `2026-05-18`

Rows after `2026-05-18` must not be used as 20-business-day labeled training rows.

## Dataset Candidate Policy

Training dataset candidates are written only under:

```text
.runtime/phase9/training_dataset_candidates/2026-05-18/
```

They are isolated from existing Phase4 / Phase5 model artifacts and are not promoted.

## Audit Policy

Each dataset candidate must record:

- source_data_refs
- row_count
- min_date / max_date
- code_count
- feature_columns
- label_columns
- feature_schema_hash
- label_null_rate
- feature_null_rate
- forbidden source check
- forbidden column check
- future leakage check

## Runtime / Effectiveness Measurement

Phase9-L2 may measure training runtime and effectiveness, but Phase9-L1 only prepares dataset candidates and manifests. No model artifact is trained or promoted in this phase.

## Phase9-L2 Safety Conditions

Phase9-L2 may proceed only if:

- Candidate and Opportunity dataset candidates are `TRAINING_DATASET_READY`
- `train_until <= safe_train_until`
- all sources are J-Quants-derived
- forbidden source / column checks are OK
- future leakage check is OK
- model promotion remains disabled by default
