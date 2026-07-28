# Phase22-PS - PIT-valid Strategy Shadow Upstream Source Resolution and BLOCK Closure

## Judgment

Phase22-PS implementation is complete for read-only Strategy shadow source resolution.

Runtime switch: `NO`

Active Runtime consumer promotion: `NO`

Legacy Runtime retirement: `NO`

Strategy shadow production mutation: `NO`

## Scope

Phase22-PS adds a production-common, read-only PIT source manifest for Runtime Test Strategy shadow evidence. It does not change active BUY, PM, Sell quantity, Pending, Submit, Execution, Fill, Ledger, Current, Broker, Runtime switch, or legacy authority.

Daily Strategy shadow now writes:

```text
reports/runtime_tests/runs/<RUN_ID>/daily/<DATE>/strategy/source_manifest.json
```

`input_manifest.json` references the source manifest path and manifest hash. `strategy_shadow_summary.json` exposes PIT validation, source manifest hash, direct blockers, propagated blockers, root blocker components, root reason codes, future-row rejection count, latest fallback flag, current-state leakage flag, sector PIT status, and corporate-event coverage status.

## Root Cause

The active historical smoke probe for `2022-09-15` previously classified Market Context and Corporate Event as future-leakage BLOCK because the source parquet files contained rows after the business date. That check was too broad: it treated future rows present in the file as equivalent to future rows selected.

Phase22-PS changes this boundary:

- Future rows present but not selected are recorded as rejected source rows.
- D-or-earlier rows are selected when available.
- If only future rows exist for the business date, the source remains fail-closed as `BLOCK` / `SOURCE_UNAVAILABLE` / `BOOTSTRAP_REQUIRED`.
- Corporate Event does not convert missing or partial coverage into confirmed `NO_EVENT`.

For the current active probe date `2022-09-15`, `.runtime` market/listed source coverage starts in 2026, so no PIT source row exists for that historical date. The resulting BLOCK is now a valid upstream source unavailability/bootstrap BLOCK, not a silent latest/current fallback.

## Implemented

- Added `ai_fund_lab_v2.strategy.source_manifest`.
- Added source resolution for portfolio state, pending state, market quotes, benchmark, sector, corporate event, Candidate, Opportunity, and bootstrap.
- Added PIT validation fields: `latest_fallback_used`, `current_state_leakage_detected`, `future_row_rejection_count`, `source_unavailable`, `bootstrap_required`, and `pit_valid`.
- Added direct vs propagated blocker classification.
- Connected `source_manifest.json` to Strategy shadow generation, run summary aggregation, validation, and `show --artifact strategy`.
- Updated Market Context and Corporate Event future-row handling so future rows are rejected unless selected.
- Updated Runtime Test guide with Strategy source manifest and PIT rollup behavior.

## Evidence

Required regression commands:

```bash
PYTHONPATH=src PYTHONPYCACHEPREFIX=/private/tmp/pycache python3 -m pytest tests/strategy -q
PYTHONPATH=src PYTHONPYCACHEPREFIX=/private/tmp/pycache python3 -m pytest tests/runtime_v2/test_phase22_p_strategy_shadow_wiring.py tests/runtime_v2/test_phase22_m_strategy_summarize_scope.py tests/runtime_v2/test_phase19_ax_system_status.py -q
PYTHONPATH=src PYTHONPYCACHEPREFIX=/private/tmp/pycache python3 -m pytest tests/strategy/test_phase22_pr_dynamic_capacity_asset_proportionality.py -q
PYTHONPATH=src PYTHONPYCACHEPREFIX=/private/tmp/pycache python3 -m compileall src scripts tests
```

Results:

- `tests/strategy`: `124 passed`
- Runtime Strategy/System Status regression: `8 passed`
- Phase22-PR dynamic capacity regression: `5 passed`
- `compileall`: PASS

1BD probe:

- Run: `runtime-test-historical-smoke-20260726T224753726008Z`
- Business date: `2022-09-15`
- `source_manifest.json`: generated
- `latest_fallback_used`: `false`
- `current_state_leakage_detected`: `false`
- `future_row_rejection_count`: `471075`
- PIT validation: `BLOCK`
- Cause: no D-or-earlier market/listed rows in the available `.runtime` source files for `2022-09-15`; bootstrap history is insufficient.

`summarize --scope strategy` on this existing run returns exit code `10` because the run remains Strategy BLOCK/incomplete. This is expected for the active historical probe and does not indicate a mutation or consumer-promotion failure.

Evidence artifacts:

```text
reports/phase22_ps_pit_valid_strategy_shadow_upstream_source_resolution_and_block_closure/
```

## Long Probe

Codex did not run the long 5BD probe.

Recommended operator command:

```bash
PYTHONPATH=src PYTHONPYCACHEPREFIX=/private/tmp/pycache python3 scripts/runtime_test.py fresh-run --profile historical-smoke --business-days 5 --start-date <PIT_COVERED_START_DATE> --confirm --yes-i-understand-this-mutates-trading-state
```

Use a start date covered by the isolated runtime root's historical market/listed/candidate/opportunity sources. A 5BD result must not be considered PASS if it succeeds by latest artifact fallback or current-state leakage.

## Final Judgment

Phase22-PS PIT Source Manifest Implemented: `YES`

Future Row Presence No Longer Equals Use: `YES`

Latest Fallback Used: `NO`

Current State Leakage Detected: `NO`

Active Runtime Mutation: `NO`

Runtime Switch Approved: `NO`

Phase22 Closure Recommendation: `REVIEW_REQUIRED`

Remaining blocker: PIT-covered historical upstream source availability for the selected historical Runtime Test dates.
