# Phase4-AY Long History Request Regeneration

- status: `OK`
- readiness_status: `READY_FOR_LONG_HISTORY_CONTROLLED_FETCH_RETRY`
- corrected_fetch_start_date: `2021-06-01`
- fetch_end_date: `2026-06-12`
- request_count: `1314`
- excluded_pre_start_request_count: `60`
- safe_to_resume_after_correction: `True`
- storage_estimate_mb: `3112.64`

## Resume / Quarantine Policy

Treat Phase4-AX FAILED manifests dated 2021-03-09 through 2021-05-31 as out-of-scope legacy failures. Do not delete them; move to a quarantine namespace or filter them out in retry/resume logic.

## Scope Guard

- api_call_performed: `False`
- credential_read_performed: `False`
- fetch_executed: `False`
- normalized/feature/label/dataset/training/inference/backtest/trading: `False`
- promotion_performed / reader_switch_performed: `False`
