# Phase15-U Demo Runtime Review Plan

Date: 2026-07-10

Final judgment:

```text
PHASE15U_DEMO_RUNTIME_REVIEW_PLAN_COMPLETE
```

## Purpose

Phase15-U defines the Demo Runtime Review plan before any Demo Runtime execution.

This phase answers:

```text
What to review
In what order
With which evidence
How PASS / REVIEW_REQUIRED / FAIL is judged
```

This phase does not execute Demo Runtime.

## Background

Phase15-S result:

```text
READY_FOR_DEMO_RUNTIME_REVIEW
```

Phase15-T result:

```text
READY_FOR_DEMO_RUNTIME_STATE_REVIEW
```

These mean the implementation is ready to plan Demo Review. They do not mean Demo has been executed, nor that Full Runtime PASS has been granted.

## Review Principles

### Evidence First

No PASS / REVIEW_REQUIRED / FAIL may be declared without artifact evidence.

### Small Batch

Operator commands must be presented in small groups. The default is one or two commands per review step.

### No Hidden PASS

The following are not sufficient for PASS:

- tests pass only
- manifest generated only
- report generated only
- payload generated only
- Broker Accepted only
- Component PASS treated as Flow PASS

### No Production

Production orders are prohibited.

### No Auto Launchd

launchd autonomous operation remains prohibited.

## Review Sequence

Demo Review must proceed in this order:

```text
Preflight Evidence
↓
Morning
↓
Pending / Approval
↓
Submit Guard
↓
REVIEW_REQUIRED scenarios
↓
HALT scenarios
↓
Broker Boundary
↓
Execution
↓
Ledger / Current
↓
Report
↓
Notification
↓
Full Demo Rehearsal
```

Full Demo Rehearsal is planned last and is not executed in Phase15-U.

## Demo Review Plan Matrix

| Step | Objective | Command Type | Required Evidence | PASS Criteria | REVIEW_REQUIRED Criteria | FAIL Criteria | Next Step |
|---|---|---|---|---|---|---|---|
| 0. Preflight Evidence | Confirm demo prerequisites exist before any operation. | Read-only inspection. | Policy artifact, Safety decision artifact, Current state, Pending state, broker readonly snapshot status, runtime root, launchd not used. | Required artifacts exist or missing items are intentionally classified before execution. | Policy/safety/broker snapshot missing but no Runtime execution attempted. | Operator cannot identify runtime root or artifacts; production/launchd path would be used. | Morning Demo Review only after prerequisites are understood. |
| 1. Morning Demo Review | Verify Policy/Safety/Feature/Current flow into Morning Planning. | Demo CLI `morning`, then artifact inspection. | Morning manifest, OrderPlan, Pending, Approval, Report, Notification payload. | Policy and Safety evidence preserved; no hidden max_orders/100k cap; Pending/Approval include policy/safety; Report/Notification show reasons. | Missing policy/safety/feature/current evidence produces REVIEW_REQUIRED with reason and no Submit. | Morning writes invalid Pending/Approval, loses policy/safety, or produces hidden policy-sized orders. | Pending / Approval Review. |
| 2. Pending / Approval Review | Verify canonical Pending and Approval state before Submit. | Read-only artifact inspection. | `pending_order_plan.json`, approval artifact/link, policy hash, safety context. | Pending is approved, target date matches, policy/safety evidence present, approval link present. | Pending not approved, expired, or requires review with clear reason. | Approval artifact becomes Current source, Pending lacks required context, or consumed Pending is reused. | Submit Guard Demo Review. |
| 3. Submit Guard Demo Review | Verify Submit Guard before broker boundary. | Demo CLI `submit` only when prerequisites pass; otherwise inspect expected REVIEW_REQUIRED. | Submit manifest, guard policy, policy consistency, item evidence, broker available quantity evidence for SELL. | Pending/Approval/active policy hash match; Safety ALLOW; BUY/SELL guards separated; SELL uses broker available quantity evidence; broker write only after guard. | Guard blocks before broker write and reason propagates to Manifest/Report/Notification. | Pending consumed without submitted ledger record; guard ignored policy/safety/broker evidence; broker boundary crossed without required evidence. | REVIEW_REQUIRED scenario review. |
| 4. REVIEW_REQUIRED Demo Review | Intentionally validate safe stop paths. | Controlled negative demo commands or fixture-prepared artifacts. | Manifest final_state, Report reason, Notification reason, Pending consume state. | Broker Write does not happen; final_state=REVIEW_REQUIRED; reason and next_operator_action appear in Manifest/Report/Notification; Pending not consumed unless submitted ledger exists. | Any negative scenario stops safely but evidence is incomplete. | Broker Write happens, Pending consumed incorrectly, reason missing, or Notification claims INFO. | HALT scenario review. |
| 5. HALT Demo Review | Validate Safety HALT and emergency_stop behavior. | Controlled safety artifact + demo CLI job. | Safety decision artifact, manifest final_state, Report HALT reason, Notification severity. | Runtime HALT; no broker write; Report/Notification explain HALT/emergency_stop. | HALT stops but reason/next action incomplete. | Runtime proceeds past Safety HALT or writes broker/current incorrectly. | Broker Boundary review. |
| 6. Broker Boundary Review | Verify broker boundary evidence before and after Submit. | Read-only inspection around Submit evidence. | Submit item result, broker adapter evidence, broker readonly snapshot, prohibited actions. | Broker write is guarded, demo-only, and tied to Submit result evidence; SELL available quantity source is explicit. | Broker evidence missing leads to REVIEW_REQUIRED. | Production endpoint/order path used, or Broker Accepted is treated as Full PASS. | Execution / Current Review. |
| 7. Execution / Current Demo Review | Verify Broker ReadOnly -> Ledger -> Current projection. | Demo CLI `execution`, then artifact inspection. | Broker readonly snapshot/report, ledger JSONL, runtime-owned projection, Current state. | Execution evidence enters ledger; runtime-owned fills only update Current; broker-only positions excluded; Current/History/Report not mixed. | Snapshot missing or projection cannot prove runtime-owned fills. | Current overwritten from broker-only positions, Report used as Current, or ledger/current mismatch. | Report / Notification Review. |
| 8. Report / Notification Demo Review | Verify operator explainability. | Read-only report/payload inspection. | Runtime report, public report, notification payload. | Why BUY/SELL/REVIEW_REQUIRED, Policy/Safety/Guard evidence, next_operator_action visible; payload-only fields correct. | Report exists but reason evidence incomplete. | Report/payload claims PASS without evidence, sends notification, or writes Current. | Full Demo Rehearsal planning. |
| 9. Full Demo Rehearsal | Run the full demo sequence only after prior steps pass. | Planned sequence, not executed in Phase15-U. | Morning -> Submit -> Execution -> Current -> Report -> Notification artifacts. | All previous step-level PASS criteria hold in one small full flow. | Any substep enters REVIEW_REQUIRED with clear stop and no unsafe side effects. | Hidden PASS, side effect without guard, Current/History confusion, real send, production order. | Phase after U. |

## Evidence Checklist

| Evidence | Path / Source | Required For | How To Inspect | PASS Condition |
|---|---|---|---|---|
| Capital Deployment Policy | `configs/runtime_v2/capital_deployment.json` | Preflight, Morning, Submit | JSON read / policy manifest in run manifest | Source/version/hash visible and used by Morning/Submit. |
| Safety Decision | `.runtime/runtime_state/safety/latest_safety_decision.json` or date-scoped safety artifact | Preflight, Morning, Submit, HALT | JSON read / safety manifest fields | decision/reason/status/block flags explicit; no placeholder allow. |
| Current State | `.runtime/persistent_ledger/state.json` | Preflight, Morning, Submit, Report | JSON read | Asset SoT exists, environment clear, not derived from report/history. |
| Pending | `.runtime/pending_order_plan/pending_order_plan.json` | Pending/Approval, Submit | JSON read | State, target date, policy/safety context, approval link valid. |
| Approval | Embedded Pending approval + approval artifact path | Pending/Approval, Submit | JSON read | Approved item IDs match Pending; policy/safety evidence preserved. |
| Feature Artifacts | `.runtime/operations/feature_artifacts` | Morning | Directory/artifact inspection | selected feature date and price evidence are valid. |
| Morning Manifest | `.runtime/runtime_state/run_manifest/<date>/runtime-v2-morning-*.json` | Morning | JSON read | Morning stage PASS/REVIEW_REQUIRED with policy/safety details. |
| Submit Manifest | `.runtime/runtime_state/run_manifest/<date>/runtime-v2-submit-*.json` | Submit Guard, REVIEW_REQUIRED | JSON read | Policy consistency, guard evidence, safety, broker evidence present. |
| Broker ReadOnly Snapshot | `.runtime/runtime_state/broker_readonly/<date>/tachibana_snapshot.json` | Broker Boundary, Execution | JSON read | Snapshot created by readonly path; no raw secrets. |
| Ledger Orders | `.runtime/persistent_ledger/orders.jsonl` | Submit, Execution | JSONL tail/read | Submitted order records append only when broker boundary was crossed. |
| Ledger Executions | `.runtime/persistent_ledger/executions.jsonl` | Execution / Current | JSONL tail/read | Execution/equivalent evidence linked to Runtime-owned fills. |
| Current Projection | `.runtime/persistent_ledger/state.json` plus projection stage details | Execution / Current | JSON read + manifest stage | Runtime-owned fills reflected; broker-only positions excluded. |
| Runtime Report | `reports/runtime_v2/<date>/runtime_report.md` and `.json` | Report Review | Markdown/JSON read | Why/Policy/Safety/Guard/Next action present. |
| Public Report | `reports/public/runtime_v2/<date>/public_report.md` and `.json` | Report Review | Markdown/JSON read | Public summary exists, redaction scan passes. |
| Notification Payload | `reports/runtime_v2/<date>/notification_payload.json` | Notification Review | JSON read | `PAYLOAD_ONLY`, `notification_sent=false`, reason summary present. |
| launchd State | `tools/launchd/com.aifundlab.runtime_v2.*.plist` and system operator state | Preflight | File inspection and operator confirmation | Not used for Demo Review; no plist change. |

## Operator Command Plan

Commands below are a plan for a future Demo Review phase. Do not run them during Phase15-U.

Use `<DATE>` as the target business date, for example `2026-07-10`.

### Step 0: Preflight Evidence

Command group 0-A:

```bash
python3 -m json.tool configs/runtime_v2/capital_deployment.json
```

Inspect:

- policy source
- policy version
- target investment ratio
- max exposure
- max position weight

Command group 0-B:

```bash
python3 -m json.tool .runtime/persistent_ledger/state.json
```

Inspect:

- current cash / buying_power / positions
- environment
- review_required

Do not continue if this would require creating/editing Current manually.

### Step 0-C: Safety Evidence

Command group 0-C:

```bash
python3 -m json.tool .runtime/runtime_state/safety/latest_safety_decision.json
```

Inspect:

- `safety_decision_id`
- `decision`
- `reason`
- `block_buy`
- `block_sell`
- `block_submit`
- `halt_runtime`
- `emergency_stop`

If missing, classify Preflight as REVIEW_REQUIRED. Do not create a placeholder allow.

### Step 1: Morning Demo Review

Command group 1-A:

```bash
python3 -m ai_fund_lab_v2.runtime_v2.cli.run_daily_operation \
  --mode demo \
  --job morning \
  --business-date <DATE> \
  --capital-deployment-policy configs/runtime_v2/capital_deployment.json \
  --notification-mode payload-only \
  --stop-on-review-required \
  --stop-on-blocked
```

Expected artifacts:

- `.runtime/runtime_state/run_manifest/<DATE>/runtime-v2-morning-*.json`
- `.runtime/pending_order_plan/pending_order_plan.json`
- `reports/runtime_v2/<DATE>/runtime_report.json`
- `reports/runtime_v2/<DATE>/notification_payload.json`

Command group 1-B:

```bash
python3 -m json.tool .runtime/pending_order_plan/pending_order_plan.json
```

Inspect:

- policy context
- safety context
- approval link
- item estimated_amount / estimated_price source

### Step 2: Morning Manifest / Report Evidence

Command group 2-A:

```bash
ls -t .runtime/runtime_state/run_manifest/<DATE> | head -2
```

Then inspect only the newest morning manifest with:

```bash
python3 -m json.tool .runtime/runtime_state/run_manifest/<DATE>/<MORNING_MANIFEST_FILE>
```

Inspect:

- `capital_deployment_policy_loaded`
- `safety_decision_id`
- `morning_ai_planning_pending_pipeline`
- generated artifacts
- final_state

### Step 3: Submit Guard Demo Review

Only proceed if Pending/Approval are valid and Operator intends to test demo submit boundary.

Command group 3-A:

```bash
python3 -m ai_fund_lab_v2.runtime_v2.cli.run_daily_operation \
  --mode demo \
  --job submit \
  --business-date <DATE> \
  --submit-enabled true \
  --capital-deployment-policy configs/runtime_v2/capital_deployment.json \
  --notification-mode payload-only \
  --stop-on-review-required \
  --stop-on-blocked
```

Inspect expected artifacts:

- submit manifest
- submit guard item evidence
- pending consume state
- ledger orders only if submitted

Command group 3-B:

```bash
ls -t .runtime/runtime_state/run_manifest/<DATE> | head -3
```

Then inspect only the newest submit manifest.

### Step 4: REVIEW_REQUIRED Scenarios

Run these one scenario at a time in a controlled later phase. Do not batch them.

Scenario 4-A: policy missing

```bash
python3 -m ai_fund_lab_v2.runtime_v2.cli.run_daily_operation \
  --mode demo \
  --job morning \
  --business-date <DATE> \
  --notification-mode payload-only \
  --stop-on-review-required
```

Expected:

- final_state=REVIEW_REQUIRED
- no Submit
- Report/Notification show missing policy reason

Scenario 4-B: broker available quantity missing for SELL

Use prepared SELL Pending and no broker available quantity evidence. Then run only submit review.

Expected:

- broker write does not happen
- Pending not consumed
- violated_policy / next_operator_action visible

### Step 5: HALT Scenario

Use a prepared Safety decision artifact with `decision=HALT` or `emergency_stop=true`.

Command group 5-A:

```bash
python3 -m ai_fund_lab_v2.runtime_v2.cli.run_daily_operation \
  --mode demo \
  --job morning \
  --business-date <DATE> \
  --capital-deployment-policy configs/runtime_v2/capital_deployment.json \
  --notification-mode payload-only \
  --stop-on-review-required \
  --stop-on-blocked
```

Expected:

- final_state=HALT or safety stage HALT
- no Broker Write
- Report/Notification explain HALT

### Step 6: Execution / Current Demo Review

Only proceed after Submit boundary evidence exists.

Command group 6-A:

```bash
python3 -m ai_fund_lab_v2.runtime_v2.cli.run_daily_operation \
  --mode demo \
  --job execution \
  --business-date <DATE> \
  --notification-mode payload-only \
  --stop-on-review-required \
  --stop-on-blocked
```

Command group 6-B:

```bash
python3 -m json.tool .runtime/persistent_ledger/state.json
```

Inspect:

- runtime-owned fill projection
- current positions
- excluded broker-only symbols
- review_required

### Step 7: Report / Notification Review

Command group 7-A:

```bash
python3 -m json.tool reports/runtime_v2/<DATE>/runtime_report.json
```

Inspect:

- `reason_evidence`
- `policy_evidence`
- `safety_evidence`
- `submit_guard_evidence`
- `next_operator_action`

Command group 7-B:

```bash
python3 -m json.tool reports/runtime_v2/<DATE>/notification_payload.json
```

Inspect:

- `severity`
- `reason_summary`
- `policy_summary`
- `safety_summary`
- `guard_summary`
- `notification_delivery_status=PAYLOAD_ONLY`
- `notification_sent=false`

### Step 8: Full Demo Rehearsal

Only after prior steps pass.

Planned sequence:

```text
morning
submit
execution
report inspection
notification payload inspection
```

Do not execute Full Demo Rehearsal in Phase15-U.

## Explicitly Prohibited Commands

Do not run:

```bash
python3 -m ai_fund_lab_v2.runtime_v2.cli.run_daily_operation --mode production ...
```

Do not run any command that:

- sends real notifications
- modifies launchd/plist
- edits `.runtime/persistent_ledger/state.json` directly
- bypasses Runtime Guard
- invokes production broker write
- treats fake adapter evidence as Full Runtime PASS

## Phase15-W Amendment

Phase15-W amends this plan from Level3 Runtime operation review to Level4 Purpose-Level Operation Acceptance.

The Demo Review must not only prove:

```text
Runtime ran
```

It must prove:

```text
Runtime does not obstruct policy-designed capital deployment,
stops safely when evidence is missing or unsafe,
preserves state,
explains decisions to the Operator,
and can continue across business days.
```

### Level4 Purpose-Level PASS

Level4 PASS means Runtime:

- does not block annual 50% target pursuit through hidden caps, hidden policy, or unexplained under-deployment
- uses explicit Capital Deployment Policy for sizing and exposure
- stops as REVIEW_REQUIRED or HALT when evidence is missing, stale, unsafe, or production-scoped
- preserves Current / History / Pending / Manifest / Report / Notification boundaries
- explains BUY / SELL / REVIEW_REQUIRED / HALT through Manifest, Report, and Notification
- can continue into the next business day without stale Pending, stale Safety, stale Feature, stale Broker snapshot, or history/current confusion

Level4 PASS is not proven by a single-day happy path.

### Capital Deployment Adequacy Review

After Morning, Operator must verify capital deployment adequacy.

Required evidence:

```text
evaluation_capital
target_investment_ratio
cash_buffer
max_exposure
planned_total_notional
remaining_cash
remaining_buying_power
unused_capital_reason
```

PASS condition:

- Operator can explain why capital remained unused.
- Valid reasons include Policy, Safety, lot size, broker constraint, position limit, price evidence, or insufficient buying power.
- `unused_capital_reason=unknown` or missing explanation is not PASS.

REVIEW_REQUIRED condition:

- planned notional is materially below policy target and no explicit reason exists.
- remaining cash/buying power cannot be explained by policy or broker constraints.

FAIL condition:

- hidden cap, hidden max order amount, hidden position count, or Runtime-local cash buffer explains under-deployment.

### Stale Evidence Stop Gate

Before Demo starts, and again before Submit and Execution, Operator must inspect freshness evidence.

Evidence targets:

```text
Current
Safety
Broker snapshot
Pending
Feature
Approval
```

Required fields where applicable:

```text
generated_at
expires_at
business_date
target_session_date
```

PASS condition:

- evidence is fresh for the intended business date/session.

REVIEW_REQUIRED condition:

- evidence is missing, stale, expired, or mismatched to target session date.

FAIL condition:

- Runtime proceeds using stale evidence without REVIEW_REQUIRED.

### Multi-Day Continuity Review

Full Demo Rehearsal must be extended from single-day to staged multi-day review.

Required continuity sequence:

```text
Day1
↓
Day2
↓
Day3
```

Required checks:

```text
stale Pending
policy change after Pending
carryover
unfilled / partially filled order
Execution incomplete day
Current continuity
History continuity
Report history separation
Notification today-vs-history separation
```

PASS condition:

- next-day Runtime does not use stale Pending, stale Safety, stale Feature, stale Broker snapshot, or stale policy hash.
- Current and Ledger remain consistent across days.
- Reports separate today's operation from cumulative history.

REVIEW_REQUIRED condition:

- previous day operation is unresolved.
- pending target session date is stale.
- policy changed after Pending generation.
- execution evidence is incomplete.

### Operator Manual Procedure

Recovery apply path is not implemented. Therefore REVIEW_REQUIRED handling is manual and must be constrained.

Required procedure:

```text
REVIEW_REQUIRED
↓
Manifest確認
↓
Report確認
↓
Notification確認
↓
Evidence更新
↓
対象Stepだけ再実行
```

Operator must not:

- edit Current directly
- edit Pending directly
- rerun Submit before evidence is refreshed
- restart launchd
- use Notification alone to decide trade action

Notification is triage only. Operator decision must follow:

```text
Manifest
↓
Report
↓
Notification
```

### Production Endpoint Detection

Before Demo, Operator must confirm:

```text
runtime_mode
broker_mode
submit_enabled
endpoint
notification_mode
production flags
```

PASS condition:

- Runtime mode is demo.
- Broker mode / endpoint are demo-scoped.
- notification mode is payload-only.
- production flags are false.

REVIEW_REQUIRED condition:

- endpoint, broker mode, or production flag cannot be confirmed.

FAIL condition:

- production endpoint or production order path is detected.

### Demo Acceptance Stop Gate

Demo must not start or continue when any of the following is true:

```text
cash under-deployment reason unknown
stale Current
stale Safety
stale Broker snapshot
stale Pending
policy changed after Pending
consumed Pending
Current outside projection
missing Report reason
Notification payload-only misread as delivery PASS
Production endpoint
launchd active
```

These are stop conditions, not warnings.

## Phase15-X Amendment: Runtime Reality Rule / Demo-Production Boundary

Phase15-X adds a Demo / Production boundary contract to this Demo Runtime Review Plan. Demo Review must validate the production-baseline Runtime control contract in a Demo broker environment. Demo constraints must be treated as Broker Environment / Broker Capability / Broker Evidence, not as Runtime Core specifications.

### Runtime Reality Rule

```text
Runtime is designed against Production Reality.

Demo constraints are Broker Environment / Broker Capability / Broker Evidence.

Do not create demo-only Runtime, phase-only Runtime, fake Runtime,
demo-only Current, demo-only Ledger, or demo-only Policy.

Demo / Production differences belong at Broker Layer or Capability Layer.
Runtime Core control contracts stay common.
```

### Demo Environment Constraint Check

Before each Demo Review step that touches Broker evidence or Broker boundary, confirm and record:

```text
broker_environment
broker_mode
broker_capability
login_window_status
order_window_status
maintenance_status
demo_execution_restriction_detected
demo_reset_detected
production_equivalent
review_required
```

PASS condition:

- Demo constraints are recorded as Broker Evidence.
- Runtime Core is not modified or bypassed for Demo.
- `production_equivalent=false` is explained and, when material, causes `REVIEW_REQUIRED`.

REVIEW_REQUIRED condition:

- login window, order window, maintenance status, capability, or reset state cannot be confirmed.
- Demo execution restriction is detected and not yet classified.
- Broker evidence is missing or stale.

FAIL condition:

- Demo constraint is hidden inside Runtime Core logic.
- Demo-only Current / Ledger / Policy / Submit / Execution is used as Runtime acceptance evidence.
- Fake adapter evidence is presented as Full Runtime PASS.

### Demo API Error Triage

When a Broker API error occurs during Demo Review, triage in this order before classifying it as a Runtime bug:

```text
1. Broker login window
2. Broker order/execution window
3. Broker maintenance
4. Demo-specific execution restriction
5. Demo reset / account state reset
6. Broker capability mismatch
7. Runtime bug
8. Broker API behavior change
```

The triage result must be carried into Manifest / Report / Notification as Broker Evidence when available. An API error without triage is not Runtime FAIL by itself, but it is not PASS either.

### Demo-Specific Implementation Prohibition

Forbidden:

```text
if demo: special trading logic
if phase15: special Runtime path
demo_current.json
demo_ledger.json as Runtime v2 SoT
demo-only Policy
demo-only Safety
demo-only Submit
demo-only Execution
Demo-only Current projection
Demo-only Report
Runtime bypass to avoid Demo constraints
```

Allowed:

```text
broker_environment=demo
broker_capability
production_equivalent=false
review_required=true
broker evidence classification
```

### Additional Demo Acceptance Stop Gate

Demo must not start or continue when any of the following is true:

```text
broker login window unknown
broker order/execution window unknown
broker maintenance status unknown
demo execution restriction detected but unclassified
demo reset detected but Current is treated as production-equivalent without evidence
broker capability mismatch not reflected in Manifest / Report
Demo-only Runtime path detected
Demo-only Current / Ledger / Policy detected
fake adapter evidence presented as Full Runtime PASS
```

These conditions require evidence refresh, Broker capability classification, or design review before proceeding.

## Phase15-Y Amendment: Non-Trading-Day Demo Acceptance Override

Phase15-Y adds an explicit manual CLI override for Demo Acceptance evidence collection on non-trading days:

```text
--allow-non-trading-day-demo
```

This is not a Runtime Core specification change. It is a Demo Acceptance evidence collection aid under the Runtime Reality Rule.

### Rules

| Case | Acceptance handling |
|---|---|
| Production + override | Must be `BLOCKED`; `reason=non_trading_day_demo_override_forbidden_in_production`. |
| Demo + non-trading day + no override | Must stop with `REVIEW_REQUIRED` or `BLOCKED`; `reason=non_trading_day`. |
| Demo + non-trading day + override | May continue only as `DEMO_ACCEPTANCE_OVERRIDE`; `production_equivalent=false`. |
| Trading day + override | Normal trading-day behavior; override is `false` or `not_applicable`. |

### Required Evidence

Manifest / Report / Notification payload must expose:

```text
trading_day
business_day
market_open
non_trading_day_demo_override
override_source
override_reason
production_equivalent
acceptance_scope
```

### Operator Command Rule

Use this option only for manual Demo Acceptance review. Do not add it to launchd / plist / autonomous operation.

The override result is not Full Runtime PASS, not Production Equivalent, and not Production readiness.

### Additional Stop Gate

Demo must stop when:

```text
--mode production --allow-non-trading-day-demo
non-trading day without explicit override
override evidence missing from Manifest
override evidence missing from Report / Notification when override is active
launchd/plist contains --allow-non-trading-day-demo
```

## PASS / REVIEW_REQUIRED / FAIL Rules

PASS means:

- Required evidence exists.
- Evidence matches the design contract.
- No hidden policy or hidden state is used.
- Report and Notification explain the decision.
- No prohibited side effect occurred.
- Capital deployment adequacy is explained.
- Evidence is fresh for the target session.
- Multi-day continuity is preserved when reviewing Level4.
- Demo / Production differences are represented as Broker Evidence, not Runtime Core behavior.

REVIEW_REQUIRED means:

- Runtime safely stopped.
- Broker Write did not happen unless explicitly expected and guarded.
- Reason appears in Manifest, Report, and Notification.
- `next_operator_action` exists.
- Stale or missing evidence is detected before unsafe operation.
- Operator can resolve by refreshing evidence and rerunning only the relevant step.
- Broker environment / capability / window / maintenance / reset evidence is missing, stale, or unclassified.

FAIL means:

- Broker Write occurs without required guard evidence.
- Production path is used.
- Pending is consumed without submitted ledger evidence.
- Current is edited directly or overwritten from broker-only state.
- Report/Notification claims PASS without evidence.
- Real notification is sent.
- launchd/plist is changed.
- Runtime proceeds with stale evidence.
- Runtime under-deploys capital for an unknown reason.
- Notification is treated as delivery PASS or as a standalone trade decision.
- Demo-specific Runtime / Current / Ledger / Policy / Submit / Execution path is used as acceptance evidence.

## Phase15-U Deliverables

- Demo Review Plan Matrix
- Evidence Checklist
- Operator Command Plan
- Explicit prohibited commands
- PASS / REVIEW_REQUIRED / FAIL rules
- Phase15-W Level4 acceptance amendment
- Capital Deployment Adequacy Review
- Stale Evidence Stop Gate
- Multi-Day Continuity Review
- Operator Manual Procedure
- Production Endpoint Detection
- Demo Acceptance Stop Gate
- Phase15-X Runtime Reality Rule / Demo-Production Boundary amendment
- Demo API Error Triage
- Broker Environment / Capability Evidence checklist

## Phase15-U Prohibited Actions Confirmation

This phase did not perform:

- Demo Runtime execution
- Broker Write
- Demo order
- Production order
- Notification real send
- launchd/plist change
- Current edit
- Runtime bypass
- fake adapter Full Runtime PASS declaration

## Final Judgment

```text
PHASE15U_DEMO_RUNTIME_REVIEW_PLAN_COMPLETE
```
