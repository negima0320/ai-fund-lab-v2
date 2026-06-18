# Phase10 Blog KaTeX Table Border Fix Samples

note貼り付け確認用。

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

## Recommended Holding Table

$$
\begin{array}{|l|r|r|r|}
\hline
\text{Code} & \text{Qty} & \text{Price} & \text{PnL} \\\\ \hline
15790 & 200 & 1234 & -1.2\% \\\\ \hline
166A0 & 100 & 987 & +2.1\% \\\\ \hline
\end{array}
$$

## Japanese Cell Check

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
