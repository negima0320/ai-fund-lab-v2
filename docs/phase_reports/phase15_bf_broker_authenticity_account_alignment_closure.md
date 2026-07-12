# Phase15-BF Broker Authenticity and Account Alignment Closure

## Executive Summary

Phase15-BF resolved the Broker Authenticity blocker without running Morning.

Final judgment:

```text
STEP0_REVIEW_REQUIRED
```

Broker Authenticity is now closed:

```text
data_origin=BROKER_API
mock_used=false
fixture_used=false
authenticity_status=READY
```

Step0 is still not READY only because Safety remains `REVIEW_REQUIRED` for the valid 4591 `HIGH_RISK_REVIEW`. Broker authenticity is `READY`, and Demo preloaded Broker positions are now classified outside Runtime-owned scope.

## Safety Boundaries

Not executed:

```text
Morning
Inference
Planning
Approval Apply
Submit
Execution processing
Broker Write
Pending mutation
Current Position mutation
Notification Send
Production Write
existing .runtime deletion
```

Executed:

- Broker ReadOnly snapshot refresh.
- Safety Evaluation.
- Safety Refresh.
- Morning-scope Data Readiness.
- Normalizer / metadata contract fixes.
- Regression tests.

## Transport / Adapter Trace

Runtime path:

```text
CLI broker_readonly_refresh
↓
run_broker_readonly_refresh
↓
RuntimeV2ReadonlyAdapter
↓
run_tachibana_broker_snapshot
↓
TachibanaReadOnlyClient
↓
HttpPostBrokerTransport
↓
Tachibana API response
↓
normalizer
↓
broker models
↓
tachibana_snapshot.json
```

Confirmed evidence:

- Runtime adapter: `runtime_v2_readonly_adapter`
- Snapshot adapter: `tachibana_broker_snapshot`
- Transport: `HTTP_POST`
- Raw response origin: `TACHIBANA_API_RESPONSE`
- Session status: `PASS`
- Login: `PASS`
- Account fetch: `PASS`
- Positions fetch: `PASS`
- Orders fetch: `PASS`
- Logout: `PASS`
- Fixture loader: not used
- Mock adapter: not used
- Raw response saved: `false`
- Secret saved: `false`

## source="mock" Root Cause

Classification:

```text
REAL_API_RESPONSE_WITH_WRONG_NORMALIZER_DEFAULT
```

Root cause:

- `broker/normalizer.py` set `source="mock"` unconditionally for balances, positions, orders, and executions.
- `broker/models.py` also defaulted `source="mock"`.
- Runtime v2 then interpreted nested `source="mock"` as actual mock evidence.

BF fix:

- Normalizer now accepts explicit origin metadata.
- Real API normalized records use `source="broker_api"`.
- Real API normalized records carry:
  - `provider=tachibana`
  - `adapter=tachibana_broker_snapshot`
  - `transport=HTTP_POST`
  - `data_origin=BROKER_API`
  - `fixture_used=false`
  - `mock_used=false`
  - `read_only=true`
- Runtime v2 authenticity classification prioritizes formal `data_origin` over legacy `source`.

## Data Origin Contract

Allowed values:

```text
BROKER_API
FIXTURE
MOCK
CACHED_API_RESPONSE
UNKNOWN
```

Current evidence:

```text
data_origin=BROKER_API
mock_used=false
fixture_used=false
```

Fixture / mock evidence remains `REVIEW_REQUIRED` and cannot become authenticity-ready.

## Authenticity Result

Artifact:

```text
.runtime/runtime_state/broker_readonly/2026-07-10/tachibana_snapshot.json
```

Result:

```text
authenticity_status=READY
```

Why:

- Network transport executed.
- Tachibana session succeeded.
- Fixture loader was not used.
- Mock adapter was not used.
- Raw response origin is provider response.
- `data_origin=BROKER_API`.

## Account Identity

Status:

```text
account_identity_status=REFERENCE_HASHED
```

The artifact stores:

- `account_identity_hash`
- `credential_reference_id`
- `session_environment=demo`

No full account ID or secret value is saved. The identity is derived from credential references and environment, not from secret contents.

## Runtime Current Alignment

Classification:

```text
RUNTIME_SCOPE_NOT_BROKER_RECONCILED
```

Broker preloaded demo positions:

```text
OUT_OF_RUNTIME_OWNED_SCOPE
```

Broker account full-position alignment:

```text
NOT_APPLICABLE
```

Evidence:

- Current positions have `source=runtime_v2_runtime_owned_fill_projection`.
- Current positions do not carry per-position Broker reconciliation fields such as `source_submit_id`, `source_execution_id`, or `broker_execution_id`.
- Broker snapshot contains demo preloaded positions such as `6501`, `6502`, and `9984`.
- `runtime_owned_positions_compared=0`
- `runtime_owned_symbols_missing_in_broker=[]`
- `broker_symbols_not_runtime_owned=[]`
- `broker_only_position_classification=OUT_OF_RUNTIME_OWNED_SCOPE`

Interpretation:

Runtime Current is a Runtime-owned / evaluation projection and is not contractually the same as the full Tachibana demo account positions. Broker full-position equality is therefore not required for Step0. Only positions with explicit submit / execution linkage are Broker reconciliation targets.

## Safety Result

Safety Evaluation:

```text
overall_decision=REVIEW_REQUIRED
triggered_guards=[INDIVIDUAL_CRASH]
high_risk_review=[HIGH_RISK_REVIEW]
input_freshness_status=PASS
```

Runtime Safety Decision:

```text
decision=REVIEW_REQUIRED
reason=HIGH_RISK_REVIEW
```

4591 remains a valid high-risk event. No threshold was changed and no symbol was removed.

## Data Readiness Result

Artifact:

```text
.runtime/runtime_state/data_readiness/2026-07-10/data_readiness.json
```

Result:

```text
overall_status=REVIEW_REQUIRED
broker_status=READY
safety_status=REVIEW_REQUIRED
feature_status=READY
missing_evidence=[]
stale_artifacts=[]
```

Review reasons:

```text
HIGH_RISK_REVIEW
```

The previous `broker_snapshot_authenticity_review_required` and `broker_account_alignment_review_required` reasons are closed.

## Code Changes

Changed:

- `src/ai_fund_lab_v2/broker/models.py`
- `src/ai_fund_lab_v2/broker/normalizer.py`
- `src/ai_fund_lab_v2/broker/tachibana_broker_snapshot.py`
- `src/ai_fund_lab_v2/runtime_v2/broker_readonly/refresh.py`
- `tests/runtime_v2/test_phase15bd_broker_readonly_refresh.py`
- `tests/runtime_v2/test_phase15bf_broker_authenticity_account_alignment.py`

## Regression

Command:

```bash
PYTHONPATH=src python3 -m pytest -q tests/runtime_v2/test_phase15bf_broker_authenticity_account_alignment.py tests/runtime_v2/test_phase15bd_broker_readonly_refresh.py tests/runtime_v2/test_phase15be_final_contract_closure.py tests/runtime_v2/test_phase15ac_runtime_safety_decision_producer.py tests/runtime_v2/test_phase15aq_runtime_data_readiness_gate.py tests/runtime_v2/test_phase15as_data_readiness_semantic_consistency.py tests/broker/test_broker_normalizer.py tests/broker/test_tachibana_phase10c_session_foundation.py
```

Result:

```text
140 passed
```

Compile check:

```bash
PYTHONPYCACHEPREFIX=/private/tmp/pycache_phase15bf PYTHONPATH=src python3 -m compileall -q src/ai_fund_lab_v2/broker src/ai_fund_lab_v2/runtime_v2/broker_readonly src/ai_fund_lab_v2/runtime_v2/data_readiness.py
```

Result:

```text
passed
```

## Runtime Mutation

No prohibited Runtime mutation occurred.

Broker refresh was read-only:

- `broker_write_executed=false`
- `ledger_appended=false`
- `pending_mutation_executed=false`
- `current_position_apply_executed=false`

## Step0 Judgment

Final judgment:

```text
STEP0_REVIEW_REQUIRED
```

Reason:

- Broker Authenticity blocker is closed.
- Broker Account Alignment is no longer a Step0 blocker because the full Broker demo account is outside Runtime-owned scope.
- Safety remains `REVIEW_REQUIRED` due valid 4591 `HIGH_RISK_REVIEW`.
- Data Readiness remains `REVIEW_REQUIRED`.

## Remaining Blockers

1. 4591 requires Human Safety Review.
2. Morning-scope Data Readiness is not READY because of `HIGH_RISK_REVIEW`.

## Recommended Next Prefix

Recommended next prefix:

```text
Phase15-BG Human Safety Review for 4591
```

Broker evidence is no longer the Step0 blocker.
