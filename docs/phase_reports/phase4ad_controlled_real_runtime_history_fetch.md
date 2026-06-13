# Phase4-AD Controlled Real Runtime History Fetch

## Purpose

Phase4-AD implements the controlled raw fetch step for J-Quants daily quotes history based on the Phase4-AC dry-run request sequence.

This phase is raw fetch only.

It may read J-Quants credentials and initialize the HTTP client, but it does not normalize data, write to normalized paths, promote data, switch readers, generate Candidate features, generate labels, build datasets, train, infer, backtest, trade, call broker APIs, place orders, or update Portfolio state.

## Read Inputs

- `docs/01_requirements/phase_roadmap.md`
- `docs/03_ai_design/candidate_ai_design.md`
- `docs/03_ai_design/candidate_training_data_design.md`
- `docs/03_ai_design/candidate_feature_builder_design.md`
- `docs/phase_reports/phase4ab_no_live_real_runtime_fetch_plan.md`
- `docs/phase_reports/phase4ac_real_runtime_history_fetch_dry_run.md`
- `reports/candidate_ai/full_range/phase4ab_no_live_real_runtime_fetch_plan_summary.json`
- `reports/candidate_ai/full_range/phase4ac_real_runtime_history_fetch_dry_run_summary.json`
- `reports/candidate_ai/full_range/phase4ac_real_runtime_history_fetch_dry_run_requests.json`
- `scripts/phase4ac_real_runtime_history_fetch_dry_run.py`
- `scripts/audit_phase4ac_real_runtime_history_fetch_dry_run.py`
- `src/ai_fund_lab_v2/data_sources/jquants/client.py`
- `src/ai_fund_lab_v2/config/settings.py`
- `src/ai_fund_lab_v2/data_store/`
- `src/ai_fund_lab_v2/runtime/`

## CLI

Run:

```bash
python3 scripts/phase4ad_controlled_real_runtime_history_fetch.py
```

The CLI reads:

```text
reports/candidate_ai/full_range/phase4ac_real_runtime_history_fetch_dry_run_summary.json
reports/candidate_ai/full_range/phase4ac_real_runtime_history_fetch_dry_run_requests.json
```

It writes raw fetch artifacts under:

```text
.runtime/data/raw/jquants/equities_bars_daily/
```

## Runtime Output

Run manifest:

```text
.runtime/data/raw/jquants/equities_bars_daily/manifest.json
```

Per-request manifests:

```text
.runtime/data/raw/jquants/equities_bars_daily/request_manifests/
```

Raw responses:

```text
.runtime/data/raw/jquants/equities_bars_daily/responses/
```

Each response is written with tmp -> final atomic move.

## Controlled Fetch Rules

- Only Phase4-AC request sequence dates are eligible.
- Endpoint is `/v2/equities/bars/daily`.
- Method is `GET`.
- `date` is taken from the dry-run request artifact.
- `code = None`.
- Pagination is followed within the same date when `pagination_key` is returned.
- `max_pages` guard is enforced.
- Successful request manifests support resume.
- Existing `SUCCESS` request manifests are skipped.
- Failed requests write `FAILED` manifests.
- Partial tmp files are reported as warnings.

## Credential Safety

Credentials are read only through existing settings.

Rules:

- credential values are not printed
- credential values are not written to summary
- credential values are not written to manifests
- credential values are not written to reports
- credential values are not included in exception messages
- audit reports only `secret_present`, not the value
- run manifest may include a non-reversible fingerprint, not the value

## Rate Limit Policy

The J-Quants client keeps the existing configured rate limit.

The Phase4-AC plan carries:

```text
Light plan 60 req/min
at most 1 request/sec
no burst
```

Phase4-AD records this policy in the summary. Future hardening may add external scheduling metrics, but this phase reuses the client rate-limit guard.

## Resume Policy

Per-date request manifest:

```text
request_manifests/YYYY-MM-DD.json
```

If that manifest has:

```text
status = SUCCESS
```

then the date is skipped on rerun.

If the manifest has:

```text
status = FAILED
```

then the date is retried on rerun.

## Partial Failure Policy

If a request fails:

- keep successful earlier responses
- write `FAILED` request manifest for the failed date
- do not delete successful response files
- return `BLOCKED_BY_FETCH_FAILURE`
- do not normalize or promote

## Explicit Non-goals

Phase4-AD does not implement:

- normalized data rebuild
- `.runtime/data/raw_normalized_real_runtime/` writes
- `.runtime/data/raw_normalized/` writes
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
- Broker API
- order placement
- trading
- Portfolio auto-update

## Readiness Status

Success:

```text
READY_FOR_POST_FETCH_RAW_AUDIT
```

Blocking statuses:

- `BLOCKED_BY_MISSING_PHASE4AC_SUMMARY`
- `BLOCKED_BY_PHASE4AC_NOT_READY`
- `BLOCKED_BY_MISSING_DRY_RUN_REQUESTS`
- `BLOCKED_BY_MISSING_CREDENTIAL`
- `BLOCKED_BY_SECRET_SAFETY`
- `BLOCKED_BY_RATE_LIMIT_SAFETY`
- `BLOCKED_BY_FETCH_FAILURE`
- `BLOCKED_BY_RAW_WRITE_FAILURE`
- `BLOCKED_BY_MANIFEST_FAILURE`
- `BLOCKED_BY_OUTPUT_PATH_SAFETY`

## Output Reports

Summary:

- `reports/candidate_ai/full_range/phase4ad_controlled_real_runtime_history_fetch_summary.json`

Audit:

- `reports/phase_reports/phase4ad_controlled_real_runtime_history_fetch_audit.json`
- `docs/phase_reports/phase4ad_controlled_real_runtime_history_fetch_audit.md`

## Phase4-AE Proposal

Phase4-AE should be `Post-fetch Raw Coverage Audit`.

It should inspect Phase4-AD raw responses and manifests for coverage, row count, code count, business day count, pagination consistency, provenance, and credential non-disclosure. Normalization should remain Phase4-AF or later.
