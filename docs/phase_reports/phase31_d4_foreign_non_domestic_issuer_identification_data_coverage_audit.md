# Phase31-D4 — Foreign / Non-Domestic Issuer Identification & Data-Coverage Audit

Status: COMPLETE
Task type: READ-ONLY AUDIT

## PRIMARY_JUDGMENT

```text
PHASE31_D4_FOREIGN_ISSUER_NOT_RELIABLY_IDENTIFIABLE
```

D4 used only J-Quants and existing repository/runtime evidence. No implementation, Universe/Candidate/BUY eligibility change, nationality-based exclusion, JPX/external paid source, fresh-run, resume, replay, or long Historical execution was performed.

The current J-Quants `listed_issues` / master artifact contains objective listed membership and product/security category fields, but it does not contain an issuer-country, domicile, foreign-issuer flag, domestic/foreign distinction, or other issuer-origin metadata. Therefore foreign/non-domestic issuer membership cannot be reliably measured from the current repository evidence without prohibited name heuristics or external knowledge.

The data can distinguish common-equity-like listings from other product categories by `ProdCat`, but that is an instrument/product classification, not issuer nationality.

## TARGET_EVIDENCE

Representative date:

```text
2026-07-06
```

Artifacts inspected:

```text
.runtime/operations/jquants/raw/jquants/listed_issues/data.parquet
.runtime/operations/jquants/raw/jquants/equities_bars_daily/data.parquet
.runtime/operations/jquants/raw/jquants/fins_summary/data.parquet
.runtime/operations/jquants/raw/jquants/earnings_calendar/data.parquet
.runtime/runtime_state/buy_ai/2026-07-06/candidate_decisions.json
.runtime/runtime_state/buy_ai/2026-07-06/opportunity_rankings.json
.runtime/strategy_artifacts/corporate_event/2026-07-06/corporate_event.json
```

For `listed_issues`, there was no exact `Date = 2026-07-06` snapshot in the artifact. The latest available PIT listed snapshot at or before the target date was used:

```text
LISTED_ISSUES_SNAPSHOT_DATE = 2026-06-30
```

This is a read-only diagnostic binding. It does not mutate canonical artifacts.

## FOREIGN_ISSUER_IDENTIFIABLE

```text
NO
```

## IDENTIFICATION_FIELDS

Issuer-origin fields found:

```text
NONE
```

Fields inspected in the target listed snapshot:

```text
Date
Code
CoName
CoNameEn
S17
S17Nm
S33
S33Nm
ScaleCat
Mkt
MktNm
Mrgn
MrgnNm
ProdCat
pagination_page
target_date
code
business_key
source
endpoint
fetched_at
```

Usable objective fields:

| Field | Meaning in D4 | Limitation |
|---|---|---|
| `Code` | listed symbol identity | no issuer-origin semantics |
| `Mkt`, `MktNm` | market/section | no domestic/foreign distinction |
| `ProdCat` | product/security category | distinguishes instrument class, not issuer nationality |
| `S17`, `S17Nm`, `S33`, `S33Nm` | sector classification | no issuer-origin semantics |
| `CoName`, `CoNameEn` | company name | not used for classification because name heuristics are prohibited |

Fields not present:

```text
issuer_country
domicile
foreign_issuer_flag
foreign_stock_classification
domestic_foreign_distinction
issuer_origin
country_of_incorporation
```

## CLASSIFICATION_SEMANTICS

Because issuer origin is not objectively available, D4 does not classify any symbol as `DOMESTIC` or `FOREIGN_ISSUER`.

The only safe auxiliary classification is product-category based:

| Auxiliary class | Rule | Business meaning |
|---|---|---|
| `COMMON_EQUITY_PROXY` | `ProdCat = 011` | ordinary/common-equity-like product category |
| `OTHER_SPECIAL_SECURITY` | `ProdCat` present and not `011` | ETF/ETN/REIT/preferred/other non-common product categories depending on J-Quants category |
| `UNRESOLVED_ISSUER_ORIGIN` | no issuer-origin evidence | not proven domestic or foreign |

`COMMON_EQUITY_PROXY` must not be read as confirmed domestic issuer.

## REAL UNIVERSE COUNT

Required issuer-origin classification:

| Metric | Count | Rate |
|---|---:|---:|
| TOTAL_SYMBOLS | 4,437 | 100.00% |
| DOMESTIC_COUNT | 0 | 0.00% |
| FOREIGN_ISSUER_COUNT | 0 | 0.00% |
| OTHER_SPECIAL_SECURITY_COUNT | 538 | 12.13% |
| UNRESOLVED_COUNT | 3,899 | 87.87% |

Interpretation:

- `DOMESTIC_COUNT = 0` and `FOREIGN_ISSUER_COUNT = 0` mean no symbol was objectively confirmed by issuer-origin evidence.
- `OTHER_SPECIAL_SECURITY_COUNT = 538` is product-category evidence, not foreign-issuer evidence.
- `UNRESOLVED_COUNT = 3,899` are common-equity-proxy listings whose issuer origin is unresolved under current J-Quants evidence.

Auxiliary product-category breakdown:

| ProdCat | Count |
|---|---:|
| `011` | 3,899 |
| `014` | 412 |
| `023` | 56 |
| `013` | 63 |
| `021` | 5 |
| `012` | 2 |

## CANDIDATE COUNT

Candidate artifact:

```text
.runtime/runtime_state/buy_ai/2026-07-06/candidate_decisions.json
```

Required issuer-origin classification:

| Metric | Count | Rate |
|---|---:|---:|
| TOTAL_CANDIDATES | 50 | 100.00% |
| DOMESTIC_CANDIDATES | 0 | 0.00% |
| FOREIGN_ISSUER_CANDIDATES | 0 | 0.00% |
| OTHER_SPECIAL_CANDIDATES | 1 | 2.00% |
| UNRESOLVED_CANDIDATES | 49 | 98.00% |

`FOREIGN_ISSUER_CANDIDATE_SYMBOLS`:

```text
[]
```

This empty list means no foreign issuer was objectively identified, not that the candidate set is proven foreign-free.

Auxiliary non-common product-category candidate:

| Symbol | Auxiliary class | ProdCat | Market | Sector |
|---|---|---:|---|---|
| `93990` | `OTHER_SPECIAL_SECURITY` | `021` | スタンダード | 情報･通信業 |

## DATA COVERAGE COMPARISON

Because no confirmed foreign/non-domestic issuer group exists in current evidence, D4 cannot compute a foreign-vs-domestic issuer coverage comparison. The following auxiliary coverage metrics are product-category based and are not nationality claims.

Universe data coverage on the 2026-06-30 listed snapshot, evaluated as of 2026-07-06:

| Group | Total | Daily quotes exact | Daily exact rate | Daily quote lookback | Lookback rate | Fins summary up to date | Fins rate | Earnings calendar symbols | Earnings rate |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| COMMON_EQUITY_PROXY | 3,899 | 3,898 | 99.97% | 3,899 | 100.00% | 26 | 0.67% | 57 | 1.46% |
| OTHER_SPECIAL_SECURITY | 538 | 538 | 100.00% | 538 | 100.00% | 0 | 0.00% | 1 | 0.19% |

Candidate data coverage:

| Metric | Value |
|---|---:|
| TOTAL_CANDIDATES | 50 |
| candidate decisions `missing_columns` | `[]` |
| daily quotes exact-date coverage | 50 / 50 = 100.00% |
| fins summary up-to-date coverage | 0 / 50 = 0.00% |
| earnings calendar symbol coverage | 0 / 50 = 0.00% |
| embedded Strategy/Candidate ranking input coverage | 50 / 50 = 100.00% |

Notes:

- The referenced `feature_path` in the candidate artifact was `.runtime/operations/feature_artifacts/2026-07-06/candidate_features.parquet`, but that parquet file was not present in the current workspace. The candidate decision artifact itself contained the candidate rows and `missing_columns = []`.
- The financial statement and earnings-calendar rates reflect the stored J-Quants raw artifacts available in the current workspace. They do not prove a foreign-issuer-specific gap because the foreign group is not identifiable.

## REQUIRED OUTPUT METRICS

```text
DOMESTIC_REQUIRED_DATA_COVERAGE_RATE = NOT_MEASURABLE_WITH_CURRENT_ISSUER_ORIGIN_EVIDENCE
FOREIGN_REQUIRED_DATA_COVERAGE_RATE = NOT_MEASURABLE_WITH_CURRENT_ISSUER_ORIGIN_EVIDENCE
FOREIGN_ISSUER_FINANCIAL_DATA_COVERAGE = NOT_MEASURABLE_WITH_CURRENT_ISSUER_ORIGIN_EVIDENCE
FOREIGN_ISSUER_STRATEGY_INPUT_COVERAGE = NOT_MEASURABLE_WITH_CURRENT_ISSUER_ORIGIN_EVIDENCE
DATA_COVERAGE_GAP = PARTIAL
```

`DATA_COVERAGE_GAP = PARTIAL` because product-category coverage differences are observable, especially around `fins_summary`, but a foreign/non-domestic issuer-specific gap is not confirmable without issuer-origin evidence.

## DATA-QUALITY GAP FINDINGS

Observed:

- product-category classification exists through `ProdCat`;
- daily quote coverage is effectively complete for both common-equity-proxy and other-special-security groups;
- `fins_summary` coverage in the stored artifact is sparse as of the target date;
- `earnings_calendar` symbol coverage is sparse;
- candidate decision rows have complete embedded Strategy/Candidate ranking inputs for the selected 50 symbols.

Not observed:

- issuer-origin metadata;
- confirmed foreign issuer group;
- evidence that foreign/non-domestic issuer data coverage is worse than confirmed domestic issuer data coverage;
- objective basis for a nationality-based Universe exclusion.

## 93180 CONTROL

PIT listed evidence for 93180:

| As of | Listed snapshot date | Code | ProdCat | Market | Sector | Issuer-origin classification |
|---|---|---:|---:|---|---|---|
| 2022-08-10 | 2022-08-01 | `93180` | `011` | スタンダード | 証券･商品先物取引業 | `UNRESOLVED` |

```text
93180_ISSUER_CLASSIFICATION = UNRESOLVED
```

93180 required data coverage as of 2022-08-10:

| Evidence | Status |
|---|---|
| listed_issues/master | PRESENT, latest PIT row 2022-08-01 |
| daily_quotes | PRESENT, latest bar 2022-08-10, 61 lookback rows found |
| candidate decision row | PRESENT in `.runtime/runtime_state/buy_ai/2022-08-10/candidate_decisions.json` |
| candidate decision `missing_columns` | `[]` |
| `listed_info.product_category` | `011` |
| `listed_info.security_type` | `011` |
| fins_summary | NOT_FOUND in current stored artifact at or before 2022-08-10 |
| earnings_calendar | NOT_FOUND in current stored artifact at or before 2022-08-10 |
| issuer-origin field | NOT_AVAILABLE |

```text
93180_REQUIRED_DATA_COVERAGE = PARTIAL
```

This is not a finding that 93180 is foreign or non-domestic. It remains unresolved by current PIT issuer-origin evidence.

## FAMILY-WIDE EXAMPLES

No foreign/non-domestic issuer symbols can be objectively listed because current evidence does not identify that family.

Objective product-category examples do exist, but they are not foreign-issuer examples. The only non-common product-category candidate on 2026-07-06 was:

```text
93990
```

## UNIVERSE POLICY EVIDENCE

```text
BLANKET_FOREIGN_EXCLUSION_SUPPORTED = NO
DATA_COVERAGE_BASED_RESTRICTION_SUPPORTED = PARTIAL
```

Reasoning:

- A blanket foreign-issuer exclusion is not supported because current evidence cannot identify foreign/non-domestic issuers.
- A data-coverage-based restriction may be supportable in a future design if it gates on objective missing required inputs or unsupported instrument/product categories, not nationality or inferred issuer origin.
- D4 does not implement any such restriction.

## CONSTRAINT CHECK

```text
D0_D1_SEMANTICS_CHANGED = NO
JPX_SOURCE_USED = NO
FUTURE_INFORMATION_USED = NO
LONG_HISTORICAL_EXECUTED = NO
NATIONALITY_BASED_RULE_ADDED = NO
SYMBOL_BLACKLIST_ADDED = NO
BUY_LOGIC_CHANGED = NO
```

## NEXT_TASK_RECOMMENDATION

```text
issuer identification source gap
```

If the project needs a true foreign/non-domestic issuer policy, the next step is an issuer-origin source/design decision. If the actual concern is missing inputs, the safer next task is a broader Company Data Quality audit that defines required-data completeness gates independent of nationality.

## FINAL QUESTIONS

1. J-Quantsだけでforeign/non-domestic issuerを客観的に識別できるか？
   NO. Current stored J-Quants listed/master evidence has no issuer-country, domicile, foreign flag, or issuer-origin field.

2. 全Universe中何銘柄あるか？
   Objectively identified foreign/non-domestic issuers are 0件. This is not proof that none exist; it is an identification-source gap. Product-category auxiliary counts are 3,899 common-equity proxy and 538 other special securities.

3. Candidate 50銘柄中何銘柄あるか？
   Objectively identified foreign/non-domestic issuers are 0件. One candidate, `93990`, is an `OTHER_SPECIAL_SECURITY` by `ProdCat`, but not an identified foreign issuer.

4. 国内普通株より必要データcoverageが悪いか？
   Foreign-vs-domestic comparison is not measurable. Product-category comparison shows daily quote coverage is complete/nearly complete, while stored `fins_summary` coverage is sparse for both groups and especially 0 / 538 for other special securities.

5. 93180は客観的にforeign/non-domestic分類になるか？
   NO. 93180 is `UNRESOLVED` for issuer origin. PIT listed evidence only shows `ProdCat = 011`, market スタンダード, and sector 証券･商品先物取引業.

6. foreign issuerを一律除外する根拠はあるか？
   NO. The required classification cannot be made from current evidence, and D4 does not support nationality-based exclusion.

7. それとも「必要データが不足する銘柄だけ除外」が妥当か？
   PARTIAL. A future objective required-data completeness gate may be defensible, but it should be based on missing canonical inputs or unsupported instrument/product category, not inferred foreign issuer status.
