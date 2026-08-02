# Phase24-HV BUY Review / SELL Continuation Contract

## Primary Contract

BUY item-scoped `REVIEW_REQUIRED` prohibits BUY submission. It does not automatically invalidate independent Position Management, SELL Planning, or approved SELL submission when valid SELL authority and Safety authority exist.

## Review Scope Classification

`REVIEW_REQUIRED` must be classified structurally:

```text
BUY_ITEM_SCOPED_REVIEW
PORTFOLIO_SCOPED_REVIEW
GLOBAL_SAFETY_REVIEW
AUTHORITY_UNKNOWN_REVIEW
```

`BUY_ITEM_SCOPED_REVIEW` applies when a specific BUY item is non-submittable for an item-local execution feasibility reason. Phase24-HT `max_exposure` failure for the BUY item is classified as `BUY_ITEM_SCOPED_REVIEW` only when canonical policy/current authority is present and the failed evidence is item-specific.

## Pending Representation

Pending must expose additive scope fields:

```text
buy_items_status
sell_items_status
plan_overall_status
approved_buy_item_ids
approved_sell_item_ids
review_required_buy_item_ids
review_required_sell_item_ids
review_scope
review_scope_source
review_scope_reason
sell_continuation_allowed
```

Legacy `state=REVIEW_REQUIRED` remains available for compatibility, but consumers must use the structured scope fields before allowing SELL continuation.

## Historical Safety Authority

Historical Daily Neutral Safety may be used for SELL continuation only when:

```text
Pending review_scope = BUY_ITEM_SCOPED_REVIEW
Safety itself is not REVIEW_REQUIRED
business_date matches
policy version matches
runtime test authority fields match
Current / Persistent Ledger is READY
PM and SELL Planning authorities are valid
```

Fail closed when:

```text
Safety artifact missing
business_date mismatch
policy version mismatch
Portfolio-wide risk review
Global safety review
authority unknown
corrupt Pending
ambiguous review scope
```

## Position Management And SELL Planning

Position Management and SELL Planning may continue only when all conditions hold:

```text
1. BUY review scope is BUY_ITEM_SCOPED_REVIEW
2. blocked BUY items have no approved BUY ids
3. valid same-business-date Historical Safety Authority exists or is resolvable
4. Current / Persistent Ledger position authority is READY
5. PM authority is valid
6. SELL Planning inputs are complete
7. no Portfolio-wide or Global Safety blocker exists
8. BUY review reason does not invalidate SELL risk handling
```

BUY items must not be mixed into the SELL path.

## Submit Boundary

Submit remains item-boundary hard validation:

```text
BUY REVIEW_REQUIRED:
  not submitted

SELL APPROVED:
  Submit Guard revalidation
  submitted only if final guard PASS
```

Submit Guard remains unchanged and final.

## Prohibited Changes

```text
max_exposure change
BUY amount rounding
Exposure weakening
Planning Preflight skip
Pending BUY promotion back to APPROVED
Submit Guard weakening
Unconditional Historical Neutral Safety
REVIEW_REQUIRED to PASS replacement
free-form reason-only fail-open
BUY evidence deletion
SELL without Safety
test-only branch
2022-07-25 special case
```
