# Adaptive BUY Quality Authority

Canonical specification: `docs/02_architecture/adaptive_buy_quality_authority.md`

Status: IMPLEMENTED_PHASE26_H

Applies to: Production, Demo, Historical

## 1. Definition

Adaptive BUY Quality Authority is the Production-common Strategy authority that evaluates how trustworthy and allocation-capable a BUY opportunity is at the decision business date.

It uses only PIT information available at the decision time:

```text
Opportunity / Candidate population
Market Context
Signal Reliability
Execution Feasibility
Portfolio Fit
```

Adaptive BUY Quality is not a predicted return, win probability, raw rank, raw score threshold, fixed position-count gate, Submit permission, Safety hard maximum, or broker execution authority.

The authority may produce:

```text
BUY_ELIGIBLE
BUY_REDUCED_ALLOCATION
BUY_REVIEW_REQUIRED
BUY_REJECTED
```

## 2. Producer

Canonical producer:

```text
Production Strategy BUY Quality Resolver
```

Canonical artifact:

```text
buy_quality_decision.v1
```

The producer must be common for Production, Demo, and Historical. Historical-only branches, profile-specific behavior, test-result feedback, Paper Ledger feedback, and future information are prohibited.

## 3. Primary Inputs

| Input | Authority | Use |
|---|---|---|
| Opportunity Ranking | Opportunity Ranking Authority | Raw relative signal, rank lineage, population distribution |
| Candidate Decision | Candidate Universe Authority | Candidate confidence and eligibility lineage |
| Market Context | Market Context Evidence Authority | Regime, breadth, trend, volatility, confidence, uncertainty |
| Portfolio Policy | Portfolio-level Target / Permission / Posture Authority | Exposure/cash posture reference; not duplicated as individual quality |
| Current Portfolio | Runtime Current / Portfolio State Authority | Current weight, sector concentration, active campaign, gross exposure |
| Data Readiness | Runtime Data Readiness Authority | Required input availability and temporal eligibility |
| Corporate Event | Corporate Event Fact Authority | PIT event risk and actionability |
| Execution Feasibility | Market Evidence / Runtime Planning feasibility authorities | Reference price, lot, liquidity, order feasibility evidence |

## 4. Component Contracts

### 4.1 Relative Opportunity Quality

Purpose: evaluate whether a symbol is strong within its same-business-date opportunity population without treating raw score as an absolute return.

Required inputs:

```text
opportunity_buy_rank
runtime_opportunity_score
daily opportunity population
source_opportunity_id / row hash
```

Recommended metrics:

```text
score_percentile
robust_z_score
score_minus_daily_median
score_minus_next_rank
score_minus_top_k_mean
daily_best_score
daily_median_score
positive_score_ratio
score_dispersion
candidate_population_size
```

Contract:

- Rank alone must not create high quality.
- Rank 1 in a weak population must not become `FULL_ALLOCATION_ELIGIBLE` by rank alone.
- Low positive raw score may pass raw Opportunity Eligibility but must still be assessed by Adaptive BUY Quality.
- Negative raw score is valid raw evidence, but cannot be silently converted into positive quality.

### 4.2 Market Context Quality Modifier

Purpose: adjust confidence in individual BUY admission and allocation strength based on market evidence.

Inputs:

```text
market trend
breadth
volatility / risk posture
market context confidence
market context uncertainty
sector / benchmark context when available
```

Contract:

- Market Context enum labels may explain the state but must not be the only calculation.
- Unfavorable market context must not automatically reject every outstanding opportunity.
- Favorable market context must not rescue a weak opportunity by itself.
- If Portfolio Policy already uses Market Context to set total exposure, the Quality modifier must not duplicate the same exposure effect. The modifier is symbol-level trust/allocation strength, not total portfolio exposure.

### 4.3 Signal Reliability

Purpose: determine whether the opportunity signal is trustworthy enough to use.

Inputs:

```text
model confidence
feature completeness
feature freshness
accepted generation binding
temporal authority
data readiness
calibration status
population stability
candidate confidence
```

Contract:

- `calibration_applied=false` means raw score must not be interpreted as calibrated expected return.
- Calibration is an extension point, not a prerequisite for relative quality.
- Missing accepted generation binding, stale features, or temporal conflict is `BUY_REVIEW_REQUIRED` or `BUY_REJECTED`, not neutral pass.

### 4.4 Execution Feasibility

Purpose: reduce or reject a theoretically attractive opportunity when safe order materialization is not evidenced.

Inputs when available:

```text
liquidity
turnover / volume
lot size
reference price confidence
execution price authority
estimated spread / market impact
price limit proximity
corporate event / earnings risk
order feasibility
```

Contract:

- Do not infer unavailable market microstructure evidence.
- Missing required price/lot/order feasibility evidence is fail-closed.
- Non-critical unavailable evidence may produce conservative reduction if the component status is explicit.

### 4.5 Portfolio Fit

Purpose: determine whether adding or increasing the symbol fits the current portfolio.

Inputs:

```text
current position weight
sector concentration
existing exposure
same-symbol active campaign
active pending
cash state
gross exposure after BUY
single-name weight after BUY
portfolio policy risk posture
```

Contract:

- Portfolio Fit is not a fixed position-count authority.
- It may reduce or reject concentration and duplicate-risk cases.
- Safety hard maximum remains separate and final; Quality must not weaken it.
- Prior realized PnL, Paper Ledger result, and Historical Test outcome are prohibited inputs.

## 5. Composite Method

The composite method must produce normalized `quality_score` in the range `0.0` to `1.0`.

The score means:

```text
0.0 = unusable for Production BUY allocation under this Quality contract
1.0 = highest trust/allocation capability under this Quality contract
```

It does not mean win probability, expected return, or fixed notional.

The initial implementation may use a transparent weighted blend, but only if each component has explicit status, weight, source authority, and missing-evidence behavior. A simple product is not required and must not be assumed by consumers.

Composite constraints:

- critical component `BLOCK` or `REVIEW_REQUIRED` cannot be hidden by other high component scores
- neutral treatment is allowed only for component status `NOT_REQUIRED`
- raw `runtime_opportunity_score` must not be silently promoted to `allocation_quality_score`
- no fixed Rank N cap
- no ungrounded fixed raw-score threshold
- no target-position-count decision reconnect

### 5.1 Phase26-H Implemented Scoring Method

Phase26-H implements a transparent weighted blend in:

```text
src/ai_fund_lab_v2/strategy/buy_quality.py
```

The producer calculates five component scores, each normalized to `0.0` through `1.0`, then combines them as:

```text
quality_score =
    0.35 * relative_opportunity_quality
  + 0.15 * market_context_quality_modifier
  + 0.25 * signal_reliability
  + 0.10 * execution_feasibility
  + 0.15 * portfolio_fit
```

Component weights are part of the artifact as `component_weights`.

The implemented component weights are:

| Component | Weight | Meaning |
|---|---:|---|
| `relative_opportunity_quality` | `0.35` | How strong the opportunity is against the same-business-date opportunity population |
| `market_context_quality_modifier` | `0.15` | Market evidence confidence modifier for BUY quality, not portfolio exposure duplication |
| `signal_reliability` | `0.25` | Accepted Generation, temporal, confidence, completeness, and calibration reliability |
| `execution_feasibility` | `0.10` | Liquidity, downside, and corporate-event feasibility evidence |
| `portfolio_fit` | `0.15` | Current weight, single-name room, exposure posture reference, and active pending fit |

The weighted blend is only used after critical component checks. Critical evidence cannot be hidden by a high weighted average.

Critical components are:

```text
relative_opportunity_quality
signal_reliability
```

If critical evidence is missing, conflicted, stale, future-dated, or otherwise not `PASS`, the decision is `REVIEW_REQUIRED` or `REJECT` with `quality_allocation_adjustment=0.0`.

### 5.2 Relative Opportunity Quality Implementation

Relative Opportunity Quality intentionally avoids treating raw opportunity score as an absolute return or using rank as a fixed gate.

For the same-business-date opportunity population, Phase26-H calculates:

```text
percentile = count(population_score <= symbol_score) / population_size
median = daily population median
MAD = median(abs(score - median))
robust_z = (symbol_score - median) / (1.4826 * MAD)
robust_norm = sigmoid(clamp(robust_z, -6, 6))
positive_ratio = count(score > 0) / population_size
best = max(population_score)
dispersion = max(population_score) - min(population_score)
magnitude = max(best, 0) / (1 + abs(best) + abs(median))
dispersion_norm = dispersion / (1 + dispersion)
population_strength =
    0.35 * positive_ratio
  + 0.45 * magnitude
  + 0.20 * dispersion_norm
relative_opportunity_quality =
    0.45 * percentile
  + 0.25 * robust_norm
  + 0.30 * population_strength
```

The result is clamped to `0.0` through `1.0`.

Additional implemented guards:

- If population size is below `5`, the relative component is capped at `0.62` and reason `small_population_conservative` is emitted.
- If the symbol is rank 1 but `population_strength < 0.45`, reason `rank1_weak_population_not_full` is emitted.
- Rank is retained as lineage and explanation, but not as a fixed top-N selector.

This means:

- Rank 1 in a weak population can still be eligible, but not automatically full allocation.
- A low positive raw score can be BUY-eligible upstream but still receive reduced or rejected quality.
- A strong outlier in a weak market can still receive reduced or full allocation if the full component evidence supports it.

### 5.3 Market Context Quality Modifier Implementation

Market Context Quality Modifier uses continuous evidence instead of only enum labels:

```text
market_score =
    0.35 * market_confidence
  + 0.30 * breadth
  + 0.20 * trend_score
  + 0.15 * (1.0 - volatility_risk)
```

Implemented `trend_score` mapping:

| Trend state | Score |
|---|---:|
| `BULL`, `UPTREND`, `STRONG_UP` | `0.85` |
| `RANGE`, `NEUTRAL`, `BALANCED` | `0.60` |
| `BEAR`, `DOWNTREND`, `WEAK` | `0.35` |
| unknown | `0.55` |

Market Context missing is explicit `NOT_AVAILABLE` with conservative score `0.55`; it is not silent neutral evidence.

### 5.4 Signal Reliability Implementation

Signal Reliability verifies that the opportunity signal is usable as PIT evidence:

```text
signal_reliability =
    (0.60 * min(opportunity_confidence, candidate_confidence)
   + 0.40 * feature_completeness)
    * calibration_factor
```

Implemented `calibration_factor`:

| Calibration evidence | Factor |
|---|---:|
| `calibration_applied=true` | `1.00` |
| `calibration_applied=false` or missing | `0.85` |

If Accepted Generation binding is not `PASS`, `BOUND`, or `COMMITTED`, the component is `REVIEW_REQUIRED` and score `0.0`.

If source business date or feature date violates the requested business date, the component is `REVIEW_REQUIRED` and score `0.0`.

Calibration missing does not prohibit relative quality, but it prevents interpreting raw score as calibrated expected return and applies the reliability penalty.

### 5.5 Execution Feasibility Implementation

Execution Feasibility uses available liquidity, downside, and corporate-event evidence:

```text
execution_feasibility =
    0.65 * liquidity
  + 0.35 * (1.0 - downside_risk)
  - corporate_event_penalty
```

If price volatility / liquidity evidence is unavailable, the component is explicit `NOT_AVAILABLE` with conservative score `0.70`.

Corporate event evidence that is present but not `PASS` applies a `0.10` penalty and emits a reason code.

### 5.6 Portfolio Fit Implementation

Portfolio Fit is a symbol-level fit score. It is not a position-count gate.

```text
concentration_room =
    1.0 - current_weight / single_name_weight_cap

portfolio_fit =
    0.70 * concentration_room
  + 0.30 * min(target_gross_exposure, 1.0)
  - pending_penalty
```

Implemented `pending_penalty`:

```text
0.35 if the same symbol already has active pending
0.00 otherwise
```

The score is clamped to `0.0` through `1.0`.

Safety hard maximum remains separate and final. Portfolio Fit must not weaken Safety.

### 5.7 Quality Band and Action Mapping

Implemented `quality_band` mapping:

| Band | Condition |
|---|---|
| `VERY_HIGH` | `quality_score >= 0.85` |
| `HIGH` | `quality_score >= 0.72` |
| `MEDIUM` | `quality_score >= 0.55` |
| `LOW` | `quality_score >= 0.35` |
| `UNUSABLE` | otherwise |

Implemented action mapping:

| Action | Condition | Allocation adjustment |
|---|---|---:|
| `FULL_ALLOCATION_ELIGIBLE` | `quality_score >= 0.72` and `relative_opportunity_quality >= 0.65` and no `rank1_weak_population_not_full` | `1.0` |
| `REDUCED_ALLOCATION_ONLY` | `quality_score >= 0.45` but full-allocation conditions are not met | `clamp(quality_score, 0.25, 0.85)` |
| `REJECT` | weighted score below reduced threshold or no-buy / non-positive / missing raw opportunity score | `0.0` |
| `REVIEW_REQUIRED` | critical evidence is unavailable or conflicted without a direct reject condition | `0.0` |

The `0.72` and `0.45` action boundaries are quality action boundaries, not raw opportunity-score thresholds. They are applied after multi-component normalization and critical evidence checks.

### 5.8 Implemented Sizing Consumption

Position Sizing consumes Adaptive BUY Quality as:

```text
post_quality_target_weight =
    resolved_target_weight * quality_allocation_adjustment
```

Where:

- `FULL_ALLOCATION_ELIGIBLE` uses adjustment `1.0`
- `REDUCED_ALLOCATION_ONLY` uses the artifact adjustment
- `REVIEW_REQUIRED` and `REJECT` use `0.0` for new BUY allocation

The notional base remains current total equity:

```text
target_notional = post_quality_target_weight * current_total_equity
```

No fixed yen table, fixed notional, position count substitution, or historical-only sizing path is introduced.

## 6. Output Contract

Artifact: `buy_quality_decision.v1`

Required fields:

```text
schema_version
business_date
symbol
quality_decision_id
quality_status
quality_score
quality_band
quality_action
quality_reason_codes
component_scores
component_statuses
component_weights
input_authority_refs
PIT_status
generated_at
producer
policy_version
source_opportunity_id
source_opportunity_hash
accepted_generation_binding
temporal_binding
future_information_used
historical_result_input_used
paper_ledger_input_used
```

Recommended `quality_band`:

```text
VERY_HIGH
HIGH
MEDIUM
LOW
UNUSABLE
REVIEW_REQUIRED
```

Recommended `quality_action`:

```text
FULL_ALLOCATION_ELIGIBLE
REDUCED_ALLOCATION_ONLY
REVIEW_REQUIRED
REJECT
```

## 7. Missing Evidence Contract

Missing evidence must not default to `quality_adjustment=1.0`.

| Missing evidence type | Behavior |
|---|---|
| Critical component missing | `BUY_REVIEW_REQUIRED` or `BUY_REJECTED` |
| Required authority conflict | `BUY_REVIEW_REQUIRED` or `BUY_REJECTED` |
| Non-critical component missing | explicit conservative reduction |
| Component not required | neutral with `NOT_REQUIRED` status |
| Calibration missing | raw-score absolute interpretation prohibited; relative quality may continue with reliability penalty/status |
| Market Context missing | fail-closed or reduced, never silent neutral |
| Reference price / lot feasibility missing for positive allocation | fail-closed before order materialization |

## 8. Quality-Sensitive Sizing

Position Sizing must preserve Current total equity as the capital base:

```text
Current total equity
  * Portfolio Policy exposure
  * Portfolio Construction base target weight
  * BUY Quality adjustment
  * Portfolio Fit adjustment
```

The formula is conceptual. Implementation may combine terms differently, but the authority boundaries must remain:

| Authority | Responsibility |
|---|---|
| Market Context | Portfolio-level exposure and contextual confidence |
| Portfolio Policy | total exposure / cash posture |
| Adaptive BUY Quality | individual opportunity admission and allocation strength |
| Portfolio Fit | concentration / compatibility adjustment |
| Position Sizing | notional and quantity candidate from accepted target allocation |
| Safety | hard block / hard maximum |

Quality must influence sizing continuously or by documented bands, but never by fixed yen tables such as "quality 90 equals 150,000 yen".

## 9. Propagation Contract

Quality lineage must propagate without loss:

```text
BUY Quality Artifact
  -> Portfolio Construction
  -> Position Sizing
  -> Runtime Planning
  -> Pending Item
  -> Approval Artifact
  -> Submit Guard Evidence
  -> Order
  -> Fill Observability
  -> Trade Attribution
```

Minimum propagated fields:

```text
quality_decision_id
quality_score
quality_band
quality_action
quality_reason_codes
component_scores
quality_policy_version
source_opportunity_id
```

Submit Guard may observe and verify lineage/status, but must not recompute Quality.

## 10. Re-entry Contract

No fixed cooldown is introduced by this design.

Every new BUY, including re-entry, must pass the same Adaptive BUY Quality Authority. Required PIT inputs:

```text
current position quantity
active pending
active campaign
previous campaign terminal status
same-day EXIT status
new opportunity authority
accepted generation binding
```

Prior realized PnL, Paper Ledger result, test-run performance, or future outcome must not be Quality inputs.

## 11. Acceptance Contract

- AC-1: Low positive Opportunity Score alone does not proceed to normal BUY allocation.
- AC-2: Rank 1 alone does not imply high quality.
- AC-3: Weak population Rank 1 is not automatically full allocation.
- AC-4: Strong population, high percentile, favorable context may become high quality.
- AC-5: Unfavorable context plus outstanding opportunity is not automatically rejected.
- AC-6: Missing required quality evidence does not default to `quality_adjustment=1.0`.
- AC-7: Quality affects Current-total-equity-based sizing.
- AC-8: `target_position_count` is not a decision consumer.
- AC-9: Fixed Rank N cap is not introduced.
- AC-10: Ungrounded fixed raw-score threshold is not introduced.
- AC-11: Historical results, Paper Ledger, and future outcomes are not inputs.
- AC-12: Production / Demo / Historical use the same contract.

## 12. Implementation Boundary

Phase26-G freezes design only. Implementation belongs to:

```text
Phase26-H Production-Common Adaptive BUY Quality Authority Implementation
```

Phase26-H must implement producer-first, then consumers, then propagation, then negative assertions and short regression. Long Historical validation remains operator-owned.
