# Phase13 Replacement Policy Roadmap Update

作成日: 2026-07-03

## 更新対象

- `docs/01_requirements/phase_roadmap.md`

## 追記内容

Phase13に `Replacement Policy / Portfolio Rotation AI` を正式追記した。

主な追記内容:

- 「より良い新規候補が出たら、既存保有を売って入れ替える」判断をPhase13テーマとして明記
- Phase12.5時点でOperations RuntimeにReplacement判断が未実装であることを明記
- SELLがExit条件またはfallback hard stopのみで、BUY/SELLが独立生成であることを明記
- 保有銘柄と新規BUY候補のスコア比較が未接続であることを明記
- `max_positions=5` はmetadata/configとして存在するが、`current_positions - planned_sell + planned_buy <= max_positions` の直接ガードは未確認であることを明記
- Phase13で設計・実装すべきReplacement edge margin、minimum holding days、turnover上限、max_positions厳格制御、SELL_FIRST_BUY_AFTER_FILL、Broker buying power SoT、Report/Audit出力を追記

## Phase12.5からの背景

Phase12.5のRuntime監査で、Daily PlanのSELL候補生成は `positions` artifact由来のExit条件またはfallback hard stopに限られていることが確認された。

一方、投資方針として必要な「今の保有より良い候補が出たら入れ替える」判断は、Operations Runtime本線には接続されていない。

このため、Phase12.5ではReplacementを新規実装せず、Production Equivalent Runtime Acceptanceを優先し、ReplacementはPhase13課題として明示する。

## Phase13で実装すべき理由

- 初日に買った銘柄が固定化されるリスクを避けるため
- ただし毎日過剰回転しないよう、edge margin / minimum holding days / turnover上限が必要なため
- SELL予定額をBUY予算に先取り加算せず、売却約定後にBroker buying powerを正として再評価する安全設計が必要なため
- Daily Reportで「なぜ売るか」「なぜ買うか」「なぜ入れ替えるか」を説明可能にするため

## 今回は実装していないこと

- Runtime実装変更なし
- Replacementロジック実装なし
- Submit実行なし
- Broker注文なし
- Production接続・Production注文なし
- artifact削除・再生成なし
- launchd変更なし
- notification送信なし
- AI再学習なし
- フルバックテストなし
