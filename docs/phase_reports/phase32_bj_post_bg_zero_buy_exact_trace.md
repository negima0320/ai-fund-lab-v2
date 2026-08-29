# Phase32-BJ Post-BG Zero-Buy Evidence Recovery / Exact Trace

## Executive Summary

Phase32-BJ attempted to recover and trace the Post-BG first-day zero-buy
evidence for:

```text
runtime-test-historical-extended-smoke-20260828T153014206482Z
```

The target run artifacts are still not visible in the local workspace. The
expected run directory is absent:

```text
reports/runtime_tests/runs/runtime-test-historical-extended-smoke-20260828T153014206482Z
```

Because the actual 2022-10-03 artifacts are unavailable, this report cannot
truthfully identify the first quantity-zero boundary, exact reason code,
REVIEW_REQUIRED state, legacy fallback state, or whether the zero-buy was a BG
regression versus a valid Cash/no-deployment decision.

No Production code, config, threshold, model, runtime state, fresh-run, resume,
replay, or backtest was changed or executed.

## Run Identity

| Field | Value |
| --- | --- |
| Target run id | `runtime-test-historical-extended-smoke-20260828T153014206482Z` |
| Target day | `2022-10-03` |
| Requested audit | Candidate -> PC -> authority -> budget -> BF -> BG switch -> PS -> Runtime -> Pending/Fill |
| Expected evidence path | `reports/runtime_tests/runs/runtime-test-historical-extended-smoke-20260828T153014206482Z` |
| Local evidence status | `MISSING` |
| Audit result | `BLOCKED_BY_MISSING_TARGET_RUN_ARTIFACTS` |

## Required Inputs

Read:

| Input | Status |
| --- | --- |
| `docs/phase_reports/phase32_bi_post_bg_first_day_zero_buy_regression_audit.md` | Present |
| `docs/phase_reports/phase32_bg_explicit_production_consumer_switch_implementation.md` | Present |

Inherited BG production path:

```text
PM / candidate evidence
-> canonical_marginal_capital_frontier_authority.v1
-> pc_to_ps_consumer_switch_boundary.aggregated_ps_targets[]
-> Position Sizing
-> Runtime
```

BG intended switch contract:

```text
target_authority_source = BF_AGGREGATED_PS_BOUNDARY_ONLY
production_consumers = [strategy.position_sizing]
production_consumer_count = 1
shadow_frontier_production_consumer_count = 0
legacy_target_gap_fallback_allowed = false
legacy_zero_fallback_allowed = false
```

## Evidence Recovery Attempt

Local checks performed:

| Check | Result |
| --- | --- |
| `test -d reports/runtime_tests/runs/runtime-test-historical-extended-smoke-20260828T153014206482Z` | Not found |
| `find reports/runtime_tests/runs -maxdepth 1 -type d` | Only `runtime-test-historical-extended-smoke-20260828T000823285458Z` found |
| `find /Users/negishi/work -type d -name runtime-test-historical-extended-smoke-20260828T153014206482Z` | No match |
| `find /private/tmp ... -name runtime-test-historical-extended-smoke-20260828T153014206482Z` | No match |
| `rg -n "153014206482Z\|20260828T153014"` | Only prior BI report references found |
| Downloads/Desktop/Documents name search | No target run match in permitted locations; Documents was not readable by the sandbox |

The only local runtime run under the expected run root remains:

```text
reports/runtime_tests/runs/runtime-test-historical-extended-smoke-20260828T000823285458Z
```

## Requested Trace Status

| Stage | Required evidence | Status | Finding |
| --- | --- | --- | --- |
| Candidate | `daily/2022-10-03/strategy/*`, ranking / buy quality / trace artifacts | Missing | Candidate count and admission cannot be established. |
| PC | `daily/2022-10-03/strategy/portfolio_construction.json` | Missing | PC output and selected targets cannot be established. |
| Marginal capital authority | `daily/2022-10-03/strategy/marginal_capital_frontier_authority.json` | Missing | Accepted targets and authority status cannot be established. |
| Budget acceptance | authority budget fields / portfolio policy / valuation projection | Missing | Budget source, budget amount, and budget stop reason cannot be established. |
| BF aggregated targets | `pc_to_ps_consumer_switch_boundary.aggregated_ps_targets[]` | Missing | BF target count cannot be established. |
| BG consumer switch | embedded active authority in PC | Missing | Switch active status cannot be established. |
| Position Sizing | `daily/2022-10-03/strategy/position_sizing.json` | Missing | PS consumer status and first zero quantity reason cannot be established. |
| Runtime | `daily/2022-10-03/strategy/runtime_planning.json` | Missing | Runtime order mapping cannot be established. |
| Pending / Fill | `morning/pending_generation_evidence.json`, `execution/submitted_order_authority.json`, `execution/fills.json` | Missing | Pending/order/fill status cannot be established. |

## Quantitative Trace

The requested quantities cannot be measured from local artifacts:

| Metric | Value |
| --- | --- |
| Authority accepted targets | `UNRESOLVED_MISSING_ARTIFACT` |
| BF aggregated targets | `UNRESOLVED_MISSING_ARTIFACT` |
| Switch active status | `UNRESOLVED_MISSING_ARTIFACT` |
| PS consumed BG authority | `UNRESOLVED_MISSING_ARTIFACT` |
| First quantity-zero boundary | `UNRESOLVED_MISSING_ARTIFACT` |
| Exact reason code | `UNRESOLVED_MISSING_ARTIFACT` |
| REVIEW_REQUIRED present | `UNRESOLVED_MISSING_ARTIFACT` |
| Legacy fallback used | `UNRESOLVED_MISSING_ARTIFACT` |

## BG Regression vs Cash Decision

The classification remains unresolved. The missing target run artifacts prevent
distinguishing among the material possibilities:

| Hypothesis | Evidence needed | Current status |
| --- | --- | --- |
| BG regression: authority not materialized/embedded | `portfolio_construction.json`, `marginal_capital_frontier_authority.json` | Missing |
| BG regression: BF rows exist but PS did not consume | `position_sizing.json` switch-consumption fields | Missing |
| BG regression: PS consumed rows but zeroed quantities | PS row-level quantity and reason fields | Missing |
| Valid Cash/no-deployment decision | authority winner/disposition and explicit Cash allocation fields | Missing |
| Upstream no-candidate/no-budget condition | strategy, PC, budget, and policy artifacts | Missing |
| Runtime/Pending dropped nonzero PS quantity | Runtime/Pending/Submit/Fill artifacts | Missing |

Therefore this audit does not assert BG root cause and does not justify a
production repair from evidence.

## Exact Root Cause

The only exact blocker observed in this local audit is evidence access:

```text
TARGET_RUN_ARTIFACT_DIRECTORY_MISSING
```

Missing path:

```text
reports/runtime_tests/runs/runtime-test-historical-extended-smoke-20260828T153014206482Z
```

## Required Evidence to Complete BJ

Place or sync the target run at:

```text
reports/runtime_tests/runs/runtime-test-historical-extended-smoke-20260828T153014206482Z
```

Minimum files needed for the exact trace:

```text
daily/2022-10-03/strategy/portfolio_construction.json
daily/2022-10-03/strategy/marginal_capital_frontier_authority.json
daily/2022-10-03/strategy/position_sizing.json
daily/2022-10-03/strategy/runtime_planning.json
daily/2022-10-03/morning/planning_evidence.json
daily/2022-10-03/morning/pending_generation_evidence.json
daily/2022-10-03/execution/submitted_order_authority.json
daily/2022-10-03/execution/fills.json
daily/2022-10-03/current_valuation_refresh/valuation_projection.json
daily/2022-10-03/strategy/portfolio_policy.json
```

Once those are present, no fresh-run/resume/replay/backtest is needed; the
requested exact trace can be completed from artifacts only.

## Final Judgments

```text
PHASE32_BJ_ZERO_BUY_REGRESSION = UNRESOLVED
PHASE32_BJ_AUTHORITY_TARGET_COUNT = UNRESOLVED_MISSING_ARTIFACT
PHASE32_BJ_BF_TARGET_COUNT = UNRESOLVED_MISSING_ARTIFACT
PHASE32_BJ_PS_CONSUMED_BG_AUTHORITY = UNRESOLVED
PHASE32_BJ_FIRST_ZERO_STAGE = UNRESOLVED_MISSING_TARGET_RUN_ARTIFACTS
PHASE32_BJ_EXACT_ROOT_CAUSE = TARGET_RUN_ARTIFACT_DIRECTORY_MISSING: reports/runtime_tests/runs/runtime-test-historical-extended-smoke-20260828T153014206482Z
PHASE32_BJ_BG_REPAIR_REQUIRED = UNRESOLVED
PHASE32_BJ_LONGER_VALIDATION_READY = NO
PHASE32_BJ_NEXT_STEP = Sync the target run artifacts into reports/runtime_tests/runs/runtime-test-historical-extended-smoke-20260828T153014206482Z, then rerun the READ-ONLY exact trace.
```
