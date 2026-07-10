# Phase15-V Purpose-Level Runtime Acceptance Meta Review

Date: 2026-07-10

Final judgment:

```text
PHASE15V_PURPOSE_LEVEL_RUNTIME_ACCEPTANCE_META_REVIEW_COMPLETE
```

## Purpose

Phase15-V reviews the acceptance plan itself before Demo Runtime execution.

This phase does not implement fixes and does not execute Demo. It checks whether Phase15-U's Demo Runtime Review Plan is sufficient against the purpose of AI Fund Lab v2 and Phase15.

AI Fund Lab v2 purpose:

```text
年間50%の利益を目指し、安心・安全に自動売買を継続できる運用システムを実現すること
```

Phase15 purpose:

```text
Runtimeという制御システムへの信頼を確立すること
```

The acceptance question is:

```text
Can Runtime support capital deployment toward the annual 50% goal,
stop safely when evidence is missing or risk is unacceptable,
remain consistent across Broker / Current / Report / Notification,
and give the Operator enough evidence to understand what happened?
```

## Executive Conclusion

Phase15-U is a strong stepwise Demo Review plan, but Purpose-Level Acceptance still has gaps.

The main gaps are not Runtime Core implementation gaps. They are acceptance-plan gaps:

- under-deployment / cash underuse is not yet explicitly reviewed against the Capital Deployment Policy
- multi-day continuous operation risks are not yet detailed enough
- stale Current / stale Safety / stale Broker snapshot / stale Pending checks need explicit stop gates
- production endpoint detection needs explicit evidence
- Operator manual handling when apply/recovery paths are absent needs a clearer Demo rule
- notification payload-only misinterpretation is covered, but real-send disabled evidence should be inspected explicitly

Final recommendation:

```text
DEMO_ACCEPTANCE_PLAN_GAPS_FOUND
```

This means: do not start Demo Runtime evidence review until Phase15-U is amended with the required follow-ups listed here.

## Purpose-Level Acceptance Matrix

| Area | Purpose Requirement | Current Coverage | Gap | Severity | Required Follow-up |
|---|---|---|---|---|---|
| Annual 50% target | Runtime must not obstruct policy-designed capital deployment with hidden caps. | Phase15-H/K/I/L removed hidden order/position caps and added policy evidence; Phase15-U checks no hidden max_orders/100k cap. | Phase15-U does not explicitly require cash under-deployment reason or target investment ratio realization check after Morning. | HIGH | Add Demo evidence that planned BUY notional, available cash, cash buffer, max exposure, and uninvested cash reason match Capital Deployment Policy. |
| Safe operation | Runtime must stop when Safety/Broker/Policy evidence is missing or unsafe. | Phase15-U covers policy missing, safety missing, broker quantity missing, REVIEW_REQUIRED, HALT. | Stale Safety, stale Broker snapshot, stale Current, and production endpoint detection are not fully specified as evidence gates. | HIGH | Add explicit stale evidence and production endpoint stop gates. |
| Automated trading | Runtime should automate safe path and isolate manual intervention points. | Phase15-U separates normal path, REVIEW_REQUIRED, HALT, and Full Demo Rehearsal. | Operator Review apply path and Recovery path are absent; manual handling rule is not explicit enough. | MEDIUM | Define Demo manual handling: stop, inspect, do not mutate Current/Pending directly, rerun only from approved step. |
| Continuous operation | Runtime must support more than one day of operation. | Phase15-U mentions Full Demo Rehearsal and current/ledger/report boundaries. | Multi-day carryover, stale Pending, policy changed after Pending, unexecuted prior day, and report history mixing are not detailed. | HIGH | Add Day+1 / carryover Demo Review section before Full Demo Rehearsal acceptance. |
| Explainability | Operator must understand why BUY/SELL/STOP happened. | Phase15-R/S/U cover Report/Notification reason evidence and next_operator_action. | Notification-only decision is risky; U should require checking the full Report for REVIEW_REQUIRED before action. | MEDIUM | Add rule: Notification is triage only; Report + Manifest are required for operator decision. |

## Acceptance Layer Review

| Level | Name | Definition | Acceptance Evidence | Phase15-V Finding |
|---|---|---|---|---|
| Level1 | Component | Individual module behavior is correct. | Unit tests / local artifacts. | Necessary but insufficient. |
| Level2 | Flow | Component boundaries pass evidence across a runtime flow. | CLI path, manifests, Pending/Approval/Submit artifacts. | Mostly covered by Phase15-H through R. |
| Level3 | Full Runtime Operation | Runtime operates the full demo flow from planning to report/notification with coherent state. | Stepwise Demo evidence and Full Demo Rehearsal. | Planned but not executed. |
| Level4 | Purpose-Level Operation Acceptance | Runtime supports the system purpose: capital deployment according to policy, safe stopping, Broker/Current/Report/Notification consistency, and Operator-understandable evidence across repeated operation. | Multi-day evidence, capital deployment adequacy, negative tests, state continuity, operator stop/recovery procedure. | Not yet fully covered by Phase15-U. |

## Level4 Acceptance Definition

```text
Level4 Purpose-Level Operation Acceptance
```

Level4 acceptance means:

1. Runtime does not introduce hidden policies that reduce or distort Capital Deployment Policy.
2. Runtime can explain under-deployment, not just prevent over-deployment.
3. Runtime stops safely for missing/stale Policy, Safety, Broker, Current, Pending, or endpoint evidence.
4. Runtime preserves state consistency across Broker, Ledger, Current, Manifest, Report, and Notification.
5. Runtime remains understandable to the Operator through Manifest + Report + Notification.
6. Runtime can repeat across multiple business days without stale artifacts, duplicate pending, stale safety, stale broker evidence, or report/history confusion.
7. Runtime distinguishes demo acceptance from production readiness.

Level4 is not proven by:

- one successful component test
- one CLI run
- Broker Accepted only
- Report generated only
- payload generated only
- fake adapter success
- a single-day happy path

## Demo Plan Gap Matrix

| Demo Step | Adequate? | Missing Evidence | Missing Negative Test | Required Plan Update |
|---|---|---|---|---|
| Preflight | PARTIAL | stale Current, stale Safety, stale Broker snapshot age, production endpoint config, launchd active status evidence | production endpoint detected, launchd active, stale safety | Add Preflight Stop Gate checklist with timestamps and endpoint/mode validation. |
| Morning | PARTIAL | target investment ratio realization, cash under-deployment reason, available cash/cash buffer/max exposure comparison | stale feature, policy changed after feature/pending | Add capital deployment adequacy checks and feature freshness checks. |
| Pending / Approval | PARTIAL | pending age, approval expiry, policy version changed after pending, stale target date | stale Pending, consumed Pending, expired Pending | Add stale/expired/consumed Pending negative tests. |
| Submit Guard | MOSTLY | explicit broker endpoint/mode evidence before submit, active policy hash vs pending/approval after policy change | production endpoint, policy changed after pending | Add endpoint evidence and policy-changed-after-pending scenario. |
| REVIEW_REQUIRED | PARTIAL | stale Current, stale Pending, stale Broker snapshot, missing Report reason | stale Current / stale Pending / missing report reason | Add stale evidence negative cases. |
| HALT | ADEQUATE | emergency_stop evidence path and notification severity check are present conceptually | stale HALT artifact age | Add HALT artifact freshness check. |
| Broker Boundary | PARTIAL | broker readonly snapshot timestamp, account/mode identifier, endpoint safety evidence | production endpoint detected, stale broker snapshot | Add broker snapshot freshness and endpoint mode check. |
| Execution / Current | PARTIAL | prior-day unexecuted order handling, Current/Ledger continuity across day boundary | execution not completed before next day, broker-only position carryover | Add Day+1 continuity scenario. |
| Report / Notification | MOSTLY | notification real-send disabled evidence, manifest/report/payload consistency on negative scenarios | missing report reason, payload-only misread as delivery PASS | Add explicit real-send-disabled and notification-is-triage-only checks. |
| Full Demo Rehearsal | PARTIAL | multi-day continuity, capital deployment adequacy, review-required unresolved stop | next-day stale artifacts, unresolved REVIEW_REQUIRED | Split into Day 1 and Day 2 rehearsal gates. |

## Historical Failure Detection Matrix

| Historical Failure | Detected By Demo Plan? | Evidence Required | Gap | Action |
|---|---|---|---|---|
| hidden 10万円cap | YES | Morning/Submit planned notional and policy max_buy_order_amount evidence. | Need under-deployment check to catch too-small orders even without explicit cap. | Add cash under-deployment reason check. |
| hidden 5件cap | YES | Morning selected count source and policy max_positions evidence. | Operator `--max-orders` must be distinguished from hidden policy. | Add explicit operator override evidence check. |
| BUY/SELL共通Guard | YES | Submit guard item evidence by side. | None for Phase15-U. | Keep BUY/SELL separate evidence mandatory. |
| Safety placeholder allow | YES | Safety decision artifact and planning/pending safety context. | Stale safety decision freshness not explicit. | Add safety generated_at/expires_at check. |
| Current proxy used as Broker available quantity | PARTIAL | SELL guard broker_available_quantity_source and broker snapshot. | Current-vs-broker source check must be explicit. | Add fail if source is Current-only for broker availability. |
| Report generated = PASS誤認 | YES | Report reason_evidence and redaction/status check. | Operator decision should require Manifest + Report, not report existence. | Add no Report-only PASS rule to command plan. |
| Payload generated = Notification PASS誤認 | YES | payload-only fields and no delivery status. | Real-send disabled evidence should be checked explicitly. | Add notification real-send disabled check. |
| Broker Accepted = Runtime PASS誤認 | YES | Ledger, Current, Report, Notification after broker evidence. | Full Demo Rehearsal must enforce post-Broker chain. | Keep chain mandatory; no Broker Accepted-only PASS. |
| Current未更新見逃し | PARTIAL | Execution result, ledger records, Current projection, Report consistency. | Day+1 unexecuted/unfinished state not explicit. | Add multi-day Current/Ledger continuity check. |
| Pending残留 / 二重Submit | PARTIAL | Pending state, consume info, ledger order IDs, dedup keys. | Stale/consumed Pending negative test not explicit enough. | Add consumed/stale/expired Pending negative tests. |

## End-to-End Evidence Chain Review

| Boundary | Producer | Consumer | Artifact | SoT | Evidence | PASS Condition |
|---|---|---|---|---|---|---|
| Policy -> Safety/Planning | Operator/config | CLI/Morning/Submit | `configs/runtime_v2/capital_deployment.json` and manifest fields | Policy artifact | source/version/hash | Policy loaded and visible in manifest/report. |
| Safety -> Planning | Safety Runtime artifact | CLI/Morning/SELL/Submit | latest/date-scoped safety decision | Safety artifact | decision/reason/status/freshness | Fresh, non-placeholder safety decision used. |
| Feature -> Planning | Market/Feature refresh | Morning | feature artifacts | Feature artifact | selected date/price/source/confidence | Feature is fresh or carryover is explicit. |
| Planning -> Capital Allocation | Morning/SELL pipeline | Planner | `CapitalAllocationSignal` / policy context | OrderPlan/Pending evidence | amount/price/source/policy | Sizing follows Policy and explains cash underuse. |
| OrderPlan -> Pending | Planner | Pending promotion | order_plan JSON / pending JSON | Pending Current | policy/safety context | Pending preserves evidence. |
| Pending -> Approval | Pending runtime | Approval runtime | approval artifact/link | Pending approval link | approved IDs/hash | Approval matches Pending. |
| Approval -> Submit Guard | Pending/Approval | Submit | pending_order_plan JSON | Pending Current | approval link + policy hash | Submit sees approved, unconsumed Pending. |
| Submit Guard -> Broker Boundary | Submit Guard | Submit adapter | submit manifest item evidence | Manifest + item result | guard_decision/reason/source | Guard passes or stops before broker write. |
| Broker -> Execution | Broker adapter/ReadOnly | Execution | order result / readonly snapshot | Broker evidence | mode/endpoint/snapshot timestamp | Demo-only and fresh broker evidence. |
| Execution -> Ledger | Execution pipeline | Ledger | JSONL records | Ledger history | orders/executions/events | Append-only, Runtime-owned evidence. |
| Ledger -> Current | Runtime-owned projection | Current | `state.json` | Current SoT | projection source records | Runtime-owned fills only. |
| Current -> Report | Report writer | Operator | runtime/public report | Derived report | current + manifest reason evidence | Report explains without writing Current. |
| Report -> Notification | Report writer / payload builder | Operator | `notification_payload.json` | Derived payload | reason summary / payload-only | Notification is triage, no send. |
| Notification -> Operator Action | Payload/report | Operator | notification + report + manifest | Human procedure | next_operator_action | Operator can decide next step without guessing. |

## Negative Test Adequacy

| Negative Scenario | Covered In Phase15-U? | Adequacy | Required Addition |
|---|---|---|---|
| policy missing | YES | Adequate | Keep as Step 4-A. |
| safety missing | YES | Partial | Add explicit missing safety artifact command/result path. |
| safety HALT | YES | Adequate | Add generated_at/expires_at freshness. |
| policy hash mismatch | IMPLIED | Partial | Add explicit policy changed after Pending scenario. |
| broker available quantity missing | YES | Adequate | Keep SELL-specific. |
| broker available quantity insufficient | IMPLIED | Partial | Add explicit insufficient quantity case. |
| stale Current | NO | Gap | Add Preflight stale Current negative test. |
| stale Pending | NO | Gap | Add stale target date / expired Pending test. |
| consumed Pending | IMPLIED | Partial | Add consumed Pending submit attempt negative test. |
| missing Report reason | IMPLIED | Partial | Add fail condition for missing `reason_evidence`. |
| notification payload-only | YES | Adequate | Add real-send-disabled evidence. |
| production endpoint detection | IMPLIED | Partial | Add explicit endpoint/mode evidence before Submit. |

## Multi-Day / Continuous Operation Risk

Phase15-U must be amended with a multi-day section before Purpose-Level Demo acceptance.

Required Day+1 review items:

- next business day carryover
- stale feature handling and carryover reason
- stale safety decision detection
- stale broker snapshot detection
- stale Pending detection
- Pending expiry
- policy change after Pending generated
- prior day execution not completed before next day
- Report / Notification history vs today separation
- Current and Ledger continuity

Recommended addition:

```text
Step 10: Multi-Day Demo Continuity Review
```

PASS only if Day+1 planning either uses fresh evidence or stops REVIEW_REQUIRED with clear reason and no unsafe side effects.

## Operator Decision Review

Current coverage:

- Report and Notification now include reason summary and next_operator_action.
- Phase15-U tells Operator to inspect artifacts stepwise.
- REVIEW_REQUIRED and HALT are planned.

Remaining Operator gaps:

- Operator decision apply path is not implemented.
- Recovery apply path is not implemented.
- Notification alone should not authorize action.
- Manual handling rules for unresolved REVIEW_REQUIRED are not fully stated.

Required Demo rule:

```text
When REVIEW_REQUIRED occurs, Operator may inspect Manifest + Report + Notification,
but must not edit Current, must not edit Pending directly, must not rerun Submit
until the failed evidence source has been refreshed and the relevant step is repeated.
```

## Acceptance Stop Gate Review

| Stop Gate | Included In Phase15-U? | Required Update |
|---|---|---|
| policy missing | YES | Keep. |
| safety missing | YES | Add explicit artifact path inspection. |
| Current stale | NO | Add stale Current check. |
| Broker evidence missing | YES | Add snapshot timestamp/freshness. |
| policy hash mismatch | IMPLIED | Add policy changed after Pending test. |
| Safety HALT | YES | Add freshness/expiry. |
| REVIEW_REQUIRED unresolved | PARTIAL | Add no-rerun/no-submit rule until evidence refreshed. |
| Production endpoint detected | IMPLIED | Add explicit endpoint/mode evidence check. |
| Notification real send enabled | PARTIAL | Add explicit disabled evidence check. |
| launchd active without approval | PARTIAL | Add operator confirmation/check. |
| Pending consumed unexpectedly | YES | Add consumed Pending negative test. |
| Current modified outside projection | YES | Add direct Current mutation diff check. |
| Report reason missing | PARTIAL | Add missing `reason_evidence` FAIL rule. |

## Required Phase15-U Plan Updates

Before Demo evidence review starts, Phase15-U should be amended with:

1. Capital Deployment Adequacy section
   - target investment ratio
   - planned notional
   - available cash
   - cash buffer
   - max exposure
   - cash under-deployment reason

2. Stale Evidence Stop Gates
   - stale Current
   - stale Safety
   - stale Broker snapshot
   - stale Pending
   - stale Feature

3. Explicit Negative Tests
   - policy hash mismatch after Pending
   - broker available quantity insufficient
   - consumed Pending submit attempt
   - production endpoint detection
   - missing report reason

4. Multi-Day Demo Continuity Review
   - Day 1 / Day 2 continuity
   - carryover
   - prior-day incomplete execution
   - Current/Ledger/Report history separation

5. Operator Manual Stop Procedure
   - no direct Current edit
   - no direct Pending edit
   - no Submit rerun before evidence refreshed
   - Notification is triage only

## Final Recommendation

```text
DEMO_ACCEPTANCE_PLAN_GAPS_FOUND
```

Rationale:

- Phase15-U is a good stepwise Demo plan.
- It is sufficient as a Level3 Demo skeleton.
- It is not yet sufficient as Level4 Purpose-Level acceptance because capital deployment adequacy, stale evidence, multi-day continuity, production endpoint detection, and Operator manual handling need explicit gates.

## Prohibited Actions Confirmation

This phase did not perform:

- Runtime implementation changes
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
PHASE15V_PURPOSE_LEVEL_RUNTIME_ACCEPTANCE_META_REVIEW_COMPLETE
```
