# Phase29-L21T-AT - Multi-Horizon Momentum Authority / Trajectory Audit

## Primary Judgment

`MULTI_HORIZON_MOMENTUM_AUTHORITY_GAP_CONFIRMED`

Secondary judgments:

- `SHORT_TERM_DETERIORATION_SIGNAL_PRESENT_BUT_NOT_EXPLICIT_BUY_NEW_AUTHORITY`
- `OVERHEAT_ACCELERATION_DETECTION_ABSENT_CONFIRMED`
- `20BD_LONG_MOMENTUM_INFLUENCE_CONFIRMED_BUT_NOT_SOLE_AUTHORITY`

This was a read-only Phase29 audit. Phase30 was not entered. No Strategy,
Runtime, Config, Model, Threshold, Pending, Ledger, Current, replay, recovery,
resume, fresh-run, or long Historical operation was performed.

## Scope

| Field | Value |
| --- | --- |
| Task ID | `Phase29-L21T-AT` |
| Target Run | `runtime-test-historical-extended-smoke-20260814T054658313415Z` |
| Sample | `72` filled actual `BUY_NEW` entries from the AS artifact |
| Runtime mutation | `NO` |
| Strategy changed | `NO` |

## Feature Availability

| Horizon / signal | Canonical field found | Candidate feature | Opportunity feature | Buy Quality direct use | Portfolio Construction direct use | Explicit BUY_NEW gate |
| --- | --- | --- | --- | --- | --- | --- |
| 1BD return | none | `NO` | `NO` | `NO` | `NO` | `NO` |
| 3BD return | none | `NO` | `NO` | `NO` | `NO` | `NO` |
| 5BD return | `price_momentum_return_5d` | `YES` | `YES` | `NO` | `NO_EXPLICIT_BUY_NEW_GATE` | `NO` |
| 10BD return | none | `NO` | `NO` | `NO` | `NO` | `NO` |
| 20BD return | `price_momentum_return_20d` | `YES` | `YES` | `NO` | `YES_SOURCE_OBSERVABILITY/REENTRY` | `NO` |
| 60BD return | `price_momentum_return_60d` | `YES` | `YES` | `NO` | not observed as BUY_NEW gate | `NO` |
| trend | `trend_close_over_ma_20d`, `trend_ma_5_20_ratio`, `trend_ma_20_60_ratio` | `YES` | `YES` | `NO` | partial source/reentry evidence | `NO` |
| volume momentum | `volume_momentum_ratio_5d`, `volume_momentum_ratio_1d_20d` | `YES` | `YES` | `NO` | not observed as BUY_NEW gate | `NO` |
| volatility | `volatility_return_std_20d` | `YES` | `YES` | execution feasibility context only | not observed as BUY_NEW gate | `NO` |
| ATR | none observed | `NO` | `NO` | `NO` | `NO` | `NO` |
| gap / fill acceleration | none pre-BUY | `NO` | `NO` | `NO` | `NO` | `NO` |
| acceleration / slope classification | none observed | `NO` | `NO` | `NO` | `NO` | `NO` |

The technical feature producer and Runtime feature artifacts can express 5BD
and 20BD momentum, plus longer 60BD and trend/volume/volatility fields. The
current BUY authority does not expose 1BD, 3BD, or 10BD price-return features,
and it does not materialize a semantic classifier for either:

- `FADING_PRIOR_WINNER`: 20BD positive while 5BD/3BD/1BD are negative.
- `RECENT_ACCELERATION_OVERHEAT`: long and short momentum positive, but the
  latest move or entry gap is extreme.

## Authority Lineage

Candidate AI reads `candidate_features.parquet` and emits
`candidate_decisions.json`. Opportunity AI reads `candidate_decisions.json` and
`opportunity_feature_input.parquet`, then emits `opportunity_rankings.json`.
Buy Quality then evaluates Opportunity score/rank, signal reliability,
execution feasibility, market context, and portfolio fit. It does not directly
consume 1BD/3BD/5BD/10BD/20BD return fields as explicit BUY_NEW momentum
authority.

Portfolio Construction receives Opportunity and Buy Quality authority. For the
audited anchor BUY_NEW rows, `price_momentum_return_20d` is observable in PC
members, but `price_momentum_return_5d` is not present as a direct PC member
field and no short-term deterioration gate is applied. PC accepts the row when
rank/quality/sizing/lot/safety authorities pass.

## Anchor Trace

### 78780 / 2022-08-24

Classification: `OTHER` with long-lookback winner and 1BD reversal.

| Field | Value |
| --- | ---: |
| pre 1BD / 3BD / 5BD / 10BD / 20BD | `-15.753% / +4.423% / +42.984% / +81.273% / +228.002%` |
| candidate feature 5BD / 20BD / 60BD | `+42.984% / +228.002% / +258.784%` |
| candidate rank / score | `5 / 0.79837418` |
| candidate reason | `high_candidate_score|price_momentum_positive|long_momentum_positive|volume_momentum_positive|liquidity_available` |
| opportunity rank / score | `3 / 0.04370588` |
| Buy Quality | `PASS`, `FULL_ALLOCATION_ELIGIBLE` |
| PC requested / lot-aware target weight | `2.5641% / 24.3762%` |
| short-term deterioration detection | `NO` |
| overheat detection | `NO` |

BUY_NEW remained eligible because Candidate/Opportunity/Buy Quality/PC
authorities passed. The 1BD reversal was available only in this audit's
post-hoc price trajectory, not as a runtime BUY_NEW gate.

### 78780 / 2022-08-31

Classification: `FADING_PRIOR_WINNER`.

| Field | Value |
| --- | ---: |
| pre 1BD / 3BD / 5BD / 10BD / 20BD | `-8.141% / -23.770% / -5.579% / +35.007% / +135.567%` |
| candidate feature 5BD / 20BD / 60BD | `-5.579% / +135.567% / +225.731%` |
| candidate rank / score | `7 / 0.77929277` |
| candidate reason | `high_candidate_score|price_momentum_positive|long_momentum_positive|liquidity_available` |
| opportunity rank / score | `6 / -0.05964049` |
| opportunity no-buy reason | `non_positive_expected_edge_score` |
| Buy Quality | `PASS`, `FULL_ALLOCATION_ELIGIBLE` |
| PC requested / lot-aware target weight | `2.5641% / 23.6376%` |
| short-term deterioration detection | `NO_EXPLICIT_AUTHORITY` |
| overheat detection | `NO` |

Although 5BD was negative in the feature artifact and Opportunity score was
negative, the score semantics were uncalibrated relative score; Buy Quality
recorded `uncalibrated_relative_score_non_positive_not_economic_gate`, so this
did not block BUY_NEW. There is no explicit authority that says "20BD prior
winner is fading across 5BD/3BD/1BD; review or reject."

### 53800 / 2022-09-06

Classification: `FADING_PRIOR_WINNER`.

| Field | Value |
| --- | ---: |
| pre 1BD / 3BD / 5BD / 10BD / 20BD | `-11.111% / -20.000% / -29.861% / -23.048% / +87.037%` |
| candidate feature 5BD / 20BD / 60BD | `-29.861% / +87.037% / +100.795%` |
| candidate rank / score | `6 / 0.75102809` |
| candidate reason | `high_candidate_score|price_momentum_positive|long_momentum_positive|liquidity_available` |
| opportunity rank / score | `7 / -0.07980215` |
| opportunity no-buy reason | `non_positive_expected_edge_score` |
| Buy Quality | `PASS`, `FULL_ALLOCATION_ELIGIBLE` |
| PC requested / lot-aware target weight | `2.3256% / 21.4606%` |
| short-term deterioration detection | `NO_EXPLICIT_AUTHORITY` |
| overheat detection | `NO` |

This is the clearest anchor for the authority gap: 5BD deterioration was
present in Candidate and Opportunity feature artifacts, while 1BD/3BD/10BD were
not canonical runtime features. The downstream BUY_NEW authority did not turn
that deterioration into an explicit block, review, or allocation penalty.

## Run-Wide Diagnostic Classification

The classification is descriptive only; it is not a proposed production
threshold. It uses AS per-entry pre-return fields and same-sample distribution
for 1BD/gap overheat evidence.

| Classification | Sample | Avg 1BD | Avg 3BD | Avg 5BD | Avg 20BD | Avg gap | Avg holding days | Exit <=1BD | Exit <=3BD | Avg realized | Avg fwd 20BD |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `FADING_PRIOR_WINNER` | `17` | `-3.726%` | `-7.300%` | `-11.121%` | `+32.825%` | `-0.685%` | `3.00` | `47.059%` | `58.824%` | `-5.358%` | `-8.354%` |
| `RECENT_ACCELERATION_OVERHEAT` | `14` | `+15.707%` | `+25.260%` | `+29.688%` | `+49.711%` | `+9.380%` | `3.93` | `28.571%` | `57.143%` | `-5.198%` | `-13.815%` |
| `HEALTHY_CONTINUATION` | `3` | `+1.095%` | `+2.066%` | `+2.506%` | `+28.649%` | `-0.575%` | `13.00` | `0.000%` | `0.000%` | `+6.876%` | `-1.626%` |
| `OTHER` | `38` | `+2.731%` | `+2.189%` | `+1.460%` | `+8.075%` | `+2.806%` | `2.93` | `28.947%` | `52.632%` | `-2.758%` | `-2.983%` |

This supports two separate weaknesses:

- Fading prior winners are identifiable with post-hoc 1BD/3BD/5BD/20BD data,
  but the current runtime only has canonical 5BD/20BD and no semantic
  deterioration authority.
- Recent acceleration / overheat is also identifiable post-hoc, especially
  using entry gap and 1BD/gap distribution, but gap is not a pre-BUY runtime
  authority and no overheat classifier exists.

## Root Cause

The root cause is not simply that all short-term information is missing. The
5BD return exists and reaches Candidate and Opportunity feature inputs. The gap
is that short-horizon deterioration and acceleration are not represented as a
transparent BUY_NEW authority contract after model scoring.

Detailed gap separation:

- Feature gap: `YES` for 1BD, 3BD, 10BD, ATR, gap/acceleration classifier.
- Propagation gap: `PARTIAL`; 5BD reaches Candidate/Opportunity, but not as
  explicit Buy Quality or PC BUY_NEW authority.
- Scoring gap: `YES`; Candidate/Opportunity model influence is opaque and can
  emit positive candidate strength despite negative 5BD with strong 20BD/60BD.
- Buy Quality gap: `YES`; non-positive uncalibrated Opportunity scores are not
  economic gates, and Buy Quality does not apply a multi-horizon deterioration
  or overheat penalty.

## Artifacts

- `reports/phase29_l21t_at_multi_horizon_momentum_authority_trajectory_audit/summary.json`
- `reports/phase29_l21t_at_multi_horizon_momentum_authority_trajectory_audit/per_entry.csv`
- `reports/phase29_l21t_at_multi_horizon_momentum_authority_trajectory_audit/group_summary.csv`
- `reports/phase29_l21t_at_multi_horizon_momentum_authority_trajectory_audit/authority_matrix.csv`
- `reports/phase29_l21t_at_multi_horizon_momentum_authority_trajectory_audit/anchor_trace.csv`

## Validation

| Check | Result |
| --- | --- |
| Read-only audit | `PASS` |
| `summary.json` parse | `PASS` |
| Artifact consistency | `PASS` |
| Runtime mutation | `NO` |
| Strategy changed | `NO` |
| Phase30 entered | `NO` |
| `git diff --check` | `PASS` |

## Next Step

Create a separate design task for a production-common multi-horizon momentum
semantics contract. The design should decide whether 1BD/3BD/10BD, acceleration
or gap/ATR-normalized movement, and an explicit fading-prior-winner / overheat
classifier belong in Candidate features, Opportunity semantics, Buy Quality, or
Portfolio Construction. This task should not tune thresholds from the 72-entry
sample alone.
