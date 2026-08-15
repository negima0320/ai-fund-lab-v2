# Phase29-L21T-AD - REDUCE Intentional No-Order Semantic Materialization Repair

Task ID: `Phase29-L21T-AD`

Primary Judgment:

```text
PHASE29_L21T_AD_REDUCE_INTENTIONAL_NO_ORDER_SEMANTIC_MATERIALIZED_FOCUSED_REGRESSION_PASS
```

Current Phase:

```text
Phase29
```

## Root Cause

Inherited from Phase29-L21T-AB:

```text
E_MULTI_CAUSAL
  C_STRATEGY_TO_EXECUTION_SEMANTIC_GAP
  B_OBSERVABILITY_GAP
```

AB found 72 PM `REDUCE` decisions in the partial long-horizon evidence: 4 executable non-zero REDUCE, 27 lot-zero REDUCE, and 41 minimum-notional / other zero REDUCE. The runtime was safety-preserving, but zero REDUCE materialization was not explicit enough to distinguish intentional no-order from HOLD, missing evidence, or lifecycle defect.

## AC Contract Implemented

Implemented the AC-approved minimal option only:

- preserve current floor-to-zero behavior;
- do not ceil sub-lot REDUCE to one lot;
- do not convert REDUCE to EXIT;
- do not change PM decision logic;
- do not change REDUCE ratios;
- do not add persistent reduce debt or lifecycle carry-forward;
- add formal no-order semantics and observability.

## Changed Files

- `src/ai_fund_lab_v2/strategy/position_sizing.py`
- `src/ai_fund_lab_v2/strategy/runtime_planning.py`
- `src/ai_fund_lab_v2/runtime_v2/planning/sell_pipeline.py`
- `scripts/runtime_test.py`
- `tests/strategy/test_phase22_j_position_sizing.py`
- `tests/strategy/test_phase22_g_runtime_planning.py`
- `tests/runtime_v2/test_phase19_bt_reduce_quantity_contract.py`
- `tests/runtime_v2/test_phase19_bv_runtime_test_summarize.py`
- `docs/02_architecture/position_management_reduce_quantity_contract.md`
- `docs/phase_reports/phase30_a_entry_gate_100bd_baseline_status.md`
- `docs/phase_reports/phase29_l21t_ad_reduce_intentional_no_order_semantic_materialization_repair.md`

## Authority Before / After

Before:

```text
PM REDUCE -> Position Sizing floors quantity to zero -> Runtime Planning NO_ACTION/NO_ORDER
```

The behavior was safe but the semantic outcome was under-materialized.

After:

```text
PM REDUCE
  -> Position Sizing emits REDUCE_UNEXECUTABLE_DUE_TO_DISCRETE_LOT or REDUCE_UNEXECUTABLE_DUE_TO_MINIMUM_NOTIONAL
  -> Runtime Planning preserves REDUCE context only long enough to produce intentional NO_ORDER
  -> Sell Planning non-executable REDUCE evidence carries canonical semantic
  -> Lifecycle checker treats only evidenced intentional no-order as terminal
```

## Semantics Materialized

```text
REDUCE_UNEXECUTABLE_DUE_TO_DISCRETE_LOT
REDUCE_UNEXECUTABLE_DUE_TO_MINIMUM_NOTIONAL
```

Missing semantic evidence remains `REVIEW_REQUIRED`; it is not treated as terminal.

## Preservation

- Executable REDUCE -> SELL_REDUCE is unchanged.
- EXIT and mandatory SELL behavior are unchanged.
- BUY/SELL independence is preserved.
- Submit / Execution transactionality is unchanged.
- Actual trading behavior changed: `NO`.
- Automatic ceil-to-EXIT: `NO`.
- Persistent reduce debt / lifecycle: `NO`.
- PM logic changed: `NO`.
- REDUCE ratios changed: `NO`.
- Target run mutation: `NO`.
- Long Historical / resume / replay / recovery / fresh-run: `NOT RUN`.

## Common SoT

Updated:

```text
docs/02_architecture/position_management_reduce_quantity_contract.md
```

The SoT now records Production/Demo/Historical common intentional no-order semantics, no historical-only workaround, REDUCE != EXIT, no min-lot ceil, missing-evidence fail-closed behavior, repeated zero no-debt behavior, next-day fresh PM reevaluation, and BUY/SELL independence.

## Phase30 Entry Gate Update

Updated:

```text
docs/phase_reports/phase30_a_entry_gate_100bd_baseline_status.md
```

AB/AC/AD are recorded as Phase30 future Strategy quality work, not as Phase30 entry. The residual quality question is whether impossible partial REDUCE should remain HOLD/fresh reevaluation or become explicit EXIT under stronger evidence.

Recorded priority candidate:

```text
Pullback vs Breakdown Separability Audit
```

`Trend Integrity Assessment` remains future-only unless separability is proven.

## Regression Results

Focused AD regression:

```text
8 passed
```

Broader affected-file regression:

```text
171 passed
```

Additional focused regression covering pending composition, BUY_ITEM_SCOPED_REVIEW / SELL continuation, submit approval fail-closed behavior, execution dedup/idempotency, BUY_ADD, REENTRY, and one-lot authority:

```text
11 passed
```

Changed-file `py_compile`:

```text
PASS
```

`git diff --check`:

```text
PASS
```

## Final Judgment

```text
PHASE29_L21T_AD_REDUCE_INTENTIONAL_NO_ORDER_SEMANTIC_MATERIALIZED_FOCUSED_REGRESSION_PASS
```

## Next Action

Do not resume the target run from this task. The next safe action is operator review of this focused repair and, separately, any future scoped validation plan requested by the user. Phase30 is not entered by AD.
