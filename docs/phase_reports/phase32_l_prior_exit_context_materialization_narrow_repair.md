# Phase32-L - Prior-Exit Context Materialization Narrow Repair

## Defect Inheritance

Phase32-L inherits the Phase32-K mandatory defect:

```text
PM SELL/EXIT decision_reason / reason_codes exist upstream
-> execution / realized slice retains only bare EXIT
-> prior-exit state materializes prior_exit_reason = EXIT
-> PC classifies previous_exit_reason_class = GENERIC
-> semantic REENTRY fails closed
```

This repair targets only the prior-exit context materialization defect. It does
not loosen re-entry thresholds, alter Cash preference, change PC/MCC
competition, change Risk Pacing, change PM/PS/Runtime authority, or claim to
solve the Phase32 excess-Cash problem.

## Repair Design

Short read-only design audit before implementation:

- PM is the authority for why a position action occurred.
- Execution is the authority for what actually filled and whether the campaign closed.
- Canonical join identity is exact PM decision identity:
  `execution.source_decision_id == pm.pm_decision_id / pm.decision_id / pm.source_pm_decision_id`.
- Symbol, PM business date, execution business date, and campaign identity are validation keys.
- Symbol/date-only join is not used.
- Same-day or future PM evidence relative to the re-entry decision date is excluded.
- Partial REDUCE does not create a prior exit while remaining campaign quantity is positive.
- When multiple SELL decisions occur, only the PM evidence attached to the final execution-proven close is materialized as prior-exit reason.
- If detailed PM evidence is absent, mismatched, future-dated, wrong-symbol, or wrong-campaign, existing generic fallback remains.

## Authority Selection

Implemented authority split:

- `STRICT_PRIOR_PM_DECISION_EVIDENCE`: semantic authority for `prior_exit_reason` and `prior_exit_reason_codes`.
- `persistent_ledger_execution_history`: execution/closure authority for the fact that a strict-prior campaign closed.
- `EXECUTION_ROW_FALLBACK`: preserved fallback for missing detailed PM context.

The bridge reads PM reason evidence from run-scoped daily artifacts and runtime PM state paths, but it materializes that evidence only if an executed strict-prior close references the same PM decision ID and passes validation.

## Join Identity

The implemented join is:

```text
execution.source_decision_id
  == pm.pm_decision_id | pm.decision_id | pm.source_pm_decision_id
```

Validation:

- PM `business_date` must equal the closing execution business date.
- PM `symbol` must equal execution symbol.
- If both PM and execution campaign IDs exist, they must match.
- If PM campaign ID exists and the resolved campaign-close ID exists, they must match.
- PM action must be `EXIT` or `REDUCE`.
- PM reason must contain `decision_reason` / `reason` / `dominant_cause` or reason-code evidence.

## PIT Proof

`_supply_prior_exit_state` now passes `run_dir` into the prior-exit bridge and records:

- `pm_reason_temporal_selection_rule = pm_decision_business_date_strictly_less_than_decision_business_date`
- `pm_reason_join_identity = execution.source_decision_id == pm.pm_decision_id/decision_id with symbol/date/campaign validation`
- `future_or_same_day_exit_used = False`
- `post_hoc_pnl_input_used = False`

The helper scans only PM sources whose date is strictly less than the re-entry decision date. The execution close itself must also be strict-prior.

## REDUCE / EXIT Semantics

Partial REDUCE is preserved as not-a-prior-exit. The resolver only writes prior-exit state when cumulative strict-prior SELL quantity closes the campaign quantity to zero. If a REDUCE execution is the final close, its PM reason may be used; if it is only partial, no prior-exit row is produced.

For multiple sell decisions in one campaign, the final close execution determines the prior-exit reason authority. Earlier partial reduce reason evidence is not promoted as the close reason.

## Implementation

Files changed:

- `src/ai_fund_lab_v2/strategy/shadow_runtime.py`
  - Added strict-prior PM exit reason evidence indexing.
  - Passed `run_dir` into prior-exit supply.
  - Extended `_resolve_prior_closed_campaigns_from_executions` to accept optional PM reason evidence.
  - Materializes PM reason/codes only on exact executed-close identity.
  - Preserves generic execution fallback.

- `tests/runtime_v2/test_phase22_p_strategy_shadow_wiring.py`
  - Added focused Phase32-L bridge regression tests.

- `tests/strategy/test_phase22_e_portfolio_construction.py`
  - Added explicit assertion that the existing semantic re-entry positive control classifies detailed trend/edge-break exit context as `TREND_MOMENTUM`.

- `docs/02_architecture/dual_path_market_quality_and_capital_competition_contract.md`
  - Added permanent SoT rule that prior-exit semantic authority comes from PM decision evidence attached to an executed close, not from bare execution action labels.

## Positive Controls

Added focused positive coverage:

- Executed strict-prior EXIT with matching PM `pm_decision_id`, symbol, date, and campaign materializes:
  - `prior_exit_reason = trend_and_opportunity_broken`
  - `prior_exit_reason_codes = ["trend_and_opportunity_broken"]`
  - `prior_exit_reason_authority = STRICT_PRIOR_PM_DECISION_EVIDENCE`
- Existing PC semantic re-entry positive control now asserts `previous_exit_reason_class = TREND_MOMENTUM`.

This proves the 2024-01-31 / 83060 semantic shape can receive non-GENERIC prior-exit context in a synthetic PIT-safe fixture. The test does not assert unconditional BUY behavior.

## Negative Controls

Added focused negative coverage:

- No detailed PM reason -> generic fallback preserved.
- PM SELL/REDUCE evidence without executed close -> no prior-exit state.
- Partial REDUCE with campaign still open -> no prior-exit state.
- Final close after prior partial REDUCE -> final close reason is used.
- Future-dated PM evidence relative to re-entry decision date -> ignored.
- Wrong-symbol PM evidence -> ignored.
- Wrong-campaign PM evidence -> ignored.

## Regression Results

Commands executed:

```bash
python3 -m pytest tests/runtime_v2/test_phase22_p_strategy_shadow_wiring.py -q
python3 -m pytest tests/strategy/test_phase22_e_portfolio_construction.py::test_phase29_l16_semantic_reentry_cooldown_and_recovery_hurdle -q
python3 -m pytest tests/runtime_v2/test_phase22_p_strategy_shadow_wiring.py tests/strategy/test_phase22_e_portfolio_construction.py::test_phase29_l16_semantic_reentry_cooldown_and_recovery_hurdle -q
PYTHONPYCACHEPREFIX=/private/tmp/ai-fund-lab-v2-pycache python3 -m py_compile src/ai_fund_lab_v2/strategy/shadow_runtime.py tests/runtime_v2/test_phase22_p_strategy_shadow_wiring.py tests/strategy/test_phase22_e_portfolio_construction.py
```

Results:

- Runtime shadow wiring focused suite: `26 passed`.
- Combined focused suite after final edits: `27 passed`.
- Compile/static check: PASS with `PYTHONPYCACHEPREFIX` redirected to `/private/tmp`.

The first direct `pytest` command failed because `pytest` was not on PATH; `python3 -m pytest` succeeded.

## Remaining Phase32 Performance Issues

Still open after this repair:

- Phase32-E: ADD vs NEW marginal semantic gap and winner capitalization gap.
- Phase32-G to J: PC/MCC Cash frontier, NEW accepted-weight suppression, passive residual Cash, and authoritative/shadow residual gap.
- Re-entry contribution to Cash: must be measured after user-operated fresh validation; this repair does not prove the magnitude of Cash reduction.
- Phase32-F: winner false-positive risk remains HIGH; blanket early exit is still prohibited; Capital-at-Risk/churn remains research scope.

## User-Operated Validation Recommendation

Run a user-operated fresh validation after review:

1. Narrow unit/focused CI for the changed bridge.
2. A small controlled historical slice that includes known PM EXIT reason rows such as `83060`.
3. Then a Spring/Plateau artifact audit to measure:
   - non-GENERIC prior-exit class rate,
   - REENTRY pass/selected rate,
   - Cash winner displacement, if any,
   - remaining reasons for zero target weight.

Do not interpret this repair alone as resolving excess Cash.

## Final Judgments

```text
PHASE32_L_PRIOR_EXIT_CONTEXT_DEFECT_REPAIRED = YES

PHASE32_L_PM_EXIT_REASON_PRESERVED = YES

PHASE32_L_PRIOR_EXIT_REASON_CODES_PRESERVED = YES

PHASE32_L_EXECUTED_CLOSE_IDENTITY_SAFE = YES

PHASE32_L_PARTIAL_REDUCE_SAFE = YES

PHASE32_L_STRICT_PRIOR_PIT_SAFE = YES

PHASE32_L_GENERIC_FALLBACK_PRESERVED = YES

PHASE32_L_REENTRY_THRESHOLDS_CHANGED = NO
PHASE32_L_CASH_LOGIC_CHANGED = NO
PHASE32_L_PC_MCC_LOGIC_CHANGED = NO
PHASE32_L_RISK_PACING_CHANGED = NO

PHASE32_L_POSITIVE_CONTROL_PASS = YES
PHASE32_L_NEGATIVE_CONTROLS_PASS = YES

PHASE32_L_REGRESSION_STATUS = PASS

PHASE32_L_CASH_PROBLEM_RESOLVED = NO

PHASE32_L_USER_FRESH_VALIDATION_REQUIRED = YES

PHASE32_L_NEXT_STEP = user-operated fresh validation on a narrow historical slice, followed by Spring/Plateau re-entry and Cash-causality measurement
```
