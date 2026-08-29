# Phase32-CL — Adaptive Buy Quality Allocation Semantics / Lot Granularity Authority Audit

## Executive Summary

This was a READ-ONLY / design-intent audit. No Production code, config, thresholds, runtime state, fresh-run, resume, replay, or backtest was changed or executed.

Conclusion:

Adaptive Buy Quality is an individual BUY admission and allocation-strength authority. Its `quality_allocation_adjustment` is not a Safety hard cap, not a predicted-return scalar, and not a fixed notional rule. The original Phase26-H SoT says downstream sizing consumes:

```text
post_quality_target_weight =
    resolved_target_weight * quality_allocation_adjustment
```

That supports preserving the adjustment as a real allocation magnitude authority. However, Phase30-V / Phase30-W architecture also explicitly introduced a PC-owned `minimum_executable_one_lot_authority` for `BUY_NEW` / `REENTRY` when a continuous positive target is below one Japanese round lot and when quality/opportunity evidence justifies the overshoot.

Therefore:

- Phase32-CH was correct to stop silent re-expansion from reduced target back to base target.
- Phase32-CJ was correct to stop implicit one-lot rescue from overriding Buy Quality.
- But CH strict hard ceiling is not the complete intended long-term architecture for Japanese 100-share lot granularity.
- The preferred design is Option C: a bounded explicit one-lot authority that can allow one lot above the quality-adjusted target only when a PIT, PC-owned authority proves the overshoot is acceptable under Buy Quality, opportunity, cap, Safety, Risk Pacing, Cash, and common capital competition.

## Sources Reviewed

- `docs/02_architecture/adaptive_buy_quality_authority.md`
- `docs/02_architecture/strategy_architecture_v1.md`
- `docs/02_architecture/strategy_intelligence_architecture_v1.md`
- `docs/02_architecture/portfolio_construction_and_position_sizing_contract.md`
- `docs/02_architecture/high_resolution_marginal_capital_value_and_portfolio_rotation_architecture.md`
- `docs/02_architecture/runtime_architecture_v2.md`
- `docs/phase_reports/phase32_ce_new_production_admission_quality_rank_semantic_audit.md`
- `docs/phase_reports/phase32_cf_adaptive_buy_quality_target_authority_preservation_design.md`
- `docs/phase_reports/phase32_ch_adaptive_buy_quality_target_authority_preservation_implementation.md`
- `docs/phase_reports/phase32_ck_old_vs_post_cj_day0_capital_deployment_delta_audit.md`
- Relevant implementation/tests in `src/ai_fund_lab_v2/strategy/buy_quality.py`, `src/ai_fund_lab_v2/strategy/position_sizing.py`, and `tests/strategy/test_phase22_e_portfolio_construction.py`

## 1. What Adaptive Buy Quality Is

Adaptive Buy Quality evaluates how trustworthy and allocation-capable a BUY opportunity is at the decision business date.

It consumes PIT evidence from:

- relative opportunity quality,
- market context,
- signal reliability,
- execution feasibility,
- portfolio fit.

It is distinct from Candidate AI:

- Candidate AI produces candidate/opportunity evidence.
- Adaptive Buy Quality judges whether that opportunity is usable for Production BUY allocation and at what strength.

It is distinct from Portfolio Construction:

- Portfolio Construction owns target membership, target weight, capital competition, Cash competition, and final deployment authority.
- Adaptive Buy Quality is an input authority to PC, not the sole allocator.

It is distinct from Position Sizing:

- Position Sizing converts accepted target allocation into notional/quantity candidates.
- PS must not reinterpret rank, score, or Quality to decide target membership/weight.

It is distinct from Safety and Risk Pacing:

- Safety is hard constraint authority.
- Risk Pacing determines prudent deployment intensity / budget.
- Buy Quality may reduce or reject an individual opportunity, but it is not the Safety hard maximum or portfolio-wide exposure controller.

### Action Semantics

| Action | Intended meaning |
| --- | --- |
| `FULL_ALLOCATION_ELIGIBLE` | Opportunity is allocation-capable at full PC target magnitude, subject to PC/BF/Cash/cap/Risk/Safety/PS constraints. |
| `REDUCED_ALLOCATION_ONLY` | Opportunity may remain Production deployable, but only at reduced allocation strength unless another explicit PIT authority authorizes more. |
| `REJECT` | No Production BUY allocation. Candidate may remain visible for audit, but target must be zero. |
| `REVIEW_REQUIRED` | No BUY crosses the broker/simulated broker boundary until resolved. |

## 2. Meaning of Allocation Adjustment

The original SoT and implementation point to this semantic:

```text
quality_allocation_adjustment = multiplicative sizing modifier / allocation strength scalar
post_quality_target_weight = resolved_target_weight * quality_allocation_adjustment
```

Best classification:

```text
C + D:
Multiplicative sizing modifier that produces a preferred / authorized reduced target,
subject to documented discrete-lot realization.
```

It is not an absolute Safety hard maximum. It is also not merely explanatory metadata. The Phase26-H SoT says Quality affects current-total-equity-based sizing and missing evidence must not default to `quality_adjustment=1.0`.

The strongest reading is:

- The post-quality target is authoritative against silent re-expansion.
- Discrete-lot realization may exceed it only through a separate explicit PC one-lot authority.

## 3. Was CH Hard-Cap Behavior Originally Intended?

Partially.

Supported by original design:

- Buy Quality is an allocation eligibility and allocation adjustment authority.
- Position Sizing consumes `post_quality_target_weight`.
- Reduced allocation must not silently become full/base allocation later.
- Missing/rejected/review Quality must fail closed.

Not fully supported as the complete design:

- Phase30 architecture explicitly allows `minimum_executable_one_lot_authority` for `BUY_NEW` / `REENTRY` when a continuous positive PC target is below one Japanese round lot.
- That authority is limited to `0 -> 1lot`.
- It must be PC-owned, PIT-safe, and justified by quality/opportunity evidence.
- Safety hard cap alone is not sufficient.
- Extreme one-lot overshoot must not be accepted merely because it is executable.

Therefore the CH/CJ strict ceiling is valid as a repair against silent fallback, but it is stricter than the older one-lot realization architecture when applied as the only possible behavior.

## 4. Japanese 100-Share Lot Interaction

For Japanese equities, a quality target around 2% can interact with one-lot weights like:

| Quality target | One-lot weight | Strict CH/CJ result | Architecture-intent result |
| ---: | ---: | --- | --- |
| 2% | 3% | Block by default | May pass only with explicit bounded one-lot authority |
| 2% | 6% | Block by default | Usually block unless strong explicit authority justifies large overshoot |
| 2% | 14% | Block by default | Block / REVIEW_REQUIRED; Safety pass alone is insufficient |
| 2% | 19% | Block by default | Block / REVIEW_REQUIRED; extreme concentration requires explicit authority |

The architecture does not support blind `ceil_to_one_lot` behavior. It also does not require permanent zero for every positive target below one lot. It requires a separate, bounded, explainable authority when the system chooses to buy one lot anyway.

## 5. Existing Guardrails If One Lot Is Bought

Existing guardrails that already constrain one-lot realization:

| Guardrail | Existing role | Sufficient alone? |
| --- | --- | --- |
| Strategy single-name cap 18% | Strategy concentration boundary | No; it caps concentration but does not justify Quality overshoot |
| Safety hard cap 25% | Final hard constraint | No; Safety pass is explicitly not enough to prove Strategy wants concentration |
| Risk Pacing | Deployment intensity / budget | No; controls aggregate deployment, not symbol-specific Quality overshoot |
| Cash / budget | Scarce capital and optionality | No; available cash does not authorize weak overshoot |
| Buy Quality | Opportunity trust and allocation strength | Necessary but needs one-lot interpretation |
| Opportunity / rank | Relative opportunity evidence | Necessary input, not sole authority |
| Common capital competition | Compares one-lot candidate vs alternatives and Cash | Necessary after explicit one-lot candidate exists |

Existing guardrails are sufficient to prevent many unsafe cases, but not sufficient to justify one-lot overshoot without an explicit one-lot authority. The missing piece is the decision contract that converts a sub-lot quality target into an allowed one-lot candidate.

## 6. Old Behavior Classification

OLD / Pre-CH behavior is MIXED:

- It resembles intended architecture because the SoT already had a `minimum_executable_one_lot_authority` concept.
- It also resembles accidental/legacy fallback because Phase32-CK found no evidence that OLD Day-0 high-price buys carried a bounded, explicit, PIT one-lot quality-overshoot authority.
- It was pragmatic discrete-lot realization, but too implicit.

For 33700 / 83060 / 92420 / 93600, OLD exposure depended materially on one-lot weights exceeding quality target by about 1.57x / 3.14x / 6.65x / 8.23x. A blanket restoration would recreate an implicit Quality override.

## Design Options

| Option | Description | Investment philosophy | Architecture fit | Risk | Cash optionality | 100-share fit | Fail-closedness | Judgment |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| A | CH strict hard ceiling: if one lot exceeds Quality target, buy 0 | Strong Quality discipline; avoids accidental concentration | PARTIAL: preserves Quality, but ignores Phase30 one-lot authority concept | Low concentration risk, high underdeployment risk | Strong Cash optionality | Poor for high-price symbols | Strong | Too strict as final design |
| B | Discrete-lot realization: if target > 0 and production deployable, allow minimum one lot | Practical deployment; avoids sub-lot dead zone | Weak: can override Quality without enough authority | High, especially 6-19% one-lot cases | Weak | Simple but blunt | Weak | Not acceptable |
| C | Bounded explicit one-lot authority | Preserves Quality while allowing practical deployment when justified | Best: matches Phase26 Quality plus Phase30 one-lot authority | Controlled if bounded and evidence-based | Preserved through competition with Cash | Good | Strong if missing/ambiguous evidence blocks | Preferred |
| OTHER | Per-symbol or price threshold exception | Could solve high-price cases mechanically | Poor unless separately justified | Tuning risk | Variable | Superficial | Often weak | Not preferred |

## Preferred Design: Bounded Explicit One-Lot Authority

Recommended contract:

```text
candidate_eligible
-> production_deployable_new/reentry
-> quality_authorized_target_weight
-> if one_lot_weight <= quality_authorized_target_weight:
       normal quality-bounded multi-lot expansion
   else:
       optional bounded one-lot authority evaluation
-> common NEW/REENTRY/ADD/Cash competition
-> BF aggregate
-> PS
```

Required evidence for one-lot exception:

- Buy Quality action is not `REJECT` / `REVIEW_REQUIRED` / `BUY_WAIT`.
- Quality score/action explicitly supports Production deployability.
- Opportunity/rank evidence is sufficient under an existing PC-owned method.
- Overshoot ratio and projected post-trade weight are materialized.
- Strategy cap and Safety hard cap both pass.
- Risk Pacing budget and Cash source pass.
- Common frontier confirms the one-lot candidate beats alternatives/Cash.
- Missing or ambiguous evidence returns `REVIEW_REQUIRED` or zero target.

Required output fields:

```text
minimum_executable_one_lot_authority:
  authority_type: PORTFOLIO_CONSTRUCTION_MINIMUM_EXECUTABLE_ONE_LOT_ADMISSION
  decision: ADMIT | BLOCK | REVIEW_REQUIRED
  original_quality_authorized_target_weight
  one_lot_weight
  overshoot_weight
  target_to_one_lot_ratio
  projected_one_lot_portfolio_weight
  strategy_cap
  safety_cap
  risk_pacing_status
  cash_budget_status
  buy_quality_status
  opportunity_evidence_status
  common_frontier_status
  reason_codes
  future_information_used: false
  historical_outcome_used: false
```

Non-negotiable:

- Do not use historical return/PnL to choose overshoot thresholds.
- Do not restore implicit one-lot rescue.
- Do not let PS independently round sub-lot targets upward.
- Do not allow available Cash or low position count alone to authorize one lot.

## Defect / No-Defect Judgment

CH/CJ fixed a real semantic defect: Buy Quality reduction was previously recorded but not preserved as final deployable sizing authority.

CK exposed a second design gap: Japanese 100-share granularity needs explicit one-lot realization semantics. Current strict blocking is semantically valid as a fail-closed interim state, but it likely under-expresses the older intended practical deployability concept.

Production repair is justified, but only as a design/implementation of explicit bounded one-lot authority. It should not be a rollback to OLD implicit minimum-lot rescue.

## Final Judgments

PHASE32_CL_ADAPTIVE_BUY_QUALITY_PURPOSE = individual BUY admission quality and allocation strength authority using PIT opportunity, market, reliability, execution feasibility, and portfolio-fit evidence

PHASE32_CL_ALLOCATION_ADJUSTMENT_SEMANTIC = multiplicative sizing modifier that produces a quality-authorized preferred/reduced target; binding against silent re-expansion, but discrete one-lot overshoot requires separate explicit authority

PHASE32_CL_CH_HARD_CEILING_ORIGINALLY_INTENDED = PARTIAL

PHASE32_CL_OLD_MINIMUM_LOT_BEHAVIOR_INTENDED = PARTIAL

PHASE32_CL_DISCRETE_LOT_SEMANTIC_GAP = YES

PHASE32_CL_EXISTING_GUARDRAILS_SUFFICIENT_FOR_ONE_LOT = PARTIAL

PHASE32_CL_PREFERRED_DESIGN_OPTION = C

PHASE32_CL_PRODUCTION_REPAIR_JUSTIFIED = YES

PHASE32_CL_NEXT_STEP = Design a bounded explicit PC-owned one-lot authority for NEW/REENTRY reduced-quality sub-lot targets, preserving CH/CJ quality ceiling by default and permitting overshoot only with PIT evidence, guardrail pass, common frontier competition, and fail-closed missing/ambiguous evidence.
