# Phase22-B Candidate / Opportunity Compatibility

## Primary Judgment

```text
PHASE22_B_COMPLETE_WITH_UPSTREAM_REVIEW_REQUIRED
```

Candidate / Opportunity compatibility boundary was implemented as read-only Strategy artifact validation. Market Context and Corporate Event artifacts are schema/hash/lineage compatible for shadow use, but remain `DRAFT / REVIEW_REQUIRED / NOT_ELIGIBLE`. They are not production decision inputs, not Candidate filters, not Opportunity scoring inputs, and not ranking inputs.

Phase22-C entry ready: `YES`, as compatible-not-connected only.
Runtime switch ready: `NO`.
Legacy retirement ready: `NO`.

## Reviewed SoT

- `docs/phase_reports/phase21_k_final_design_freeze_phase21_closure_and_phase22_entry_approval.md`
- `docs/phase_reports/phase21_i_cutover_completeness_runtime_wiring_and_regression_preservation_audit.md`
- `docs/phase_reports/phase21_j_legacy_retirement_authority_revocation_and_data_decommission_architecture.md`
- `docs/02_architecture/strategy_architecture_v1.md`
- `docs/02_architecture/runtime_architecture_v2.md`
- `docs/03_ai_design/market_context_design.md`
- `docs/03_ai_design/corporate_event_authority_design.md`
- `docs/02_architecture/artifact_acceptance_contract.md`
- `docs/phase_reports/phase22_a_market_context_artifact_foundation.md`
- `docs/phase_reports/phase22_aa_corporate_event_artifact_foundation.md`

## Candidate Inventory

Candidate producer remains the existing runtime BUY AI path:

```text
src/ai_fund_lab_v2/runtime_v2/buy_ai/producer.py::_produce_candidate_artifact
scripts/run_phase4bg_formal_candidate_inference.py::build_scored_candidates
src/ai_fund_lab_v2/candidate_ai/feature_builder.py::build_candidate_features_mock_with_audit
```

Candidate schema remains `runtime_v2_candidate_decision_v1` plus the Candidate feature contract in `candidate_ai.schemas.CandidateFeatureSchemaContract`. Candidate artifacts remain `runtime_state/buy_ai/<business_date>/candidate_decisions.json` and historical/report Candidate Top50 artifacts. Candidate consumers remain Opportunity inference and status/report readers.

Candidate responsibilities are unchanged: universe eligibility, tradability/data readiness style prerequisites, score/rank output, and reason codes. Phase22-B added no Candidate filter and no Candidate scoring rule.

## Opportunity Inventory

Opportunity producer remains:

```text
src/ai_fund_lab_v2/runtime_v2/buy_ai/producer.py::_produce_opportunity_artifact
src/ai_fund_lab_v2/opportunity_ai/inference.py::run_opportunity_inference
src/ai_fund_lab_v2/opportunity_ai/inference.py::build_inference_output
```

Opportunity schema remains `runtime_v2_opportunity_ranking_v1` plus `opportunity_ai.inference.OUTPUT_COLUMNS`. Opportunity consumers remain Morning Planning AI signals, `runtime_v2/buy_ai/opportunity_eligibility.py`, PM adapter/status/report readers.

Existing market/sector proxy references were inventoried but not changed: `opportunity_ai/market_sector_completion.py` produces market return, market breadth, market volatility, market risk/downtrend, sector return, sector rank, sector breadth, and stock-vs-sector features. `opportunity_ai/inference.py::calculate_downside_risk_score` uses existing volatility/trend/volume proxy columns.

## Direct Reference Inventory

Machine-readable inventory:

```text
reports/phase22_b_candidate_opportunity_compatibility/phase22_b_evidence_20260727/direct_reference_inventory.json
```

Current direct references were classified as Candidate, Opportunity, Runtime, Historical adapter, status/summarize, test fixture, recovery, and scheduler/LaunchAgent references. Phase22-B records these as future cutover surfaces only.

## Compatibility Implementation

Added:

```text
src/ai_fund_lab_v2/strategy/candidate_opportunity_compatibility.py
tests/strategy/test_phase22_b_candidate_opportunity_compatibility.py
```

The implementation validates:

- supported schema versions: `strategy_market_context.v1`, `corporate_event_authority.v1`
- `business_date` equality with requested Candidate/Opportunity business date
- `feature_date <= business_date`
- artifact hash
- source artifact lineage and source hashes
- lifecycle status, producer result status, runtime eligibility
- production use rejection for `DRAFT / REVIEW_REQUIRED / NOT_ELIGIBLE`
- Candidate output preservation
- Opportunity score/rank/feature vector/tie-break preservation

Compatibility states implemented include `COMPATIBLE_NOT_CONNECTED`, `INCOMPATIBLE_SCHEMA`, `INCOMPATIBLE_DATE`, `INCOMPATIBLE_HASH`, `SOURCE_REVIEW_REQUIRED`, `SOURCE_BLOCKED`, `SOURCE_NOT_ELIGIBLE`, `SOURCE_MISSING`, and `AUTHORITY_CONFLICT`.

## Schema / Status / Eligibility

Evidence:

```text
reports/phase22_b_candidate_opportunity_compatibility/phase22_b_evidence_20260727/schema_compatibility_validation.json
reports/phase22_b_candidate_opportunity_compatibility/phase22_b_evidence_20260727/eligibility_validation.json
```

Observed result:

```text
Market Context status: SOURCE_NOT_ELIGIBLE
Corporate Event status: SOURCE_NOT_ELIGIBLE
Candidate compatibility status: COMPATIBLE_NOT_CONNECTED
Opportunity compatibility status: COMPATIBLE_NOT_CONNECTED
```

Both artifacts are shadow-readable but production decision use is rejected. `ACCEPTED` was not auto-assigned.

## Date / PIT / Hash / Lineage

Evidence:

```text
reports/phase22_b_candidate_opportunity_compatibility/phase22_b_evidence_20260727/date_alignment_validation.json
reports/phase22_b_candidate_opportunity_compatibility/phase22_b_evidence_20260727/hash_lineage_validation.json
```

Validation confirmed:

```text
requested_business_date = 2026-07-15
market_context.business_date = 2026-07-15
corporate_event.business_date = 2026-07-15
feature_date PIT = PASS
artifact hash = PASS
source lineage = PASS
source hashes = PASS
implicit latest fallback used = false
```

Cross-date artifact mismatch is tested and fails closed.

## Behavior Preservation

Candidate evidence:

```text
reports/phase22_b_candidate_opportunity_compatibility/phase22_b_evidence_20260727/candidate_behavior_preservation.json
```

Preserved:

```text
Candidate count
Candidate security codes
Candidate order
Candidate eligibility
Candidate reason codes
```

Opportunity evidence:

```text
reports/phase22_b_candidate_opportunity_compatibility/phase22_b_evidence_20260727/opportunity_behavior_preservation.json
reports/phase22_b_candidate_opportunity_compatibility/phase22_b_evidence_20260727/ranking_preservation.json
```

Preserved:

```text
Opportunity count
Opportunity security codes
Opportunity score
Opportunity rank
Opportunity feature vector
Opportunity tie-break
```

## Shadow Compatibility

Evidence:

```text
reports/phase22_b_candidate_opportunity_compatibility/phase22_b_evidence_20260727/shadow_compatibility_validation.json
reports/phase22_b_candidate_opportunity_compatibility/phase22_b_evidence_20260727/produced_compatible_not_consumed_validation.json
```

Phase22-B reads Market Context and Corporate Event artifacts only to produce compatibility results. It does not write to Candidate output, Opportunity output, Runtime Planning, Pending, Submit, Approval, Execution, Ledger, or Current.

## Tests

Executed short tests only:

```text
python3 -m pytest tests/strategy/test_phase22_b_candidate_opportunity_compatibility.py
```

Result:

```text
10 passed
```

Regression:

```text
python3 -m pytest tests/strategy/test_phase22_a_market_context.py tests/strategy/test_phase22_aa_corporate_event.py tests/strategy/test_phase22_b_candidate_opportunity_compatibility.py tests/test_phase4e_candidate_feature_builder_mock.py tests/opportunity_ai/test_phase5f_opportunity_inference.py
```

Result:

```text
33 passed
```

Compile:

```text
PYTHONPYCACHEPREFIX=.runtime/pycache_phase22b python3 -m compileall src/ai_fund_lab_v2/strategy tests/strategy
```

Result:

```text
PASS
```

Known regression confirmation:

```text
python3 -m pytest tests/phase12/test_market_calendar.py tests/runtime_v2/test_phase14e36_feature_date_contract_carryover_policy.py tests/artifact_registry/test_inventory_helpers.py
```

Result:

```text
10 passed
1 failed
```

Known failure remains:

```text
tests/runtime_v2/test_phase14e36_feature_date_contract_carryover_policy.py::test_phase14e36_morning_uses_selected_carryover_feature_date
StopIteration while finding morning_ai_planning_pending_pipeline stage
```

Phase22-B code path is not involved.

## Design Freeze Compliance

No Candidate responsibility change.
No Opportunity responsibility change.
No Market Context threshold/window/source decision.
No Corporate Event source gap fixture/fill.
No Production Consumer connection.
No Runtime switch.
No Pending/Submit connection.
No old path removal.
No Accepted promotion.
No long Historical test.

## Gaps

Blocking gaps:

```text
none
```

Non-blocking upstream gaps:

```text
Market Context threshold/window/benchmark/sector source remain REVIEW_REQUIRED.
Corporate Event earnings schedule, financial statements, standalone corporate actions, TOB/merger coverage remain REVIEW_REQUIRED.
```

## Next Gate

```text
Phase22-C entry ready: YES
Runtime switch ready: NO
Legacy retirement ready: NO
```
