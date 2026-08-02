# Phase24-HY Ranking Consumer Alignment and Portfolio Construction Rank Authority Repair

## 1. Primary Judgment

`PHASE24_HY_RANKING_CONSUMER_ALIGNMENT_REPAIRED_SHORT_VALIDATION_PASS_RUNTIME_RERUN_REQUIRED`

## 2. Executive Summary

Phase24-HX confirmed that the Ranking producer was correct, but a downstream consumer adapter could use `candidate_rank` before `buy_rank` for opportunity rows. Phase24-HY repaired that consumer boundary.

Opportunity rows now resolve rank from canonical opportunity rank authority only: semantic `opportunity_buy_rank`, materialized by the current artifact as `buy_rank`. Missing, invalid, or conflicting opportunity rank authority fails closed as `REVIEW_REQUIRED` with row rejection. Candidate rows remain bound to `candidate_rank`, but candidate rank is never promoted to opportunity rank.

No Ranking producer, eligibility, Strategy parameter, Portfolio Policy, Position Sizing policy, PM, Re-entry, Submit Guard, max exposure, cash buffer, historical-only, or test-only behavior was changed.

## 3. Reviewed Evidence

- `docs/phase_reports/phase24_hx_opportunity_ranking_semantics_and_top_rank_selection_trace_audit.md`
- `reports/phase_reports/phase24_hx_opportunity_ranking_semantics_and_top_rank_selection_trace_audit.json`
- `docs/02_architecture/strategy_architecture_v1.md`
- `docs/02_architecture/autonomous_ai_operations_architecture.md`
- `docs/02_architecture/runtime_architecture_v2.md`
- `docs/01_requirements/phase_roadmap.md`

## 4. Architecture / Contract Updates

Updated:

- `docs/02_architecture/strategy_architecture_v1.md`
- `docs/02_architecture/autonomous_ai_operations_architecture.md`
- `docs/02_architecture/runtime_architecture_v2.md`
- `docs/01_requirements/phase_roadmap.md`

Created:

- `docs/phase_reports/phase24_hy_ranking_consumer_alignment_and_rank_authority_contract.md`

## 5. Rank Authority Contract

| Field | Contract |
|---|---|
| Canonical semantic field | `opportunity_buy_rank` |
| Runtime artifact field | `buy_rank` |
| Source artifact | `.runtime/runtime_state/buy_ai/<business_date>/opportunity_rankings.json` |
| Producer | Runtime v2 BUY AI Producer |
| Sort | `expected_edge_score DESC`, `code ASC` |
| Consumer | Strategy adapter, Portfolio Construction, Position Sizing, Runtime Planning, Pending lineage |

Forbidden fallback for opportunity rows:

- `candidate_rank`
- candidate model rank
- adapter index
- array order
- recomputed rank

## 6. Implementation Summary

### HY-I1 Adapter Rank Selection Repair

`shadow_runtime._candidate_downstream_rows` now separates candidate and opportunity rank authority. Opportunity rows resolve only `opportunity_buy_rank` / `buy_rank`; candidate rows resolve `candidate_rank`.

### HY-I2 Missing Rank Fail-Closed

Opportunity rows with missing, invalid, or conflicting rank authority are marked `REVIEW_REQUIRED`, `REJECTED`, and `NOT_ELIGIBLE`.

### HY-I3 Portfolio Construction Evidence Repair

Portfolio Construction members now expose:

```text
input_opportunity_rank
input_opportunity_rank_authority
input_opportunity_rank_source_path
input_opportunity_rank_source_hash
input_opportunity_row_id
input_opportunity_row_authority_hash
```

### HY-I4 Downstream Lineage Propagation

Position Sizing and Runtime Planning now propagate:

```text
opportunity_buy_rank
opportunity_row_id
opportunity_row_authority_hash
opportunity_artifact_path
opportunity_artifact_hash
```

### HY-I5 Strategy Decision Trace Repair

Strategy observability now separates `candidate_rank`, `opportunity_buy_rank`, `opportunity_rank_authority`, and Runtime Planning rank lineage.

### HY-I6 Planning Evidence Consistency

Runtime Planning plans now carry Portfolio Construction and Position Sizing opportunity rank lineage fields for consistency checks. Pending/execution campaign lineage was not redesigned.

## 7. Regression

Short validation:

```text
tests/strategy/test_phase24_hy_rank_authority.py
tests/strategy/test_phase22_e_portfolio_construction.py
tests/strategy/test_phase22_j_position_sizing.py
tests/strategy/test_phase22_g_runtime_planning.py
tests/runtime_v2/test_phase23_i_strategy_planning_authority.py
tests/runtime_v2/test_phase24_ht_planning_submit_feasibility.py
tests/runtime_v2/test_phase17_x_historical_sell_planning_authority.py
tests/runtime_v2/test_phase24_h_cost_basis_authority.py
```

Result:

```text
5 passed
94 passed
40 passed
```

Runtime fresh run / resume was not executed.

## 8. Acceptance

- Architecture updated: PASS
- Contract updated: PASS
- Roadmap updated: PASS
- Canonical opportunity rank authority maintained: PASS
- Ranking producer unchanged: PASS
- Eligibility unchanged: PASS
- Portfolio Policy unchanged: PASS
- Position Sizing policy unchanged: PASS
- Submit Guard unchanged: PASS
- Strategy parameters unchanged: PASS
- Historical/test-only branch avoided: PASS
- Short regression PASS: PASS
- Runtime rerun required: YES

## 9. Risks

Old direct unit fixtures may still use `opportunity_rank` / `rank` as explicit legacy aliases before the HY adapter boundary. The adapter itself remains fail-closed for opportunity rows missing `buy_rank` / `opportunity_buy_rank`.

## 10. Recommended Next Task

Operator Runtime rerun for Phase24-HY confirmation, focusing on the 2022-07-25 and 2022-07-26 opportunity rank lineage for 66590 and downstream Portfolio Construction / Planning evidence consistency.
