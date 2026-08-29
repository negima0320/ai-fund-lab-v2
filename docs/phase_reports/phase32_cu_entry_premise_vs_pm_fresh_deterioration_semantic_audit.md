# Phase32-CU Entry Premise vs PM Fresh Deterioration Semantic Audit

## Executive Summary

This was a READ-ONLY audit. No Production code, config, threshold, runtime state, fresh-run, resume, replay, or backtest was changed or executed.

Run audited:

```text
runtime-test-historical-extended-smoke-20260829T060203037185Z
```

Coverage:

```text
2022-10-03 through 2022-10-07
```

Post-CS early REDUCE/EXIT is not explained by a missing one-lot authority anymore. The priority Day-0 campaigns all entered with explicit `CONTINUATION_WITH_CAUTION` premise. Most early-exit campaigns had known entry risk already present at T0: weak trend health, weak participation, elevated regime/participation risk, reduced Buy Quality allocation, and low or negative opportunity score. PM then used same-family sell evidence on T+1/T+2, often while continuation/downside statuses were still `PASS`.

The key semantic defect is not that PM exits are all wrong. It is that PM does not appear to have a full, explicit entry-premise comparison contract, so it cannot distinguish cleanly between:

- risk known and priced into a reduced/caution entry,
- genuinely fresh post-entry deterioration,
- hard failure that must remain sell-authoritative.

`94340` is the control: it also entered as `CONTINUATION_WITH_CAUTION`, but with rank 3, HIGH quality, manageable participation risk, FULL-equivalent target, and PM HOLD/ADD evidence from T+1 onward. PM can identify strong survivor evidence, but for weaker caution entries it often treats already-known risk families as immediate sell pressure.

## Entry Premise

All priority Day-0 entries had `entry_admission_state = CONTINUATION_WITH_CAUTION` and `entry_admission_action = BUY_NEW_REDUCED_ONLY`. The system knowingly bought reduced/caution entries, not clean full-conviction entries.

| Symbol | Rank | Opportunity score | BQ action | BQ score / band | T0 known premise | Quality target | Final target | T0 technical context |
| --- | ---: | ---: | --- | --- | --- | ---: | ---: | --- |
| `37820` | 6 | -0.1603 | `REDUCED_ALLOCATION_ONLY` | 0.7166 / MEDIUM | weak trend, mixed relative strength, weak participation/persistence, elevated regime and participation risk | 2.4103% | 2.4103% | 1d +3.03%, 5d -2.86%, 20d -2.86%, close/MA20 0.858 |
| `67860` | 37 | -0.4478 | `REDUCED_ALLOCATION_ONLY` | 0.4828 / LOW | weak trend/relative strength/participation/persistence, elevated regime and participation risk | 1.6238% | 1.6238% | 1d +5.26%, 5d -3.61%, 20d -13.98%, close/MA20 0.871 |
| `76470` | 26 | -0.3436 | `REDUCED_ALLOCATION_ONLY` | 0.5763 / MEDIUM | weak trend/relative strength/participation/persistence, elevated regime and participation risk, 3 risk votes | 1.9385% | 1.9385% | 1d -3.57%, 5d -3.57%, 20d -3.57%, close/MA20 0.969 |
| `82540` | 35 | -0.4344 | `REDUCED_ALLOCATION_ONLY` | 0.5131 / LOW | weak trend, supportive relative strength, weak participation, mixed persistence, elevated risk | 1.7260% | 0.0000%; one-lot authority admitted | 1d +1.34%, 5d +1.00%, 20d +5.96%, close/MA20 0.993 |
| `89180` | 25 | -0.3390 | `REDUCED_ALLOCATION_ONLY` | 0.5853 / MEDIUM | weak trend/relative strength/participation/persistence, elevated regime and participation risk, 3 risk votes | 1.9686% | 1.9686% | 1d -10.00%, 5d -10.00%, 20d -10.00%, close/MA20 0.891 |
| `96100` | 41 | -0.4580 | `REDUCED_ALLOCATION_ONLY` | 0.4712 / LOW | weak trend/relative strength/participation/persistence, elevated regime and participation risk, 3 risk votes | 1.5850% | 0.0000%; one-lot authority admitted | 1d +11.86%, 5d -1.00%, 20d -16.81%, close/MA20 0.958 |
| `33500` | 29 | -0.3840 | `REDUCED_ALLOCATION_ONLY` | 0.5577 / MEDIUM | supportive trend/relative strength, weak participation, mixed persistence, elevated regime/participation risk, 4 risk votes | 1.8760% | 1.8760% | 1d 0.00%, 5d +1.98%, 20d +31.11%, close/MA20 1.043 |
| `94340` | 3 | +0.2403 | `REDUCED_ALLOCATION_ONLY` label, but target not reduced / HIGH | 0.7659 / HIGH | weak trend/relative strength, supportive participation, manageable participation risk, 2 risk votes | 3.3636% | 3.3636% | 1d -0.41%, 5d -3.09%, 20d -5.57%, close/MA20 0.964 |

The main premise: the system intentionally bought multiple weak/risky continuation setups with reduced size. It did not buy them because the risk evidence was absent.

## PM T+1 to T+3 Evidence

| Symbol | First PM action | PM reason | PM semantic state | Continuation / downside | Current return | Classification |
| --- | --- | --- | --- | --- | ---: | --- |
| `37820` | 10/04 EXIT | `trend_and_opportunity_broken` | `EXIT_GRADE`, `WORSENING`, `PM_SEVERITY_EXIT_CANDIDATE` | PASS / PASS | +3.03% | AMBIGUOUS; same risk family as entry premise, but PM states EXIT_GRADE |
| `67860` | 10/04 EXIT | `trend_and_opportunity_broken` | `EXIT_GRADE`, `WORSENING`, `PM_SEVERITY_EXIT_CANDIDATE` | PASS / PASS | +6.67% | AMBIGUOUS; same risk family as entry premise, profitable and downside PASS |
| `76470` | 10/04 EXIT | `weak_hold_score` | `EXIT_GRADE`, `WORSENING`, `PM_SEVERITY_EXIT_CANDIDATE` | PASS / PASS | 0.00% | ENTRY_PREMISE_ALREADY_KNOWN / AMBIGUOUS |
| `82540` | 10/04 REDUCE, 10/05 REDUCE | `risk_increased_but_trend_not_broken` | 10/04 `WEAKENING_BUT_INTACT`, 10/05 `PERSISTENT_DETERIORATION` | PASS / PASS | +1.34% then +1.34% pre-action | FRESH_DETERIORATION by persistence on 10/05; 10/04 is first-observation caution |
| `89180` | 10/04 EXIT | `hard_stop_current_return` | `EXIT_GRADE`, `WORSENING`, `PM_SEVERITY_EXIT_CANDIDATE` | PASS / PASS | -10.00% by PM price/cost | HARD_FAILURE |
| `96100` | 10/04 EXIT | `trend_and_opportunity_broken` | `EXIT_GRADE`, `WORSENING`, `PM_SEVERITY_EXIT_CANDIDATE` | PASS / PASS | +10.00% by PM price/cost | AMBIGUOUS; entry had weak/elevated risk, but PM asserts trend/edge break |
| `33500` | 10/04 REDUCE, 10/05 REDUCE, 10/06 REDUCE/sold | `risk_increased_but_trend_not_broken` | 10/04-05 `WEAKENING_BUT_INTACT`, 10/06 `PERSISTENT_DETERIORATION` | PASS / PASS | -5.24%, -3.57%, -3.57% | FRESH_DETERIORATION / TRUE_BREAKDOWN by 10/06; initial REDUCE partly known-risk reuse |
| `94340` | 10/04 HOLD, 10/05-07 ADD intent | HOLD: `positive_expected_edge|downside_risk_contained`; ADD: `strong_trend_continuation|opportunity_rank_still_high|no_loss_averaging` | `HEALTHY_OR_RECOVERING`, `RECOVERED`, `PM_SEVERITY_NORMAL` | PASS / PASS | +2.63%, then +2.35%, +0.53%, +0.19% | IMPROVEMENT / survivor control |

Important observed PM pattern:

- PM deterioration dimensions repeatedly include nested states `ELEVATED_RISK` and `WEAK`.
- Those states were already present in the T0 entry premise for most priority early exits.
- PM artifacts still report `strategy_intelligence_continuation_quality_status = PASS` and `strategy_intelligence_downside_risk_status = PASS` for the T+1 exits/reduces.
- The PM severity layer preserves baseline PM action with `existing_pm_exit_grade` for T+1 full exits, rather than proving a fresh delta from the T0 accepted premise.

## Fresh Deterioration Count

Priority non-control campaigns: 7.

| Classification | Count | Symbols |
| --- | ---: | --- |
| HARD_FAILURE | 1 | `89180` |
| FRESH_DETERIORATION / TRUE_BREAKDOWN by persistence | 2 | `82540`, `33500` |
| ENTRY_PREMISE_ALREADY_KNOWN / AMBIGUOUS | 4 | `37820`, `67860`, `76470`, `96100` |

Interpretation:

- One hard failure is valid and should remain protected: `89180`.
- Two reduce paths become more defensible after persistence appears (`82540`, `33500`), though their first REDUCE still reuses entry-known risk families.
- Four T+1 EXITs are not cleanly separable from known entry caution in the artifacts. They may be valid PM decisions, but the available contract does not show the fresh-deterioration delta against the accepted entry premise.

## Entry Premise Availability To PM

PM input/source artifacts on 2022-10-04 include:

- `strategy_intelligence.json`: `COMPATIBLE_PRODUCTION_EVIDENCE`
- `.runtime/persistent_ledger/state.json`: position lifecycle `PASS`
- `technical_features.json`: `PASS`
- opportunity summary: `PASS`
- position management decisions: `PASS`
- market context / corporate event / portfolio policy: `COMPATIBLE_NOT_CONNECTED`

What is present:

- current position lifecycle,
- current campaign age,
- current return / MFE / giveback,
- current technical features,
- current strategy intelligence continuation/downside,
- PM action/reason and canonical sell semantics.

What is not materially present as a PM comparison authority:

- Day-0 entry admission action/state as an explicit baseline premise,
- Day-0 Buy Quality action/score/band as an accepted-risk baseline,
- Day-0 entry consumed-evidence risk vector,
- a same-campaign `known_at_entry` vs `new_since_entry` deterioration diff.

Therefore:

```text
PM can observe current weakness/risk.
PM cannot prove, from the materialized contract, that the weakness is fresh rather than already accepted at entry.
```

This is an entry-premise lineage migration gap, not a request to weaken hard stops or add minimum holding days.

## Control: 94340

`94340` demonstrates the intended positive path:

- T0 rank 3 and positive opportunity score.
- Buy Quality score 0.7659 / HIGH.
- Participation risk `MANAGEABLE`, not `ELEVATED_RISK`.
- Final target remained 3.3636%.
- PM T+1: HOLD with `positive_expected_edge|downside_risk_contained`.
- PM T+2/T+3/T+4: ADD intent from `strong_trend_continuation|opportunity_rank_still_high|no_loss_averaging`.
- Canonical sell state remains `HEALTHY_OR_RECOVERING`; PM severity `PM_SEVERITY_NORMAL`; recovery state `RECOVERED`.

The early-exit group differs not just by later price action but by entry premise quality: lower rank, negative opportunity, reduced allocation, weaker relative strength/participation/persistence, and elevated risk. This supports preserving hard PM protection while adding explicit context so PM does not treat accepted entry noise as new deterioration.

## Answers To Required Questions

1. Early EXITs that are clearly fresh deterioration: 2 partial cases by persistence (`82540`, `33500`) plus 1 hard failure (`89180`). Four T+1 full exits are ambiguous against known entry caution.

2. Known entry caution reused as exit evidence: PARTIAL/YES. `ELEVATED_RISK` and `WEAK` risk-family evidence appears in both T0 entry premise and T+1 PM deterioration dimensions for most early-exit campaigns.

3. PM has partial context only. It sees current lifecycle and same-day evidence, but not a full entry-premise baseline.

4. Entry premise lineage migration gap: YES. The PM materialized artifact does not carry a structured entry premise diff.

5. The issue is more semantic context absence than simple PM threshold sensitivity. PM may be sensitive, but the first repair boundary is to materialize `known_at_entry` versus `fresh_since_entry` before changing thresholds.

6. Hard stops/true breakdown can be preserved. `89180` should remain a hard-failure exit. `33500`/`82540` show persistence-based deterioration that can remain sell-authoritative if explicitly fresh/persistent. The repair should only prevent accepted entry caution from becoming sell evidence without a fresh-delta contract.

## Defect / No-Defect Judgment

Defect class:

```text
ENTRY_PM_CONTEXT_MIGRATION_GAP
```

This is not a proof that every early sell is incorrect. It is a proof that the artifacts do not establish the semantic distinction required by the investment lifecycle:

```text
Entry accepted caution with reduced size
!=
fresh post-entry deterioration requiring REDUCE/EXIT
```

Production repair is justified as a semantic materialization repair: PM should receive or reconstruct entry-premise evidence and classify deterioration as `KNOWN_AT_ENTRY`, `FRESH_DETERIORATION`, `HARD_FAILURE`, `TRUE_BREAKDOWN`, or `AMBIGUOUS_REVIEW_REQUIRED`. No minimum holding period or threshold tuning is recommended here.

## Final Judgments

PHASE32_CU_ENTRY_PREMISE_AVAILABLE_TO_PM = PARTIAL

PHASE32_CU_FRESH_DETERIORATION_SEPARABLE = PARTIAL

PHASE32_CU_KNOWN_CAUTION_REUSED_AS_EXIT_EVIDENCE = PARTIAL

PHASE32_CU_HARD_FAILURE_EXITS_VALID = YES

PHASE32_CU_PM_OVERSENSITIVE = PARTIAL

PHASE32_CU_ENTRY_PM_CONTEXT_MIGRATION_GAP = YES

PHASE32_CU_PRIMARY_EARLY_EXIT_CAUSE = entry-known caution/risk is not explicitly separated from fresh deterioration in PM; valid hard failure exists for 89180, persistence-based deterioration exists for 33500/82540, but multiple T+1 EXITs remain ambiguous because PM lacks a materialized entry-premise diff

PHASE32_CU_PRODUCTION_REPAIR_JUSTIFIED = YES

PHASE32_CU_NEXT_STEP = Narrow design/repair for PM entry-premise context materialization: carry Day-0 entry admission, Buy Quality, target premise, and risk vector into PM lifecycle context; classify PM deterioration as known-at-entry vs fresh/persistent/hard-failure before preserving or escalating REDUCE/EXIT.
