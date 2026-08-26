# Phase31-G45 - Refined Capital Decision Lineage Runtime Persistence Integration

Task type: IMPLEMENTATION + END-TO-END LINEAGE PERSISTENCE

Fresh run / resume / replay / Historical rerun / long Historical: NO

## Primary Judgment

PRIMARY_JUDGMENT =
PHASE31_G45_REFINED_CAPITAL_LINEAGE_RUNTIME_PERSISTENCE_IMPLEMENTED_ACCEPTED

G45 extends the existing G30 `strategy_authority_lineage` envelope with a
versioned compact `refined_capital_decision_lineage.v1` payload. The payload is
created at the Runtime Planning authority boundary from already-authoritative
Strategy / Portfolio Construction / Position Sizing evidence and is then
preserved through the existing Pending, Submit, Historical snapshot,
Execution, and ledger projection lineage path.

No downstream layer re-runs Market Quality, Risk Pacing, Opportunity Quality,
cash competition, capital winner selection, ADD / re-entry semantics, lot
reconsideration, or quantity authority.

## Implementation Summary

Changed:

- `src/ai_fund_lab_v2/strategy/runtime_planning.py`
- `tests/runtime_v2/test_phase31_g45_refined_capital_lineage.py`
- `docs/phase_reports/phase31_g45_refined_capital_decision_lineage_runtime_persistence_integration.md`

Runtime Planning now persists:

- top-level `strategy_authority_lineage.refined_capital_decision_lineage`
- per-plan / per-item `strategy_authority_lineage.refined_capital_decision_lineage`
- schema version `refined_capital_decision_lineage.v1`
- compact canonical evidence identities, hashes, reason codes, as-of fields,
  winner fields, ADD / re-entry / lot / sizing summaries, and explicit
  downstream no-redecision counters

Older or thin lineage sources are not silently reinterpreted. If refined
canonical evidence is absent, the lineage records:

```text
lineage_status = UNAVAILABLE_LEGACY_RECORD
missing_refined_lineage_not_reconstructed_from_later_state = True
```

## Inventory

PRE_G45_RUNTIME_LINEAGE_INVENTORY_COMPLETE = YES

Existing G30/G31 lineage consumers confirmed:

- Runtime Planning writes top-level and per-plan `strategy_authority_lineage`.
- Pending model/writer/reader preserve top-level and item lineage/hash.
- Submit command copies item lineage.
- Submit ledger order records copy Pending item or command lineage.
- Historical submit evidence persists command lineage.
- Historical broker-readonly normalization preserves order lineage.
- Execution projected order ledger records preserve order lineage.

## Required Acceptance

REFINED_CAPITAL_LINEAGE_SCHEMA_IMPLEMENTED = YES

LINEAGE_TRACEABILITY_COMPLETE = YES

UNBOUNDED_ARTIFACT_DUPLICATION_CREATED = NO

RUNTIME_PLANNING_PERSISTS_REFINED_LINEAGE = YES

PENDING_ITEM_PERSISTS_REFINED_LINEAGE = YES

PENDING_PLAN_PERSISTS_REFINED_LINEAGE = YES

PENDING_RELOAD_LINEAGE_EQUIVALENCE = PASS

SUBMIT_COMMAND_PERSISTS_REFINED_LINEAGE = YES

ORDER_LEDGER_PERSISTS_REFINED_LINEAGE = YES

HISTORICAL_SUBMIT_EVIDENCE_PERSISTS_REFINED_LINEAGE = YES

EXECUTION_SNAPSHOT_PERSISTS_REFINED_LINEAGE = YES

PROJECTED_ORDER_LEDGER_PERSISTS_REFINED_LINEAGE = YES

FILL_PROJECTION_LINEAGE_PRESERVED = YES

DOWNSTREAM_RISK_PACING_RECOMPUTATION_COUNT = 0

DOWNSTREAM_OPPORTUNITY_QUALITY_RECOMPUTATION_COUNT = 0

DOWNSTREAM_CASH_COMPETITION_RECOMPUTATION_COUNT = 0

DOWNSTREAM_CAPITAL_WINNER_RECOMPUTATION_COUNT = 0

DOWNSTREAM_CAPITAL_RECLASSIFICATION_COUNT = 0

VALID_MULTI_LAYER_VALIDATION_PRESERVED = YES

CASH_WINNER_DOWNSTREAM_SECURITY_SUBSTITUTION_COUNT = 0

SECURITY_WINNER_QUANTITY_SOURCE = POSITION_SIZING

LOT_RECONSIDERATION_LINEAGE_COMPLETE = YES

ADD_BINDING_LINEAGE_COMPLETE = YES

REENTRY_BINDING_LINEAGE_COMPLETE = YES

FINAL_NO_DEPLOYABLE_LINEAGE_COMPLETE = YES

REFINED_LINEAGE_TEMPORAL_CONTRACT = PASS

FUTURE_INPUT_COUNT = 0

HISTORICAL_OUTCOME_LINEAGE_INPUT_COUNT = 0

PAPER_LEDGER_DECISION_INPUT_COUNT = 0

AUDIT_RESULT_DECISION_INPUT_COUNT = 0

REFINED_LINEAGE_SCHEMA_VERSIONED = YES

MISSING_REFINED_LINEAGE_NOT_RECONSTRUCTED_FROM_LATER_STATE = YES

LEGACY_RUNTIME_CAPITAL_DECISION_PATH_COUNT = 0

PRODUCTION_DEMO_HISTORICAL_LINEAGE_CONTRACT_ALIGNED = YES

BUY_NEW_REFINED_LINEAGE_E2E = PASS

CASH_WINNER_REFINED_LINEAGE_E2E = PASS

ADD_REFINED_LINEAGE_E2E = PASS

LOT_RECONSIDERATION_REFINED_LINEAGE = PASS

PENDING_RELOAD_REFINED_LINEAGE_EQUIVALENCE = PASS

NO_DOWNSTREAM_REDECISION_SYNTHETIC = PASS

G30_G31_LINEAGE_REGRESSION = PASS

ACCOUNTING_BASIS_REGRESSION = PASS

SELL_NON_REGRESSION = PASS

SAFETY_NON_REGRESSION = PASS

POSITION_SIZING_NON_REGRESSION = PASS

G43_G44_NON_REGRESSION = PASS

## Verification

G45 focused tests:

```bash
python3 -m pytest tests/runtime_v2/test_phase31_g45_refined_capital_lineage.py
```

Result:

```text
4 passed
```

Focused lineage / G40-G44 / Pending / ledger projection regression:

```bash
python3 -m pytest tests/runtime_v2/test_phase31_g45_refined_capital_lineage.py tests/runtime_v2/test_phase31_g30_authority_lineage.py tests/strategy/test_phase31_g40_opportunity_quality_continuum.py tests/strategy/test_phase31_g41_cash_competitor_evidence.py tests/strategy/test_phase31_g42_market_candidate_cash_interaction.py tests/strategy/test_phase31_g43_risk_pacing_economic_binding.py tests/strategy/test_phase31_g44_add_reentry_lot_binding_integration.py tests/runtime_v2/test_phase13_p_pending_reader_writer.py tests/runtime_v2/test_phase13_q_ledger_projection.py
```

Result:

```text
56 passed
```

Focused Submit / fill projection / accounting basis / Position Sizing
regression:

```bash
python3 -m pytest tests/runtime_v2/test_phase31_f1w_item_scoped_partial_submit.py tests/runtime_v2/test_phase14e25_runtime_owned_fill_projection.py tests/runtime_v2/test_phase24_h_cost_basis_authority.py tests/strategy/test_phase22_j_position_sizing.py tests/runtime_v2/test_phase13_o_ledger_models.py tests/runtime_v2/test_phase13_o_ledger_append_dedup.py
```

Result:

```text
143 passed
```

PY_COMPILE = PASS

```bash
PYTHONPYCACHEPREFIX=/private/tmp/ai_fund_lab_v2_pycache_g45 python3 -m py_compile src/ai_fund_lab_v2/strategy/runtime_planning.py tests/runtime_v2/test_phase31_g45_refined_capital_lineage.py
```

GIT_DIFF_CHECK = PASS

```bash
git diff --check -- src/ai_fund_lab_v2/strategy/runtime_planning.py tests/runtime_v2/test_phase31_g45_refined_capital_lineage.py docs/phase_reports/phase31_g45_refined_capital_decision_lineage_runtime_persistence_integration.md
```

## Required Output

PRIMARY_JUDGMENT =
PHASE31_G45_REFINED_CAPITAL_LINEAGE_RUNTIME_PERSISTENCE_IMPLEMENTED_ACCEPTED

PRE_G45_RUNTIME_LINEAGE_INVENTORY_COMPLETE =
YES

REFINED_CAPITAL_LINEAGE_SCHEMA_IMPLEMENTED =
YES

LINEAGE_TRACEABILITY_COMPLETE =
YES

UNBOUNDED_ARTIFACT_DUPLICATION_CREATED =
NO

RUNTIME_PLANNING_PERSISTS_REFINED_LINEAGE =
YES

PENDING_ITEM_PERSISTS_REFINED_LINEAGE =
YES

PENDING_PLAN_PERSISTS_REFINED_LINEAGE =
YES

PENDING_RELOAD_LINEAGE_EQUIVALENCE =
PASS

SUBMIT_COMMAND_PERSISTS_REFINED_LINEAGE =
YES

ORDER_LEDGER_PERSISTS_REFINED_LINEAGE =
YES

HISTORICAL_SUBMIT_EVIDENCE_PERSISTS_REFINED_LINEAGE =
YES

EXECUTION_SNAPSHOT_PERSISTS_REFINED_LINEAGE =
YES

PROJECTED_ORDER_LEDGER_PERSISTS_REFINED_LINEAGE =
YES

FILL_PROJECTION_LINEAGE_PRESERVED =
YES

DOWNSTREAM_RISK_PACING_RECOMPUTATION_COUNT =
0

DOWNSTREAM_OPPORTUNITY_QUALITY_RECOMPUTATION_COUNT =
0

DOWNSTREAM_CASH_COMPETITION_RECOMPUTATION_COUNT =
0

DOWNSTREAM_CAPITAL_WINNER_RECOMPUTATION_COUNT =
0

DOWNSTREAM_CAPITAL_RECLASSIFICATION_COUNT =
0

VALID_MULTI_LAYER_VALIDATION_PRESERVED =
YES

CASH_WINNER_DOWNSTREAM_SECURITY_SUBSTITUTION_COUNT =
0

SECURITY_WINNER_QUANTITY_SOURCE =
POSITION_SIZING

LOT_RECONSIDERATION_LINEAGE_COMPLETE =
YES

ADD_BINDING_LINEAGE_COMPLETE =
YES

REENTRY_BINDING_LINEAGE_COMPLETE =
YES

FINAL_NO_DEPLOYABLE_LINEAGE_COMPLETE =
YES

REFINED_LINEAGE_TEMPORAL_CONTRACT =
PASS

FUTURE_INPUT_COUNT =
0

HISTORICAL_OUTCOME_LINEAGE_INPUT_COUNT =
0

PAPER_LEDGER_DECISION_INPUT_COUNT =
0

AUDIT_RESULT_DECISION_INPUT_COUNT =
0

REFINED_LINEAGE_SCHEMA_VERSIONED =
YES

MISSING_REFINED_LINEAGE_NOT_RECONSTRUCTED_FROM_LATER_STATE =
YES

LEGACY_RUNTIME_CAPITAL_DECISION_PATH_COUNT =
0

PRODUCTION_DEMO_HISTORICAL_LINEAGE_CONTRACT_ALIGNED =
YES

BUY_NEW_REFINED_LINEAGE_E2E =
PASS

CASH_WINNER_REFINED_LINEAGE_E2E =
PASS

ADD_REFINED_LINEAGE_E2E =
PASS

LOT_RECONSIDERATION_REFINED_LINEAGE =
PASS

PENDING_RELOAD_REFINED_LINEAGE_EQUIVALENCE =
PASS

NO_DOWNSTREAM_REDECISION_SYNTHETIC =
PASS

FOCUSED_TEST_RESULTS =
PASS

PY_COMPILE =
PASS

GIT_DIFF_CHECK =
PASS

FUTURE_INFORMATION_USED =
NO

FRESH_RUN_EXECUTED =
NO

RESUME_EXECUTED =
NO

REPLAY_EXECUTED =
NO

LONG_HISTORICAL_EXECUTED =
NO
