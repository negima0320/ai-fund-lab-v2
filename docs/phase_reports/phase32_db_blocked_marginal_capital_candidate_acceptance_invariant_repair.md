# Phase32-DB - Blocked Marginal Capital Candidate Acceptance Invariant Repair

## Executive Summary

Implemented a narrow repair for the Phase32-DA production authority inconsistency where `2022-10-21` `94320` ADD lot #1/#2/#3 were accepted despite blocked marginal-capital evidence.

The repair preserves ADD admission as a necessary-but-not-sufficient gate and adds a security-lot invariant before common frontier acceptance:

- `comparison_class = BLOCKED` cannot enter the acceptance pool.
- `marginal_capital_value_class = BLOCKED_OR_NOT_ELIGIBLE` cannot enter the acceptance pool.
- `desirability.status != PASS` cannot enter the acceptance pool.
- Cash remains separately handled.

Also added defensive validation at BF aggregation and Runtime submit feasibility. No thresholds, value formula, PM, PS arithmetic, Runtime mapping, REDUCE/EXIT, Cash, Risk Pacing, or ADD policy tuning were changed.

## Inherited Defect

From Phase32-DA:

| Boundary | Observed defect |
| --- | --- |
| ADD admission | `final_add_eligibility = PASS` |
| Capital comparison | `comparison_class = BLOCKED`, `marginal_capital_value_class = BLOCKED_OR_NOT_ELIGIBLE` |
| Desirability | `desirability.status = REVIEW_REQUIRED` |
| Reason | `opportunity_quality_add_hard_block` |
| Frontier | `ACCEPTED_INCREMENTAL_TARGET` |
| BF / PS / Runtime | +300 BUY_ADD reached fill |

Root cause was that `canonical_marginal_capital_frontier_authority.v1` treated ADD admission PASS plus positive bounded value as enough to accept the lots, while not honoring blocked comparison/desirability state.

## Implementation

Changed production files:

- `src/ai_fund_lab_v2/strategy/marginal_capital_frontier_authority.py`
- `src/ai_fund_lab_v2/runtime_v2/planning_submit_feasibility.py`

Changed tests:

- `tests/strategy/test_phase32_az_marginal_capital_frontier_authority.py`
- `tests/runtime_v2/test_phase24_ht_planning_submit_feasibility.py`

Updated Architecture SoT:

- `docs/02_architecture/portfolio_construction_and_position_sizing_contract.md`

### PC Frontier Guard

Added a shared security candidate validation helper used by:

- `_authority_candidate()`
- `_bounded_value()`
- `_available()`

For security lots, blocked/non-comparable evidence now produces:

```text
capital_value_status = NOT_COMPARABLE
authority_disposition = INELIGIBLE_MARGINAL_CAPITAL_VALUE_BLOCKED
```

for blocked marginal-capital classes. Desirability non-PASS without an explicit blocked class is fail-closed as `REVIEW_REQUIRED`.

### BF Defensive Invariant

`build_pc_to_ps_switch_boundary_validation()` now checks every accepted target's `accepted_frontier_candidate_ids` against the source `frontier_candidates`.

If a source candidate is blocked, non-eligible, or desirability non-PASS, BF does not aggregate positive PS targets and emits `REVIEW_REQUIRED`.

This is an authority consistency check only; BF does not recompute capital value.

### Runtime / Submit Defensive Invariant

`evaluate_buy_item_submit_feasibility()` now rejects positive BUY items with:

```text
marginal_capital_value_class = BLOCKED_OR_NOT_ELIGIBLE
```

unless an explicit diagnostic-only authority is present. The resulting review reason is:

```text
blocked_marginal_capital_value_positive_buy_quantity
```

Runtime/submit still does not recompute capital value.

## Focused Reproduction

In-memory rebuild from existing `2022-10-21` artifacts:

| 94320 ADD lot | ADD admission | comparison | capital value status | authority disposition |
| ---: | --- | --- | --- | --- |
| 1 | `PASS` | `BLOCKED` | `NOT_COMPARABLE` | `INELIGIBLE_MARGINAL_CAPITAL_VALUE_BLOCKED` |
| 2 | `PASS` | `BLOCKED` | `NOT_COMPARABLE` | `INELIGIBLE_MARGINAL_CAPITAL_VALUE_BLOCKED` |
| 3 | `PASS` | `BLOCKED` | `NOT_COMPARABLE` | `INELIGIBLE_MARGINAL_CAPITAL_VALUE_BLOCKED` |

Result:

- `94320 accepted target count = 0`
- `94320 BF target count = 0`
- BF boundary remains `PASS` because blocked candidates are simply unavailable and no poisoned target remains.

## Positive Controls

In-memory rebuilds from existing run artifacts preserved accepted ADD controls:

| Date | Symbol | Accepted ADD lots after repair |
| --- | --- | ---: |
| 2022-10-06 | 94340 | 3 |
| 2022-10-11 | 94340 | 3 |
| 2022-10-12 | 94320 | 3 |
| 2022-10-13 | 94340 | 1 |
| 2022-10-28 | 94320 | 3 |
| 2022-11-01 | 94320 | 1 |

These controls remained `COMPARABLE_MARGINAL` with `capital_value_status = PASS` where accepted.

## Regression Coverage

Added focused regressions for:

- `2022-10-21`-shaped 94320 blocked ADD with ADD admission PASS cannot be accepted.
- BLOCKED NEW cannot be accepted.
- BLOCKED REENTRY cannot be accepted.
- Desirability `REVIEW_REQUIRED` cannot be accepted.
- Valid comparable candidates still compete with Cash.
- BF rejects a poisoned accepted-source row.
- Runtime submit feasibility rejects positive BUY with blocked marginal-capital class.

Verification:

```text
python3 -m pytest tests/strategy/test_phase32_az_marginal_capital_frontier_authority.py tests/runtime_v2/test_phase24_ht_planning_submit_feasibility.py -q
101 passed in 2.11s
```

Compile check:

```text
PYTHONPYCACHEPREFIX=/private/tmp/ai-fund-lab-v2-pycache python3 -m py_compile src/ai_fund_lab_v2/strategy/marginal_capital_frontier_authority.py src/ai_fund_lab_v2/runtime_v2/planning_submit_feasibility.py
PASS
```

Initial `python3 -m py_compile` without `PYTHONPYCACHEPREFIX` failed only because Python attempted to write bytecode under `~/Library/Caches`, outside the writable sandbox.

## Preservation Notes

Preserved:

- ADD admission PASS remains necessary but not sufficient.
- NEW/REENTRY comparison path remains common-frontier based.
- Valid ADD controls remain accepted.
- Cash competition and budget conservation remain unchanged.
- Strategy/Safety caps and Risk Pacing remain unchanged.
- BF-only authority and legacy fallback zero remain unchanged.
- PS arithmetic and Runtime mapping remain unchanged.
- PIT flags remain explicit in the touched authority paths.

No fresh-run, resume, replay, backtest, threshold tuning, value-formula change, or historical outcome selection was performed.

## Final Judgments

PHASE32_DB_BLOCKED_FRONTIER_ACCEPTANCE_ZERO = YES

PHASE32_DB_DESIRABILITY_NONPASS_ACCEPTANCE_ZERO = YES

PHASE32_DB_94320_2022_10_21_ADD_BLOCKED = YES

PHASE32_DB_VALID_ADD_CONTROLS_PRESERVED = YES

PHASE32_DB_NEW_REENTRY_NON_REGRESSION = PASS

PHASE32_DB_BF_DEFENSIVE_INVARIANT = YES

PHASE32_DB_RUNTIME_DEFENSIVE_INVARIANT = YES

PHASE32_DB_PIT_CONTRACT = PASS

PHASE32_DB_REGRESSION_STATUS = PASS

PHASE32_DB_FRESH_VALIDATION_READY = YES

PHASE32_DB_NEXT_STEP = User-operated short fresh validation from a clean Post-DB run, with explicit check that `2022-10-21`-style blocked marginal-capital classes cannot reach BF/PS/Runtime positive BUY paths.
