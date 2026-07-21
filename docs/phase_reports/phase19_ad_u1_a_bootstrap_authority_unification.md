# Phase19-AD-U1-A Bootstrap and Authority Unification

## Final Judgment

`PHASE19_AD_U1_A_BOOTSTRAP_AUTHORITY_FOUNDATION_PASS`

Supporting:

- `BUY_FAIL_CLOSED_WITHOUT_ACCEPTED_GENERATION`
- `RUNTIME_LIFECYCLE_AUTHORITY_FOUNDATION_UNIFIED`
- `SELL_CONTINUITY_BOUNDARY_PASS`
- `TRADING_STATE_NON_MUTATION_PASS`
- `NO_LEGACY_RUNTIME_FALLBACK_PASS`

This is not `AD_U1_COMPLETE`, `BUY_READY`, `PRODUCTION_READY`, `PHASE19_COMPLETE`, or `AUTONOMOUS_OPERATION_COMPLETE`.

## Sources Read

Primary SoT:

- `docs/02_architecture/autonomous_ai_operations_architecture.md`
- `docs/02_architecture/runtime_architecture_v2.md`
- `docs/01_requirements/phase_roadmap.md`

Phase18 handoff and reports:

- `docs/phase_reports/phase18_final_summary_and_phase19_handoff.md`
- `docs/phase_reports/phase18_to_phase19_chatgpt_handoff.md`
- `docs/phase_reports/phase18_ab_runtime_legacy_model_provenance_and_ai_generation_pipeline_audit.md`
- `docs/phase_reports/phase18_ac_autonomous_ai_operations_architecture_design.md`
- `docs/phase_reports/phase18_ad_autonomous_ai_operations_architecture_closure_review.md`
- `docs/phase_reports/phase18_ae_autonomous_ai_operations_architecture_final_system_review.md`
- `docs/phase_reports/phase18_af_autonomous_ai_operations_architecture_final_consistency_amendment.md`
- `docs/phase_reports/phase18_w_historical_runtime_scoped_block_and_accepted_bundle_authority.md`

Runtime test contracts:

- `docs/02_architecture/runtime_test_specification.md`
- `docs/02_architecture/runtime_test_specification.json`
- `docs/02_architecture/historical_runtime_test_contract.md`
- `docs/03_operations/runtime_test_command_guide.md`

Evidence JSON under:

- `reports/phase18_ad_autonomous_ai_operations_architecture_closure_review/`
- `reports/phase18_ae_architecture_final_system_review/`
- `reports/phase18_af_autonomous_ai_operations_architecture_final_consistency_amendment/`

## Current Authority Findings

Runtime BUY inference previously resolved:

```text
produce_buy_ai_decisions
-> resolve_buy_ai_artifact_paths
-> CANDIDATE_AI_SET / OPPORTUNITY_AI_SET
-> legacy accepted component model paths
```

Lifecycle Gate resolved:

```text
build_runtime_lifecycle_evidence
-> runtime_state/accepted_buy_ai_bundle.json
-> evaluate_runtime_ai_gate
```

This proved the current two-authority mismatch:

```text
Runtime inference authority = Registry accepted component sets
Lifecycle Gate authority = Accepted Atomic BUY AI Bundle evidence
```

Evidence:

- `reports/phase19_ad_u1_a_bootstrap_authority_unification/current_authority_inventory.json`
- `reports/phase19_ad_u1_a_bootstrap_authority_unification/current_buy_inference_call_graph.json`
- `reports/phase19_ad_u1_a_bootstrap_authority_unification/current_lifecycle_gate_call_graph.json`

## Implemented Foundation

Added `src/ai_fund_lab_v2/runtime_v2/accepted_generation_resolver.py`.

The resolver reads only:

```text
<runtime_root>/runtime_state/accepted_buy_ai_bundle.json
```

and accepts only:

```text
transaction_state = COMMITTED
```

It rejects missing pointers, malformed pointers, non-`COMMITTED` pointers, missing manifests, promotion candidate refs, aggregate hash mismatch, missing Candidate member, missing Opportunity member, member file absence, and member hash mismatch.

`src/ai_fund_lab_v2/runtime_v2/buy_ai/producer.py` now resolves accepted generation authority before normal model resolution for non-isolated Runtime paths. If no accepted generation exists, BUY produces no signals and does not call the legacy component resolver.

`src/ai_fund_lab_v2/runtime_v2/lifecycle_evidence.py` now accepts the same `AcceptedGenerationResolution`, so BUY inference and Lifecycle Gate can share one resolution artifact.

Evidence:

- `reports/phase19_ad_u1_a_bootstrap_authority_unification/resolver_contract.json`
- `reports/phase19_ad_u1_a_bootstrap_authority_unification/bootstrap_behavior_matrix.json`

## BUY Bootstrap Behavior

When no Accepted Generation exists:

- resolution status: `NO_ACCEPTED_GENERATION`
- reason: `NO_ACCEPTED_GENERATION_BOOTSTRAP`
- BUY planning: scoped blocked / review required
- BUY submit: blocked
- BUY broker write: prohibited
- legacy component fallback: not used
- Promotion Candidate fallback: not used

Evidence:

- `reports/phase19_ad_u1_a_bootstrap_authority_unification/bootstrap_behavior_matrix.json`
- `reports/phase19_ad_u1_a_bootstrap_authority_unification/failure_injection_results.json`

## SELL Continuity

The existing SELL continuity evaluator is retained. BUY AI generation failure alone does not set `block_sell=true`. SELL planning remains a separate Runtime job that evaluates its own Current, Pending, Ledger, PM, Safety, Broker, Submit, and Execution dependencies.

Evidence:

- `reports/phase19_ad_u1_a_bootstrap_authority_unification/current_sell_continuity_call_graph.json`
- `reports/phase19_ad_u1_a_bootstrap_authority_unification/buy_sell_failure_matrix.json`

## Historical Contract

The new resolver does not select by `latest`, mtime, or max `accepted_at`. It fixes the current Runtime contract to a committed accepted generation pointer, which is compatible with future Historical as-of filtering. Historical as-of accepted generation selection itself remains later AD-U1 / AD-U5 work.

## Non-Mutation

Focused non-mutation evidence covered:

- `persistent_ledger/state.json`
- `pending_order_plan/pending_order_plan.json`
- `runtime_state/current_state.json`

Before and after contents were identical when no accepted generation was present.

Evidence:

- `reports/phase19_ad_u1_a_bootstrap_authority_unification/non_mutation_evidence.json`

## Failure Injection

Covered or implemented:

- pointer missing
- pointer malformed
- non-`COMMITTED` pointer
- manifest missing
- aggregate hash mismatch
- Candidate member missing
- Opportunity member missing via same branch
- legacy accepted component resolver not reached
- Promotion Candidate pointer rejected
- SELL not blocked solely by BUY generation failure
- partial read / resolver failure fail-closed

Evidence:

- `reports/phase19_ad_u1_a_bootstrap_authority_unification/failure_injection_results.json`

## Regression

Passing:

```text
tests/runtime_v2/test_phase19_ad_u1_a_accepted_generation_resolver.py
tests/ai_lifecycle/test_phase18s_accepted_runtime_evidence_authority.py
tests/ai_lifecycle/test_phase18p_runtime_lifecycle_evidence_authority.py
tests/ai_lifecycle/test_phase18t_buy_only_and_restore_failure.py
tests/runtime_v2/test_phase18w_historical_scoped_block.py
tests/runtime_v2/test_phase16av_registry_consumer_cutover.py
```

`py_compile` passed for changed runtime modules.

Stale tests classified:

```text
tests/runtime_v2/test_phase15ag_candidate_opportunity_runtime_connection.py
tests/runtime_v2/test_phase15ao_candidate_opportunity_controlled_schema_validation.py
```

Classification: `TEST_CONTRACT_STALE`.

Reason: these Phase15 tests expect explicit isolated model paths to produce BUY PASS without accepted generation authority. AD-U1-A now requires accepted generation for normal Runtime authority and blocks before legacy model authority. No fallback was added to satisfy those stale expectations.

Evidence:

- `reports/phase19_ad_u1_a_bootstrap_authority_unification/test_results.json`

## Changed Files

Implementation:

- `src/ai_fund_lab_v2/runtime_v2/accepted_generation_resolver.py`
- `src/ai_fund_lab_v2/runtime_v2/lifecycle_evidence.py`
- `src/ai_fund_lab_v2/runtime_v2/buy_ai/producer.py`
- `tests/runtime_v2/test_phase19_ad_u1_a_accepted_generation_resolver.py`

Report / evidence:

- `docs/phase_reports/phase19_ad_u1_a_bootstrap_authority_unification.md`
- `reports/phase19_ad_u1_a_bootstrap_authority_unification/`
- `reports/phase_reports/phase19_ad_u1_a_bootstrap_authority_unification.json`

## Remaining AD-U1 Work

- Bootstrap Generation path
- Human Review workflow materialization
- formal COMMITTED pointer writer / transaction integration
- legacy resolver cutover and deletion conditions
- Historical accepted generation as-of resolver completion
- broader production-equivalent smoke after bootstrap generation exists

## AD-U2 Readiness

`NOT_READY`

AD-U2 must not start yet. AD-U1 still has remaining bootstrap and authority materialization work.
