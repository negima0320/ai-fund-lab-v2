# Phase24-IE Aggregate Feasibility BUY Item Review / SELL Continuation Contract

## 1. Primary Judgment

`PHASE24_IE_BUY_ITEM_SCOPED_REVIEW_SELL_CONTINUATION_REPAIRED_SHORT_VALIDATION_PASS_RUNTIME_RERUN_REQUIRED`

Phase24-IE freezes the contract between Phase24-ID aggregate Planning Submit Feasibility and Phase24-HV BUY review / SELL continuation.

## 2. Scope

This contract covers only Runtime state classification after aggregate Planning Submit Feasibility returns `REVIEW_REQUIRED` for BUY items. It does not change Strategy, Ranking, Position Sizing, PM decision logic, BUY quantity, max exposure, cash reserve, Submit Guard, or SELL Submit Guard.

## 3. Aggregate Feasibility Result

Planning Submit Feasibility remains aggregate over the approved Pending batch. Sequential BUY reservation for cash, buying power, exposure, and position count is preserved.

If any BUY item violates a concrete canonical policy with valid authority, the batch may not become `APPROVED`.

## 4. BUY Item-Scoped Review

`BUY_ITEM_SCOPED_REVIEW` is valid only when:

- the top-level Pending state is `REVIEW_REQUIRED`
- `approved_item_ids` is empty
- `approved_buy_item_ids` is empty
- all non-PASS feasibility items are BUY items
- each review-required BUY item has a concrete `violated_policy` and `violated_policy_source`
- `review_required_sell_item_ids` is empty
- `sell_continuation_allowed` is true

The BUY review item remains non-submittable. No BUY item may cross the Submit boundary from this Pending state.

## 5. Batch Atomicity

Phase24-IE keeps batch submit atomicity for the reviewed Pending plan:

```text
Aggregate batch REVIEW_REQUIRED
  -> approved_item_ids = []
  -> approved_buy_item_ids = []
  -> approved_sell_item_ids = []
  -> no Submit boundary crossing from that Pending plan
```

An item that passed feasibility inside the reviewed batch may be recorded with `feasibility_status = PASS`, but its batch submit state must show that it is blocked by the batch review and is not approved for Submit.

## 6. SELL Continuation

SELL Planning may continue when Pending is structurally classified as `BUY_ITEM_SCOPED_REVIEW` and valid same-date Historical Safety authority exists. This does not mean the reviewed BUY batch is submitted. It means existing holdings PM and SELL planning are not globally blocked by an unrelated BUY item review.

## 7. Historical Safety Resolver

Historical Safety resolver must not classify a valid same-date `BUY_ITEM_SCOPED_REVIEW` Pending as a global lifecycle mismatch solely because top-level state is `REVIEW_REQUIRED`.

It must still fail closed for:

- missing safety context
- business-date mismatch
- runtime identity mismatch
- unknown review scope
- missing policy authority
- SELL review items
- non-empty approved BUY item IDs
- global Safety review

## 8. Runtime Boundary

`REVIEW_REQUIRED` is not always a global runtime block. Consumers must inspect review scope and side-specific item IDs.

`BUY_ITEM_SCOPED_REVIEW` blocks BUY Submit and permits SELL continuation only under the authority checks above.

## 9. Next Task

Operator historical extended smoke rerun for the Phase24-ID/IE runtime path.
