# Phase17-B Historical Runtime Readiness Revalidation and 5BD Smoke Test Preparation

## Final Judgment

Final judgment: `PHASE17_B_IMPLEMENTATION_REQUIRED`

Recommended next prefix: `Phase17-B1`

Recommended next work:

```text
Historical Runtime Readiness Gap Implementation
```

Phase17-B was performed as a read-only readiness audit and 5BD smoke preparation review. The 5BD Historical Runtime Test was not executed.

The Operational Data Foundation remains complete, but that does not yet mean Historical Runtime 5BD execution is ready. The current repository has accepted Registry-backed artifacts and a working Resolver, but several Historical Runtime execution-specific gates are not ready:

- no formal all-state Trading State Backup / Reset / Restore implementation;
- normal CLI does not currently expose a Historical Simulated Broker boundary for submit/execution;
- normal CLI validation still rejects most `--mode simulation` jobs;
- Runtime market refresh / feature generation is still wired to operational recent data paths, not the full canonical historical data chain;
- persisted historical Trading Calendar and Listed Issues remain insufficient for 2021+ historical replay;
- 5BD candidate window has only four existing feature artifact dates;
- PM Runtime Adapter accepted snapshot differs from current source actually executed by Runtime.

## Reviewed Materials

Required materials reviewed:

- `docs/phase_reports/phase17_a_integrated_system_test_and_production_readiness_strategy.md`
- `reports/phase_reports/phase17_a_integrated_system_test_and_production_readiness_strategy.json`
- `docs/phase_reports/phase16_final_summary_and_phase17_handoff.md`
- `reports/phase_reports/phase16_final_summary_and_phase17_handoff.json`
- `docs/phase_reports/phase16_ax_operational_data_foundation_final_conformance_and_ai_integrity_audit.md`
- `reports/phase_reports/phase16_ax_operational_data_foundation_final_conformance_and_ai_integrity_audit.json`
- `docs/phase_reports/phase16_b_prerequisite_audit.md`
- `reports/phase_reports/phase16_b_prerequisite_audit.json`
- `docs/phase_reports/phase16_g_canonical_historical_data_source_audit.md`
- `reports/phase_reports/phase16_g_canonical_historical_data_source_audit.json`
- `docs/phase_reports/phase16_a_historical_runtime_v2_performance_test_design.md`
- `reports/phase_reports/phase16_a_historical_runtime_v2_performance_test_design.json`
- `docs/02_architecture/historical_runtime_test_contract.md`
- `docs/02_architecture/runtime_temporal_freshness_contract.md`
- `docs/02_architecture/operational_data_architecture.md`
- `docs/02_architecture/operational_lifecycle_state_reset_and_environment_transition_contract.md`
- `docs/02_architecture/ai_input_output_and_artifact_contract.md`
- `docs/02_architecture/ai_artifact_registry_and_capital_allocation_contract.md`
- `docs/02_architecture/artifact_registry_event_and_acceptance_evidence_contract.md`
- `docs/02_architecture/materialized_registry_index_and_event_replay_contract.md`
- `docs/02_architecture/runtime_architecture_v2.md`

Current code, CLI, Registry, artifact manifests, current Trading State hashes, and persisted data artifacts were also inspected read-only.

## Current Runtime Mainline

Normal entrypoint:

```text
PYTHONPATH=src python3 -m ai_fund_lab_v2.runtime_v2.cli.run_daily_operation
```

Supported CLI jobs:

```text
daily_rehearsal
morning
sell_planning
sell_hold_review_only_morning
submit_pending_promotion_review
authoritative_pending_apply_review
submit
execution
market_refresh
safety_evaluation
safety_refresh
data_readiness
pending_lifecycle
runtime_state_refresh
current_temporal_migration
current_valuation_refresh
broker_readonly_refresh
```

The intended 5BD path should use the normal CLI and normal `.runtime` root:

```text
Market Refresh
↓
Feature Refresh
↓
Candidate AI
↓
Opportunity AI
↓
Position Management
↓
Safety / Data Readiness
↓
Capital Allocation / Planning
↓
Authoritative Pending
↓
Submit Guard
↓
Historical Simulated Broker
↓
Execution Processor
↓
Ledger / Current Apply
↓
Runtime State
↓
Runtime Report / Audit
```

Evidence:

- `src/ai_fund_lab_v2/runtime_v2/cli/run_daily_operation.py` exposes the normal Runtime v2 CLI.
- CLI accepts `--runtime-root`, defaulting to `.runtime`.
- CLI accepts `--mode {demo,simulation,production}` and `--business-date` / `--evaluation-time`.
- CLI help was inspected read-only.

Blocking readiness issue:

`_validate_rehearsal_args()` still rejects most non-demo jobs. `--mode simulation` is syntactically available, but the normal CLI path is not yet configured as a historical execution mode for market/morning/submit/execution job sequencing.

## Planned Command Design

This is the intended command shape after readiness gaps are implemented. It is not currently executable as the 5BD acceptance command.

Per business date:

```text
PYTHONPATH=src python3 -m ai_fund_lab_v2.runtime_v2.cli.run_daily_operation \
  --mode simulation \
  --job market_refresh \
  --business-date <YYYY-MM-DD> \
  --evaluation-time <YYYY-MM-DD>T00:30:00+00:00 \
  --runtime-root .runtime \
  --feature-root .runtime/operations/feature_artifacts \
  --market-refresh-allow-api-fetch false \
  --notification-mode payload-only

PYTHONPATH=src python3 -m ai_fund_lab_v2.runtime_v2.cli.run_daily_operation \
  --mode simulation \
  --job morning \
  --business-date <YYYY-MM-DD> \
  --evaluation-time <YYYY-MM-DD>T00:35:00+00:00 \
  --runtime-root .runtime \
  --feature-root .runtime/operations/feature_artifacts \
  --notification-mode payload-only

PYTHONPATH=src python3 -m ai_fund_lab_v2.runtime_v2.cli.run_daily_operation \
  --mode simulation \
  --job sell_planning \
  --business-date <YYYY-MM-DD> \
  --evaluation-time <YYYY-MM-DD>T00:40:00+00:00 \
  --runtime-root .runtime \
  --feature-root .runtime/operations/feature_artifacts \
  --notification-mode payload-only

PYTHONPATH=src python3 -m ai_fund_lab_v2.runtime_v2.cli.run_daily_operation \
  --mode simulation \
  --job submit \
  --submit-enabled true \
  --business-date <YYYY-MM-DD> \
  --evaluation-time <YYYY-MM-DD>T00:45:00+00:00 \
  --runtime-root .runtime \
  --notification-mode payload-only

PYTHONPATH=src python3 -m ai_fund_lab_v2.runtime_v2.cli.run_daily_operation \
  --mode simulation \
  --job execution \
  --business-date <YYYY-MM-DD> \
  --evaluation-time <YYYY-MM-DD>T06:30:00+00:00 \
  --runtime-root .runtime \
  --notification-mode payload-only
```

Required before execution:

- CLI simulation mode must be accepted for these jobs.
- Submit must use Historical Simulated Broker through the normal Submit Pipeline.
- Execution must use historical snapshot provider through the normal Execution Processor.
- Backup / Reset / Restore must be accepted before normal `.runtime` Trading State is reset.

## Backup / Reset / Restore Readiness

Status: `IMPLEMENTATION_REQUIRED`

Classification: `IMPLEMENTATION_REQUIRED`

Blocking: `true`

Evidence:

- `src/ai_fund_lab_v2/runtime_v2/asset/initializer.py` implements `initialize_demo_operation_current_sot()`.
- That helper backs up only `PERSISTENT_LEDGER_FILES`: `state.json`, `orders.jsonl`, `executions.jsonl`, `positions.jsonl`, `cash.jsonl`, `events.jsonl`.
- The helper writes demo initial Current/Ledger files and is Phase14e8/demo-specific.
- No formal all-state Trading State Backup / Reset / Restore CLI was found for Current, Persistent Ledger, Pending, Runtime State, Approval, Execution, Idempotency, Open orders, Historical Simulated Broker state, operational transient state, manifests, and logs.

Required action:

Implement and accept a formal Backup / Reset / Restore mechanism with all-or-nothing behavior, hash manifest, file count, source paths, `environment_id`, `run_id`, Git commit, Runtime version, and restore validation. It must explicitly exclude Canonical Data, accepted Artifact Sets, Registry, schemas, policies, freeze manifests, training/validation evidence, architecture docs, and phase evidence.

## Historical Clock Readiness

Status: `REVIEW_REQUIRED`

Classification: `CLOCK_CONFIGURATION_GAP`

Blocking: `true`

Evidence:

- CLI accepts `--business-date` and `--evaluation-time`.
- CLI passes parsed `evaluation_time` to many jobs including safety, market evidence, data readiness, pending lifecycle, pending promotion/apply, buy AI, PM, sell planning, submit, current temporal migration, current valuation, and runtime state refresh.
- CLI still falls back to `date.today()` when `--business-date` is omitted.
- CLI `run_id`, `started_at`, `finished_at`, logs, and stage timestamps use actual `_utc_now()`.
- Report markdown writer still has a `date.today()` fallback when no business date can be resolved.
- Runtime and operations code still contains several `datetime.now()` / `utc_now_iso()` paths. Some are expected generation timestamps; others need job-by-job classification before historical execution.

Readiness interpretation:

`--business-date` and `--evaluation-time` provide the preferred injection points, but Phase17-B cannot certify all intended 5BD jobs as historical-clock complete until the actual job sequence is accepted and every state-affecting time source is classified.

Required action:

Add a Historical Clock audit for the exact 5BD command sequence and classify every current-time dependency as:

- `EXPECTED_NON_DETERMINISM`
- `CLOCK_CONFIGURATION_GAP`
- `HISTORICAL_ADAPTER_REQUIREMENT`
- `TEMPORAL_CONTRACT_BUG`

Historical execution commands must require explicit `--business-date` and `--evaluation-time`.

## Historical Simulated Broker Readiness

Status: `IMPLEMENTATION_REQUIRED`

Classification: `BROKER_ADAPTER_DEFECT`

Blocking: `true`

Evidence:

- `src/ai_fund_lab_v2/runtime_v2/simulation/broker.py` defines `SimulationBroker`.
- It supports immediate BUY/SELL fills, insufficient buying power, insufficient quantity, duplicate pending item submit, and post-send-unknown review.
- `src/ai_fund_lab_v2/runtime_v2/simulation/harness.py` defines `run_simulation_replay()`.
- The harness constructs simulation instructions internally and is not the normal CLI mainline.
- `run_submit_pipeline()` accepts an optional adapter at lower level, but CLI submit does not expose adapter selection.
- `run_execution_readonly_pipeline()` accepts an optional snapshot provider at lower level, but CLI execution does not expose historical snapshot provider selection.
- CLI submit calls `run_submit_pipeline(...)` without adapter.
- CLI execution calls `run_execution_readonly_pipeline(...)` without snapshot provider.

Missing broker specifications for Historical 5BD:

- fill price source;
- market/limit order rules;
- lot size / trading unit / tick size;
- daily price limit;
- suspension / no quote / missing data;
- unfilled and partial fill rules;
- fees / tax / slippage;
- corporate actions / splits / reverse splits / delisting;
- normal CLI selection;
- normal Execution schema transformation from historical fills.

Required classification fields are not yet emitted by the normal CLI:

```text
simulation=true
historical_replay=true
broker_write=false
production_equivalent=false
acceptance_only=false
```

Required action:

Connect a historical broker adapter and historical execution snapshot provider to the normal CLI without replacing Runtime mainline. Do not use `run_simulation_replay()` as the official Historical Runtime mainline.

## Canonical Historical Data Readiness

Status: `IMPLEMENTATION_REQUIRED`

Classification: `CANONICAL_DATA_GAP`

Blocking: `true`

Read-only data profile:

| Data | Path | Period | Rows | SHA-256 | Readiness |
|---|---|---:|---:|---|---|
| Canonical normalized OHLCV | `.runtime/phase9/canonical_data/normalized_daily_quotes/data.parquet` | 2021-06-14 to 2026-06-26 | 5,108,552 | `4d02647fc11d5a2855f9993203fe2cb9b32d553cd1192dfc5c03690bdb40201f` | OHLCV historical source exists, but path remains phase-numbered and Runtime feature generation does not use it by default |
| Runtime operational normalized OHLCV | `.runtime/operations/jquants/raw_normalized/jquants/equities_bars_daily/data.parquet` | 2026-02-16 to 2026-07-10 | 418,281 | `c0f9b435e4a951dca1c97a3712571586b9028ace6747328fd7e6e69cfecc479d` | Current Runtime feature source, not full historical |
| Formal trading calendar | `.runtime/data/raw/jquants/trading_calendar/data.parquet` | 2026-03-02 to 2026-06-28 | 91 | `6ddcdef8402dc36ce948fb4bec1b9338af28bcd7404bea835c7f017a7ad4bff7` | Insufficient for 2021+ historical |
| Runtime trading calendar | `.runtime/operations/jquants/raw/jquants/trading_calendar/data.parquet` | 2026-02-16 to 2026-07-10 | 145 | `83dae980628a28c7592c07d4ab8c6c74271491d420b01578fa8a6ccafd6043ec` | Recent only |
| Formal listed issues | `.runtime/data/raw/jquants/listed_issues/data.parquet` | 2026-06-01 to 2026-06-26 | 44,439 | `6fdf7d768d3b1e91431d3eaf4fe4a831b53a41bbcb9e3d13cd6f92d75d495aa1` | Insufficient for point-in-time historical |
| Runtime listed issues | `.runtime/operations/jquants/raw/jquants/listed_issues/data.parquet` | 2026-07-06 to 2026-07-10 | 17,750 | `a02f4afd0f2bd31f2fdd1512c0e74e8251e6ce497d28a31c867efd12f31ed733` | Recent only |

Additional evidence:

- Raw J-Quants daily quote response JSON files exist from `2021-06-14_page_001` to `2026-06-12_page_001`, count `1305`.
- Runtime market refresh uses `.runtime/operations/jquants/raw_normalized/.../data.parquet` and `.runtime/operations/jquants/raw/jquants/listed_issues/data.parquet`.
- Runtime feature generation does not currently read the full canonical historical normalized file by default.

Required action:

Before historical 5BD or longer historical replay, define or implement the accepted connection from canonical historical data to the normal Feature Producer, including historical Trading Calendar, Listed Issues, point-in-time universe, corporate action policy, and fill/valuation price source.

## Point-in-Time Readiness

Status: `IMPLEMENTATION_REQUIRED`

Classification: `CANONICAL_DATA_GAP`

Blocking: `true`

Evidence:

- Candidate features contain as-of and target date fields in existing operational feature artifacts.
- Feature date contract artifacts exist for `2026-07-08`, `2026-07-09`, and `2026-07-10`.
- Feature consumer readiness artifacts exist for `2026-07-06` and `2026-07-10`.
- Historical listed issues and trading calendar do not cover 2021+.
- Standalone corporate action source was not found; adjusted OHLCV exists but standalone split/reverse split/delisting auditability remains incomplete.

Required action:

Accept point-in-time historical data rules for listed status, universe membership, delisting, corporate actions, feature cutoff, valuation, and broker fill prices before 5BD execution.

## Feature Generation Readiness

Status: `IMPLEMENTATION_REQUIRED`

Classification: `FEATURE_DEFECT`

Blocking: `true`

Evidence:

Existing runtime feature artifacts:

| Feature date | Candidate | Opportunity | PM | Capital |
|---|---:|---:|---:|---:|
| 2026-07-06 | 4,370 rows | 4,370 rows | 0 rows | 1 row |
| 2026-07-07 | 4,370 rows | 4,370 rows | 0 rows | 1 row |
| 2026-07-08 | 4,370 rows | 4,370 rows | 0 rows | 1 row |
| 2026-07-09 | missing | missing | missing | missing |
| 2026-07-10 | 4,373 rows | 4,373 rows | 5 rows | 1 row |

Interpretation:

- A complete 5BD window cannot be formed from already generated Runtime feature artifacts.
- Historical Feature Artifact generation from accepted canonical historical data is not ready through the normal Runtime path.
- Reusing Phase4/5/6 training features remains prohibited.

Required action:

Implement or accept a read-only historical feature generation preparation path that uses accepted canonical data and normal Feature Producer contracts, then produce run-scoped feature artifacts for the selected 5BD window.

## Artifact Registry Freeze

Status: `PASS_WITH_BLOCKING_PM_ADAPTER_GAP`

Classification: `REGISTRY_FREEZE_READY_EXCEPT_PM_ADAPTER`

Blocking: `true`

Registry hashes:

| Item | SHA-256 |
|---|---|
| Event Log | `1a8e661eec4d3e7b42d1d8e5a63844056ca7da3640dd5105f95d1a6be6724af6` |
| Materialized Index file | `4fbb7ea6dffc8232139f53b94ba912d6d2650ebc841c0661a7b9639beb5afbbf` |
| Index semantic hash | `7a9e5324371d5525649f9af3df420d5f2081996f8eb00413cf7bb52d0fd4087d` |
| Latest checkpoint file | `ef01348c6f79ca77612db336bea7c10c171316190904737510a7c9ed23a2dcd6` |
| Checkpoint semantic hash | `eff573cd38f2e454e66d9cf94190517bd73f06b47932de06e5e69e03ace95723` |

Accepted Artifact Sets:

| Logical ID | Status | Runtime eligible | Content hash | Schema hash |
|---|---|---:|---|---|
| `ai.candidate.accepted_set` | ACCEPTED | true | `efe4dc1881bfe85a2e346540acfdb4693d5485dfaa2418ee13a3615e627898fe` | `b84eace8cbaa266d581b479ab35e481b43c3d8ba4ed6e8ac2321531f53f0bdab` |
| `ai.opportunity.accepted_set` | ACCEPTED | true | `c14e995857379c95c0d290a9babca5a7a6fc9261bef08960e872094776a45201` | `a09199d7f772781feae05e7f85115875b42841bd14fff1b2b2ce03429811015e` |
| `control.position_management.accepted_set` | ACCEPTED | true | `903131867ea482719939f729fb6c0fad8f71cf3bcb119cbc722d59154c5d5bb8` | `a922dfff5d09b0f58a9bd969437d7b5ba6ac46fb1dfd0e87290feab4fd13dc57` |
| `control.capital_allocation.accepted_set` | ACCEPTED | true | `c97ce2d8f816cbb59aaab5caec31d8122cd6beef9c4f930fcdea65a0648f3b4a` | `c8529d709329593014706132446f6f93689d7881dfaac05e482b361396e1ae58` |
| `features.shared.accepted_set` | ACCEPTED | true | `2052420848150777de73586cb2cd565a2068b8bab01de69a1f8eaab877e4da30` | `349c894ab31687b72a44d0ec871963f4f1bbdfae563e6cfefdcd0bf6ca0b9317` |

Read-only Resolver check:

```text
CANDIDATE_AI_SET ACCEPTED true ai.candidate.accepted_set members=8
OPPORTUNITY_AI_SET ACCEPTED true ai.opportunity.accepted_set members=7
POSITION_MANAGEMENT_POLICY_SET ACCEPTED true control.position_management.accepted_set members=7
CAPITAL_ALLOCATION_POLICY_SET ACCEPTED true control.capital_allocation.accepted_set members=6
FEATURE_SCHEMA_SET ACCEPTED true features.shared.accepted_set members=4
```

Opportunity / Capital confirmations:

- Opportunity accepted set uses Phase5-P model and Phase5-P metrics in the same accepted set.
- Phase5-E is not in the accepted Opportunity set.
- Capital loadable policy resolves to `.runtime/artifacts/control/capital_allocation/policy/capital_deployment_v1/sha256-d3e2a046fb4b56b3/policy.json`.

## PM Runtime Adapter Source Drift

Status: `BLOCKING`

Classification: `ARTIFACT_AUTHORITY_GAP`

Evidence:

| Item | Path | SHA-256 |
|---|---|---|
| Current PM Runtime source actually imported by Runtime | `src/ai_fund_lab_v2/runtime_v2/position_management/producer.py` | `0e238f497dbc4b558cf4e955450ac0d63feb71d3f656f958b92d222f9086b8e5` |
| Accepted PM Runtime Adapter snapshot | `.runtime/artifacts/control/position_management/runtime_adapter/default/sha256-6ffa7da2b91f5fd5/runtime_adapter.py` | `6ffa7da2b91f5fd5cfa76aa4c487e6e6cf5e1293ba929fe374abd61aaadb7d1b` |

Runtime behavior:

- PM producer imports and executes current source from `src/.../position_management/producer.py`.
- It resolves the accepted PM set and requires the `RUNTIME_ADAPTER` member to exist and hash-match.
- It does not import or execute the accepted adapter snapshot file.

Readiness interpretation:

This is not safe to treat as a non-blocking observation for 5BD without an explicit acceptance decision. It is a Runtime artifact authority gap for Historical Runtime execution because the executed adapter body is not byte-identical to the accepted adapter artifact.

Required action:

Before 5BD, either:

- accept the current PM adapter source as a new artifact set/member; or
- execute the frozen accepted adapter artifact; or
- formally approve the source-drift gate behavior as an accepted runtime policy for this test scope.

## Report / Notification / External Effects

Status: `REVIEW_REQUIRED`

Classification: `OPTIONAL_COMPONENT_CONFIGURATION_GAP`

Blocking: `true`

Evidence:

- CLI requires `--notification-mode payload-only` in rehearsal validation.
- Manifest records `notification_sent=false` and `production_order_executed=false`.
- CLI still generates public report / payload artifacts after the job block.
- Historical 5BD must not access Tachibana API, Discord, LINE, Blog publish, or Production API.
- CLI does not yet provide a clean historical mode that disables all external-boundary components while retaining internal reports.

Readiness interpretation:

File-only report/payload generation can be acceptable evidence, but the exact 5BD command sequence must prove no Tachibana ReadOnly, Demo Write, Production Write, Discord, LINE, Blog publish, notification delivery, or Production API access occurs.

Required action:

Add explicit historical external-effects controls or produce a command-level evidence matrix proving all external effects are disabled.

## Regression Baseline

Status: `PARTIAL`

Classification: `IMPLEMENTATION_REQUIRED`

Blocking: `true`

Baseline evidence captured read-only:

| Item | Value |
|---|---|
| Git commit | `abf2d671ad09d5afcd1b8b122a4a5e7700f44b20` |
| Registry Event Log hash | `1a8e661eec4d3e7b42d1d8e5a63844056ca7da3640dd5105f95d1a6be6724af6` |
| Registry Index semantic hash | `7a9e5324371d5525649f9af3df420d5f2081996f8eb00413cf7bb52d0fd4087d` |
| Registry latest checkpoint hash | `eff573cd38f2e454e66d9cf94190517bd73f06b47932de06e5e69e03ace95723` |
| Current hash | `add4f37373c6f7331b6894b29322ffd39a6a0c911086150427d57a2ddb442b0f` |
| Pending hash | `84075f23cc6d1c5ae227de1bfe4a213221aefd131fdadb395058755601ac2c77` |
| Runtime State hash | `4eddb45f782fa5feb028d617acfcbfc9ffda9e53be11ffeb3f990d67d610be03` |

Current state snapshot:

- Runtime State: `business_date=2026-07-12`, `state=REVIEW_REQUIRED`, `environment=demo`.
- Persistent Ledger / Current: `environment=demo`, `as_of=2026-07-09`, `cash=140500`, `buying_power=140500`, `positions_count=5`.
- Pending: `state=EMPTY`, `item_count=0`.

Required action:

Before 5BD, create a formal regression baseline manifest covering Git commit, Runtime version, Registry checkpoint, accepted set IDs, artifact hashes, canonical data manifests, Feature Schema hash, Policy hash, Safety hash, Capital Allocation hash, Current hash, Ledger hash, Pending hash, Runtime State hash, and Market State hash.

## Candidate 5BD Test Window

Status: `NOT_READY`

Classification: `CANONICAL_DATA_GAP`

Blocking: `true`

Candidate window:

```text
requested_start_date=2026-07-06
effective_start_date=2026-07-06 after readiness gaps are closed
five_business_dates=2026-07-06, 2026-07-07, 2026-07-08, 2026-07-09, 2026-07-10
lookback_start=2026-02-16 for current operational normalized data
```

Selection rationale:

- Runtime operational normalized OHLCV covers `2026-02-16` to `2026-07-10`.
- Runtime trading calendar covers `2026-02-16` to `2026-07-10`.
- Runtime listed issues covers `2026-07-06` to `2026-07-10`.
- Feature artifacts exist for `2026-07-06`, `2026-07-07`, `2026-07-08`, and `2026-07-10`.
- `2026-07-10` includes PM feature rows and current positions, useful for sell/hold behavior.

Excluded date:

| Date | Reason |
|---|---|
| `2026-07-09` | Feature artifacts missing under `.runtime/operations/feature_artifacts/2026-07-09/` |

Scenario coverage assessment:

- BUY: likely possible only after full feature + AI + planning readiness is proven.
- SELL/HOLD: likely only if Current has positions and PM feature/opportunity inputs exist; currently PM rows observed on `2026-07-10`.
- NO_TRADE / NO_FILL / valuation-only / Pending carryover / Pending consume / rerun idempotency: cannot be guaranteed from this 5BD window without either natural occurrence or separate contract/fixture tests.

Required action:

Do not mutate data or decisions to force scenarios. If the 5BD natural window does not produce BUY/SELL/HOLD/NO_TRADE/NO_FILL/Pending scenarios, split missing cases into isolated contract tests and record them as supplemental evidence, not official Historical Runtime performance.

## Entry Gates

| Gate | Status | Blocking | Classification | Required action |
|---|---|---:|---|---|
| `NORMAL_MAINLINE_READY` | `IMPLEMENTATION_REQUIRED` | true | `IMPLEMENTATION_REQUIRED` | Accept CLI simulation/historical job sequence without creating separate mainline |
| `BACKUP_RESET_RESTORE_READY` | `IMPLEMENTATION_REQUIRED` | true | `IMPLEMENTATION_REQUIRED` | Implement formal all-state backup/reset/restore |
| `HISTORICAL_CLOCK_READY` | `REVIEW_REQUIRED` | true | `CLOCK_CONFIGURATION_GAP` | Audit exact job sequence and require explicit business/evaluation time |
| `HISTORICAL_BROKER_READY` | `IMPLEMENTATION_REQUIRED` | true | `BROKER_ADAPTER_DEFECT` | Connect historical broker/snapshot provider through normal CLI submit/execution |
| `CANONICAL_HISTORICAL_DATA_READY` | `IMPLEMENTATION_REQUIRED` | true | `CANONICAL_DATA_GAP` | Connect canonical historical data, calendar, listed, corporate action, fill/valuation prices |
| `POINT_IN_TIME_READY` | `IMPLEMENTATION_REQUIRED` | true | `CANONICAL_DATA_GAP` | Accept point-in-time rules for listed/universe/corporate action/fill/valuation |
| `FEATURE_GENERATION_READY` | `IMPLEMENTATION_REQUIRED` | true | `FEATURE_DEFECT` | Generate run-scoped 5BD features from accepted sources through normal Feature Producer |
| `REGISTRY_FREEZE_READY` | `PASS_WITH_BLOCKING_PM_ADAPTER_GAP` | true | `ARTIFACT_AUTHORITY_GAP` | Resolve PM adapter source drift before 5BD |
| `EXTERNAL_EFFECTS_DISABLED` | `REVIEW_REQUIRED` | true | `OPTIONAL_COMPONENT_CONFIGURATION_GAP` | Prove/implement no external effects for historical mode |
| `REGRESSION_BASELINE_READY` | `PARTIAL` | true | `IMPLEMENTATION_REQUIRED` | Write formal baseline manifest before reset/execution |
| `TEST_WINDOW_READY` | `NOT_READY` | true | `CANONICAL_DATA_GAP` | Fill missing 2026-07-09 readiness or choose accepted alternative |

No Entry Gate is ready to start 5BD execution.

## Blocking Findings

1. `B17-BF-01 BACKUP_RESET_RESTORE_NOT_FORMAL`
   - Classification: `IMPLEMENTATION_REQUIRED`
   - Evidence: only demo-specific partial initializer found.
   - Required action: implement accepted all-state backup/reset/restore.

2. `B17-BF-02 CLI_HISTORICAL_MODE_NOT_READY`
   - Classification: `IMPLEMENTATION_REQUIRED`
   - Evidence: CLI exposes `--mode simulation`, but `_validate_rehearsal_args()` rejects non-demo for most jobs.
   - Required action: accept historical/simulation CLI mode for the planned job sequence.

3. `B17-BF-03 HISTORICAL_BROKER_NOT_CONNECTED_TO_NORMAL_CLI`
   - Classification: `BROKER_ADAPTER_DEFECT`
   - Evidence: lower-level adapter seams exist, but CLI does not expose historical submit adapter or execution snapshot provider.
   - Required action: connect historical broker boundary to normal Submit and Execution paths.

4. `B17-BF-04 CANONICAL_HISTORICAL_DATA_CHAIN_NOT_READY`
   - Classification: `CANONICAL_DATA_GAP`
   - Evidence: OHLCV exists historically, but Runtime feature source is operational recent data; calendar/listed data are recent only.
   - Required action: accepted canonical historical data connection and point-in-time sources.

5. `B17-BF-05 FEATURE_5BD_WINDOW_INCOMPLETE`
   - Classification: `FEATURE_DEFECT`
   - Evidence: 2026-07-09 feature artifacts missing.
   - Required action: produce accepted run-scoped features or choose another validated window.

6. `B17-BF-06 PM_ADAPTER_SOURCE_DRIFT`
   - Classification: `ARTIFACT_AUTHORITY_GAP`
   - Evidence: current executed PM source hash differs from accepted adapter snapshot hash.
   - Required action: accept current source, execute frozen adapter, or formally approve gate-only behavior.

7. `B17-BF-07 EXTERNAL_EFFECTS_NOT_FULLY_PROVEN_DISABLED`
   - Classification: `OPTIONAL_COMPONENT_CONFIGURATION_GAP`
   - Evidence: file payload/public report generation exists; full historical no-external-effect command matrix not yet accepted.
   - Required action: implement/prove historical external effect controls.

## Non-Blocking Findings

1. `B17-NF-01 REGISTRY_RESOLVER_READINESS_PASS`
   - Classification: `OBSERVATION`
   - Evidence: read-only Resolver returned all five accepted eligible sets.

2. `B17-NF-02 EXPECTED_RUNTIME_TIMESTAMP_NONDETERMINISM`
   - Classification: `EXPECTED_NON_DETERMINISM`
   - Evidence: run_id, logs, started_at, finished_at use actual `_utc_now()`.
   - Required action: exclude or separately classify timestamp-only differences in semantic regression.

3. `B17-NF-03 EXISTING_RECENT_OPERATIONAL_WINDOW_CANDIDATE`
   - Classification: `OBSERVATION`
   - Evidence: operational data and most feature artifacts exist for the 2026-07-06 to 2026-07-10 week.
   - Limitation: not ready because 2026-07-09 features are missing and historical canonical source is not accepted for the 5BD path.

## Read-only Validations Performed

- CLI help inspection:

```text
PYTHONPATH=src python3 -m ai_fund_lab_v2.runtime_v2.cli.run_daily_operation --help
```

- Registry resolver read-only smoke:

```text
RegistryArtifactResolver().resolve(...)
```

- SHA-256 hash checks for Registry, Current, Pending, Runtime State, PM current source, and accepted PM adapter snapshot.

- Read-only Parquet profiling for canonical OHLCV, operational OHLCV, trading calendar, listed issues, and existing feature artifacts.

No Historical Runtime execution, reset, restore, broker simulation execution, Tachibana access, feature regeneration, canonical data regeneration, or state mutation was performed.

## Out of Scope

The following were intentionally not performed:

- Historical Runtime execution.
- 5BD / 20BD / 1-year / full-period execution.
- Normal `.runtime` reset.
- Trading State backup execution.
- Trading State restore execution.
- Current / Ledger / Pending / Runtime State mutation.
- Historical Broker order simulation execution.
- Tachibana API access.
- Tachibana Demo submit.
- Production connection.
- AI retraining.
- Model replacement.
- Policy / Safety / Capital Allocation optimization.
- Runtime Core modification.
- Registry / Acceptance / artifact path redesign.
- Canonical Data regeneration.
- Feature regeneration.
- Baseline overwrite.

