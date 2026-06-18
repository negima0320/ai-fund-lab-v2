# Phase10 Blog Report KaTeX Fix

作成日: 2026-06-17

判定:

```text
PHASE10_BLOG_KATEX_FIX_COMPLETE
```

## 前回実装の問題点

前回のKaTeX表化は、方向性としてはKaTeX table採用だったが、次の問題があった。

- note貼り付け時にKaTeXとしてレンダリングされず、文字列表示になるケースがあった。
- 元リストの情報を表へ完全に引き継げていなかった。
- 保有銘柄・購入銘柄の銘柄名が表から欠落していた。
- Candidate Top50が上位10件だけ表で、11位以降が従来リストだった。
- Top5候補の表に銘柄名・理由・補足が入っていなかった。
- 既存レポートの内容を表化したのではなく、簡略版の別表になっていた。

## noteでKaTeXが表示されなかった原因調査

今回のnote向け出力では、以下を前提にした。

- KaTeXブロックはコードブロックで囲まない。
- `$$` は行頭単独で置く。
- `$$` ブロックの前後に空行を置く。
- `\begin{array}` の直後に `\hline` を置く。
- 各行末はPattern A形式の `\\\\ \hline` にする。
- `\text{日本語}` を含む最小サンプルを別ファイルで用意する。

最小検証サンプル:

```text
reports/public/phase9_daily/katex_note_minimal_test.md
```

このファイルはコードブロックなしで、本文に直接KaTeXを置く。

note貼り付け確認ポイント:

- `$$` の前後に空行がある状態で貼る。
- `$$` の前にスペースや引用記号を入れない。
- 見出し直後で崩れる場合は、見出しと `$$` の間に空行を1行残す。
- 最小サンプルが表示されることを先に確認する。
- 長いarrayで崩れる場合は、Candidateのように10件単位で分割する。

## Pattern A正式採用

採用Pattern:

$$
\begin{array}{|l|l|r|}
\hline
\text{Code} & \text{Name} & \text{Score} \\\\ \hline
\text{1579} & \text{日経レバレッジ} & 95 \\\\ \hline
\text{3063} & \text{ジェイグループHD} & 81 \\\\ \hline
\end{array}
$$

必須条件:

- `\begin{array}{...}`
- `\hline`
- ヘッダー `\\\\ \hline`
- データ行 `\\\\ \hline`
- `\end{array}`

## 情報欠落の修正内容

v4でKaTeX表化した対象:

- 資産状況
- 現在保有中の銘柄
- 本日の購入銘柄
- 本日の売却銘柄
- Candidate Top50
- 本日の購入候補 Top5

保有銘柄の必須列:

```text
Code
銘柄名
Qty
Price
Market Value
PnL
保有理由
```

購入銘柄の必須列:

```text
Code
銘柄名
Qty
Price
購入理由
```

Candidate Top50:

- 50件すべてをKaTeX表化。
- 10件ずつ、5つのKaTeX表に分割。
- Rank / Code / 銘柄名 / Candidate Score / 理由 / 補足 を保持。

Top5:

- 5件すべてを1つのKaTeX表に出力。
- Rank / Code / 銘柄名 / Opportunity Score / AI信頼度 / 理由 / 補足 を保持。

## KaTeX escape方針

実装箇所:

```text
src/ai_fund_lab_v2/paper_trading/reporting/blog_report_v2_writer.py
```

追加/修正した主な関数:

- `_render_markdown_v4`
- `_katex_array`
- `_katex_text`
- `_katex_code`
- `_katex_number`
- `_katex_escape_text_char`
- `_katex_escape_math_char`

escape対象:

```text
_
%
&
#
{
}
\
$
```

置換は文字単位で行う。これにより、`\` を `\textbackslash{}` へ置換した後に、生成済みの `{}` がさらに再置換される問題を避ける。

## v4レポート生成結果

生成:

```text
reports/public/phase9_daily/2026-06-16_blog_report_v4.md
reports/public/phase9_daily/2026-06-16_blog_report_v4.json
```

生成結果:

```text
BLOG_REPORT_V2_READY
```

確認:

- v4に ```latex は含まれない。
- v4にコードフェンス ``` は含まれない。
- v4に `$$` が含まれる。
- v4に `\begin{array}` が含まれる。
- array直後に `\hline` がある。
- 保有銘柄に銘柄名が含まれる。
- 購入銘柄に銘柄名が含まれる。
- Candidate Top50は5つのKaTeX表で50件保持。
- Top5に銘柄名・理由・補足が含まれる。
- KaTeX特殊文字escapeの単体テストを追加。

## テスト

実行:

```bash
python3 -m pytest tests/paper_trading/test_phase9t_blog_report_v2.py tests/paper_trading/test_phase10_blog_katex_table_investigation.py
```

結果:

```text
7 passed
```

## 残課題

- note実機で `katex_note_minimal_test.md` を先に貼り付け、最小サンプルの表示を確認する。
- v4のCandidate Top50は長いため、noteモバイルで横幅・スクロール挙動を確認する。
- 長い銘柄名が多いETF/ETN候補では、note側のレンダリング幅に依存する。
- 必要なら、次段階でCandidateだけ案B、つまり表を Rank / Code / 銘柄名 / Score に絞り、理由・補足をRank別短文へ分離する。

## 完了判定

```text
PHASE10_BLOG_KATEX_FIX_COMPLETE
```

