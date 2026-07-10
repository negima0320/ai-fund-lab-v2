# Phase15-O Runtime Core Mid Review

## Status

`PHASE15O_RUNTIME_CORE_MID_REVIEW_COMPLETE`

Core review judgment:

```text
RUNTIME_CORE_REVIEW_GAPS_FOUND
```

Phase15-H through N materially improved Runtime Core consistency. Capital Deployment Policy, Morning policy propagation, Submit BUY / SELL separation, policy hash consistency, SELL Broker available quantity evidence, and Safety / Operation Guard connection are now present on the normal CLI path and covered by regression.

However, this review does not declare Runtime Core PASS because Planning still creates internal `SafetySignal` placeholder-allow records after the external Runtime Safety gate has passed. The external gate blocks missing / blocked / halt Safety correctly, but the internal placeholder can still be misread as semantic Safety evidence. This is a Core review gap, not a Broker / order execution failure found in this phase.

## Review Scope

Reviewed Runtime Core through:

```text
Capital Deployment Policy
↓
Safety / Operation Guard
↓
Morning Planning
↓
Capital Allocation Evidence
↓
OrderPlan
↓
Pending
↓
Approval
↓
Submit Guard
↓
Broker Submit Boundary
↓
Execution / Fill
↓
Ledger
↓
Current Projection
```

Report / Notification / Operator Review / Demo Operation are not accepted in this phase.

## Runtime Core Flow Matrix

| Boundary | Expected Contract | Implementation Evidence | CLI Evidence | Manifest Evidence | Regression Evidence | Status | Gap |
|---|---|---|---|---|---|---|---|
| Policy -> CLI | Explicit Capital Deployment Policy is required for guarded jobs. No hidden capital defaults. | `load_capital_deployment_policy` requires all fields and raises on missing fields. | `run_daily_operation` loads `--capital-deployment-policy` before guarded jobs. | `capital_deployment_policy` stage and top-level fields. | Phase15-H tests. | PASS | None found. |
| Policy -> Morning | Morning sizing derives from policy, not hidden `max_orders=5` / 100k cap. | `_effective_order_limit`, `_policy_planning_budget`, `_policy_per_order_budget`. | `morning` passes loaded policy into Morning pipeline. | Morning stage has policy source, sizing method, order count source, hidden cap removed. | Phase15-K tests. | PASS | `--max-orders` remains an operator override capped by policy; keep as operator control, not policy source. |
| Safety -> Morning | Missing / blocked / halt Safety stops BUY planning. | `load_runtime_safety_decision` + `safety_allows_action(... side=BUY)`. | `morning` passes CLI-loaded Safety decision into Morning pipeline. | `safety_operation_guard` stage and Morning stage safety fields. | Phase15-N tests. | PASS_WITH_GAP | OrderPlan builder receives internal placeholder `SafetySignal` after external gate. |
| Morning -> OrderPlan | Selected candidates become priced AI / allocation / safety inputs. | Morning builds `PlanningInput`, writes `order_plan.json`. | `morning` normal path invokes pipeline. | Morning stage has order plan path and selected symbols. | Phase14-E15 and Phase15-K tests. | PASS_WITH_GAP | Internal SafetySignal placeholder can confuse semantic evidence. |
| OrderPlan -> Pending | Non-blocked planned items become canonical Pending. | `promote_order_plan_to_pending`, source order plan path/hash retained. | Morning and SELL planning write `.runtime/pending_order_plan/pending_order_plan.json`. | Pending path and pending plan id emitted. | Phase15-K, Phase14-E50 tests. | PASS | None found. |
| Pending -> Approval | Approval links back to Pending and policy context. | `build_approval_request`, `build_approval_artifact`, `link_approval_to_pending`. | Morning / SELL planning build approval artifacts. | Approval path emitted in stage details. | Phase15-K tests. | PASS | None found. |
| Approval -> Submit | Submit consumes approved Pending only and reconstructs linked approval. | `_pending_submit_guard`, `_approval_from_pending`. | `submit` reads Pending current via regular reader. | Submit stage has pending and approval evidence. | Phase14-E17, Phase15-L tests. | PASS | None found. |
| Policy hash consistency | Pending / Approval / active policy hash must match before Submit. | `_policy_consistency_evidence` blocks mismatch/missing evidence. | Submit passes active policy path. | `submit_policy_consistency` top-level and stage details. | Phase15-L tests. | PASS | None found. |
| Safety -> Submit | Missing / block / halt Safety stops before Broker boundary. | `_submit_guard_item_evidence` calls `safety_allows_action`. | CLI passes Safety decision into submit pipeline. | Submit item evidence includes safety fields. | Phase15-N tests. | PASS | None found at Submit boundary. |
| Submit BUY Guard | BUY is new exposure and uses BUY policy only. | `_buy_guard_evidence` checks cash, buying power, exposure, position weight, optional BUY cap. | Submit regular path. | Item guard evidence includes side, policy source, guard decision. | Phase15-I tests. | PASS | None found. |
| Submit SELL Guard | SELL is liquidation / risk reduction and not blocked by BUY cap. | `_sell_guard_evidence` uses Current quantity, Broker available quantity, optional SELL cap only. | Submit regular path. | Item guard evidence separates SELL quantity and policy source. | Phase15-I / M tests. | PASS | None found. |
| SELL Broker available quantity | SELL requires Broker ReadOnly available quantity evidence; Current proxy is forbidden. | `_load_broker_available_quantity_snapshot`, `_broker_available_quantity_evidence`. | Submit loads latest Broker position snapshot before guard. | Broker available quantity fields emitted per item. | Phase15-M tests. | PASS | None found. |
| Submit -> Broker boundary | Guarded items only can reach broker preflight / submit. | Guard evidence is evaluated before `run_submit_preflight` and adapter call. | `submit-enabled=true` allowed only for `submit`; production blocked. | `demo_submit_executed`, result counts, prohibited actions. | Phase14-E17, Phase14-E19, Phase15-N tests. | PASS | Review used fake adapter / fixtures only. |
| Broker / Execution -> Ledger | ReadOnly execution evidence is normalized and appended to ledger; raw secrets not saved. | `run_execution_readonly_pipeline` appends orders/executions/positions/cash/events. | `execution` job invokes ReadOnly pipeline. | Execution stage details include ledger counts and raw value flags. | Phase14-E21, Phase13-O tests. | PARTIAL_CORE | Broker Write / real execution not tested in Phase15-O. |
| Ledger -> Current Projection | Runtime-owned accepted fills project to fixed Current SoT only. | `project_runtime_owned_fills_to_current` uses Runtime-owned accepted submit evidence and ledger positions. | Execution job invokes projection after ReadOnly PASS. | Execution stage details include projection status and excluded broker symbols. | Phase14-E25 test. | PARTIAL_CORE | End-to-end live Runtime evidence not produced in this phase. |

## Hidden Policy Re-Audit

| Hidden Policy Candidate | Evidence Checked | Status | Severity | Follow-up |
|---|---|---|---|---|
| `max_order_amount=100000` | Submit guard now uses `max_buy_order_amount` / `max_sell_liquidation_amount` from explicit policy. Phase15-I regression covers BUY over 100k and SELL over 100k. | NOT_FOUND_IN_CORE_MAINLINE | LOW | Keep no-hidden-policy regression. |
| `max_orders=5` | Morning uses policy `max_positions`; tests assert removed source snippets and policy-driven count. | NOT_FOUND_AS_HIDDEN_DEFAULT | LOW | Keep `--max-orders` as explicit operator override capped by policy. |
| `max_positions=5` hidden default | Loader requires `max_positions`; demo value 5 appears only in explicit policy/fixtures. | NOT_FOUND_AS_HIDDEN_DEFAULT | LOW | Keep manifest source fields. |
| per-order 100k cap | Morning per-order budget derives from planning budget, max position weight, optional policy BUY cap. | NOT_FOUND_IN_CORE_MAINLINE | LOW | Keep Phase15-K budget regression. |
| `estimated_price=1000` fallback | Morning requires price evidence; no-price returns Review Required / no signal. Tests assert generated pending prices are not fallback 1000. | NOT_FOUND_IN_MORNING_MAINLINE | LOW | Extend boundary-price tests later if needed. |
| Runtime-owned cash buffer / target investment ratio / max exposure | Policy loader requires explicit values; Morning and Submit consume policy fields. | NOT_FOUND_AS_RUNTIME_DEFAULT | LOW | Keep policy missing/incomplete tests. |
| Runtime-owned position sizing | Morning sizing derived from Capital Deployment Policy. | NOT_FOUND_AS_HIDDEN_POLICY | LOW | Keep manifest `sizing_policy_reason`. |
| BUY cap applied to SELL | SELL uses optional `max_sell_liquidation_amount`; BUY cap does not stop SELL. | NOT_FOUND | LOW | Keep BUY/SELL separation regression. |
| Safety placeholder allow | External Runtime Safety gate correctly blocks missing / blocked / halt decisions, but internal Planning `_safety` still emits placeholder allow signals. | FOUND_AS_COMPONENT_INTERNAL_PLACEHOLDER | HIGH | Replace internal placeholder with Runtime Safety evidence-derived SafetySignal or clearly separate it from semantic Safety acceptance. |
| Current proxy as Broker available quantity | SELL Submit uses Broker ReadOnly snapshot and blocks missing evidence. | NOT_FOUND | LOW | Keep Phase15-M regression. |

## Review Level

```text
Review Level: Level2 Flow Review with selected Level1 component evidence
Verification Boundary: Static code review + saved report review + regression tests
Fake / fixture usage: Yes, tests use fixtures and fake adapters
Broker Write: Not performed
Demo order: Not performed
Production order: Not performed
Notification real send: Not performed
Launchd: Not modified / not executed as live operation
Full Runtime PASS: No
```

This is not a Level3 Full Runtime Operation review.

## Regression Retention

Executed:

```text
python3 -m pytest tests/runtime_v2/test_phase15n_safety_operation_guard_runtime_connection.py tests/runtime_v2/test_phase15m_sell_broker_available_quantity_evidence.py tests/runtime_v2/test_phase15l_submit_policy_hash_consistency_guard.py tests/runtime_v2/test_phase15k_morning_policy_propagation_hidden_policy_removal.py tests/runtime_v2/test_phase15i_submit_guard_buy_sell_policy_manifest.py tests/runtime_v2/test_phase15h_capital_deployment_policy.py tests/runtime_v2/test_phase14e15_morning_ai_planning_pending_connection.py tests/runtime_v2/test_phase14e36_feature_date_contract_carryover_policy.py tests/runtime_v2/test_phase14e17_submit_pipeline_connection.py tests/runtime_v2/test_phase14e19_submit_issue_code_normalization.py tests/runtime_v2/test_phase14e32_sell_runtime_io_contract.py tests/runtime_v2/test_phase14e50_sell_planning_runtime_connection.py tests/runtime_v2/test_phase14e11_daily_operation_scheduler.py tests/runtime_v2/test_phase13_p_pending_models.py tests/runtime_v2/test_phase13_p_pending_consume.py tests/runtime_v2/test_phase14d14_demo_sell_guarded_preflight.py tests/runtime_v2/test_phase14e21_execution_readonly_pipeline.py tests/runtime_v2/test_phase14e25_runtime_owned_fill_projection.py tests/runtime_v2/test_phase13_o_ledger_models.py
```

Result:

```text
77 passed
```

Covered retention targets:

- Phase15-H Policy loader.
- Phase15-I Submit Guard BUY / SELL evidence.
- Phase15-K Morning policy propagation.
- Phase15-L Policy hash consistency.
- Phase15-M SELL Broker available quantity evidence.
- Phase15-N Safety / Operation Guard connection.
- Pending-only Submit.
- Approval linkage.
- duplicate / consumed Pending guard.
- production submit block.
- issue code normalization.
- no raw request / response / secret fields in ledger models.
- Execution ReadOnly -> Ledger -> Runtime-owned Current projection evidence.

## Core Acceptance Assessment

PASS conditions checked:

- Hidden notional cap no longer found in Submit Core mainline.
- Policy propagates through Morning / Pending / Approval / Submit.
- Submit blocks policy hash mismatch.
- BUY / SELL Guard is separated.
- SELL Broker available quantity is Broker ReadOnly evidence-derived.
- Safety missing / block / halt stops Core paths.
- Existing regression suite passed.
- Broker Write / Demo order / Production order were not performed.

Blocking gap for Core PASS:

- Internal Planning `SafetySignal` placeholder allow remains in Morning and SELL planning after the Runtime Safety gate. The gate prevents unsafe continuation when Safety evidence is missing or blocking, but the placeholder should not be treated as semantic Safety evidence. This should be resolved before declaring Runtime Core review PASS.

## Remaining Non-Core Gaps

Deferred to later Phase15 subphases:

- Report policy reason propagation.
- Notification policy reason propagation.
- Operator Review apply path.
- Demo Operation evidence.
- real notification send.
- Production Broker Write / production unlock.
- launchd automated operation readiness.

## Prohibited Actions Check

Not performed:

- Runtime implementation change
- Gap fix
- Broker Write
- Demo order
- Production order
- Notification real send
- launchd / plist modification
- Current direct edit
- Runtime bypass creation
- fake adapter Full Runtime PASS declaration
- Report / Notification propagation
- Operator Review apply path

## Final Judgment

```text
PHASE15O_RUNTIME_CORE_MID_REVIEW_COMPLETE
```
