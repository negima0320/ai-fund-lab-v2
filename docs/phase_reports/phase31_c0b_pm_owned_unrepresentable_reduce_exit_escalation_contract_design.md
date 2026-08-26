# Phase31-C0B — PM-owned Unrepresentable REDUCE -> EXIT Escalation Contract Design

Status: COMPLETE
Task type: DESIGN ONLY

## PRIMARY_JUDGMENT

```text
PHASE31_C0B_PM_OWNED_LOT_AWARE_REDUCE_EXIT_ESCALATION_CONTRACT_DESIGNED
```

The canonical REDUCE contract should be refined, not discarded.

`REDUCE` should remain the continuous Strategy intent to reduce exposure while preserving campaign optionality when partial de-risk is executable or semantically appropriate. However, when the desired partial reduction is materially unrepresentable at the discrete lot boundary, PM must be allowed to choose the executable Strategy representation:

```text
preserve position
or
EXIT
```

That decision must be made only by Strategy / Position Management. PS, PC, Runtime Planning, Sell Planning, Pending, Submit, and lot rounding may expose unrepresentability evidence, but must not transform `REDUCE` into `EXIT`.

Preferred alternative:

```text
Alternative G — Hybrid
```

Hybrid means:

1. Pre-PM lot-aware action resolution is the primary architecture.
2. Immediate PM-owned EXIT escalation is allowed for strong/high-confidence unrepresentable de-risk cases with current PIT deterioration confirmation.
3. Persistent PM-owned EXIT escalation is allowed for lighter unrepresentable REDUCE pressure when fresh PM reevaluations repeatedly confirm deterioration and recovery is absent.

No implementation is authorized by this design.

## CURRENT_PROBLEM

The existing contract is safe but incomplete for one-lot positions.

For a 100-share position with a 100-share tradable unit:

```text
PM LIGHT REDUCE = 25%
desired reduction = 25 shares
rounded executable quantity = 0 shares
actual reduction = 0%
```

The system currently preserves this as:

```text
REDUCE -> REDUCE_UNEXECUTABLE_DUE_TO_DISCRETE_LOT -> NO_ORDER
```

This is correct under the Phase29 / Phase30 lot-safety contract. It avoids overselling, avoids hidden reduce debt, and avoids downstream authority drift.

The missing semantic is different:

```text
When the only executable choices are keep all shares or sell all shares,
PM needs an explicit authority to decide which executable representation
best matches the current Strategy state.
```

C0A showed this is material:

| Metric | Value |
|---|---:|
| Usable business dates | 86 |
| PM REDUCE rows | 344 |
| Executable REDUCE rows | 0 |
| Lot-zeroed REDUCE rows | 344 |
| Affected symbols / campaigns | 82 |
| Current quantity <= one lot cases | 309 |
| First-zero notional by symbol | 4,878,020 JPY |

The issue is not that PS or Runtime failed to sell. The issue is that Strategy lacks a PM-owned representation authority for unrepresentable de-risk intent.

## Existing Authority Evidence

Current REDUCE quantity contract:

- PM owns `HOLD / ADD / REDUCE / EXIT`.
- PM may emit REDUCE intent and `reduce_intensity`.
- Sell Planning owns broker-final REDUCE quantity calculation.
- Default tradable unit is 100 shares.
- Rounding is floor-to-tradable-unit.
- `REDUCE` must not implicitly escalate into `EXIT`.
- A zeroed REDUCE is not HOLD, not EXIT, and not a 0-share order.
- Fresh PM reevaluation is required on the next business day.

Evidence:

- `docs/02_architecture/position_management_reduce_quantity_contract.md`
- `src/ai_fund_lab_v2/strategy/reduce_intensity_authority.py`
- `src/ai_fund_lab_v2/strategy/position_sizing.py`
- `src/ai_fund_lab_v2/runtime_v2/planning/sell_pipeline.py`

Runtime boundary:

- Runtime does not recalculate Market Context, position sizing, ranking, or `HOLD / ADD / REDUCE / EXIT`.
- Runtime maps upstream Strategy outputs into safe operational state.

Evidence:

- `docs/02_architecture/runtime_architecture_v2.md`

PC / PS / Runtime boundary:

- PM keeps existing-position directional intent authority.
- PC owns target membership and target weight.
- PS owns target quantity and quantity delta.
- Runtime Planning maps quantity delta to Runtime action and must not change PM intent.

Evidence:

- `docs/02_architecture/portfolio_construction_and_position_sizing_contract.md`

Phase31 boundary:

- BUY / SELL independence must remain intact.
- No Historical-only Strategy path.
- No threshold tuning from short evidence.

Evidence:

- `docs/phase_reports/phase30_to_phase31_chatgpt_handoff.md`
- `docs/phase_reports/phase30_final_summary_and_phase31_handoff.md`
- `docs/01_requirements/phase_roadmap.md`

## Contract Refinement

CURRENT_REDUCE_SEMANTIC_CHANGED:

```text
REFINED
```

The design should distinguish:

```text
REDUCE_INTENT
REDUCE_EXECUTABLE_REPRESENTATION
```

REDUCE_INTENT:

```text
PM wants less exposure while preserving optionality in the continuous Strategy space.
```

REDUCE_EXECUTABLE_REPRESENTATION:

```text
Given current quantity, tradable unit, reduce_intensity, PIT deterioration evidence,
and campaign state, PM decides whether the executable Strategy action should be
preserve-position or EXIT.
```

This refinement does not weaken quantity safety. Lot rounding remains floor-based. Sub-lot partial sells remain forbidden.

LOT_ROUNDING_CHANGED:

```text
NO
```

PS_EXIT_AUTHORITY_ADDED:

```text
NO
```

RUNTIME_EXIT_AUTHORITY_ADDED:

```text
NO
```

## Proposed Authority

Canonical concept:

```text
PM_UNREPRESENTABLE_REDUCE_EXECUTABLE_REPRESENTATION_AUTHORITY
```

Short name:

```text
UNREPRESENTABLE_REDUCE_ESCALATION_AUTHORITY
```

Owner:

```text
Strategy / Position Management
```

Owned decision:

```text
When PM de-risk intent is unrepresentable as a partial executable REDUCE,
choose whether PM emits REDUCE/preserve-position or EXIT.
```

Not owned:

- lot size;
- discrete quantity;
- broker feasibility;
- cash;
- Safety hard caps;
- Submit validity;
- Pending lifecycle;
- BUY ranking;
- Portfolio Construction capital ordering.

Output states should be semantic, not threshold-bound:

```text
REPRESENTABLE_REDUCE
UNREPRESENTABLE_REDUCE_PRESERVE
UNREPRESENTABLE_REDUCE_EXIT_IMMEDIATE
UNREPRESENTABLE_REDUCE_EXIT_PERSISTENT
REVIEW_REQUIRED
```

The final PM action emitted downstream remains one of the existing canonical PM actions:

```text
HOLD / ADD / REDUCE / EXIT
```

No new downstream Runtime action is required.

## Required PIT Inputs

Current PM intent:

- preliminary PM action candidate;
- `reduce_intensity`;
- PM reason codes / dominant cause;
- action confidence / score evidence;
- current campaign state.

Discrete representation evidence:

- current quantity;
- tradable unit;
- target reduce ratio;
- raw reduce quantity;
- rounded reduce quantity;
- actual reduction fraction;
- `REDUCE_UNEXECUTABLE_DUE_TO_DISCRETE_LOT`;
- final sell quantity under REDUCE quantity contract.

Persistence evidence:

- prior PM actions for the same campaign;
- prior unrepresentable REDUCE events for the same campaign;
- consecutive fresh-PM REDUCE count;
- recent-window fresh-PM REDUCE frequency;
- days since first unrepresentable REDUCE;
- recovery interruptions such as HOLD/ADD with restored continuation evidence.

Existing deterioration evidence:

- Expected Edge status / trajectory where canonical;
- PM trend and opportunity deterioration reasons;
- momentum and trend evidence;
- trend decay evidence;
- downside risk state;
- continuation quality state;
- selection / rank deterioration where already canonical;
- canonical Market Context / regime;
- campaign state, campaign age, MFE, giveback, current campaign relative return.

All inputs must be point-in-time. Future price movement, later regime labels, final PnL, and Historical outcome classifications are forbidden as runtime inputs.

NEW_MARKET_FEATURE_REQUIRED:

```text
NO
```

If existing features prove insufficient in validation, the correct result is an evidence-gap finding, not a new C0B predictor.

## Representation Error

The authority should formalize deterministic representation error:

```text
desired_reduction_fraction = target_reduce_ratio
actual_reduction_fraction = final_sell_quantity / current_quantity
reduce_representation_error = desired_reduction_fraction - actual_reduction_fraction
```

Example:

```text
current_quantity = 100
tradable_unit = 100
reduce_intensity = STRONG
desired_reduction_fraction = 0.50
final_sell_quantity = 0
actual_reduction_fraction = 0.00
reduce_representation_error = 0.50
```

This is not a new alpha feature. It is deterministic evidence derived from PM intent plus lot constraints. It is useful because `LIGHT` and `STRONG` unrepresentable REDUCE do not carry the same semantic distortion.

Magnitude alone must not force EXIT.

## Persistence Semantics

PERSISTENCE_USED_AS_STRATEGY_EVIDENCE:

```text
YES
```

Persistence means repeated fresh PM decisions, not accumulated execution debt.

Valid persistence evidence:

```text
Day N   PM fresh decision = REDUCE, REDUCE unrepresentable
Day N+1 PM fresh decision = REDUCE, REDUCE unrepresentable
Day N+k PM fresh decision = REDUCE, REDUCE unrepresentable
```

Invalid persistence model:

```text
25 shares desired today
+25 shares desired tomorrow
+25 shares desired later
= hidden 100-share reduce debt
```

HIDDEN_REDUCE_DEBT_ALLOWED:

```text
NO
```

Persistence is Strategy evidence for a new PM decision. It is never a latent order quantity.

## Recovery Reset

RECOVERY_RESET_DEFINED:

```text
YES
```

The authority should support reset or decay states:

```text
RECOVERY_RESET
RECOVERY_DECAY
NO_RECOVERY
REVIEW_REQUIRED
```

Conceptual behavior:

- `REDUCE -> HOLD` with restored continuation evidence can reset or materially decay escalation pressure.
- `REDUCE -> ADD` with valid ADD evidence is stronger recovery and should reset escalation pressure unless other Safety/PM evidence blocks it.
- `REDUCE -> HOLD` while PIT evidence remains weak should not automatically reset; it should decay only if the hold evidence is substantively healthy.
- `REDUCE -> REDUCE` with no recovery indicates persistent de-risk pressure.

This protects winner recovery cases observed in C0A, including 40800, 27670, 92270, 66330, and 32050.

## Immediate Escalation

IMMEDIATE_ESCALATION_SUPPORTED:

```text
CONDITIONAL
```

Immediate PM-owned escalation may be appropriate when all conceptual conditions are true:

- position is one-lot or otherwise materially unrepresentable;
- preliminary PM intent is REDUCE;
- reduce intensity expresses large desired de-risk distortion, such as `STRONG`;
- existing PIT deterioration evidence already supports full close semantics;
- winner-protection evidence is absent or weak;
- PM can emit `EXIT` directly as its final action.

Example semantic family:

```text
100 shares
STRONG REDUCE candidate
REDUCE final sell quantity would be 0
trend/Expected Edge/downside/continuation evidence indicates severe deterioration
=> PM may emit EXIT immediately
```

No numeric threshold is selected here.

## Persistent Escalation

PERSISTENT_ESCALATION_SUPPORTED:

```text
CONDITIONAL
```

Persistent PM-owned escalation may be appropriate when all conceptual conditions are true:

- REDUCE remains unrepresentable over repeated fresh PM reevaluations;
- current PIT deterioration persists;
- recovery reset has not occurred;
- representation error remains material;
- normal partial REDUCE remains unavailable;
- PM emits a new `EXIT` decision with full explanation.

Example semantic family:

```text
100 shares
LIGHT or MEDIUM REDUCE candidate
multiple fresh PM decisions continue to de-risk
REDUCE remains lot-unrepresentable
continuation / downside / expected-edge evidence remains weak
no meaningful recovery reset
=> PM may emit EXIT
```

This is the family intended to address 61750-like indefinite loops without creating a symbol rule.

## Existing PIT Confirmation

EXISTING_PIT_CONFIRMATION_REQUIRED:

```text
YES
```

Repeated unrepresentable REDUCE alone is not enough. C0A observed 57 campaigns that later recovered to HOLD/ADD after first zeroed REDUCE and 24 winner false-positive cases under an immediate-exit proxy.

The authority must require contemporaneous confirmation from existing Production-visible evidence, such as:

- Expected Edge deterioration or insufficiency;
- continuation weakening or break;
- downside risk increase;
- trend / momentum deterioration;
- profit protection / giveback context where already canonical;
- Market Context as a modifier, not a hard action rule;
- campaign state and recovery evidence.

Potential conceptual states:

```text
HEALTHY_RECOVERY
TEMPORARY_CAUTION
PERSISTENT_DERISK
EXIT_LIKE_DERISK
```

Names may change during implementation design to fit existing SoT. The important semantic is that recovered PIT state blocks stale persistence from forcing EXIT.

## One-Lot Semantics

ONE_LOT_SPECIAL_SEMANTICS:

```text
One-lot positions have a discrete representation problem, not a symbol-specific rule.
```

For one-lot positions:

```text
partial REDUCE may be impossible;
actual executable choices may be preserve all shares or sell all shares;
PM must decide which executable representation fits current Strategy evidence.
```

This does not mean every one-lot REDUCE becomes EXIT. It means one-lot REDUCE requires explicit PM-owned representation handling when partial REDUCE is unrepresentable.

## Multi-Lot Semantics

MULTI_LOT_NORMAL_REDUCE_PRESERVED:

```text
YES
```

If a partial REDUCE can be represented as an executable lot quantity, normal REDUCE must be preserved.

Example:

```text
500 shares
MEDIUM REDUCE
raw reduction ~= 165 shares
rounded executable reduction = 100 shares
=> normal REDUCE, not EXIT
```

Persistence must not escalate an executable partial REDUCE to EXIT merely because past REDUCE pressure existed. The primary scope is materially unrepresentable REDUCE.

## Same-Day vs Next-Day vs Pre-PM Resolution

Alternative 1: Same-day second PM resolution

```text
PM emits REDUCE
PS/Sell Planning returns unrepresentable evidence
PM re-enters and decides HOLD vs EXIT in the same cycle
```

Pros:

- fastest reaction.

Risks:

- circular producer/consumer orchestration;
- duplicate authority appearance;
- harder deterministic audit;
- more risk of Runtime-driven action drift.

Alternative 2: Next-day fresh PM resolution

```text
Day N REDUCE is unrepresentable and preserved as NO_ORDER.
Day N+1 PM consumes prior evidence plus fresh PIT state and may emit EXIT.
```

Pros:

- fits existing fresh reevaluation contract;
- avoids orchestration cycles;
- clean audit story.

Risks:

- one-business-day reaction delay.

Alternative 3: Pre-PM lot-aware action resolution

```text
PM has legitimate current quantity / tradable unit / representability evidence
before final action selection.
PM chooses REDUCE or EXIT directly.
```

Pros:

- cleanest single-authority model;
- supports immediate escalation without downstream transformation;
- easier to explain: PM emitted EXIT, not Runtime converted REDUCE.

Risks:

- requires PM input materialization to include canonical lot-representability evidence;
- must avoid duplicating PS quantity authority;
- must keep lot feasibility as evidence, not PM-owned quantity calculation.

SAME_DAY_OR_NEXT_DAY_RESOLUTION:

```text
HYBRID
```

Recommended architecture:

```text
PRE_PM_LOT_AWARE as primary final-action resolution
NEXT_DAY_FRESH_PM as persistence path
NO same-day downstream re-entry loop
```

This means PM should receive enough PIT current-position and lot-representability evidence to choose its final action before publishing PM output. If unrepresentability is discovered only downstream in an interim implementation, the evidence should be persisted and consumed by the next business day's fresh PM evaluation, not bounced back into same-day Runtime-driven redecision.

## Candidate Alternatives

| Alternative | Summary | Cleanliness | PIT validity | Winner protection | Reaction speed | Complexity | Regression risk | Judgment |
|---|---|---|---|---|---|---|---|---|
| A | Current behavior | High | High | High | Low | Low | Low | Safe but leaves material loss opportunity |
| B | Magnitude-only | Medium | High | Low | High | Low | Medium | Too blunt |
| C | Persistence-only | Medium | High | Medium | Medium | Medium | Medium | Better, but stale pressure can hurt recoveries |
| D | Magnitude + persistence | Medium | High | Medium | Medium | Medium | Medium | Useful but not enough alone |
| E | Persistence + PIT deterioration | High | High | High | Medium | Medium | Low-Medium | Strong candidate |
| F | Lot-aware PM direct action | Very high | High | Conditional | High | Medium | Medium | Cleanest authority shape |
| G | Hybrid F + E, with immediate strong-case support | High | High | High | High where justified | Medium-High | Medium | Preferred |

PREFERRED_ALTERNATIVE:

```text
G
```

Reason:

```text
G best satisfies the user's intent that REDUCE may map to full liquidation at the
executable boundary, while preserving PM single-authority semantics and avoiding
blind exit of recoverable winners.
```

## Required State / Evidence

REQUIRED_STATE / EVIDENCE:

- campaign-scoped PM action history;
- prior unrepresentable REDUCE event history;
- prior event business date and source PM decision id;
- current quantity and current quantity authority;
- tradable unit and source authority;
- target reduce ratio from canonical reduce intensity;
- raw reduce quantity;
- rounded reduce quantity under current floor policy;
- final REDUCE sell quantity;
- desired reduction fraction;
- actual reduction fraction;
- representation error;
- current PM reason codes and dominant cause;
- Expected Edge semantic status where canonical;
- continuation quality evidence;
- downside risk evidence;
- trend / momentum evidence;
- Market Context / regime;
- campaign state, campaign age, MFE/giveback/current return;
- recovery reset / decay evidence;
- PIT proof fields: business date, feature date, source path/hash, future information flags.

Persistence state should live with existing campaign/PM evidence if sufficient. Preferred storage is campaign-scoped Strategy evidence or PM decision trace, not a new standalone execution-debt store. If existing campaign state cannot reliably persist unrepresentable REDUCE events across restarts, C0C should design the smallest canonical campaign-scoped evidence extension.

## Unset Parameters

UNSET_PARAMETERS:

- persistence count required for persistent escalation;
- recent-window length;
- days-since-first-unrepresentable weighting;
- representation-error materiality bands;
- immediate-escalation intensity eligibility;
- deterioration confirmation categories;
- recovery reset strength;
- recovery decay half-life / expiry;
- Market Context modifier role;
- minimum evidence sufficiency rules for Expected Edge trajectory;
- campaign age handling;
- winner-protection block conditions;
- re-entry observation window after escalated EXIT.

Existing canonical reduce intensity values may be consumed:

```text
LIGHT = 0.25
MEDIUM = 0.33
STRONG = 0.50
```

No new production threshold is selected from C0A.

## Overfit Prevention Plan

OVERFIT_PREVENTION_PLAN:

1. Development evidence:
   Use C0A only for mechanism discovery and test-case selection. Do not tune production thresholds from the 86BD window.

2. Validation design:
   Define candidate semantic variants before running a separate chronological validation period.

3. Validation metrics:
   Evaluate avoided loss, winner damage, MDD, campaign contribution, capital release, turnover, holding duration, re-entry impact, SELL fill correctness, BUY/SELL independence, and review/fail-closed counts.

4. Holdout:
   Keep a separate untouched period where feasible. Use it only after parameters are frozen from development + validation reasoning.

5. PIT audit:
   For every escalated EXIT candidate, prove that inputs existed at decision time and no future outcome, later regime, final PnL, or later classification was used.

6. Regression audit:
   Confirm normal executable REDUCE, existing EXIT, BUY_ADD, BUY_NEW, Pending review, Submit, and Current valuation paths are unchanged.

## Required Flags

REDUCE_EXIT_ESCALATION_OWNER:

```text
Strategy / Position Management
```

LOT_ROUNDING_CHANGED:

```text
NO
```

PS_EXIT_AUTHORITY_ADDED:

```text
NO
```

RUNTIME_EXIT_AUTHORITY_ADDED:

```text
NO
```

PERSISTENCE_USED_AS_STRATEGY_EVIDENCE:

```text
YES
```

HIDDEN_REDUCE_DEBT_ALLOWED:

```text
NO
```

BUY_SELL_INDEPENDENCE_PRESERVED:

```text
YES
```

REENTRY_BLANKET_BAN_ADDED:

```text
NO
```

MUTATING_IMPLEMENTATION_AUTHORIZED:

```text
NO
```

## Re-entry

An escalated EXIT closes the current campaign. It must not create a permanent re-entry ban.

If later PIT evidence legitimately recovers, normal Candidate / Opportunity / BUY Quality / Portfolio Construction / PM rules may admit a new BUY under existing re-entry controls. C0B adds no blanket re-entry prohibition.

## Market Context

Market Context may modify confirmation strength, but must not mechanically force EXIT.

Example:

```text
BEAR + persistent unrepresentable REDUCE + weak continuation evidence
```

may support escalation.

But:

```text
BEAR alone
```

does not create mandatory EXIT unless a separate accepted SoT already grants that authority.

## Design Examples

Case 1:

```text
100 shares
LIGHT REDUCE
first occurrence
continuation evidence healthy
=> preserve position / no EXIT
```

Case 2:

```text
100 shares
LIGHT REDUCE
repeated unrepresentable REDUCE
current PIT deterioration confirmed
recovery absent
=> PM may emit EXIT
```

Case 3:

```text
100 shares
STRONG REDUCE
current PIT breakdown strongly confirmed
=> PM may emit EXIT immediately
```

Case 4:

```text
500 shares
MEDIUM REDUCE
100-share executable reduction exists
=> normal REDUCE
```

Case 5:

```text
100 shares
prior unrepresentable REDUCE history
current PIT state recovered strongly
=> do not EXIT solely from stale persistence
```

## 61750 Control

61750 should not remain indefinitely in:

```text
REDUCE -> NO_ORDER -> REDUCE -> NO_ORDER
```

when PM repeatedly emits fresh unrepresentable de-risk intent and current PIT evidence confirms no recovery.

However, C0B does not create:

```text
if symbol == 61750: EXIT
```

61750 is a control case for campaign-scoped persistence and one-lot representation error. It is not a symbol rule and not a threshold source.

## Winner Damage Protection

WINNER_DAMAGE_PROTECTION:

```text
Required.
```

The authority must preserve:

```text
temporary de-risk != full liquidation
```

C0A winner controls show why:

- 40800 recovered after initial pressure;
- 27670 recovered quickly;
- 92270 recovered quickly;
- 66330 recovered after repeated pressure;
- 32050 recovered after repeated pressure.

Therefore the design must allow HOLD/ADD recovery evidence to reset or decay escalation pressure and must require current PIT confirmation before EXIT.

## Production Commonness

Future implementation must be Production-common:

```text
Production = Demo = Historical
```

No Historical-only escalation path is allowed.

## NEXT_TASK_RECOMMENDATION

```text
Phase31-C0C validation design
```

C0C should define the overfit-safe validation protocol, candidate parameter roles, evidence extraction rules, and acceptance metrics for Alternative G. It should still be design/validation-first unless the user explicitly authorizes implementation later.

## Final Questions

### 1. Should REDUCE remain universally "partial sell while always preserving position membership"?

```text
REFINED
```

REDUCE remains partial de-risk intent in continuous Strategy space. It should not universally force membership preservation when partial de-risk is unrepresentable and PM-owned evidence supports full close as the correct executable Strategy representation.

### 2. When partial REDUCE is impossible at the lot boundary, can EXIT be the correct executable Strategy action?

```text
CONDITIONAL
```

Yes, when PM-owned PIT evidence supports full liquidation and winner-protection / recovery evidence does not block escalation.

### 3. Who must decide that?

```text
Strategy / Position Management via PM_UNREPRESENTABLE_REDUCE_EXECUTABLE_REPRESENTATION_AUTHORITY
```

### 4. Should a STRONG unrepresentable REDUCE ever be allowed to become EXIT immediately when existing PIT evidence already confirms severe deterioration?

```text
CONDITIONAL
```

Yes, as a PM-owned pre-PM lot-aware final action decision. It must not be a PS or Runtime conversion.

### 5. Should repeated LIGHT/MEDIUM unrepresentable REDUCE be allowed to escalate to EXIT when deterioration persists and recovery is absent?

```text
CONDITIONAL
```

Yes, as a fresh PM decision using persistence as Strategy evidence plus current PIT deterioration confirmation.

### 6. Should PS or Runtime ever make that REDUCE -> EXIT business decision?

```text
NO
```

PS and Runtime may preserve and expose evidence only.

### 7. Can the design be built from existing Production-visible PIT evidence without a new alpha feature?

```text
YES
```

The design can use PM intent, reduce_intensity, lot representability, campaign state, Strategy Intelligence, Expected Edge semantics, continuation/downside/trend/momentum evidence, and canonical Market Context. Validation may still find evidence gaps, but no new alpha feature is required by the design.

### 8. Is this candidate strong enough to proceed to an overfit-safe validation design?

```text
YES
```

C0A showed material opportunity and material winner-damage risk. That combination is exactly why C0C should validate the Hybrid PM-owned design before any mutation.
