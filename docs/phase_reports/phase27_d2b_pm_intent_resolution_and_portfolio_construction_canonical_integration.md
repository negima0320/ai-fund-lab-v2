# Phase27-D2-B PM Intent Resolution and Portfolio Construction Canonical Integration

## 1. Scope

Phase27-D2-B adds the shadow `target_portfolio_decision.v1` resolver that consumes `position_intent.v1` as canonical PM directional intent evidence.

```text
Implementation Change: true
Existing Portfolio Construction Decision Change: false
Position Sizing Change: false
Runtime Planning Change: false
Legacy ADD Change: false
Historical Execution: PROHIBITED_NOT_EXECUTED
```

## 2. Primary Judgment

```text
PHASE27_D2B_PM_INTENT_RESOLUTION_COMPLETE_D2C_READY
```

Supporting judgments:

```json
{
  "d2a_evidence_correction": "COMPLETE",
  "pm_consumer_audit": "COMPLETE",
  "target_portfolio_decision_v1": "IMPLEMENTED_SHADOW",
  "pm_intent_resolution": "COMPLETE",
  "action_conflict_handling": "PASS",
  "existing_portfolio_output": "UNCHANGED_CONFIRMED",
  "downstream_decision_effect": "ZERO_CONFIRMED",
  "mode_parity": "CONFIRMED",
  "degression": "PASS",
  "next_entry": "D2-C_APPROVED"
}
```

## 3. D2-A Evidence Correction

D2-A test counts are aligned as:

```text
New D2-A unit tests: 8 passed
Targeted existing regression: 103 passed
Total executed tests: 111 passed
```

## 4. Implemented

- Added `docs/02_architecture/schemas/target_portfolio_decision.v1.schema.json`.
- Added `src/ai_fund_lab_v2/strategy/target_portfolio_decision.py`.
- Added mapping, conflict, mismatch, duplicate, and negative decision-effect tests.
- Generated PM consumer audit, caller inventory, non-change proof, and D2-B evidence JSON.
- Updated the main Momentum Follow SoT with D2-B implementation facts.

## 5. Not Implemented

- Existing Portfolio Construction output replacement.
- Target weight calculation changes.
- Position Sizing connection.
- Runtime Planning connection.
- BUY_ADD generation.
- Legacy ADD migration.
- Pending / Approval / Submit / Execution changes.

## 6. Sample Artifact Evidence

```text
position_intent: /Users/negishi/work/ai-fund-lab-v2/reports/phase27_d2b_pm_intent_resolution_and_portfolio_construction_canonical_integration/sample_runtime_root/strategy_artifacts/position_intent/2026-07-15/position_intent.json
target_portfolio_decision: /Users/negishi/work/ai-fund-lab-v2/reports/phase27_d2b_pm_intent_resolution_and_portfolio_construction_canonical_integration/sample_runtime_root/strategy_artifacts/target_portfolio_decision/2026-07-15/target_portfolio_decision.json
```

## 7. Tests

```text
python3 -m pytest -q tests/strategy/test_phase27_d2a_position_intent.py tests/strategy/test_phase27_d2b_target_portfolio_decision.py
Result: 20 passed

python3 -m pytest -q tests/strategy/test_phase27_d2a_position_intent.py tests/strategy/test_phase27_d2b_target_portfolio_decision.py tests/strategy/test_phase22_e_portfolio_construction.py tests/strategy/test_phase22_j_position_sizing.py tests/strategy/test_phase22_g_runtime_planning.py tests/runtime_v2/test_phase21_b_pending_composition_add_consumer.py
Result: 123 passed
```

No fresh-run, resume, 10BD/100BD Historical, one-year Historical, long smoke, or long regression was executed.
