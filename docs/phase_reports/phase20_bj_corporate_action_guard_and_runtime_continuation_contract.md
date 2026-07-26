# Phase20-BJ Corporate Action Guard and Runtime Continuation Contract

## Summary

Final status:

```text
PHASE20_BJ_CORPORATE_ACTION_EXPECTED_SAFE_HALT_CONFIRMED
```

Supporting judgments:

```text
PHASE20_BJ_ROOT_CAUSE_CONFIRMED
PHASE20_BJ_SYMBOL_NORMALIZATION_PASS
PHASE20_BJ_PIT_TEMPORAL_AUTHORITY_PASS
PHASE20_BJ_NO_FUTURE_DATA_LEAKAGE_PASS
PHASE20_BJ_PENDING_LIFECYCLE_CONTRACT_PASS
PHASE20_BJ_SHORT_REGRESSION_PASS
PHASE20_BJ_RESUME_DECISION_COMPLETE
```

Range run `runtime-test-historical-extended-smoke-20260724T000054969857Z` stopped at `2026-04-22:submit` because Historical Submit Adapter detected a Corporate Action impact for `60850` from J-Quants raw daily quote `AdjFactor=0.1` on the same business date. This is not a symbol-normalization failure and not a future-data leak.

The project does not currently have a standalone accepted Corporate Action event SoT for split/reverse split/code-change/merger lifecycle handling. Existing Phase17/Phase19 contracts treat non-1.0 adjustment factors as fail-closed Corporate Action impact evidence. Therefore the correct behavior is: do not submit the order, do not consume Pending, and stop for review.

No Runtime logic, PM decision rule, sell quantity, Corporate Action Guard, model, threshold, broker path, training, calibration, or Accepted Generation was changed.

## Run Evidence

Range run:

```text
run_id = runtime-test-historical-extended-smoke-20260724T000054969857Z
status = HALT
completed_days = 8 / 20
stopped_at = 2026-04-22:submit
runtime_cli_exit_code = 10
runner_exit_code = 30
```

2026-04-22 stage sequence:

```text
morning = PASS
sell_planning = PASS
submit = BLOCKED / NO_SUBMIT_ATTEMPTED
```

Submit item:

```text
pending_item_id = opi-sell-exit-pm-60850-001
symbol = 60850
side = SELL
source_decision = EXIT
position_quantity_before = 200
requested_sell_quantity = 200
final_sell_quantity = 200
expected_remaining_quantity = 0
```

Contracts that passed before Corporate Action Guard:

```text
PM EXIT decision = PASS
Sell Planning = PASS
Pending lifecycle / approval = PASS
Safety authority = ALLOW
Submit Guard = PASS
Current quantity = 200
Historical simulated broker available quantity = 200
Sell quantity contract = PASS
PIT listed issues universe = PASS
```

Failure point:

```text
adapter_preflight_status = HALT
reason = corporate action guard failed
corporate_action_status = IMPACT_DETECTED
submit_status = NOT_SUBMITTED
submit_action = NO_SUBMIT_ATTEMPTED
broker_write = false
```

## Corporate Action Evidence

Source artifact:

```text
reports/runtime_tests/runs/runtime-test-historical-extended-smoke-20260724T000054969857Z/daily/2026-04-22/market_refresh/inputs/historical_asof/2026-04-22/raw/jquants/equities_bars_daily/data.parquet
sha256 = 156aed1e4a67a8720df1efbdb872ab1df6cd1e741b90a4fee0e468d61b7d9ce1
```

Relevant rows:

| Date | Code | AdjFactor | O | H | L | C | AdjO | AdjH | AdjL | AdjC | Vo | AdjVo |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 2026-04-20 | 60850 | 1.0 | 3640.0 | 3990.0 | 3640.0 | 3960.0 | 364.0 | 399.0 | 364.0 | 396.0 | 730000.0 | 7300000.0 |
| 2026-04-21 | 60850 | 1.0 | 3990.0 | 3990.0 | 3700.0 | 3800.0 | 399.0 | 399.0 | 370.0 | 380.0 | 380600.0 | 3806000.0 |
| 2026-04-22 | 60850 | 0.1 | 396.0 | 460.0 | 393.0 | 430.0 | 396.0 | 460.0 | 393.0 | 430.0 | 8562600.0 | 8562600.0 |

Decision:

```text
event_type = ADJFACTOR_ADJUSTMENT_EVENT
event_type_confidence = DERIVABLE_PARTIAL
ex_or_effective_date = 2026-04-22
reference_date = 2026-04-22
impact_factor = 0.1
price_scale_impact = detected
quantity_impact = not accepted from current artifact, requires standalone CA SoT
final_impact_decision = IMPACT_DETECTED
```

The raw quote row itself is the available Corporate Action proxy. A standalone Corporate Action event table is not available in the current accepted Runtime authority, so the exact corporate event name is not inferred beyond the adjustment-factor event.

## PIT And Future Leakage

Historical as-of view:

```text
reports/runtime_tests/runs/runtime-test-historical-extended-smoke-20260724T000054969857Z/daily/2026-04-22/market_refresh/historical_asof_view.json
sha256 = 3548872b39052e3112a2d7c672b5b079a3ed20b7d3cb49b93f7b757aa6c1d315
status = PASS
business_date = 2026-04-22
latest_available_market_date = 2026-04-22
```

Logical input manifest:

```text
reports/runtime_tests/runs/runtime-test-historical-extended-smoke-20260724T000054969857Z/daily/2026-04-22/market_refresh/inputs/historical_asof/2026-04-22/logical_input_manifest.json
sha256 = 2fa9512904561d6c8e80aeec335c2ce6ab7256f0ec6916f00faf37447467608e
```

PIT checks:

```text
consumer_cutoff = 2026-04-22
source rows consumed after 2026-04-22 for 60850 = 0
future_snapshot_used = false
listed_issues_snapshot = 2026-04-22
listed_issues_content_hash_verified = true
```

Listed Issues PIT authority:

```text
selected_snapshot_path = .runtime/operations/jquants/historical_snapshots/listed_issues/snapshots/2026-04-22/data.parquet
selected_manifest_path = .runtime/operations/jquants/historical_snapshots/listed_issues/snapshots/2026-04-22/manifest.json
selected_snapshot_date = 2026-04-22
matched_row_count = 1
normalized_symbol = 60850
```

## Symbol Normalization

Runtime symbol and J-Quants key:

```text
Runtime symbol = 60850
J-Quants raw quote Code = 60850
J-Quants listed issues Code = 60850
Corporate Action lookup key = 60850
```

Broker available quantity evidence:

```text
broker_available_quantity_symbol = 60850
broker_available_quantity_issue_code = 6085
```

The `60850 -> 6085` representation appears only in broker available quantity evidence, where 4-digit broker/security code representation is expected. The Corporate Action Guard itself compares the runtime symbol to raw OHLCV `Code` through `_normalize_listed_issue_code`, preserving `60850`. No evidence shows an accidental match to a different issue.

Conclusion:

```text
PHASE20_BJ_SYMBOL_NORMALIZATION_PASS
```

## Normal SELL Comparison

Same symbol normal submit example:

```text
date = 2026-04-20
pending_item_id = opi-sell-reduce-pm-60850-005
symbol = 60850
side = SELL
source_decision = REDUCE
AdjFactor = 1.0
preflight_status = PASS
submit_status = ACCEPTED
business_classification = HISTORICAL_FILL_ACCEPTED
broker_write = false
```

Comparison:

| Item | 2026-04-20 REDUCE | 2026-04-22 EXIT |
| --- | --- | --- |
| Runtime symbol | 60850 | 60850 |
| Broker issue code evidence | 6085 | 6085 |
| Submit Guard | PASS | PASS |
| Safety | ALLOW | ALLOW |
| Corporate Action proxy | AdjFactor 1.0 | AdjFactor 0.1 |
| Adapter preflight | PASS | HALT |
| Submit | ACCEPTED historical fill | NOT_SUBMITTED |
| Pending consumed | yes after accepted submit | no |

The distinguishing factor is the Corporate Action proxy, not symbol identity or quantity authority.

## Runtime Continuation Contract

Existing SoT reviewed:

```text
docs/02_architecture/runtime_test_specification.md
docs/02_architecture/autonomous_ai_operations_architecture.md
docs/02_architecture/ai_artifact_registry_and_capital_allocation_contract.md
reports/phase17_d_5bd_smoke_minimum_readiness/corporate_action_guard.json
reports/phase19_ad_u2_d_corporate_action_policy_approval/corporate_action_policy_contract.json
```

Relevant established rules:

```text
Tests fail closed when authority, temporal, state, data, or environment evidence is incomplete.
Future corporate action / future adjustment leakage is prohibited.
Standalone Corporate Action event SoT is NOT_AVAILABLE / NOT_FORMALLY_ACCEPTED.
Full Corporate Action support is outside the current accepted smoke/runtime scope.
Integrity or authority failures are HALT.
```

Judgment:

```text
Option A is the current accepted contract.
Corporate Action impact detected -> do not submit -> keep Pending unconsumed -> halt/review before continuation.
```

Option B, a non-executable terminal outcome that consumes or terminates only the affected Pending item while continuing the run, is a possible future contract, but it is not currently accepted. Adopting it would require a new common Runtime design for non-executable terminal orders, duplicate prevention, resume semantics, and Current/Pending/Execution reporting.

Option C, excluding before Planning, is also a possible future observability improvement, but current PM/Planning does not have an accepted standalone CA SoT to use before submit.

## Root Cause

```text
EXPECTED_SAFE_HALT_DUE_TO_SUPPORTED_GUARD_DETECTING_UNSUPPORTED_CORPORATE_ACTION_IMPACT
```

Secondary observability gap:

```text
Corporate Action Guard response records IMPACT_DETECTED but does not persist matched raw OHLCV rows, AdjFactor values, or source hash directly in response_classification.
```

Submit status mapping note:

```text
HistoricalSubmitAdapter returns HALT, but SubmitPipelineResult top-level status becomes BLOCKED because no item was submitted and no review_required flag is set.
```

This did not cause unsafe submission. It does make the final CLI classification less explicit than the adapter evidence. A future contract may choose to propagate adapter HALT to submit top-level status, but Phase20-BJ did not change behavior.

## Resume Decision

```text
EXPECTED_SAFE_HALT
RESUME_NOT_SAFE
FRESH_RUN_REQUIRED for any changed Range evaluation period
```

Actual resume to continue the same run is not safe because it would re-enter the same approved Pending EXIT submit and hit the same Corporate Action Guard. Skipping the failed submit job would violate the Pending-only / no silent skip contract. Dry-run resume is safe for inspection only.

Dry-run command for operator inspection:

```bash
cd /Users/negishi/work/ai-fund-lab-v2
PYTHONPATH=src:. python3 scripts/runtime_test.py resume \
  --run-id runtime-test-historical-extended-smoke-20260724T000054969857Z \
  --dry-run
```

If the Range campaign should be continued for cross-regime comparison, select a new Range window or explicitly accept a Corporate Action-containing test scenario, then start a new fresh run. Do not reuse the halted run as a completed 20BD Range baseline.

## Test Gap

Existing tests covered:

```text
target-symbol Corporate Action Guard halts on non-1.0 AdjFactor
unrelated Corporate Action does not halt another symbol
PIT listed issues future snapshot rejection
```

Existing tests did not cover:

```text
real 20BD Range replay with actual AdjFactor=0.1
top-level SubmitPipeline status propagation for adapter HALT
non-executable terminal Pending contract
resume behavior after Corporate Action halted submit
full event metadata because standalone CA event SoT does not exist
```

## Validation

Executed short checks:

```text
PYTHONPYCACHEPREFIX=/private/tmp/pycache PYTHONPATH=src:. python3 -m pytest -q tests/runtime_v2/test_phase17_bv8_historical_submit_pit_universe_authority.py
```

Result:

```text
8 passed
```

Executed read-only probes:

```text
60850 raw OHLCV AdjFactor inspection for 2026-04-20..2026-04-22
60850 future rows after 2026-04-22 in logical input
2026-04-20 normal SELL submit comparison
2026-04-22 failed EXIT submit manifest inspection
Listed Issues PIT snapshot lookup for 60850
```

Not executed:

```text
Range 20BD fresh-run
Bull / Bear / Range rerun
Historical Acquisition
Broker connection
Training
Calibration
Accepted Generation change
Full backtest
```

## Cross-Regime Impact

The Range run is not a complete 20BD comparable baseline:

```text
completed_days = 8 / 20
usable_for_full_cross_regime_comparison = false
```

It remains valid evidence for:

```text
Corporate Action safe halt behavior
PIT Corporate Action proxy detection
Pending unconsumed after no-submit halt
Range campaign selection risk
```

Next action should be one of:

```text
1. Choose a different Range 20BD window without unsupported Corporate Action impact.
2. Treat this Range run as a Corporate Action scenario, not the main Range PM comparison.
3. Design and accept a non-executable terminal Corporate Action contract before attempting continuation through the same event.
```

