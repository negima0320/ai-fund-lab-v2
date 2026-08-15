# Phase29-L21T-AL - Post-AK Runtime Authority Path Mismatch Root Cause Audit

## Task ID

`Phase29-L21T-AL`

## Primary Judgment

`PHASE29_L21T_AL_POST_AK_SEMANTIC_METADATA_PROPAGATION_GAP_CONFIRMED_IMPLEMENTATION_READY`

## Current Phase

`Phase29`

This was a read-only runtime authority path / implementation reachability audit.
It did not start Phase30.

## Target Run

`runtime-test-historical-extended-smoke-20260814T041426689731Z`

Audit date:

`2022-08-10`

Target run status from `run_state.json`:

| Field | Value |
| --- | --- |
| status | `HALT` |
| next_job | `2022-09-29:current_valuation_refresh` |
| target run mutated by this audit | `NO` |
| fresh-run / resume / replay / recovery executed | `NO` |

## AK Judgment

Phase29-L21T-AK focused regression passed.

AK repaired the Portfolio Construction and Runtime Planning semantic contract in
the focused test path: under `runtime_opportunity_score` /
`uncalibrated_relative_model_score` / `calibration_applied=false` /
`economic_units_available=false`, `non_positive_expected_edge_score` is a soft
relative metadata reason, not an absolute hard BUY block.

## Actual Hard-Block Status

`CONFIRMED`

The post-AK fresh run still materialized these reason codes for negative
relative-score target candidates on `2022-08-10`:

```text
opportunity_no_buy_reason_hard_block:non_positive_expected_edge_score
opportunity_no_buy_reason_present:non_positive_expected_edge_score
```

The hard block happens in Portfolio Construction before Position Sizing and
Runtime Planning. Runtime Planning does not receive BUY plans for the excluded
symbols.

## Per-Symbol Runtime Path

Detailed evidence:

```text
reports/phase29_l21t_al_post_ak_runtime_authority_path_mismatch_root_cause_audit/per_symbol_runtime_path.csv
reports/phase29_l21t_al_post_ak_runtime_authority_path_mismatch_root_cause_audit/summary.json
```

Summary:

| Symbol | Opportunity Reason | PC Intent | PC Classification | PS Intent | Runtime Planning |
| --- | --- | --- | --- | --- | --- |
| `23700` | `non_positive_expected_edge_score` | `EXCLUDE` | `REVIEW_REQUIRED / semantic_metadata_missing` | `EXCLUDE` | not present |
| `36640` | `non_positive_expected_edge_score` | `EXCLUDE` | `REVIEW_REQUIRED / semantic_metadata_missing` | `EXCLUDE` | not present |
| `66590` | `non_positive_expected_edge_score` | `EXCLUDE` | `REVIEW_REQUIRED / semantic_metadata_missing` | `EXCLUDE` | not present |
| `93180` | `non_positive_expected_edge_score` | `EXCLUDE` | `REVIEW_REQUIRED / semantic_metadata_missing` | `EXCLUDE` | not present |
| `94320` | none | `ADD_CANDIDATE` | `PASS` | `ADD_CANDIDATE` | `BUY_NEW / 900` |

## Semantic Metadata Presence

| Layer | Status | Evidence |
| --- | --- | --- |
| Opportunity source artifact | `YES` | top-level `canonical_score_field=runtime_opportunity_score`, `score_semantic_role=uncalibrated_relative_model_score`, `calibration_applied=false`, `economic_units_available=false` |
| Opportunity rows | `PARTIAL` | rows carry role/calibration/economic metadata but not row-level `canonical_score_field` |
| Portfolio Construction upstream summary | `NO` | `upstream_artifacts.opportunity.summary` lacks all four semantic contract fields |
| Portfolio Construction score contract | `PARTIAL / FAIL-CLOSED` | `score_semantic_role`, `calibration_applied`, and `economic_units_available` are present; `canonical_score_field` is missing |
| Runtime Planning | `PARTIAL` | it consumes final PC; excluded symbols never reach executable planning |
| Strategy Decision Trace | `NO / OBSERVABILITY_ONLY` | trace copies PC membership and reason codes; it does not recompute membership authority |

## Module Paths

Actual runtime producer:

```text
src/ai_fund_lab_v2/strategy/shadow_runtime.py
```

Key functions:

- `produce_strategy_shadow_artifacts`
- `_pc_summary`
- `_summary_kwargs`
- `_payload_from_summary_item`

Portfolio Construction authority:

```text
src/ai_fund_lab_v2/strategy/portfolio_construction.py
```

Key functions:

- `produce_portfolio_construction_artifact`
- `_reconcile_members`
- `_opportunity_score_semantic_contract`
- `_classify_opportunity_no_buy_reason`

Strategy trace producer:

```text
src/ai_fund_lab_v2/strategy/observability.py
```

Key functions:

- `produce_strategy_decision_trace`
- `build_strategy_decision_trace`

## Same Code Path

`YES_FOR_PORTFOLIO_CONSTRUCTION_CORE / INPUT_ADAPTER_EQUIVALENCE_NO`

The actual post-AK run uses the same Portfolio Construction core code as the AK
repair. The actual artifacts include AK-added fields such as
`no_buy_reason_classification`, `target_member_eligibility`, and
`runtime_opportunity_score_authority`.

The focused regression and the actual runtime path are not equivalent at the
input-adapter boundary. The focused regression supplies semantic metadata in the
`PortfolioConstructionSourceSummary.summary` contract. The actual
`shadow_runtime._pc_summary(opportunity)` path supplies rows where
`canonical_score_field` is missing and a summary that also lacks
`canonical_score_field`.

## First Real Runtime Divergence

`shadow_runtime._pc_summary(opportunity)` creates the Portfolio Construction
source summary without propagating opportunity score semantic metadata from the
top-level opportunity artifact.

The source artifact is:

```text
.runtime/runtime_state/buy_ai/2022-08-10/opportunity_rankings.json
```

It contains top-level semantic metadata:

```json
{
  "canonical_score_field": "runtime_opportunity_score",
  "score_semantic_role": "uncalibrated_relative_model_score",
  "calibration_applied": false,
  "economic_units_available": false
}
```

However, the actual PC artifact records:

```text
upstream_artifacts.opportunity.summary.canonical_score_field = missing
upstream_artifacts.opportunity.summary.score_semantic_role = missing
upstream_artifacts.opportunity.summary.calibration_applied = missing
upstream_artifacts.opportunity.summary.economic_units_available = missing
```

Then `_opportunity_score_semantic_contract` sees:

```text
canonical_score_field = ""
missing_fields = ["canonical_score_field"]
semantic_metadata_complete = false
```

That triggers the fail-closed branch in
`_classify_opportunity_no_buy_reason`, returning:

```text
status = REVIEW_REQUIRED
blocks_buy = true
review_reason = semantic_metadata_missing
hard_blocking_reasons = ["non_positive_expected_edge_score"]
```

## Duplicate Legacy Gate

`NO`

The evidence does not show a separate legacy target-member gate or trace-side
recomputation as the first cause. The hard-block reason is already present in
the PC artifact before Strategy Decision Trace is produced.

`strategy_decision_trace.json` is observability materialization of PC outputs.
It copies `portfolio_membership_intent` and `portfolio_reason_codes` from PC.

## Stale Artifact

`NO`

The run's `strategy/source_manifest.json` points to:

```text
.runtime/runtime_state/buy_ai/2022-08-10/opportunity_rankings.json
```

The source manifest hash matches the current artifact hash. The actual PC
artifact also contains AK-added fields, so the issue is not explained by a stale
pre-AK artifact or an alternate pre-AK code path.

## Root Cause Classification

`B_SEMANTIC_METADATA_PROPAGATION_GAP_CONFIRMED`

The source artifact has the required top-level semantic metadata, but the
runtime summary adapter does not carry that metadata into Portfolio
Construction's semantic score contract. Because row-level
`canonical_score_field` is also absent, the AK repair correctly fails closed.

## Regression Classification

`MIGRATION_GAP`

The core implementation is reachable. The remaining issue is that the actual
runtime producer/adapter path has not been migrated to preserve the semantic
metadata needed by the repaired PC authority.

## Implementation Repair

Required:

`YES`

Design required:

`NO`

Implementation readiness:

`YES - minimal Production-common runtime adapter metadata propagation repair`

Next repair should preserve the existing AK authority. It should propagate the
already-existing opportunity top-level semantic contract into the
PortfolioConstructionSourceSummary used by PC, without inventing a new score
authority, without forcing BUY counts or exposure, and without changing model,
threshold, Strategy tuning, Runtime, Safety, or Historical-specific behavior.

## Phase30 Blocker

`YES`

Post-AK actual runtime still hard-blocks relative-score `non_positive_expected_edge_score`
when the metadata drops at the runtime adapter boundary. This post-AK run is not
a clean Phase30 entry baseline.

## RESUME_SAFE_NOW

`NO`

No resume, replay, recovery, or fresh-run was executed. The current AL audit did
not mutate Runtime, Pending, Ledger, Current State, accepted generation, or the
target run.

## Common SoT Updates

No Common SoT change was made in this read-only task.

Recommended next-task SoT update after repair:

- document that opportunity score semantic metadata is a mandatory
  Production-common source-summary contract for Portfolio Construction and
  downstream planning consumers;
- document that adapters may not strip `canonical_score_field`,
  `score_semantic_role`, `calibration_applied`, or
  `economic_units_available` when rows depend on relative score semantics.

## Validation

| Check | Result |
| --- | --- |
| summary JSON parse | `PASS` |
| per-symbol runtime path consistency | `PASS` |
| source code changed | `NO` |
| target runtime mutation | `NO` |
| long Historical / fresh-run / resume / replay / recovery | `NO` |
| `git diff --check` | see final task output |

## Next Task

`Phase29-L21T-AM - Runtime Opportunity Semantic Metadata Propagation Repair`

Expected scope:

- add focused regression reproducing the actual runtime adapter gap;
- minimally repair Production-common summary propagation;
- prove `23700`, `36640`, `66590`, and `93180` become soft relative reasons
  when the complete source semantic contract is available;
- preserve fail-closed behavior when semantic metadata is truly missing;
- keep Phase30 blocked until a user-operated post-repair fresh validation
  produces clean evidence.
