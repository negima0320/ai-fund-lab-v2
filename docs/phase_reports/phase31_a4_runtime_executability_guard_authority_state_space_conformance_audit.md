# Phase31-A4 — Runtime Executability / Guard Authority State-Space Conformance Audit

## PRIMARY_JUDGMENT

`PHASE31_A4_RUNTIME_EXECUTABILITY_AUTHORITY_STATE_SPACE_GAPS_CONFIRMED`

The current long-run pattern is not merely unrelated edge bugs. The audited common Runtime path has a broader executable-membership / authority-consumption coverage problem:

1. Some precomputable item-level authorities can still be discovered first at Submit after an item has remained executable through Planning/Pending.
2. Submit guard item failures are generally not normalized into AK9R29 typed guard fields, even when the semantic class is clear.
3. Cash, quantity, broker boundary, and post-send checks remain mostly conformant as legitimate stage-specific revalidations, not duplicate authority decisions.

A3 is the concrete confirmed instance: Historical corporate-action quarantine for `76920` was available in Runtime state but not consumed by Planning/Pending executable membership; Submit failed closed with `corporate_action_event_not_resolved`.

## Required Counts

| Count | Value |
| --- | ---: |
| `TOTAL_ACTIVE_BLOCKING_AUTHORITIES` | 16 |
| `MISSING_EARLY_CONSUMER_COUNT` | 1 |
| `DUPLICATE_AUTHORITY_DECISION_COUNT` | 0 |
| `PRODUCER_CONSUMER_GAP_COUNT` | 2 |
| `ITEM_TO_BATCH_ESCALATION_RISK_COUNT` | 1 |
| `UNTYPED_GUARD_PATH_COUNT` | 11 |
| `LEGAL_STATE_COMBINATIONS_AUDITED` | 18 |
| `UNCOVERED_LEGAL_STATE_COUNT` | 3 |
| `CRITICAL_GAP_COUNT` | 1 |
| `HIGH_GAP_COUNT` | 2 |

## Evidence Base

- SoT: `docs/02_architecture/runtime_architecture_v2.md`
  - Runtime order requires producer-before-consumer authority: Data Readiness / Safety / Planning / Pending / Submit / Execution / lifecycle.
  - Legitimate multi-layer checks include symbol-level order amount feasibility, aggregate batch cash feasibility, broker buying power, canonical quantity equality validation, stage-specific temporal validation, and post-fill reconciliation.
  - Invalid duplication includes downstream resizing, reclassifying item-scoped review as batch failure, reason-string side inference, and cash-meaning collapse.
- SoT: `docs/phase_reports/phase30_ak9r27_central_pending_review_scope_authority_contract_repair.md`
  - Pending Review Scope Authority owns item membership only, not cash, quantity, Strategy cap, Safety hard cap, broker feasibility, valuation, PM intent, PC allocation, or PS sizing.
  - Reviewed SELL remains batch-blocked; reviewed BUY must not submit; reviewed BUY must not block valid SELL continuation.
- SoT: `docs/phase_reports/phase30_ak9r29_runtime_system_guard_taxonomy_review_reason_normalization.md`
  - REVIEW/BLOCK evidence must carry typed fields such as `guard_class`, `guard_code`, scope, affected side, affected items, batch-blocking flag, recoverability, canonical owner, and consumer action.
- SoT: `docs/phase_reports/phase30_ak9r30_canonical_quantity_cash_authority_consumer_contract_cleanup.md`
  - Quantity chain is PC discrete executable quantity -> PS consumption -> Runtime Planning -> Pending -> Submit equality validation.
  - Cash meanings are distinct and may be validated at multiple stage boundaries without becoming duplicate authority.
- Code evidence:
  - `src/ai_fund_lab_v2/runtime_v2/submit/pipeline.py` marks multiple Submit guard failures with `should_have_been_blocked_at_planning=True`.
  - `src/ai_fund_lab_v2/runtime_v2/planning/morning_pipeline.py` consumes Opportunity BUY eligibility and Market Status BUY eligibility during candidate selection.
  - `src/ai_fund_lab_v2/runtime_v2/planning_submit_feasibility.py` is shared by Planning and Submit for cash, dynamic exposure, position sizing, and canonical quantity revalidation.
  - `src/ai_fund_lab_v2/runtime_v2/historical_support/corporate_action_quarantine.py` exposes a readable Historical symbol quarantine registry and `unresolved_entry`.
  - `src/ai_fund_lab_v2/runtime_v2/pending/review_scope_authority.py` does not consume cash, quantity, broker, safety, valuation, or corporate-action quarantine.
  - `src/ai_fund_lab_v2/runtime_v2/guard_taxonomy.py` can classify `corporate_action` as `DATA_INTEGRITY_SAFETY` / `CORPORATE_ACTION_UNRESOLVED`, but Submit item guard evidence is not currently a taxonomy producer.

## Authority Matrix

| AUTHORITY | CANONICAL_OWNER | PRODUCER_STAGE | EARLIEST_REQUIRED_CONSUMER | LATER_VALIDATION_CONSUMERS | CAN_CHANGE_EXECUTABLE_MEMBERSHIP | ITEM_SCOPED_OR_BATCH | TYPED_GUARD_CLASS | STAGE_SPECIFIC_OR_PRECOMPUTABLE | CURRENT_PLANNING_CONSUMED | CURRENT_PENDING_CONSUMED | CURRENT_SUBMIT_CONSUMED | CURRENT_EXECUTION_CONSUMED | CONFORMANCE_STATUS | GAP_DESCRIPTION |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Pending Review Scope Authority | `pending_review_scope_authority` | Pending generation/composition | Pending consume / Submit source selection | Sell Planning, Submit, lifecycle | Yes | Item and batch | `ITEM_SCOPED_REVIEW` / `BATCH_LEVEL_FAILURE` | Precomputable from Pending | Yes | Yes | Yes | Indirect | `CONFORMANT` | Owns only membership. Reviewed BUY excluded; reviewed SELL batch-blocked. |
| Historical / Production temporal authority | Data Readiness / Historical safety authority | Data Readiness before Planning | Data Readiness gate before Planning | Submit Data Readiness, Execution | Yes | Batch/system | `DATA_INTEGRITY_SAFETY` or `INTERNAL_SYSTEM_CONSISTENCY` | Precomputable plus stage-specific freshness | Yes | Indirect | Yes | Yes | `CONFORMANT` | A1 class fixed/passed for target run; safety authority propagated after initial checkpoint. |
| Historical corporate-action quarantine | Historical CA quarantine registry | Historical support / prior run detection | Planning candidate/executable membership, then Pending membership | Submit defense-in-depth, lifecycle terminalization | Yes | Symbol/item | Semantically `DATA_INTEGRITY_SAFETY` / `CORPORATE_ACTION_UNRESOLVED` | Precomputable once registry entry exists | No | No | Yes | Yes, no-submitted-order path | `MISSING_EARLY_CONSUMER` | A3: `76920` remained executable through Planning/Pending and was first blocked at Submit. |
| Corporate Action Adjustment Authority | Runtime CA adjustment authority | Submit/materialized CA evidence, Historical environment | Earliest stage with PIT event evidence; no later than Planning when event is known | Submit and Historical simulated submit | Yes | Item/symbol | `DATA_INTEGRITY_SAFETY` | Mixed: event-specific; precomputable when known | Partial/unclear | No | Yes | Yes | `PRODUCER_CONSUMER_SEMANTIC_GAP` | Submit has common fail-closed authority; early consumer coverage is not complete for known impacted symbols. |
| Market Status BUY Eligibility | `market_status.buy_eligibility` | Morning candidate selection from listed issues | Morning candidate selection | Submit guard revalidation | Yes | BUY item | `DATA_INTEGRITY_SAFETY` | Precomputable | Yes | Via item `listed_info` | Yes | N/A | `DUPLICATE_BUT_VALID_STAGE_SPECIFIC_VALIDATION` | Planning consumes it; Submit revalidates to catch stale/mutated Pending item authority. |
| Opportunity BUY Eligibility / lineage | Runtime BUY Opportunity Ranking Producer + eligibility resolver | Morning candidate selection | Morning candidate selection | Runtime Planning lineage, Submit hash/row revalidation | Yes | BUY item | `MARKET_PORTFOLIO_SAFETY` / `DATA_INTEGRITY_SAFETY` for lineage mismatch | Precomputable with stage-specific artifact hash revalidation | Yes | Via item `listed_info` | Yes | N/A | `DUPLICATE_BUT_VALID_STAGE_SPECIFIC_VALIDATION` | Planning filters non-eligible rows; Submit may block hash/row drift. |
| Strategy / PM intent authority | Strategy PM / Runtime Planning mapper | Strategy/PM, Runtime Planning | Runtime Planning | Pending, Submit lineage | Yes | Item | `MARKET_PORTFOLIO_SAFETY` / `INTERNAL_SYSTEM_CONSISTENCY` on missing authority | Precomputable | Yes | Yes | Yes | N/A | `CONFORMANT` | Runtime Planning maps quantity deltas; it must not decide Strategy. |
| PC discrete executable quantity | Portfolio Construction | PC / Position Sizing artifact | Position Sizing | Runtime Planning, Pending, Submit equality | Yes | Item | `EXECUTION_SAFETY` | Precomputable plus Submit equality | Yes | Yes | Yes | N/A | `CONFORMANT` | Submit validates equality; no resize/redecision confirmed. |
| Position Sizing authority | Strategy Position Sizing | Position Sizing | Runtime Planning | Planning Submit Feasibility, Submit | Yes | Item | `EXECUTION_SAFETY` | Precomputable | Yes | Yes | Yes | N/A | `CONFORMANT` | Shared feasibility catches missing/mismatched sizing. |
| Cash exposure / dynamic exposure authority | Strategy dynamic cash exposure + policy context | Planning | Planning Submit Feasibility | Submit aggregate feasibility | Yes | BUY item or batch | `EXECUTION_SAFETY` / `MARKET_PORTFOLIO_SAFETY` | Boundary-specific | Yes | Yes | Yes | Post-fill cash updates | `DUPLICATE_BUT_VALID_STAGE_SPECIFIC_VALIDATION` | Cash meanings remain separated; no generic cash collapse confirmed. |
| Current cash / buying power | Current SoT / broker cash authority | Runtime state refresh / broker readonly | Planning for BUY budget | Submit aggregate cash, broker boundary | Yes | BUY item/batch | `EXECUTION_SAFETY` | Stage-specific current boundary | Yes | Reservation evidence | Yes | Yes | `DUPLICATE_BUT_VALID_STAGE_SPECIFIC_VALIDATION` | Planning and Submit validate their own boundary from selected Current authority. |
| Submit aggregate feasibility | Planning Submit Feasibility shared evaluator | Planning and Submit | Planning before Pending generation | Submit revalidation | Yes | BUY item/batch | `EXECUTION_SAFETY` | Stage-specific revalidation | Yes | Yes | Yes | N/A | `DUPLICATE_BUT_VALID_STAGE_SPECIFIC_VALIDATION` | Legitimate because current/reserved state can differ at Submit. |
| Safety operation guard / Safety hard cap | Runtime Safety + Strategy hard cap authority | Safety / Strategy policy | Data Readiness / Planning | Submit guard | Yes | Portfolio/batch/side | `MARKET_PORTFOLIO_SAFETY` | Mixed, stage-specific safety refresh valid | Yes | Safety context carried | Yes | N/A | `CONFORMANT` | Submit check is valid fail-closed defense. |
| SELL current quantity authority | Runtime Current / PM SELL planning | Sell Planning from Current positions | Sell Planning | Submit SELL quantity equality/current revalidation | Yes | SELL item | `EXECUTION_SAFETY` | Stage-specific current boundary | Yes for Sell Planning | Yes | Yes | Yes | `DUPLICATE_BUT_VALID_STAGE_SPECIFIC_VALIDATION` | Submit blocks stale SELL if Current changed or missing; not a duplicate sizing decision. |
| Broker available quantity / broker-write feasibility | Broker ReadOnly or Historical simulated broker authority | Submit boundary | Submit | Execution / reconciliation | Yes | SELL side/item | `EXECUTION_SAFETY` | Stage-specific | No | No | Yes | Yes | `DUPLICATE_BUT_VALID_STAGE_SPECIFIC_VALIDATION` | Legitimate Submit-specific broker boundary check. |
| Broker write uncertainty / POST_SEND_UNKNOWN | Submit adapter / delivery ledger | Submit after attempted send | Submit state machine | Execution, Pending lifecycle, operator review | Yes | Batch/unknown submitted item | `EXECUTION_SAFETY` / `INTERNAL_SYSTEM_CONSISTENCY` if lifecycle handoff breaks | Stage-specific only | N/A | N/A | Yes | Yes | `CONFORMANT` | Automatic resubmit forbidden; lifecycle fails closed. |
| Pending lifecycle authority | Pending lifecycle runner | Pre-Data Readiness and next-session lifecycle | Orchestration invokes lifecycle | Data Readiness, Current valuation, day completion | Yes | Batch/item residual | `INTERNAL_SYSTEM_CONSISTENCY` when unsupported | Stage-specific after submit/execution evidence | N/A | Yes | Indirect | Yes | `CONFORMANT` | A2 repaired mixed BUY review / SELL continuation terminalization; unsupported states still fail closed. |

## State-Space Audit

| Legal State | Expected Authority | Expected Consumer | Allowed Next State | DR Continue? | Partial Submit? | SELL Continuation? | Fail-Closed? | Pending Terminalize? | Coverage |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| BUY-only, no reviewed items, all executable, not submitted | PC/PS + cash + market/opportunity eligibility | Pending -> Submit | submitted / review_required | Yes if readiness PASS | N/A | N/A | On guard failure | After submit/execution | Covered |
| SELL-only, no reviewed items, all executable | PM SELL + Current quantity | Pending -> Submit | submitted / review_required | Yes | N/A | N/A | On current/broker quantity failure | After terminal execution | Covered |
| Mixed BUY+SELL, no reviewed items | Combined Pending authority + side-specific guards | Submit | submitted / partial failure | Yes | Yes | Yes | On item/batch failure | After terminal execution | Covered |
| BUY-only, reviewed BUY only, no executable items | Pending Review Scope | Data Readiness/Pending lifecycle | remains review / expires | Continue only if lifecycle says non-blocking | No | N/A | No broker write | Yes if stale/no-fill conditions met | Covered |
| BUY-only, reviewed BUY + executable BUY | Pending Review Scope + cash/quantity | Submit only executable BUY | partial submit / review residual | Yes | N/A | N/A | Reviewed BUY must not submit | Terminalize residual only with evidence | Covered |
| SELL-only, reviewed SELL | Pending Review Scope | Pending/Submit | review_required | No normal submit | No | No | Yes, batch blocked | No until review | Covered |
| Mixed reviewed BUY + executable SELL | Pending Review Scope | Sell Planning / Submit | SELL submitted, BUY reviewed | Yes when readiness PASS | Yes | Must proceed | Fail closed if SELL guard fails | A2 terminalizes after SELL terminal/no-fill BUY | Covered |
| Mixed executable BUY + reviewed SELL | Pending Review Scope | Submit | batch review_required | No normal submit | No | No | Yes | No | Covered |
| Multiple item-scoped reviewed BUYs + executable BUY/SELL | Pending Review Scope | Submit | partial submit / residual review | Yes when executable subset valid | Yes | SELL must proceed | Reviewed items excluded | Yes after terminal evidence | Covered |
| No executable items, reviewed BUY residual only | Pending lifecycle | Pre-Data Readiness lifecycle | expired/review_required | Continue only after lifecycle terminalization | No | N/A | If unsupported/stale evidence missing | Yes when no-fill/non-submit proven | Covered |
| Executable item has known CA quarantine before Submit | CA quarantine registry | Planning/Pending | reviewed/blocked before Pending executable membership | Should continue without broker write for item | For other valid items yes | SELL should proceed | Yes item-scoped | Yes for quarantined residual | Uncovered |
| Executable item has CA adjustment unresolved at Submit | CA Adjustment Authority | Earliest known event consumer, then Submit | reviewed/blocked | Depends on earlier consumer | Other valid items yes | SELL should proceed if unrelated | Yes | Yes/no submitted item depending evidence | Partially covered |
| All executable, Submit fully submitted | Submit state machine | Execution | filled/reconciled/consumed | Yes next stage | Already done | Already done | On execution ambiguity | Yes after reconciled | Covered |
| Partial submit: submitted valid subset + reviewed BUY residual | Submit + Pending lifecycle | Execution then lifecycle | consumed/expired residual | Yes after terminal evidence | Already done | SELL already proceeded | On unknown/reject | Yes if A2 preconditions met | Covered |
| Partial submit: submitted subset + blocked CA item | Submit CA guard + lifecycle | Execution then lifecycle | review_required / terminal CA no-submit | Run may HALT until repair/operator | Already done | SELL should not be blocked | Yes item scoped, but run-level halt risk | Partially covered |
| POST_SEND_UNKNOWN | Submit adapter | Pending lifecycle / Execution ReadOnly | review_required/operator | No automatic continuation | No auto retry | No auto retry | Yes | No until reconciled | Covered |
| Execution partial fill | Execution/Reconciliation | Ledger/current apply | reconciled or review | Continue only after reconciliation | N/A | N/A | If ambiguous | Yes after reconciled | Covered conceptually |
| Stale Pending after previous session | Pending lifecycle | Pre-Data Readiness lifecycle | expired/review_required/blocked | Only if lifecycle resolves | No until resolved | SELL continuation only if scoped | Yes unsupported | Yes when evidence supports | Covered after A2 |

`UNCOVERED_LEGAL_STATE_COUNT=3` corresponds to:

1. Known Historical corporate-action quarantine item still executable at Planning/Pending.
2. Known common corporate-action adjustment unresolved item lacking a uniform early membership consumer.
3. Submit item guard REVIEW/BLOCK states lacking typed guard materialization for downstream consumers.

## A3 Corporate Action Path

| Question | Answer |
| --- | --- |
| Canonical corporate-action quarantine owner | `runtime_v2.historical_support.corporate_action_quarantine` owns Historical symbol quarantine registry; common CA adjustment authority owns resolved/unresolved adjustment proof. |
| When quarantine becomes available | When `upsert_quarantine` writes `.runtime/runtime_state/corporate_action_quarantine/historical_symbol_registry.json`; A3 registry entry for `76920` existed when Submit called `unresolved_entry`. |
| Already available at Planning time? | For A3 target run, yes as Runtime state evidence before Submit; Planning did not consume it. |
| Should Planning consume it? | Yes, when the registry entry is known before order generation. It changes executable membership and should mark the item reviewed/blocked before Pending executable membership. |
| Should Pending executable membership consume it? | Yes, as an item/symbol-level membership exclusion; Pending Review Scope may still not own cash/quantity. |
| Should Submit retain defense-in-depth revalidation? | Yes. Submit/broker boundary must remain fail-closed. |
| Is Submit revalidation legitimate after earlier blocking? | Yes. It should normally see no such executable item; if it does, it should block and emit typed guard evidence. |
| Is current Submit-only discovery a conformance gap? | Yes. A3 proves `UPSTREAM_EXECUTABLE -> DOWNSTREAM_NEW_BLOCKING_AUTHORITY -> FAIL_CLOSED/HALT`. |

## Same Defect-Family Search

Submit has explicit diagnostics for late-discovered conditions:

- `accepted_generation_binding` with `should_have_been_blocked_at_planning=True`
- `historical_corporate_action_symbol_quarantine` with `should_have_been_blocked_at_planning=True`
- `corporate_action_adjustment_authority` with `should_have_been_blocked_at_planning=True`
- `buy_market_status_eligibility` with `should_have_been_blocked_at_planning=True`
- `opportunity_buy_eligibility` with `should_have_been_blocked_at_planning=True`
- aggregate feasibility / dynamic cash / position sizing revalidation with `should_have_been_blocked_at_planning=True`
- `sell_current_position_quantity` with `should_have_been_blocked_at_planning=True`

Classification:

- `buy_market_status_eligibility`, `opportunity_buy_eligibility`, aggregate feasibility, dynamic cash, PS/PC quantity, and SELL current quantity have legitimate upstream consumers plus valid Submit revalidation.
- `accepted_generation_binding` is a lineage/temporal revalidation; Submit blocking is valid if artifacts drift after Planning.
- `historical_corporate_action_symbol_quarantine` is the confirmed missing early consumer.
- `corporate_action_adjustment_authority` is a broader coverage risk: common Submit fail-closed logic exists, but early membership consumption is not uniformly present for known impacted symbols.

## Typed Guard Audit

Correctly typed paths:

- Data Readiness uses `normalize_component_review_results` and emits `review_guard_classes`, `review_guard_codes`, and `review_guard_summary`.
- Pending lifecycle uses `normalize_review_result` for unsupported/stale lifecycle states and, after A2, materializes `INTERNAL_SYSTEM_CONSISTENCY` guard evidence for lifecycle REVIEW_REQUIRED.

Missing typed guard paths:

Submit item guard blocked paths currently materialize `guard_reason`, `violated_policy`, `submit_item_status`, and `should_have_been_blocked_at_planning`, but not AK9R29 typed guard fields. Active missing typed paths include:

1. `aggregate_submit_feasibility`
2. `accepted_generation_binding`
3. `historical_corporate_action_symbol_quarantine`
4. `corporate_action_adjustment_authority`
5. `safety_operation_guard`
6. `buy_market_status_eligibility`
7. `opportunity_buy_eligibility`
8. `supported_side`
9. `sell_current_position_quantity`
10. `broker_available_quantity`
11. `max_sell_liquidation_amount`

Mismatched typed guard paths:

- None confirmed. The main problem is absence, not an observed wrong typed class.

## BUY / SELL Independence

- Reviewed BUY does not block valid SELL under canonical Pending Review Scope.
- Reviewed SELL remains batch-blocking; this is intentional because SELL review may involve Current/broker quantity authority.
- A2 repair is active and conformant for mixed reviewed BUY + executable SELL continuation.
- A3 confirms valid SELLs (`54010`, `41700`) were submitted despite reviewed BUYs and one blocked BUY.
- Remaining risk is not SELL blocked by BUY review; it is a run-level HALT/REVIEW after partial Submit when a late item-level guard appears at Submit.

## Quantity And Cash

Quantity remains conformant:

```text
PC discrete executable quantity
-> PS consumption
-> Runtime Planning
-> Pending item / quantity_contract
-> Submit equality validation
```

Submit revalidation is legitimate and did not resize A3 `76920`: quantity stayed `500`, PC/PS authority was `PASS`, and the block reason was corporate-action quarantine.

Cash remains conformant:

```text
Strategy deployable budget
PC residual allocation
Current cash / buying_power
Pending reserved notional
Submit aggregate cash
broker buying power
post-fill cash
```

A3 `76920` had enough Submit cash/buying power (`321160` before, `277560` after reserved notional `43600`). The direct blocker was not cash.

## Ranked Gaps

1. Critical: Precomputable Historical corporate-action quarantine is not consumed by Planning/Pending executable membership.
   - Can cause long-run HALT: yes.
   - Can submit item that should have been reviewed: Submit prevents broker write, but item reaches Submit incorrectly.
   - Frequency/reachability: confirmed in A3.
   - Blast radius: all Historical long-run dates with quarantined symbols.

2. High: Submit item guard REVIEW/BLOCK evidence is not normalized into typed guard taxonomy fields.
   - Can cause long-run diagnosis churn: yes.
   - Can obscure item-vs-batch behavior: yes.
   - Blast radius: all Submit blocked paths.

3. High: Common corporate-action adjustment authority lacks a uniform early executable-membership consumer for known impacted symbols.
   - Can cause Submit-only fail-closed: yes when event evidence is known before Submit.
   - Blast radius: Production/Demo/Historical common CA adjustment path.

4. Medium: Run-level partial failure handling can escalate an item-scoped late guard into a long-run stop even when valid SELL/BUY subset has proceeded.
   - This is correct fail-closed behavior today, but needs bounded lifecycle/reporting semantics after early-consumer repair.

## Required Outcome Answer

The current long-run failure pattern is not just a collection of unrelated edge bugs. Evidence supports a broader Runtime executable-membership / authority-consumption coverage problem, centered on precomputable item-level guard authorities that are not uniformly consumed before Pending executable membership, plus missing typed Submit guard materialization.

This does not invalidate Phase30 cash/quantity centralization or A2. The broader issue is narrower: executable membership must consume precomputable blocking authorities before Submit, while Submit retains defense-in-depth revalidation.

## Next Task Recommendation

Do not repair one symbol.

Recommended bounded architecture repair sequence:

1. Precomputable authority coverage map:
   - Define a common `ExecutableMembershipGuard` consumer layer for Planning/Pending.
   - Scope it to precomputable item/symbol authorities only: Historical corporate-action quarantine, known CA adjustment unresolved, known market/listing prohibition, known opportunity lineage rejection, known temporal/data-integrity item invalidity.

2. Corporate-action family repair:
   - Add Planning/Pending consumption of Historical corporate-action quarantine.
   - Add common CA adjustment unresolved consumption when event evidence is known before Submit.
   - Keep Submit defense-in-depth unchanged.

3. Submit typed guard materialization:
   - Normalize every Submit blocked item through Runtime Guard Taxonomy.
   - Emit item-level `guard_class`, `guard_code`, affected item id, affected side, batch-blocking flag, recoverability, and canonical owner.

4. State-space regression coverage:
   - Add focused tests for legal reachable combinations: reviewed BUY + executable SELL + quarantined BUY; BUY-only quarantined item; common CA adjustment unresolved; typed Submit guard fields; POST_SEND_UNKNOWN preserved.

No implementation was performed in A4.
