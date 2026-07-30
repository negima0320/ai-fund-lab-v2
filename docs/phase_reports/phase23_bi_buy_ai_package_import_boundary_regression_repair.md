# Phase23-BI Buy AI Package Import Boundary Regression Repair

## Primary Judgment

```text
PHASE23_BI_BUY_AI_IMPORT_BOUNDARY_SHORT_VALIDATION_PASS
```

## Secondary Judgment

```text
PRODUCTION_ENTRYPOINT_IMPORT_RESTORED
SRC_TO_SCRIPTS_DEPENDENCY_REMOVED
BUY_AI_EAGER_IMPORT_SIDE_EFFECT_REMOVED
BH_NO_BUY_CONTRACT_PRESERVED
RUNTIME_TEST_ENTRYPOINT_IMPORT_PASS
READY_FOR_1BD_RUNTIME_RERUN
```

## Root Cause

This was not a Runtime HALT.

```text
Runtime Test run creation = NOT REACHED
run_id = NOT CREATED
backup = NOT CREATED
Runtime state mutation = NOT STARTED
```

Observed failure:

```text
ModuleNotFoundError: No module named 'scripts'
```

Confirmed import chain:

```text
scripts/runtime_test.py
-> strategy.shadow_runtime
-> strategy.portfolio_construction
-> runtime_v2.buy_ai.opportunity_eligibility
-> runtime_v2.buy_ai.__init__
-> runtime_v2.buy_ai.producer
-> scripts.run_phase4bg_formal_candidate_inference
-> ModuleNotFoundError
```

Additional producer import boundary found during validation:

```text
runtime_v2.buy_ai.producer
-> runtime_v2.buy_ai.generation_bound_inference
-> ai_lifecycle.__init__
-> dataset_rebuild
-> adapters
-> scripts.build_phase4bc_long_history_features
```

Both were package import boundary issues.

## 修正内容

`buy_ai.__init__` was changed from eager producer import to lazy public export.

```text
from ai_fund_lab_v2.runtime_v2.buy_ai.opportunity_eligibility import ...
```

now loads only the package initializer and the requested utility module. It does not load `buy_ai.producer` and does not require repository-level `scripts`.

Candidate formal inference helper logic used by production `buy_ai.producer` was moved into a canonical `src` module:

```text
src/ai_fund_lab_v2/candidate_ai/formal_inference.py
```

`buy_ai.producer` now imports:

```text
ai_fund_lab_v2.candidate_ai.formal_inference
```

instead of:

```text
scripts.run_phase4bg_formal_candidate_inference
```

The Phase4BG script remains compatible and now uses the `src` canonical helpers.

`ai_lifecycle.__init__` was also made lazy so Runtime inference can import `ai_lifecycle.training_pipeline` without accidentally loading dataset rebuild adapters that depend on repository scripts.

## Import Contract

Confirmed:

```text
PYTHONPATH=src portfolio_construction import: PASS
PYTHONPATH=src opportunity_eligibility import: PASS
buy_ai.producer not loaded by opportunity_eligibility import: PASS
scripts.run_phase4bg_formal_candidate_inference not loaded: PASS
PYTHONPATH=src buy_ai producer lazy export import: PASS
PYTHONPATH=src scripts/runtime_test.py --help: PASS
```

Target-scope dependency audit:

```text
src_to_scripts_dependency_count = 0
```

## BH Contract Preservation

Unchanged:

```text
opportunity_no_buy_reason is hard BUY exclusion
Portfolio Construction EXCLUDE / target_weight = 0
Runtime Planning NO_ORDER / planned_quantity = 0
Submit Guard fail-closed defense preserved
no forced BUY
no forced replacement
```

## Modified Files

```text
src/ai_fund_lab_v2/runtime_v2/buy_ai/__init__.py
src/ai_fund_lab_v2/runtime_v2/buy_ai/producer.py
src/ai_fund_lab_v2/ai_lifecycle/__init__.py
src/ai_fund_lab_v2/candidate_ai/formal_inference.py
scripts/run_phase4bg_formal_candidate_inference.py
tests/runtime_v2/test_phase23_bi_buy_ai_import_boundary.py
```

## Short Validation

```text
py_compile import boundary files: PASS
BI import boundary tests: 6 passed
Phase4BG formal candidate script compatibility: 5 passed
Buy AI producer targeted subset: 8 passed, 2 deselected
Portfolio Construction + Runtime Planning expanded BH regression: 39 passed
Opportunity / Strategy Planning regression slice: 11 passed, 8 deselected
Submit policy / opportunity guard regression slice: 6 passed, 4 deselected
runtime_test.py --help under PYTHONPATH=src: PASS
git diff --check scoped files: PASS
```

Observed but classified out of BI scope:

```text
tests/runtime_v2/test_phase15ag_candidate_opportunity_runtime_connection.py
  full file: 8 passed, 2 failed
```

The two failures occur after import succeeds, with Morning PM schema review preventing legacy order_plan/report expectations. They are not `ModuleNotFoundError`, not `src -> scripts`, and not the BI entrypoint import blocker.

Not executed:

```text
fresh-run
1BD
10BD
20BD
Broker Write
Runtime Switch
J-Quants fetch
```

## Evidence

Human:

```text
docs/phase_reports/phase23_bi_buy_ai_package_import_boundary_regression_repair.md
```

Machine:

```text
reports/phase_reports/phase23_bi_buy_ai_package_import_boundary_regression_repair.json
```

Evidence directory:

```text
reports/phase23_bi_buy_ai_package_import_boundary_regression_repair/
```

Required evidence files:

```text
root_cause.json
before_after_import_graph.json
buy_ai_initializer_audit.json
producer_dependency_trace.json
src_to_scripts_dependency_audit.json
entrypoint_import_reproduction.json
bh_contract_regression.json
targeted_test_results.json
existing_run_hash_preservation.json
modified_files.json
```

## Existing Run Preservation

Read-only tree hashes were recorded for:

```text
runtime-test-historical-smoke-20260730T063001897459Z
runtime-test-historical-smoke-20260730T054102824494Z
runtime-test-historical-smoke-20260730T050344341520Z
```

No preserved run directory was modified.

## Remaining Gaps

No BI import boundary blocker remains under short validation.

The two full-file `test_phase15ag_candidate_opportunity_runtime_connection.py` failures are retained as out-of-scope Morning PM/schema review behavior, not an import-boundary failure.

## Next Operator Action

```text
READY_FOR_1BD_RUNTIME_RERUN = YES
```

Operator may rerun the formal 1BD command after Evidence Review.
