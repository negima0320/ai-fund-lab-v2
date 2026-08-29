# Phase32-CZ — Current Production Architecture / Investment Behavior Conformance Audit

## Executive Summary

READ-ONLY audit of primary run:

- `runtime-test-historical-extended-smoke-20260829T082306780474Z`
- coverage inspected: `2022-10-03` through `2022-12-29`
- completed business days inspected: `61`

The current Production path is mostly conformant with the Phase32 architecture direction:

- PC-owned `canonical_marginal_capital_frontier_authority.v1` is active as the Production target authority.
- NEW multi-lot target magnitude, Buy Quality target ceiling, one-lot explicit blocking, BF-only PS boundary, budget/cash conservation, campaign entry-premise lifecycle, and PM fresh-deterioration context all materialize on the actual path.
- PIT flags scanned cleanly on the major authority artifacts inspected.
- Cash remains an explicit authorized allocation every inspected day.
- PM lifecycle behavior is materially healthier than the CW/CX failure mode: PM snapshot status was PASS for all 482 PM position rows inspected, with zero `AMBIGUOUS_REVIEW_REQUIRED`.

However, the end-to-end authority chain is not a clean PASS. Two conformance gaps remain:

1. `2022-10-21` 94320 ADD lot #1/#2/#3 were accepted even though the frontier candidates carried `comparison_class = BLOCKED` and `opportunity_quality_add_hard_block`. Runtime Planning also exposed the same row as `BUY_ADD` with `marginal_capital_value_class = BLOCKED_OR_NOT_ELIGIBLE`, yet the 300-share BUY reached execution. This is an authority semantic mismatch, not a performance judgment.
2. The current run's execution fills still carry sparse BUY provenance: all 83 BUY fills have `source_decision_id = MISSING` and generic `source_decision_type = BUY`. Campaign lifecycle recovers entry premise through strict-prior same-run artifacts after Phase32-CY semantics, but execution ledger observability remains weaker than the intended authoritative lineage contract.

OLD baseline `runtime-test-historical-extended-smoke-20260828T000823285458Z` was not present under `reports/runtime_tests/runs/` in this workspace, so OLD comparison is limited to prior phase report evidence and not used as a primary acceptance gate.

## End-to-End Authority Chain

| Boundary | Actual Evidence | Judgment |
| --- | --- | --- |
| Candidate -> Entry admission | PC/PS rows separate candidate eligibility from deployability; `NOT_APPLICABLE`, `REDUCED_ALLOCATION_ONLY`, and `FULL_ALLOCATION_ELIGIBLE` are visible. | PASS |
| Adaptive Buy Quality -> target | NEW/REENTRY positive target rows preserve quality upper bounds; no NEW/REENTRY silent re-expansion found. | PASS |
| One-lot authority | 894 sub-lot candidates fail closed via `quality_ceiling_blocks_one_lot_rescue`; no implicit rescue observed. | PASS |
| NEW/REENTRY multi-lot | 4772 NEW candidates, 537 REENTRY candidates, 2649 accepted NEW lots; REENTRY surface exists but no REENTRY fills in this coverage. | PARTIAL |
| ADD eligibility/value | 117 ADD candidates, 17 accepted ADD lots; most carry PASS add admission, but 3 accepted lots had BLOCKED comparison class. | PARTIAL |
| Common frontier -> BF | `production_consumer_enabled = true` on all 61 frontier authority artifacts; BF aggregated targets consumed by PS. | PASS |
| BF -> PS -> Runtime | PS-positive rows and Runtime Planning align in quantity for normal cases; one 94320 ADD row propagated despite blocked value class. | PARTIAL |
| Pending/Submit/Fill | Run completes daily jobs; BUY fills occur, but BUY execution provenance remains generic/missing. | PARTIAL |
| Campaign lifecycle -> PM | Entry premise snapshot PASS at PM for 482/482 rows; PM delta classes materialize. | PASS |
| REDUCE/EXIT/capital recycling | 75 SELL fills, 82 BUY_NEW fills, and cash allocation every day demonstrate recycling/cash choice. | PASS |

Overall: PARTIAL. The architecture is functioning, but the ADD blocked-class acceptance and sparse execution BUY lineage prevent a clean PASS.

## Investment Philosophy

| Philosophy Item | Evidence | Judgment |
| --- | --- | --- |
| Entry | 82 BUY_NEW fills over 75 symbols; Buy Quality reduction and one-lot fail-closed behavior are visible. | CONFORMANT |
| Winner | PM emitted 360 HOLD, 39 ADD decisions, and ADD candidate surface exists. | PARTIAL |
| Exit | PM emitted 48 EXIT and 35 REDUCE; hard failure class appears and remains actionable. | CONFORMANT |
| Cash | Authorized cash allocation materialized on 61/61 days; no fixed exposure target observed. | CONFORMANT |
| Capital recycling | BUY notional `3,665,960`, SELL notional `3,060,640`; deployment and de-risking both active. | CONFORMANT |

Winner capitalization is PARTIAL because the ADD machinery works but one accepted ADD day violates the blocked-class semantic boundary.

## Current Run Metrics

### Trading / Capital Flow

| Metric | Value |
| --- | ---: |
| BUY_NEW fills | 82 |
| BUY_ADD fills by execution semantic | 0 |
| SELL fills | 75 |
| BUY_NEW notional | 3,665,960 |
| SELL notional | 3,060,640 |
| Unique BUY_NEW symbols | 75 |
| Unique SELL symbols | 67 |
| Average exposure | 66.57% |
| Min / max exposure | 9.91% / 97.25% |
| Final inspected exposure | 63.80% |
| Average cash | 345,278.85 |
| Min / max cash | 29,870 / 907,880 |
| Final inspected cash | 394,680 |
| Average position count | 8.03 |
| Min / max position count | 3 / 17 |

Execution classifies all BUY fills as generic `BUY`, so authority-level ADD acceptance is visible in PC/PS/Runtime but not preserved as execution `BUY_ADD`.

### Frontier

| Frontier Metric | Count |
| --- | ---: |
| NEW_FIRST_LOT candidates | 4,772 |
| REENTRY_FIRST_LOT candidates | 537 |
| ADD_NEXT_LOT candidates | 117 |
| CASH_OPTIONALITY candidates | 61 |
| Accepted NEW_FIRST_LOT lots | 2,649 |
| Accepted ADD_NEXT_LOT lots | 17 |
| Accepted REENTRY lots | 0 |
| Capital conservation PASS days | 61 |
| Explicit cash allocation days | 61 |
| Cap blocks | 111 |
| Cash blocks | 0 |
| Risk Pacing blocks | 0 |
| Safety blocks | 0 |
| No-loss-averaging blocks | 0 |

ADD accepted lot distribution:

- lot #1: `7`
- lot #2: `5`
- lot #3: `5`

ADD accepted days:

- `2022-10-06`: 94340, 3 lots
- `2022-10-11`: 94340, 3 lots
- `2022-10-12`: 94320, 3 lots
- `2022-10-13`: 94340, 1 lot
- `2022-10-21`: 94320, 3 lots, semantic mismatch
- `2022-10-28`: 94320, 3 lots
- `2022-11-01`: 94320, 1 lot

### PM / Campaign Lifecycle

PM rows inspected: `482`

| PM Action / Context | Count |
| --- | ---: |
| HOLD | 360 |
| EXIT | 48 |
| REDUCE | 35 |
| ADD | 39 |
| IMPROVEMENT | 147 |
| KNOWN_AT_ENTRY | 70 |
| FRESH_DETERIORATION | 231 |
| PERSISTENT_DETERIORATION | 26 |
| HARD_FAILURE | 8 |
| PM snapshot PASS | 482 |
| AMBIGUOUS_REVIEW_REQUIRED | 0 |

Campaign lifecycle snapshots:

- `campaign_entry_premise_snapshot.v1` PASS observations: `1470`
- PM entry premise snapshot status PASS: `482`
- No PIT violation found in snapshot/delta scan.

This confirms the CW/CY lifecycle premise repair is materially active in this run despite sparse execution BUY rows.

## NEW / REENTRY Conformance

Conformant:

- Candidate eligibility and Production deployability are separated.
- `REDUCED_ALLOCATION_ONLY` remains visible and is not silently re-expanded for NEW/REENTRY positive rows.
- NEW multi-lot target magnitude is active.
- Sub-lot quality ceiling blocks are explicit, with no implicit one-lot rescue.
- Extreme overshoot is blocked by quality-ceiling / cap semantics.
- Cash remains a competing residual allocation rather than an afterthought.

Partial:

- REENTRY candidates are generated (`537`) but no accepted or filled REENTRY appeared in inspected coverage. This is not a defect by itself, but it limits actual-path REENTRY acceptance confidence.
- Runtime Planning still labels positive quantity source as `LEGACY_POSITION_SIZING` for 191 positive plans, even while BF authority is active. This appears to be stale nomenclature/observability rather than an active legacy fallback, because BF fields show `legacy_target_gap_fallback_allowed = false`.

## ADD Conformance

Conformant:

- ADD candidate generation works.
- ADD uses campaign identity.
- Repeated lots materialize and feed BF/PS.
- ADD admission authority generally shows `final_add_eligibility = PASS`.
- No residual ADD target without BF target was observed in the inspected ADD accepted rows.
- No-loss-averaging guard is represented and no no-loss-averaging block count was observed.

Non-conformant residual:

On `2022-10-21`, 94320 ADD lot #1/#2/#3:

- frontier `authority_disposition = ACCEPTED_INCREMENTAL_TARGET`
- `comparison_class = BLOCKED`
- reason includes `opportunity_quality_add_hard_block`
- Runtime Planning: `planning_intent = BUY_ADD`, `planned_quantity = 300`, `marginal_capital_value_class = BLOCKED_OR_NOT_ELIGIBLE`
- execution: 94320 BUY 300 shares

This indicates the final acceptance sequence or BF/PS boundary is allowing an ADD row whose own value-class surface says blocked. Because the underlying `add_investment_evidence.final_add_eligibility = PASS`, this is not the old BZ FAIL_CLOSED admission bug. It is a later common-frontier / value-class consistency defect.

Classification: P1 Architecture semantic mismatch. It may become P0 if the blocked comparison class is confirmed to be authoritative rather than stale diagnostic labeling.

## PM / Campaign Lifecycle Conformance

Conformant:

- Entry premise snapshot is available to PM.
- No PM row fell into `AMBIGUOUS_REVIEW_REQUIRED`.
- KNOWN_AT_ENTRY, FRESH_DETERIORATION, PERSISTENT_DETERIORATION, HARD_FAILURE, and IMPROVEMENT classes all appear.
- Hard failure remains actionable.
- Known entry caution no longer creates a blanket PM halt.
- Full EXIT / REDUCE activity is present.

Partial:

- Execution BUY lineage remains sparse, so lifecycle currently depends on strict-prior strategy artifacts to recover entry premise. Phase32-CY repairs that bridge, but the primary run itself still demonstrates weak execution ledger provenance.

## Capital Behavior

The run shows adaptive capital behavior:

- Early period: exposure starts at 16.93%, drops to 9.91% on 2022-10-04, then slowly redeploys.
- Mid period: exposure rises materially, reaching over 90% in high-deployment stretches.
- Late period: de-risking and redeployment both occur; exposure falls to 43.80% on 2022-12-20 after eight SELL fills, then rises again to 71.18% by 2022-12-26.
- Cash is not fixed: it ranges from 29,870 to 907,880 and is explicitly allocated every day.

This is broadly consistent with:

- weak opportunity -> Cash
- strong opportunity -> deploy
- deterioration -> REDUCE/EXIT
- subsequent opportunity -> redeploy

The main caveat is that execution fills cannot distinguish BUY_NEW from BUY_ADD at the ledger semantic field, so contribution attribution is weaker than the authority chain intends.

## Regime Behavior

The artifacts inspected exposed portfolio policy `entry_posture = MAINTAIN` across the primary aggregation, rather than a rich BEAR/RANGE/RECOVERY/BULL taxonomy. Within that available regime label:

- days: 61
- average exposure: 66.57%
- BUY_NEW fills: 82
- SELL fills: 75
- cash allocation days: 61

Regime responsiveness is therefore PARTIAL: capital behavior is responsive over time, but artifact-level regime classification is too coarse in this run to prove differentiated BEAR/RANGE/RECOVERY/BULL behavior.

## Legacy / Migration Cleanup

| Path / Artifact Surface | Classification | Evidence |
| --- | --- | --- |
| BF aggregated target authority | KEEP | Active Production target source. |
| `canonical_marginal_capital_frontier_authority.v1` | KEEP | Active PC authority, 61/61 days. |
| Shadow frontier | KEEP | `shadow_frontier_remains_non_authoritative = true` on 61 days. |
| Legacy target-gap fallback | REMOVE/KEEP-ZERO | BF fields show fallback forbidden; no fallback-used count observed. |
| Runtime `canonical_quantity_source = LEGACY_POSITION_SIZING` label | MIGRATE | 191 positive plans still carry legacy wording despite BF authority. |
| Execution generic BUY provenance | MIGRATE | 83/83 BUY fills have missing source decision id. |
| Old implicit one-lot rescue | REMOVE | No implicit rescue observed; explicit fail-closed blocks present. |
| Old ADD bridge / residual ADD | MIGRATE | Mostly replaced, but 2022-10-21 blocked-class ADD acceptance requires repair/audit. |

## PIT / Future Information

Scanned:

- frontier authority top-level PIT/outcome flags
- allocation budget authority flags
- ADD admission authority flags
- one-lot authority flags
- PC discrete executable quantity authority flags
- PM entry premise delta flags
- campaign entry premise snapshot flags

Result:

- PIT violation count found: `0`
- historical outcome field used as decision input: not observed
- later-date contamination: not observed in inspected authority artifacts

## Remaining Defects

| Priority | Issue | Evidence | Recommendation |
| --- | --- | --- | --- |
| P1 | ADD blocked-class accepted into Production path | `2022-10-21` 94320 ADD #1/#2/#3 accepted despite `comparison_class = BLOCKED` and Runtime `BLOCKED_OR_NOT_ELIGIBLE`. | Narrow audit/repair of frontier value-class acceptance contract and BF/PS blocking consistency. |
| P1/P3 | BUY execution ledger provenance sparse | 83/83 BUY fills have `source_decision_id = MISSING`, generic `source_decision_type = BUY`. | Ensure CY-style BUY pending provenance reaches order/execution ledger in a fresh validation. |
| P3 | Runtime quantity source label stale | 191 positive plans report `LEGACY_POSITION_SIZING` despite BF authority. | Rename/migrate observability label after confirming no active fallback. |
| P3 | Regime taxonomy too coarse for CZ regime proof | Portfolio policy aggregation surfaced only `MAINTAIN`. | Improve/report regime labels if BEAR/RANGE/RECOVERY/BULL acceptance is required. |

Unresolved P0 count: `0` based on current evidence.

Unresolved P1 count: `2` if sparse BUY provenance is treated as authority lineage, or `1` if treated as observability because CY bridge recovers lifecycle context.

## Final Judgments

PHASE32_CZ_END_TO_END_AUTHORITY_CHAIN = PARTIAL

PHASE32_CZ_INVESTMENT_PHILOSOPHY_CONFORMANCE = PARTIAL

PHASE32_CZ_NEW_REENTRY_CONFORMANCE = PARTIAL

PHASE32_CZ_ADD_CONFORMANCE = PARTIAL

PHASE32_CZ_PM_LIFECYCLE_CONFORMANCE = YES

PHASE32_CZ_CAPITAL_RECYCLING_CONFORMANCE = YES

PHASE32_CZ_REGIME_RESPONSIVENESS = PARTIAL

PHASE32_CZ_CASH_OPTIONALITY_VALID = YES

PHASE32_CZ_WINNER_CAPITALIZATION_VALID = PARTIAL

PHASE32_CZ_LEGACY_ACTIVE_GAPS = runtime_planning_canonical_quantity_source_legacy_label; execution_buy_source_decision_id_missing; 2022-10-21_94320_add_blocked_class_accepted

PHASE32_CZ_PIT_CONTRACT = PASS

PHASE32_CZ_UNRESOLVED_P0_COUNT = 0

PHASE32_CZ_UNRESOLVED_P1_COUNT = 2

PHASE32_CZ_PRODUCTION_CHANGE_JUSTIFIED = PARTIAL

PHASE32_CZ_LONG_VALIDATION_CONTINUE = YES

PHASE32_CZ_NEXT_STEP = Run a narrow READ-ONLY trace of 2022-10-21 94320 ADD value-class acceptance and BF/PS propagation, then repair only the blocked-class acceptance boundary if confirmed authoritative; separately validate that post-CY fresh BUY pending provenance reaches execution ledger.
