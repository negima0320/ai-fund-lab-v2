# Phase31-G84 — Normal Participation vs Weak-Tail CASH_PREFERRED Semantic Separability Audit

## PRIMARY_JUDGMENT

PHASE31_G84_CASH_PREFERRED_SEMANTIC_TOO_COARSE_EXISTING_EVIDENCE_PARTIALLY_SUFFICIENT_REPAIR_REQUIRED

## Scope

READ-ONLY audit only.

- Pre-G81 normal reference run: `runtime-test-historical-extended-smoke-20260823T140946562431Z`
- Post-G83 over-defensive run: `runtime-test-historical-extended-smoke-20260823T232301910860Z`
- No code, config, threshold, weight, Market Quality, Risk Pacing, Candidate ranking, BUY filter, fresh-run, resume, replay, or long Historical changes were made.
- Future information and Historical outcome were not used as Strategy decision inputs.

## Executive Conclusion

Current `CASH_PREFERRED` collapses at least two economically different states:

1. `PARTICIPATION_VALID_CASH_PREFERRED`: Cash is preferred over full deployment, but reduced security participation remains valid under same-date PIT evidence.
2. `WEAK_TAIL_CASH_PREFERRED`: candidate quality is weak enough that optional Cash should fully win the marginal allocation.

The distinction is not recoverable from `market_candidate_cash_interaction.reason_codes` alone. The same reason-code pairs appear in normal participation rows, plateau weak-tail rows, and post-G83 suppressed rows:

```text
CAUTIOUS_COMPARABLE_MARGINAL_CASH_PREFERRED
CAUTIOUS_MARGINAL_LOST_TO_CASH

GRADUAL_COMPARABLE_MARGINAL_CASH_PREFERRED
GRADUAL_MARGINAL_LOST_TO_CASH
```

However, existing same-date PIT evidence does carry useful separability:

- row-level rank, score, confidence, quality score, entry state/action, momentum, relative strength
- same-day opportunity-set context such as top scores, median score, rank position, and count of stronger candidates
- aggregate participation context such as number of simultaneous `CASH_PREFERRED` rows and total deferred weight
- Portfolio Policy cash state and deployment capacity

The distinction is currently lost at:

```text
portfolio_construction._interaction_result_for_quality()
-> market_candidate_cash_interaction.interaction_result = CASH_PREFERRED
-> portfolio_construction._canonical_multi_allocation_deployment_set()
-> non-bootstrap CASH_PREFERRED becomes unconditional cash_preferred_security_deferral
```

G83 correctly restored bootstrap participation but left non-bootstrap `CASH_PREFERRED` as an unconditional zero-security result. The post-G83 artifact shows that this over-defends normal early participation rows.

## Cohort Evidence

### Cohort A — Normal Participation CASH_PREFERRED

Pre-G81 normal period: `2022-10-04` through `2022-11-30`.

Rows included: non-bootstrap `CASH_PREFERRED` BUY/ADD rows that received positive security allocation pre-G81.

```text
rows = 123
affected_dates = 30
symbols = 57
cumulative_positive_weight = 7.521452
average_rows_per_affected_date = 4.10
average_cash_preferred_weight_per_affected_date = 0.2507
```

Distribution:

| Field | Cohort A |
| --- | ---: |
| median rank | 18 |
| rank >= 31 | 16 / 123 = 13.0% |
| median runtime opportunity score | -0.3543 |
| score < -0.5 | 26 / 123 = 21.1% |
| median confidence | 0.66 |
| confidence < 0.3 | 5 / 123 = 4.1% |
| median quality score | 0.6641 |
| rank <= 10, score >= 0, confidence >= 0.6 | 21 |
| canonical quality class | `COMPARABLE_MARGINAL` 120, `COMPARABLE_HIGH` 3 |

This proves normal reduced participation `CASH_PREFERRED` existed before G81/G83.

## Cohort B — Plateau Weak-Tail CASH_PREFERRED

Pre-G81 plateau / weak-tail period: `2023-05-31` through `2023-08-22`.

Rows included: positive `CASH_PREFERRED` security allocations that G80 identified as weak-tail overdeployment risk.

```text
rows = 142
affected_dates = 43
symbols = 109
cumulative_positive_weight = 8.794019
average_rows_per_affected_date = 3.30
average_cash_preferred_weight_per_affected_date = 0.2045
```

Distribution:

| Field | Cohort B |
| --- | ---: |
| median rank | 34 |
| rank >= 31 | 86 / 142 = 60.6% |
| median runtime opportunity score | -0.4973 |
| score < -0.5 | 69 / 142 = 48.6% |
| median confidence | 0.34 |
| confidence < 0.3 | 56 / 142 = 39.4% |
| median quality score | 0.5591 |
| rank <= 10, score >= 0, confidence >= 0.6 | 2 |
| canonical quality class | `COMPARABLE_MARGINAL` 129, `COMPARABLE_HIGH` 13 |

This proves weak-tail `CASH_PREFERRED` also exists. It is materially lower-ranked, lower-score, and lower-confidence than normal-period participation rows.

## Post-G83 Over-Defense Evidence

Post-G83 run: `runtime-test-historical-extended-smoke-20260823T232301910860Z`.

Window: `2022-10-04` through `2022-10-19`.

```text
cash_preferred_security_deferral_rows = 101
affected_dates = 11
cumulative_deferred_weight = 7.103426
security_allocation_count = 0 on all 11 audited dates
average_deferral_rows_per_date = 9.18
average_deferred_weight_per_date = 0.6458
cash_state = NORMAL_INVESTED_PORTFOLIO for all 101 deferred rows
```

The suppressed rows look much closer to normal participation than plateau weak-tail:

| Field | Post-G83 Deferred Rows |
| --- | ---: |
| median rank | 13 |
| rank >= 31 | 3 / 101 = 3.0% |
| median runtime opportunity score | -0.2619 |
| score < -0.5 | 0 / 101 = 0.0% |
| median confidence | 0.76 |
| confidence < 0.3 | 0 / 101 = 0.0% |
| median quality score | 0.6841 |
| rank <= 10, score >= 0, confidence >= 0.6 | 13 |
| canonical quality class | `COMPARABLE_MARGINAL` 100, `COMPARABLE_HIGH` 1 |

Examples of high-quality rows deferred solely because non-bootstrap `CASH_PREFERRED` is binding:

| Date | Symbol | Rank | Score | Confidence | Quality Score | Requested Weight |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| 2022-10-14 | 94320 | 1 | 0.4491 | 1.00 | 0.7842 | 0.015711 |
| 2022-10-17 | 94320 | 1 | 0.4450 | 1.00 | 0.7849 | 0.015708 |
| 2022-10-18 | 94320 | 1 | 0.3913 | 1.00 | 0.7853 | 0.015889 |
| 2022-10-06 | 94320 | 1 | 0.3824 | 1.00 | 0.8083 | 0.037037 |
| 2022-10-13 | 94340 | 2 | 0.3083 | 0.98 | 0.6950 | 0.014353 |
| 2022-10-12 | 94340 | 2 | 0.2858 | 0.98 | 0.7574 | 0.014398 |

These rows do not resemble the G80 weak-tail pattern of rank 31+, low confidence, and deeply negative opportunity scores.

## Same-Date Pre/Post Comparison

For `2022-10-04` through `2022-10-19`, pre-G81 had positive `CASH_PREFERRED` security allocation on every audited date. Post-G83 converted all audited non-bootstrap `CASH_PREFERRED` rows to deferrals.

| Date | Pre-G81 positive CP rows | Pre-G81 CP weight | Post-G83 deferred CP rows | Post-G83 deferred weight | Post-G83 security weight |
| --- | ---: | ---: | ---: | ---: | ---: |
| 2022-10-04 | 7 | 0.5707 | 7 | 0.5707 | 0 |
| 2022-10-05 | 6 | 0.2983 | 7 | 0.5600 | 0 |
| 2022-10-06 | 6 | 0.2036 | 9 | 0.6377 | 0 |
| 2022-10-07 | 4 | 0.1743 | 10 | 0.6653 | 0 |
| 2022-10-11 | 3 | 0.0926 | 9 | 0.5377 | 0 |
| 2022-10-12 | 4 | 0.0852 | 9 | 0.5658 | 0 |
| 2022-10-13 | 6 | 0.4681 | 8 | 0.6950 | 0 |
| 2022-10-14 | 5 | 0.4943 | 10 | 0.6780 | 0 |
| 2022-10-17 | 2 | 0.2122 | 9 | 0.6682 | 0 |
| 2022-10-18 | 4 | 0.1811 | 13 | 0.6697 | 0 |
| 2022-10-19 | 5 | 0.2684 | 10 | 0.8554 | 0 |

This confirms the G83 over-defense mechanism: after bootstrap, all `NORMAL_INVESTED_PORTFOLIO + CASH_PREFERRED` candidates are treated like weak-tail deferrals even when the row-level evidence resembles normal participation.

## Reason-Code Semantics

Reason codes are not sufficient by themselves.

Normal participation rows and weak-tail rows share the same core codes:

```text
CAUTIOUS_COMPARABLE_MARGINAL_CASH_PREFERRED
CAUTIOUS_MARGINAL_LOST_TO_CASH
GRADUAL_COMPARABLE_MARGINAL_CASH_PREFERRED
GRADUAL_MARGINAL_LOST_TO_CASH
```

These codes say Cash wins relative to a cautious/gradual marginal security row. They do not encode whether the row is:

- a high-ranked, high-confidence reduced-risk participation candidate; or
- a low-ranked, low-confidence weak-tail candidate that should fully defer to Cash.

The missing semantic is not a new market indicator. It is a final partition semantic that combines existing row-level quality and same-day opportunity-set/aggregate context before converting `CASH_PREFERRED` to either reduced participation or zero-security deferral.

## Row-Level Separability

Row-level evidence is partially sufficient.

Strong separability exists at the tails:

- Plateau weak-tail rows are heavily concentrated in rank >= 31, score < -0.5, and confidence < 0.3.
- Post-G83 suppressed rows have almost none of those weak-tail markers.
- Post-G83 contains many rank 1-10, positive-score, high-confidence rows that should not be treated as equivalent to plateau weak-tail.

But row-level evidence alone is not fully sufficient because there is overlap:

- Cohort A still contains some rank >= 31 and score < -0.5 rows.
- Cohort B still contains a small number of high-ranked / high-confidence rows.
- The same `COMPARABLE_MARGINAL` class covers both economically acceptable reduced participation and true weak-tail.

Therefore row-level fields can identify many obvious weak-tail and many obvious normal-participation rows, but a safe production distinction requires same-day opportunity-set and aggregate context as well.

## Opportunity-Set And Aggregate Context

Opportunity-set context is needed.

Existing evidence already exposes:

- top1/top3/top10 opportunity scores
- median candidate score
- rank position and stronger-candidate count
- valid competitor count
- selected competitor set
- accepted/requested security weights
- Cash state and deployment capacity
- aggregate `CASH_PREFERRED` security/deferred weight

This context is necessary because the defect is partly aggregate:

```text
individually plausible reduced participation
-> many simultaneous CASH_PREFERRED rows
-> possible aggregate weak-tail overdeployment
```

G80's plateau problem was not merely that one row had `CASH_PREFERRED`; it was that many reduced-only / marginal rows were allowed to consume capital while Cash was only residual. G83's new problem is the opposite: every non-bootstrap `CASH_PREFERRED` row becomes zero security, even when the same-date row evidence is strong relative to the opportunity set.

## Architecture Sufficiency

Existing architecture evidence is partially sufficient.

Sufficient existing evidence:

- Portfolio Policy distinguishes bootstrap from residual/normal cash state.
- Risk Pacing defines deployment intensity, not security admission.
- Market Candidate Cash Interaction preserves canonical opportunity quality class and reason codes.
- Competitors preserve rank, construction priority, accepted weight, lot context, and within-class evidence.
- Portfolio members preserve runtime opportunity score, confidence, quality score, entry admission, momentum, and relative strength.
- Architecture SoT says weak market plus strong stock-specific evidence may produce reduced allocation rather than automatic zero, and `CAUTIOUS_MARGINAL_AUTOMATIC_ZERO = NO`.

Missing materialized semantic:

```text
For non-bootstrap CASH_PREFERRED, the final PC partition does not publish
whether the row is participation-valid reduced risk or true weak-tail Cash win.
```

No new indicator, score, Historical threshold, rank cutoff, confidence cutoff, or parameter tuning is required to state the contract. A repair is still required because the current production consumer boundary only has:

```text
CASH_PREFERRED + non-bootstrap -> zero security deferral
```

## Required Root-Cause Judgment

CASH_PREFERRED_SEMANTIC_IS_TOO_COARSE = YES

NORMAL_PARTICIPATION_CASH_PREFERRED_EXISTS = YES

WEAK_TAIL_CASH_PREFERRED_EXISTS = YES

NORMAL_VS_WEAK_TAIL_CASH_PREFERRED_SEPARABILITY = PARTIAL

ROW_LEVEL_EVIDENCE_SUFFICIENT = PARTIAL

OPPORTUNITY_SET_CONTEXT_NEEDED_FOR_SEPARABILITY = YES

AGGREGATE_CONTEXT_REQUIRED = YES

G83_OVERDEFENSE_CAUSE_CONFIRMED = YES

EXISTING_ARCHITECTURE_EVIDENCE_SUFFICIENT = PARTIAL

NEW_FEATURE_REQUIRED = NO

REPAIR_REQUIRED = YES

## Direct Answers

### What differentiates normal reduced participation from true weak-tail Cash preference?

Existing PIT evidence differentiates them through a combination of:

- row-level rank / score / confidence / quality score
- entry and continuation evidence
- momentum and relative strength context
- opportunity quality class and Cash interaction reason codes
- same-day opportunity-set richness and stronger-candidate count
- aggregate number and total weight of `CASH_PREFERRED` rows
- Portfolio Policy cash state and deployment capacity

No single current reason code provides the distinction.

### Where is the distinction lost?

The distinction is first lost when `_interaction_result_for_quality()` maps broad `CAUTIOUS_DEPLOYMENT` or `GRADUAL_REDEPLOYMENT` marginal cases to one shared `CASH_PREFERRED` result. It becomes operationally harmful at `_canonical_multi_allocation_deployment_set()`, where post-G83 non-bootstrap `CASH_PREFERRED` is consumed as unconditional zero-security deferral.

### Is G80 contradicted?

No. G80 remains valid: plateau weak-tail `CASH_PREFERRED` rows should not consume capital merely because Cash is residual. G84 shows that the G81/G83 repair overgeneralized the weak-tail protection to normal non-bootstrap participation rows.

## Not Executed

CODE_CHANGED = NO

CONFIG_CHANGED = NO

THRESHOLD_WEIGHT_TUNING = NO

MARKET_QUALITY_CHANGED = NO

RISK_PACING_CHANGED = NO

CANDIDATE_RANKING_CHANGED = NO

FRESH_RUN_EXECUTED = NO

RESUME_EXECUTED = NO

REPLAY_EXECUTED = NO

LONG_HISTORICAL_EXECUTED = NO

FUTURE_INPUT_COUNT = 0

HISTORICAL_OUTCOME_PARAMETER_SELECTION_COUNT = 0

## Next

The next task should repair only the final PC partition semantic for non-bootstrap `CASH_PREFERRED`:

```text
normal participation-valid CASH_PREFERRED
vs
weak-tail CASH_PREFERRED
```

The repair should reuse existing row-level and opportunity-set evidence, preserve G81 weak-tail Cash protection, preserve G83 bootstrap participation, and avoid new thresholds, BUY filters, Market Quality redesign, or Historical-outcome tuning.
