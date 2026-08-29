# Phase32-BX - ADD Evidence Scale / Requalification Semantic Audit

## Executive Summary

This was a READ-ONLY semantic audit of ADD decision-time evidence in run
`runtime-test-historical-extended-smoke-20260828T230436594098Z`.

Coverage snapshot used while the run was still active:

```text
2022-10-03 through 2022-12-21
completed business days = 55
```

No production code, config, thresholds, model, runtime state, fresh-run, resume,
replay, or backtest was changed or executed. The Phase32-BW outcome observation
that ADD-active campaigns were net negative was used only to select an audit
surface, not for parameter selection.

The ADD machinery should be preserved: campaign identity, multi-lot generation,
per-lot quantity progression, budget competition, Cash competition, and
effective cap enforcement are all visible in the artifacts. The semantic gap is
narrower: the production-shaped frontier can accept ADD lots even when the
underlying `add_investment_evidence.v1` record says the ADD evidence is
`FAIL_CLOSED`. In those cases the accepted marginal value is mostly driven by
rank, quality, opportunity score, and remaining headroom, while fresh ADD
requalification since the prior ADD is not a hard admission boundary.

Primary diagnosis:

```text
ADD is mechanically distinct from NEW, but not semantically strict enough.
The frontier carries ADD-specific evidence, yet accepted ADD value can override
non-PASS ADD investment evidence. Repeated same-day lots reuse the same
opportunity/quality/rank/requalification signal and decay mainly through
headroom, so "still strong" is not consistently separated from "new evidence
justifies more capital now."
```

## Run Identity

| Field | Value |
| --- | --- |
| Run | `runtime-test-historical-extended-smoke-20260828T230436594098Z` |
| Coverage snapshot | `2022-10-03` through `2022-12-21` |
| Completed business days | 55 |
| Primary artifact | `daily/<date>/strategy/marginal_capital_frontier_authority.json` |
| PM artifact | `daily/<date>/position_management/pm_decisions.json` |
| Prior characterization | `docs/phase_reports/phase32_bw_winner_concentration_vs_tail_deployment_contribution_audit.md` |

## Architecture Standard

The relevant Architecture SoT says ADD is not merely an open-position or high
rank continuation action. ADD requires incremental continuation quality,
downside acceptance, opportunity-cost acceptance, relative strength, campaign
maturity, prior ADD history, current exposure, and incremental investment
eligibility. PM ADD is evidence, not capital authority. PC owns the capital
competition and each ADD lot must independently win against NEW, REENTRY, other
ADD lots, and Cash.

That standard implies two distinct questions:

1. Is the existing position still good enough to hold?
2. Is there fresh evidence that another unit of capital should be committed now?

The current artifact materializes many fields for both questions, but does not
always enforce the second question before accepting ADD targets.

## Target ADD Trace

Accepted target ADD lots for the requested campaigns:

| Date | Symbol | PM ADD reason | Accepted lots | Quantity path | Value range | Requal | ADD evidence | Expected edge | Opportunity cost | Rank / quality / opp | Trend close/MA20 | Momentum class |
| --- | --- | --- | ---: | --- | ---: | ---: | --- | --- | --- | --- | ---: | --- |
| 2022-10-05 | 94340 | strong trend, rank still high, no-loss-averaging | 3 | 100 -> 200 -> 300 -> 400 | 0.447686 -> 0.431411 | 0.0000 | FAIL_CLOSED | WEAKENING / FAIL_CLOSED | NEW_BUY_SUPERIOR / FAIL_CLOSED | 0.5 / 0.786355 / 0.22465077 | 0.992057 | MIXED_OR_UNRESOLVED |
| 2022-10-06 | 94340 | strong trend, rank still high, no-loss-averaging | 3 | 400 -> 500 -> 600 -> 700 | 0.522536 -> 0.506278 | 0.6667 | PASS | IMPROVING / PASS | PASS / PASS | 0.5 / 0.765738 / 0.23967307 | 0.988557 | MIXED_OR_UNRESOLVED |
| 2022-10-07 | 94320 | strong trend, rank still high, no-loss-averaging | 3 | 100 -> 200 -> 300 -> 400 | 0.641401 -> 0.623878 | 0.3333 | FAIL_CLOSED | WEAKENING / FAIL_CLOSED | PASS / PASS | 1.0 / 0.799811 / 0.36338273 | 1.014706 | MIXED_OR_UNRESOLVED |
| 2022-10-11 | 94320 | strong trend, rank still high, no-loss-averaging | 3 | 400 -> 500 -> 600 -> 700 | 0.653970 -> 0.636321 | 0.6667 | PASS | IMPROVING / PASS | PASS / PASS | 1.0 / 0.745498 / 0.37144026 | 1.022070 | HEALTHY_CONTINUATION |
| 2022-10-12 | 94320 | strong trend, rank still high, no-loss-averaging | 3 | 400 -> 500 -> 600 -> 700 | 0.670126 -> 0.652620 | 0.6667 | PASS | IMPROVING / PASS | PASS / PASS | 1.0 / 0.746750 / 0.42547970 | 1.009391 | FADING_PRIOR_WINNER |
| 2022-10-17 | 94320 | strong trend, rank still high, no-loss-averaging | 3 | 700 -> 800 -> 900 -> 1000 | 0.593217 -> 0.575630 | 0.3333 | FAIL_CLOSED | WEAKENING / FAIL_CLOSED | PASS / PASS | 1.0 / 0.720233 / 0.44501321 | 1.013563 | HEALTHY_CONTINUATION |
| 2022-10-18 | 94320 | strong trend, rank still high, no-loss-averaging | 3 | 700 -> 800 -> 900 -> 1000 | 0.577357 -> 0.559622 | 0.3333 | FAIL_CLOSED | WEAKENING / FAIL_CLOSED | PASS / PASS | 1.0 / 0.720828 / 0.39130731 | 1.023060 | HEALTHY_CONTINUATION |
| 2022-10-19 | 94320 | strong trend, rank still high, no-loss-averaging | 3 | 700 -> 800 -> 900 -> 1000 | 0.573192 -> 0.555378 | 0.3333 | FAIL_CLOSED | WEAKENING / FAIL_CLOSED | PASS / PASS | 1.0 / 0.736378 / 0.36733412 | 1.023262 | HEALTHY_CONTINUATION |
| 2022-10-20 | 94320 | strong trend, rank still high, no-loss-averaging | 3 | 700 -> 800 -> 900 -> 1000 | 0.567047 -> 0.549080 | 0.3333 | FAIL_CLOSED | WEAKENING / FAIL_CLOSED | PASS / PASS | 1.0 / 0.727096 / 0.35367951 | 1.038080 | HEALTHY_CONTINUATION |
| 2022-10-21 | 94320 | strong trend, rank still high, no-loss-averaging | 1 | 1000 -> 1100 | 0.600755 -> 0.600755 | 0.6667 | PASS | IMPROVING / PASS | PASS / PASS | 1.0 / 0.707833 / 0.40629465 | 1.021357 | MIXED_OR_UNRESOLVED |
| 2022-12-12 | 72730 | strong trend, rank still high, no-loss-averaging | 3 | 100 -> 200 -> 300 -> 400 | 0.389964 -> 0.371685 | 0.0000 | FAIL_CLOSED | UNKNOWN / FAIL_CLOSED | NEW_BUY_SUPERIOR / FAIL_CLOSED | 0.3333 / 0.714457 / 0.21137415 | 1.049744 | FADING_PRIOR_WINNER |

## Evidence Semantics

The ADD rows are mechanically distinct from NEW rows:

- `semantic_type = ADD_NEXT_LOT`
- PM ADD decision id and position campaign id are present
- `strategy_intelligence_add_worthiness_state` is present
- `add_investment_evidence.v1` is embedded
- same-campaign continuation and no-loss-averaging checks are present
- current quantity, current weight, pre/post lot quantity, pre/post lot weight,
  cap headroom, Cash, and Risk Pacing are present

However, the admission semantics are not strict enough:

- 21 of 31 accepted ADD lots in the 55BD snapshot had `final_add_eligibility =
  FAIL_CLOSED`.
- Accepted FAIL_CLOSED lots include explicit reasons such as
  `ADD_EXPECTED_EDGE_WEAKENING`, `ADD_INCREMENTAL_VALUE_UNKNOWN`, and
  `ADD_OPPORTUNITY_COST_FAIL`.
- 94340 on 2022-10-05 accepted three lots with requalification `0.0`, expected
  edge weakening, incremental value unknown, and NEW_BUY_SUPERIOR.
- 94320 on 2022-10-07 and 2022-10-17 through 2022-10-20 accepted multiple lots
  while expected edge was weakening and incremental value was unknown.
- 72730 on 2022-12-12 accepted three lots with requalification `0.0`, expected
  edge unknown/fail-closed, incremental value unknown, and NEW_BUY_SUPERIOR.

This means the frontier can still treat strong rank/quality/opportunity and
available headroom as enough to deploy ADD capital even when the dedicated ADD
investment evidence says not to.

## Repeated-Lot Requalification

Same-day repeated ADD lots reuse the same signal vector:

| Date | Symbol | Accepted lots | Unique signal rows | Shared signal |
| --- | --- | ---: | ---: | --- |
| 2022-10-05 | 94340 | 3 | 1 | opp 0.22465077, quality 0.786355, rank 0.5, requal 0.0 |
| 2022-10-06 | 94340 | 3 | 1 | opp 0.23967307, quality 0.765738, rank 0.5, requal 0.6667 |
| 2022-10-07 | 94320 | 3 | 1 | opp 0.36338273, quality 0.799811, rank 1.0, requal 0.3333 |
| 2022-10-11 | 94320 | 3 | 1 | opp 0.37144026, quality 0.745498, rank 1.0, requal 0.6667 |
| 2022-10-12 | 94320 | 3 | 1 | opp 0.42547970, quality 0.746750, rank 1.0, requal 0.6667 |
| 2022-10-17 | 94320 | 3 | 1 | opp 0.44501321, quality 0.720233, rank 1.0, requal 0.3333 |
| 2022-10-18 | 94320 | 3 | 1 | opp 0.39130731, quality 0.720828, rank 1.0, requal 0.3333 |
| 2022-10-19 | 94320 | 3 | 1 | opp 0.36733412, quality 0.736378, rank 1.0, requal 0.3333 |
| 2022-10-20 | 94320 | 3 | 1 | opp 0.35367951, quality 0.727096, rank 1.0, requal 0.3333 |
| 2022-12-12 | 72730 | 3 | 1 | opp 0.21137415, quality 0.714457, rank 0.3333, requal 0.0 |

Per-lot quantity/headroom is recomputed correctly, and later lots receive lower
capital value. But same-day lot #2 and lot #3 do not have fresh evidence beyond
the same T0 signal used by lot #1. The primary decay is headroom/concentration,
not evidence requalification.

## Controls

### Rejected ADD Controls

Rejected ADD rows were rejected by feasibility/cap rather than by a clean
semantic ADD admission boundary:

| Pattern | Count / Example | Interpretation |
| --- | --- | --- |
| `INFEASIBLE_CAP_BLOCKED` | 71 ADD rows | Cap enforcement works as a hard guardrail. |
| 94320 2022-10-21 lot #2/#3 | pre/post weights cross 18% effective cap | BT cap repair is effective. |
| 94320 2022-10-24 through 2022-10-28 | rank 1.0 and quality around 0.70, but cap-blocked | ADD can be blocked after high rank, but by cap rather than requalification. |

The rejected ADD controls therefore support guardrail integrity, not the
presence of a sufficiently strict ADD evidence admission gate.

### Strong Non-ADD Controls

Strong non-ADD controls such as 92420, 99840, 92270, 66320, 78860, 97310, and
30820 were accepted as NEW first lots with positive PC production admission.
Their capital values generally came from the same bounded value contract:
quality, rank, headroom, and requalification. Examples:

| Date | Symbol | Type | Value | Quality | Rank component | Momentum class |
| --- | --- | --- | ---: | ---: | ---: | --- |
| 2022-10-03 | 92420 | NEW_FIRST_LOT | 0.336920 | 0.615140 | 0.0476 | HEALTHY_CONTINUATION |
| 2022-10-07 | 99840 | NEW_FIRST_LOT | 0.373004 | 0.723145 | 0.0909 | HEALTHY_CONTINUATION |
| 2022-11-10 | 66320 | NEW_FIRST_LOT | 0.432551 | 0.729776 | 0.0833 | MIXED_OR_UNRESOLVED |
| 2022-11-14 | 78860 | NEW_FIRST_LOT | 0.413165 | 0.758757 | 0.1250 | MIXED_OR_UNRESOLVED |
| 2022-11-24 | 30820 | NEW_FIRST_LOT | 0.396274 | 0.659056 | 0.0455 | HEALTHY_CONTINUATION |

This confirms that ADD and NEW are on the same marginal value surface, but it
also shows the semantic risk: ADD can compare favorably to NEW through rank and
quality even when its own incremental ADD evidence is non-PASS.

## Diagnosis

The current ADD authority distinguishes ADD from NEW at the object and lineage
level, but not always at the decisive admission/value level.

What works:

- Stable campaign identity and PM ADD lineage are materialized.
- Per-lot ADD candidate identities are stable and deterministic.
- Per-lot quantity, Cash, weight, headroom, cap, and budget are recomputed.
- Cash and NEW/REENTRY competition remain visible.
- Cap blocked rows fail closed.

What is semantically weak:

- `add_investment_evidence.final_add_eligibility = FAIL_CLOSED` is not a hard
  blocker for ADD target acceptance.
- `requalification = 0.0` can still receive accepted ADD lots.
- Repeated same-day lots do not require incremental strengthening beyond lot #1.
- PM reason codes like `strong_trend_continuation` and
  `opportunity_rank_still_high` are allowed to behave too much like "still
  strong" rather than "freshly stronger since the last ADD".
- The ADD/NEW value scale is comparable mechanically, but partially unfair
  semantically when ADD's dedicated incremental evidence is bypassed.

The issue is not ADD quantity machinery. It is an ADD admission/value semantic
gap.

## Defect / No-Defect Judgment

This is a production repair candidate, but not a performance-tuning mandate.
The appropriate repair boundary is to make ADD investment evidence and
fresh requalification authoritative for ADD target admission/value, while
preserving the common frontier, multi-lot ADD, Cash competition, cap enforcement,
budget conservation, and PS/runtime behavior.

No historical future outcome should be used to choose new thresholds or weights.
The repair should use existing PIT evidence already materialized in
`add_investment_evidence.v1` and the architecture contract that ADD requires
incremental investment eligibility.

## Final Judgments

```text
PHASE32_BX_ADD_EVIDENCE_DISTINCT_FROM_NEW = PARTIAL
PHASE32_BX_FRESH_REQUALIFICATION_PER_ADD = PARTIAL
PHASE32_BX_INCREMENTAL_STRENGTHENING_EVIDENCE = PARTIAL
PHASE32_BX_ADD_NEW_VALUE_SCALE_COMPARABLE = PARTIAL
PHASE32_BX_REPEATED_ADD_SEMANTIC_GAP = YES
PHASE32_BX_PRIMARY_DIAGNOSIS = ADD_OBJECT_AND_LINEAGE_ARE_DISTINCT_BUT_ADD_ADMISSION_VALUE_CAN_ACCEPT_NON_PASS_INCREMENTAL_EVIDENCE_AND_REUSE_NEW_LIKE_STRENGTH_SIGNALS
PHASE32_BX_PRODUCTION_REPAIR_JUSTIFIED = PARTIAL
PHASE32_BX_ADD_MACHINERY_PRESERVE = YES
PHASE32_BX_LONG_RUN_CONTINUE = YES
PHASE32_BX_NEXT_STEP = DESIGN_NARROW_ADD_REQUALIFICATION_AND_INCREMENTAL_EVIDENCE_ADMISSION_REPAIR_WITHOUT_CHANGING_QUANTITY_MACHINERY_OR_TUNING_FROM_OUTCOMES
```
