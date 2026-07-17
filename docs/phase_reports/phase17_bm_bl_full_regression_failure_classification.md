# Phase17-BM BL Full Regression Failure Classification

## Executive Summary

Final judgment:

```text
PHASE17_BM_REGRESSION_FIX_REQUIRED
```

Phase17-BM re-ran the full Runtime v2 test suite after Phase17-BL and classified all 69 failures by test node id.

No genuine Phase17-BL Runtime logic regression was confirmed. The BL-specific and adjacent Data Readiness / Runner tests still pass. The PM Registry hash mismatch is an expected fail-closed result after `position_management/producer.py` changed.

However, Registry refresh is not yet eligible because non-Registry failures remain: old fixtures that do not materialize the normal Feature Date Contract, old Phase13/14/15 expectations, and shared acceptance fixture drift. Those must be fixed or formally retired before the Registry acceptance refresh gate can be cleanly passed.

## Full Failure Inventory

Command:

```bash
python3 -m pytest tests/runtime_v2 --tb=short -ra --maxfail=0 --junitxml=reports/phase17_bm_bl_full_regression_failure_classification/runtime_v2_pytest.xml
```

Result:

```text
69 failed
800 passed
869 total
```

Detailed inventory:

```text
reports/phase17_bm_bl_full_regression_failure_classification/failure_inventory.json
```

Classification totals:

| Classification | Count | Summary |
|---|---:|---|
| A. Registry identity expected failure | 5 | PM producer source hash differs from accepted `POSITION_MANAGEMENT_POLICY_SET:RUNTIME_ADAPTER`; fail-closed is correct. |
| B. Obsolete test expectation | 42 | Old fixtures still treat CLI/profile Feature Date or minimal readiness fixtures as enough; BL/current contracts require materialized authority/evidence. |
| C. Genuine regression | 0 | No confirmed BL Runtime logic regression. |
| D/E. Isolation or pre-existing drift | 22 | Static Phase13 guards, legacy submit preflight API drift, shared `.runtime_acceptance_*` hash/state drift, older scheduler expectations. |
| F. Ambiguous | 0 | All failures were assigned to a concrete group. |

## Key Failure Groups

### A. Registry Identity Expected Failure

Direct Registry resolver failures:

- `tests/runtime_v2/test_phase16av_registry_consumer_cutover.py::test_pm_policy_registry_members_match_legacy_and_current_adapter`
- `tests/runtime_v2/test_phase17_b1i_b_pm_adapter_authority.py::test_registry_resolver_returns_current_pm_source_authority`

PM producer / acceptance cascade:

- `tests/runtime_v2/test_phase15af_position_management_runtime_connection.py::test_phase15af_pm_artifact_generation_and_sell_planning_reads_it`
- `tests/runtime_v2/test_phase15af_position_management_runtime_connection.py::test_phase15af_current_liquidation_and_pm_decision_are_not_mixed`
- `tests/runtime_v2/test_phase15by2_authority_cleanup.py::test_phase15by2_closes_buy_origin_authority_without_semantic_mutation`

Root cause:

```text
accepted RUNTIME_ADAPTER hash = d08d854266f6822f322a7947fd7deb20a2906d2a56806d030e2618114bdcaa4b
current producer.py hash     = 4f1c0f7e7409cba1a65238d5c88736624071c7911b8b55ea74974bb7e8e763c7
```

This is correct fail-closed behavior. It must not be bypassed with mocks or direct JSON edits.

### B. BL Feature Date Contract Fixture Drift

29 failures are directly tied to the BL contract change:

- Runtime Test plan gate now requires `source=normal_feature_date_contract`, `contract_materialized=true`, and an existing materialized contract.
- Data Readiness now treats explicit CLI `--feature-date` as a value that must match the materialized contract, not as authority.
- Missing normal contract now returns `REVIEW_REQUIRED` with `feature_date_contract_missing`.

Affected tests are listed under:

- `bl_normal_feature_date_contract_required_fixture_missing_or_stage_absent`
- `bl_runtime_test_plan_gate_expectation_changed`

Required action:

```text
Update fixtures to write .runtime/operations/feature_date_contract/{business_date}.json and corresponding consumer readiness evidence, or update tests to expect PRECONDITION_FAILURE where missing contract is intentionally under test.
```

### B. Other Obsolete Runtime Contract Expectations

13 failures are obsolete but not directly BL-specific:

- Feature generation / consumer readiness expectations now fail closed under current schema contracts.
- PM/Sell Planning fixtures expect producer stage execution without current market/broker/PM readiness evidence.

Required action:

```text
Update isolated fixtures to satisfy current Data Readiness and PM consumer contracts. Do not loosen fail-closed checks.
```

### D/E. Pre-existing or Isolation Drift

22 failures are unrelated to BL:

- Phase13 static guard tests flag later accepted source strings/imports.
- Phase14 broker rehearsal helpers call a legacy `run_submit_preflight(max_order_amount=...)` API.
- Shared `.runtime_acceptance_phase15_demo_reinit` state/hash assertions no longer match the current workspace.
- Older scheduler/promotion/capital-policy tests assert prior reason/state vocabulary.

These are not evidence that BL broke Runtime Feature Date or PM Opportunity authority, but they still block a clean full-suite gate.

## BL Diff Impact Assessment

### Runtime Test Runner

Impact:

- `resolve_feature_date()` now reads the materialized normal Feature Date Contract for each `business_date`.
- Profile `accepted_feature_dates` is assertion-only.
- Plan entry fails closed when the materialized contract is missing or mismatched.

Production/Demo/Historical impact:

- Runtime Test Runner only affects Runtime Test orchestration, but the authority rule matches the shared Runtime Feature Date contract.

### Data Readiness

Impact:

- `explicit_feature_date` no longer becomes authority when a normal contract is missing.
- CLI/contract mismatch becomes `REVIEW_REQUIRED`.
- PM Opportunity default path resolves by runtime `business_date`.

Production/Demo/Historical impact:

- Common fail-closed contract. No historical-only bypass was added.

### Position Management Producer

Impact:

- Default BUY Opportunity path is `.runtime/runtime_state/buy_ai/{business_date}/opportunity_rankings.json`.
- Opportunity artifact `business_date` is checked against runtime `business_date`.
- Opportunity artifact `feature_date` and ranking row `target_date` are checked against selected Feature Date.

Production/Demo/Historical impact:

- Common contract. It fixes the business-date / feature-date semantic split without relaxing PM fail-closed behavior.

## Registry Contract Audit

Source of truth:

```text
.runtime/artifact_registry/events/registry_events.jsonl
.runtime/artifact_registry/index/registry_index.json
.runtime/artifact_registry/checkpoints/latest.json
```

Runtime resolver:

```text
src/ai_fund_lab_v2/runtime_v2/artifact_lookup.py
```

Runtime PM adapter identity check:

```text
src/ai_fund_lab_v2/runtime_v2/position_management/producer.py
verify_position_management_runtime_adapter_authority()
```

Hash material:

```text
sha256 over repo-relative source file bytes:
src/ai_fund_lab_v2/runtime_v2/position_management/producer.py
```

Formal workflow candidate:

```text
scripts/phase17_b1i_b_pm_adapter_authority_resolution.py
```

Audit finding:

- The script implements append-only DRAFT / VALIDATED / ACCEPTED event flow, index validation, checkpoint validation, protected state hash checks, resolver check, and fail-closed test.
- It does not expose a dry-run flag.
- BM did not execute it because it mutates Registry state.
- Direct `.runtime` JSON editing is forbidden and was not performed.

Registry refresh eligibility:

```text
NOT_ELIGIBLE in Phase17-BM
```

Reason:

```text
Registry mismatch is expected and formally refreshable in principle, but non-Registry full-suite failures remain. The eligibility gate requires Registry mismatch to be the only remaining failure before refresh.
```

## Revalidation

BL-specific:

```text
python3 -m pytest -q tests/runtime_v2/test_phase17_bl_feature_date_authority_unification.py
4 passed
```

Data Readiness:

```text
python3 -m pytest -q tests/runtime_v2/test_phase15aq_runtime_data_readiness_gate.py
10 passed
```

PM / Registry related:

```text
python3 -m pytest -q tests/runtime_v2/test_phase15ap_position_management_input_contract.py tests/runtime_v2/test_phase17_ah_pm_adapter_registry_identity_guard.py tests/runtime_v2/test_phase17_b1i_b_pm_adapter_authority.py tests/runtime_v2/test_phase16av_registry_consumer_cutover.py
31 passed, 2 failed
```

The 2 failures are the expected PM Registry hash mismatch.

Runtime Test Runner:

```text
python3 -m pytest -q tests/runtime_v2/test_phase17_k_runtime_test_runner.py tests/runtime_v2/test_phase17_l_historical_asof_and_evidence_isolation.py tests/runtime_v2/test_phase17_bl_feature_date_authority_unification.py
23 passed
```

## Historical Smoke Resume Assessment

Target:

```text
runtime-test-historical-smoke-20260715T111433056797Z
```

Observed source identity:

```text
run source commit = 31aad0d859e58503dbfe7ebc375836c2e7715941
current HEAD      = 31aad0d859e58503dbfe7ebc375836c2e7715941
current tree      = dirty
```

Day4 evidence is BL-pre-fix split evidence:

```text
Data Readiness selected_feature_date = 2026-07-09
Morning planning selected_feature_date = 2026-07-08
```

Assessment:

- Do not resume at Day4 Sell Planning.
- Do not re-run only Sell Planning against Day4 Morning artifacts.
- Day4 Morning and Data Readiness were generated under the split contract, so a clean baseline new run is the safest path.
- After test/fixture blockers and Registry identity are resolved, use a new clean baseline run rather than editing Frozen Run evidence.

## Prohibited Operations Confirmation

Not executed:

- `scripts/runtime_test.py run`
- `scripts/runtime_test.py resume`
- `scripts/runtime_test.py reset`
- `scripts/runtime_test.py rollback`
- `scripts/runtime_test.py backup`
- `scripts/runtime_test.py close`
- Frozen Run edits
- `.runtime` manual edits
- Registry refresh / accepted hash update
- broker write
- order submit
- external notification delivery
- J-Quants fetch

## Required Next Boundary

Before Registry refresh:

1. Update obsolete BL-related fixtures to materialize normal Feature Date Contracts.
2. Resolve or formally retire pre-existing Phase13/14/15 failures.
3. Re-run full `tests/runtime_v2`.
4. Confirm only PM Registry identity mismatch remains.

Then Phase17-BN can perform formal PM Runtime Adapter Registry acceptance refresh through append-only workflow.

