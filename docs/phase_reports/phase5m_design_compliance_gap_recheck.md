# Phase5-M Design Compliance Gap Recheck

## 1. Purpose

This document rechecks why Phase5-M classified unconnected Opportunity AI features as known gaps / future improvements rather than Phase5 completion blockers.

This is a design-compliance clarification before Phase6. It does not change implementation, training, inference, backtest, Paper Trading, Broker API, orders, capital allocation, promotion, or reader switching.

## 2. Recheck Judgment

Judgment:

- maintain `PHASE5_DESIGN_COMPLIANT_WITH_KNOWN_GAPS`

Phase5 additional implementation before Phase6:

- not required

Phase6 handoff:

- allowed, with known gaps documented

Reason:

- The core Opportunity AI responsibility was implemented: Candidate Top50 expected-value ranking with 20-business-day labels.
- Full-history validation was completed.
- Leakage and forbidden feature audits were OK.
- Final output schema was fixed.
- Missing feature families were feature expansion gaps, not evidence that Phase5 invaded other responsibilities or failed to rank Candidate Top50.

## 3. Source Document Recheck

### 3.1 Opportunity AI Design

`docs/03_ai_design/opportunity_ai_design.md` defines the core role:

```text
候補銘柄の期待値を判定するAI
```

It also states that Opportunity AI ranks Candidate AI candidates and does not search the universe itself.

Interpretation:

- The central design obligation is expected-value ranking of Candidate AI outputs.
- The design document defines the broad Opportunity AI role, but it does not by itself define a Phase5 exit gate requiring every possible input family to be connected before completion.

### 3.2 Phase5-A Design

`docs/phase_reports/phase5a_opportunity_ai_design.md` defines Phase5 responsibility as:

- rank Candidate Top50
- compare expected value inside the Candidate group
- output expected_edge_score / buy_rank / risk/explanation fields
- do not extract candidates
- do not manage positions
- do not allocate capital
- do not call Broker API
- do not Paper Trade
- do not place orders

For features, Phase5-A lists:

- market data
- technical features
- fundamental features
- market environment features

But it also describes several items as:

```text
候補 feature
```

Interpretation:

- Phase5-A establishes the desired feature direction, but the immediate completion-critical responsibility remains Candidate Top50 expected-value ranking.
- Fundamental / market environment items are legitimate design targets, but not explicitly stated as mandatory blockers for Phase5 completion.

### 3.3 Phase5-C Feature Design

`docs/phase_reports/phase5c_opportunity_feature_design.md` is titled:

```text
Opportunity Feature Design / Expansion
```

It explicitly says:

```text
Phase5-C では「どの feature を使うか」だけを設計する。
feature 生成、dataset 生成、学習、推論、backtest、Paper Trading、Broker API、発注、資金配分は行わない。
```

It also lists available J-Quants sources and derivable features, including:

- J-Quants daily quotes
- J-Quants listed issue master
- J-Quants fins / statements
- J-Quants index / market data if available
- sector aggregation derivable from listed issue master and daily quotes

Interpretation:

- Phase5-C is a design and expansion document.
- It defines the allowed universe and candidate schema, not a guarantee that every listed candidate feature is connected in the first Phase5 full-history implementation.
- It is stricter about what must not happen: no future leakage, no backtest/trade/portfolio-derived features, and no non-J-Quants feature sources.

### 3.4 Phase5-M Review

`docs/phase_reports/phase5m_design_compliance_review.md` classified:

- actual features: 16
- unused designed features: 17
- known gaps: 17
- completion impact: `known_gap_future_improvement`

It documented that Candidate, momentum, volume momentum, trend, volatility, liquidity, and data quality features were implemented, while Fundamental, market environment, and sector strength were not connected.

Interpretation:

- Phase5-M did not claim full feature-design completion.
- It claimed design compliance with known gaps because the implemented system satisfied the core ranking role and safety/leakage/final-schema/full-history conditions.

## 4. Actual Unconnected Feature Recheck

| Feature | Category | Classification | Blocker | Reason |
| --- | --- | --- | --- | --- |
| `sales_growth_rate` | Fundamental | known gap but Phase5 completion acceptable | no | J-Quants fins/as_of_date join was designed but not connected. This is a future Opportunity feature, not a core ranking blocker. |
| `operating_profit_growth_rate` | Fundamental | known gap but Phase5 completion acceptable | no | Same as above. Needs disclosure-date-safe financial statement join. |
| `ordinary_profit_growth_rate` | Fundamental | known gap but Phase5 completion acceptable | no | Same as above. |
| `net_income_growth_rate` | Fundamental | known gap but Phase5 completion acceptable | no | Same as above. |
| `roe` | Fundamental | known gap but Phase5 completion acceptable | no | Same as above. |
| `equity_ratio` | Fundamental | known gap but Phase5 completion acceptable | no | Same as above. |
| `operating_margin` | Fundamental | known gap but Phase5 completion acceptable | no | Same as above. |
| `TOPIX` | Market environment | known gap but Phase5 completion acceptable | no | J-Quants index / market environment join was listed as available if present; not connected in Phase5. |
| `market_trend` | Market environment | known gap but Phase5 completion acceptable | no | Market trend was designed but not connected. Must be added later without future regime leakage. |
| `sector_strength` | Sector strength | known gap but Phase5 completion acceptable | no | Requires listed issue master / sector aggregation join. Not connected in Phase5. |
| `close` | Market data | replaced by derived feature | no | Raw close is not direct feature, but close-derived return/trend features are used. |
| `high` | Market data | future improvement | no | High-derived range / close-to-high features were designed but not connected. |
| `low` | Market data | future improvement | no | Low/high-low range features were designed but not connected. |
| `volume` | Market data | replaced by derived feature | no | Raw volume is not direct feature, but volume momentum and average volume liquidity features are used. |

Machine-readable outputs:

- `reports/opportunity_ai/phase5m/design_compliance_gap_recheck.json`
- `reports/opportunity_ai/phase5m/design_compliance_gap_recheck.csv`

## 5. Why These Are Not Completion Blockers

They are not blockers under the current Phase5 governance because:

- Phase5-A defines the primary responsibility as Candidate Top50 expected-value ranking.
- Phase5-C is feature design / expansion and explicitly does not perform feature generation.
- Phase5-D through Phase5-I produced a full-history dataset, training, quality audit, and combined validation with the connected feature set.
- Phase5-L already confirmed artifacts, leakage, full-history readiness, schema, policy, and safety boundaries.
- The missing features did not cause forbidden feature usage, future leakage, schema inconsistency, or inability to rank Candidate Top50.
- Raw `close` and `volume` are represented by derived price/volume features, so their absence as direct columns is less severe than a missing data family.

## 6. When They Would Become Blockers

They should be considered blockers if any of the following governance rules are adopted:

- Phase5 completion requires every input family listed in the original design to have at least one connected feature.
- Fundamental, market environment, and sector strength are declared mandatory for Opportunity AI v1 promotion readiness.
- The system cannot rank Candidate Top50 without those features.
- Missing features create leakage, schema inconsistency, or invalid labels.
- Raw OHLCV absence means no OHLCV-derived information exists. This is not the current case because momentum, trend, volume momentum, volatility, and liquidity features are connected.

## 7. Should Phase5-M Readiness Be Changed?

Recommendation:

- do not change Phase5-M readiness
- keep `PHASE5_DESIGN_COMPLIANT_WITH_KNOWN_GAPS`

Reason:

- The current readiness label already expresses the important nuance: Phase5 is compliant with known gaps, not fully feature-complete.
- Changing to `PHASE5_DESIGN_NON_COMPLIANT` would imply a core responsibility failure or safety/leakage/schema failure, which the evidence does not show.

If the project wants stricter feature-family completion criteria, the better action is to add a new governance rule for Phase6 / Opportunity AI improvement, not retroactively reinterpret Phase5-C as requiring all expansion features to be implemented.

## 8. Phase6 Recommendation

Phase6 may proceed.

Additional implementation before Phase6:

- not required

Recommended follow-up tasks:

- add J-Quants fins features with `disclosure_date <= as_of_date`
- add TOPIX / market trend features with explicit no-future-regime audit
- add sector strength from listed issue master and quote-derived sector aggregation
- evaluate high/low/range and trading-value features
- keep future columns label/evaluation-only

These should be tracked as Opportunity AI improvement tasks, not as Phase5 completion blockers.

## 9. Safety

This recheck did not run:

- implementation changes
- training
- inference
- backtest
- Paper Trading
- Broker API
- orders
- capital allocation
- promotion
- reader switch
