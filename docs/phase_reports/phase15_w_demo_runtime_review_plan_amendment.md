# Phase15-W Demo Runtime Review Plan Amendment

Date: 2026-07-10

Final judgment:

```text
PHASE15W_DEMO_RUNTIME_REVIEW_PLAN_AMENDED
```

## Purpose

Phase15-W amends the Phase15-U Demo Runtime Review Plan using the Phase15-V Purpose-Level Acceptance findings.

This phase does not execute Demo Runtime and does not change Runtime implementation.

The amendment raises Demo Review from:

```text
Level3: Runtime operation confirmation
```

to:

```text
Level4: Purpose-Level Operation Acceptance
```

## Purpose Reminder

AI Fund Lab v2 purpose:

```text
年間50%の利益を目指し、
安心・安全に自動売買を継続できる運用システムを実現すること
```

Phase15 purpose:

```text
Runtimeという制御システムへの信頼を確立すること
```

Demo Runtime Review must therefore prove that Runtime:

- does not obstruct capital deployment with hidden policy
- stops safely when evidence is missing or unsafe
- preserves state boundaries
- explains decisions to the Operator
- can continue across business days

## Updated File

Updated:

```text
docs/phase_reports/phase15_u_demo_runtime_review_plan.md
```

Added section:

```text
Phase15-W Amendment
```

## Amendment Summary

### 1. Capital Deployment Adequacy Review

Added required Morning-after evidence:

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

PASS requires Operator to explain unused capital. Unknown under-deployment is not PASS.

### 2. Stale Evidence Stop Gate

Added stale evidence gates for:

```text
Current
Safety
Broker snapshot
Pending
Feature
Approval
```

Required freshness fields:

```text
generated_at
expires_at
business_date
target_session_date
```

Stale evidence must stop as REVIEW_REQUIRED.

### 3. Multi-Day Continuity Review

Added Day1 / Day2 / Day3 continuity concept.

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

### 4. Operator Manual Procedure

Added manual REVIEW_REQUIRED flow:

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

Prohibited during manual handling:

- Current direct edit
- Pending direct edit
- Submit rerun before evidence refresh
- launchd restart
- Notification-only trade decision

### 5. Production Endpoint Detection

Added evidence requirements:

```text
runtime_mode
broker_mode
submit_enabled
endpoint
notification_mode
production flags
```

Production endpoint or production order path is FAIL.

### 6. Notification Operation Rule

Added rule:

```text
Notification is triage only.
```

Operator decision order:

```text
Manifest
↓
Report
↓
Notification
```

### 7. Demo Acceptance Stop Gate

Added stop gates:

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

### 8. Purpose-Level PASS Criteria

Added Level4 PASS criteria:

```text
Runtime資金投入を阻害せず
安全に停止し
Stateを保ち
Operatorへ説明でき
翌営業日も継続できる
```

## Result

Phase15-U is now amended to address the Phase15-V purpose-level gaps:

- capital deployment adequacy
- stale evidence
- multi-day continuity
- operator manual procedure
- production endpoint detection
- notification triage rule
- Level4 stop gates

## Prohibited Actions Confirmation

This phase did not perform:

- Demo Runtime execution
- Broker Write
- Demo order
- Production order
- Notification real send
- launchd/plist change
- Runtime implementation change
- Current edit
- Runtime bypass

## Final Judgment

```text
PHASE15W_DEMO_RUNTIME_REVIEW_PLAN_AMENDED
```
