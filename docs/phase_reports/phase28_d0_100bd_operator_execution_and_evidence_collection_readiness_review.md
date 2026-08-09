# Phase28-D0: 100BD Operator Execution and Evidence Collection Readiness Review

Task ID: `phase28_d0_100bd_operator_execution_and_evidence_collection_readiness_review`

Status: `COMPLETE`

Primary Judgment: `PHASE28_D0_READY_WITH_NON_BLOCKING_EVIDENCE_LIMITATIONS`

100BD Operator Entry Decision: `APPROVED`

This is a read-only execution contract review. No runtime, strategy, configuration, schema, or test implementation was changed. No fresh/resume/10BD/20BD/100BD/1y/long historical execution was run by Codex during this review.

## Scope

Phase28-D0 verifies whether the Phase28-C canonical ADD allocation bridge is ready for a user-operated 100BD After run and whether the evidence required for Phase28-D can be collected without further implementation.

The reviewed contract covers:

- baseline comparability
- repository state capture
- preflight checks
- fresh 100BD After command
- resume command
- monitoring commands
- performance report evidence
- ADD funnel evidence
- required attachments
- stop conditions

## Baseline Contract

Primary baseline run:

- `run_id`: `runtime-test-historical-smoke-20260804T074611098414Z`
- profile: `historical-smoke`
- runtime root: `.runtime`
- period: `2023-01-04` through `2023-05-31`
- business days: `100`
- initial capital: `1,000,000 JPY`
- source commit captured in run artifacts: `a9eeb27833e7c56898fe6a8a5b7daefe4ec48f3f`
- source dirty captured in run artifacts: `true`
- external effects: broker write `false`, external delivery `false`, J-Quants fetch `false`, Tachibana API `false`, notification mode payload-only
- performance report exists under `reports/runtime_tests/runs/runtime-test-historical-smoke-20260804T074611098414Z/performance_report/`

The baseline remains usable for Phase28-D because Phase28-A adopted it as the primary ADD baseline and extracted the canonical ADD failure facts. The known limitation is that the baseline fresh-run summary carried close/strategy-shadow review limitations. That limitation is not a D0 blocker, but it must be disclosed in Phase28-D comparison.

## Baseline ADD Facts

From Phase28-A:

- existing-position rows: `364`
- PM ADD rows: `145`
- Runtime BUY_ADD rows: `0`
- ADD submit/fill rows: `0`
- zero delta/quantity rows among PM ADD: `145`
- Rank1 existing-position rows: `86`
- Rank1 PM ADD rows: `76`
- Rank1 BUY_ADD rows: `0`
- average cash ratio: `50.108%`
- final cash ratio: `65.965%`
- average invested ratio: `49.892%`
- final invested ratio: `34.035%`

This is the causal baseline for Phase28-D: PM selected ADD opportunities, but canonical sizing produced no incremental buy quantity and runtime had no BUY_ADD orders.

## After Run Contract

The After run must preserve comparability:

- same profile: `historical-smoke`
- same period: `2023-01-04` through `2023-05-31`
- same business day count: `100`
- same initial cash: `1,000,000 JPY`
- same runtime root unless the operator intentionally records an isolated root
- no configuration, schema, runtime, strategy, or threshold edits between preflight and run start
- exact source commit and dirty diff must be captured before execution

Approved fresh command:

```bash
PYTHONPATH=src python3 scripts/runtime_test.py fresh-run \
  --profile historical-smoke \
  --start-date 2023-01-04 \
  --business-days 100 \
  --initial-cash 1000000 \
  --confirm \
  --yes-i-understand-this-mutates-trading-state \
  --json
```

Approved resume command:

```bash
PYTHONPATH=src python3 scripts/runtime_test.py resume \
  --profile historical-smoke \
  --run-id <AFTER_RUN_ID> \
  --confirm \
  --yes-i-understand-this-mutates-trading-state \
  --json
```

Dry-run checks may be used before mutation:

```bash
PYTHONPATH=src python3 scripts/runtime_test.py fresh-run --profile historical-smoke --start-date 2023-01-04 --business-days 100 --initial-cash 1000000 --dry-run --json
PYTHONPATH=src python3 scripts/runtime_test.py resume --profile historical-smoke --run-id <AFTER_RUN_ID> --dry-run --json
```

## Preflight Contract

Required preflight before the After run:

```bash
git rev-parse --abbrev-ref HEAD
git rev-parse HEAD
git status --short
git diff --stat
git diff --name-only

PYTHONPATH=src PYTHONPYCACHEPREFIX=/private/tmp/ai-fund-lab-v2-pycache python3 -m py_compile \
  src/ai_fund_lab_v2/strategy/portfolio_construction.py \
  src/ai_fund_lab_v2/strategy/position_sizing.py \
  src/ai_fund_lab_v2/strategy/runtime_planning.py

PYTHONPATH=src PYTHONPYCACHEPREFIX=/private/tmp/ai-fund-lab-v2-pycache python3 -m pytest \
  tests/strategy/test_phase22_e_portfolio_construction.py::test_phase28_c_canonical_add_bridge_increases_existing_target_weight_when_incremental_evidence_passes \
  tests/strategy/test_phase22_e_portfolio_construction.py::test_phase28_c_canonical_add_bridge_fails_closed_when_expected_edge_evidence_missing \
  tests/strategy/test_phase22_j_position_sizing.py::test_phase28_c_add_target_weight_bridge_reaches_positive_quantity_delta \
  tests/strategy/test_phase22_j_position_sizing.py::test_phase28_c_add_lot_rounding_zero_delta_is_explicit \
  tests/strategy/test_phase22_g_runtime_planning.py::test_phase27_d2e_runtime_planning_maps_canonical_quantity_delta_to_runtime_action \
  tests/strategy/test_phase22_g_runtime_planning.py::test_phase27_d2e_canonical_delta_disables_pm_fallback \
  -q

jq -e . config/runtime_tests/historical_smoke_5bd.json configs/strategy/position_sizing.json configs/strategy/portfolio_policy.json configs/safety/portfolio_limits.json

PYTHONPATH=src python3 scripts/runtime_test.py run-status --profile historical-smoke --json
PYTHONPATH=src python3 scripts/runtime_test.py system-status --profile historical-smoke --scope readiness --target-start-date 2023-01-04 --target-end-date 2023-05-31 --json
PYTHONPATH=src python3 scripts/runtime_test.py ai-status --profile historical-smoke --check-runtime-readiness --json
PYTHONPATH=src python3 scripts/runtime_test.py plan --profile historical-smoke --start-date 2023-01-04 --business-days 100 --json
```

If any preflight command fails, do not start the 100BD After run.

## Monitoring Contract

During or after execution:

```bash
PYTHONPATH=src python3 scripts/runtime_test.py run-status --profile historical-smoke --json
PYTHONPATH=src python3 scripts/runtime_test.py system-status --profile historical-smoke --scope runtime --json
PYTHONPATH=src python3 scripts/runtime_test.py summarize --profile historical-smoke --run-id <AFTER_RUN_ID> --scope overview --json
PYTHONPATH=src python3 scripts/runtime_test.py summarize --profile historical-smoke --run-id <AFTER_RUN_ID> --scope performance --json
PYTHONPATH=src python3 scripts/runtime_test.py summarize --profile historical-smoke --run-id <AFTER_RUN_ID> --scope strategy --json
PYTHONPATH=src python3 scripts/runtime_test.py validate --profile historical-smoke --run-id <AFTER_RUN_ID> --json
```

The run is complete only when run state and validation indicate completion/pass and the performance report directory exists.

## Evidence Contract

The operator must preserve the full After run directory:

```text
reports/runtime_tests/runs/<AFTER_RUN_ID>/
```

Required evidence paths:

- `run_state.json`
- `plan.json`
- `historical_evaluation_authority.json`
- `strategy_shadow_manifest.json`
- `final_summary.json`
- `performance_report/performance_summary.json`
- `performance_report/trade_history.csv`
- `performance_report/equity_curve.csv`
- `performance_report/drawdown.csv`
- `performance_report/symbol_statistics.csv`
- `performance_report/quality_statistics.csv`
- `performance_report/holding_period.csv`
- `daily/<business_date>/position_management/pm_decisions.json`
- `daily/<business_date>/positions/position_campaigns.json`
- `daily/<business_date>/strategy/portfolio_construction.json`
- `daily/<business_date>/strategy/position_sizing.json`
- `daily/<business_date>/strategy/runtime_planning.json`
- `daily/<business_date>/strategy/strategy_decision_trace.json`
- `daily/<business_date>/execution/submitted_order_authority.json`
- `daily/<business_date>/execution/fills.json`
- `daily/<business_date>/execution/historical_fill_authority.json`

Required ADD funnel evidence:

- PM ADD count and rows
- portfolio construction ADD bridge eligibility and target_weight deltas
- position sizing positive and zero quantity_delta counts
- runtime BUY_ADD count and submitted orders
- execution ADD fills
- ADD position campaign continuity
- Rank1 existing-position ADD recovery
- cash/invested ratio change versus baseline

There is no blocker in the artifact topology. A dedicated ADD extraction CLI was not confirmed in D0, so Phase28-D should use the raw run artifacts and/or existing summarize scopes. This is a non-blocking evidence limitation because the required JSON/CSV inputs are present and attachable.

## Stop Conditions

Stop before or during execution if:

- preflight fails
- branch/commit/dirty diff cannot be captured
- profile, period, business day count, or initial cash differs from baseline without explicit evidence
- runtime reports an active conflicting run
- external effects become enabled unexpectedly
- fresh-run dry-run rejects the command
- strategy/runtime/config/schema/test implementation changes after preflight
- run enters abandoned/failed/error state
- performance report is missing after completion
- required daily strategy or execution artifacts are missing
- ADD funnel evidence cannot be extracted from the run directory

## Open Gaps

No blocking gaps remain for starting the user-operated 100BD After run.

Non-blocking limitations:

- baseline source was dirty, so the After run must capture commit and dirty diff for honest comparison
- baseline close/strategy-shadow review limitations must be restated in Phase28-D
- dedicated ADD funnel CLI was not confirmed; raw artifacts and summarize scopes are the evidence source

## Next Step

Proceed to user-operated Phase28-D 100BD After execution using the runbook:

`docs/phase_reports/phase28_d0_100bd_operator_runbook.md`
