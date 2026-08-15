# Phase29-L21T-BH — Current Valuation Economic Price Producer / Reconciliation Propagation Repair

## Task

- Task ID: Phase29-L21T-BH
- Mode: IMPLEMENTATION REPAIR
- Phase: Phase29 continued; Phase30 not entered

No fresh-run, resume, replay, recovery, long Historical run, or target run mutation was performed.

## Primary Judgment

`PHASE29_L21T_BH_CURRENT_VALUATION_ECONOMIC_PRICE_PRODUCER_RECONCILIATION_REPAIRED_FOCUSED_REGRESSION_PASS`

## Root Cause

BG confirmed that post-BE Day1 current valuation halted because all 9 held symbols had adjusted normalized quotes without explicit economic valuation reconciliation:

- normalized quote `adjusted=true`
- no `economic_price_reconciliation_status`
- no `economic_price_provenance`
- no `economic_valuation_price`

The raw/economic OHLCV source existed, but the actual current valuation path converted only normalized OHLCV into quote evidence. BE correctly failed closed; the missing piece was producer integration.

## Changed Files

- `src/ai_fund_lab_v2/runtime_v2/current_state/valuation.py`
- `src/ai_fund_lab_v2/runtime_v2/market_refresh/evidence.py`
- `tests/runtime_v2/test_phase17_aa_historical_current_valuation_authority.py`
- `tests/runtime_v2/test_phase15aw_market_quote_evidence_producer.py`
- `docs/02_architecture/runtime_temporal_freshness_contract.md`
- `docs/phase_reports/phase29_l21t_bh_current_valuation_economic_price_producer_reconciliation_repair.md`
- `reports/phase29_l21t_bh_current_valuation_economic_price_producer_reconciliation_repair/summary.json`

## Authority Before / After

Before:

- Normalized adjusted `Close` was carried as quote `price`.
- Adjusted quotes failed closed unless explicit reconciliation fields already existed.
- Historical current valuation could see raw source paths in `historical_asof_view`, but did not use them to materialize economic valuation evidence.

After:

- The production-common quote producer resolves a raw/economic OHLCV source corresponding to normalized OHLCV.
- The historical-asof current valuation path also resolves raw OHLCV from `historical_asof_view` / logical input metadata.
- For `adjusted=true`, the producer reads same symbol/date raw close and materializes:
  - `price_role=reconciled_raw_economic_valuation_price`
  - `economic_price_reconciliation_status=PASS`
  - `economic_price_provenance=raw_ohlcv_close:<source>:<column>`
  - `economic_valuation_price=<raw close>`
  - `adjusted_analytical_price=<normalized adjusted close>`
- Current valuation continues to consume `economic_valuation_price`, not adjusted analytical `Close`.

## BG Day1 Fixture Result

Focused fixture covering the BG 2022-08-10 9-symbol shape now passes:

- `23700`, `23880`, `45710`, `66590`, `76470`, `89180`, `93180` raw close equals adjusted close and reconciles as valid economic valuation.
- `94320` uses raw close `3744.0`, not adjusted analytical close `149.8`.
- `94340` uses raw close `1517.5`, not adjusted analytical close `151.8`.
- Current valuation result: `READY`
- valued position count: `9`

## Fail-Closed Preservation

The BE 67310 ambiguity fixture remains fail-closed when adjusted normalized quote lacks raw/economic source or explicit reconciliation evidence.

The repair does not introduce:

- adjusted `Close` as economic valuation
- zero-fill
- stale fallback
- silent fallback
- Historical-only logic
- symbol-specific logic
- consumer requirement relaxation

## Regression Results

Focused:

- `python3 -m pytest -q tests/runtime_v2/test_phase17_aa_historical_current_valuation_authority.py tests/runtime_v2/test_phase15aw_market_quote_evidence_producer.py`
  - PASS: `22 passed`

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
- `python3 -m pytest -q tests/runtime_v2/test_phase21_b_pending_composition_add_consumer.py tests/strategy/test_phase26_h_adaptive_buy_quality.py`
  - PASS: `48 passed`

Final validation:

- `py_compile`: tracked in final validation
- `summary.json` parse: tracked in final validation
- `git diff --check`: tracked in final validation

## Preservation

- BE fail-closed weakened: no
- Corporate Action changed: no
- Execution changed: no
- Strategy changed: no
- Historical-only logic: no
- Runtime mutated: no target run mutation
- Fresh-run executed: no
- Phase30 entered: no

## Recommended Next Action

User-owned post-BH 20BD fresh validation from `2022-08-10`.

Codex must not execute fresh-run/resume/replay/recovery. The expected first check is that Day1 current valuation no longer halts at BE fail-closed when raw/economic reconciliation evidence can be generated.
