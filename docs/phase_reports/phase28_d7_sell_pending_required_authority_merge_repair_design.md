# Phase28-D7: SELL Pending Required Authority Merge Repair Design

Task ID: `Phase28-D7`

Task Type: `DESIGN ONLY`

Status: `COMPLETE`

Primary Judgment: `PHASE28_D7_SELL_PENDING_AUTHORITY_MERGE_DESIGN_COMPLETE_PHASE28_D8_READY`

Phase28-D8 Entry Decision: `APPROVED`

Implementation Changed: `false`

Resume Executed: `false`

Fresh Run Executed: `false`

Long Historical Executed: `false`

## 1. Executive Summary

Phase28-D7 designs the compatible SELL pending authority merge repair for the
Phase28-D5/D6 `43880` halt class.

The D6 trace is accepted:

```text
Existing strategy SELL pending:
strategy-d3ca3c09c7e90609497b
listed_info = null

New PM SELL item:
opi-sell-exit-pm-43880-001
listed_info = valid

D3 reconciliation:
SAME_SYMBOL_COMPATIBLE_UPDATE
PRESERVE_EXISTING
PENDING_SELL_COMPATIBLE_UPDATE_MERGED

Result:
existing null item preserved, new valid listed_info discarded
```

D7 recommends a single D8 repair:

```text
Option A: Reconciliation Authority Merge only
```

D8 should preserve the existing pending identity but enrich required submit
authority fields, starting with `listed_info`, only after strict lineage,
date/session, symbol, side, generation, state, and field validation pass.

This is not a Strategy, Performance, ADD, Submit, Broker, or threshold change.
Submit Guard remains the final defensive fail-closed layer.

## 2. Scope

In scope:

- Pending field inventory
- Submit-required authority inventory
- Producer/consumer matrix
- Compatible SELL authority merge contract
- `listed_info` merge contract
- Approval-prevalidation contract
- Identity/hash/provenance/failure contracts
- D8 one-repair recommendation
- Short regression and fresh 100BD contracts

Out of scope:

- implementation
- config/schema/threshold changes
- fresh/resume/long historical runs
- Phase28-C ADD bridge
- BUY/HOLD/ADD/REDUCE/EXIT criteria
- Submit/Broker behavior changes

## 3. Phase28-D6 Findings Accepted

Accepted facts:

- `43880` strategy pending item was first generated with `listed_info=None`.
- The first null source was `strategy_authority._listed_info_from_opportunity_authority(...)` returning `None` because opportunity authority was absent.
- Sell Planning later generated a PM EXIT item with valid basic listed info.
- D3 compatible SELL reconciliation preserved the existing strategy item and did not merge the new PM item's listed info.
- Approval and Submit consumed the preserved null item.
- Phase28-C has no direct causality.
- D3 is directly related because compatible preservation omitted authority-field merge.

## 4. Documents Reviewed

- `docs/phase_reports/phase28_d6_sell_pending_listed_info_authority_trace.md`
- `docs/phase_reports/phase28_d5_20230410_submit_halt_root_cause.md`
- `docs/phase_reports/phase28_d3_runtime_sell_pending_reconciliation_implementation.md`
- `docs/phase_reports/phase28_d2_runtime_sell_planning_pending_conflict_repair_design.md`
- `docs/02_architecture/runtime_architecture_v2.md`
- `docs/02_architecture/position_management_reduce_quantity_contract.md`
- `docs/02_architecture/momentum_follow_position_lifecycle_and_canonical_decision_architecture.md`
- `docs/02_architecture/position_management_decision_trace_contract.md`
- `docs/01_requirements/phase_roadmap.md`

## 5. Current Defect

Current defect definition:

```text
Compatible SELL pending reconciliation can preserve an existing pending item
whose required submit authority fields are incomplete, while discarding a new
compatible PM SELL item that carries valid required authority fields.
```

For D5/D6, the missing field is `listed_info`.

Defect class:

- Producer defect: partial. Strategy pending listed_info source is opportunity-only.
- Copy/merge defect: primary. Compatible SELL reconciliation did not merge valid listed info.
- Condition defect: compatible preservation does not validate required submit authority completeness.
- Consumer defect: Submit requires listed info for broker normalization, but upstream does not fail before approval.

## 6. Pending Field Inventory

Inventory artifact:

```text
reports/phase28_d7_sell_pending_required_authority_merge_repair_design/pending_field_inventory.json
```

High-level categories:

- `IDENTITY_FIELDS`: `pending_item_id`, `symbol`, `side`, `state`, `source_position_symbol`
- `DECISION_LINEAGE_FIELDS`: planning, PM source, and accepted-generation fields
- `QUANTITY_AUTHORITY_FIELDS`: `quantity`, amount, constraints, quantity contract, ADD notional fields
- `BROKER_NORMALIZATION_FIELDS`: `listed_info`, order/price authority fields
- `SAFETY_FIELDS`: safety decision and source fields
- `TEMPORAL_FIELDS`: safety business date, temporal authority, runtime-test context
- `EXECUTION_FIELDS`: approval, submit policy, feasibility, allocation state
- `OBSERVABILITY_FIELDS`: review reason and manual review threshold
- `OPTIONAL_METADATA_FIELDS`: add signal and policy metadata

## 7. Submit-required Authority Inventory

Inventory artifact:

```text
reports/phase28_d7_sell_pending_required_authority_merge_repair_design/submit_required_field_inventory.json
```

Submit requires:

- approved pending state and approval linkage
- approved item id
- supported side/order type
- order condition authority
- symbol broker capability
- positive quantity
- SELL current quantity
- SELL broker available quantity
- `listed_info` fields sufficient for broker issue-code normalization

Broker normalization requires:

```text
listed_info.code
listed_info.market
listed_info.product_category
listed_info.security_type
listed_info.current_listed == true
```

Current gap:

```text
listed_info missing can survive until Submit defensive fail-closed.
```

## 8. Producer / Consumer Authority Matrix

Matrix artifact:

```text
reports/phase28_d7_sell_pending_required_authority_merge_repair_design/authority_producer_matrix.json
```

Important boundaries:

- Strategy Authority can create pending items and listed info when opportunity authority exists.
- Opportunity Authority is valid when present but must not be the only SELL listed-info source long-term.
- Sell Planning can produce basic listed info for PM SELL items.
- Pending Composition owns preserve/reconcile/replace/review and must own authority merge evidence.
- Approval owns approval ids and order conditions, not late authority repair.
- Submit Guard owns final pre-submit validation and defensive fail-closed.

## 9. Compatible Reconciliation Merge Principles

Compatible SELL reconciliation must satisfy both:

```text
identity preservation
authority completeness
```

It may preserve `pending_item_id`, lineage, intent, side, symbol, quantity
contract, generation, and campaign identity while enriching required submit
authority fields only when all validation gates pass.

No blind copy is allowed.

## 10. listed_info Merge Contract

Contract artifact:

```text
reports/phase28_d7_sell_pending_required_authority_merge_repair_design/listed_info_merge_contract.json
```

Merge prerequisites:

- same business date
- same target session date
- same normalized symbol
- same side
- same compatible SELL intent lineage
- same campaign when available
- same or compatible accepted generation authority
- new listed info schema valid
- `current_listed == true`
- code matches normalized symbol
- market/product/security valid
- source authority identified
- no conflicting existing non-null value
- submit not started
- partial fill not started

Cases:

```text
existing null / new valid -> FILL_MISSING_FROM_NEW
existing valid / new null -> PRESERVE_EXISTING
both valid equivalent -> PRESERVE_EXISTING plus provenance merge
both valid conflicting -> CONFLICT_REVIEW_REQUIRED
both null -> REVIEW_REQUIRED before Approval / Submit
```

## 11. Non-opportunity listed_info Authority

Design artifact:

```text
reports/phase28_d7_sell_pending_required_authority_merge_repair_design/non_opportunity_listed_info_authority_design.json
```

Principle:

```text
Opportunity ranking absent != listed_info unknown
```

Long-term primary authority should be PIT listed-issue metadata, preferably
from canonical Listed Issues / Market Refresh historical listed-info evidence.

D8 should not implement this producer redesign. It should use Option A only,
because D8 must remain one Runtime repair. The non-opportunity producer gap is
documented as follow-up.

## 12. Identity Preservation

Contract artifact:

```text
reports/phase28_d7_sell_pending_required_authority_merge_repair_design/identity_preservation_contract.json
```

Do not change during authority enrichment:

- existing pending item id
- source decision id
- planning authority id
- intent class
- side
- symbol
- quantity contract
- approval lineage unless reapproval is forced
- accepted generation
- campaign id

Hash contract:

- identity remains stable
- content hash changes when authority is enriched
- previous/new item hash must be recorded
- already-approved enrichment requires reapproval or is prohibited
- atomic write required

## 13. Approval Prevalidation

Contract artifact:

```text
reports/phase28_d7_sell_pending_required_authority_merge_repair_design/approval_prevalidation_contract.json
```

State rules:

```text
DRAFT: listed_info missing may be allowed with evidence
EXECUTABLE_PENDING: listed_info missing prohibited
APPROVED: listed_info missing prohibited
SUBMIT: final defensive fail-closed only
```

Recommended validation points:

- Pending Composition completion
- Pending write before `APPROVED`
- Approval input validation

## 14. Provenance

Contract artifact:

```text
reports/phase28_d7_sell_pending_required_authority_merge_repair_design/provenance_contract.json
```

Required provenance fields include:

```text
listed_info_source
listed_info_source_artifact
listed_info_source_hash
listed_info_source_business_date
listed_info_source_item_id
listed_info_merge_action
listed_info_existing_status
listed_info_new_status
listed_info_conflict_status
listed_info_validation_status
```

D8 can materialize these in additive reconciliation evidence without changing
core schema unless implementation proves machine consumption requires it.

## 15. Failure Contract

Contract artifact:

```text
reports/phase28_d7_sell_pending_required_authority_merge_repair_design/failure_contract.json
```

Fail-closed conditions include symbol/side/date/session/generation mismatch,
invalid schema, normalization mismatch, metadata conflicts, both sources null,
unknown source authority, submitted/partial-fill state, post-approval mutation,
hash race, and multiple incompatible new items.

Failure action:

```text
original pending preserve
REVIEW_REQUIRED
proposed enrichment separate evidence
no empty plan overwrite
```

## 16. BUY / SELL Independence

Contract artifact:

```text
reports/phase28_d7_sell_pending_required_authority_merge_repair_design/buy_sell_independence_contract.json
```

Requirements:

- SELL authority merge does not modify BUY items.
- BUY listed info is never copied into SELL item.
- BUY no-signal/review state is unchanged.
- Mixed pending plan BUY item hashes are unchanged.
- Opposite-side preserved evidence remains.
- Phase28-C ADD bridge remains unchanged.

## 17. Phase28-C Conformance

Phase28-C is unchanged:

- no Expected Edge change
- no Incremental Investment Value change
- no ADD bridge change
- no BUY_ADD mapping change
- no Portfolio Construction / Position Sizing performance change

## 18. Phase28-D3 Conformance

D8 must preserve the D3 structure:

```text
classify -> preserve / reconcile / review
```

Allowed D8 change:

```text
compatible SELL reconciliation authority enrichment when preserving existing item
```

Do not break:

- same-intent idempotency
- original pending preservation
- no-signal overwrite guard
- submitted/partial-fill fail-closed
- BUY/SELL independence

## 19. D8 Option Comparison

Comparison artifact:

```text
reports/phase28_d7_sell_pending_required_authority_merge_repair_design/phase28_d8_option_comparison.json
```

Option A: Reconciliation Authority Merge only.

Recommended because it is the minimal direct repair for the `43880` halt class
and preserves D3 architecture.

Option B: Strategy SELL Producer Authority only.

Not recommended for D8 because it is broader and does not fix D3 authority-drop
behavior.

Option C: Merge + Producer.

Not recommended for D8 because it violates the one Runtime repair discipline.

## 20. D8 Minimal Repair Recommendation

Candidate artifact:

```text
reports/phase28_d7_sell_pending_required_authority_merge_repair_design/phase28_d8_minimal_repair_candidate.json
```

Primary recommendation:

```text
Option A: Reconciliation Authority Merge only
```

D8 should implement exactly one repair:

```text
When compatible SELL reconciliation preserves an existing pending item,
validate and merge required submit authority fields from the new compatible
SELL item, starting with listed_info.
```

## 21. Short Regression Contract

Regression artifact:

```text
reports/phase28_d7_sell_pending_required_authority_merge_repair_design/short_regression_contract.json
```

Minimum cases:

- 43880 reproduction
- existing null / new valid
- existing valid / new null
- both valid equivalent
- both valid conflicting
- both null
- submitted / partial fill / generation mismatch / date mismatch / symbol mismatch / plan hash race
- same-intent duplicate preserve
- compatible quantity reconciliation
- REDUCE -> EXIT upgrade
- EXIT -> REDUCE downgrade prohibition
- no-signal does not overwrite active pending
- BUY item unchanged
- ordinary SELL valid existing listed info unchanged
- Phase28-C ADD fixtures pass
- Submit Guard unchanged as final defense

## 22. Fresh 100BD Contract

Contract artifact:

```text
reports/phase28_d7_sell_pending_required_authority_merge_repair_design/fresh_100bd_contract.json
```

The halted run must not be resumed:

```text
runtime-test-historical-smoke-20260805T231619492537Z
```

After D8 repair and short validation, user/operator must run a fresh 100BD.
Codex must not run fresh/resume/long historical in D7.

## 23. Risks

- Option A fixes the D5/D6 damaging path, but strategy pending without later PM SELL item can still carry null listed info.
- Sell Planning basic listed info source must be validated and proven enough for broker normalization.
- Post-approval authority enrichment would create approval/hash ambiguity, so D8 must keep enrichment pre-approval or force reapproval.
- Provenance fields may need schema promotion later if evidence-only materialization proves insufficient.

## 24. Open Gaps

Open gap artifact:

```text
reports/phase28_d7_sell_pending_required_authority_merge_repair_design/open_gap_inventory.json
```

Open gaps:

- Strategy executable SELL pending can still be generated with `listed_info=null` when opportunity authority is absent.
- First-class listed-info provenance fields are not part of current Pending schema.
- Submit preflight does not block listed-info absence before broker normalization.

These do not block D8 Option A because D8 is intentionally the minimal direct
repair for the observed compatible-reconciliation authority drop.

## 25. Final Judgment

```text
Primary Judgment:
PHASE28_D7_SELL_PENDING_AUTHORITY_MERGE_DESIGN_COMPLETE_PHASE28_D8_READY

Phase28-D8 Entry Decision:
APPROVED

Current defect:
Compatible SELL reconciliation can preserve existing pending identity while
discarding required submit authority fields from a valid new compatible PM SELL
item.

Pending identity ownership:
Pending Composition owns preserve/reconcile/review identity decisions.

listed_info Primary Authority:
For D8 Option A, the new compatible PM SELL item listed_info after validation.
Long-term primary should be canonical PIT listed-issue metadata.

listed_info Secondary Authority:
Opportunity Authority when present; Current/campaign metadata only when bound
to canonical listed metadata.

merge conditions:
same date/session/symbol/side/intent/generation, valid schema, current listed,
source identified, no submitted/partial-fill state, no conflict.

preserve conditions:
existing valid and new null; both valid equivalent; non-mergeable identity fields.

conflict conditions:
symbol/side/date/session/generation/schema/code/market/product/security/current_listed mismatch.

both null:
REVIEW_REQUIRED before Approval / Submit.

Approval prevalidation:
Executable and approved pending items must not carry listed_info missing.

hash / lineage:
preserve identity, record previous/new content hashes, require atomic write;
post-approval merge prohibited unless reapproval is forced.

provenance fields:
listed_info_source, source_artifact, source_hash, source_business_date,
source_item_id, merge_action, existing/new/conflict/validation status.

D8 recommended repair:
Option A only: compatible SELL pending required-authority merge.

D8 unchanged:
Strategy producer, Submit Guard, Broker, BUY logic, Phase28-C ADD bridge,
performance conditions, config, thresholds.

43880 reproduction:
existing compatible SELL listed_info null + new PM SELL valid -> preserve
existing id and enrich listed_info -> Approval/Submit broker normalization PASS.

fresh 100BD:
required after D8 short validation by user/operator; no resume of halted run.
```

## 26. Phase28-D8 Entry Decision

`APPROVED`.

All D8 entry conditions are satisfied for Option A:

- Pending field inventory complete
- Submit-required field inventory complete
- listed_info producer priority defined for D8 and long-term
- merge/preserve/conflict/both-null contracts defined
- identity/hash/reapproval contract defined
- Approval-prevalidation contract defined
- provenance materialization defined
- BUY/SELL independence preserved
- D3 classifier preserved
- D8 repair limited to one runtime repair
- Phase28-C unchanged
- 43880 reproduction fixture defined
- Submit Guard retained as final defense
- no Historical-only implementation required
- fresh 100BD restart requirement explicit
