# Phase24-HY Ranking Consumer Alignment and Rank Authority Contract

## 1. Primary Judgment

`PHASE24_HY_CONTRACT_DEFINED_IMPLEMENTATION_REQUIRED`

## 2. Scope

Phase24-HY fixes the downstream consumer interpretation of opportunity rank. It does not change the Ranking producer, `expected_edge_score`, `expected_return`, eligibility, Candidate Top50, Portfolio Policy, Position Sizing policy, PM, Re-entry, Submit Guard, `max_exposure`, cash buffer, or historical/runtime thresholds.

## 3. Canonical Rank Authority

| Item | Contract |
|---|---|
| Canonical semantic field | `opportunity_buy_rank` |
| Runtime artifact field | `buy_rank` |
| Source artifact | `.runtime/runtime_state/buy_ai/<business_date>/opportunity_rankings.json` |
| Producer | Runtime v2 BUY AI Producer |
| Sort authority | `expected_edge_score DESC`, `code ASC` |
| Consumer | Strategy adapter, Portfolio Construction, Position Sizing, Runtime Planning, Pending lineage |

`buy_rank` in the opportunity ranking artifact maps to the canonical consumer field `opportunity_buy_rank`.

## 4. Rank Field Semantics

| Field | Meaning | May Substitute For Opportunity Rank |
|---|---|---|
| `candidate_rank` | Candidate model order before opportunity ranking | No |
| `opportunity_buy_rank` | Canonical opportunity BUY rank | Yes |
| `input_opportunity_rank` | Portfolio Construction copy of canonical opportunity rank | Yes, only after authority mapping |
| `portfolio_selection_order` | Portfolio Construction selection order | No |
| `runtime_planning_order` | Runtime Planning emission/order trace | No |

## 5. Adapter Contract

Opportunity rows:

- rank authority is `opportunity_buy_rank`, sourced from artifact `buy_rank` / `opportunity_buy_rank`
- `candidate_rank`, candidate model rank, adapter index, artifact array order, and recomputed rank are forbidden as opportunity rank fallback
- missing, invalid, or conflicting opportunity rank authority is `REVIEW_REQUIRED` and row consumer rejection

Candidate rows:

- rank authority is `candidate_rank`
- candidate rank is never promoted to opportunity rank

## 6. Portfolio Construction Evidence

Opportunity-backed Portfolio Construction members must expose:

```text
input_opportunity_rank
input_opportunity_rank_authority
input_opportunity_rank_source_path
input_opportunity_rank_source_hash
input_opportunity_row_id
input_opportunity_row_authority_hash
```

Selected rows must also preserve downstream lineage:

```text
opportunity_buy_rank
opportunity_row_id
opportunity_row_authority_hash
opportunity_artifact_path
opportunity_artifact_hash
```

## 7. Downstream Propagation

Position Sizing, Runtime Planning, and Pending evidence must carry the opportunity rank lineage when a selected row originates from the opportunity artifact. Runtime Planning may add planning order evidence, but planning order is not rank authority.

## 8. Failure State

| Condition | Result |
|---|---|
| Missing opportunity rank | `REVIEW_REQUIRED`, row rejected |
| Invalid opportunity rank | `REVIEW_REQUIRED`, row rejected |
| Conflicting opportunity rank aliases | `REVIEW_REQUIRED`, row rejected |
| Candidate rank present on opportunity row | Ignored for opportunity rank |
| Downstream rank mismatch | `REVIEW_REQUIRED` evidence gap |

## 9. Environment Contract

The same authority and failure contract applies to Historical, Demo, and Production. Historical-specific, test-specific, or demo-specific rank branches are prohibited.

## 10. Implementation Gate

Implementation may proceed only after this contract, architecture documents, and roadmap are updated. Short regression and static validation are required. Runtime fresh run, resume, and long historical execution are prohibited in Phase24-HY.
