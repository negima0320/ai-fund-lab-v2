# Phase14-E21 Tachibana 11102 Root Cause Audit & Execution ReadOnly Completion

## Summary

Phase14-E21 audited the Tachibana Demo `BUSINESS_REJECT` / `sResultCode=11102` observed in Phase14-E20 and completed the Runtime v2 Execution ReadOnly connection.

Final judgment: `PHASE14E21_ROOT_CAUSE_IDENTIFIED`

Root cause:

The E20 rejects were not caused by Runtime v2 issue-code normalization or by missing `CLMKabuNewOrder` request fields. The D8 accepted BUY request and E20 rejected BUY requests have the same broker request structure; after E19, E20 sends 4-digit broker issue codes. The remaining differentiator is the submitted issue code set itself. Therefore the actionable root cause is:

`Runtime v2 Demo Planning/Submit only filters 9000-series, but does not yet verify Tachibana Demo orderability for non-9000 candidate symbols.`

E20 submitted the following normalized symbols:

- `65220 -> 6522`
- `78780 -> 7878`
- `68970 -> 6897`
- `63270 -> 6327`
- `45910 -> 4591`

All five reached Broker Submit and returned:

- `p_errno=0`
- `sResultCode=11102`
- `business_classification=BUSINESS_REJECT`
- `order_number_present=false`

## Prohibited Actions

| Action | Result |
| --- | --- |
| Additional Submit | Not executed |
| Production order | Not executed |
| Production Broker API Write | Not executed |
| Notification actual send | Not executed |
| launchd change | Not executed |
| Phase9 Runtime | Not used |
| Phase9 Writer | Not used |

## Request-Level Comparison

The request payloads below are reconstructed through the same `TachibanaCashStockOrderRequestBuilder`. Volatile fields are excluded:

- `p_no`
- `p_sd_date`
- `sSecondPassword`

### D15 Success: 7203 SELL ACCEPTED

| Field | Value |
| --- | --- |
| `sCLMID` | `CLMKabuNewOrder` |
| `sZyoutoekiKazeiC` | `1` |
| `sIssueCode` | `7203` |
| `sSizyouC` | `00` |
| `sBaibaiKubun` | `1` |
| `sCondition` | `0` |
| `sOrderPrice` | `0` |
| `sOrderSuryou` | `100` |
| `sGenkinShinyouKubun` | `0` |
| `sOrderExpireDay` | `0` |
| `sGyakusasiOrderType` | `0` |
| `sGyakusasiZyouken` | `0` |
| `sGyakusasiPrice` | `*` |
| `sTatebiType` | `*` |
| `sTategyokuZyoutoekiKazeiC` | `*` |

Result:

- status: `ACCEPTED`
- broker_order_id_hash present
- post_send_unknown: `false`

### D8 Success: 7203 BUY ACCEPTED

D8 is important because it removes `BUY` itself as a suspected cause.

| Field | Value |
| --- | --- |
| `sCLMID` | `CLMKabuNewOrder` |
| `sZyoutoekiKazeiC` | `1` |
| `sIssueCode` | `7203` |
| `sSizyouC` | `00` |
| `sBaibaiKubun` | `3` |
| `sCondition` | `0` |
| `sOrderPrice` | `0` |
| `sOrderSuryou` | `100` |
| `sGenkinShinyouKubun` | `0` |
| `sOrderExpireDay` | `0` |
| `sGyakusasiOrderType` | `0` |
| `sGyakusasiZyouken` | `0` |
| `sGyakusasiPrice` | `*` |
| `sTatebiType` | `*` |
| `sTategyokuZyoutoekiKazeiC` | `*` |

Result:

- status: `ACCEPTED`
- broker_order_id_hash present
- post_send_unknown: `false`
- Broker OrderList confirmed `7203 BUY 100` as filled in D8.

### E20 Failure: BUY BUSINESS_REJECT

E20 request structure is the same as D8 BUY except `sIssueCode`.

| Runtime Symbol | Broker `sIssueCode` | Side | Market | Quantity | Result |
| --- | --- | --- | --- | --- | --- |
| `65220` | `6522` | BUY / `3` | `00` | `100` | `sResultCode=11102` |
| `78780` | `7878` | BUY / `3` | `00` | `100` | `sResultCode=11102` |
| `68970` | `6897` | BUY / `3` | `00` | `100` | `sResultCode=11102` |
| `63270` | `6327` | BUY / `3` | `00` | `100` | `sResultCode=11102` |
| `45910` | `4591` | BUY / `3` | `00` | `100` | `sResultCode=11102` |

Shared E20 request fields:

| Field | Value |
| --- | --- |
| `sCLMID` | `CLMKabuNewOrder` |
| `sZyoutoekiKazeiC` | `1` |
| `sSizyouC` | `00` |
| `sBaibaiKubun` | `3` |
| `sCondition` | `0` |
| `sOrderPrice` | `0` |
| `sOrderSuryou` | `100` |
| `sGenkinShinyouKubun` | `0` |
| `sOrderExpireDay` | `0` |
| `sGyakusasiOrderType` | `0` |
| `sGyakusasiZyouken` | `0` |
| `sGyakusasiPrice` | `*` |
| `sTatebiType` | `*` |
| `sTategyokuZyoutoekiKazeiC` | `*` |

## Required Comparison Items

| Item | D15 SELL 7203 | D8 BUY 7203 | E20 BUY set | Finding |
| --- | --- | --- | --- | --- |
| Issue Code | `7203` | `7203` | `6522`, `7878`, `6897`, `6327`, `4591` | Only material differentiator vs D8 BUY |
| Market | `00` | `00` | `00` | Same |
| Side | SELL / `1` | BUY / `3` | BUY / `3` | D8 proves BUY accepted |
| Order Type | `CLMKabuNewOrder` | `CLMKabuNewOrder` | `CLMKabuNewOrder` | Same |
| Price Type | Market | Market | Market | Same |
| Price | `0` | `0` | `0` | Same |
| Quantity | `100` | `100` | `100` | Same |
| Lot | 100-share unit | 100-share unit | 100-share unit | Same |
| Account | `sZyoutoekiKazeiC=1` | `1` | `1` | Same |
| Cash/Margin | `sGenkinShinyouKubun=0` | `0` | `0` | Same |
| Trade Type | cash stock | cash stock | cash stock | Same |
| Settlement | cash | cash | cash | Same |
| Customer Type | no separate field found | no separate field found | no separate field found | No D15/E20 difference |
| Branch | no separate field found | no separate field found | no separate field found | No D15/E20 difference |
| Product Category | `011` after E19 metadata | `011` after E19 metadata | `011` | Same metadata class |
| Security Type | `011` after E19 metadata | `011` after E19 metadata | `011` | Same metadata class |
| Exchange | `sSizyouC=00` | `00` | `00` | Same |
| Request parameter list | 15 non-secret fields | 15 non-secret fields | 15 non-secret fields | Same |
| POST fields | same plus second password at send boundary | same | same | Same, secret not saved |
| Builder omitted fields | no evidence of E20-only omission | no evidence | no evidence | Not root cause |

## Broker Response Comparison

| Field | D15 SELL 7203 | D8 BUY 7203 | E20 BUY set |
| --- | --- | --- | --- |
| accepted | `true` | `true` | `false` |
| status | `ACCEPTED` | `ACCEPTED` | `REJECTED_OR_UNKNOWN` |
| post_send_unknown | `false` | `false` | `false` |
| order_number_present | true by broker_order_id_hash | true by broker_order_id_hash | `false` |
| p_errno | not saved in older D15 artifact | not saved in older D8 artifact | `0` |
| sResultCode | success implied by `ACCEPTED` | success implied by `ACCEPTED` | `11102` |
| business_classification | accepted implied | accepted implied | `BUSINESS_REJECT` |

E20 response normalizer did not collapse the result into unknown:

- `p_err_classification=BUSINESS_REJECT`
- `business_classification=BUSINESS_REJECT`
- `result_code_present=true`
- `result_code_zero=false`
- `order_number_present=false`

## Root Cause

The evidence rules out the following:

- 5-digit issue code passed to broker: ruled out by E20 `sIssueCode` values being 4-digit.
- BUY side itself: ruled out by D8 `7203 BUY 100` accepted.
- Market order shape: ruled out by D8 using the same market order fields.
- Missing common request field: ruled out by identical non-secret `CLMKabuNewOrder` field set.
- Response normalizer misclassification: ruled out by redacted classification preserving `sResultCode=11102` and `BUSINESS_REJECT`.

The identified root cause is a missing Tachibana Demo orderability/capability filter for non-9000 candidate symbols.

Runtime v2 currently excludes 9000-series for Demo, but E20 shows that non-9000 symbols can still be rejected by Tachibana Demo even with valid 4-digit issue codes and valid request shape.

## Execution ReadOnly Completion

E21 connected the Runtime v2 Execution Job to a normal Broker ReadOnly ingestion pipeline.

Implemented:

- Runtime v2 execution pipeline interface:
  - `src/ai_fund_lab_v2/runtime_v2/execution/readonly_pipeline.py`
- Broker-side adapter boundary:
  - `src/ai_fund_lab_v2/broker/runtime_v2_readonly_adapter.py`
- CLI connection:
  - `src/ai_fund_lab_v2/runtime_v2/cli/run_daily_operation.py`
- Test:
  - `tests/runtime_v2/test_phase14e21_execution_readonly_pipeline.py`

The Runtime v2 package does not directly import `ai_fund_lab_v2.broker`; the actual Broker call is behind a provider/adapter boundary.

## Execution Job Evidence

Command executed:

`python3 -m ai_fund_lab_v2.runtime_v2.cli.run_daily_operation --mode demo --job execution --business-date 2026-07-08 --submit-enabled false --notification-mode payload-only ...`

Manifest:

`.runtime/runtime_state/run_manifest/2026-07-08/runtime-v2-execution-2026-07-08-20260708T061003.808159+0000.json`

Result:

- exit_code: `20`
- final_state: `REVIEW_REQUIRED`
- stage: `runtime_v2_execution_readonly_pipeline`
- stage status: `REVIEW_REQUIRED`
- snapshot_status: `PASS_WITH_WARNINGS`
- orderlist_readonly_connected: `true`
- execution_reflection_connected: `true`
- ledger_connected: `true`
- asset_connected: `true`
- asset_current_written: `false`
- reconcile_status: `REVIEW_REQUIRED`
- reconcile_findings: `8`

Snapshot:

`.runtime/runtime_state/broker_readonly/2026-07-08/tachibana_snapshot.json`

Broker ReadOnly result:

- orders_count: `0`
- executions_count: `0`
- positions_count: `7`
- cash/buying_power present: `20,000,000`

Interpretation:

- E20 rejected orders did not appear in Broker OrderList, consistent with `order_number_present=false`.
- Demo Broker daily reset evidence was captured.
- Runtime did not overwrite Current SoT with Demo Broker cash/positions.
- Reconcile correctly stopped at REVIEW_REQUIRED due Broker demo evidence vs Runtime 1,000,000 yen Current SoT.

## Verification

- `python3 -m pytest tests/runtime_v2/test_phase14e21_execution_readonly_pipeline.py` -> 1 passed
- `python3 -m pytest tests/runtime_v2/test_phase13_l_no_legacy_runtime_import.py tests/runtime_v2/test_phase13_q_no_side_effects.py tests/runtime_v2/test_phase13_x_legacy_runtime_isolation.py tests/runtime_v2/test_phase14e21_execution_readonly_pipeline.py` -> 8 passed
- `python3 -m pytest tests/runtime_v2` -> 325 passed

## Acceptance Review

| Acceptance Item | Result |
| --- | --- |
| 11102 cause identified with evidence | PASS |
| D15 vs E20 request diff listed | PASS |
| D8 BUY accepted used to isolate BUY-side factor | PASS |
| Issue code normalization verified | PASS |
| Broker response classification preserved | PASS |
| Additional Submit not executed | PASS |
| Production order not executed | PASS |
| Execution Job Broker ReadOnly connected | PASS |
| Execution Reflection connected | PASS |
| Ledger ingestion connected | PASS |
| Asset policy connected without overwriting Demo Current | PASS |
| Reconcile connected | PASS |
| Morning -> Submit -> Broker -> Execution -> Report is normal Runtime path | PASS, but state is REVIEW_REQUIRED due broker business reject and demo reset reconcile findings |

## Next Required Work

1. Add a Tachibana Demo orderability preflight/capability filter beyond 9000-series.
2. The filter should not hard-code AI logic; it should be BrokerCapability or Broker Adapter evidence.
3. Candidate Planning should skip or review symbols that are not Demo-orderable.
4. Keep E20 Pending consumed; do not resubmit it.
5. For the next retry, generate a fresh Morning Pending and submit only candidates passing Demo orderability preflight.

## Final Judgment

`PHASE14E21_ROOT_CAUSE_IDENTIFIED`

