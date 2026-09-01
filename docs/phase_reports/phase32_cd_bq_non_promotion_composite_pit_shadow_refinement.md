# Phase32-CD — BQ Non-Promotion Composite PIT SHADOW Refinement

## Scope

- Target run: `runtime-test-historical-extended-smoke-20260831T234344371102Z`
- Audit mode: SHADOW / READ-ONLY
- Latest completed actual Runtime day used: `2023-05-25`
- BZ fixed comparable window: through `2023-04-18`
- CD extended window: through `2023-05-25`

No source, config, PM decision, HOLD/REDUCE/EXIT semantic, SELL threshold, PM threshold, model, weight, BQ Production decision, Runtime state, Pending, Ledger, resume, recover, replay, or fresh-run action was changed or executed.

CD preserves Phase32-BO/BP/BQ:

- Current BQ `SHADOW_FULL_EXIT` path is accepted and Production-active.
- Broad `lot-blocked REDUCE -> FULL EXIT` remains rejected.
- BO's profit-cushion correction remains intact: profit is context, not standalone HOLD or SELL authority.
- BQ Production promotion remains limited to BO `SHADOW_FULL_EXIT`.
- BZ's harmful non-promotion population is real but only partially separable.
- CC does not justify changing PM HOLD -> REDUCE Production semantics.
- 59350-style PM HOLD confirmation lag is out of scope for CD.

Later outcomes were used only after PIT classification was frozen.

## Evidence Sources

- `.runtime/runtime_state/sell_pipeline/<business_date>/order_plan.json`
- `reports/runtime_tests/runs/runtime-test-historical-extended-smoke-20260831T234344371102Z/run_state.json`
- `reports/runtime_tests/runs/runtime-test-historical-extended-smoke-20260831T234344371102Z/daily/<date>/current_valuation_refresh/current_valuation_manifest.json`
- `reports/runtime_tests/runs/runtime-test-historical-extended-smoke-20260831T234344371102Z/daily/<date>/current_valuation_refresh/valuation_projection.json`
- `reports/runtime_tests/runs/runtime-test-historical-extended-smoke-20260831T234344371102Z/daily/<date>/execution/fills.json`
- `docs/phase_reports/phase32_bz_recurrent_bq_insufficient_hold_later_loss_pit_separability_read_only_audit.md`
- `docs/phase_reports/phase32_cc_existing_pm_hold_reduce_exit_boundary_shadow_reclassification_audit.md`
- `docs/phase_reports/phase32_bo_profit_cushion_contextualized_shadow_refinement_evaluation.md`
- `docs/phase_reports/phase32_bp_bo_full_exit_production_promotion_acceptance_read_only_audit.md`
- `docs/phase_reports/phase32_bq_lot_blocked_reduce_reconsidered_full_exit_production_implementation.md`

## Population Reproduction

Population rule:

```text
PM REDUCE
-> REDUCE_UNEXECUTABLE_DUE_TO_DISCRETE_LOT
-> BQ in {SHADOW_INSUFFICIENT_EVIDENCE, SHADOW_HOLD}
-> status = NOT_PROMOTED
-> Production = NO_ORDER
```

### BZ Fixed Comparable Population

Through `2023-04-18`, CD reproduced BZ's structural counts:

| Scope | Count |
|---|---:|
| non-promoted raw rows | 219 |
| campaign first episodes | 113 |
| raw `SHADOW_INSUFFICIENT_EVIDENCE` | 201 |
| raw `SHADOW_HOLD` | 18 |
| first-episode `SHADOW_INSUFFICIENT_EVIDENCE` | 103 |
| first-episode `SHADOW_HOLD` | 10 |
| current BQ `SHADOW_FULL_EXIT` raw rows | 31 |

Outcome labels with evidence capped at the same fixed window:

| Label | First episode count |
|---|---:|
| `HARMFUL_NON_PROMOTION` | 5 |
| `BENEFICIAL_NON_PROMOTION` | 3 |
| `NEUTRAL` | 104 |
| `INSUFFICIENT_OUTCOME` | 1 |

### CD Extended Population

Through `2023-05-25`:

| Scope | Count |
|---|---:|
| non-promoted raw rows | 259 |
| campaign first episodes | 133 |
| raw `SHADOW_INSUFFICIENT_EVIDENCE` | 238 |
| raw `SHADOW_HOLD` | 21 |
| first-episode `SHADOW_INSUFFICIENT_EVIDENCE` | 122 |
| first-episode `SHADOW_HOLD` | 11 |
| current BQ `SHADOW_FULL_EXIT` raw rows | 36 |
| current BQ `SHADOW_FULL_EXIT` first episodes | 32 |

Extended first-episode outcome labels:

| Label | First episode count |
|---|---:|
| `HARMFUL_NON_PROMOTION` | 6 |
| `BENEFICIAL_NON_PROMOTION` | 4 |
| `NEUTRAL` | 122 |
| `INSUFFICIENT_OUTCOME` | 1 |

## Current FULL EXIT Neighborhood

Current accepted BQ `SHADOW_FULL_EXIT` rows through `2023-05-25` share this neighborhood:

- recovery: all `NO_RECOVERY`
- strong medium-term structure: false for all rows
- trend health: `MIXED` or `WEAK`
- relative strength: `MIXED` or `WEAK`
- reversal risk: `MIXED` or `ELEVATED_RISK`
- PM reason: almost all `risk_increased_but_trend_not_broken`

This remains the correct positive semantic reference. A refined non-promotion diagnostic should be close to this neighborhood, not merely profitable or large.

## SHADOW Composite Refinement

The evaluated SHADOW-only composite uses existing BO/BQ PIT fields only:

- `NO_RECOVERY`
- no `strong_medium_term_structure`
- weak participation
- elevated reversal / participation / exhaustion risk
- trend health not supportive
- relative strength not supportive, or multi-risk evidence strong enough to offset one supportive dimension
- repeated REDUCE evidence as persistence context only
- position notional as severity context only, not directional authority

Diagnostic labels:

- `SHADOW_REFINED_FULL_EXIT_CANDIDATE`
- `SHADOW_REFINED_HOLD`
- `SHADOW_REFINED_AMBIGUOUS`

No Production action is changed.

Extended raw-row diagnostic counts:

| Diagnostic | Raw count |
|---|---:|
| `SHADOW_REFINED_FULL_EXIT_CANDIDATE` | 32 |
| `SHADOW_REFINED_HOLD` | 67 |
| `SHADOW_REFINED_AMBIGUOUS` | 160 |

Extended first-episode diagnostic counts:

| Diagnostic | Campaign first episodes |
|---|---:|
| `SHADOW_REFINED_FULL_EXIT_CANDIDATE` | 12 |
| `SHADOW_REFINED_HOLD` | 39 |
| `SHADOW_REFINED_AMBIGUOUS` | 82 |

## Mandatory Harmful Cases

| Symbol | Date | BQ | Refined diagnostic | PM reason | Raw reduce | Qty | Return | Age | Notional | PIT read | Later label |
|---:|---|---|---|---|---:|---:|---:|---:|---:|---|---|
| 78860 | 2022-12-02 | `SHADOW_INSUFFICIENT_EVIDENCE` | `SHADOW_REFINED_AMBIGUOUS` | `peak_drawdown_warning` | 50 | 100 | +31.3% | 17 | 146,600 | SUPPORTIVE trend, MIXED RS, WEAK participation, ELEVATED participation risk, MIXED reversal, no structure, `PROFIT_AT_RISK`, no recovery | harmful, -18,400 |
| 97310 | 2022-12-14 | `SHADOW_INSUFFICIENT_EVIDENCE` | `SHADOW_REFINED_HOLD` | `peak_drawdown_warning` | 33 | 100 | +5.2% | 26 | 205,700 | SUPPORTIVE trend/RS, WEAK participation, manageable exhaustion/reversal, strong structure true, `PROFIT_AT_RISK`, no recovery | harmful, -24,500 |
| 14000 | 2023-02-24 | `SHADOW_INSUFFICIENT_EVIDENCE` | `SHADOW_REFINED_AMBIGUOUS` | `risk_increased_but_trend_not_broken` | 66 | 200 | -5.4% | 2 | 32,400 | SUPPORTIVE trend, MIXED RS, SUPPORTIVE participation, manageable risk, no structure, no recovery | harmful, -17,300 |
| 14000 | 2023-03-01 | `SHADOW_INSUFFICIENT_EVIDENCE` | `SHADOW_REFINED_AMBIGUOUS` | `peak_drawdown_warning` | 66 | 200 | -7.2% | 7 | 30,800 | SUPPORTIVE trend, MIXED RS, WEAK participation, ELEVATED exhaustion/participation/reversal, no structure, no recovery | harmful, -15,700 |
| 52470 | 2023-04-05 | `SHADOW_INSUFFICIENT_EVIDENCE` | `SHADOW_REFINED_FULL_EXIT_CANDIDATE` | `risk_increased_but_trend_not_broken` | 25 | 100 | +6.8% | 2 | 271,000 | MIXED trend, SUPPORTIVE RS, WEAK participation, ELEVATED exhaustion/participation/reversal, risk votes 4, no structure, `PROFIT_AT_RISK`, no recovery | harmful, -10,000 |
| 41660 | 2023-04-13 | `SHADOW_HOLD` | `SHADOW_REFINED_HOLD` | `peak_drawdown_warning` | 50 | 100 | +8.1% | 1 | 168,500 | SUPPORTIVE trend/RS/participation, manageable risk, strong structure true, `CONTEXTUAL_HOLD_SUPPORT`, no recovery | harmful, -33,500 |

Findings:

- `52470_FULL_EXIT_NEIGHBOR_SUPPORTED = YES_SHADOW_ONLY`
- `14000_PERSISTENCE_STRENGTHENS_EXIT_CASE = YES_BUT_NOT_ENOUGH`; the repeated row adds weak participation and elevated risks, but SUPPORTIVE trend remains.
- `97310_REMAINS_AMBIGUOUS = YES`; the loss is real, but strong/supportive structure is current PIT evidence.
- `41660_REMAINS_AMBIGUOUS = YES`; current BQ HOLD is coherent because support is broad and profit is contextual HOLD support.

## Mandatory Controls

| Symbol | Date | BQ | Refined diagnostic | PIT read | Later label |
|---:|---|---|---|---|---|
| 92420 | 2022-10-04 | `SHADOW_INSUFFICIENT_EVIDENCE` | `SHADOW_REFINED_AMBIGUOUS` | WEAK trend/participation and elevated risk, but SUPPORTIVE RS and no current FULL_EXIT confirmation | beneficial |
| 99840 | 2022-10-31 | `SHADOW_HOLD` | `SHADOW_REFINED_HOLD` | SUPPORTIVE trend/RS/participation, strong structure true, `CONTEXTUAL_HOLD_SUPPORT` | beneficial |
| 43880 | 2023-03-23 | `SHADOW_INSUFFICIENT_EVIDENCE` | `SHADOW_REFINED_HOLD` | SUPPORTIVE trend/RS with strong structure true despite weak participation | beneficial |

Representative neutral controls captured by the refined candidate include `93600`, `91070`, `92540`, `62270`, `89380`, `46890`, `79010`, `31330`, `74860`, `94210`, and `45980`. These share FULL_EXIT-neighborhood ingredients but did not produce material +5BD losses.

## False-Exit Control

Extended first-episode `SHADOW_REFINED_FULL_EXIT_CANDIDATE` outcomes:

| Outcome | Count |
|---|---:|
| harmful captured | 1 |
| beneficial false exit | 0 |
| neutral captured | 11 |

Extended harmful first episodes:

| Metric | Count |
|---|---:|
| harmful campaigns captured | 1 |
| harmful campaigns missed | 5 |

Economic characterization:

- estimated avoided-loss opportunity directly captured: approximately `10,000`, from `52470`
- beneficial false-exit cost: `0` by the `>= 10,000` beneficial threshold
- neutral false-exit exposure exists: 11 neutral first episodes would be flagged if this were promoted mechanically

This is not enough for Production. It is enough to justify SHADOW refinement because the candidate is more precise than broad BQ promotion and does not capture the known beneficial controls.

## Composite Separability

Judgment:

```text
BQ_NON_PROMOTION_COMPOSITE_PIT_SEPARABILITY = PARTIALLY_SEPARABLE
```

Most informative composite dimensions:

- current FULL_EXIT neighborhood proximity
- no recovery
- no strong medium-term structure
- weak participation
- elevated reversal / participation / exhaustion risk
- trend health MIXED or WEAK
- risk vote context
- repeated REDUCE persistence as context only
- profit-at-risk as context only
- position notional as severity context only

Not sufficient alone:

- profit at risk
- peak drawdown warning
- high notional
- repeated warning count
- `SHADOW_INSUFFICIENT_EVIDENCE`
- `risk_increased_but_trend_not_broken`

## Relationship To Production BQ

The refinement is best classified as:

```text
evidence persistence / semantic clarification inside existing BQ shadow boundary
```

It is not ready as Production action logic. Production BQ should remain limited to BO `SHADOW_FULL_EXIT`.

No optimized current-return cutoff, notional cutoff, loss cutoff, warning-count cutoff, or future-outcome-selected threshold was used.

Profit alone was not used as SELL authority. Position notional was not used as directional SELL authority.

## Required Final Answers

1. `LATEST_COMPLETED_DATE_USED = 2023-05-25`
2. `BZ_FIXED_COMPARABLE_POPULATION_REPRODUCED = YES; 219 raw / 113 first episodes / 201 INSUFFICIENT / 18 HOLD`
3. `CD_EXTENDED_NON_PROMOTED_RAW_COUNT = 259`
4. `CD_EXTENDED_NON_PROMOTED_CAMPAIGN_COUNT = 133`
5. `78860_REPRODUCED = YES`
6. `97310_REPRODUCED = YES`
7. `14000_REPRODUCED = YES`
8. `52470_REPRODUCED = YES`
9. `41660_REPRODUCED = YES`
10. `92420_CONTROL_PRESERVED = YES; classified SHADOW_REFINED_AMBIGUOUS, not FULL_EXIT candidate`
11. `99840_CONTROL_PRESERVED = YES; classified SHADOW_REFINED_HOLD`
12. `43880_CONTROL_PRESERVED = YES; classified SHADOW_REFINED_HOLD`
13. `BQ_NON_PROMOTION_COMPOSITE_PIT_SEPARABILITY = PARTIALLY_SEPARABLE`
14. `MOST_INFORMATIVE_COMPOSITE_DIMENSIONS = FULL_EXIT_NEIGHBORHOOD_PROXIMITY, NO_RECOVERY, NO_STRONG_STRUCTURE, WEAK_PARTICIPATION, ELEVATED_REVERSAL/PARTICIPATION/EXHAUSTION_RISK, MIXED_OR_WEAK_TREND, RISK_VOTE_CONTEXT, REPEATED_REDUCE_PERSISTENCE_CONTEXT`
15. `52470_FULL_EXIT_NEIGHBOR_SUPPORTED = YES_SHADOW_ONLY`
16. `14000_PERSISTENCE_STRENGTHENS_EXIT_CASE = YES_BUT_NOT_ENOUGH_FOR_REFINED_FULL_EXIT`
17. `97310_REMAINS_AMBIGUOUS = YES`
18. `41660_REMAINS_AMBIGUOUS = YES`
19. `REPEATED_REDUCE_PERSISTENCE_USEFUL = YES_AS_CONTEXT_ONLY; NOT_A_THRESHOLD`
20. `SHADOW_REFINED_FULL_EXIT_CANDIDATE_COUNT = 32_RAW / 12_FIRST_EPISODES`
21. `SHADOW_REFINED_HOLD_COUNT = 67_RAW / 39_FIRST_EPISODES`
22. `SHADOW_REFINED_AMBIGUOUS_COUNT = 160_RAW / 82_FIRST_EPISODES`
23. `HARMFUL_CAMPAIGNS_CAPTURED = 1`
24. `HARMFUL_CAMPAIGNS_MISSED = 5`
25. `BENEFICIAL_FALSE_EXIT_COUNT = 0`
26. `NEUTRAL_FALSE_EXIT_COUNT = 11`
27. `ESTIMATED_AVOIDED_LOSS_OPPORTUNITY = APPROX_10,000`
28. `ESTIMATED_FALSE_EXIT_COST = 0_BENEFICIAL_THRESHOLD_COST; NEUTRAL_FALSE_EXIT_EXPOSURE_PRESENT`
29. `PROFIT_ALONE_USED_AS_SELL_AUTHORITY = NO`
30. `POSITION_NOTIONAL_USED_AS_DIRECTION_AUTHORITY = NO`
31. `NEW_COMPONENT_CREATED = NO`
32. `NEW_MODULE_CREATED = NO`
33. `NEW_MODEL_REQUIRED = NO_CONCRETE_EVIDENCE`
34. `NEW_PRODUCTION_THRESHOLD_REQUIRED = NO`
35. `MATERIALLY_NEW_STRATEGY_LOGIC_REQUIRED = NO_FOR_SHADOW; YES_IF_PROMOTED_TO_PRODUCTION_NOW`
36. `REFINED_FULL_EXIT_CANDIDATE_PRODUCTION_READINESS = SHADOW_ONLY`
37. `PRODUCTION_CHANGE_JUSTIFIED = NO`
38. `NEXT_RECOMMENDED_STEP = Implement or evaluate SHADOW-only refined BQ diagnostic labels inside the existing BQ/BO evidence path, with 52470 as the positive neighbor and 92420/99840/43880 plus neutral candidate captures as false-exit controls.`
39. `FINAL_JUDGMENT = PHASE32_CD_BQ_NON_PROMOTION_COMPOSITE_PARTIALLY_PIT_SEPARABLE_REFINED_FULL_EXIT_CANDIDATE_SHADOW_ONLY_PRODUCTION_NOT_JUSTIFIED`

## Final Judgment

```text
PHASE32_CD_BQ_NON_PROMOTION_COMPOSITE_PARTIALLY_PIT_SEPARABLE_REFINED_FULL_EXIT_CANDIDATE_SHADOW_ONLY_PRODUCTION_NOT_JUSTIFIED
```
