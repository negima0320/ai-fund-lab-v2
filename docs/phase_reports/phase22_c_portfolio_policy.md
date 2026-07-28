# Phase22-C Portfolio Policy

## Primary Judgment

```text
PHASE22_C_COMPLETE_WITH_UPSTREAM_REVIEW_REQUIRED
```

Portfolio Policy foundation was implemented as a production-common, read-only Strategy artifact producer. The artifact is generated as `DRAFT / REVIEW_REQUIRED / NOT_ELIGIBLE` because upstream Market Context and Corporate Event artifacts remain `REVIEW_REQUIRED / NOT_ELIGIBLE`.

Phase22-D entry ready: `YES`, for read-only policy reference foundation only.
Runtime switch ready: `NO`.
Legacy retirement ready: `NO`.

## Reviewed SoT

- `docs/phase_reports/phase21_k_final_design_freeze_phase21_closure_and_phase22_entry_approval.md`
- `docs/02_architecture/strategy_architecture_v1.md`
- `docs/phase_reports/phase22_strategy_architecture_implementation_plan.md`
- `docs/03_ai_design/portfolio_manager_policy_design.md`
- `docs/03_ai_design/market_context_design.md`
- `docs/03_ai_design/corporate_event_authority_design.md`
- `docs/03_ai_design/capital_deployment_design.md`
- `docs/03_ai_design/position_management_ai_design.md`
- `docs/02_architecture/runtime_architecture_v2.md`
- `docs/02_architecture/autonomous_ai_operations_architecture.md`
- `docs/02_architecture/artifact_acceptance_contract.md`
- `docs/phase_reports/phase21_i_cutover_completeness_runtime_wiring_and_regression_preservation_audit.md`
- `docs/phase_reports/phase21_j_legacy_retirement_authority_revocation_and_data_decommission_architecture.md`
- Phase22-A / AA / B reports, schemas, code, and evidence

## Existing Policy Inventory

Machine-readable inventory:

```text
reports/phase22_c_portfolio_policy/phase22_c_evidence_20260727/existing_policy_inventory.json
```

Current active policy-like logic remains in:

```text
src/ai_fund_lab_v2/runtime_v2/policy/capital_deployment.py
src/ai_fund_lab_v2/runtime_v2/planning/morning_pipeline.py
src/ai_fund_lab_v2/runtime_v2/planning/add_consumer.py
src/ai_fund_lab_v2/runtime_v2/planning/sell_pipeline.py
src/ai_fund_lab_v2/runtime_v2/submit/pipeline.py
src/ai_fund_lab_v2/runtime_v2/position_management/producer.py
configs/runtime_v2/capital_deployment.json
configs/runtime_v2/capital_deployment_demo.json
```

Phase22-C does not move active authority away from these paths.

## Current Authority Inventory

Machine-readable inventory:

```text
reports/phase22_c_portfolio_policy/phase22_c_evidence_20260727/current_authority_inventory.json
```

Current authority remains:

- position count: `CapitalDeploymentPolicy.max_positions`
- cash target style limits: `target_investment_ratio` and `cash_buffer`
- gross exposure: `CapitalDeploymentPolicy.max_exposure`
- new entry permission: Opportunity eligibility, Planning, Safety
- ADD / REDUCE / EXIT: Position Management AI and existing planning consumers

Future Portfolio Policy authority is represented in Phase22-C only as intent axes, not concrete values.

## Direct Reference Inventory

Machine-readable inventory:

```text
reports/phase22_c_portfolio_policy/phase22_c_evidence_20260727/direct_reference_inventory.json
```

References were classified across Candidate, Opportunity, Portfolio Manager naming, Position Management, Portfolio Construction, Capital Deployment, Runtime Planning, Historical adapter, status/summarize, test fixtures, recovery, and scheduler/LaunchAgent. No cutover was performed.

## Portfolio Policy Responsibility

Portfolio Policy now has a standalone foundation:

```text
src/ai_fund_lab_v2/strategy/portfolio_policy.py
schemas/strategy/portfolio_policy.schema.json
```

It produces portfolio-level policy intent and status evidence only. It does not decide individual BUY, SELL, HOLD, ADD, REDUCE, EXIT, rank, score, weight, quantity, Pending, Submit, Approval, Execution, Fill, Ledger, or Current.

## Input Contract

Implemented producer inputs:

- `business_date`
- Market Context artifact metadata
- Corporate Event artifact metadata / coverage
- Candidate summary
- Opportunity summary
- current portfolio summary
- current cash summary
- current exposure summary
- explicit policy config
- source refs / source hashes

Forbidden inputs remain unused: backtest result, historical performance, paper ledger PnL, future return, future regime, future event, test pass/fail, accepted/rejected mimicry, future portfolio value.

## Schema / Intent Taxonomy

Schema version:

```text
portfolio_policy.v1
```

Intent axes are separate:

```text
risk_posture
entry_posture
position_count_posture
cash_posture
exposure_posture
position_management_bias
```

Machine-readable validation:

```text
reports/phase22_c_portfolio_policy/phase22_c_evidence_20260727/schema_validation.json
reports/phase22_c_portfolio_policy/phase22_c_evidence_20260727/policy_intent_validation.json
```

## Concrete Value Non-decision

Phase22-C did not decide:

```text
target_position_count
minimum_positions
target_positions
maximum_positions
target_cash_ratio
target_exposure_ratio
gross_exposure
position_size
minimum_holding
cooldown
```

The artifact records `concrete_values_decided=false` and rejects concrete target fields in validation.

## Upstream Status Handling

Machine-readable validation:

```text
reports/phase22_c_portfolio_policy/phase22_c_evidence_20260727/upstream_status_validation.json
```

Observed status:

```text
Market Context: SOURCE_NOT_ELIGIBLE
Corporate Event: SOURCE_NOT_ELIGIBLE
Portfolio Policy producer_result_status: REVIEW_REQUIRED
runtime_consumer_eligibility: NOT_ELIGIBLE
```

No fixed BALANCED/RISK_OFF `PASS` fallback is used. The fixture config can express intent labels, but upstream `REVIEW_REQUIRED / NOT_ELIGIBLE` keeps the artifact `REVIEW_REQUIRED`.

## Date / PIT / Hash / Lineage

Machine-readable validation:

```text
reports/phase22_c_portfolio_policy/phase22_c_evidence_20260727/date_pit_validation.json
reports/phase22_c_portfolio_policy/phase22_c_evidence_20260727/hash_lineage_validation.json
```

Validated:

- Portfolio Policy business_date matches requested business_date
- Market Context / Corporate Event business_date alignment
- Candidate / Opportunity summary business_date alignment
- `feature_date <= business_date`
- no implicit latest fallback
- no previous-day Policy copy
- output artifact hash
- source artifact lineage and source hashes
- policy config hash

## Failure / Bootstrap

Failure contract:

- upstream REVIEW_REQUIRED / NOT_ELIGIBLE -> Portfolio Policy REVIEW_REQUIRED
- upstream BLOCK / schema mismatch / date mismatch / hash mismatch / source missing -> BLOCK
- required config missing -> REVIEW_REQUIRED unless required upstream is missing, then fail-closed BLOCK
- future leakage -> BLOCK
- lineage/hash shortage -> REVIEW_REQUIRED or BLOCK according to severity

Bootstrap validation:

```text
reports/phase22_c_portfolio_policy/phase22_c_evidence_20260727/bootstrap_validation.json
```

Initial absence does not copy previous-day policy, does not use latest fallback, and does not produce fixed BALANCED/RISK_OFF PASS.

## Fixture / Shadow

Machine-readable validation:

```text
reports/phase22_c_portfolio_policy/phase22_c_evidence_20260727/fixture_shadow_validation.json
```

The fixture consumer reads DRAFT artifacts for schema/status/hash/lineage checks and rejects production use. It does not decide position count, cash ratio, exposure, position sizing, Runtime Planning, Pending, or Submit.

## No-behavior-change

Machine-readable validation:

```text
reports/phase22_c_portfolio_policy/phase22_c_evidence_20260727/behavior_preservation.json
reports/phase22_c_portfolio_policy/phase22_c_evidence_20260727/produced_not_consumed_validation.json
reports/phase22_c_portfolio_policy/phase22_c_evidence_20260727/scope_preservation_validation.json
```

Preserved:

```text
Candidate behavior changed = false
Opportunity behavior changed = false
PM behavior changed = false
Position Management changed = false
Portfolio Construction changed = false
Capital Deployment changed = false
Runtime Planning changed = false
Pending changed = false
Submit changed = false
```

## Artifacts

Generated read-only artifact:

```text
.runtime/strategy_artifacts/portfolio_policy/2026-07-15/portfolio_policy.json
```

Machine-readable report:

```text
reports/phase22_c_portfolio_policy/phase22_c_portfolio_policy.json
```

Evidence directory:

```text
reports/phase22_c_portfolio_policy/phase22_c_evidence_20260727/
```

## Tests

Phase22-C tests:

```text
python3 -m pytest tests/strategy/test_phase22_c_portfolio_policy.py
```

Result:

```text
10 passed
```

Core short regression:

```text
python3 -m pytest tests/strategy/test_phase22_a_market_context.py tests/strategy/test_phase22_aa_corporate_event.py tests/strategy/test_phase22_b_candidate_opportunity_compatibility.py tests/strategy/test_phase22_c_portfolio_policy.py tests/test_phase4e_candidate_feature_builder_mock.py tests/opportunity_ai/test_phase5f_opportunity_inference.py tests/runtime_v2/test_phase17_b1i_b_pm_adapter_authority.py
```

Result:

```text
47 passed
```

Compile:

```text
PYTHONPYCACHEPREFIX=.runtime/pycache_phase22c python3 -m compileall src/ai_fund_lab_v2/strategy tests/strategy
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

Phase22-C code path is not involved.

Additional attempted policy/runtime regression:

```text
tests/runtime_v2/test_phase15h_capital_deployment_policy.py
tests/runtime_v2/test_phase17_b1i_b_pm_adapter_authority.py
```

Result:

```text
51 passed
1 failed
```

Failure was existing sell_planning CLI `exit_code=20`, not a Phase22-C consumer path.

## Design Freeze Compliance

No Portfolio Policy authority was connected to production consumers.
No PM behavior changed.
No Position Management behavior changed.
No Portfolio Construction behavior changed.
No Capital Deployment behavior changed.
No Runtime Planning behavior changed.
No Market Context threshold/source decision changed.
No Corporate Event source gap was filled.
No old path was removed.
No artifact was promoted to ACCEPTED.

## Gaps

Blocking gaps:

```text
none
```

Non-blocking gaps:

```text
Market Context remains REVIEW_REQUIRED / NOT_ELIGIBLE.
Corporate Event remains REVIEW_REQUIRED / NOT_ELIGIBLE.
Concrete dynamic position count/cash/exposure/sizing remain deferred to Phase22-H/I/J.
Ancillary existing runtime policy/opportunity tests returned REVIEW_REQUIRED/exit 20 without Phase22-C code path involvement.
```

## Next Gate

```text
Phase22-D entry ready: YES
Runtime switch ready: NO
Legacy retirement ready: NO
```
