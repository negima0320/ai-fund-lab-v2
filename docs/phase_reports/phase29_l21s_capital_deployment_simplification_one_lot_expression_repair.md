# Phase29-L21S — Capital Deployment Simplification / One-Lot Expression Repair

Task ID: `Phase29-L21S`  
Mode: focused design confirmation + implementation + short regression. No fresh-run, resume-run, long Historical run, runtime/pending mutation, accepted-generation change, model change, threshold tuning, Safety hard cap change, or cash target change was performed.

## Primary Judgment

`PHASE29_L21S_ONE_LOT_CAPITAL_EXPRESSION_REPAIRED_FOCUSED_REGRESSION_PASS`

`L21T_READY = YES`

## Before

L21M/N/O showed that many positive-intent candidates were reduced to zero because the execution-expression layer treated `minimum_meaningful_notional` as a hard lot requirement. With the current `max(50,000 JPY, 1.02 * round_lot_notional)` expression, a candidate often required two policy lots even when exactly one round lot was cash/gross/Safety feasible.

This left deployable capital in Cash despite:

- positive PC economic intent;
- one round lot feasible;
- no Buy Quality, REENTRY, Corporate Action, capacity, broker, cash, gross, or Safety hard blocker.

## Root Cause

The hard blocker was not the exchange round lot. It was the additional `minimum_meaningful_notional` expression layered above the round lot. That policy is useful as observability, but L21N did not find evidence that it is an independent Safety hard requirement for the 1M JPY portfolio.

## Minimum Meaningful Notional Final Handling

Final handling: `DIAGNOSTIC_ONLY`.

Position Sizing still emits:

- `minimum_meaningful_notional`;
- `minimum_meaningful_notional_policy`;
- `minimum_meaningful_notional_applied_to`;
- diagnostic reason `minimum_meaningful_notional_diagnostic_unmet`.

It no longer zeroes otherwise executable BUY_NEW / one-lot BUY_ADD simply because target notional is below that diagnostic threshold.

SELL/REDUCE behavior was not relaxed.

## One-Lot Expression Rule

The executable floor used for one-lot capital expression is now the exchange/broker round lot:

```text
one_lot_quantity = tradable_unit
one_lot_notional = reference_price * tradable_unit
one_lot_weight = one_lot_notional / portfolio_value
```

When positive investment intent exists and normal continuous sizing rounds to zero, PC evaluates one round lot. It allocates that one lot only if hard blockers pass.

## Safety Interaction

Safety hard max remains enforced.

If one lot would exceed Safety hard concentration, PC keeps allocation at zero with:

```text
minimum_lot_exceeds_safety_hard_cap
```

L21S does not introduce a Safety fail-open. The unresolved broader question of allowing small discrete overshoots above 25% remains out of scope unless a future phase explicitly changes Safety semantics.

## Cash Interaction

One-lot fallback must fit remaining deployable budget. If the one-lot weight exceeds remaining cash/gross budget, allocation stays zero with:

```text
minimum_lot_exceeds_remaining_budget
```

## Gross Interaction

L19 residual reallocation remains the authority for target gross exposure conservation. One-lot allocations subtract from remaining deployable budget and return residual capital to the normal iterative candidate queue.

## Capacity Interaction

L21R3 capacity semantics remain intact.

- resolved normal capacity can pass;
- severe / excessive capacity remains fail-closed;
- missing capacity remains UNKNOWN / review-required where the current REENTRY or low-price contract requires it.

L21S did not turn capacity UNKNOWN or SEVERE into PASS.

## BUY_NEW Behavior

BUY_NEW can now receive one-lot allocation when:

- membership is `ADD_CANDIDATE`;
- positive economic intent exists;
- one lot is broker/cash/gross/Safety feasible;
- no hard blocker already zeroed the member.

Strategy 18% remains a target/soft cap, but a Safety-contained one-lot expression is no longer hard-blocked only because it slightly exceeds 18%.

## REENTRY Behavior

REENTRY remains semantically REENTRY. One-lot fallback does not convert REENTRY to BUY_NEW.

REENTRY fallback requires the existing REENTRY chain to have passed before the member reaches positive allocation intent. REENTRY cooldown/recovery/capacity/CA failures still zero the member before one-lot expression.

## BUYADD Behavior

BUY_ADD remains current-campaign ADD. One-lot fallback applies only when ADD economic evidence is positive and existing ADD semantics pass.

The L21D/L21F ADD authorization path was preserved, but the old two-policy-lot lift was removed. ADD can now express exactly one round lot where that is the feasible Safety-contained increment.

## Residual Reallocation Behavior

L19 iterative residual reallocation remains active:

- blocked high-priority candidates pass residual to later candidates;
- successful one-lot allocations reduce remaining deployable budget;
- duplicate allocation prevention is preserved by per-symbol candidate indexing;
- residual cash evidence still reports `residual_cash_reason`;
- candidate exhaustion is still explicit.

## Observability

PC / L19 evidence now carries one-lot expression fields:

- `continuous_target_weight`;
- `continuous_target_notional`;
- `normal_lot_quantity`;
- `one_lot_quantity`;
- `one_lot_notional`;
- `one_lot_feasibility_status`;
- `one_lot_fallback_applied`;
- `blocker_reason`;
- `final_allocated_quantity`;
- `residual_capital_after_allocation_weight`;
- previous meaningful-notional threshold as diagnostic evidence.

No parallel schema was introduced; fields are attached to existing L19 / lot-aware reallocation evidence.

## Regression Results

PASS:

```bash
PYTHONPATH=src python3 -m pytest tests/strategy/test_phase22_e_portfolio_construction.py -k 'phase29_l21s or phase29_l19 or phase28_d55_b or phase29_l21d or phase29_l16_sell_reduce_exit' -q
```

Result:

```text
16 passed
```

PASS:

```bash
PYTHONPATH=src python3 -m pytest tests/strategy/test_phase22_j_position_sizing.py -k 'phase29_l21s or phase29_l19 or phase28_d55_b or phase28_d61 or phase29_l21f' -q
```

Result:

```text
11 passed
```

PASS:

```bash
PYTHONPATH=src python3 -m pytest tests/strategy/test_phase22_e_portfolio_construction.py tests/strategy/test_phase22_j_position_sizing.py tests/strategy/test_phase22_g_runtime_planning.py -q
```

Result:

```text
208 passed
```

PASS:

```bash
PYTHONPATH=src python3 -m pytest tests/strategy/test_phase29_l21k_prior_exit_materialization.py tests/strategy/test_phase22_qe_input_materialization.py -q
```

Result:

```text
23 passed
```

Static:

```text
py_compile PASS
git diff --check PASS
```

## Remaining Gaps

L21S does not claim aggregate utilization improvement without a user-operated fresh validation run.

Remaining out-of-scope items:

- no forced 80% capital deployment;
- no cash target rewrite;
- no Safety hard max rewrite;
- no maximum position count rewrite;
- no Corporate Action policy change;
- no REENTRY policy threshold change;
- no model/ranking/Buy Quality change.

## User-Run Validation Recommendation

Recommended next task:

`Phase29-L21T — Post-Repair Capital Utilization Focused Fresh Validation`

Codex did not run fresh/resume/long Historical validation. The user should run a focused fresh validation and compare:

- positive BUY_NEW / REENTRY / BUY_ADD counts;
- one-lot fallback applied count;
- Safety hard block count;
- cash/gross block count;
- average and median invested ratio;
- residual cash reasons;
- realized BUY fills versus planned BUYs.

## L21T Entry Gate

`L21T_READY = YES`

Gate assessment:

- positive economic intent is not zeroed only by minimum meaningful notional: YES;
- feasible one lot can materialize: YES;
- infeasible one lot is stopped by hard blockers: YES;
- Safety fail-open introduced: NO;
- REENTRY semantics preserved: YES;
- BUY_ADD semantics preserved: YES;
- SELL/REDUCE/EXIT non-regression: YES;
- L19 residual reallocation non-regression: YES.

