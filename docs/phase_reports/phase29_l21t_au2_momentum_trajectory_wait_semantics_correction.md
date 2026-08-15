# Phase29-L21T-AU2 - Momentum Trajectory WAIT Semantics Correction

## Primary Judgment

`BUY_WAIT_TEMPORARY_BUY_INELIGIBLE_SEMANTICS_SELECTED`

This is a design/document correction only. Phase30 was not entered. No
Strategy, Runtime, Config, Model, Threshold, Pending, Ledger, Current, 4-year
run, fresh-run, resume, replay, recovery, or long Historical operation was
changed or executed.

## Correction

AU incorrectly used `BUY_REVIEW_REQUIRED` as shorthand for "wait". That is not
the desired semantics for `FADING_PRIOR_WINNER` or
`RECENT_ACCELERATION_OVERHEAT`.

Corrected semantic:

```text
BUY_WAIT
alias: TEMPORARY_BUY_INELIGIBLE
```

Meaning:

- do not generate `BUY_NEW` order
- do not generate BUY Pending item
- do not generate Human Review Pending
- do not halt Runtime
- do not block SELL Planning
- do not change HOLD / ADD / REDUCE / EXIT authority for existing holdings
- reevaluate normally on the next business date from PIT features
- if the symbol returns to `HEALTHY_CONTINUATION`, BUY_NEW eligibility can
  return

## Existing Contract Check

| Question | Finding |
| --- | --- |
| Existing exact BUY wait action exists? | `NO`; Adaptive BUY Quality currently defines full, reduced, review, reject. |
| Existing downstream temporary ineligible vocabulary exists? | `PARTIAL`; some Runtime authority checks recognize `NO_BUY` / `INELIGIBLE`, but these are not current Adaptive BUY Quality canonical actions. |
| Pending can be avoided by zero BUY_NEW allocation? | `YES_DESIGN`; PC/Position Sizing already turn non-submittable quality actions into zero new allocation. Implementation must map `BUY_WAIT` to zero BUY_NEW allocation without review pending. |
| SELL independence preserved? | `YES_DESIGN`; trajectory wait is BUY_NEW-scoped and must not alter SELL Planning, PM, or existing holding authority. |
| Next-day reevaluation possible? | `YES`; classification is PIT feature based and not a persistent rejection. |
| BUY_ADD affected? | `NO`; AU2 keeps the component critical for `BUY_NEW` only. |
| REENTRY affected? | `NO` by default; any REENTRY application requires separate design. |

## Selected Canonical Semantics

`BUY_WAIT` is the selected Adaptive BUY Quality action name for this design.
`TEMPORARY_BUY_INELIGIBLE` is the explicit semantic alias for observability and
reason codes.

The action should be materialized in Buy Quality as:

```text
quality_action = BUY_WAIT
quality_status = PASS
quality_allocation_adjustment = 0.0
momentum_trajectory_action = TEMPORARY_BUY_INELIGIBLE
```

The exact `quality_status` can be finalized in implementation, but it must not
be Runtime/Human `REVIEW_REQUIRED` solely because of fading or overheat
trajectory. If existing schema compatibility requires a transitional status,
the implementation must keep the effect scoped to BUY_NEW zero allocation and
must not create review Pending or block SELL.

## Corrected Treatment

| Classification | Corrected default treatment |
| --- | --- |
| `HEALTHY_CONTINUATION` | eligible under existing BQ/PC/Safety authority |
| `FADING_PRIOR_WINNER` | `BUY_WAIT` / `TEMPORARY_BUY_INELIGIBLE` |
| `RECENT_ACCELERATION_OVERHEAT` | `BUY_WAIT` / `TEMPORARY_BUY_INELIGIBLE` |
| `MIXED_OR_UNRESOLVED` | conservative reduction or `BUY_WAIT`; missing required evidence should be BUY-only fail-closed where possible |

## Missing Feature Semantics

Required trajectory feature missing should also avoid Human Review Pending when
the existing implementation path can express BUY-only fail-closed behavior.

Selected design:

- missing required trajectory feature -> `BUY_WAIT` /
  `TEMPORARY_BUY_INELIGIBLE` for BUY_NEW
- no BUY_NEW Pending item
- no Runtime halt
- SELL Planning continues if SELL inputs are valid

If an existing contract classifies a structural artifact failure as
`REVIEW_REQUIRED`, the review must be scoped to BUY admission and must not block
SELL continuation. The implementation task must include regression coverage for
this distinction.

## AU Design Preserved

Unchanged:

- Technical Features own raw multi-horizon facts.
- Buy Quality owns trajectory classification authority.
- PC does not recompute trajectory classification.
- Production-common 1BD / 3BD / 5BD / 20BD feature design remains.
- `HEALTHY_CONTINUATION`, `FADING_PRIOR_WINNER`,
  `RECENT_ACCELERATION_OVERHEAT`, and `MIXED_OR_UNRESOLVED` remain.
- threshold tuning remains prohibited.
- Historical-only logic remains prohibited.
- `score <= 0` absolute gate remains prohibited.
- existing holdings are not automatically sold.

## Implementation Implication

The next implementation task must add `BUY_WAIT` as a non-submittable,
non-review, BUY_NEW-scoped quality action. It should be consumed by PC and
Position Sizing as zero new BUY allocation and by Runtime Planning as "no BUY
item materialized for this symbol/date".

Regression must prove:

- `FADING_PRIOR_WINNER` creates no BUY Pending and no Human Review Pending.
- `RECENT_ACCELERATION_OVERHEAT` creates no BUY Pending and no Human Review
  Pending.
- SELL Planning still creates executable SELL items when SELL authority says so.
- Next-day PIT reclassification can return the symbol to BUY eligibility.
- BUY_ADD / REENTRY / existing holding PM behavior are unaffected.

## Validation

| Check | Result |
| --- | --- |
| Markdown consistency | `PASS` |
| Runtime mutation | `NO` |
| Strategy changed | `NO` |
| Phase30 entered | `NO` |
