# Phase32-EI — EH ADD Blocked / Comparable-Negative Root-Cause READ-ONLY Audit

## Scope

This is a READ-ONLY audit of the Phase32-EH PC Security Opportunity SHADOW consumer output.

No Production code, SHADOW code, runtime state, Pending state, Ledger state, source configuration, fresh-run, resume, recover, replay, or long Historical execution was performed in Phase32-EI.

Historical outcome, future price, future return, future regime, future MFE/MAE, and PnL were not used to justify any Production decision.

## Evidence Used

- EH accepted analysis output: `reports/runtime_tests/analysis/phase32_eh_pc_security_opportunity_shadow_20260903T014000`
- EH report: `docs/phase_reports/phase32_eh_pc_security_opportunity_shadow_consumer_production_preservation_audit.md`
- EG/EH SHADOW source contract evidence in `src/ai_fund_lab_v2/strategy/marginal_capital_value.py`
- Source run referenced by EH manifest: `runtime-test-historical-extended-smoke-20260902T060955933565Z`
- Source identity recorded by EH manifest: `1f64f49ee9a8dd48280007e4df656e5f03e231ca`

EH evidence confirms:

- `business_day_count = 264`
- `diagnostic_row_count = 7831`
- `add_unknown_116_total = 116`
- `add_unknown_116_pc_shadow_reclassification = {BLOCKED: 54, COMPARABLE_NEGATIVE: 62}`
- `authoritative_consumer_count = 0`
- `production_pc_path_unchanged = PASS`
- `buy_new_production_equivalence = PASS`
- `reentry_production_equivalence = PASS`
- `future_information_used = false`
- `historical_outcome_used = false`
- `target_run_mutated = false`
- `runtime_state_mutated = false`

## Executive Finding

The EH ADD UNKNOWN population is not blocked because Security Opportunity evidence is missing. EG made the intrinsic security evidence complete, and EH proves the PC SHADOW consumer can observe it.

The remaining suppression is caused by ADD-increment authority, not by security visibility:

- all 116 rows have complete Security Opportunity evidence;
- all 116 rows are top-ranked or otherwise visible held-security opportunities in the EH diagnostic population;
- all 116 rows have `target_weight <= current_weight`;
- all 116 rows have `next_executable_quantity = 0`;
- 115 of 116 have headroom available, so portfolio headroom is not the dominant blocker.

Therefore, the dominant current root cause is that the current Production PC ADD contract interprets ADD through current target/current exposure and accepted executable increment mechanics. It does not yet represent a separate "held security is strong, low/mid exposure, next marginal lot deserves capital" authority.

This is a residual winner-capitalization representation gap, not proof that Production should immediately buy these rows.

## ADD_BLOCKED_54_ROOT_CAUSE_PROFILE

The 54 `BLOCKED` rows are hard blocked before they can become comparable marginal capital competitors.

Primary profile from the EH decomposition:

| Root cause | Count | Meaning |
| --- | ---: | --- |
| `BQ_BLOCKS_INCREMENT` | 37 | Buy Quality / ADD quality gate does not authorize an incremental ADD. |
| `ENTRY_NO_ADD` | 16 | Entry/ADD admission semantics do not authorize ADD. |
| `SAFETY_OR_STRATEGY_CAP` | 1 | Strategy cap / safety-like bound blocks the increment. |

Secondary profile across the total ADD UNKNOWN population:

- `TARGET_LE_CURRENT = 116`
- `NEXT_QTY_ZERO = 116`
- `DESIRED_INC_ZERO = 92`
- `OPPORTUNITY_COST_NEW_SUPERIOR = 84`
- `EXPECTED_EDGE_WEAKENING = 72`
- `BQ_BUY_WAIT = 37`
- `ENTRY_NO_ADD = 18`

Interpretation:

`BLOCKED` rows are not "strong evidence but accidentally ignored" cases. They are rows where the ADD path lacks current positive increment authorization, most often because BQ or entry/ADD semantics explicitly block or withhold the increment.

## ADD_NEGATIVE_62_ROOT_CAUSE_PROFILE

The 62 `COMPARABLE_NEGATIVE` rows are complete enough to compare, but the next ADD unit loses under the current EH shadow comparison.

Primary profile:

| Root cause | Count | Meaning |
| --- | ---: | --- |
| `EXPECTED_EDGE_WEAKENING` | 42 | The incumbent ADD edge evidence is weakening. |
| `OPPORTUNITY_COST_LOSES_TO_NEW` | 20 | The next ADD unit loses to available NEW opportunity cost evidence. |

Common structural facts:

- `target_weight <= current_weight`: 62 of 62
- `next_executable_quantity = 0`: 62 of 62

Interpretation:

The negative classification is not caused by missing Security Opportunity evidence. It is produced after security evidence becomes observable and the ADD increment is evaluated as a next capital unit. The ADD side remains negative because current target/current exposure and marginal ADD evidence do not produce a positive executable next-lot authority.

## STRONG_SECURITY_LOW_EXPOSURE_NEGATIVE_INCREMENT_CASES

Classification: `PRESENT_BUT_NOT_CLEAN_UNDERCAPITALIZED`

A material subset of `COMPARABLE_NEGATIVE` rows is strong, visible, low/mid exposure, and has headroom:

- `strong_low_neg_count = 30` using top-rank / held visible / current weight <= 6% / headroom available / no hard-block criteria.
- However, no clean undercapitalized row was found where all of the following were true at once:
  - strong/top-ranked security evidence;
  - low/mid current exposure;
  - headroom available;
  - BQ/entry did not block ADD;
  - expected edge improving;
  - opportunity cost PASS;
  - positive target expansion or positive next executable quantity.

All observed strong/low negative rows still have `target_weight == current_weight` and `next_executable_quantity = 0`, and each is explained by weakening ADD edge, NEW opportunity cost superiority, BQ withholding, or entry/ADD withholding.

This is a capitalization-design signal, not a standalone correctness defect.

## STRONG_SECURITY_ALREADY_WELL_SIZED_CONTROLS

The EH negative population is "already well-sized" in the current Production PC target sense:

- 62 of 62 `COMPARABLE_NEGATIVE` rows have `target_weight <= current_weight`.

This does not mean every row is large in absolute portfolio weight. Position-size buckets across all 116 ADD UNKNOWN rows:

| Current weight bucket | Count |
| --- | ---: |
| `<3%` | 29 |
| `3-6%` | 21 |
| `6-9%` | 34 |
| `>=9%` | 32 |

So the current target authority treats many low/mid exposure positions as already at target. That is the exact residual design tension: target equality can suppress next-lot capitalization even when the intrinsic security remains strong.

Representative controls:

- `99840` on 2022-11-07: rank 4, current/target about 14.8%, expected edge improving, NEW buy superior, `COMPARABLE_NEGATIVE`.
- `99840` on 2022-11-09: rank 3, current/target about 15.3%, expected edge improving, NEW buy superior, `COMPARABLE_NEGATIVE`.
- `83060` on 2023-01-24: rank 1, current/target about 7.8%, expected edge weakening, opportunity cost PASS, `COMPARABLE_NEGATIVE`.

## WEAKENING_INCUMBENT_NEGATIVE_BEHAVIOR

Weakening incumbent evidence remains a major and legitimate negative behavior in the current SHADOW explanation:

- `EXPECTED_EDGE_WEAKENING = 72` across the 116 rows.
- It is the primary explanation for 42 of 62 `COMPARABLE_NEGATIVE` rows.
- It also appears as a secondary explanation in blocked rows.

This behavior should be preserved. The fact that Security Opportunity is complete does not mean a held security's next ADD unit should ignore incumbent deterioration or weakening marginal evidence.

## 94320_EH_NEGATIVE_BLOCKED_DEEP_DIVE

`94320` is the largest single winner-control contributor:

- EH rows: 82
- ADD UNKNOWN rows: 33
- Reclassification: 19 `BLOCKED`, 14 `COMPARABLE_NEGATIVE`

Profile:

- All 94320 ADD UNKNOWN rows have headroom available.
- All have `target_weight == current_weight`.
- All have `next_executable_quantity = 0`.
- The campaign repeatedly appears as high-rank/visible but does not receive positive ADD increment authority.

Representative path:

| Date | Class | Rank | Approx weight | Key explanation |
| --- | --- | ---: | ---: | --- |
| 2022-10-19 | `COMPARABLE_NEGATIVE` | 1 | 3.1% | BQ reduced, entry reduced, expected edge weakening, no positive desired increment. |
| 2022-10-20 | `COMPARABLE_NEGATIVE` | 1 | 3.1% | Same campaign, expected edge weakening, no positive desired increment. |
| 2022-10-31 | `BLOCKED` | 1 | 3.1% | Entry `NO_ADD`, expected edge weakening. |
| 2022-11-02 | `BLOCKED` | 1 | 4.5% | BQ `BUY_WAIT`, expected edge weakening. |
| 2023-01-24 | `BLOCKED` | 2 | 2.6% | BQ `BUY_WAIT`; ADD allowed at entry layer but BQ blocks increment. |
| 2023-02-07 | `COMPARABLE_NEGATIVE` | 3 | 3.7% | BQ full, entry reduced, expected edge weakening, NEW buy superior. |
| 2023-02-14 | `COMPARABLE_NEGATIVE` | 1 | 4.9% | BQ reduced, expected edge weakening. |
| 2023-02-28 | `BLOCKED` | 2 | 7.9% | BQ `BUY_WAIT`, expected edge improving, NEW buy superior. |
| 2023-03-07 | `COMPARABLE_NEGATIVE` | 2 | ~8% | Expected edge improving, NEW buy superior. |
| 2023-03-13 | `BLOCKED` | 4 | ~8% | BQ `BUY_WAIT`, expected edge improving, NEW buy superior. |

94320 therefore demonstrates both sides of the current ADD suppression:

1. The opportunity remains visible and often high ranked.
2. The next ADD increment remains blocked or negative because marginal ADD authority is not positive.

## INCUMBENT_NEGATIVE_CONTROL_COMPARISON

Winner-control symbols show the same pattern, not a 94320-only artifact:

| Symbol | ADD UNKNOWN | BLOCKED | COMPARABLE_NEGATIVE | Primary profile |
| --- | ---: | ---: | ---: | --- |
| 94320 | 33 | 19 | 14 | BQ blocks, edge weakening, NEW superior. |
| 94340 | 16 | 6 | 10 | Edge weakening and BQ blocks dominate. |
| 99840 | 15 | 9 | 6 | BQ blocks and edge weakening dominate. |
| 83060 | 13 | 6 | 7 | BQ blocks and edge weakening dominate. |
| 43880 | 12 | 3 | 9 | Edge weakening and NEW superior dominate. |
| 54010 | 5 | 1 | 4 | NEW superior dominates. |

`weak_add_negative_controls_preserved = PASS` in the EH summary. Existing weak/negative ADD controls remain negative or blocked.

## 2023_JUN_SEP_ADD_SUPPRESSION_ROOT_CAUSE_PROFILE

EH official Jun-Sep 2023 profile:

| Class | Count |
| --- | ---: |
| `BLOCKED` | 14 |
| `COMPARABLE_NEGATIVE` | 4 |
| `INSUFFICIENT` | 2 |

For the 16 Jun-Sep rows inside the ADD UNKNOWN decomposed subset:

| Primary root cause | Count |
| --- | ---: |
| `BQ_BLOCKS_INCREMENT` | 7 |
| `ENTRY_NO_ADD` | 5 |
| `EXPECTED_EDGE_WEAKENING` | 2 |
| `OPPORTUNITY_COST_LOSES_TO_NEW` | 2 |

Representative Jun-Sep rows:

- 2023-06-01 `59550`: `BLOCKED`, rank 5, current/target about 4.2%, entry `NO_ADD`, expected edge weakening, NEW buy superior.
- 2023-06-14 `99840`: `BLOCKED`, rank 5, current/target about 9.2%, BQ `BUY_WAIT`, expected edge improving, NEW buy superior.
- 2023-06-21 `40520`: `COMPARABLE_NEGATIVE`, rank 5, current/target about 8.4%, expected edge weakening, opportunity cost PASS.
- 2023-06-27 `40520`: `COMPARABLE_NEGATIVE`, rank 4, current/target about 8.2%, expected edge improving, NEW buy superior.
- 2023-09-27 `94340`: `COMPARABLE_NEGATIVE`, rank 4, current/target about 2.9%, expected edge improving, NEW buy superior.
- 2023-09-28 `94340`: `BLOCKED`, rank 3, current/target about 2.9%, BQ `BUY_WAIT`.

June-Sep suppression is therefore not a single cap defect. It is a combined BQ/entry/edge/opportunity-cost/current-target equality phenomenon.

## ADD_NEGATIVE_POSITION_SIZE_CONTEXT_PROFILE

Position-size context shows that ADD suppression is not restricted to overlarge incumbents:

- 50 of 116 rows are below 6% current weight.
- 66 of 116 rows are 6% or above.
- 115 of 116 have headroom available.

The common suppressor is not absolute size. It is that current Production target authority already places the next ADD increment at zero.

## ADD_SUPPRESSION_SECURITY_STRENGTH_PROFILE

Security Opportunity evidence is complete for the EH ADD UNKNOWN population.

Across the 116 rows:

- Security evidence completeness is `COMPLETE`.
- Security Opportunity visibility is present.
- Diagnostic ranks fall in the top observed opportunity set.
- Production consumer count remains zero.

However, Security Opportunity is intentionally action-neutral. It excludes ADD-specific sizing, target-weight authority, quantity authority, and current-position duplication from intrinsic attractiveness. That design is correct for EG/EH. The missing piece is not "security strength"; it is the ADD next-increment translation.

## ADD_OPPORTUNITY_COST_NEGATIVE_TRUTH_PROFILE

Opportunity cost is partly true negative and partly structural.

True alternative-superiority signal:

- `OPPORTUNITY_COST_LOSES_TO_NEW = 20` primary `COMPARABLE_NEGATIVE` rows.
- `OPPORTUNITY_COST_NEW_SUPERIOR = 84` as a broader secondary signal.

Structural ADD-side suppression:

- all 62 negative rows have `target_weight <= current_weight`;
- all 62 negative rows have `next_executable_quantity = 0`;
- therefore some rows lose to NEW not because the held security is intrinsically weak, but because the ADD side offers no positive executable next unit under the current target/increment contract.

This supports further SHADOW design around marginal ADD value representation, not immediate Production promotion.

## COMPARABLE_NEGATIVE_AUTHORITY_TRACE

Canonical authority trace:

1. EG builds `security_opportunity_evidence.v1`.
   - Intrinsic security evidence is action-neutral.
   - Position relationship is recorded separately.
   - `authoritative_consumer_count = 0`.
2. EH builds `pc_security_opportunity_shadow_consumer.v1`.
   - It consumes Security Opportunity evidence only diagnostically.
   - It preserves Production PC path and BUY_NEW/REENTRY equivalence.
3. EH reclassifies Production ADD UNKNOWN rows.
   - If hard ADD increment authority is absent, the row becomes `BLOCKED`.
   - If evidence is complete but next ADD unit loses to weakening edge or opportunity cost, the row becomes `COMPARABLE_NEGATIVE`.
4. No downstream Production planning, sizing, ordering, reservation, or runtime consumer uses this SHADOW output.

The negative classification is therefore canonical as a diagnostic explanation, not as Production authority.

## RESIDUAL_WINNER_CAPITALIZATION_GAP

Classification: `MATERIAL_BUT_NOT_YET_PRODUCTION_DEFECT`

There is a real residual winner-capitalization gap:

- complete action-neutral Security Opportunity evidence exists;
- many held winners remain visible and strong;
- some are low/mid exposure with headroom;
- current ADD target/increment authority still materializes zero next executable quantity.

But the same evidence also shows legitimate negative controls:

- BQ `BUY_WAIT`;
- entry `NO_ADD`;
- expected edge weakening;
- NEW opportunity cost superiority;
- current Production target already reached.

Therefore a Production repair is not justified by EI alone. The next safe step is a SHADOW-only design that separates:

- intrinsic held-security strength;
- current-position size adequacy;
- next-lot feasibility;
- incumbent deterioration;
- opportunity cost versus NEW;
- explicit positive ADD increment authority.

## PRODUCTION_REPAIR_JUSTIFIED

`CONDITIONAL`

No immediate Production repair is justified from EI alone.

Conditional future repair may be justified only after a SHADOW contract proves that a held security has:

- complete intrinsic security opportunity evidence;
- low or moderate exposure relative to a canonical size context;
- available headroom;
- no BQ/entry hard block;
- no unresolved deterioration;
- opportunity cost competitive with NEW;
- positive next-lot feasible increment;
- preserved G129 increment authority semantics.

## NARROWEST_SAFE_REPAIR_BOUNDARY

Recommended boundary:

`SHADOW_ONLY_MARGINAL_ADD_VALUE_REPRESENTATION_AND_POSITION_SIZE_CONTEXT`

Do not change Production PC target weights, ranking, thresholds, BQ gates, entry gates, cash/risk pacing, or Runtime planning from EI.

The narrowest safe next step is to design/evaluate an ADD-specific SHADOW contract for positive next-lot authority that can distinguish:

- truly undercapitalized strong incumbent;
- already-at-target incumbent;
- weakening incumbent;
- BQ/entry blocked incumbent;
- incumbent that loses to NEW opportunity cost;
- lot/price infeasible next increment.

## CURRENT_PRODUCTION_BEHAVIORS_TO_PRESERVE

Preserve:

- Production PC path unchanged.
- BUY_NEW production equivalence.
- REENTRY production equivalence.
- G129 BUY_ADD order-increment scoped semantics.
- KI-006 zero ADD preservation.
- BQ `BUY_WAIT` as a hard no-positive-increment signal.
- Entry `NO_ADD` / reduced ADD semantics.
- Expected-edge weakening as a legitimate negative control.
- NEW opportunity cost competition.
- Fail-closed behavior for incomplete or malformed authority.
- SHADOW-only non-authoritative Security Opportunity consumer status.

## Required Final Answers

- `ADD_BLOCKED_54_ROOT_CAUSE_PROFILE`: 37 `BQ_BLOCKS_INCREMENT`, 16 `ENTRY_NO_ADD`, 1 strategy/safety cap-like block.
- `ADD_NEGATIVE_62_ROOT_CAUSE_PROFILE`: 42 `EXPECTED_EDGE_WEAKENING`, 20 `OPPORTUNITY_COST_LOSES_TO_NEW`; all 62 have `target_weight <= current_weight` and `next_executable_quantity = 0`.
- `STRONG_SECURITY_LOW_EXPOSURE_NEGATIVE_INCREMENT_CASES`: present as diagnostic candidates, but no clean undercapitalized positive-next-lot case was confirmed.
- `STRONG_SECURITY_ALREADY_WELL_SIZED_CONTROLS`: confirmed in current Production target sense; all 62 negative rows are at or above current target, though not all are high absolute weight.
- `WEAKENING_INCUMBENT_NEGATIVE_BEHAVIOR`: confirmed and should be preserved.
- `94320_EH_NEGATIVE_BLOCKED_DEEP_DIVE`: 33 ADD UNKNOWN rows; 19 blocked, 14 comparable-negative; repeated high-rank visibility with zero next executable quantity.
- `INCUMBENT_NEGATIVE_CONTROL_COMPARISON`: confirmed across 94320, 94340, 99840, 83060, 43880, and 54010.
- `2023_JUN_SEP_ADD_SUPPRESSION_ROOT_CAUSE_PROFILE`: mainly BQ blocks and entry no-add, with smaller edge-weakening and NEW-superior negative groups.
- `ADD_NEGATIVE_POSITION_SIZE_CONTEXT_PROFILE`: suppression spans low, mid, and high weights; current target equality is the common suppressor.
- `ADD_SUPPRESSION_SECURITY_STRENGTH_PROFILE`: Security Opportunity evidence is complete; ADD increment authority remains non-positive.
- `ADD_OPPORTUNITY_COST_NEGATIVE_TRUTH_PROFILE`: mixed; 20 primary true NEW-superior negatives, 84 secondary NEW-superior signals, plus structural ADD-side zero-increment suppression.
- `COMPARABLE_NEGATIVE_AUTHORITY_TRACE`: EG action-neutral Security Opportunity -> EH diagnostic PC consumer -> ADD UNKNOWN reclassification; no Production consumer.
- `RESIDUAL_WINNER_CAPITALIZATION_GAP`: material representation gap remains, but not yet a mandatory Production correctness defect.
- `PRODUCTION_REPAIR_JUSTIFIED`: `CONDITIONAL`.
- `NARROWEST_SAFE_REPAIR_BOUNDARY`: SHADOW-only marginal ADD value / position-size context contract before any Production promotion.
- `CURRENT_PRODUCTION_BEHAVIORS_TO_PRESERVE`: listed above.
- `PRODUCTION_CHANGE_EXECUTED`: `NO`.
- `SHADOW_CHANGE_EXECUTED`: `NO` in Phase32-EI.
- `TARGET_RUN_MUTATED`: `NO`.
- `RUNTIME_STATE_MUTATED`: `NO`.
- `LONG_RUNTIME_EXECUTED`: `NO`.
- `FUTURE_OUTCOME_USED`: `NO`.
- `HISTORICAL_PNL_USED_FOR_DECISION`: `NO`.
- `NEXT_RECOMMENDED_STEP`: Design a SHADOW-only positive ADD next-lot authority / position-size adequacy contract; do not promote Production yet.

## Final Judgment

`PHASE32_EI_EH_ADD_BLOCKED_NEGATIVE_ROOT_CAUSE_IDENTIFIED_CONDITIONAL_SHADOW_ONLY_ADD_INCREMENT_REPRESENTATION_GAP_NO_PRODUCTION_CHANGE`
