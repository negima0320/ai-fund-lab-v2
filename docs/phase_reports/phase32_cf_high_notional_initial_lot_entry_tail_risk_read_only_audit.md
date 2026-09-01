# Phase32-CF — High-Notional Initial Lot Entry Tail-Risk READ-ONLY Audit

Target run:

`runtime-test-historical-extended-smoke-20260831T234344371102Z`

Evidence snapshot:

- run status at inspection: `RUNNING`
- source commit recorded in run commands: `cf0a00b0271d170094aa0ce2bfbedc203c364406`
- latest completed business date used: `2023-06-15`
- completed business days used: `173`
- no mutating Runtime command was executed

This is a READ-ONLY characterization. No code, config, sizing rule, cap, Strategy parameter, Runtime state, Pending, Ledger, resume, recover, replay, or fresh-run action was changed or executed.

## Preserved CE Conclusions

This audit preserves Phase32-CE:

- severe losses are disproportionately single-name dominated
- unpredictable loss concentration amplification is material
- organic Winner concentration is material
- high-notional initial lot entry is also material
- ADD-driven concentration is not primary
- concentration has a material two-sided upside/downside tradeoff
- no Production cap change is currently justified

CF narrows the question to initial entry only. It does not reopen 59350-style organic Winner retention, HOLD/REDUCE/EXIT, BQ, ADD, or cap values.

## Current Initial Entry Sizing Contract

`CURRENT_INITIAL_ENTRY_SIZING_CONTRACT`:

```text
BUY_NEW / REENTRY
-> Portfolio Construction target/member authority
-> Position Sizing lot preflight with reference price, trading unit, target weight, current weight, cash and cap context
-> phase29_l19_lot_resolution
-> PC final discrete executable quantity authority
-> Runtime Planning / Pending / Submit consume the PC/PS quantity
-> execution/fill records actual notional
```

Current caps and sizing boundaries:

- Strategy single-name soft cap: `0.18`
- Safety hard single-name cap: `0.25`
- standard Japan equity trading unit observed in the relevant high-notional starters: `100` shares
- Strategy soft cap is an allocation / desired-target boundary, not the same as the Safety terminal boundary
- Safety hard cap is the fail-closed boundary consumed by PC/PS/Runtime feasibility checks
- one-lot overshoot may be accepted only when PC/PS materialize explicit discrete-lot authority and Safety hard-cap preservation is proven
- if the minimum executable lot exceeds Safety hard cap, the path fail-closes as `minimum_lot_exceeds_safety_hard_cap`
- if the lot/cap/cash authority is malformed or unresolved, the path does not silently resize downstream

Evidence:

- `docs/02_architecture/portfolio_construction_and_position_sizing_contract.md` separates Strategy soft cap and Safety hard cap.
- `configs/strategy/portfolio_policy.json#single_name_weight_cap = 0.18`.
- `configs/safety/portfolio_limits.json#concentration.maximum_position_weight = 0.25`.
- `src/ai_fund_lab_v2/strategy/position_sizing.py` emits `phase29_l19_lot_resolution` with `strategy_target_cap`, `safety_hard_cap`, `one_lot_notional`, `one_lot_weight`, `post_trade_weight`, and `safety_hard_cap_preserved`.
- `src/ai_fund_lab_v2/strategy/portfolio_construction.py` blocks `MINIMUM_EXECUTABLE_LOT_EXCEEDS_SAFETY_HARD_MAX` / `safety_hard_cap_preserved is False`.

## Initial Entry Population

Campaign initial entries were reconstructed from the first BUY fill per campaign, excluding subsequent ADD fills and later organic appreciation.

| Metric | Value |
|---|---:|
| Initial entry count | 266 |
| BUY_NEW initial entries | 266 |
| REENTRY initial entries observed | 0 |
| Median initial fill notional / pre-entry equity | 3.98% |
| P75 | 7.95% |
| P90 | 14.43% |
| P95 | 16.79% |
| P99 | 19.42% |
| Max | 20.13% |

Minimum-lot reference-weight distribution:

| Metric | Value |
|---|---:|
| Median minimum-lot / pre-entry equity | 3.79% |
| P90 | 14.55% |
| P95 | 17.14% |
| P99 | 21.48% |

Cap-bucket counts:

| Bucket | Count |
|---|---:|
| Initial fill below 18% soft cap | 259 |
| Initial fill above 18% and below 25% hard cap | 7 |
| Initial fill above 25% hard cap | 0 |
| Minimum lot above 18% soft cap | 11 |
| Minimum lot above 25% hard cap | 0 |
| Same-day EOD initial position above 25% hard cap | 0 |

## High-Notional Starter Population

To avoid fitting a threshold from outcomes, this audit uses the existing cap landmarks:

High-notional starter means at least one of:

- initial fill notional / pre-entry equity `>= 18%`
- minimum executable lot / pre-entry equity `>= 18%`
- same-day EOD position / equity `>= 18%`

High-notional starter count: `11`.

Total initial cash consumed by these 11 entries: `2,784,750`.

Average / median high-notional starter fill:

- average notional: `253,159`
- median notional: `267,700`

Representative high-notional starters:

| Date | Symbol | Campaign | Initial weight | Min-lot weight | EOD weight | PS target weight | Initial notional | Result class |
|---|---|---|---:|---:|---:|---:|---:|---|
| 2022-10-04 | 70640 | `pc-f0a25f6542b3fe75-70640-0001` | 20.13% | 22.13% | 21.35% | 15.33% | 203,750 | winner |
| 2023-03-14 | 77940 | `pc-dd51cd175efb7e18-77940-0001` | 20.07% | 20.32% | 20.62% | 11.86% | 252,000 | winner |
| 2023-04-11 | 51890 | `pc-44550ee856c9a100-51890-0001` | 19.62% | 18.54% | 20.20% | 13.00% | 346,500 | costly |
| 2023-03-30 | 68980 | `pc-73d110b65c262cdd-68980-0001` | 19.32% | 22.60% | 21.22% | 15.10% | 280,300 | winner |
| 2022-10-03 | 93600 | `pc-be524356b874aa8b-93600-0001` | 19.19% | 19.11% | 18.88% | 13.20% | 191,900 | costly |
| 2022-12-06 | 79010 | `pc-72afa6bb55cb0134-79010-0001` | 18.48% | 21.13% | 20.91% | 14.69% | 209,000 | winner/mixed |
| 2023-04-24 | 64080 | `pc-0ead1347c207ec9c-64080-0001` | 18.07% | 19.30% | 18.99% | 10.98% | 278,000 | winner |
| 2023-04-10 | 67310 | `pc-27d94d3180070a27-67310-0001` | 17.83% | 23.77% | 22.65% | 23.77% | 300,000 | mixed/gap |
| 2022-10-14 | 92540 | `pc-91b32ced93dbc97f-92540-0001` | 17.56% | 18.17% | 17.98% | 18.17% | 181,600 | costly/flat |
| 2023-04-03 | 52470 | `pc-85bf06340b720569-52470-0001` | 17.07% | 18.07% | 17.18% | 10.98% | 274,000 | costly |
| 2023-05-22 | 88900 | `pc-8f9ed2cc025115c9-88900-0001` | 16.82% | 18.15% | 17.83% | 10.09% | 267,700 | winner |

Interpretation:

The high-notional starter group is not identical to "bad starter". It contains strong positive controls (`70640`, `68980`, `64080`, `88900`) and costly controls (`51890`, `52470`, `93600`). This makes a blunt Production rejection unsafe.

## 67310 Mandatory Case

Decision date: `2023-04-10`.

Entry authority:

- source decision type: `BUY_NEW`
- campaign: `pc-27d94d3180070a27-67310-0001`
- quantity: `100`
- execution price: `3,000`
- fill notional: `300,000`
- pre-entry equity: `1,682,840`
- initial fill weight: `17.83%`
- same-day EOD market value: `400,000`
- same-day EOD equity: `1,766,350`
- same-day EOD weight: `22.65%`

Position Sizing / lot authority:

- PS target weight: `23.7693%`
- PS target notional: `399,999.29`
- reference price: `4,000`
- trading unit: `100`
- minimum lot notional at reference price: `400,000`
- minimum lot weight: `23.7693%`
- Strategy target cap: `18%`
- Safety hard cap: `25%`
- recorded reason codes include `LOT_AWARE_STRATEGY_CAP_OVERSHOOT_WITHIN_SAFETY_HARD_CAP` and `ONE_LOT_DISCRETE_QUANTITY_AUTHORITY_CONSUMED`

Smaller executable position:

`67310_SMALLER_EXECUTABLE_POSITION_POSSIBLE = NO`

The practical entry choice under the 100-share trading unit was binary:

```text
0 shares or 100 shares
```

`67310_BINARY_0_OR_100_SHARES = YES`

Contract judgment:

`67310_ENTRY_CONTRACT_VALID = YES_UNDER_CURRENT_PC_PS_LOT_AUTHORITY`

The accepted entry did not breach the 25% hard cap at fill, minimum-lot reference, or same-day EOD. It did exceed the 18% Strategy soft-cap boundary in PS reference terms, but current artifacts explicitly recorded one-lot soft-cap overshoot inside Safety hard cap.

CE's later classification is preserved:

`67310` later produced a `NEW_INFORMATION_OR_GAP_LOSS`. The later loss is not reinterpreted here as an entry-quality failure by hindsight.

## Minimum-Lot Constraint

The high-notional starter evidence supports a binary admission problem:

- all 11 high-notional starters are 100-share entries
- 11 entries had minimum-lot reference weight above 18%
- 0 entries had minimum-lot reference weight above 25%
- several entries had PS target weights materially below actual/min-lot weight, e.g. `70640` target `15.33%` vs minimum-lot `22.13%`, `77940` target `11.86%` vs `20.32%`, `64080` target `10.98%` vs `19.30%`, `88900` target `10.09%` vs `18.15%`

Therefore discrete lot granularity sometimes forced accepted risk materially above the Strategy-sized allocation, while still inside the Safety hard-cap boundary.

This is a binary admission issue, not an ordinary continuous sizing issue.

## Soft / Hard Cap Semantics

### 18% Strategy Soft Cap

Resolved meaning:

- desired Strategy / Portfolio Construction allocation boundary
- routine concentration reference
- not a continuous forced-trim rule
- not sufficient by itself to cross broker/submit boundary when lot/cap authority is missing
- may be exceeded only when explicit PC/PS discrete-lot authority proves Safety hard-cap preservation

### 25% Safety Hard Cap

Resolved meaning:

- fail-closed safety boundary for new executable quantity / post-trade lot authority
- used by PC/PS/Runtime submit feasibility as a validation boundary
- not proven by current SoT to be an automatic continuous EOD forced-rebalance trigger
- if one lot exceeds Safety hard cap or `safety_hard_cap_preserved` is false, the item must be blocked/reviewed

## Hard-Cap And Soft-Cap Audit

Initial hard-cap breach audit:

- fill notional / pre-entry equity `>25%`: `0`
- minimum-lot reference notional / pre-entry equity `>25%`: `0`
- same-day EOD position / equity `>25%`: `0`

`INITIAL_ENTRY_HARD_CAP_CORRECTNESS_DEFECT_FOUND = NO`

Initial soft-cap overshoot audit:

- actual fill weight `>18%`: `7`
- minimum-lot reference weight `>18%`: `11`
- same-day EOD high-notional starter set: included because several entries moved around the 18% boundary after fill

`SOFT_CAP_OVERSHOOT_ROOT_CAUSE = DISCRETE_100_SHARE_LOT_REFERENCE_NOTIONAL_PLUS_EXPLICIT_PC_PS_ONE_LOT_AUTHORITY_WITHIN_SAFETY_HARD_CAP; SOME CASES ALSO HAVE SAME_DAY_PRICE/FILL_REFERENCE_DIFFERENCE`

This is not a silent downstream resize. The overshoot was visible in PS/PC reason codes.

## Starter Tail Outcomes

Fixed descriptive horizons after entry, after freezing entry evidence:

| Group | Horizon | N | Median contribution | Mean contribution | Loss rate |
|---|---:|---:|---:|---:|---:|
| High-notional starter | same-day EOD | 11 | +19,000 | +22,177 | 18.2% |
| High-notional starter | +1BD | 11 | +9,300 | +8,316 | 9.1% |
| High-notional starter | +3BD | 11 | +8,000 | +5,577 | 18.2% |
| High-notional starter | +5BD | 11 | +7,670 | +2,911 | 36.4% |
| High-notional starter | +10BD | 11 | +8,000 | +4,997 | 36.4% |
| Ordinary starter | same-day EOD | 255 | +300 | +1,508 | 31.0% |
| Ordinary starter | +1BD | 253 | +400 | +1,770 | 37.9% |
| Ordinary starter | +3BD | 251 | +300 | +2,384 | 41.8% |
| Ordinary starter | +5BD | 249 | +40 | +2,495 | 44.6% |
| Ordinary starter | +10BD | 241 | 0 | +2,991 | 47.7% |

High-notional starters were not broadly worse in median short-horizon terms through this snapshot. The risk is tail magnitude: when a high-notional starter fails, the single-name yen loss can be large before the campaign has earned Winner status.

## Large-Loss Tail Contribution

Large loss events used CE-style criteria:

- daily return `<= -2%`, or
- daily PnL `<= -50,000`

Through `2023-06-15`, large-loss absolute PnL total was approximately `621,790`.

High-notional starter negative contribution on those days:

- total: `-185,380`
- share of large-loss absolute magnitude: `29.8%`

Key high-notional starter contributions:

- `2022-10-11`: high-notional starters contributed about `-15,550`, including `70640`
- `2022-12-07`: `79010` contributed about `-21,330`
- `2023-04-11`: `67310` and `51890` together contributed about `-119,000`
- `2023-04-12`: high-notional starter contribution about `-29,500`, mainly `51890`

`HIGH_NOTIONAL_STARTER_TAIL_CONTRIBUTION = MATERIAL_BUT_NOT_DOMINANT_OVERALL`

It is material enough to deserve a SHADOW admission/risk study, but it does not explain the whole severe tail because 59350-style organic Winner concentration remains separate and important.

## Upside Contribution

High-notional starter aggregate contribution through the snapshot:

- positive contribution: approximately `+380,530`
- negative contribution: approximately `-330,260`
- outcome classes: 6 winner, 4 costly, 1 flat/open/mixed

Successful high-notional controls:

| Symbol | Entry date | Initial weight | Initial notional | PS target weight | Net contribution | Notes |
|---|---|---:|---:|---:|---:|---|
| 70640 | 2022-10-04 | 20.13% | 203,750 | 15.33% | +18,000 | high-ratio early winner |
| 79010 | 2022-12-06 | 18.48% | 209,000 | 14.69% | +10,670 | mixed but net positive |
| 68980 | 2023-03-30 | 19.32% | 280,300 | 15.10% | +34,700 | strong positive control |
| 64080 | 2023-04-24 | 18.07% | 278,000 | 10.98% | +20,700 | positive high-notional starter |
| 88900 | 2023-05-22 | 16.82% | 267,700 | 10.09% | +33,300 | positive control selected below actual-fill soft cap but above minimum-lot soft cap |

`HIGH_NOTIONAL_STARTER_UPSIDE_CONTRIBUTION = MATERIAL`

A blunt initial notional cap would have removed real upside and would not be acceptable as a direct Production conclusion from CF.

## Candidate Quality And Admission Semantics

Current architecture has:

- generic opportunity / Buy Quality / PC / PS / cash competition
- lot feasibility
- Strategy soft-cap and Safety hard-cap checks
- low-price and minimum meaningful notional diagnostics
- no explicit high-notional starter admission semantic that demands stronger evidence solely because one minimum lot consumes an unusually large fraction of equity

Therefore:

`CURRENT_ARCHITECTURE_HAS_EXPLICIT_HIGH_NOTIONAL_ADMISSION_SEMANTIC = NO_BEYOND_GENERIC_LOT_CAP_SAFETY_AUTHORITY`

`HIGH_NOTIONAL_STARTER_REQUIRES_STRONGER_CURRENT_AUTHORITY = NO_CURRENT_CONTRACT_DOES_NOT_REQUIRE_A_SEPARATE_STRONGER_HIGH_NOTIONAL_ADMISSION_PROOF`

Capital competition is material because 11 high-notional starters consumed `2,784,750` of initial BUY capital in large binary chunks, but final PC evidence often chose Cash over other candidates as well. This audit does not claim every displaced candidate was better.

`CAPITAL_COMPETITION_MATERIAL = YES_AS_CAPACITY_AND_DIVERSIFICATION_PRESSURE; NOT_PROVEN_AS_ALTERNATIVE_WINNER_SELECTION`

## 67310 vs Successful High-Notional Controls

Decision-time comparison:

- `67310`: `CORRECTION`, PS target/min-lot `23.77%`, same-day EOD +100,000 then next-day gap loss, entry admission reason `entry_continuation_with_caution`
- `68980`: `RANGE`, initial `19.32%`, min-lot `22.60%`, net positive
- `70640`: `RANGE`, initial `20.13%`, min-lot `22.13%`, net positive
- `64080`: `RECOVERY`, initial `18.07%`, min-lot `19.30%`, net positive
- `88900`: `BULL`, initial `16.82%`, min-lot `18.15%`, net positive

There is weak contextual separation: `67310` entered during `CORRECTION` with an unusually high PS reference/min-lot weight. But successful high-notional starters also had soft-cap overshoot or high minimum-lot pressure, and the current evidence does not prove a deterministic PIT discriminator that would reject `67310` while retaining the controls.

`67310_VS_SUCCESSFUL_HIGH_NOTIONAL_STARTER_PIT_SEPARABILITY = WEAKLY_SEPARABLE`

## Organic Winner Retention Out Of Scope

`ORGANIC_WINNER_RETENTION_OUT_OF_SCOPE_PRESERVED = YES`

CF applies to:

```text
initial BUY_NEW / REENTRY binary admission
```

It does not automatically apply to:

```text
existing Winner appreciated above cap
```

The 59350-style problem remains organic Winner concentration / retention tradeoff, not an initial high-notional starter admission case. A future CF follow-up must not implement forced trimming of appreciated Winners based on this report.

## Primary Judgment

`PRIMARY_INITIAL_CONCENTRATION_MECHANISM = BINARY_HIGH_NOTIONAL_ADMISSION_GAP`

The current path is contract-valid and Safety hard-cap clean for initial entries through this snapshot. The design gap is that one minimum 100-share lot can consume 18-24% of equity before Winner status is earned, and the current architecture does not separately require high-notional starter evidence strength beyond generic PC/PS/lot/cap authority.

`HIGH_NOTIONAL_STARTER_RISK_REDUCIBLE_WITHOUT_WINNER_RETENTION_DAMAGE = MATERIAL`

Reason:

- initial binary admission can be studied separately from organic Winner retention
- high-notional starter risk contributed about 29.8% of large-loss magnitude through this snapshot
- the same population also produced material upside, so any follow-up must be SHADOW and control for false rejection

`PRODUCTION_CHANGE_JUSTIFIED = NO`

## Required Final Answers

1. `LATEST_COMPLETED_DATE_USED = 2023-06-15`
2. `CURRENT_INITIAL_ENTRY_SIZING_CONTRACT = BUY_NEW/REENTRY -> PC target/member authority -> PS lot/cap preflight -> phase29_l19_lot_resolution -> PC final discrete executable quantity -> Runtime Planning/Pending/Submit -> fill; one-lot soft-cap overshoot may pass only with explicit PC/PS authority and Safety hard-cap preservation`
3. `INITIAL_ENTRY_COUNT = 266`
4. `INITIAL_ENTRY_MEDIAN_WEIGHT = 3.98%`
5. `INITIAL_ENTRY_P90_WEIGHT = 14.43%`
6. `INITIAL_ENTRY_MAX_WEIGHT = 20.13%`
7. `SOFT_CAP_EXCEED_ENTRY_COUNT = 7`
8. `HARD_CAP_EXCEED_ENTRY_COUNT = 0`
9. `MINIMUM_LOT_ABOVE_SOFT_CAP_COUNT = 11`
10. `MINIMUM_LOT_ABOVE_HARD_CAP_COUNT = 0`
11. `67310_DESIRED_ALLOCATION = PS_TARGET_WEIGHT_23.7693%; PS_TARGET_NOTIONAL_399,999.29`
12. `67310_MINIMUM_LOT_NOTIONAL = 400,000 by 4,000 reference price x 100 shares`
13. `67310_INITIAL_WEIGHT = 17.83% fill/pre-entry equity; 22.65% same-day EOD position/equity`
14. `67310_SMALLER_EXECUTABLE_POSITION_POSSIBLE = NO`
15. `67310_BINARY_0_OR_100_SHARES = YES`
16. `67310_ENTRY_CONTRACT_VALID = YES_UNDER_CURRENT_PC_PS_LOT_AUTHORITY`
17. `INITIAL_ENTRY_HARD_CAP_CORRECTNESS_DEFECT_FOUND = NO`
18. `SOFT_CAP_OVERSHOOT_ROOT_CAUSE = DISCRETE_100_SHARE_LOT_REFERENCE_NOTIONAL_PLUS_EXPLICIT_PC_PS_ONE_LOT_AUTHORITY_WITHIN_SAFETY_HARD_CAP; SOME_CASES_HAVE_FILL_REFERENCE_OR_SAME_DAY_PRICE_EFFECT`
19. `HIGH_NOTIONAL_STARTER_COUNT = 11`
20. `HIGH_NOTIONAL_STARTER_TAIL_CONTRIBUTION = MATERIAL_BUT_NOT_DOMINANT_OVERALL; approx -185,380 / 621,790 = 29.8% of large-loss absolute magnitude`
21. `HIGH_NOTIONAL_STARTER_UPSIDE_CONTRIBUTION = MATERIAL; approx +380,530 positive contribution`
22. `HIGH_NOTIONAL_STARTER_WINNER_COUNT = 6`
23. `HIGH_NOTIONAL_STARTER_COSTLY_COUNT = 4; plus 1 mixed/flat/open`
24. `BINARY_ADMISSION_PROBLEM_MATERIAL = YES`
25. `CURRENT_ARCHITECTURE_HAS_EXPLICIT_HIGH_NOTIONAL_ADMISSION_SEMANTIC = NO_BEYOND_GENERIC_LOT_CAP_SAFETY_AUTHORITY`
26. `HIGH_NOTIONAL_STARTER_REQUIRES_STRONGER_CURRENT_AUTHORITY = NO_CURRENT_CONTRACT_DOES_NOT_REQUIRE_SEPARATE_STRONGER_PROOF`
27. `CAPITAL_COMPETITION_MATERIAL = YES_AS_CAPACITY_AND_DIVERSIFICATION_PRESSURE; NOT_PROVEN_AS_ALTERNATIVE_WINNER_SELECTION`
28. `67310_VS_SUCCESSFUL_HIGH_NOTIONAL_STARTER_PIT_SEPARABILITY = WEAKLY_SEPARABLE`
29. `ORGANIC_WINNER_RETENTION_OUT_OF_SCOPE_PRESERVED = YES`
30. `PRIMARY_INITIAL_CONCENTRATION_MECHANISM = BINARY_HIGH_NOTIONAL_ADMISSION_GAP`
31. `HIGH_NOTIONAL_STARTER_RISK_REDUCIBLE_WITHOUT_WINNER_RETENTION_DAMAGE = MATERIAL`
32. `PRODUCTION_CHANGE_JUSTIFIED = NO`
33. `NEXT_RECOMMENDED_STEP = READ-ONLY/SHADOW high-notional starter admission/risk-allocation study inside existing PC/PS/cap architecture, explicitly preserving successful controls such as 70640/68980/64080/88900 and excluding organic Winner forced-trim semantics.`
34. `FINAL_JUDGMENT = PHASE32_CF_BINARY_HIGH_NOTIONAL_INITIAL_LOT_ADMISSION_GAP_MATERIAL_HARD_CAP_CORRECTNESS_DEFECT_NOT_FOUND_SHADOW_STUDY_JUSTIFIED_PRODUCTION_CHANGE_NOT_JUSTIFIED`

## No Change Confirmation

- code change: NO
- config/model/threshold/weight/cap change: NO
- Runtime/Pending/Ledger mutation: NO
- resume/recover/replay/fresh-run: NO
- Production behavior change: NO
- future outcome used for entry-time authority: NO

## Final Judgment

`PHASE32_CF_BINARY_HIGH_NOTIONAL_INITIAL_LOT_ADMISSION_GAP_MATERIAL_HARD_CAP_CORRECTNESS_DEFECT_NOT_FOUND_SHADOW_STUDY_JUSTIFIED_PRODUCTION_CHANGE_NOT_JUSTIFIED`
