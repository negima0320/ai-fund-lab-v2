# Phase23-AD: J-Quants Historical OHLCV Coverage Extension Command Audit and Operator Materialization Handoff

## 1. Primary Judgment

`PHASE23_AD_CANONICAL_PROMOTION_SAFETY_GAP_DETECTED`

Secondary:

- `PHASE23_AD_DATA_REVISION_AUDIT_GAP_RECORDED`
- `PHASE23_CONTINUES`

## 2. Phase23継続確認

Phase23は継続。Phase complete、Phase24 ready、Production ready、10BD ready とは判定しない。

CodexはJ-Quants live fetch、canonical mutation、Promotion、fresh-run、resume、10BDを実行していない。

## 3. Exact Required Coverage

10BD対象営業日は以下。

```text
2026-07-06
2026-07-07
2026-07-08
2026-07-09
2026-07-10
2026-07-13
2026-07-14
2026-07-15
2026-07-16
2026-07-17
```

最低限必要なtarget-date OHLCV coverageは `through 2026-07-17`。

Feature Builderは61BD lookbackを要求する。既存sourceは `2026-07-14` までのlookbackを持つため、incremental mergeが正式実装されていれば `2026-07-15..2026-07-17` の取得で不足日そのものは埋まる。ただし現行のAD-compliant canonical promotionが不足している。

## 4. J-Quants CLI Inventory

正式確認したCLI:

- `scripts/runtime_test.py market-data-acquisition {plan,run,resume,status}`
- `scripts/runtime_test.py market-data-bootstrap {plan,run}`
- `scripts/run_phase9i_market_data_refresh.py`
- `scripts/fetch_jquants_daily.py`
- `scripts/normalize_jquants_raw.py`
- `scripts/check_jquants_raw_quality.py`
- `scripts/show_jquants_manifest.py`
- `scripts/inspect_raw_validation.py`

詳細は `reports/phase23_ad_jquants_historical_ohlcv_coverage_extension_command_audit_and_operator_materialization_handoff/jquants_cli_inventory.json`。

## 5. Canonical Data Flow

実装上の主なflowは3つ。

1. Runtime v2 staged acquisition  
   `J-Quants API -> Production Market Refresh core -> staging raw/raw_normalized -> staging validation -> bootstrap handoff`

2. Bootstrap normalized promotion  
   `validated normalized source -> merge with operations normalized -> backup -> os.replace`

3. Production direct refresh  
   `J-Quants API -> raw merge -> normalized merge -> manifest`

ADが要求する `immutable acquisition run -> validated raw/normalized -> atomic operations raw+normalized promotion` は現行CLIとして完結していない。

## 6. Acquisition Command

Operator用Plan:

```bash
PYTHONPATH=src python3 scripts/runtime_test.py market-data-acquisition plan \
  --start-date 2026-07-15 \
  --end-date 2026-07-17 \
  --run-id jquants-acquisition-20260715-20260717-ad-extension \
  --chunk day \
  --write-evidence \
  --json
```

Operator用Live fetch:

```bash
PYTHONPATH=src python3 scripts/runtime_test.py market-data-acquisition run \
  --start-date 2026-07-15 \
  --end-date 2026-07-17 \
  --run-id jquants-acquisition-20260715-20260717-ad-extension \
  --chunk day \
  --confirm \
  --yes-i-understand-this-fetches-large-market-data \
  --write-evidence \
  --json
```

Codexは実行していない。

## 7. Normalization Command

`market-data-acquisition` はProduction Market Refresh coreを再利用し、staging rawとstaging normalizedを自動生成する。別Normalization commandは不要。

Legacy commandとして `scripts/normalize_jquants_raw.py --endpoint daily_quotes` は存在するが、ADの選定経路ではない。

## 8. Coverage Validation

Primary keyは実装上 `Date + Code`。`parquet_inventory()` のduplicate checkとbootstrap merge keyで確認。

Operatorは以下を確認する。

```text
raw max date >= 2026-07-17
normalized max date >= 2026-07-17
2026-07-15 rows > 0
2026-07-16 rows > 0
2026-07-17 rows > 0
duplicate Date+Code keys = 0
required OHLCV columns present
```

詳細コマンドは `docs/03_operations/phase23_ad_jquants_ohlcv_materialization_operator_runbook.md`。

## 9. Canonical Promotion

BLOCK。

`market-data-bootstrap run` はnormalized OHLCVのみをoperations canonicalへmergeする。raw OHLCVを同じtransactionでpromoteしない。

`scripts/run_phase9i_market_data_refresh.py` はoperations rootを指定すればraw/normalized両方を書けるが、immutable acquisition runからのseparate promotionではなく、明示的なpromotion confirmation guardもない。そのためPhase23-ADの採用方針には合わない。

## 10. Rollback Contract

Normalized bootstrapは以下を持つ。

```text
tmp parquet
merged validation
backup existing normalized
os.replace target
backup_path emitted
```

Gap:

```text
raw+normalized共通transaction IDなし
raw operations promotionなし
raw rollback referenceなし
```

## 11. Data Revision Semantics

Legacy `MarketDataStore` は `new/updated/unchanged` とduplicate breakdownを持つ。

一方、Runtime v2 bootstrap normalized promotionはoverlap revision auditを出さない。

Gap:

- overlap row diff未記録
- replaced row count未記録
- unchanged row count未記録
- raw OHLCV revision auditなし

## 12. Post-promotion Verification

Future approved promotion後に確認すべき期待値:

```text
operations raw OHLCV max date >= 2026-07-17
operations normalized OHLCV max date >= 2026-07-17
2026-07-15 / 2026-07-16 / 2026-07-17 rows > 0
QUOTE_TARGET_DATE_MISSING absent
```

現時点ではpromotion gapがあるため未実行。

## 13. 2026-07-15 Isolated Verification

Promotion gap解消後、まずread-only plan:

```bash
PYTHONPATH=src python3 scripts/runtime_test.py plan \
  --profile historical-smoke \
  --start-date 2026-07-15 \
  --business-days 1 \
  --json
```

実際のisolated replay / 1BD実行はCodex未実施。Operator判断待ち。

## 14. Existing HALT Run Handling

既存HALT run:

```text
reports/runtime_tests/runs/runtime-test-historical-extended-smoke-20260729T065337151378Z/
```

はresumeしない。Source baseline / canonical data hashが変わるため、新しいfresh-runを開始する。

## 15. Runtime Test Source Baseline Implication

Canonical J-Quants source更新後、次回10BD runのsource baselineは新hashになる。

Accepted Generation、model generation、strategy configは変更しない。J-Quants source coverageのみ更新対象。

## 16. Operator Copy-ready Runbook

作成済み。

```text
docs/03_operations/phase23_ad_jquants_ohlcv_materialization_operator_runbook.md
```

Runbookはpreflight、acquisition、validation、promotion gap停止、post-promotion verification、既存HALT run abandon、10BD gated commandを含む。

## 17. Modified Files

作成:

- `docs/03_operations/phase23_ad_jquants_ohlcv_materialization_operator_runbook.md`
- `docs/phase_reports/phase23_ad_jquants_historical_ohlcv_coverage_extension_command_audit_and_operator_materialization_handoff.md`
- `reports/phase_reports/phase23_ad_jquants_historical_ohlcv_coverage_extension_command_audit_and_operator_materialization_handoff.json`
- `reports/phase23_ad_jquants_historical_ohlcv_coverage_extension_command_audit_and_operator_materialization_handoff/*.json`

Production codeは変更していない。

## 18. Short Validation

実施:

- CLI help確認
- implementation static audit
- JSON artifact generation

未実施:

- J-Quants live fetch
- canonical mutation
- promotion
- fresh-run
- resume
- 10BD

## 19. 未実施事項

以下は未実施。

```text
J-Quants API live fetch
長時間market data acquisition
Canonical operations source mutation
Promotion
2026-07-15 isolated Runtime replay
fresh-run
resume
10BD
20BD
1年
3年
Runtime Switch
Broker Write
Tachibana API
```

## 20. 次のOperator Action

まずOperatorが `market-data-acquisition` で `2026-07-15..2026-07-17` をstaging取得し、staging coverageを確認する。

その後は、現行のままpromotionへ進まない。raw+normalized OHLCVをimmutable stagingからoperations canonicalへatomic promoteし、revision auditとrollback referenceを記録する正式command/contractを追加または承認してから、2026-07-15 isolated verificationと10BD fresh-runへ進む。
