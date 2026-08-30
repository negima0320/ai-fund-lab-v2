# Phase32-E - Progressive ADD / Winner Capitalization Root-Cause Audit

Audit type: READ-ONLY correctness audit.  
Target run: `runtime-test-historical-extended-smoke-20260829T205402869666Z`  
Final judgment focus: `STRONG_EXISTING_CAMPAIGNS_WITH_VALID_DECISION_TIME_ADD_EVIDENCE_WERE_UNABLE_TO_ACCUMULATE_CAPITAL`

## Scope Controls

This audit did not implement repairs, did not change Strategy parameters, thresholds, weights, cash policy, risk pacing, BUY_ADD semantics, or G129 behavior, and did not run fresh-run, resume, replay, or long Historical. The only generated artifact is this report.

The audit used current run artifacts, current source, and existing Architecture/SoT documents. No future price, future return, future regime, campaign final outcome, MFE/MAE after decision time, or Historical profitability was used as evidence.

## Current Source / Run Identity

- Current source commit: `887a3361eed9f46dccfa6b5b04cb8bb7ee83aa59`
- Current worktree: dirty, from prior Phase32-C/D source and artifact work.
- Target run source baseline:
  - `source_commit`: `887a3361eed9f46dccfa6b5b04cb8bb7ee83aa59`
  - `source_dirty`: `true`
  - `accepted_artifact_hash`: `d2352977bf6feaea22e7c4e5d00980d775eefe1622126fbbde4bd22d3ee6e0e0`
  - `registry_hash`: `ac108fcfadb01f613263fa2ea00ba37fc7a0ded0ad224387d18222bfb73c3ec2`
- Observed completed evidence window: 85 completed business days, `2022-10-03` through `2023-02-06`.
- Run state at audit time: `RUNNING`; therefore conclusions are bounded to accumulated evidence, not a completed 300BD run.

## Architecture / SoT Baseline

The relevant Production-common contract is:

- Portfolio Construction owns `MARGINAL_CAPITAL_VALUE_AUTHORITY` for already-eligible `BUY_NEW` and already-positive-increment `BUY_ADD` competitors. It is an ordering authority only and must not change PM ADD semantics, thresholds, Market Context, Safety hard cap, Submit, or Execution.
- PM ADD is directional intent, not an order.
- ADD becomes executable only through:

```text
PM ADD
  -> Portfolio Construction
  -> Position Sizing
  -> positive quantity_delta_candidate
  -> Runtime Planning BUY_ADD
  -> Pending / Submit / Execution
```

The current source aligns with the same contract at the Runtime Planning boundary: positive current-position `quantity_delta_candidate` maps to `BUY_ADD`; zero delta maps to no action.

## Run Evidence Summary

Completed-window aggregate counts:

| Evidence | Count |
|---|---:|
| PM `ADD` intents | 78 |
| PM `HOLD` | 568 |
| PM `REDUCE` | 111 |
| PM `EXIT` | 134 |
| Runtime `BUY_ADD` plans | 25 |
| Runtime `BUY_NEW` plans | 320 |
| Filled `BUY_ADD` | 23 |
| Filled `BUY_NEW` | 147 |
| BUY_ADD filled symbols | 3 (`94340`, `94320`, `76470`) |
| BUY_NEW filled symbols | 143 |
| BUY_ADD notional | 204,000 JPY |
| BUY_NEW notional | 9,144,500 JPY |
| BUY_ADD share of BUY notional | 2.18% |

Campaign progression from `positions/position_campaigns.json` snapshots:

| Max campaign quantity bin | Campaigns |
|---|---:|
| 100 shares only | 91 |
| 200 shares | 8 |
| 300 shares | 1 |
| 400 shares | 2 |
| 500+ shares | 9 |

Top campaign quantities show that large share counts are often low-price BUY_NEW sizing rather than progressive winner capitalization. Examples:

- `93180`, campaign `pc-8d21a051e2fa175e-93180-0001`: max 6,700 shares, max market value 26,800 JPY, PM ADD events 0.
- `76470`, campaign `pc-44e568880028e63b-76470-0002`: max 2,400 shares, max market value 66,700 JPY, PM ADD events 25.
- `94320`, campaign `pc-7c8ed2dbb215f3a4-94320-0001`: max 700 shares, max market value 110,040 JPY, PM ADD events 15.
- `94340`, campaign `pc-406548ac1977e41b-94340-0001`: max 500 shares, max market value 75,150 JPY, PM ADD events 6.

## ADD Funnel

For the 78 PM ADD rows, the first observed decisive stop was:

| First stop | Count | Interpretation |
|---|---:|---|
| `ADD_TARGET_WEIGHT_UNCHANGED` | 53 | PM authorized ADD intent, but PC/PS resolved no incremental capital. Existing quantity was preserved. |
| `FILLED` | 23 | PM ADD became positive PS delta, Runtime BUY_ADD, and filled. |
| `PLAN_NO_FILL` | 2 | Positive Runtime BUY_ADD plan existed, but no same-day BUY_ADD fill was observed in accumulated execution evidence. |

Representative zero-increment examples:

- `2022-10-05 94340`: PM `ADD`, quality `FULL_ALLOCATION_ELIGIBLE`, current weight equals target weight `0.028291`, accepted increment `0.0`, PS `quantity_delta_candidate=0`, Runtime `NO_ACTION`.
- `2022-10-07 94340`: PM `ADD`, quality `FULL_ALLOCATION_ELIGIBLE`, current weight equals target weight `0.041218`, accepted increment `0.0`, PS `quantity_delta_candidate=0`.
- `2022-10-07 94320`: PM `ADD`, quality `REDUCED_ALLOCATION_ONLY`, quality adjustment `0.7917`, current weight equals target weight `0.029755`, accepted increment `0.0`.

Representative filled ADD examples:

- `2022-10-06 94340`: PM `ADD`, quality `FULL_ALLOCATION_ELIGIBLE`, PS `quantity_delta_candidate=100`, Runtime `BUY_ADD`, filled 100 shares.
- `2022-10-12 94340`: PM `ADD`, quality `FULL_ALLOCATION_ELIGIBLE`, accepted increment `0.014072`, Runtime `BUY_ADD`, filled 100 shares.
- `2022-10-28 94320`: PM `ADD`, quality `REDUCED_ALLOCATION_ONLY`, quality adjustment `0.783619`, Runtime `BUY_ADD`, filled 100 shares.

## Repeated ADD Progression

Repeated ADD exists but is narrow:

- `76470`: 12 BUY_ADD fills after reentry/new campaign evidence, in repeated 100-share increments.
- `94320`: 8 BUY_ADD fills across two campaign ordinals.
- `94340`: 3 BUY_ADD fills.

Therefore progressive ADD is not absent and the canonical BUY_ADD path is not globally broken. It is materially weak by breadth and capital share: only 3 symbols received ADD fills, and BUY_ADD accounted for 2.18% of BUY notional in the observed window.

## Existing Winner vs NEW Capital Competition

Execution days:

- Same day with both BUY_ADD and BUY_NEW fills: 16.
- BUY_ADD-only filled days: 5.
- BUY_NEW-only filled days: 52.

This proves that NEW capital dominates observed deployment volume. It does not by itself prove a correctness defect where capital is systematically and wrongly diverted from strong existing campaigns to NEW positions.

The dominant PM ADD stop is `ADD_TARGET_WEIGHT_UNCHANGED`, where PC/PS explicitly preserved existing quantity and emitted no positive increment. This is a portfolio construction / sizing decision boundary, not Runtime re-ranking: Runtime Planning evidence keeps `cash_winner_redecision_runtime=false`, `runtime_capital_priority_redecision=false`, and consumes Strategy order rather than recomputing BUY_NEW vs BUY_ADD preference.

Root-cause class for NEW-vs-existing diversion: `INSUFFICIENT_EVIDENCE` for a defect-level claim of systematic diversion. The run supports `NEW capital dominates deployment`, but not `Runtime/control incorrectly diverted valid ADD capital to NEW`.

## KI-005 BUY_ADD Authority Ambiguity

G129 is not reclassified as a defect.

Current evidence:

- Runtime BUY_ADD plans: 25.
- All 25 have `quantity_authority=PHASE22_J_POSITION_SIZING`.
- All 25 have `canonical_quantity_source=LEGACY_POSITION_SIZING`.
- All 25 have `pm_fallback_used=false`.
- All 25 preserve `source_pm_decision_id` and `quality_decision_id`.
- Runtime reason codes include `position_sizing_positive_quantity_delta_maps_to_buy_add` and `position_sizing_quantity_candidate_resolved`.

Judgment: the current ADD weakness is not caused by fallback/residual mechanics inventing BUY_ADD quantities after PM ADD. Positive BUY_ADD quantity has a visible PS/RP authority path. However, because the field is still named `LEGACY_POSITION_SIZING`, reportability remains confusing and overlaps with KI-006 in the BUY_WAIT cases. This is an observability/authority-label concern, not the primary root cause of weak ADD accumulation.

## KI-006 Adaptive Buy Quality Target Re-Expansion

This issue is currently reproduced and material.

Observed execution-path violations:

| Date | Symbol | Quality action | Quality adjustment | Accepted increment | Runtime / fill |
|---|---|---|---:|---:|---|
| `2022-10-12` | `94320` | `BUY_WAIT` | `0.0` | `0.021765` | BUY_ADD 100 filled |
| `2022-11-04` | `94320` | `BUY_WAIT` | `0.0` | `0.034615` | BUY_ADD 100 filled |
| `2022-11-09` | `94320` | `BUY_WAIT` | `0.0` | `0.032258` | BUY_ADD 100 filled |

For `2022-10-12 94320`, evidence path:

- Buy Quality: `quality_action=BUY_WAIT`, `quality_allocation_adjustment=0.0`, `momentum_trajectory_buy_wait`, `prior_winner_short_horizon_deterioration`, PIT `PASS`.
- Portfolio Construction: still emits `target_weight=0.045821`, `accepted_incremental_weight=0.021765`, `lot_aware_accepted_incremental_weight=0.015146`.
- Position Sizing: keeps `buy_quality_adjustment=0.0`, but emits `quantity_delta_candidate=100`, `final_quantity_delta=100`.
- Runtime Planning: maps positive PS delta to `BUY_ADD`, `planned_quantity=100`.
- Execution: BUY_ADD fill 100 shares.

Current source root cause:

- `src/ai_fund_lab_v2/strategy/buy_quality.py` assigns `BUY_WAIT` an allocation adjustment of `0.0`.
- `src/ai_fund_lab_v2/strategy/portfolio_construction.py` uses `_buy_wait_applies_to_member(row)`, which returns `False` for non-`BUY_NEW` semantics and current positions. This means BUY_WAIT does not block existing-position ADD in the PC target path.
- `src/ai_fund_lab_v2/strategy/position_sizing.py` preserves existing-position baseline for ADD, then computes ADD transaction delta from `lot_aware_accepted_incremental_weight`, `accepted_incremental_weight`, or `target-current`, without fail-closing when `pm_action=ADD` and Buy Quality says `BUY_WAIT` with adjustment `0.0`.

This is a correctness/authority preservation defect: Buy Quality's decision-time authority says no incremental ADD allocation, but the downstream PC/PS/RP path can resurrect positive executable ADD quantity.

## J-Quants / PIT Evidence

Representative ADD evidence uses J-Quants decision-time market data through local run artifacts:

- `2022-10-05 94340`: reference price `148.0`, source dataset `J-Quants equities_bars_daily`, source path `daily/2022-10-05/market_refresh/inputs/historical_asof/2022-10-05/raw_normalized/jquants/equities_bars_daily/data.parquet`, PIT `PASS`.
- `2022-10-12 94320`: reference price `158.0`, source dataset `J-Quants equities_bars_daily`, source path `daily/2022-10-12/market_refresh/inputs/historical_asof/2022-10-12/raw_normalized/jquants/equities_bars_daily/data.parquet`, PIT `PASS`.

The audit did not fetch new market data. It relied on run artifact reference-price authority and PIT proof fields.

## Root-Cause Classification

Overall class: `G_MULTIPLE_CAUSES`

Breakdown:

- Primary breadth/capital-share cause: `A_NO_DEFECT_STRATEGY_DID_NOT_AUTHORIZE_MORE_ADD` for many positions after PC/PS resolved target weight unchanged. PM ADD intent was present, but no positive target increment was authorized.
- Feasibility/conversion contributor: `E_DISCRETE_SIZING_OR_CAP_FEASIBILITY_LIMIT` for the small number of positive plans without observed fill and for 100-share lot granularity. This is not a defect by itself.
- Confirmed correctness defect: `C_BUY_QUALITY_AUTHORITY_PRESERVATION_DEFECT` for BUY_WAIT / zero quality adjustment becoming executable BUY_ADD in three observed cases.
- Not supported as primary cause: `B_ADD_AUTHORITY_PATH_DEFECT`. The path produced 25 BUY_ADD plans and 23 fills.
- Not confirmed as defect: `D_CAPITAL_COMPETITION_SYSTEMATICALLY_FAVORS_NEW`. NEW dominates deployment, but evidence does not prove an invalid diversion from decision-time-valid ADD to NEW.
- Not used: `H_INSUFFICIENT_EVIDENCE` only for the defect-level NEW-diversion claim and the two plan-without-fill terminal causes.

## Repair Boundary If Any

Mandatory narrow repair boundary:

```text
Adaptive Buy Quality authority
  -> Portfolio Construction existing-position ADD target/increment
  -> Position Sizing ADD transaction delta
  -> Runtime BUY_ADD mapping
```

Minimum repair concept, for a later repair phase only:

- For existing-position `PM ADD`, preserve the existing baseline quantity, but apply Buy Quality only to the incremental ADD allocation.
- If `quality_action=BUY_WAIT` or `quality_allocation_adjustment=0.0`, downstream PC/PS must not emit positive `accepted_incremental_weight`, `lot_aware_accepted_incremental_weight`, `quantity_delta_candidate`, or Runtime `BUY_ADD`.
- Keep G129 unchanged: when a valid positive PS ADD delta exists, Runtime/Submits should still treat BUY_ADD quantity as the order increment.

No Strategy parameter, threshold, weight, candidate-selection, cash-policy, risk-pacing, or BUY_ADD semantic change is required by this audit.

## Required Final Answers

### IS_PROGRESSIVE_ADD_MATERIALLY_WEAK_IN_THE_CURRENT_SYSTEM

YES. It is materially weak by breadth and capital share: 78 PM ADD intents yielded 25 Runtime BUY_ADD plans and 23 BUY_ADD fills, concentrated in only 3 symbols, with BUY_ADD representing 2.18% of observed BUY notional.

### WHY_DO_POSITIONS_OFTEN_REMAIN_NEAR_INITIAL_LOT_SIZE

Because most PM ADD intents do not become positive incremental capital authority. The dominant observed stop is `ADD_TARGET_WEIGHT_UNCHANGED` in PC/PS: existing quantity is preserved, accepted increment is zero, and Runtime maps the row to no action. Separately, many campaigns never receive PM ADD at all before HOLD/REDUCE/EXIT decisions.

### ARE_VALID_STRONG_CAMPAIGN_ADD_OPPORTUNITIES_BEING_LOST

PARTIAL YES, but not through a global Runtime BUY_ADD path loss. Valid PM ADD opportunities often stop at PC/PS zero-increment authority, which is an explicit portfolio/sizing decision in the current baseline. The confirmed correctness defect is the opposite direction for three cases: Buy Quality says BUY_WAIT / zero allocation, yet downstream authority resurrects executable BUY_ADD.

### IS_CAPITAL_SYSTEMATICALLY_DIVERTED_FROM_EXISTING_STRONG_CAMPAIGNS_TO_NEW_POSITIONS

UNCONFIRMED as a correctness defect. NEW positions dominate capital deployment and appear on many days with or without ADD, but the evidence does not prove invalid Runtime/control diversion from accepted strong ADD opportunities to NEW. Runtime evidence indicates Strategy order is consumed rather than re-ranked downstream.

### WHICH_EXACT_AUTHORITY_BOUNDARY_REQUIRES_REPAIR_IF_ANY

The exact repair boundary is Adaptive Buy Quality preservation across existing-position ADD incremental capital:

```text
Buy Quality BUY_WAIT / quality_allocation_adjustment=0.0
  must bind PC accepted ADD increment
  must bind PS transaction delta
  must prevent Runtime BUY_ADD unless a positive quality-authorized increment exists
```

## Confirmations

- NO source code change in Phase32-E: confirmed.
- NO config change in Phase32-E: confirmed.
- NO Strategy/parameter/threshold/weight change: confirmed.
- NO candidate-selection change: confirmed.
- NO fresh-run/resume/replay/long Historical by Codex: confirmed.
- G129 BUY_ADD accepted repair treated as baseline and not regressed: confirmed.

## Final Judgment

`PROGRESSIVE_ADD_IS_MATERIALLY_WEAK_BUT_NOT_GLOBALLY_BROKEN; PRIMARY_OBSERVED_WEAKNESS_IS_PC_PS_ZERO_INCREMENT_AUTHORITY; CONFIRMED_REPAIR_BOUNDARY_IS_KI006_BUY_QUALITY_TO_PC_PS_RUNTIME_ADD_INCREMENT_PRESERVATION; SYSTEMATIC_NEW_OVER_VALID_ADD_DIVERSION_UNCONFIRMED`
