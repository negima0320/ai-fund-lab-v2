# Phase25-B3 Full Authority Conflict Inventory

## 1. Executive Summary

Phase25-B3 completed a read-only authority conflict inventory. No Runtime, Strategy, config, schema, fallback, or legacy deletion was changed.

The central finding is that multiple new Strategy/Architecture authorities exist, but fixed legacy Runtime authorities still win in active Planning/Submit feasibility paths.

## 2. Primary Judgment

```text
PHASE25_B3_AUTHORITY_CONFLICT_INVENTORY_COMPLETE_CRITICAL_CONFLICTS_CONFIRMED
```

Critical authority conflicts are confirmed for capital base, position count, and cash/exposure authority.

## 3. Scope and Method

Reviewed Phase25-B/B1/B2, Phase25-A3/A3R, runtime and strategy architecture documents, gap inventory, configs, schemas, Runtime consumers, Strategy producers, and existing runtime evidence.

Method:

```text
Authority Candidate -> Producer -> Consumer -> Runtime Winner -> Selection Rule -> Consequence -> Evidence -> Judgment
```

## 4. Authority Conflict Definition

An authority conflict exists when more than one layer can decide the same Runtime concept and the selected winner is old, ambiguous, unmaterialized, mode-divergent, or inconsistent with Architecture SoT.

New artifact existence alone is not conformance.

## 5. Capital Authority Conflicts

Confirmed:

- `P25-AUTH-CAP-001`: `current_total_equity` / Strategy sizing versus fixed `CapitalDeploymentPolicy.evaluation_capital` and `max_exposure`.
- `P25-AUTH-CAP-002`: ambiguous `runtime_evaluation_capital`.

Judgments:

- `P25-AUTH-CAP-001`: `LEGACY_OVERRIDES_NEW_AUTHORITY`, `CRITICAL`.
- `P25-AUTH-CAP-002`: `ACTIVE_AUTHORITY_CONFLICT`, `HIGH`.

## 6. Position Count Authority Conflicts

Confirmed:

- `P25-AUTH-POS-001`: Dynamic Position Count and Portfolio Policy target count exist, but active Runtime still consumes fixed `max_positions=5`.

Judgment: `LEGACY_OVERRIDES_NEW_AUTHORITY`, `CRITICAL`.

## 7. Cash / Exposure Authority Conflicts

Confirmed:

- `P25-AUTH-EXP-001`: Dynamic Cash / Exposure target ratios coexist with fixed `target_investment_ratio=0.85`, `cash_buffer=0.05`, and `max_exposure=850000`.

Judgment: `LEGACY_OVERRIDES_NEW_AUTHORITY`, `CRITICAL`.

## 8. Position Weight Authority Conflicts

Confirmed:

- `P25-AUTH-WGT-001`: Position Sizing effective weight and Safety concentration cap coexist with downstream fixed `evaluation_capital * max_position_weight`.

Judgment: `ACTIVE_AUTHORITY_CONFLICT`, `HIGH`.

## 9. Strategy Lifecycle Metadata Conflicts

Confirmed:

- `P25-AUTH-LIFE-001`: Runtime consumes Strategy planning/sizing artifacts while schema and producer metadata still say shadow-only or not eligible.

Judgment: `ACTIVE_AUTHORITY_CONFLICT`, `HIGH`.

## 10. Accepted Generation Authority Conflicts

Evidence required:

- `P25-AUTH-GEN-001`: Accepted Generation resolver exists, but old fallback/default generation zero is not proven mode-by-mode.

Judgment: `EVIDENCE_REQUIRED`, `HIGH`.

## 11. Current / Ledger / Broker Authority Conflicts

Findings:

- `P25-AUTH-CUR-001`: Current/Ledger/Broker layering is mostly valid but not fully materialized.
- `P25-AUTH-CUR-002`: Runtime-owned projection can prefer `runtime_evaluation_capital` over Current cash.

Judgments:

- `P25-AUTH-CUR-001`: `AMBIGUOUS_LAYERING`, `MEDIUM`.
- `P25-AUTH-CUR-002`: `ACTIVE_AUTHORITY_CONFLICT`, `HIGH`.

## 12. Planning / Submit Authority Conflicts

Confirmed:

- `P25-AUTH-PLAN-001`: Planning Submit Feasibility can override active Strategy planning using fixed policy caps.

Judgment: `ACTIVE_AUTHORITY_CONFLICT`, `HIGH`.

## 13. BUY / SELL Independence Conflicts

No active conflict confirmed.

- `P25-AUTH-BS-001`: BUY and SELL authority independence is valid layered authority if SELL exposure reduction remains unblocked by BUY capacity constraints.

Judgment: `VALID_LAYERED_AUTHORITY`, `LOW`.

## 14. Safety Authority Conflicts

Confirmed ambiguous layering:

- `P25-AUTH-SAFE-001`: Independent Safety hard limits exist, but legacy deployment caps can be mistaken for Safety authority.

Judgment: `AMBIGUOUS_LAYERING`, `HIGH`.

## 15. Temporal Authority Conflicts

Evidence required:

- `P25-AUTH-TEMP-001`: business-date checks exist, but B3 cannot prove all latest/shared-state paths are bounded and PIT-safe across modes.

Judgment: `EVIDENCE_REQUIRED`, `HIGH`.

## 16. Corporate Action Authority Conflicts

No active conflict confirmed.

- `P25-AUTH-CA-001`: Runtime Corporate Action Authority fail-closes to manual review. Operator CLI remains future operations work.

Judgment: `VALID_LAYERED_AUTHORITY`, `LOW`.

## 17. Cross-cutting Invariant Results

| Invariant | Judgment |
|---|---|
| INV-01 Future Data Prohibited | `EVIDENCE_REQUIRED` |
| INV-02 Accepted Generation Authority | `EVIDENCE_REQUIRED` |
| INV-03 Common Runtime | `PARTIAL` |
| INV-04 Planning Authority | `FAIL` |
| INV-05 Submit/Safety Not Weakened | `PASS_WITH_NON_BLOCKING_GAPS` |
| INV-06 Safety Independence | `PARTIAL` |
| INV-07 Old Consumer Zero | `FAIL` |
| INV-08 No Runtime Result Learning | `PASS_BY_STATIC_REVIEW` |
| INV-09 Fail Closed | `PARTIAL` |
| INV-10 Capital Authority Materialized | `FAIL` |
| INV-11 Resume Bound State | `EVIDENCE_REQUIRED` |
| INV-12 Artifact Exists Is Not Conformance | `FAIL` |

## 18. Production Conflicts

Production-active confirmed conflicts:

- `P25-AUTH-CAP-001`
- `P25-AUTH-CAP-002`
- `P25-AUTH-POS-001`
- `P25-AUTH-EXP-001`
- `P25-AUTH-WGT-001`
- `P25-AUTH-LIFE-001`
- `P25-AUTH-CUR-002`
- `P25-AUTH-PLAN-001`
- `P25-AUTH-SAFE-001`

## 19. Demo Conflicts

Demo shares the same confirmed Runtime-active conflicts as Production. Demo also requires Current/Broker reset authority evidence because broker cash and positions can be evidence-only depending on capability policy.

## 20. Historical Conflicts

Historical shares the core fixed capital/count/exposure conflicts. Additional evidence is required for Accepted Generation default behavior and latest/shared-state temporal paths.

## 21. Performance-impacting Conflicts

Highest performance impact:

- fixed `evaluation_capital`
- fixed `max_exposure`
- fixed `max_positions`
- fixed cash/exposure target values
- fixed per-position notional cap
- ambiguous `runtime_evaluation_capital`
- Planning/Submit feasibility override

## 22. Safety / Temporal-impacting Conflicts

Safety-impacting:

- `P25-AUTH-SAFE-001`
- `P25-AUTH-PLAN-001`
- `P25-AUTH-CUR-002`

Temporal-impacting:

- `P25-AUTH-GEN-001`
- `P25-AUTH-TEMP-001`

No Submit Guard or Corporate Action bypass was confirmed.

## 23. Phase26 Authority Unification Mapping

| Phase26 Task | Conflict IDs |
|---|---|
| Phase26-A | `P25-AUTH-CAP-001`, `P25-AUTH-WGT-001` |
| Phase26-B | `P25-AUTH-POS-001` |
| Phase26-C | `P25-AUTH-EXP-001`, `P25-AUTH-SAFE-001` |
| Phase26-D | `P25-AUTH-LIFE-001` |
| Phase26-E | `P25-AUTH-PLAN-001` |
| Phase26-F | `P25-AUTH-CAP-002`, `P25-AUTH-CUR-002` |
| Phase26-G | `P25-AUTH-GEN-001` |
| Phase26-H | `P25-AUTH-CUR-001`, `P25-AUTH-BS-001`, `P25-AUTH-TEMP-001`, `P25-AUTH-CA-001` |

## 24. Confirmed Gaps

Added to Gap Inventory:

- `P25-GAP-AUTH-CAP-001`
- `P25-GAP-AUTH-CAP-002`
- `P25-GAP-AUTH-POS-001`
- `P25-GAP-AUTH-EXP-001`
- `P25-GAP-AUTH-WGT-001`
- `P25-GAP-AUTH-LIFE-001`
- `P25-GAP-AUTH-CUR-001`
- `P25-GAP-AUTH-PLAN-001`
- `P25-GAP-AUTH-SAFE-001`

## 25. Suspected Gaps

Added as evidence-required or suspected:

- `P25-GAP-AUTH-GEN-001`
- `P25-GAP-AUTH-TEMP-001`

## 26. Evidence-required Items

Evidence still required:

- Accepted Generation fallback/default zero across Production/Demo/Historical.
- Latest/shared-state path classification.
- Current/Ledger/Broker selected authority materialization.
- Resume old fallback zero.

## 27. Non-gaps

Non-gaps in B3:

- BUY/SELL independence when side-aware Safety behavior is preserved.
- Corporate Action Runtime fail-closed manual review.
- Independent Safety config existence itself.

## 28. Blocking Gaps

Blocking for architecture conformance:

- fixed capital authority active
- fixed position count authority active
- fixed cash/exposure authority active
- shadow-era lifecycle metadata on active Strategy consumers
- Planning/Submit authority conflict

## 29. Non-blocking Gaps

Non-blocking but required:

- `runtime_evaluation_capital` naming/trace repair
- Accepted Generation fallback-zero evidence
- latest/shared-state classification
- Current/Ledger/Broker source materialization
- Safety/deployment attribution clarity

## 30. Recommended Next Task

Recommended next task:

```text
Phase25-B4 Migration Completion Audit
```

B4 should verify each claimed migration with new producer, new artifact, active consumer switch, old producer retirement, old consumer zero, old config zero, old schema zero, old fallback zero, and regression coverage.

## 31. Validation

Performed:

- Static code/config/schema scan.
- Mandatory Phase25/B1/B2/A3/A3R review.
- B3 conflict inventory materialization.
- Gap Inventory update.
- JSON validation.

Not performed:

- No Runtime change.
- No Strategy change.
- No config/schema change.
- No long Historical test.

Deliverables:

- `reports/phase_reports/phase25_b3_full_authority_conflict_inventory.json`
- `reports/phase_reports/phase25_b3_authority_conflict_inventory.json`
- `reports/phase25_b3_full_authority_conflict_inventory/`

