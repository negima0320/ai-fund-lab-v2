# Phase29-L21T-BE — Valuation Price Normalization / Authority Repair

## Task

Phase29-L21T-BE

Mode: IMPLEMENTATION REPAIR.

Phase29 was continued. Phase30 was not entered. No fresh-run, resume, replay, recovery, or long Historical run was executed. The active 4-year Historical run was not stopped or mutated.

## Primary Judgment

`PHASE29_L21T_BE_VALUATION_PRICE_NORMALIZATION_AUTHORITY_REPAIRED_FOCUSED_REGRESSION_PASS`

## Root Cause

A0V confirmed that Current valuation accepted normalized OHLCV `Close` rows with `PriceSource=adjusted` as if they were canonical economic yen prices. For `67310`, this allowed an adjusted analytical close sequence of `2000 -> 3000 -> 2000 -> 3000` while holding `100` shares, producing false +/-100,000 yen daily equity swings.

The arithmetic DAILY_PNL reconciliation was correct. The defect was upstream: valuation price authority did not separate adjusted analytical prices from economic valuation prices.

## Changed Files

- `src/ai_fund_lab_v2/runtime_v2/current_state/valuation.py`
- `src/ai_fund_lab_v2/runtime_v2/market_refresh/evidence.py`
- `tests/runtime_v2/test_phase17_aa_historical_current_valuation_authority.py`
- `tests/runtime_v2/test_phase15aw_market_quote_evidence_producer.py`
- `docs/02_architecture/runtime_temporal_freshness_contract.md`
- `docs/phase_reports/phase29_l21t_be_valuation_price_normalization_authority_repair.md`
- `reports/phase29_l21t_be_valuation_price_normalization_authority_repair/summary.json`

## Authority Before / After

Before:

- `normalized_ohlcv.Close` was selected as quote `price`.
- `adjusted` was recorded but not used as a valuation eligibility authority.
- Current valuation could consume adjusted analytical `Close` directly as `current_price`.

After:

- Quote evidence carries explicit price provenance:
  - `normalized_price_source`
  - `price_source_column`
  - `price_role`
  - `economic_price_reconciliation_status`
  - `economic_price_provenance`
  - `economic_valuation_price`
- Current valuation resolves a canonical economic valuation price before applying market value.
- `adjusted=false` quotes remain valid economic yen prices when freshness/source checks pass.
- `adjusted=true` quotes fail closed unless explicit economic reconciliation evidence is present and positive.
- Reconciled adjusted quotes use `economic_valuation_price`, not analytical `price`.

## 67310 Fixture Result

Input:

- symbol: `67310`
- quantity: `100`
- previous current price: `2000`
- normalized `Close`: `3000`
- `PriceSource`: `adjusted`
- no economic reconciliation evidence

Result:

- Current valuation status: `REVIEW_REQUIRED`
- Apply executed: `false`
- Reason includes: `current_valuation_quote_invalid:67310`
- Existing Current price remained `2000`
- Existing market value remained `200000`

This prevents the false +100,000 yen valuation swing from being committed.

## Valid Economic Raw Fixture Result

Input:

- `PriceSource=unadjusted`
- `Close=1100`

Result:

- Current valuation status: `READY`
- Apply executed: `true`
- `current_price=1100`
- `valuation_price_authority=PASS`
- `valuation_price_role=economic_valuation_price`

## Reconciled Adjusted Fixture Result

Input:

- `PriceSource=adjusted`
- analytical `Close=1120`
- `economic_price_reconciliation_status=PASS`
- non-empty `economic_price_provenance`
- `economic_valuation_price=1020`

Result:

- Current valuation status: `READY`
- Apply executed: `true`
- `current_price=1020`
- `valuation_adjusted=true`
- `valuation_price_role=reconciled_adjusted_economic_valuation_price`

## Regression Results

Focused:

- `python3 -m pytest -q tests/runtime_v2/test_phase17_aa_historical_current_valuation_authority.py tests/runtime_v2/test_phase15aw_market_quote_evidence_producer.py`
  - PASS: `19 passed`
- `PYTHONPYCACHEPREFIX=/private/tmp/ai-fund-lab-v2-pycache python3 -m py_compile src/ai_fund_lab_v2/runtime_v2/current_state/valuation.py src/ai_fund_lab_v2/runtime_v2/market_refresh/evidence.py`
  - PASS

Broader focused:

- `python3 -m pytest -q tests/runtime_v2/test_phase15az_current_valuation_no_fill_producer.py tests/runtime_v2/test_phase17_ab_current_valuation_pre_gate_authority.py tests/runtime_v2/test_phase17_bv12_current_valuation_symbol_identity.py`
  - PASS: `31 passed`
- `python3 -m pytest -q tests/runtime_v2/test_phase17_bg_empty_no_action_execution_contract.py tests/runtime_v2/test_phase17_g_historical_submit_guard_and_fill.py tests/runtime_v2/test_phase24_ht_planning_submit_feasibility.py`
  - PASS: `50 passed`
- `python3 -m pytest -q tests/strategy/test_phase22_j_position_sizing.py tests/strategy/test_phase22_g_runtime_planning.py`
  - PASS: `140 passed`
- `python3 -m pytest -q tests/runtime_v2/test_phase19_bt_reduce_quantity_contract.py tests/runtime_v2/test_phase26_step4_position_sizing_authority.py`
  - PASS: `23 passed`
- `python3 -m pytest -q tests/runtime_v2/test_phase14e25_runtime_owned_fill_projection.py tests/runtime_v2/test_phase29_l4_b_authority_materialization.py`
  - PASS: `18 passed`
- `python3 -m pytest -q tests/runtime_v2/test_phase17_bg_empty_no_action_execution_contract.py tests/runtime_v2/test_phase21_b_pending_composition_add_consumer.py`
  - PASS: `43 passed`

## Preservation

- Normal valuation changed: only authority validation and provenance recording changed.
- Corporate Action changed: no. Explicit adjusted-price reconciliation can be supplied by a future/available authority without changing quantity semantics.
- Quantity authority changed: no.
- Execution price handling changed: no.
- Strategy changed: no.
- Threshold tuned: no.
- Historical-only logic: no.
- Runtime mutated: no target run mutation.
- Fresh-run executed: no.

## RESUME_SAFE_NOW

No.

The target long run contains pre-repair valuation state. Do not assume it is safe to resume as-is. A scoped validation/recovery plan should be chosen after inspecting which dates and Current snapshots consumed ambiguous adjusted prices.

## Scoped Recovery / Replay Requirement

Required before trusting the affected long-run equity series.

The safe next step is a read-only scoped impact inventory for pre-repair ambiguous adjusted valuation consumption, then a bounded regeneration/replay plan from the earliest affected valuation boundary. Manual Pending/Ledger/Current JSON edits remain prohibited.

## Next Step

`Phase29-L21T-BF — Valuation Price Normalization Post-Repair Scoped Impact / Replay Readiness Audit`

