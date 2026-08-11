# Phase29-D Lot-First Capital Recycling and Concentration Policy Repair Design

Status:

```text
COMPLETE
PRODUCTION-COMMON ARCHITECTURE REPAIR DESIGN
NO IMPLEMENTATION
```

Primary Judgment:

```text
PHASE29_D_LOT_FIRST_CAPITAL_RECYCLING_REPAIR_DESIGN_COMPLETE_PHASE29_E_READY
```

## 1. Scope

Phase29-D is design-only. No production code, strategy code, runtime code,
configuration, threshold, concentration cap, model, schema, Accepted Generation,
Pending, Runtime artifact, test fixture, fresh run, resume, historical run, or
100BD execution was changed or run.

Design evidence:

```text
reports/phase29_d_lot_first_capital_recycling_and_concentration_policy_repair_design/architecture_decision.json
reports/phase29_d_lot_first_capital_recycling_and_concentration_policy_repair_design/invariant_matrix.json
reports/phase29_d_lot_first_capital_recycling_and_concentration_policy_repair_design/regression_contract.json
reports/phase29_d_lot_first_capital_recycling_and_concentration_policy_repair_design/risk_register.json
reports/phase29_d_lot_first_capital_recycling_and_concentration_policy_repair_design/schema_config_impact.json
```

## 2. Phase29-C Basis

Phase29-C confirmed a multi-causal bottleneck:

```text
continuous target-weight allocation + roughly 1M JPY capital
+ Japanese 100-share lots + minimum executable notional + 0.18 cap
=> many positive allocation intents become zero at lot-aware conversion.
```

Observed post-D61 funnel:

| Action | PC positive request | PC positive accept | Lot positive accept | Lot zero after positive accept |
|---|---:|---:|---:|---:|
| ADD | 68 | 60 | 4 | 56 |
| BUY_NEW | 155 | 102 | 29 | 73 |

Capital recycling was `PARTIAL`: 78/100 days had lot skips, but only 11 total
lot promotions occurred, and 96/100 days retained unused deployable capital
after lot-aware conversion.

## 3. Current Architecture

Current chain:

```text
Opportunity / PM
-> D55-A ADD investment evidence
-> Portfolio Construction continuous request
-> Opportunity Competition / incremental budget reconciliation
-> accepted weight
-> Position Sizing lot feasibility preflight
-> Portfolio Construction lot-aware final reallocation
-> Position Sizing final quantity
-> Runtime Position Plan
-> Pending
-> Submit
-> Fill
```

Current authority map:

| Topic | Current authority |
|---|---|
| Capital Pool | Dynamic Cash Exposure target gross exposure, target cash, current cash/exposure, and pending reservation feed PC deployment capacity. |
| Target Cash | Dynamic Cash Exposure, using Market Context, Portfolio Policy, opportunity capacity, uncertainty, pending reservation, and Safety cash limits. |
| ADD/BUY_NEW Competition | Portfolio Construction incremental budget reconciliation over ADD_INCREMENT and BUY_NEW participants. |
| Lot Feasibility | Position Sizing preflight after PC draft and before PC final. |
| Concentration Headroom | PC final lot-aware reallocation uses single-name cap; PS has hard cap revalidation. |
| Skipped Allocation | Skipped capital remains as `remaining_cash_weight` / residual cash. |
| Second Pass | Existing lot-aware pass can skip high-priority infeasible candidates and fund lower-ranked feasible ones once, but it is not full rebatch recycling. |
| Pending/Submit Boundary | Runtime Planning and Pending remain the only route to pending/submit. PC must not generate Pending directly. |

## 4. Recommended Architecture

Recommended:

```text
Design B - Lot-First Feasibility-Aware Rebatch
```

Use the existing two-pass shape, but make lot feasibility and concentration
headroom first-class inputs to capital competition. Continuous weights remain
useful as preference and desired exposure signals, but they must not become final
capital reservation authority when they cannot be expressed as executable lots.

Proposed chain:

```text
Opportunity / PM / D55-A
-> PC draft desired allocation and common ADD/BUY_NEW candidate set
-> PS-derived lot feasibility facts
-> feasibility classification
-> common lot-first capital competition
-> recycle skipped deployable capital
-> deterministic rebatch over remaining executable candidates
-> residual cash reason materialization
-> PC final target weights
-> PS final quantity
-> Runtime Position Plan
-> Pending
-> Submit
-> Fill
```

Feasibility classifications:

| Class | Meaning |
|---|---|
| EXECUTABLE_NOW | One lot or more is executable under current capital, lot, cap, safety, broker, and target-cash constraints. |
| EXECUTABLE_IF_RECYCLED | First-pass allocation is too small, but pooled unused deployable capital could fund at least one lot. |
| CONCENTRATION_BLOCKED | One lot would exceed the current single-name cap/headroom. |
| CAPITAL_BLOCKED | One lot cannot fit within deployable capital after target cash, pending reservation, and prior allocations. |
| BROKER_OR_SAFETY_BLOCKED | Broker, Safety, Corporate Action, or eligibility blocks the symbol. |
| UNKNOWN_FAIL_CLOSED | Required authority is missing or unresolved. |

## 5. Option Comparison

| Option | Summary | Pros | Cons | Judgment |
|---|---|---|---|---|
| A Existing-order second pass | Keep existing ordering and recycle once more. | Smallest change, low immediate regression risk. | Does not explain or solve 96/100 residual-capital days well. | Not recommended. |
| B Feasibility-aware rebatch | Rebuild competition from executable/conditionally executable candidates. | Directly addresses lot/cap mismatch, deterministic, explainable, lower risk than optimizer. | Moderate PC semantic change and new evidence/test burden. | Recommended. |
| C Portfolio-level discrete optimizer | Optimize full lot combinations globally. | Highest theoretical capital efficiency. | High complexity, lower explainability, high regression risk, likely over-designed. | Not recommended. |

## 6. Required Design Decision Table

| Decision | Options | Recommended | Reason | Regression Risk |
|---|---|---|---|---|
| Lot feasibility timing | pre-PC / in-PC / post-PC | in-PC using PS-derived preflight after draft and before final allocation | Lot facts must inform allocation without making PS the economic authority. | MEDIUM |
| Capital recycling | none / second-pass / rebatch | feasibility-aware rebatch | Current second-pass behavior left residual deployable capital on 96/100 days. | MEDIUM |
| ADD/BUY_NEW competition | separate / common | common | Fixed side priority violates DGI-5; both consume incremental capital. | MEDIUM |
| Continuous weight role | authority / preference / remove | preference | Still useful for desired exposure and ranking, unsafe as final reservation authority. | LOW_MEDIUM |
| Concentration cap | preserve / change later | preserve in Phase29-E; Gate B later | Phase29-B already showed worse concentration and drawdown. | LOW |
| Residual Cash authority | implicit / explicit reason | explicit reason taxonomy | Cash retention must be explainable for Phase29-E attribution. | LOW |
| Migration | direct / shadow comparison | direct focused producer change with optional side-by-side evidence in tests | Schema is additive-friendly; behavior still needs guardrails. | MEDIUM |

## 7. Capital Recycling Contract

Recycling input:

```text
unused_deployable_capital
skipped candidate and skip reason
remaining eligible opportunities
current portfolio state
pending reserved cash/exposure
target cash reserve
single-name concentration headroom
lot feasibility rows
deterministic ordering keys
```

Recycling eligibility:

| Skip reason | Recycle source capital? | Candidate can be reconsidered? |
|---|---|---|
| sub-lot / minimum executable notional | YES | YES only if recycled pool can fund one lot and all gates pass. |
| concentration blocked | YES | NO for same symbol unless policy/headroom changes; recycle to other candidates or cash. |
| capital blocked | YES | YES if later rebatch order/pool changes make it executable. |
| competition loss | YES | YES through common rebatch if still eligible. |
| broker blocked | YES | NO for same symbol. |
| safety/corporate action blocked | YES | NO for same symbol. |
| unknown authority | YES to cash or other PASS candidates | NO for unknown symbol. |

Recycling destination:

```text
next eligible BUY_NEW
next eligible ADD
additional lot for an already selected feasible candidate
explicit residual cash
```

ADD and BUY_NEW must compete in a common deterministic queue. No fixed
"existing first" or "new first" rule is allowed.

Termination:

```text
no executable candidate remains
remaining deployable capital < next minimum executable lot
target cash reserve would be breached
all remaining candidates are blocked or exhausted
max_recycle_passes reached
no allocation state changed in the pass
```

Capital conservation invariant:

```text
allocated_buy_notional
+ pending_reserved_buy_cash
+ residual_cash
+ target_cash_reserve
= authoritative_available_capital
within configured rounding tolerance
```

Planned SELL proceeds are excluded until actual execution/fill authority exists.

## 8. Determinism

Rebatch ordering must be deterministic:

```text
1. producer_result_status / eligibility PASS before REVIEW/BLOCK
2. opportunity / incremental value priority
3. D55-A ADD investment evidence for ADD rows
4. runtime_opportunity_score or existing construction priority
5. lower minimum executable weight only as a tie-break, not as alpha
6. security_code
7. source row id / stable hash
```

Floating-point weights must be normalized using existing target-weight precision
and converted to notional/quantity only through the existing PS lot functions.
No random allocation is allowed.

## 9. Residual Cash Reason Contract

Residual cash must be materialized explicitly. Initial taxonomy:

```text
TARGET_CASH_RESERVE
NO_ELIGIBLE_OPPORTUNITY
NO_LOT_FEASIBLE_OPPORTUNITY
CONCENTRATION_LIMIT
SAFETY_LIMIT
BROKER_LIMIT
MARKET_CONTEXT_DEFENSIVE
MINIMUM_EXECUTABLE_NOTIONAL
CAPITAL_BELOW_NEXT_LOT
COMPETITION_EXHAUSTED
UNKNOWN_FAIL_CLOSED
```

Day-level evidence should expose:

```text
starting deployable capital
total requested capital
first-pass allocated capital
skipped capital
recycled capital
final allocated capital
intentionally retained cash
unexplained residual cash
```

Per-opportunity evidence should expose:

```text
requested allocation
requested notional
minimum executable notional
lot size
lot feasibility status
concentration headroom
first-pass result
skip reason
recycled capital amount
rebatch result
final executable quantity
residual cash reason
```

## 10. Concentration Gate

Phase29-E must not change the 0.18 strategy single-name cap.

Gate A:

```text
Recycling-only repair with 0.18 preserved.
Measure how much capital efficiency improves from lot-first rebatch alone.
```

Gate B:

```text
Separate concentration policy review only if Gate A shows many high-quality,
otherwise executable opportunities remain structurally blocked by 0.18.
```

Why not simply raise 0.18:

```text
Phase29-B showed max drawdown worsened from -8.46% to -12.25%.
Average largest position weight rose from 17.39% to 18.37%.
Max largest position weight rose from 20.73% to 24.23%.
Average top3 concentration rose from 44.62% to 46.20%.
```

Capital deployment shortage and concentration risk must be solved together.
Return improvement alone must not justify cap expansion.

## 11. Preservation Contracts

| Contract | Design preservation |
|---|---|
| D61 | PM ADD remains current-baseline incremental request. Do not reintroduce `base_target - current_weight` collision. |
| D69 | `target_weight_change` remains signed observability; executable ADD authority stays positive-only. |
| ADD not forced | D55-A PASS plus opportunity, cap, cash, lot, broker, and safety gates are still required. |
| BUY_NEW not forced | Low opportunity or infeasible candidates can be skipped and cash retained. |
| No forced cash deployment | Target cash, risk-off, opportunity shortage, and genuine infeasibility can retain cash. |
| No fixed position count | Do not re-authorize `max_positions=5` or any fixed performance target count. |
| Market Context | Risk-off target cash is not broken by recycling. |
| Fail-closed | UNKNOWN/REVIEW_REQUIRED/BLOCK cannot be upgraded because cash remains. |
| Production-common | Same strategy contract for production, demo, and historical. |

## 12. SELL / Pending / Safety Non-Regression

SELL / REDUCE / EXIT:

```text
NO DESIGN IMPACT
```

The repair target is BUY-side capital allocation and lot conversion only.
SELL Planning quantity authority, REDUCE quantity contract, EXIT full-sell
contract, active SELL pending reconciliation, and sell quantity broker guards
must not change.

Pending / Submit / Execution:

```text
Recycling result must become a normal Runtime Position Plan and then pass
Pending, Approval, Submit Guard, broker eligibility, and Execution authority.
Portfolio Construction must never write Pending directly.
```

Safety:

```text
Corporate Action blocked, broker ineligible, Safety blocked, Safety unknown,
and future/PIT invalid symbols are not restored by recycling.
```

## 13. Schema And Config Impact

Phase29-D:

```text
Schema change = NO
Config change = NO
```

Phase29-E expected schema impact:

| Artifact | Impact |
|---|---|
| Portfolio Construction | Additive optional fields for lot-first recycling evidence, residual cash reason, and per-member rebatch result. |
| Position Sizing | Additive optional preflight fields: concentration headroom, one-lot post-trade weight, feasibility classification. |
| Runtime Planning | No required change if final PS quantities remain the source; optional lineage fields only. |
| Pending / Submit / Execution | No expected schema change; do not bypass existing contracts. |

Phase29-E expected config impact:

| Type | Candidate fields |
|---|---|
| Architecture config | `lot_first_recycling_enabled`, `max_recycle_passes`, `recycle_candidate_limit`, `residual_cash_reason_required`, `tie_break_policy` |
| Investment policy | No Phase29-E change. `single_name_weight_cap`, target cash policy, and minimum meaningful notional stay separate policy decisions. |

## 14. Risk Register

| Risk | Severity | Trigger | Mitigation / Regression Test |
|---|---|---|---|
| D61 regression | HIGH | ADD increment uses base target instead of current baseline. | current_weight > base target + D55-A PASS positive request test. |
| concentration bypass | HIGH | Recycled capital buys one lot above 0.18. | one-lot just above cap blocked test. |
| forced investment | HIGH | Cash target treated as mandatory deployment floor. | no opportunity and risk-off cash retention tests. |
| ADD favoritism | MEDIUM | Existing positions always prioritized. | common queue test where BUY_NEW beats ADD. |
| BUY_NEW favoritism | MEDIUM | New names always prioritized. | common queue test where ADD beats BUY_NEW. |
| Capital double-use | HIGH | skipped/recycled/pending cash counted twice. | capital conservation invariant test. |
| Pending reserve double-use | HIGH | pending_reserved_cash ignored. | pending reserved cash regression. |
| SELL proceeds premature use | HIGH | planned SELL notional treated as current cash. | SELL proceeds unavailable until fill test. |
| infinite recycle | HIGH | rebatch loop does not terminate. | max passes and no-state-change termination test. |
| non-determinism | MEDIUM | tie order depends on dict/input order. | deterministic tie test. |
| Market Context bypass | HIGH | risk-off target cash ignored. | risk-off target cash preservation test. |
| Safety bypass | HIGH | blocked/unknown symbol re-enters. | safety/broker/corporate action blocked tests. |
| schema consumer breakage | MEDIUM | required field or rename breaks consumers. | additive optional fields and schema validation tests. |
| Production/Historical divergence | HIGH | historical-only branch changes behavior. | shared contract tests across demo/historical fixtures. |

## 15. Phase29-E Acceptance Criteria

Minimum acceptance:

```text
AC-1 D61 target/current collision does not return.
AC-2 D69 signed delta semantics are preserved.
AC-3 Lot-skip capital can recycle to next eligible executable opportunity.
AC-4 No forced deployment when no eligible opportunity exists.
AC-5 0.18 concentration cap is preserved and not bypassed.
AC-6 Safety/broker/corporate action unknown or blocked remains fail-closed.
AC-7 Capital conservation holds.
AC-8 Same input produces same allocation.
AC-9 ADD and BUY_NEW compete in one common queue.
AC-10 SELL/REDUCE/EXIT unaffected.
AC-11 Deprecated max_positions=5 and legacy max_exposure are not re-authorized.
AC-12 Production-common, no historical-only branch.
```

Short regression matrix:

```text
Existing:
Phase28 D55-A, D61, D63, D69, D70B, Portfolio Construction,
Position Sizing, Runtime Position Planning, Sell Planning, Submit Safety,
NO_ORDER_AUTHORIZED / EMPTY terminal, REDUCE quantity, EXIT quantity.

New focused:
lot skip -> next BUY_NEW
lot skip -> next ADD
ADD skip -> BUY_NEW recycle
BUY_NEW skip -> ADD recycle
multiple lot skips
all candidates infeasible
no opportunity
risk-off
concentration blocked
pending reserved cash
broker blocked
corporate action blocked
exact one-lot feasible
one-lot just above cap
residual capital below minimum lot
deterministic tie
capital conservation invariant
residual cash reason taxonomy
```

Long historical validation remains user-operated after Phase29-E implementation
and short regression pass. Codex should provide the command, not run it.

## 16. Future Effect Attribution

After Phase29-E implementation and user-operated historical validation, compare:

```text
Capital Deployment:
average/median cash ratio, average/median exposure, days exposure >= 80%,
days exposure >= 90%, unused deployable capital, residual cash reason distribution.

ADD and BUY_NEW:
PC positive, lot positive, PS positive, Runtime plan, Fill, notional.

Risk:
max drawdown, largest weight, top2/top3 concentration.

Behavior:
average/min/max position count.
```

Return alone must not decide acceptance.

## 17. Recommended Next Task

```text
Phase29-E Lot-First Capital Recycling Implementation with Regression Guardrails
```

