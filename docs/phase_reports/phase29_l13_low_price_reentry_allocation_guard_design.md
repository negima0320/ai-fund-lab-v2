# Phase29-L13 - Low-Price Eligibility / Re-entry Cooldown / Allocation Guard Design

## 0. Task ID

Phase29-L13

## 1. Primary Judgment

```text
PHASE29_L13_LOW_PRICE_REENTRY_ALLOCATION_GUARD_DESIGN_COMPLETE_THRESHOLD_CALIBRATION_REQUIRED_BEFORE_IMPLEMENTATION
```

Recommended design is Option B:

```text
Price + Liquidity Conditional Eligibility + Portfolio Construction Allocation Guard + REENTRY Recovery Hurdle
```

This is a Production / Demo / Historical common Strategy design. It is not a
Historical-only patch and not a 93180-specific exclusion. Threshold values must
be calibrated in a later task against multiple periods and symbols before
implementation.

## 2. Scope and Non-Mutation Statement

This task is design-only and read-only.

```text
Production code changed: NO
Strategy implementation changed: NO
Config changed: NO
Existing schema changed: NO
Runtime state mutated: NO
Pending mutated: NO
Ledger mutated: NO
Accepted Generation mutated: NO
Historical executed: NO
Fresh-run executed: NO
Resume executed: NO
```

Deliverables:

```text
docs/phase_reports/phase29_l13_low_price_reentry_allocation_guard_design.md
reports/phase29_l13_low_price_reentry_allocation_guard_design/
docs/01_requirements/phase_roadmap.md
```

## 3. Confirmed L12 Root Cause

Root cause confirmed:

```text
LOW_PRICE_ELIGIBILITY_AND_ALLOCATION_DESIGN_GAP
```

93180 passed the current encoded BUY path because:

```text
Universe / listed eligibility: PASS as ProdCat 011 supported equity
Opportunity: PASS / BUY_ELIGIBLE when expected_edge_score was positive
Buy Quality: FULL_ALLOCATION_ELIGIBLE on BUY dates
Portfolio Construction: normal target_weight 0.153333 to 0.18
Position Sizing: correctly materialized target notional into low-price quantity
Planning: emitted BUY_NEW, not REENTRY
Submit: not the Strategy selection authority
```

Important non-root-cause:

```text
ADD regression: NO
SELL / REDUCE / EXIT regression: NO
Quantity cap issue: NO
```

Large share quantity is arithmetic from 4-6 JPY price. The risk is allowing a
low-price issue to receive ordinary portfolio notional allocation and repeated
BUY_NEW re-entry.

## 4. Current Authority Findings

### 4.1 Universe / Listed Authority

93180 had PIT listed evidence:

```text
Code 93180
CoName アジア開発キャピタル
CoNameEn Asia Development Capital Co.Ltd.
MktNm スタンダード
ProdCat 011
S33Nm 証券･商品先物取引業
issuer country / foreign flag: not present
```

Current system treatment of ProdCat 011 is supported equity. There is no direct
listed-issues evidence proving foreign classification.

### 4.2 Opportunity Authority

Current Opportunity BUY eligibility blocks missing/non-finite expected edge,
non-positive expected edge, feature-date mismatch, and explicit no-buy reason.
It does not include low-price, traded-value, price/tick distortion, or re-entry
semantic authority.

93180 was:

```text
2022-08-26: rank 5, expected_edge_score 0.00848027
2022-10-21: rank 3, expected_edge_score 0.08364030
```

Opportunity model distortion is plausible but not proven by L13. Current
features include percentage returns and volatility; for a 4 JPY stock, one tick
to 5 JPY is +25%, so low absolute price can amplify percentage-based features.
However, the audited 93180 technical rows showed 5d and 20d price momentum of
0.0 on the two BUY dates. Therefore L13 must not declare the model defective
from 93180 alone.

### 4.3 Buy Quality Authority

Buy Quality uses weighted components:

```text
relative_opportunity_quality
market_context_quality_modifier
signal_reliability
execution_feasibility
portfolio_fit
```

The execution feasibility component is soft. If price/volatility evidence is
missing, it returns a non-critical conservative reduction. If present, it uses a
liquidity-like score and downside risk, but the audited path did not hard-block
93180 despite 4-6 JPY price.

### 4.4 J-Quants Liquidity / Traded Value Availability

PIT-safe raw J-Quants equities bars include fields usable for a liquidity
authority:

```text
Vo: volume
Va: traded value
AdjFactor: adjustment factor
AdjC: adjusted close
AdjVo: adjusted volume
MktCap: market capitalization
```

93180 evidence:

```text
2022-08-26: C 6, Vo 8,855,600, Va 52,999,300, AdjFactor 1.0
2022-10-21: C 4, Vo 14,610,000, Va 63,424,100, AdjFactor 1.0
```

Current candidate features include average volume, volume momentum, returns,
volatility, and trend, but not hard rolling traded-value or position-notional /
traded-value capacity checks.

### 4.5 Portfolio Construction / Position Sizing Authority

Portfolio Construction owns target_weight / target_notional authority. Recent
Phase29 work explicitly keeps economic allocation in PC and leaves Position
Sizing to materialize accepted target weights into quantities. Lot-aware final
reallocation also records that PS preflight does not decide economic allocation.

Therefore, low-price allocation control should be applied in Portfolio
Construction target weight authority, not as a final quantity-only cap in
Position Sizing.

### 4.6 ADD and BUY_NEW Separation

Current PC separates:

```text
current_position + PM ADD -> ADD_INCREMENT / BUY_ADD
no current_position + ADD_CANDIDATE -> BUY_NEW
```

Canonical ADD has its own evidence contract:

```text
expected edge improvement
incremental investment value
opportunity cost
campaign continuation
no-loss averaging
concentration
capital availability
execution feasibility
```

L13 must not weaken that contract. Low-price control should primarily apply to
BUY_NEW and semantic REENTRY. Existing-position ADD may receive only a
risk-budget multiplier when the added exposure increases a low-price position,
and only if the ADD evidence still passes; it must not be blanket-blocked.

### 4.7 REENTRY Authority Gap

PM configuration already contains cooldown and re-entry concepts for existing
position management, including `post_exit_reentry_cooldown_business_days` and
recovery rules. But the 2022-10-21 93180 event had current quantity 0 and was
planned as BUY_NEW. The prior EXIT semantic state was not used to distinguish
REENTRY from ordinary BUY_NEW.

Past EXIT semantic state can be a valid Strategy input only if it is derived
from already-confirmed runtime state as of the decision date. It must not use
realized PnL, campaign PnL, backtest result, future price, future opportunity,
or selected/bought outcome.

## 5. Design Alternatives

| Option | Summary | Performance upside | Downside protection | False exclusion risk | Split / reverse split sensitivity | PIT safety | Complexity | Regression risk | ADD impact | BUY_NEW impact | REENTRY impact | Cash utilization | Opportunity Cost compatibility |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| A | Hard Low-Price Exclusion | Low | High for low-price tail risk | High | High | Medium if PIT price only | Low | Medium | Should be none if scoped, but easy to overblock | Strong restriction | Strong restriction | Can strand cash | Weak unless reallocation is added |
| B | Price + Liquidity Conditional Eligibility + Allocation Guard | High | High | Medium/Low after calibration | Medium/Low with AdjFactor and CA guards | High | Medium/High | Medium | Preserved; optional incremental risk multiplier only | Conditional | Cooldown + recovery hurdle | Capital can recycle to ADD / better BUY_NEW | Strong |
| C | Liquidity / Execution Risk Only | Medium/High | Medium | Low | Low | High | Medium | Low/Medium | Preserved | Conditional by liquidity only | Weak unless separate re-entry rule added | Good | Strong |
| D | Allocation Guard Only | High | Medium | Low | Medium | High | Medium | Low/Medium | Preserved | Still eligible but capped | Still eligible but capped | Good | Strong |

Decision:

```text
Option B is recommended.
Option A is rejected as too blunt and too sensitive to nominal price / corporate actions.
Option C is insufficient because 93180 had large Va on BUY dates and would likely pass pure liquidity.
Option D is useful but incomplete because repeated re-entry and low-price edge distortion would remain unaddressed.
```

## 6. Recommended Production Strategy Contract

### 6.1 BUY_NEW Eligibility

BUY_NEW remains possible.

Recommended BUY_NEW low-price contract:

```text
If price is normal tier:
  use existing Opportunity + Buy Quality + PC flow.

If price enters low-price watch tier:
  require PIT price evidence, listed evidence, corporate action status, and liquidity capacity evidence.
  if missing critical evidence: symbol-level BUY_INELIGIBLE / REVIEW_REQUIRED, not whole-run halt.
  if liquidity and execution capacity pass: BUY_NEW may proceed but target allocation is capped by PC.
  if liquidity or CA evidence fails: BUY_NEW is ineligible for that symbol.

If price enters extreme low-price tier:
  require stronger eligibility and allocation cap; implementation thresholds require calibration.
```

Absolute price is not the sole authority. It is a risk signal that activates
additional liquidity, execution, and allocation requirements.

### 6.2 REENTRY Eligibility

Semantic REENTRY is required:

```text
REENTRY = current_quantity == 0 and prior same-symbol EXIT is known in past runtime state before the decision date.
```

REENTRY does not need a new Runtime order side/type in L14. It can be a Strategy
semantic classification attached to a BUY_NEW plan and propagated as evidence.

Recommended REENTRY contract:

```text
REENTRY after EXIT must pass BUY_NEW eligibility plus a recovery hurdle.
Low-price REENTRY must pass BUY_NEW low-price guard plus a stronger recovery hurdle.
```

Recovery hurdle should consider PIT-safe evidence:

```text
expected edge
opportunity rank
quality score/action
momentum recovery
technical recovery
liquidity/traded-value capacity
corporate action status
```

It must not use realized PnL, campaign PnL, future outcome, backtest result, or
future opportunity.

### 6.3 Re-entry Cooldown

Recommended:

```text
Re-entry cooldown recommended: YES, but as hybrid minimum cooldown + recovery hurdle.
```

Do not use cooldown alone. A time-only cooldown would have allowed 2022-10-21
if the threshold were 10 business days, because 2022-09-12 to 2022-10-21 is far
longer than the existing PM post-exit cooldown setting. A hybrid rule would
still require recovery and low-price liquidity/allocation evidence.

93180 example:

```text
2022-09-12 EXIT
2022-10-21 semantic REENTRY

Time-only cooldown: likely PASS for a 10BD threshold
Recovery hurdle: REVIEW_REQUIRED / capped / possibly ineligible depending calibrated expected-edge, quality, momentum, and liquidity thresholds
Hybrid: not automatically blocked by time, but must clear recovery and low-price allocation controls
```

### 6.4 ADD Eligibility

Canonical ADD is preserved.

```text
ADD blanket ban for low-price symbols: FORBIDDEN
ADD semantics changed: NO
```

If an existing low-price position seeks additional capital, the design may add
a low-price incremental risk-budget multiplier in PC, but only after the
existing ADD contract passes. That multiplier limits additional notional; it
does not suppress SELL/REDUCE/EXIT and does not convert ADD into a low-price
blanket rejection.

### 6.5 Liquidity Authority

Liquidity authority is required.

Minimum evidence fields:

```text
close / adjusted close
daily traded value Va
rolling median traded value
volume / adjusted volume
position_notional / traded_value
estimated liquidation capacity
expected liquidation days
volatility
price/tick relationship
AdjFactor / Corporate Action status
```

Recommended authority location:

```text
Market Refresh / feature authority produces PIT liquidity capacity evidence.
Buy Eligibility / Buy Quality consumes symbol-level eligibility.
Portfolio Construction consumes allocation cap and capacity multiplier.
```

### 6.6 Target-Weight / Allocation Guard

Allocation guard is required and should be owned by Portfolio Construction.

Recommended cap form:

```text
low_price_adjusted_target_weight_cap =
  min(
    normal_strategy_single_name_cap,
    liquidity_capacity_cap,
    price_tier_cap,
    volatility / tick-sensitivity risk multiplier cap,
    opportunity_confidence_adjusted_cap
  )
```

This cap applies before Position Sizing. PS should continue to convert accepted
target weights into executable lots/quantities and fail closed when conversion
is infeasible.

### 6.7 Opportunity Interaction

Opportunity model distortion is not proven in L13.

Recommended interaction:

```text
Do not retrain or change the Opportunity model from L13 alone.
Add low-price / liquidity risk evidence as downstream Strategy authority first.
Record model-distortion diagnostics for later calibration.
If multi-symbol calibration proves systematic low-price edge inflation, create a later model/feature repair task.
```

### 6.8 Capital Reallocation

Low-price exclusion or cap must not simply increase cash.

Released capital priority:

```text
1. Strong existing ADD that passes canonical ADD and opportunity-cost evidence
2. Higher-quality BUY_NEW that passes BUY_NEW eligibility
3. Cash only when no opportunity passes
```

PC should treat trimmed low-price allocation as deployable capital in the same
incremental budget / lot-aware reallocation queue, preserving Opportunity Cost
and Dynamic Capital semantics.

### 6.9 SELL / REDUCE / EXIT Independence

Risk-reducing actions must bypass BUY low-price guards.

```text
SELL independence: preserved
REDUCE independence: preserved
EXIT independence: preserved
```

Low-price, liquidity, allocation cap, and re-entry cooldown checks must not
block SELL / REDUCE / EXIT. They may be recorded as context, but risk-reducing
orders remain governed by PM, Position Sizing SELL quantity contract, Planning,
Pending, Submit, and Corporate Action safety authorities.

### 6.10 Missing Evidence Behavior

Preferred behavior is symbol-level fail closed.

```text
Missing price: symbol BUY_INELIGIBLE / REVIEW_REQUIRED
Missing liquidity/traded value for low-price watch tier: symbol BUY_INELIGIBLE / REVIEW_REQUIRED
Missing PIT listed evidence: symbol BUY_INELIGIBLE / REVIEW_REQUIRED for BUY_NEW / REENTRY
Missing previous EXIT semantic authority: treat as ordinary BUY_NEW, but record REENTRY_STATUS_UNKNOWN; do not infer from PnL
Unresolved Corporate Action: existing Production / Demo fail-closed preserved
```

The whole run should not halt solely because one BUY candidate lacks low-price
eligibility evidence, as long as other symbols and SELL/REDUCE/EXIT can proceed
safely. Production must not fail open for that symbol.

### 6.11 PIT / Temporal / Corporate Action Contract

All low-price and liquidity evidence must be PIT-safe and dated on or before
the business date. Use J-Quants raw/normalized bars and listed evidence already
materialized for the historical/as-of view.

Corporate Action interaction:

```text
Use AdjFactor / adjusted price / adjusted volume for distortion diagnostics.
Do not use L9-L11 Historical-only Corporate Action quarantine semantics as Strategy eligibility.
If Corporate Action is unresolved, preserve Production / Demo fail-closed behavior.
Do not let nominal split/reverse-split price alone create permanent exclusion.
```

## 7. Architecture Ownership

| Layer | L13 ownership |
|---|---|
| Universe | Product/listed support remains here. Do not encode final low-price allocation authority here. |
| Candidate | May expose PIT low-price/liquidity feature evidence. |
| Opportunity | Keeps ranking authority; may later receive model distortion repair only after calibration. |
| Buy Eligibility | Owns BUY_NEW/REENTRY low-price conditional eligibility and no-buy reason. |
| Buy Quality | Consumes liquidity/execution risk as quality evidence; may emit REDUCED_ALLOCATION_ONLY or REVIEW_REQUIRED. |
| Portfolio Construction | Owns low-price target-weight cap, allocation multiplier, and capital reallocation. |
| Position Sizing | Materializes PC target weights to lot/quantity; no final economic low-price cap. |
| Portfolio Management | Owns existing-position HOLD/ADD/REDUCE/EXIT; provides prior EXIT state only as past runtime semantic evidence where available. |
| Planning | Carries BUY_NEW plus semantic REENTRY evidence; does not invent low-price authority. |
| Submit Guard | Final safety guard only; not Strategy low-price selection authority. |

## 8. Threshold Policy

Threshold calibration required before implementation:

```text
YES
```

L13 does not approve hard numerical thresholds. L14 should calibrate:

```text
low-price tiers: <10, <20, <50, <100 as candidates, not pre-approved cutoffs
minimum daily / rolling median traded value
maximum target_notional / traded_value ratio
estimated liquidation days
low-price allocation cap
extreme-low-price cap
re-entry cooldown days
recovery expected-edge / rank / quality hurdle
tick-sensitivity threshold
```

Calibration must use multiple symbols and periods. It must not optimize solely
to block 93180.

## 9. Regression Preservation Checklist

```text
Canonical ADD weakened: NO
BUY_NEW still possible: YES
Strong momentum BUY preserved: YES
Strong existing ADD preserved: YES
SELL preserved: YES
REDUCE preserved: YES
EXIT preserved: YES
Opportunity Cost preserved: YES
Dynamic Capital preserved: YES
Cash Exposure Authority preserved: YES
Production fail-closed preserved: YES
Historical-only Strategy introduced: NO
Future leakage introduced: NO
PnL used as Strategy input: NO
Backtest result used as Strategy input: NO
```

## 10. Recommended Next Task

```text
Phase29-L14 - Low-Price Liquidity / Re-entry Threshold Calibration and Implementation Readiness
```

L14 should be calibration/readiness first, then implementation only if the
calibration produces generalizable thresholds and regression guardrails.

Required L14 outputs:

```text
1. Multi-symbol low-price tier distribution.
2. Historical BUY candidate impact by tier.
3. Traded-value / allocation-cap calibration.
4. REENTRY cooldown and recovery-hurdle calibration.
5. ADD non-regression proof plan.
6. SELL / REDUCE / EXIT independence regression plan.
7. Implementation-ready contract values or explicit no-go.
```

## 11. Final Required Fields

```text
Primary Judgment:
PHASE29_L13_LOW_PRICE_REENTRY_ALLOCATION_GUARD_DESIGN_COMPLETE_THRESHOLD_CALIBRATION_REQUIRED_BEFORE_IMPLEMENTATION

Root Cause confirmed:
YES - LOW_PRICE_ELIGIBILITY_AND_ALLOCATION_DESIGN_GAP

Low-price hard exclusion recommended:
NO

Liquidity authority required:
YES

Opportunity model distortion confirmed:
NOT_PROVEN

Allocation guard required:
YES

REENTRY semantic required:
YES

Re-entry cooldown recommended:
YES, as hybrid cooldown + recovery hurdle

Recovery hurdle recommended:
YES

ADD semantics changed:
NO

BUY_NEW semantics change required:
YES

SELL semantics changed:
NO

REDUCE semantics changed:
NO

EXIT semantics changed:
NO

Opportunity Cost preserved:
YES

Capital reallocation path identified:
YES

Production fail-closed preserved:
YES

Historical-only Strategy introduced:
NO

Future leakage introduced:
NO

PnL / Backtest result used as Strategy input:
NO

Production code changed:
NO

Config changed:
NO

Existing schema changed:
NO

Runtime mutated:
NO

Pending mutated:
NO

Ledger mutated:
NO

Historical executed:
NO

Fresh-run required now:
NO

Recommended next task:
Phase29-L14 - Low-Price Liquidity / Re-entry Threshold Calibration and Implementation Readiness

Recommended implementation layers:
Buy Eligibility / Buy Quality evidence, Portfolio Construction target-weight authority, Planning semantic evidence propagation, read-only market feature authority

Threshold calibration required before implementation:
YES
```
