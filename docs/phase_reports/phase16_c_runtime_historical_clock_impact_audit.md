# Phase16-C Runtime v2 Historical Clock Impact Audit

Prefix: `Phase16-C`  
Work name: `Runtime v2 Historical Clock Impact Audit`  
Audit date: `2026-07-13`  
Primary judgment: `PHASE16_C_RUNTIME_TEMPORAL_BUG_FIX_REQUIRED`  
Secondary findings: `CLI_PROPAGATION_FIX_REQUIRED`

## Executive Summary

Runtime v2 already has the right conceptual injection points: `--business-date` and `--evaluation-time`. Several freshness and safety components also accept `now` and behave correctly when `evaluation_time` reaches them.

However, the current mainline still has real-time dependencies that affect Runtime semantic state, not only logs. The clearest blockers are:

- Pending lifecycle accepts `now`, but the CLI does not pass `evaluation_time`.
- Submit Pipeline does not accept `now`; it writes real UTC into Pending `updated_at` and Ledger order `created_at`.
- Data Readiness, Market Evidence, Candidate/Opportunity BUY producer, Position Management producer, and review-only producer accept or use `now`, but normal CLI does not consistently pass `evaluation_time`.
- Physical CLI metadata such as run id, manifest start/finish, stage timestamps, and logs are expected nondeterministic metadata and are not by themselves historical blockers.

No implementation, Runtime change, CLI change, reset, test run, AI run, historical simulation, or replay was performed.

## Audit Scope

Required documents reviewed:

- `docs/phase_reports/phase16_a_historical_runtime_v2_performance_test_design.md`
- `docs/02_architecture/historical_runtime_test_contract.md`
- `docs/phase_reports/phase16_b_prerequisite_audit.md`
- `docs/02_architecture/runtime_architecture_v2.md`
- `docs/02_architecture/runtime_temporal_freshness_contract.md`
- `docs/02_architecture/runtime_auto_trade_authority_contract.md`
- `docs/02_architecture/runtime_submit_order_condition_authority_contract.md`
- `docs/phase_reports/phase15_ca_runtime_v2_completion_and_final_review.md`

Search scope:

- `src/ai_fund_lab_v2/runtime_v2/`
- `src/ai_fund_lab_v2/candidate_ai/`
- `src/ai_fund_lab_v2/opportunity_ai/`
- `src/ai_fund_lab_v2/position_management_ai/`
- `src/ai_fund_lab_v2/paper_trading/`
- `src/ai_fund_lab_v2/order_manager/`

Direct current-time dependency count:

- Runtime v2 direct matches for `date.today`, `datetime.now`, `datetime.utcnow`, `time.time`, `_utc_now`: `38`
- Scoped repository direct matches across the required directories: `85`

The full text search also found many generated field names such as `created_at`, `generated_at`, `business_date`, and `expires_at`; the material findings below focus on the normal Runtime v2 mainline.

## Datetime Dependency Inventory

| ID | Location | Function / class | Source | Explicit argument | Fallback | Caller / consumer | Affected artifact / state | Classification | Impact |
|---|---|---|---|---|---|---|---|---|---|
| D01 | `runtime_v2/cli/run_daily_operation.py:94-97` | `main` | `_utc_now()`, `date.today()` | `--business-date` only | yes | CLI | run id, log path, manifest | A / B | `date.today()` fallback is `CURRENT_TIME_FALLBACK_RISK`; run id is metadata. |
| D02 | `runtime_v2/cli/run_daily_operation.py:923-924` | `_build_manifest` | `_utc_now()` | no | yes | CLI | manifest `finished_at` | A | `EXPECTED_NONDETERMINISTIC_METADATA`. |
| D03 | `runtime_v2/cli/run_daily_operation.py:1327-1333` | `_stage` | `_utc_now()` | no | yes | CLI | stage `created_at` | A | `EXPECTED_NONDETERMINISTIC_METADATA`. |
| D04 | `runtime_v2/cli/run_daily_operation.py:1352-1355` | `_append_log` | `_utc_now()` | no | yes | CLI | log timestamp | A | `NO_HISTORICAL_IMPACT` for investment semantics. |
| D05 | `runtime_v2/pending/lifecycle_runner.py:30-42` | `run_pending_lifecycle_review` | `now or datetime.now(timezone.utc)` | `now` | yes | CLI pending lifecycle | `transitioned_at` | C / D | `HISTORICAL_STATE_TRANSITION_BLOCKER` when CLI omits `now`. |
| D06 | `runtime_v2/pending/lifecycle_runner.py:351-357` | `_stale_reasons` | `transitioned_at` | indirect | yes through D05 | Pending lifecycle | `approval_expired`, terminal/review transitions | C / D | 2021 pending can expire under 2026 wall clock. |
| D07 | `runtime_v2/submit/pipeline.py:369-382` | `run_submit_pipeline` | `_utc_now()` | no | yes | CLI submit | Pending `updated_at`, consumed state | D | `HISTORICAL_STATE_TRANSITION_BLOCKER`. |
| D08 | `runtime_v2/submit/pipeline.py:563-570` | `_ledger_order_record` | `_utc_now()` | no | yes | Submit | Ledger order `created_at` / `recorded_at` | D / physical metadata | `CURRENT_TIME_FALLBACK_RISK`; ledger semantic record includes real timestamp. |
| D09 | `runtime_v2/safety/evaluation.py:93-113` | `run_runtime_safety_evaluation` | `now or datetime.now` | `now` | yes | CLI safety_evaluation | Safety report, `expires_at` | C | `CONTROLLED_BY_EXPLICIT_ARGUMENT` if CLI passes `evaluation_time`. |
| D10 | `runtime_v2/safety/evaluation.py:624-638` | `_set_snapshot_age` | `now` | yes | no inside call | Safety freshness | Broker snapshot freshness | C | `CONTROLLED_BY_EXPLICIT_ARGUMENT`. |
| D11 | `runtime_v2/safety/producer.py:45-64` | `produce_runtime_safety_decision` | `now or datetime.now` | `now` | yes | CLI safety_refresh | Runtime Safety Decision | C | `CONTROLLED_BY_EXPLICIT_ARGUMENT` if CLI passes `evaluation_time`. |
| D12 | `runtime_v2/data_readiness.py:160-177` | `evaluate_runtime_data_readiness` | `now or datetime.now` | `now` | yes | CLI data readiness | readiness artifact `generated_at` | A / C | CLI currently does not pass `now`; mostly metadata, but downstream review-only human review uses `now`. |
| D13 | `runtime_v2/data_readiness.py:977-988` | `_safety_readiness_payload` | `decision.expires_at` date part | no `now` | n/a | Data Readiness | safety expiry status | C | Date-only comparison to `business_date`; not 2026 wall-clock dependent but less precise than evaluation time. |
| D14 | `runtime_v2/data_readiness.py:1045-1050` | `_review_only_morning_payload` | `now` to human review validation | yes | currently omitted by CLI | Data Readiness | high-risk review validation | C | `CURRENT_TIME_FALLBACK_RISK` through missing CLI propagation. |
| D15 | `runtime_v2/human_review.py:138-144` | `validate_human_review_artifact` | `now or datetime.now` | `now` | yes | Review-only / Data Readiness | human review expiration | C | Controlled only if caller passes `now`. |
| D16 | `runtime_v2/broker_readonly/refresh.py:153-171` | broker readonly refresh | `evaluation_time or datetime.now` | `evaluation_time` | yes | CLI broker_readonly_refresh | broker freshness | C | `CONTROLLED_BY_EXPLICIT_ARGUMENT`. |
| D17 | `runtime_v2/market_refresh/evidence.py:90-103` | `produce_market_quote_evidence` | `now or datetime.now` | `now` | yes | Market refresh pipeline | market evidence freshness | C | Pipeline does not pass `now`; `CURRENT_TIME_FALLBACK_RISK`. |
| D18 | `runtime_v2/market_refresh/pipeline.py:102-109` | `run_runtime_v2_market_refresh_pipeline` | no `now` pass | none | indirect | CLI market_refresh | market evidence | C | CLI cannot control market evidence evaluation time. |
| D19 | `runtime_v2/buy_ai/producer.py:102-107` | `produce_buy_ai_decisions` | `now or datetime.now` | `now` | yes | CLI morning | BUY AI artifacts, runtime id | A / B | CLI omits `now`; likely metadata/id, but artifact ids can differ. |
| D20 | `runtime_v2/position_management/producer.py:104-112` | PM producer | `now or datetime.now` | `now` | yes | CLI sell_planning | PM artifacts, runtime id | A / B | CLI omits `now`; likely metadata/id. |
| D21 | `runtime_v2/position_management/producer.py:489-499` | Current temporal check | business date/current fields | explicit `business_date` | no real-time fallback | PM AI | current freshness | B / D | Controlled by business date and Current fields. |
| D22 | `runtime_v2/review_only/sell_hold_morning.py:65-71` | review-only producer | `now or datetime.now` | `now` | yes | CLI review-only | review-only artifact | A / C | CLI currently omits `now`; may affect linked human-review validation through downstream calls. |
| D23 | `runtime_v2/runtime_state/contract.py:63-68` | `produce_runtime_operation_state` | `now or datetime.now` | `now` | yes | CLI runtime state | Runtime State `generated_at`, `updated_at` | D / metadata | CLI passes `evaluation_time`; controlled. |
| D24 | `runtime_v2/current_state/temporal.py:224-278` | Current temporal migration | `now or datetime.now` | `now` | yes | CLI migration | migration artifact, optional Current write | D | CLI passes `evaluation_time`; controlled. |
| D25 | `runtime_v2/current_state/temporal.py:409-414` | `_atomic_write_current` | `now or datetime.now` | `now` | yes | migration apply | backup file name | A | Controlled if CLI passes `evaluation_time`; backup path metadata. |
| D26 | `runtime_v2/current_state/valuation.py:211-263` | valuation refresh | `_iso(now)` | `now` | yes | CLI valuation | valuation artifact, optional Current write | D | CLI passes `evaluation_time`; controlled. |
| D27 | `runtime_v2/current_state/valuation.py:419-420` | valuation history digest | payload digest | indirect | n/a | valuation | history path | D | If generated_at changes, history digest changes; controlled only when `now` is passed. |
| D28 | `runtime_v2/report/markdown_writer.py:102-108` | report context load | `date.today()` fallback | `business_date` | yes | CLI report | report date | E | CLI passes `business_date`; standalone report has fallback risk. |
| D29 | `runtime_v2/temporal/resolver.py:25-39` | `resolve_temporal_context` | `now or datetime.now(Asia/Tokyo)` | `now` | yes | market/safety/broker freshness | calendar_date, publication window context | B / C | Safe only when callers pass `now`. |

## Business Date Propagation

`--business-date` is parsed at `runtime_v2/cli/run_daily_operation.py:993`. The CLI falls back to `date.today()` at `runtime_v2/cli/run_daily_operation.py:95` if it is omitted.

Propagation status:

| Component | Status | Evidence |
|---|---|---|
| Market Refresh | `RECEIVES_BUSINESS_DATE` | `run_daily_operation.py:737-742`, `market_refresh/pipeline.py:75-109` |
| Feature Refresh | `RECEIVES_BUSINESS_DATE` via market refresh feature date contract | `market_refresh/pipeline.py:92-109` |
| Candidate AI | `RECEIVES_BUSINESS_DATE` | `run_daily_operation.py:460-490`, `buy_ai/producer.py:99-114` |
| Opportunity AI | `RECEIVES_BUSINESS_DATE` through BUY AI producer | `buy_ai/producer.py:112-114` |
| Position Management AI | `RECEIVES_BUSINESS_DATE` | `run_daily_operation.py:543-551`, `position_management/producer.py:99-113` |
| Policy | `RECEIVES_BUSINESS_DATE` indirectly through job/pending policy context | CLI policy loading and pending promotion/apply calls |
| Safety | `RECEIVES_BUSINESS_DATE` | `run_daily_operation.py:177-213` |
| Planning | `RECEIVES_BUSINESS_DATE` | `run_daily_operation.py:484-490`, `543-551` |
| Approval | `RECEIVES_BUSINESS_DATE` through promotion/apply review | `run_daily_operation.py:606-647` |
| Pending lifecycle | `RECEIVES_BUSINESS_DATE` | `run_daily_operation.py:323-329` |
| Submit Guard | `RECEIVES_BUSINESS_DATE` | `run_daily_operation.py:672-681` |
| Execution | `RECEIVES_BUSINESS_DATE` | `run_daily_operation.py:714-719` |
| Current Projection | `RECEIVES_BUSINESS_DATE` | `execution/readonly_pipeline.py:255-289` |
| Current Apply | `RECEIVES_BUSINESS_DATE` | `current_state/apply.py:72-104` |
| Runtime State | `RECEIVES_BUSINESS_DATE` | `run_daily_operation.py:295-303` |
| Runtime Report | `RECEIVES_BUSINESS_DATE` | `run_daily_operation.py:818-824` |
| Audit | `RECEIVES_BUSINESS_DATE` through report context | `report/markdown_writer.py:102-108` |

Conclusion: business-date propagation is broadly present, but historical runs must always pass it explicitly. The fallback to today is a configuration risk.

## Evaluation Time Propagation

`--evaluation-time` is parsed at `runtime_v2/cli/run_daily_operation.py:1252-1258`.

| Component | Status | Evidence |
|---|---|---|
| Safety Evaluation | `RECEIVES_EVALUATION_TIME`, `USES_EXPLICIT_TIME` | `run_daily_operation.py:177-184`, `safety/evaluation.py:93-113` |
| Safety Refresh | `RECEIVES_EVALUATION_TIME`, `USES_EXPLICIT_TIME` | `run_daily_operation.py:206-213`, `safety/producer.py:45-64` |
| Runtime State | `RECEIVES_EVALUATION_TIME`, `USES_EXPLICIT_TIME` | `run_daily_operation.py:295-303`, `runtime_state/contract.py:63` |
| Current Temporal Migration | `RECEIVES_EVALUATION_TIME`, `USES_EXPLICIT_TIME` | `run_daily_operation.py:347-351`, `current_state/temporal.py:220-278` |
| Current Valuation | `RECEIVES_EVALUATION_TIME`, `USES_EXPLICIT_TIME` | `run_daily_operation.py:373-377`, `current_state/valuation.py:211-263` |
| Broker ReadOnly Refresh | `RECEIVES_EVALUATION_TIME`, `USES_EXPLICIT_TIME` | `run_daily_operation.py:399-403`, `broker_readonly/refresh.py:153-171` |
| Pending Promotion Review | `RECEIVES_EVALUATION_TIME`, `USES_EXPLICIT_TIME` | `run_daily_operation.py:606-613` |
| Authoritative Pending Apply Review | `RECEIVES_EVALUATION_TIME`, `USES_EXPLICIT_TIME` | `run_daily_operation.py:639-647` |
| Pending Lifecycle | `RECEIVES_BUSINESS_DATE`, `USES_REAL_TIME_FALLBACK` | `run_daily_operation.py:323-329`, `pending/lifecycle_runner.py:30-42` |
| Data Readiness | `USES_REAL_TIME_FALLBACK` | `run_daily_operation.py:424-440` omits `now`; `data_readiness.py:160-177` accepts `now` |
| Market Evidence | `USES_REAL_TIME_FALLBACK` | `market_refresh/pipeline.py:102-109` omits `now`; `market_refresh/evidence.py:90-103` accepts `now` |
| Candidate/Opportunity BUY Producer | `USES_REAL_TIME_FALLBACK` | `run_daily_operation.py:460-470` omits `now`; `buy_ai/producer.py:102-107` accepts `now` |
| Position Management Producer | `USES_REAL_TIME_FALLBACK` | CLI omits `now`; `position_management/producer.py:104-112` accepts `now` |
| Sell/Hold Review-only Producer | `USES_REAL_TIME_FALLBACK` | `review_only/sell_hold_morning.py:65-71` accepts `now`; CLI call needs propagation audit/fix |
| Submit Pipeline | `USES_REAL_TIME_FALLBACK` | `submit/pipeline.py:369-382`, `563-570`, `1175-1176`; no `now` parameter |
| Execution ReadOnly Pipeline | `UNKNOWN` for historical broker boundary | It uses broker snapshot timestamps; historical broker replacement is separate Phase16 prerequisite. |
| Runtime Report | `TIME_NOT_REQUIRED` when CLI passes business date | `run_daily_operation.py:818-824`, `report/markdown_writer.py:102-108` |

## Pending Lifecycle Impact

Evidence:

- `run_pending_lifecycle_review` accepts `now` at `pending/lifecycle_runner.py:30-37`.
- It derives `transitioned_at` from `now or datetime.now(timezone.utc)` at `pending/lifecycle_runner.py:42`.
- The normal CLI call omits `now=evaluation_time` at `run_daily_operation.py:323-329`.
- `_stale_reasons` marks `approval_expired` when `approval_expires_at <= transitioned_at` at `pending/lifecycle_runner.py:355-357`.
- Transition writes update Pending `updated_at` and history `transitioned_at` at `pending/lifecycle_runner.py:215-222` and `240-275`.

Impact:

If Phase16 simulates a 2021 pending plan while the actual wall clock is 2026, CLI-driven pending lifecycle can compare a 2021 approval expiration against a 2026 `transitioned_at` and mark it expired/review-required. This is a historical state-transition blocker.

Target session check:

- `target_session_date < business_date` is based on explicit `business_date` at `pending/lifecycle_runner.py:351-354`; this part is controlled.

Approval expiration:

- Expiration is based on `transitioned_at`; because the CLI does not pass `evaluation_time`, this is not controlled.

Consume / expire / review:

- The lifecycle can write REVIEW_REQUIRED/EXPIRED/CANCELLED history and mutate Pending based on `transitioned_at`. Therefore this is Runtime semantic state, not metadata only.

Isolated test design, not executed:

1. Create a temp runtime root with a pending plan: `business_date=2021-07-05`, `target_session_date=2021-07-05`, `approval_expires_at=2021-07-05T15:00:00+09:00`, state `APPROVED`.
2. Call `run_pending_lifecycle_review(..., business_date="2021-07-05", now=datetime(2021, 7, 5, 9, 0, tzinfo=UTC))`; expected no expiry from approval time.
3. Call the same function without `now`; expected expiry under current 2026 wall clock.
4. Verify the only difference is lifecycle state/history caused by `transitioned_at`.

## Safety / Freshness Impact

Safety Evaluation and Safety Refresh are mostly controlled when `evaluation_time` is passed:

- Safety evaluation uses `now_dt = _aware(now or datetime.now(timezone.utc))` at `safety/evaluation.py:97`.
- Safety expiration is generated as `now_dt + 4 hours` at `safety/evaluation.py:113`.
- Broker snapshot freshness receives `now` at `safety/evaluation.py:624-638`.
- Safety refresh uses `now` at `safety/producer.py:53-64`.

Gaps:

- Data Readiness accepts `now` but CLI omits it at `run_daily_operation.py:424-440`; generated metadata and human-review freshness can use real time.
- `_safety_readiness_payload` compares `date_part(expires_at) < business_date` at `data_readiness.py:986-988`; this avoids 2026 wall-clock expiry, but is only date-level precision.
- Market Evidence freshness uses `resolve_temporal_context(... now=now_dt)` at `market_refresh/evidence.py:90-103`, but the market refresh pipeline does not pass `now`.
- Temporal context falls back to JST real time at `temporal/resolver.py:25-39` when `now` is missing.

Status-specific observations:

- `VALID_CARRYOVER`, `DATA_NOT_YET_AVAILABLE`, and `STALE` can be impacted by publication-window logic whenever `resolve_temporal_context` receives wall-clock `now`.
- `EXPIRED` for Safety in Data Readiness is currently date-part based against `business_date`, not real wall-clock.
- `REVIEW_REQUIRED`/`HALT` from Safety Evaluation are controlled if the CLI passes `evaluation_time`.
- Human review expiration is real-time dependent unless `now` is passed, via `human_review.py:138-144`.

## Current / Ledger / Hash Impact

Semantic hash separation:

- `current_state/authority.py:11-28` excludes only authority/pointer/reference/path fields from Current hash.
- It does not exclude generic physical metadata such as `created_at`, `updated_at`, `generated_at`, or valuation generated fields.

Controlled Current paths:

- Runtime-owned fill projection writes Current `created_at` and `updated_at` as `business_date`, not wall-clock, at `asset/runtime_owned_fill_projection.py:141-148` and `294-304`.
- Current Apply derives `runtime_state_version` only from `business_date`, `mode`, `current_hash`, and execution refs at `current_state/apply.py:123-139`.
- Current Apply writes Runtime State `updated_at` as `business_date` at `current_state/apply.py:72-104`.

Potential reproducibility risks:

- Current temporal migration and valuation refresh are controlled if `now` is passed. If called without `now`, generated fields and valuation history digest can differ (`current_state/valuation.py:257-263`, `419-420`, `512-513`).
- Submit Ledger order records use real UTC `created_at` at `submit/pipeline.py:563-570`; `ledger/writer.py` mirrors `recorded_at` from `created_at`. This is a Ledger semantic artifact field.
- Pending state updates in Submit use real UTC `updated_at` at `submit/pipeline.py:369-382`.

Assessment:

- PnL, cash, position quantity, average price, and Runtime State version appear protected from wall-clock time in Current Apply and runtime-owned projection.
- Ledger order `created_at` and Pending `updated_at` are not protected and can make state artifacts differ for identical historical inputs.
- Current semantic hash can change if a Current-producing path writes wall-clock metadata into the Current payload before hashing.

## Report Impact

Evidence:

- Runtime report generation passes `business_date` from the CLI at `run_daily_operation.py:818-824`.
- `markdown_writer.py:102-108` only falls back to `date.today()` if no report business date can be resolved.
- Public JSON summary includes `business_date`, current run, ledger history, audit, and notification payload at `markdown_writer.py:1486-1510`.

Impact:

- Normal CLI report date is controlled by `business_date`.
- Standalone report generation can drift to wall-clock date if called without `business_date`.
- Report fallback does not appear to feed Runtime State, Ledger, Current, PnL, or next-stage inputs.
- Report/Public/Notification generation may block the mainline if redaction fails, but date fallback itself is output-only under the normal CLI path.

## Historical Simulation Blockers

1. Pending lifecycle `evaluation_time` not propagated from CLI to `run_pending_lifecycle_review`.
2. Submit Pipeline lacks a `now`/evaluation-time parameter and writes wall-clock values to Pending and Ledger.
3. Market Evidence / Temporal Context can use real JST time through missing `now` propagation.
4. Data Readiness can use real time where `now` is omitted, especially for generated metadata and human-review expiration.
5. BUY/Opportunity and PM producers use wall-clock artifact ids/generated_at because CLI does not pass `now`.

## No-impact Metadata Dependencies

The following are acceptable nondeterministic metadata if they remain outside semantic state/hash/PnL:

- CLI run id timestamp.
- CLI manifest `started_at` / `finished_at`.
- Stage `created_at`.
- Log timestamps.
- Report physical generated path timestamps when not used as Runtime inputs.

## Unknowns

- Execution ReadOnly historical behavior cannot be fully classified until the Historical Simulated Broker boundary is specified.
- It is not proven whether all BUY/PM generated timestamps are excluded from downstream semantic hashes. They should be treated as `CURRENT_TIME_FALLBACK_RISK` until isolated evidence confirms metadata-only behavior.
- Data Readiness publication-window behavior under 2021 evaluation time needs isolated evidence once `now` propagation exists.

## Implementation Necessity Judgment

Option selected: `RUNTIME_TEMPORAL_BUG_FIX_REQUIRED`

Reason:

Runtime v2 does not merely write real time to logs. Submit Pipeline and Pending lifecycle can use real wall-clock time in state transitions or state artifacts. That violates the Runtime Temporal/Freshness Contract for historical operation and can change historical simulation outcomes.

Secondary option: `CLI_PROPAGATION_FIX_REQUIRED`

Reason:

Several components already accept `now`, so part of the fix is simply propagating `evaluation_time` from the CLI.

## Minimal Change Options

### Option A: CLI propagation only

- Change targets: CLI calls for Pending lifecycle, Data Readiness, Market Refresh/Evidence, BUY AI, PM AI, review-only.
- Runtime Contract impact: aligns existing `evaluation_time` with components that already accept `now`.
- Normal operation impact: none if `evaluation_time` remains optional and defaults continue unchanged.
- Historical effect: fixes many fallback risks.
- Regression risk: low.
- Required tests: unit tests proving CLI passes `evaluation_time` to each existing `now` argument.
- Limitation: does not fix Submit Pipeline wall-clock state writes.

### Option B: Add optional `now` to Submit Pipeline

- Change targets: `run_submit_pipeline`, `_ledger_order_record`, Pending state update timestamps.
- Runtime Contract impact: makes Submit state mutation use explicit evaluation time when provided.
- Normal operation impact: none if default remains `datetime.now(timezone.utc)`.
- Historical effect: fixes Submit Pending/Ledger wall-clock contamination.
- Regression risk: medium because Submit is authority-sensitive.
- Required tests: Submit Pipeline with fixed `now` produces deterministic Pending `updated_at` and Ledger `created_at`; default path remains unchanged.
- Alternative: wrap Submit adapter only. Not sufficient because the timestamps are inside Runtime Submit.

### Option C: Historical Clock adapter/provider

- Change targets: shared Runtime clock provider or dependency injection layer.
- Runtime Contract impact: broad.
- Normal operation impact: larger surface area.
- Historical effect: comprehensive.
- Regression risk: medium-high.
- Required tests: broad mainline regression and deterministic artifact tests.
- Recommendation: defer unless Option A+B still leaves uncontrolled semantic time.

## Regression Risks

- Submit idempotency and Pending consumption must not regress.
- Ledger dedup keys must remain stable.
- Safety expiration must remain valid for normal operation.
- Data Readiness must not accidentally treat valid production wall-clock as historical.
- Current hash should not start excluding semantic temporal fields such as `valuation_as_of` or `position_state_as_of`.
- Do not introduce Phase16-only state machine or historical-only Runtime path.

## Recommended Next Step

Proceed to a narrowly scoped Phase16-D or Phase16-C2 implementation pass:

1. Propagate `evaluation_time` through existing `now` parameters in the normal CLI.
2. Add optional `now` to Submit Pipeline and use it for Pending `updated_at` and Ledger order `created_at`.
3. Add isolated tests for Pending lifecycle expiration and Submit deterministic timestamps.
4. Re-run this audit after implementation before Reset or Historical Runtime Test.

Do not start Reset or Historical Runtime Simulation until these clock blockers pass.
