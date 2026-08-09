# Phase28-D0 100BD Operator Runbook

Use this runbook to execute the Phase28-D After 100BD run. Do not edit strategy, runtime, configuration, schema, or tests between preflight and run completion.

## 1. Capture Repository State

```bash
cd /Users/negishi/work/ai-fund-lab-v2
git rev-parse --abbrev-ref HEAD
git rev-parse HEAD
git status --short
git diff --stat
git diff --name-only
```

Save the output for Phase28-D attachments.

## 2. Run Preflight

```bash
PYTHONPATH=src PYTHONPYCACHEPREFIX=/private/tmp/ai-fund-lab-v2-pycache python3 -m py_compile \
  src/ai_fund_lab_v2/strategy/portfolio_construction.py \
  src/ai_fund_lab_v2/strategy/position_sizing.py \
  src/ai_fund_lab_v2/strategy/runtime_planning.py
```

```bash
PYTHONPATH=src PYTHONPYCACHEPREFIX=/private/tmp/ai-fund-lab-v2-pycache python3 -m pytest \
  tests/strategy/test_phase22_e_portfolio_construction.py::test_phase28_c_canonical_add_bridge_increases_existing_target_weight_when_incremental_evidence_passes \
  tests/strategy/test_phase22_e_portfolio_construction.py::test_phase28_c_canonical_add_bridge_fails_closed_when_expected_edge_evidence_missing \
  tests/strategy/test_phase22_j_position_sizing.py::test_phase28_c_add_target_weight_bridge_reaches_positive_quantity_delta \
  tests/strategy/test_phase22_j_position_sizing.py::test_phase28_c_add_lot_rounding_zero_delta_is_explicit \
  tests/strategy/test_phase22_g_runtime_planning.py::test_phase27_d2e_runtime_planning_maps_canonical_quantity_delta_to_runtime_action \
  tests/strategy/test_phase22_g_runtime_planning.py::test_phase27_d2e_canonical_delta_disables_pm_fallback \
  -q
```

```bash
jq -e . config/runtime_tests/historical_smoke_5bd.json configs/strategy/position_sizing.json configs/strategy/portfolio_policy.json configs/safety/portfolio_limits.json
```

```bash
PYTHONPATH=src python3 scripts/runtime_test.py run-status --profile historical-smoke --json
PYTHONPATH=src python3 scripts/runtime_test.py system-status --profile historical-smoke --scope readiness --target-start-date 2023-01-04 --target-end-date 2023-05-31 --json
PYTHONPATH=src python3 scripts/runtime_test.py ai-status --profile historical-smoke --check-runtime-readiness --json
PYTHONPATH=src python3 scripts/runtime_test.py plan --profile historical-smoke --start-date 2023-01-04 --business-days 100 --json
PYTHONPATH=src python3 scripts/runtime_test.py fresh-run --profile historical-smoke --start-date 2023-01-04 --business-days 100 --initial-cash 1000000 --dry-run --json
```

Stop if any command fails.

## 3. Start 100BD After Run

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

Record `<AFTER_RUN_ID>` from the output.

## 4. Monitor

```bash
PYTHONPATH=src python3 scripts/runtime_test.py run-status --profile historical-smoke --json
PYTHONPATH=src python3 scripts/runtime_test.py system-status --profile historical-smoke --scope runtime --json
PYTHONPATH=src python3 scripts/runtime_test.py summarize --profile historical-smoke --run-id <AFTER_RUN_ID> --scope overview --json
```

## 5. Resume If Needed

```bash
PYTHONPATH=src python3 scripts/runtime_test.py resume --profile historical-smoke --run-id <AFTER_RUN_ID> --dry-run --json
```

If the dry-run is acceptable:

```bash
PYTHONPATH=src python3 scripts/runtime_test.py resume \
  --profile historical-smoke \
  --run-id <AFTER_RUN_ID> \
  --confirm \
  --yes-i-understand-this-mutates-trading-state \
  --json
```

## 6. Final Validation

```bash
PYTHONPATH=src python3 scripts/runtime_test.py validate --profile historical-smoke --run-id <AFTER_RUN_ID> --json
PYTHONPATH=src python3 scripts/runtime_test.py summarize --profile historical-smoke --run-id <AFTER_RUN_ID> --scope performance --write-evidence --json
PYTHONPATH=src python3 scripts/runtime_test.py summarize --profile historical-smoke --run-id <AFTER_RUN_ID> --scope strategy --json
PYTHONPATH=src python3 scripts/runtime_test.py summarize --profile historical-smoke --run-id <AFTER_RUN_ID> --scope strategy-trace --json
PYTHONPATH=src python3 scripts/runtime_test.py summarize --profile historical-smoke --run-id <AFTER_RUN_ID> --scope strategy-attribution --json
```

## 7. Attach Evidence

Attach or preserve:

- repository state outputs from step 1
- full command output from preflight, fresh-run, resume if used, validate, and summarize
- `reports/runtime_tests/runs/<AFTER_RUN_ID>/run_state.json`
- `reports/runtime_tests/runs/<AFTER_RUN_ID>/plan.json`
- `reports/runtime_tests/runs/<AFTER_RUN_ID>/historical_evaluation_authority.json`
- `reports/runtime_tests/runs/<AFTER_RUN_ID>/strategy_shadow_manifest.json`
- `reports/runtime_tests/runs/<AFTER_RUN_ID>/final_summary.json`
- full `reports/runtime_tests/runs/<AFTER_RUN_ID>/performance_report/`
- daily strategy, position management, position campaign, submit, and execution artifacts for all 100 business days

## 8. Stop Conditions

Stop and preserve evidence if:

- preflight fails
- run-status shows a conflicting active run
- fresh-run dry-run rejects the contract
- external effects are unexpectedly enabled
- run fails, abandons, or cannot resume
- performance report is missing
- daily strategy or execution artifacts are missing
- ADD evidence cannot be extracted from raw artifacts
