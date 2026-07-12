# Phase15-BW Runtime End-to-End Daily System Test Review

## Executive Summary

Final judgment:

```text
END_TO_END_DAILY_SYSTEM_REVIEW_REQUIRED
```

BT〜BVで、Demo Broker WriteからCurrent Applyまでの実Evidenceチェーンは成立した。ただし、通常Runtime Mainlineの完全End-to-Endとはまだ言えない。

理由は明確で、BTは通常Submit Pipelineではなく `RuntimeV2TachibanaDemoSubmitAdapter` の直呼びを使い、BUはDemo限定Fallbackを使い、BVは `scripts/apply_phase15_bv_demo_execution.py` という専用Apply ScriptでLedger/Currentへ反映しているためである。

つまり、今回Acceptedできるのは:

```text
Demo-only evidence chain accepted
```

であり、

```text
Normal Runtime mainline accepted
```

ではない。

## Actual Path

BT〜BVで実際に通った経路:

| Phase | Path | Type | Status |
|---|---|---|---|
| BS | Safety / Approval / Pending / No-send Preflight | Acceptance Harness | `ACCEPTED_BY_COMPONENT` |
| BT | `RuntimeV2TachibanaDemoSubmitAdapter(dry_run=false).submit` | Direct Adapter Call | `DEMO_ONLY` |
| BT | Broker ReadOnly Order List / Position | ReadOnly Evidence Producer | `ACCEPTED_BY_COMPONENT` |
| BU | Order List + Position Difference fallback | Acceptance Harness | `DEMO_ONLY` |
| BV | `scripts/apply_phase15_bv_demo_execution.py` | Dedicated Apply Script | `ACCEPTANCE_HARNESS_ONLY` |
| BU | Browser confirmation | Operator Browser Evidence | `DEMO_ONLY` |

Observed chain:

```text
User Authorization
↓
Submit Preconditions
↓
Demo Broker Write
↓
Broker ACCEPTED
↓
Order List 全部約定
↓
Position 200 → 100
↓
Demo-only Execution-equivalent
↓
Execution Normalization
↓
Ledger Append
↓
Current Projection
↓
Current Apply
↓
Runtime State CURRENT_APPLIED
↓
Pending CONSUMED
```

## Mainline Comparison

| Runtime Stage | BW Status |
|---|---|
| Market Refresh | `NOT_EXECUTED` |
| Feature Consumer Readiness | `NOT_EXECUTED` |
| Candidate AI | `NOT_EXECUTED` |
| Opportunity AI | `NOT_EXECUTED` |
| Policy | `ACCEPTED_BY_COMPONENT` |
| Safety | `ACCEPTED_BY_COMPONENT` |
| Morning | `NOT_EXECUTED` |
| BUY Planning | `NOT_EXECUTED` |
| SELL Planning | `ACCEPTED_BY_COMPONENT` |
| Approval / Auto Authority | `AUTHORITY_CONTRACT_NOT_CLOSED` |
| Authoritative Pending | `ACCEPTANCE_HARNESS_ONLY` |
| Submit Pipeline | `SIMULATION_ONLY` |
| Broker Adapter | `DEMO_ONLY` |
| Broker ReadOnly Reconciliation | `ACCEPTED_BY_COMPONENT` |
| Execution Processing | `ACCEPTANCE_HARNESS_ONLY` |
| Ledger | `ACCEPTANCE_HARNESS_ONLY` |
| Current | `ACCEPTANCE_HARNESS_ONLY` |
| Report | `NOT_EXECUTED_AFTER_BV` |
| Notification | `NOT_EXECUTED` |

## Submit Path Evaluation

BT did not prove the full normal Submit Pipeline real-write path.

What was proven:

- Pending reader / guard concepts are component-proven.
- Submit command and Tachibana request generation are component-proven.
- Broker adapter can send a Demo order and receive `ACCEPTED`.
- Real Broker Write happened exactly once.

What was not proven:

- `run_submit_pipeline(...)` performing the real Broker Write end-to-end.
- Normal pipeline ledger order append and pending consume around the real broker response.
- Normal pipeline handling of the same 6501 scenario without direct adapter control.

Conclusion:

```text
REAL_BROKER_WRITE_ACCEPTED_BY_DIRECT_ADAPTER_BUT_NORMAL_SUBMIT_PIPELINE_REAL_WRITE_NOT_ACCEPTED
```

通常Submit Pipelineでの実Broker Write再Acceptanceは必要。

## Execution Path Evaluation

BU/BV did not use the normal Execution Processor for the apply step.

| Check | Result |
|---|---|
| Normal Execution Processor used for BV apply | `false` |
| Normal Execution Normalizer used for BV apply | `false` |
| Normal Ledger Writer used for BV apply | `false` |
| Normal Current Projector used for BV apply | `false` |
| Normal Current Apply Producer used for BV apply | `false` |
| Dedicated script reimplemented runtime logic | `true` |

This is a major mainline gap. The dedicated script was acceptable for BV evidence closure, but it must not become the normal Runtime path.

## Current Integrity

BV後のCurrent:

| Field | Value |
|---|---:|
| 6501 quantity | `100` |
| cash | `17,704,424` |
| buying_power | `20,009,824` |
| market_value | `470,000` |
| total_equity | `18,174,424` |
| current_version | `phase15bv_current_v1` |
| current_hash | `sha256:11cadb1bdda853fee9bef405acb951a5273848b0488d3c1c6ef007e1053b8bc4` |
| pending | `CONSUMED` |
| runtime_state | `CURRENT_APPLIED` |

Integrity checks:

| Check | Result |
|---|---|
| Cash delta = `100 JPY × 100 shares` | `PASS` |
| Market value = `4700 JPY × 100 shares` | `PASS` |
| Execution price / valuation price separated | `PASS` |
| Browser `6501 100株` match | `PASS` |
| Double apply prevented | `PASS` |
| Current restorable from files | `PASS_WITH_SCOPE_NOTE` |
| Ledger can reconstruct Current through normal projector | `REVIEW_REQUIRED` |
| Next Morning can read fixed Current path | `LIKELY`, but not executed after BV |

## BUY-Origin Gap

SELL Demo acceptance must not be treated as BUY acceptance.

| BUY-origin stage | Status |
|---|---|
| BUY AI inference accepted | `false` |
| BUY Planning accepted | `false` |
| BUY Pending accepted | `false` |
| BUY Submit Simulation accepted | `false` |
| BUY Broker Write accepted | `false` |
| BUY Execution accepted | `false` |
| BUY Current Apply accepted | `false` |
| Next-day PM / SELL-HOLD after BUY | `SELL/HOLD review-only accepted, not BUY next-day accepted` |

The desired path remains unaccepted:

```text
Market
↓
Feature
↓
Candidate AI
↓
Opportunity AI
↓
Policy
↓
Safety
↓
Morning
↓
BUY Planning
↓
Submit
↓
Broker
↓
Execution
↓
Current
↓
翌日の PM AI / SELL
```

## Auto Trade Authority

Current classification:

```text
AUTHORITY_CONTRACT_NOT_CLOSED
```

Evidence:

- BJ/BK separate Human Review and Human Approval.
- BK approval artifact explicitly has `automatic_trade_authorized=false`.
- The system currently proves explicit human-approved acceptance better than normal automatic submit.
- AI Fund Lab v2 purpose expects normal operation to be automatic, with Human Review only on abnormal or high-risk cases.

Conclusion:

Normal auto submit vs human approval vs safety-dependent review remains a Phase15 blocker for true daily operation.

## Report / Notification

| Area | Status |
|---|---|
| Execution Report generation | `NOT_EXECUTED_AFTER_BV` |
| Current Report generation | `NOT_EXECUTED_AFTER_BV` |
| Daily Report generation | `PAYLOAD_ONLY_ACCEPTED_COMPONENT` |
| Notification Payload generation | `PAYLOAD_ONLY_ACCEPTED` |
| Notification Delivery | `NOT_EXECUTED` |

Notification実配信はPhase15の次段でもよいが、Current Apply後のReport生成はPhase15 Complete前に必要。

## Demo Reset Handling

Tachibana Demo日次リセットは未解決。

| Check | Status |
|---|---|
| Broker ResetをRuntime SELLと誤認しない | `NOT_ACCEPTED` |
| Broker Position消失をExecution扱いしない | `NOT_ACCEPTED` |
| Runtime CurrentをBroker Snapshotで上書きしない | `PARTIAL_DESIGN_ONLY` |
| Reset検知 | `MISSING` |
| Demo reset後のReconciliation mode | `NOT_CONNECTED` |

Recommended contract:

```text
DEMO_ACCOUNT_RESET_DETECTION_CONTRACT
```

## Operational Test Readiness

判定:

```text
BROKER_CONNECTED_OPERATIONAL_TEST_NOT_READY
```

理由:

- Normal Submit Pipeline real Broker Write is unaccepted.
- Normal Execution Processor -> Current Apply is unaccepted for this path.
- BUY-origin full flow is unaccepted.
- Demo reset detection is missing.
- Auto trade authority contract is not closed.

## Phase15 Remaining Steps

Mandatory:

1. Normal Runtime Mainline Submit real Demo Broker Write acceptance using `run_submit_pipeline`, not direct adapter call.
2. Normal Execution Processor acceptance for the submitted order, including Demo fallback integration without dedicated apply script.
3. Current projection/apply through normal Runtime execution/current components.
4. BUY-origin End-to-End acceptance.
5. Report generation after Current Apply through the normal report path.
6. Demo Account Reset Detection Contract and reconciliation mode.
7. Auto trade authority contract closure.
8. Final Phase15 audit proving no Acceptance harness remains in the normal operating path.

Optional / Phase16 candidates:

- Notification real delivery acceptance.
- Historical Runtime Replay.
- Operation dashboard.
- Long-term monitoring / alert runbook refinement.

## Regression

Regression test:

```bash
PYTHONPATH=src python3 -m pytest -q tests/runtime_v2/test_phase15bw_runtime_end_to_end_daily_system_test_review.py
```

Required checks:

- BT〜BV artifact linkage matches.
- Request Hash matches.
- Broker Order Hash matches.
- Execution ID matches.
- Ledger dedup exists.
- Current Hash matches.
- Pending is `CONSUMED`.
- Double apply is prevented.
- Existing `.runtime` hashes are unchanged.
- Demo-only flags remain.
- `production_equivalent=false` remains.

## Final Judgment

```text
END_TO_END_DAILY_SYSTEM_REVIEW_REQUIRED
```

BT〜BVは重要な成果だが、Acceptance専用経路と通常Runtime Mainlineの差分がまだ大きい。

## Next Prefix

Recommended next prefix:

```text
Phase15-BX Normal Runtime Mainline End-to-End Connection Closure
```
