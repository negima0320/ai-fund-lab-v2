# Phase22-QB Upstream Strategy REVIEW_REQUIRED Root Cause Decomposition

## Executive Summary

Primary Judgment:

```text
PHASE22_QB_MULTIPLE_CLOSURE_BLOCKERS_IDENTIFIED
```

This task was evidence review only. No code repair, no new 5BD, no Runtime Switch, no Broker access, no lifecycle promotion, and no consumer eligibility promotion was performed.

Latest reviewed run:

```text
runtime-test-historical-smoke-20260728T023230953202Z
```

Runtime result is PASS. Strategy Shadow is `REVIEW_REQUIRED`, not `BLOCK`. QA's Safety authority repair is reflected: all five days resolve `strategy_maximum_position_weight = 0.18`, `safety_maximum_position_weight = 0.25`, and `effective_maximum_position_weight = 0.18`.

The remaining zero target is not caused by Safety cap. It is caused by upstream `REVIEW_REQUIRED` propagation, especially:

- Status contract mixing between producer result, lifecycle, and consumer eligibility
- non-materialized `price_volatility`
- non-materialized Position Management technical features
- missing `configs/strategy/portfolio_policy.json` source lineage
- Corporate Event `PARTIAL` coverage propagating as whole-chain review

## Latest 5BD Confirmed Facts

| Item | Evidence |
|---|---|
| Runtime status | `PASS` |
| test_validity_judgment | `VALID` |
| acceptance_gate_judgment | `PASS` |
| Strategy Shadow | `REVIEW_REQUIRED` |
| Strategy generated dates | 5 / 5 |
| Strategy blocked dates | 0 |
| Runtime Switch | `false` |
| Active runtime consumer eligibility | `NO` |
| latest fallback | `false` |
| current-state leakage | `false` |

Position Sizing all five days:

```text
producer_result_status = REVIEW_REQUIRED
target_position_count = 0
target_gross_exposure_ratio = 0.0
positions_sized = 0
total_target_weight = 0
```

## REVIEW_REQUIRED Dependency Graph

Primary dependency chain:

```text
Corporate Event PARTIAL
Market/Strategy artifacts DRAFT + NOT_ELIGIBLE
→ SOURCE_NOT_ELIGIBLE compatibility status
→ Portfolio Policy REVIEW_REQUIRED
→ Dynamic Position Count REVIEW_REQUIRED / target_position_count = 0
→ Dynamic Cash Exposure REVIEW_REQUIRED / target_gross_exposure_ratio = 0.0
→ Position Sizing REVIEW_REQUIRED / total_target_weight = 0
```

Parallel review chains:

```text
price_volatility_summary_not_materialized_for_shadow
→ Position Sizing price_volatility_review_required
```

```text
technical_feature_summary_not_materialized_for_shadow
→ Position Management technical_features_review_required
→ Portfolio Construction / Capital Deployment / Position Sizing review
```

```text
configs/strategy/portfolio_policy.json missing
→ source_lineage_hash_required
→ Portfolio Construction / Position Management / Capital Deployment review
```

## Artifact-by-Artifact Root Cause

| Artifact | Judgment | Root Cause |
|---|---|---|
| Price Volatility | IMPLEMENTATION_DEFECT | Not materialized for Strategy Shadow |
| Dynamic Position Count | PROPAGATED_REVIEW | Portfolio Policy review causes target count 0 |
| Dynamic Cash Exposure | PROPAGATED_REVIEW | Policy/count review causes target exposure 0.0 |
| Portfolio Construction | PARTIAL_OUTPUT_WITH_REVIEW | 50 members generated, but PM/weight intent unresolved |
| Position Management | IMPLEMENTATION_AND_STATUS_CONTRACT_REPAIR_REQUIRED | Technical features missing; shadow positions required; upstream SOURCE_NOT_ELIGIBLE |
| Capital Deployment | PROPAGATED_REVIEW_AND_SOURCE_LINEAGE_GAP | Upstream SOURCE_NOT_ELIGIBLE and missing policy config source hash |

## Status Contract Audit

The strongest structural finding is status contract mixing.

Current code and evidence conflate:

- producer calculation success
- artifact lifecycle state
- runtime consumer eligibility
- validation status
- human review requirement

Example:

```text
Market Context producer_result_status = PASS
artifact_lifecycle_status = DRAFT
runtime_consumer_eligibility = NOT_ELIGIBLE
downstream status = SOURCE_NOT_ELIGIBLE
```

That downstream `SOURCE_NOT_ELIGIBLE` then makes Portfolio Policy `REVIEW_REQUIRED`. Because Dynamic Position Count and Dynamic Cash Exposure set numeric outputs to zero whenever upstream is not `PASS`, the system cannot distinguish:

```text
target exposure intentionally 0
```

from:

```text
target exposure unresolved
```

This is a Phase22 closure blocker.

## Initial Empty Portfolio Audit

The latest 5BD is not an empty-portfolio run. It contains five current positions by 2026-07-09. Therefore QB cannot prove the initial 100% cash / zero holdings path from this evidence alone.

Risk:

`Position Management` emits:

```text
position_management_shadow_positions_required
```

If this also fires for an empty portfolio, the system may be unable to start a new BUY path from cash-only state. This requires a synthetic empty-portfolio test after Status Contract separation.

## Corporate Event Coverage Impact

Corporate Event is `PARTIAL` on the reviewed run:

```text
corporate_event_source_coverage_incomplete
jquants_corporate_actions_not_implemented_or_missing
jquants_earnings_schedule_not_implemented_or_missing
jquants_financial_statements_not_implemented_or_missing
```

This propagates through Portfolio Policy, Position Management, and Portfolio Construction as `SOURCE_NOT_ELIGIBLE`.

The current behavior may be over-defensive: partial Corporate Event coverage appears to push the whole chain into review, instead of applying target-specific conservative exclusion or per-symbol review. That needs a contract repair, not a reason-code deletion.

## Historical Accepted Generation Impact

The run still uses an accepted generation with:

```text
effective_from = 2026-07-20T00:00:00+09:00
historical target dates = 2026-07-06 through 2026-07-10
```

This is not the direct cause of the six Position Sizing review reason codes. It remains a Runtime Switch / PIT validation blocker and must not be ignored when later approving Strategy artifacts.

## Non-Zero Target Feasibility

Non-zero target generation is structurally possible under PASS upstream conditions. Existing strategy tests confirm Position Sizing can produce `positions_sized > 0` and `total_target_weight > 0` when:

- target position count > 0
- target gross exposure > 0
- portfolio construction rows exist
- volatility is available
- safety/effective cap > 0

Current 5BD lacks:

- `target_position_count > 0`
- `target_gross_exposure_ratio > 0`
- Price Volatility materialization
- Position Management technical features
- production-common policy config source lineage

So current total target weight remains zero for structural upstream reasons.

## Production Commonality

QB did not find evidence of latest/current fallback or historical-only bypass in the reviewed run:

- `latest_fallback_used = false`
- `current_state_leakage_detected = false`
- PIT validation `PASS`
- Runtime mutation `false`
- Runtime Switch `false`

The required repairs must still be production-common. In particular, do not make a historical-only price volatility override or force `REVIEW_REQUIRED` to `PASS` for the 5BD date range.

## Observability Gaps

Remaining gaps:

- Position Sizing lists six review reasons but does not mark primary vs propagated root.
- `SOURCE_NOT_ELIGIBLE` hides whether the issue is lifecycle, consumer eligibility, calculation review, or true source invalidity.
- Dynamic Cash Exposure writes `target_gross_exposure_ratio = 0.0` for unresolved target.
- Portfolio Construction creates 50 members but lacks concise target member/weight rollups.
- Price Volatility has no dedicated artifact in Strategy Shadow.

## Phase22 Closure Blockers

Phase22 Closure remains:

```text
NO
```

Closure blockers:

1. Status contract mixing causes DRAFT/NOT_ELIGIBLE artifacts to behave like calculation-invalid upstreams.
2. Price Volatility is not materialized for Strategy Shadow.
3. Technical feature summary is not materialized for Position Management.
4. `configs/strategy/portfolio_policy.json` is referenced but missing, causing source lineage gaps.
5. Corporate Event PARTIAL coverage propagates as whole-chain review.
6. Empty-portfolio BUY path is not proven by this run.

## Closure Recovery Plan

Recommended sequence:

```text
Phase22-QC - Status Contract Separation Repair
```

Separate producer calculation status from lifecycle, consumer eligibility, validation, and human review.

```text
Phase22-QD - Shadow Input Materialization and Source Lineage Repair
```

Materialize or contractually define price volatility and technical feature summaries. Provide real portfolio policy config source lineage or remove the dead config path.

```text
Phase22-QE - Corporate Event Partial Coverage Contract Repair
```

Define target-specific conservative exclusion vs whole-chain review for PARTIAL coverage.

```text
Phase22-QF - Operator 5BD Post-Repair Validation Review
```

Review operator-run evidence only. Codex should not run the 5BD by default.

```text
Phase22-QG - Final Phase22 Closure Re-review
```

Reassess Phase22 closure and Phase23 entry after evidence validates non-zero-capable Strategy Shadow.

## Recommended Next Task

Recommended:

```text
Phase22-QC - Status Contract Separation Repair
```

Primary scope:

- Keep `artifact_lifecycle_status = DRAFT` and `runtime_consumer_eligibility = NOT_ELIGIBLE`.
- Allow shadow-only producers to expose calculation-valid numeric outputs when inputs are valid.
- Preserve active Runtime isolation and Runtime Switch prohibition.
- Add observability for producer status vs lifecycle vs consumer eligibility vs human review.
