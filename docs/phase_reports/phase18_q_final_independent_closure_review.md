# Phase18-Q Final Independent Closure Review

- Run ID: `phase18q-final-independent-closure-review-20260717T000000Z`
- Primary Judgment: `PHASE18_Q_CRITICAL_CONTRACT_VIOLATION_DETECTED`
- Secondary Judgment: `PHASE18_NOT_COMPLETE, PHASE19_NOT_READY`
- Evidence: `reports/phase18_q_final_independent_closure_review/phase18q-final-independent-closure-review-20260717T000000Z`

## Executive Summary

Phase18-Q cannot close Phase18. The independent review found one critical Registry Authority gap and multiple high-severity Runtime/Freshness/Drift/SELL continuity gaps. Phase18-P evidence is useful, but it does not prove accepted-only Runtime authority or full SELL continuity.

## Critical Finding

- `Q-GAP-001`: Runtime accepted bundle discovery falls back to the latest Promotion Candidate bundle when no accepted runtime state exists. This directly conflicts with the Phase18-Q prohibition on Promotion Candidate Runtime adoption.

## O-GAP Closure Result

| Gap | Result | Evidence |
|---|---|---|
| O-GAP-001 Freshness Authority | FAIL | Negative model-training lag and silent calendar fallback remain. |
| O-GAP-002 Accepted Drift Baseline | PARTIAL | Baseline is reconstructed from summary stats and integrity is not fully verified. |
| O-GAP-003 Runtime Decision Contract | PARTIAL | Gate separates MARKET_NO_OPPORTUNITY and MODEL_UNHEALTHY, but `block_submit` remains ambiguous. |
| O-GAP-004 BUY BLOCK / SELL Continuity | PARTIAL | Control-plane sell continuity is recorded; downstream SELL path is not proven. |

## Promotion Boundary Evidence

- `.runtime/runtime_state/accepted_buy_ai_bundle.json` exists: `False`
- Default resolved bundle: `.runtime/artifact_registry/promotion_candidates/transactions/promotion-tx-phase18i-1081babc49b5d26b/atomic_buy_ai_bundle.json`
- Default resolution is Promotion Candidate: `True`

## Freshness Evidence

```json
{
  "label_safe_cutoff": "2026-06-04",
  "model_training_cutoff": "2026-07-17T00:00:00+00:00",
  "model_training_lag_business_days": -22,
  "negative_model_training_lag_treated_as_pass": true,
  "trading_calendar_identity": "1f4d127feb4798dcb5cd59aa8bfa013c3daf9c0701f68549b8ffa72f88128b50",
  "trading_calendar_ref": "artifact:.runtime/data/raw/jquants/trading_calendar/data.parquet",
  "training_dataset_max_date": "2026-05-15"
}
```

## Runtime Dry-run Summary

| Case | Decision | Classification | block_buy | block_sell | block_submit |
|---|---|---:|---:|---:|---:|
| healthy_current | `PASS` | `HEALTHY` | `False` | `False` | `False` |
| market_no_opportunity | `PASS` | `MARKET_NO_OPPORTUNITY` | `False` | `False` | `False` |
| hard_drift | `BLOCK` | `MODEL_UNHEALTHY` | `True` | `False` | `True` |
| missing_baseline | `REVIEW_REQUIRED` | `INSUFFICIENT_EVIDENCE` | `True` | `False` | `True` |
| freshness_stale | `BLOCK` | `MODEL_UNHEALTHY` | `True` | `False` | `True` |

## Test Execution

- Targeted lifecycle tests: `10 passed in 3.24s`
- Cross-contract regression: `85 passed, 2 warnings in 3.93s`
- Test quality result: PASS does not cover accepted-only Runtime discovery, negative freshness lag fail-closed, formal calendar missing fail-closed, accepted bundle hash mismatch, materialized baseline distribution authority, or end-to-end SELL continuity under BUY block.

## Design-to-Implementation Matrix

| SoT Requirement | Production Implementation | Test / Evidence | Status | Remaining Work |
|---|---|---|---|---|
| PIT Dataset Rebuild | Phase18-B/C bundles exist | Phase reports and bundle files | `PASS_WITH_REVIEW` | No Q blocker found |
| Training / Validation | Phase18-D/H training bundles | Phase18-H report | `PASS_WITH_REVIEW` | No Registry accepted adoption in Q |
| Promotion Readiness | Phase18-G/H/I reports | Promotion ready with review | `PASS_WITH_REVIEW` | Operational Utility review remains documented |
| Authority | Authority and Registry operator scripts | Phase18-I transaction artifact | `PASS_WITH_REVIEW` | Do not use as Runtime accepted authority until fixed |
| Promotion Candidate Boundary | Runtime evidence resolver | Q-GAP-001 | `CONTRACT_CONFLICT` | Remove latest Promotion Candidate fallback |
| Artifact Registry | Phase16 Registry plus Phase18 rollback/revoke | Regression and Q review | `PASS_WITH_REVIEW` | Restore-failure CRITICAL path |
| Atomic BUY AI Bundle | Phase18-I bundle | Promotion candidate bundle | `PASS_WITH_REVIEW` | Accepted hash/lineage verification before Runtime use |
| Runtime Discovery | Resolver and runtime artifacts | Q-GAP-001 | `CONTRACT_CONFLICT` | Accepted-only discovery |
| Freshness Authority | lifecycle_evidence freshness resolver | Q-GAP-002/Q-GAP-003 | `CONTRACT_CONFLICT` | Future-date and calendar fail-closed |
| Freshness Gate | evaluate_freshness_gate | Q gate cases | `PARTIAL` | Negative lag handling |
| Accepted Drift Baseline | summary-stat sampling | Q-GAP-005 | `PARTIAL` | Materialized accepted distributions |
| Runtime Current Evidence | candidate/opportunity runtime payloads | Q current evidence | `PASS_WITH_REVIEW` | Hash current evidence artifact |
| Quantitative Drift Gate | PSI/coverage/population/all-negative/calibration checks | Q-GAP-005/Q-GAP-006 | `PARTIAL` | Baseline authority and delayed calibration separation |
| Runtime Daily Wiring | morning buy producer invokes lifecycle gate | producer/CLI audit | `PASS_WITH_REVIEW` | Accepted boundary fix |
| Runtime Decision Contract | block_buy/block_sell/block_submit | Q gate cases | `PARTIAL` | Separate BUY submit from global submit |
| SELL Continuity | sell continuity stage | Q-GAP-007 | `PARTIAL` | Entrypoint-level SELL path proof |
| Weekly Scheduler | Phase18-N/P scripts | report review | `PASS_WITH_REVIEW` | No Q blocker found |
| PM Policy Lifecycle | Phase18-N/P lifecycle classification | report review | `PASS_WITH_REVIEW` | Future acceptance |
| Safety Policy Lifecycle | Phase18-N/P lifecycle classification | report review | `PASS_WITH_REVIEW` | Future acceptance |
| Future AI Onboarding | classification artifacts | report review | `PASS_WITH_REVIEW` | Apply to future AIs |
| Rollback / Revoke | rollback_revoke snapshots | Phase18-P tests | `PASS_WITH_REVIEW` | Restore-failure CRITICAL proof |
| Atomic Failure Restore | failure injection | Q-GAP-008 | `PARTIAL` | Restore failure injection |
| Lifecycle Internal E2E | Not fully proven | Q review | `PARTIAL` | After gaps fixed |
| Operator Parameterization | Phase scripts still contain fixed IDs; production modules partially parameterized | hard-code audit | `REVIEW_REQUIRED` | Move phase constants out of production defaults where needed |

## Remaining Gaps

### Q-GAP-001 - CRITICAL

- Category: `REGISTRY_AUTHORITY_GAP`
- Title: Runtime accepted bundle resolver falls back to latest Promotion Candidate
- Evidence: lines 158-183 resolve missing accepted bundle to .runtime/artifact_registry/promotion_candidates/transactions/*/atomic_buy_ai_bundle.json
- Runtime impact: Normal BUY AI lifecycle evidence can consume a Promotion Candidate when no accepted bundle state exists.
- Registry impact: Promotion Candidate boundary is bypassed without Registry accepted event.
- Recommended remediation: Remove Promotion Candidate fallback from production resolution; require Registry accepted authority or explicit isolated review input that cannot be used by normal Runtime.

### Q-GAP-002 - HIGH

- Category: `FRESHNESS_AUTHORITY_GAP`
- Title: Negative model training lag is treated as PASS
- Evidence: _model_training_cutoff falls back to training_metadata.created_at; gate checks only lag greater than threshold.
- Runtime impact: Future-dated training cutoff relative to label-safe cutoff is not fail-closed.
- Registry impact: Accepted freshness evidence can look healthy despite inconsistent authority dates.
- Recommended remediation: Resolve true model_training_cutoff from training/data authority and classify negative lag/future dates as BLOCK or REVIEW_REQUIRED.

### Q-GAP-003 - HIGH

- Category: `FRESHNESS_AUTHORITY_GAP`
- Title: Formal trading calendar absence silently falls back to weekdays
- Evidence: _load_trading_calendar returns [] for missing/unreadable refs; _bdiff then calls business_days_between without adding REVIEW_REQUIRED reason.
- Runtime impact: Business-day clocks can PASS without formal calendar authority.
- Registry impact: Accepted artifact metadata source authority is not enforced.
- Recommended remediation: Require readable formal calendar from accepted metadata and emit fail-closed evidence when unavailable.

### Q-GAP-004 - HIGH

- Category: `ARTIFACT_EVIDENCE_GAP`
- Title: Integrity evidence records hashes but does not verify bundle references, schema, lineage, or expected hash
- Evidence: _integrity_evidence returns PASS when JSON loads; no comparison of content_hash to joint_bundle_hash/hash_manifest or dataset/training hashes.
- Runtime impact: Accepted artifact hash mismatch case is not independently blocked by Runtime evidence authority.
- Registry impact: Registry authority can be bypassed by a readable but inconsistent bundle file.
- Recommended remediation: Verify joint bundle hash, dataset/training bundle hashes, schema hashes, lineage refs, and Candidate/Opportunity compatibility before PASS.

### Q-GAP-005 - HIGH

- Category: `DRIFT_BASELINE_GAP`
- Title: Accepted drift baseline uses synthetic samples reconstructed from summary stats
- Evidence: _sample_from_stats fabricates prediction/feature values for PSI instead of using materialized accepted baseline distributions.
- Runtime impact: Quantitative drift gate may compare current evidence against generated proxy distributions.
- Registry impact: Accepted Atomic BUY AI Bundle baseline identity does not fully prove source distribution authority.
- Recommended remediation: Materialize accepted baseline arrays/histograms in the bundle and verify their hashes before gate use.

### Q-GAP-006 - HIGH

- Category: `RUNTIME_INTEGRATION_GAP`
- Title: Daily hard gate uses calibration_error_delta without delayed labels
- Evidence: evaluate_drift_gate can BLOCK on calibration_error_delta; current calibration is a score-only proxy.
- Runtime impact: A delayed-outcome monitoring metric can affect immediate BUY gate with proxy evidence.
- Registry impact: Runtime acceptance semantics differ from the delayed monitoring boundary.
- Recommended remediation: Separate immediate calibration-compatible score evidence from delayed realized calibration monitoring; do not hard-block daily BUY on realized calibration error without labels.

### Q-GAP-007 - HIGH

- Category: `SELL_CONTINUITY_GAP`
- Title: BUY BLOCK / SELL continuity is recorded but not proven through downstream Runtime stages
- Evidence: morning job appends buy_lifecycle_sell_continuity then exits BLOCKED/REVIEW_REQUIRED before morning planning; separate sell_planning path is not exercised by this continuity check.
- Runtime impact: SELL continuity remains a control-plane assertion, not an entrypoint-level proof.
- Registry impact: None direct.
- Recommended remediation: Introduce explicit BUY-only block semantics and an integration test proving SELL planning/submit authorization remains reachable under BUY lifecycle block.

### Q-GAP-008 - MEDIUM

- Category: `ROLLBACK_GAP`
- Title: Rollback restore failure behavior is not proven as CRITICAL fail-closed
- Evidence: Phase18-P adds restore snapshots, but the review found no explicit restore-failure CRITICAL path in the audited flow.
- Runtime impact: Atomic failure rehearsal is incomplete for restore-failure scenarios.
- Registry impact: Potential partial recovery risk under secondary write failure.
- Recommended remediation: Add restore failure injection and explicit CRITICAL transaction artifact/no accepted mutation guarantee.

## Non-mutation Confirmation

- Registry event count before/after: `42` / `42`
- Registry event log hash before/after: `3c7a529dc4bcaf48ef8bda795a27b4e8be338e5bda1efd215e92b1801c0a019d` / `3c7a529dc4bcaf48ef8bda795a27b4e8be338e5bda1efd215e92b1801c0a019d`
- Runtime switch: not performed
- Runtime submit: not performed
- BUY restart: not performed
- Broker write: not performed

## Phase18 / Phase19 Judgment

- Phase18 completion judgment: `PHASE18_NOT_COMPLETE`
- Phase19 readiness judgment: `PHASE19_NOT_READY`
- Final judgment: `PHASE18_Q_CRITICAL_CONTRACT_VIOLATION_DETECTED`
