# Phase29-L21T-AC - REDUCE Lot-Aware Semantic Contract Design and Implementation Gate

Task ID: Phase29-L21T-AC

Mode:

```text
DESIGN ONLY / NO IMPLEMENTATION
```

Primary Judgment:

```text
PHASE29_L21T_AC_REDUCE_LOT_AWARE_SEMANTIC_CONTRACT_DESIGNED_IMPLEMENT_IN_PHASE29_MINIMAL_OBSERVABILITY_ONLY
```

Implementation Gate:

```text
IMPLEMENT_IN_PHASE29
```

This gate approves only the minimal semantic / observability contract described here. It does not approve REDUCE ratio tuning, forced minimum-lot selling, persistent reduce debt, Pullback / Breakdown modeling, BUY sizing changes, or any performance optimization.

## Task Scope

Current phase:

```text
Phase29
```

Primary run:

```text
runtime-test-historical-smoke-20260812T212155604711Z
```

Task ID uniqueness:

```text
Phase29-L21T-AC appeared only as the recommended next task in the AB report.
No existing AC task/report/implementation was found.
```

No runtime mutation, resume, replay, recovery, fresh-run, long Historical, 100BD, Pending edit, Ledger edit, Current edit, Strategy implementation, Runtime implementation, or config change was performed.

## AB Evidence Summary

Inherited AB root cause:

```text
E_MULTI_CAUSAL
  C_STRATEGY_TO_EXECUTION_SEMANTIC_GAP
  B_OBSERVABILITY_GAP
```

AB evidence:

```text
PM REDUCE decisions:                         72
Deduped semantic REDUCE decisions:           72
Executable non-zero REDUCE:                   4
Lot-zero REDUCE:                             27
Minimum-notional zero / other policy:        41
Unresolved / missing materialization:         0
Actual SELL_REDUCE plans:                     4
Submit + execution/fill for executable:       4
Lot-zero conversion rate:                 37.50%
All-zero REDUCE rate:                     94.44%
```

The objective is not to maximize REDUCE conversion. The objective is to preserve the meaning of PM risk-reduction intent under discrete market constraints.

## Problem Definition

PM can validly express:

```text
LIGHT REDUCE
```

but a small position may make the requested partial reduction physically unexpressible:

```text
100 shares * 25% = 25 shares
tradable unit = 100 shares
executable partial quantity = 0
```

The current behavior is safety-preserving, but semantically incomplete when `0 shares` is indistinguishable from pure HOLD, missing materialization, minimum-notional block, or lifecycle defect.

## Existing Authority Chain

Current REDUCE authority chain:

```text
PM
  -> REDUCE intent + reduce_intensity
  -> canonical reduce intensity authority
  -> Portfolio Construction partial target weight
  -> Position Sizing discrete quantity
  -> Runtime Planning SELL_REDUCE only if non-zero executable
  -> Sell Planning quantity contract
  -> Pending / Submit / Execution
```

Key evidence:

- PM says Position Management emits reduce intensity while Sell Planning owns broker quantity calculation: `src/ai_fund_lab_v2/runtime_v2/position_management/producer.py:635`.
- Canonical ratios are `LIGHT=0.25`, `MEDIUM=0.33`, `STRONG=0.50`: `src/ai_fund_lab_v2/strategy/reduce_intensity_authority.py:9`.
- Position Sizing floors REDUCE quantity and zeros below lot/minimum notional: `src/ai_fund_lab_v2/strategy/position_sizing.py:871`.
- Runtime Planning requires PM EXIT authority before full liquidation: `src/ai_fund_lab_v2/strategy/runtime_planning.py:969`.
- Runtime Planning maps non-zero negative quantity to SELL_REDUCE and zero delta to NO_ACTION: `src/ai_fund_lab_v2/strategy/runtime_planning.py:1243`.
- Sell Planning already has a precise non-executable REDUCE quantity contract: `src/ai_fund_lab_v2/runtime_v2/planning/sell_pipeline.py:1728`.

## Existing REDUCE / EXIT Semantic Contract

Existing docs already establish:

```text
REDUCE = partial exposure reduction intent
EXIT   = full close intent
```

Phase28-D25 contract:

```text
REDUCE -> SELL_REDUCE when partial executable; no silent SELL_EXIT escalation
EXIT   -> SELL_EXIT preserved
```

Phase28-D34 contract:

```text
REDUCE intensity flows through canonical authority without converting REDUCE into EXIT.
Single-lot LIGHT REDUCE must not force EXIT.
```

Therefore:

```text
REDUCE raw quantity < 1 lot
does not authorize
REDUCE -> EXIT
```

## Discrete-Lot Expressiveness Problem

Small positions cannot express the full continuous REDUCE vocabulary:

```text
100 shares: executable choices are 0 or 100 shares.
200 shares: executable choices are roughly 0, 100, or 200 shares.
500 shares: 25% target = 125 shares, floor to 100 shares, actual 20%.
```

The smaller the position, the larger the approximation error between Strategy intent and executable market action.

## One-Lot / Small-Lot Examples

Case 1 - LIGHT REDUCE / trend not broken:

```text
position = 100
tradable unit = 100
PM = LIGHT REDUCE 25%
raw = 25
discrete executable partial = 0
semantic outcome = REDUCE_UNEXECUTABLE_DUE_TO_DISCRETE_LOT
runtime action = NO_SELL_ORDER
position = unchanged
next day = fresh PM reevaluation
```

Case 2 - MEDIUM REDUCE / partial impossible:

```text
position = 100
PM = MEDIUM REDUCE 33%
raw = 33
discrete executable partial = 0
no silent full EXIT
```

Case 3 - STRONG REDUCE / 100-share position:

```text
STRONG = 50%
raw = 50
discrete executable partial = 0
no automatic EXIT unless PM / Safety explicitly emits EXIT
```

Case 4 - Explicit EXIT:

```text
position = 100
PM / Safety = EXIT
expected = 100-share SELL
REDUCE lot-zero semantics must not block EXIT
```

Case 5 - 200-share LIGHT REDUCE:

```text
raw = 50
floor = 0
ceil = 100 would sell 50% instead of requested 25%
no automatic ceil without explicit Strategy authority
```

Case 6 - 500-share LIGHT REDUCE:

```text
raw = 125
floor = 100
actual reduction = 20%
existing floor approximation can remain acceptable when at least one lot is executable
```

## Lot-Zero vs Minimum-Notional-Zero Separation

AB separated:

```text
Lot-zero REDUCE:                      27
Minimum-notional zero / other policy: 41
```

These should not share a single semantic label. The next implementation should distinguish at least:

```text
REDUCE_UNEXECUTABLE_DUE_TO_DISCRETE_LOT
REDUCE_UNEXECUTABLE_DUE_TO_MINIMUM_NOTIONAL
REDUCE_UNEXECUTABLE_DUE_TO_POLICY_OR_SAFETY
REDUCE_QUANTITY_AUTHORITY_UNRESOLVED
```

The first two can be evidence/reason-code extensions; they do not require a new persistent lifecycle.

## Design Principles

```text
REDUCE intent != EXIT intent
Execution / Position Sizing must not silently transform REDUCE intensity into EXIT.
Do not synthesize SELL quantity solely to make REDUCE executable.
Keep daily PIT recomputation.
Do not persist reduce debt.
Do not introduce count-based EXIT escalation.
Do not couple BUY and SELL.
Do not weaken explicit EXIT, mandatory SELL, Safety, or no-oversell guards.
Separate runtime behavior from observability.
```

## Candidate Option A - Current Floor-to-Zero + Explicit Semantics

Contract:

```text
PM REDUCE valid
intensity valid
partial executable quantity = 0
semantic outcome = REDUCE_UNEXECUTABLE_DUE_TO_DISCRETE_LOT or REDUCE_UNEXECUTABLE_DUE_TO_MINIMUM_NOTIONAL
runtime action = NO_SELL_ORDER
position effect = unchanged
next day = fresh PM reevaluation
```

Benefits:

```text
minimal behavioral change
no oversell
no forced EXIT
no persistent state
low resume/idempotency risk
compatible with current Long-Horizon run
focused regression surface
```

Limitations:

```text
does not reduce risk on the day of a lot-zero REDUCE
requires explicit observability so repeated REDUCE pressure is not invisible
```

Assessment:

```text
Preferred
```

## Candidate Option B - Minimum-Lot Ceil

Contract:

```text
raw 25 -> SELL 100
```

Reject for Phase29.

Reason:

```text
For one-lot positions, LIGHT/MEDIUM/STRONG REDUCE becomes full EXIT.
For 200-share LIGHT REDUCE, requested 25% becomes 50%.
This violates D25/D34 REDUCE != EXIT semantics and creates winner premature EXIT risk.
```

## Candidate Option C - Strategy Semantic Reclassification

Contract:

```text
REDUCE + partial impossible -> same-day Strategy reclassifies as HOLD or EXIT
```

This is conceptually strong, but not Phase29-minimal. It needs a reliable decision-time distinction between healthy pullback, deterioration, and breakdown. That authority is not currently proven as a separate production-common contract.

Assessment:

```text
Phase30 research candidate; not AC implementation scope.
```

## Candidate Option D - Persistent Reduce Debt

Contract:

```text
accumulate 25 + 25 + 25 + 25 -> SELL 100
```

Reject for Phase29.

Reason:

```text
stale intent risk
temporal authority complexity
resume/replay/idempotency risk
double-counting risk
forced sell against fresh PM evidence
new persistent lifecycle required
```

## Preferred Minimal-Change Design

Adopt Option A as the Phase29 implementation target.

Preferred semantic contract:

```text
Strategy Intent:          REDUCE
Target Exposure Reduction: LIGHT / MEDIUM / STRONG ratio
Continuous Target:        raw_reduce_quantity
Discrete Executability:   PASS / UNEXECUTABLE_BELOW_ONE_LOT / UNEXECUTABLE_MINIMUM_NOTIONAL / REVIEW_REQUIRED
Runtime Action:           SELL_REDUCE when executable, NO_SELL_ORDER when intentional zero
Position Effect:          reduced when executable, unchanged when intentional zero
Follow-up:                next daily PM reevaluation
```

Recommended names:

```text
REDUCE_UNEXECUTABLE_DUE_TO_DISCRETE_LOT
REDUCE_UNEXECUTABLE_DUE_TO_MINIMUM_NOTIONAL
```

The implementation should materialize these as semantic evidence and reason codes. It should not change quantity rounding behavior in Phase29.

## PM Responsibility

PM owns:

```text
HOLD / ADD / REDUCE / EXIT intent
REDUCE intensity
position-level risk / trend interpretation
decision-time evidence
```

PM should not own:

```text
broker mechanics
Pending mechanics
Submit mechanics
Execution mechanics
```

AC does not recommend fully lot-aware PM in Phase29. PM may remain abstract while Position Sizing / Sell Planning return formal feasibility semantics.

## Position Sizing Responsibility

Position Sizing owns:

```text
current quantity
tradable unit
minimum executable quantity
minimum notional
continuous-to-discrete quantity materialization
approximation evidence
zero reason separation
```

Position Sizing must not own:

```text
REDUCE -> EXIT action conversion
```

Minimal implementation likely belongs primarily here.

## Sell Planning Responsibility

Sell Planning owns:

```text
authoritative SELL quantity contract
no oversell
sellable quantity / restricted quantity
quantity contract evidence
```

Sell Planning already has `REDUCE_BELOW_MINIMUM_TRADABLE_QUANTITY`; the next implementation should align Position Sizing / Runtime Planning observability with this sharper contract instead of inventing conflicting SELL behavior.

## Lifecycle / Observability Contract

Intentional no-sell evidence should include:

```text
source_pm_decision_id
source_decision = REDUCE
reduce_intensity
target_reduce_ratio
position_quantity_before
tradable_unit
raw_reduce_quantity
rounded_reduce_quantity
final_sell_quantity = 0
executability_status
zero_reason
runtime_action = NO_SELL_ORDER
pending_order_generated = false
position_effect = UNCHANGED
followup = NEXT_DAILY_PM_REEVALUATION
```

Lifecycle checker should treat this as:

```text
EXPECTED_NO_ORDER_REDUCE_UNEXECUTABLE
```

not as:

```text
missing materialization
stale pending
submit failure
execution failure
```

## EXIT / Mandatory SELL Preservation

Explicit EXIT remains unchanged:

```text
PM EXIT / explicit higher-priority liquidation authority -> SELL_EXIT
```

Mandatory SELL / Safety EXIT must not be blocked by REDUCE lot-zero semantics.

REDUCE feasibility and EXIT feasibility are separate contracts.

## Repeated-Zero Semantics

Repeated REDUCE zero should remain stateless:

```text
Day N: fresh PM REDUCE -> intentional no-sell semantic
Day N+1: fresh PM evidence -> fresh PM decision
```

No count-based escalation:

```text
3 consecutive lot-zero REDUCE -> EXIT
```

Observability may count repeated pressure for reports, but it must not become a production Strategy input without a later approved contract.

## Pullback vs Breakdown Future Extension Boundary

AC does not implement Pullback / Breakdown.

Phase30 candidate:

```text
Pullback vs Breakdown Separability Audit
```

Research question:

```text
Can PIT-safe J-Quants evidence available at PM decision time separate Healthy Pullback from True Breakdown?
```

Possible future outputs:

```text
STRONG_CONTINUATION
HEALTHY_PULLBACK
DETERIORATING
BREAKDOWN
continuation confidence
breakdown confidence
```

This future component is not a prerequisite for the Phase29 minimal semantic contract.

## Complexity Assessment

Option A:

```text
new persistent state required: NO
new schema required: MINIMAL_EXTENSION_ONLY
new lifecycle required: NO
PM modification required: NO
Position Sizing modification required: YES
Sell Planning modification required: NO or MINIMAL_ALIGNMENT_ONLY
Pending modification required: NO
Submit modification required: NO
Execution modification required: NO
Lifecycle checker modification required: YES
Observability modification required: YES
```

Option B:

```text
complexity low, semantic risk high, rejected
```

Option C:

```text
semantic potential high, complexity high, defer to Phase30
```

Option D:

```text
complexity and temporal risk high, rejected for Phase29
```

## Regression Risk Assessment

Winner retention regression:

```text
Option A LOW because it does not force EXIT. Option B HIGH.
```

Loser under-reduction risk:

```text
Option A EXISTING/KNOWN because lot-zero still does not reduce exposure. Must be visible, not hidden.
```

Turnover regression:

```text
Option A LOW. Option B HIGH.
```

Re-entry regression:

```text
Option A LOW. Option B HIGH due to premature EXIT.
```

SELL lifecycle regression:

```text
Option A LOW if non-zero REDUCE and EXIT paths are left unchanged.
```

Runtime regression:

```text
Option A LOW because no Pending / Submit / Execution mutation is required.
```

Strategy authority regression:

```text
Option A LOW if Position Sizing records feasibility but does not overwrite PM intent.
```

## Long-Horizon Compatibility

The preferred Phase29 implementation is behavior-preserving for orders:

```text
no new SELL quantity
no new Pending
no Submit / Execution change
no persistent reduce debt
```

Therefore direct resume compatibility risk is low.

Validation implication:

```text
If implemented mid-run, final performance evidence should distinguish pre-patch observability from post-patch observability.
Because order behavior is unchanged, performance comparability impact should be low, but evidence labels differ.
```

Existing materialized historical evidence should not be rewritten. New evidence should apply prospectively after patch.

## Implementation Scope If Approved

Approved minimal next scope:

```text
1. Split Position Sizing REDUCE zero reasons:
   - below one tradable lot
   - below minimum notional
   - unresolved authority

2. Materialize REDUCE intentional-zero semantic evidence:
   - REDUCE_UNEXECUTABLE_DUE_TO_DISCRETE_LOT
   - REDUCE_UNEXECUTABLE_DUE_TO_MINIMUM_NOTIONAL

3. Preserve current order behavior:
   - final sell quantity remains 0 for intentional zero
   - no forced EXIT
   - no min-lot ceil

4. Teach lifecycle / summarize observability that intentional zero is expected no-order.
```

Out of scope:

```text
PM ratio tuning
PM threshold tuning
REDUCE -> EXIT conversion
Pullback / Breakdown component
persistent reduce debt
BUY sizing changes
initial position sizing changes
performance tuning
```

## Required Regression Matrix If Implemented

Minimum regression design:

```text
Existing executable REDUCE:
  quantity >= 1 lot -> SELL_REDUCE unchanged.

Lot-zero LIGHT REDUCE:
  100 shares * 25% -> no forced EXIT, explicit no-sell semantic.

Lot-zero MEDIUM REDUCE:
  100 shares * 33% -> no silent full EXIT.

Lot-zero STRONG REDUCE:
  100 shares * 50% -> no automatic EXIT without explicit EXIT authority.

Multi-lot floor:
  500 shares * 25% -> floor to 100 remains executable.

Minimum-notional zero:
  rounded lot exists but notional < policy -> separate semantic from lot-zero.

Explicit EXIT:
  100 shares -> SELL_EXIT unchanged.

Mandatory SELL / Safety EXIT:
  unchanged and not blocked by REDUCE semantic.

BUY blocked + SELL:
  SELL independent from BUY review/block.

Pending:
  intentional zero creates no stale Pending.

Resume:
  same-day and next-day idempotency unchanged.

Duplicate execution:
  no duplicate SELL.

Observability:
  intentional zero vs missing materialization distinguishable.

Lifecycle checker:
  expected zero is not false unresolved.
```

67310 fixture:

```text
position = 100
tradable unit = 100
PM = LIGHT REDUCE
target ratio = 0.25
raw = 25
rounded = 0
semantic = REDUCE_UNEXECUTABLE_DUE_TO_DISCRETE_LOT
SELL order = NO
Pending defect = NO
next-day fresh PM reevaluation = YES
future price outcome not used
```

## Phase29 vs Phase30 Gate

Gate criteria assessment:

```text
Production-common semantic gap closable with minimal change: YES
REDUCE -> EXIT automatic conversion required: NO
Existing EXIT semantics preserved: YES
Mandatory SELL preserved: YES
Safety preserved: YES
BUY/SELL independence preserved: YES
Persistent state required: NO
Pending semantics broad change required: NO
Resume/idempotency risk: LOW
Focused regression possible: YES
```

Decision:

```text
IMPLEMENT_IN_PHASE29
```

Rationale:

```text
The approved implementation can close the AB semantic / observability gap without changing actual SELL behavior. Deferring all work to Phase30 would leave known Production-common ambiguity in Phase29 runtime evidence, while Phase29 can safely materialize intentional no-order semantics now.
```

## Final Recommendation

Recommended next task:

```text
Phase29-L21T-AD - REDUCE Intentional No-Order Semantic Materialization Repair
```

AD should implement only the AC-approved minimal contract. It must start by confirming `Phase29-L21T-AD` is unused.

## No-Change Confirmation

```text
Runtime code changed: NO
Strategy code changed: NO
Config changed: NO
Schema changed: NO
Runtime state mutated: NO
Target run mutated: NO
Fresh-run executed: NO
Resume / replay / recovery executed: NO
Long-running test executed: NO
Phase30 entered: NO
```

Required final fields:

```text
Root Cause inherited from AB: E_MULTI_CAUSAL / C_STRATEGY_TO_EXECUTION_SEMANTIC_GAP + B_OBSERVABILITY_GAP
Preferred semantic contract: REDUCE_UNEXECUTABLE_DUE_TO_DISCRETE_LOT / REDUCE_UNEXECUTABLE_DUE_TO_MINIMUM_NOTIONAL
REDUCE -> EXIT automatic escalation allowed: NO
One-lot REDUCE semantic: intentional no-sell, next-day fresh PM reevaluation
Small-lot REDUCE semantic: no ceil unless executable floor produces non-zero allowed quantity
Lot-zero semantic: REDUCE_UNEXECUTABLE_DUE_TO_DISCRETE_LOT
Minimum-notional-zero semantic: REDUCE_UNEXECUTABLE_DUE_TO_MINIMUM_NOTIONAL
Repeated-zero semantic: stateless daily recomputation, observable pressure only
Persistent reduce debt required: NO
New persistent lifecycle required: NO
New schema required: MINIMAL_EXTENSION_ONLY
PM modification required if implemented: NO
Position Sizing modification required if implemented: YES
Sell Planning modification required if implemented: NO / MINIMAL_ALIGNMENT_ONLY
Pending modification required if implemented: NO
Submit modification required if implemented: NO
Execution modification required if implemented: NO
Lifecycle checker modification required if implemented: YES
Observability modification required if implemented: YES
Existing EXIT semantics preserved: YES
Mandatory SELL preserved: YES
BUY / SELL independence preserved: YES
Production fail-closed preserved: YES
Resume / idempotency risk: LOW
Winner premature EXIT risk: LOW under Option A
Loser under-reduction risk: EXISTING_KNOWN_NOT_WORSENED
Complexity assessment: LOW / MINIMAL
Long-Horizon compatibility: LOW_RISK_PROSPECTIVE_OBSERVABILITY_CHANGE
Implementation Gate: IMPLEMENT_IN_PHASE29
Recommended next Task: Phase29-L21T-AD
```
