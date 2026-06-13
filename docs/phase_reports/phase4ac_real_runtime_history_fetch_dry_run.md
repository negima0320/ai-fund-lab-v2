# Phase4-AC Real Runtime History Fetch Dry-run CLI

## Purpose

Phase4-AC adds a no-live dry-run CLI that reads the Phase4-AB fetch plan and renders the J-Quants daily quotes request sequence without calling J-Quants.

This phase creates only planning artifacts:

- dry-run request sequence
- dry-run summary
- audit report

It does not call APIs, execute fetches, initialize an HTTP client, read credentials, write raw data, write normalized data, promote data, switch readers, generate Candidate features, generate labels, train, infer, backtest, trade, call broker APIs, place orders, or update Portfolio state.

## Read Inputs

- `docs/01_requirements/phase_roadmap.md`
- `docs/03_ai_design/candidate_ai_design.md`
- `docs/03_ai_design/candidate_feature_catalog.md`
- `docs/03_ai_design/candidate_training_data_design.md`
- `docs/03_ai_design/candidate_feature_builder_design.md`
- `docs/phase_reports/phase4_handoff_summary.md`
- `docs/phase_reports/phase4aa_real_runtime_coverage_gap_plan.md`
- `docs/phase_reports/phase4ab_no_live_real_runtime_fetch_plan.md`
- `reports/candidate_ai/full_range/phase4aa_real_runtime_coverage_gap_plan_summary.json`
- `reports/candidate_ai/full_range/phase4ab_no_live_real_runtime_fetch_plan_summary.json`
- `reports/phase_reports/phase4ab_no_live_real_runtime_fetch_plan_audit.json`
- `scripts/audit_phase4ab_no_live_real_runtime_fetch_plan.py`
- `tests/test_phase4ab_no_live_real_runtime_fetch_plan.py`

## CLI

Run:

```bash
python3 scripts/phase4ac_real_runtime_history_fetch_dry_run.py
```

The CLI reads:

```text
reports/candidate_ai/full_range/phase4ab_no_live_real_runtime_fetch_plan_summary.json
```

It writes:

```text
reports/candidate_ai/full_range/phase4ac_real_runtime_history_fetch_dry_run_requests.json
reports/candidate_ai/full_range/phase4ac_real_runtime_history_fetch_dry_run_summary.json
```

Stdout prints only:

- no-live dry-run status
- target date range
- planned / generated request count
- request artifact path
- `api_call_performed=false`
- `fetch_executed=false`

## Request Sequence

Each request has:

- `request_index`
- `endpoint`
- `method`
- `date`
- `code`
- `pagination_key`
- `params`
- `planned_raw_output_path`
- `expected_rate_limit_delay_seconds`
- `pagination_placeholder`
- `no_live`
- `api_call_performed`
- `fetch_executed`

Current endpoint:

```text
/v2/equities/bars/daily
```

Current method:

```text
GET
```

Current target range:

```text
2026-03-10 .. 2026-06-01
```

The initial request sequence includes one request per missing business day. Pagination is represented as a placeholder because additional pages can be known only during controlled fetch.

## Current Plan Result

Current Phase4-AB input:

- `planned_request_count = 59`
- `target_start_date = 2026-03-10`
- `target_end_date = 2026-06-01`
- raw output plan: `.runtime/data/raw/jquants/equities_bars_daily/`
- isolated normalized output plan: `.runtime/data/raw_normalized_real_runtime/jquants/equities_bars_daily/`
- mock normalized path remains unchanged: `.runtime/data/raw_normalized/jquants/equities_bars_daily/`

## Safety Guarantees

Phase4-AC sets:

- `api_call_performed = false`
- `fetch_executed = false`
- `credential_read_performed = false`
- `http_client_initialized = false`
- `raw_data_written = false`
- `normalized_data_written = false`
- `promotion_performed = false`
- `reader_switch_performed = false`
- `feature_generation_executed = false`
- `label_generation_executed = false`
- `training_executed = false`
- `inference_executed = false`
- `backtest_executed = false`
- `trading_executed = false`

The CLI does not import or initialize the J-Quants client. It reads only Phase4-AB JSON and writes report artifacts under `reports/`.

## Gates Carried Forward

The dry-run summary carries forward:

- manifest / provenance plan
- post-fetch raw audit condition
- post-normalize coverage audit condition
- promotion gate
- reader switch gate
- rollback plan

## Readiness Status

If the Phase4-AB summary is present, ready, request sequence count matches the planned count, output paths are safe, and no-live safety flags are all false:

```text
READY_FOR_CONTROLLED_REAL_RUNTIME_HISTORY_FETCH
```

This means the project is ready to consider a separately approved controlled fetch phase. It does not mean any fetch has happened.

## Output Reports

Summary:

- `reports/candidate_ai/full_range/phase4ac_real_runtime_history_fetch_dry_run_summary.json`

Request artifact:

- `reports/candidate_ai/full_range/phase4ac_real_runtime_history_fetch_dry_run_requests.json`

Audit:

- `reports/phase_reports/phase4ac_real_runtime_history_fetch_dry_run_audit.json`
- `docs/phase_reports/phase4ac_real_runtime_history_fetch_dry_run_audit.md`

## Explicit Non-goals

Phase4-AC does not implement:

- J-Quants API call
- HTTP request execution
- credential reading
- live fetch
- raw data write
- normalized data write
- promotion
- reader switch
- Candidate feature full generation
- label generation
- dataset builder
- Candidate AI model
- training
- inference
- backtest
- Historical Evaluation
- Opportunity AI
- Position Management AI
- Capital Allocation
- Paper Trading
- Order Manager
- Broker API
- order placement
- trading
- Portfolio auto-update

## Phase4-AD Proposal

Phase4-AD should be `Controlled Real Runtime History Fetch`.

Phase4-AD is the first phase that may use J-Quants credentials, but only after explicit approval. It must add credential handling, rate-limit enforcement, resume behavior, partial failure handling, raw manifest writing, and post-fetch raw audit before any normalization or promotion.
