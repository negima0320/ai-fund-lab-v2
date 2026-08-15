# Phase29-L21T-AM - Runtime Opportunity Semantic Metadata Propagation Repair

## Task ID

`Phase29-L21T-AM`

## Primary Judgment

`PHASE29_L21T_AM_RUNTIME_OPPORTUNITY_SEMANTIC_METADATA_PROPAGATION_REPAIRED_ACTUAL_ADAPTER_REGRESSION_PASS`

## Current Phase

`Phase29`

Phase30 was not entered.

## AL Judgment Inherited

`PHASE29_L21T_AL_POST_AK_SEMANTIC_METADATA_PROPAGATION_GAP_CONFIRMED_IMPLEMENTATION_READY`

## Root Cause

Opportunity source artifacts already contained the canonical score semantic
metadata:

```text
canonical_score_field = runtime_opportunity_score
score_semantic_role = uncalibrated_relative_model_score
calibration_applied = false
economic_units_available = false
```

AL showed that the Production-common Strategy adapter path did not preserve
that metadata into the Portfolio Construction source summary. PC core was
already reachable after AK, but it correctly failed closed when
`canonical_score_field` was missing at the consumer-visible contract.

AM repaired the adapter boundary. It did not change Strategy score meaning,
model, thresholds, ranking, exposure, BUY count, Safety caps, or Historical
behavior.

## Changed Files

Code:

```text
src/ai_fund_lab_v2/strategy/shadow_runtime.py
```

Tests:

```text
tests/strategy/test_phase22_e_portfolio_construction.py
```

Common SoT:

```text
docs/02_architecture/portfolio_construction_and_position_sizing_contract.md
```

Phase30 entry register:

```text
docs/phase_reports/phase30_a_entry_gate_100bd_baseline_status.md
```

Report / summary:

```text
docs/phase_reports/phase29_l21t_am_runtime_opportunity_semantic_metadata_propagation_repair.md
reports/phase29_l21t_am_runtime_opportunity_semantic_metadata_propagation_repair/summary.json
```

## Authority Before / After

Before AM:

```text
Opportunity artifact top-level semantic metadata: COMPLETE
shadow_runtime adapter / PC source summary: INCOMPLETE
Portfolio Construction classifier: semantic_metadata_missing
non_positive_expected_edge_score: hard fail-closed block
```

After AM:

```text
Opportunity artifact top-level semantic metadata: COMPLETE
shadow_runtime adapter / PC source summary: COMPLETE
Portfolio Construction classifier: semantic_metadata_complete=true
non_positive_expected_edge_score: soft relative reason under uncalibrated semantics
```

If metadata is truly missing or malformed at the source, the adapter does not
fabricate it and PC remains fail-closed.

## Source / Adapter / Consumer Separation

Source Authority:

```text
Opportunity artifact
```

Responsibility: define the score semantic contract.

Adapter:

```text
shadow_runtime._ai_output_summary
shadow_runtime._pc_summary
shadow_runtime._summary_kwargs
```

Responsibility: preserve source-present metadata into the Portfolio Construction
source summary without inference or reinterpretation.

Consumer:

```text
Portfolio Construction
```

Responsibility: apply the AK semantic classifier. PC core was not repaired again
because AL proved it was reachable and the defect was input-adapter equivalence.

## Actual-Adapter Evidence

Focused regression passes the required path:

```text
Opportunity payload
-> shadow_runtime._ai_output_summary(...)
-> shadow_runtime._pc_summary(...)
-> PortfolioConstructionSourceSummary
-> Portfolio Construction semantic classifier
```

Input Opportunity top-level:

```text
canonical_score_field = runtime_opportunity_score
score_semantic_role = uncalibrated_relative_model_score
calibration_applied = false
economic_units_available = false
```

PC source summary after adapter:

```text
canonical_score_field = runtime_opportunity_score
score_semantic_role = uncalibrated_relative_model_score
calibration_applied = false
economic_units_available = false
```

PC classifier:

```text
semantic_metadata_complete = true
hard_blocking_reasons = []
soft_relative_reasons = ["non_positive_expected_edge_score"]
```

This proves `non_positive_expected_edge_score` is not a standalone hard BUY
block under complete uncalibrated relative metadata.

## Counterexamples

Missing metadata:

```text
source canonical_score_field = MISSING
adapter fabricates metadata = NO
PC semantic_metadata_complete = false
review_reason = semantic_metadata_missing
BUY block = YES
```

Malformed metadata:

```text
score_semantic_role = unknown_score_semantic_role
PC review_reason = unsupported_score_semantic_contract
BUY block = YES
```

Hard reason:

```text
high_downside_risk_score|non_positive_expected_edge_score
hard_blocking_reasons = ["high_downside_risk_score"]
soft_relative_reasons = ["non_positive_expected_edge_score"]
BUY block = YES
```

Future calibrated economic:

```text
calibration_applied = true
economic_units_available = true
non_positive_expected_edge_score
BUY block = YES
```

Positive control:

```text
94320 equivalent
classification = PASS
membership_intent = ADD_CANDIDATE
positive allocation path preserved = YES
```

## Required Field Answers

| Field | Answer |
| --- | --- |
| actual runtime adapter repaired | `YES` |
| source semantic authority preserved | `YES` |
| canonical_score_field propagated | `YES` |
| score_semantic_role propagated | `YES` |
| calibration_applied propagated | `YES` |
| economic_units_available propagated | `YES` |
| adapter infers semantic metadata | `NO` |
| semantic metadata truly missing remains fail-closed | `YES` |
| semantic metadata malformed remains fail-closed | `YES` |
| non_positive_expected_edge_score standalone hard block under uncalibrated semantics | `NO` |
| below_opportunity_top20 standalone hard block under uncalibrated semantics | `NO` |
| high_downside_risk_score hard block preserved | `YES` |
| future calibrated economic negative hard gate preserved | `YES` |
| Buy Quality REJECT preserved | `YES` |
| AK PC authority preserved | `YES` |
| AK Runtime Planning authority preserved | `YES` |
| Strategy Decision Trace remains observability-only | `YES` |
| actual-adapter regression added | `YES` |
| Strategy cap preserved | `YES` |
| Safety hard cap preserved | `YES` |
| BUY count forced | `NO` |
| Exposure forced | `NO` |
| negative score auto-BUY introduced | `NO` |
| Config changed | `NO` |
| Model changed | `NO` |
| Threshold changed | `NO` |
| Retraining performed | `NO` |
| Future return used by Runtime | `NO` |
| Historical-only branch added | `NO` |
| Target run mutated by Codex | `NO` |
| Long Historical executed by Codex | `NO` |
| Common SoT updated | `YES` |
| Phase30 entry register updated | `YES` |
| fresh validation required | `YES` |
| Phase30 entered | `NO` |
| Phase30 blocker status | `BLOCKED_PENDING_POST_AM_FRESH_EARLY_GATE_VALIDATION` |

## Regression Results

| Area | Result |
| --- | --- |
| actual-adapter focused regression | `PASS - 8 passed` |
| Portfolio Construction regression | `PASS - 99 passed` |
| Position Sizing regression | `PASS - included in 140 passed` |
| Runtime Planning regression | `PASS - included in 140 passed` |
| Opportunity eligibility regression | `PASS - included in 27 passed` |
| Buy Quality regression | `PASS - included in 27 passed` |
| Shadow Runtime relevant regression | `PASS - 17 passed` |
| ADD regression | `PASS - included in 36 passed` |
| SELL / REDUCE / EXIT regression | `PASS - included in 36 passed` |
| REENTRY regression | `PASS - included in 26 passed` |
| Lot / Safety regression | `PASS - included in 26 passed` |
| Planning Submit feasibility regression | `PASS - 34 passed` |
| Runtime runner relevant regression | `PASS - included in 74 passed` |
| py_compile | `PASS` |
| summary JSON parse | see final checks |
| git diff --check | see final checks |

Commands executed:

```text
PYTHONPATH=src python3 -m pytest -q tests/strategy/test_phase22_e_portfolio_construction.py -k 'phase29_l21t_am'
PYTHONPATH=src python3 -m pytest -q tests/strategy/test_phase22_e_portfolio_construction.py
PYTHONPATH=src python3 -m pytest -q tests/strategy/test_phase22_g_runtime_planning.py tests/strategy/test_phase22_j_position_sizing.py
PYTHONPATH=src python3 -m pytest -q tests/runtime_v2/test_phase17_bv15_opportunity_buy_eligibility_contract.py tests/strategy/test_phase26_h_adaptive_buy_quality.py
PYTHONPATH=src python3 -m pytest -q tests/runtime_v2/test_phase22_p_strategy_shadow_wiring.py
PYTHONPATH=src python3 -m pytest -q tests/runtime_v2/test_phase21_b_pending_composition_add_consumer.py tests/runtime_v2/test_phase19_bt_reduce_quantity_contract.py
PYTHONPATH=src python3 -m pytest -q tests/strategy/test_phase29_l21k_prior_exit_materialization.py tests/runtime_v2/test_phase26_step4_position_sizing_authority.py
PYTHONPATH=src python3 -m pytest -q tests/runtime_v2/test_phase23_i_strategy_planning_authority.py tests/runtime_v2/test_phase24_ht_planning_submit_feasibility.py
PYTHONPATH=src python3 -m pytest -q tests/runtime_v2/test_phase17_g_historical_submit_guard_and_fill.py tests/runtime_v2/test_phase17_bg_empty_no_action_execution_contract.py tests/runtime_v2/test_phase17_k_runtime_test_runner.py
PYTHONPYCACHEPREFIX=/private/tmp/ai-fund-lab-v2-pycache-am python3 -m py_compile src/ai_fund_lab_v2/strategy/shadow_runtime.py tests/strategy/test_phase22_e_portfolio_construction.py
```

## Fresh Validation Requirement

`YES`

The pre-AM run remains pre-AM evidence only:

```text
runtime-test-historical-extended-smoke-20260814T041426689731Z
```

Codex did not resume, replay, recover, fresh-run, long-run, or mutate it.

First post-AM user-operated fresh validation should stop at the `2022-08-10`
early gate and confirm:

1. Opportunity source artifact has the four semantic fields.
2. PC upstream Opportunity summary has the same four fields.
3. `23700`, `36640`, `66590`, and `93180` are not
   `semantic_metadata_missing`.
4. `non_positive_expected_edge_score` alone is not a hard block.
5. `below_opportunity_top20|non_positive_expected_edge_score` alone is not a
   hard block.
6. `high_downside_risk_score` and other hard authorities still block.
7. Membership intent is decided by relative competition and downstream
   feasibility, not by stale absolute score sign.

## Recommended Next Task

`Phase29-L21T-AN - Post-AM Fresh Validation Early Gate Readiness / Operator Command Evidence`

## Final Questions

Opportunity source artifactに存在する4つのcanonical score semantic metadata
は、AM後、actual Production-common runtime adapterを経由してPortfolio
Constructionへ欠落なく伝播するか？

```text
YES
```

Evidence: actual-adapter focused regression passes
`Opportunity payload -> shadow_runtime adapter -> PC source summary -> PC
classifier`, and the PC source summary contains all four fields.

semantic metadataがcompleteなuncalibrated relative candidateについて、
`non_positive_expected_edge_score` は単独hard BUY blockではなくなったか？

```text
YES
```

Evidence: focused regression shows `semantic_metadata_complete=true`,
`hard_blocking_reasons=[]`, and
`soft_relative_reasons=["non_positive_expected_edge_score"]`.

semantic metadataが本当にmissing / malformedな場合のfail-closed、および
high downside / Safety / Lot / Corporate Action / Broker / Re-entry等のhard
authorityは維持されているか？

```text
YES
```

Evidence: missing metadata, malformed metadata, high downside, calibrated
economic negative, Buy Quality, ADD, SELL / REDUCE / EXIT, REENTRY, Lot /
Safety, Planning Submit feasibility, and Runtime runner regressions passed.
