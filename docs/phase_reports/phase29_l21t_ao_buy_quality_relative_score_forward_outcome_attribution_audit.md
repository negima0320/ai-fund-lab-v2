# Phase29-L21T-AO - Buy Quality x Relative Opportunity Score Forward Outcome Attribution Audit

## Primary Judgment

`PHASE29_L21T_AO_BUY_QUALITY_RELATIVE_SCORE_FORWARD_OUTCOME_ATTRIBUTION_READ_ONLY_AUDIT_COMPLETE_INSUFFICIENT_FOR_IMMEDIATE_GATE_CHANGE`

This is a read-only Phase29 audit.  Phase30 is not entered.

## Scope

| Field | Value |
| --- | --- |
| Task ID | `Phase29-L21T-AO` |
| Target run | `runtime-test-historical-extended-smoke-20260814T054658313415Z` |
| Current Phase | `Phase29` |
| Codex runtime mutation | `NO` |
| Codex fresh-run / resume / replay / recovery / long Historical | `NO` |
| Strategy / Runtime / Config / Model / Threshold changed | `NO` |
| Future return used by Runtime | `NO` |
| Historical-only branch added | `NO` |

Read-only snapshot used by the audit script:

| Field | Value |
| --- | --- |
| run_state status | `RUNNING` |
| completed business days | `55` |
| completed range | `2022-08-10` through `2022-10-31` |
| next job snapshot | `2022-11-01:morning` |

Forward returns use J-Quants adjusted close (`AdjC`) as post-hoc audit evidence
only.  Horizons are `1BD`, `5BD`, `10BD`, and `20BD`.

## Artifacts

```text
scripts/audits/phase29_l21t_ao_buy_quality_relative_score_forward_outcome_audit.py
tests/audits/test_phase29_l21t_ao_buy_quality_relative_score_forward_outcome_audit.py
reports/phase29_l21t_ao_buy_quality_relative_score_forward_outcome_attribution_audit/summary.json
reports/phase29_l21t_ao_buy_quality_relative_score_forward_outcome_attribution_audit/per_entry.csv
reports/phase29_l21t_ao_buy_quality_relative_score_forward_outcome_attribution_audit/group_summary.csv
reports/phase29_l21t_ao_buy_quality_relative_score_forward_outcome_attribution_audit/anchor_2022_08_10.csv
```

The script is intentionally import-isolated from runtime package code and only
reads already-materialized evidence plus adjusted daily bars.

## 2022-08-10 Anchor

Actual `BUY_NEW` count was `11`.

| Group | Count |
| --- | ---: |
| `FULL_ALLOCATION_ELIGIBLE` | `4` |
| `REDUCED_ALLOCATION_ONLY` | `7` |
| FULL x negative runtime score | `4` |
| REDUCED x negative runtime score | `6` |

Actual symbols:

```text
23230, 23700, 23880, 30100, 36640, 66590, 76470, 89180, 93180, 94320, 94340
```

Notional-held-constant counterfactual for the anchor:

| Portfolio | 1BD | 5BD | 10BD | 20BD |
| --- | ---: | ---: | ---: | ---: |
| Actual 11 names | `+0.365%` | `+0.577%` | `+0.234%` | `+0.295%` |
| FULL only | `+3.456%` | `+1.603%` | `+0.191%` | `+4.173%` |
| Exclude REDUCED x negative | `+2.780%` | `+1.345%` | `+0.307%` | `+4.273%` |

This supports a research hypothesis that some REDUCED x negative names diluted
the first-day anchor.  It does not prove an absolute reject gate, because the
multi-day actual sample does not show the same simple ordering.

## Actual BUY_NEW Forward Outcomes

Across the available run snapshot, actual `BUY_NEW` sample count is `99`.

| Group | Count | Mean 5BD | Mean 10BD | Mean 20BD | Capital-Weighted 20BD |
| --- | ---: | ---: | ---: | ---: | ---: |
| FULL | `64` | `-0.383%` | `-1.063%` | `+2.303%` | `-10.998%` |
| FULL x negative score | `44` | `+1.135%` | `+3.632%` | `+2.027%` | `-10.639%` |
| REDUCED | `35` | `+6.672%` | `+7.027%` | `+5.961%` | `-4.066%` |
| REDUCED x negative score | `23` | `+10.247%` | `+11.168%` | `+8.206%` | `-8.419%` |

Interpretation:

- H1, "FULL is better than REDUCED", is `NO_ON_CURRENT_SAMPLE`.
- H2, "REDUCED x negative is particularly bad", is not supported by
  equal-weight mean returns, though capital-weighted 20BD remains negative.
- H3, "percentile/rank gives better separation than sign", is
  `INSUFFICIENT_FOR_GATE_DESIGN`.
- H4, "post-AM removal of the absolute negative gate picked too broadly", is
  `INSUFFICIENT`; current evidence supports design review, not a Runtime reject.
- H5, "REDUCED allocations limit damage", is partially supported on the
  `2022-08-10` anchor, but not enough for a new gate.

## Candidate-Day Context

Candidate-day rows total `2,277`; eligible-but-not-bought rows total `2,178`.

| Group | Count | Mean 20BD | Positive Rate 20BD |
| --- | ---: | ---: | ---: |
| FULL candidates | `247` | `-4.166%` | `31.984%` |
| REDUCED candidates | `2,030` | `-1.601%` | `38.971%` |
| FULL x negative candidates | `146` | `-3.932%` | `24.658%` |
| REDUCED x negative candidates | `1,966` | `-1.599%` | `38.304%` |
| Eligible not bought | `2,178` | `-2.130%` | `37.834%` |

This again does not support restoring the old `score <= 0` hard gate.

## Exposure Semantics Observation

The anchor day still shows a separate field-semantics / lot-execution follow-up:

| Field | Value |
| --- | ---: |
| PC incremental accepted BUY_NEW weight | `0.99999` |
| Actual EOD exposure | `0.1887884267631103` |

This is not treated as a Phase29-L21T-AO Runtime defect.  It should be audited
separately if capital allocation field semantics need canonicalization.

## Required Answers

| Question | Answer |
| --- | --- |
| Is REDUCED consistently worse than FULL? | `NO` |
| Is REDUCED x score < 0 consistently worse than other groups? | `NO / MIXED` |
| Is there enough evidence to use score < 0 as an absolute gate again? | `NO` |
| Is Phase30 design review for REDUCED x low relative score worthwhile? | `YES` |
| Should an immediate REJECT be implemented for REDUCED x score < 0? | `NO` |
| Should the current post-AM run continue absent runtime defect? | `YES` |

## Root Classification

```text
INSUFFICIENT_LONG_HORIZON_SAMPLE_FOR_ABSOLUTE_GATE
DEPLOYED_CAPITAL_QUALITY_RESEARCH_NEEDED
ACCEPTED_WEIGHT_VS_ACTUAL_EXPOSURE_FIELD_SEMANTICS_OR_LOT_EXECUTION_FOLLOW_UP_REQUIRED
```

User hypothesis classification:

```text
MIXED_EVIDENCE_DESIGN_REVIEW_ONLY
```

## Next Step

Continue the user-operated post-AM long-horizon validation.  Do not make a new
BUY gate, reject rule, score threshold, or Strategy performance tuning change
from this audit alone.

Recommended future work after enough completed evidence:

```text
Phase30 research item: deployed-capital quality review for Buy Quality x
relative Opportunity score, including allocation scaling rather than hard
absolute rejection.
```
