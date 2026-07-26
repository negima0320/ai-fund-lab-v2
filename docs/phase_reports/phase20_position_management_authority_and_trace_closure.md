# Phase20-S Position Management Decision-Time Authority and Trace Closure

## Status

PHASE20_S_POSITION_MANAGEMENT_AUTHORITY_AND_TRACE_COMPLETE

## Scope

This phase closes the Phase20-R Position Management authority / observability gap.

No Performance threshold, score formula, decision order, Runtime action, quantity ratio, AI training, calibration, or full historical smoke was changed or executed.

## Inputs Reviewed

- `docs/phase_reports/phase20_position_management_design_review.md`
- `docs/phase_reports/phase20_position_management_decision_trace_and_outcome_analysis.md`
- `docs/02_architecture/position_management_feature_input_contract.md`
- `docs/03_ai_design/position_management_ai_design.md`
- `src/ai_fund_lab_v2/position_management_ai/inference.py`
- `src/ai_fund_lab_v2/runtime_v2/position_management/producer.py`

## Implementation Summary

Added the formal contract:

- `docs/02_architecture/position_management_decision_trace_contract.md`

Added the machine-readable schema:

- `schemas/runtime_v2/position_management_decision_trace.schema.json`

Updated Runtime PM producer to emit:

- `.runtime/runtime_state/position_management/<business_date>/position_management_decision_trace.json`
- embedded `decision_trace` in each `position_management_decisions.json` decision
- `dominant_cause`
- `secondary_causes`
- `decision_reason_codes`
- `action_score`
- `selected_action_score`
- `confidence_semantics = selected_action_score_not_calibrated_probability`

Updated Runtime Test PM snapshot copying to preserve the new trace-derived fields when present, while keeping legacy fixture compatibility.

## Authority Closure

Decision-time position state is now explicit:

- Canonical PM position state: `current_holdings_snapshot.csv`, derived from Runtime Current.
- Canonical technical feature state: `position_feature_input.parquet` / `.csv`.
- Canonical opportunity/risk context: `position_management_opportunity_context.csv`.
- Non-canonical operational copies inside `position_feature_input` are retained only as observability copies and compared in trace.

The trace records `position_state_copy_mismatch` so cases like Phase20-R can be detected without changing PM scoring.

## Reason Code Closure

The legacy `reason` field remains for compatibility, but trace now formalizes dominant causes:

- `REDUCE_BY_WEAK_HOLD_SCORE`
- `REDUCE_BY_REDUCE_SCORE_THRESHOLD`
- `REDUCE_BY_HIGH_DOWNSIDE_RISK`
- `REDUCE_BY_PEAK_DRAWDOWN_WARNING`
- `HOLD_BY_STRONG_CONTINUATION`
- `HOLD_BY_PARTIAL_CONTINUATION`
- `HOLD_BY_FALLBACK`
- `EXIT_BY_HARD_STOP`
- `EXIT_BY_PEAK_DRAWDOWN`
- `EXIT_BY_TREND_AND_EDGE_BREAK`
- `EXIT_BY_RISK_GUARD`
- `EXIT_BY_EXIT_SCORE_HIGH`
- `EXIT_BY_WEAK_HOLD_SCORE`

## Confidence Semantics

`confidence` is retained as a compatibility alias.

The formal semantics are:

```text
selected_action_score_not_calibrated_probability
```

New fields:

- `action_score`
- `selected_action_score`
- `confidence_semantics`

Consumers must not treat PM confidence as calibrated probability.

## Runtime Compatibility

The implementation is observability-only. It does not change:

- `decision`
- `runtime_action`
- `runtime_sell_quantity`
- `runtime_quantity_authority`
- Sell Planning consumer output

The targeted regression test verifies an intentional `current_holdings_snapshot` / `position_feature_input` price mismatch is recorded while the PM decision and Sell Planning handoff remain unchanged.

## Validation

Executed:

```text
PYTHONPYCACHEPREFIX=/private/tmp/pycache python3 -m py_compile src/ai_fund_lab_v2/runtime_v2/position_management/producer.py
PYTHONPYCACHEPREFIX=/private/tmp/pycache python3 -m pytest -q tests/runtime_v2/test_phase15ap_position_management_input_contract.py::test_phase20_s_pm_decision_trace_preserves_runtime_behavior_and_authority
PYTHONPYCACHEPREFIX=/private/tmp/pycache python3 -m pytest -q tests/runtime_v2/test_phase15ap_position_management_input_contract.py
python3 -m json.tool schemas/runtime_v2/position_management_decision_trace.schema.json
```

Result:

- compile: PASS
- targeted unit test: PASS
- PM input contract regression file: PASS, 15 tests
- schema JSON syntax validation: PASS
- instance schema validation: NOT_RUN because `jsonschema` is not installed in the local environment

Full historical smoke was not executed.

## Acceptance

- PM_DECISION_TIME_PRICE_AUTHORITY_EXPLICIT: PASS
- PM_INPUT_ARTIFACT_RELATIONSHIP_EXPLICIT: PASS
- PM_DECISION_TRACE_COMPLETE: PASS
- PM_TRIGGER_CAUSE_OBSERVABLE: PASS
- PM_CONFIDENCE_SEMANTICS_EXPLICIT: PASS
- PM_RUNTIME_BEHAVIOR_UNCHANGED: PASS
- PM_THRESHOLD_CHANGE_STILL_PROHIBITED: PASS

## Final Status

PHASE20_S_POSITION_MANAGEMENT_AUTHORITY_AND_TRACE_COMPLETE
