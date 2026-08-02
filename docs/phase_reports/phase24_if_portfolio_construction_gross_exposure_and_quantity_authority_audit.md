# Phase24-IF Portfolio Construction Gross Exposure and Quantity Authority Audit

## 1. Primary Judgment

`PHASE24_IF_PORTFOLIO_CONSTRUCTION_GROSS_EXPOSURE_REPAIRED_SHORT_VALIDATION_PASS_RUNTIME_RERUN_REQUIRED`

Target run: `runtime-test-historical-extended-smoke-20260801T223117629647Z`

Business date: `2023-06-14`

Direct halt reason:

```text
morning pipeline blocked: strategy_runtime_planning_blocked
```

## 2. Portfolio Policy Authority

Portfolio Policy was valid:

| Field | Value |
|---|---:|
| status | `PASS` |
| target_position_count | `10` |
| target_gross_exposure | `0.79` |
| cash_reserve | `0.21` |
| single_name_weight_cap | `0.18` |

No Policy, Market Context, Safety, Ranking, PM, or Position Sizing policy change was required.

## 3. Duplicate Existing Candidate Reconciliation

`76470` and `94320` were current-position rows and also present in the opportunity/candidate stream. Portfolio Construction reconciled each to one canonical membership row.

| Symbol | Current Position | Candidate / Opportunity | Membership | Target Weight | Judgment |
|---|---:|---:|---|---:|---|
| `76470` | true | true | `UNRESOLVED` | `0.0` | informational reconciliation |
| `94320` | true | true | `UNRESOLVED` | `0.0` | informational reconciliation |

`duplicate_existing_candidate_reconciled:*` is `INFO`, not a direct BLOCK reason. No duplicate weight double count was found.

## 4. Gross Exposure Calculation

Materialized selected BUY candidates:

```text
21340
59550
67310
99840
37820
40520
```

Calculation:

| Metric | Value |
|---|---:|
| target_gross_exposure | `0.79` |
| selected_member_count | `6` |
| unrounded base weight | `0.13166666666666665` |
| rounded per-member weight | `0.131667` |
| unrounded sum | `0.79` |
| materialized rounded sum | `0.790002` |
| observed overflow | `0.000002` |

The observed BLOCK was caused by six-decimal target weight rounding accumulation exceeding the fixed `0.000001` tolerance.

## 5. Contract Classification

`sum(target_weight) <= target_gross_exposure` remains the contract. This case is not genuine capacity overflow and not a gross exposure policy gap. It is a rounding tolerance implementation defect.

Genuine gross exposure overflow beyond rounding tolerance remains `BLOCK`.

## 6. Quantity Authority Audit

The six runtime planning quantity review symbols were:

```text
21340
37820
40520
59550
67310
99840
```

Each had a Portfolio Construction target row, but Position Sizing was already `BLOCK` via:

```text
portfolio_construction_block:BLOCK
```

Therefore the quantity failures are `UPSTREAM_BLOCK_PROPAGATION`, not independent Quantity Authority defects.

## 7. Block Propagation

Observed chain:

```text
Portfolio Construction BLOCK
  -> Position Sizing BLOCK
  -> Runtime Planning BLOCK
  -> Strategy Planning Authority BLOCKED
  -> Morning final_state BLOCKED
  -> exit_code 10
```

Position Sizing propagation was expected. Runtime Planning over-reported missing quantity authority as independent review reasons.

## 8. Safety Marker

The Morning preflight safety marker was non-causal. Data Readiness had historical neutral safety ready; the direct stop was Strategy Runtime Planning.

Classification:

```text
NON_CAUSAL_PREFLIGHT_MARKER
```

## 9. Root Cause Matrix

| Item | Judgment |
|---|---|
| Portfolio Construction Input Authority | `PASS` |
| Duplicate Existing Candidate Handling | `CORRECT` |
| Duplicate Reason Severity | `INFO` |
| Target Gross Exposure Authority | `PASS` |
| Overflow Cause | `FLOATING_POINT_ROUNDING_ACCUMULATION` |
| Portfolio Construction BLOCK | `DEFECT` |
| Position Sizing BLOCK | `EXPECTED_PROPAGATION` |
| Quantity Authority Failures | `UPSTREAM_ONLY` |
| Runtime Planning BLOCK | `OVER_REPORTED` |
| Production Risk | `YES` |
| Implementation Required | `YES` |
| Architecture Change Required | `NO` |

## 10. Recommended Next Task

Operator historical extended smoke rerun and confirm `2023-06-14` no longer stops on rounding-only gross exposure overflow, while genuine overflow and Phase24-ID/IE guards remain preserved.
