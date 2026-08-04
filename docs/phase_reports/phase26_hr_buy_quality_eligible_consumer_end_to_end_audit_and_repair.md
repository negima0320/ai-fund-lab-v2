# Phase26-HR BUY Quality Eligible Consumer End-to-End Audit and Repair

## Judgment

PHASE26_HR_BUY_QUALITY_ELIGIBLE_CONSUMER_EDGE_REPAIRED

## Primary Root Cause

BUY Quality produced valid eligible decisions in the target run, but the Consumer edge into Portfolio Construction dropped the decision rows. `shadow_runtime._pc_summary()` loaded generic rows only and did not expose `buy_quality_decisions.json.decisions` as `PortfolioConstructionSourceSummary.rows`.

Portfolio Construction therefore produced membership and non-zero `target_weight`, but without `quality_decision_id` / `quality_action`. Position Sizing correctly failed closed with `adaptive_buy_quality_decision_missing`, resulting in `QUALITY_UNAVAILABLE`, `target_weight=0`, `target_notional=0`, `quantity_delta_candidate=0`. Runtime Planning then emitted `NO_ORDER` / `zero_quantity_delta`, so Pending, Submit, and Execution received no BUY item.

## First Divergence

- Stage: Portfolio Construction Consumer Edge
- Field: `portfolio_members[].quality_decision_id`
- First downstream visible reason: `adaptive_buy_quality_decision_missing` in Position Sizing

## Repair

`shadow_runtime._pc_summary()` now reads `payload.decisions` from artifact-backed summary items. This connects `buy_quality_decisions.json` to Portfolio Construction membership rows without changing the Quality formula, boundaries, weights, Safety, Submit Guard, Accepted Generation, Temporal Authority, or runtime mode behavior.

## Target Run Trace

The 15 requested candidates are saved in:

- `eligible_buy_end_to_end_trace.json`
- `eligible_buy_end_to_end_trace.csv`

All 15 had non-zero Portfolio Construction `target_weight`, then zeroed at Position Sizing due missing Adaptive BUY Quality lineage.

## target_position_count Residual Judgment

`target_position_count` was not the root cause for this run. The 15 eligible rows had PC membership `ADD_CANDIDATE` and non-zero `target_weight`. `member_not_selected` / `opportunity_not_selected` were not present for the 15 rows. Residual terms are classified in `target_position_count_derived_residual_audit.json`.

## Regression

- compile: PASS
- Phase26-H / Portfolio Construction / Position Sizing / Runtime Planning: PASS, 105 passed
- manifest / closure included: PASS, 118 passed set
- Pending / Submit Guard / Strategy Planning Authority: PASS, 28 passed
- fresh-run: NOT EXECUTED

## User Rerun Command

```bash
PYTHONPATH=src python3 scripts/runtime_test.py fresh-run --profile historical-smoke --date-from 2022-07-01 --business-days 3
```

## Readiness

READY
