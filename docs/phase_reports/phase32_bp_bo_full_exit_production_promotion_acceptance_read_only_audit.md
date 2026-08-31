# Phase32-BP - BO FULL EXIT Production Promotion Acceptance READ-ONLY Audit

## Scope

Target run:

`runtime-test-historical-extended-smoke-20260831T003243720082Z`

This phase is READ-ONLY acceptance. No implementation was performed.

No code, config, model, threshold, weight, BO shadow logic, Production EXIT authority, PM, PC, PS, Runtime, Pending, Submit, Execution, runtime state, Accepted Generation, fresh-run, resume, recover, replay, or long Historical action was changed.

## Mandatory Evidence Reviewed

- `docs/phase_reports/phase32_bj_pm_reduce_full_exit_counterfactual_read_only_characterization.md`
- `docs/phase_reports/phase32_bk_lot_blocked_reduce_harmful_beneficial_pit_semantic_separability_read_only_audit.md`
- `docs/phase_reports/phase32_bl_lot_blocked_reduce_binary_materialization_shadow_design.md`
- `docs/phase_reports/phase32_bm_lot_blocked_reduce_binary_shadow_economic_tail_loss_evaluation.md`
- `docs/phase_reports/phase32_bn_profit_cushion_vs_profit_protection_semantic_conflict_read_only_audit.md`
- `docs/phase_reports/phase32_bo_profit_cushion_contextualized_shadow_refinement_evaluation.md`
- `docs/02_architecture/position_management_reduce_quantity_contract.md`
- `docs/02_architecture/position_management_decision_trace_contract.md`
- `docs/02_architecture/strategy_intelligence_architecture_v1.md`
- current source around PM decision output and Sell Planning REDUCE quantity resolution

Historical outcomes are used only as acceptance evidence. They are not accepted as decision authority and were not used to tune BO.

## Exact Promotion Scope

Production promotion, if implemented in Phase32-BQ, must be limited to this canonical trigger:

```text
PM source action = REDUCE
REDUCE intensity is canonical
Current position/campaign authority exists
partial REDUCE quantity authority resolves normally
partial REDUCE is not executable specifically because of discrete-lot granularity
rounded/final executable REDUCE quantity = 0
desired REDUCE quantity > 0
same-date PIT Strategy Intelligence / Market Context evidence is complete
run/profile/source binding is current
BO semantic result = SHADOW_FULL_EXIT
```

Explicitly excluded:

- executable REDUCE
- minimum-notional failures
- cash or capital failures
- BUY / HOLD / native EXIT
- malformed evidence
- stale or cross-run evidence
- future-dated evidence
- BO `SHADOW_HOLD`
- BO `SHADOW_INSUFFICIENT_EVIDENCE`

BO population under the fixed `2022-10-03` to `2024-05-01` window:

| Population | Count |
|---|---:|
| raw BO `SHADOW_FULL_EXIT` rows | 46 |
| first-campaign BO `SHADOW_FULL_EXIT` episodes | 23 |
| BO `SHADOW_HOLD` first episodes | 23 |
| BO `SHADOW_INSUFFICIENT_EVIDENCE` first episodes | 297 |

The 297 ambiguous episodes remain untouched by the candidate promotion.

## Authority Ownership

Current SoT says:

- PM owns existing-position investment actions: `HOLD / ADD / REDUCE / EXIT`.
- Sell Planning owns deterministic REDUCE quantity materialization.
- Runtime, Submit, Execution, and generic sizing must not invent an `EXIT`.
- Current REDUCE quantity contract explicitly says REDUCE must not silently become EXIT.

Therefore the correct Production authority owner is:

```text
Strategy materialization adapter with explicit PM-derived reconsideration authority
```

The adapter should sit at the PM/Strategy boundary after discrete-lot non-executability is known, and before ordinary SELL planning/Pending publication emits an executable item. It may consume:

- PM REDUCE decision and decision id
- PM reason/provenance
- PS/Sell Planning reduce quantity contract proving discrete-lot zero executability
- current campaign identity
- BO PIT semantic evidence

It must author a distinct reconsidered Strategy action, not allow Runtime/Submit/Execution to convert REDUCE to EXIT.

Required semantic name:

```text
PM_REDUCE_LOT_BLOCKED_RECONSIDERED_FULL_EXIT
```

or an equivalent canonical reason/action contract.

## Canonical Action Semantics

Promoted FULL EXIT should use ordinary downstream PM EXIT machinery after the reconsideration boundary:

- full remaining sellable quantity
- normal `SELL_EXIT` planning
- normal Pending
- normal Submit Guard
- normal Execution
- normal campaign preservation
- normal provenance
- normal cash/position reconciliation

No special execution shortcut should exist.

This is not the same as native PM EXIT. It must remain distinguishable as:

```text
native PM EXIT
```

versus:

```text
PM REDUCE -> discrete-lot blocked -> canonical reconsideration -> FULL EXIT
```

## Provenance / Campaign Identity Requirements

Promotion is acceptable only if the BQ implementation preserves:

- original PM `source_decision_id`
- original source action `REDUCE`
- reconsidered action / reason
- BO PIT evidence hash/path
- reduce quantity contract evidence
- lot-block reason `REDUCE_UNEXECUTABLE_DUE_TO_DISCRETE_LOT`
- `position_campaign_id` / `campaign_id`
- order plan item id
- pending item id
- downstream execution/fill lineage

The promoted item should carry both:

- executable downstream action: `SELL_EXIT`
- lineage: `PM_REDUCE_LOT_BLOCKED_RECONSIDERED_FULL_EXIT`

No symbol-only join or downstream campaign id regeneration is acceptable.

## Duplicate / Idempotency Safety

Candidate promotion is compatible with existing idempotency only if BQ defines one canonical single-authority point:

```text
one lot-blocked REDUCE reconsideration artifact/member per symbol/campaign/business_date
```

Required fail-closed/review conditions:

- a same-symbol native EXIT already exists
- an executable REDUCE already exists
- any SELL for the same campaign/date is already submitted/executed
- active Pending SELL conflict exists
- recovered/replayed state already contains terminal execution for that symbol/campaign/date
- reduce quantity contract is missing, stale, malformed, or not discrete-lot zero
- BO evidence is missing, stale, future-dated, cross-run, or not `SHADOW_FULL_EXIT`

Implementation must not create:

- original REDUCE order plus FULL EXIT order
- duplicate SELL_EXIT across retries
- repeated FULL EXIT across repeated REDUCE observations without fresh current-day authority
- next-day carry-over from stale prior-day authority

## Interaction With Existing EXIT Semantics

BO FULL EXIT is semantically compatible with current PM/Strategy philosophy only as an execution-granularity reconsideration of a REDUCE that cannot be represented.

It must not be described as:

- PM originally emitted EXIT
- profit-taking shortcut
- Runtime fallback
- lot-rounding ceil-up
- hidden reduce debt

It should be represented as distinct reconsidered EXIT reason while using the same downstream full-exit machinery.

The current PM EXIT philosophy remains preserved:

- native hard-stop / thesis-broken / persistent deterioration EXIT remains unchanged
- `REDUCE` remains partial exposure-reduction intent by default
- only the accepted BO FULL_EXIT subset may be reconsidered when partial REDUCE cannot execute

## Profit Cushion Semantics

BN/BO correction is Architecture-compatible:

```text
profit cushion != standalone HOLD authority
```

and:

```text
profit + intact continuation -> HOLD support
profit + deterioration/risk -> profit-at-risk / protection context
```

This is already supported by the common SoT principle that Profit Protection is evidence, not action authority. BQ should update the permanent SoT to describe the new reconsideration contract if Production promotion is implemented.

## BO FULL EXIT Population Acceptance

BO reported:

- `SHADOW_FULL_EXIT`: 23 first episodes, 46 raw rows
- avoided loss: `130,100`
- false-exit cost: `4,600`
- net effect: `+127,450`
- 67310 tail captured
- 6 of 9 large-loss days preventable by BO `SHADOW_FULL_EXIT`

The inspected BO FULL_EXIT candidates are semantically narrow:

- all are PM `REDUCE`
- all are discrete-lot unrepresentable
- all have final executable REDUCE quantity `0`
- all have no structural HOLD-side evidence
- all rely on current PIT deterioration/risk evidence
- all keep `shadow_order_authority = false`
- all report no future information / later PnL / final campaign outcome as decision input

No BO FULL_EXIT episode was found that requires a Historical-fitted threshold, new model, future outcome, or symbol/date-specific rule.

Acceptance caveat:

BO remains economically partial. It improves the specific tail problem but does not solve broad ambiguity. This does not block promoting only the clear BO FULL_EXIT subset, but it does block expanding beyond that subset.

## Winner False-Exit Controls

Mandatory BO non-FULL-EXIT controls remain excluded from Production promotion:

| Symbol | BO decision | Promotion effect |
|---|---|---|
| 62280 | `SHADOW_INSUFFICIENT_EVIDENCE` | unchanged / no FULL EXIT |
| 74270 | `SHADOW_INSUFFICIENT_EVIDENCE` | unchanged / no FULL EXIT |
| 92270 | `SHADOW_INSUFFICIENT_EVIDENCE` | unchanged / no FULL EXIT |
| 72140 | `SHADOW_INSUFFICIENT_EVIDENCE` | unchanged / no FULL EXIT |
| 83040 | `SHADOW_INSUFFICIENT_EVIDENCE` | unchanged / no FULL EXIT |
| 69730 | `SHADOW_HOLD` | unchanged / no FULL EXIT |

Therefore the major BO winner false-exit controls are excluded by the proposed scope.

## Remaining Ambiguity Boundary

BO still has `297` `SHADOW_INSUFFICIENT_EVIDENCE` first episodes.

Production promotion must not attempt to resolve them:

- current behavior remains unchanged
- no automatic FULL EXIT
- no new threshold
- no new reason-family shortcut
- no outcome-derived expansion

BP acceptance concerns only the already-clear BO FULL_EXIT subset.

## Runtime / Pending / Historical Safety

Promotion is compatible with AX-BE safety repairs only if BQ keeps item-scoped authority:

- reviewed/malformed items stay non-submittable
- unrelated executable items remain separable
- Corporate Action authority remains item-scoped and run-scoped
- Historical temporal authority rejects stale/cross-run evidence
- Pending lifecycle does not carry stale reconsidered EXIT authority into a later date
- current valuation and day rollover can distinguish consumed executable items from reviewed residual items
- retries/resumes reuse the same order/pending identity and do not duplicate broker evidence

No Runtime/Pending safety bypass is acceptable.

## BQ Implementation Plan

Suggested minimal BQ scope:

1. Add/extend a Strategy-owned reconsideration contract, e.g. `PM_REDUCE_LOT_BLOCKED_RECONSIDERED_FULL_EXIT`.
2. Author it after PM REDUCE and discrete-lot zero-executable quantity evidence are materialized, before executable SELL planning/Pending publication.
3. Preserve original PM `REDUCE` provenance and attach BO PIT evidence, reduce quantity contract, and lot-block reason.
4. Convert only accepted reconsidered members into ordinary downstream `SELL_EXIT` planning.
5. Leave executable REDUCE, minimum-notional, BO HOLD, and BO INSUFFICIENT paths unchanged.
6. Add fail-closed validation for stale/cross-run/future/missing BO and quantity-contract evidence.
7. Add duplicate/idempotency guards for same-symbol/campaign/date native EXIT, existing SELL, submitted order, execution, and recovery/replay states.
8. Update SoT docs for the explicit reconsideration boundary.
9. If the PM Runtime adapter source changes, use the canonical accepted artifact/registry/index/checkpoint path; do not patch hashes.

Likely files to inspect/change in BQ:

- `src/ai_fund_lab_v2/strategy/unrepresentable_reduce_exit_shadow.py` or a Production sibling module
- `src/ai_fund_lab_v2/runtime_v2/planning/sell_pipeline.py`
- `src/ai_fund_lab_v2/runtime_v2/planning/planner.py`
- `src/ai_fund_lab_v2/runtime_v2/planning/strategy_authority.py`
- PM/Strategy architecture docs for the new reconsideration contract
- focused tests around REDUCE quantity, SELL planning, Pending, Submit, idempotency, G129/KI-006/AX-BE adjacency

Required BQ tests:

- BO FULL_EXIT creates a single ordinary SELL_EXIT executable plan with full quantity.
- Original REDUCE provenance and campaign id survive through Pending/Submit/Execution/fill.
- executable REDUCE remains unchanged.
- minimum-notional remains unchanged.
- BO HOLD remains unchanged.
- BO INSUFFICIENT remains unchanged.
- native PM EXIT remains unchanged.
- missing/stale/future/cross-run BO evidence fails closed.
- duplicate same-symbol/campaign/date SELL states fail closed or reconcile idempotently.
- mixed review, current valuation, day rollover, and resume/retry contracts remain PASS.
- G129 BUY_ADD, KI-004 separation, KI-006 zero preservation, and Winner Retention focused tests remain PASS.

Fresh-run before BQ implementation is not required. Post-BQ validation may require a user-operated focused fresh-run or continuation command, but BP does not prescribe a mutating command.

## Required Final Answers

1. `BO_FULL_EXIT_PROMOTION_SCOPE_CLEAR`: YES
2. `PRODUCTION_AUTHORITY_OWNER`: `Strategy materialization adapter with explicit PM-derived reconsideration authority`
3. `RUNTIME_ALLOWED_TO_INVENT_EXIT`: NO
4. `CANONICAL_RECONSIDERATION_BOUNDARY`: after PM REDUCE + discrete-lot zero-executable quantity evidence, before ordinary executable SELL planning/Pending publication
5. `EXECUTABLE_REDUCE_UNCHANGED`: YES
6. `BO_HOLD_UNCHANGED`: YES
7. `BO_INSUFFICIENT_UNCHANGED`: YES
8. `NATIVE_PM_EXIT_SEMANTICS_PRESERVED`: YES
9. `RECONSIDERED_EXIT_DISTINGUISHABLE_IN_AUDIT`: YES, required by BQ contract
10. `CAMPAIGN_IDENTITY_PRESERVED`: YES, required; no downstream regeneration
11. `PROVENANCE_PRESERVED`: YES, required; original REDUCE plus reconsidered EXIT lineage
12. `DUPLICATE_SELL_RISK_CONTROLLED`: YES if BQ implements the single-authority/idempotency guards above
13. `RESUME_RETRY_IDEMPOTENCY_COMPATIBLE`: YES if BQ reuses canonical pending/order identity and reconciles terminal executions
14. `PENDING_LIFECYCLE_COMPATIBLE`: YES with item-scoped same-date authority and no stale carry-over
15. `MIXED_REVIEW_SAFETY_COMPATIBLE`: YES, provided reviewed items remain non-submittable and unrelated items stay item-scoped
16. `HISTORICAL_TEMPORAL_SAFETY_COMPATIBLE`: YES, provided run/date/source bindings are validated and stale/cross-run evidence fails closed
17. `PROFIT_CUSHION_SEMANTIC_ARCHITECTURE_COMPATIBLE`: YES
18. `BO_FULL_EXIT_POPULATION_SEMANTICALLY_ACCEPTABLE`: YES for the narrow subset
19. `WINNER_FALSE_EXIT_CONTROLS_EXCLUDED`: YES
20. `297_AMBIGUOUS_EPISODES_REMAIN_UNTOUCHED`: YES
21. `NEW_FEATURE_REQUIRED`: NO
22. `NEW_MODEL_REQUIRED`: NO
23. `NEW_THRESHOLD_REQUIRED`: NO
24. `PRODUCTION_PROMOTION_ARCHITECTURALLY_JUSTIFIED`: YES, for the BO FULL_EXIT subset only
25. `PRODUCTION_IMPLEMENTATION_SAFE_TO_PROCEED`: YES, with the BQ constraints/fail-closed guards above
26. `FRESH_RUN_REQUIRED_BEFORE_IMPLEMENTATION`: NO
27. `NEXT_RECOMMENDED_STEP`: implement Phase32-BQ as a narrow Strategy-owned PM REDUCE lot-blocked reconsideration Production contract, using ordinary SELL_EXIT downstream machinery and preserving BO HOLD/INSUFFICIENT behavior.
28. `FINAL_JUDGMENT`: `PHASE32_BP_BO_FULL_EXIT_PRODUCTION_PROMOTION_ACCEPTED_FOR_NARROW_BQ_IMPLEMENTATION`

## Final Judgment

`PHASE32_BP_BO_FULL_EXIT_PRODUCTION_PROMOTION_ACCEPTED_FOR_NARROW_BQ_IMPLEMENTATION`

