# Phase5-N Design Deviation Decision Record

## 1. Purpose

Phase5-M judged Phase5 as:

```text
PHASE5_DESIGN_COMPLIANT_WITH_KNOWN_GAPS
```

However, the Opportunity AI design defined broad input categories that include market data, fundamentals, market environment, and sector strength. The actual Phase5 model used 16 `feature__*` columns and did not connect several designed feature families.

This document records the decision on whether those gaps invalidate Phase5 completion.

## 2. Decision

Decision:

```text
A. Phase5 remains complete with documented design deviations
```

Decision status:

```text
PHASE5_COMPLETE_WITH_DOCUMENTED_DESIGN_DEVIATIONS
```

Important wording:

```text
Phase5 is not "fully implemented exactly as the complete Opportunity AI feature design."
Phase5 is "core design compliant with documented design deviations."
```

Promotion:

- `promotion_ready=false`
- no promotion
- no reader switch

Phase6:

- Phase6 may proceed
- missing feature families must be carried as known Opportunity AI improvement tasks

## 3. Why This Is A Design Deviation

The original Opportunity AI design and Phase5-A define input categories including:

- Candidate AI output
- market data: price, volume, high, low
- technical: price momentum, volume momentum, trend strength, volatility
- fundamental: sales growth, profit growth, ROE, financial soundness
- market environment: TOPIX, market trend, sector strength

The actual full-history Opportunity model used 16 features:

```text
feature__candidate_rank
feature__candidate_reason
feature__candidate_score
feature__liquidity_avg_volume_20d
feature__missing_flags_insufficient_history
feature__missing_flags_price
feature__missing_flags_volume
feature__price_momentum_return_20d
feature__price_momentum_return_5d
feature__price_momentum_return_60d
feature__trend_close_over_ma_20d
feature__trend_ma_20_60_ratio
feature__trend_ma_5_20_ratio
feature__volatility_return_std_20d
feature__volume_momentum_ratio_1d_20d
feature__volume_momentum_ratio_5d
```

Therefore, there is a real design deviation:

- fundamental features are not connected
- TOPIX / market trend are not connected
- sector strength is not connected
- high / low / range features are not connected
- avg trading value is not connected
- raw close / raw volume are not used directly

## 4. Source Interpretation

### Opportunity AI Design

`docs/03_ai_design/opportunity_ai_design.md` defines the core role:

```text
候補銘柄の期待値を判定するAI
```

It also says Opportunity AI ranks Candidate AI candidates. The design is broad and conceptual. It does not define a Phase5 exit gate requiring every input family to be connected.

### Phase5-A

`docs/phase_reports/phase5a_opportunity_ai_design.md` defines Phase5 responsibility as:

- rank Candidate Top50
- compare expected value
- output expected_edge_score / buy_rank / risk and explanation fields
- do not extract candidates
- do not manage positions
- do not allocate capital
- do not call Broker API
- do not Paper Trade
- do not place orders

It lists fundamental and market environment items as `候補 feature`.

### Phase5-C

`docs/phase_reports/phase5c_opportunity_feature_design.md` is explicitly:

```text
Opportunity Feature Design / Expansion
```

It also says:

```text
Phase5-C では「どの feature を使うか」だけを設計する。
feature 生成、dataset 生成、学習、推論、backtest、Paper Trading、Broker API、発注、資金配分は行わない。
```

Therefore Phase5-C is not evidence that every listed feature must be implemented before Phase5 completion. It is evidence that those features are valid design targets and must obey J-Quants / as_of_date / leakage rules when implemented.

### Phase5-L / Phase5-M

Phase5-L confirmed:

- artifacts complete
- final schema fixed
- leakage OK
- full-history ready
- safety boundaries OK
- promotion disabled

Phase5-M confirmed:

- core design compliance
- actual feature coverage
- known gaps

The gap recheck then confirmed that the missing features are not completion blockers under current Phase5 governance.

## 5. Deviation Table

| Feature | Design treatment | Implementation status | Classification | Blocker | Impact |
| --- | --- | --- | --- | --- | --- |
| `close` | Price feature from daily quotes | not direct feature | replaced by derived feature | no | close-derived return/trend features are used |
| `high` | Price feature from daily quotes | not connected | future enhancement | no | high-derived range/close-to-high absent |
| `low` | Price feature from daily quotes | not connected | future enhancement | no | low/range features absent |
| `volume` | Volume feature from daily quotes | not direct feature | replaced by derived feature | no | volume momentum and avg volume are used |
| `high_low_range` | Range / volatility feature | not connected | future enhancement | no | volatility_return_std_20d is partial proxy |
| `avg_trading_value_20d` | Liquidity feature | not connected | acceptable implementation gap | no | avg_volume_20d is connected, trading value is not |
| `sales_growth_rate` | Fundamental | not connected | true design deviation | no | sales growth absent |
| `operating_profit_growth_rate` | Fundamental | not connected | true design deviation | no | operating profit growth absent |
| `ordinary_profit_growth_rate` | Fundamental | not connected | true design deviation | no | ordinary profit growth absent |
| `net_income_growth_rate` | Fundamental | not connected | true design deviation | no | net income growth absent |
| `roe` | Fundamental | not connected | true design deviation | no | ROE absent |
| `equity_ratio` | Fundamental | not connected | true design deviation | no | financial soundness absent |
| `operating_margin` | Fundamental | not connected | true design deviation | no | margin quality absent |
| `TOPIX` | Market environment | not connected | true design deviation | no | market-wide context absent |
| `market_trend` | Market environment | not connected | true design deviation | no | market trend context absent |
| `sector_strength` | Sector strength | not connected | true design deviation | no | sector relative strength absent |

Machine-readable record:

- `reports/opportunity_ai/phase5n/design_deviation_decision_record.json`

## 6. Completion Blocker Decision

Blocker count:

- 0

Why not blockers:

- Phase5 completed the core responsibility: Candidate Top50 20-business-day expected-value ranking.
- Phase5-D through Phase5-I produced a full-history dataset, training, quality audit, and combined validation.
- Phase5-J and Phase5-K documented calibration and policy candidates.
- Phase5-L confirmed final schema, leakage, artifact completeness, full-history readiness, and safety.
- Missing feature families did not create leakage.
- Missing feature families did not introduce forbidden data.
- Missing feature families did not prevent Candidate Top50 ranking.
- Phase5-C was a feature design / expansion document, not a mandatory all-feature implementation gate.

This is still a design deviation. It is not erased or minimized. It is accepted for Phase5 v1 completion and must be carried forward.

## 7. Specification Change Assessment

This is partly a specification non-fulfillment and partly a staged scope adjustment.

Assessment:

- Is it a spec non-fulfillment? yes, for full feature-family coverage.
- Is it a staged scope adjustment? yes.
- Was there an implicit spec change during Phase5? yes.

Interpretation:

Phase5 v1 narrowed implementation to connected Candidate, technical, liquidity, volatility, and data quality features while leaving fundamental, market environment, sector strength, high/low/range, and trading value features for future improvement.

Where this decision is recorded:

- `docs/phase_reports/phase5m_design_compliance_review.md`
- `docs/phase_reports/phase5m_design_compliance_gap_recheck.md`
- `docs/phase_reports/phase5n_design_deviation_decision_record.md`
- `reports/opportunity_ai/phase5n/design_deviation_decision_record.json`

## 8. Re-evaluation Of Phase5 Completion

Selected outcome:

```text
A. Phase5 remains complete with documented design deviations
```

Rejected outcomes:

```text
B. conditional complete
C. not complete
```

Reason:

The evidence does not show a core responsibility failure, leakage issue, final schema inconsistency, missing full-history validation, or safety violation. The evidence shows incomplete feature-family implementation. That should be documented as design deviation and improvement backlog, not treated as Phase5 failure under current governance.

## 9. If Stricter Governance Is Required

If the project decides that every originally listed feature family must be connected before completion, then the correct decision changes to:

```text
C. Phase5 is not complete and requires additional implementation
```

Required work would be:

### Phase5-N1 Fundamental Feature Connection

Implement and audit:

- `sales_growth_rate`
- `operating_profit_growth_rate`
- `ordinary_profit_growth_rate`
- `net_income_growth_rate`
- `roe`
- `equity_ratio`
- `operating_margin`

Mandatory rule:

- `disclosure_date <= as_of_date`

### Phase5-N2 TOPIX / Market Trend Feature Connection

Implement and audit:

- TOPIX returns
- market trend
- market risk proxy

Mandatory rule:

- no future regime label leakage

### Phase5-N3 Sector Strength Feature Connection

Implement and audit:

- sector strength
- sector momentum
- stock versus sector return

Mandatory rule:

- derive only from J-Quants listed issue master and quote data available as of target date

### Phase5-N4 Raw OHLCV / Range / Trading Value Feature Connection

Implement and audit:

- high / low
- high_low_range
- avg_trading_value_20d
- optional normalized close / volume fields

### Phase5-N5 Retraining / Full History Validation / Completion Re-audit

Re-run:

- dataset build
- training
- quality audit
- combined validation
- calibration
- policy finalization
- completion audit
- design compliance review

This stricter path is not the current recommendation.

## 10. Current Recommendation

Do not reopen Phase5.

Proceed to Phase6 with this exact caveat:

```text
Phase5 is complete as core design compliant with documented design deviations.
Phase5 is not a complete implementation of every Opportunity AI feature family.
```

Carry forward:

- fundamental feature connection
- TOPIX / market trend feature connection
- sector strength feature connection
- high/low/range/trading-value feature connection
- retraining and full-history validation after those additions

Keep:

- `promotion_ready=false`
- no Broker API
- no Paper Trading
- no orders
- no capital allocation
- no reader switch

## 11. Safety

This decision record did not perform:

- implementation changes
- training
- inference
- backtest
- Broker API calls
- Paper Trading
- orders
- capital allocation
- promotion
- reader switch
