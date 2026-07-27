# Strategy Performance Acceptance Contract

作成日: 2026-07-27

## 1. 目的

本書はStrategy変更を採用、保留、却下するためのPerformance Acceptance Contractである。Phase23 Controlled Validation and Performance Evaluationの基準として使用する。

上位SoT:

```text
docs/02_architecture/strategy_architecture_v1.md
```

## 2. Authority分類

Runtime authority:

- 当日判断に使用可能なJ-Quants PIT data、Accepted Artifact、Current、Pending、Safety、Policy

Post-hoc diagnostic:

- Historical Runtime result
- Performance attribution
- Run PnL
- fills / realized slices
- profit giveback
- holding period outcome

Training authority:

- J-Quants由来PITデータのみ

Performance EvidenceはTraining / Runtime / Calibration入力に使用しない。

## 3. Metrics

必須Metric候補:

- Total Return
- CAGR / annualized return
- Maximum Drawdown
- Volatility
- Sharpe-like metric
- Cash Ratio
- Cash Utilization
- Gross Exposure
- Turnover
- Position Count
- Single-name Concentration
- Sector Concentration
- Benchmark Relative Return
- Win / Loss
- Holding Period
- Profit Retention
- Profit Giveback
- ADD contribution
- REDUCE contribution
- EXIT contribution
- Market Regime attribution

各metricは以下を持つ。

- value
- status
- authority
- source_artifacts
- limitations
- missing_data_policy
- temporal_safety
- contract_version

## 4. Missing Metric Handling

| 状態 | 意味 |
|---|---|
| `AVAILABLE` | Authority artifactから利用可能 |
| `DERIVABLE_EXACT` | 正確に導出可能 |
| `DERIVABLE_PARTIAL` | 一部のみ導出可能 |
| `MISSING` | Authority未整備 |
| `NOT_APPLICABLE` | 評価対象外 |
| `AUTHORITY_CONFLICT` | Authority競合 |

Missingを0として扱わない。

## 5. Benchmark

Benchmark候補:

- TOPIX
- Nikkei 225
- cash baseline

Benchmark data authorityが未整備の場合、Benchmark relative returnは `MISSING` とする。Missing benchmarkをcashやzero returnで代替しない。

## 6. Sector

Sector concentration、Sector PnL、Sector exposureはsector mapping authorityが必要である。coverageが不足する場合は `MISSING` または `DERIVABLE_PARTIAL` とする。

## 7. Acceptance / Review / Reject

Accept候補条件:

- Runtime regression PASS
- Authority / Lifecycle / Safety PASS
- multi-regimeで改善
- drawdown悪化が許容範囲
- turnover / concentrationが悪化しすぎない
- out-of-period評価で破綻しない

Review条件:

- return改善だがdrawdown悪化
- single regimeのみ改善
- metric missingが多い
- concentration増加
- cash utilization改善が過剰risk由来

Reject条件:

- Runtime Contract破壊
- Safety破壊
- Authority mismatch
- Future leakage
- specific run overfit
- returnだけ改善してriskが大幅悪化

## 8. Data Boundary

禁止:

- Historical Run損益をRuntime入力にする
- Backtest resultをTraining / Calibrationに使う
- Paper LedgerをStrategy featureにする
- Future Returnを特徴量にする
- Test合否を学習に使う

## 9. Production Applicability

Strategy採用はProduction / Demo / Historical共通Contractで評価する。Historicalだけで有効な入力、Profit logic、特殊分岐は禁止する。
