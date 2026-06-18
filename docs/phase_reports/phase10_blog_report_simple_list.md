# Phase10 Blog Report Simple List

Status:

```text
PHASE10_BLOG_SIMPLE_LIST_COMPLETE
```

## 表形式を中止した理由

Phase9公開ブログレポートでは、KaTeX表、Markdown表、表画像化をいったん中止した。

理由:

- note本文幅では横長表が読みづらい。
- KaTeXはnote貼り付け時のレンダリングが安定しない。
- 表画像は文字が小さくなり、スマートフォンで読みづらい。
- 公開ブログの読者にとって重要なのは、まず「何の銘柄か」を素早く見ること。
- 理由・補足は定型文が多く、公開本文では情報量に対して可読性が悪い。

## シンプルリスト採用理由

シンプルリストは、note本文にそのまま貼り付けても表示が安定する。

採用理由:

- Markdownの標準的な番号付きリストだけで表示できる。
- 銘柄コード、銘柄名、スコア、数量、価格、損益を1行で確認できる。
- Candidate Top50を分割せず、50件すべてを同じ形式で読める。
- 表の横スクロールやKaTeX失敗時の文字列表示を避けられる。
- 理由・補足はJSONに残し、公開本文では省略できる。

## 表示項目

資産状況:

- 現金
- 株式評価額
- 現在資産
- 損益
- 損益率
- 実現損益
- 含み損益

現在保有中の銘柄:

- No
- Code
- 銘柄名
- 数量
- 評価額
- 損益

本日の購入銘柄:

- No
- Code
- 銘柄名
- 数量
- 約定価格

本日の売却銘柄:

- No
- Code
- 銘柄名
- 数量
- 約定価格
- 損益

Candidate Top50:

- Rank
- Code
- 銘柄名
- Candidate Score

本日の購入候補 Top5:

- Rank
- Code
- 銘柄名
- Opportunity Score
- AI信頼度

## 削除した項目

公開Markdown本文から削除した項目:

- KaTeX数式ブロック
- `\begin{array}` によるKaTeX表
- Markdown表
- Candidate Top50の理由
- Candidate Top50の補足
- Top5の理由
- Top5の補足
- 保有理由の長文
- 購入理由の銘柄別長文

購入理由は、本文では次の一文に集約した。

```text
購入理由: AI評価上位かつ資金配分ルールを満たしたため。
```

内部JSONには、従来どおり理由・補足系フィールドを保持している。

## note貼り付け運用方針

運用方針:

- v4 Markdownをnote本文へそのまま貼り付ける。
- KaTeX、Markdown表、表画像は使わない。
- Candidate Top50は50件すべて番号付きリストで表示する。
- 銘柄名が長い場合も、note側の通常テキスト折り返しに任せる。
- 読者向けには銘柄識別とスコア確認を優先する。

## 生成結果

生成したレポート:

```text
reports/public/phase9_daily/2026-06-16_blog_report_v4.md
```

JSON:

```text
reports/public/phase9_daily/2026-06-16_blog_report_v4.json
```

生成結果:

```text
BLOG_REPORT_V2_READY
PUBLIC_REPORT_READY
```

確認結果:

- v4に `$$` は含まれない。
- v4に `\begin{array}` は含まれない。
- v4にMarkdown表の `|` 区切りは含まれない。
- Candidate Top50は50件すべて表示される。
- Candidate Top50に銘柄名が含まれる。
- 本日の購入候補 Top5に銘柄名が含まれる。
- 現在保有中の銘柄に銘柄名が含まれる。
- 本日の購入銘柄に銘柄名が含まれる。
- Candidate Top50から理由・補足の定型長文を削除した。

## テスト結果

実行コマンド:

```bash
python3 -m pytest tests/paper_trading/test_phase9t_blog_report_v2.py
```

結果:

```text
2 passed
```

補足:

PyArrowがmacOS sandbox上でCPU情報取得の警告を出すことがあるが、レポート生成とテスト結果には影響しなかった。
