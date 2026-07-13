# Phase16-E Historical Runtime Simulation Prerequisite Re-Audit

Prefix: `Phase16-E`

## Executive Summary

Phase16-D resolved the material semantic clock blockers identified in Phase16-C. The normal Runtime v2 path now propagates `--evaluation-time` to Pending lifecycle, Data Readiness, Market Refresh/Evidence, BUY AI producer, PM producer, review-only producer, and Submit; Submit also records deterministic Pending and Ledger timestamps when `now` is supplied.

Historical Runtime Simulation must still not start. The remaining blockers are not temporal clock bugs; they are missing prerequisites around full-state Backup/Reset/Restore, CLI-selectable Historical Broker injection, Historical Execution Evidence production, point-in-time run manifest, and model/config freeze.

Final judgment: `PHASE16_E_PREREQUISITES_READY_FOR_IMPLEMENTATION`.

This means the missing implementation units and connection points are now clear. It does not mean 5 business day Historical Simulation is startable.

## Scope And Non-Actions

Performed:

- Read-only code and contract inspection.
- Read-only historical data range inspection.
- Phase16-D diff and test evidence review.
- Report creation only.

Not performed:

- No Runtime code change.
- No CLI change.
- No Broker implementation.
- No Reset, Restore, or Current/Ledger/Pending mutation.
- No Historical Simulation, 5BD test, 2021 replay, or AI retraining.

## Phase16-D Fix Verification

Verified from current diff and test additions:

- `src/ai_fund_lab_v2/runtime_v2/cli/run_daily_operation.py:323-330` passes `now=evaluation_time` to Pending lifecycle.
- `src/ai_fund_lab_v2/runtime_v2/cli/run_daily_operation.py:425-442` passes `now=evaluation_time` to Data Readiness.
- `src/ai_fund_lab_v2/runtime_v2/cli/run_daily_operation.py:462-473` passes `now=evaluation_time` to BUY AI producer.
- `src/ai_fund_lab_v2/runtime_v2/cli/run_daily_operation.py:523-532` passes `now=evaluation_time` to PM producer.
- `src/ai_fund_lab_v2/runtime_v2/cli/run_daily_operation.py:579-586` passes `now=evaluation_time` to review-only producer.
- `src/ai_fund_lab_v2/runtime_v2/cli/run_daily_operation.py:676-687` passes `now=evaluation_time` to Submit.
- `src/ai_fund_lab_v2/runtime_v2/cli/run_daily_operation.py:743-750` passes `now=evaluation_time` to Market Refresh.
- `src/ai_fund_lab_v2/runtime_v2/submit/pipeline.py:128-145` accepts optional `now` and derives a single timestamp.
- `src/ai_fund_lab_v2/runtime_v2/submit/pipeline.py:367-392` uses that timestamp for Pending state updates.
- `src/ai_fund_lab_v2/runtime_v2/submit/pipeline.py:333-339` and `src/ai_fund_lab_v2/runtime_v2/submit/pipeline.py:561-574` use the same timestamp for Ledger order creation.
- `src/ai_fund_lab_v2/runtime_v2/pending/lifecycle_runner.py:351-359` now compares approval expiry with timezone-aware parsing.

Phase16-D test evidence already passed:

- `tests/runtime_v2/test_phase15ar_pending_lifecycle_stale_handling.py` and `tests/runtime_v2/test_phase14e17_submit_pipeline_connection.py`: `17 passed`.
- Phase15 submit / safety / acceptance regression set: `15 passed`.
- Current temporal / valuation regression set: `31 passed`.

## Temporal Readiness

Status: `READY_WITH_CONFIGURATION_RULE`.

Resolved:

- Phase16-C semantic clock blockers for Pending lifecycle, Data Readiness, Market Refresh/Evidence, AI producers, PM producer, review-only producer, and Submit state timestamps are resolved by Phase16-D.
- Normal operation defaults are preserved: components still default to current UTC when `now` is omitted.

Known limitations:

- `run_daily_operation.py:94-97` still uses wall-clock UTC for `started_at` and `run_id`.
- `run_daily_operation.py:95` falls back to `date.today()` if `--business-date` is omitted.
- Report fallback behavior remains possible outside the normal CLI if report generation is called without explicit `business_date`.
- Execution timestamp semantics depend on the Historical Execution Provider writing point-in-time snapshot evidence.

Configuration rule:

- Historical runs must require explicit `--business-date` and `--evaluation-time`.
- Wall-clock run id/log/manifest timestamps should be classified as audit metadata unless deterministic run ids are later required.

## Backup / Reset / Restore

### Backup

Status: `IMPLEMENTATION_REQUIRED`.

Evidence:

- `src/ai_fund_lab_v2/runtime_v2/asset/initializer.py:27-43` contains `initialize_demo_operation_current_sot`, not a formal Phase16 backup.
- `src/ai_fund_lab_v2/runtime_v2/asset/initializer.py:17-24` only enumerates persistent ledger files.
- `src/ai_fund_lab_v2/runtime_v2/asset/initializer.py:123-129` copies only those persistent ledger files.

Missing:

- Full backup manifest with hashes for Current, Ledger, Pending, Runtime State, Approval, Execution evidence, idempotency state, run manifests, logs, reports, broker/historical broker state, and configuration.
- Backup validation and inventory.

### Reset

Status: `IMPLEMENTATION_REQUIRED`.

Evidence:

- Phase14e8 initializer writes a fixed demo Current and ledger seed at `src/ai_fund_lab_v2/runtime_v2/asset/initializer.py:45-115`.
- It must not be treated as Phase16 formal Reset.

Missing:

- Formal Reset CLI/procedure.
- Initial Current validation.
- Consistent initialization for Current, Ledger, Pending, Runtime State, Approval, Execution, Idempotency, and Historical Broker state.

### Restore

Status: `IMPLEMENTATION_REQUIRED`.

Evidence:

- No all-state restore CLI or all-or-nothing restore mechanism was found.

Missing:

- All-or-nothing restore with preflight validation.
- Post-restore consistency check across Current, Ledger, Pending, Runtime State, Approval, Execution, Idempotency, reports/manifests/logs, and Historical Broker state.

## Historical Broker Readiness

### Submit Boundary

Status: `IMPLEMENTATION_REQUIRED`.

Evidence:

- `src/ai_fund_lab_v2/runtime_v2/submit/pipeline.py:44-49` defines `RuntimeV2SubmitAdapter` with `preflight` and `submit`.
- `src/ai_fund_lab_v2/runtime_v2/submit/pipeline.py:128-140` accepts `adapter`.
- `src/ai_fund_lab_v2/runtime_v2/cli/run_daily_operation.py:676-687` calls Submit without an adapter injection option.
- `src/ai_fund_lab_v2/runtime_v2/submit/pipeline.py:152-153` blocks every mode other than `demo`.
- `src/ai_fund_lab_v2/runtime_v2/cli/run_daily_operation.py:986` allows CLI `--mode simulation`, but Submit still blocks it.

Minimum implementation:

- Add a CLI/config-selected Historical Submit Adapter path.
- Add a historical/simulation submit capability policy that does not weaken Submit Guard or Authority.
- Preserve existing Pending, Approval, Safety, Capital Policy, and Submit Guard checks.
- Guarantee no Tachibana Demo API write in Phase16 historical mode.

### Historical Execution Provider

Status: `IMPLEMENTATION_REQUIRED`.

Evidence:

- `src/ai_fund_lab_v2/runtime_v2/execution/readonly_pipeline.py:91-98` accepts `snapshot_provider`.
- `src/ai_fund_lab_v2/runtime_v2/cli/run_daily_operation.py:720-725` calls Execution without exposing `snapshot_provider`.
- `src/ai_fund_lab_v2/runtime_v2/execution/readonly_pipeline.py:108-113` blocks modes outside `demo` and `production`.
- `src/ai_fund_lab_v2/runtime_v2/execution/readonly_pipeline.py:128-136` writes/reads a broker readonly snapshot at the normal Execution boundary.

Minimum implementation:

- Add CLI/config-selected Historical Execution Provider.
- Add historical/simulation classification and evidence source naming.
- Produce snapshot payload compatible with existing broker-readonly normalization.
- Avoid reliance on Demo fallback as the source of truth.

### Execution Processor Compatibility

Status: `READY_WITH_KNOWN_LIMITATION`.

Evidence:

- `src/ai_fund_lab_v2/runtime_v2/execution/readonly_pipeline.py:147-162` normalizes snapshot payload into orders, executions, positions, and cash.
- `src/ai_fund_lab_v2/runtime_v2/execution/readonly_pipeline.py:187-242` appends normalized evidence to Ledger.
- `src/ai_fund_lab_v2/runtime_v2/execution/readonly_pipeline.py:255-289` projects runtime-owned fills to Current and applies Current to Runtime State.
- `src/ai_fund_lab_v2/runtime_v2/execution/readonly_pipeline.py:149-153` already has a simulation source classification when payload contains `simulation` or `acceptance_only`.

Limitation:

- Processor compatibility exists if the Historical Provider writes the expected snapshot shape. The provider and CLI injection do not yet exist.

## 5BD Minimal Fill Specification

This is a prerequisite specification for implementation, not an executed simulation.

| Item | 5BD Smoke minimum |
|---|---|
| order date | Runtime `business_date`; Submit requires Pending `target_session_date == business_date` via `src/ai_fund_lab_v2/runtime_v2/submit/pipeline.py:450-451`. |
| target session | Same date as authorized Pending target session for 5BD smoke. |
| fill date | Historical Execution Evidence date equals target session date when that session has an available quote; otherwise `missing_quote` review. |
| fill price source | Point-in-time OHLCV from `.runtime/operations/jquants/raw_normalized/jquants/equities_bars_daily/data.parquet`; source/date/hash must be recorded. |
| BUY | Fill only if quote exists, trading unit is satisfied, and simulated cash covers notional plus configured cost assumption. |
| SELL | Fill only if quote exists, trading unit is satisfied, and Current quantity covers requested quantity. |
| market order | Existing Runtime order condition contract allows market order with null limit price; Historical Broker must select a deterministic OHLC field. |
| trading unit | Must be enforced from broker capability or listed issue metadata; if unavailable, use explicit configured unit and record bias. |
| insufficient cash | Reject or REVIEW_REQUIRED without Ledger execution. |
| insufficient quantity | Reject or REVIEW_REQUIRED without Ledger execution. |
| missing quote | REVIEW_REQUIRED / no execution. |
| duplicate execution | Idempotency key must prevent duplicate execution evidence for the same submitted command/order id/date. |

Design decision still required before implementation:

- Choose the deterministic market-order fill price for 5BD (`Open`, `Close`, or conservative worst-side OHLC). The audit recommends a configured fill price rule with evidence hash rather than hard-coding.

## Normal Mainline Readiness

Status: `READY_WITH_KNOWN_LIMITATION`.

Evidence:

- Normal CLI jobs already cover Market Refresh, Data Readiness, AI producers, Planning, Pending, Submit, Execution, Ledger, Current projection/apply, Runtime State, Report, and Audit.
- `src/ai_fund_lab_v2/runtime_v2/simulation/harness.py` exists but is not required and should not be used as the Phase16 mainline substitute.
- The intended insertion points are Submit adapter injection and Execution snapshot provider injection.

Limitation:

- Until those two dependency injection points are CLI/config-selectable, the normal mainline cannot run Historical Simulation end-to-end.

## Public Output Optionality

Status: `READY_WITH_KNOWN_LIMITATION`.

Evidence:

- `src/ai_fund_lab_v2/runtime_v2/cli/run_daily_operation.py:1003-1005` has `--notification-mode` with default `payload-only`.
- `src/ai_fund_lab_v2/runtime_v2/cli/run_daily_operation.py:1043-1044` requires `payload-only` for daily scheduler rehearsal.
- `src/ai_fund_lab_v2/runtime_v2/cli/run_daily_operation.py:825-836` unconditionally generates Runtime/Public report artifacts and notification payload stage.

Classification:

- Notification delivery can be kept off.
- Public/Blog/LINE/Discord payload artifacts are unnecessary artifacts, not Runtime Core dependencies.
- This is not a 5BD blocker unless artifact generation cost becomes material.
- Long runs should add output optionality to reduce storage/noise.

## Point-In-Time / Look-Ahead Readiness

Overall status: `IMPLEMENTATION_REQUIRED`.

Existing guards:

- Candidate loader drops rows after `as_of_date` at `src/ai_fund_lab_v2/candidate_ai/data_loader.py:100-116`.
- Candidate validation counts future rows at `src/ai_fund_lab_v2/candidate_ai/data_loader.py:136-155`.
- Candidate leakage audit flags future/label/post-as-of leakage at `src/ai_fund_lab_v2/candidate_ai/leakage_audit.py:10-37`.

Readiness classification:

| Item | Classification | Evidence / gap |
|---|---|---|
| Market date cutoff | `REQUIRED_BEFORE_5BD` | Market data exists, but Historical Broker and run manifest must enforce cutoff per run. |
| Feature date cutoff | `READY_FOR_5BD` | Existing feature/date contracts and candidate loader cutoff exist; 5BD manifest still required. |
| Future label禁止 | `READY_FOR_5BD` | Candidate leakage audit forbids future/label columns. |
| Candidate input cutoff | `READY_FOR_5BD` | Candidate loader drops rows after `as_of_date`. |
| Opportunity input cutoff | `REQUIRED_BEFORE_5BD` | Need end-to-end manifest proving no future opportunity inputs in Historical run. |
| PM input cutoff | `REQUIRED_BEFORE_5BD` | Need manifest proving PM input date and Current date are point-in-time. |
| Listed status | `KNOWN_BIAS_ACCEPTED_FOR_SMOKE` | Listed issues data exists only for 2026-07-06 to 2026-07-10 in current raw data. |
| Universe membership | `KNOWN_BIAS_ACCEPTED_FOR_SMOKE` | Universe history is not fully point-in-time for requested 2021 start. |
| Financial disclosure availability | `REQUIRED_BEFORE_1Y` | Not required to unblock 5BD smoke if bias is documented; required before long performance evaluation. |
| Corporate actions | `REQUIRED_BEFORE_20BD` | Adjusted prices exist in raw quotes, but corporate-action availability/audit is not formalized. |
| Fill price separation | `REQUIRED_BEFORE_5BD` | Historical Broker must use only quote data available at fill date. |
| Backtest result contamination | `READY_FOR_5BD` | Contract prohibits feedback; needs freeze manifest enforcement before run. |

## Model / Config Freeze Readiness

Status: `IMPLEMENTATION_REQUIRED`.

Evidence:

- Runtime CLI accepts model/config paths such as candidate model, opportunity model, opportunity metrics, feature date, and capital deployment policy.
- Candidate and Opportunity model artifacts exist in `.runtime/candidate_ai` and `reports/opportunity_ai` / `models/opportunity_ai`.
- `docs/02_architecture/historical_runtime_test_contract.md:139-165` prohibits AI retraining and requires model freeze manifest fields.
- Normal Runtime CLI does not call training scripts during the mainline jobs inspected.

Missing freeze manifest:

- Git commit.
- Runtime version.
- Candidate model path/hash/version/training period.
- Opportunity model path/hash/version/training period.
- PM model/config path/hash if applicable.
- Feature schema.
- Policy, Safety, Capital Allocation config.
- Calendar and market data hashes.
- Historical Broker config.
- Initial Current hash.

## Historical Data Period

Requested start date: `2021-07-01`.

Read-only data availability findings:

| Dataset | Min date | Max date | Notes |
|---|---:|---:|---|
| Raw trading calendar `.runtime/operations/jquants/raw/jquants/trading_calendar/data.parquet` | 2026-02-16 | 2026-07-10 | 145 rows. |
| Raw listed issues `.runtime/operations/jquants/raw/jquants/listed_issues/data.parquet` | 2026-07-06 | 2026-07-10 | 4 dates, 4,439 unique codes. |
| Raw daily bars `.runtime/operations/jquants/raw/jquants/equities_bars_daily/data.parquet` | 2026-02-16 | 2026-07-10 | 99 trading dates, 4,523 unique codes. |
| Normalized daily bars `.runtime/operations/jquants/raw_normalized/jquants/equities_bars_daily/data.parquet` | 2026-02-16 | 2026-07-10 | 99 trading dates, 4,373 unique codes. |
| Candidate long-history dataset `.runtime/candidate_ai/datasets/phase4be_long_history_dataset_2021-06-14_2026-05-15.parquet` | 2021-06-14 | 2026-05-15 | 1,202 target dates, 4,780 unique codes; derived dataset, not sufficient as raw market/fill evidence. |
| Runtime feature artifacts `.runtime/operations/feature_artifacts/<date>/` | 2026-07-06 | 2026-07-10 | Present for 2026-07-06, 07, 08, 10; 2026-07-09 feature artifact directory not present in the inspected listing. |

Result:

- `effective_start_date_candidate`: `2026-02-16` for raw/normalized daily bars; `2021-06-14` only for candidate derived dataset.
- `latest_available_date`: `2026-07-10`.
- `estimated_business_day_count`: 99 raw daily-bar dates from 2026-02-16 to 2026-07-10.
- `blocking_data_gaps`: Requested 2021-07-01 raw market/fill/calendar/listed-state evidence is not present in the current raw Runtime data root.
- `known_biases`: Listed status and universe membership are incomplete for long historical replay; candidate derived dataset cannot replace raw fill-price evidence.

5BD data implication:

- A 5BD smoke is plausible only inside the available 2026 raw quote window after Backup/Reset/Restore and Historical Broker prerequisites are implemented.
- A 2021 replay is not data-ready from the inspected raw Runtime data root.

## 5BD Entry Gate

Status: `IMPLEMENTATION_REQUIRED`.

| Gate | Status |
|---|---|
| Temporal semantic blockers resolved | `READY_WITH_CONFIGURATION_RULE` |
| Backup mechanism ready | `IMPLEMENTATION_REQUIRED` |
| Reset mechanism ready | `IMPLEMENTATION_REQUIRED` |
| Restore mechanism ready | `IMPLEMENTATION_REQUIRED` |
| Historical Broker ready | `IMPLEMENTATION_REQUIRED` |
| Historical execution evidence ready | `IMPLEMENTATION_REQUIRED` |
| Normal mainline connection ready | `READY_WITH_KNOWN_LIMITATION` |
| Initial Current validation ready | `IMPLEMENTATION_REQUIRED` |
| No broker write guaranteed | `IMPLEMENTATION_REQUIRED` |
| No notification delivery guaranteed | `READY` |
| Required look-ahead guards ready | `IMPLEMENTATION_REQUIRED` |
| Model/config freeze ready | `IMPLEMENTATION_REQUIRED` |

5BD simulation must not start until every `IMPLEMENTATION_REQUIRED` gate above is closed.

## Judgment Matrix

| Target | Judgment | Reason |
|---|---|---|
| Temporal Clock | `READY_WITH_KNOWN_LIMITATION` | Semantic blockers fixed; historical runs must require explicit business/evaluation time. |
| Backup | `IMPLEMENTATION_REQUIRED` | Only partial ledger/current backups exist. |
| Reset | `IMPLEMENTATION_REQUIRED` | Phase14e8 initializer is not formal Phase16 reset. |
| Restore | `IMPLEMENTATION_REQUIRED` | No all-state restore found. |
| Historical Submit Adapter | `IMPLEMENTATION_REQUIRED` | Protocol exists; CLI/config injection and mode/capability policy missing. |
| Historical Execution Provider | `IMPLEMENTATION_REQUIRED` | Provider seam exists; CLI/config injection and simulation mode policy missing. |
| Execution Processor Compatibility | `READY_WITH_KNOWN_LIMITATION` | Existing processor can normalize compatible evidence and write Ledger/Current. |
| Normal Mainline | `READY_WITH_KNOWN_LIMITATION` | Mainline exists; broker dependency injection missing. |
| Public Output Optionality | `READY_WITH_KNOWN_LIMITATION` | Delivery is off; unnecessary artifacts still generated. |
| Point-in-time Guard | `IMPLEMENTATION_REQUIRED` | Candidate guards exist; end-to-end run/fill manifest missing. |
| Model Freeze | `IMPLEMENTATION_REQUIRED` | No single freeze manifest/hash gate. |
| Historical Period | `READY_WITH_KNOWN_LIMITATION` | 2026 5BD window likely available; requested 2021 raw evidence not available. |
| 5BD Readiness | `IMPLEMENTATION_REQUIRED` | Backup/Reset/Restore, Historical Broker, point-in-time, and freeze blockers remain. |

## Remaining Implementation

Minimum implementation order:

1. Full Runtime Backup manifest and validator.
2. Formal Runtime Reset for isolated Historical runtime roots, with Initial Current validation.
3. All-or-nothing Restore.
4. Historical Submit Adapter and CLI/config injection, preserving Submit Guard and no real Broker write.
5. Historical Execution Provider and CLI/config injection, producing compatible snapshot evidence.
6. Historical Broker fill-price/idempotency/cash/quantity rules.
7. Point-in-time run manifest for market, feature, opportunity, PM, fill price, and Current inputs.
8. Model/config freeze manifest with hashes.
9. Optional public/blog/payload output switches for long runs.

## Design Decisions Required

- Fill price rule for market orders in 5BD smoke: open, close, or conservative side-specific OHLC.
- Historical mode naming and policy: use existing `simulation` mode or introduce a more explicit historical broker environment while preserving Runtime authority.
- Whether listed/universe bias is acceptable for the first 5BD smoke date range or must be blocked until point-in-time listed/universe history is complete.

## Final Judgment

`PHASE16_E_PREREQUISITES_READY_FOR_IMPLEMENTATION`

The remaining work is sufficiently scoped for the next prefix. Historical Simulation and Reset must still not be started.

Recommended next prefix:

`Phase16-F`

Recommended Phase16-F scope:

- Implement the missing prerequisites only, starting with Backup/Reset/Restore and then Historical Submit/Execution injection.
