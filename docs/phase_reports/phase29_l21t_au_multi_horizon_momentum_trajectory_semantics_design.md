# Phase29-L21T-AU - Multi-Horizon Momentum Trajectory Semantics Design

## Primary Judgment

`MULTI_HORIZON_MOMENTUM_TRAJECTORY_SEMANTICS_DESIGN_READY`

This is a design-only Phase29 continuation. Phase30 was not entered. No
Strategy, Runtime, Config, Model, Threshold, Pending, Ledger, Current, 4-year
run, fresh-run, resume, replay, recovery, or long Historical operation was
changed or executed.

## Selected Design

Add a Production-common `Momentum Trajectory Quality` extension to Adaptive BUY
Quality for `BUY_NEW` admission quality. Technical Features own raw
multi-horizon facts. Candidate and Opportunity may consume the raw fields for
ranking, but the explicit semantic classification is owned by Buy Quality.
Portfolio Construction only consumes the Buy Quality decision and must not
duplicate trajectory logic.

Phase29-L21T-AU2 correction: the trajectory component must not use
`BUY_REVIEW_REQUIRED` to mean "wait". Fading / overheat trajectory findings are
not intended to create Human Review Pending, Runtime halt, or SELL blockage.
The selected BUY-only wait semantic is:

```text
BUY_WAIT
alias: TEMPORARY_BUY_INELIGIBLE
```

`BUY_WAIT` means no `BUY_NEW` order, no BUY Pending item, no Human Review
Pending, and normal PIT reevaluation on the next business date.

The design is intentionally not a simple "ban fast-rising stocks" rule. It
separates:

- `HEALTHY_CONTINUATION`
- `FADING_PRIOR_WINNER`
- `RECENT_ACCELERATION_OVERHEAT`
- `MIXED_OR_UNRESOLVED`

## Required Features

### Reuse Existing Features

| Field | Use |
| --- | --- |
| `price_momentum_return_5d` | short-horizon continuation / deterioration |
| `price_momentum_return_20d` | medium lookback trend strength |
| `price_momentum_return_60d` | long-lookback prior-winner context |
| `trend_close_over_ma_20d` | trend quality / trend break evidence |
| `trend_ma_5_20_ratio` | trend slope proxy |
| `trend_ma_20_60_ratio` | medium vs long trend context |
| `volume_momentum_ratio_5d` | confirmation / exhaustion context |
| `volume_momentum_ratio_1d_20d` | recent volume spike context |
| `volatility_return_std_20d` | normalization base for recent moves |

### Add Production-Common Features

| New field | Formula concept | Owner |
| --- | --- | --- |
| `price_momentum_return_1d` | close_t / close_t_minus_1 - 1 | Technical Features |
| `price_momentum_return_3d` | close_t / close_t_minus_3 - 1 | Technical Features |
| `price_momentum_return_10d` | close_t / close_t_minus_10 - 1 | Technical Features |
| `recent_move_volatility_z_1d` | 1BD return / 20BD return volatility | Technical Features |
| `recent_move_volatility_z_3d` | 3BD return / scaled 20BD return volatility | Technical Features |
| `momentum_5d_vs_20d_delta` | 5BD return minus normalized 20BD context | Technical Features |
| `momentum_1d_vs_5d_delta` | 1BD return minus normalized 5BD pace | Technical Features |
| `gap_prev_close_to_reference` | reference/open planning gap when a PIT reference is available before BUY materialization | Technical Features or Execution Feasibility Evidence |
| `gap_volatility_z` | gap normalized by recent volatility | Technical Features or Execution Feasibility Evidence |

These are raw facts, not gates. All formulas must be PIT-only and common across
Production, Demo, and Historical. If a production-time gap reference is not
available before BUY planning, the field must be absent with explicit
`NOT_AVAILABLE`, not backfilled from fill evidence.

## Trajectory Classes

The class definitions below are semantic contracts, not tuned numeric
thresholds.

### HEALTHY_CONTINUATION

Meaning:

- medium/long trend is positive enough to support a continuation thesis
- 1BD/3BD/5BD do not show clear reversal
- recent move is not abnormally concentrated into the latest bar or gap
- volatility and volume evidence do not indicate an unresolved blow-off move

BUY_NEW treatment:

- no automatic rejection
- no automatic boost above existing quality
- eligible for existing Buy Quality scoring
- may receive a small reliability support flag only if all required evidence is
  present and coherent

### FADING_PRIOR_WINNER

Meaning:

- 20BD/60BD or trend context remains strong
- 1BD/3BD/5BD show deterioration, reversal, or trend-quality conflict
- the row is a prior winner whose latest short-horizon facts no longer support
  immediate BUY_NEW

BUY_NEW treatment:

- default action: `BUY_WAIT` / `TEMPORARY_BUY_INELIGIBLE`
- permitted alternative in later policy design: `BUY_REDUCED_ALLOCATION` only
  when the deterioration is mild and other reliability evidence is strong
- not a hard permanent reject; the symbol can become eligible again after
  fresh PIT features reclassify it
- no Human Review Pending is generated solely from this trajectory class
- SELL / REDUCE / EXIT authority remains independent and must not be blocked

Rationale:

AT found `17` diagnostic `FADING_PRIOR_WINNER` filled BUY_NEW entries with
average 20BD forward return `-8.354%`. The issue is late entry into a prior
winner, not that historical winners are always bad.

### RECENT_ACCELERATION_OVERHEAT

Meaning:

- trend can still be strong
- 1BD/3BD return, gap, or volatility-adjusted move indicates the latest entry
  point may be dominated by a short-lived acceleration
- volume spike can confirm that the move requires review, but must not be the
  sole cause unless explicitly designed later

BUY_NEW treatment:

- default action: `BUY_WAIT` / `TEMPORARY_BUY_INELIGIBLE`, especially when the
  overheat evidence depends on a gap or volatility-normalized move
- permitted alternative in later policy design: stronger allocation reduction
  than fading-prior-winner when the trajectory is still otherwise healthy
- not a blanket "acute momentum ban"; healthy continuation must remain eligible
- no Human Review Pending is generated solely from this trajectory class
- SELL / REDUCE / EXIT authority remains independent and must not be blocked

Rationale:

AT found `14` diagnostic `RECENT_ACCELERATION_OVERHEAT` filled BUY_NEW entries
with average 20BD forward return `-13.815%`. AS also showed high entry-gap
entries had weaker forward return and higher short-exit rates.

### MIXED_OR_UNRESOLVED

Meaning:

- raw features are contradictory, missing non-critical context, or do not fit a
  clean semantic class

BUY_NEW treatment:

- does not automatically reject
- may reduce the `momentum_trajectory_quality` component score
- if required trajectory inputs are missing or stale, BUY_NEW should become
  `BUY_WAIT` / `TEMPORARY_BUY_INELIGIBLE` when the existing contract allows a
  BUY-only fail-closed result. If the missing input is a structural artifact
  authority failure that existing contracts require to be `REVIEW_REQUIRED`,
  the design must keep the review scoped to BUY admission and must not block
  SELL Planning.

## Authority Owner

| Layer | Responsibility |
| --- | --- |
| Technical Features | Produce PIT raw fields, missingness, temporal evidence, source hashes |
| Candidate AI | May consume raw fields for model score/rank; must not be sole semantic owner |
| Opportunity AI | May consume raw fields for ranking; must preserve score semantics |
| Buy Quality | Owns trajectory classification and action effect for BUY_NEW |
| Portfolio Construction | Consumes Buy Quality action/adjustment; no duplicated trajectory logic |
| Position Sizing | Applies Buy Quality allocation adjustment; no trajectory recomputation |
| Runtime Planning / Submit / Execution | Preserve existing authority chain; no restore or hidden override |

## Buy Quality Integration

Add a sixth component:

```text
momentum_trajectory_quality
```

The component emits:

```text
trajectory_classification
trajectory_status
trajectory_action
trajectory_reason_codes
trajectory_feature_snapshot
trajectory_authority
```

Recommended component behavior:

| Classification | Component status | Quality action effect |
| --- | --- | --- |
| `HEALTHY_CONTINUATION` | `PASS` | no penalty; existing BQ action can proceed |
| `FADING_PRIOR_WINNER` | `BUY_WAIT` or `PASS_WITH_REDUCTION` | wait by default; reduced allocation only if later policy permits |
| `RECENT_ACCELERATION_OVERHEAT` | `BUY_WAIT` or `PASS_WITH_REDUCTION` | wait by default; stronger reduction may be permitted later |
| `MIXED_OR_UNRESOLVED` | `PASS_WITH_REDUCTION` or `BUY_WAIT` | conservative score; BUY-only fail closed if required evidence missing |

This component should be critical for `BUY_NEW` only. `BUY_WAIT` maps to zero
new BUY allocation and no BUY Pending item for the current business date. It
must not create Human Review Pending, Runtime halt, or automatically force or
block SELL/EXIT/REDUCE for existing holdings. Existing PM and SELL authorities
remain independent.

No raw `runtime_opportunity_score <= 0` absolute gate is reintroduced. A
negative uncalibrated score can remain relative evidence, but it cannot rescue a
bad trajectory or hide a trajectory `BUY_WAIT`.

## Missing Feature Semantics

Required for trajectory classification:

```text
price_momentum_return_1d
price_momentum_return_3d
price_momentum_return_5d
price_momentum_return_20d
volatility_return_std_20d
trend_close_over_ma_20d
```

Optional but recommended:

```text
price_momentum_return_10d
price_momentum_return_60d
trend_ma_5_20_ratio
trend_ma_20_60_ratio
volume_momentum_ratio_5d
volume_momentum_ratio_1d_20d
gap_prev_close_to_reference
gap_volatility_z
```

Fail-closed rules:

- missing required fields: `BUY_WAIT` / `TEMPORARY_BUY_INELIGIBLE` when scoped
  BUY-only fail-closed is available; otherwise BUY-scoped `REVIEW_REQUIRED`
  without SELL blockage
- non-finite required fields: `BUY_WAIT` / `TEMPORARY_BUY_INELIGIBLE` when
  scoped BUY-only fail-closed is available; otherwise BUY-scoped
  `REVIEW_REQUIRED` without SELL blockage
- future-dated or stale feature row: `BUY_WAIT` / `TEMPORARY_BUY_INELIGIBLE`
  when scoped BUY-only fail-closed is available; otherwise BUY-scoped
  `REVIEW_REQUIRED` without SELL blockage
- gap not available before planning: classify with `gap_status=NOT_AVAILABLE`
  and do not infer from execution fill
- optional missing evidence: explicit reason code and conservative component
  score, not silent neutral evidence

## Observability Fields

Buy Quality decisions must expose:

```text
momentum_trajectory_schema_version
momentum_trajectory_classification
momentum_trajectory_status
momentum_trajectory_action
momentum_trajectory_component_score
momentum_trajectory_reason_codes
momentum_trajectory_required_features
momentum_trajectory_missing_features
momentum_trajectory_optional_features
momentum_trajectory_feature_snapshot
momentum_trajectory_source_artifact_path
momentum_trajectory_source_artifact_hash
momentum_trajectory_temporal_validation_status
momentum_trajectory_pit_status
```

Portfolio Construction and Runtime Planning should copy the classification,
status, action, and authority hash as observability fields only. They must not
recompute class membership.

## Treatment Comparison

| Treatment | FADING_PRIOR_WINNER | RECENT_ACCELERATION_OVERHEAT | Notes |
| --- | --- | --- | --- |
| hard reject | not selected for AU default | not selected for AU default | too blunt; could reject legitimate pullback/continuation |
| reduced allocation | allowed as later policy option | allowed as later policy option | requires design-time policy, not 72-sample tuning |
| Human Review Pending | not selected | not selected | wrong semantics for temporary trajectory wait |
| BUY wait | selected default | selected default | no Pending, no Runtime halt, next-day reevaluation |
| quality penalty | selected as component behavior | selected as component behavior | transparent and BQ-owned |

Selected AU design:

```text
FADING_PRIOR_WINNER -> BUY_WAIT / TEMPORARY_BUY_INELIGIBLE by default, reduced allocation only by later explicit policy
RECENT_ACCELERATION_OVERHEAT -> BUY_WAIT / TEMPORARY_BUY_INELIGIBLE by default, reduced allocation only by later explicit policy
HEALTHY_CONTINUATION -> eligible under existing BQ/PC/Safety authority
```

## Existing Holdings Boundary

The design applies to `BUY_NEW` admission quality. It does not change:

- HOLD / ADD / REDUCE / EXIT thresholds
- PM hard-stop behavior
- SELL Planning independence
- Winner HOLD semantics
- Re-entry guard
- Safety hard maximums

If the same raw trajectory facts are later useful for ADD, REDUCE, or EXIT,
that must be a separate design with PM authority reviewed explicitly.

## Implementation Scope

Minimum implementation task:

1. Extend Production-common technical features with 1BD/3BD/10BD and
   volatility-normalized recent move facts.
2. Add feature schema and consumer readiness validation for Candidate and
   Opportunity feature artifacts.
3. Extend Buy Quality with `momentum_trajectory_quality`.
4. Add `BUY_WAIT` as a BUY Quality action aliasing
   `TEMPORARY_BUY_INELIGIBLE`; map it to zero BUY_NEW allocation and no BUY
   Pending generation for that symbol/date.
5. Wire BQ observability into PC, Position Sizing, Runtime Planning, Pending,
   and Submit evidence as copies only.
6. Keep PC free of duplicated classification logic.
7. Preserve Production/Demo/Historical common path.

Out of scope for first implementation:

- threshold tuning
- model retraining
- fresh 4-year Historical run
- SELL/PM behavior changes
- score <= 0 absolute Opportunity gate

## Focused Regression Scope

Required focused tests:

- Technical feature producer: 1BD/3BD/10BD formulas, PIT-only, missing data,
  duplicate rows, insufficient observations.
- Candidate/Opportunity consumer readiness: schema additions accepted, stale or
  missing required fields fail closed.
- Buy Quality:
  - `HEALTHY_CONTINUATION` remains eligible.
  - `FADING_PRIOR_WINNER` becomes `BUY_WAIT` by default.
  - `RECENT_ACCELERATION_OVERHEAT` becomes `BUY_WAIT` by default.
  - missing required trajectory feature fails closed for BUY_NEW without
    creating Human Review Pending when scoped BUY-only fail-closed is available.
  - optional gap unavailable does not use fill evidence.
- Portfolio Construction: consumes BQ decision and does not recompute
  classification.
- Position Sizing: applies BQ allocation adjustment only.
- Runtime Planning / Pending / Submit: preserves evidence, creates no BUY_NEW
  Pending item for `BUY_WAIT`, and keeps SELL continuation independent.
- BUY/SELL independence and L21T-M SELL continuation regression.
- Re-entry guard regression.
- one-lot authority regression.
- `BUY_ADD`, `REENTRY`, `SELL`, `REDUCE`, `EXIT` unaffected regression.
- `py_compile`.
- `git diff --check`.

## Safety Constraints

Preserved:

- Historical-only Strategy: `NO`
- Production/Demo/Historical common contract: `YES`
- future data: `NO`
- score <= 0 absolute gate: `NO`
- SELL independence: `YES`
- Safety fail-closed: `YES`
- Re-entry guard: `UNCHANGED`
- Existing holdings SELL/PM authority: `UNCHANGED`

## Implementation Readiness

The design is ready for a separate implementation task. It deliberately does
not pick hard numeric thresholds from the AT/AS 72-entry sample. The next task
should implement the authority skeleton, feature propagation, and regression
fixtures with symbolic/descriptive cases first, then require a separate
calibration/research task before any threshold tuning.
