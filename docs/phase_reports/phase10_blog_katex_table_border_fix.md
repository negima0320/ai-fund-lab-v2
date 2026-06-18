# Phase10 Blog KaTeX Table Border Fix

作成日: 2026-06-17

判定:

```text
RECOMMENDED
```

ただし、採用対象は短い数値表に限定する。

## 目的

note上でKaTeX `array` 表が表示できることは確認済み。

一方で、次の形式では最上部の横罫線が表示されない問題がある。

```latex
$$
\begin{array}{|l|c|r|}
\text{TH1} & \text{TH2} & \text{TH3} \\\\ \hline
\text{R1C1} & \text{R1C2} & \text{R1C3} \\\\ \hline
\text{R2C1} & \text{R2C2} & \text{R2C3} \\\\ \hline
\end{array}
$$
```

原因は、`array` の先頭に `\hline` がないため、ヘッダー行より上の横罫線が描画されないことと考えられる。

KaTeX公式Support Tableでは `{array}` がサポート対象、`\hline` がサポート対象、`\cline` は非対応とされている。

参照:

- https://katex.org/docs/support_table.html

## Pattern A

```latex
$$
\begin{array}{|l|c|r|}
\hline
\text{TH1} & \text{TH2} & \text{TH3} \\\\ \hline
\text{R1C1} & \text{R1C2} & \text{R1C3} \\\\ \hline
\text{R2C1} & \text{R2C2} & \text{R2C3} \\\\ \hline
\end{array}
$$
```

評価:

- 上罫線: 表示される想定。
- 左右罫線: 表示される想定。
- 行罫線: 表示される想定。
- Markdown出力上の行区切り: `\\\\`
- note適性: 良い。
- 保守性: 中。行末に `\\\\ \hline` を置くため、Python生成時にやや読みにくい。

コメント:

先頭罫線欠落だけを直すなら、この形でも成立する可能性が高い。

## Pattern B

```latex
$$
\begin{array}{|l|c|r|}
\hline
\text{TH1} & \text{TH2} & \text{TH3} \\\\
\hline
\text{R1C1} & \text{R1C2} & \text{R1C3} \\\\
\hline
\text{R2C1} & \text{R2C2} & \text{R2C3} \\\\
\hline
\end{array}
$$
```

評価:

- 上罫線: 表示される想定。
- 左右罫線: 表示される想定。
- 行罫線: 表示される想定。
- Markdown出力上の行区切り: `\\\\`
- note適性: 最も良い。
- 保守性: 良い。行区切りと罫線命令を分けるため、生成コードと目視確認がしやすい。

コメント:

今回の最終推奨パターン。`array` 直後に `\hline` を置き、各データ行の後に独立行として `\hline` を置く。

## Pattern C

```latex
$$
\begin{array}{|l|c|r|}
\hline
\hline
\text{TH1} & \text{TH2} & \text{TH3} \\\\
\hline
\text{R1C1} & \text{R1C2} & \text{R1C3} \\\\
\hline
\text{R2C1} & \text{R2C2} & \text{R2C3} \\\\
\hline
\end{array}
$$
```

評価:

- 上罫線: 表示される想定。
- 左右罫線: 表示される想定。
- 行罫線: 表示される想定。
- Markdown出力上の行区切り: `\\\\`
- note適性: 条件付き。
- 保守性: 中。

コメント:

先頭に二重線を作る意図なら使える可能性があるが、通常のブログ表としては強すぎる。上罫線を確実に出す目的だけなら過剰。

## Pattern D

```latex
$$
\left|
\begin{array}{lcr}
\text{TH1} & \text{TH2} & \text{TH3} \\\\
\text{R1C1} & \text{R1C2} & \text{R1C3} \\\\
\text{R2C1} & \text{R2C2} & \text{R2C3}
\end{array}
\right|
$$
```

評価:

- 上罫線: 表示されない。
- 左右罫線: 外側のみ表示される想定。
- 行罫線: 表示されない。
- Markdown出力上の行区切り: `\\\\`
- note適性: 低い。
- 保守性: 良いが、表としての視認性が弱い。

コメント:

罫線付き表ではなく、縦棒で囲んだ数式配列になる。Phase9 Blog Reportの表には不向き。

## note表示結果

現状確認済み:

| パターン | note表示 | 上罫線 | 左右罫線 | 行罫線 | 日本語セル | モバイル |
|---|---|---|---|---|---|---|
| 既存形式 | 確認済み | NG | OK想定 | OK想定 | 要確認 | 要確認 |
| Pattern A | 要note実機確認 | OK想定 | OK想定 | OK想定 | 要確認 | 要確認 |
| Pattern B | 要note実機確認 | OK想定 | OK想定 | OK想定 | 要確認 | 要確認 |
| Pattern C | 要note実機確認 | OK想定 | OK想定 | OK想定 | 要確認 | 要確認 |
| Pattern D | 要note実機確認 | NG想定 | 外枠のみ | NG | 要確認 | 要確認 |

この環境からnoteエディタへ実投稿しての視覚確認は行っていない。ユーザー側で既存形式がnote表示できることは確認済みのため、次の手動確認ではPattern Bを最優先にする。

## スクリーンショット保存方法

推奨保存先:

```text
reports/public/phase9_daily/katex_table_border_screenshots/
```

推奨ファイル名:

```text
pattern_a_desktop.png
pattern_a_mobile.png
pattern_b_desktop.png
pattern_b_mobile.png
pattern_c_desktop.png
pattern_c_mobile.png
pattern_d_desktop.png
pattern_d_mobile.png
```

確認手順:

1. noteの下書き記事にPattern A-Dを貼り付ける。
2. デスクトップ幅でプレビューを表示する。
3. 各Patternの上罫線、左右罫線、行罫線を確認する。
4. ブラウザ開発者ツールまたは実スマホでモバイル幅を確認する。
5. 日本語セル入りPatternを追加で貼り付ける。
6. スクリーンショットを上記保存先へ保存する。
7. 表示結果をこの資料へ追記する。

## 日本語セル確認用

```latex
$$
\begin{array}{|l|c|r|}
\hline
\text{区分} & \text{状態} & \text{損益} \\\\
\hline
\text{保有} & \text{継続} & -1.2\% \\\\
\hline
\text{売却} & \text{なし} & 0.0\% \\\\
\hline
\end{array}
$$
```

## 最終推奨パターン

Pattern Bを推奨する。

```latex
$$
\begin{array}{|l|r|r|r|}
\hline
\text{Code} & \text{Qty} & \text{Price} & \text{PnL} \\\\
\hline
15790 & 200 & 1234 & -1.2\% \\\\
\hline
166A0 & 100 & 987 & +2.1\% \\\\
\hline
\end{array}
$$
```

理由:

- `\begin{array}` 直後に `\hline` があり、上罫線欠落を避けられる。
- 行区切り `\\\\` と罫線 `\hline` を別行にするため、生成コードが読みやすい。
- note貼り付け時の差分確認がしやすい。
- 最小限のKaTeX構文だけで構成できる。

## 採用可否

短い数値表については採用可。

```text
RECOMMENDED
```

ただし、以下は非推奨。

- Candidate Top50全体のKaTeX表化
- 長い日本語銘柄名を表内に入れる形式
- PC幅前提の列数が多い表
- `\hline` を行末へ詰め込むだけの生成方式

## Phase9 Blog Reportへの最小変更案

本番コードはまだ変更しない。

もしnote実機でPattern Bが最も綺麗に表示される場合、最小変更は以下。

```text
KaTeX表生成時に、array開始直後へ \hline を追加する。
各行は Markdown出力上で \\\\ を保持する。
各行の直後に独立行として \hline を出力する。
```

Python生成イメージ:

```python
lines = [
    "$$",
    r"\begin{array}{|l|r|r|r|}",
    r"\hline",
    r"\text{Code} & \text{Qty} & \text{Price} & \text{PnL} \\\\",
    r"\hline",
    r"15790 & 200 & 1234 & -1.2\% \\\\",
    r"\hline",
    r"166A0 & 100 & 987 & +2.1\% \\\\",
    r"\hline",
    r"\end{array}",
    "$$",
]
```

注意:

```text
Markdown出力上に \\\\ が残ることをテストで保証する。
```

