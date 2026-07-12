# Phase15-BO Isolated Normal Submit Acceptance Simulation-Only

## Summary

Phase15-BO executed Runtime Acceptance Step2 for the isolated normal SELL Submit path in simulation-only mode.

Final judgment:

```text
ISOLATED_SIMULATED_SUBMIT_ACCEPTED
```

The accepted scenario proved that an APPROVED Authoritative Pending can pass Submit preconditions, produce a Submit command and broker request payload, cross only a simulation transport boundary, be classified as ACCEPTED, and move the Pending lifecycle to CONSUMED without broker network access, broker write, execution, current mutation, or notification.

## Read Documents

- `docs/02_architecture/runtime_architecture_v2.md`
- `docs/02_architecture/runtime_temporal_freshness_contract.md`
- `docs/02_architecture/runtime_submit_order_condition_authority_contract.md`
- `docs/phase_reports/phase15_bi_system_purpose_phase15_purpose_alignment_review.md`
- `docs/phase_reports/phase15_bj_runtime_acceptance_step2_submit_scope_review.md`
- `docs/phase_reports/phase15_bk_submit_pending_promotion_contract_closure.md`
- `docs/phase_reports/phase15_bl_authoritative_submit_pending_apply_review.md`
- `docs/phase_reports/phase15_bm_safety_blocked_submit_path_closure.md`
- `docs/phase_reports/phase15_bm_isolated_submit_acceptance_scenario_plan.md`
- `docs/phase_reports/phase15_bn_isolated_normal_submit_scenario_preparation.md`
- `docs/phase_reports/phase14_e51_sell_submit_execution_cleanup_cycle.md`
- `docs/phase_reports/phase14_e52_sell_submit_guard_contract_audit.md`
- `docs/phase_reports/phase14_e53_buy_sell_submit_guard_regression_audit.md`
- `src/ai_fund_lab_v2/runtime_v2/submit/`
- `src/ai_fund_lab_v2/runtime_v2/pending/`
- `src/ai_fund_lab_v2/runtime_v2/approval/`
- `src/ai_fund_lab_v2/runtime_v2/execution/`

## Safety Boundary

Allowed scope:

- APPROVED Authoritative Pending read
- Submit precondition evaluation
- Submit command construction
- Broker request payload construction
- Simulation transport
- Submit result classification
- Pending lifecycle update inside isolated runtime root
- Submit Evidence
- Idempotency regression

Forbidden scope result:

| Boundary | Result |
| --- | --- |
| Tachibana Demo API | Not called |
| Real broker client | Not called |
| Broker write | Not performed |
| Execution/fill | Not created |
| Current apply | Not mutated |
| Notification | Not sent |
| Existing `.runtime` mutation | Not mutated |

## Existing Runtime Preservation

Existing Runtime Root:

```text
.runtime
```

The existing Runtime remained the 4591 Safety-blocked evidence root and was not used for normal Submit.

Hash evidence after Phase15-BO:

| Artifact | SHA-256 |
| --- | --- |
| `.runtime/pending_order_plan/pending_order_plan.json` | `84075f23cc6d1c5ae227de1bfe4a213221aefd131fdadb395058755601ac2c77` |
| `.runtime/runtime_state/safety/latest_safety_decision.json` | `c4c1019497fc47b245ad92f21b0b06d59abe32e449f026eb0f9b0aed112faeb7` |
| `.runtime/persistent_ledger/state.json` | `add4f37373c6f7331b6894b29322ffd39a6a0c911086150427d57a2ddb442b0f` |

These match the Phase15-BN baseline.

Result:

```text
existing_runtime_mutated=false
```

## Isolated Runtime Root

Acceptance root:

```text
.runtime_acceptance_phase15_submit
```

Scenario:

| Field | Value |
| --- | --- |
| Side | `SELL` |
| Issue code | `6522` |
| Pending state before Submit | `APPROVED` |
| Order type | `MARKET` |
| Price condition | `MARKET` |
| Limit price | `null` |
| Time in force | `DAY` |
| Target session date | `2026-07-09` |
| Approval hash | `sha256:e0294e64921fed5e136a560bc0ad7d5a15a0ae56663c190ebd9a0cab100955e8` |

## Accepted Submit Simulation Evidence

Evidence artifact:

```text
reports/phase_reports/phase15_bo/simulated_accepted_submit_evidence.json
```

Accepted path:

```text
APPROVED Authoritative Pending
-> Submit Preconditions
-> Submit Command
-> Broker Request Payload
-> Simulation Transport
-> ACCEPTED Classification
-> Pending CONSUMED
-> Submit Evidence
-> Idempotency Blocked Resubmit
```

Observed result:

| Check | Evidence |
| --- | --- |
| Submit preflight | `DRY_RUN_READY` simulation adapter preflight |
| Pipeline result | `PASS` |
| Submit classification | `ACCEPTED` |
| Submitted count | `1` |
| Accepted count | `1` |
| Pending before | `APPROVED` |
| Pending after | `CONSUMED` |
| Pending consumed | `true` |
| Ledger order delta | `1` |
| Network called | `false` |
| Broker client called | `false` |
| Broker write performed | `false` |
| Execution created | `false` |
| Current mutated | `false` |

Pending consume reason:

```text
runtime_v2 submit accepted; automatic resubmit forbidden
```

The isolated ledger received one simulated submit order record with `status=ACCEPTED`, `production_equivalent=false`, and response classification `simulation=true`.

## Submit Command and Request Payload

The request payload was derived from the approved Pending item and did not invent order conditions.

| Field | Value |
| --- | --- |
| `pending_plan_id` | `pending-order-plan-phase15bn` |
| `pending_item_id` | `phase15bn-sell-6522` |
| `issue_code` | `6522` |
| `broker_issue_code` | `6522` |
| `side` | `SELL` |
| `quantity` | `100.0` |
| `order_type` | `MARKET` |
| `price_type` | `MARKET` |
| `limit_price` | `null` |
| `environment` | `demo` |
| `cash_equity_only` | `true` |
| `target_session_date` | `2026-07-09` |
| `raw_request_saved` | `false` |
| `secret_saved` | `false` |
| `network_called` | `false` |

## Idempotency

After the accepted simulation, the same Submit path was attempted again against the same isolated root.

Observed result:

| Check | Evidence |
| --- | --- |
| Second run status | `BLOCKED` |
| Block reason | `dangerous pending state blocked: CONSUMED` |
| Second run submitted count | `0` |
| Second run simulation transport calls | `0` |
| Duplicate order count delta | `0` |
| Idempotency status | `PASS_NO_RESUBMIT` |

Result:

```text
accepted Pending was not resent
```

## Rejected Scenario Regression

Rejected behavior was verified in temporary isolated roots.

Expected and observed:

| Check | Result |
| --- | --- |
| Simulated broker classification | `REJECTED` |
| Pipeline review status | `REVIEW_REQUIRED` |
| Pending after | `REVIEW_REQUIRED` |
| Auto consume | Not performed |
| Execution/current mutation | Not performed |
| Network/broker write | Not performed |

Rejected therefore does not become an execution or current mutation.

## POST_SEND_UNKNOWN Regression

POST_SEND_UNKNOWN behavior was verified in temporary isolated roots.

Expected and observed:

| Check | Result |
| --- | --- |
| Simulated broker classification | `POST_SEND_UNKNOWN` |
| Pipeline review status | `REVIEW_REQUIRED` |
| Pending after | `POST_SEND_UNKNOWN` |
| Immediate second send | Blocked |
| Duplicate order delta | `0` |
| Execution/current mutation | Not performed |
| Network/broker write | Not performed |

POST_SEND_UNKNOWN is therefore retained for broker read-only/human review and is not auto-resent.

## Regression

Commands:

```text
PYTHONPATH=src python3 -m pytest -q tests/runtime_v2/test_phase15bo_isolated_submit_simulation.py
```

Result:

```text
6 passed
```

Broader Submit/Pending/Safety regression:

```text
PYTHONPATH=src python3 -m pytest -q tests/runtime_v2/test_phase15bo_isolated_submit_simulation.py tests/runtime_v2/test_phase15bn_isolated_normal_submit_scenario.py tests/runtime_v2/test_phase15bm_safety_blocked_submit_path.py tests/runtime_v2/test_phase15bl_authoritative_pending_apply_review.py tests/runtime_v2/test_phase15bk_submit_pending_promotion_contract.py tests/runtime_v2/test_phase15n_safety_operation_guard_runtime_connection.py tests/runtime_v2/test_phase15i_submit_guard_buy_sell_policy_manifest.py tests/runtime_v2/test_phase15m_sell_broker_available_quantity_evidence.py tests/runtime_v2/test_phase13_p_pending_no_fallback.py tests/runtime_v2/test_phase13_p_pending_lifecycle.py tests/runtime_v2/test_phase14e17_submit_pipeline_connection.py
```

Result:

```text
58 passed
```

Compile check:

```text
PYTHONPYCACHEPREFIX=/private/tmp/pycache_phase15bo PYTHONPATH=src python3 -m compileall -q src/ai_fund_lab_v2/runtime_v2/submit/pipeline.py tests/runtime_v2/phase15bo_submit_simulation.py tests/runtime_v2/test_phase15bo_isolated_submit_simulation.py
```

Result:

```text
passed
```

## Updated Evidence

- `reports/phase_reports/phase15_bo/simulated_accepted_submit_evidence.json`
- `reports/phase_reports/phase15_bo/evidence_snapshot.json`
- `.runtime_acceptance_phase15_submit/pending_order_plan/pending_order_plan.json`
- `.runtime_acceptance_phase15_submit/persistent_ledger/orders.jsonl`

The updated isolated runtime state is intentional Phase15-BO evidence. Existing `.runtime` was not mutated.

## Remaining Blockers

- Real Tachibana Demo Broker Write has not been accepted.
- Explicit Demo Broker Write review is required before any real broker write.
- Real execution/fill/current reflection remains outside this acceptance.
- Notification remains outside this acceptance.

## Final Judgment

```text
ISOLATED_SIMULATED_SUBMIT_ACCEPTED
```

## Recommended Next Prefix

```text
Phase15-BP Runtime Acceptance Step2 Explicit Demo Broker Write Review
```
