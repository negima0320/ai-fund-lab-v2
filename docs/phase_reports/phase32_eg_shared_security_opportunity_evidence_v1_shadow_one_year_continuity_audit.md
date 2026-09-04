# Phase32-EG - Shared Security Opportunity Evidence v1 SHADOW Audit

## Scope

EG implemented a SHADOW-only evidence record:

`security_opportunity_evidence.v1`

Purpose:

```text
Evaluate current security attractiveness independently of whether the symbol is
NEW, held, or REENTRY.
```

EG did not connect the record to Production and did not change Candidate
ranking, PM, SELL/REDUCE, BQ/Entry, PC, PS, Runtime, target weights, quantities,
Risk Pacing, Cash, caps, or lot rules. EG did not execute fresh-run, resume,
recover, replay, or long Historical.

Primary source run:

- `runtime-test-historical-extended-smoke-20260902T060955933565Z`

Backfill window:

- `2022-10-03` through `2023-10-26`

EG analysis output:

- `reports/runtime_tests/analysis/phase32_eg_security_opportunity_evidence_20260903T012000`

The earlier diagnostic output
`reports/runtime_tests/analysis/phase32_eg_security_opportunity_evidence_20260903T010000`
was not used for acceptance because it exposed an over-broad
`REENTRY_NOT_APPLICABLE` relationship classifier. The implementation was fixed
and the accepted EG output is the `20260903T012000` directory.

## Contract

The new SHADOW envelope is:

- schema: `security_opportunity_evidence.v1`
- authority type: `SECURITY_OPPORTUNITY_SHADOW_AUTHORITY`
- contract id: `phase32_eg_security_opportunity_evidence.v1`
- owner: `STRATEGY_INTELLIGENCE_SECURITY_OPPORTUNITY_SHADOW_AUTHORITY`
- `authoritative_consumer_count = 0`
- `shadow_only = true`
- `action_authority = false`
- `target_weight_authority = false`
- `quantity_authority = false`

The record answers only:

```text
How attractive is this security right now under current PIT evidence?
```

It does not decide:

- NEW / ADD / REENTRY
- HOLD / REDUCE / EXIT
- target weight
- quantity
- capital allocation

## Implementation

Changed / added for EG:

- `src/ai_fund_lab_v2/strategy/marginal_capital_value.py`
  - added `build_security_opportunity_evidence`
  - added `security_opportunity_evidence.v1` record normalization
  - kept intrinsic security evidence separate from position relationship
- `scripts/runtime_test.py`
  - added `shadow-backfill-security-opportunity`
  - added isolated one-year SHADOW backfill manifest/summary/daily artifacts
- `tests/strategy/test_phase32_eg_security_opportunity_evidence.py`
- `tests/runtime_v2/test_phase32_eg_security_opportunity_backfill.py`
- `docs/phase_reports/phase32_eg_shared_security_opportunity_evidence_v1_shadow_one_year_continuity_audit.md`

The runtime_test command writes only under `reports/runtime_tests/analysis/...`.
It validates that output-root is outside the source run and outside `.runtime`.

## Evidence Separation

Intrinsic security evidence includes reusable PIT evidence such as:

- `runtime_opportunity_score`
- `input_opportunity_rank`
- Candidate / Opportunity refs
- BUY Quality state and reason evidence
- Entry evidence before action replacement
- selection quality tier and reasons
- continuation quality
- relative strength
- downside risk
- expected-edge calibration availability
- trend / momentum
- tick-normalized trend and momentum confidence
- minimum-tick / tick-quantization evidence
- liquidity capacity
- confidence / uncertainty

Position relationship is separate:

- `HELD`
- `FLAT_AFTER_EXIT`
- `FLAT_NEVER_HELD_OR_UNKNOWN`

Action-specific evidence is referenced separately:

- current quantity / current weight
- target weight
- campaign id
- PM action
- ADD incremental value / expected edge / opportunity-cost state
- REENTRY prior context
- lot resolution

Those action-specific fields are not placed in
`intrinsic_security_evidence`.

## One-Year Backfill Result

Command executed:

```bash
PYTHONPATH=src:. PYTHONPYCACHEPREFIX=/private/tmp/pycache-phase32-eg python3 scripts/runtime_test.py shadow-backfill-security-opportunity --source-run-id runtime-test-historical-extended-smoke-20260902T060955933565Z --start-date 2022-10-03 --end-date 2023-10-26 --output-root reports/runtime_tests/analysis/phase32_eg_security_opportunity_evidence_20260903T012000 --confirm --json
```

Result:

- status: `PASS`
- business days: `264`
- unique symbols: `1168`
- records: `14284`
- `production_change_executed = false`
- `target_run_mutated = false`
- `runtime_state_mutated = false`
- `future_information_used = false`
- `historical_outcome_used = false`

Manifest provenance:

- current git head: `1f64f49ee9a8dd48280007e4df656e5f03e231ca`
- `marginal_capital_value.py` sha256:
  `5ebf48434a9b17119bcdf6b2468736b7eeb04337c1be27b32e3d7b2afe6dc756`
- `portfolio_construction.py` sha256:
  `37a9cb6d93ce70260312138d7c5bd345a5c0e7c4ec11b23353798db0c522f5d7`

## Coverage

Completeness:

| Class | Count |
| --- | ---: |
| `COMPLETE` | 14,284 |

Position relationship:

| Relationship | Count |
| --- | ---: |
| `FLAT_AFTER_EXIT` | 5,196 |
| `FLAT_NEVER_HELD_OR_UNKNOWN` | 5,856 |
| `HELD` | 3,232 |

Security attractiveness state:

| State | Count |
| --- | ---: |
| `ATTRACTIVE` | 223 |
| `WATCHLIST` | 5,387 |
| `BLOCKED` | 8,634 |
| `INSUFFICIENT` | 40 |

The attractiveness state is diagnostic only. `BLOCKED` and `INSUFFICIENT` are
not Production trading actions and do not alter PM/PC/BQ/Entry decisions.

## Ownership Neutrality

`OWNERSHIP_STATUS_INTRINSIC_SCORE_EFFECT = NONE`

The record preserves the same `runtime_opportunity_score` and
`input_opportunity_rank` as PIT evidence regardless of whether the symbol is
flat, held, or post-EXIT. Ownership is represented only in
`position_relationship` and action-specific refs. No stale purchase-time score
carry-forward was observed:

- `stale_purchase_time_score_carry_forward_count = 0`

## Held-Symbol Visibility Gap

EF found:

- held PC rows: `3232`
- held rows with Candidate/BQ opportunity refs: `2148`
- apparent gap: `1084`

EG reassessment:

| Class | Count |
| --- | ---: |
| `HELD_WITH_CANDIDATE_OPPORTUNITY_REF` | 2,148 |
| `EF_GAP_COMMON_EVIDENCE_NOW_MATERIALIZABLE` | 1,084 |

`EF_HELD_VISIBILITY_GAP_REASSESSMENT = ALL_1084_GAP_ROWS_NOW_HAVE_COMPLETE_COMMON_SECURITY_OPPORTUNITY_EVIDENCE`

Interpretation: the 1,084-row EF gap was not a lack of usable PIT security
evidence. It was mainly an artifact-shape / representation gap: the evidence
could be materialized when normalized into a common action-neutral record.

## Pre-Buy / Post-Buy Continuity

Mandatory controls:

| Symbol | Records | Flat | Held | Post-EXIT | Continuity |
| --- | ---: | ---: | ---: | ---: | --- |
| `43880` | 38 | 6 | 16 | 16 | `CONTINUOUS_VISIBLE_BEFORE_AND_AFTER_OWNERSHIP` |
| `54010` | 149 | 8 | 53 | 88 | `CONTINUOUS_VISIBLE_BEFORE_AND_AFTER_OWNERSHIP` |
| `83060` | 263 | 1 | 175 | 87 | `CONTINUOUS_VISIBLE_BEFORE_AND_AFTER_OWNERSHIP` |
| `94320` | 264 | 3 | 230 | 31 | `CONTINUOUS_VISIBLE_BEFORE_AND_AFTER_OWNERSHIP` |
| `94340` | 264 | 1 | 137 | 126 | `CONTINUOUS_VISIBLE_BEFORE_AND_AFTER_OWNERSHIP` |
| `99840` | 183 | 3 | 105 | 75 | `CONTINUOUS_VISIBLE_BEFORE_AND_AFTER_OWNERSHIP` |

`PRE_BUY_POST_BUY_SECURITY_EVIDENCE_CONTINUITY = PASS`

Useful security-attractiveness evidence remains continuously available after
purchase in all mandatory controls. The action classification changes, but the
current-day security evidence remains materializable.

## Flat Candidate Equivalence

`FLAT_CANDIDATE_EVIDENCE_EQUIVALENCE = PASS`

For flat Candidate / Opportunity rows with source refs present, the common
record copies score/rank evidence rather than recalculating or tuning it:

- `runtime_opportunity_score` remains an uncalibrated relative score.
- `input_opportunity_rank` remains the existing PIT rank evidence.
- no Candidate ranking is changed.
- no target weight or quantity is inferred from the common record.

Candidate overlap:

| Class | Count |
| --- | ---: |
| `CANDIDATE_OR_OPPORTUNITY_REF_PRESENT` | 13,200 |
| `CANDIDATE_OR_OPPORTUNITY_REF_MISSING` | 1,084 |

The missing-ref rows correspond to the EF held visibility gap and are now still
represented by complete common evidence.

## PM / BQ / Entry Diagnostic Comparison

PM/BQ/PC overlap:

| Class | Count |
| --- | ---: |
| `BQ_OR_ENTRY_PRESENT` | 14,284 |
| `PM_REF_PRESENT` | 3,232 |

The common record is diagnostic only:

- PM lifecycle authority is not replaced.
- BQ/Entry action interpretation is not replaced.
- REENTRY provenance is not replaced.
- SELL/REDUCE behavior is unchanged.

## EE ADD-UNKNOWN Test

EE found:

- `ADD incremental_value UNKNOWN = 116`

EG common Security Opportunity coverage for those same rows:

| Class | Count |
| --- | ---: |
| `COMPLETE` | 116 |

`EE_ADD_UNKNOWN_SECURITY_EVIDENCE_COVERAGE = COMPLETE_116_OF_116`

Answer to the key EG question:

Yes. Usable current security-attractiveness evidence exists even when ADD
marginal-value evidence is UNKNOWN. This does not convert any row into ADD.
It only proves that the security-level evidence and ADD incremental-capital
evidence are separable.

## June-September 2023

EE had 20 ADD rows in June through September 2023:

- BLOCKED: 16
- INSUFFICIENT: 4
- ADD superior: 0

EG Security Opportunity visibility:

| Class | Count |
| --- | ---: |
| `COMPLETE` | 20 |

`2023_JUN_SEP_SECURITY_OPPORTUNITY_VISIBILITY = COMPLETE_20_OF_20`

Interpretation: even during the June-September ADD-suppression period, current
security evidence was available. The suppression belongs to the ADD
marginal-capital/action layer, not to absence of security opportunity evidence.

## Architecture Judgment

`SHARED_SECURITY_OPPORTUNITY_ARCHITECTURE_FEASIBILITY = STRONG`

The one-year backfill supports EF's proposed separation:

```text
Security Opportunity Evidence
-> Position Relationship
-> NEW / ADD / REENTRY / HOLD / no action classification
-> PC marginal capital competition
```

The common record successfully materializes one daily security evidence record
per business-date/symbol while keeping ownership and action context separate.

`CURRENT_PRODUCTION_BEHAVIOR_PRESERVABLE_UNDER_FUTURE_MIGRATION = YES`

Preservation is plausible because:

- Production has zero consumers of EG.
- Candidate ranking is copied, not tuned.
- PM/PC/BQ/Entry/PS/Runtime are not changed.
- action-specific semantics remain outside intrinsic evidence.
- ADD UNKNOWN rows are not promoted.
- SELL/REDUCE remain isolated.

The next step should be the smallest SHADOW consumer only: a PC diagnostic
consumer that reads `security_opportunity_evidence.v1` and reports divergence
against existing Candidate/BQ/Entry/PC evidence without changing allocation.

## Validation

Focused EG tests:

```bash
PYTHONPATH=src:. PYTHONPYCACHEPREFIX=/private/tmp/pycache-phase32-eg python3 -m pytest -q tests/strategy/test_phase32_eg_security_opportunity_evidence.py tests/runtime_v2/test_phase32_eg_security_opportunity_backfill.py
```

Result:

- `5 passed`

Focused adjacent regression:

```bash
PYTHONPATH=src:. PYTHONPYCACHEPREFIX=/private/tmp/pycache-phase32-eg python3 -m pytest -q tests/strategy/test_phase32_eg_security_opportunity_evidence.py tests/runtime_v2/test_phase32_eg_security_opportunity_backfill.py tests/strategy/test_phase32_dq_unified_marginal_capital_shadow.py tests/runtime_v2/test_phase32_dt_shadow_backfill_marginal_capital.py tests/strategy/test_phase31_g115_add_marginal_authoritative_binding.py tests/strategy/test_phase31_g119_pc_final_authority_ps_consistency.py tests/strategy/test_phase31_g44_add_reentry_lot_binding_integration.py tests/strategy/test_phase31_g63_runtime_executable_binding.py tests/strategy/test_phase31_g43_risk_pacing_economic_binding.py tests/runtime_v2/test_phase30_ak9r27_pending_review_scope_authority.py tests/runtime_v2/test_phase31_f1w_item_scoped_partial_submit.py
```

Result:

- `74 passed`

Compile check:

```bash
PYTHONPATH=src:. PYTHONPYCACHEPREFIX=/private/tmp/pycache-phase32-eg python3 -m py_compile scripts/runtime_test.py src/ai_fund_lab_v2/strategy/marginal_capital_value.py
```

Result:

- `PASS`

## Required Final Answers

- `SECURITY_OPPORTUNITY_EVIDENCE_V1_IMPLEMENTED = YES`
- `authoritative_consumer_count = 0`
- `SECURITY_OPPORTUNITY_ACTION_AUTHORITY = NO`
- `POSITION_RELATIONSHIP_SEPARATE_FROM_OPPORTUNITY = YES`
- `OWNERSHIP_STATUS_INTRINSIC_SCORE_EFFECT = NONE`
- `PRE_BUY_POST_BUY_SECURITY_EVIDENCE_CONTINUITY = PASS`
- `EF_HELD_VISIBILITY_GAP_REASSESSMENT = ALL_1084_GAP_ROWS_NOW_HAVE_COMPLETE_COMMON_SECURITY_OPPORTUNITY_EVIDENCE`
- `FLAT_CANDIDATE_EVIDENCE_EQUIVALENCE = PASS`
- `EE_ADD_UNKNOWN_SECURITY_EVIDENCE_COVERAGE = COMPLETE_116_OF_116`
- `2023_JUN_SEP_SECURITY_OPPORTUNITY_VISIBILITY = COMPLETE_20_OF_20`
- `SHARED_SECURITY_OPPORTUNITY_ARCHITECTURE_FEASIBILITY = STRONG`
- `CURRENT_PRODUCTION_BEHAVIOR_PRESERVABLE_UNDER_FUTURE_MIGRATION = YES`
- `NEXT_RECOMMENDED_CONSUMER_STEP = PC_SHADOW_DIAGNOSTIC_CONSUMER_ONLY_ZERO_PRODUCTION_AUTHORITY`
- `FUTURE_OUTCOME_USED = NO`
- `HISTORICAL_PNL_USED_FOR_DESIGN_OR_NORMALIZATION = NO`
- `PRODUCTION_CHANGE_EXECUTED = NO`
- `TARGET_RUN_MUTATED = NO`
- `RUNTIME_STATE_MUTATED = NO`
- `LONG_RUNTIME_EXECUTED = NO`
- `FINAL_JUDGMENT = PHASE32_EG_SHARED_SECURITY_OPPORTUNITY_EVIDENCE_V1_SHADOW_ACCEPTED_ARCHITECTURE_FEASIBILITY_STRONG_NO_PRODUCTION_CHANGE`

## Final Judgment

`PHASE32_EG_SHARED_SECURITY_OPPORTUNITY_EVIDENCE_V1_SHADOW_ACCEPTED_ARCHITECTURE_FEASIBILITY_STRONG_NO_PRODUCTION_CHANGE`

EG confirms that the system can continuously answer:

```text
How attractive is this security right now?
```

before and after ownership. The current Security Opportunity evidence is
materializable for held, flat, and post-EXIT symbols while preserving separate
position relationship and action authority. This supports the shared Security
Opportunity architecture as a SHADOW-first migration path, not an immediate ADD
increase or Production promotion.
