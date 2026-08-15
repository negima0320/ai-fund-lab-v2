# Phase29-L21T-S MARKET BUY Reservation / Strategy Sizing Authority Separation Repair

## Scope

IMPLEMENTATION + FOCUSED REGRESSION.

This repair is Production/Demo/Historical common Runtime v2 work only.  Codex
did not run fresh-run, resume-run, long Historical validation, scoped recovery,
manual Pending approval, or runtime mutation for the target run.

Target run remains:

```text
runtime-test-historical-smoke-20260812T083943290963Z
```

## Primary Judgment

`PHASE29_L21T_S_MARKET_BUY_RESERVATION_STRATEGY_SIZING_AUTHORITY_SEPARATED_FOCUSED_REGRESSION_PASS`

Required judgments:

```text
ROOT_CAUSE_CONFIRMED = YES
Q1B_RESERVATION_AUTHORITY_PRESERVED = YES
Q2_TRANSACTIONALITY_PRESERVED = YES
RESERVED_NOTIONAL_SELECTED_POSITION_AMOUNT_COMPARISON_REMOVED = YES
STRATEGY_EXECUTABLE_NOTIONAL_SIZING_PROTECTION_PRESERVED = YES
CASH_INSUFFICIENT_RESERVATION_PROTECTION_PRESERVED = YES
BUY_ITEM_SCOPED_REVIEW_FAIL_CLOSED_PRESERVED = YES
BUY_SELL_INDEPENDENCE_PRESERVED = YES
HISTORICAL_SPECIFIC_WORKAROUND_ADDED = NO
RESUME_SAFE_NOW = NO
SCOPED_RECOVERY_REPLAY_REQUIRED = YES
```

## Root Cause

L21T-R confirmed that the 2023-06-12 `59550` BUY was blocked by a semantic
authority mix-up:

```text
selected_position_amount = 115253.75
strategy/reference executable notional = 108000.0
reservation_price = 152.0
reserved_notional = 152000.0
cash / buying_power = 609670.0
```

The Strategy-sized trade was valid:

```text
108000.0 <= 115253.75
```

The broker cash reservation was also valid:

```text
152000.0 <= 609670.0
```

The defect was the direct position-sizing comparison:

```text
152000.0 > 115253.75
```

which produced:

```text
reserved notional exceeds selected_position_amount
```

`reserved_notional` is a broker/pre-commit cash hold authority.  It is valid for
cash, buying power, dynamic cash, dynamic exposure, aggregate batch reservation,
and execution pre-commit safety.  It is not the Strategy position-sizing
notional.

## Changed Files

- `src/ai_fund_lab_v2/runtime_v2/planning_submit_feasibility.py`
- `tests/runtime_v2/test_phase24_ht_planning_submit_feasibility.py`
- `docs/phase_reports/phase29_l21t_s_market_buy_reservation_strategy_sizing_authority_separation_repair.md`

The worktree already contained unrelated prior Phase29 changes before L21T-S;
they were not reverted or normalized.

## Authority Before / After

Before:

```text
cash feasibility: reserved_notional <= cash / buying_power / cash-exposure authority
position sizing: reserved_notional <= selected_position_amount
```

After:

```text
cash feasibility: reserved_notional <= cash / buying_power / cash-exposure authority
position sizing: strategy_executable_notional <= selected_position_amount
```

`strategy_executable_notional` is resolved from existing item authority only:

```text
estimated_amount
fallback: quantity_contract.lot_adjusted_notional
fallback: quantity_contract.selected_notional
fallback: quantity_contract.target_notional
fallback: quantity_contract.incremental_buy_notional
fallback: resolved position_sizing_authority.lot_adjusted_notional
```

No new Strategy authority was invented.  The fallback exists only for older or
partially materialized payloads where `estimated_amount` is not available.

## 2023-06-12 Fixture Result

Added:

```text
test_phase29_l21t_s_market_buy_reservation_does_not_violate_strategy_sizing
```

Input:

```text
selected_position_amount = 115253.75
strategy/reference executable notional = 108000.0
reserved_notional = 152000.0
cash = 609670.0
buying_power = 609670.0
```

Result:

```text
Planning Submit feasibility = PASS
Pending state = APPROVED
approved_buy_item_ids = (buy-59550)
strategy_executable_notional = 108000.0
reserved_notional = 152000.0
reason != reserved notional exceeds selected_position_amount
```

This proves the old invalid cross-authority comparison no longer creates
BUY_ITEM_SCOPED_REVIEW by itself.

## Negative Fixture Results

Cash-insufficient reservation fixture:

```text
test_phase29_l21t_s_market_buy_reservation_still_blocks_cash_shortfall
```

Result:

```text
Pending state = REVIEW_REQUIRED
violated_policy = cash
reason = reserved notional exceeds Current cash
review_scope = BUY_ITEM_SCOPED_REVIEW
```

Strategy-sizing violation fixture:

```text
test_phase29_l21t_s_strategy_executable_notional_still_blocks_sizing_violation
```

Result:

```text
strategy_executable_notional = 108000.0
selected_position_amount = 100000.0
reserved_notional = 109000.0
violated_policy = position_sizing
reason = estimated amount exceeds selected_position_amount
```

This preserves the existing Strategy sizing fail-closed protection while
removing only the invalid reservation-vs-sizing comparison.

## Regression Results

Planning Submit feasibility:

```bash
python3 -m pytest tests/runtime_v2/test_phase24_ht_planning_submit_feasibility.py -q
```

Result:

```text
15 passed in 1.71s
```

Broad focused Runtime / Strategy regression:

```bash
python3 -m pytest \
  tests/runtime_v2/test_phase24_ht_planning_submit_feasibility.py \
  tests/runtime_v2/test_phase17_g_historical_submit_guard_and_fill.py \
  tests/runtime_v2/test_phase14e23_execution_acceptance_policy.py \
  tests/runtime_v2/test_phase14e25_runtime_owned_fill_projection.py \
  tests/runtime_v2/test_phase21_b_pending_composition_add_consumer.py \
  tests/runtime_v2/test_phase23_i_strategy_planning_authority.py \
  tests/runtime_v2/test_phase26_step4_position_sizing_authority.py \
  tests/runtime_v2/test_phase26_step6_submit_guard_authority.py \
  tests/runtime_v2/test_phase28_d8_sell_pending_authority_merge.py \
  tests/runtime_v2/test_phase29_l7_sell_quantity_contract_materialization.py \
  tests/runtime_v2/test_phase15n_safety_operation_guard_runtime_connection.py \
  tests/runtime_v2/test_phase17_x_historical_sell_planning_authority.py \
  tests/runtime_v2/test_phase15m_sell_broker_available_quantity_evidence.py \
  tests/runtime_v2/test_phase15bv_execution_normalization_current_apply.py \
  tests/runtime_v2/test_phase15bw_runtime_end_to_end_daily_system_test_review.py::test_phase15bw_ledger_dedup_and_demo_only_flags_remain \
  tests/strategy/test_phase22_j_position_sizing.py \
  tests/strategy/test_phase22_e_portfolio_construction.py \
  -q
```

Result:

```text
323 passed in 44.41s
```

Compile:

```bash
PYTHONPYCACHEPREFIX=/private/tmp/ai-fund-lab-v2-l21t-s-pycache python3 -m py_compile \
  src/ai_fund_lab_v2/runtime_v2/planning_submit_feasibility.py \
  tests/runtime_v2/test_phase24_ht_planning_submit_feasibility.py
```

Result:

```text
PASS
```

Whitespace:

```bash
git diff --check
```

Result:

```text
PASS
```

## Q1B Protection Preserved

Q1B stop-high reservation remains the cash authority for MARKET BUY.

Preserved checks:

```text
reserved_notional > Current cash -> REVIEW_REQUIRED
reserved_notional > buying_power -> REVIEW_REQUIRED
reserved_notional > dynamic cash capacity -> REVIEW_REQUIRED
current exposure + reserved_notional > selected_runtime_exposure_limit -> REVIEW_REQUIRED
aggregate sequential BUY reservation uses reserved_notional
```

The Q1B tests for previous-close stop-high reservation, LIMIT reservation, and
aggregate stop-high batch blocking passed inside the focused regression set.

## Q2 Transactionality Preserved

No Execution commit code was changed.  The Q2 transactional protections remain:

```text
pre-commit execution cash feasibility
candidate Current projection
validate-before-commit
no Ledger mutation on failed projection
no Current mutation on failed projection
retry / dedup safety
Ledger / Current consistency
```

The Execution and retry/dedup focused tests passed in the 323-test regression
set.

## BUY / SELL Independence Preserved

No SELL Planning, Pending composition, Submit-side approved item filtering, or
BUY/SELL authority merge code was changed.  L21T-M SELL continuation and
BUY_ITEM_SCOPED_REVIEW preservation tests passed in the focused regression set.

## Resume Decision

`RESUME_SAFE_NOW = NO`.

The target run currently contains a 2023-06-12 REVIEW_REQUIRED Pending generated
before this repair.  That current Pending must not be assumed valid for direct
resume.  A direct resume from `2023-06-12:sell_planning` could preserve the stale
review pending rather than regenerating Planning Submit feasibility under the
repaired semantics.

## Scoped Recovery / Replay Requirement

`SCOPED_RECOVERY_REPLAY_REQUIRED = YES`.

The safe user-owned continuation should regenerate 2023-06-12 planning/pending
from the earliest job that writes the BUY pending for that day.  Based on the
target run evidence, that boundary is:

```text
2023-06-12:morning
```

or any more specific official scoped replay command that rewinds to the same
Strategy Planning / BUY pending producer boundary.  It should not manually edit
Pending, manually approve the BUY, or continue from the existing
`sell_planning` halt state.

## Next Step

User-operated scoped recovery/replay of the target run from the 2023-06-12
morning/planning boundary, followed by focused inspection that `59550` no longer
enters BUY_ITEM_SCOPED_REVIEW solely because `reserved_notional >
selected_position_amount`.  Long Historical validation remains user-owned and
should wait until the scoped replay evidence is coherent.

