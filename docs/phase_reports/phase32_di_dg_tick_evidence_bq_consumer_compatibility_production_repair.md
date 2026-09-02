# Phase32-DI — DG Tick-Normalized Evidence BQ Consumer Compatibility Production Repair

## Final Judgment

`PHASE32_DI_DG_TICK_EVIDENCE_BQ_CONSUMER_COMPATIBILITY_REPAIRED_FRESH_VALIDATION_REQUIRED`

Phase32-DH root cause is confirmed and narrowly repaired. Technical Features already produced valid current-run PIT tick-normalized evidence; Buy Quality now consumes that evidence correctly through the Strategy materialization surface, and empty Candidate/Opportunity placeholder fields no longer shadow valid Technical Features authority.

No Strategy thresholds, weights, ranks, entry policy, PC tick caps, PM semantics, G129 semantics, or performance tuning were changed. The failed target run was not mutated and was not resumed/recovered/replayed.

## Root Cause Confirmed

`ROOT_CAUSE_CONFIRMED = DG_BQ_TICK_EVIDENCE_MATERIALIZATION_SOURCE_SELECTION_DEFECT`

Accepted DH facts preserved:

- Target run: `runtime-test-historical-extended-smoke-20260902T051836637658Z`
- First HALT: `2022-10-03:morning`
- First canonical reason: `strategy_planning_authority_unresolved`
- First planning reason code: `strategy_plan_order_side_unresolved`
- Technical Features first-day authority: `PASS`
- 50/50 Technical Features rows had valid canonical tick evidence.
- BQ read 50/50 rows as `tick_normalized_evidence_missing` before DI.
- PM accepted generation/hash: `PASS`
- Runtime fail-closed behavior: correct.

## Repair Performed

Files changed:

- `src/ai_fund_lab_v2/strategy/shadow_runtime.py`
- `src/ai_fund_lab_v2/strategy/buy_quality.py`
- `tests/strategy/test_phase32_dg_tick_normalized_production.py`
- `docs/02_architecture/strategy_intelligence_architecture_v1.md`
- `docs/phase_reports/phase32_di_dg_tick_evidence_bq_consumer_compatibility_production_repair.md`

### Full Tick Evidence Propagation

`FULL_TICK_EVIDENCE_PROPAGATION = PASS`

`shadow_runtime._supply_reentry_source_evidence(...)` now propagates the full DG tick-normalized row contract from current-run Technical Features into the BQ-consumed opportunity row surface:

- `minimum_tick`
- `single_tick_pct`
- `minimum_tick_authority_status`
- `minimum_tick_authority_hash`
- `minimum_tick_authority`
- `minimum_tick_authority_source`
- `minimum_tick_resolution`
- `tick_quantization_status`
- `tick_normalized_trend_state`
- `momentum_confidence_state`
- `close_level_diversity_state`
- `candidate_rank_tick_reliability`
- `trend_robustness_authority`
- `momentum_confidence_authority`
- `tick_quantization_reason_codes`
- selected tick-context counts and movement fields

### Empty Placeholder Shadowing

`EMPTY_PLACEHOLDER_SHADOWING_FIXED = YES`

`buy_quality._tick_quantization_source_row(...)` no longer treats empty placeholder keys as materialized DG evidence. A row with only:

```text
tick_quantization_status = ""
tick_normalized_trend_state = ""
momentum_confidence_state = ""
candidate_rank_tick_reliability = ""
```

is not selected as the tick evidence source.

### Evidence Precedence Contract

`BQ_TICK_EVIDENCE_PRECEDENCE_CONTRACT = current-run Technical Features enriched opportunity evidence > valid enriched opportunity evidence > valid candidate evidence > genuinely missing evidence`

Canonical owner selected:

`BQ_CANONICAL_TICK_SOURCE_OWNER = TECHNICAL_FEATURES_VIA_STRATEGY_MATERIALIZATION_SURFACE`

BQ does not reconstruct minimum-tick or tick-normalized evidence locally. It consumes already-materialized current-run Technical Features evidence through the existing Strategy materialization row surface.

### Fail-Closed Preservation

`GENUINE_MISSING_TICK_EVIDENCE_FAIL_CLOSED = PASS`

If DG placeholder keys are present but no materialized tick authority exists, BQ now returns explicit review-required tick evidence:

- `tick_quantization_status = INSUFFICIENT_EVIDENCE`
- `trend_state = INSUFFICIENT_EVIDENCE`
- `momentum_state = INSUFFICIENT_EVIDENCE`
- reason includes `tick_normalized_evidence_placeholder_without_authority`

Legacy rows with no DG tick evidence surface remain `NOT_APPLICABLE`; DG-shaped rows with missing materialized authority remain review/fail-closed.

## 2022-10-03 Evidence Compatibility Validation

`20221003_BQ_COMPATIBILITY_VALIDATION = PASS`

Using immutable target-run artifacts without runtime mutation:

- Input Technical Features rows: `50`
- `technical_supplied_count`: `50`
- Rebuilt BQ decision count: `50`
- BQ tick status counts: `{"PASS": 50}`
- `tick_normalized_evidence_missing` count: `0`
- `quality_action = REVIEW_REQUIRED` count caused by missing tick evidence: `0`
- First examples:
  - `94320`: `BUY_WAIT`, tick `PASS`, trend `ACCEPTABLE`
  - `76920`: `BUY_WAIT`, tick `PASS`, trend `ROBUST`
  - `94340`: `FULL_ALLOCATION_ELIGIBLE`, tick `PASS`, trend `ACCEPTABLE`

This was a focused, read-only Python reconstruction of BQ materialization. It did not run `fresh-run`, `resume`, `recover`, `replay`, or mutate the target run.

## Regression Tests

Commands run:

```bash
PYTHONPYCACHEPREFIX=/private/tmp/pycache python3 -m py_compile \
  src/ai_fund_lab_v2/strategy/buy_quality.py \
  src/ai_fund_lab_v2/strategy/shadow_runtime.py \
  src/ai_fund_lab_v2/strategy/tick_quantization.py \
  src/ai_fund_lab_v2/strategy/input_materialization.py
```

Result: `PASS`

```bash
PYTHONPATH=src PYTHONPYCACHEPREFIX=/private/tmp/pycache python3 -m pytest -q \
  tests/strategy/test_phase32_dg_tick_normalized_production.py \
  tests/strategy/test_phase32_df_minimum_tick_authority.py \
  tests/strategy/test_phase26_h_adaptive_buy_quality.py
```

Result: `48 passed`

```bash
PYTHONPATH=src PYTHONPYCACHEPREFIX=/private/tmp/pycache python3 -m pytest -q \
  tests/strategy/test_phase22_e_portfolio_construction.py \
  tests/strategy/test_phase22_j_position_sizing.py \
  tests/strategy/test_phase22_g_runtime_planning.py
```

Result: `281 passed`

```bash
PYTHONPATH=src PYTHONPYCACHEPREFIX=/private/tmp/pycache python3 -m pytest -q \
  tests/strategy/test_phase32_cw_minimal_residual_reentry.py \
  tests/strategy/test_phase31_g115_add_marginal_authoritative_binding.py \
  tests/runtime_v2/test_phase31_g30_authority_lineage.py \
  tests/runtime_v2/test_phase22_p_strategy_shadow_wiring.py
```

Result: `51 passed`

```bash
PYTHONPATH=src PYTHONPYCACHEPREFIX=/private/tmp/pycache python3 -m pytest -q \
  tests/runtime_v2/test_phase23_i_strategy_planning_authority.py::test_phase28_d70b_no_action_missing_current_authority_still_fails_closed
```

Result: `1 passed`

```bash
git diff --check -- \
  src/ai_fund_lab_v2/strategy/buy_quality.py \
  src/ai_fund_lab_v2/strategy/shadow_runtime.py \
  tests/strategy/test_phase32_dg_tick_normalized_production.py \
  docs/02_architecture/strategy_intelligence_architecture_v1.md
```

Result: `PASS`

Non-blocking note: a broader full-file run of `tests/runtime_v2/test_phase23_i_strategy_planning_authority.py` produced two failures in existing submit/corporate-action approval expectations. The failure reason was `corporate_action_event_authority_unusable`, not DI tick evidence propagation/source selection. The DI-required strategy planning unresolved-order-side fail-closed test passed individually.

## Required Status Answers

1. `ROOT_CAUSE_CONFIRMED`: `DG_BQ_TICK_EVIDENCE_MATERIALIZATION_SOURCE_SELECTION_DEFECT`
2. `FULL_TICK_EVIDENCE_PROPAGATION`: `PASS`
3. `EMPTY_PLACEHOLDER_SHADOWING_FIXED`: `YES`
4. `BQ_TICK_EVIDENCE_PRECEDENCE_CONTRACT`: `TECHNICAL_FEATURES_CURRENT_RUN_ENRICHED_OPPORTUNITY > VALID_ENRICHED_OPPORTUNITY > VALID_CANDIDATE > GENUINELY_MISSING`
5. `GENUINE_MISSING_TICK_EVIDENCE_FAIL_CLOSED`: `PASS`
6. `FIRST_DAY_FRESH_RUN_SHAPED_REGRESSION`: `PASS`
7. `20221003_BQ_COMPATIBILITY_VALIDATION`: `PASS`
8. `DG_TICK_SEMANTICS_CHANGED`: `NO`
9. `93180_DG_CONTROL_REGRESSION`: `PASS`
10. `LOW_PRICE_POSITIVE_CONTROL_REGRESSION`: `PASS` for `33500`, `76470`, `17570`, `67400`
11. `NORMAL_PRICE_CONTROL_REGRESSION`: `PASS` for `76920`, `94320`, `83060`
12. `MINIMUM_TICK_AUTHORITY_REGRESSION`: `PASS`
13. `BQ_PERFORMANCE_SEMANTICS_CHANGED`: `NO`
14. `PC_TICK_CAP_REGRESSION`: `PASS`
15. `PS_AUTHORITY_REGRESSION`: `PASS`
16. `STRATEGY_PLANNING_FAIL_CLOSED_REGRESSION`: `PASS`
17. `CW_REENTRY_REGRESSION`: `PASS`
18. `G129_BUY_ADD_REGRESSION`: `PASS`
19. `CAMPAIGN_IDENTITY_REGRESSION`: `PASS`
20. `BQ_CANONICAL_TICK_SOURCE_OWNER`: `TECHNICAL_FEATURES_VIA_STRATEGY_MATERIALIZATION_SURFACE`
21. `BQ_SOURCE_ARTIFACT_MANIFEST_UPDATED_IF_REQUIRED`: `NO_DIRECT_BQ_SOURCE_ARTIFACT_CHANGE_REQUIRED`; full evidence is propagated through existing materialized opportunity surface
22. `ARCHITECTURE_SOT_UPDATED_IF_REQUIRED`: `YES`; `docs/02_architecture/strategy_intelligence_architecture_v1.md`
23. `FOCUSED_REGRESSION_RESULT`: `PASS`, with unrelated broader submit/corporate-action expectation failures noted separately
24. `PRODUCTION_CHANGE_EXECUTED`: `YES`; narrow production evidence handoff/source-selection repair
25. `PERFORMANCE_TUNING_EXECUTED`: `NO`
26. `TARGET_RUN_MUTATED`: `NO`
27. `FRESH_VALIDATION_REQUIRED`: `YES`
28. `FRESH_VALIDATION_COMMAND`:

```bash
PYTHONPATH=src python3 scripts/runtime_test.py fresh-run \
  --profile historical-extended-smoke \
  --start-date 2022-10-03 \
  --business-days 650 \
  --initial-cash 1000000 \
  --confirm \
  --yes-i-understand-this-mutates-trading-state
```

29. `NEXT_RECOMMENDED_STEP`: user-operated fresh Historical validation with the command above
30. `FINAL_JUDGMENT`: `PHASE32_DI_DG_TICK_EVIDENCE_BQ_CONSUMER_COMPATIBILITY_REPAIRED_FRESH_VALIDATION_REQUIRED`

## Fresh Validation

`FRESH_VALIDATION_REQUIRED = YES`

Codex did not execute fresh validation. The user should run the fresh-run command after reviewing this repair.
