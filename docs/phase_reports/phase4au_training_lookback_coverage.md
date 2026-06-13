# Phase4-AU Training Lookback Coverage Audit

## Purpose

Phase4-AU audits whether Phase4-AO training dataset target dates have enough normalized business-day history for 5d, 20d, and 60d lookback features. This phase performs audit only.

## Explicitly Not Executed

- Feature expansion
- Label changes
- Dataset rebuild
- Training
- Inference
- Backtest
- Trading
- Promotion or reader switch

## Summary

- status: `OK`
- readiness_status: `READY_FOR_LONG_HISTORY_FETCH_PLAN`
- normalized date range: `2026-03-02` to `2026-05-29`
- normalized_business_day_count: `60`
- dataset target_date range: `2026-03-02` to `2026-04-27`
- dataset_target_date_count: `40`
- label target_date range: `2026-03-02` to `2026-04-27`
- feature target_date range: `2026-03-02` to `2026-05-29`

## Lookback Coverage

- first_target_date_with_5d_lookback: `2026-03-06`
- first_target_date_with_20d_lookback: `2026-03-30`
- first_target_date_with_60d_lookback: `None`
- lookback_5d_coverage_rate: `0.9`
- lookback_20d_coverage_rate: `0.525`
- lookback_60d_coverage_rate: `0.0`

## Training Gate Impact

- trainable_target_date_range: `None` to `None`
- trainable_target_date_count: `0`
- trainable_row_count: `0`
- excluded_by_lookback_target_date_count: `40`
- excluded_by_lookback_row_count: `167668`

## Root Cause

No Phase4-AO dataset target_date satisfies the 60-business-day lookback window. Training-period features are null/constant because label target_dates are too early relative to the current real_runtime normalized history.

## Blocking Issue

training_label_target_dates_precede_required_60d_lookback_window

## Recommended Fix Plan

- Plan a longer real_runtime normalized history fetch before formal Candidate training.
- Require at least 60 target_date<=normalized business-day rows before including rows in training.
- Keep feature expansion separate; the current root cause is lookback coverage, not model quality.

## Quality Gate Proposal

Before formal Candidate training, dataset rows should pass a lookback gate that requires the longest active feature window, currently 60 business days, to be available using only target_date-or-earlier normalized history.

