# Phase19-BU Position Management Feature Input Contract Completion

Final judgment: `PHASE19_BU_PM_FEATURE_INPUT_CONTRACT_COMPLETE_20BD_SMOKE_DEFERRED_BY_USER`

## Scope

Phase19-BU completed the Production-common Position Management feature input contract gap identified in Phase19-BS. The objective was not to increase SELL, and no PM threshold, EXIT / REDUCE threshold, Opportunity score, BUY policy, SELL policy, or Historical-only behavior was changed.

Reviewed SoT / contract:

- `docs/02_architecture/autonomous_ai_operations_architecture.md`
- `docs/02_architecture/runtime_architecture_v2.md`
- `docs/02_architecture/ai_input_output_and_artifact_contract.md`
- `docs/02_architecture/ai_generation_artifact_contract.md`
- `docs/02_architecture/ai_artifact_registry_and_capital_allocation_contract.md`
- `docs/02_architecture/position_management_reduce_quantity_contract.md`
- `docs/03_ai_design/position_management_ai_design.md`
- Phase19-BP/BQ/BR/BS/BT reports

## Root Cause

Phase19-BS correctly identified a remaining PM feature input contract gap: Runtime PM feature artifacts contained position state, Current valuation, and Opportunity context, but the technical market features already consumed by the PM scorer were absent from Production Runtime inputs. As a result, PM inference could fall back to internal defaults for trend/risk components.

This was a contract mismatch, not a SELL distribution target and not a Historical-only issue.

## Classification

| Class | Judgment | Evidence |
|---|---:|---|
| Runtime defect | No, after BU fix | PM now fail-closes before inference when required PM technical features are absent. |
| AI Policy defect | No | PM scoring logic and thresholds were not changed. |
| Contract mismatch | Fixed | A formal PM feature input contract was added and implemented in the Production-common feature/PM path. |
| Test Profile limitation | Partial | 20BD smoke was not completed per user instruction; 1BD and 5BD smoke passed before the stop. |
| No defect | Not the original classification | The pre-BU technical feature omission was a real contract gap. |

## Contract Added

Created:

```text
docs/02_architecture/position_management_feature_input_contract.md
```

Required PM technical features:

- `price_momentum_return_5d`
- `price_momentum_return_20d`
- `trend_close_over_ma_20d`
- `trend_ma_5_20_ratio`
- `volume_momentum_ratio_5d`
- `volatility_return_std_20d`

Optional feature:

- `no_position_reason`

No scoring feature may be silently defaulted in Runtime. Held-position inference requires empty `missing_features`, empty `defaulted_features`, valid temporal metadata, finite numeric technical values, and one row per held `target_date` / `code`.

## Implementation

Feature Refresh now emits the required PM technical fields in `position_feature_input.parquet`. The PM feature builder does not reimplement the market calculations. It receives the canonical `candidate_features.parquet` frame created by the Feature Refresh pipeline and copies the canonical technical columns for the same `feature_date` and `code`.

Evidence:

- `src/ai_fund_lab_v2/paper_trading/feature_refresh.py` adds the PM required columns and passes the candidate frame into `_build_position_feature_input()`.
- `_candidate_technical_context()` copies the canonical technical columns and records `feature_source_artifact` / `feature_source_hash`.
- `src/ai_fund_lab_v2/runtime_v2/position_management/producer.py` defines `PM_FEATURE_CONTRACT_VERSION = runtime_v2_pm_feature_input_contract_v2`.
- PM validation requires the technical columns, rejects missing/non-finite values, rejects duplicate joins, rejects future/stale data, rejects non-empty `missing_features`, and rejects non-empty `defaulted_features`.
- `src/ai_fund_lab_v2/runtime_v2/market_refresh/consumer_readiness.py` now requires the same PM v2 columns.
- `src/ai_fund_lab_v2/position_management_ai/inference.py` classifies the new provenance columns as metadata-only, so they do not become scoring features.

## Feature Authority

Authority path:

```text
Canonical market data
  -> Feature Refresh / candidate_features.parquet
  -> position_feature_input.parquet
  -> PM input contract validation
  -> Position Management inference
  -> position_management_decisions.json
```

No normalization, recalculation, symbol-specific bypass, Historical-only branch, or test-only fallback was added in the PM adapter.

## Runtime Evidence

Runtime evidence file:

```text
reports/phase_reports/phase19_bu_pm_feature_runtime_evidence.json
```

From the 5BD historical smoke state after rollback from the user-cancelled 20BD run:

- Feature dates: `2026-06-17`, `2026-06-18`, `2026-06-19`, `2026-06-22`, `2026-06-23`
- PM feature rows with held positions: 16
- Held symbols observed: `43780`, `45640`, `66590`, `81050`, `89180`
- Required technical feature null count: 0 for all six required technical fields
- `missing_features`: `[]`
- `defaulted_features`: `[]`
- `temporal_validation_status`: `PASS`
- `feature_source_hash`: non-empty for all held-position PM feature rows

Technical feature daily variation was observed:

| Feature | Min | Median | Max | Unique values |
|---|---:|---:|---:|---:|
| `price_momentum_return_5d` | -0.288703 | -0.0339285 | 0.105263 | 12 |
| `price_momentum_return_20d` | -0.447917 | 0.0 | 0.545455 | 13 |
| `trend_close_over_ma_20d` | 0.728051 | 0.9688015 | 1.042184 | 13 |
| `trend_ma_5_20_ratio` | 0.788009 | 0.9971645 | 1.054819 | 14 |
| `volume_momentum_ratio_5d` | 0.257998 | 0.783756 | 1.060304 | 16 |
| `volatility_return_std_20d` | 0.036801 | 0.078642 | 0.193535 | 15 |

5BD PM action distribution:

| Action | Count |
|---|---:|
| ADD | 3 |
| HOLD | 8 |
| REDUCE | 2 |
| EXIT | 3 |

This distribution is evidence that the contract completion does not block existing EXIT/REDUCE reachability. It is not used as a SELL-volume tuning target.

## Regression

Executed before the user requested no further tests:

```text
PYTHONPATH=src PYTHONPYCACHEPREFIX=/private/tmp/phase19_bu_pycache python3 -m pytest -q \
  tests/runtime_v2/test_phase15af_position_management_runtime_connection.py \
  tests/runtime_v2/test_phase15ap_position_management_input_contract.py \
  tests/runtime_v2/test_phase19_bn_pm_opportunity_model_authority.py \
  tests/runtime_v2/test_phase19_br_accepted_generation_bound_runtime_inference.py \
  tests/runtime_v2/test_phase19_bt_reduce_quantity_contract.py
```

Result:

```text
39 passed
```

Related feature/consumer regression:

```text
81 passed
```

Included coverage:

- required PM features are supplied
- required feature missing fails closed
- optional feature missing follows explicit contract
- no implicit default fallback
- feature values match canonical source artifact
- future data rejected
- stale / wrong-date rows rejected
- date/symbol join integrity
- historical/demo/production feature parity
- technical features affect PM score path
- existing EXIT/REDUCE remains valid

Historical smoke:

| Scope | Run ID | Result |
|---|---|---:|
| 1BD | `runtime-test-historical-smoke-20260721T212343110216Z` | PASS |
| 5BD | `runtime-test-historical-smoke-20260721T212431085076Z` | PASS |
| 20BD | `runtime-test-historical-smoke-20260721T212717811530Z` | Stopped by user request, closed as REVIEW_REQUIRED |

20BD is intentionally not marked PASS. The interrupted 20BD run was rolled back to `backup-historical-smoke-20260721T212709934434Z`; runner status returned to IDLE.

## Registry Note

Changing `src/ai_fund_lab_v2/runtime_v2/position_management/producer.py` changed the accepted PM runtime adapter source hash. The PM accepted current-path registry was repaired and refreshed to the current producer hash:

```text
93581111ae9b61facf669f8033d87e927f103d05483b4f212da4a592dbb15185
```

Full event log validation returned PASS/NONE after repair and index/checkpoint refresh.

## Fix Necessity

Fix was required because PM design says Position Management evaluates trend rather than only profit, and the architecture contract requires PM to consume explicit Feature Artifacts with point-in-time validity. Allowing PM technical trend/risk features to be absent while the scorer defaults them would leave a hidden input contract gap.

No further PM policy change is recommended in this phase.

## Regression Recommendation

Before declaring full Phase19-BU smoke closure, rerun a clean 20BD historical smoke when the operator allows testing again. Do not treat the user-cancelled 20BD run as PASS evidence.

Final supporting judgments:

- `PM_FEATURE_AUTHORITY_PASS`
- `PM_REQUIRED_FEATURE_SCHEMA_PASS`
- `PM_TECHNICAL_FEATURE_CONNECTION_PASS`
- `PM_FEATURE_TEMPORAL_CONTRACT_PASS`
- `PM_FEATURE_FAIL_CLOSED_PASS`
- `PM_FEATURE_DAILY_VARIATION_PASS`
- `HISTORICAL_DEMO_PRODUCTION_PM_FEATURE_COMMON_PASS`
- `PHASE19_BU_20BD_HISTORICAL_SMOKE_DEFERRED_BY_USER`
