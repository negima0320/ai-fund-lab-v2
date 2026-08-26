# Phase31-G128 — BUY_ADD Submit Review / Campaign Materialization Root-Cause Audit

## Final Decision

`G128_BUY_ADD_ACTUAL_PATH_ROOT_CAUSES_CONFIRMED_READY_FOR_NARROW_REPAIR`

## Scope

Task type: READ-ONLY root-cause audit.

Primary diagnostic run:

`runtime-test-historical-extended-smoke-20260825T135619843503Z`

Evidence cutoff follows G127: completed immutable artifacts through `2023-09-13`.

No implementation, config change, threshold change, fresh-run, resume, replay, long Historical execution, or run mutation was performed.

## Source Basis

Reports G113 through G127 were used as the contract basis, with G127 as the immediate entry evidence. Relevant current source was inspected for Portfolio Construction, Position Sizing, Runtime Planning, Pending/Submit review scope, execution fill projection, and campaign materialization.

Key current source boundaries:

- `src/ai_fund_lab_v2/runtime_v2/planning_submit_feasibility.py`
- `src/ai_fund_lab_v2/runtime_v2/pending/promotion.py`
- `src/ai_fund_lab_v2/runtime_v2/submit/pipeline.py`
- `src/ai_fund_lab_v2/strategy/shadow_runtime.py`
- `src/ai_fund_lab_v2/strategy/portfolio_construction.py`

## Executive Conclusion

G127's primary defect is reproduced and decomposes into three narrow root causes, not one broad Market Quality / ADD philosophy problem.

1. Authorized BUY_ADD mostly reaches Pending/Submit but is deferred by item-scoped review because Submit's canonical discrete quantity authority consumer requires all canonical quantity fields to equal the submitted item quantity. For reviewed ADDs, the submitted order increment is `100`, while `executable_quantity_delta` / `preflight_executable_quantity_delta` often describe a larger position-scope or stale cumulative delta such as `200`, `1200`, `2100`. Submit correctly fails closed on the inconsistency, but the inconsistency is an ADD quantity-contract propagation / consumer-scope defect, not legitimate Safety rejection.

2. The 5 BUY_ADD fills that do occur update current quantity, but their execution fill `position_campaign_id` is a runtime-owned `pc-f9cf...` identity that does not match the open canonical campaign id in `positions/position_campaigns.json`. G122's strict-prior ledger merge logic can merge BUY history when ledger execution identity lines up with the open campaign, but the actual fill path does not materialize those fills as same-campaign ADD events. This is a campaign identity / materialization boundary defect distinct from Submit review.

3. The 8 `MARKET_CANDIDATE_CASH_INTERACTION_FAIL_CLOSED` rows are separate. They occur before Submit, in PC/G115 marginal ADD classification. Same-date ADD evidence is positive/PASS, but the cash interaction consumer maps `FAIL_CLOSED` / `BLOCKED` interaction results to ADD insufficiency. This is a PC cash interaction consumer defect, not a Submit/Pending/campaign lifecycle defect.

## Authorized ADD Population

The G127 PM-linked authorized ADD population was reconstructed from actual completed artifacts by matching Submit BUY items against same-date canonical Position Sizing `semantic_type = BUY_ADD` rows.

AUTHORIZED_ADD_ROWS_RECONSTRUCTED = `74/74`

| Submit disposition | Count |
| --- | ---: |
| Submitted / PASS / filled path | 5 |
| REVIEW_REQUIRED / deferred | 69 |

Review reasons:

| Reason | Count |
| --- | ---: |
| `pc_discrete_quantity_authority_quantity_mismatch` | 67 |
| `reserved notional exceeds dynamic cash capacity` | 2 |

For all 69 reviewed ADD rows, the submitted item quantity differed from canonical `executable_quantity_delta` and `preflight_executable_quantity_delta`.

`mismatch_vs_item_quantity = exec+pre: 69`

Representative reviewed rows:

| Date | Symbol | Submit qty | `final_allocated_quantity` | `executable_quantity_delta` | `preflight_executable_quantity_delta` | Review reason |
| --- | --- | ---: | ---: | ---: | ---: | --- |
| 2022-10-06 | 94340 | 100 | 100 | 200 | 200 | `pc_discrete_quantity_authority_quantity_mismatch` |
| 2022-10-28 | 94320 | 100 | 100 | 200 | 200 | `pc_discrete_quantity_authority_quantity_mismatch` |
| 2022-11-25 | 76470 | 100 | 100 | 1200 | 1200 | `pc_discrete_quantity_authority_quantity_mismatch` |
| 2022-11-30 | 76470 | 100 | 100 | 2100 | 2100 | `pc_discrete_quantity_authority_quantity_mismatch` |

Filled controls:

| Date | Symbol | Submit qty | `final_allocated_quantity` | `executable_quantity_delta` | `preflight_executable_quantity_delta` | Result |
| --- | --- | ---: | ---: | ---: | ---: | --- |
| 2022-10-12 | 94320 | 100 | 100 | 100 | 100 | PASS / fill |
| 2022-10-12 | 94340 | 100 | 100 | 100 | 100 | PASS / fill |
| 2022-10-13 | 94340 | 100 | 100 | 100 | 100 | PASS / fill |
| 2023-02-15 | 54010 | 100 | 100 | 100 | 100 | PASS / fill |
| 2023-05-31 | 30410 | 100 | 100 | 100 | 100 | PASS / fill |

FILLED_VS_REVIEWED_ADD_PRIMARY_DIFFERENCE =
`filled rows have item quantity == final_allocated_quantity == executable_quantity_delta == preflight_executable_quantity_delta; reviewed rows do not`

## Submit Review Producer Trace

ITEM_SCOPED_REVIEW_REQUIRED_COUNT = `67` direct item-scoped deferred ADD rows, plus `2` additional reviewed ADD rows with reserved-cash review.

ITEM_SCOPED_REVIEW_PRODUCER =

`runtime_v2.planning_submit_feasibility._canonical_discrete_quantity_submit_authority`
-> `runtime_v2.pending.promotion._materialize_item_scoped_review_state`
-> `runtime_v2.submit.pipeline._buy_item_scoped_review_partial_submission_evidence`

Producer mechanics:

- `planning_submit_feasibility.py` builds `canonical_discrete_quantity_submit_authority`.
- It sets `authorized_quantity = authority.final_allocated_quantity`.
- It then requires `item.quantity`, resolved PS quantity, and optional lot-resolution quantity fields to match `authorized_quantity`.
- When an ADD row has `item.quantity = 100`, `final_allocated_quantity = 100`, but `executable_quantity_delta = 200` / `preflight_executable_quantity_delta = 200`, the authority returns `REVIEW_REQUIRED` with `pc_discrete_quantity_authority_quantity_mismatch`.
- Pending promotion materializes this as a BUY item-scoped review state.
- Submit consumes the review scope as `BUY_ITEM_SCOPED_REVIEW_PARTIAL_PASS_SUBMISSION` and records `not_submitted_reason = item_scoped_review_required`.

ITEM_SCOPED_REVIEW_REASON_COUNTS:

| Reason | Count |
| --- | ---: |
| `pc_discrete_quantity_authority_quantity_mismatch` | 67 |

## BUY_ADD Review Root Cause Classification

BUY_ADD_SUBMIT_REVIEW_ROOT_CAUSE_COUNTS:

| Class | Meaning | Count | Classification |
| --- | --- | ---: | --- |
| B | Cash / reserved notional | 2 | `EXPECTED_FAIL_CLOSED`, cash evidence must be preserved |
| K | Submit contract mismatch | 67 | `ACTION_TYPE_SCOPE_DEFECT` / `CONSUMER_DEFECT` |
| A/C/D/E/F/G/H/I/J/L | Other | 0 | Not observed as primary trigger |

The K rows are not legitimate Safety rejects. Safety is READY/PASS in the inspected Submit manifests. Submit is preserving fail-closed behavior because the canonical discrete quantity fields conflict. The defect is that actual BUY_ADD rows carry inconsistent increment-vs-position-scope quantity evidence into Submit.

SUBMIT_REDECIDES_STRATEGY_CAPITAL_PRIORITY = `NO`

Submit does not choose between ADD and NEW_BUY and does not re-rank capital. It verifies item-level executable quantity authority and fails closed on quantity mismatch.

BUY_ADD_SILENT_DROP = `NO`

The dominant non-fill path is explicit `REVIEW_REQUIRED` / `item_scoped_review_required`, not silent loss.

BUY_ADD_TERMINAL_STATE_EXPLICIT = `NO`

The reviewed ADD item is explicitly deferred/reviewed, but not terminally submitted or filled. This preserves safety but leaves ADD scaling unmaterialized until the authority contract is repaired.

## BUY_NEW Control

Same-date BUY_NEW population was reconstructed on dates where authorized BUY_ADD became reviewed.

SAME_DATE_BUY_NEW_COUNT = `284`

SAME_DATE_BUY_NEW_ITEM_REVIEW_RATE = `74 / 284 = 26.06%`

Same-date BUY_NEW review reasons:

| Reason | Count |
| --- | ---: |
| `item_scoped_review_required` | 37 |
| `reserved notional exceeds dynamic cash capacity` | 19 |
| `corporate_action_event_not_resolved` | 17 |
| `pc_discrete_quantity_authority_quantity_mismatch` | 1 |

AUTHORIZED_BUY_ADD_ITEM_REVIEW_RATE = `69 / 74 = 93.24%`

The same review authority can apply to BUY_NEW, but the `pc_discrete_quantity_authority_quantity_mismatch` pattern is overwhelmingly concentrated in BUY_ADD. BUY_NEW rows typically carry internally consistent `final_allocated_quantity = executable_quantity_delta = preflight_executable_quantity_delta = item quantity`. Reviewed ADD rows frequently do not.

## Filled BUY_ADD Campaign Materialization

All 5 true BUY_ADD fills from G127 were inspected:

| Date | Symbol | Fill qty | Fill campaign id | Canonical open campaign id |
| --- | --- | ---: | --- | --- |
| 2022-10-12 | 94320 | 100 | `pc-f9cfb6b5498e35e5-94320-0001` | `pc-e62b56d6967476ec-94320-0001` |
| 2022-10-12 | 94340 | 100 | `pc-f9cfb6b5498e35e5-94340-0001` | `pc-1018b460441d595a-94340-0001` |
| 2022-10-13 | 94340 | 100 | `pc-f9cfb6b5498e35e5-94340-0001` | `pc-1018b460441d595a-94340-0001` |
| 2023-02-15 | 54010 | 100 | `pc-f9cfb6b5498e35e5-54010-0001` | `pc-ace730ca2278c71f-54010-0001` |
| 2023-05-31 | 30410 | 100 | `pc-f9cfb6b5498e35e5-30410-0001` | `pc-9357311690cdfb6c-30410-0001` |

Current quantity reflects the fills, but the canonical campaign artifact still shows one initial BUY and no ADD history for these campaigns.

G122_ACTUAL_PATH_REACHED = `PARTIAL`

G122's materializer is reached for current quantity refresh, and `shadow_runtime._merge_strict_prior_ledger_history_into_open_campaign()` can merge strict-prior ledger events into an open campaign when the ledger campaign is compatible. However, the actual fill path carries a runtime-owned `pc-f9cf...` campaign identity that differs from the canonical open campaign id, so ADD event history is not appended to the intended campaign.

BUY_ADD_HISTORY_ROOT_CAUSE_COUNTS:

| Root cause | Count |
| --- | ---: |
| Fill campaign id differs from canonical open campaign id, ADD event not merged into same campaign history | 5 |

G122_ACTUAL_PATH_CLASS = `A_ACTUAL_RUNTIME_FILL_IDENTITY_PATH_DIFFERS_FROM_G122_MATERIALIZATION_ANCHOR`

This is not a reason to synthesize ADD history from quantity delta. The narrow repair must propagate/resolve actual BUY_ADD fill identity into the canonical open campaign identity, while preserving G122's no-synthetic-ADD contract.

## MCC Fail-Closed Rows

G127 identified 8 ADD rows where canonical ADD evidence was present but not consumed:

| Date | Symbol |
| --- | --- |
| 2022-10-21 | 94320 |
| 2022-11-29 | 76470 |
| 2023-03-20 | 94320 |
| 2023-04-21 | 94320 |
| 2023-06-20 | 21340 |
| 2023-08-16 | 94320 |
| 2023-09-05 | 94320 |
| 2023-09-08 | 94320 |

MCC_FAIL_CLOSED_ROWS_RECONSTRUCTED = `8/8`

MCC_FAIL_CLOSED_DEFECT_CONFIRMED = `YES`

Current PC code classifies ADD marginal increments as `INSUFFICIENT_EVIDENCE / MARKET_CANDIDATE_CASH_INTERACTION_FAIL_CLOSED` when the market-candidate-cash interaction result is `FAIL_CLOSED` or `BLOCKED`. This happens before PS, Runtime, Pending, Submit, or campaign materialization. It is a distinct PC consumer/interaction defect.

## Root Cause Topology

BUY_ADD_DEFECT_ROOT_CAUSE_TOPOLOGY = `THREE_NARROW_INDEPENDENT_ROOT_CAUSES`

| Boundary | Root cause | Explains |
| --- | --- | --- |
| PC/PS -> Submit quantity authority | ADD quantity fields conflict: submitted increment is 100 while executable/preflight quantity fields often carry larger cumulative values | Most authorized ADD non-fills |
| Execution fill -> campaign lifecycle | Runtime-owned fill campaign id does not match canonical open campaign id | 5/5 filled ADD history failures |
| PC G115 / market-candidate-cash interaction | Positive ADD evidence fails closed via `MARKET_CANDIDATE_CASH_INTERACTION_FAIL_CLOSED` | 8 evidence-present-but-not-consumed ADD rows |

## Safety Contracts To Preserve

SAFETY_CONTRACTS_TO_PRESERVE:

- Submit must continue to fail closed on true quantity mismatch.
- Submit must not re-rank Strategy capital priority.
- Reserved cash / dynamic cash capacity review must remain fail-closed.
- Corporate action quarantine must remain fail-closed.
- No synthetic order, fill, or ADD event may be created.
- PS remains discrete quantity owner.
- Runtime must not re-decide capital priority.
- G122 must not infer ADD history from mere current quantity delta.
- MCC repair must not make weak-tail Cash preference consume capital merely because ADD exists.

## Narrow Repair Plan

REPAIR_REGRESSION_PLAN_COMPLETE = `YES`

Recommended G129 repair scope:

1. Repair BUY_ADD discrete quantity contract propagation/consumption at the PC/PS -> Submit boundary:
   - Preserve Submit fail-closed behavior for malformed rows.
   - For `semantic_type = BUY_ADD`, require submitted item quantity to match the canonical ADD order increment, not stale/cumulative position-scope `executable_quantity_delta` if that field is not the item quantity authority.
   - Add regressions for reviewed examples such as `2022-10-06 / 94340`, `2022-10-28 / 94320`, `2022-11-25 / 76470`, and filled controls from `2022-10-12`.

2. Repair actual BUY_ADD fill campaign identity materialization:
   - Preserve the canonical open campaign id.
   - Merge actual BUY_ADD fills into the open campaign only when same-symbol open-campaign identity is proven by Runtime/Pending/PS lineage or strict-prior ledger evidence.
   - Do not synthesize ADD events from quantity deltas alone.

3. Repair or isolate the 8 MCC fail-closed ADD rows:
   - Keep Cash optionality and weak-tail fail-closed behavior.
   - Ensure positive ADD evidence is not discarded solely by an unrelated market-candidate-cash interaction field when the ADD-vs-Cash frontier contract is satisfied.

## Performance Interpretation

BUY_ADD_DEFECT_EXPLAINS_GENERAL_RETURN_SUPPRESSION = `YES_PARTIAL`

The defect materially suppresses Winner Scaling because 74 authorized ADDs shrink to 5 fills, and those 5 fills are not visible as same-campaign ADD history. This does not alone explain all performance behavior, but it directly breaks the small-entry -> confirmation -> ADD -> scaled-winner loop.

BUY_ADD_DEFECT_EXPLAINS_APRIL_BREAK_TIMING = `UNPROVEN`

The ADD defect is broad across months and regimes. G124/G125/G126 show April structural and early-failure questions remain separate characterization tracks. G128 confirms an ADD scaling defect, not an April-only timing root cause.

MANDATORY_REPAIR_FOUND = `YES`

## Required Output

AUTHORIZED_ADD_ROWS_RECONSTRUCTED = `74/74`

ITEM_SCOPED_REVIEW_REQUIRED_COUNT = `67`

ITEM_SCOPED_REVIEW_PRODUCER =
`runtime_v2.planning_submit_feasibility._canonical_discrete_quantity_submit_authority -> runtime_v2.pending.promotion._materialize_item_scoped_review_state -> runtime_v2.submit.pipeline._buy_item_scoped_review_partial_submission_evidence`

BUY_ADD_SUBMIT_REVIEW_ROOT_CAUSE_COUNTS =
`B cash/reserved notional = 2; K Submit contract mismatch = 67; all others = 0`

SAME_DATE_BUY_NEW_ITEM_REVIEW_RATE = `26.06%`

AUTHORIZED_BUY_ADD_ITEM_REVIEW_RATE = `93.24%`

FILLED_VS_REVIEWED_ADD_PRIMARY_DIFFERENCE =
`quantity fields internally consistent for filled ADD; executable/preflight quantity fields conflict with item quantity for reviewed ADD`

SUBMIT_REDECIDES_STRATEGY_CAPITAL_PRIORITY = `NO`

BUY_ADD_SILENT_DROP = `NO`

BUY_ADD_TERMINAL_STATE_EXPLICIT = `NO`

G122_ACTUAL_PATH_REACHED = `PARTIAL`

BUY_ADD_HISTORY_ROOT_CAUSE_COUNTS =
`fill campaign id mismatch with canonical open campaign id = 5`

G122_ACTUAL_PATH_CLASS =
`A_ACTUAL_RUNTIME_FILL_IDENTITY_PATH_DIFFERS_FROM_G122_MATERIALIZATION_ANCHOR`

MCC_FAIL_CLOSED_ROWS_RECONSTRUCTED = `8/8`

MCC_FAIL_CLOSED_DEFECT_CONFIRMED = `YES`

BUY_ADD_DEFECT_ROOT_CAUSE_TOPOLOGY = `THREE_NARROW_INDEPENDENT_ROOT_CAUSES`

SAFETY_CONTRACTS_TO_PRESERVE = `listed above`

REPAIR_REGRESSION_PLAN_COMPLETE = `YES`

BUY_ADD_DEFECT_EXPLAINS_GENERAL_RETURN_SUPPRESSION = `YES_PARTIAL`

BUY_ADD_DEFECT_EXPLAINS_APRIL_BREAK_TIMING = `UNPROVEN`

MANDATORY_REPAIR_FOUND = `YES`

FUTURE_INFORMATION_USED_FOR_PRODUCTION_DECISION = `NO`

PERFORMANCE_USED_TO_SELECT_PRODUCTION_PARAMETER = `NO`

CODE_CHANGED = `NO`

CONFIG_CHANGED = `NO`

FRESH_RUN_EXECUTED = `NO`

RESUME_EXECUTED = `NO`

REPLAY_EXECUTED = `NO`

LONG_HISTORICAL_EXECUTED = `NO`

## Next

`PHASE31_G129_BUY_ADD_ACTUAL_PATH_NARROW_REPAIR`

Repair only the confirmed boundaries above. Do not redesign ADD scoring, Market Quality, Risk Pacing, Safety, Position Sizing ownership, or Runtime capital priority.
