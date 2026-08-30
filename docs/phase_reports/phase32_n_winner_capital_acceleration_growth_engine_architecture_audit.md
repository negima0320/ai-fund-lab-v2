# Phase32-N — Winner Capital Acceleration / Growth Engine Architecture Audit

## Scope

This is a READ-ONLY performance architecture research audit. No implementation
was performed.

NO CODE CHANGE: confirmed. The only Phase32-N workspace change is this phase
report.

NO future-information use: confirmed. This audit did not use future price,
future return, future regime, future MFE/MAE, later SELL outcome, final campaign
outcome, Historical profitability, or selected/bought future outcome to choose
or justify parameters.

Primary philosophy preserved:

```text
Small Entry -> Evidence Strengthens -> Increase Capital -> Hold Strong Winner
-> Reduce on Deterioration -> Exit on Breakdown
```

Primary target context:

- Initial capital assumption: `1,000,000 JPY`
- Aspirational long-term target: approximately `+50% annual return`
- The target is not guaranteed and was not used for Historical return tuning.

Evidence basis:

- Current source HEAD: `887a3361eed9f46dccfa6b5b04cb8bb7ee83aa59`
- Phase32-M report:
  `docs/phase_reports/phase32_m_end_to_end_plateau_susceptibility_root_cause_audit.md`
- Phase32-G ADD authority audit:
  `docs/phase_reports/phase32_g_pm_add_pc_increment_authority_root_cause_audit.md`
- Phase32-L campaign / REENTRY provenance repair report:
  `docs/phase_reports/phase32_l_campaign_identity_reentry_provenance_actual_path_repair.md`
- Current Historical decision-time artifacts:
  `runtime-test-historical-extended-smoke-20260830T010004222332Z`
- Accepted Architecture / SoT documents.

Important coverage caveat:

- The current run is not a completed three-year plateau reproduction.
- Available valuation coverage is 75 business days, `2022-10-03` through
  `2023-01-23`.
- Strategy artifact coverage is 76 business days, `2022-10-03` through
  `2023-01-24`.
- Within that short window, total equity moved from `1,012,350` to `1,241,460`.
  Therefore this report studies architecture fit and acceleration shape, not
  realized performance optimization.

## Current Growth-Engine Map

| Stage | Owner | Current authority | Effect | Domain |
|---|---|---|---|---|
| Candidate discovery | Candidate / Opportunity AI | accepted generation `phase19_aq_accepted_generation_641e6e313543f013` | `ACCELERATOR` by providing 50 candidates/day | Strategy |
| Buy Quality | Strategy BUY Quality Resolver | quality action, score, momentum trajectory, component statuses | `BRAKE` for reduced/wait/reject evidence | Strategy |
| BUY_NEW admission | Portfolio Construction | entry admission, capital competition, Cash alternative | `BRAKE` by selecting limited positive targets | Strategy / Risk |
| Initial sizing | Position Sizing | PC target -> discrete lot quantity | `BRAKE` through 100-share feasibility and min meaningful notional | Execution feasibility |
| Runtime BUY_NEW | Runtime Planning / Pending / Submit | consumes PS-bound quantity | `NEUTRAL` consumer, no Strategy redecision | Execution |
| PM HOLD | Position Management | campaign health, downside risk, trend continuation | `ACCELERATOR` by retaining strong campaigns | Strategy / Risk |
| PM ADD | Position Management | directional ADD intent, not order authority | `ACCELERATOR` signal only | Strategy |
| PC ADD capital | Portfolio Construction | ADD marginal capital competition, Cash/NEW/ADD frontier | primary `BRAKE` / selective accelerator | Strategy / Risk |
| PS ADD sizing | Position Sizing | accepted incremental weight -> discrete BUY_ADD quantity | `BRAKE` through lot feasibility | Execution feasibility |
| Runtime BUY_ADD | Runtime Planning / Submit / Execution | consumes PS-bound BUY_ADD order increment per G129 | `NEUTRAL` consumer | Execution |
| REDUCE | PM + Sell Planning / PS | risk increase / partial de-risk authority | `BRAKE` / risk release | Strategy / Risk |
| EXIT | PM + Runtime sell path | breakdown / stop / protection authority | `BRAKE` / hard de-risk | Strategy / Risk |
| REENTRY | PC semantic REENTRY + Runtime | strict-prior context and renewed evidence | potential `ACCELERATOR`, currently acceptance pending after Phase32-L | Strategy |

The primary current acceleration path is not first BUY_NEW; it is:

```text
PM ADD intent
-> PC positive ADD increment
-> PS executable 100-share lot
-> Runtime BUY_ADD
-> fill
```

## Initial Entry Vs Confirmed-Winner Capital

The architecture correctly distinguishes an uncertain new opportunity from an
already-held campaign:

- BUY_NEW starts from candidate / opportunity / BQ / PC admission.
- ADD starts from an existing campaign with PM confirmation and current
  position state.
- ADD then competes against NEW and Cash at PC.
- PS and Runtime cannot promote ADD on their own.

However, the current production shape mostly preserves a conservative allocation
regime after strength is confirmed:

- PM emitted ADD intent 66 times in the Phase32-M evidence window.
- Only 16 BUY_ADD fills occurred.
- All BUY_ADD fills were one lot.
- PC selected `ADD` as final capital winner on only 2 of 76 Strategy days.
- PC selected `CASH_OPTIONALITY` on 51 of 76 Strategy days.
- PC selected `NEW_BUY` on 23 of 76 Strategy days.

Judgment:

- The distinction exists and is architecturally clean.
- The post-confirmation capital increase is real but conservative.
- The system is better at preserving winners than accelerating them.

## Existing Strengthening Evidence Inventory

Existing decision-time evidence that can support confirmation-based capital
acceleration without inventing new features:

Confidence-strengthening evidence:

- PM `ADD` with `strong_trend_continuation`.
- PM `ADD` with `opportunity_rank_still_high`.
- PM `HOLD` with `trend_continuation`.
- PM `HOLD` with `positive_expected_edge`.
- Buy Quality `FULL_ALLOCATION_ELIGIBLE`.
- Buy Quality `REDUCED_ALLOCATION_ONLY` when explicitly not blocked.
- momentum trajectory classification and status.
- short trend / MA evidence embedded in BQ and PC reentry/entry fields.
- rank persistence through `opportunity_buy_rank`.
- expected edge improvement state.
- incremental investment value state.
- opportunity cost status.
- campaign health / continuation state.

Capital feasibility evidence:

- current weight.
- current quantity.
- single-name cap / maximum position weight.
- concentration headroom.
- available incremental budget.
- Cash competitor state.
- risk pacing intent.
- PC `accepted_incremental_weight`.
- PC / PS `lot_aware_accepted_incremental_weight`.
- PS `final_quantity_delta`.
- lot size / one-lot authority.
- pending reserved cash.

Risk constraint evidence:

- no-loss-averaging status.
- downside risk status.
- Safety hard constraints.
- broker eligibility.
- corporate-action status.
- liquidity capacity.
- safety hard max / cap feasibility.
- REDUCE / EXIT reason classifications.
- Risk Pacing intent (`CAUTIOUS_DEPLOYMENT`, `GRADUAL_REDEPLOYMENT`,
  `NORMAL_DEPLOYMENT`).

No new feature family is required to express a first version of acceleration.
The current evidence can already distinguish:

- ADD intent only,
- ADD with improving edge,
- ADD with positive incremental value,
- ADD with opportunity-cost pass,
- ADD with feasible lot/cap headroom,
- ADD defeated by Cash/NEW/lot/safety.

## Current ADD Acceleration Shape

Observed ADD behavior from current run artifacts:

- PM ADD decisions: 66.
- BUY_ADD fills: 16.
- BUY_ADD symbols:
  - `76470`: 11 ADD fills.
  - `94340`: 3 ADD fills.
  - `94320`: 2 ADD fills.
- ADD cadence gaps between repeated ADD fills:
  - min 1 business day
  - median 2 business days
  - p75 3 business days
  - max 8 business days
- BUY_ADD quantity: all 16 fills were 100 shares.
- BUY_ADD notional:
  - min `2,600`
  - median `2,800`
  - p75 `14,587.5`
  - max `16,390`

Representative `76470` decision-time path:

- `2022-11-11`: BUY_NEW 300 shares at `26`, notional `7,800`.
- `2022-11-25` through `2023-01-05`: eleven BUY_ADD fills of 100 shares each.
- By `2023-01-05`, the campaign reached 1,400 shares.
- The acceleration occurred through repeated one-lot increments, not multi-lot
  capital authorization.

Representative positive ADD rows:

- `2022-10-06` `94340`: PC increment `0.035714`, PS delta `100`, BUY_ADD
  filled.
- `2022-10-12` `94340`: PC increment `0.021765`, PS delta `100`, BUY_ADD
  filled.
- `2022-10-28` `94320`: PC increment `0.037037`, PS delta `100`, BUY_ADD
  filled.
- `2022-11-25` `76470`: PC increment `0.028508`, PS delta `100`, BUY_ADD
  filled.

Representative braking rows:

- `2022-10-05` `94340`: PM ADD but PC no positive ADD increment.
- `2022-11-15` `99840`: PC positive increment `0.031250`, PS delta `0`.

Judgment:

- The ADD cadence can be fast; it is not fundamentally calendar-blocked.
- The magnitude is slow because the authorized execution unit is usually one
  lot and because PC often gives no positive ADD increment.
- The maximum effective acceleration rate is therefore limited by
  one-lot-per-authorized-ADD plus PC final-winner selectivity.

## Candidate Acceleration Architectures

### Option 1 — Faster Repeated ADD Cadence

Fit: medium.

The evidence shows repeated ADD can already happen quickly: median ADD-to-ADD
gap is 2 business days, with 1-business-day gaps present. Cadence alone is not
the primary bottleneck. It may still help if formal cooldown or recomputation
rules block same-strength follow-through in the three-year run.

Classification: `MEDIUM_PRIORITY_RESEARCH`

### Option 2 — Multi-Lot ADD Magnitude

Fit: high.

This directly targets the observed bottleneck: positive ADD execution is
typically one lot. A multi-lot ADD mechanism could preserve cautious initial
entry while allowing a confirmed campaign to scale faster when existing PIT
evidence is strong and cap/risk/lot constraints pass.

Required guardrails:

- PC owns magnitude.
- PS owns discrete quantity.
- Runtime consumes only PS-bound order increment.
- G129 remains order-increment scoped.
- Multi-lot authorization must be evidence-tiered and cap-aware.
- Missing or conflicting evidence remains fail-closed.

Classification: `HIGH_PRIORITY_PERFORMANCE_INITIATIVE`

### Option 3 — Evidence-Tiered ADD

Fit: very high.

Conceptual tiers can preserve semantics without choosing thresholds in this
phase:

- ordinary ADD: one staged increment.
- strong ADD: more capital or faster repeated increments when improving edge,
  positive incremental value, opportunity-cost pass, momentum/continuation
  strength, no-loss-averaging pass, and cap headroom agree.
- exceptional ADD: rare, larger authorization under normal/constructive Risk
  Pacing and strong safety/feasibility evidence.

This maps directly to the accepted philosophy:

```text
evidence strengthens -> increase capital
```

Classification: `HIGH_PRIORITY_PERFORMANCE_INITIATIVE`

### Option 4 — Dynamic Target Weight Expansion

Fit: medium-high.

Dynamic expansion can give PC a clearer target path from small entry toward the
single-name cap as confidence improves. It risks becoming a hidden parameter
increase if implemented as a broad target-weight uplift. It should therefore be
implemented only as an ADD-specific, evidence-tiered PC authority rather than a
global BUY_NEW target change.

Classification: `MEDIUM_PRIORITY_RESEARCH`

### Option 5 — Existing Winner Priority In Capital Competition

Fit: high.

Current PC frequently selects Cash or NEW while PM ADD winners are present. The
architecture already allows ADD/NEW/Cash comparison; an initiative could make
existing winner marginal value more explicit when it is clearly stronger than
new alternatives. This should not make ADD automatically superior. It should
only reduce undercapitalization when existing campaign evidence is materially
stronger than competing NEW evidence.

Classification: `HIGH_PRIORITY_PERFORMANCE_INITIATIVE`

### Option 6 — Broader Daily Deployment

Fit: medium.

Current PC selected zero or one deployment security per day in the audited
window, with average deployment security count `0.329`. Broader daily deployment
could improve capital usage when multiple independent strong opportunities
exist. But it can also dilute confirmation-based acceleration by spreading
capital across more names. It should be secondary to winner ADD magnitude.

Classification: `MEDIUM_PRIORITY_RESEARCH`

### Option 7 — Cash Optionality Rebalancing

Fit: medium.

Cash is a first-class allocation destination and must remain so. The evidence
does show Cash final winner on 51 of 76 Strategy days, often with cautious
market optionality and marginal opportunity set reasons. Rebalancing may be
reasonable when strong deployable evidence exists, but a blanket lower cash
target would violate the task philosophy.

Classification: `MEDIUM_PRIORITY_RESEARCH`

## High-Resolution Marginal Capital Value Relevance

`canonical_high_resolution_marginal_capital_value.v1` is relevant but not yet
mandatory.

Current coarse evidence already distinguishes enough states for a first
acceleration initiative:

- weak ADD: expected edge weakening, incremental value unknown, opportunity-cost
  fail.
- normal ADD: PM ADD with incomplete or comparable evidence.
- strong ADD: improving expected edge, positive incremental investment value,
  opportunity-cost pass, BQ pass/reduced-but-eligible, no-loss-averaging pass.
- strong NEW: high rank / BQ / entry admission / PC target.

The architecture reminder remains important:

```text
COMMON_MARGINAL_VALUE_SEMANTIC DOES NOT REQUIRE SINGLE SCALAR
SECURITY_QUALITY != HOLD_RETENTION_VALUE != ADD_NEXT_LOT_MARGINAL_VALUE
```

Recommendation:

- Do not import a deferred high-resolution architecture automatically.
- First use existing PIT evidence to define explicit ADD acceleration tiers.
- Introduce high-resolution marginal value only if the three-year run shows the
  current categorical evidence cannot cleanly rank strong ADD vs strong NEW vs
  Cash without ambiguity.

Classification: `MEDIUM_PRIORITY_RESEARCH`

## Capital Acceleration Vs Risk

Acceleration must not become faster than de-risking can control.

Risk controls already available:

- single-name cap / maximum position weight.
- concentration headroom.
- safety hard cap.
- broker eligibility.
- corporate-action block.
- liquidity capacity.
- downside risk status.
- no-loss-averaging status.
- REDUCE authority for partial de-risk.
- EXIT authority for full breakdown.
- Risk Pacing intent.

Risk implications by mechanism:

| Mechanism | Concentration impact | Cash impact | Risk interaction | Risk judgment |
|---|---|---|---|---|
| Faster ADD cadence | medium | medium | requires fresh evidence each cycle | acceptable if evidence refresh is strict |
| Multi-lot ADD magnitude | high | high | must bind cap/safety before PS | highest reward, highest guardrail need |
| Evidence-tiered ADD | controlled | controlled | best fit for bounded acceleration | best architecture fit |
| Dynamic target expansion | medium-high | medium | risk of broad semantic drift | research before implementation |
| Winner priority in PC | medium | medium | must keep NEW/Cash valid competitors | high fit if non-automatic |
| Broader deployment | medium | high | may increase fragmentation | secondary |
| Cash rebalancing | medium | high | must not remove Cash optionality | secondary |

Slow-acceleration / fast-deacceleration asymmetry is present:

- PM can emit REDUCE/EXIT frequently.
- ADD is staged, one-lot, and often stopped at PC.
- This asymmetry can suppress compounding even when individual de-risking rules
  are valid.

It is not a correctness defect, but it is the core performance architecture
pressure.

## REDUCE / EXIT Interaction

More aggressive winner capitalization can coexist with current REDUCE / EXIT
semantics if the acceleration remains PC/PS-authorized and cap-aware.

Current sell-side evidence:

- PM `REDUCE`: 138
- PM `EXIT`: 80
- REDUCE reasons:
  - `risk_increased_but_trend_not_broken`: 115
  - `peak_drawdown_warning`: 23
- EXIT reasons:
  - `trend_and_opportunity_broken`: 46
  - `weak_hold_score`: 15
  - `hard_stop_current_return`: 12
  - `profit_retention_break`: 12

Sell authorities appear structurally sufficient:

- REDUCE can scale down progressively.
- EXIT remains campaign-wide on breakdown.
- Sell Planning / Runtime should remain quantity and execution consumers for
  sell-side authority.

Potential structural addition for future design:

- an acceleration-tier audit field that records whether the current position
  can be de-risked by current REDUCE/EXIT authority if increased. This is not a
  new stop threshold; it is evidence completeness for acceleration.

No sell thresholds should be changed in Phase32-N.

## REENTRY Interaction

Acceleration should not apply identically to BUY_NEW, REENTRY, and ADD.

Recommended semantic distinction:

- BUY_NEW: remains cautious initial entry.
- REENTRY: starts cautiously after valid strict-prior context and renewed
  evidence; can later accelerate as ADD after the new campaign proves strength.
- Existing ADD: primary capital acceleration surface because the campaign has
  active position evidence, PM continuation evidence, and current risk/cap
  context.

Phase32-L repaired source-level campaign identity / REENTRY provenance, but
actual-path acceptance is still pending on a post-L run. Therefore REENTRY
capital acceleration should wait until post-L evidence confirms prior-context
survival and new campaign identity continuity.

## Ranked Initiative Candidates

| Rank | Initiative | Category | Rationale |
|---:|---|---|---|
| 1 | Evidence-tiered ADD magnitude | `HIGH_PRIORITY_PERFORMANCE_INITIATIVE` | best fit with confirmation-based philosophy; uses existing PIT evidence; preserves small entry |
| 2 | Existing winner priority in PC capital competition | `HIGH_PRIORITY_PERFORMANCE_INITIATIVE` | addresses primary PC bottleneck without Runtime redecision |
| 3 | Multi-lot ADD authorization | `HIGH_PRIORITY_PERFORMANCE_INITIATIVE` | direct answer to one-lot magnitude limit; must be tier/cap guarded |
| 4 | Dynamic target weight expansion for confirmed winners | `MEDIUM_PRIORITY_RESEARCH` | useful but higher semantic drift risk |
| 5 | Broader daily deployment | `MEDIUM_PRIORITY_RESEARCH` | may improve deployment but can increase fragmentation |
| 6 | Cash optionality rebalancing | `MEDIUM_PRIORITY_RESEARCH` | relevant, but blanket cash reduction is not acceptable |
| 7 | Faster repeated ADD cadence | `MEDIUM_PRIORITY_RESEARCH` | cadence already can be fast; magnitude/PC winner selection matter more |
| 8 | BQ aggressiveness increase | `LOW_PRIORITY` | affects initial selection too broadly; less aligned with preferred direction |
| 9 | REDUCE/EXIT loosening | `NOT_RECOMMENDED` | violates no-hindsight and weakens risk controls |

## Minimum-Change Recommendation

Smallest architecture change with the best expected risk/reward:

```text
Add an evidence-tiered PC ADD acceleration authority that can authorize more
than one executable ADD lot, or a larger staged ADD increment, only when
existing decision-time evidence is complete and strongly positive.
```

This should be a PC-owned performance initiative, not a Runtime change.

Minimum required design constraints:

- BUY_NEW initial entry remains cautious.
- PM ADD remains directional intent only.
- PC owns acceleration tier and continuous capital authorization.
- PS owns discrete quantity and lot conversion.
- Runtime/Pending/Submit/Execution consume the PS-bound G129 order increment.
- Cash remains a first-class competitor.
- Risk Pacing remains authoritative input, not bypassed.
- Safety / broker / corporate action remain hard fail-closed constraints.
- No acceleration is allowed on missing provenance, missing current position
  authority, missing incremental value, no-loss-averaging failure, cap breach, or
  safety conflict.
- Acceleration tier must be observable as decision-time evidence.

The first version should avoid introducing a universal scalar if the current
categorical evidence is sufficient.

## Required Lever Classification

| Lever | Classification | Reason |
|---|---|---|
| BQ aggressiveness | `KEEP` | Candidate supply exists; broad BQ loosening would affect initial selection rather than confirmed winners |
| initial BUY_NEW sizing | `KEEP` | cautious initial entry is core philosophy; evidence does not show correctness defect |
| ADD cadence | `INVESTIGATE` | repeated ADD can already occur quickly; verify in 3-year run |
| ADD magnitude | `HIGH_PRIORITY_PERFORMANCE_INITIATIVE` | one-lot ADD is the clearest acceleration limit |
| PC winner-vs-NEW competition | `HIGH_PRIORITY_PERFORMANCE_INITIATIVE` | PC is the primary bottleneck and correct owner |
| deployment breadth | `INVESTIGATE` | useful only if it does not increase fragmentation |
| Cash optionality | `INVESTIGATE` | Cash wins often, but must remain first-class |
| lot/minimum notional behavior | `INVESTIGATE` | important feasibility brake; do not bypass PS authority |
| REDUCE/EXIT posture | `KEEP` | risk controls should not be loosened without separate approval and evidence |

## What Must Remain Unchanged

- Candidate selection.
- BUY_NEW cautious entry posture.
- Strategy parameters / thresholds / weights.
- Buy Quality semantics.
- Cash as first-class alternative.
- Risk Pacing authority.
- Safety hard constraints.
- Broker eligibility and corporate-action blocks.
- PM / PC / PS / Runtime ownership boundaries.
- G129 BUY_ADD order-increment semantics.
- Phase32-L campaign identity and REENTRY provenance repair.
- REDUCE / EXIT thresholds and stop philosophy.

## What Requires User Approval

The following are performance initiatives and require explicit user approval
before design or implementation:

- Evidence-tiered ADD acceleration.
- Multi-lot ADD authorization.
- Existing winner priority in PC capital competition.
- Dynamic target expansion for confirmed winners.
- Broader daily deployment.
- Cash optionality rebalancing.
- Lot/minimum meaningful notional redesign.

These must not be introduced as correctness repairs.

## What Should Wait For The Planned 3-Year Historical Run

The planned long run should characterize, without production hindsight tuning:

- PM ADD count by month.
- PM ADD -> PC positive increment -> PS positive quantity -> BUY_ADD fill funnel.
- ADD cadence gap distribution.
- ADD fill lots per campaign.
- time from BUY_NEW to first ADD.
- time from first ADD to reaching 50%, 75%, and 100% of single-name cap.
- strong ADD evidence counts:
  - improving expected edge,
  - positive incremental investment value,
  - opportunity-cost pass,
  - no-loss-averaging pass,
  - BQ eligible,
  - concentration headroom.
- Cash final-winner frequency when strong ADD evidence exists.
- NEW final-winner frequency when strong ADD evidence exists.
- cases where PS zeroes PC-positive ADD solely due to lot/cap feasibility.
- REDUCE/EXIT after accelerated-size campaigns, classified only by
  decision-time reason.
- post-Phase32-L REENTRY provenance acceptance before any REENTRY acceleration
  design is considered.

Do not use the three-year run to tune to realized return. Use it to measure
decision-time funnel shape and authority bottlenecks.

## Final Judgment

1. `IS_CURRENT_CAPITAL_ACCELERATION_TOO_WEAK_RELATIVE_TO_THE_ACCEPTED_INVESTMENT_PHILOSOPHY`

   Yes, as an architecture-performance judgment. The system preserves the
   small-entry and hold-strong-winner philosophy, but capital acceleration after
   confirmation is conservative: PM ADD appears 66 times, BUY_ADD fills occur 16
   times, all BUY_ADD fills are one lot, and PC selects ADD as final capital
   winner on only 2 of 76 Strategy days.

2. `WHERE_IS_THE_PRIMARY_ACCELERATION_BOTTLENECK`

   Portfolio Construction ADD capital authorization and winner-vs-NEW-vs-Cash
   capital competition. PS lot conversion is a secondary brake; Runtime is not
   the bottleneck because it consumes PS-bound authority.

3. `WHICH_EXISTING_DECISION_TIME_EVIDENCE_CAN_SAFELY_AUTHORIZE_MORE_CAPITAL`

   PM ADD with strong trend continuation, improving expected edge, positive
   incremental investment value, opportunity-cost pass, BQ eligible status,
   momentum/continuation strength, no-loss-averaging pass, current weight,
   concentration headroom, cash availability, Risk Pacing, and Safety/broker/CA
   PASS evidence.

4. `SHOULD_ACCELERATION_BE_INCREASED_THROUGH_ENTRY_ADD_PC_OR_CASH`

   Increase acceleration through ADD/PC, not through broader BUY_NEW entry or
   blanket cash reduction. PC is the correct authority for confirmed-winner
   capital acceleration; PS and Runtime should remain consumers.

5. `WHAT_IS_THE_MINIMUM_ARCHITECTURAL_CHANGE_WITH_THE_BEST_EXPECTED_RISK_REWARD`

   Add a PC-owned evidence-tiered ADD acceleration authority that can authorize
   multi-lot or larger staged ADD increments when current PIT evidence is
   complete and strongly positive, while preserving Cash, Risk Pacing, Safety,
   single-name cap, PS discrete quantity authority, and G129 semantics.

6. `WHICH_CHANGES_REQUIRE_USER_APPROVAL_AS_PERFORMANCE_INITIATIVES`

   Evidence-tiered ADD, multi-lot ADD, existing winner priority in PC, dynamic
   target expansion, broader daily deployment, Cash optionality rebalancing, and
   lot/minimum-notional redesign all require explicit user approval as
   performance initiatives.

7. `WHAT_SHOULD_BE_VALIDATED_IN_THE_PLANNED_3_YEAR_HISTORICAL_RUN`

   Validate the decision-time ADD funnel, strong-evidence ADD frequency,
   PC-positive-to-PS-positive conversion, ADD cadence and magnitude, Cash/NEW
   defeat frequency when strong ADD exists, campaign path to single-name cap,
   REDUCE/EXIT manageability for larger campaigns, and post-Phase32-L REENTRY
   provenance acceptance. Do not use realized return to select parameters.

Final classification:

`PHASE32_N_CONFIRMATION_BASED_PC_ADD_ACCELERATION_RECOMMENDED_AS_PERFORMANCE_INITIATIVE`

