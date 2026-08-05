# Phase27-AR1 — Phase27-A Evidence Consolidation and Architecture / Strategy Review Pack

## 1. Scope

Task ID: Phase27-AR1

Task Type:

```text
Read-only Evidence Consolidation
Architecture / Strategy Review Preparation
```

Primary Judgment:

```text
PHASE27_AR1_REVIEW_PACK_COMPLETE_WITH_LIMITATIONS
```

Baseline:

```text
Run ID: runtime-test-historical-smoke-20260804T074611098414Z
Period: 2023-01-04 through 2023-05-31
Business Days: 100
```

This review pack does not design improvements, recommend implementation, propose thresholds, propose formulas, propose weights, or modify Strategy / Runtime logic.

## 2. Safety Boundary

No implementation changed.

No Strategy, Candidate, Opportunity, BUY Quality, Portfolio Policy, Portfolio Construction, Position Sizing, Planning, Submit, Safety, PM, Exit, or Re-entry logic was changed.

No fresh-run, resume, Historical, 10BD, 100BD, or long regression was executed.

`.runtime` was not used as canonical evidence.

## 3. Overall Timeline

| Task | Objective | Judgment | Main Finding | Remaining Uncertainty |
|---|---|---|---|---|
| A1 | Inventory run-scoped 100BD evidence | `PHASE27_A1_EVIDENCE_INVENTORY_COMPLETE_ATTRIBUTION_READY_WITH_LIMITATIONS` | 100 daily dirs and key artifacts complete; 5,000 Quality decisions; 25 BUYs; 45 SELLs | Full candidate universe missing; fill direct IDs missing |
| A2 | Baseline attribution and hypothesis extraction | `PHASE27_A2_BASELINE_ATTRIBUTION_COMPLETE_PARTIAL_ROOT_CAUSES_IDENTIFIED` | PF 0.8385; re-entry losses confirmed; rank/quality/capital/exit partially implicated | Root causes not yet separated |
| A3 | Re-entry causality and selection validity | `PHASE27_A3_REENTRY_PARTIALLY_EXPLAINED` | Re-entry losses reflect selection, whipsaw, exit interaction; 93180 is outlier | Re-entry logic alone not proven wrong |
| A4 | Opportunity / Quality / final selection discrimination | `PHASE27_A4_SELECTION_DISCRIMINATION_PARTIALLY_VALID_IMPROVEMENT_TARGETS_IDENTIFIED` | 0/25 clearly stronger available candidates ignored; only 3/25 best available | Full candidate universe unavailable |
| A5 | Higher-ranked ineligibility and Quality component diagnosis | `PHASE27_A5_INELIGIBILITY_DIAGNOSIS_COMPLETE_MULTI_STAGE_INTERACTION_IDENTIFIED` | Higher-ranked dropout mostly existing-position zero-delta; Quality Reject not primary | ADD vs HOLD philosophy unresolved |
| A6 | Incremental eligibility and fallback selection diagnosis | `PHASE27_A6_INCREMENTAL_ELIGIBILITY_DIAGNOSIS_COMPLETE_CURRENT_LOGIC_PARTIALLY_VALID` | 18 moderate incremental cases; 7 weak/relative-only; No-BUY valid; no forced deployment | Explicit buy-vs-cash eligibility not present |

## 4. Evidence Inventory

| Finding | Evidence | Confidence | Status |
|---|---|---|---|
| Attribution-ready evidence exists with limitations | 100 daily dirs; 5,000 Quality decisions; 25 BUYs; 45 SELLs | HIGH | Partially Confirmed |
| Baseline underperformed | Final equity 984,580; return -15,420; PF 0.8385 | HIGH | Confirmed |
| Re-entry losses were material | Re-entry gross loss -173,870; 93180 PnL -120,600 | HIGH | Confirmed |
| Re-entry logic alone was not proven wrong | A3: 1 valid, 6 questionable, 3 whipsaw, 1 insufficient | MEDIUM | Partially Confirmed |
| Clearly stronger executable observed candidates were not ignored | A4: selected-despite-clearly-stronger count 0/25 | MEDIUM | Rejected alternative |
| System did not always buy best available observed-funnel candidate | A4: best available 3/25 | HIGH | Confirmed |
| Higher-ranked dropout was mainly existing-position zero-delta | A5: 40/63 higher-ranked rows | HIGH | Confirmed |
| Quality Reject was not primary cause | A5 rejected excessive Quality Reject hypothesis | MEDIUM | Rejected |
| Active implicit buy pressure was not found | A6: no fixed minimum BUY count, no forced deployment consumer | MEDIUM | Rejected alternative |
| No-BUY / cash retention is valid | 79/100 days had zero BUY; NO_ACTION/NO_ORDER supported | HIGH | Confirmed |
| Explicit incremental investment eligibility is not present | A6: Quality is allocation eligibility/scaling, not selected-vs-cash authority | MEDIUM | Partially Confirmed |
| Full candidate-universe superiority cannot be claimed | Candidate universe not copied as canonical run-scoped evidence | HIGH | Insufficient Evidence |

## 5. Architecture Review

| Component | Review | Evidence |
|---|---|---|
| Runtime | Healthy | Phase26 closure PASS; no A1-A6 defect evidence |
| Current | Healthy | Current/Ledger/Broker Authority PASS; valuation evidence complete |
| Ledger | Healthy | Fills and realized slices reconcile; direct BUY IDs missing but joins usable |
| Temporal | Healthy | PIT/future-information boundary preserved |
| Accepted Generation | Healthy | Phase26 closure PASS |
| Candidate | Open Question | Full candidate universe missing as canonical run-scoped evidence |
| Opportunity | Minor Concern | Score ordering exists but compression and weak buckets remain |
| BUY Quality | Minor Concern | Propagates correctly, but FULL underperformed REDUCED post-hoc |
| Portfolio Policy | Healthy | Cash retention valid; no forced deployment |
| Portfolio Construction | Minor Concern | No clearly stronger available candidate ignored; fallback/zero-delta interaction remains |
| Position Sizing | Minor Concern | Mostly upstream zero-weight propagation; some lot/minimum effects |
| Planning | Healthy | NO_ACTION / NO_ORDER supported |
| Submit | Healthy | No forced deployment or active defect found |
| PM | Open Question | ADD/HOLD/Exit philosophy under-evidenced |
| Exit | Open Question | MFE/MAE and exact PM sell reasons unavailable |
| Performance Toolkit | Healthy | Run-scoped, post-hoc, not Strategy input |

No explicit Architecture Defect is raised by AR1.

## 6. Strategy Review

| Topic | Review | Evidence |
|---|---|---|
| Candidate quality | Unknown | Full candidate universe unavailable |
| Opportunity discrimination | Possible Weakness | Score buckets ordered but compressed; Rank 2 and 6-10 weak post-hoc |
| Quality discrimination | Possible Weakness | FULL PnL -130,410 vs REDUCED +82,890; causality not proven |
| Portfolio Construction | Confirmed Strength | 0/25 clearly stronger available observed candidates ignored |
| Capital deployment | Possible Weakness | High cash was multi-causal |
| Existing Position handling | Possible Weakness | 40/63 higher-ranked ineligibility rows were zero-delta |
| Re-entry | Possible Weakness | Re-entry losses material, especially 93180 |
| Exit | Unknown | Exit partially implicated; MFE/MAE missing |
| Holding | Unknown | Holding days known, but giveback path unavailable |
| Fallback selection | Possible Weakness | 22/25 fallback or near-tie; 7 weak/relative-only incremental cases |

## 7. What We Have Ruled Out

Evidence-backed rejected or unsupported explanations:

- Portfolio Construction randomly selected weak candidates.
- Portfolio Construction repeatedly ignored clearly stronger executable observed-funnel candidates.
- Forced BUY count exists.
- Forced cash deployment exists.
- Fixed `target_position_count` remained an active invalid BUY decision consumer.
- BUY Quality was simply too conservative as the primary cause.
- Position Sizing alone was the primary cause.
- Re-entry logic alone was proven to be the root cause.
- Cash being high automatically means implementation failure.
- Quality Score or Opportunity Score can be treated as expected return.

## 8. Remaining Open Questions

Prioritized review questions:

1. Should strong existing positions become ADD candidates instead of zero-delta blockers?
2. Does Strategy need explicit incremental investment eligibility distinct from relative ranking and Quality eligibility?
3. How should BUY vs HOLD CASH be compared when No-BUY is contractually valid?
4. What is the correct re-entry philosophy?
5. What is the correct exit and holding philosophy?
6. Should BUY and ADD share the same decision logic?
7. How much cash should be acceptable in weak opportunity environments?

AR1 does not answer these questions. It prepares them for review.

## 9. Evidence Limitations

Key limitations:

- Full candidate universe is missing as canonical run-scoped evidence.
- BUY fill rows lack direct `pending_item_id`, `order_plan_item_id`, and `quality_decision_id`.
- Many subgroup findings are small-sample: 25 BUYs and 11 re-entry campaigns.
- PM intent, ADD/HOLD reasoning, and exact sell reasoning are only partially joinable.
- MFE/MAE and winner giveback are unavailable.
- No virtual PnL was generated for unbought candidates, No-BUY, or alternate choices.
- Capital impact is only partially quantified.

## 10. Design Review Topics

Neutral topics for Phase27 review:

| Topic | Review Question |
|---|---|
| Momentum philosophy | What level of absolute Opportunity strength should matter beyond relative rank? |
| Capital deployment philosophy | When is high cash acceptable rather than a failure? |
| Position management philosophy | Should strong existing holdings be ADD candidates, HOLD-only, or no-delta blockers? |
| Re-entry philosophy | How should valid trend re-entry be separated from whipsaw? |
| Cash philosophy | How should Strategy compare weak BUY candidates against cash retention? |
| Incremental investment philosophy | Should selected-vs-cash eligibility become an explicit concept? |

These are discussion topics only.

## 11. Recommended Review Agenda

1. Runtime and architecture closure boundary
2. Evidence limitations
3. Opportunity discrimination
4. BUY Quality semantics
5. Portfolio Construction and existing positions
6. Re-entry and exit interaction
7. Capital deployment and cash philosophy
8. Incremental eligibility
9. Phase27-B candidate themes

## 12. Phase27-B Candidate Topics

Candidate topics for discussion only:

| Topic | Classification |
|---|---|
| Incremental investment eligibility | Performance Design Candidate |
| Existing-position ADD/HOLD philosophy | Strategy Review Topic |
| Re-entry philosophy | Strategy Review Topic |
| Exit / holding diagnosis | Additional Diagnosis Candidate |
| Opportunity score compression | Performance Design Candidate |
| Cash deployment philosophy | Strategy Review Topic |

No Phase27-B implementation is recommended or authorized by AR1.

## 13. Deliverables

Output directory:

```text
reports/phase27_ar1_phase27a_review_pack/
```

Files:

```text
summary.json
phase27_findings_matrix.json
architecture_review.json
strategy_review.json
confirmed_findings.json
rejected_hypotheses.json
remaining_questions.json
evidence_limitations.json
review_agenda.json
phase27b_candidate_topics.json
test_results.json
```

## 14. Final Judgment

```text
PHASE27_AR1_REVIEW_PACK_COMPLETE_WITH_LIMITATIONS
```

The limitation is not a failure of AR1. It reflects Phase27-A's known evidence boundary: full candidate-universe data, direct fill IDs, PM intent details, and MFE/MAE are not fully available as canonical run-scoped evidence.
