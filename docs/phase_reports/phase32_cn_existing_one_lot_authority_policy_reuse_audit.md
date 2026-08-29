# Phase32-CN Existing Minimum Executable One-Lot Authority Policy Reuse Audit

## Executive Summary

Phase30 already designed and implemented a PC-owned minimum executable one-lot authority for `BUY_NEW` / `REENTRY` cases where a positive continuous PC target is below one Japanese trading unit. The authority still exists in current code and remains guarded through Portfolio Construction, Position Sizing, runtime position sizing authority, and submit-feasibility validation.

The existing policy is not a pure legacy fallback. It was an explicit authority repair: PC may promote `0 -> 1lot` only after entry admission, one-lot feasibility, Strategy cap, Safety hard cap, Cash/budget, and broker/lot guards pass. PS consumes the result only after PC materializes the authority.

However, the policy is only partially reusable for Phase32-CM. Its current overshoot semantics are coarse. It records `target_to_one_lot_ratio`, `projected_one_lot_portfolio_weight`, Strategy cap, Safety cap, entry state, Buy Quality action, relative opportunity, and opportunity cost, but it does not provide a deterministic bounded overshoot taxonomy for `ADMIT_ONE_LOT` / `BLOCK` / `REVIEW_REQUIRED`. Before CH/CJ, `BUY_NEW_REDUCED_ONLY` could pass one-lot admission if cap/safety/budget passed. After CH/CJ, reduced-quality sub-lot names are blocked by `lot_minimum_exceeds_quality_authorized_target` before the old authority can express a bounded one-lot decision.

Conclusion: reuse the Phase30 authority chain, owner, evidence fields, and fail-closed guards, but migrate it with semantic repair and schema extension into the current CH/CJ/CC/BF architecture. A fully new policy is not justified; an as-is reuse is also not safe.

## Sources Reviewed

- `docs/phase_reports/phase32_cm_bounded_minimum_executable_one_lot_authority_design.md`
- `docs/phase_reports/phase32_cl_adaptive_buy_quality_allocation_semantics_lot_granularity_authority_audit.md`
- `docs/phase_reports/phase32_ck_old_vs_post_cj_day0_capital_deployment_delta_audit.md`
- `docs/phase_reports/phase30_v_entry_intelligence_overheated_momentum_one_lot_capital_concentration_repair_design.md`
- `docs/phase_reports/phase30_ak1u_minimum_executable_one_lot_admission_contract_audit.md`
- `docs/phase_reports/phase30_ak2_minimum_executable_one_lot_admission_repair_implementation.md`
- `docs/02_architecture/strategy_intelligence_architecture_v1.md`
- `src/ai_fund_lab_v2/strategy/portfolio_construction.py`
- `src/ai_fund_lab_v2/strategy/position_sizing.py`
- `src/ai_fund_lab_v2/runtime_v2/position_sizing_authority.py`
- `src/ai_fund_lab_v2/runtime_v2/planning_submit_feasibility.py`
- `tests/strategy/test_phase30_w_entry_one_lot_repair.py`
- `tests/strategy/test_phase22_e_portfolio_construction.py`
- `tests/strategy/test_phase22_j_position_sizing.py`
- `tests/runtime_v2/test_phase24_ht_planning_submit_feasibility.py`

No fresh-run, resume, replay, backtest, production code change, threshold change, or performance-based selection was performed.

## Phase30 Authority Reconstruction

### Owner And Boundary

Owner:

- Portfolio Construction.

Authority type:

- `PORTFOLIO_CONSTRUCTION_MINIMUM_EXECUTABLE_ONE_LOT_ADMISSION`

Schema:

- `minimum_executable_one_lot_authority.v1`

Lifecycle scope:

- `BUY_NEW`
- `REENTRY`
- current quantity must be zero
- promotion is limited to `0 -> 1lot`

Explicit non-scope:

- `BUY_ADD`
- second-lot-plus expansion
- PS-side independent rounding
- Safety-only concentration approval

Position Sizing remains executable quantity authority. Safety remains hard cap authority. Submit feasibility verifies the handoff before allowing the order path to proceed.

### Inputs

The implemented and documented authority uses the following PIT evidence:

- semantic intent: `BUY_NEW` / `REENTRY`
- current quantity
- original positive PC target / increment
- continuous target notional
- one-lot weight / notional / quantity
- projected post-trade weight
- `target_to_one_lot_ratio`
- Strategy cap
- Safety hard cap
- one-lot feasibility status
- Safety hard-cap preservation
- entry admission action and state
- Buy Quality action
- relative opportunity state
- opportunity cost state
- Cash / remaining budget feasibility through lot-aware reallocation
- broker / tradable-unit feasibility
- PIT flag: `future_information_used=false`

### Admission Semantics

Phase30 documentation defines a semantic, not fitted-performance, contract:

- If one lot is within target/headroom, normal execution may proceed.
- If one lot modestly exceeds Strategy target, admission may pass only when quality and opportunity evidence justify the overshoot.
- If one lot extremely exceeds Strategy target, Safety pass alone must not authorize the concentration.
- Overheated or reversal entry states defer or block.
- Missing or ambiguous evidence is not safe.
- Skipped/deferred capital should recycle to other executable candidates or Cash.

The Phase30-AK2 implementation narrows this to an explicit PC materialization requirement:

- original PC target must be positive and below one lot
- final promoted target must equal exactly one lot
- `one_lot_admission.status` must be `PASS`
- `one_lot_feasibility_status` must be `PASS`
- Safety hard cap must be preserved
- final promoted target must not exceed the supplied Strategy cap
- one-lot quantity must be positive

PS then consumes only if the authority exists, decision is `ADMIT`, quantity and notional match, intent and symbol match, and cap/safety guards still pass.

## Current Implementation Status

### Current PC Producer

Current Portfolio Construction still contains:

- `_quality_adjusted_one_lot_admission(...)`
- `_minimum_executable_one_lot_authority(...)`

`_minimum_executable_one_lot_authority(...)` emits:

- `schema_version = minimum_executable_one_lot_authority.v1`
- `authority_type = PORTFOLIO_CONSTRUCTION_MINIMUM_EXECUTABLE_ONE_LOT_ADMISSION`
- `decision = ADMIT`
- `reason = MINIMUM_EXECUTABLE_ONE_LOT_ADMITTED`
- `intent = BUY_NEW | REENTRY`
- `current_quantity = 0`
- `original_pc_target_weight`
- `original_pc_increment_weight`
- `one_lot_weight`
- `target_to_one_lot_ratio`
- `projected_one_lot_portfolio_weight`
- Strategy cap
- Safety cap
- `ps_final_quantity`
- `future_information_used = false`

### Current PS And Runtime Consumers

`strategy/position_sizing.py` still validates the authority before treating a row as minimum-one-lot authorized. It requires:

- semantic `BUY_NEW` / `REENTRY`
- current quantity zero
- `decision = ADMIT`
- reason `MINIMUM_EXECUTABLE_ONE_LOT_ADMITTED`
- lot-resolution admitted flag
- one-lot feasibility `PASS`
- one-lot fallback applied
- Safety hard cap preserved
- target and post-trade weight within Safety cap
- final quantity positive and no more than one lot

`runtime_v2/position_sizing_authority.py` also recognizes and consumes the same authority.

`runtime_v2/planning_submit_feasibility.py` verifies semantic, symbol, intent, decision, quantity, notional, Strategy cap, and Safety cap before submit feasibility passes.

### Active Or Disconnected?

The policy is active in code and tests, but only partially active in the current Phase32 path.

Active:

- PC can still materialize the authority in qualifying paths.
- PS and runtime authority can still consume it.
- Submit feasibility still validates it.
- Phase30/Phase22 tests still cover admission, Strategy cap block, Safety cap block, Cash insufficiency, BUY_WAIT block, REENTRY admission, and ADD/second-lot exclusion.

Migration gap:

- CH/CJ introduced quality ceiling preservation. For reduced-quality sub-lot `BUY_NEW`, `_quality_adjusted_one_lot_admission(...)` now fail-closes when `quality_authorized_target_weight < one_lot_weight`, with `lot_minimum_exceeds_quality_authorized_target`.
- That block occurs before the minimum one-lot authority can express the CM-style bounded decision.
- Current BF/CC production-shaped flow needs an explicit one-lot candidate admitted into common capital competition, not an implicit final target promotion inside older lot-aware reallocation.

Therefore the existing authority is not gone, but it is not yet correctly migrated into the current CH/CJ/CC/BF reduced-quality sub-lot boundary.

## Overshoot Policy Assessment

Overshoot policy exists only partially.

Defined:

- `target_to_one_lot_ratio`
- one-lot weight and notional
- projected post-trade weight
- Strategy cap
- Safety hard cap
- cap preservation
- entry state
- Buy Quality action
- relative opportunity state
- opportunity cost state
- residual Cash destination

Not sufficiently defined:

- deterministic bounded overshoot classification
- distinction between modest, material, and extreme overshoot beyond cap-only tests
- `ADMIT_ONE_LOT` vs `BLOCK` vs `REVIEW_REQUIRED` as first-class authority decisions
- explicit explanation that quality target overshoot is acceptable because specific PIT evidence justifies one lot
- common-frontier comparison against alternatives before final deployment

Phase30 prose says extreme overshoot needs stronger quality evidence and Safety pass alone is insufficient. The current implementation does not fully encode that prose. If entry action is `BUY_NEW_ALLOWED`, `BUY_NEW_REDUCED_ONLY`, or blank, and cap/safety/budget pass, the policy can pass without a separate overshoot severity taxonomy.

No evidence was found that a fixed overshoot threshold was selected from historical performance. The fixed numbers in the path are existing Strategy/Safety caps and discrete lot mechanics, not a performance-tuned one-lot admission threshold.

## Buy Quality Integration Assessment

Buy Quality integration is partial.

Positive integration:

- `entry_admission_action` is consumed.
- `entry_admission_state` is consumed.
- `quality_action` is materialized.
- `BUY_WAIT`, `REJECT_BUY_NEW`, `REVIEW_REQUIRED`, `OVERHEATED_DECELERATING_ENTRY`, and `REVERSAL_RISK_ENTRY` block or defer.
- Reduced allocation is recognized as distinct from full allocation.

Gap:

- Before CH/CJ, `BUY_NEW_REDUCED_ONLY` could pass one-lot overshoot broadly if other guards passed.
- After CH/CJ, reduced-quality sub-lot targets are blocked categorically by the quality ceiling before a bounded one-lot authority can decide.
- Neither state provides the CM-required middle path: preserve Buy Quality reduction, but allow PC to explicitly admit one lot only when PIT evidence explains why overshooting the reduced target is still acceptable.

## Representative Case Characterization

The following cases use the CK/CM decision-time weights. No future outcome or PnL evidence is used.

| Symbol | Quality target | One-lot weight | Overshoot ratio | Existing Phase30 pre-CH/CJ policy, conceptually | Current post-CJ behavior | Reuse implication |
|---|---:|---:|---:|---|---|---|
| 33700 | about 2.17% | about 3.41% | 1.57x | Likely ADMIT if entry action is allowed/reduced and cap/safety/budget pass | BLOCK: `lot_minimum_exceeds_quality_authorized_target` | Good candidate for bounded explicit review/admit logic |
| 83060 | about 2.06% | about 6.48% | 3.14x | Likely ADMIT if cap/safety/budget pass | BLOCK: `lot_minimum_exceeds_quality_authorized_target` | Needs stronger overshoot explanation than current Phase30 code provides |
| 92420 | about 2.07% | about 13.75% | 6.65x | Likely ADMIT if below 18% Strategy cap and 25% Safety cap | BLOCK: `lot_minimum_exceeds_quality_authorized_target` | Exposes major gap: extreme overshoot can pass cap-only old policy |
| 93600 | about 2.32% | about 19.11% | 8.23x | BLOCK by 18% Strategy cap unless an explicit cap-overshoot authority exists | BLOCK: quality ceiling and/or Strategy cap | Existing cap guard is reusable |

Important distinction:

- Existing Phase30 policy would not simply buy every positive target. It blocks Safety cap breaches, Strategy cap breaches, BUY_WAIT, rejected entries, review-required entries, overheated/reversal entries, Cash insufficiency, lot/broker infeasibility, ADD, and second-lot-plus cases.
- But for reduced-quality sub-lot `BUY_NEW` that is below Strategy/Safety caps, it does not fully encode the overshoot acceptability semantics required by CM.

## Reuse Classification

Classification:

- `REUSE_WITH_SEMANTIC_REPAIR`

Reason:

- Reuse owner boundary: yes.
- Reuse evidence fields: yes.
- Reuse PS/submit validation chain: yes.
- Reuse cap/safety/budget/fail-closed guards: yes.
- Reuse as-is: no, because the old policy is too permissive for reduced-quality extreme overshoot and the current CH/CJ path is too strict for all reduced-quality sub-lot cases.
- Schema migration is also needed, but semantic repair is the dominant classification.

## Migration Requirements For CM

The repaired CM implementation should reuse Phase30 as the backbone:

1. Keep PC as the one-lot admission owner.
2. Keep PS as executable quantity authority.
3. Keep submit-feasibility validation.
4. Keep `0 -> 1lot` only.
5. Keep ADD and second-lot-plus exclusion.
6. Keep Strategy cap and Safety hard cap separation.
7. Keep missing/ambiguous evidence fail-closed.
8. Keep PIT flags and lineage.

But it must add or migrate:

1. First-class decisions: `ADMIT_ONE_LOT`, `BLOCK`, `REVIEW_REQUIRED`.
2. Explicit quality-target overshoot evidence.
3. Deterministic overshoot acceptability explanation from existing PIT evidence.
4. Common-frontier candidate materialization after `ADMIT_ONE_LOT`, not forced purchase.
5. Cash and alternative opportunity comparison lineage.
6. BF/CC compatibility so admitted one-lot candidates compete with NEW/REENTRY/ADD/Cash.
7. No fallback to old implicit one-lot rescue.

## Defect / No-Defect Judgment

No defect was found in Phase30’s core ownership principle. The architecture already anticipated the discrete-lot problem and correctly separated PC admission from PS quantity conversion.

A current migration gap is present. Phase32 CH/CJ correctly preserved Buy Quality reduction against silent re-expansion, but it removed the old implicit/reduced one-lot behavior without migrating Phase30’s explicit authority into the new common-frontier boundary. That leaves high-price reduced-quality positive targets with only two extremes:

- strict zero when one lot exceeds quality target, or
- unsafe legacy-style one-lot rescue if the old behavior were restored directly.

The intended next step is the middle path: bounded explicit PC one-lot authority, derived from Phase30, repaired for CM semantics, then exposed to common capital competition.

## Final Judgments

PHASE32_CN_EXISTING_ONE_LOT_AUTHORITY_FOUND = YES

PHASE32_CN_EXISTING_POLICY_ACTIVE = PARTIAL

PHASE32_CN_POLICY_OWNER = Portfolio Construction owns minimum executable one-lot admission; Position Sizing owns quantity conversion; submit-feasibility validates the handoff.

PHASE32_CN_OVERSHOOT_POLICY_DEFINED = PARTIAL

PHASE32_CN_BUY_QUALITY_INTEGRATION = PARTIAL

PHASE32_CN_CURRENT_PATH_MIGRATION_GAP = YES

PHASE32_CN_POLICY_REUSE_CLASS = REUSE_WITH_SEMANTIC_REPAIR

PHASE32_CN_NEW_POLICY_REQUIRED = PARTIAL

PHASE32_CN_CM_IMPLEMENTATION_READY_AFTER_AUDIT = PARTIAL

PHASE32_CN_NEXT_STEP = Implement CM by reusing Phase30 PC-owned one-lot authority, extending it with explicit `ADMIT_ONE_LOT` / `BLOCK` / `REVIEW_REQUIRED` decisions, bounded overshoot evidence, and CC/BF common-frontier candidate integration while preserving CH/CJ quality ceilings and all Strategy/Safety/Cash/Risk guards.
