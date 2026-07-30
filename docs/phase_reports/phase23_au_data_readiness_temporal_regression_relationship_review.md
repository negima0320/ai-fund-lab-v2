# Phase23-AU Data Readiness Temporal Regression Relationship Review

## Primary Judgment

```text
PHASE23_AU_DATA_READINESS_RELATIONSHIP_REVIEW_COMPLETE
```

## Summary

Phase23-ATで残ったData Readiness temporal subsetの3 failuresを読取専用で確認した。

結論:

```text
Pattern B
```

3件すべてがReference Price / Position Sizingに関係するわけではない。むしろReference Price関連は0件だった。

ただし、1件はHistorical trading calendar authority欠損によりCurrent Valuation Temporal Authorityが解決できないfailであり、Temporal Authority / PIT relatedである。したがって「3件ともProduction Contractとは独立」とは証明できない。

## Counts

```text
OUT_OF_SCOPE_COUNT = 0
OBSOLETE_TEST_COUNT = 3
PRODUCTION_CONTRACT_COUNT = 0
REFERENCE_PRICE_RELATED_COUNT = 0
TEMPORAL_AUTHORITY_RELATED_COUNT = 1
PIT_RELATED_COUNT = 1
READY_FOR_1BD_RUNTIME_VALIDATION = false
```

## Failure Classification

### F1

```text
tests/runtime_v2/test_phase15as_data_readiness_semantic_consistency.py::test_phase15as_market_evidence_ready_and_safety_allow_can_be_ready
```

Expected:

```text
result.status = READY
```

Actual:

```text
result.status = REVIEW_REQUIRED
review_reasons = ["consumer_schema_review_required:pm"]
```

Market Evidence、quote、safety、current valuationはREADYだった。

Classification:

```text
OBSOLETE_TEST_EXPECTATION
```

Relation:

```text
Reference Price: no
Current Valuation: no
Market Evidence: no
Position Sizing: no
Temporal Authority: no
PIT: no
AQ/AR/AS/AT: no
```

## F2

```text
tests/runtime_v2/test_phase15as_data_readiness_semantic_consistency.py::test_phase15as_empty_pending_slot_is_ready_and_cli_has_no_missing_warning
```

Expected:

```text
exit_code = 0
```

Actual:

```text
exit_code = 20
final_state = REVIEW_REQUIRED
warnings = ["consumer_schema_review_required:pm"]
pending_slot_status = EMPTY
pending_active = false
```

Pending empty contract自体は通っている。fail原因はPM feature consumer readiness。

Classification:

```text
OBSOLETE_TEST_EXPECTATION
```

Relation:

```text
Reference Price: no
Current Valuation: no
Market Evidence: no
Position Sizing: no
Temporal Authority: no
PIT: no
AQ/AR/AS/AT: no
```

## F3

```text
tests/runtime_v2/test_phase17_ba_submit_temporal_authority_contract.py::test_phase17_ba_submit_pre_close_accepts_previous_trading_day_close_for_all_modes[historical-historical_simulated]
```

Expected:

```text
historical submit pre-close previous trading day close is READY
```

Actual:

```text
result.status = REVIEW_REQUIRED
review_reasons = [
  "current_valuation_not_ready",
  "historical_trading_calendar_authority_missing",
  "market_calendar_closed"
]
current_valuation_temporal_authority = missing_trading_calendar_authority
current_valuation_temporal_reason = current_valuation_previous_trading_date_missing
missing_evidence = ["historical_trading_calendar_authority"]
```

Classification:

```text
TEMPORAL_AUTHORITY_RELATED
PIT_RELATED
OBSOLETE_TEST_EXPECTATION
```

Relation:

```text
Reference Price: no
Current Valuation: yes
Market Evidence: no
Position Sizing: no
Temporal Authority: yes
PIT: yes
AQ/AR/AS/AT: no
```

## Production Contract Relation

F1/F2は、現在のProduction-common PM feature consumer readiness contractに対してfixture/test expectationが古い。

Evidence:

```text
consumer_schema_review_required:pm
```

F3は、Historical trading calendar authorityがない状態でprevious trading dateを仮定してはいけない、というProduction-common Temporal Authority contractに沿ってfail-closedしている。

Evidence:

```text
historical_trading_calendar_authority_missing
current_valuation_previous_trading_date_missing
```

## AT Relationship

Phase23-ATのReference Price Authority bindingとは直接関係なし。

AT変更ファイル:

```text
src/ai_fund_lab_v2/strategy/input_materialization.py
src/ai_fund_lab_v2/strategy/position_sizing.py
```

3failの直接原因:

```text
PM feature consumer readiness
Historical trading calendar / current valuation temporal authority
```

したがって、Reference Price修正を継続する必要はない。ただし、Pattern Aではないため、ATを「3件ともProduction Contractと独立」として正式PASSへ昇格することはできない。

## Deliverables

Human:

```text
docs/phase_reports/phase23_au_data_readiness_temporal_regression_relationship_review.md
```

Machine:

```text
reports/phase_reports/phase23_au_data_readiness_temporal_regression_relationship_review.json
```

Evidence:

```text
reports/phase23_au_data_readiness_temporal_regression_relationship_review/
```

## Existing Run Preservation

Required runtime test runs were read-only. No runtime rerun, fresh-run, resume, 1BD, 10BD, 20BD, Broker Write, Runtime Switch, J-Quants acquisition, Production code edit, or test edit was performed.

## Next Action

Reference Price path is not blocked by these failures, but 1BD gate should remain closed until the Temporal Authority related F3 is accepted as obsolete fixture expectation or handled in a separate Data Readiness/Historical Calendar follow-up.
