# Phase4-AH Controlled Extension Fetch

## Purpose

Phase4-AH executes a controlled raw fetch for only the six extension dates produced by Phase4-AG.

The target endpoint is:

```text
/v2/equities/bars/daily
```

This phase is raw fetch only. It does not rebuild normalized data, write to `.runtime/data/raw_normalized_real_runtime/`, write to `.runtime/data/raw_normalized/`, promote data, switch readers, generate Candidate features, generate labels, build datasets, train, infer, backtest, trade, call broker APIs, place orders, or update Portfolio state.

## Input

- `reports/candidate_ai/full_range/phase4ag_real_runtime_extension_fetch_dry_run_summary.json`
- `reports/candidate_ai/full_range/phase4ag_real_runtime_extension_fetch_dry_run_requests.json`

Extension dates:

```text
2026-03-02
2026-03-03
2026-03-04
2026-03-05
2026-03-06
2026-03-09
```

## Runtime Output

Raw responses:

```text
.runtime/data/raw/jquants/equities_bars_daily/responses/
```

Request manifests:

```text
.runtime/data/raw/jquants/equities_bars_daily/request_manifests/
```

Run manifest:

```text
.runtime/data/raw/jquants/equities_bars_daily/manifest.json
```

Reports:

```text
reports/candidate_ai/full_range/phase4ah_controlled_extension_fetch_summary.json
reports/phase_reports/phase4ah_controlled_extension_fetch_audit.json
docs/phase_reports/phase4ah_controlled_extension_fetch_audit.md
```

## Safety Rules

- Credentials are read through the existing settings loader.
- The secret value is never printed, logged, or written to report/manifest.
- Summary records only `secret_present` and a non-secret fingerprint.
- Each request is limited to the Phase4-AG extension request sequence.
- Existing successful request manifests are skipped for resume.
- Existing raw response files are not deleted.
- Existing request manifests are not deleted.
- Failed requests write FAILED manifests with sanitized error messages.
- Writes use tmp-to-final atomic JSON moves.
- Pagination is followed only when the API returns `pagination_key`.
- J-Quants Light plan rate limit policy remains one request per second / 60 req per minute.

## Merge Policy

Phase4-AH appends extension date artifacts to the existing raw root. Existing successful manifests and responses remain intact.

If a same-date SUCCESS manifest exists:

```text
skip
```

If a same-date FAILED manifest exists:

```text
rerun candidate
```

## Readiness

On success:

```text
READY_FOR_POST_EXTENSION_RAW_COVERAGE_AUDIT
```

Blocking statuses:

- `BLOCKED_BY_MISSING_PHASE4AG_SUMMARY`
- `BLOCKED_BY_PHASE4AG_NOT_READY`
- `BLOCKED_BY_MISSING_DRY_RUN_REQUESTS`
- `BLOCKED_BY_MISSING_CREDENTIAL`
- `BLOCKED_BY_SECRET_SAFETY`
- `BLOCKED_BY_RATE_LIMIT_SAFETY`
- `BLOCKED_BY_EXTENSION_FETCH_FAILURE`
- `BLOCKED_BY_RAW_WRITE_FAILURE`
- `BLOCKED_BY_MANIFEST_FAILURE`
- `BLOCKED_BY_OUTPUT_PATH_SAFETY`

## Next Phase

Phase4-AI should re-audit raw daily quote coverage after extension fetch. Only if 60 non-empty trading days are confirmed should real runtime normalized rebuild be considered.
