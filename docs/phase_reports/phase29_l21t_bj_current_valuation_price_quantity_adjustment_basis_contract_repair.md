# Phase29-L21T-BJ Current Valuation Price / Quantity Adjustment Basis Contract Repair

## Task

Phase29-L21T-BJ

Implementation repair. Phase29 continued. Phase30 was not entered.

Codex did not run fresh-run, resume, replay, recovery, or long Historical validation. The target run was not mutated.

## Root Cause

Phase29-L21T-BI confirmed `PRICE_QUANTITY_ADJUSTMENT_BASIS_MISMATCH`.

On 2022-08-10 the runtime-owned positions for `94320` and `94340` were held on an adjusted price/quantity basis:

| Symbol | Quantity | Fill Price | Adjusted Close | Raw Close | Defect |
|---|---:|---:|---:|---:|---|
| 94320 | 200 | 149.2 | 149.8 | 3744.0 | Raw close was applied to adjusted-basis quantity |
| 94340 | 100 | 151.4 | 151.8 | 1517.5 | Raw close was applied to adjusted-basis quantity |

This produced false market value inflation and the observed Day1 equity of `1,851,270`. The consistent-basis Day1 equity is `995,860`.

## Changed Files

- `src/ai_fund_lab_v2/runtime_v2/current_state/valuation.py`
- `src/ai_fund_lab_v2/runtime_v2/market_refresh/evidence.py`
- `tests/runtime_v2/test_phase17_aa_historical_current_valuation_authority.py`
- `tests/runtime_v2/test_phase15aw_market_quote_evidence_producer.py`
- `docs/02_architecture/runtime_temporal_freshness_contract.md`
- `reports/phase29_l21t_bj_current_valuation_price_quantity_adjustment_basis_contract_repair/summary.json`

## Authority Before / After

Before BJ:

- BE/BH prevented blind adjusted analytical price consumption.
- BH connected raw/economic source into quote evidence.
- Current valuation then selected raw/economic price for adjusted quote rows even when runtime-owned quantity was adjusted-basis.
- Result: price basis and quantity basis could diverge.

After BJ:

- Market quote evidence exposes both raw/economic and adjusted-basis valuation candidates when raw source is available.
- Current valuation resolves the runtime-owned quantity basis from explicit position metadata when present, otherwise from fill-derived unit-price evidence such as `average_price`, `current_price`, and `market_value / quantity`.
- Current valuation applies a price only when the selected price basis matches the resolved quantity basis, or an explicit reconciled authority is provided.
- Unknown, ambiguous, or mismatched basis fails closed.

## Implemented Contract

Price basis authority:

- `RAW`: unadjusted/economic price basis from raw source or unadjusted quote.
- `ADJUSTED`: adjusted-basis valuation price reconciled against adjusted quote/raw adjusted fields.
- `RECONCILED`: explicit economic reconciliation evidence supplied by upstream authority.

Quantity basis authority:

- Explicit `quantity_basis` / `position_quantity_basis` is honored when present.
- Otherwise Current valuation infers basis from runtime-owned position unit-price evidence.
- If adjusted and raw candidates both match, or neither matches, basis is unresolved and valuation fails closed.

Basis reconciliation:

- `price_basis == quantity_basis` is accepted.
- Explicit `RECONCILED` price evidence remains accepted.
- Raw source remains available as reconciliation evidence, but raw close is not blindly multiplied by adjusted-basis quantity.

## Fixture Results

2022-08-10 BI Day1 9-symbol fixture:

- Current valuation status: `READY`
- Market value: `250,040`
- Cash: `745,820`
- Total equity: `995,860`
- False `+85%` gain: prevented

94320:

- Quantity: `200`
- Compatible valuation price: `149.8`
- Market value: `29,960`
- Price basis: `ADJUSTED`

94340:

- Quantity: `100`
- Compatible valuation price: `151.8`
- Market value: `15,180`
- Price basis: `ADJUSTED`

Negative fixtures:

- Adjusted-basis quantity plus raw-only price evidence without adjusted-basis reconciliation: `REVIEW_REQUIRED`
- Raw-basis quantity plus adjusted-only price evidence without raw/economic reconciliation: `REVIEW_REQUIRED`
- BE `67310` adjusted ambiguity without raw/economic or basis reconciliation: still `REVIEW_REQUIRED`

## Preservation

BE protection preserved:

- Adjusted analytical close cannot be used as valuation price without provenance.
- Ambiguous adjusted/raw authority remains fail-closed.

BH raw source preserved:

- Raw source is still consumed and propagated as economic evidence.
- Raw source is now reconciliation evidence, not an unconditional valuation selector.

Corporate Action:

- Corporate Action quantity authority was not changed.
- Basis mismatch remains fail-closed unless explicit reconciliation evidence exists.

Execution:

- Execution behavior was not changed.
- Fill-derived position prices are used by Current valuation as evidence for runtime-owned quantity basis.

Strategy:

- No Strategy, threshold, model, or performance tuning changes were made.

## Regression Results

Focused regression:

- `python3 -m pytest -q tests/runtime_v2/test_phase17_aa_historical_current_valuation_authority.py tests/runtime_v2/test_phase15aw_market_quote_evidence_producer.py`
- Result: `25 passed`

Broader regression:

- `python3 -m pytest -q tests/runtime_v2/test_phase15az_current_valuation_no_fill_producer.py tests/runtime_v2/test_phase17_ab_current_valuation_pre_gate_authority.py tests/runtime_v2/test_phase17_bv12_current_valuation_symbol_identity.py`
- Result: `31 passed`

- `python3 -m pytest -q tests/runtime_v2/test_phase17_bg_empty_no_action_execution_contract.py tests/runtime_v2/test_phase17_g_historical_submit_guard_and_fill.py tests/runtime_v2/test_phase24_ht_planning_submit_feasibility.py`
- Result: `50 passed`

- `python3 -m pytest -q tests/strategy/test_phase22_j_position_sizing.py tests/strategy/test_phase22_g_runtime_planning.py`
- Result: `140 passed`

- `python3 -m pytest -q tests/runtime_v2/test_phase19_bt_reduce_quantity_contract.py tests/runtime_v2/test_phase26_step4_position_sizing_authority.py`
- Result: `23 passed`

- `python3 -m pytest -q tests/runtime_v2/test_phase14e25_runtime_owned_fill_projection.py tests/runtime_v2/test_phase29_l4_b_authority_materialization.py`
- Result: `18 passed`

- `python3 -m pytest -q tests/runtime_v2/test_phase21_b_pending_composition_add_consumer.py tests/strategy/test_phase26_h_adaptive_buy_quality.py`
- Result: `48 passed`

Final validation:

- `summary.json` parse: PASS
- `py_compile`: PASS
- `git diff --check`: PASS

## Judgment

Primary Judgment:

`PHASE29_L21T_BJ_PRICE_QUANTITY_ADJUSTMENT_BASIS_CONTRACT_REPAIRED_FOCUSED_REGRESSION_PASS`

## Runtime Safety

- Runtime mutated: NO
- Fresh-run executed: NO
- Resume/replay/recovery executed: NO
- Phase30 entered: NO

## Recommended Next Action

User-owned post-BJ 20BD fresh validation from 2022-08-10.
