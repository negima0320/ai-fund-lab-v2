# Phase27-D2-A Schema / Authority Freeze, Caller Inventory, and Position Intent Foundation

## 1. Scope

Phase27-D2-A implements the minimal `position_intent.v1` shadow foundation and freezes the initial schema/authority boundary.

```text
Implementation Change: true
Runtime Decision Change: false
Strategy Logic Change: false
Historical Execution: PROHIBITED_NOT_EXECUTED
```

## 2. Primary Judgment

```text
PHASE27_D2A_POSITION_INTENT_FOUNDATION_COMPLETE_D2B_READY
```

Supporting judgments:

```json
{
  "caller_inventory": "COMPLETE",
  "schema_freeze": "COMPLETE",
  "position_intent_v1": "IMPLEMENTED_SHADOW",
  "decision_effect": "ZERO_CONFIRMED",
  "mode_parity": "CONFIRMED",
  "degression": "PASS",
  "next_entry": "D2-B_APPROVED"
}
```

## 3. Implemented

- Added `docs/02_architecture/schemas/position_intent.v1.schema.json`.
- Added `src/ai_fund_lab_v2/strategy/position_intent.py`.
- Added unit tests for PM ADD/HOLD/REDUCE/EXIT shadow mapping, missing inputs, accepted-generation mismatch, duplicate dedup key, BUY_NEW unresolved shadow candidate handling, and downstream-field rejection.
- Generated caller inventory and D2-A evidence JSON.
- Updated the D1/D1R main SoT with D2-A implementation facts.

## 4. Not Implemented

- PM -> Portfolio Construction decision connection.
- Legacy ADD retirement or non-decision conversion.
- Position Sizing changes.
- Runtime Planning changes.
- Pending / Approval / Submit / Execution changes.
- Momentum, Incremental Eligibility, ADD, HOLD, REDUCE, EXIT, Quality, Opportunity, or cash policy changes.

## 5. Sample Artifact Evidence

```text
/Users/negishi/work/ai-fund-lab-v2/reports/phase27_d2a_schema_authority_freeze_caller_inventory_and_position_intent_foundation/sample_runtime_root/strategy_artifacts/position_intent/2026-07-15/position_intent.json
```

## 6. Tests

```text
python3 -m pytest -q tests/strategy/test_phase27_d2a_position_intent.py
Result: 8 passed

python3 -m pytest -q tests/strategy/test_phase22_e_portfolio_construction.py tests/strategy/test_phase22_j_position_sizing.py tests/strategy/test_phase22_g_runtime_planning.py tests/runtime_v2/test_phase21_b_pending_composition_add_consumer.py
Result: 103 passed

Combined executed tests:
8 new D2-A tests + 103 targeted existing regression tests = 111 passed

env PYTHONPYCACHEPREFIX=/private/tmp/phase27_d2a_pycache python3 -m py_compile src/ai_fund_lab_v2/strategy/position_intent.py
Result: PASS
```

No fresh-run, resume, 10BD/100BD Historical, one-year Historical, long smoke, or long regression was executed.
