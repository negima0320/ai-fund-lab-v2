# Phase15-A Purpose / Goal Definition

## Summary

Phase15-A defines the purpose, position, and final goal of Phase15.

Phase15 is not a continuation phase for simply adding more Runtime implementation. It is the phase for re-establishing trust in Runtime v2, the control center of AI Fund Lab v2.

Final judgment: **PHASE15A_PURPOSE_GOAL_DEFINED**

This phase is documentation-only.

No Runtime implementation change, Submit, Broker Write, Production order, Notification real send, launchd/plist change, Current direct edit, fake-adapter Full Runtime PASS declaration, or Phase15-specific Runtime bypass was performed.

## 1. Final Purpose of AI Fund Lab v2

AI Fund Lab v2 exists to achieve the following operating goal:

```text
年間50%の利益を目指し、安心・安全に自動売買を継続できる運用システムを実現すること
```

Phase15 must be defined backward from this purpose.

Annual return is not achieved by Runtime alone. Candidate AI, Opportunity AI, Position Management AI, Capital Allocation, Risk Policy, Safety, Broker integration, Current State, Report, Notification, and operation procedures all contribute to the system.

However, if Runtime v2 is not trustworthy, the entire operating system cannot be trusted. Even when AI judgment, Capital Allocation, Safety, Broker evidence, Report, and Notification are individually correct, the full system can still fail if Runtime connects or controls them incorrectly.

Therefore, Phase15 treats Runtime v2 trust as a system-level requirement, not as a local component quality issue.

## 2. Runtime Role

Runtime is not AI.

Runtime is the control center that connects and controls the system according to explicit design contracts:

```text
AI
↓
Capital Allocation
↓
Safety
↓
Runtime
↓
Broker
↓
Current
↓
Report
↓
Notification
```

Runtime does not decide investment attractiveness by itself. Runtime does not invent capital allocation policy. Runtime does not silently replace Safety or Risk Policy with local hidden defaults.

Runtime is responsible for ensuring that approved decisions and explicit policies are executed in the correct order, through the correct path, with correct evidence, and without double execution or hidden behavior.

Runtime reliability is directly connected to system reliability because Runtime is where the following contracts meet:

- AI output
- Capital Allocation
- Risk Policy
- Safety decision
- Pending / Approval
- Submit Guard
- Broker evidence
- Execution evidence
- Current SoT
- Report / Public Report
- Notification
- Regression evidence

If Runtime breaks, the full operating chain breaks.

## 3. Phase15 Purpose

Phase15 exists to establish trust in Runtime as a control system.

Phase15 is not merely:

- reviewing Runtime
- completing Runtime implementation
- making tests pass
- proving that one broker order was accepted
- proving that one report or payload was generated

Phase15 must prove that Runtime v2:

- operates according to design contract
- does not obstruct Capital Allocation / Risk Policy / Safety
- has no hidden policy
- controls BUY and SELL with distinct, explicit contracts
- remains consistent from Broker to Current to Report to Notification
- can be continuously verified through operation tests
- can stop as REVIEW_REQUIRED when evidence or policy is insufficient

The Phase14 Submit Guard Regression showed that a Runtime path can appear operational while still violating the design contract. Phase15 therefore treats trust as something that must be proven by aligned evidence, not inferred from partial success.

## 4. Phase15 Work Scope

### A. Regression Fixes

Phase15 addresses regressions and review failures identified in Phase14:

- hidden default
- hidden policy
- Submit Guard Regression
- Capital Allocation contract mismatch
- BUY / SELL Guard contract gaps
- Current / Report / Notification connection and scope gaps
- Review Level misclassification
- insufficient regression coverage

The key known regression is:

```text
max_order_amount = 100000
```

This hidden default applied to both BUY and SELL in the regular Submit path and broke the Capital Allocation and SELL liquidation contracts.

### B. Missing Contract Completion

Phase15 makes previously unresolved contracts explicit:

- Capital Deployment Contract
- BUY notional policy
- SELL liquidation policy
- max order amount policy
- max positions policy
- cash buffer policy
- Review Required policy
- Notification delivery policy
- Blog / Public Report policy
- launchd / demo operation readiness policy

Any policy that affects Runtime behavior must be visible as design contract, implementation behavior, manifest/report/audit evidence, and regression coverage.

### C. Full Runtime Flow Tests

Phase15 must not accept Component PASS as Runtime PASS.

The Runtime flow must be reviewed and tested across the full chain:

```text
Market Refresh
↓
Feature Refresh
↓
Morning Planning
↓
Pending
↓
Approval
↓
Submit
↓
Broker
↓
Execution
↓
Current Projection
↓
Report
↓
Notification
```

Flow acceptance must confirm not only that each step runs, but also that each step consumes the intended input, emits the intended output, and is consumed by the next step according to contract.

### D. Demo Operation Tests

Phase15 must verify Runtime in operation-like Demo conditions.

Review targets include:

- BUY Runtime
- SELL Runtime
- Current update
- Report generation
- Notification payload / delivery
- Runtime Manifest
- Regression
- REVIEW_REQUIRED stop and operator confirmation procedure

Demo operation acceptance must remain scoped. Demo Broker Accepted is not the same as Production readiness. Notification payload generation is not the same as Notification delivery. Component tests are not the same as Full Runtime Operation.

## 5. Phase15 PASS Criteria

Phase15 PASS requires alignment across the complete evidence chain:

```text
Design Contract
↓
Implementation
↓
CLI Regular Path
↓
Runtime Manifest
↓
Broker Evidence
↓
Current SoT
↓
Report
↓
Notification
↓
Regression
```

The following are necessary evidence candidates, but are not sufficient by themselves:

- `tests pass`
- `Broker Accepted`
- `Report generated`
- `Payload generated`
- fake adapter PASS
- fixture PASS
- component-level PASS

Phase15 PASS must mean that the design contract, actual implementation, regular CLI path, Runtime artifacts, Broker/Current evidence, Report/Notification outputs, and regression coverage all tell the same story.

## 6. Review Quality Improvement

Phase15 also improves the quality of Runtime review itself.

### Runtime Evidence First Rule

Runtime state must not be guessed.

When Runtime artifacts, Broker state, Current SoT, manifest, ledger, report, notification payload, or other evidence can be checked, evidence takes priority over inference.

### Evidence Request Rule

When evidence is missing, the reviewer must ask the Operator for the smallest useful confirmation command before issuing fix instructions.

Do not request a large command batch at once. Ask for one or two commands, inspect the result, and then decide the next review step.

### No Guess Rule

Do not declare `PASS`, `FAIL`, or root cause from speculation.

Review must proceed in this order:

```text
Runtime Evidence
↓
Review
↓
Judgment
```

### Review Level Separation

Phase15 must distinguish review levels:

| Level | Meaning |
| --- | --- |
| Level1 | Component |
| Level2 | Flow |
| Level3 | Full Runtime Operation |

Level1 Component PASS must not be reported as Level2 Flow PASS.

Level2 Flow PASS must not be reported as Level3 Full Runtime Operation PASS.

Fake adapter, fixture, and test-only path evidence must not be treated as Full Runtime PASS.

## 7. Phase15 Final Goal

Phase15 final goal is:

```text
AI Fund Lab v2 の制御システムである Runtime v2 が、
年間50%の利益を目指すAI運用を、
安心・安全に自動売買として継続できるよう支えられることを、
設計契約・実装・Runtime証跡・運用テストによって証明する。
```

In short, Phase15 must make Runtime v2 and Runtime review trustworthy enough to support continued AI-driven operation.

## Prohibited Actions Check

| Action | Performed |
| --- | --- |
| Runtime implementation change | No |
| Submit execution | No |
| Broker Write | No |
| Production order | No |
| Notification real send | No |
| launchd/plist change | No |
| Current direct edit | No |
| fake adapter Full Runtime PASS declaration | No |
| Phase15-specific Runtime bypass | No |

## Final Judgment

```text
PHASE15A_PURPOSE_GOAL_DEFINED
```
