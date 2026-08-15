# Phase29-L21T-AI - Post-AH Fresh Validation Readiness and Expected Edge Regression Lineage Audit

## Primary Judgment

`PHASE29_L21T_AI_POST_AH_FRESH_VALIDATION_BLOCKED_BY_ACTIVE_MIXED_RUN_REGRESSION_LINEAGE_COMPLETE`

Current Phase remains `Phase29`.  Phase30 was not entered.

## Scope

| Field | Value |
| --- | --- |
| Task ID | `Phase29-L21T-AI` |
| Task ID reuse check | `UNUSED_AS_TASK_ARTIFACT`; only referenced as AH recommended next task |
| Task type | `READ_ONLY_REGRESSION_LINEAGE_AUDIT_AND_FRESH_VALIDATION_READINESS` |
| AH Judgment inherited | `PHASE29_L21T_AH_EXPECTED_EDGE_RELATIVE_ALLOCATION_SEMANTICS_IMPLEMENTED_FOCUSED_REGRESSION_PASS` |
| Target mixed-code run | `runtime-test-historical-extended-smoke-20260814T005603520480Z` |
| Target run mutated by Codex | `NO` |
| Long Historical executed by Codex | `NO` |
| Strategy / Runtime / Config / Model changed | `NO` |

Codex did not stop, abandon, resume, replay, recover, fresh-run, or mutate the
target run.

## Mandatory Source Documents

Read and reconciled:

- `docs/phase_reports/phase29_l21t_af_expected_edge_opportunity_gate_forward_return_attribution_audit.md`
- `docs/phase_reports/phase29_l21t_ag_expected_edge_gate_calibration_allocation_semantics_design.md`
- `docs/phase_reports/phase29_l21t_ah_expected_edge_relative_allocation_semantics_implementation.md`

Additional lineage evidence:

- `docs/phase_reports/phase17_bv15_opportunity_buy_eligibility_contract_fix.md`
- `docs/phase_reports/phase17_bv16_opportunity_expected_edge_semantics_and_runtime_distribution_investigation.md`
- `docs/phase_reports/phase24_hx_opportunity_ranking_semantics_and_top_rank_selection_trace_audit.md`
- `docs/phase_reports/phase24_hy_ranking_consumer_alignment_and_rank_authority_contract.md`
- `docs/phase_reports/phase26_f_buy_quality_admission_rank_score_and_reentry_authority_audit.md`
- `docs/phase_reports/phase26_h_production_common_adaptive_buy_quality_authority_implementation.md`
- `docs/phase_reports/phase29_l21i_opportunity_score_semantic_contract_repair.md`
- `docs/02_architecture/strategy_architecture_v1.md`
- `docs/02_architecture/portfolio_construction_and_position_sizing_contract.md`

## Regression Classification

| Field | Judgment |
| --- | --- |
| Regression classification | `MIXED_AUTHORITY_MIGRATION_DEFECT` |
| Regression confirmed | `NO` |
| Introducing commit | `4e2a705 phase5` introduced Opportunity inference score/no-buy reason production |
| BV15 absolute gate commit | `78d0f1c phase17 FIX` introduced Runtime BUY eligibility enforcement |
| Later semantic migration evidence | `d470765 phase26 FIX`, `1db2ce8 phase28 FIX`, Phase29-L21I/AF/AG/AH docs and code |
| Breaking commit proven | `NO`; no single previous-correct relative-competition contract then breaking commit was proven |

The AH fix is not a clean `REGRESSION_CONFIRMED` from a previously documented
correct Runtime relative-competition contract.  The stronger evidence is that an
older absolute Expected Edge gate remained active after the score authority
migrated / was clarified into an uncalibrated relative model signal.

## Lineage Answers

### Q1 - `non_positive_expected_edge_score` introduction

`non_positive_expected_edge_score` traces back to Phase5 Opportunity AI
inference (`4e2a705 phase5`).  Phase5-F assigned raw model predictions into
`expected_edge_score`, ranked descending by that score, and generated
`non_positive_expected_edge_score` when the score was `<= 0`.

### Q2 - Introduction-time score semantic

The introduction-time semantic was best described as a raw model prediction for
`label__expected_edge_label_20d`, exposed under the economically suggestive name
`expected_edge_score`.  Phase17-BV16 later documented it as a raw regression
prediction copied directly into `expected_edge_score` / `expected_return` with no
sign inversion or scale conversion.

Classification at introduction: `raw_model_score_with_expected_edge_label_name`.

### Q3 - Was `score <= 0 -> BUY_INELIGIBLE` design-valid at introduction?

At BV15/BV16 time, it was treated as design-valid because Runtime had been
incorrectly using rank/top-N membership as BUY permission.  BV15 fixed that by
requiring finite positive `expected_edge_score` and no blocking `no_buy_reason`.

That decision was locally coherent under the then-documented assumption that the
score represented an absolute expected edge estimate.  It is not valid under the
current AH contract when the score explicitly carries
`calibration_applied=false` and `economic_units_available=false`.

### Q4 - Later score producer / semantic / alias changes

Later authority documents and Runtime artifacts changed / clarified the contract:

- Phase26-F documented `expected_edge_score` as the Opportunity Ranking
  Authority's `runtime_opportunity_score`, a cross-sectional relative signal.
- Phase26-H introduced `relative_opportunity_quality` in Buy Quality as the
  Production-common relative allocation authority.
- Phase29-L21I/AF/AG/AH formalized
  `canonical_score_field=runtime_opportunity_score`,
  `score_semantic_role=uncalibrated_relative_model_score`,
  `calibration_applied=false`, and `economic_units_available=false`.
- AH propagates these fields through producer, Morning listed info, and Submit
  revalidation.

### Q5 - Evidence that negative raw score candidates previously reached relative competition

Evidence exists that negative raw-score, high-rank candidates previously reached
BUY consideration through rank/top-N consumption, but BV15 classified that as a
bug: rank/top20 membership was being treated as BUY permission.

Evidence was not found for a previously documented correct contract of:

```text
negative raw score -> relative_quality -> Portfolio Construction competition
```

before the later Buy Quality / semantic-metadata work.  Therefore regression from
a known-good relative contract is not proven.

### Q6 - Top20 lineage

Phase5 introduced Top5/Top10/Top20 as ranking columns and
`below_opportunity_top20` as a no-buy reason.  BV15/BV16 made top/rank
insufficient for BUY and enforced score/no-buy reason as hard eligibility.

Phase24-HX/HY clarified that rank generation itself was not defective and that
downstream consumers must not treat rank as fixed BUY authority.  AF/AG/AH then
separated top20 from uncalibrated score eligibility: for uncalibrated artifacts,
top20 is metadata / diagnostic shortlist evidence, not a hard BUY_NEW rejection
and not automatic BUY permission.

### Q7 - Alias meaning change

Yes.  `expected_edge_score` and `expected_return` began as active score fields
with expected-edge naming.  Current artifacts mark them as deprecated
compatibility aliases of `runtime_opportunity_score`.  They are not economic
expected return unless a future artifact explicitly sets
`calibration_applied=true` and `economic_units_available=true`.

## AH Contract Consistency

AH changed the current common Runtime path so uncalibrated negative score sign is
not, by itself, BUY-ineligible:

```text
calibration_applied=false
economic_units_available=false
runtime_opportunity_score <= 0
-> relative competition eligible
```

Preserved fail-closed cases:

- malformed / missing / conflicting score contract
- stale / mismatched Opportunity artifact, row, symbol, business date, feature date, or hash
- calibrated economic score `<= 0`
- hard no-buy reasons such as high downside risk, corporate action, listing, broker, or liquidity blocks
- Submit revalidation before broker boundary

Current AH contract consistent: `YES`.

## Fresh Validation Readiness

| Check | Result |
| --- | --- |
| AH changes present | `YES` |
| Required AH tests recorded PASS | `YES` |
| Runtime / Historical common path preserved | `YES` |
| Config change required before rerun | `NO` |
| Model change required before rerun | `NO` |
| Accepted Generation compatible | `YES` |
| Schema compatibility | `YES`; additive metadata / aliases preserved |
| Existing long run mixed-code | `YES` |
| Existing run usable as formal post-AH baseline | `NO` |
| Fresh 4-year rerun required | `YES` |
| Fresh-run readiness | `BLOCKED_BY_ACTIVE_MIXED_RUN` |

The target run state was read directly from run evidence:

| Field | Value |
| --- | --- |
| `status` | `RUNNING` |
| `profile_id` | `historical-extended-smoke` |
| `next_job` | `2023-01-11:market_refresh` |
| completed business days | `101` |
| completed window | `2022-08-10` through `2023-01-10` |
| source commit | `54f91f8edb8562a40ba1d4681babf9adbfa3dec4` |
| source dirty | `true` |

CLI contract check:

- `fresh-run` dry-run can preview with active run evidence.
- actual `fresh-run` checks `active_run_for_profile`.
- any unclosed `RUNNING` / `HALT` run for the same profile is an active conflict.
- `stop` transitions `RUNNING -> HALT` without Trading State mutation.
- `abandon` finalizes a HALT run as not resumable and removes it from active run selection.

Therefore:

| Field | Value |
| --- | --- |
| Existing run stop required | `YES` |
| Existing run abandon required | `YES` |
| Parallel fresh-run possible for same profile | `NO` |

## Recommended User Commands

Codex must not execute these commands.  They are operator commands for the user.

1. Inspect current active run:

```bash
PYTHONPATH=src python3 scripts/runtime_test.py show \
  --run-id runtime-test-historical-extended-smoke-20260814T005603520480Z \
  --json
```

2. Stop dry-run:

```bash
PYTHONPATH=src python3 scripts/runtime_test.py stop \
  --run-id runtime-test-historical-extended-smoke-20260814T005603520480Z \
  --reason phase29_l21t_ai_superseded_by_post_ah_fresh_validation \
  --dry-run \
  --json
```

3. Stop:

```bash
PYTHONPATH=src python3 scripts/runtime_test.py stop \
  --run-id runtime-test-historical-extended-smoke-20260814T005603520480Z \
  --reason phase29_l21t_ai_superseded_by_post_ah_fresh_validation \
  --confirm \
  --yes-i-understand-this-mutates-trading-state \
  --json
```

4. Abandon dry-run:

```bash
PYTHONPATH=src python3 scripts/runtime_test.py abandon \
  --run-id runtime-test-historical-extended-smoke-20260814T005603520480Z \
  --reason phase29_l21t_ai_formal_post_ah_baseline_requires_fresh_run \
  --dry-run \
  --json
```

5. Abandon:

```bash
PYTHONPATH=src python3 scripts/runtime_test.py abandon \
  --run-id runtime-test-historical-extended-smoke-20260814T005603520480Z \
  --reason phase29_l21t_ai_formal_post_ah_baseline_requires_fresh_run \
  --confirm \
  --yes-i-understand-this-mutates-trading-state \
  --json
```

6. Fresh-run dry-run:

```bash
PYTHONPATH=src python3 scripts/runtime_test.py fresh-run \
  --profile historical-extended-smoke \
  --date-from 2022-08-10 \
  --date-to 2026-08-09 \
  --initial-cash 1000000 \
  --dry-run \
  --json
```

7. Fresh-run execution:

```bash
PYTHONPATH=src python3 scripts/runtime_test.py fresh-run \
  --profile historical-extended-smoke \
  --date-from 2022-08-10 \
  --date-to 2026-08-09 \
  --initial-cash 1000000 \
  --confirm \
  --yes-i-understand-this-mutates-trading-state \
  --json
```

8. Run status after start:

```bash
PYTHONPATH=src python3 scripts/runtime_test.py run-status \
  --profile historical-extended-smoke \
  --json
```

9. Early checkpoint inspection after 10-20 business days have completed:

```bash
PYTHONPATH=src python3 scripts/runtime_test.py summarize \
  --run-id <NEW_RUN_ID> \
  --scope overview \
  --json

PYTHONPATH=src python3 scripts/runtime_test.py summarize \
  --run-id <NEW_RUN_ID> \
  --scope performance \
  --json

PYTHONPATH=src python3 scripts/runtime_test.py summarize \
  --run-id <NEW_RUN_ID> \
  --scope strategy \
  --json

PYTHONPATH=src python3 scripts/runtime_test.py daily-evidence \
  --run-id <NEW_RUN_ID> \
  --business-date 2022-08-22 \
  --json
```

## Recommended Early Checkpoint

Inspect the first 10-20 business days before waiting for the full 4-year run.
Compare against the pre-AH baseline where `2022-08-10` through `2022-08-22`
were mostly `94320` only, exposure around `13-18%`, and cash around `82-87%`.

Minimum evidence to inspect:

- position count
- cash
- exposure
- BUY_NEW candidate count
- BUY allocated count
- negative uncalibrated score candidates reaching relative competition
- Quality PASS count
- PC positive allocation count
- PS executable count
- actual BUY fills
- lot / safety blocks
- no-buy canonical reasons

Success is not defined as forced higher exposure.  Success is that candidates
previously rejected solely by uncalibrated score sign now reach relative
competition and downstream fail/succeed for the appropriate authority reason.

## Command Guide Compliance

No new CLI command was added.  Existing commands are sufficient:

- `show`
- `stop`
- `abandon`
- `fresh-run`
- `run-status`
- `summarize`
- `daily-evidence`

Command guide update required: `NO`.

## Validation

Read-only / documentation validation:

```text
lineage evidence consistency check: PASS
summary.json parse: PASS
git diff --check: PASS
```

No py_compile was required for AI because no Python code was changed in this
task.

## Required Final Fields

| Field | Value |
| --- | --- |
| Task ID | `Phase29-L21T-AI` |
| Primary Judgment | `PHASE29_L21T_AI_POST_AH_FRESH_VALIDATION_BLOCKED_BY_ACTIVE_MIXED_RUN_REGRESSION_LINEAGE_COMPLETE` |
| Current Phase | `Phase29` |
| AH Judgment inherited | `PHASE29_L21T_AH_EXPECTED_EDGE_RELATIVE_ALLOCATION_SEMANTICS_IMPLEMENTED_FOCUSED_REGRESSION_PASS` |
| Regression classification | `MIXED_AUTHORITY_MIGRATION_DEFECT` |
| Regression confirmed | `NO` |
| Absolute zero gate introduction lineage | `Phase5 producer reason -> Phase17-BV15 Runtime enforcement` |
| Score semantic change lineage | `Phase26/Phase29 semantic metadata moved score to uncalibrated relative model signal` |
| Top20 lineage | `rank metadata -> BV15 not BUY permission -> AH not uncalibrated hard rejection` |
| Previous relative competition evidence | `NOT_PROVEN_AS_CORRECT_CONTRACT` |
| Current AH contract consistent | `YES` |
| Existing long run mixed-code | `YES` |
| Existing run usable as formal post-AH baseline | `NO` |
| Fresh 4-year rerun required | `YES` |
| Fresh-run readiness | `BLOCKED` |
| Existing run stop required | `YES` |
| Existing run abandon required | `YES` |
| Runtime / Historical common path | `YES` |
| Accepted Generation compatible | `YES` |
| Config change required before rerun | `NO` |
| Model change required before rerun | `NO` |
| Target run mutated by Codex | `NO` |
| Long Historical executed by Codex | `NO` |
| Phase30 entered | `NO` |

## Recommended Next Task

`Phase29-L21T-AJ - Post-AH Fresh 4-Year Early Checkpoint Evidence Review`

Only after the user completes stop/abandon and starts the fresh post-AH run,
review the first 10-20 business days using funnel evidence rather than exposure
alone.
