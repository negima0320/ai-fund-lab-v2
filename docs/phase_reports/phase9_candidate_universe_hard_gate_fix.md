# Phase9 Candidate Universe Hard Gate Fix

## 結論

```text
PHASE9_CANDIDATE_UNIVERSE_HARD_GATE_FIX_COMPLETE
```

Candidate UniverseにHard Gateを実装し、2026-06-16対象のfeature refresh / daily inference / 2026-06-17 Blog Report v4を軽量再生成した。

修正後、`1400` / canonical code `14000` はCandidate Top50 / Opportunity Top5から除外された。

## BUG原因

監査資料:

```text
docs/phase_reports/candidate_universe_delisted_security_audit.md
```

原因:

```text
Candidate Universeがlisted_infoではなくcanonical quotesの価格履歴だけを母集団にしていた。
```

従来の`universe_eligible`は、主にlookback行数を満たすかだけで判定されていた。

そのため、以下のような銘柄が候補に入った。

```text
code: 14000
display code: 1400
latest listed_info: 不在
canonical last price date: 2023-12-29
candidate rank: 2
opportunity rank: 2
top5 rank: 2
```

## 実装したHard Gate

実装箇所:

```text
src/ai_fund_lab_v2/paper_trading/feature_refresh.py
```

Candidate feature refresh時点で以下をすべて満たす場合のみ`universe_eligible=true`にする。

```text
enough_lookback
is_current_listed
has_current_name
is_fresh_price
is_allowed_product
```

追加した監査列:

```text
is_current_listed
has_current_name
is_fresh_price
product_category
market_name
is_allowed_product
universe_exclusion_reason
```

Product / Market gate:

```text
allowed ProdCat: 011, 021
allowed MktNm: プライム, スタンダード, グロース
```

除外対象:

```text
latest listed_info未一致
CoName空
data_end_date < target_data_until
ETF
ETN
REIT
外国籍ETF
商品系上場商品
TOKYO PRO MARKET
その他分類不明
```

補足:

listed_infoは未来情報を避けるため、`target_data_until`以下の最新snapshotを使用する。

## Inference / Blog防御

実装箇所:

```text
src/ai_fund_lab_v2/paper_trading/daily_inference_runner.py
src/ai_fund_lab_v2/paper_trading/reporting/blog_report_v2_writer.py
```

Daily Inference:

```text
candidate artifact / opportunity artifactへHard Gate監査列を引き継ぐ
daily inferenceは従来通り universe_eligible=true のみを使用
```

Blog Report:

```text
Data QualityにHard Gate防御件数を表示
```

追加表示:

```text
missing_name_count
listed_info_unmatched_count
stale_price_count
disallowed_product_count
universe_hard_gate_violation_count
```

## Before / After

Beforeは監査時点の数値。

```text
eligible universe before: 4,780
eligible universe after: 3,706
```

After詳細:

```text
total candidate feature rows: 4,989
eligible_count: 3,706
eligible_14000_count: 0
eligible_not_current_listed_count: 0
eligible_missing_name_count: 0
eligible_stale_price_count: 0
eligible_disallowed_product_count: 0
```

Eligible product categories:

```text
ProdCat 011: 3,701
ProdCat 021: 5
```

Eligible markets:

```text
プライム: 1,563
スタンダード: 1,553
グロース: 590
```

## 1400除外確認

修正後:

```text
candidate_features universe_eligible内の14000: 0
Candidate Top50 contains 1400: false
Opportunity Top5 contains 1400: false
```

14000の除外理由:

```text
not_current_listed
missing_name
stale_price
disallowed_product
```

## ETF / ETN / REIT除外確認

修正後:

```text
eligible universe ETF: 0
eligible universe ETN: 0
eligible universe REIT: 0
Candidate Top50 ETF/ETN/REIT: 0
Opportunity Top20 ETF/ETN/REIT: 0
Opportunity Top5 ETF/ETN/REIT: 0
```

## Candidate Top50 Before / After

Before:

```text
Candidate Top50 total: 50
ordinary/equity-like: 39
ETF: 9
ETN: 1
REIT: 0
not current listed: 1
missing name: 1
1400 rank: 2
```

After:

```text
Candidate Top50 total: 50
ordinary/equity-like: 50
ETF: 0
ETN: 0
REIT: 0
not current listed: 0
missing name: 0
1400 included: false
```

After Top10:

```text
1. 166A タスキホールディングス
2. 1948 弘電社
3. 212A フィットイージー
4. 215A タイミー
5. 2393 日本ケアサプライ
6. 285A キオクシアホールディングス
7. 3063 ジェイグループホールディングス
8. 3436 SUMCO
9. 3441 山王
10. 3480 ジェイ・エス・ビー
```

## Opportunity Top5 Before / After

Before:

```text
total: 5
ordinary/equity-like: 0
ETF: 4
ETN: 0
REIT: 0
not current listed: 1
missing name: 1
1400 rank: 2
```

After:

```text
total: 5
ordinary/equity-like: 5
ETF: 0
ETN: 0
REIT: 0
not current listed: 0
missing name: 0
1400 included: false
```

After Top5:

```text
1. 166A タスキホールディングス
2. 1948 弘電社
3. 212A フィットイージー
4. 215A タイミー
5. 2393 日本ケアサプライ
```

## Blog再生成結果

バックアップ:

```text
.runtime/phase9/recovery_backups/2026-06-17_candidate_universe_hard_gate/
```

再生成:

```text
reports/public/phase9_daily/2026-06-17_blog_report_v4.md
reports/public/phase9_daily/2026-06-17_blog_report_v4.json
```

Blog Data Quality:

```text
missing_name_count: 0
listed_info_unmatched_count: 0
stale_price_count: 0
disallowed_product_count: 0
universe_hard_gate_violation_count: 0
```

## 軽量監査結果

監査JSON:

```text
.runtime/phase9/audits/candidate_universe_hard_gate_fix_validation.json
```

確認:

```text
candidate_features universe_eligible内に14000が存在しない
candidate_features universe_eligible内に最新listed_info未一致が0件
candidate_features universe_eligible内に名称未取得が0件
candidate_features universe_eligible内にdata_end_date < target_data_untilが0件
candidate_features universe_eligible内にETF/ETN/REITが0件
Candidate Top50内に1400が存在しない
Opportunity Top5内に1400が存在しない
Opportunity Top5が普通株のみ
Blog Reportに名称未取得が出ない
```

## 実行コマンド

Feature refresh:

```bash
python3 scripts/run_phase9j_feature_refresh.py --target-data-until 2026-06-16 --execute
```

Daily inference:

```bash
python3 scripts/run_phase9l2_daily_inference.py --decision-for 2026-06-16 --data-until 2026-06-16
```

Blog regeneration:

```text
write_blog_report_v2(decision_for=2026-06-16, execution_date=2026-06-17, report_version=v4)
```

Tests:

```bash
python3 -m pytest tests/paper_trading/test_phase9j_feature_refresh.py tests/paper_trading/test_phase9j2_feature_refresh_canonical_paths.py tests/paper_trading/test_phase9l2_daily_inference_runner.py tests/paper_trading/test_phase9t_blog_report_v2.py
```

Result:

```text
12 passed
```

## 30営業日検証の再開可否

新規Candidate / Opportunity生成については再開可能。

ただし、2026-06-16の初回Virtual Fillでは修正前UniverseによりETFが保有に入っている。

現在保有に含まれるETF:

```text
1579
213A
221A
```

そのため、Phase9の検証目的を「普通株のみ」と厳密に定義する場合、30営業日検証を完全にクリーンに再開するには以下のどちらかを決める必要がある。

```text
案A: 既存Paper Ledgerをリセットし、Hard Gate後UniverseでDay1から再開始
案B: 既存ETF保有をlegacy positionとして明示し、以後の新規購入だけHard Gate対象として継続
```

推奨:

```text
普通株のみの検証としては案A。
運用継続性を重視する観察としては案B。
```

