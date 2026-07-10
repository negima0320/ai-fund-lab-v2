# Phase15-E Blocker Fix and Regression Plan

## Summary

Phase15-E defines the blocker fix plan and regression plan before implementation changes.

```text
Implementation Fix is NOT performed in Phase15-E.
```

Phase15-E is limited to:

```text
Fix Plan
Regression Plan
Acceptance Plan
```

No Runtime implementation change, gap fix, Submit execution, Broker Write, Demo order, Production order, Notification real send, launchd/plist change, Current direct edit, Runtime bypass creation, or fake-adapter Full Runtime PASS declaration was performed.

Final judgment: **PHASE15E_BLOCKER_FIX_AND_REGRESSION_PLAN_COMPLETE**

## Evidence Basis

Primary evidence:

- `docs/phase_reports/phase15_c_runtime_architecture_design_implementation_gap_audit.md`
- `docs/phase_reports/phase15_d_historical_regression_coverage_audit.md`
- `docs/02_architecture/runtime_architecture_v2.md`
- `src/ai_fund_lab_v2/runtime_v2/submit/pipeline.py`
- `src/ai_fund_lab_v2/runtime_v2/submit/guards.py`
- `src/ai_fund_lab_v2/runtime_v2/planning/morning_pipeline.py`
- `src/ai_fund_lab_v2/runtime_v2/planning/sell_pipeline.py`
- `src/ai_fund_lab_v2/runtime_v2/cli/run_daily_operation.py`

## Blocker Fix Plan

| Blocker | Current Implementation | Contract Violation | Fix Direction | Files Likely Affected | Regression Required | Severity |
|---|---|---|---|---|---|---|
| Submit hidden cap | `run_submit_pipeline(... max_order_amount=100_000.0)` and side-neutral Submit Guard | Runtime hidden policy; Capital Allocation overwritten after Pending; BUY/SELL >100k blocked; policy source absent | Remove hidden default. Submit must read explicit Capital Deployment / Submit Guard policy. If policy missing, return `REVIEW_REQUIRED` or `BLOCKED`. Split BUY amount policy and SELL liquidation policy. | `submit/pipeline.py`, `submit/guards.py`, `submit/models.py`, `cli/run_daily_operation.py`, report/audit manifest writers | BUY >100k regular CLI; SELL >100k regular CLI; no hidden static default; active policy manifest | `BLOCKER` |
| Morning Planning hidden max orders | `run_morning_ai_planning_pending_pipeline(... max_orders=5)` and CLI `--max-orders default=5` | Runtime controls order/position count as hidden policy instead of Risk Policy / Capital Deployment Contract | Replace default with explicit policy input. If policy missing, do not silently truncate; emit planning-level `REVIEW_REQUIRED` / policy_missing. CLI may accept operator override only as explicit policy source, not hidden default. | `planning/morning_pipeline.py`, `planning/sell_pipeline.py`, `cli/run_daily_operation.py`, policy loader/model | 6+ candidates with no policy; 6+ candidates with explicit policy; max_positions manifest | `BLOCKER` |
| Morning Planning hidden per-order cap | `per_order_budget = min(planning_budget / max_orders, 100_000.0)` | Runtime reintroduces fixed fixture-like allocation and can block target capital deployment | Derive BUY sizing from Capital Deployment Policy: evaluation capital, target investment ratio, cash buffer, max exposure, max position weight, buying power, price, lot size, broker constraint, Safety result. | `planning/morning_pipeline.py`, `planning/planner.py`, policy model/loader, manifest/report/audit | BUY target amount >100k allowed by policy; boundary 99,999/100,000/100,001; no hardcoded cap static test | `BLOCKER` |
| BUY / SELL Guard not separated | `run_submit_preflight` uses common notional guard path and Submit supplies SELL broker quantity from Current | BUY is risk intake while SELL is risk reduction; SELL liquidation can be blocked by BUY cap; Broker available quantity not independently evidenced | Implement side-specific guard evaluation. BUY uses capital/risk/buying-power policy. SELL uses Current-owned position, Current quantity, Broker available quantity, issue-code normalization, Safety/Operation Guard, explicit SELL liquidation policy. | `submit/guards.py`, `submit/pipeline.py`, `submit/models.py`, broker readonly integration, sell planning/manifest | SELL >100k allowed when Current-owned and Broker available; Broker-only exclusion; Broker available lower than Current blocks/review | `BLOCKER` |
| Submit Guard Active Policy Manifest missing | Submit result/stage details show item status/reason but not active policy object | Operator cannot know why Submit allowed/blocked, which policy was used, or whether Planning vs Submit should own the block | Add structured `active_guard_policy` and per-item `guard_evidence` to Submit result. CLI must write it to manifest; Report/Audit must carry source-safe summary. | `submit/models.py`, `submit/pipeline.py`, `submit/guards.py`, `cli/run_daily_operation.py`, report/audit writers, tests | BUY/SELL manifest required fields; violated_policy/source; manual_review_required; report/audit policy propagation | `HIGH` |

## Capital Deployment Policy Proposal

Runtime must not decide this policy. Runtime reads it, validates it, executes it, and emits it.

Recommended policy object:

```json
{
  "policy_version": "capital_deployment_v1",
  "policy_source": "risk_policy/capital_deployment_contract",
  "evaluation_capital": 1000000,
  "target_investment_ratio": 0.85,
  "cash_buffer": 0.05,
  "max_exposure": 850000,
  "max_position_weight": 0.2,
  "max_positions": 5,
  "min_order_amount": 0,
  "max_buy_order_amount": null,
  "max_sell_liquidation_amount": null,
  "buy_notional_policy": "derived_from_capital_allocation_and_constraints",
  "sell_liquidation_policy": "current_owned_available_quantity_policy",
  "manual_review_threshold": {
    "buy_amount": null,
    "sell_liquidation_amount": null
  }
}
```

Policy handling rules:

- Runtime does not invent `evaluation_capital`, `target_investment_ratio`, `cash_buffer`, `max_exposure`, `max_position_weight`, `max_positions`, or order amount caps.
- Runtime may validate a policy object for completeness and consistency.
- If policy is missing, Runtime does not use fallback hidden defaults.
- If policy is missing at Planning, Planning returns `REVIEW_REQUIRED` or `BLOCKED` with `policy_missing`.
- If policy is missing at Submit, Submit returns `REVIEW_REQUIRED` or `BLOCKED` with `policy_missing`.
- Active policy must be emitted to manifest / report / audit.
- Any operator CLI override must be recorded as `policy_source=operator_cli_explicit`, not treated as default.

Recommended source priority:

1. Approved Risk Policy / Capital Deployment Contract artifact.
2. Explicit operator policy artifact for demo operation.
3. Explicit CLI override only for controlled tests, with policy source emitted.
4. No implicit fallback. Missing policy is `REVIEW_REQUIRED` or `BLOCKED`.

## BUY Policy

BUY is new risk intake. Submit Guard must not reallocate capital, but it may block or review a BUY if explicit policy or operational safety is violated.

BUY validation inputs:

- Capital Allocation amount
- cash / buying_power
- max exposure
- max position weight
- price
- lot size
- broker constraint
- Safety result
- pending/approval linkage
- duplicate submit guard
- broker capability

BUY block/review evidence must include:

- `violated_policy`
- `violated_policy_source`
- `should_have_been_blocked_at_planning`
- `blocked_at_submit_reason`
- `manual_review_required`
- `capital_allocation_amount`
- `estimated_amount`
- `max_buy_order_amount`
- `notional_guard_source`

Recommended rule:

```text
BUY order size is valid if it is derived from Capital Allocation and remains within explicit Risk / Capital Deployment / Broker / Safety constraints.
Submit Guard must not apply a hidden fixed amount cap after Planning.
```

## SELL Policy

SELL is risk reduction. SELL liquidation must not be blocked by BUY notional cap.

SELL validation inputs:

- SELL source is Runtime-owned Current position
- quantity <= Current quantity
- quantity <= Broker available quantity
- Broker-only position is not sold
- Broker issue code normalization is valid
- explicit SELL liquidation policy is satisfied
- Safety / Operation Guard does not stop execution
- duplicate submit / rerun guard passes

SELL high-notional policy candidates:

| Candidate | Meaning | Pros | Cons | Recommendation |
|---|---|---|---|---|
| Allow if Runtime-owned and available quantity confirmed | SELL amount has no fixed cap when it reduces Runtime-owned exposure and Broker available quantity is confirmed | Best matches risk-reduction contract; avoids blocking liquidation | Requires strong Broker ReadOnly evidence | Recommended default for demo and normal liquidation |
| Review above configured liquidation threshold | Large SELL is allowed only after manual review threshold | Adds human safety for unusually large liquidation | Can delay risk reduction | Use only when explicit policy config defines threshold |
| Split order | Large SELL is split into smaller orders | May reduce broker/order-size risk | Adds partial fill and rerun complexity | Optional only if broker or policy requires it |
| Quantity reduction | Reduce SELL quantity until under threshold | Prevents oversized order | Leaves residual risk unintentionally | Not recommended unless explicit policy requires it |

Recommended SELL rule:

```text
SELL liquidation is allowed when the position is Runtime-owned, quantity is within Current and Broker available quantity, and explicit SELL liquidation policy allows it. BUY max notional policy does not apply.
```

If SELL is blocked or reviewed, manifest must show:

- whether source was Current-owned
- Current quantity
- Broker available quantity
- `current_position_source`
- `quantity_guard_source`
- `max_sell_liquidation_amount`
- `violated_policy`
- `violated_policy_source`
- `manual_review_required`

## Submit Guard Active Policy Manifest Design

Submit manifest / audit / report must include a run-level policy object and per-item guard evidence.

Run-level structure:

```json
{
  "guard_policy_version": "submit_guard_v1",
  "active_amount_policy": {
    "policy_version": "capital_deployment_v1",
    "policy_source": "risk_policy/capital_deployment_contract",
    "target_investment_ratio": 0.85,
    "cash_buffer": 0.05,
    "max_position_weight": 0.2,
    "max_positions": 5,
    "max_buy_order_amount": null,
    "max_sell_liquidation_amount": null,
    "notional_guard_source": "capital_deployment_contract",
    "quantity_guard_source": "current_and_broker_available_quantity"
  }
}
```

Per-item structure:

```json
{
  "side": "BUY",
  "estimated_amount": 200000,
  "capital_allocation_amount": 200000,
  "max_buy_order_amount": null,
  "max_sell_liquidation_amount": null,
  "target_investment_ratio": 0.85,
  "cash_buffer": 0.05,
  "max_position_weight": 0.2,
  "max_positions": 5,
  "notional_guard_source": "capital_deployment_contract",
  "quantity_guard_source": "broker_capability_or_current_position",
  "current_position_source": "",
  "broker_available_quantity_checked": false,
  "guard_decision": "ALLOW",
  "guard_reason": "within explicit BUY policy",
  "manual_review_required": false,
  "violated_policy": "",
  "violated_policy_source": "",
  "should_have_been_blocked_at_planning": false,
  "blocked_at_submit_reason": ""
}
```

For SELL, `broker_available_quantity_checked` must be true before normal allowance, and `current_position_source` must reference Runtime-owned Current SoT.

## Regression Plan

| Regression | Condition | Expected Result | Path | Severity |
|---|---|---|---|---|
| BUY 10万円超 | evaluation capital 1,000,000; target allocation produces BUY amount >100,000; explicit policy allows it | Submit Guard does not stop on hidden 100,000 cap; active policy source appears in manifest | CLI regular path: `morning` -> `submit`; direct unit also allowed | `BLOCKER` |
| SELL 10万円超 | Runtime-owned Current position market value >100,000; quantity <= Current; Broker available quantity confirmed; SELL policy allows it | BUY cap does not stop SELL; SELL policy decides; manifest shows SELL policy source | CLI regular path: `sell_planning` -> `submit`; submit guard unit | `BLOCKER` |
| max_orders / max_positions hidden default prohibited | 6+ candidate/planned orders; no explicit policy | Runtime does not silently cut to 5; returns `REVIEW_REQUIRED` or Planning reason with `policy_missing` | `morning` CLI and planning unit | `BLOCKER` |
| Capital Deployment Contract missing | No Capital Deployment Policy artifact/input | No hidden fallback; `REVIEW_REQUIRED` / `BLOCKED`; manifest shows `policy_missing` | `morning`, `sell_planning`, `submit` CLI | `BLOCKER` |
| Submit Guard Active Policy Manifest | BUY and SELL pending items | Required policy fields appear; guard decision/reason/source appears for each item | Submit unit and CLI manifest | `HIGH` |
| CLI regular path policy consistency | `run_daily_operation --job morning`, `--job sell_planning`, `--job submit` | Same policy object used as direct pipeline; manifest proves source | CLI tests without monkeypatching policy | `HIGH` |
| No hidden policy static test | mainline Runtime code scanned for `max_order_amount=100000`, `max_orders=5`, `max_positions=5`, `estimated_price=1000`, hardcoded cash buffer/investment ratio | No hidden defaults remain in regular Runtime path | Static test over `src/ai_fund_lab_v2/runtime_v2` | `HIGH` |
| BUY boundary values | 99,999 / 100,000 / 100,001 with explicit policy | Decision follows policy, not magic number | Submit guard unit + CLI manifest | `HIGH` |
| SELL available quantity mismatch | Current quantity > Broker available quantity | SELL is blocked/reviewed by quantity policy, not notional cap | Submit guard unit; later CLI with Broker evidence fixture | `HIGH` |
| POST_SEND_UNKNOWN rerun | Submitted unknown item exists and pending rerun occurs | No auto-resend; Review Required / dedup evidence emitted | Submit state/idempotency test | `BLOCKER` |

## Acceptance Plan

Phase15 blocker fixes can be accepted only when all of the following align:

```text
Design Contract
↓
Implementation
↓
CLI Regular Path
↓
Runtime Manifest
↓
Report / Audit Evidence
↓
Regression
```

Acceptance conditions:

- Hidden `max_order_amount=100000` is absent from regular Runtime path.
- Hidden `max_orders=5` / `max_positions=5` is absent unless explicit policy source is present.
- Hidden `per_order_budget` cap of 100,000 is absent.
- BUY and SELL guards are side-specific.
- SELL liquidation is not blocked by BUY cap.
- Submit Guard Active Policy Manifest exists for BUY and SELL.
- Missing Capital Deployment Policy produces `REVIEW_REQUIRED` or `BLOCKED`, not fallback.
- CLI regular path proves the same behavior as direct pipeline tests.
- Regression covers above-100k BUY and SELL, 6+ candidates, missing policy, active manifest, and static hidden policy scan.

Non-acceptance examples:

- `tests pass` alone is not PASS.
- `Broker Accepted` alone is not PASS.
- `Report generated` alone is not Report semantic PASS.
- `Payload generated` alone is not Notification PASS.
- fake adapter evidence is not Full Runtime PASS.

## Next Phase Recommendation

The next implementation phase should proceed in this order:

1. Add Capital Deployment Policy model/loader and missing-policy behavior.
2. Remove Submit hidden amount default and implement side-specific BUY/SELL guard policy.
3. Remove Morning hidden `max_orders=5` and per-order 100,000 cap.
4. Add Submit Guard Active Policy Manifest.
5. Add regression suite before or alongside each implementation slice.
6. Run only safe static/unit/CLI tests first; defer Demo operation until blocker regressions are green.

## Final Judgment

```text
PHASE15E_BLOCKER_FIX_AND_REGRESSION_PLAN_COMPLETE
```
