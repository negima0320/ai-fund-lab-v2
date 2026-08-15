# Phase29-L21T-AJ - Post-AH Portfolio Construction Zero-Weight Root Cause Audit

## Primary Judgment

`PHASE29_L21T_AJ_POST_AH_DOWNSTREAM_PORTFOLIO_CONSTRUCTION_ZERO_WEIGHT_AUTHORITY_GAP_CONFIRMED_IMPLEMENTATION_READY`

This was a read-only audit.  No Strategy, Runtime, Config, Model, Threshold,
Ledger, Current State, Pending, replay, recovery, resume, fresh-run, or target
runtime evidence was changed.

## Scope

| Field | Value |
| --- | --- |
| Task ID | `Phase29-L21T-AJ` |
| Current Phase | `Phase29` |
| Target run | `runtime-test-historical-extended-smoke-20260814T032532992929Z` |
| Audit dates | `2022-08-10`, `2022-08-12`, `2022-08-15` |
| Run state observed | `HALT` |
| Halt boundary | `2022-08-23:morning` |
| Completed days observed | `8` |
| Source commit | `54f91f8edb8562a40ba1d4681babf9adbfa3dec4` |
| Code changed | `NO` |
| Runtime mutated | `NO` |
| Fresh-run / resume / replay / recovery executed | `NO` |

## Required Artifacts

| Artifact | Status |
| --- | --- |
| Summary JSON | `reports/phase29_l21t_aj_post_ah_portfolio_construction_zero_weight_root_cause_audit/summary.json` |
| Per-symbol trace CSV | `reports/phase29_l21t_aj_post_ah_portfolio_construction_zero_weight_root_cause_audit/per_symbol_trace.csv` |

## Root Cause

AH correctly moved the Runtime Opportunity score contract toward uncalibrated
relative-score competition.  The post-AH run shows that negative/zero
`runtime_opportunity_score` candidates are no longer lost before Portfolio
Construction: each audit date has `50` Opportunity candidates and `49`
negative/zero score candidates materialized into Portfolio Construction.

The first functional divergence is inside Portfolio Construction, before target
weight assignment:

```text
Portfolio Construction member reconciliation / target-member selection
  consumes Opportunity no_buy_reason + raw runtime_opportunity_score
  -> converts negative/zero new candidates to EXCLUDE or non-selectable
  -> requested_buy_new_weight = 0
  -> accepted_buy_new_weight = 0
  -> Position Sizing / Planning see no executable BUY candidate
```

The primary stale authority is:

```text
no_buy_reason = non_positive_expected_edge_score
```

Portfolio Construction calls `opportunity_no_buy_reason_blocks_buy(no_buy_reason)`
without passing the AH semantic contract that `economic_units_available = false`.
The default remains economic-units mode, so `non_positive_expected_edge_score`
is interpreted as a hard buy block.

There is also a second downstream raw-score sign gate in
`_select_target_members`: new candidates with `runtime_opportunity_score < 0`
are not selectable even if they remain `ADD_CANDIDATE`.

Root cause classification:

`E_MULTI_CAUSAL_PRIMARY_STALE_NO_BUY_REASON_SECONDARY_RAW_SCORE_SIGN_TARGET_MEMBER_GATE`

Relation to L21T-AI:

`CONFIRMS_AND_LOCALIZES_MIXED_AUTHORITY_MIGRATION_DEFECT_DOWNSTREAM_IN_PORTFOLIO_CONSTRUCTION`

## Evidence Summary

| Date | Opp Candidates | Neg/Zero Candidates | Neg/Zero In PC | Neg/Zero Positive PC Weight | BQ PASS | BQ FULL | PC Positive BUY_NEW Weight | Runtime Plans |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `2022-08-10` | 50 | 49 | 49 | 0 | 41 | 4 | 1 (`94320`) | 1 (`94320`) |
| `2022-08-12` | 50 | 49 | 49 | 0 | 39 | 4 | 0 | 1 (`94320`, quantity 0) |
| `2022-08-15` | 50 | 49 | 49 | 0 | 39 | 5 | 0 | 1 (`94320`, quantity 0) |

Canonical Opportunity score contract in the source artifacts:

| Field | Value |
| --- | --- |
| canonical score field | `runtime_opportunity_score` |
| semantic role | `uncalibrated_relative_model_score` |
| calibration applied | `false` |
| economic units available | `false` |

## Symbol Trace Highlights

Positive control:

| Date | Symbol | Score | BQ Action | PC Intent | Requested | Accepted | Runtime Quantity |
| --- | --- | ---: | --- | --- | ---: | ---: | ---: |
| `2022-08-10` | `94320` | `0.16908343` | `REDUCED_ALLOCATION_ONLY` | `ADD_CANDIDATE` | `0.18` | `0.18` | `900` |
| `2022-08-12` | `94320` | `0.17946130` | `REDUCED_ALLOCATION_ONLY` | `RETAIN` | `0` | `0` | `0` |
| `2022-08-15` | `94320` | `0.19132343` | `REDUCED_ALLOCATION_ONLY` | `RETAIN` | `0` | `0` | `0` |

Negative/zero score candidates that Buy Quality accepted but PC zeroed:

| Date | Symbol | Score | no_buy_reason | BQ Action | PC Intent | PC Zero Reason |
| --- | --- | ---: | --- | --- | --- | --- |
| `2022-08-10` | `66590` | `-0.07228975` | `non_positive_expected_edge_score` | `FULL_ALLOCATION_ELIGIBLE` | `EXCLUDE` | `opportunity_not_selected` |
| `2022-08-10` | `93180` | `-0.09100653` | `non_positive_expected_edge_score` | `FULL_ALLOCATION_ELIGIBLE` | `EXCLUDE` | `opportunity_not_selected` |
| `2022-08-10` | `23700` | `-0.09952183` | `non_positive_expected_edge_score` | `FULL_ALLOCATION_ELIGIBLE` | `EXCLUDE` | `opportunity_not_selected` |
| `2022-08-10` | `36640` | `-0.10457570` | `non_positive_expected_edge_score` | `FULL_ALLOCATION_ELIGIBLE` | `EXCLUDE` | `opportunity_not_selected` |
| `2022-08-15` | `37820` | `-0.00016243` | `non_positive_expected_edge_score` | `FULL_ALLOCATION_ELIGIBLE` | `EXCLUDE` | `opportunity_not_selected` |

One hard-risk control remains valid:

| Date | Symbol | no_buy_reason | BQ Action | PC Zero Reason |
| --- | --- | --- | --- | --- |
| `2022-08-12` | `37820` | `below_opportunity_top20|high_downside_risk_score|non_positive_expected_edge_score` | `REJECT` | `buy_quality_rejected` |

## Authority Before / After

Before AH:

```text
Expected-edge score sign was treated like an absolute economic pass/fail gate.
non_positive_expected_edge_score could legitimately block BUY entry.
```

After AH intended contract:

```text
runtime_opportunity_score is uncalibrated relative model output.
Score sign is metadata for relative ranking/quality context, not an economic
expected-return hard gate.
Buy Quality and downstream portfolio allocation must decide whether the
candidate participates, while preserving hard safety blocks.
```

Observed post-AH Portfolio Construction behavior:

```text
PC still applies stale absolute-score authority through:
1. no_buy_reason -> opportunity_no_buy_reason_blocks_buy(default economic mode)
2. runtime_opportunity_score < 0 -> new candidate not selectable
```

Required next repair should migrate PC to the same post-AH score contract while
preserving hard blockers such as high downside, corporate action, liquidity, and
unsupported broker product category.

## Required Questions

Why did 50 candidates reach PC but almost only `94320` get BUY allocation?

`94320` was the only positive-score, no stale no-buy-reason candidate selected
as a target member on `2022-08-10`.  The 49 negative/zero score candidates were
present in PC but converted to `EXCLUDE` or non-selectable before target weight
assignment, so they never entered the positive BUY_NEW weight competition.

Is this AH repair miss, PC design issue, or expected valid zero allocation?

This is a post-AH downstream Portfolio Construction authority migration gap.
AH entry eligibility is working for score-sign migration because candidates are
materialized into PC.  The remaining defect is that PC still consumes stale
absolute expected-edge semantics.  The zero allocation is not expected under the
post-AH contract.

## Required Field Answers

| Field | Answer |
| --- | --- |
| AH entry eligibility working | `YES` |
| AH semantic metadata reaches PC consumer | `NO - partial artifact metadata is present, but not consumed by PC authority` |
| negative score candidates reach PC | `YES` |
| Buy Quality accepts negative/zero candidates | `YES` |
| PC assigns positive weight to negative/zero candidates | `NO` |
| First divergence point | `Portfolio Construction member reconciliation / target-member selection` |
| First divergence producer | `Runtime BUY AI Opportunity artifact` |
| First divergence consumer | `Portfolio Construction` |
| Divergence fields | `no_buy_reason`, `runtime_opportunity_score`, `membership_intent`, `target_membership`, `requested_buy_new_weight` |
| Base weight source | `target_gross_exposure / selected target member count, capped by single-name cap` |
| Zeroing point | `before target weight assignment, through PC target-member selection` |
| Positive reason for `94320` | `positive score, empty no_buy_reason, selected target member` |
| Negative reason for strong candidates | `stale non_positive_expected_edge_score / raw negative score gate` |
| stale non_positive_expected_edge_score active | `YES` |
| stale below_opportunity_top20 active | `YES as stale no_buy_reason metadata path; not proven as sole blocker here` |
| stale opportunity_no_buy_reason_present active | `YES` |
| raw score sign downstream | `YES` |
| Buy Quality / PC aligned | `NO` |
| Capital shortage root cause | `NO` |
| Market Context root cause | `NO` |
| Lot / Safety root cause | `NO` |
| Regression confirmed | `NOT_PROVEN` |
| Root cause classification | `E_MULTI_CAUSAL` |
| Relation to AI `MIXED_AUTHORITY_MIGRATION_DEFECT` | `Confirmed downstream localization in PC` |
| Production-common repair required | `YES` |
| New strategy design required | `NO` |
| Implementation readiness | `YES` |
| Phase30 blocker | `YES` |

## Next Repair Boundary

Recommended next task:

`Phase29-L21T-AK - Post-AH Downstream Portfolio Construction Relative Allocation Authority Completion`

Expected repair scope:

- Production-common Portfolio Construction authority migration.
- Pass/consume Opportunity score semantic metadata when evaluating
  `no_buy_reason`.
- Remove raw negative-score sign as a standalone PC target-member hard blocker
  for uncalibrated relative scores.
- Preserve hard no-buy reasons and Buy Quality hard reject/review behavior.
- Add focused regression for negative uncalibrated score candidates that are
  Buy Quality eligible and should receive positive relative allocation.

## Validation

| Check | Result |
| --- | --- |
| `summary.json` generated | `PASS` |
| `per_symbol_trace.csv` generated | `PASS` |
| Code changed | `NO` |
| Runtime mutated | `NO` |
| py_compile | `NOT RUN - no code change` |

