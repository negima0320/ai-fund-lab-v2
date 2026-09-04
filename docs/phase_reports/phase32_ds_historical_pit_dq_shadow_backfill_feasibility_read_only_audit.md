# Phase32-DS — Historical PIT Artifact DQ SHADOW Backfill Feasibility READ-ONLY Audit

## Scope

- Target source run: `runtime-test-historical-extended-smoke-20260902T060955933565Z`
- Desired window: `2022-10-03` through `2023-10-26`
- Audit type: READ-ONLY feasibility audit
- Backfill executed: NO
- Tiny in-memory proof fixture executed: YES, no file output
- Production change executed: NO
- Target run mutated: NO
- Fresh-run/resume/recover/replay/long runtime executed by Codex: NO
- Future outcome / later PnL used: NO

Mandatory references read:

- `docs/phase_reports/phase32_dq_unified_marginal_capital_authority_shadow_implementation.md`
- `docs/phase_reports/phase32_dr_production_vs_unified_marginal_capital_shadow_divergence_read_only_audit.md`
- `docs/phase_reports/phase32_dp_winner_capitalization_unified_marginal_capital_allocation_deep_dive_shadow_audit.md`
- `docs/phase_reports/phase32_do_post_cw_dg_one_year_growth_persistence_capital_utilization_read_only_audit.md`
- `src/ai_fund_lab_v2/strategy/marginal_capital_value.py`
- `src/ai_fund_lab_v2/strategy/portfolio_construction.py`
- Runtime Test Specification and Runtime Test Command Guide sections on run evidence, Strategy shadow PIT source resolution, read-only inspection, and non-mutation boundaries.

## Executive Finding

The one-year target window is feasible for an isolated DQ SHADOW backfill if the next phase consumes each day's immutable `strategy/portfolio_construction.json` as the canonical PIT input and emits results only into a separate analysis namespace.

The safe path is not to rerun the full Strategy or PC producer. The safe path is a narrow post-hoc evaluator that loads the original day-specific PC artifact and calls only:

```text
marginal_capital_value.build_unified_marginal_capital_shadow(...)
```

with stored inputs:

```text
portfolio_members
capital_competition.competitors
capital_competition.canonical_cash_competitor_evidence
capital_competition.market_candidate_cash_interaction
capital_competition.risk_pacing_evidence
incremental_budget_reconciliation
business_date
```

This preserves the original Production decision and applies the current DQ SHADOW evaluator as an explicitly dual-provenance analysis artifact.

`ONE_YEAR_DQ_SHADOW_BACKFILL_FEASIBILITY = YES_WITH_GAPS`

The main gap is not PIT input availability. It is source-version interpretation: DQ was implemented after the historical dates, and current DQ action classification differs from the earliest native DQ artifact on `2023-11-10`. Backfill output must therefore record dual provenance and must not claim to be an artifact originally produced by the historical run.

## Required Inputs

`DQ_BACKFILL_REQUIRED_INPUTS = AVAILABLE_FROM_DAILY_PC_ARTIFACTS`

| Required input | Canonical producer / owner | Historical artifact path | Schema/version observed | Binding requirements | Window availability |
|---|---|---|---|---|---:|
| PC member universe | Portfolio Construction | `daily/<date>/strategy/portfolio_construction.json::portfolio_members` | parent `portfolio_construction.v1`; member rows embedded | `business_date=<date>`, source hashes embedded in PC artifact | 264/264 |
| Production competitors | Portfolio Construction Capital Competition | `daily/<date>/strategy/portfolio_construction.json::capital_competition.competitors` | `portfolio_construction.capital_competition.v1` parent | same PC artifact/run/date binding | 264/264 |
| Cash evidence | Portfolio Construction Cash Competitor | `capital_competition.canonical_cash_competitor_evidence` | `cash_competitor_evidence.v1` | `business_date=<date>`, future/historical flags false | 264/264 |
| Market-candidate cash interaction | Portfolio Construction Capital Competition | `capital_competition.market_candidate_cash_interaction` | embedded PC capital competition evidence | same PC artifact/run/date binding | 264/264 |
| Incremental budget evidence | Portfolio Construction | `incremental_budget_reconciliation` and `available_incremental_budget` | embedded PC evidence | same PC artifact/run/date binding | 264/264 |
| Risk pacing evidence | Portfolio Policy / PC consumer | `capital_competition.risk_pacing_evidence` | embedded risk-pacing evidence | `risk_pacing_as_of=<date>` where populated | 264/264 |
| BQ / Entry / SI materialization | Buy Quality / Entry / Strategy Intelligence, consumed by PC | embedded in `portfolio_members`; source refs in `upstream_artifacts` | daily artifact summaries and member fields | `business_date_aligned=true`, `feature_date_lte_business_date=true` where recorded | 264/264 through PC materialization |
| PM / campaign identity | Position Management, consumed by PC | embedded in `portfolio_members`; source refs in `upstream_artifacts.position_management` | PM decision fields embedded in member rows | `position_campaign_id`, `source_pm_decision_ref`, current-position fields | 264/264 for PC universe; ADD-specific rows on 113 days |
| Portfolio snapshot / cash / exposure | Persistent Ledger Current snapshot consumed by PC | embedded in PC member current fields and cash/risk evidence | PC snapshot fields | same-day PC artifact and upstream current portfolio binding | 264/264 |
| DQ evaluator source | Current source | `src/ai_fund_lab_v2/strategy/marginal_capital_value.py` | `unified_marginal_capital_shadow.v1` | backfill producer source identity must be recorded | current only, not historical |

The preferred input artifact is the original daily PC artifact because it already materializes the upstream PM/BQ/Entry/SI/risk/portfolio context that DQ consumes. Recomputing Candidate, Opportunity, BQ, Entry, PM, or SI from raw market data is not required for the backfill feasibility established here.

## PIT Availability Matrix

Target-window scan:

| Metric | Count |
|---|---:|
| Desired business days | 264 |
| Days with `strategy/portfolio_construction.json` | 264 |
| Days with `portfolio_members` | 264 |
| Days with `capital_competition` | 264 |
| Days with `capital_competition.competitors` | 264 |
| Days with canonical cash evidence | 264 |
| Days with market-candidate cash interaction | 264 |
| Days with risk pacing evidence | 264 |
| Days with incremental budget evidence | 264 |
| Fully reconstructable days by stored PC-input contract | 264 |
| Partially reconstructable days | 0 |
| Unreconstructable days | 0 |

Contiguous reconstructable window:

- first day: `2022-10-03`
- last day: `2023-10-26`
- contiguous fully reconstructable count: 264

`DQ_BACKFILL_PIT_AVAILABILITY_MATRIX = 264_TOTAL; 264_FULLY_RECONSTRUCTABLE; 0_PARTIAL; 0_UNRECONSTRUCTABLE; CONTIGUOUS_2022-10-03_TO_2023-10-26`

## Current-State Dependency

The DQ producer in `marginal_capital_value.build_unified_marginal_capital_shadow` is a pure payload builder over supplied mappings. It does not read `.runtime`, latest Current, latest campaign registry, active accepted generation, current-day caches, broker state, or global mutable state.

The unsafe path would be invoking full modern Portfolio Construction for old dates, because that could re-resolve upstream producers and current runtime roots. The feasible path avoids that by consuming the stored PC artifact and invoking only the DQ pure function.

`DQ_CURRENT_STATE_DEPENDENCY = NONE_FOR_DQ_PURE_FUNCTION; FULL_PC_RECOMPUTE_NOT_REQUIRED_AND_NOT_RECOMMENDED`

## PIT Safety By Domain

### ADD Campaign Identity

Historical ADD rows are reconstructable from stored PC member rows. Example rows include `position_campaign_id`, `current_position=true`, `pm_action=ADD`, `semantic_buy_type=BUY_ADD`, `source_pm_decision_ref`, candidate/opportunity IDs, current quantity/weight, Entry/BQ decisions, and lot-resolution evidence.

Observed ADD coverage from in-memory current-DQ estimate:

- days with at least one DQ `BUY_ADD_NEXT_LOT`: 113
- estimated `BUY_ADD_NEXT_LOT` rows: 152
- example successful graduation controls:
  - `2023-02-13 / 94320 / pc-7c5bd9294d48b016-94320-0001`
  - `2023-03-15 / 94320 / pc-7c5bd9294d48b016-94320-0001`

`HISTORICAL_ADD_CAMPAIGN_IDENTITY_RECONSTRUCTABLE = YES`

### REENTRY Context

The PC member rows contain semantic REENTRY state and related prior/recovery evidence as materialized on the original business date. The DQ evaluator consumes those fields from the member and does not need later REENTRY outcomes.

Estimated current-DQ competitor coverage:

- `REENTRY_NEXT_LOT` rows: 5,196
- REENTRY rows present across 264/264 days

`HISTORICAL_REENTRY_CONTEXT_RECONSTRUCTABLE = YES`

### Portfolio Snapshot

Each PC artifact carries current-position rows, current quantity, current weight, target weight, cash competitor evidence, gross exposure, remaining cash weight, concentration/headroom-related reason codes, and lot-resolution evidence. This is sufficient for DQ's marginal-row observability without reading later ledger state.

`HISTORICAL_PORTFOLIO_SNAPSHOT_RECONSTRUCTABLE = YES`

### Risk / Regime

DQ directly consumes `capital_competition.risk_pacing_evidence`, available 264/264 days.

Risk-pacing coverage:

| Risk pacing intent | Days |
|---|---:|
| `CAUTIOUS_DEPLOYMENT` | 171 |
| `NORMAL_DEPLOYMENT` | 48 |
| `GRADUAL_REDEPLOYMENT` | 45 |

Broader market-regime labels are available in `strategy/source_manifest.json` / strategy summaries for analysis joins:

| Trend regime | Days |
|---|---:|
| `BULL` | 111 |
| `RECOVERY` | 46 |
| `RANGE` | 46 |
| `BEAR` | 45 |
| `CORRECTION` | 16 |

`HISTORICAL_RISK_CONTEXT_RECONSTRUCTABLE = YES`

### BQ / Entry / SI

The backfill should consume BQ, Entry, and SI as already materialized in the original PC member rows and upstream summaries. It should not recompute those producers with today's code. Sample upstream artifact bindings record same-day source refs and hashes for `buy_quality`, `candidate`, `opportunity`, `current_portfolio`, `pending`, `policy_config`, and compatible materialized evidence for `strategy_intelligence`, `position_management`, `market_context`, and `portfolio_policy`.

`HISTORICAL_BQ_ENTRY_SI_RECONSTRUCTABLE = YES_FROM_PC_MATERIALIZATION; DO_NOT_RECOMPUTE_UPSTREAM_PRODUCERS`

## Production Independence

The proposed backfill is SHADOW-only and must not rewrite any original run artifact:

- original PC allocation
- accepted weights
- Position Sizing
- Runtime Planning
- Pending
- Submit
- Execution / fills
- Ledger / Current
- campaign state
- cash state

`FUTURE_OUTCOME_USED = NO`

`ORIGINAL_PRODUCTION_DECISION_PRESERVED = YES`

## Backfill Output Isolation

Recommended output namespace:

```text
reports/runtime_tests/analysis/<backfill_id>/
  source_run_id.txt
  manifest.json
  daily/<business_date>/unified_marginal_capital_shadow.json
  daily/<business_date>/input_hashes.json
  summary.json
```

The backfill must never overwrite:

```text
reports/runtime_tests/runs/<RUN_ID>/daily/<date>/strategy/portfolio_construction.json
```

or any runtime state path.

`BACKFILL_OUTPUT_ISOLATED_FROM_ORIGINAL_RUN = YES`

## Dual Provenance Contract

Backfill artifacts need explicit dual provenance:

- original source run id: `runtime-test-historical-extended-smoke-20260902T060955933565Z`
- original Production source identity from `run_state.source_baseline`:
  - source commit: `a56f2bc26105eb14fd67322b7cd53c0d6ef1b1bd`
  - source dirty: `true`
  - accepted artifact hash: `5451016e490214f81440f0d4fd154dc89cd76a86f84dd7daed5e8fb383e144a5`
  - registry hash: `4c07b5647425b32653e3e0a0e1a1164130133cc0db2c22881dcef5b7c97a35ba`
- original daily PC artifact path and hash
- input artifact hashes from DQ payload
- DQ SHADOW evaluator source identity at backfill execution time
- backfill id and timestamp
- `shadow_only=true`
- `production_allocation_consumer=false`
- `runtime_planning_consumer=false`

`BACKFILL_DUAL_PROVENANCE_CONTRACT = REQUIRED_AND_FEASIBLE`

## Determinism / Proof Fixture

Tiny in-memory proof fixture was executed with no output files and no runtime mutation.

Historical ADD-era proof dates:

| Date | Result |
|---|---|
| `2023-02-13` | DQ function produced 25 competitors: `BUY_ADD_NEXT_LOT=1`, `BUY_NEW_NEXT_LOT=11`, `REENTRY_NEXT_LOT=12`, `CASH_OPTIONALITY=1`; ADD sample `94320` preserved campaign id and PM source ref |
| `2023-03-15` | DQ function produced 38 competitors: `BUY_ADD_NEXT_LOT=1`, `BUY_NEW_NEXT_LOT=15`, `REENTRY_NEXT_LOT=21`, `CASH_OPTIONALITY=1`; ADD sample `94320` preserved campaign id and PM source ref |

Native post-DQ equivalence control:

| Date | Native vs in-memory recompute |
|---|---|
| `2023-11-10` | PARTIAL: winner and divergence class match, but hash and candidate count differ; native had 56 rows, current source recompute has 40 rows |
| `2023-11-13` | PASS: hash, candidate count, top types, winner, and divergence class match |
| `2023-11-14` | PASS: hash, candidate count, top types, winner, and divergence class match |

`DQ_BACKFILL_PROOF_FIXTURE = PASS`

`NATIVE_DQ_VS_BACKFILL_EQUIVALENCE = PARTIAL`

The `2023-11-10` mismatch is explained by action-classification generation drift: the native artifact includes continuation-like rows typed as `REENTRY_NEXT_LOT` even when the current source excludes `REENTRY_NOT_APPLICABLE` from REENTRY classification. The current source is better aligned with DS's requirement not to treat ADD-capable held campaigns as REENTRY, but it means exact native hash equivalence cannot be assumed across all DQ-generation boundaries.

## Action Classification Integrity

Current DQ classification rules:

- `BUY_ADD_NEXT_LOT` when `current_position=true` and `pm_action=ADD`
- `REENTRY_NEXT_LOT` when `semantic_buy_type=REENTRY` or `reentry_semantic_state` starts with `REENTRY_`, excluding `REENTRY_NOT_APPLICABLE`
- `BUY_NEW_NEXT_LOT` when not current position and `membership_intent=ADD_CANDIDATE`

This current rule correctly separates ADD-capable held campaigns from REENTRY for historical backfill. Native `2023-11-10` artifacts show earlier-generation classification drift, so a future backfill must record the DQ evaluator source identity and should use the corrected current DQ rule rather than trying to preserve the earlier native artifact's misclassification.

`BACKFILL_ACTION_CLASSIFICATION_INTEGRITY = PASS_WITH_SOURCE_VERSION_NOTE`

If the goal is byte-for-byte reproduction of native early-DQ artifacts, the answer is no. If the goal is safe one-year current-DQ SHADOW evaluation over original PIT inputs, the classification path is acceptable and preferable.

## Estimated Backfill Coverage

In-memory current-DQ estimate over the target window:

| Competitor type | Estimated rows |
|---|---:|
| `BUY_NEW_NEXT_LOT` | 2,483 |
| `REENTRY_NEXT_LOT` | 5,196 |
| `BUY_ADD_NEXT_LOT` | 152 |
| `CASH_OPTIONALITY` | 264 |
| Total | 8,095 |

ADD bucket estimate:

| ADD bucket | Count |
|---|---:|
| `LOW_VALUE + COMPLETE + INFEASIBLE_DUE_TO_LOT + BLOCKED_BY_CONCENTRATION` | 77 |
| `HIGH_VALUE_EVIDENCE_INCOMPLETE + INCOMPLETE + INFEASIBLE_DUE_TO_LOT + BLOCKED_BY_CONCENTRATION` | 40 |
| `MEDIUM_VALUE + COMPLETE + FEASIBLE + BLOCKED_BY_CONCENTRATION` | 19 |
| `MEDIUM_VALUE + COMPLETE + INFEASIBLE_DUE_TO_LOT + BLOCKED_BY_CONCENTRATION` | 11 |
| `LOW_VALUE + COMPLETE + FEASIBLE + BLOCKED_BY_CONCENTRATION` | 5 |

`ESTIMATED_BACKFILL_ADD_COMPETITOR_COVERAGE = 113_DAYS; 152_BUY_ADD_NEXT_LOT_ROWS`

`BACKFILL_REGIME_COVERAGE = BULL_111; RECOVERY_46; RANGE_46; BEAR_45; CORRECTION_16`

## Recommended Execution Surface

Recommended next implementation surface:

```text
PYTHONPATH=src python3 scripts/runtime_test.py shadow-backfill-marginal-capital \
  --source-run-id runtime-test-historical-extended-smoke-20260902T060955933565Z \
  --start-date 2022-10-03 \
  --end-date 2023-10-26 \
  --output-root reports/runtime_tests/analysis/<backfill_id> \
  --confirm-read-only
```

Command requirements:

- read only from `reports/runtime_tests/runs/<source_run_id>/daily/<date>/strategy/portfolio_construction.json`
- fail closed when required PC/DQ inputs are missing or date/run bindings do not match
- never read live `.runtime` state for historical values
- never mutate Runtime, Pending, Ledger, Current, Registry, Accepted Generation, Broker state, or original run evidence
- emit isolated analysis artifacts only
- include dual provenance and input hashes
- support `--dry-run` / plan mode before artifact write
- optionally include a native-DQ equivalence check for dates with existing native DQ artifacts

`RECOMMENDED_BACKFILL_EXECUTION_SURFACE = NEW_NON_MUTATING_RUNTIME_TEST_ANALYSIS_COMMAND_shadow-backfill-marginal-capital`

Existing `summarize` is read-only but not appropriate as the primary surface because it is an inspection/report command, not a deterministic per-day SHADOW artifact generator. Existing recovery/replay/resume commands are explicitly not appropriate.

## Feasibility / Evidence Quality

`ONE_YEAR_DQ_SHADOW_BACKFILL_FEASIBILITY = YES_WITH_GAPS`

`BACKFILL_EVIDENCE_QUALITY = STRONG_DIAGNOSTIC_PIT`

The evidence is strong enough for diagnostic SHADOW analysis because the original daily PC artifacts preserve the decision-time materialization consumed by DQ. It should not be called Production-decision-grade authority because DQ itself did not exist as a Production or accepted consumer at the historical decision time, and because source-version drift must be represented explicitly.

## Required Final Answers

1. `DQ_BACKFILL_REQUIRED_INPUTS = AVAILABLE_FROM_DAILY_PC_ARTIFACTS; SEE_REQUIRED_INPUTS_TABLE`
2. `DQ_BACKFILL_PIT_AVAILABILITY_MATRIX = 264_TOTAL; 264_FULLY_RECONSTRUCTABLE; 0_PARTIAL; 0_UNRECONSTRUCTABLE; CONTIGUOUS_2022-10-03_TO_2023-10-26`
3. `DQ_CURRENT_STATE_DEPENDENCY = NONE_FOR_DQ_PURE_FUNCTION; FULL_PC_RECOMPUTE_NOT_REQUIRED_AND_NOT_RECOMMENDED`
4. `HISTORICAL_ADD_CAMPAIGN_IDENTITY_RECONSTRUCTABLE = YES`
5. `HISTORICAL_REENTRY_CONTEXT_RECONSTRUCTABLE = YES`
6. `HISTORICAL_PORTFOLIO_SNAPSHOT_RECONSTRUCTABLE = YES`
7. `HISTORICAL_RISK_CONTEXT_RECONSTRUCTABLE = YES`
8. `HISTORICAL_BQ_ENTRY_SI_RECONSTRUCTABLE = YES_FROM_PC_MATERIALIZATION; DO_NOT_RECOMPUTE_UPSTREAM_PRODUCERS`
9. `FUTURE_OUTCOME_USED = NO`
10. `ORIGINAL_PRODUCTION_DECISION_PRESERVED = YES`
11. `BACKFILL_OUTPUT_ISOLATED_FROM_ORIGINAL_RUN = YES`
12. `BACKFILL_DUAL_PROVENANCE_CONTRACT = REQUIRED_AND_FEASIBLE`
13. `DQ_BACKFILL_DETERMINISM = YES_FOR_SAME_INPUTS_AND_SAME_DQ_SOURCE; RECORD_SOURCE_VERSION`
14. `ORIGINAL_ARTIFACT_PRIORITY = YES`
15. `DQ_BACKFILL_PROOF_FIXTURE = PASS`
16. `NATIVE_DQ_VS_BACKFILL_EQUIVALENCE = PARTIAL; 2023-11-13_AND_2023-11-14_HASH_MATCH; 2023-11-10_DIFFERS_DUE_CLASSIFICATION_GENERATION_DRIFT`
17. `BACKFILL_ACTION_CLASSIFICATION_INTEGRITY = PASS_WITH_SOURCE_VERSION_NOTE`
18. `ESTIMATED_BACKFILL_ADD_COMPETITOR_COVERAGE = 113_DAYS; 152_BUY_ADD_NEXT_LOT_ROWS`
19. `BACKFILL_REGIME_COVERAGE = BULL_111; RECOVERY_46; RANGE_46; BEAR_45; CORRECTION_16`
20. `RECOMMENDED_BACKFILL_EXECUTION_SURFACE = NEW_NON_MUTATING_RUNTIME_TEST_ANALYSIS_COMMAND_shadow-backfill-marginal-capital`
21. `ONE_YEAR_DQ_SHADOW_BACKFILL_FEASIBILITY = YES_WITH_GAPS`
22. `BACKFILL_EVIDENCE_QUALITY = STRONG_DIAGNOSTIC_PIT`
23. `PRODUCTION_CHANGE_EXECUTED = NO`
24. `TARGET_RUN_MUTATED = NO`
25. `LONG_RUNTIME_EXECUTED = NO`
26. `NEXT_RECOMMENDED_STEP = PHASE32-DT_IMPLEMENT_ISOLATED_DQ_SHADOW_BACKFILL_COMMAND_THEN_RUN_IT_ON_2022-10-03_TO_2023-10-26_ANALYSIS_NAMESPACE_ONLY`
27. `FINAL_JUDGMENT = PHASE32_DS_ONE_YEAR_DQ_SHADOW_BACKFILL_FEASIBLE_WITH_ISOLATED_DUAL_PROVENANCE_ANALYSIS_PATH`

## Final Judgment

`PHASE32_DS_ONE_YEAR_DQ_SHADOW_BACKFILL_FEASIBLE_WITH_ISOLATED_DUAL_PROVENANCE_ANALYSIS_PATH`

The existing one-year Historical run contains enough immutable decision-time PC artifacts to reconstruct DQ SHADOW diagnostics without rerunning Production behavior and without touching the original run. The next phase should implement a dedicated non-mutating analysis command that applies the current DQ evaluator to original day-specific PC artifacts, writes only isolated analysis output, records dual provenance, and fails closed on missing or stale PIT inputs.
