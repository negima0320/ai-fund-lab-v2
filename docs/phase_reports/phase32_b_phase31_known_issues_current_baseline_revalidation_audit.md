# Phase32-B - Phase31 Known Issues Current-Baseline Revalidation Audit

Audit type: READ-ONLY correctness audit.  
Target run: `runtime-test-historical-extended-smoke-20260829T181133963759Z`  
Reference requested: `phase31_final_baseline_known_issues_discovered_during_phase32(1).md`

## Scope and Exclusions

This audit uses only accumulated evidence from the current Historical validation run and local source/registry identity. It does not use Historical PnL or returns for parameter selection. It does not import Phase32-only architecture into Phase31. It does not run fresh-run, resume, replay, or long Historical. It does not implement repairs.

The requested reference file was not found in the workspace by filename or by the `P31-KI-*` identifiers. The seven issue definitions in the Phase32-B request are therefore treated as the authoritative issue list, with existing Phase reports used only as supporting context.

## Current Source and Baseline Identity

- Source commit: `887a3361eed9f46dccfa6b5b04cb8bb7ee83aa59`
- Current `producer.py` hash: `36f081ee0c3c9ec1b39e00ed83d01e931af8cfc0754d47303deb548dd8df04db`
- Run source baseline:
  - `accepted_artifact_hash`: `92f10d14d7558b3b2a8ac6f428cfb653583e26d6781014caa03a64de0518db94`
  - `registry_hash`: `bbb561d36a93f6cc8d4984dff6bff38b4b05219ea27f33768c13983c84e5e26a`
  - `source_dirty`: `true`
- PM Runtime Adapter authority was synchronized in Phase32-A before this run:
  - active PM set after synchronization: `control.position_management.accepted_set@sha256-fd83589a6f000156`
  - active PM set content hash: `fd83589a6f000156d9f3b9ce34bb37c0c2fc025bb2faf29c1bc08431ea2346e1`
  - accepted Runtime Adapter hash: `36f081ee0c3c9ec1b39e00ed83d01e931af8cfc0754d47303deb548dd8df04db`

## Current Run Evidence Coverage

The run was still `RUNNING` during this audit snapshot. At the latest observed read:

- run status: `RUNNING`
- completed business days: 73
- completed window observed: `2022-10-03` through `2023-01-19`
- next job observed: `2023-01-20:submit`

Daily evidence includes the normal stage set for completed days: `market_refresh`, `data_readiness`, `morning`, `position_management`, `strategy`, `sell_planning`, `submit`, `execution`, `current_valuation_refresh`, `runtime_state_refresh`, `positions`, and `day_completion`.

Because the target 300BD run was not complete, any issue requiring later-period observation is bounded by this partial-run evidence. Where current evidence is insufficient, the classification remains conservative.

## Summary Classification

| Issue | Classification | Production correctness impact | Strategy semantic impact | Runtime/control impact | Repair necessity |
|---|---|---:|---:|---:|---|
| `P31-KI-001` Prior EXIT semantic information loss | `CURRENT_REPRODUCED` | High | Yes | Yes | `MANDATORY` |
| `P31-KI-002` Source decision / campaign provenance loss | `CURRENT_REPRODUCED` | High | No | Yes | `MANDATORY` |
| `P31-KI-003` Campaign identity authority split | `CURRENT_REPRODUCED` | High | Yes | Yes | `MANDATORY` |
| `P31-KI-004` REENTRY safety reason classification ambiguity | `STRUCTURALLY_PRESENT_NOT_YET_OBSERVED` | Medium | Conditional | Yes | `CONDITIONAL` |
| `P31-KI-005` BUY_ADD explicit authority ambiguity | `CURRENT_REPRODUCED` | High | No | Yes | `MANDATORY` |
| `P31-KI-006` Adaptive Buy Quality target re-expansion | `CURRENT_REPRODUCED` | High | Yes | Yes | `MANDATORY` |
| `P31-KI-007` PC continuous target / 100-share lot resolution gap | `NOT_A_DEFECT_IN_CURRENT_BASELINE` | Low | No | No | `NO_REPAIR` |

## Issue-by-Issue Evidence

### P31-KI-001 - Prior EXIT semantic information loss

Classification: `CURRENT_REPRODUCED`  
Repair necessity: `MANDATORY`

Observed evidence:

- PM EXIT decisions preserve local reason semantics, for example:
  - `2022-10-04 83060`: `decision_type=EXIT`, `decision_reason=trend_and_opportunity_broken`, `reason_codes=["trend_and_opportunity_broken"]`, `position_campaign_id=pc-7c82ec6c7ee4b3d1-83060-0001`
  - `2022-10-04 89180`: `decision_type=EXIT`, `decision_reason=hard_stop_current_return`, `reason_codes=["hard_stop_current_return"]`
- Later REENTRY evaluation preserves only generic prior-exit identity:
  - unique REENTRY evaluation observations: 1646
  - `prior_exit_context_status=REVIEW_REQUIRED`: 1646
  - `prior_exit_reason_class=GENERIC`: 1646
- Example:
  - `2022-10-05 83060`: `semantic_buy_type=REENTRY`, `reentry_identity=PRIOR_EXIT_SAME_SYMBOL`, `prior_exit_business_date=2022-10-04`, `prior_exit_context_status=REVIEW_REQUIRED`, `prior_exit_reason_class=GENERIC`, `recovery_reason=insufficient_prior_exit_context`

Judgment: strict-prior PIT date identity is present, but EXIT semantic reason/context is not carried into later REENTRY evaluation. This is a correctness issue because REENTRY evaluation cannot distinguish a risk-driven EXIT from a generic closed campaign.

Known-issue comparison: correctly carried over from Phase31 and reproduced in the reconstructed baseline.

### P31-KI-002 - Source decision / campaign provenance loss

Classification: `CURRENT_REPRODUCED`  
Repair necessity: `MANDATORY`

Observed evidence:

- `execution/fills.json` across observed evidence:
  - records: 262 at the earlier full completed-stage sample
  - `source_decision_id` missing: 178
  - `source_decision_type` missing: 40
  - `pending_item_id` missing: 178
  - `order_plan_item_id` missing: 262
  - `position_campaign_id` present: 262
- Examples:
  - `2022-10-03 83060 BUY`: `source_decision_id=MISSING`, `source_decision_type=BUY`, `pending_item_id=MISSING`, `order_plan_item_id=MISSING`, `position_campaign_id=pc-7c82ec6c7ee4b3d1-83060-0001`
  - `2022-10-05 33700 SELL`: `source_decision_id=MISSING`, `source_decision_type=MISSING`
- Persistent ledger read-only inspection at audit time:
  - `.runtime/persistent_ledger/orders.jsonl`: 534 records, `source_decision_id` missing in 534, `position_campaign_id` missing in 534, `pending_item_id` present in 534
  - `.runtime/persistent_ledger/executions.jsonl`: 267 records, `source_decision_id`, `source_decision_type`, `pending_item_id`, `position_campaign_id`, and `campaign_id` missing in 267
  - `.runtime/persistent_ledger/positions.jsonl`: 822 records, source/campaign provenance fields missing in 822

Judgment: provenance is not preserved end-to-end from Strategy decision through pending/order/execution/fill/ledger. Submit-stage orders retain `pending_item_id`, but ledger executions and positions lose the core decision/campaign fields.

Known-issue comparison: correctly carried over from Phase31 and reproduced in the reconstructed baseline.

### P31-KI-003 - Campaign identity authority split

Classification: `CURRENT_REPRODUCED`  
Repair necessity: `MANDATORY`

Observed evidence:

- Current position/PM/fill campaign IDs use one authority family, for example `pc-7c82ec6c7ee4b3d1-94340-0001`.
- `positions/position_campaigns.json` uses a different authority family for the same symbol and nominal campaign ordinal, for example `pc-0933bfcd9c22aaaf-94340-0001`.
- Symbols with multiple campaign IDs across PM/fill/campaign evidence: 88.
- Examples:
  - `94340`: PM/fill `pc-7c82ec6c7ee4b3d1-94340-0001`; campaign authority `pc-0933bfcd9c22aaaf-94340-0001`
  - `94320`: PM/fill `pc-7c82ec6c7ee4b3d1-94320-0001` and `...-0002`; campaign authority `pc-d7897f467b62eedf-94320-0001` and `pc-57e3b3de16848884-94320-0002`

Judgment: same-symbol campaign identity is split across authorities. This can directly affect ADD/REDUCE/EXIT/REENTRY continuity because one subsystem can consider a campaign continuous while another emits a different campaign identity.

Known-issue comparison: correctly carried over from Phase31 and reproduced in the reconstructed baseline.

### P31-KI-004 - REENTRY safety reason classification ambiguity

Classification: `STRUCTURALLY_PRESENT_NOT_YET_OBSERVED`  
Repair necessity: `CONDITIONAL`

Observed evidence:

- REENTRY nodes frequently set `safety_restriction_status=FAIL_CLOSED` while the actual reason is prior-exit/context insufficiency:
  - `REENTRY_INSUFFICIENT_EVIDENCE`: observed
  - `prior_exit_context_status=REVIEW_REQUIRED`: observed
  - `recovery_reason=insufficient_prior_exit_context`: observed
- Non-REENTRY nodes also show `safety_restriction_status=REVIEW_REQUIRED` with `reason_codes=["REENTRY_NOT_APPLICABLE"]`, for example `2022-10-12 33500`.
- Broker and corporate-action evidence in observed examples is usually explicit and not negative:
  - `broker_eligibility_status=PASS`
  - `corporate_action_status=NO_EVENT`

Judgment: the field model is structurally ambiguous because `safety_restriction_status` is used as a broad fail-closed marker in paths that are not necessarily negative safety/broker/corporate-action blocks. However, this audit did not find a concrete case where supportive/informational/unknown evidence was definitively misclassified as an actual negative broker or corporate-action block. Keep this as conditional repair pending a focused classification contract review.

Known-issue comparison: carried over as a structural concern; not fully reproduced as a concrete misclassification in the current observed run window.

### P31-KI-005 - BUY_ADD explicit authority ambiguity

Classification: `CURRENT_REPRODUCED`  
Repair necessity: `MANDATORY`

Observed evidence:

- BUY_ADD plans observed: 16.
- Examples:
  - `2022-10-06 94340`: `planning_intent=BUY_ADD`, `planned_quantity=100`, `canonical_quantity_source=LEGACY_POSITION_SIZING`, `reason_codes=["position_sizing_positive_quantity_delta_maps_to_buy_add", "position_sizing_quantity_candidate_resolved"]`
  - `2022-10-12 94320`: `planning_intent=BUY_ADD`, `planned_quantity=100`, `quality_action=BUY_WAIT`, `quality_allocation_adjustment=0.0`, `canonical_quantity_source=LEGACY_POSITION_SIZING`
  - `2022-11-04 94320`: same pattern, `BUY_WAIT` yet `planned_quantity=100`
- Runtime planning lineage shows PM intent is `ADD` and PC weight intent is `INCREASE`, but `canonical_sizing_evidence` is empty for the decisive positive quantity fields:
  - `final_allocated_quantity=null`
  - `executable_quantity_delta=null`
  - `lot_feasibility_status=""`

Judgment: G129 accepted semantics are not being defect-treated again. The G129 rule that Runtime BUY_ADD submit must use order increment rather than position-scope delta remains the baseline. The current defect is upstream authority ambiguity: the positive BUY_ADD quantity can still be emitted through legacy position sizing / residual mechanics without a single explicit authoritative origin visible in the run evidence.

Known-issue comparison: correctly carried over from Phase31 and reproduced in the reconstructed baseline. Old Phase32 work may have amplified visibility, but this is present in the current baseline evidence.

### P31-KI-006 - Adaptive Buy Quality target re-expansion

Classification: `CURRENT_REPRODUCED`  
Repair necessity: `MANDATORY`

Observed evidence:

- Adaptive Buy Quality reduced or blocked many candidates:
  - reduced/blocking quality observations: 3284
  - `BUY_WAIT` / `quality_allocation_adjustment=0.0` examples exist.
- Downstream PC/PS still retains positive target or quantity fields after quality blocking:
  - observed re-expansion candidates: 154
  - `2022-10-06 99840`: PC `quality_action=BUY_WAIT`, `target_weight=0.125301`, `final_risk_adjusted_target_weight=0.035714`, `lot_aware_final_target_weight=0.125301`
  - `2022-10-06 99840`: PS `quality_action=BUY_WAIT`, `buy_quality_adjustment=0.0`, `final_target_quantity=100`, `discrete_authorized_quantity=0`
- Stronger execution-path examples exist in BUY_ADD planning:
  - `2022-10-12 94320`: `quality_action=BUY_WAIT`, `quality_allocation_adjustment=0.0`, yet `planning_intent=BUY_ADD`, `planned_quantity=100`
  - `2022-11-04 94320`: same pattern
  - `2022-11-09 94320`: same pattern

Judgment: quality-adjusted reduced/blocking authority can be re-expanded downstream toward base/pre-quality target or positive executable planning. This is an authority preservation defect, independent of Historical profitability.

Known-issue comparison: correctly carried over from Phase31 and reproduced in the reconstructed baseline.

### P31-KI-007 - PC continuous target / 100-share lot resolution gap

Classification: `NOT_A_DEFECT_IN_CURRENT_BASELINE`  
Repair necessity: `NO_REPAIR`

Observed evidence:

- Continuous-to-discrete conversion is visible rather than silent:
  - `g61_lot_aware_compatibility_consumed_by_runtime=true`
  - `g63_runtime_binding.g61_compatibility_consumed_by_runtime=true`
  - `final_capital_winner_binds_before_discrete_sizing=true`
  - `discrete_authorized_quantity`, `final_target_quantity`, `continuous_target_notional`, and lot feasibility fields are present in PS evidence.
- The observed conversion explains 100-share discreteness and lot feasibility constraints. The audit did not find evidence that PC investment meaning was silently overwritten by an undocumented lot conversion path.

Judgment: 100-share discreteness is expected and not a defect by itself. Current baseline evidence presents the conversion as an explicit discrete feasibility conversion, not a silent semantic override.

Known-issue comparison: no longer a defect in the current reconstructed Phase31 baseline for the observed window. It may have been exposed or amplified by older Phase32 analysis, but current evidence does not reproduce it as a correctness defect.

## Phase32-Only Semantics Explicitly Excluded

The audit excludes Phase32-only implementation ideas from the Phase31 baseline judgment. In particular, no issue is classified because a Phase32-only architecture would handle it better. Classifications above are based on current Phase31 accepted source and the current run evidence only.

## Recommended Repair Priority

1. `P31-KI-002` and `P31-KI-003`: repair first as shared identity/provenance foundations. They affect order/execution/ledger traceability and campaign continuity across multiple lifecycle actions.
2. `P31-KI-001`: repair next, binding prior EXIT semantic reason/context into closed-campaign and REENTRY evaluation with strict-prior PIT semantics.
3. `P31-KI-005` and `P31-KI-006`: repair together or in a tightly coordinated sequence, because BUY_ADD positive quantity authority and Adaptive Buy Quality preservation overlap in the observed BUY_WAIT -> BUY_ADD cases.
4. `P31-KI-004`: conditional repair after a focused classification contract review proves whether the ambiguity can produce a concrete wrong safety/broker/corporate-action block.
5. `P31-KI-007`: no repair recommended from current evidence.

## Confirmations

- NO CODE CHANGE in Phase32-B: confirmed. This task created only this audit report.
- NO fresh-run/resume/replay/long Historical executed by Codex in Phase32-B: confirmed.
- NO Strategy parameter/threshold/weight change: confirmed.
- NO Historical PnL/return used for parameter selection: confirmed.
- G129 BUY_ADD accepted semantics were not reclassified as a defect: confirmed.

## Final Judgment

`WHICH_PHASE31_KNOWN_ISSUES_ARE_ACTUALLY_REPRODUCED_AND_REQUIRE_REPAIR_IN_THE_CURRENT_BASELINE`

Actually reproduced and requiring repair in the current reconstructed Phase31 baseline:

- `P31-KI-001` Prior EXIT semantic information loss - `MANDATORY`
- `P31-KI-002` Source decision / campaign provenance loss - `MANDATORY`
- `P31-KI-003` Campaign identity authority split - `MANDATORY`
- `P31-KI-005` BUY_ADD explicit authority ambiguity - `MANDATORY`
- `P31-KI-006` Adaptive Buy Quality target re-expansion - `MANDATORY`

Not fully reproduced as a concrete current defect, but structurally present:

- `P31-KI-004` REENTRY safety reason classification ambiguity - `CONDITIONAL`

Not a defect in the current observed baseline:

- `P31-KI-007` PC continuous target / 100-share lot resolution gap - `NO_REPAIR`
