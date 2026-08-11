# Phase29-L12 - 93180 Universe Eligibility / Low-Price Opportunity Root Cause Audit

## 0. Task ID

Phase29-L12

## 1. Primary Judgment

```text
PHASE29_L12_93180_LOW_PRICE_ELIGIBILITY_AND_REENTRY_DESIGN_GAP_IDENTIFIED_NO_PRODUCTION_DEFECT_READ_ONLY_AUDIT_COMPLETE
```

93180 was not bought because ADD was weakened. The mandatory 2022-09-08,
2022-09-09, and 2022-09-12 events were not BUY / ADD events in the run
evidence; they were SELL REDUCE / SELL REDUCE / SELL EXIT. The true BUY-side
issue is that a 4-6 JPY low-price issue was allowed to remain universe-eligible,
rank highly in Opportunity, pass Buy Quality as FULL_ALLOCATION_ELIGIBLE, and
receive normal target-weight notional allocations. After PM EXIT, the symbol was
also allowed to re-enter as BUY_NEW without a cooldown or low-price-specific
exclusion.

## 2. Scope and Non-Mutation Statement

Source run:

```text
reports/runtime_tests/runs/runtime-test-historical-smoke-20260810T232622909184Z
```

This audit is read-only.

```text
Production code changed: NO
Strategy changed: NO
Portfolio Management changed: NO
Portfolio Construction changed: NO
Position Sizing changed: NO
Candidate / Opportunity model changed: NO
Config changed: NO
Schema changed: NO
Runtime state / pending / ledger / accepted generation mutated: NO
Historical executed: NO
Fresh-run executed: NO
Resume executed: NO
```

Deliverables:

```text
docs/phase_reports/phase29_l12_93180_universe_eligibility_low_price_opportunity_root_cause_audit.md
reports/phase29_l12_93180_universe_eligibility_low_price_opportunity_root_cause_audit/
docs/01_requirements/phase_roadmap.md
```

## 3. Security Identity and Listed Authority

PIT listed authority:

```text
reports/runtime_tests/runs/runtime-test-historical-smoke-20260810T232622909184Z/daily/2022-08-26/market_refresh/inputs/historical_asof/2022-08-26/raw/jquants/listed_issues/data.parquet
reports/runtime_tests/runs/runtime-test-historical-smoke-20260810T232622909184Z/daily/2022-10-21/market_refresh/inputs/historical_asof/2022-10-21/raw/jquants/listed_issues/data.parquet
```

93180 listed row:

```text
Code: 93180
CoName: アジア開発キャピタル
CoNameEn: Asia Development Capital Co.Ltd.
S17: 16
S17Nm: 金融（除く銀行）
S33: 7100
S33Nm: 証券･商品先物取引業
ScaleCat: -
Mkt: 0112
MktNm: スタンダード
Mrgn: 1
MrgnNm: 信用
ProdCat: 011
```

Classification:

```text
Foreign / special security classification: UNKNOWN from PIT listed row
Issuer country / domestic-foreign field present: NO
Ordinary domestic common-stock equivalent under current system treatment: YES
Reason: ProdCat/security_type 011 and Standard market were treated as supported equity product evidence.
```

The audit found no PIT listed field that proves issuer country or foreign-stock
status. The system therefore did not have direct evidence to classify 93180 as
foreign. It treated ProdCat 011 as broker-supported listed equity.

## 4. Universe Eligibility

Current system result:

```text
Universe eligibility: PASS
Universe inclusion reason: BROKER_PRODUCT_CATEGORY_SUPPORTED + candidate_eligible + opportunity_rank_preserved
```

Portfolio Construction evidence for BUY dates:

```text
2022-08-26: reason_codes=[BROKER_PRODUCT_CATEGORY_SUPPORTED, buy_quality_full_allocation_eligible, candidate_eligible, opportunity_rank_preserved]
2022-10-21: reason_codes=[BROKER_PRODUCT_CATEGORY_SUPPORTED, buy_quality_full_allocation_eligible, candidate_eligible, opportunity_rank_preserved]
```

Filter presence:

```text
Explicit low-price filter exists: NO evidence found
Liquidity filter exists: PARTIAL / QUALITY-SCORE FEATURE ONLY
```

Liquidity-like features and Buy Quality execution-feasibility scoring exist in
the codebase, but the audited artifacts do not show a hard low-price exclusion
or a hard liquidity/value-traded floor blocking 93180. Buy Quality reason codes
included `execution_feasibility_available` while 93180 traded at 4-6 JPY.

## 5. Mandatory Date Event Table

| Date | Runtime event | Rank | Expected edge | Quality | Target weight | Position-sizing ref price | Target notional | Fill price | Fill quantity | Fill notional | BUY type |
|---|---:|---:|---:|---|---:|---:|---:|---:|---:|---:|---|
| 2022-08-26 | BUY | 5 | 0.00848027 | FULL_ALLOCATION_ELIGIBLE / PASS | 0.180000 | 6 | 179,692.20 | 6 | 29,900 | 179,400 | BUY_NEW |
| 2022-09-08 | SELL REDUCE | 9 | -0.15391145 | REJECT / REJECTED | 0.137315 | 6 | 134,549.48 | 6 | 7,400 | 44,400 sell | Not BUY |
| 2022-09-09 | SELL REDUCE | 14 | -0.21291214 | REJECT / REJECTED | 0.102065 | 6 | 101,249.50 | 6 | 5,600 | 33,600 sell | Not BUY |
| 2022-09-12 | SELL EXIT | 13 | -0.23949336 | REJECT / REJECTED | 0.000000 | 5 | 0.00 | 6 | 16,900 | 101,400 sell | Not BUY |
| 2022-10-21 | BUY | 3 | 0.08364030 | FULL_ALLOCATION_ELIGIBLE / PASS | 0.153333 | 4 | 165,128.91 | 5 | 41,200 | 206,000 | BUY_NEW / semantic re-entry |

Important correction:

```text
The user-facing concern listed 2022-09-08, 2022-09-09, and 2022-09-12 as BUYs.
The run evidence shows they were SELL REDUCE, SELL REDUCE, and SELL EXIT.
```

## 6. 2022-10-21 Classification

System classification:

```text
2022-10-21 planning_intent: BUY_NEW
2022-10-21 PM action in Position Sizing: NEW
2022-10-21 source_decision_type in fill: BUY
```

Semantic classification:

```text
REENTRY after prior full exit
```

Reason: the first 93180 campaign was fully sold out by 2022-09-12. The
2022-10-21 purchase started a new buy campaign from zero current quantity. It
was not ADD. It was system-classified as BUY_NEW, but semantically it was a
re-entry into the same low-price issue after PM had exited it.

## 7. Opportunity Ranking Context

Top-10 opportunity ranking evidence:

2022-08-26:

```text
1 94320 edge 0.21208916
2 37820 edge 0.11275261 no_buy_reason high_downside_risk_score
3 78780 edge 0.08614545
4 23880 edge 0.01181874
5 93180 edge 0.00848027
```

2022-10-21:

```text
1 94320 edge 0.40629465
2 94340 edge 0.08618400
3 93180 edge 0.08364030
4 39060 edge 0.06128178
5 76920 edge 0.04351775
```

On both BUY dates, 93180 was inside the investable high-rank set and had no
Opportunity no-buy reason.

## 8. Capital and PnL Attribution

Observed 93180 fills through 2022-10-27:

```text
2022-08-26 BUY  29,900 @ 6 = 179,400
2022-09-08 SELL  7,400 @ 6 =  44,400
2022-09-09 SELL  5,600 @ 6 =  33,600
2022-09-12 SELL 16,900 @ 6 = 101,400
2022-10-21 BUY  41,200 @ 5 = 206,000
2022-10-24 SELL 41,200 @ 4 = 164,800
2022-10-25 BUY  34,200 @ 5 = 171,000
2022-10-27 SELL 34,200 @ 5 = 171,000
```

Capital deployed and PnL:

```text
Total BUY capital deployed through 2022-10-27: 556,400 JPY
Realized PnL through 2022-10-27: -41,200 JPY
Current valuation unrealized PnL evidence at 2022-10-27 before SELL execution: -34,200 JPY
Post-2022-10-27 fill residual position: no 93180 position indicated by the same-day EXIT fill
```

Drawdown contribution:

```text
Direct realized loss through 2022-10-27: -41,200 JPY
Worst observed pre-execution unrealized evidence on 2022-10-27: -34,200 JPY
Run-level drawdown contribution: PARTIAL / SYMBOL-LOCAL ONLY from available evidence
```

The symbol-local realized loss is clear. A precise run-level drawdown share
requires the full portfolio equity time series and drawdown attribution model,
which this read-only audit did not recompute.

## 9. Low-Price Bias Assessment

All BUY fills observed in the current run evidence:

```text
BUY count: 17
Total BUY notional: 2,601,420 JPY
Price < 10: 4 BUYs, 704,800 JPY, symbols=[93180]
Price < 20: 4 BUYs, 704,800 JPY, symbols=[93180]
Price < 50: 5 BUYs, 874,900 JPY, symbols=[76470, 93180]
Price < 100: 7 BUYs, 1,192,800 JPY, symbols=[37820, 76470, 76920, 93180]
```

93180 low-price recurrence:

```text
2022-08-26 BUY 29,900 @ 6
2022-10-21 BUY 41,200 @ 5
2022-10-25 BUY 34,200 @ 5
2022-10-28 BUY 37,100 @ 4
```

Judgment:

```text
Low-price bias systemic: YES, as a BUY-side eligibility / scoring / allocation design gap
Quantity-only explanation: NO
Notional explanation: YES
```

The large quantities are an arithmetic effect of the low price. The risk is not
the large share count by itself. The risk is that low-price issues can receive
ordinary target-weight notional allocations and repeated BUY_NEW re-entry.

## 10. Root Cause Classification

Primary root cause:

```text
LOW_PRICE_ELIGIBILITY_AND_ALLOCATION_DESIGN_GAP
```

Contributing causes:

```text
1. No hard low-price / penny-like price floor was evidenced in BUY eligibility.
2. Buy Quality allowed 93180 to pass FULL_ALLOCATION_ELIGIBLE at 4-6 JPY.
3. Opportunity ranked 93180 highly on BUY dates without a low-price distortion penalty.
4. Portfolio Construction assigned normal target weights of 14-18%.
5. Position Sizing converted those weights into large share quantities but not outsized target notional relative to the portfolio policy.
6. PM EXIT did not create a same-symbol re-entry cooldown or low-price risk quarantine.
```

Not root causes:

```text
ADD regression: NO
SELL / REDUCE / EXIT regression: NO evidence
Foreign-stock classification defect: UNKNOWN / NOT PROVEN by PIT listed evidence
Lot/minimum-notional conversion defect: NO
Production implementation defect: NO
```

## 11. Production Defect and Strategy Gap Decision

```text
Production defect: NO
Strategy design gap: YES
```

This is not a production defect because the system behaved according to the
current encoded rules: ProdCat 011 was supported, Opportunity ranked the symbol,
Buy Quality passed it, Portfolio Construction assigned a target weight, and
Position Sizing converted the target notional to quantity. The problem is that
the encoded strategy lacks low-price, low-price-distortion, and post-exit
re-entry controls.

## 12. Recommended Repair

Recommended next repair should be a design task, not an immediate implementation:

```text
Phase29-L13 - Low-Price Eligibility / Re-entry Cooldown / Allocation Guard Design
```

Recommended design scope:

```text
1. Add an explicit BUY-side low-price eligibility policy.
2. Decide price-floor tiers, for example below 50 JPY / below 100 JPY, with PIT evidence.
3. Add liquidity / value-traded floor evidence separate from soft quality scoring.
4. Add low-price opportunity score penalty or fail-closed no-buy reason.
5. Add low-price allocation cap so sub-threshold issues cannot receive normal 14-18% target weights.
6. Add post-PM-EXIT same-symbol cooldown or re-entry review gate.
7. Preserve SELL / REDUCE / EXIT independence.
8. Preserve ADD strength: do not weaken canonical ADD; only constrain BUY_NEW / re-entry eligibility for low-price issues unless separately approved.
```

## 13. Final L12 Required Fields

```text
Primary Judgment:
PHASE29_L12_93180_LOW_PRICE_ELIGIBILITY_AND_REENTRY_DESIGN_GAP_IDENTIFIED_NO_PRODUCTION_DEFECT_READ_ONLY_AUDIT_COMPLETE

93180 security identity:
アジア開発キャピタル / Asia Development Capital Co.Ltd. / ProdCat 011 / Standard / Securities & Commodity Futures

Foreign/security classification:
UNKNOWN from PIT listed evidence

Ordinary domestic common stock equivalent:
YES under current system treatment; issuer country remains UNKNOWN

Universe eligibility:
PASS under current encoded rules

Universe inclusion reason:
BROKER_PRODUCT_CATEGORY_SUPPORTED + candidate_eligible + opportunity_rank_preserved

Low-price filter exists:
NO evidence found

Liquidity filter exists:
PARTIAL / quality-score feature only; no hard audited block observed

2022-08-26:
BUY_NEW, rank 5, price 6, quantity 29,900, fill notional 179,400, target_weight 0.18, expected_edge 0.00848027

2022-09-08:
Not BUY; SELL REDUCE, rank 9, price 6, quantity 7,400 sell, sell notional 44,400, target_weight 0.137315, expected_edge -0.15391145

2022-09-09:
Not BUY; SELL REDUCE, rank 14, price 6, quantity 5,600 sell, sell notional 33,600, target_weight 0.102065, expected_edge -0.21291214

2022-09-12:
Not BUY; SELL EXIT, rank 13, price 6, quantity 16,900 sell, sell notional 101,400, target_weight 0, expected_edge -0.23949336

2022-10-21:
BUY_NEW / semantic re-entry, rank 3, price 5, quantity 41,200, fill notional 206,000, target_weight 0.153333, expected_edge 0.08364030

2022-10-21 BUY classification:
System BUY_NEW; semantic re-entry after full 2022-09-12 exit; not ADD

93180 total capital deployed:
556,400 JPY through 2022-10-27

93180 realized PnL:
-41,200 JPY through 2022-10-27

93180 unrealized PnL at 2022-10-27:
-34,200 JPY in pre-execution current valuation evidence; post-fill residual position not indicated

Contribution to run drawdown:
Symbol-local realized contribution -41,200 JPY; precise run-level drawdown share not recomputed

Low-price bias systemic:
YES

Production defect:
NO

Strategy design gap:
YES

Recommended repair:
Phase29-L13 low-price eligibility, hard liquidity/value-traded floor, allocation cap, opportunity penalty, and post-EXIT re-entry cooldown design

Runtime mutated:
NO

Historical executed:
NO

Recommended next task:
Phase29-L13 - Low-Price Eligibility / Re-entry Cooldown / Allocation Guard Design
```
