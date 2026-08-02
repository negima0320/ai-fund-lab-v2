# Phase24-C Low Opportunity Capacity and Market Context Override Investigation

Task ID: `Phase24-C`

Task Name: `Low Opportunity Capacity and Market Context Override Investigation`

Report date: 2026-07-31

Target run: `reports/runtime_tests/runs/runtime-test-historical-smoke-20260730T211110605880Z`

Primary target: `2022-07-07`, symbol `94320`

## 1. Primary Judgment

`PHASE24_C_MARKET_CONTEXT_HARD_OVERRIDE_CONFIRMED`

`2022-07-07`の`target_position_count=0`は、Opportunityの件数不足や`94320`のscore不足ではなく、Dynamic Position Count内部式で `BEAR + WEAK + strategy_minimum_position_count=0` が実質的に0配備へ落ちるために発生した。

Supporting findings:

- Opportunity capacity itself is not low in the canonical position-count path: `resolved_candidate_capacity=50`, `resolved_opportunity_capacity=50`, `meaningful_allocation_position_count=50`.
- Opportunity rank/score is not directly consumed by the Portfolio Policy position-count calculation.
- The `internal_dynamic_cash_exposure:low_opportunity_capacity` reason code is produced by Dynamic Cash Exposure using legacy field names `available_opportunity_count` / `valid_opportunity_count`; it does not read canonical `opportunity_capacity_count`. This makes the reason misleading for the investigated run because the Policy artifact also reports `resolved_opportunity_capacity=50`.
- Runtime correctness remains aligned; the issue is Strategy/Policy design and observability consistency, not Runtime Planning.

## 2. Executive Summary

Phase24-B identified that `94320` was `BUY_ELIGIBLE` and Opportunity Rank 1 on `2022-07-07`, but Portfolio Policy emitted:

```text
target_position_count = 0
deployment_posture = PAUSE
```

Phase24-C decomposes why.

The canonical owner of the final published `target_position_count` is Portfolio Policy, but the internal calculation is delegated to `dynamic_position_count.build_dynamic_position_count_payload()` and `_decide_counts()`. The formula for `2022-07-07` is:

```text
base_target = regime_rules["BEAR"] = 1
breadth_delta = breadth_rules["WEAK"].target_delta = -2
volatility_delta = volatility_rules["NORMAL"].target_delta = 0
uncertainty_delta = uncertainty_rules["LOW"].target_delta = 0
minimum = min(strategy_minimum_position_count=0, meaningful_capacity=50) = 0
raw_target = max(1 - 2 + 0 + 0, 0) = 0
target_position_count = min(raw_target, meaningful_capacity) = 0
```

On `2022-07-08`, only the trend regime changed materially:

```text
base_target = regime_rules["RANGE"] = 3
breadth_delta = -2
raw_target = 1
target_position_count = 1
```

Therefore, the 0 -> 1 decision difference is explained by `trend_regime: BEAR -> RANGE`, not by stronger Opportunity quality. In fact, `94320`'s top score was lower on `2022-07-08` (`0.3835215`) than on `2022-07-07` (`0.4255533`).

## 3. Reviewed Documents and Evidence

Required reports:

- `docs/phase_reports/phase24_b_p24_gap01_zero_deployment_root_cause_investigation.md`
- `docs/phase_reports/phase24_a_performance_evaluation_contract.md`
- `docs/phase_reports/phase23_to_phase24_chatgpt_handoff.md`
- `docs/phase_reports/phase23_final_summary_and_phase24_handoff.md`
- `docs/phase_reports/phase23_bv_phase21_design_conformance_full_architecture_runtime_evidence_closure_review.md`
- `docs/01_requirements/phase_roadmap.md`

Canonical design / implementation sources:

- `docs/03_ai_design/market_context_design.md`
- `docs/03_ai_design/portfolio_manager_policy_design.md`
- `docs/03_ai_design/opportunity_ai_design.md`
- `docs/03_ai_design/capital_deployment_design.md`
- `docs/02_architecture/strategy_architecture_v1.md`
- `docs/02_architecture/portfolio_construction_and_position_sizing_contract.md`
- `src/ai_fund_lab_v2/strategy/portfolio_policy.py`
- `src/ai_fund_lab_v2/strategy/dynamic_position_count.py`
- `src/ai_fund_lab_v2/strategy/dynamic_cash_exposure.py`
- `src/ai_fund_lab_v2/strategy/portfolio_construction.py`
- `src/ai_fund_lab_v2/strategy/position_sizing.py`
- `configs/strategy/portfolio_policy.json`
- `configs/strategy/dynamic_position_count.json`
- `configs/strategy/dynamic_cash_exposure.json`

Runtime evidence:

- `reports/runtime_tests/runs/runtime-test-historical-smoke-20260730T211110605880Z/daily/2022-07-07/strategy/market_context.json`
- `reports/runtime_tests/runs/runtime-test-historical-smoke-20260730T211110605880Z/daily/2022-07-07/strategy/portfolio_policy.json`
- `reports/runtime_tests/runs/runtime-test-historical-smoke-20260730T211110605880Z/daily/2022-07-07/strategy/portfolio_construction.json`
- `reports/runtime_tests/runs/runtime-test-historical-smoke-20260730T211110605880Z/daily/2022-07-07/strategy/position_sizing.json`
- `reports/runtime_tests/runs/runtime-test-historical-smoke-20260730T211110605880Z/daily/2022-07-07/strategy/runtime_planning.json`
- `.runtime/runtime_state/buy_ai/2022-07-07/candidate_decisions.json`
- `.runtime/runtime_state/buy_ai/2022-07-07/opportunity_rankings.json`
- `.runtime/runtime_state/buy_ai/2022-07-08/candidate_decisions.json`
- `.runtime/runtime_state/buy_ai/2022-07-08/opportunity_rankings.json`
- `reports/runtime_tests/runs/runtime-test-historical-smoke-20260730T211110605880Z/daily/2022-07-08/execution/fills.json`

Read-only commands executed:

| Command scope | Result | Mutation |
|---|---|---|
| `sed`, `rg`, `find`, `jq`, `nl` on docs/src/config/reports | Exit code 0 except expected missing standalone artifact probes | None |
| `jq empty` planned for final JSON validation | Schema-level JSON parse only | None |

No Runtime execution, fresh-run, J-Quants fetch, code change, config change, threshold change, or Strategy parameter change was performed.

## 4. Canonical Owner of low_opportunity_capacity

There are two distinct owners that must not be conflated:

| Concept | Canonical owner | Implementation | Output |
|---|---|---|---|
| Final `target_position_count` | Portfolio Policy | `portfolio_policy._resolve_internal_portfolio_policy()` calls `dynamic_position_count.build_dynamic_position_count_payload()` | `portfolio_policy.json.target_position_count` |
| Position-count opportunity capacity | Dynamic Position Count internal resolver, materialized into Portfolio Policy | `dynamic_position_count.resolve_capacity_count()` and `_decide_counts()` | `resolved_candidate_capacity`, `resolved_opportunity_capacity`, `meaningful_allocation_position_count` |
| `low_opportunity_capacity` reason code | Dynamic Cash Exposure internal resolver | `dynamic_cash_exposure._decide()` | `internal_dynamic_cash_exposure:low_opportunity_capacity` reason and cash/exposure deltas |

Important:

`low_opportunity_capacity` is not the reason that makes `target_position_count=0` on `2022-07-07`. The final count becomes zero in Dynamic Position Count because `BEAR` base target plus `WEAK` breadth delta reaches zero with configured minimum zero.

## 5. Calculation and Threshold

### Position Count Formula

Source:

- `src/ai_fund_lab_v2/strategy/dynamic_position_count.py:906-985`
- `configs/strategy/dynamic_position_count.json:5-64`

Confirmed formula:

```text
target = regime_rules[trend_regime]
target += breadth_rules[market_breadth].target_delta
target += volatility_rules[volatility_regime].target_delta
target += uncertainty_rules[uncertainty].target_delta

meaningful_capacity =
    min(available_candidate_count, available_opportunity_count)

if risk_posture == RISK_ON
   and entry_posture == EXPAND
   and market_breadth == STRONG:
    target = meaningful_capacity

minimum =
    min(strategy_minimum_position_count, meaningful_capacity)

raw_target =
    max(target, minimum)

capacity_limited_target =
    min(raw_target, meaningful_capacity)

target_position_count =
    max(minimum if capacity_limited_target >= minimum else 0,
        capacity_limited_target)
```

For `2022-07-07`:

| Input | Value | Threshold / Rule | Contribution | Evidence |
|---|---:|---|---:|---|
| `trend_regime` | `BEAR` | `regime_rules.BEAR = 1` | `+1 base` | `market_context.json`, `dynamic_position_count.json` config |
| `market_breadth` | `WEAK` | `breadth_rules.WEAK.target_delta = -2` | `-2` | `market_context.json`, config |
| `volatility_regime` | `NORMAL` | `volatility_rules.NORMAL.target_delta = 0` | `0` | `market_context.json`, config |
| `uncertainty` | `LOW` | `uncertainty_rules.LOW.target_delta = 0` | `0` | `portfolio_policy.json`, config |
| `strategy_minimum_position_count` | `0` | minimum is configurable | floors at `0` | `configs/strategy/dynamic_position_count.json` |
| `resolved_candidate_capacity` | `50` | target must not exceed candidates | not binding | `portfolio_policy.json` |
| `resolved_opportunity_capacity` | `50` | target must not exceed opportunities | not binding | `portfolio_policy.json` |
| `meaningful_allocation_position_count` | `50` | downstream capacity | not binding | `portfolio_policy.json` |
| Result | `0` | `max(1 - 2, 0)` | zero count | `portfolio_policy.json` |

### `low_opportunity_capacity` Formula

Source:

- `src/ai_fund_lab_v2/strategy/dynamic_cash_exposure.py:459-475`
- `configs/strategy/dynamic_cash_exposure.json:40-44`

Confirmed formula:

```text
low_opportunity_capacity =
    int(opportunity.available_opportunity_count
        or opportunity.valid_opportunity_count
        or 0)
    < low_opportunity_count_threshold

low_opportunity_count_threshold = 3

if low_opportunity_capacity:
    cash += 0.08
    exposure += -0.08
    reason_codes += ["low_opportunity_capacity"]
```

Key finding:

The Opportunity summary adapter emits `opportunity_capacity_count` and `consumer_eligible_rows`, but Dynamic Cash Exposure checks only `available_opportunity_count` and `valid_opportunity_count`. Therefore, when those legacy fields are absent, the cash/exposure logic falls back to `0` and emits `low_opportunity_capacity` even though Portfolio Policy reports canonical `resolved_opportunity_capacity=50`.

This reason-code path affects cash/exposure (`0.46` on BEAR days, `0.64` on RANGE day) but is not the root cause of position count zero.

## 6. Input Field Inventory

| Input | Used by position count? | Used by cash/exposure low-opportunity reason? | Evidence |
|---|---|---|---|
| Market Context | Yes: `trend_regime`, `market_breadth`, `volatility_regime`, `confidence`, `uncertainty` | Yes: trend/breadth/volatility | `dynamic_position_count.py`, `dynamic_cash_exposure.py` |
| Candidate count | Yes via `candidate_capacity_count` / aliases | No direct low-opportunity trigger | `resolve_capacity_count()` |
| BUY_ELIGIBLE count | No direct Policy count input | No | BUY_ELIGIBLE appears in Runtime Planning, downstream of Policy |
| Opportunity count | Yes via `opportunity_capacity_count` / aliases | Intended, but DCE only reads `available_opportunity_count` / `valid_opportunity_count` | `dynamic_position_count.py:783-784`, `dynamic_cash_exposure.py:472` |
| Opportunity Rank | No | No | No code path found into Policy count |
| Opportunity score | No | No | No code path found into Policy count or DCE low-opportunity check |
| Expected edge | No | No | Used in Opportunity artifact and Runtime Planning lineage only |
| Confidence | Market/Policy confidence only for Policy confidence; row-level opportunity confidence no | No | `_decide_counts()` |
| Score distribution | No | No | No code path found |
| Top-N breadth | No direct score/rank breadth | No | No code path found |
| Current position count | Yes, only for posture comparison | No | `_decide_counts()` |
| Cash | No | Yes for cash/exposure amount construction, not low-opportunity boolean | `dynamic_cash_exposure.py` |
| Exposure | No | Yes as output/calculation context | `dynamic_cash_exposure.py` |
| Risk constraint | Yes: `risk_posture`, `entry_posture` constrain status; config caps exist but are not applied in `_decide_counts()` target math | Yes: risk posture deltas | Source code |

Answers to central questions:

| Q | Answer |
|---|---|
| Q1 | Final owner is Portfolio Policy; internal owner for count capacity is Dynamic Position Count; reason-code owner for `low_opportunity_capacity` is Dynamic Cash Exposure. |
| Q2 | Count is computed by `dynamic_position_count._decide_counts()` using config `configs/strategy/dynamic_position_count.json`; `low_opportunity_capacity` reason is computed by `dynamic_cash_exposure._decide()` using `configs/strategy/dynamic_cash_exposure.json`. |
| Q3 | Count uses Market Context, Candidate count, Opportunity capacity count, current position count, risk/entry posture, uncertainty. It does not use rank, score, expected edge, row confidence, score distribution, or BUY_ELIGIBLE count. |
| Q4 | For count: BUY_ELIGIBLE can exist and target still becomes zero when Market Context deltas produce raw target zero and minimum is zero. For the reason code: it fires when DCE sees `available_opportunity_count` / `valid_opportunity_count` missing or below 3. |
| Q5 | Yes. `BEAR` base `1` plus `WEAK` delta `-2` produces zero regardless of opportunity quality/count when `strategy_minimum_position_count=0`. |
| Q6 | No. Rank 1 is not a direct input to Portfolio Policy position-count calculation. |
| Q7 | `0.4255533` was preserved downstream in Portfolio Construction/Runtime Planning lineage, but not evaluated by Policy count logic. |
| Q8 | Exposure and count are calculated by separate internal resolvers. Exposure ratio is an upper/target capital posture, not a deployment obligation; deployment becomes `PAUSE` when count is zero. |
| Q9 | Design says Market Context influences posture/reasons/bias and should not directly decide symbol BUY/SELL. Current implementation uses it as a portfolio-level capacity rule that can reduce new-entry count to zero. |
| Q10 | Broad boundary conformance is aligned, but Phase24 performance adequacy and DCE reason-code consistency are not validated. |

## 7. 2022-07-07 Opportunity Breadth and Quality

| Metric | Value | Authority | Interpretation |
|---|---:|---|---|
| Candidate evaluated count | `50` | `.runtime/runtime_state/buy_ai/2022-07-07/candidate_decisions.json` | Candidate breadth was not thin. |
| Candidate eligible/capacity count | `50` | `portfolio_policy.json.resolved_candidate_capacity` | Policy count resolver saw capacity. |
| Opportunity input/ranking count | `50` | `.runtime/runtime_state/buy_ai/2022-07-07/opportunity_rankings.json` | Opportunity artifact had full 50 ranking rows. |
| Resolved opportunity capacity | `50` | `portfolio_policy.json.resolved_opportunity_capacity` | Dynamic Position Count saw canonical opportunity capacity. |
| BUY_ELIGIBLE count | `6` | `runtime_planning.json` | Six plans carried `BUY_ELIGIBLE`; all were NO_ORDER due zero quantity. |
| Top rank symbol | `94320` | Opportunity rankings / Runtime Planning | Focus symbol was top-ranked. |
| Top rank expected edge | `0.4255533` | Opportunity rankings / Runtime Planning | Positive and stronger than 07-08 top score. |
| Top rank confidence | `1.0` | Opportunity rankings | High row-level confidence, not used by Policy count. |
| Positive expected-edge count | `6` | Opportunity rankings | At least six positive opportunities existed. |
| Score min / mean / max | `-0.61536224 / -0.2810580664 / 0.4255533` | Opportunity rankings | Distribution is mixed/negative mean, but Policy did not use distribution. |
| Blank no-buy reason count | `6` | Opportunity rankings | Matches positive eligible-looking opportunities. |
| Nonblank no-buy reason count | `44` | Opportunity rankings | Mostly non-positive expected edge exclusions. |

Interpretation:

The investigated day is not a "candidate absent" or "opportunity absent" day. It is a "positive top opportunity exists, but Market Context-derived position-count rule sets deployable new positions to zero" day.

## 8. Market Context Override Analysis

Primary classification:

```text
Case B: BEAR / WEAK条件がOpportunity qualityより優先され、
target_position_count=0を強制する。
```

Supporting classifications:

```text
Case D: Opportunity情報の一部、特にscore/rank/expected edgeはPolicy position countへ渡っていない。
Case F: Phase21 boundary design is broadly followed, but performance adequacy is unvalidated.
```

Rejected or not primary:

```text
Case A: Opportunity qualityが高ければ1件以上の配備余地がある。
Case C: Market ContextとOpportunity breadthの双方を評価して今回だけ複合条件で0。
Case E: Opportunity情報は渡っているが閾値・重み付けが保守的すぎる。
```

Why:

- Opportunity breadth/capacity was `50`, so opportunity capacity did not bind.
- `94320` score was positive and top-ranked, but score/rank did not enter Policy count math.
- `BEAR + WEAK + minimum 0` alone explains the zero count.
- `2022-07-08` had weaker top score and fewer positive opportunities, yet moved to count 1 because `trend_regime` changed to `RANGE`.

## 9. 2022-07-07 vs 2022-07-08 Comparison

| Field | 2022-07-07 | 2022-07-08 | Difference | Decision impact |
|---|---:|---:|---|---|
| `trend_regime` | `BEAR` | `RANGE` | Base target `1 -> 3` | Primary driver of count `0 -> 1` |
| `market_breadth` | `WEAK` | `WEAK` | No change | Both days get `-2` breadth delta |
| `volatility_regime` | `NORMAL` | `NORMAL` | No change | No count delta |
| Market confidence | `0.981132542038` | `0.981296387927` | Nearly same | Not driver |
| Candidate count | `50` | `50` | No change | Not driver |
| Resolved opportunity capacity | `50` | `50` | No change | Not driver |
| BUY_ELIGIBLE count | `6` | `4` | Lower on 07-08 | Opposite of count increase |
| Opportunity rank 1 score | `0.4255533` | `0.3835215` | Lower on 07-08 | Score did not drive count |
| Positive score count | `6` | `4` | Lower on 07-08 | Quality breadth did not drive count |
| Score distribution mean | `-0.2810580664` | `-0.3082094172` | Lower on 07-08 | Not used by Policy count |
| `low_opportunity_capacity` reason | Present | Present | No change | DCE reason not count driver |
| `market_or_policy_risk_constrained` | Present | Absent | Removed on RANGE day | Confirms BEAR/CORRECTION risk constraint path |
| `target_position_count` | `0` | `1` | Increase by 1 | Main output difference |
| Cash reserve | `0.50` | `0.36` | Lower on 07-08 | Cash/exposure became less defensive |
| Target gross exposure | `0.46` | `0.64` | Higher on 07-08 | Exposure posture less defensive |
| Deployment posture | `PAUSE` | `DEFENSIVE_DEPLOYMENT` | New entry allowed | Derived from count/exposure/cash |
| Target membership count | `0` | `1` | Increase by 1 | Portfolio Construction capacity opens |
| BUY_NEW execution | None | `BUY 94320 1100 @ 153.3` | First buy occurs | Execution followed opened capacity |

Conclusion:

The decisive change from zero deployment to one deployment was `trend_regime=BEAR` becoming `RANGE`. Opportunity quality did not improve; it weakened slightly.

## 10. target_position_count / target_gross_exposure Consistency

Observed on `2022-07-07`:

```text
target_gross_exposure_ratio = 0.46
target_position_count = 0
deployment_posture = PAUSE
```

Classification:

```text
A. exposure ratioは上限/target postureであり、実配備義務ではない
B. position countが0ならexposureは実質0で正常
C. Policy内部で別々に算出される
D. opportunity capacity reasonがcash/exposure側に残る
```

Not classified as a Runtime correctness gap.

Explanation:

- `target_position_count` comes from Dynamic Position Count.
- `target_gross_exposure_ratio` comes from Dynamic Cash Exposure.
- Portfolio Policy deployment posture explicitly returns `PAUSE` when `target_position_count <= 0` even if exposure ratio is positive.
- Portfolio Construction later makes `target_weight=0.0` when `target_position_count=0`, so actual allocation remains zero.

There is an observability/Policy consistency gap candidate: positive exposure target with zero count can confuse performance interpretation unless the report explicitly distinguishes exposure posture from deployable membership count.

## 11. Config and Hardcode Audit

| Setting / Rule | Value | Owner | Config Path | Hardcoded? | Runtime Active? |
|---|---|---|---|---|---|
| BEAR base count | `1` | Dynamic Position Count | `configs/strategy/dynamic_position_count.json` | Configurable | Yes, via Portfolio Policy internal resolver |
| CORRECTION base count | `2` | Dynamic Position Count | same | Configurable | Yes |
| RANGE base count | `3` | Dynamic Position Count | same | Configurable | Yes |
| WEAK breadth delta | `-2` | Dynamic Position Count | same | Configurable | Yes |
| NORMAL volatility delta | `0` | Dynamic Position Count | same | Configurable | Yes |
| LOW uncertainty delta | `0` | Dynamic Position Count | same | Configurable | Yes |
| Minimum target position count | `0` | Dynamic Position Count | same | Configurable | Yes |
| Candidate capacity field | `available_candidate_count` config label; implementation accepts canonical `candidate_capacity_count` | Dynamic Position Count | same + source code | Mixed | Yes |
| Opportunity capacity field | `available_opportunity_count` config label; implementation accepts canonical `opportunity_capacity_count` | Dynamic Position Count | same + source code | Mixed | Yes |
| Target must not exceed candidates | `true` | Dynamic Position Count | same | Configurable | Yes |
| Target must not exceed opportunities | `true` | Dynamic Position Count | same | Configurable | Yes |
| RISK_ON/EXPAND/STRONG full capacity override | condition only | Dynamic Position Count | source code | Hardcoded | Yes |
| Risk constrained status for BEAR/CORRECTION | BEAR or CORRECTION marks `MARKET_RISK_CONSTRAINED` | Dynamic Position Count | source code | Hardcoded | Yes |
| Deployment posture PAUSE | `target_position_count <= 0 OR exposure <= 0` | Portfolio Policy | source code | Hardcoded | Yes |
| Cash baseline | `0.20` | Dynamic Cash Exposure | `configs/strategy/dynamic_cash_exposure.json` | Configurable | Yes |
| Max cash | `0.50` | Dynamic Cash Exposure | same | Configurable | Yes |
| Gross exposure baseline | `0.80` | Dynamic Cash Exposure | same | Configurable | Yes |
| BEAR cash/exposure delta | `+0.18 / -0.18` | Dynamic Cash Exposure | same | Configurable | Yes |
| WEAK breadth cash/exposure delta | `+0.08 / -0.08` | Dynamic Cash Exposure | same | Configurable | Yes |
| Low opportunity threshold | `3` | Dynamic Cash Exposure | same | Configurable | Yes |
| Low opportunity cash/exposure delta | `+0.08 / -0.08` | Dynamic Cash Exposure | same | Configurable | Yes |
| DCE low opportunity input fields | `available_opportunity_count` or `valid_opportunity_count` | Dynamic Cash Exposure | source code | Hardcoded | Yes |
| Opportunity rank/score Policy count input | Not used | Portfolio Policy / DPC | source code | Hardcoded absence | Yes |
| Specific date/symbol/run branch | None found in production code/config | N/A | `src/`, `scripts/`, `config`, `schemas`, `tests` search | N/A | N/A |

No date-specific, symbol-specific, or run-id-specific production branch was found for `2022-07-07`, `2022-07-08`, `94320`, or the target run id. Matches found were test fixtures only.

## 12. Phase21 Design Conformance

Conforms:

- Market Context is consumed as portfolio-level posture/risk evidence, not as symbol-level BUY/SELL authority.
- Opportunity Rank 1 is not treated as forced BUY.
- Portfolio Policy owns target position count.
- Portfolio Construction owns target membership/weight and respects `target_position_count=0`.
- Position Sizing and Runtime Planning correctly propagate zero allocation.

Potential design/performance tension:

- Phase21 design says Market Context influences reason/bias and does not mechanically override individual momentum/opportunity. Current implementation does not symbol-level override, but it can portfolio-level hard-zero all new entries via `BEAR + WEAK + minimum 0`. That is boundary-conformant, but its performance suitability is unproven.
- The `low_opportunity_capacity` reason code is inconsistent with canonical opportunity capacity evidence because Dynamic Cash Exposure does not read `opportunity_capacity_count`.

## 13. Runtime Correctness Judgment

`PASS_FOR_INVESTIGATED_PATH`

Runtime lineage is coherent:

```text
Opportunity Rank 1 / BUY_ELIGIBLE
-> Portfolio Policy target_position_count = 0
-> Portfolio Construction target_weight = 0.0
-> Position Sizing quantity_delta_candidate = 0
-> Runtime Planning NO_ORDER
```

No evidence was found for:

- Runtime Planning bug
- Authority missing
- Cash inconsistency
- Ledger inconsistency
- Future leakage
- Safety violation
- Source repair need in this task

## 14. Strategy Performance Judgment

`STRATEGY_PERFORMANCE_REVIEW_REQUIRED`

The current policy is conservative in a way that can suppress high-ranked positive opportunities:

- `2022-07-07`: Rank 1 score `0.4255533`, positive count `6`, but count `0`.
- `2022-07-08`: Rank 1 score `0.3835215`, positive count `4`, count `1`, BUY executed.

This means the Strategy is more sensitive to market regime label (`BEAR` vs `RANGE`) than to top opportunity quality in this window. That may be desirable risk control, but Phase24 performance evidence must validate it.

## 15. Root Cause

Root cause:

```text
Dynamic Position Count config and implementation make BEAR + WEAK breadth
produce target_position_count = 0 when strategy_minimum_position_count = 0,
regardless of top Opportunity rank/score.
```

Detailed path:

```text
Market Context
  trend_regime = BEAR
  market_breadth = WEAK
  volatility_regime = NORMAL

↓

Portfolio Policy internal Dynamic Position Count
  base BEAR count = 1
  WEAK breadth delta = -2
  NORMAL volatility delta = 0
  LOW uncertainty delta = 0
  minimum position count = 0
  meaningful capacity = 50

↓

target_position_count = 0
capacity status includes market_or_policy_risk_constrained

↓

Portfolio Policy deployment_posture = PAUSE

↓

Portfolio Construction / Position Sizing / Runtime Planning
  target_weight = 0
  quantity_delta_candidate = 0
  NO_ORDER
```

Secondary root cause candidate:

```text
Dynamic Cash Exposure emits low_opportunity_capacity because it reads
available_opportunity_count / valid_opportunity_count but not canonical
opportunity_capacity_count.
```

This secondary issue affects reason-code truthfulness and cash/exposure posture, but does not explain the zero position count because canonical resolved opportunity capacity is 50.

## 16. Improvement Hypotheses

No implementation was performed.

| Hypothesis | Changed Component | Expected Benefit | Risk | Evaluation Metric | Required Windows |
|---|---|---|---|---|---|
| H1: Market Context sets an upper bound, but high-quality top opportunities allow minimum exploratory position. | Portfolio Policy / Dynamic Position Count | Reduce missed top-ranked positive opportunities and cash drag. | Higher drawdown in true risk-off regimes. | Cash utilization, total return, max drawdown, relative return, trade count. | 10BD, 20BD, 60BD, 200BD, 1Y. |
| H2: Separate WEAK breadth from absolute zero capacity. | Dynamic Position Count | Defensive posture remains, but BEAR/WEAK does not always force zero. | Entering during broad market weakness. | Drawdown, entry quality, win rate, benchmark delta. | Regime-segment 60BD/200BD. |
| H3: Use top score / expected edge / confidence in capacity calculation. | Portfolio Policy | Align count with Opportunity quality rather than only market regime. | Overfitting to short-horizon score scale. | Opportunity capture rate, payoff ratio, Sortino, turnover. | 20BD, 60BD, 200BD, out-of-period. |
| H4: Permit minimum target_position_count=1 in BEAR unless crash/risk-off/high-volatility. | Dynamic Position Count config | Avoid total zero deployment in non-crash weak regimes. | Strategy may buy too early in downtrends. | Max drawdown, loss attribution, cash utilization. | 60BD, 200BD, 1Y, 3Y. |
| H5: Two-axis matrix: Market Context x Opportunity Quality. | Portfolio Policy | More explicit governance and attribution. | Increased complexity and more parameters. | Attribution by regime, entry quality, concentration, return/drawdown. | 200BD, 1Y, 3Y. |
| H6: Observability-only repair for DCE low opportunity field alignment. | Observability / Policy reason contract | Make reason codes match canonical capacity evidence. | Schema/report churn. | Reason-code consistency, source hash lineage, no behavior change. | Unit/regression only plus next baseline read. |

Recommended priority:

1. H6 as a read-only/observability contract clarification task before behavioral experiments.
2. H1 or H5 as controlled Strategy experiments after Phase24 baseline attribution.

## 17. Risks

| Risk | Detail | Mitigation |
|---|---|---|
| Misreading `low_opportunity_capacity` as position-count root cause | It appears in Portfolio Policy reasons but comes from Dynamic Cash Exposure. | Keep count and cash/exposure resolver responsibilities separate. |
| Over-optimizing to one 10BD period | 07-07/07-08 contrast is diagnostic, not performance proof. | Follow Phase24-A windows and one-hypothesis-one-change rule. |
| Confusing Runtime correctness with Strategy quality | Runtime correctly propagated zero quantity. | Treat this as Strategy performance evaluation. |
| Score scale overfitting | Opportunity score is model-specific and calibration-sensitive. | Use out-of-period windows and attribution metrics. |
| Reason-code truthfulness | DCE low opportunity reason does not align with canonical `opportunity_capacity_count`. | Treat as observability/contract gap candidate, not immediate behavior change. |

## 18. Recommended Next Task

Recommended next task:

```text
Phase24-D Portfolio Policy Opportunity Quality Input Contract and Observability Alignment
```

Purpose:

Before changing behavior, formally decide whether Portfolio Policy should consume Opportunity rank/score/positive count, and separately clarify/repair the `low_opportunity_capacity` reason-code contract so Dynamic Cash Exposure uses the same canonical capacity fields as Dynamic Position Count.

