# Phase24-IA Rank Authority Metadata Runtime Evidence Audit and Observability Closure

## 1. Primary Judgment

`PHASE24_IA_RANK_AUTHORITY_METADATA_OBSERVABILITY_REPAIRED_SHORT_VALIDATION_PASS`

## 2. Runtime Run

```text
runtime-test-historical-extended-smoke-20260731T223424412826Z
```

Audit window:

```text
2022-07-01 to 2022-07-29
20 business days
```

Focused evidence review:

```text
2022-07-25
2022-07-26
```

## 3. Executive Summary

Rank value alignment was PASS. For 2022-07-25 and 2022-07-26, the focused symbols preserved:

```text
opportunity_buy_rank = input_opportunity_rank
rank_authority_status = PASS
```

The apparent `null` extraction for `canonical_opportunity_buy_rank` and `rank_authority_source` was partly an extraction-path issue: those are not the HY Contract artifact fields. The actual Portfolio Construction fields are:

```text
opportunity_buy_rank
input_opportunity_rank
input_opportunity_rank_authority
input_opportunity_rank_source_path
input_opportunity_rank_source_hash
input_opportunity_row_id
input_opportunity_row_authority_hash
opportunity_artifact_path
opportunity_artifact_hash
```

However, a real observability gap existed after Runtime Planning: `morning/planning_evidence.json` and `morning/pending_generation_evidence.json` did not expose the rank authority metadata even though Runtime Planning already had it.

## 4. Canonical Source Artifact

Canonical source:

```text
.runtime/runtime_state/buy_ai/<business_date>/opportunity_rankings.json
```

Canonical artifact field:

```text
buy_rank
```

Canonical semantic field:

```text
opportunity_buy_rank
```

Observed source paths:

| Business Date | Source Path | Source Hash |
|---|---|---|
| 2022-07-25 | `.runtime/runtime_state/buy_ai/2022-07-25/opportunity_rankings.json` | `babf02cbe9102552457b6ae8733ca8950af91371fa1c2516f3ea3f6c795a05e4` |
| 2022-07-26 | `.runtime/runtime_state/buy_ai/2022-07-26/opportunity_rankings.json` | `c0299c839a6ceb3dd8c06a115e23fa16af18f98a38b6621b00f6ec10323b55b9` |

## 5. Portfolio Construction Field Mapping

Portfolio Construction lineage status: `COMPLETE`.

For 66590:

| Business Date | opportunity_buy_rank | input_opportunity_rank | Authority | Source Path | Row ID / Hash |
|---|---:|---:|---|---|---|
| 2022-07-25 | 4 | 4 | `OPPORTUNITY_BUY_RANK_AUTHORITY` | present | present |
| 2022-07-26 | 4 | 4 | `OPPORTUNITY_BUY_RANK_AUTHORITY` | present | present |

The missing fields from the simple extraction were not contract fields:

```text
canonical_opportunity_buy_rank
rank_authority_source
```

## 6. Downstream Lineage

| Layer | Judgment | Notes |
|---|---|---|
| Portfolio Construction | COMPLETE | Rank value and authority metadata materialized |
| Position Sizing | COMPLETE | Rank authority fields propagated |
| Runtime Planning | COMPLETE | Rank authority fields propagated and `opportunity_authority` present |
| Planning Evidence | PARTIAL before repair | Lineage item omitted rank metadata |
| Pending Generation Evidence | MISSING before repair | Evidence summary omitted rank metadata |

## 7. Direct Root Cause

Runtime Planning already contained complete rank authority metadata, but the Planning Authority lineage serializer only emitted minimal fields:

```text
planning_id
security_code
planning_intent
order_side_intent
pending_item_generated
reason
position_sizing_used
```

`pending_generation_evidence.json` then emitted only pending path/status fields. This dropped observability metadata at the evidence layer, not in ranking, Portfolio Construction, Position Sizing, or Runtime Planning.

## 8. Observability Repair

Changed only evidence serialization:

- `src/ai_fund_lab_v2/runtime_v2/planning/strategy_authority.py`
- `src/ai_fund_lab_v2/runtime_v2/cli/run_daily_operation.py`

Added rank authority metadata to Planning Authority item lineage:

```text
opportunity_buy_rank
portfolio_input_opportunity_rank
position_sizing_opportunity_buy_rank
rank_authority_status
rank_authority
rank_authority_field
rank_authority_reason
opportunity_row_id
opportunity_row_authority_hash
opportunity_artifact_path
opportunity_artifact_hash
```

Added selected-item rank authority summary to `pending_generation_evidence.json` as:

```text
rank_authority_lineage
```

No decision logic, rank calculation, sizing calculation, lifecycle logic, or Submit Guard behavior was changed.

## 9. Regression

PASS:

```text
py_compile
tests/runtime_v2/test_phase23_i_strategy_planning_authority.py
tests/strategy/test_phase24_hy_rank_authority.py
tests/runtime_v2/test_phase24_ht_planning_submit_feasibility.py
tests/runtime_v2/test_phase17_x_historical_sell_planning_authority.py
tests/runtime_v2/test_phase24_h_cost_basis_authority.py
```

Aggregate:

```text
45 passed
```

Runtime fresh-run / resume was not executed.

## 10. Prohibited Change Check

| Item | Changed |
|---|---|
| Ranking Producer | NO |
| `expected_edge_score` | NO |
| `expected_return` | NO |
| Eligibility | NO |
| Candidate Top50 | NO |
| Portfolio membership decision | NO |
| Target position count | NO |
| Position Sizing calculation | NO |
| Minimum notional / lot判定 | NO |
| PM | NO |
| Re-entry | NO |
| Capital Deployment | NO |
| Max exposure / cash buffer | NO |
| Submit Guard | NO |
| BUY/SELL lifecycle | NO |
| Historical-specific branch | NO |
| Runtime fresh-run / resume | NO |

## 11. Evidence

Evidence root:

```text
reports/phase24_ia_rank_authority_metadata_runtime_evidence_audit_and_observability_closure/
```

Machine report:

```text
reports/phase_reports/phase24_ia_rank_authority_metadata_runtime_evidence_audit_and_observability_closure.json
```

## 12. Remaining Performance Gap

No new performance logic gap was introduced or evaluated in this task. The remaining performance work should continue from Phase24 performance gap inventory after Operator review of the closed IA observability path.

## 13. Recommended Next Task

Operator inspection of the next available Runtime evidence using the corrected Planning Evidence / Pending Generation evidence paths. Do not request a new Runtime rerun solely for IA.
