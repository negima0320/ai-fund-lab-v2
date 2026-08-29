# Phase32-BI Post-BG First-Day Zero-Buy Regression Audit

## Executive Summary

Phase32-BI could not complete the requested actual-path blocker trace because
the target run evidence is not present in the local workspace.

Requested run:

```text
runtime-test-historical-extended-smoke-20260828T153014206482Z
```

Expected evidence path:

```text
reports/runtime_tests/runs/runtime-test-historical-extended-smoke-20260828T153014206482Z
```

Local result:

```text
MISSING
```

The first-day zero-buy claim therefore cannot be attributed to Candidate, PC,
the marginal capital authority, BF aggregation, the active consumer switch,
Position Sizing, Runtime Planning, Pending, Order, or Fill from local artifact
evidence. No Production code, config, threshold, model, runtime state, replay,
resume, fresh-run, or backtest was used.

## Run Identity

| Field | Value |
| --- | --- |
| Target run id | `runtime-test-historical-extended-smoke-20260828T153014206482Z` |
| Target date | `2022-10-03` |
| Requested mode | READ-ONLY artifact audit |
| Local expected run directory | `reports/runtime_tests/runs/runtime-test-historical-extended-smoke-20260828T153014206482Z` |
| Local directory status | `MISSING` |
| Audit status | `BLOCKED_BY_MISSING_RUN_ARTIFACTS` |

## Required Inputs Reviewed

The following handoff/design reports were available and read:

| Report | Local status |
| --- | --- |
| `docs/phase_reports/phase32_bg_explicit_production_consumer_switch_implementation.md` | Present |
| `docs/phase_reports/phase32_bf_pc_to_ps_consumer_switch_boundary_validator.md` | Present |
| `docs/phase_reports/phase32_bc_budget_bounded_frontier_acceptance_implementation.md` | Present by reference from BF/BG context |

Relevant inherited BG contract:

```text
PM / candidate evidence
-> canonical_marginal_capital_frontier_authority.v1
-> pc_to_ps_consumer_switch_boundary.aggregated_ps_targets[]
-> Position Sizing
-> Runtime
```

BG explicitly makes BF aggregated targets the switched target authority:

```text
target_authority_source = BF_AGGREGATED_PS_BOUNDARY_ONLY
production_consumers = [strategy.position_sizing]
production_consumer_count = 1
shadow_frontier_production_consumer_count = 0
legacy_target_gap_fallback_allowed = false
legacy_zero_fallback_allowed = false
```

## Local Evidence Inventory

The local run inventory under `reports/runtime_tests/runs` contains only:

```text
reports/runtime_tests/runs/runtime-test-historical-extended-smoke-20260828T000823285458Z
```

The requested BI run id was not found under:

```text
reports/runtime_tests/runs
```

Repository text search for:

```text
runtime-test-historical-extended-smoke-20260828T153014206482Z
```

returned no local report or artifact references.

A broader read-only name search under `/Users/negishi` also produced no match
before being stopped after it only traversed unrelated/private macOS locations
and emitted permission-denied messages. No target evidence path was discovered.

## Missing Day-0 Artifacts

Because the target run directory is absent, all requested first-day trace
artifacts are unavailable locally:

| Stage | Required artifact | Local status |
| --- | --- | --- |
| Candidate / strategy evidence | `daily/2022-10-03/strategy/*` | Missing |
| Portfolio Construction | `daily/2022-10-03/strategy/portfolio_construction.json` | Missing |
| Marginal capital authority | `daily/2022-10-03/strategy/marginal_capital_frontier_authority.json` | Missing |
| Allocation budget | authority / policy payloads for `2022-10-03` | Missing |
| BF aggregated targets | `pc_to_ps_consumer_switch_boundary.aggregated_ps_targets[]` | Missing |
| Active consumer switch | embedded authority in PC artifact | Missing |
| Position Sizing | `daily/2022-10-03/strategy/position_sizing.json` | Missing |
| Runtime Planning | `daily/2022-10-03/strategy/runtime_planning.json` | Missing |
| Pending generation | `daily/2022-10-03/morning/pending_generation_evidence.json` | Missing |
| Submit / order authority | `daily/2022-10-03/execution/submitted_order_authority.json` | Missing |
| Fill evidence | `daily/2022-10-03/execution/fills.json` | Missing |
| Day completion | `daily/2022-10-03/day_completion/day_completion_evidence.json` | Missing |

## Requested Trace Status

| Boundary | Evidence status | Finding |
| --- | --- | --- |
| Candidate -> PC | Missing | Cannot determine whether candidates existed or were admitted. |
| PC -> marginal capital authority | Missing | Cannot determine authority status or target count. |
| Authority -> allocation budget | Missing | Cannot determine budget source, budget amount, or REVIEW_REQUIRED state. |
| Authority -> BF targets | Missing | Cannot determine whether BF aggregated targets existed. |
| BF targets -> active switch | Missing | Cannot determine whether BG switch was active in this run. |
| Active switch -> PS | Missing | Cannot determine whether PS consumed the new authority. |
| PS -> Runtime Planning | Missing | Cannot determine first zero quantity boundary. |
| Runtime Planning -> Pending/Order/Fill | Missing | Cannot determine whether Runtime dropped orders or received zero from PS. |

## Exact Blocker

The first locally provable blocker is outside the trading pipeline:

```text
FIRST_BLOCKER = target run artifact directory missing from local workspace
```

This is not evidence that the BG switch did or did not cause the first-day
zero-buy regression. It means the requested actual-path audit cannot be
performed from the current local evidence set.

## BG Causality

BG is a plausible causal boundary because it changed Production behavior by
switching Position Sizing to consume BF aggregated target rows when a valid
active authority is embedded in Portfolio Construction.

However, BI requires artifact proof for one of these exact cases:

| Possible cause | Evidence required | Local result |
| --- | --- | --- |
| Authority produced zero accepted targets | `marginal_capital_frontier_authority.json` | Missing |
| BF boundary produced zero rows | `pc_to_ps_consumer_switch_boundary` | Missing |
| Active switch invalid / REVIEW_REQUIRED | embedded authority in `portfolio_construction.json` | Missing |
| PS did not consume authority | `position_sizing.json` switch-consumption fields | Missing |
| PS consumed authority but rounded all quantities to zero | PS sizing rows and reasons | Missing |
| Runtime dropped nonzero PS orders | `runtime_planning.json` and pending/order artifacts | Missing |
| Submit/fill failed after nonzero pending | submit/execution artifacts | Missing |

Therefore:

```text
PHASE32_BI_BG_SWITCH_ROOT_CAUSE = UNRESOLVED
```

## Comparison With Prior 2022-10-03

The earlier local run:

```text
runtime-test-historical-extended-smoke-20260828T000823285458Z
```

is present and was used by earlier AW/AX/BA/BD/BF reports. It is not a
substitute for the missing BI run. Because the BI target artifacts are absent,
this audit does not compare old and new day-0 quantities; doing so would risk
attributing a regression without actual-path evidence.

## State / Mutation

No runtime state was modified. No resume, replay, fresh-run, backtest, or
production command was executed. The only file created by this task is this
report.

## Repair Readiness

Production repair is not justified from the local evidence alone. The missing
run artifacts must be synced or provided first. Once the target run is present,
the shortest complete audit path is:

1. Read `daily/2022-10-03/strategy/marginal_capital_frontier_authority.json`.
2. Confirm `authority_result`, allocation budget status, accepted targets, and
   BF `aggregated_ps_targets`.
3. Read `daily/2022-10-03/strategy/portfolio_construction.json` and confirm
   active BG switch embedding.
4. Read `daily/2022-10-03/strategy/position_sizing.json` and identify whether
   PS consumed the authority and where quantity became zero.
5. Read Runtime/Pending/Submit/Fill artifacts only if PS produced nonzero
   quantity.

## Final Judgments

```text
PHASE32_BI_ZERO_BUY_REGRESSION = UNRESOLVED
PHASE32_BI_AUTHORITY_TARGETS_EXIST = UNRESOLVED
PHASE32_BI_BF_TARGETS_EXIST = UNRESOLVED
PHASE32_BI_PS_CONSUMED_NEW_AUTHORITY = UNRESOLVED
PHASE32_BI_FIRST_ZERO_QUANTITY_STAGE = UNRESOLVED_MISSING_TARGET_RUN_ARTIFACTS
PHASE32_BI_EXACT_BLOCKER = TARGET_RUN_ARTIFACT_DIRECTORY_MISSING: reports/runtime_tests/runs/runtime-test-historical-extended-smoke-20260828T153014206482Z
PHASE32_BI_BG_SWITCH_ROOT_CAUSE = UNRESOLVED
PHASE32_BI_PRODUCTION_REPAIR_REQUIRED = UNRESOLVED
PHASE32_BI_LONGER_VALIDATION_READY = NO
PHASE32_BI_NEXT_STEP = Sync or provide runtime-test-historical-extended-smoke-20260828T153014206482Z artifacts, then rerun the READ-ONLY BI artifact trace without executing fresh-run/resume/replay/backtest.
```
