# Phase19-AH — Dual-Gate Implementation and Runtime Separation

## Final Judgment

```text
PHASE19_AH_DUAL_GATE_IMPLEMENTATION_COMPLETE
PHASE19_AI_FORMAL_CORRECTIVE_REEVALUATION_CONTRACT_READY
```

Forbidden declarations were not made:

```text
FORMAL_VALIDATION_PASS
DUAL_GATE_FORMAL_PASS
UNIFIED_GENERATION_CREATED
ACCEPTED_GENERATION_CREATED
RUNTIME_READY
BUY_READY
PRODUCTION_READY
```

## Human Decision Materialization

Reviewer:

```text
user:negishi
```

Decision:

```text
APPROVE_DUAL_GATE_IMPLEMENTATION_WITH_RUNTIME_SEPARATION
```

Approved rule:

```text
Opportunity Generation Eligible
=
Global Quality Gate PASS
AND
Selection Utility Gate PASS
```

## Implemented Components

Implemented:

```text
Opportunity Global Gate Evaluator
Opportunity Selection Utility Evaluator
Candidate-passed Universe Binding
Opportunity Dual-Gate Aggregator
Dual-Gate Artifact Writer
Runtime Separation Guard
Dual-Gate Artifact Schema
Fixture Smoke / Failure Injection Tests
```

Files:

```text
src/ai_fund_lab_v2/ai_lifecycle/opportunity_global_gate.py
src/ai_fund_lab_v2/ai_lifecycle/opportunity_selection_gate.py
src/ai_fund_lab_v2/ai_lifecycle/opportunity_dual_gate.py
src/ai_fund_lab_v2/ai_lifecycle/dual_gate_artifact_writer.py
src/ai_fund_lab_v2/ai_lifecycle/runtime_separation_guard.py
schemas/ai_lifecycle/opportunity_dual_gate_artifact.schema.json
tests/ai_lifecycle/test_phase19_ah_dual_gate.py
```

## Global Gate

Gate ID:

```text
OPPORTUNITY_GLOBAL_QUALITY_GATE_V1
```

Fixture coverage:

```text
Global PASS + valid threshold semantics = PASS
Explosion = FAIL
Missing approved threshold/status semantics = REVIEW_REQUIRED
Missing required metric = METRIC_UNAVAILABLE
```

No numeric threshold was invented by the evaluator. Threshold/status semantics must be supplied by an approved policy payload.

## Selection Utility Gate

Gate ID:

```text
OPPORTUNITY_SELECTION_UTILITY_GATE_V1
```

Implemented historical-compatible metric families:

```text
realized return
Top-minus-bottom
Hit Rate
Downside Rate
Rank Lift
NDCG
Spearman / ranking correlation
```

Fixture coverage:

```text
Top5 / Top10 / Top20 positive utility = PASS
Top5-only positive with Top10 / Top20 weak = FAIL
reversed ranking = FAIL
missing approved threshold/status semantics = REVIEW_REQUIRED
missing historical metric mapping = REVIEW_REQUIRED
```

## Candidate Population Binding

Implemented required binding:

```text
candidate_source_artifact_id
candidate_source_content_hash
candidate_score_field
candidate_pass_rule
candidate_population_size
candidate_selected_rows_hash
```

Fixture coverage:

```text
CandidateTop50 normal fixture = PASS
Candidate source hash mismatch = REVIEW_REQUIRED
Candidate population mismatch = REVIEW_REQUIRED
Candidate row binding mismatch = REVIEW_REQUIRED
CandidateTop50 definition mismatch = REVIEW_REQUIRED
```

The Selection Gate cannot silently treat all Opportunity rows as Candidate-passed.

## Dual-Gate Aggregator

Decision table implemented:

```text
Global PASS + Selection PASS = DUAL_GATE_PASS
Global FAIL + Selection PASS = DUAL_GATE_FAIL
Global PASS + Selection FAIL = DUAL_GATE_FAIL
Any REVIEW_REQUIRED = DUAL_GATE_REVIEW_REQUIRED
Any METRIC_UNAVAILABLE = DUAL_GATE_REVIEW_REQUIRED
```

Generation eligibility:

```text
DUAL_GATE_PASS = true
all other statuses = false
```

Candidate quality, backtest profit, paper profit, and runtime profit cannot offset either Opportunity gate.

## Dual-Gate Artifact / Hash Inventory

Schema:

```text
schemas/ai_lifecycle/opportunity_dual_gate_artifact.schema.json
```

Fixture schema validation:

```text
PASS
```

Hash inventory validation:

```text
PASS
```

Required hash entries:

```text
dual_gate_artifact_file_sha256
global_gate_payload_sha256
selection_gate_payload_sha256
candidate_source_artifact_sha256
formal_validation_artifact_sha256
dual_gate_contract_sha256
runtime_separation_contract_sha256
content_sha256
manifest_sha256
```

Dual-Gate Artifact flags:

```text
runtime_eligibility = false
accepted = false
```

## Runtime Separation Contract

Materialized:

```text
Dual Gate is Generation Acceptance authority only.
Dual Gate is not Runtime decision input.
```

Runtime SHALL NOT:

```text
run Global Quality Gate daily
run Selection Utility Gate daily
compare Global / Selection results
suppress BUY because of Gate disagreement
use Gate metrics for symbol-level trading decisions
change Generation eligibility
overwrite Accepted Generation with Gate results
```

Runtime allowed authorities remain:

```text
Accepted Generation pointer
Accepted Generation manifest
Candidate model / scaler / calibration
Opportunity model / scaler / calibration
approved Runtime policy
```

## Runtime Dependency Audit

Static audit target:

```text
src/ai_fund_lab_v2/runtime_v2
```

Result:

```text
PASS
findings = []
```

## Runtime Gate Access Failure Injection

PASS.

Required BLOCK cases:

```text
Runtime attempts to read Dual-Gate Evidence = BLOCK
Runtime attempts to execute Gate = BLOCK
Runtime suppresses BUY due Gate disagreement = BLOCK
```

Allowed control:

```text
Accepted Generation manifest access = PASS
Accepted generation unavailable suppression reason = PASS
```

## Fixture Smoke

PASS.

Covered:

```text
Global PASS + Selection PASS
Global FAIL + Selection PASS
Global PASS + Selection FAIL
Global REVIEW_REQUIRED + Selection PASS
Global PASS + Selection METRIC_UNAVAILABLE
CandidateTop50 normal fixture
Candidate binding mismatches
TopN positive / weak / reversed ranking
missing historical metric
missing approved threshold
Runtime prohibited access
```

## Regression

```text
PYTHONPATH=src PYTHONPYCACHEPREFIX=.pytest_cache/pycache python3 -m py_compile ...
PASS

PYTHONPATH=src python3 -m pytest tests/ai_lifecycle/test_phase19_ah_dual_gate.py
6 passed
```

## Formal Evaluation Status

Formal Validation rerun:

```text
0
```

Recent Holdout access:

```text
0
```

This phase did not perform formal corrective reevaluation.

## Non-mutation

PASS.

```text
Training = 0
Calibration refit = 0
Opportunity Model change = 0
Feature change = 0
Target change = 0
Policy threshold invention = 0
Unified Generation = 0
Accepted Generation = 0
Runtime pointer change = 0
BUY restart = 0
Broker write = 0
Ledger mutation = 0
```

## Evidence Paths

```text
docs/phase_reports/phase19_ah_dual_gate_implementation_and_runtime_separation.md
reports/phase_reports/phase19_ah_dual_gate_implementation_and_runtime_separation.json
reports/phase19_ah_dual_gate_implementation_and_runtime_separation/
```

Required evidence:

```text
implementation_summary.json
global_gate_fixture_results.json
selection_gate_fixture_results.json
dual_gate_aggregator_results.json
candidate_population_binding_validation.json
historical_metric_mapping_validation.json
runtime_separation_contract.json
runtime_dependency_static_audit.json
runtime_gate_access_failure_injection.json
runtime_buy_suppression_prohibition_test.json
dual_gate_artifact_schema_validation.json
dual_gate_hash_inventory_validation.json
failure_injection_results.json
regression_results.json
non_formal_execution_evidence.json
non_mutation_evidence.json
changed_files.json
remaining_risks.json
next_step_decision.json
final_judgment.json
```

## Remaining Risks

AH is fixture-only implementation. Formal corrective reevaluation still needs a separate AI contract and execution step.

Approved threshold/status semantics must be provided for formal use. Missing semantics correctly produce:

```text
REVIEW_REQUIRED
generation_eligibility = false
```

## Next Step

```text
PHASE19_AI_FORMAL_CORRECTIVE_REEVALUATION_CONTRACT_READY
```
