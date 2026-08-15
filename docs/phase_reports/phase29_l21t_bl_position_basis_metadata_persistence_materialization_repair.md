# Phase29-L21T-BL Position Basis Metadata Persistence / Materialization Repair

## Task

Phase29-L21T-BL

Implementation repair. Phase29 continued. Phase30 was not entered.

Codex did not run fresh-run, resume, replay, recovery, or long Historical validation. The target run was not mutated.

## Root Cause

Phase29-L21T-BK confirmed that BJ's Day1 valuation contract worked, but the
next runtime-owned Current rebuild dropped position basis metadata.

Target run:

`runtime-test-historical-extended-smoke-20260815T022202383846Z`

HALT:

- Date: `2022-08-12`
- Stage: `current_valuation_refresh`
- Direct failing symbol: `94320`
- Direct reason: `position_quantity_basis_unresolved`

On 2022-08-10, `94320` had:

- `quantity_basis = ADJUSTED`
- `valuation_price_basis = ADJUSTED`
- Current valuation READY
- Equity = `995,860`

After Day2 runtime-owned fill projection, `quantity_basis`,
`valuation_price_basis`, `valuation_price_role`, `valuation_price_provenance`,
and `current_price` were absent. BJ then correctly failed closed because basis
could not be resolved.

## Changed Files

- `src/ai_fund_lab_v2/runtime_v2/asset/models.py`
- `src/ai_fund_lab_v2/runtime_v2/asset/runtime_owned_fill_projection.py`
- `tests/runtime_v2/test_phase14e25_runtime_owned_fill_projection.py`
- `docs/02_architecture/runtime_temporal_freshness_contract.md`
- `reports/phase29_l21t_bl_position_basis_metadata_persistence_materialization_repair/summary.json`

## Authority Before / After

Before BL:

- Current valuation could establish basis metadata.
- Runtime-owned fill projection rebuilt positions from ledger position rows and cost projection.
- The public Current position payload only retained symbol, quantity, average price, market value, cost basis, unrealized PnL, source, and as-of.
- Existing position basis and `current_price` were dropped across state transitions.
- New BUY positions did not materialize explicit quantity basis.

After BL:

- `CurrentAssetPosition` carries optional basis/provenance metadata.
- Runtime-owned fill projection preserves existing position basis metadata.
- New BUY / ADD materializes quantity basis from execution/fill price authority.
- REDUCE / partial SELL preserves basis for the remaining position.
- EXIT removes the position normally.
- Explicit basis conflicts fail closed with `runtime_owned_position_basis_conflict:<symbol>`.
- `current_price` is retained only as basis/provenance evidence; same-day valuation still uses same-day market evidence under BJ.

## Implemented Metadata

Current position state can now retain:

- `current_price`
- `quantity_basis`
- `quantity_basis_provenance`
- `valuation_price_basis`
- `valuation_price_role`
- `valuation_price_provenance`
- `execution_price_basis`
- `fill_price_basis`

Normal path authority:

1. Existing position `quantity_basis` / provenance is carried forward.
2. Explicit latest position or execution/fill basis is used when present.
3. New position basis is materialized from runtime execution price authority.
4. Fallback inference remains a valuation-side safety check for legacy/malformed state, not the normal persistence authority.

## Fixture Results

BK Day1 -> Day2 94320:

- Day1 `quantity_basis=ADJUSTED` persisted through projection.
- `current_price=149.8` persisted as basis evidence.
- 2022-08-12 valuation used same-day adjusted-basis close `147.9`.
- Current valuation status: `READY`.

94340:

- `quantity_basis=ADJUSTED` persisted.
- Valuation no longer depends on incidental fallback match.
- Same-day adjusted-basis valuation price: `151.4`.

New BUY positions:

- `30100`: `quantity_basis=ADJUSTED`
- `36640`: `quantity_basis=ADJUSTED`
- `91070`: `quantity_basis=ADJUSTED`

ADD:

- Existing basis is preserved after weighted average cost recalculation.

REDUCE / partial SELL:

- Remaining position basis is preserved.

EXIT:

- Fully exited position is removed normally.

Negative basis fixture:

- Explicit prior `ADJUSTED` basis plus explicit latest `RAW` basis fails closed.

## Preservation

BJ fail-closed preserved:

- Basis mismatch/unknown still fails closed.
- No raw/adjusted fixed fallback was introduced.

BE protection preserved:

- Adjusted analytical price is still not consumed without provenance.
- Ambiguous price authority remains fail-closed.

Corporate Action:

- Corporate Action quantity authority was not changed.

Execution:

- Execution semantics were not changed.
- Projection now persists/materializes basis metadata derived from execution/fill authority.

Strategy:

- No Strategy, threshold, model, or tuning changes were made.

## Regression Results

Focused regression:

- `python3 -m pytest -q tests/runtime_v2/test_phase14e25_runtime_owned_fill_projection.py`
- Result: `17 passed`

Broader regression:

- `python3 -m pytest -q tests/runtime_v2/test_phase17_aa_historical_current_valuation_authority.py tests/runtime_v2/test_phase15aw_market_quote_evidence_producer.py`
- Result: `25 passed`

- `python3 -m pytest -q tests/runtime_v2/test_phase17_bg_empty_no_action_execution_contract.py tests/runtime_v2/test_phase17_g_historical_submit_guard_and_fill.py tests/runtime_v2/test_phase24_ht_planning_submit_feasibility.py`
- Result: `50 passed`

- `python3 -m pytest -q tests/strategy/test_phase22_j_position_sizing.py tests/strategy/test_phase22_g_runtime_planning.py`
- Result: `140 passed`

- `python3 -m pytest -q tests/runtime_v2/test_phase19_bt_reduce_quantity_contract.py tests/runtime_v2/test_phase26_step4_position_sizing_authority.py`
- Result: `23 passed`

- `python3 -m pytest -q tests/runtime_v2/test_phase15az_current_valuation_no_fill_producer.py tests/runtime_v2/test_phase17_ab_current_valuation_pre_gate_authority.py tests/runtime_v2/test_phase17_bv12_current_valuation_symbol_identity.py`
- Result: `31 passed`

- `python3 -m pytest -q tests/runtime_v2/test_phase21_b_pending_composition_add_consumer.py tests/strategy/test_phase26_h_adaptive_buy_quality.py`
- Result: `48 passed`

Final validation:

- `summary.json` parse: PASS
- `py_compile`: PASS
- `git diff --check`: PASS

## Judgment

Primary Judgment:

`PHASE29_L21T_BL_POSITION_BASIS_METADATA_PERSISTENCE_MATERIALIZATION_REPAIRED_FOCUSED_REGRESSION_PASS`

## Runtime Safety

- Runtime mutated: NO
- Fresh-run executed: NO
- Resume/replay/recovery executed: NO
- Phase30 entered: NO

## Recommended Next Action

User-owned post-BL 20BD fresh validation from 2022-08-10.
