# Phase32-AV - Broad Shadow Frontier Characterization

## Executive Summary

Phase32-AV could not complete broad actual-artifact materialization because the
target long-run artifact directory is not present in this workspace.

Target run requested:

```text
runtime-test-historical-extended-smoke-20260827T093649849074Z
```

Expected path:

```text
reports/runtime_tests/runs/runtime-test-historical-extended-smoke-20260827T093649849074Z
```

Observed:

```text
target run directory missing
```

Therefore no AV-specific broad materialization, candidate counts, winner counts,
cash-source acceptance counts, ADD trace, or production/shadow divergence counts
were generated. No production code, config, threshold, model, Runtime state,
fresh-run, resume, replay, or backtest was changed or executed.

## Required Inputs Read

Read:

- `docs/phase_reports/phase32_au_shadow_frontier_cash_source_resolver_repair.md`
- `docs/phase_reports/phase32_at_shadow_marginal_capital_frontier_artifact_only_characterization.md`
- `docs/phase_reports/phase32_aq_add_scarcity_marginal_capital_value_target_gap_root_architecture_audit.md`

These prior reports establish:

- AU implemented the shadow-only Cash resolver and focused regressions passed.
- AT previously characterized the same named run in memory when that run was
  available and showed the shadow frontier was semantically useful.
- AQ established that production ADD scarcity is primarily a Portfolio
  Construction target-gap / marginal-capital-value architecture gap, not a
  Position Sizing lot-rounding defect.

Those inherited facts are not a substitute for AV acceptance, because AV asks
for post-AU broad materialization over the actual run artifacts.

## Target Run Availability Check

Commands executed:

```text
test -d reports/runtime_tests/runs/runtime-test-historical-extended-smoke-20260827T093649849074Z
find reports -maxdepth 4 -type d -name 'runtime-test-historical-extended-smoke-20260827T093649849074Z'
find . -maxdepth 5 -type d -name 'runtime-test-historical-extended-smoke-20260827T093649849074Z'
find reports -maxdepth 5 -type f -name '*093649849074Z*'
```

Result:

```text
No matching target run directory or run artifact file found.
```

`reports/runtime_tests` exists, but the available local tree contains
`system_status` and older `fresh_runs` paths, not the requested
`reports/runtime_tests/runs/{run_id}` directory.

## Materialization Status

AV materialization status:

```text
NOT_RUN_TARGET_ARTIFACTS_MISSING
```

The shadow day materializer requires at least per-day artifacts such as:

```text
daily/{date}/strategy/portfolio_construction.json
daily/{date}/strategy/position_sizing.json
daily/{date}/strategy/portfolio_policy.json
daily/{date}/current_valuation_refresh/valuation_projection.json
```

Because the run directory is absent, no `diagnostic_shadow` artifact was written
and no existing run state was mutated.

## Mandatory AV Aggregates

No AV-specific aggregate can be measured from absent artifacts.

| Required aggregate | AV result |
| --- | --- |
| candidate counts by NEW / REENTRY / ADD / Cash | `NOT_MEASURED_TARGET_RUN_MISSING` |
| winner counts by NEW / REENTRY / ADD / Cash | `NOT_MEASURED_TARGET_RUN_MISSING` |
| runner-up counts by NEW / REENTRY / ADD / Cash | `NOT_MEASURED_TARGET_RUN_MISSING` |
| ADD next-lot #1/#2/#3+ counts | `NOT_MEASURED_TARGET_RUN_MISSING` |
| multi-lot shadow projection counts | `NOT_MEASURED_TARGET_RUN_MISSING` |
| Cash source status / lineage / REVIEW_REQUIRED counts | `NOT_MEASURED_TARGET_RUN_MISSING` |
| cap / Cash / Safety / Risk Pacing blocks | `NOT_MEASURED_TARGET_RUN_MISSING` |
| production target-gap=0 with shadow ADD candidate days | `NOT_MEASURED_TARGET_RUN_MISSING` |
| ADD winner days | `NOT_MEASURED_TARGET_RUN_MISSING` |
| ADD loss primary reason classification | `NOT_MEASURED_TARGET_RUN_MISSING` |
| released capital shadow destination | `NOT_MEASURED_TARGET_RUN_MISSING` |
| high-position-count / sideways behavior | `NOT_MEASURED_TARGET_RUN_MISSING` |
| persistent ADD campaign trace, including 94320 | `NOT_MEASURED_TARGET_RUN_MISSING` |

## Inherited AT Reference Only

When the same named run was available during Phase32-AT, AT reported:

| Metric | AT value |
| --- | ---: |
| in-memory shadow rows characterized | 15,081 |
| days characterized | 315 |
| ADD next-lot candidates | 1,047 |
| shadow ADD winner days | 5 |
| shadow NEW winner days | 145 |
| shadow REENTRY winner days | 165 |
| shadow Cash winner days | 0 |

This is included only as prior context. It is not AV post-AU actual-path
acceptance evidence because AU specifically repaired the materializer Cash
source resolver after AT.

## Production Boundary

No production path was changed or executed:

- no production target weight change;
- no Position Sizing change;
- no Runtime Planning change;
- no Pending / Order / Execution change;
- no Safety / REDUCE / EXIT change;
- no Cash policy or threshold change;
- no fresh-run, resume, replay, or backtest.

## Defect / No-Defect Judgment

AV is blocked by missing evidence, not by a known AU resolver defect.

The AU focused regression suite already verified:

- portfolio_policy Cash resolves;
- valuation fallback resolves;
- missing / conflicting Cash fails closed as `REVIEW_REQUIRED`;
- broad-day fixture materialization avoids false insufficient-cash collapse;
- deterministic rerun;
- production consumer count remains zero.

However, AV requires the actual long-run artifacts. Since those artifacts are not
available locally, broad acceptance cannot be granted.

## Recommendation

Provide or restore:

```text
reports/runtime_tests/runs/runtime-test-historical-extended-smoke-20260827T093649849074Z
```

Then rerun AV as artifact-only shadow materialization / characterization. The
next pass should use the repaired AU materializer and compute the required broad
counts directly from the actual day artifacts.

## Final Judgments

PHASE32_AV_AU_ACTUAL_PATH_ACCEPTED = NO

PHASE32_AV_CASH_RESOLVER_BROAD_PASS = NO

PHASE32_AV_MULTI_LOT_ADD_SURFACE_CONFIRMED = NO

PHASE32_AV_ADD_WINNER_DAYS = NOT_MEASURED_TARGET_RUN_MISSING

PHASE32_AV_NEW_WINNER_DAYS = NOT_MEASURED_TARGET_RUN_MISSING

PHASE32_AV_REENTRY_WINNER_DAYS = NOT_MEASURED_TARGET_RUN_MISSING

PHASE32_AV_CASH_WINNER_DAYS = NOT_MEASURED_TARGET_RUN_MISSING

PHASE32_AV_ADD_LOW_WIN_RATE_PRIMARY_CAUSE = UNRESOLVED_TARGET_RUN_MISSING

PHASE32_AV_CROSS_TYPE_COMPARISON_SEMANTICALLY_FAIR = UNRESOLVED

PHASE32_AV_STRUCTURED_ORDERING_BIAS = UNRESOLVED

PHASE32_AV_GUARDRAILS_PRESERVED = UNRESOLVED

PHASE32_AV_PRODUCTION_ACTIVATION_READY = NO

PHASE32_AV_LONG_RUN_CONTINUE = NO

PHASE32_AV_NEXT_STEP = Restore the target run artifacts, then rerun Phase32-AV broad shadow materialization and characterization without fresh-run/resume/replay/backtest.
