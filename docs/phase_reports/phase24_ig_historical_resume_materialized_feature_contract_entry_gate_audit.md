# Phase24-IG Historical Resume Materialized Feature Contract Entry Gate Audit

## 1. Primary Judgment

`PHASE24_IG_RESUME_FEATURE_CONTRACT_ENTRY_GATE_REPAIRED_SHORT_VALIDATION_PASS_OPERATOR_RESUME_REQUIRED`

Target run:

```text
runtime-test-historical-extended-smoke-20260801T223117629647Z
```

Resume result before repair:

```text
PRECONDITION_FAILURE / exit_code = 70
```

Direct failed check:

```text
materialized_contract_state_consistent
```

## 2. Resume Start Resolution

Run state resolves resume to:

```text
business_date = 2023-06-14
job = morning
```

Completed business day count:

```text
109
```

Resume start resolution is `PASS`.

## 3. Authority Matrix

| Lifecycle state | Authority |
|---|---|
| Completed day | `RUN_SCOPED_EVIDENCE` |
| Failed day | `RUN_SCOPED_EVIDENCE` |
| Future day | `PLAN_EXPECTATION` |

Run-scoped feature contract evidence exists in `daily/<date>/data_readiness/data_readiness.json` for the inspected completed and failed days.

## 4. Date Comparison

| Date | State | Run-scoped evidence | Global contract | Plan expectation | Expected Gate |
|---|---|---:|---:|---|---|
| 2023-01-04 | Completed | yes | yes | `NOT_YET_MATERIALIZED` | PASS |
| 2023-01-31 | Completed | yes | yes | `NOT_YET_MATERIALIZED` | PASS |
| 2023-02-14 | Completed | yes | yes | `NOT_YET_MATERIALIZED` | PASS |
| 2023-06-13 | Completed | yes | yes | `NOT_YET_MATERIALIZED` | PASS |
| 2023-06-14 | Failed | yes | yes | `NOT_YET_MATERIALIZED` | PASS |

The plan still contains fresh-run schedule expectations, which is valid as planning metadata but invalid as materialized resume authority for already executed dates.

## 5. Root Cause

Primary root cause:

```text
Resume reused the fresh-run Plan Entry Gate and validated all plan entries
against plan-time NOT_YET_MATERIALIZED expectations instead of lifecycle-aware
run-scoped materialized evidence.
```

Secondary root cause:

```text
Completed / failed / future day classification was missing from the Entry Gate.
```

This explains why `feature_date_evidence.status = PASS` still failed: `status_pass` and `materialized_contract_state_consistent` are separate checks. The latter compared plan expectation materialization state rather than the completed day's run-scoped authority.

## 6. Classification

| Item | Judgment |
|---|---|
| Completed Day Contract Authority | `RUN_SCOPED_EVIDENCE` |
| Failed Day Contract Authority | `RUN_SCOPED_EVIDENCE` |
| Future Day Contract Authority | `PLAN_EXPECTATION` |
| Resume Start Date Resolution | `PASS` |
| Completed Day Classification | `DEFECTIVE_BEFORE_REPAIR` |
| Failed Day Classification | `DEFECTIVE_BEFORE_REPAIR` |
| Plan Expectation Used as Materialized Authority | `YES` |
| Global Runtime Cleanup Impact | `NO` |
| Run-scoped Evidence Sufficient | `YES` |
| Implementation Required | `YES` |

## 7. Non-Changes

No Runtime resume, fresh-run, long historical test, Run Evidence deletion, Run State edit, Ledger edit, Current edit, Pending edit, or Feature Contract manual generation was performed.

No Strategy, Ranking, Eligibility, PM, Position Sizing, Submit Guard, or Safety Guard was changed.

## 8. Recommended Next Task

Operator resume for `runtime-test-historical-extended-smoke-20260801T223117629647Z`.
