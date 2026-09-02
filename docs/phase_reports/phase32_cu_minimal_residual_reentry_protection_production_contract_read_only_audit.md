# Phase32-CU — Minimal Residual REENTRY Protection Production Contract READ-ONLY Audit

## Scope

This is a READ-ONLY Production contract audit. No source code, configuration, runtime state, Pending state, Ledger state, run artifact, resume, recover, replay, or fresh-run was changed or executed.

Primary actual-path run:

- `runtime-test-historical-extended-smoke-20260901T205837445258Z`

Supporting long-horizon evidence:

- `runtime-test-historical-extended-smoke-20260831T234344371102Z`

Pre-CO evidence is interpreted only through the Phase32-CN strict-prior semantic reconstruction principle. Historical PnL, later returns, future price, MFE/MAE, final campaign outcome, and selected/bought outcome were not used to choose semantics.

## References

Mandatory phase reports read:

- `docs/phase_reports/phase32_co_prior_exit_semantic_provenance_production_repair.md`
- `docs/phase_reports/phase32_cp_reentry_temporal_lifecycle_prior_campaign_relevance_read_only_audit.md`
- `docs/phase_reports/phase32_cq_reentry_time_renewed_pit_new_equivalent_lifecycle_shadow_contract_design.md`
- `docs/phase_reports/phase32_cr_fixed_temporal_floor_necessity_vs_evidence_based_reentry_release_shadow_audit.md`
- `docs/phase_reports/phase32_cs_post_co_first_divergence_reentry_actual_path_causal_audit.md`
- `docs/phase_reports/phase32_ct_reentry_dedicated_penalty_necessity_legacy_safety_mechanism_read_only_audit.md`

Architecture / SoT reviewed:

- `docs/02_architecture/strategy_intelligence_architecture_v1.md`
- `docs/02_architecture/strategy_architecture_v1.md`
- `docs/02_architecture/dual_path_market_quality_and_capital_competition_contract.md`
- `docs/02_architecture/portfolio_construction_and_position_sizing_contract.md`

Source reviewed:

- `src/ai_fund_lab_v2/strategy/portfolio_construction.py`
- `src/ai_fund_lab_v2/strategy/runtime_planning.py`
- `src/ai_fund_lab_v2/strategy/strategy_intelligence.py`
- relevant REENTRY / CK / G129 tests

## CT Direction

`CT_DIRECTION_PRESERVED = YES`

CU preserves CT's architectural direction:

- Keep REENTRY lineage and campaign audit history.
- Keep authoritative prior EXIT reason and reason-code consumption.
- Keep generic/missing prior context fail-closed / REVIEW_REQUIRED.
- Keep short-horizon churn protection.
- Keep prior-cause recovery context.
- Keep HARD_STOP enhanced recovery.
- Remove or migrate REENTRY-specific rank penalty, BQ/quality penalty, long-lived time penalty, and prior-ownership capital competition discount.

No repository evidence contradicted CT.

## Current REENTRY Gate Source Map

`CURRENT_REENTRY_GATE_SOURCE_MAP`:

| Gate | Source | Function / boundary | Condition | Input authority | Downstream consumer | Duplicates ordinary BUY authority |
| --- | --- | --- | --- | --- | --- | --- |
| Semantic REENTRY identity | `portfolio_construction.py:1407-1439` | `_semantic_reentry_evidence` | flat symbol with strict-prior `prior_exit_business_date < business_date` | prior EXIT materialized by `shadow_runtime` / candidate row | PC member, semantic authority, runtime lineage | No |
| Immediate cooldown | `portfolio_construction.py:70`, `1421-1423`, `1639-1657` | `_semantic_reentry_evidence`, `_canonical_reentry_semantic_eligibility` | `business_days_since_exit >= 3`, else `FAIL_CLOSED` | business calendar + prior EXIT date | PC target zeroing, reason `semantic_reentry_cooldown_blocked` | No, but insufficient as sole churn guard |
| Prior context generic/missing | `portfolio_construction.py:1493-1495`, `1620-1630` | `_reentry_recovery_evidence`, `_canonical_reentry_semantic_eligibility` | generic/empty/UNKNOWN/EXIT/SELL prior reason | CO-restored prior EXIT context | REVIEW_REQUIRED / prior-context block | No |
| REENTRY rank/requalification | `portfolio_construction.py:1443`, `1496-1499`, `1548-1549` | `_reentry_recovery_evidence` | rank missing -> review; rank > 10 -> fail | current opportunity rank | recovery PASS/FAIL, PC target zeroing | Yes |
| REENTRY BQ/quality gate | `portfolio_construction.py:1445`, `1500-1503` | `_reentry_recovery_evidence` | BQ must be `REDUCED_ALLOCATION_ONLY` or `FULL_ALLOCATION_ELIGIBLE` | current Buy Quality | recovery PASS/FAIL, PC target zeroing | Yes |
| Corporate action / broker / safety | `portfolio_construction.py:1460-1461`, `1504-1507`, `1591-1593`, `1697-1705`, `1821-1838` | `_reentry_recovery_evidence`, `_canonical_reentry_semantic_eligibility`, `_reentry_broker_eligibility_status`, `_reentry_safety_status` | blocking CA/broker/safety fails or reviews | current PIT CA/broker/safety evidence | PC member, runtime lineage, Pending/Submit safety | Mostly no; keep as ordinary safety separation |
| Liquidity / capacity | `portfolio_construction.py:1234-1239`, `1508-1511` | `_resolve_low_price_reentry_allocation_guard`, `_reentry_recovery_evidence` | missing capacity reviews; severe or >3% capacity fails | current traded-value / PC notional | PC target cap or fail | Yes as current BUY capacity, not REENTRY-specific |
| Entry Admission | `portfolio_construction.py:1448-1451`, `1512-1520`; `strategy_intelligence.py:1419-1488` | `_reentry_recovery_evidence`, `_entry_admission` | BUY_WAIT / REJECT / REVIEW_REQUIRED / NO_ADD and insufficient evidence block | ordinary Entry Admission | recovery PASS/FAIL | Yes as ordinary current entry timing |
| Continuation Quality / downside | `portfolio_construction.py:1452-1458`, `1521-1524` | `_reentry_recovery_evidence` | non-PASS/OK/ACCEPTABLE blocks | Strategy Intelligence CQ/downside | recovery PASS/FAIL | Yes as ordinary quality/risk |
| Repeated unresolved churn | `portfolio_construction.py:1459`, `1525-1528` | `_reentry_recovery_evidence` | prior exits >=2 and unresolved context/entry/technical recovery | prior same-symbol campaign history + current PIT | recovery fail | No; unique residual safety |
| Trend/momentum recovery | `portfolio_construction.py:1525-1536` | `_reentry_recovery_evidence` | TREND_MOMENTUM/HARD_STOP/CA require trend and momentum evidence | current PIT technicals + prior EXIT class | recovery PASS/FAIL | Partly; keep as prior-cause recovery context |
| HARD_STOP new thesis | `portfolio_construction.py:1537-1538` | `_reentry_recovery_evidence` | HARD_STOP requires `FULL_ALLOCATION_ELIGIBLE` | prior EXIT class + current BQ | recovery fail | No for HARD_STOP-specific residual guard |
| Portfolio-competition prior cause | `portfolio_construction.py:1539-1540` | `_reentry_recovery_evidence` | rank > 5 fails for prior portfolio competition | current rank + prior class | recovery fail | Migrate; rank is ordinary capital competition evidence |
| REVERSAL normalization | `portfolio_construction.py:1541-1543` | `_reentry_recovery_evidence` | entry state must normalize | Entry Admission | recovery fail | Keep as prior-cause context |
| Eligibility maps to PC target zero | `portfolio_construction.py:1271-1286` | `_resolve_low_price_reentry_allocation_guard` | any non-PASS REENTRY eligibility zeroes target | semantic eligibility | PC member target, runtime planning | Keep for residual guards; remove broad penalty triggers |
| Buy-new bypass guard | `portfolio_construction.py:5942-5980` | `_blocked_reentry_buy_new_reason` | REENTRY with non-PASS authority cannot enter NEW_BUY competition | PC semantic authority | budget reconciliation, capital competition, lot rebatch | No; CK invariant |
| Runtime lineage propagation | `runtime_planning.py:1038-1074`, `1308-1315`, `1516-1525` | `_compact_reentry_summary` / runtime authority lineage | PC REENTRY authority copied into runtime planning lineage | PC member | Pending/Submit/runtime evidence | No |
| SI lifecycle shadow label | `strategy_intelligence.py:1419`, `1761-1762` | `_entry_admission`, `_strategy_intelligence_interpretation` | lifecycle intent set to REENTRY when semantic context says REENTRY | lifecycle context | shadow evidence only | No action authority |
| PS one-lot / sizing semantic preservation | `position_sizing.py` and PC lot authority | REENTRY treated as BUY_NEW-like zero-to-one-lot semantic for lot authority | PC/PS semantic type | PS/runtime quantity | No; preserve classification |

## Gate Legacy Classification

`REENTRY_GATE_LEGACY_CLASSIFICATION`:

| Gate | Classification | Contract |
| --- | --- | --- |
| Semantic REENTRY identity | `KEEP` | permanent lifecycle/provenance classification |
| Prior campaign id / prior EXIT date / prior reason / reason codes | `KEEP` | required strict-prior authority |
| Generic/missing prior context fail-closed | `KEEP` | no silent BUY_NEW fallback |
| Existing 3BD immediate cooldown | `KEEP` | immediate churn floor |
| Additional broad time penalty | `REMOVE` | no permanent or long-lived prior-ownership penalty |
| REENTRY rank <=10 hurdle | `MIGRATE` | current rank belongs to ordinary BUY/capital competition; not a REENTRY-only penalty |
| REENTRY BQ eligible gate | `MIGRATE` | current BQ belongs to ordinary BUY authority |
| Entry Admission / CQ / downside checks | `MIGRATE` | ordinary current opportunity quality/risk authority |
| Capacity / liquidity | `MIGRATE` | ordinary BUY capacity authority |
| Trend/momentum recovery by prior class | `KEEP` | prior-cause recovery context |
| Repeated unresolved churn | `KEEP` | unique residual safety |
| HARD_STOP full-quality/new-thesis guard | `KEEP` | unique residual safety |
| Portfolio-competition rank <=5 | `MIGRATE` | relative opportunity belongs to ordinary capital competition |
| REVERSAL normalization | `KEEP` | prior-cause context through Entry Admission |
| CK buy-new bypass guard | `KEEP` | prevents blocked REENTRY from relabeling as BUY_NEW |
| Runtime/PS lineage propagation | `KEEP` | auditability and downstream authority |
| Legacy shadow-only compatibility fields/tests that assert permanent penalty | `DEPRECATE` | remove after production contract migration |

## Target REENTRY Definition

`TARGET_REENTRY_SEMANTIC_DEFINITION`:

REENTRY is a lifecycle/provenance classification for a currently flat symbol that has a strict-prior closed same-symbol campaign. It preserves prior campaign lineage, prior EXIT semantics, and auditability. REENTRY is not, by itself, a reason for lower rank treatment, lower Buy Quality treatment, lower capital priority, long-lived suppression, or literal relabeling to BUY_NEW.

After residual safety gates pass, REENTRY enters ordinary current BUY authority and capital competition on neutral terms.

## Prior EXIT Context Contract

`PRIOR_EXIT_CONTEXT_CONTRACT`:

| Field | Requirement | Missing behavior |
| --- | --- | --- |
| `prior_campaign_id` / `prior_exit_campaign_id` | Required for REENTRY | REVIEW_REQUIRED / fail-closed, no BUY_NEW fallback |
| `prior_exit_business_date` | Required | fail-closed, no temporal inference |
| `prior_exit_decision_type` | Required, normally `EXIT` / SELL full-exit semantic | REVIEW_REQUIRED if ambiguous |
| `prior_exit_reason` / `previous_exit_reason` | Required semantic scalar | generic/empty/EXIT/SELL/UNKNOWN => REVIEW_REQUIRED |
| `prior_exit_reason_codes` / `previous_exit_reason_codes` | Required when scalar is not enough to classify | REVIEW_REQUIRED if absent and scalar is generic |
| `prior_exit_reason_class` | Derived required classification | must derive from authoritative scalar/codes |
| `source_pm_decision_id` | Required where PM EXIT was authority | REVIEW_REQUIRED if canonical upstream exists but id is absent |
| `source_decision_id` | Required lifecycle/source provenance | REVIEW_REQUIRED if canonical upstream exists but id is absent |
| prior campaign audit history | Optional for richer diagnostics | analytics-only unless needed for repeated churn count |
| prior PnL / future outcome | Forbidden as decision input | not consumed |

## Short Churn Guard

`SHORT_CHURN_GUARD_AUTHORITY`:

The existing owner is Portfolio Construction semantic REENTRY authority:

- `REENTRY_COOLDOWN_BUSINESS_DAYS = 3`
- `_semantic_reentry_evidence` computes `business_days_since_exit`.
- `_canonical_reentry_semantic_eligibility` maps non-PASS cooldown to `REENTRY_NOT_ELIGIBLE_CHURN_PROTECTION`.
- `_reentry_recovery_evidence` also blocks repeated unresolved same-symbol churn using prior exit count plus current unresolved PIT evidence.

This protects immediate rebuy / unresolved same-thesis oscillation. CR shows the current 3BD floor prevents `0-3BD` active churn escape, but it may not be sufficient to prove independence for all `4-10BD` rebounds. CU does not introduce a new fixed day count; it requires the future implementation to keep the existing 3BD hard floor and repeated-unresolved-churn guard, and to express any additional near-term thesis-continuity guard through existing PIT evidence and focused negative controls rather than Historical returns.

`NEW_CHURN_THRESHOLD_REQUIRED = NO_FOR_CU`

CU is implementation-ready without selecting a new numeric churn threshold. If a future implementation cannot constrain CR's five `4-10BD` cases using the existing 3BD floor plus repeated-unresolved-churn / prior-cause evidence, it must stop and request a separate threshold design; CU does not authorize inventing one.

## Prior-Cause Recovery

`PRIOR_CAUSE_RECOVERY_CONTRACT`:

Prior cause is context, not a permanent penalty.

| Prior EXIT class | Target contract |
| --- | --- |
| `TREND_MOMENTUM` | Require current trend and momentum recovery from decision-time PIT evidence; after recovery passes, ordinary current rank/BQ/Entry/PC decide capital. |
| `HARD_STOP` | Keep stricter new-thesis treatment; ordinary trend/momentum is insufficient by itself. |
| `CORPORATE_ACTION` | Require resolved same-run corporate-action authority; do not infer recovery from price/rank. |
| `REVERSAL` | Require Entry Admission normalization; unresolved reversal/timing remains blocked. |
| `PORTFOLIO_COMPETITION` | Require renewed relative opportunity through ordinary capital competition; do not retain special rank <=5 penalty as a REENTRY-only rule. |
| Administrative / non-investment EXIT | No special recovery treatment once authoritative non-investment classification is present, safety is clear, and ordinary BUY authority passes. |
| Generic / missing | REVIEW_REQUIRED / fail-closed. |

## HARD_STOP Contract

`HARD_STOP_REENTRY_CONTRACT`:

HARD_STOP remains separate from TREND_MOMENTUM. Minimum existing evidence before HARD_STOP REENTRY can pass:

- strict-prior prior campaign id and prior EXIT date;
- authoritative HARD_STOP prior EXIT reason or reason code;
- current BQ `FULL_ALLOCATION_ELIGIBLE`;
- current trend recovery and momentum recovery;
- Entry Admission not BUY_WAIT / REJECT / REVIEW_REQUIRED / NO_ADD;
- CQ and downside acceptable when present;
- safety, broker, corporate action, and capacity non-blocking;
- no repeated unresolved churn.

No new model, feature, or score is required.

## Ordinary BUY Authority Integration

`ORDINARY_BUY_AUTHORITY_FOR_REENTRY`:

| Dimension | Ordinary owner |
| --- | --- |
| current rank / opportunity | Candidate / Opportunity evidence and PC capital competition |
| Buy Quality | BQ producer and ordinary PC allocation cap |
| Entry timing | Strategy Intelligence Entry Admission |
| continuation quality | Strategy Intelligence Continuation Quality |
| downside | Strategy Intelligence Downside Risk |
| capacity / liquidity | PC low-price / liquidity capacity authority and PS feasibility |
| cash / budget | PC capital competition and budget reconciliation |
| lot / quantity | Position Sizing and Runtime Planning |
| safety / broker / corporate action | dedicated safety/broker/CA authorities |

The target contract avoids checking the same quality dimension twice solely because the symbol is REENTRY-lineage.

## Rank Contract

`REENTRY_RANK_PENALTY_REMOVAL_CONTRACT`:

Remove the REENTRY-only `rank <= 10` recovery hurdle as an independent penalty. Replace it with ordinary current opportunity evidence:

- rank may remain materialized in REENTRY evidence for diagnostics and current opportunity context;
- current rank still affects candidate eligibility, PC membership, capital competition, and no-deployable-opportunity decisions;
- a REENTRY row must not be rejected solely because it fails a stricter REENTRY-only rank cutoff if it passes ordinary current BUY authority and residual REENTRY safety gates.

Do not alter the base rank model, base thresholds, or candidate ordering.

## BQ / Quality Contract

`REENTRY_BQ_QUALITY_PENALTY_REMOVAL_CONTRACT`:

Remove REENTRY-specific BQ/quality treatment as an independent penalty. Reuse ordinary BQ, Entry Admission, CQ, downside, liquidity/capacity, and PC/PS feasibility. BQ may still block, reduce, or cap allocation exactly as it does for ordinary current BUY authority; it must not be applied a second time only because the symbol is REENTRY-lineage.

HARD_STOP is the exception: current `FULL_ALLOCATION_ELIGIBLE` remains part of the HARD_STOP enhanced-recovery guard because it is prior-cause-specific, not a broad REENTRY quality penalty.

## Time Logic Final Disposition

`REENTRY_TIME_LOGIC_FINAL_DISPOSITION`:

| Time logic | Disposition |
| --- | --- |
| strict-prior date `prior_exit_business_date < business_date` | `KEEP` |
| existing 3BD cooldown | `KEEP` |
| repeated unresolved churn based on prior same-symbol history | `KEEP` |
| elapsed time as supporting evidence of independence | `KEEP_AS_CONTEXT` |
| fixed 60BD hard floor | `DO_NOT_PROMOTE_FROM_SHADOW` |
| permanent prior-ownership time penalty | `REMOVE` |
| relabel old REENTRY as literal BUY_NEW after time passes | `REMOVE` |

## Capital Competition Contract

`REENTRY_CAPITAL_COMPETITION_FINAL_CONTRACT`:

After residual safety gates pass:

- no REENTRY bonus;
- no REENTRY discount;
- no NEW bonus;
- no forced allocation;
- no old-campaign capital handicap;
- compare current marginal opportunity only;
- preserve REENTRY lineage and create a new campaign if filled after full prior EXIT.

This matches the capital competition SoT: eligible re-entry behaves as ordinary `NEW_BUY` capital competitor while preserving lifecycle semantics.

## Classification Boundary

`BUY_NEW_REENTRY_CLASSIFICATION_BOUNDARY`:

Do not relabel REENTRY as BUY_NEW to bypass restrictions. PC must retain `semantic_buy_type = REENTRY` and pass semantic eligibility into Runtime lineage. Runtime Planning may still emit a BUY / BUY_NEW order intent for a post-full-exit buy, but the PC authority must retain REENTRY lineage, prior campaign id, prior EXIT date/reason, and source provenance.

## Invariants

`BUY_ADD_G129_INVARIANT`:

The target cleanup does not touch active-position detection, PM ADD intent, ADD campaign inheritance, PC/PS ADD materialization, BUY_ADD sizing, or G129 order-increment semantics. Current source classifies current-position ADD as `BUY_ADD` / not REENTRY, and tests already assert ADD is not blocked by REENTRY cooldown and BUY_ADD quantity remains order-increment scoped.

`CK_BYPASS_GUARD_INVARIANT`:

Blocked REENTRY must never become BUY_NEW by omission. `_blocked_reentry_buy_new_reason` must remain or be migrated equivalently so any REENTRY with non-PASS residual authority is excluded from NEW_BUY capital competition and cannot silently rebatch into BUY_NEW.

`CO_PRIOR_EXIT_PROVENANCE_INVARIANT`:

All proposed paths continue consuming CO-restored authoritative non-generic prior EXIT semantics. Generic scalar action labels must not override PM/campaign reason codes. Missing semantic authority remains REVIEW_REQUIRED.

`MISSING_CONTEXT_FAIL_CLOSED_CONTRACT`:

When a prior campaign exists but authoritative prior EXIT context cannot be resolved, the row remains semantically REENTRY and is REVIEW_REQUIRED / fail-closed. It must not silently fall back to BUY_NEW, rank-only selection, or current BQ-only selection.

## Positive And Negative Controls

`83060_TARGET_CONTRACT_RESULT`:

The target contract should permit post-CO `83060` on `2022-10-25`:

- prior class `TREND_MOMENTUM`;
- prior EXIT `2022-10-04`;
- elapsed `14BD`;
- non-generic prior reason restored by CO;
- current trend/momentum/BQ/Entry/CQ/downside evidence valid;
- ordinary capital competition allowed;
- no extra rank/capital penalty solely from prior ownership.

Later PnL was not used.

`CR_NEAR_TERM_FIVE_TARGET_CONTRACT_RESULT`:

The CR `4-10BD` five cases are negative/safety controls. They should be constrained by the residual near-term churn / same-thesis guard unless existing PIT evidence can explicitly prove independence without a new threshold. The intended blocker is not broad permanent REENTRY penalty; it is a narrow short-horizon churn contract plus prior-cause recovery evidence.

## Legacy Removal Scope

`LEGACY_REMOVAL_SCOPE`:

Code candidates:

- `portfolio_construction._reentry_recovery_evidence`: remove or migrate `rank > 10` as REENTRY-only failure.
- `portfolio_construction._reentry_recovery_evidence`: migrate broad BQ, capacity, Entry Admission, CQ, downside checks into ordinary BUY authority references instead of separate REENTRY penalty failures.
- `portfolio_construction._reentry_recovery_evidence`: migrate `PORTFOLIO_COMPETITION` rank <=5 to ordinary capital competition.
- `portfolio_construction._canonical_reentry_semantic_eligibility`: add explicit residual-safety vs ordinary-current-authority composition so `REENTRY_ELIGIBLE` does not mean all ordinary quality was double-checked.
- `portfolio_construction._resolve_low_price_reentry_allocation_guard`: stop zeroing REENTRY target for migrated ordinary gates when ordinary PC already made the capital decision.
- capital competition helpers: preserve CK blocking for residual non-PASS REENTRY only.

Tests:

- update L16/Z tests that encode rank <=10 or broad BQ as REENTRY-only penalties;
- add neutral capital competition tests for eligible REENTRY;
- keep generic context, cooldown, HARD_STOP, repeated churn, CK bypass, and G129 tests.

Config/schema/docs:

- no new config threshold in CU;
- schema may need explicit residual state names such as `REENTRY_RESIDUAL_PROTECTION_PASS` vs ordinary BUY authority pass;
- update Strategy Intelligence / PC SoT to state prior ownership is not a capital discount;
- deprecate shadow-only compatibility text implying fixed 60BD or permanent prior-ownership penalty.

## Migration Strategy

`MIGRATION_STRATEGY = ATOMIC`

The implementation can be atomic because the source map is localized around PC semantic eligibility/recovery and downstream lineage consumers already preserve REENTRY semantics. A staged migration is unnecessary unless future implementation discovers that CR's near-term controls cannot be expressed without a new threshold.

## Focused Validation Matrix

`FOCUSED_VALIDATION_MATRIX`:

| Case | Expected |
| --- | --- |
| genuine BUY_NEW no prior EXIT | not REENTRY; unchanged PC/PS/runtime path |
| valid TREND_MOMENTUM REENTRY like 83060 | residual protection PASS; ordinary capital competition allowed |
| invalid `0-3BD` short-churn REENTRY | fail-closed as churn protection |
| CR `4-10BD` negative controls | constrained by near-term churn / same-thesis protection unless explicit independence exists |
| `21-40BD` high-confidence renewed opportunity | no broad time/rank/capital penalty solely from prior ownership |
| HARD_STOP insufficient recovery | fail-closed |
| HARD_STOP valid recovery | pass only with stricter existing evidence |
| generic/missing prior context | REVIEW_REQUIRED / fail-closed |
| corporate-action prior cause unresolved | fail-closed / review under CA authority |
| Entry Admission BUY_WAIT | ordinary BUY authority blocks, not REENTRY duplicate penalty |
| BQ reject | ordinary BQ blocks, not REENTRY duplicate penalty |
| weak current candidate | ordinary PC/candidate authority blocks |
| CK blocked REENTRY no BUY_NEW bypass | blocked REENTRY cannot enter NEW_BUY competition |
| BUY_ADD/G129 | unchanged |
| capital competition neutrality | eligible REENTRY has no bonus/discount vs current marginal opportunity |
| Runtime lineage | semantic REENTRY evidence materialized into runtime planning |
| missing provenance with otherwise good current evidence | REVIEW_REQUIRED, no fallback |

## Post-Implementation Validation Plan

`POST_IMPLEMENTATION_FRESH_VALIDATION_PLAN`:

Correctness validation:

- focused unit/regression tests for the matrix above;
- non-long actual-path short run or existing focused reproduction through the first post-CO REENTRY event;
- verify 83060 positive control, immediate churn negatives, CK, CO, and G129.

Performance characterization:

- long Historical only after semantic correctness is accepted;
- do not use long Historical PnL to tune churn threshold, rank, BQ, Entry Admission, or Candidate AI.

## Production Decision

`NEW_COMPONENT_REQUIRED = NO`

`NEW_MODEL_REQUIRED = NO`

`NEW_FEATURE_REQUIRED = NO`

`IMPLEMENTATION_READY = YES`

`PRODUCTION_CHANGE_JUSTIFIED = YES`

Reason: CT direction survives source-level review. Current code still contains REENTRY-only rank/BQ/quality/capital-adjacent gates that duplicate ordinary current BUY authority after CO restored prior EXIT semantics. The minimal Production contract is precise enough to implement inside existing PC semantic eligibility and downstream lineage without introducing a new model/component/feature.

`PRODUCTION_CHANGE_EXECUTED = NO`

`TARGET_RUN_MUTATED = NO`

## Required Final Answers

1. `CT_DIRECTION_PRESERVED`: `YES`
2. `CURRENT_REENTRY_GATE_SOURCE_MAP`: see source map table above.
3. `REENTRY_GATE_LEGACY_CLASSIFICATION`: see KEEP/MIGRATE/REMOVE/DEPRECATE table above.
4. `TARGET_REENTRY_SEMANTIC_DEFINITION`: REENTRY is lifecycle/provenance, not a rank/quality/capital discount.
5. `PRIOR_EXIT_CONTEXT_CONTRACT`: prior campaign id, date, semantic reason/class, reason codes, and source ids are required; missing/generic fails closed.
6. `SHORT_CHURN_GUARD_AUTHORITY`: PC semantic REENTRY authority, existing 3BD cooldown, and repeated-unresolved-churn evidence.
7. `NEW_CHURN_THRESHOLD_REQUIRED`: `NO_FOR_CU`.
8. `PRIOR_CAUSE_RECOVERY_CONTRACT`: prior cause is context; TREND_MOMENTUM uses current trend/momentum recovery, HARD_STOP stricter, generic missing fails closed.
9. `HARD_STOP_REENTRY_CONTRACT`: separate enhanced recovery with full BQ, trend/momentum, Entry/CQ/downside, safety/CA/broker/capacity, no churn.
10. `ORDINARY_BUY_AUTHORITY_FOR_REENTRY`: Candidate/Opportunity rank, BQ, Entry Admission, CQ, downside, PC/PS, safety/broker/CA/capacity own current BUY quality.
11. `REENTRY_RANK_PENALTY_REMOVAL_CONTRACT`: remove REENTRY-only rank <=10 rejection; retain rank as ordinary current opportunity evidence.
12. `REENTRY_BQ_QUALITY_PENALTY_REMOVAL_CONTRACT`: remove REENTRY-only BQ/quality duplicate; reuse ordinary authorities, with HARD_STOP exception.
13. `REENTRY_TIME_LOGIC_FINAL_DISPOSITION`: keep strict-prior and 3BD/churn; remove long-lived/permanent prior-ownership time penalty; do not promote fixed 60BD.
14. `REENTRY_CAPITAL_COMPETITION_FINAL_CONTRACT`: no bonus, no discount, current marginal opportunity only.
15. `BUY_NEW_REENTRY_CLASSIFICATION_BOUNDARY`: preserve REENTRY lineage; do not relabel as BUY_NEW to bypass.
16. `BUY_ADD_G129_INVARIANT`: unchanged.
17. `CK_BYPASS_GUARD_INVARIANT`: blocked REENTRY cannot enter BUY_NEW path.
18. `CO_PRIOR_EXIT_PROVENANCE_INVARIANT`: authoritative non-generic prior EXIT semantics remain required.
19. `MISSING_CONTEXT_FAIL_CLOSED_CONTRACT`: prior campaign with unresolved semantic context stays REENTRY REVIEW_REQUIRED / fail-closed.
20. `83060_TARGET_CONTRACT_RESULT`: should PASS and compete neutrally after residual protections.
21. `CR_NEAR_TERM_FIVE_TARGET_CONTRACT_RESULT`: should remain constrained by narrow near-term churn / same-thesis guard, not broad penalty.
22. `LEGACY_REMOVAL_SCOPE`: localized PC recovery/eligibility branches, tests, schema/docs, and shadow compatibility paths listed above.
23. `MIGRATION_STRATEGY`: `ATOMIC`
24. `FOCUSED_VALIDATION_MATRIX`: see matrix above.
25. `POST_IMPLEMENTATION_FRESH_VALIDATION_PLAN`: focused correctness first; long Historical only after semantic acceptance.
26. `NEW_COMPONENT_REQUIRED`: `NO`
27. `NEW_MODEL_REQUIRED`: `NO`
28. `NEW_FEATURE_REQUIRED`: `NO`
29. `IMPLEMENTATION_READY`: `YES`
30. `PRODUCTION_CHANGE_JUSTIFIED`: `YES`
31. `PRODUCTION_CHANGE_EXECUTED`: `NO`
32. `TARGET_RUN_MUTATED`: `NO`
33. `NEXT_RECOMMENDED_STEP`: implement the atomic PC contract cleanup that keeps residual provenance/churn/HARD_STOP protections and removes broad REENTRY-specific rank/BQ/capital penalties, then run focused validation before any long Historical.
34. `FINAL_JUDGMENT`: `PHASE32_CU_MINIMAL_RESIDUAL_REENTRY_PROTECTION_CONTRACT_IMPLEMENTATION_READY_READ_ONLY_NO_MUTATION`

## Final Judgment

`PHASE32_CU_MINIMAL_RESIDUAL_REENTRY_PROTECTION_CONTRACT_IMPLEMENTATION_READY_READ_ONLY_NO_MUTATION`
