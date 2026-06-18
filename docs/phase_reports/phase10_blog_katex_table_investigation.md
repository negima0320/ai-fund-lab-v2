# Phase10 Blog KaTeX Table Investigation

作成日: 2026-06-17

判定:

```text
NOT_RECOMMENDED
```

対象:

- 保有銘柄
- 当日購入銘柄
- 当日売却銘柄
- Candidate Top50
- Top5候補
- 資産推移

## 1. KaTeX表の対応状況

KaTeX公式Support Tableを確認した。

参照:

- https://katex.org/docs/support_table.html
- https://docs.github.com/en/get-started/writing-on-github/working-with-advanced-formatting/writing-mathematical-expressions

確認結果:

- `{array}` はサポート対象。
- `{matrix}` / `{bmatrix}` などのmatrix系はサポート対象。
- `{aligned}` / `{align}` などの整列環境はサポート対象。
- `\hline` はサポート対象。
- `\cline` は非対応。
- `\text{...}` はサポート対象。
- GitHub MarkdownはLaTeX形式の数式表示に対応しているが、GitHub側はMathJaxレンダリングであり、note/KaTeXと同一挙動とは限らない。

Phase9 Blog Reportの表現には、`array` が最も近い。

例:

```latex
\[
\begin{array}{|c|r|r|r|}
\hline
Code & Qty & Price & PnL \\\\
\hline
1579 & 200 & 846.8 & -200 \\\\
166A & 100 & 1091.0 & +2100 \\\\
\hline
\end{array}
\]
```

## 2. noteで利用可能か

今回のローカル調査では、noteへ実投稿しての表示確認は行っていない。

前提として、note上でKaTeX数式が表示できる場合、`array` 形式の表は表示候補になり得る。ただし、以下の理由で本番採用前にnoteエディタ上での手動貼り付け確認が必須。

- note側のMarkdown/KaTeX処理が公式KaTeXそのものと完全一致する保証がない。
- `\[` `\]` のブロック数式区切りがnoteで通るかは、note側実装に依存する。
- `\\\\` をMarkdown上に残した場合、note側で期待どおりKaTeX行区切りへ変換されるかは実機確認が必要。
- 長い日本語銘柄名はKaTeX表内で折り返しにくく、モバイル表示で横にはみ出す可能性が高い。

結論:

```text
noteで使える可能性はあるが、現時点では本採用不可。
短い数値表のみ手動検証対象。
```

## 3. `\\\\` 改行エスケープの検証結果

サンプルMarkdownを作成した。

```text
reports/public/phase9_daily/2026-06-16_blog_report_katex_table_sample.md
```

軽量テストを追加した。

```text
tests/paper_trading/test_phase10_blog_katex_table_investigation.py
```

検証内容:

- KaTeX表サンプル内に `\\\\` が含まれる。
- 表の行末が単独の `\\` ではなく、Markdown上で `\\\\` になっている。
- Python文字列 `row = "Code & Qty & Price & PnL \\\\\\\\"` を書き出した後、実ファイル上に `\\\\` が残る。

実行結果:

```bash
python3 -m pytest tests/paper_trading/test_phase10_blog_katex_table_investigation.py
```

```text
2 passed
```

既存Blog Reportテストとの併走:

```bash
python3 -m pytest tests/paper_trading/test_phase9t_blog_report_v2.py tests/paper_trading/test_phase10_blog_katex_table_investigation.py
```

```text
4 passed
```

## 4. サンプル出力

資産推移:

```latex
\[
\begin{array}{|c|r|}
\hline
Item & Value \\\\
\hline
Initial & 1{,}000{,}000 \\\\
Current & 993{,}140 \\\\
PnL & -6{,}860 \\\\
PnL\% & -0.69\% \\\\
Cash & 283{,}330 \\\\
MarketValue & 709{,}810 \\\\
\hline
\end{array}
\]
```

保有銘柄:

```latex
\[
\begin{array}{|c|r|r|r|r|}
\hline
Code & Qty & Avg & Last & PnL \\\\
\hline
1579 & 200 & 846.8 & 845.8 & -200 \\\\
166A & 100 & 1091.0 & 1112.0 & +2100 \\\\
213A & 300 & 544.7 & 542.5 & -660 \\\\
221A & 100 & 1538.0 & 1530.0 & -800 \\\\
3063 & 100 & 1210.0 & 1137.0 & -7300 \\\\
\hline
\end{array}
\]
```

日本語セル:

```latex
\[
\begin{array}{|c|c|}
\hline
\text{区分} & \text{状態} \\\\
\hline
\text{保有} & \text{継続} \\\\
\text{売却} & \text{なし} \\\\
\hline
\end{array}
\]
```

## 5. 利点

- noteでMarkdown表が崩れる場合、数式ブロックとして表を固定表示できる可能性がある。
- 数値中心の短い表では、縦罫線と横罫線により見た目が揃う。
- `array` に寄せることで、Markdown表パーサ差異を一部回避できる。
- `\\\\` の実ファイル保持はPythonテストで検証可能。

## 6. 欠点

- Markdownとしての可読性が低い。
- GitHub / VSCode / noteでレンダリングエンジンが異なり、表示互換性が落ちる。
- Candidate Top50のような長い表は、モバイル表示で横スクロールまたは縮小表示になりやすい。
- 長い日本語銘柄名をKaTeX表内に入れると折り返しが難しい。
- コピー後の再利用性が低い。表としてコピーするより、LaTeXソースとしてコピーされる。
- `\%`, `{,}`, `&`, `_` など、値のエスケープ処理が必要になる。
- `\cline` が使えないため、複雑な罫線制御は難しい。

## 7. Markdown表との比較

Markdown標準表:

```markdown
| Code | Qty | Price | PnL |
|---:|---:|---:|---:|
| 1579 | 200 | 846.8 | -200 |
| 166A | 100 | 1091.0 | +2100 |
```

比較:

| 観点 | Markdown表 | KaTeX array |
|---|---|---|
| GitHub Markdown | 強い | 数式レンダリング依存 |
| VSCode Preview | 強い | 標準Previewでは不安定、拡張依存 |
| note | note側の表対応に依存 | note側のKaTeX対応に依存 |
| モバイル表示 | 比較的自然 | 横長になりやすい |
| 日本語銘柄名 | 扱いやすい | 折り返しに弱い |
| コピー性 | 高い | 低い |
| 実装保守 | 容易 | エスケープが増える |
| 数値の見栄え | 十分 | 短い表なら良い |

## 8. 推奨方式

全面KaTeX化は推奨しない。

推奨:

```text
Markdown標準表を第一候補にする。
noteでMarkdown表が崩れる場合のみ、短い数値表に限定してKaTeX arrayを代替採用する。
```

対象別:

| 対象 | 推奨 |
|---|---|
| 資産推移 | Markdown表。note崩れ時のみKaTeX可 |
| 保有銘柄 | Markdown表。銘柄名は表外補足も可 |
| 当日購入銘柄 | Markdown表 |
| 当日売却銘柄 | Markdown表または「本日はなし」の短文 |
| Candidate Top50 | KaTeX非推奨。長すぎるためMarkdown表またはリスト |
| Top5候補 | Markdown表。note崩れ時のみKaTeX可 |

最終判定:

```text
NOT_RECOMMENDED
```

ただし、以下の限定条件では再評価可能。

```text
note実機でKaTeX arrayが安定表示される
表は5行程度まで
銘柄名を表内に入れずCode中心にする
実ファイル上の行区切りが \\\\ であることをテストで保証する
```
