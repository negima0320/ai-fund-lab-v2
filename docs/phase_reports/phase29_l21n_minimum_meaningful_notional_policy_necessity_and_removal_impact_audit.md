# Phase29-L21N — Minimum Meaningful Notional Policy Necessity / Removal Impact Audit

Task ID: `Phase29-L21N`  
Target run: `runtime-test-historical-smoke-20260811T152905733571Z`  
Mode: read-only audit. No implementation, configuration, threshold, model, schema, accepted-generation, runtime, pending, resume, abort, repair, fresh run, or historical-run mutation was performed.

## Executive Summary

`minimum_meaningful_notional` is not an independent Safety hard constraint. It is a Position Sizing execution-expression policy that combines a 50,000 JPY base floor with a buffered round-lot floor:

`max(50,000 JPY, reference_price * tradable_unit * 1.02)`

In the L21M 185 blocked instances, the 2% buffer turns every official minimum policy lot into 2 round lots. That official 2-lot minimum exceeds Safety hard cap in all 185 cases, so the current block is internally correct. However, the policy's independent necessity is not proven for a 1M JPY Japanese-equity portfolio. Existing components already control the core risks: BQ/ranking controls quality, PC controls target membership and competition, Strategy cap controls desired concentration, Safety hard cap controls final concentration, gross exposure/cash controls portfolio budget, and broker lot controls exchange executability.

Counterfactual A, removing only the minimum meaningful notional gate while preserving target allocation and Strategy cap semantics, creates 0 new executable orders. Counterfactual B, replacing the policy with a Safety-aware one-round-lot fallback, creates 38 feasible one-lot cases, including 23 BUY_NEW and 15 BUY_ADD, and deploys about 5.91M JPY more notional across the fixed L21M/L21L baseline. The theoretical PC-stage average gross exposure moves from about 47.87% to 50.33%. This is a mechanics estimate, not a PnL claim.

Primary classification: `POLICY_REQUIRED_BUT_THRESHOLD_OR_EXPRESSION_INAPPROPRIATE` and `POLICY_REPLACEMENT_WITH_LOT_AWARE_FALLBACK_RECOMMENDED`.

## Policy Authority / Origin

Authority chain:

| Item | Evidence |
|---|---|
| Producer | Position Sizing |
| Implementation | `src/ai_fund_lab_v2/strategy/position_sizing.py` |
| Config source | `configs/strategy/position_sizing.json#minimum_meaningful_notional` |
| Current config | `base_jpy=50000`, `tradable_unit=100`, `price_buffer_ratio=0.02`, `policy=max_base_jpy_or_buffered_round_lot_notional` |
| Function | `_minimum_notional(config, price)` |
| Artifact fields | `minimum_meaningful_notional`, `minimum_executable_notional`, `minimum_policy_lots`, `minimum_policy_lot_weight`, `minimum_meaningful_notional_applied_to` |
| Consumers | Position Sizing final quantity, Position Sizing lot preflight, PC lot-aware final reallocation, Runtime Planning no-order mapping |
| Downstream effect | below threshold becomes zero quantity / no order; in preflight it can require 2 policy lots and make a candidate Safety-infeasible |
| Fail semantics | fail closed to zero/no order for BUY transactions; existing baselines are preserved after Phase28-D31 |
| BUY_NEW | applies to total target notional |
| BUY_ADD | applies to incremental transaction notional, not retained baseline |
| Environment difference | no Historical/Demo/Production difference found in the config path |
| Phase origin | Present in Phase22 Position Sizing introduction |

Design rationale found:

- Architecture docs define `minimum_executable_notional_policy` as a Position Sizing input/output contract.
- Phase28-D30/D31 state that the policy should apply to incremental transaction notional, not erase existing baseline holdings.
- Phase29-C/L18 describe it as part of lot feasibility and capital conversion.

No explicit design rationale was found proving that the 50,000 JPY plus 2% buffered round-lot threshold is independently required as a Safety constraint for 1M JPY capital.

`RATIONALE_NOT_FOUND` for an independent 1M-account Safety necessity.

## Current Contract

Current behavior:

- For BUY_NEW, `minimum_meaningful_notional` applies to total target notional.
- For BUY_ADD, it applies to the incremental transaction delta.
- `_minimum_notional` returns the larger of 50,000 JPY and buffered 1 round lot.
- `minimum_policy_lots = ceil(minimum_notional / one_lot_notional)`.
- Because the buffer is 1.02, every round-lot-priced candidate in the L21M blocked set requires 2 policy lots.
- If 2 policy lots exceed Safety hard cap, the lot boundary becomes `MINIMUM_EXECUTABLE_LOT_EXCEEDS_SAFETY_HARD_MAX`.

The policy therefore does more than reject tiny orders. In this run it converts many otherwise Safety-contained 1-lot possibilities into 2-lot Safety breaches.

## Risk Protected by Policy

Likely protected risks:

| Risk | Existing controls already present | Independent need proven? |
|---|---|---|
| Tiny position proliferation | PC competition, DPC/internal capacity, Strategy cap, Safety cap, broker lot | Partial |
| Excessive position count | Portfolio Policy meaningful allocation count, PC membership, no routine fixed Safety max | Partial |
| Portfolio fragmentation | PC target allocation, opportunity competition, residual cash preservation | Partial |
| Transaction cost inefficiency | Not otherwise explicit in current artifacts | Partial |
| Opportunity dilution | BQ, opportunity rank, PC competition | Mostly redundant |
| Target weight fidelity | PC target weights, PS lot rounding evidence | Redundant |
| Concentration control | Strategy 18% cap, Safety 25% hard cap | Redundant |
| Broker lot feasibility | `tradable_unit=100`, lot rounding | Redundant |
| Capital efficiency | DCE/gross/cash, PC residual handling | Not protected; current policy can reduce efficiency |

The policy has a plausible role as a transaction-efficiency guard, but its Safety and concentration roles are redundant with existing authorities.

## Redundancy Analysis

The following controls remain even without the minimum meaningful notional gate:

- Buy Quality and opportunity eligibility decide whether a candidate is worth considering.
- Opportunity ranking and PC competition decide priority.
- PC target allocation decides desired weight.
- Strategy maximum position weight remains 18%.
- Safety hard concentration remains 25%.
- Gross exposure remains bounded at 100%.
- Available cash remains required.
- Broker round lot remains required.
- Position Sizing remains quantity authority.
- Runtime Planning remains order-intent authority.

Thus full policy removal would not remove the important safety rails. It would remove a transaction-size expression rule.

## 1M Portfolio Meaningfulness Analysis

For the 185 L21M blocked instances, one round lot is not economically tiny:

| One-lot resulting weight band | Count |
|---|---:|
| <2% | 0 |
| 2-5% | 0 |
| 5-10% | 0 |
| 10-15% | 0 |
| 15-20% | 12 |
| 20-25% | 28 |
| >25% | 145 |

All 185 one-lot results are at least 10% of portfolio value, and 173 are at least 20%. Calling these "meaningless small positions" is not appropriate. The more accurate risk is the opposite: one round lot is often large relative to 1M JPY capital.

For the 38 Safety/cash/gross feasible fallback cases:

- 11 land in 15-20%.
- 27 land in 20-25%.
- 0 exceed Safety hard cap.

So the feasible set is meaningful, but also concentration-heavy. It needs explicit one-lot risk semantics rather than blind policy removal.

## Removal Counterfactual

Counterfactual A removes only `minimum_meaningful_notional` while preserving:

- BQ and opportunity eligibility.
- Ranking and PC competition.
- Target allocation.
- Strategy soft cap semantics.
- Safety hard cap.
- Cash and gross exposure.
- Broker 100-share lot.
- Position Sizing and Runtime Planning roles.

Result:

| Metric | Value |
|---|---:|
| Newly executable count | 0 |
| Newly executable notional | 0 JPY |
| Safety violation count | 0 |
| Target allocation overshoot count | 0 |
| Position count impact | 0 |
| Average gross exposure impact | 0 |

Conclusion: complete gate removal alone does not solve L21M, because target allocation and Strategy cap still prevent one-lot orders whose 100-share notional exceeds the target/cap expression.

## Lot-Aware Fallback Counterfactual

Counterfactual B permits an execution candidate when target quantity is otherwise zero, but exactly one round lot is available and:

- candidate already passed BQ/PC membership,
- broker lot is valid,
- one lot is within Safety hard cap,
- one lot is within cash,
- one lot is within target gross exposure.

Result:

| Metric | Value |
|---|---:|
| Newly feasible instances | 38 |
| BUY_NEW feasible | 23 |
| BUY_ADD feasible | 15 |
| Newly deployable notional | 5,914,400 JPY |
| Safety violation count | 0 |
| Strategy cap overshoot count | 38 |
| Target allocation overshoot count | 38 |
| New position events | 23 |
| ADD events | 15 |
| Actual PC-stage average gross exposure | 47.87% |
| Theoretical average gross exposure | 50.33% |
| Max concurrent positions | 6 -> 7 |
| Average concurrent positions | 3.19 -> 3.28 |

This is the only counterfactual that materially changes capital deployment.

## Dangerous Overshoot Cases

The fallback set is not free of risk:

- 38 / 38 feasible fallback cases overshoot target allocation.
- 38 / 38 overshoot the 18% Strategy cap.
- 27 / 38 overshoot Strategy cap by more than 2pp.
- 15 / 38 overshoot target by more than 5pp.
- 1 / 38 overshoots target by more than 10pp.
- Maximum target overshoot: about 10.54pp.
- Safety violations: 0.

Representative high-overshoot case:

- `2023-03-22`, symbol `59350`, BUY_NEW, BQ `FULL_ALLOCATION_ELIGIBLE`, rank 4.
- Target weight about 11.11%.
- One-lot resulting weight about 21.65%.
- Target overshoot about 10.54pp.
- Strategy cap overshoot about 3.65pp.
- Safety hard cap remains preserved.

Conclusion: "Safety内なら何でも1lot許可" is too broad. A fallback needs explicit constraints, evidence, and possibly an overshoot band/rank/BQ contract.

## BUY_NEW vs BUY_ADD

BUY_ADD:

- Existing-position baseline already exists.
- L21D/L21F provide a narrow lot-aware Strategy soft-cap overshoot authorization for economically accepted ADD.
- Minimum meaningful notional applies only to incremental transaction notional.

BUY_NEW:

- Creates a new single-name risk.
- Does not have the L21D/L21F authorization contract.
- In the L21N fallback set, 23 BUY_NEW cases become feasible under Safety but all overshoot Strategy/target.

No design document was found proving that BUY_NEW alone must retain the current buffered minimum meaningful notional rule. The distinction that BUY_NEW creates new exposure is valid, but that argues for a BUY_NEW-specific one-lot authorization contract, not necessarily for preserving the current 2-policy-lot expression.

## Position Fragmentation Impact

Counterfactual B does not create tiny fragments in the L21M blocked set:

- One-lot feasible positions are 15-25% positions.
- New BUY_NEW events: 23 across the baseline.
- Same-day max concurrent positions increases from 6 to 7.
- Average concurrent positions increases from 3.19 to 3.28.

DPC / Portfolio Policy no longer imposes a routine fixed max-position Safety cap, so fragmentation is mainly controlled by PC membership, opportunity quality, target allocation, Strategy/Safety concentration, gross exposure, and broker lot. In this evidence set, those controls are sufficient to avoid tiny-position proliferation, but a future fallback should still record position-count impact explicitly.

## Architecture Assessment

Primary:

`POLICY_REQUIRED_BUT_THRESHOLD_OR_EXPRESSION_INAPPROPRIATE`

Secondary:

`POLICY_REPLACEMENT_WITH_LOT_AWARE_FALLBACK_RECOMMENDED`

Also applicable:

- `POLICY_INCOMPATIBLE_WITH_1M_JP_EQUITY_LOT_DISCRETIZATION` for the buffered 2-policy-lot expression.
- `POLICY_REDUNDANT_WITH_EXISTING_ARCHITECTURE` for Safety/concentration/broker-lot roles.

Not supported:

- `POLICY_REQUIRED_AND_CORRECT`
- `POLICY_REMOVAL_UNSAFE` as a blanket claim

The policy has a reasonable transaction-efficiency role, but its current expression blocks Safety-contained one-lot opportunities and does not fit the 1M JPY / 100-share Japanese equity setting well.

## Regression Assessment

Regression is not confirmed.

The policy exists from Phase22 Position Sizing introduction. No evidence was found that a prior production implementation lacked this policy or had a working BUY_NEW one-lot fallback that was later removed. The issue is an architecture / policy design gap exposed by long-horizon capital deployment validation.

## Recommended Next Task

Recommended next task:

`Phase29-L21O — BUY_NEW Safety-Aware One-Lot Fallback Design`

Recommended direction:

- Do not fully remove all minimum meaningful notional semantics.
- Replace the current BUY_NEW/BY_ADD blocked expression with a narrow lot-aware fallback design.
- Preserve BQ, opportunity ranking, PC competition, broker lot, cash, gross exposure, and Safety hard cap.
- For BUY_NEW, require explicit new-entry risk semantics, target/Strategy overshoot evidence, and fail-closed validation.
- For BUY_ADD, align with the existing L21D/L21F authorization contract.
- Improve observability so "minimum meaningful notional", "round lot", "Strategy cap", and "Safety hard cap" are separate reasons.

## Primary Judgment

Required final answers:

1. What is the policy for? It is a Position Sizing minimum executable transaction-size policy, likely for transaction efficiency and avoiding non-meaningful orders.
2. Is the rationale documented? The contract is documented, but independent 1M-account Safety necessity was not found: `RATIONALE_NOT_FOUND`.
3. Does it overlap other components? Yes, for Safety, concentration, broker lot, quality, and allocation roles.
4. Is one round lot meaningless in a 1M account? No. In this evidence set all one-lot results are >=10% weight.
5. Is complete removal architecturally safe? Not useful by itself; with Strategy/target preserved it creates 0 new executable cases.
6. Is lot-aware fallback better than complete removal? Yes.
7. Are dangerous target overshoot cases present? Yes. 38 / 38 fallback cases overshoot target; max overshoot is about 10.54pp.
8. Do DPC/Safety/Strategy position-count controls sufficiently prevent fragmentation? In this evidence set yes, but future fallback should record position-count impact.
9. Is there a reason to keep policy only for BUY_NEW? No explicit design rationale found; BUY_NEW needs separate risk semantics, not necessarily this buffered threshold.
10. Is BUY_ADD difference valid? Yes, because BUY_ADD has existing exposure and L21D/L21F authorization; BUY_NEW creates new exposure.
11. Regression confirmed? No.
12. Architecture gap? Yes.
13. Is a fix needed? Yes, design first.
14. Next implementation direction? Lot-aware replacement/fallback, not blanket removal.

Primary judgment:

`PHASE29_L21N_MINIMUM_MEANINGFUL_NOTIONAL_POLICY_REPLACEMENT_WITH_LOT_AWARE_FALLBACK_RECOMMENDED`
