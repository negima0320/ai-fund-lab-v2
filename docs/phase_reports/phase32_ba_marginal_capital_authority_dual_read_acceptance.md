# Phase32-BA Marginal Capital Authority Dual-Read Acceptance

## Executive Summary

READ-ONLY dual-read acceptance was performed for:

```text
runtime-test-historical-extended-smoke-20260828T000823285458Z
```

The Phase32-AZ production-shaped authority:

```text
canonical_marginal_capital_frontier_authority.v1
```

was built in memory only from actual fresh-run artifacts. No artifact was
written into the run directory, no production consumer was enabled, and no
fresh-run, resume, replay, backtest, or current-run control was executed.

Primary result:

```text
Authority generation PASS on 50 / 50 characterized days.
Accepted target gaps were observed for NEW, REENTRY, and ADD.
Multi-lot ADD target projections were observed.
Projected PS-compatible quantity fields were internally consistent on 490 / 490 accepted targets.
Production behavior remained unchanged because the authority remains consumer-disabled.
```

Important migration finding:

```text
The disabled authority projects materially broader target gaps than current production.
This is acceptable for dual-read generation, but it is not yet safe for consumer switch.
```

## Required Inputs

Read:

- `docs/phase_reports/phase32_az_production_shaped_marginal_capital_value_authority_implementation.md`
- `docs/phase_reports/phase32_ax_broad_fresh_run_shadow_frontier_acceptance.md`
- `docs/phase_reports/phase32_ay_marginal_capital_frontier_production_migration_design.md`

Actual artifacts read:

- `run_state.json`
- `strategy_shadow_manifest.json`
- `daily/{date}/strategy/portfolio_construction.json`
- `daily/{date}/strategy/position_sizing.json`
- `daily/{date}/strategy/portfolio_policy.json`
- `daily/{date}/current_valuation_refresh/valuation_projection.json`
- `daily/{date}/current_valuation_refresh/safety_authority_decision.json`
- `daily/{date}/morning/safety_decision.json`, only where valuation safety was absent

## Coverage

| Field | Value |
| --- | --- |
| Run id | `runtime-test-historical-extended-smoke-20260828T000823285458Z` |
| Evidence path | `reports/runtime_tests/runs/runtime-test-historical-extended-smoke-20260828T000823285458Z` |
| Characterized days | 50 |
| Coverage start | `2022-10-03` |
| Coverage end | `2022-12-14` |
| In-memory authority generation only | `YES` |

## Authority Generation

| Metric | Count |
| --- | ---: |
| Authority generation `PASS` days | 50 |
| Authority generation `REVIEW_REQUIRED` days | 0 |
| Cash source `PASS` days | 50 |
| Cash source `REVIEW_REQUIRED` days | 0 |
| Ambiguous actual-path value failures | 0 |
| Determinism mismatches | 0 |
| Forbidden future/outcome fields in authority output | 0 |

The absence of actual-path `REVIEW_REQUIRED` rows means no missing/ambiguous
cash or candidate-evidence condition was encountered in this 50BD sample. The
fail-closed contract remains covered by Phase32-AZ focused regression tests.

## Candidate Surface

| Candidate type | Count |
| --- | ---: |
| `NEW_FIRST_LOT` | 1,529 |
| `REENTRY_FIRST_LOT` | 594 |
| `ADD_NEXT_LOT` | 153 |
| `CASH_OPTIONALITY` | 50 |
| Total | 2,326 |

## Accepted Target Gaps

| Accepted type | Target rows | Days observed |
| --- | ---: | ---: |
| `NEW_FIRST_LOT` | 262 | 50 |
| `REENTRY_FIRST_LOT` | 134 | 48 |
| `ADD_NEXT_LOT` | 94 | 31 |
| `CASH_OPTIONALITY` | 0 | 0 |
| Total security targets | 490 | 50 |

ADD lot acceptance:

| ADD lot | Accepted targets |
| --- | ---: |
| lot #1 | 32 |
| lot #2 | 32 |
| lot #3 | 30 |

This confirms that the authority can materialize sequential ADD target gaps
and accepted candidate lineage on actual fresh-run artifacts.

## Multi-Lot ADD Examples

| Date | Symbol | Campaign | Accepted lots |
| --- | --- | --- | --- |
| `2022-10-05` | `94340` | `pc-993d47f0f8d7e622-94340-0001` | `#1 0.0141075990`, `#2 0.0141075990`, `#3 0.0141075990` |
| `2022-10-07` | `94320` | `pc-e0c5da196f07ea55-94320-0001` | `#1 0.0148027236`, `#2 0.0148027236`, `#3 0.0148027236` |
| `2022-10-12` | `94320` | `pc-e0c5da196f07ea55-94320-0001` | `#1 0.0151455603`, `#2 0.0151455603`, `#3 0.0151455603` |
| `2022-10-12` | `94340` | `pc-993d47f0f8d7e622-94340-0001` | `#1 0.0140719510`, `#2 0.0140719510`, `#3 0.0140719510` |
| `2022-10-19` | `94320` | `pc-e0c5da196f07ea55-94320-0001` | `#1 0.0154374257`, `#2 0.0154374257`, `#3 0.0154374257` |

Each accepted target retained:

- `accepted_incremental_weight`
- `target_gap`
- `target_minus_current`
- `accepted_incremental_quantity`
- `accepted_incremental_notional`
- `accepted_frontier_candidate_ids`
- `source_pm_decision_id`
- `source_candidate_id`
- `source_pc_evidence_ids`

## 94320 Persistent Campaign Trace

Representative `94320` ADD authority rows:

| Date | Lot | Disposition | Capital value | Incremental weight | Post weight |
| --- | ---: | --- | ---: | ---: | ---: |
| `2022-10-07` | 1 | `ACCEPTED_INCREMENTAL_TARGET` | 0.6391167296 | 0.0148027236 | 0.0445577236 |
| `2022-10-07` | 2 | `ACCEPTED_INCREMENTAL_TARGET` | 0.6331956401 | 0.0148027236 | 0.0593604473 |
| `2022-10-07` | 3 | `ACCEPTED_INCREMENTAL_TARGET` | 0.6272745506 | 0.0148027236 | 0.0741631709 |
| `2022-10-12` | 1 | `ACCEPTED_INCREMENTAL_TARGET` | 0.7008361859 | 0.0151455603 | 0.0458205603 |
| `2022-10-12` | 2 | `ACCEPTED_INCREMENTAL_TARGET` | 0.6947779617 | 0.0151455603 | 0.0609661207 |
| `2022-10-12` | 3 | `ACCEPTED_INCREMENTAL_TARGET` | 0.6887197376 | 0.0151455603 | 0.0761116810 |
| `2022-10-19` | 1 | `ACCEPTED_INCREMENTAL_TARGET` | 0.6292302157 | 0.0154374257 | 0.0616344257 |
| `2022-10-19` | 2 | `ACCEPTED_INCREMENTAL_TARGET` | 0.6230552454 | 0.0154374257 | 0.0770718514 |
| `2022-10-19` | 3 | `ACCEPTED_INCREMENTAL_TARGET` | 0.6168802752 | 0.0154374257 | 0.0925092771 |

The capital value declines across lots because post-lot headroom declines. The
current disabled contract still accepts later lots when their value remains
above Cash optionality and feasibility remains PASS.

## Production Dual-Read Comparison

Current production PC/PS was not changed. The BA comparison only asks whether
the new authority projection differs from existing production target gaps.

| Metric | Count |
| --- | ---: |
| Accepted authority targets compared to production PS rows | 490 |
| Same target-gap weight | 3 |
| Different target-gap weight | 487 |
| Same projected quantity as production quantity | 116 |
| Different projected quantity from production quantity | 374 |

Production gap `0` while authority gap `> 0`:

| Type | Count |
| --- | ---: |
| `NEW_FIRST_LOT` | 176 |
| `REENTRY_FIRST_LOT` | 131 |
| `ADD_NEXT_LOT` | 67 |
| Total | 374 |

Representative examples:

| Date | Symbol | Type | Lot | Authority gap | Production qty | Authority qty | Capital value |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: |
| `2022-10-03` | `94320` | `NEW_FIRST_LOT` | 1 | 0.0153500000 | 0 | 100 | 0.7590540840 |
| `2022-10-03` | `76920` | `NEW_FIRST_LOT` | 1 | 0.0145800000 | 0 | 100 | 0.6140894310 |
| `2022-10-05` | `94340` | `ADD_NEXT_LOT` | 1 | 0.0141075990 | 0 | 100 | 0.4450407914 |
| `2022-10-05` | `94340` | `ADD_NEXT_LOT` | 2 | 0.0141075990 | 0 | 100 | 0.4393977518 |
| `2022-10-07` | `94320` | `ADD_NEXT_LOT` | 1 | 0.0148027236 | 0 | 100 | 0.6391167296 |

Interpretation:

- The authority successfully emits PS-compatible target gaps.
- The projection is materially broader than current production.
- This is not a production behavior regression because the consumer is disabled.
- It is a migration blocker for immediate consumer switch.

## Projected PS Quantity Equivalent

The authority target rows retain the candidate executable quantity generated by
the frontier candidate surface. Internal target-to-quantity consistency:

```text
490 / 490 accepted targets matched the accepted candidate increment quantity.
```

This is sufficient for dual-read compatibility. It is not sufficient for
production switch because existing production PS quantities differ on 374
accepted authority targets.

## Cash Winner / No Deployment

| Metric | Count |
| --- | ---: |
| Cash accepted/no-deployment days | 0 |
| Security accepted days | 50 |

Cash remained first-class and PASS on all days, but the current cardinal
contract selected at least one security target on every characterized day.

## Guardrails

| Guardrail | Count |
| --- | ---: |
| Cap blocked candidates | 279 |
| Cash blocked candidates | 426 |
| Safety blocked candidates | 0 |
| Risk Pacing blocked candidates | 0 |
| No-loss-averaging blocked candidates | 0 |

Guardrails were preserved. Safety and Risk Pacing did not fire in this sample;
they were not bypassed.

## Fail-Closed / Determinism / PIT

Actual-path checks:

- Authority generation deterministic rerun: PASS, 50 / 50 days.
- Stable payload hash verification: PASS, 50 / 50 days.
- Future/outcome forbidden key scan: PASS, 0 findings.
- Missing/ambiguous actual Cash evidence: none observed.
- Ambiguous actual cross-type top value: none observed.

Focused Phase32-AZ tests remain the direct evidence for fail-closed behavior
under injected missing Cash, missing campaign, and ambiguous cross-type value
conditions.

## Cardinal Value Semantic Judgment

The cardinal value contract is semantically useful for dual-read:

- It produces bounded deterministic values.
- It separates Cash from security candidates as a first-class competitor.
- It retains explainable components.
- It surfaces ADD target gaps missing from production.
- It preserves cap/Cash/Safety/Risk/no-loss guardrails.

However, it is only partially accepted for production migration:

- The current disabled contract accepts all feasible security targets whose
  value exceeds Cash optionality.
- This produces 490 accepted targets across 50 days and 374
  production-zero/authority-positive cases.
- The resulting projection is materially broader than current production and
  needs a consumer-switch allocation-budget / acceptance-boundary design before
  it can become active production authority.

## Production Boundary

No consumer switch was performed:

```text
production_consumer_enabled = false
production_consumer_count = 0
feeds_position_sizing = false
feeds_runtime_planning = false
feeds_pending = false
feeds_orders = false
feeds_execution = false
feeds_safety_authority = false
production_behavior_changed = false
```

No production artifacts or runtime state were changed.

## Final Judgments

```text
PHASE32_BA_AUTHORITY_ACTUAL_PATH_PASS = YES
PHASE32_BA_ACCEPTED_TARGET_GAP_OBSERVED = YES
PHASE32_BA_MULTI_LOT_ADD_TARGET_OBSERVED = YES
PHASE32_BA_PRODUCTION_ZERO_NEW_POSITIVE_GAP_CASES = 374
PHASE32_BA_PS_COMPATIBLE_PROJECTION = YES
PHASE32_BA_GUARDRAILS_PRESERVED = YES
PHASE32_BA_FAIL_CLOSED_PASS = YES
PHASE32_BA_CARDINAL_VALUE_SEMANTICALLY_ACCEPTED = PARTIAL
PHASE32_BA_PRODUCTION_CONSUMER_ENABLED = NO
PHASE32_BA_PRODUCTION_BEHAVIOR_CHANGED = NO
PHASE32_BA_CONSUMER_SWITCH_READY = PARTIAL
PHASE32_BA_LONG_RUN_CONTINUE = YES
PHASE32_BA_NEXT_STEP = Add a consumer-switch readiness design/repair that constrains accepted target-gap breadth with an explicit PC-owned allocation budget and acceptance boundary, then rerun READ-ONLY dual-read before enabling any production consumer.
```
