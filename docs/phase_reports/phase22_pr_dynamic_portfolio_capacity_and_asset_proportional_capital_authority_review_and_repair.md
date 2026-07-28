# Phase22-PR - Dynamic Portfolio Capacity and Asset-Proportional Capital Authority Review and Repair

## Summary

Phase22-PR reviewed Phase21 Strategy Architecture, Phase22-H through P implementation, Strategy config/schema/tests, Runtime Test shadow wiring, and generated probe evidence for fixed position-count and fixed JPY capital authority.

The Phase21 position-count question is resolved as Case B: fixed maximum position count is not allowed as Strategy authority. Daily position count is derived from eligible opportunities, meaningful allocation capacity, current holdings, asset-proportional sizing, concentration, liquidity/lot feasibility, cash reserve, Pending reservation, and Safety review state.

## Changes

- Removed Strategy use of `strategy_maximum_position_count = 8` as a calculation cap.
- Removed routine Safety position-count hard maximum authority; `safety_hard_maximum` remains nullable compatibility/observability only.
- Added explicit non-use flags:
  - `strategy_fixed_position_cap_used = false`
  - `strategy_fixed_jpy_exposure_cap_used = false`
  - `legacy_max_exposure_authority_used = false`
- Added asset-proportional Dynamic Cash / Exposure fields:
  - `portfolio_total_equity`
  - `current_cash`
  - `current_market_value`
  - `pending_reserved_cash`
  - `net_available_cash`
  - `target_cash_amount`
  - `target_invested_ratio`
  - `target_invested_notional`
  - `current_invested_ratio`
  - `incremental_deployment_capacity`
- Added Position Sizing delta fields:
  - `current_notional`
  - `incremental_target_notional`
  - `incremental_buy_notional`
- Updated Runtime Test Strategy shadow validation for ratio-to-notional consistency, fixed-cap non-use, legacy isolation, Pending single deduction, and target-weight sum.

## Evidence

Machine-readable evidence:

```text
reports/phase22_pr_dynamic_portfolio_capacity_and_asset_proportional_capital_authority_review_and_repair/
```

Important files:

```text
phase22_pr_report.json
authority_inventory.json
design_traceability.json
fixed_limit_usage_audit.json
asset_proportionality_evidence.json
legacy_isolation_evidence.json
schema_migration_evidence.json
pit_lineage_evidence.json
runtime_mutation_evidence.json
test_results.json
final_gate.json
```

## Tests

```bash
PYTHONPATH=src PYTHONPYCACHEPREFIX=/private/tmp/pycache python3 -m pytest tests/strategy -q
# 118 passed
```

```bash
PYTHONPATH=src PYTHONPYCACHEPREFIX=/private/tmp/pycache python3 -m pytest \
  tests/runtime_v2/test_phase22_p_strategy_shadow_wiring.py \
  tests/runtime_v2/test_phase22_m_strategy_summarize_scope.py \
  tests/runtime_v2/test_phase19_ax_system_status.py \
  -q
# 8 passed
```

```bash
PYTHONPATH=src PYTHONPYCACHEPREFIX=/private/tmp/pycache python3 -m compileall -q \
  scripts/runtime_test.py \
  src/ai_fund_lab_v2/strategy \
  src/ai_fund_lab_v2/runtime_v2/safety
# PASS
```

## Probe

`fresh-run` 1BD with `historical-smoke` was not executed because an existing active run is present:

```text
runtime-test-historical-smoke-20260726T224753726008Z
```

A shadow-only generation was run for the active run business date `2022-09-15`. It produced run-scoped Strategy evidence and did not mutate Runtime authority:

```text
runtime_mutation_performed = false
broker_write_performed = false
active_runtime_consumer_eligibility = NO
runtime_switch_performed = false
```

The probe judgment remains `BLOCK` because upstream Strategy components are BLOCK in the existing halted active run, including market context future/source blockers, corporate event source blockers, and portfolio policy incompatibility. This is not treated as successful PIT validation.

`validate --run-id runtime-test-historical-smoke-20260726T224753726008Z --business-date 2022-09-15 --json` reports Strategy shadow structural validity PASS and the new fixed-cap checks PASS:

```text
fixed_cap_non_use = PASS
ratio_to_notional_consistency = PASS
legacy_authority_isolation = PASS
pending_single_deduction = PASS
target_weight_sum = PASS
```

## Operator 5BD Command

Codex did not run the long 5BD command. Operator validation remains:

```bash
PYTHONPATH=src python3 scripts/runtime_test.py fresh-run \
  --profile historical-smoke \
  --start-date 2026-07-06 \
  --business-days 5 \
  --initial-cash 1000000 \
  --confirm \
  --yes-i-understand-this-mutates-trading-state
```

Post-run checks:

```bash
PYTHONPATH=src python3 scripts/runtime_test.py run-status --profile historical-smoke --json
PYTHONPATH=src python3 scripts/runtime_test.py summarize --profile historical-smoke --scope strategy --json
PYTHONPATH=src python3 scripts/runtime_test.py validate --profile historical-smoke --json
```

## Final Judgment

```text
Primary Judgment:
REVIEW_REQUIRED

Phase21 Position Count Design:
FIXED_MAXIMUM_NOT_ALLOWED

Strategy Fixed Position Maximum:
REMOVED

Strategy Fixed JPY Exposure Cap:
REMOVED

Asset-Proportional Capital Allocation:
PASS

Current Holdings Delta Sizing:
PASS

Pending Double Deduction:
NOT_DETECTED

Legacy max_positions Isolation:
PASS

Legacy max_exposure Isolation:
PASS

Historical PIT:
BLOCK

Runtime Mutation:
NONE

Shadow Consumer Eligibility:
REVIEW_REQUIRED

Active Runtime Consumer Eligibility:
NO

Runtime Switch Performed:
NO

Legacy Authority Active:
YES

Blocking Gaps:
1 - Existing active run Strategy shadow is BLOCK due upstream PIT/source blockers unrelated to fixed-cap authority.

Non-blocking Gaps:
1 - 5BD operator validation is not run by Codex.

5BD Operator Validation Ready:
NO

Phase22 Closure Recommendation:
REVIEW_REQUIRED

Next Task:
Phase22-PS - PIT-valid Strategy Shadow Fixture / Upstream BLOCK Closure
```
