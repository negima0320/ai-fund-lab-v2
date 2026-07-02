# Portfolio Rotation AI / Position Management v2 Design

## 1. Purpose

Portfolio Rotation AI is not a simple Exit AI.

It is a mechanism for comparing where limited capital should be placed:

```text
current holding expected value

vs

new candidate expected value
```

The core question is:

```text
Should capital remain in this holding,
or should it rotate into a higher expected-value candidate?
```

Phase13 is a design and validation phase only. It does not yet confirm whether this should become a new AI, Position Management AI v2, or part of Capital Allocation.

## 2. Difference From Position Management AI

Position Management AI is a health check for holdings.

```text
holding-only view

HOLD / EXIT / ADD / REDUCE
```

Portfolio Rotation AI compares holdings with new candidates.

```text
holding vs candidate view

HOLD / ROTATE / REDUCE / EXIT
```

Position Management AI asks:

```text
Is this holding still healthy?
```

Portfolio Rotation AI asks:

```text
Is this holding still the best use of capital?
```

## 3. Difference From Opportunity AI

Opportunity AI ranks new candidates.

```text
new candidate expected value ranking
```

Portfolio Rotation AI includes existing holdings in the comparison universe.

```text
existing holdings

+

new candidates

=

capital placement comparison
```

Opportunity AI should not learn from portfolio outcomes, broker state, or backtest results. Portfolio Rotation AI must follow the same data boundary.

## 4. Difference From Capital Allocation

Capital Allocation decides:

```text
how much to buy

how many positions to hold

how to satisfy portfolio constraints
```

Portfolio Rotation AI decides:

```text
which holding should remain

which holding is a rotation candidate

which new candidate is worth rotating into
```

Capital Allocation may consume Rotation proposals later, but Phase13 must first define the responsibility boundary.

## 5. Input Candidates

Allowed input candidates:

```text
J-Quants derived features

Candidate AI score

Opportunity AI score

Position Management AI output

prediction-time features for holdings

expected value estimate for holdings

expected value estimate for new candidates

holding_days

current_return

peak_return

position_size

volatility

trend strength

market regime

sector strength
```

Runtime holding information may be used as decision input. If any holding-derived field is proposed as an AI training feature, it must pass leakage audit first.

Forbidden as AI training or inference features:

```text
future_return

future_max_return

future_drawdown

trade_result

realized PnL

Broker Snapshot

Paper Ledger

Safety Result

Audit Result

cash

portfolio value

selected / bought / affordable data

backtest result
```

Future return, future drawdown, and post-sell return may be used only as evaluation labels, never as prediction-time input.

## 6. Output Candidates

Output candidates:

```text
HOLD

ROTATE

REDUCE

EXIT

ADD_CANDIDATE
```

`ROTATE` means:

```text
The holding is not necessarily broken,
but a new candidate has sufficiently higher expected value,
so capital replacement should be reviewed.
```

`ROTATE` should become a distinct sell reason so that reports can separate:

```text
loss cut

trend end

profit protection

max holding days

rotation
```

## 7. Evaluation Design

Phase13 evaluation should compare:

```text
Phase12-G SELL integrated

vs

Phase13 Rotation integrated
```

Minimum metrics:

```text
annualized_return

max_drawdown

profit_factor

trade_count

average_holding_days

capital_turnover

early_sell_count

early_sell_opportunity_loss

loss_cut_avoided_loss

rotation_success_rate

rotation_after_return

rotation_opportunity_cost
```

Phase12-H baseline:

```text
1 year annualized_return:
17.6736%

1 year max_drawdown:
-24.7342%

5 year annualized_return:
51.2017%

5 year max_drawdown:
-21.5802%

SELL after 20 business days > +5%:
60 cases

SELL after 20 business days < -5%:
143 cases

estimated avoided loss:
about 1,146,749 JPY
```

The first Phase13 success test is whether Rotation can improve the degraded 1-year result without destroying the 5-year annualized return above 50%.

## 8. Risks

Primary risks:

```text
overtrading

fee and slippage sensitivity

overreaction to short-term noise

early selling of strong winners

rotation when expected-value spread is too small

responsibility overlap with Position Management AI

responsibility overlap with Opportunity AI

responsibility overlap with Capital Allocation
```

Controls to design:

```text
minimum expected-value spread

minimum holding period

confirmation window

sector concentration guard

turnover budget

slippage-aware evaluation

ROTATE-specific explainability
```

## 9. Phase13 Work Plan

Phase13 should proceed as:

```text
Phase13-A:
Responsibility boundary design

Phase13-B:
Rotation hypothesis design

Phase13-C:
Post-hoc analysis using existing artifacts

Phase13-D:
Lightweight prototype

Phase13-E:
1-year / 5-year comparison
```

Implementation starts only after Phase13 design review. Phase12 Demo operation work continues independently.

## 10. Non-Goals

Phase13 design does not allow:

```text
AI retraining

Backtest rerun as part of this roadmap update

Broker API connection

Demo order

Production order

Production Unlock

LINE send

LLM investment decision automation

margin trading

leverage
```

## 11. Open Design Questions

Open questions:

```text
Should Rotation be a new AI or Position Management AI v2?

Should Rotation produce only proposals, or final SELL reasons?

Should Capital Allocation decide the final replacement set after Rotation proposals?

How large must expected-value spread be before ROTATE is valid?

How should transaction cost and slippage be included?

How should sector and market regime constraints affect rotation?
```

Phase13 must answer these before any implementation or retraining.
