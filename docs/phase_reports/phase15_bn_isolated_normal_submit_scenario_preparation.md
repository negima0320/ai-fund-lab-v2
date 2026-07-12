# Phase15-BN Isolated Normal Submit Scenario Preparation

## Summary

Phase15-BN prepared a reproducible isolated normal Submit scenario without modifying the existing `.runtime` root.

Final judgment:

```text
ISOLATED_SCENARIO_READY
```

The scenario reached no-send Submit preflight READY in an isolated root. Broker client preflight/send was not called. Broker Write, Execution, Current Apply, and Notification Send were not performed.

## Read Documents

- `docs/02_architecture/runtime_architecture_v2.md`
- `docs/02_architecture/runtime_temporal_freshness_contract.md`
- `docs/phase_reports/phase15_bi_system_purpose_phase15_purpose_alignment_review.md`
- `docs/phase_reports/phase15_bj_runtime_acceptance_step2_submit_scope_review.md`
- `docs/phase_reports/phase15_bk_submit_pending_promotion_contract_closure.md`
- `docs/phase_reports/phase15_bl_authoritative_submit_pending_apply_review.md`
- `docs/phase_reports/phase15_bm_safety_blocked_submit_path_closure.md`
- `docs/phase_reports/phase15_bm_isolated_submit_acceptance_scenario_plan.md`
- `docs/phase_reports/phase14_e51_sell_submit_execution_cleanup_cycle.md`
- `docs/phase_reports/phase14_e52_sell_submit_guard_contract_audit.md`
- `docs/phase_reports/phase14_e53_buy_sell_submit_guard_regression_audit.md`
- `src/ai_fund_lab_v2/runtime_v2/pending_promotion.py`
- `src/ai_fund_lab_v2/runtime_v2/pending_apply.py`
- `src/ai_fund_lab_v2/runtime_v2/submit/`
- `src/ai_fund_lab_v2/runtime_v2/pending/`
- `src/ai_fund_lab_v2/runtime_v2/execution/`

## Existing Runtime Preservation

Existing Runtime Root:

```text
.runtime
```

Preserved as 4591 Safety-blocked evidence. It was not used for normal Submit.

Hash evidence before and after BN:

| Artifact | SHA-256 |
| --- | --- |
| `.runtime/pending_order_plan/pending_order_plan.json` | `84075f23cc6d1c5ae227de1bfe4a213221aefd131fdadb395058755601ac2c77` |
| `.runtime/runtime_state/safety/latest_safety_decision.json` | `c4c1019497fc47b245ad92f21b0b06d59abe32e449f026eb0f9b0aed112faeb7` |
| `.runtime/persistent_ledger/state.json` | `add4f37373c6f7331b6894b29322ffd39a6a0c911086150427d57a2ddb442b0f` |

Result:

```text
existing_runtime_mutated=false
```

## Isolated Runtime Root

Created:

```text
.runtime_acceptance_phase15_submit
```

Scenario manifest:

```text
.runtime_acceptance_phase15_submit/scenario_manifest.json
```

The isolated root contains separate:

- Runtime State
- Pending
- Human Approval
- Promotion Candidate
- Apply Candidate
- Safety Decision
- Current
- Broker Evidence
- Broker Capability Evidence
- Run Manifest / Logs / Reports directories

No symlink or fallback to existing `.runtime` is used.

## Normal Submit Scenario

Selected scope:

```text
SELL normal scenario
```

Target issue code:

```text
6522
```

This is an explicit Acceptance fixture, not an investment decision. 4591 is not used.

Scenario evidence:

- Safety action scope: `sell_submit=ALLOWED`, `broker_write=ALLOWED_FOR_ACCEPTANCE`
- Market / Quote: `READY`
- Broker ReadOnly: `READY`
- Current: `READY`
- Policy: `READY`
- Human Approval: valid
- Promotion Candidate: valid
- Apply Candidate: valid
- Pending: `APPROVED`
- Target Session: valid
- Order Conditions: approved
- Broker available quantity: sufficient

## Order Condition Authority

Contract created:

```text
docs/02_architecture/runtime_submit_order_condition_authority_contract.md
```

Resolved status:

```text
ORDER_CONDITION_AUTHORITY_READY
```

Authority split:

- Policy defines allowed order methods and constraints.
- Human Approval approves concrete item order conditions.
- Submit Pending Producer freezes approved conditions into Pending.
- Broker Capability Evidence verifies supported side/order/session/cash/demo constraints.
- Submit Runtime sends approved conditions unchanged.

Scenario order condition:

```text
order_type=MARKET
price_condition=MARKET
limit_price=null
target_session=2026-07-09
time_in_force=DAY
```

Submit preflight now blocks unresolved or unapproved order conditions before the Broker client boundary.

## Broker Capability

Broker capability evidence:

```text
.runtime_acceptance_phase15_submit/runtime_state/broker_capability/2026-07-09/broker-capability-demo.json
```

Status:

```text
READY
```

Verified:

- SELL side accepted for fixture
- MARKET order type accepted
- Target session accepted
- Quantity/trading unit declared
- Limit price validation not applicable for MARKET
- Cash equity only
- Demo environment

## Authoritative Pending

The isolated root contains an `APPROVED` Pending fixture:

```text
.runtime_acceptance_phase15_submit/pending_order_plan/pending_order_plan.json
```

This is isolated fixture materialization for Acceptance preflight. It is not an Apply to existing `.runtime`, and it did not perform Broker Write.

## No-Send Submit Preflight

Command:

```bash
PYTHONPATH=src python3 -c '... run_submit_preflight(...) ...'
```

Observed:

```json
{
  "pending_read_valid": true,
  "pending_path": ".runtime_acceptance_phase15_submit/pending_order_plan/pending_order_plan.json",
  "pending_state": "APPROVED",
  "preflight_allowed": true,
  "preflight_blocked": false,
  "preflight_reason": "approved",
  "command_symbol": "6522",
  "command_order_type": "MARKET",
  "broker_client_called": false,
  "broker_write_performed": false
}
```

Classification:

```text
submit_preflight_status=READY
submit_attempted=false
broker_client_called=false
broker_write_performed=false
```

## Hidden Fixed Path Audit

Finding fixed:

- Submit pipeline previously resolved Pending through `runtime_root.parent + .runtime/...`.
- BN changed it to read `runtime_root/pending_order_plan/pending_order_plan.json`.

Regression confirms the submit pipeline reports the isolated Pending path and does not read existing `.runtime`.

## Regression

Command:

```bash
PYTHONPATH=src python3 -m pytest -q tests/runtime_v2/test_phase15bn_isolated_normal_submit_scenario.py tests/runtime_v2/test_phase15bm_safety_blocked_submit_path.py tests/runtime_v2/test_phase15bl_authoritative_pending_apply_review.py tests/runtime_v2/test_phase15bk_submit_pending_promotion_contract.py tests/runtime_v2/test_phase15n_safety_operation_guard_runtime_connection.py tests/runtime_v2/test_phase15i_submit_guard_buy_sell_policy_manifest.py tests/runtime_v2/test_phase15m_sell_broker_available_quantity_evidence.py tests/runtime_v2/test_phase13_p_pending_no_fallback.py tests/runtime_v2/test_phase13_p_pending_lifecycle.py
```

Result:

```text
48 passed
```

Compile check:

```bash
PYTHONPYCACHEPREFIX=/private/tmp/pycache_phase15bn PYTHONPATH=src python3 -m compileall -q src/ai_fund_lab_v2/runtime_v2/approval/models.py src/ai_fund_lab_v2/runtime_v2/pending/models.py src/ai_fund_lab_v2/runtime_v2/approval/linkage.py src/ai_fund_lab_v2/runtime_v2/pending/promotion.py src/ai_fund_lab_v2/runtime_v2/pending/reader.py src/ai_fund_lab_v2/runtime_v2/submit/pipeline.py src/ai_fund_lab_v2/runtime_v2/submit/guards.py tests/runtime_v2/phase15bn_isolated_submit_fixture.py tests/runtime_v2/test_phase15bn_isolated_normal_submit_scenario.py
```

Result: PASS

## Runtime Mutation

Existing `.runtime`:

- Not mutated
- Safety not changed
- 4591 not reused
- Existing Pending not changed
- Existing Current not changed
- Existing Ledger not changed

Isolated root:

- Created `.runtime_acceptance_phase15_submit`
- Created Acceptance fixture artifacts
- Created `scenario_manifest.json`

No Broker Write, real Submit, Execution, Current Apply, Notification Send, Production Write, or launchd change occurred.

## Remaining Blockers

None for isolated scenario preparation.

Remaining future scope:

- BO must decide whether normal Submit Acceptance uses Demo Broker Write with explicit authorization or complete simulation.
- BUY Submit Acceptance remains outside this SELL-first scenario.

## Final Judgment

```text
ISOLATED_SCENARIO_READY
```

## Recommended Next Prefix

```text
Phase15-BO Runtime Acceptance Step2 Isolated Normal Submit Acceptance
```
