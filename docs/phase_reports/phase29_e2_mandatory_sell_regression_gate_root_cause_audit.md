# Phase29-E2 Mandatory SELL Regression Gate Root Cause Audit

Status:

```text
COMPLETE
TEST-ONLY REPAIR
100BD READY
```

Primary Judgment:

```text
PHASE29_E2_MANDATORY_SELL_REGRESSION_STALE_FIXTURE_REPAIRED_100BD_READY
```

## 1. Scope

Phase29-E2 audited the single mandatory SELL regression failure from Phase29-E:

```text
tests/runtime_v2/test_phase19_bt_reduce_quantity_contract.py::test_phase19_bt_reduce_pending_sell_conflict_review_required
```

No Production code, config, schema, Runtime artifact, Pending artifact, fresh run,
resume, Historical run, or 100BD run was changed or executed. The only code
change was a test fixture repair in:

```text
tests/runtime_v2/test_phase19_bt_reduce_quantity_contract.py
```

Evidence:

```text
reports/phase29_e2_mandatory_sell_regression_gate_root_cause_audit/root_cause.json
reports/phase29_e2_mandatory_sell_regression_gate_root_cause_audit/causality_matrix.json
reports/phase29_e2_mandatory_sell_regression_gate_root_cause_audit/fixture_contract_audit.json
reports/phase29_e2_mandatory_sell_regression_gate_root_cause_audit/regression_results.json
```

## 2. Reproduction

The specified test failure was reproduced before repair:

```text
Expected: REVIEW_REQUIRED
Observed: PASS
```

Trace showed that the old fixture wrote a minimal active pending payload:

```json
{"state": "APPROVED", "active_pending": true, "items": [{"symbol": "6522", "side": "SELL", "quantity": 100}]}
```

Current Pending reader classified that payload as:

```text
INVALID
```

because it lacked current required Pending authority fields including
`schema_version`, `pending_plan_id`, `environment`, date/session fields,
`source_order_plan`, `approved_item_ids`, `submit_constraints`, and `consume`.
SELL reconciliation therefore saw no valid existing active pending and returned:

```text
PASS
PENDING_SELL_NO_EXISTING_ACTIVE_PENDING
```

## 3. Current Contract

Phase19-BT originally treated any same-symbol active pending SELL as a coarse
conflict:

```text
REVIEW_REQUIRED_REDUCE_PENDING_SELL_CONFLICT:<symbol>
```

Phase28-D3 replaced that coarse gate with current SELL pending reconciliation:

```text
valid existing active SELL pending
+ new Sell Planning SELL intent
-> classify by date/session, state, lineage, intent, generation, quantity
-> preserve/reconcile if compatible
-> REVIEW_REQUIRED if conflicting
```

For this test's intended case, valid existing SELL 100 vs new REDUCE MEDIUM 300
is:

```text
SAME_SYMBOL_CONFLICTING_QUANTITY
PENDING_SELL_CONFLICTING_QUANTITY_REVIEW
PENDING_PLAN_CONFLICT_ORIGINAL_PRESERVED
```

So `REVIEW_REQUIRED` remains the correct judgment. The legacy reason code was
the stale part after Phase28-D3.

## 4. Root Cause

Primary classification:

```text
STALE_TEST_FIXTURE
```

Secondary expectation update:

```text
Reason-code expectation changed by prior Phase28-D3 contract.
```

The failure was not caused by Phase29-E. Phase29-E changed only Strategy
Portfolio Construction and Position Sizing. The failing test route uses Runtime
SELL Planning, Pending reader, and Pending reconciliation, and does not call the
Phase29-E modified Production functions.

## 5. Repair

The test now creates a valid current Pending fixture using Production Pending
model/promotion/writer helpers:

```text
PendingOrderItem
promote_order_plan_to_pending
attach_approval_link
write_pending_order_plan
```

The fixture preserves the original intent:

```text
Current position: 6522, 1000 shares
Existing active pending SELL: 6522, 100 shares, REDUCE
New PM REDUCE MEDIUM: 300 shares
Expected result: REVIEW_REQUIRED
```

The assertion now checks the current D3 reason codes:

```text
PENDING_SELL_CONFLICTING_QUANTITY_REVIEW
PENDING_PLAN_CONFLICT_ORIGINAL_PRESERVED
```

## 6. Regression

Results:

```text
Original failing test after repair: 1 passed
Full REDUCE quantity contract: 12 passed
Related SELL pending reconciliation: 19 passed
Phase29-E mandatory broad regression subset: 230 passed
Compile changed test: PASS
```

## 7. Gate Decision

```text
Failure reproduced = YES
Root Cause classification = STALE_TEST_FIXTURE
Phase29-E causal = NO
Production defect = NO
Fixture stale = YES
Expectation stale = YES, reason code only
Production code changed = NO
Test-only repair performed = YES
SELL authority preserved = YES
Fresh 100BD Ready = YES
100BD executed by Codex = NO
```

## 8. Final Judgment

```text
PHASE29_E2_MANDATORY_SELL_REGRESSION_STALE_FIXTURE_REPAIRED_100BD_READY
```
