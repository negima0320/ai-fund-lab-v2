# Phase15-AC Runtime Safety Decision Producer Connection

Date: 2026-07-10

## Objective

Phase15-AC closes the Step0 gap found in Phase15-AA:

```text
Runtime Safety Decision Producer未接続
```

Runtime v2 already had:

- Runtime Safety Decision reader
- Runtime Safety Decision validator
- Planning / Submit Safety consumers
- missing Safety -> `REVIEW_REQUIRED` guard

It did not have a regular Runtime path that produces:

```text
.runtime/runtime_state/safety/latest_safety_decision.json
```

Phase15-AC implements the missing producer path without creating implicit `ALLOW`, Demo-only Safety, Phase-only Safety, or hand-written Operator ALLOW JSON operation.

## Safety Source Investigation

Investigated:

```text
src/ai_fund_lab_v2/safety/
src/ai_fund_lab_v2/safety_phase11/
.runtime/operations/safety_result/
.runtime/operations/safety_monitor/
.runtime/operations/safety_events/
.runtime/safety/
```

Findings:

| Source | Finding | Classification |
|---|---|---|
| `src/ai_fund_lab_v2/safety_phase11/report_schema.py` | Produces `phase11_safety_report_v2` with `overall_decision`, safety state, blocked actions, review items, emergency candidates, buy/sell review fields. | Authoritative source contract |
| `src/ai_fund_lab_v2/safety_phase11/report_writer.py` | Writes Phase11 safety report JSON. | Authoritative producer upstream |
| `.runtime/operations/safety_result/*` | Older operations-era safety result with limited fields. | Legacy / insufficient for Runtime v2 mapping |
| `.runtime/operations/safety_monitor/*` | Monitor result, rich operational status but not the final RuntimeSafetyDecision contract. | Supporting evidence |
| `.runtime/safety/reports/*` | Older safety report schema with status / lock / reconciliation fields. | Legacy supporting evidence |
| `.runtime/safety/locks/*` | Trading lock state. | Supplemental conflict / HALT evidence |
| `.runtime/safety/phase11/state/manual_unlock_approval.json` | Manual unlock approval state. | Recovery / operator evidence, not direct ALLOW producer |

## Authoritative Safety Source Contract

Runtime v2 Producer uses:

```text
authoritative_safety_source=phase11_safety_report_v2
```

Default source path:

```text
reports/safety/phase11/<business_date>_safety_report.json
```

CLI may explicitly provide:

```text
--safety-report-path <path>
```

Contract:

| Field | Source |
|---|---|
| `authoritative_safety_source` | `schema_version=phase11_safety_report_v2` |
| `source_artifact_path` | explicit `--safety-report-path` or default Phase11 report path |
| `source_policy_version` | source `schema_version` |
| `source_business_date` | source `business_date` |
| `source_generated_at` | source `generated_at` |
| `source_expiry` | source `expires_at` |
| `decision_mapping` | source `overall_decision` + `next_recommended_safety_state` + emergency candidates |
| `block_buy_mapping` | source blocked actions, buy review fields, non-ALLOW decision |
| `block_sell_mapping` | source sell review fields, sell blocked actions, HALT |
| `block_submit_mapping` | source blocked submit/broker actions, non-ALLOW decision |
| `halt_mapping` | `overall_decision=EMERGENCY_STOP` or emergency safety state |
| `emergency_stop_mapping` | emergency candidates or emergency safety state |
| `review_required_mapping` | non-ALLOW decision or review items |

Supplemental trading lock evidence is read from:

```text
.runtime/safety/locks/*.json
```

If the Phase11 source says `ALLOW` while a trading lock is active, Producer does not allow Runtime progression. It emits `REVIEW_REQUIRED` with conflict reason.

## Producer Implementation

Added:

```text
src/ai_fund_lab_v2/runtime_v2/safety/producer.py
src/ai_fund_lab_v2/runtime_v2/safety/__init__.py
```

Main function:

```python
produce_runtime_safety_decision(
    *,
    runtime_root: Path,
    business_date: str,
    mode: str,
    source_artifact_path: Path | str | None = None,
) -> RuntimeSafetyProducerResult
```

Flow:

```text
authoritative Safety artifactを読む
↓
schema / business_date / mode / generated_at / expires_at / conflict を検証
↓
RuntimeSafetyDecisionへ正規化
↓
temporary file
↓
fsync
↓
atomic replace
↓
latest_safety_decision.json
↓
history/<business_date>/<decision_id>.json
```

Fixed current path:

```text
.runtime/runtime_state/safety/latest_safety_decision.json
```

History path:

```text
.runtime/runtime_state/safety/history/<business_date>/<decision_id>.json
```

`latest_safety_decision.json` remains Current Safety SoT. History is not used to infer Current.

## Freshness Contract

Producer verifies:

```text
business_date
runtime_mode / environment
generated_at
expires_at
source artifact freshness
schema_version
conflicting trading lock evidence
```

The following never produce implicit `ALLOW`:

- source missing
- source invalid
- source stale / expired
- business_date mismatch
- mode mismatch
- generated_at missing / invalid
- expires_at missing / invalid
- conflicting Safety evidence

In these cases Producer emits a `REVIEW_REQUIRED` RuntimeSafetyDecision, with blocking flags set safe-side.

## CLI Connection

Added regular Runtime v2 CLI job:

```text
--job safety_refresh
```

Example:

```text
python3 -m ai_fund_lab_v2.runtime_v2.cli.run_daily_operation \
  --mode demo \
  --job safety_refresh \
  --business-date <date> \
  --runtime-root .runtime \
  --safety-report-path reports/safety/phase11/<date>_safety_report.json
```

This job:

- produces Runtime Safety Decision from authoritative Safety evidence
- writes fixed path atomically
- writes history
- emits producer evidence into run manifest
- performs no Broker Write
- performs no Morning / Submit / Execution
- is not added to launchd in Phase15-AC

## Manifest Evidence

Safety Producer run manifest now includes:

```text
safety_producer_status
authoritative_safety_source
source_artifact_path
source_policy_version
source_business_date
source_generated_at
source_expires_at
source_freshness_status
runtime_safety_decision_path
safety_decision_id
safety_policy_version
safety_decision
safety_reason
block_buy
block_sell
block_submit
halt_runtime
emergency_stop
review_required
production_equivalent
```

## Runtime Reality Rule Compliance

Producer is Demo / Production common. It does not implement:

- `if demo: ALLOW`
- `demo_safety_decision.json`
- `phase15_safety_allow.json`
- fixture-generated runtime Safety
- Demo Safety bypass
- hand-written Operator ALLOW JSON operation

Allowed:

- `runtime_mode=demo`
- explicit source path
- evidence classification
- `production_equivalent=false` in manifest evidence

## Regression

Added:

```text
tests/runtime_v2/test_phase15ac_runtime_safety_decision_producer.py
```

Coverage:

- valid authoritative source produces Runtime Safety Decision
- fixed path and history are written
- reader loads produced artifact as PASS
- missing source does not generate ALLOW
- stale source becomes REVIEW_REQUIRED
- conflicting trading lock does not allow
- emergency stop maps to HALT
- BUY / SELL block flags remain separated
- CLI `safety_refresh` regular path generates reader artifact
- Runtime mainline has no fixture Safety producer strings

Executed:

```text
python3 -m pytest -q tests/runtime_v2/test_phase15ac_runtime_safety_decision_producer.py
python3 -m pytest -q tests/runtime_v2/test_phase15n_safety_operation_guard_runtime_connection.py tests/runtime_v2/test_phase15r_report_notification_reason_propagation.py tests/runtime_v2/test_phase15y_non_trading_day_demo_acceptance_override.py
PYTHONPYCACHEPREFIX=/private/tmp/phase15ac_pycache python3 -m py_compile src/ai_fund_lab_v2/runtime_v2/safety/producer.py src/ai_fund_lab_v2/runtime_v2/safety/__init__.py src/ai_fund_lab_v2/runtime_v2/cli/run_daily_operation.py
```

Results:

```text
8 passed
16 passed
py_compile PASS
```

## Phase15-AA Re-Judgment Impact

Phase15-AC resolves the missing Producer implementation gap.

It does not automatically make Step0 PASS. Next Step0 evidence must be generated and reviewed:

```text
safety_refresh
↓
Evidence review
↓
Step0 re-judgment
↓
Morning Review only if Step0 passes
```

Operator should provide only:

```text
.runtime/runtime_state/safety/latest_safety_decision.json
Safety Producer manifest
```

No Morning execution should happen before the Step0 re-review.

## Prohibited Actions Confirmation

This phase did not perform:

- Morning execution
- Submit execution
- Execution job
- Broker Write
- Demo order
- Production order
- Notification real send
- launchd/plist change
- Current edit
- Runtime bypass
- hand-written ALLOW JSON operation adoption
- Demo-only Safety Producer
- Phase-only Safety Producer

## Final Judgment

```text
PHASE15AC_RUNTIME_SAFETY_DECISION_PRODUCER_CONNECTION_COMPLETE
```
