# Phase32-L — Campaign Identity Continuity and REENTRY Provenance Actual-Path Repair

## Scope

- Target run evidence: `runtime-test-historical-extended-smoke-20260830T010004222332Z`
- Evidence root: `reports/runtime_tests/runs/runtime-test-historical-extended-smoke-20260830T010004222332Z`
- Source commit recorded by target run jobs: `887a3361eed9f46dccfa6b5b04cb8bb7ee83aa59`
- Repair type: correctness only
- Fresh-run/resume/replay/long Historical: NOT RUN
- Future price/return/regime/MFE/MAE/later outcome/Historical profitability: NOT USED

## Shared Root Cause Assessment

One shared campaign authority boundary explains the campaign split and is a direct cause of REENTRY provenance fragility.

Phase32-K showed that fills and PM artifacts often had the canonical campaign id, while `positions/position_campaigns.json` row-level identity generated a different campaign family. The events inside the same campaign artifact still retained the fill campaign id, proving that the upstream fill/ledger evidence was not absent.

Examples:

- 83060:
  - `2022-10-26` BUY fill campaign: `pc-1533c2a55c4c8bf5-83060-0001`
  - `2022-10-27` position campaign row: `pc-d8c9ed4a368c8b8d-83060-0002`
  - `2022-10-27` PM HOLD campaign: `pc-1533c2a55c4c8bf5-83060-0001`
- 76470:
  - `2022-11-11` BUY_NEW fill campaign: `pc-77ed2705efa03f62-76470-0001`
  - PM ADD campaign: `pc-77ed2705efa03f62-76470-0001`
  - PC/current-position campaign: `pc-08ec9eef313ee674-76470-0002`
  - later BUY_ADD fill campaign: `pc-08ec9eef313ee674-76470-0002`

Root cause:

- `_strict_prior_ledger_campaigns_by_symbol(...)` calls `_new_campaign_from_execution(...)` when a flat position becomes open.
- `_new_campaign_from_execution(...)` always generated a deterministic `pc-<hash>-<symbol>-<ordinal>` id from symbol, ordinal, and execution ref.
- It did this even when the ledger/fill execution row already carried an explicit canonical `position_campaign_id` / `campaign_id`.
- Therefore the campaign observability row body replaced canonical fill/ledger authority with a new generated family.

This also weakens REENTRY provenance because strict-prior closed campaign resolution and PM EXIT context matching depend on stable campaign authority. When the active campaign family is regenerated at the current-position materialization boundary, downstream REENTRY prior context can no longer be accepted as one continuous lifecycle authority.

## First Campaign Identity Split Boundary

First split boundary:

`persistent_ledger/executions.jsonl` BUY row -> `_strict_prior_ledger_campaigns_by_symbol(...)` -> `_new_campaign_from_execution(...)`

The fill/ledger row has the canonical campaign id, but the materialized campaign row generated another id for the same open campaign.

## First REENTRY Provenance Materialization-Loss Boundary

First materialization-loss boundary:

`strict-prior closed campaign / PM EXIT context join` -> REENTRY input materialization

Phase32-J already added source-id PM EXIT lookup, but Phase32-K actual evidence still showed all REENTRY rows with:

- `prior_exit_provenance_status=REVIEW_REQUIRED`: 983 / 983
- non-empty `prior_campaign_id`: 0 / 983
- non-empty `source_pm_decision_id`: 0 / 983
- non-empty `source_decision_id`: 0 / 983

The shared campaign identity split is not the only possible implementation failure mode, but it is a direct authority violation that must be fixed first because REENTRY prior context must point to a stable prior campaign identity.

## Canonical Campaign Authority

For actual runtime lifecycle:

1. BUY_NEW / accepted REENTRY:
   - materialize campaign id once from upstream fill/order/lifecycle authority when present.
   - only generate a deterministic fallback id if canonical upstream id is genuinely absent.
2. HOLD / ADD / REDUCE / EXIT:
   - inherit the same open campaign id.
3. Full EXIT:
   - close that same campaign id.
4. Later accepted REENTRY:
   - create a new campaign id once, again preserving upstream fill/order/lifecycle authority when present.

Forbidden behavior:

- replacing an explicit fill/ledger campaign id with `run/symbol/ordinal` or execution-hash derived ids,
- symbol-only identity,
- downstream current-position regeneration when canonical id exists.

## Canonical Prior Provenance Authority

For REENTRY:

- persistent ledger proves a strict-prior closed campaign exists;
- strict-prior PM EXIT decision artifacts supply the canonical prior EXIT reason/context;
- ledger lifecycle row supplies runtime `source_decision_id`;
- PM EXIT context supplies `source_pm_decision_id`;
- if the join cannot be proven, provenance remains `REVIEW_REQUIRED`.

No synthetic prior campaign id or source decision id is allowed.

## Repair Performed

Changed `src/ai_fund_lab_v2/strategy/shadow_runtime.py`:

- `_new_campaign_from_execution(...)` now preserves explicit campaign identity from the execution row:
  - `position_campaign_id`
  - `campaign_id`
  - `canonical_position_campaign_id`
  - `open_position_campaign_id`
  - `source_position_campaign_id`
- It falls back to deterministic generation only when no upstream campaign id exists.

This is a narrow authority-boundary repair. It does not change PM ADD semantics, PC capital competition, Re-entry thresholds, Buy Quality, Risk Pacing, cash policy, Safety rules, or G129 quantity semantics.

## Files Changed

- `src/ai_fund_lab_v2/strategy/shadow_runtime.py`
- `tests/strategy/test_phase31_g122_campaign_lifecycle_add_history.py`
- `tests/strategy/test_phase29_l21k_prior_exit_materialization.py`
- `docs/phase_reports/phase32_l_campaign_identity_reentry_provenance_actual_path_repair.md`

PM source was not changed.

## PM Re-Acceptance Status

`PM_REACCEPTANCE_REQUIRED=NO`

Reason: `src/ai_fund_lab_v2/runtime_v2/position_management/producer.py` was not modified by Phase32-L.

## Focused Validation Results

PASS:

- `PYTHONPATH=src python3 -m pytest tests/strategy/test_phase31_g122_campaign_lifecycle_add_history.py`
  - 13 passed
- `PYTHONPATH=src python3 -m pytest tests/strategy/test_phase29_l21k_prior_exit_materialization.py`
  - 24 passed
- `PYTHONPATH=src python3 -m pytest tests/runtime_v2/test_phase32_c_provenance_campaign_identity.py`
  - 3 passed
- `PYTHONPATH=src python3 -m pytest tests/strategy/test_phase31_g115_add_marginal_authoritative_binding.py tests/strategy/test_phase31_g44_add_reentry_lot_binding_integration.py`
  - 12 passed
- `PYTHONPATH=src python3 -m pytest tests/strategy/test_phase26_h_adaptive_buy_quality.py tests/strategy/test_phase30_s_position_sizing_production_handoff.py::test_phase30_s_ps_consumes_pc_buy_quality_reason_code_without_rethresholding`
  - 25 passed
- `PYTHONPATH=src python3 -m pytest tests/strategy/test_phase22_e_portfolio_construction.py -k 'reentry or broker or corporate_action'`
  - 7 passed, 117 deselected

New focused cases prove:

- BUY_NEW fill campaign id becomes row-level current-position campaign authority when current snapshot lacks campaign id.
- Accepted REENTRY creates a new campaign id once and later BUY_ADD inherits it.
- 83060-shaped REENTRY prior provenance reaches final REENTRY result with:
  - `prior_campaign_id`
  - `source_pm_decision_id`
  - `source_decision_id`
  - `prior_exit_provenance_status=PASS`
- Missing provenance remains `REVIEW_REQUIRED`.
- Same-day/future evidence remains excluded by existing strict-prior tests.

## Regression Assessment

- Phase32-C regression: NO
- Phase32-F regression: NO
- Phase32-H/J regression: NO
- G129 regression: NO
- KI-004 regression: NO
- Strategy semantic change: NO
- Re-entry policy change: NO
- Safety rule change: NO

## Retest Required

Retest required: YES

Reason: focused/unit regression validates the repaired authority boundary, but current target run artifacts were produced before this Phase32-L repair. A new actual Historical run is required to materialize repaired campaign identity and REENTRY provenance in artifacts.

Exact user command:

```bash
PYTHONPATH=src python3 scripts/runtime_test.py fresh-run --profile historical-extended-smoke --start-date 2022-10-03 --business-days 100 --initial-cash 1000000 --confirm --yes-i-understand-this-mutates-trading-state
```

Codex did not run this command.

## Final Judgment

`PHASE32_L_CAMPAIGN_IDENTITY_AND_REENTRY_PROVENANCE_REPAIRED`

