# Phase14-D14 Demo SELL Guarded Test Preflight

Final decision: **PHASE14D14_SELL_PREFLIGHT_COMPLETE**

## 1. Purpose

Phase14-D14 is the guarded preflight for a Runtime v2 pure submit path Demo SELL test.

Phase14-D13 fixed the Tachibana Position response mapping gap, and the D11-equivalent BUY reflection was re-evaluated successfully with `7203 quantity=100` as Runtime v2 Position evidence. Phase14-D14 therefore verifies that Runtime v2 can safely prepare a SELL path before any Demo SELL Submit is executed.

This phase is preflight only. No SELL Submit, new BUY Submit, Cancel API, correction API, Production order, production Broker API write, real-money operation, notification send, launchd / plist change, AI retraining, Backtest, or Simulation was executed.

## 2. Evidence Source

Phase14-D14 uses the existing Phase14-D13 ReadOnly snapshot as preflight evidence:

- Snapshot: `.runtime/phase14d13/tachibana_demo_snapshot.json`
- D13 report: `docs/phase_reports/phase14_d13_position_response_mapping_fix.md`
- D13 re-evaluation: `.runtime/phase14d13/reflection_reevaluation/phase14_d13_d11_reflection_check.json`

Target Position evidence:

| Field | Value |
| --- | --- |
| issue_code | `7203` |
| account_type | `cash` |
| quantity | `100` |
| available_quantity | `100` |
| average_price | `102.0000` |
| market_price | `2941.0000` |
| raw_clmid | `CLMGenbutuKabuList` |

This confirms that the SELL quantity guard can use Broker Position as the Source of Truth.

## 3. Runtime v2 SELL Preflight Design

The SELL test candidate is:

| Field | Value |
| --- | --- |
| issue_code | `7203` |
| side | `SELL` |
| quantity | `100` or less |
| maximum allowed quantity | `100` |
| maximum available quantity | `100` |
| account_type | `cash` |
| environment | `demo` |
| source path | `pending_order_plan/pending_order_plan.json` |

Runtime v2 must satisfy all of the following before a future SELL Submit:

- `environment=demo`.
- Demo base URL only.
- Production endpoint is blocked.
- Production credential is not used as submit authority.
- Submit source is only `pending_order_plan/pending_order_plan.json`.
- Pending state is `APPROVED`.
- Approval artifact is `APPROVED`.
- Pending approval hash matches the Approval artifact hash.
- Duplicate submit guard passes.
- RuntimeV2SubmitCommand expresses `side=SELL`.
- SELL quantity is positive.
- SELL quantity is not greater than Broker Position quantity.
- SELL quantity is not greater than Broker available quantity.
- Legacy `OrderCommand` / `RuntimeMode` is not used as submit authority.
- Legacy Runtime entrypoint is not called.

## 4. Guard Updates

Phase14-D14 adds explicit SELL quantity guards to Runtime v2 submit preflight:

| Guard | Result |
| --- | --- |
| Missing broker position quantity | `BLOCKED` |
| Missing broker available quantity | `BLOCKED` |
| SELL quantity > broker position quantity | `BLOCKED` |
| SELL quantity > broker available quantity | `BLOCKED` |
| SELL quantity <= broker position and available quantity | preflight may proceed |

The Tachibana Demo Submit Adapter now accepts RuntimeV2SubmitCommand with `side=SELL` in dry-run / preflight mode. It still blocks production endpoints, non-demo settings, non-current submit sources, unsupported sides, disabled live order flag, non-positive quantity, and 9000-series symbols for demo fill test candidates.

No actual Demo SELL Submit was executed.

## 5. Preflight Results

Lightweight test coverage was added:

- `tests/runtime_v2/test_phase14d14_demo_sell_guarded_preflight.py`

Verified cases:

| Case | Result |
| --- | --- |
| 7203 SELL 100 with broker quantity=100 and available_quantity=100 | PASS |
| SELL quantity 101 with broker quantity=100 | BLOCKED |
| SELL quantity 100 with available_quantity=99 | BLOCKED |
| Duplicate pending plan | BLOCKED |
| Rejected approval artifact | BLOCKED |
| RuntimeV2TachibanaDemoSubmitAdapter dry-run accepts SELL command without Broker API call | PASS |
| Tachibana order request metadata represents SELL | PASS |

Command executed locally:

```bash
PYTHONPATH=src:. PYTHONPYCACHEPREFIX=.runtime/pycache_phase14d14 python3 -m pytest tests/runtime_v2/test_phase14d14_demo_sell_guarded_preflight.py tests/runtime_v2/test_phase14d3_pure_submit_path.py tests/runtime_v2/test_phase14d4_tachibana_demo_submit_adapter.py -q
```

Result:

```text
15 passed
```

## 6. Expected Post-SELL Reflection

In the future Phase14 SELL execution test, Broker ReadOnly evidence remains the Source of Truth after Submit.

Expected reflection policy:

- OrderList confirms SELL order status.
- Position evidence confirms `7203` quantity decreases or disappears.
- Cash / Buying Power evidence confirms funds increase.
- Ledger records a SELL execution-equivalent event only when OrderList + Position + Cash / Buying Power evidence is consistent.
- Asset is updated from Position / Cash evidence, not BrokerOrder alone.
- Reconcile checks the expected position and cash changes.
- Report shows current state and evidence separately.
- Audit records source, guard decisions, broker response classification, and reflection decisions.
- Notification Payload may be generated only; actual notification send remains prohibited.

If Broker status is unknown, Position / Cash evidence is inconsistent, or POST_SEND_UNKNOWN occurs, Runtime v2 must stop in `REVIEW_REQUIRED` or `BLOCKED` and must not auto-resubmit.

## 7. Next Phase Execution Conditions

Phase14 SELL execution may proceed only if all conditions are met immediately before Submit:

- Fresh Demo Broker ReadOnly snapshot confirms `7203 quantity >= planned_sell_quantity`.
- Fresh Demo Broker ReadOnly snapshot confirms `7203 available_quantity >= planned_sell_quantity`.
- Planned SELL quantity is `100` or less.
- Demo environment and demo base URL are confirmed.
- Production endpoint and production credential are blocked.
- Pending SELL plan exists only at `pending_order_plan/pending_order_plan.json`.
- Approval artifact is approved and hash-matched to the Pending plan.
- Duplicate submit guard is clean.
- RuntimeV2SubmitCommand is built directly from Runtime v2 models.
- Tachibana Demo Submit Adapter dry-run returns `DRY_RUN_READY`.
- No legacy `OrderCommand` / `RuntimeMode` is used as submit authority.
- The test remains one SELL order only.

## 8. Acceptance Criteria

| Acceptance Criteria | Result |
| --- | --- |
| 7203保有100株を確認 | PASS |
| SELL数量guardが保有数量超過をBLOCKする | PASS |
| SELL数量guardがavailable_quantity超過をBLOCKする | PASS |
| Pending-only SELLが維持される | PASS |
| Approval必須 | PASS |
| duplicate guard有効 | PASS |
| Runtime v2 pure submit pathでSELL可能な設計 | PASS |
| 旧Runtime Submit authority未使用 | PASS |
| 今回SELL Submitしていない | PASS |
| 次フェーズでSELL 1件を実行できる条件が明記されている | PASS |

## 9. Final Decision

**PHASE14D14_SELL_PREFLIGHT_COMPLETE**
