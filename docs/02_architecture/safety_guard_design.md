# AI Fund Lab vNext Safety Guard 設計書

---

# 1. このドキュメントの目的

本ドキュメントは、

```text
Safety Guard
```

の役割、責務、停止条件を定義する。

---

# 2. Safety Guard の役割

## 一言で言うと

```text
システムを壊さないための最後の砦
```

---

Candidate AI が正しくても、

Opportunity AI が正しくても、

Broker Sync が壊れていたら失敗。

---

Safety Guard の目的は、

```text
利益を出すこと
```

ではない。

---

目的は、

```text
致命的な事故を防ぐこと
```

である。

---

# 3. 基本思想

## 最重要原則

```text
分からない時は止まる
```

---

禁止。

```text
多分大丈夫

きっと大丈夫

たまたま
```

---

異常があれば、

```text
停止
```

を優先する。

---

# 4. システム内の位置付け

```text
Candidate AI

↓

Opportunity AI

↓

Broker Sync Manager

↓

Portfolio State Manager

↓

Position Management AI

↓

Capital Allocation Engine

↓

Safety Guard

↓

Order Manager
```

---

Safety Guard は、

```text
全体
```

を監視する。

---

# 5. Safety Status

状態は3段階。

---

## OK

```text
正常
```

売買継続可能。

---

## WARNING

```text
注意
```

運用継続。

ログ記録。

通知送信。

---

## HALT

```text
停止
```

新規売買禁止。

人間確認待ち。

---

# 6. 監視対象

## API状態

監視対象

```text
立花証券 API

J-Quants API
```

---

異常例

```text
タイムアウト

認証失敗

レスポンス異常

連続失敗
```

---

# 7. Broker Sync監視

最重要。

---

比較対象

```text
システム状態

証券会社状態
```

---

確認項目

```text
現金残高

保有銘柄

保有数量

注文状態
```

---

不一致

↓

```text
HALT
```

---

# 8. 注文監視

監視対象

```text
注文状態
```

---

異常例

```text
二重注文

注文重複

約定未確認

注文失敗
```

---

結果

```text
WARNING

または

HALT
```

---

# 9. Portfolio監視

監視対象

```text
保有銘柄数

資金使用率

損益
```

---

異常例

```text
想定外ポジション

保有数超過

資金超過利用
```

---

結果

```text
HALT
```

---

# 10. 損失監視

## 日次損失

例

```text
-5%
```

超過。

---

結果

```text
WARNING
```

---

## 総DD

例

```text
-10%
```

超過。

---

結果

```text
HALT
```

---

数値は後で調整可能。

---

# 11. AI異常監視

監視対象

```text
Candidate AI

Opportunity AI

Position Management AI
```

---

異常例

```text
候補数ゼロ

候補数異常増加

全銘柄BUY

全銘柄SELL
```

---

結果

```text
WARNING
```

---

# 12. データ異常監視

異常例

```text
株価ゼロ

出来高ゼロ

取得失敗

欠損大量発生
```

---

結果

```text
HALT
```

---

# 13. HALT条件

即停止。

---

## API認証失敗

---

## Broker Sync不一致

---

## 想定外ポジション

---

## 二重注文疑い

---

## Portfolio破損

---

## データ破損

---

## 人間による停止指示

---

# 14. WARNING条件

警告のみ。

---

## API遅延

---

## 日次損失超過

---

## AI候補数異常

---

## 一時的取得失敗

---

# 15. 停止時の動作

禁止。

```text
新規買い
```

---

許可。

```text
状態取得

監査

レポート生成
```

---

設定可能。

```text
保有継続

保有売却
```

---

# 16. 通知

通知対象

```text
WARNING

HALT
```

---

通知内容

```text
発生時刻

異常内容

対象モジュール

影響範囲

推奨対応
```

---

# 17. ログ

必須保存。

---

保存対象

```text
停止理由

警告理由

APIエラー

注文エラー

同期エラー

Portfolio不整合
```

---

# 18. 復旧

復旧条件

```text
異常解消

Broker Sync成功

人間確認
```

---

自動復旧禁止。

---

再開は、

```text
人間承認
```

必須。

---

# 19. やってはいけないこと

禁止。

```text
エラー無視

同期無視

注文失敗無視

ポジション不一致無視

推測で継続
```

---

# 20. 最終原則

Safety Guard は、

```text
利益を作らない
```

---

しかし、

```text
利益を守る
```

---

AI Fund Lab の最終責任者は、

```text
Candidate AI

Opportunity AI

Position Management AI
```

ではない。

---

最後の責任者は、

```text
Safety Guard
```

である。

---

異常時は、

```text
儲けるより止まる
```

を優先する。
