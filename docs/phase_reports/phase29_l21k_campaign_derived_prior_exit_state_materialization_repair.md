# Phase29-L21K - Campaign-Derived Prior EXIT State Materialization Repair

## Primary Judgment

```text
PHASE29_L21K_PRIOR_EXIT_STATE_MATERIALIZATION_REPAIRED_FOCUSED_REGRESSION_PASS
```

L21K repaired the L21J gap by materializing prior same-symbol EXIT state from production-common runtime ledger execution history into Strategy BUY_NEW inputs before Buy Quality / Portfolio Construction consume them.

## Scope

Changed:

- `src/ai_fund_lab_v2/strategy/shadow_runtime.py`
- `tests/strategy/test_phase29_l21k_prior_exit_materialization.py`
- `docs/phase_reports/phase29_l21k_prior_exit_state_materialization_design.md`
- `docs/phase_reports/phase29_l21k_campaign_derived_prior_exit_state_materialization_repair.md`

Not changed:

- Portfolio Construction L16 predicate
- Position Sizing economics
- Runtime Planning intent taxonomy
- Submit / Execution / Pending lifecycle
- Safety caps
- Buy Quality / L21I score semantics
- Accepted Generation / model / thresholds
- active historical run artifacts

## Implementation

Strategy input construction now:

1. reads `persistent_ledger/executions.jsonl`;
2. derives same-symbol campaigns using only execution rows with `business_date < decision business_date`;
3. resolves the latest PIT-valid prior closed campaign by symbol;
4. attaches `prior_exit_business_date` plus diagnostic fields to candidate/opportunity rows when the symbol has no current position;
5. preserves explicit prior EXIT row authority if already present;
6. records materialization evidence in `strategy/input_manifest.json` under `prior_exit_state`.

The existing L16 contract then classifies:

```text
current_position == false
prior_exit_business_date present and < business_date
→ semantic_buy_type = REENTRY
```

Runtime Planning order intent remains `BUY_NEW`; `REENTRY` is Strategy semantic evidence, not a new order side.

## Temporal Safety

PIT rule:

```text
execution.business_date < decision business_date
```

The resolver does not consume same-day later executions or future exits. It does not use realized PnL as a Strategy decision input. PnL remains observability/performance evidence only.

## 23880 Reproduction

Focused fixture equivalent:

```text
2022-08-23 BUY 1200
2022-08-29 SELL 300
2022-08-30 SELL 900
2022-09-01 candidate returns
```

Result after materialization:

```text
prior_exit_business_date = 2022-08-30
semantic_buy_type = REENTRY
business_days_since_exit = 1
```

Existing L16 recovery evaluation starts from the materialized state and returns:

```text
reentry_recovery_status = FAIL_CLOSED
reentry_recovery_reason = reentry_expected_edge_below_threshold
```

This verifies contract activation only; it is not a post-hoc PnL judgment.

## Tests

PASS:

```text
PYTHONPATH=src python3 -m pytest tests/strategy/test_phase29_l21k_prior_exit_materialization.py
```

Result:

```text
6 passed
```

PASS:

```text
PYTHONPATH=src python3 -m pytest \
  tests/strategy/test_phase22_e_portfolio_construction.py \
  tests/strategy/test_phase22_j_position_sizing.py \
  tests/strategy/test_phase22_g_runtime_planning.py \
  tests/runtime_v2/test_phase20_j_performance_observability.py \
  tests/runtime_v2/test_phase20_l_long_run_readiness_destructive.py
```

Result:

```text
205 passed
```

PASS:

```text
PYTHONPATH=src python3 -m pytest \
  tests/runtime_v2/test_phase22_p_strategy_shadow_wiring.py \
  tests/runtime_v2/test_phase23_i_strategy_planning_authority.py \
  tests/runtime_v2/test_phase26_step5_runtime_planning_authority.py
```

Result:

```text
38 passed
```

PASS:

```text
PYTHONPYCACHEPREFIX=/tmp/ai-fund-lab-v2-pycache-l21k \
  python3 -m py_compile src/ai_fund_lab_v2/strategy/shadow_runtime.py
```

## Final Classification

```text
Prior EXIT materialization: IMPLEMENTED
Canonical authority: persistent runtime ledger execution history
Historical-only branch introduced: NO
Future / same-day execution consumed: NO
PnL Strategy gate introduced: NO
Normal BUY_NEW preserved: YES
BUY_ADD preserved: YES
Sell side preserved: YES
Focused regression: PASS
```
