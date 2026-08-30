# Phase32-M — End-to-End Plateau Susceptibility Root-Cause Audit

## Scope

This is a READ-ONLY correctness audit. No Strategy parameter, threshold, weight,
feature, rule, ADD aggressiveness, cash policy, Risk Pacing, or Runtime control
logic was changed.

NO CODE CHANGE: confirmed. The only Phase32-M workspace change is this phase
report.

Target evidence:

- Run: `runtime-test-historical-extended-smoke-20260830T010004222332Z`
- Current source HEAD: `887a3361eed9f46dccfa6b5b04cb8bb7ee83aa59`
- Run source baseline: same commit, `source_dirty=true`
- Historical evaluation authority: `PASS`
- Accepted AI generation: `phase19_aq_accepted_generation_641e6e313543f013`
- Completed valuation coverage: 75 business days, `2022-10-03` through
  `2023-01-23`
- Strategy artifact coverage: 76 business days, `2022-10-03` through
  `2023-01-24`
- Current run state at audit time: `HALT`, next job `2023-01-24:submit`

The run is not itself a completed long-horizon plateau reproduction. Within the
available valuation window, total equity moved from `1,012,350` on
`2022-10-03` to `1,241,460` on `2023-01-23` (`+22.63%`). Therefore this audit
classifies plateau susceptibility from actual decision-path evidence, not from
long-run realized profitability.

Future price, future return, future regime, future MFE/MAE, later SELL result,
final campaign outcome, Historical PnL, and selected/bought outcome were not
used for parameter selection or hindsight rule judgment. PC artifacts report
`future_information_used=true` count `0` and Historical/outcome input count `0`
in the audited material.

NO future-information use: confirmed for this audit.

## Architecture Boundary

The accepted architecture makes several important constraints explicit:

- Runtime is an execution system and must not recompute ranking, target weights,
  HOLD/ADD/REDUCE/EXIT, sizing, or cash posture.
- PM `ADD` is an intent / candidate signal, not an order.
- PC owns NEW/ADD/Cash capital competition.
- PS owns discrete quantity conversion.
- Runtime Planning maps PS-bound positive deltas to `BUY_NEW` / `BUY_ADD`.
- Cash and residual optionality are first-class allocation destinations.
- G129 requires actual BUY_ADD fill materialization and canonical campaign
  identity proof; same-symbol movement alone is not authority.

These boundaries mean that a low number of BUY_ADD fills, high cash optionality,
or many zero-delta candidates is not automatically a correctness defect.

## Evidence Coverage

Operational and decision evidence available:

- `buy_quality_decisions.json`: 3,800 decisions, exactly 50 per Strategy day.
- `portfolio_construction.json`: 4,064 PC rows.
- `position_sizing.json`: 4,064 PS rows.
- `runtime_planning.json`: 2,581 Runtime Planning rows.
- `fills.json`: 280 fills.
- `pm_decisions.json`: 783 PM decisions.
- `valuation_projection.json`: 75 valuation snapshots.
- `position_campaigns.json`: campaign-state snapshots through the covered days.

Because Phase32-L repaired campaign identity / REENTRY provenance in source
after this run's artifacts were produced, pre-L artifact identity splits are not
reopened as Phase32-M defects. Phase32-L still requires a fresh actual-path
acceptance run.

## A. Candidate Supply

Candidate supply is not scarce in this evidence window:

- BQ candidates: 50 per day, 3,800 total.
- BQ action distribution:
  - `REDUCED_ALLOCATION_ONLY`: 2,144
  - `FULL_ALLOCATION_ELIGIBLE`: 323
  - `BUY_WAIT`: 699
  - `REJECT`: 634
- Quality score distribution:
  - min `0.000000`, median `0.590289`, p75 `0.681177`, max `0.822074`
- Runtime opportunity score distribution:
  - min `-0.943784`, median `-0.476747`, p75 `-0.276587`, max `0.493936`
- BQ component status:
  - execution feasibility, market context modifier, portfolio fit, relative
    opportunity quality, and signal reliability all `PASS` for all 3,800 rows.
  - momentum trajectory quality: `PASS_WITH_REDUCTION` 2,200, `BUY_WAIT` 809,
    `PASS` 791.

Interpretation: supply exists, but accepted decision-time evidence frequently
classifies it as reduced or wait/reject. This is candidate-quality / trajectory
weakness and entry caution, not missing data or discovery failure.

Classification:

- `CANDIDATE_SCARCITY`: `NOT_REPRODUCED`
- `CANDIDATE_QUALITY_WEAKNESS`: `PERFORMANCE_INITIATIVE_CANDIDATE`
- Correctness defect: `NO`

## B. Candidate To BUY_NEW Funnel

For top-10, BQ-eligible BUY candidates (`FULL_ALLOCATION_ELIGIBLE` or
`REDUCED_ALLOCATION_ONLY`) that were not current positions when identifiable:

- `BUY_NEW_FILLED`: 17
- `PC_NO_BUY_NEW_TARGET`: 228
- `PS_NO_EXECUTABLE_BUY_NEW_DELTA`: 59
- `NO_BUY_NEW_FILL`: 23

Representative actual-path examples:

- `2022-10-03` `94340`: BQ rank 3, PC target `0.033636`, PS delta `200`,
  BUY_NEW filled.
- `2022-10-04` `76920`: BQ rank 5, no positive PC BUY_NEW target.
- `2022-10-05` `39060`: BQ rank 3, PC target `0.034074`, PS delta `0`.
- `2022-10-05` `76920`: BQ rank 4, PC target `0.034074`, PS delta `200`, but
  no same-day BUY_NEW fill.

Runtime Planning and fills:

- Runtime plans: `BUY_NEW` 288, `BUY_ADD` 19, `SELL_EXIT` 119, `NO_ACTION` 546,
  `NO_ORDER` 1,609.
- Fills: `BUY_NEW` 131, `BUY_ADD` 16, `SELL_EXIT` 117, `REDUCE` 16.

Interpretation: the dominant BUY_NEW stop is PC no-target, followed by PS
discrete feasibility and non-fill/submit execution effects. This is a
deliberately selective funnel. No evidence shows Runtime re-deciding Strategy.

Classification:

- `ENTRY_FUNNEL_SUPPRESSION`: `PERFORMANCE_INITIATIVE_CANDIDATE`
- `LOT_OR_CAP_FEASIBILITY`: `INTENDED_BEHAVIOR`
- Correctness defect: `NO`

## C. Initial BUY_NEW Sizing

BUY_NEW fill sizing:

- Count: 131
- Notional: min `7,800`, median `41,500`, p75 `84,250`, max `222,000`
- Quantity: min `100`, median `100`, p75 `100`, max `6,500`

Initial sizing often lands at one lot, but the evidence shows this flows through
accepted PC target and PS lot conversion. There is not enough evidence that
continuous investment meaning is silently overwritten incorrectly; many one-lot
orders are explainable under 100-share feasibility.

Classification:

- `INITIAL_SIZING_TOO_SMALL_BY_AUTHORITY`: `INSUFFICIENT_EVIDENCE`
- `LOT_OR_CAP_FEASIBILITY`: `INTENDED_BEHAVIOR`
- Correctness defect: `NO`

## D. Winner Capitalization / ADD

PM emitted ADD intent 66 times:

- PM ADD reasons:
  - `strong_trend_continuation`: 66
  - `opportunity_rank_still_high`: 66
  - `no_loss_averaging`: 66

ADD funnel from PM intent:

- `PC_NO_POSITIVE_ADD_INCREMENT`: 45
- `BUY_ADD_FILLED`: 16
- `PS_NO_EXECUTABLE_ADD_DELTA`: 3
- `NO_BUY_ADD_FILL`: 2

BUY_ADD fill sizing:

- Count: 16
- Notional: min `2,600`, median `2,800`, p75 `14,587.5`, max `16,390`
- Quantity: all 16 were 100 shares.

Representative ADD path examples:

- `2022-10-06` `94340`: positive PC increment `0.035714`, PS delta `100`,
  BUY_ADD filled.
- `2022-11-25` `76470`: positive PC increment `0.028508`, PS delta `100`,
  BUY_ADD filled.
- `2022-10-05` `94340`: PM ADD, but PC emitted no positive ADD increment.
- `2022-11-15` `99840`: PC positive increment `0.031250`, PS delta `0`.

Interpretation: winners can receive ADD, and G129-style order-increment ADD
fills are present, but capitalization is narrow and staged. Most PM ADD intents
lose before execution, usually at PC capital competition. This is consistent
with the accepted architecture: PM ADD-worthiness alone does not authorize
capital. However, structurally, this can undercapitalize true winners if the
user wants a more aggressive winner-capitalization philosophy.

Classification:

- `WINNER_CAPITALIZATION_LIMIT`: `PERFORMANCE_INITIATIVE_CANDIDATE`
- `OVER_CONSERVATIVE_PC_COMPETITION`: `PERFORMANCE_INITIATIVE_CANDIDATE`
- `LOT_OR_CAP_FEASIBILITY`: `INTENDED_BEHAVIOR`
- Correctness defect: `NO`

## E. Capital Fragmentation / Concentration

Valuation and exposure:

- Equity: `1,012,350` first, `1,241,460` latest; median `1,135,450`
- Cash ratio: min `0.009182`, median `0.227892`, p75 `0.359100`,
  max `0.719822`
- Exposure ratio: min `0.280178`, median `0.772108`, p75 `0.879130`,
  max `0.990818`

Position concentration:

- Open position count: min `0`, median `10`, p75 `11.25`, max `14`
- 100-share positions: median `7`, p75 `8`, max `13`
- Max single-name weight: median `0.168267`, p75 `0.214837`, max `0.229133`
- Top-3 weight: median `0.421679`, p75 `0.506961`, max `0.550639`
- Top-5 weight: median `0.570415`, p75 `0.682083`, max `0.773318`
- Median position weight: median `0.055188`

PC cash / capital competition:

- Final capital winner: `CASH_OPTIONALITY` 51 days, `NEW_BUY` 23 days, `ADD` 2
  days.
- Deployment security count per day: min `0`, max `1`, average `0.329`.
- Cash reasons include `LOT_RESIDUAL_OPTIONALITY` 68,
  `UNAVOIDABLE_LOT_RESIDUAL` 68, `CAUTIOUS_MARKET_OPTIONALITY_ELEVATED` 55,
  `MARGINAL_OPPORTUNITY_SET` 52, `STRONG_OPPORTUNITY_PRESENT` 24.

Interpretation: the portfolio is not trivially over-fragmented by position count
alone: top weights are meaningful and top-5 concentration can exceed 57% median.
However, effective capital deployment is fragmented into many one-lot / small
positions while PC frequently selects Cash optionality and permits at most one
deployment security per day. This creates a plausible plateau susceptibility:
capital may be exposed, yet incremental capital is often not concentrated into
existing valid winners.

Classification:

- `CAPITAL_FRAGMENTATION`: `PERFORMANCE_INITIATIVE_CANDIDATE`
- `CASH_INTENDED`: `INTENDED_BEHAVIOR`
- `OVER_CONSERVATIVE_PC_COMPETITION`: `PERFORMANCE_INITIATIVE_CANDIDATE`
- Correctness defect: `NO`

## F. HOLD / Winner Retention

PM decisions:

- `HOLD`: 499
- `ADD`: 66
- `REDUCE`: 138
- `EXIT`: 80

HOLD reasons:

- `trend_continuation`: 315
- `downside_risk_contained`: 301
- `positive_expected_edge`: 96
- `hold_score_above_exit_threshold`: 53

This shows winners or acceptable continuing positions are often retained. The
system distinguishes HOLD-worthy from ADD-worthy, and the architecture requires
that distinction. The available evidence does not show a correctness defect in
retention semantics.

Classification:

- `EARLY_REDUCE_EXIT`: `INSUFFICIENT_EVIDENCE`
- `WINNER_CAPITALIZATION_LIMIT`: `PERFORMANCE_INITIATIVE_CANDIDATE`
- Correctness defect: `NO`

## G. REDUCE / EXIT Funnel

PM REDUCE reasons:

- `risk_increased_but_trend_not_broken`: 115
- `peak_drawdown_warning`: 23

PM EXIT reasons:

- `trend_and_opportunity_broken`: 46
- `weak_hold_score`: 15
- `hard_stop_current_return`: 12
- `profit_retention_break`: 12

REDUCE and EXIT are frequent enough to cap compounding when combined with narrow
ADD capitalization. But the reasons are decision-time risk / trend /
profit-protection classifications, not future-outcome-derived tuning. The
evidence does not prove systematic incorrect exit suppression or churn; judging
that would require additional actual-path windows and explicit decision-time
reason-to-execution continuity analysis.

Classification:

- `EARLY_REDUCE_EXIT`: `INSUFFICIENT_EVIDENCE`
- `CAMPAIGN_LIFECYCLE_DEFECT`: `NOT_REOPENED_IN_PHASE32_M`
- Correctness defect: `NO` from current evidence

## H. REENTRY Lifecycle

Pre-Phase32-L artifacts in this run show:

- REENTRY semantic rows: 1,055
- `FAIL_CLOSED`: 973
- `REVIEW_REQUIRED`: 80
- `PASS`: 2
- `reentry_safety_restriction_status`: `PASS` for all 1,055
- broker eligibility: `PASS` for all 1,055
- corporate action: `NO_EVENT` for all 1,055
- prior context/provenance: `REVIEW_REQUIRED` for all 1,055

This run confirms that safety/broker/corporate-action classification is
separated after Phase32-J style semantics. It also contains pre-L provenance
loss artifacts, but Phase32-L repaired the current source contract after this
run. Therefore this audit does not use the pre-L run to fail Phase32-L; it marks
actual-path Phase32-L acceptance as still required.

Classification:

- `REENTRY_OPPORTUNITY_LOSS`: `INSUFFICIENT_EVIDENCE` for current source
- `CAMPAIGN_LIFECYCLE_DEFECT`: repaired in source by Phase32-L, actual-path
  acceptance pending
- Correctness defect requiring new Phase32-M repair: `NO`

## I. Plateau Taxonomy

| Taxonomy | Current Classification | Evidence |
|---|---:|---|
| `CANDIDATE_SCARCITY` | `NOT_REPRODUCED` | 50 BQ rows/day, 3,800 total |
| `CANDIDATE_QUALITY_WEAKNESS` | `PERFORMANCE_INITIATIVE_CANDIDATE` | 2,144 reduced-only; 699 wait; 634 reject; median runtime score negative |
| `ENTRY_FUNNEL_SUPPRESSION` | `PERFORMANCE_INITIATIVE_CANDIDATE` | Top-10 eligible funnel: 228 PC no-target, 59 PS zero-delta |
| `INITIAL_SIZING_TOO_SMALL_BY_AUTHORITY` | `INSUFFICIENT_EVIDENCE` | Median BUY_NEW quantity 100, but continuous-to-discrete conversion is explainable |
| `CAPITAL_FRAGMENTATION` | `PERFORMANCE_INITIATIVE_CANDIDATE` | Median 10 positions, median 7 one-lot positions, small ADD fills |
| `WINNER_CAPITALIZATION_LIMIT` | `PERFORMANCE_INITIATIVE_CANDIDATE` | 66 PM ADD -> 16 BUY_ADD fills, all one lot |
| `OVER_CONSERVATIVE_PC_COMPETITION` | `PERFORMANCE_INITIATIVE_CANDIDATE` | Cash final winner 51/76 days; ADD final winner 2/76 days |
| `RISK_PACING_INTENDED_SUPPRESSION` | `INTENDED_BEHAVIOR` | Risk Pacing is PC-consumed authority; no redecision evidence |
| `CASH_INTENDED` | `INTENDED_BEHAVIOR` | Cash optionality explicit; residual and cautious market reasons recorded |
| `LOT_OR_CAP_FEASIBILITY` | `INTENDED_BEHAVIOR` | PS lot conversion and one-lot feasibility are formal boundaries |
| `EARLY_REDUCE_EXIT` | `INSUFFICIENT_EVIDENCE` | REDUCE/EXIT frequent, but no defect shown without longer actual-path review |
| `REENTRY_OPPORTUNITY_LOSS` | `INSUFFICIENT_EVIDENCE` | Pre-L artifacts cannot accept/reject repaired current source |
| `CAMPAIGN_LIFECYCLE_DEFECT` | `NOT_REOPENED_IN_PHASE32_M` | Phase32-L repaired source; actual-path acceptance pending |
| `NO_SINGLE_STRUCTURAL_CAUSE` | `SUPPORTED` | Evidence indicates composed conservatism, not one isolated bug |
| `INSUFFICIENT_EVIDENCE` | `APPLIES_TO_LONG_HORIZON_PLATEAU_PROOF` | Current window rises; not a completed plateau reproduction |

## Composed Conservatism

Composed conservatism is present.

The current system can structurally plateau when several individually valid
decision-time controls stack:

1. BQ often reduces rather than fully authorizes candidates.
2. PC treats Cash/residual optionality as a first-class competitor.
3. PC final deployment cardinality is narrow in the observed artifacts
   (`0` or `1` deployment security/day).
4. PM ADD frequently emits winner continuation intent, but PC authorizes only a
   minority of positive ADD increments.
5. PS converts many positive continuous targets to zero or one-lot quantities.
6. REDUCE/EXIT risk controls can realize de-risking faster than staged ADD can
   recapitalize winners.
7. REENTRY actual repaired source still needs post-L evidence before opportunity
   recovery can be credited.

This is a plausible end-to-end plateau mechanism. It is not currently proven as
a correctness defect.

## Correctness Vs Performance

No remaining Phase32-M finding requires repair before integration acceptance,
based on the available evidence.

Correctness defects excluded or already addressed:

- G129 BUY_ADD semantics: not regressed by this audit; actual BUY_ADD fills are
  present and order-increment scoped.
- KI-006 Adaptive Buy Quality authority: not reopened; no BQ re-expansion
  defect was found in this audit.
- KI-004 Safety classification: current REENTRY rows separate Safety/Broker/CA
  from prior-context failure.
- Campaign/Re-entry provenance: Phase32-L source repair stands; this pre-L run
  is not valid acceptance evidence for that repair.

Performance initiative candidates requiring explicit user approval:

- Loosen or redesign BQ reduced/wait behavior.
- Increase PC deployment breadth or allow multi-allocation production binding.
- Rebalance Cash optionality vs security deployment.
- Make winner capitalization more aggressive.
- Revisit one-lot / minimum meaningful notional behavior.
- Revisit REDUCE/EXIT aggressiveness against longer holding objectives.

These are Strategy semantics and must not be smuggled into Phase32 correctness
repair.

## Additional Evidence / Retest Required

Recommended evidence before any performance initiative:

- A post-Phase32-L fresh Historical run long enough to observe campaign
  continuity and REENTRY acceptance on current source.
- At least 150-300 business days for plateau susceptibility, because the current
  75 completed valuation days show positive equity progression rather than a
  persistent plateau.
- Explicit decision-time funnel summaries per month:
  candidate -> BQ -> PC -> PS -> Runtime -> Pending -> Submit -> Fill.
- ADD cohort summaries by decision-time evidence class, not by future outcome.
- REDUCE/EXIT cohort summaries by decision-time reason class and holding age,
  not by later profitability.

Codex did not run fresh-run, resume, replay, or long Historical.

## What Must Not Change

The following must remain unchanged unless the user explicitly approves a new
performance initiative:

- Candidate selection
- Strategy parameters / thresholds / weights
- BUY/SELL/ADD thresholds
- Cash policy
- Risk Pacing
- Re-entry rules
- BUY_ADD / G129 semantics
- Phase32-L campaign identity and REENTRY provenance repair
- Accepted artifact / registry fail-closed behavior

## Final Judgment

1. `WHAT_CAN_CAUSE_LONG_HORIZON_EQUITY_PLATEAU_IN_THE_CURRENT_SYSTEM`

   A long-horizon plateau can be caused by composed conservatism: reduced BQ
   authorization, PC Cash optionality and narrow deployment selection, staged
   one-increment ADD authority, PS 100-share feasibility, small initial and ADD
   lot sizes, and active REDUCE/EXIT risk controls combining so that valid
   winners are retained but only slowly recapitalized.

2. `IS_ANY_REMAINING_CAUSE_A_CORRECTNESS_DEFECT`

   No concrete remaining correctness defect was reproduced in Phase32-M.
   Phase32-L still requires actual-path acceptance on a new run, but this audit
   does not identify a new repair requirement.

3. `IS_CAPITAL_TOO_FRAGMENTED_RELATIVE_TO_VALID_EXISTING_OPPORTUNITIES`

   `UNCONFIRMED` as a correctness claim. Structurally, capital is susceptible to
   fragmentation: median 10 open positions, median 7 one-lot positions, and
   small ADD fills. But top-name concentration is also meaningful, and deciding
   that this is "too fragmented" is a Strategy/performance judgment requiring
   user approval.

4. `ARE_WINNERS_BEING_UNDERCAPITALIZED_BY_ARCHITECTURE_OR_BY_VALID_DECISION_TIME_EVIDENCE`

   Winners are capitalized conservatively by accepted architecture and
   decision-time evidence. PM ADD appears 66 times, while only 16 BUY_ADD fills
   occur, all one-lot. The dominant stop is PC no positive ADD increment, not a
   Runtime regression. Treat undercapitalization as a performance initiative
   candidate, not a correctness defect.

5. `ARE_ENTRY_OR_EXIT_RULES_SYSTEMATICALLY_SUPPRESSING_LONG_TERM_GROWTH`

   `INSUFFICIENT_EVIDENCE` for systematic long-term suppression. Entry funnel
   suppression is clearly present, and REDUCE/EXIT are frequent, but this run's
   completed valuation period rises materially and is too short to prove a
   long-horizon plateau mechanism as a defect.

6. `IS_COMPOSED_CONSERVATISM_PRESENT`

   Yes. It is the primary supported plateau susceptibility mechanism.

7. `WHICH_FINDINGS_REQUIRE_REPAIR_AND_WHICH_REQUIRE_USER_APPROVAL_AS_NEW_PERFORMANCE_INITIATIVES`

   Repair required before Phase32 integration acceptance: `NO`, from Phase32-M
   evidence. User-approval performance initiatives: BQ aggressiveness, PC
   deployment breadth, Cash optionality balance, winner capitalization/ADD
   aggressiveness, discrete sizing/minimum notional behavior, and REDUCE/EXIT
   retention posture.

Final classification:

`PHASE32_M_NO_NEW_CORRECTNESS_REPAIR_REQUIRED_COMPOSED_CONSERVATISM_IDENTIFIED`
