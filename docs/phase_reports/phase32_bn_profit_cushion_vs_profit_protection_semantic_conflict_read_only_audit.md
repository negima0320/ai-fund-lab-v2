# Phase32-BN - Profit Cushion vs Profit Protection Semantic Conflict READ-ONLY Audit

## Scope

Target run:

`runtime-test-historical-extended-smoke-20260831T003243720082Z`

Evaluation window fixed for BM/BJ/BK comparability:

`2022-10-03` through `2024-05-01`

This was a READ-ONLY diagnosis. No code, config, model, threshold, weight, Runtime state, Pending, Ledger, resume, recover, replay, or fresh-run action was performed.

Historical outcomes are used only as post-decision evaluation labels.

## BM Reproduction

BM methodology was reproduced from completed artifacts by regenerating BL shadow decisions in memory only. No shadow artifact was written into the run.

| Population | Count |
|---|---:|
| First lot-blocked REDUCE episodes | 343 |
| `SHADOW_FULL_EXIT` | 22 |
| `SHADOW_HOLD` | 23 |
| `SHADOW_INSUFFICIENT_EVIDENCE` | 298 |

Episode outcomes:

| Outcome | Count |
|---|---:|
| Harmful if held / Full EXIT helped | 138 |
| Beneficial if held / Full EXIT hurt | 62 |
| Neutral | 143 |

`SHADOW_INSUFFICIENT_EVIDENCE` composition:

| Outcome | Count |
|---|---:|
| Harmful | 118 |
| Beneficial | 52 |
| Neutral | 128 |

Unresolved Full EXIT counterfactual net:

`+331,100`

`BM_AMBIGUOUS_POPULATION_REPRODUCED = YES`

## Why BL Refuses To Decide

Conflict family classification for the 298 `SHADOW_INSUFFICIENT_EVIDENCE` episodes:

| Conflict family | Count | Harmful | Beneficial | Neutral | Net if Full EXIT | Profit present |
|---|---:|---:|---:|---:|---:|---:|
| profit cushion vs deterioration | 175 | 73 | 36 | 66 | +183,600 | 175 |
| supportive structure vs elevated risk | 119 | 44 | 15 | 60 | +148,600 | 4 |
| mixed hold/exit evidence | 4 | 1 | 1 | 2 | -1,100 | 0 |

Dominant conflict:

`profit_cushion_vs_deterioration`

Profit-cushion ambiguous subset:

- `179` insufficient episodes had profit cushion on the HOLD side.
- Their net Full EXIT counterfactual was `+172,100`.
- `30` episodes had profit cushion as the only HOLD-side evidence while at least two EXIT-side deterioration/risk signals were present.
- That narrower "profit-only blocked Full EXIT shape" had net `+79,110`.

## Profit Cushion Semantics

Architecture and PM contracts do not support treating profit cushion as independent HOLD authority.

Relevant current contract findings:

- Strategy Intelligence architecture says Profit Protection is evidence, not action authority.
- The Profit Protection matrix distinguishes:
  - meaningful profit + no deterioration + manageable risk -> HOLD
  - meaningful profit + decelerating continuation + rising risk -> profit protection evidence / stop ADD
  - large profit + material deterioration + high risk -> REDUCE evidence
- Phase31 F1C marks `strategy_intelligence_current_campaign_relative_return`, observed MFE, and observed giveback as SUPPORTING PIT lifecycle context, not primary action authority.
- PM severity evidence records campaign economics with role `SEVERITY_MODIFIER_NOT_PRIMARY_SELL_SIGNAL`.
- PM severity mapping explicitly avoids direct exit from profit state alone.

Therefore the intended meaning is:

`profit available to protect, conditional on continuation / deterioration evidence`

not:

`HOLD authority because the position is profitable`

`PROFIT_CUSHION_CURRENT_SEMANTIC = PROFIT_AVAILABLE_TO_PROTECT_CONDITIONAL_ON_CONTINUATION_EVIDENCE`

## BL Semantic Conflict

BL currently adds:

`current_campaign_relative_return > 0 -> hold_side_evidence: profit_cushion PRESENT`

That makes profit cushion an independent HOLD-side vote in the binary shadow layer. This is stricter than existing PM philosophy, where profit is context/modifier/protection evidence and must be interpreted with continuation and deterioration.

Read-only judgment:

`PROFIT_CUSHION_OVERWEIGHTED_AS_HOLD_AUTHORITY = YES`

This does not mean high profit should imply SELL. It means profit cushion should not independently force HOLD when PM already wants REDUCE and partial REDUCE is unrepresentable.

## 67310 Deep Dive

First blocked REDUCE:

`2023-04-24`

PIT evidence at the decision boundary:

| Field | Value |
|---|---|
| PM action | `REDUCE` |
| PM intensity | `LIGHT` |
| PM reason family | `risk_increased_but_trend_not_broken` |
| Current campaign relative return | `+50.0%` |
| Trend health | `WEAK` |
| Relative strength | `WEAK` |
| Participation quality | `WEAK` |
| Exhaustion risk | `MIXED` |
| Participation risk | `ELEVATED_RISK` |
| Risk vote count | `1` |
| Strong medium-term structure | `false` |
| Action score | `0.30458124`, diagnostic only |
| Canonical sell state | `WEAKENING_BUT_INTACT` |
| Exit confirmation | `DEFENSIVE_ONLY`, `soft_deterioration_not_terminal` |
| PM severity | `PM_SEVERITY_CAUTION` |
| PM severity economics role | `SEVERITY_MODIFIER_NOT_PRIMARY_SELL_SIGNAL` |
| Production action | `NO_ORDER` because partial REDUCE was lot-blocked |

BL evidence split:

| Side | Evidence |
|---|---|
| HOLD | `profit_cushion: PRESENT` |
| EXIT | `relative_strength: WEAK`, `trend_health: WEAK`, `participation_quality: WEAK`, `participation_risk: ELEVATED_RISK` |

BL returned:

`SHADOW_INSUFFICIENT_EVIDENCE`

Why:

The binary shadow rule requires multiple EXIT-side signals and no HOLD-side continuation evidence for `SHADOW_FULL_EXIT`. 67310 had multiple EXIT-side signals, but profit cushion was counted as HOLD-side evidence. That single profit-cushion vote blocked `SHADOW_FULL_EXIT`.

Semantic judgment:

The `+50%` profit cushion was valid PIT context, but under existing PM philosophy it was not valid independent HOLD authority. It was evidence that substantial profit existed and could require protection once continuation had deteriorated.

## Profit Cushion / Continuation Interaction

Ambiguous episodes split by categorical continuation context:

| Group | Definition | Count | Harmful | Beneficial | Neutral | Net if Full EXIT | Avg current return |
|---|---|---:|---:|---:|---:|---:|---:|
| P1 | profit + supportive trend and supportive relative strength | 40 | 9 | 16 | 15 | -105,190 | +5.08% |
| P2 | profit + weak/mixed trend or weak/mixed relative strength | 139 | 64 | 22 | 53 | +277,290 | +3.97% |
| P3 | no/negative profit + multiple deterioration signals | 119 | 45 | 14 | 60 | +159,000 | -2.19% |

Read:

- Profit cushion plus intact continuation often protects real winners/recoveries.
- Profit cushion plus weak/mixed continuation often marks profit at risk, not standalone HOLD authority.
- No/negative profit plus deterioration is directionally EXIT-side, but still contains neutral and beneficial cases, so it is not a production shortcut.

`PROFIT_CUSHION_REQUIRES_CONTINUATION_CONTEXT = YES`

## Winner Protection Controls

| Symbol | First blocked REDUCE | Profit cushion | Trend | Relative strength | Exhaustion | Strong medium | BL decision | Protection source |
|---|---:|---:|---|---|---|---|---|---|
| 62280 | 2023-12-22 | +9.51% | SUPPORTIVE | SUPPORTIVE | MANAGEABLE | true | `SHADOW_INSUFFICIENT_EVIDENCE` | Structural continuation plus cushion |
| 74270 | 2023-08-14 | +2.55% | WEAK | MIXED | MIXED | false | `SHADOW_INSUFFICIENT_EVIDENCE` | Ambiguity; profit-only protection is weak |
| 92270 | 2022-10-24 | -3.33% | SUPPORTIVE | SUPPORTIVE | ELEVATED_RISK | false | `SHADOW_INSUFFICIENT_EVIDENCE` | Structural relative/trend strength, not profit |
| 72140 | 2023-05-25 | +11.99% | MIXED | SUPPORTIVE | MANAGEABLE | false | `SHADOW_INSUFFICIENT_EVIDENCE` | Relative strength + manageable exhaustion + cushion |
| 83040 | 2024-02-21 | +3.00% | WEAK | MIXED | MIXED | false | `SHADOW_INSUFFICIENT_EVIDENCE` | Ambiguity; profit-only protection is weak |
| 69730 | 2022-11-04 | +5.73% | SUPPORTIVE | SUPPORTIVE | MANAGEABLE | true | `SHADOW_HOLD` | Clear structural continuation plus cushion |

Conclusion:

Beneficial winners were best protected when profit cushion coexisted with structural continuation: supportive relative strength, supportive trend, manageable exhaustion, or strong medium-term structure. Profit alone did not explain clean protection.

## Harmful Giveback Controls

| Symbol | First blocked REDUCE | Profit cushion | Trend | Relative strength | Exhaustion | Strong medium | BL decision | Read |
|---|---:|---:|---|---|---|---|---|---|
| 67310 | 2023-04-24 | +50.00% | WEAK | WEAK | MIXED | false | `SHADOW_INSUFFICIENT_EVIDENCE` | Profit cushion blocked Full EXIT despite weak continuation. |
| 62310 | 2023-05-01 | +1.39% | SUPPORTIVE | MIXED | MANAGEABLE | false | `SHADOW_INSUFFICIENT_EVIDENCE` | Mixed genuine structure and risk. |
| 74770 | 2023-10-04 | -6.47% | SUPPORTIVE | SUPPORTIVE | ELEVATED_RISK | true | `SHADOW_INSUFFICIENT_EVIDENCE` | Structural support conflicted with risk; not profit. |
| 34160 | 2024-03-05 | +7.72% | SUPPORTIVE | SUPPORTIVE | MANAGEABLE | true | `SHADOW_INSUFFICIENT_EVIDENCE` | Looks structurally protected at PIT; later harm is not predictable cleanly. |
| 36670 | 2023-06-16 | -3.13% | MIXED | MIXED | ELEVATED_RISK | false | `SHADOW_FULL_EXIT` | Captured; no HOLD-side evidence. |
| 51890 | 2023-04-14 | -7.93% | SUPPORTIVE | MIXED | ELEVATED_RISK | false | `SHADOW_INSUFFICIENT_EVIDENCE` | Trend support conflicted with risk. |

Harmful cases commonly show `profit still positive` plus deterioration, but not universally. The strongest profit-cushion semantic conflict is 67310.

## Large-Loss Tail Link

BM found 9 days with `DAILY_PNL <= -100,000`. Six had prior lot-blocked REDUCE on the dominant position, all tied to 67310.

| Tail date | Dominant symbol | Prior BL decision | Profit-cushion conflict involved |
|---|---|---|---|
| 2023-06-08 | 67310 | `SHADOW_INSUFFICIENT_EVIDENCE` | YES |
| 2023-06-26 | 67310 | `SHADOW_INSUFFICIENT_EVIDENCE` | YES |
| 2023-06-30 | 67310 | `SHADOW_INSUFFICIENT_EVIDENCE` | YES |
| 2023-07-26 | 67310 | `SHADOW_INSUFFICIENT_EVIDENCE` | YES |
| 2023-08-08 | 67310 | `SHADOW_INSUFFICIENT_EVIDENCE` | YES |
| 2023-08-17 | 67310 | `SHADOW_INSUFFICIENT_EVIDENCE` | YES |

All six prior-lot-blocked large-loss tail days are linked to the 67310 profit-cushion conflict.

If profit cushion were treated as protection context rather than independent HOLD evidence, the 67310 boundary would become semantically reconsiderable under existing EXIT-side deterioration evidence. This is not a production simulation and not a new rule acceptance.

## Shadow Refinement Feasibility

A next SHADOW refinement appears feasible without:

- new feature
- new model
- new fitted threshold
- future information

Supported semantic direction:

`profit cushion` should not independently force HOLD.

Instead:

- profit cushion + intact continuation = HOLD-side support
- profit cushion + deteriorating continuation = profit-at-risk / protection context

This aligns with current PM/Strategy Intelligence semantics and does not require selecting a profit threshold from historical outcomes.

Production change is not justified now. The next step should be another SHADOW-only refinement and evaluation, not direct activation.

## Required Final Answers

1. `BM_AMBIGUOUS_POPULATION_REPRODUCED`: YES. `343` episodes; `298` insufficient; insufficient net `+331,100`.
2. `DOMINANT_INSUFFICIENT_EVIDENCE_CONFLICT`: `profit_cushion_vs_deterioration`, `175 / 298` insufficient episodes.
3. `PROFIT_CUSHION_CURRENT_SEMANTIC`: PIT lifecycle/profit-protection context; not standalone HOLD authority.
4. `PROFIT_CUSHION_OVERWEIGHTED_AS_HOLD_AUTHORITY`: YES in BL shadow semantics.
5. `67310_AMBIGUITY_ROOT_CAUSE`: profit cushion was the only HOLD-side evidence and blocked Full EXIT classification despite multiple deterioration/risk signals.
6. `67310_PROFIT_CUSHION_BLOCKED_EXIT_SIDE_CLASSIFICATION`: YES.
7. `PROFIT_CUSHION_REQUIRES_CONTINUATION_CONTEXT`: YES.
8. `BENEFICIAL_WINNERS_PROTECTED_BY_PROFIT_OR_STRUCTURE`: primarily structure plus profit; not profit alone.
9. `HARMFUL_CASES_SHOW_PROFIT_WITH_DERIORATION`: YES for a material subset, strongest in 67310.
10. `PM_PHILOSOPHY_SUPPORTS_PROFIT_PROTECTION_OVER_STATIC_PROFIT_HOLD`: YES.
11. `LARGE_LOSS_TAIL_AMBIGUITY_LINKED_TO_PROFIT_CUSHION`: YES. Six prior-lot-blocked tail days are linked to 67310's profit-cushion conflict.
12. `NEW_FEATURE_REQUIRED`: NO.
13. `NEW_MODEL_REQUIRED`: NO.
14. `NEW_THRESHOLD_REQUIRED`: NO.
15. `SHADOW_SEMANTIC_REFINEMENT_JUSTIFIED`: YES.
16. `PRODUCTION_CHANGE_JUSTIFIED_NOW`: NO.
17. `NEXT_RECOMMENDED_STEP`: implement a SHADOW-only refinement that reclassifies profit cushion as context: HOLD support only when continuation remains intact; profit-at-risk context when continuation/risk evidence has deteriorated. Then rerun BM-style read-only economic and tail-loss evaluation.
18. `FINAL_JUDGMENT`: see below.

## Final Judgment

`PHASE32_BN_PROFIT_CUSHION_OVERWEIGHT_AS_HOLD_AUTHORITY_CONFIRMED_SHADOW_REFINEMENT_JUSTIFIED_PRODUCTION_CHANGE_NOT_JUSTIFIED`
