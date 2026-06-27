# Phase9 Completion Summary / Phase10 Handoff

作成日: 2026-06-27

## 1. Phase9の位置づけ

Phase9は以下として整理する。

```text
30営業日Paper Trading / Unified Daily Operation Validation
```

目的は、実売買に進む前に、毎営業日20:00 JSTの自動運用サイクルが壊れずに回るかを検証することだった。対象は単なるPaper Ledgerではなく、J-Quantsデータ更新、canonical normalized更新、feature refresh、daily inference、pending order作成、virtual fill、ledger valuation、Blog Report v4、30BD tracker、通知までを含む日次運用全体である。

Phase9の30営業日テストは継続中だが、Phase10へ進むためのreadiness documentとして、本資料で現在地を固定する。

## 2. Phase9で完成した主要機能

### Unified Daily Runner

- 主要ファイル: `scripts/run_aifundlab_daily_paper_trading.py`, `src/ai_fund_lab_v2/paper_trading/unified_daily_runner.py`
- 20:00 JSTのlaunchd実行を前提に、market refresh、canonical update、feature refresh、inference、pending order作成、virtual fill、valuation、tracker、Blog Report v4、通知を統合。
- `--date` 未指定時はJST当日を解決。
- paper-trading modeでは非営業日を直近営業日に丸めない。

### launchd連携

- plist名: `com.aifundlab.daily-paper-trading`
- 実行時刻: 毎日20:00 JST
- 実行コマンド: `run_aifundlab_daily_paper_trading.py`
- ログ保存先: `.runtime/daily_operation/scheduler_logs/`
- scheduler/launchdの自動変更は禁止のまま運用。

### Paper Ledger / Virtual Fill

- Paper Ledgerは`.runtime/phase9/ledger/latest.json`で管理。
- pending orderを翌営業日始値で仮想約定。
- virtual fillはBroker注文ではなく、内部Paper Ledgerのみを更新する。
- Phase9-Yで、fill時に`run_date`ではなく各orderの`virtual_execution_date`を使うよう修正済み。

### 30BD tracker

- 保存先: `.runtime/phase9/tracker/phase9_30bd_tracker.json`
- 現在進捗: `6/30`
- pipeline success、data readiness、report generation、ledger integrity、no broker order violationを追跡。

### Blog Report v4

- 保存先: `reports/public/phase9_daily/`
- note向けにMarkdown tableを廃止し、リスト形式で出力。
- 見出しを「本日約定した銘柄」「翌営業日の購入予定候補 Top5」に修正し、判断日と約定日の誤解を減らした。
- 銘柄コードは公開用に末尾0を落とした表示へ修正済み。
- 内部score、feature schema hash、artifact path、broker account情報、secret類は公開しない方針。

### Candidate / Opportunity score ranking

- Candidate / Opportunityの順位付けを、公開用clip済みscoreではなく`raw_score_preclip` / `rank_score`ベースへ修正。
- `public_confidence_score`は説明用スコアとして残し、ランキング用scoreとは分離。

### J-Quants market refresh / canonical normalized data

- daily_quotesはper-date fetchへ修正。
- requested_to_dateとdata_untilを分離。
- latest available dateまでの取得を許容。
- canonical normalized daily_quotesは長期履歴を維持し、日付単位mergeで更新。
- valuation quotes pathは `.runtime/phase9/canonical_data/normalized_daily_quotes/data.parquet` を期待値とする。

### Feature Refresh Auto Execution

- market refresh / canonical update後、feature artifactが不足している場合は自動でfeature refreshを実行。
- feature refresh失敗時はfail closed。
- daily inferenceはfeatures ready後に進む。

### Business Day Guard

- J-Quants trading_calendar優先。
- `HolDiv == "1"` のみ営業日扱い。
- 土日・祝日・休場日は `NON_BUSINESS_DAY_SKIPPED`。
- calendar missing / fetch失敗 / 判定不能は `TRADING_CALENDAR_NOT_READY_BLOCKED`。
- paper-trading modeでは非営業日を直近営業日に丸めない。

### Pending Order Dedup

- 同一`decision_for` / `virtual_execution_date` / `code` / `side` / `quantity` / `planned_price`相当のfingerprintで重複作成を防止。
- 土曜誤実行で発生したpending order 10件を5件へ復旧済み。

### LINE / Discord Notification

- 主要ファイル: `src/ai_fund_lab_v2/paper_trading/notifications/`
- LINE Messaging APIとDiscord Webhookに対応。
- 通知失敗は本体バッチを失敗扱いにしない。
- 環境変数:
  - `AIFUNDLAB_LINE_CHANNEL_ACCESS_TOKEN`
  - `AIFUNDLAB_LINE_TO_ID`
  - `AIFUNDLAB_DISCORD_WEBHOOK_URL`
- `.env.example`へサンプル追加済み。
- 実送信テストはLINE / Discordともに成功済み。

## 3. Phase9で発見・修正した重要バグ

### Score Saturation bug

症状:

- Candidate / Opportunity scoreが全件100にclipされていた。
- 多数同点になり、rankが実質code順に近い挙動になっていた。
- 3063 ジェイグループHDが不自然に採用され、高値掴み疑いが出た。

修正:

- Candidate rankは`raw_score_preclip`由来の`rank_score`で決定。
- Opportunity rankも`rank_score`で決定し、Candidate側rank_scoreを利用。
- 公開用scoreは0-100に丸めるが、rankには使わない。
- 監査で3063 ジェイグループHDは修正後の候補・採用対象外であることを確認。

参照:

- `docs/phase_reports/phase9v_score_saturation_fix.md`

### Date Resolve / Stale Valuation bug

症状:

- 2026-06-18 runで、quotes max dateが2026-06-17のまま正常レポートが出るリスクがあった。
- `decision_for` / `valuation_date` が最新取得済みquote日へ寄ってしまい、実行日とズレた。

修正:

- 20:00 JST運用では `run_date = decision_for = valuation_date` を基本に整理。
- `quote_source_max_date < valuation_date` の場合はstale price sourceとしてfail closed。
- stale状態ではtracker正常entryや正常Blog Reportへ進めない。

参照:

- `docs/phase_reports/phase9w_unified_runner_market_refresh_and_date_resolution.md`

### Market Refresh未接続

症状:

- `--allow-api-fetch`を指定しても、Unified Runner内でmarket refreshが実行されていなかった。
- 古いcanonical dataのまま進むリスクがあった。

修正:

- Unified RunnerからJ-Quants market refreshを実行。
- raw保存、normalized更新、canonical更新へ接続。
- allow-api-fetch指定時にfetchしない設計を禁止。

### Feature Refresh未接続

症状:

- market refresh / canonical update後にfeature artifactが不足しても、監査だけで止まり、featuresが作られなかった。
- daily inferenceが `candidate_feature_artifact_missing` などでblockされた。

修正:

- `skip-feature-refresh`未指定時、missing feature artifactがあれば自動feature refresh。
- refresh成功後にdaily inferenceへ続行。
- 失敗時は具体的blocked reasonでfail closed。

### canonical normalized overwrite bug

症状:

- market refresh後のcanonical updateで長期履歴を上書きし、long lookbackが失われる可能性があった。

修正:

- canonical normalized daily_quotesを日付単位mergeへ修正。
- 2021-06-14からの長期履歴を維持。
- Phase9 feature refreshで必要なlookbackを確保。

参照:

- `docs/phase_reports/phase9j3_canonical_normalized_rebuild.md`

### Virtual Fill execution date bug

症状:

- due判定は`virtual_execution_date <= run_date`だったが、fill実行時に`run_date`を渡していた。
- 2026-06-22予定orderがデータ未取得で翌日に再実行された場合、2026-06-23始値でfillされるリスクがあった。

修正:

- pending orderを`virtual_execution_date`ごとにgroup化。
- fill時の`execution_date`はorder自身の`virtual_execution_date`を使用。
- 該当日のquotesがなければpending維持。

参照:

- `docs/phase_reports/phase9y_virtual_fill_execution_date.md`

### Weekend duplicate pending bug

症状:

- 2026-06-20(土) 20:00のlaunchd起動が、直近営業日の2026-06-19として再実行された。
- 2026-06-19作成済みpending order 5件に同一5件が追加され、pending order 10件になった。

修正:

- 重複pending orderをfingerprintでdedupし、5件へ復旧。
- 非営業日のpaper-trading実行は `NON_BUSINESS_DAY_SKIPPED`。
- 同一decision_for再実行でもpending orderが増えないようdedup guardを追加。

参照:

- `docs/phase_reports/phase9z_weekend_run_guard_pending_dedup.md`

### Holiday / Trading Calendar bug

症状:

- Phase9-Z2でtrading_calendar優先にしたが、ローカルcalendarが古い場合、営業日もfail closedでSKIPされた。
- 2026-06-22が `TRADING_CALENDAR_DATE_MISSING` によりSKIPされ、6/19作成pending orderがfillされなかった。

修正:

- 営業日判定前にtrading_calendar refreshを試行。
- `HolDiv == "1"` なら通常実行。
- calendar missing/fetch失敗は `TRADING_CALENDAR_NOT_READY_BLOCKED` として、非営業日skipと区別。

参照:

- `docs/phase_reports/phase9z3_trading_calendar_refresh_before_business_day_guard.md`

### Manifest / Ledger summary metadata

症状:

- runner manifest statusが`None`に見えるケースがあった。
- Ledger summaryの`trade_count` / `realized_pnl` / `unrealized_pnl`などが確認スクリプトから見えないケースがあった。

修正:

- manifest top-level statusを常に明示。
- ledger top-level summaryに`trade_count`, `realized_pnl`, `unrealized_pnl`, `total_equity`, `cash`, `market_value`, `positions_count`, `pending_orders_count`, `last_valuation_date`, `last_execution_date`を補完。

参照:

- `docs/phase_reports/phase9z4_manifest_status_ledger_summary.md`

補足:

- 最新Ledgerのsummary fieldsは存在している。
- 一方、最新Ledgerの`metadata.initial_cash`は`0`になっており、運用上の初期資金はtracker/blog summaryの`1,000,000 JPY`を正として扱う。metadata側の初期資金表現は今後の軽微な整備対象。

## 4. 現在のPaper Trading状態

最新参照:

- `.runtime/phase9/ledger/latest.json`
- `.runtime/phase9/tracker/phase9_30bd_tracker.json`
- `reports/public/phase9_daily/2026-06-26_blog_report_v4.json`

### Ledger summary

| item | value |
|---|---:|
| operational initial cash | 1,000,000 JPY |
| current cash | 144,400 JPY |
| market value | 851,200 JPY |
| total equity | 995,600 JPY |
| cumulative PnL | -4,400 JPY |
| cumulative return | -0.44% |
| realized PnL | 0 JPY |
| unrealized PnL | -4,400 JPY |
| positions count | 7 |
| pending orders count | 0 |
| trade count | 7 |
| last valuation date | 2026-06-26 |
| last execution date | 2026-06-25 |
| tracker progress | 6/30 |

### Current positions

| code | name | quantity | average cost | market value | unrealized PnL | holding days |
|---|---|---:|---:|---:|---:|---:|
| 5367 | ニッカトー | 100 | 1,609 | 167,800 | +6,900 | 5 |
| 6966 | 三井ハイテック | 100 | 1,194 | 99,200 | -20,200 | 5 |
| 6336 | 石井表記 | 100 | 2,000 | 191,100 | -8,900 | 5 |
| 7245 | 大同メタル工業 | 100 | 1,501 | 169,100 | +19,000 | 5 |
| 3237 | イントランス | 2,100 | 89 | 193,200 | +6,300 | 5 |
| 7048 | ベルトラ | 100 | 193 | 16,200 | -3,100 | 3 |
| 6181 | タメニー | 200 | 95 | 14,600 | -4,400 | 2 |

### Tracker

- 2026-06-19: Day1, pending 5, positions 0, total equity 1,000,000
- 2026-06-22: Day2, pending 5, positions 0, total equity 1,000,000
- 2026-06-23: Day3, positions 5, pending 1, total equity 1,000,000
- 2026-06-24: Day4, positions 6, pending 1, total equity 1,047,100
- 2026-06-25: Day5, positions 7, pending 0, total equity 1,044,300
- 2026-06-26: Day6, positions 7, pending 0, total equity 995,600

## 5. 現在の運用方法

### launchd

```text
plist name:
com.aifundlab.daily-paper-trading

run time:
20:00 JST

command:
run_aifundlab_daily_paper_trading.py
```

### 営業日判定

- J-Quants trading_calendarを優先。
- `HolDiv == "1"` のみ営業日。
- 土日・祝日・休場日は `NON_BUSINESS_DAY_SKIPPED`。
- calendar missing / fetch failure / 対象日なしは `TRADING_CALENDAR_NOT_READY_BLOCKED`。
- paper-trading modeでは直近営業日への丸めは禁止。

### 出力先

```text
manifest:
.runtime/daily_operation/runs/YYYY-MM-DD/unified_daily_run_manifest.json

operation log:
.runtime/daily_operation/operation_logs/YYYY-MM-DD_operation_log.json

public blog report:
reports/public/phase9_daily/YYYY-MM-DD_blog_report_v4.md

ledger:
.runtime/phase9/ledger/latest.json

tracker:
.runtime/phase9/tracker/phase9_30bd_tracker.json
```

### 確認コマンド

```bash
launchctl print gui/$(id -u)/com.aifundlab.daily-paper-trading | grep -E "runs|last exit code"

ls -lt .runtime/daily_operation/runs
ls -lt .runtime/daily_operation/operation_logs
ls -ltL reports/public/phase9_daily
```

## 6. Phase9の現在評価

### 総評

Phase9の運用パイプラインは、初期の重要バグを潰したことでかなり安定してきた。とくに、score saturation、stale valuation、market refresh未接続、feature refresh未接続、virtual fill日付ズレ、非営業日再実行、pending重複、trading calendar missingを一通り経験し、運用で必要なfail closedの境界が明確になった。

30営業日テストはまだ6/30であり、Phase9自体の実績検証は継続中である。ただし、Phase10のread-only Broker接続へ進むための運用基盤は整っている。

### AI特性

- 現行AIは短中期モメンタム型の性格が強い。
- 上昇トレンド、テーマ株、値動きが出ている銘柄の捕捉に強い可能性がある。
- 一方、急落相場、往復ビンタ相場、高値追い、gap-up後の反落には弱い可能性がある。
- 高値追いペナルティ、gap-up no-fill policy、Safety Layerの重要性が高い。

### 現時点の制約

- 実売買は禁止。
- Broker注文は禁止。
- Phase10はread-only接続から開始する。
- Safety Layer未完成のまま本番注文へ進まない。

## 7. 残課題

### High

- 30営業日Paper Trading完走。
- Safety Layer未実装のため、実売買は禁止。
- Phase10の立花証券API接続はread-onlyから開始し、発注APIは使わない。
- no-live-order auditが完了するまで本番注文は禁止。

### Medium

- Blog Report v4の継続安定運用。
- LINE / Discord通知の本番日次運用確認。
- 高値追いペナルティ検討。
- gap-up no-fill / gap-up risk filter検討。
- low-price / affordability bias監査。
- `score_clipped`と`rank_score`の表示整理。
- Ledger `metadata.initial_cash`と運用初期資金表現の整備。
- `daily_quotes_normalization_status=ERROR` warningがoperation logに残っているため、原因切り分け。

### Low

- ブログ文面の継続改善。
- 購入理由・売却理由の自然文改善。
- Public Confidence Scoreの説明表現改善。
- 週次/月次レポートの整備。

## 8. Phase10への引き継ぎ

Phase10タイトル:

```text
Tachibana Securities API Connection
```

Phase10の目的:

```text
立花証券e支店APIと接続し、
実売買前のBroker Integrationをread-only中心に進める
```

### Phase10でやること

- 立花証券API認証情報管理。
- secrets管理。
- read-only login / session管理。
- account snapshot取得。
- positions取得。
- orders/history取得。
- realtime quote取得。
- API response schema保存。
- Broker Snapshot保存。
- Tachibana Broker Adapter実装。
- Paper Ledgerとのreconciliation。
- dry-run order plan validation。
- no-live-order audit。

### Phase10で禁止すること

- 実買い注文。
- 実売り注文。
- 発注API実行。
- unlock_trade。
- 自動売買。
- secrets平文コミット。
- Safety Layer未実装での実売買。

### Phase10完了条件

- Tachibana read-only疎通PASS。
- account / positions / orders / history snapshot取得PASS。
- realtime quote取得PASS。
- secrets管理PASS。
- order APIが明示的に禁止されていること。
- no-live-order audit PASS。
- Paper LedgerとBroker Snapshotのreconciliation設計完了。
- Phase11 Safety Layerに進める状態。

## 9. Phase11への前提

Phase11タイトル:

```text
Safety Layer / Emergency Brake
```

Phase11で実装予定:

- 個別銘柄 -7% warning。
- 個別銘柄 -10% sell candidate。
- 個別銘柄 -15% forced sell candidate。
- 立花証券realtime quote監視。
- portfolio drawdown based buy suspension。
- emergency stop。
- auto recovery。
- safety state machine。
- safety report。

Phase11は、Phase10でBroker read-only / realtime quoteが安定してから着手する。Safety LayerはAI判断とは独立したルールベース安全装置として設計する。

## 10. 次チャットで最初に読むべき資料

優先順:

1. `docs/phase_reports/phase9_completion_summary_and_phase10_handoff.md`
2. `docs/01_requirements/phase_roadmap.md`
3. `docs/phase_reports/phase9v_score_saturation_fix.md`
4. `docs/phase_reports/phase9w_unified_runner_market_refresh_and_date_resolution.md`
5. `docs/phase_reports/phase9z3_trading_calendar_refresh_before_business_day_guard.md`
6. `docs/phase_reports/phase9z4_manifest_status_ledger_summary.md`
7. `docs/phase_reports/phase9aa_daily_notifications.md`
8. `.runtime/phase9/ledger/latest.json`
9. `.runtime/phase9/tracker/phase9_30bd_tracker.json`
10. `scripts/run_aifundlab_daily_paper_trading.py`

## 11. 禁止事項

本資料作成では以下を実行していない。

- コード実装。
- API接続。
- Broker注文。
- OpenD起動。
- unlock_trade。
- 実売買。
- AI再学習。
- フルバックテスト。
- scheduler/launchd変更。
- Ledger変更。
- secrets作成/編集。

## 12. 判定

```text
PHASE9_HANDOFF_READY
```

理由:

- Unified Daily Runnerは稼働中。
- launchd 20:00実行が継続中。
- Paper Ledgerは稼働中。
- Virtual Fillは実行済み。
- Blog Report v4は生成中。
- 30BD trackerは6/30まで進行。
- LINE / Discord通知準備済み。
- Phase10の方向性はTachibana Securities API Connectionとしてロードマップに反映済み。

ただし、Phase9の30営業日検証は未完走のため、Phase10はread-only / dry-run / no-live-order境界を厳守して開始する。
