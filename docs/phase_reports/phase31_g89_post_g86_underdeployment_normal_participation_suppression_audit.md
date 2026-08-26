# Phase31-G89 — Post-G86 Under-Deployment / Normal Participation Suppression Audit

## PRIMARY_JUDGMENT

PHASE31_G89_G86_AGGREGATE_CASH_PREFERRED_RESOLVER_OVER_SUPPRESSES_NORMAL_PARTICIPATION_REPAIR_REQUIRED

## Scope

READ-ONLY audit only.

Comparison runs:

- Pre-G81 / pre-G86 reference: `runtime-test-historical-extended-smoke-20260823T140946562431Z`
- Post-G86 + G88 clean validation: `runtime-test-historical-extended-smoke-20260824T032350824281Z`

Primary window:

- `2022-12-20` through `2023-01-19`

Focus dates:

- `2023-01-17`
- `2023-01-18`
- `2023-01-19`

No code, config, threshold, weight, run state, fresh-run, resume, replay, or Historical execution was performed for G89.

## Executive Conclusion

The post-G86 under-deployment is real and is first introduced inside Portfolio Construction at the G86 PC-owned final partition boundary:

```text
market_candidate_cash_interaction
-> cash_preferred_participation_deferral_resolution.v1
-> canonical_multi_allocation_deployment_set.v1 security_allocations / cash_preferred_security_deferrals
```

Portfolio Policy, Market Quality, Risk Pacing, and capital budget do not directly zero deployment. In the audited window, both runs use the same Market Quality / Risk Pacing distribution:

```text
SHORT_TERM_BREADTH_BREAKDOWN = 6 dates
CONFLICTED_MARKET_STRUCTURE = 14 dates
CAUTIOUS_DEPLOYMENT = 20 dates
```

The material divergence occurs after selected PC competitors already exist. Post-G86 converts 101 selected `CASH_PREFERRED` `NEW_BUY` increments into `cash_preferred_security_deferrals[]`, with cumulative requested security weight `5.174962`, while final security allocation drops from pre-run `83` rows / `5.841721` weight to post-run `26` rows / `1.369249` weight.

G86 does preserve the intended weak-tail defense in principle, but in this January window the aggregate resolver is too coarse: it keeps only the same-quality-class frontier row and labels most non-frontier rows `CASH_PREFERRED_AGGREGATE_WEAK_TAIL_DEFERRAL`, even when row evidence is complete and many rows resemble G84 normal reduced participation more than G80 plateau weak-tail.

## Window Aggregate

| Metric | Pre-G81/pre-G86 | Post-G86+G88 |
| --- | ---: | ---: |
| Business dates audited | 20 | 20 |
| PC security allocation count | 83 | 26 |
| PC security allocation weight | 5.841721 | 1.369249 |
| CASH_PREFERRED deferral count | 0 | 101 |
| CASH_PREFERRED deferred requested weight | 0.000000 | 5.174962 |
| Average authorized Cash allocation weight | 0.024945 | 0.268440 |
| Average available incremental budget | 0.317031 | 0.336902 |
| G61 lot-executable allocation rows | 83 | 26 |
| Market Quality states | 6 `SHORT_TERM_BREADTH_BREAKDOWN`, 14 `CONFLICTED_MARKET_STRUCTURE` | same |
| Risk Pacing states | 20 `CAUTIOUS_DEPLOYMENT` | same |

Post-G86 deferral inventory:

```text
deferrals = 101
actions = NEW_BUY 101
classes = COMPARABLE_MARGINAL 97, COMPARABLE_HIGH 4
median rank = 6
rank >= 31 = 0
median runtime opportunity score = -0.395917
score < -0.5 = 22
median confidence = 0.72
confidence < 0.3 = 7
row_evidence_complete = 101 / 101
opportunity_set_frontier = false for 98 / 101
```

Dominant post-G86 deferral reason codes:

```text
CASH_PREFERRED_BINDING_AT_FINAL_ALLOCATION = 101
CASH_PREFERRED_DEFER_TO_OPTIONAL_CASH = 101
CASH_PREFERRED_ROW_PARTICIPATION_EVIDENCE_COMPLETE = 101
PC_PARTICIPATION_DEFERRAL_AUTHORITY = 101
CASH_PREFERRED_AGGREGATE_WEAK_TAIL_DEFERRAL = 98
```

The key contradiction is that all 101 deferred rows have complete row evidence, while 98 are deferred because they are not the same-quality-class frontier row.

## Target Date Diff

### 2023-01-17

| Metric | Pre-G81/pre-G86 | Post-G86+G88 |
| --- | ---: | ---: |
| Available incremental budget | 0.426733 | 0.416795 |
| Market Quality | `CONFLICTED_MARKET_STRUCTURE` | `CONFLICTED_MARKET_STRUCTURE` |
| Risk Pacing | `CAUTIOUS_DEPLOYMENT` | `CAUTIOUS_DEPLOYMENT` |
| Cash preference semantic | `OPTIONALITY_ELEVATED` | `OPTIONALITY_ELEVATED` |
| PC competitor count | 29 | 32 |
| Selected deployable count | 6 | 8 |
| Security allocation count / weight | 6 / 0.399813 | 1 / 0.021765 |
| CASH_PREFERRED deferral count / weight | 0 / 0.000000 | 7 / 0.388729 |
| Authorized Cash allocation | 0.026920 | 0.395030 |
| G61 executable rows | 6 | 1 |
| BUY fills | 3 | 1 |

Pre positive security increments not present as post positive allocations:

| Symbol | Pre weight | Pre rank | Pre score | Pre confidence | Post status |
| --- | ---: | ---: | ---: | ---: | --- |
| 38960 | 0.031291 | 4 | -0.420967 | 0.68 | deferred by G86 aggregate weak-tail |
| 65670 | 0.053642 | 5 | -0.463018 | 0.58 | deferred by G86 aggregate weak-tail |
| 21950 | 0.090834 | 7 | -0.532208 | 0.30 | absent from post selected allocation |
| 44900 | 0.153238 | 8 | -0.541201 | 0.28 | absent from post selected allocation |
| 30830 | 0.044255 | 9 | -0.547938 | 0.26 | absent from post selected allocation |
| 79460 | 0.026553 | 11 | -0.574520 | 0.20 | absent from post selected allocation |

Post-G86 deferred rows include stronger-looking rows than several pre-G81 rows that previously participated. For example, `59860` was deferred with rank `3`, score `-0.295067`, confidence `0.84`; `65370` was deferred with rank `5`, score `-0.356325`, confidence `0.78`. Both were rejected solely through the G86 `CASH_PREFERRED_AGGREGATE_WEAK_TAIL_DEFERRAL` path.

### 2023-01-18

| Metric | Pre-G81/pre-G86 | Post-G86+G88 |
| --- | ---: | ---: |
| Available incremental budget | 0.708221 | 0.745314 |
| Market Quality | `CONFLICTED_MARKET_STRUCTURE` | `CONFLICTED_MARKET_STRUCTURE` |
| Risk Pacing | `CAUTIOUS_DEPLOYMENT` | `CAUTIOUS_DEPLOYMENT` |
| Cash preference semantic | `OPTIONALITY_ELEVATED` | `OPTIONALITY_NEUTRAL` |
| PC competitor count | 30 | 31 |
| Selected deployable count | 7 | 11 |
| Security allocation count / weight | 7 / 0.471428 | 2 / 0.084892 |
| CASH_PREFERRED deferral count / weight | 0 / 0.000000 | 9 / 0.654568 |
| Authorized Cash allocation | 0.236793 | 0.660422 |
| G61 executable rows | 7 | 2 |
| BUY fills | 5 | 2 |

Post-G86 allocated one `SELECTIVE_COMPETITION` row and one `CASH_PREFERRED_PARTICIPATION_VALID` row, but deferred nine `CASH_PREFERRED` rows. The deferred rows again include credible normal-participation-like evidence:

| Symbol | Requested weight | Rank | Score | Confidence | G86 reason |
| --- | ---: | ---: | ---: | ---: | --- |
| 65370 | 0.022194 | 4 | -0.353170 | 0.76 | aggregate weak-tail deferral |
| 42630 | 0.129743 | 6 | -0.400186 | 0.68 | aggregate weak-tail deferral |
| 21380 | 0.093862 | 8 | -0.466086 | 0.60 | aggregate weak-tail deferral |
| 94220 | 0.176535 | 9 | -0.505538 | 0.50 | aggregate weak-tail deferral |
| 70680 | 0.043371 | 10 | -0.509626 | 0.48 | aggregate weak-tail deferral |
| 91070 | 0.085604 | 11 | -0.517112 | 0.44 | aggregate weak-tail deferral |
| 61810 | 0.027059 | 12 | -0.518742 | 0.42 | aggregate weak-tail deferral |
| 48890 | 0.031257 | 14 | -0.538200 | 0.32 | aggregate weak-tail deferral |
| 39350 | 0.044943 | 17 | -0.563402 | 0.26 | aggregate weak-tail deferral |

This date is mixed: several lower-confidence rows plausibly resemble weak-tail, but the top deferred rows do not look like obvious G80 weak-tail. The resolver still classifies all non-frontier rows together.

### 2023-01-19

| Metric | Pre-G81/pre-G86 | Post-G86+G88 |
| --- | ---: | ---: |
| Available incremental budget | 0.494188 | 0.718634 |
| Market Quality | `CONFLICTED_MARKET_STRUCTURE` | `CONFLICTED_MARKET_STRUCTURE` |
| Risk Pacing | `CAUTIOUS_DEPLOYMENT` | `CAUTIOUS_DEPLOYMENT` |
| Cash preference semantic | `OPTIONALITY_ELEVATED` | `OPTIONALITY_ELEVATED` |
| PC competitor count | 27 | 28 |
| Selected deployable count | 5 | 10 |
| Security allocation count / weight | 5 / 0.469132 | 2 / 0.174463 |
| CASH_PREFERRED deferral count / weight | 0 / 0.000000 | 8 / 0.538641 |
| Authorized Cash allocation | 0.025056 | 0.544171 |
| G61 executable rows | 5 | 2 |
| BUY fills | 3 | 2 |

Pre positive security increments not present as post positive allocations:

| Symbol | Pre weight | Pre rank | Pre score | Pre confidence | Post status |
| --- | ---: | ---: | ---: | ---: | --- |
| 38140 | 0.026519 | 3 | -0.459738 | 0.60 | deferred by G86 aggregate weak-tail |
| 77110 | 0.126547 | 4 | -0.597261 | 0.20 | absent |
| 70360 | 0.107198 | 5 | -0.598747 | 0.18 | absent |
| 39760 | 0.064267 | 6 | -0.607248 | 0.14 | absent |
| 57590 | 0.144601 | 7 | -0.611943 | 0.12 | absent |

Post-G86 deferrals:

| Symbol | Requested weight | Rank | Score | Confidence | G86 reason |
| --- | ---: | ---: | ---: | ---: | --- |
| 65370 | 0.022354 | 3 | -0.350530 | 0.72 | aggregate weak-tail deferral |
| 29980 | 0.041340 | 5 | -0.421337 | 0.66 | aggregate weak-tail deferral |
| 38140 | 0.028241 | 7 | -0.459738 | 0.60 | aggregate weak-tail deferral |
| 21380 | 0.094750 | 8 | -0.479607 | 0.54 | aggregate weak-tail deferral |
| 89380 | 0.100546 | 9 | -0.514649 | 0.44 | aggregate weak-tail deferral |
| 94220 | 0.175610 | 10 | -0.517463 | 0.42 | aggregate weak-tail deferral |
| 48890 | 0.031921 | 12 | -0.520199 | 0.38 | aggregate weak-tail deferral |
| 39350 | 0.043879 | 14 | -0.568431 | 0.26 | aggregate weak-tail deferral |

Again, the first causal boundary is not absence of budget or absence of selected competitors. It is the G86 final partition from requested security increments into `CASH_PREFERRED_DEFER`.

## Normal Participation vs Weak-Tail Classification

G84 established two separable states:

- `PARTICIPATION_VALID_CASH_PREFERRED`: Cash preferred over full deployment, but reduced security participation remains valid.
- `WEAK_TAIL_CASH_PREFERRED`: optional Cash should fully win the marginal allocation.

G84 also showed descriptive, non-production-tuned cohort differences:

- Normal participation cohort median rank `18`, median score `-0.3543`, median confidence `0.66`.
- Plateau weak-tail cohort median rank `34`, median score `-0.4973`, median confidence `0.34`.
- Post-G83 over-defense cohort median rank `13`, median score `-0.2619`, median confidence `0.76`.

Post-G86 January deferrals:

- median rank `6`
- median score `-0.395917`
- median confidence `0.72`
- rank `>=31`: `0 / 101`
- score `< -0.5`: `22 / 101`
- confidence `<0.3`: `7 / 101`

This distribution is materially closer to the normal / post-G83 over-defense cohorts than to the G80 weak-tail cohort. The correct conclusion is not that every deferred row should be bought. It is that G86's aggregate frontier-only partition is over-defensive for this window and does not preserve normal reduced participation sufficiently.

POST_G86_DEFERRAL_CLASSIFICATION_COUNTS:

```text
clearly_participation_valid_like = 14 / 24 on focus dates
clearly_weak_tail_like = 10 / 24 on focus dates
ambiguous = 0 / 24 on focus dates
```

This classification uses G84 descriptive cohort markers only for audit characterization; it is not a proposed production threshold.

## G86 Resolver Behavior

The current resolver in `src/ai_fund_lab_v2/strategy/portfolio_construction.py` builds `frontier_by_quality` across simultaneous `CASH_PREFERRED` rows, then allows participation only when:

```text
row_evidence_valid
quality in {COMPARABLE_HIGH, COMPARABLE_MARGINAL}
relative_strength != WEAK
on_frontier
ADD evidence preserved
```

For the audited post-G86 window:

- `row_evidence_valid = true` for `101 / 101` deferred rows.
- `CASH_PREFERRED_ROW_PARTICIPATION_EVIDENCE_COMPLETE` appears in all `101` deferrals.
- `CASH_PREFERRED_AGGREGATE_WEAK_TAIL_DEFERRAL` appears in `98 / 101` deferrals.
- `opportunity_set_frontier = false` for `98 / 101` deferrals.

Therefore the dominant suppression condition is:

```text
non-bootstrap CASH_PREFERRED
+ row evidence complete
+ same-quality-class non-frontier
=> CASH_PREFERRED_AGGREGATE_WEAK_TAIL_DEFERRAL
=> authorized_allocation_weight = 0
```

This is the first material divergence from the pre-G81 path.

## Lost Deployment Cause Classification

Window-level lost / redirected deployment is concentrated at G86:

| Cause | Count / weight | Notes |
| --- | ---: | --- |
| `CASH_PREFERRED_DEFER` | 101 / 5.174962 | Direct post-G86 final allocation deferral |
| `AGGREGATE_DEFERRAL` | 98 / most deferred weight | Dominant non-frontier aggregate condition |
| `LOT/CAP_FEASIBILITY` | not primary | G61 executable rows equal final PC positive rows; no later recovery of deferred rows |
| `STRONGER_SECURITY_COMPETITION` | partial | Frontier rows survive; non-frontier rows are not individually compared into a richer allocation set |
| `ADD/NEW_BUY_COMPETITION` | no direct evidence in focus window | Deferrals are `NEW_BUY 101`; post allocations include `ADD 5`, but no ADD-specific G86 suppression was observed here |
| `FAIL_CLOSED_EVIDENCE` | no | Deferrals have row evidence complete |
| `MARKET/RISK_BUDGET` | enabling context, not direct cause | Same MQ/Risk distribution pre and post; budget remains positive |
| `OTHER` | path-dependent symbol-set differences | Some pre symbols are absent in post selected set due changed run state, but this is not the first causal boundary |

## Weak-Tail Reference Comparison

G80 weak-tail examples remain valid and should not be reverted:

| Date | Symbol | G80/G86 expected result |
| --- | --- | --- |
| 2023-07-21 | 14390 | `CASH_PREFERRED_DEFER` |
| 2023-07-24 | 69320 | `CASH_PREFERRED_DEFER` |
| 2023-08-01 | 37600 | `CASH_PREFERRED_DEFER` |
| 2023-08-01 | 87500 | `CASH_PREFERRED_DEFER` |

G80's issue was aggregate weak-tail overdeployment: multiple weak reduced rows consumed material capital when Cash was only residual. G89 does not disprove that root cause.

The new G89 finding is the opposite failure mode: the G86 aggregate protection now acts as a frontier-only bottleneck in a normal participation window, moving too much requested reduced participation into Cash.

## Required Judgments

POST_G86_UNDERDEPLOYMENT_PRESENT = YES

FIRST_CAUSAL_BOUNDARY = PORTFOLIO_CONSTRUCTION_G86_CASH_PREFERRED_PARTICIPATION_DEFERRAL_RESOLUTION

NORMAL_PARTICIPATION_OVER_SUPPRESSED = YES

TRUE_WEAK_TAIL_DEFERRAL_PRESENT = YES

G86_RESOLVER_OVERDEFENSE = YES

G86_RESOLVER_DOMINANT_SUPPRESSION_CONDITION = SAME_QUALITY_CLASS_NON_FRONTIER_CASH_PREFERRED_AGGREGATE_WEAK_TAIL_DEFERRAL

OPPORTUNITY_SET_CONTEXT_MISCLASSIFIED = PARTIAL

AGGREGATE_CONTROL_OVERDEFENSE = YES

G86_ADD_SUPPRESSION = NO

CAPITAL_BUDGET_CAUSE = NO

MARKET_QUALITY_CAUSE = NO

RISK_PACING_CAUSE = NO

CANDIDATE_SELECTION_CAUSE = PARTIAL

EXISTING_EVIDENCE_SUFFICIENT_FOR_REPAIR = YES

REPAIR_REQUIRED = YES

## Safety / Mutability

CODE_CHANGED_BY_G89 = NO

CONFIG_CHANGED = NO

THRESHOLD_WEIGHT_TUNING = NO

RUN_MODIFIED = NO

FRESH_RUN_EXECUTED = NO

RESUME_EXECUTED = NO

REPLAY_EXECUTED = NO

LONG_HISTORICAL_EXECUTED = NO

FUTURE_INPUT_COUNT = 0

HISTORICAL_OUTCOME_PARAMETER_SELECTION_COUNT = 0

## Repair Boundary Recommendation

Repair only the PC-owned G86 final partition boundary:

```text
cash_preferred_participation_deferral_resolution.v1
```

Do not revert G81/G86. Preserve G80 weak-tail protection, but replace the current frontier-only aggregate suppression with a partition that can preserve multiple normal participation-valid reduced rows when same-date row evidence and opportunity-set context support participation. The repair should reuse existing PIT evidence already present in PC artifacts:

- row evidence completeness
- entry admission action/state/sufficiency
- relative strength / momentum context
- within-class priority evidence
- opportunity quality class
- aggregate requested `CASH_PREFERRED` weight
- capital budget / Cash state / Risk Pacing context

No Market Quality redesign, candidate ranking change, BUY filter, threshold tuning, or Historical-outcome parameter selection is warranted by G89.
