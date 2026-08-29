# Phase32-CC — NEW/REENTRY Target-Magnitude Multi-Lot Implementation

## Executive Summary

Phase32-CC implemented PC-authorized NEW/REENTRY target magnitude preservation in the production-shaped marginal capital authority path.

Before CC, `NEW_FIRST_LOT` and `REENTRY_FIRST_LOT` were generated as a single frontier lot even when PC had already authorized a larger executable target. BF then explicitly rejected entry lots whose `increment_index != 1`, so PC conviction magnitude collapsed at the PC-to-PS boundary.

After CC:

- NEW and REENTRY rows expand into deterministic lot #1/#2/#N candidates up to the PC target executable quantity.
- Each entry lot independently participates in the existing NEW/REENTRY/ADD/Cash common capital competition.
- BF aggregates accepted entry lots into one PS-compatible net target row.
- PC target quantity is preserved as the hard upper bound; lot #N+1 is absent.
- Cash, budget, cap, Safety, Risk Pacing, BV admission, BZ ADD PASS-only, BZ BF-only ADD authority, BR ADD quantity progression, and BT effective concentration cap behavior are preserved.

No fresh run, resume, replay, backtest, threshold tuning, marginal value tuning, Cash policy change, PM change, PS arithmetic change, Runtime change, REDUCE/EXIT change, or legacy fallback reactivation was performed.

## Implementation

### Shadow Frontier Entry Lot Expansion

Updated `src/ai_fund_lab_v2/strategy/common_marginal_capital_frontier_shadow.py`.

Key behavior:

- `NEW_FIRST_LOT` and `REENTRY_FIRST_LOT` now call `_entry_target_lot_candidates(...)` instead of emitting a single `_security_candidate(...)`.
- `_entry_target_magnitude_authority(...)` resolves PC target magnitude from lot-resolution evidence when present, or from PC `target_weight` floored to trading unit.
- The resolved target quantity is attached to each candidate as `pc_target_magnitude_authority`.
- Candidate identities remain stable because `increment_index`, `pre_quantity`, `post_quantity`, symbol, semantic type, and source lineage are included in the candidate identity.
- Entry lot pre/post weights are recomputed from hypothetical lot state; ADD weight progression remains on the pre-existing BR contract.
- Zero-target BV rows remain blocked by PC production admission and are not promoted to REVIEW_REQUIRED by missing target-magnitude evidence.

Important implementation references:

- [common_marginal_capital_frontier_shadow.py](/Users/negishi/work/ai-fund-lab-v2/src/ai_fund_lab_v2/strategy/common_marginal_capital_frontier_shadow.py:63)
- [common_marginal_capital_frontier_shadow.py](/Users/negishi/work/ai-fund-lab-v2/src/ai_fund_lab_v2/strategy/common_marginal_capital_frontier_shadow.py:426)
- [common_marginal_capital_frontier_shadow.py](/Users/negishi/work/ai-fund-lab-v2/src/ai_fund_lab_v2/strategy/common_marginal_capital_frontier_shadow.py:513)

### Production-Shaped Authority / BF Boundary

Updated `src/ai_fund_lab_v2/strategy/marginal_capital_frontier_authority.py`.

Key behavior:

- Budget-bounded acceptance now tracks accepted entry lots by `semantic_type|symbol`, requiring contiguous lot sequence.
- BF boundary validation now allows NEW/REENTRY increment indexes `1..N`, validates pre/post quantity progression, validates first entry pre-quantity is zero, and verifies final target quantity does not exceed the PC target magnitude authority.
- BF aggregates multi-lot NEW/REENTRY into the same PS-compatible net target structure already used by ADD.
- `_target_from_candidate(...)` carries `entry_lot_index` and `pc_target_magnitude_authority` into accepted targets.

Important implementation references:

- [marginal_capital_frontier_authority.py](/Users/negishi/work/ai-fund-lab-v2/src/ai_fund_lab_v2/strategy/marginal_capital_frontier_authority.py:320)
- [marginal_capital_frontier_authority.py](/Users/negishi/work/ai-fund-lab-v2/src/ai_fund_lab_v2/strategy/marginal_capital_frontier_authority.py:909)
- [marginal_capital_frontier_authority.py](/Users/negishi/work/ai-fund-lab-v2/src/ai_fund_lab_v2/strategy/marginal_capital_frontier_authority.py:929)

## Guardrail Preservation

Preserved by focused tests:

- BV: legacy PC `target_weight=0` NEW/REENTRY rows remain non-PS-consumable.
- BZ: ADD `final_add_eligibility != PASS` remains blocked.
- BZ: ADD remains BF-only for PS/Runtime BUY_ADD generation.
- BR: ADD repeated-lot quantity progression remains consistent.
- BT: effective Strategy/Safety concentration cap behavior remains active.
- BO: PIT flags continue to pass planning submit feasibility.
- Legacy zero fallback remains disabled.
- Production consumer switch behavior remains explicit through BG/BF authority only.

## Focused Verification

Commands run:

```bash
PYTHONPYCACHEPREFIX=/private/tmp/phase32_cc_pycache python3 -m py_compile src/ai_fund_lab_v2/strategy/common_marginal_capital_frontier_shadow.py src/ai_fund_lab_v2/strategy/marginal_capital_frontier_authority.py tests/strategy/test_phase32_az_marginal_capital_frontier_authority.py tests/strategy/test_phase32_bg_pc_to_ps_consumer_switch.py
```

Result: PASS.

```bash
PYTHONPYCACHEPREFIX=/private/tmp/phase32_cc_pycache python3 -m pytest tests/strategy/test_phase32_as_common_marginal_capital_frontier_shadow.py tests/strategy/test_phase32_az_marginal_capital_frontier_authority.py tests/strategy/test_phase32_bg_pc_to_ps_consumer_switch.py
```

Result: PASS, 66 passed.

New/updated focused coverage includes:

- PC 400 shares -> NEW lots #1-#4.
- Lot #5 absent.
- REENTRY multi-lot expansion.
- Lot #1 reject prevents later lot acceptance.
- Cash stops remaining entry lots.
- Cap crossing blocks the crossing lot.
- BV zero-target NEW remains blocked.
- BZ FAIL_CLOSED ADD remains blocked.
- PASS ADD multi-lot remains preserved.
- BF net aggregation for entry lots.
- PS consumes NEW/REENTRY net quantity deltas.
- Duplicate entry target identity fails closed.
- Deterministic/PIT focused coverage remains passing.

Representative test references:

- [test_phase32_az_marginal_capital_frontier_authority.py](/Users/negishi/work/ai-fund-lab-v2/tests/strategy/test_phase32_az_marginal_capital_frontier_authority.py:713)
- [test_phase32_bg_pc_to_ps_consumer_switch.py](/Users/negishi/work/ai-fund-lab-v2/tests/strategy/test_phase32_bg_pc_to_ps_consumer_switch.py:282)

## Changed Files

- `src/ai_fund_lab_v2/strategy/common_marginal_capital_frontier_shadow.py`
- `src/ai_fund_lab_v2/strategy/marginal_capital_frontier_authority.py`
- `tests/strategy/test_phase32_az_marginal_capital_frontier_authority.py`
- `tests/strategy/test_phase32_bg_pc_to_ps_consumer_switch.py`
- `docs/phase_reports/phase32_cc_new_reentry_target_magnitude_multilot_implementation.md`

## Notes

For rows that have positive PC target weight but no explicit executable target quantity evidence and whose target notional is below one trading lot, CC preserves prior one-lot behavior instead of inventing multi-lot magnitude. Multi-lot expansion requires resolvable PC target quantity/weight magnitude and remains bounded by that authority.

The working tree already contained many pre-existing untracked/dirty Phase32 files. CC did not revert or modify unrelated files.

## Final Judgments

PHASE32_CC_NEW_MULTI_LOT_IMPLEMENTED = YES

PHASE32_CC_REENTRY_MULTI_LOT_IMPLEMENTED = YES

PHASE32_CC_PC_TARGET_HARD_UPPER_BOUND = YES

PHASE32_CC_COMMON_COMPETITION_PRESERVED = YES

PHASE32_CC_ADD_SEMANTICS_PRESERVED = YES

PHASE32_CC_BV_BZ_GUARDRAILS_PRESERVED = YES

PHASE32_CC_BF_NET_AGGREGATION_PASS = YES

PHASE32_CC_PS_COMPATIBLE = YES

PHASE32_CC_LEGACY_FALLBACK_ZERO = YES

PHASE32_CC_REGRESSION_STATUS = PASS

PHASE32_CC_FRESH_VALIDATION_READY = YES

PHASE32_CC_NEXT_STEP = User-operated short fresh validation after CC, with first focus on Day-0 NEW target magnitude distribution, BF aggregated net quantities, PS consumed quantities, and no regression in ADD PASS-only/BF-only behavior.
