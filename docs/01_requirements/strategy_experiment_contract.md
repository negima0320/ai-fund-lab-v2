# Strategy Experiment Contract

作成日: 2026-07-27

## 1. 目的

本書はPhase23でStrategy variantを検証するためのExperiment Contractである。

上位SoT:

```text
docs/02_architecture/strategy_architecture_v1.md
```

## 2. Experiment単位

各Experimentは以下を持つ。

- experiment_id
- baseline
- variant
- single-change declaration
- hypothesis
- changed_contract
- unchanged_contracts
- run windows
- regimes
- metrics
- rollback plan
- acceptance criteria
- rejection criteria

## 3. Single-change Principle

原則として1Experimentで変更するStrategy要素は1つに限定する。

例:

- Market Context consumerのみ
- target cash ratioのみ
- dynamic position countのみ
- ADD policyのみ
- EXIT thresholdのみ
- position sizingのみ

同時に複数変更する場合は、明示的に `MULTI_CHANGE_REVIEW_REQUIRED` とする。

## 4. Validation Windows

最低限:

- Bull window
- Bear window
- Range window
- Long-run
- Out-of-period evaluation

特定期間だけに最適化しない。

## 5. Regression Gates

必須:

- Existing Runtime Regression PASS
- Phase21-B Pending Composition / ADD Consumer PASS
- Artifact Authority PASS
- Safety PASS
- Lifecycle PASS
- Duplicate order 0
- Production / Demo / Historical common path維持

## 6. Risk Metrics

Returnだけで採用しない。

必須risk観点:

- Maximum Drawdown
- Volatility
- Cash Ratio
- Gross Exposure
- Single-name Concentration
- Sector Concentration
- Turnover
- Position Count
- Loss tail

## 7. Overfitting Prevention

禁止:

- 特定Run ID専用logic
- 特定期間専用threshold
- Historical PnLからのfeature生成
- Test result training
- Future return imitation
- Backtest結果をRuntime入力にする

## 8. Result Status

| Status | 意味 |
|---|---|
| `ACCEPT` | 全Acceptanceを満たす |
| `REVIEW_REQUIRED` | 一部改善だがrisk/authority/coverage懸念あり |
| `REJECT` | Contract破壊、過学習、risk悪化、leakage |
| `INSUFFICIENT_EVIDENCE` | window/metric不足 |

## 9. Rollback

Accepted Strategy変更はrollback手順を持つ。Artifact Acceptance対象のsource path変更は正式Acceptance refreshを必須にする。

## 10. Phase23 Output

Phase23の各Experimentは、Machine-readable evidenceを残す。

```yaml
experiment_id: phase23_x
baseline_ref: accepted_strategy_baseline
variant_ref: strategy_variant
single_change: true
runtime_regression: PASS
authority_status: PASS
performance_status: REVIEW_REQUIRED
decision: REVIEW_REQUIRED
```
