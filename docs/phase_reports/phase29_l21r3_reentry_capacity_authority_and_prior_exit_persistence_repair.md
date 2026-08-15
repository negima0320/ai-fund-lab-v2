# Phase29-L21R3 — Re-entry Capacity Authority + Prior Exit Persistence Repair

Task ID: `Phase29-L21R3`  
Mode: focused implementation + short regression. No fresh-run, resume-run, long Historical run, pending/runtime state mutation, accepted-generation change, model retraining, threshold tuning, Safety relaxation, or capital deployment policy change was performed.

## Primary Judgment

`PHASE29_L21R3_REENTRY_CAPACITY_AUTHORITY_AND_PRIOR_EXIT_PERSISTENCE_REPAIRED_FOCUSED_REGRESSION_PASS`

`L21S_READY = YES` for the L21R3 entry gate, subject to user-operated fresh/long validation for aggregate capital-deployment metrics.

## Before

L21R2 confirmed two defects:

- REENTRY capacity used `rolling_median_traded_value_20`, but production-common Strategy input materialization did not produce the field. Capacity therefore stayed `UNKNOWN` and blocked REENTRY recovery.
- PC semantic REENTRY awareness depended on the row being an active `ADD_CANDIDATE`. A temporary `EXCLUDE` row could blank `prior_exit_business_date` and classify as ordinary `BUY_NEW` despite persistent ledger prior EXIT evidence.

## Root Cause

Capacity root cause:

- PC consumer existed.
- L21R source evidence copy hook existed.
- The upstream production-common technical feature materializer did not emit canonical rolling traded value evidence.

Prior EXIT root cause:

- `_semantic_reentry_evidence` returned `BUY_NEW` with blank prior EXIT whenever `is_buy_new` was false.
- That conflated buy eligibility / row lifecycle with semantic awareness of a closed prior campaign.

## Implementation

Changed production-common Strategy code:

- `src/ai_fund_lab_v2/strategy/input_materialization.py`
- `src/ai_fund_lab_v2/strategy/shadow_runtime.py`
- `src/ai_fund_lab_v2/strategy/portfolio_construction.py`
- `src/ai_fund_lab_v2/strategy/position_sizing.py`

Added focused tests in:

- `tests/strategy/test_phase22_qe_input_materialization.py`
- `tests/strategy/test_phase29_l21k_prior_exit_materialization.py`
- `tests/strategy/test_phase22_e_portfolio_construction.py`

No Historical-only branch was added.

## Authority Chain

Capacity canonical source:

```text
J-Quants equities_bars_daily
-> production-common Strategy technical feature materialization
-> rolling_median_traded_value_20
-> shadow_runtime re-entry source evidence wiring
-> Portfolio Construction low-price / REENTRY capacity guard
-> Position Sizing observability fields
```

Capacity producer:

`input_materialization.produce_pm_technical_feature_artifact`

Materialized field:

`rolling_median_traded_value_20`

Formula:

```text
daily_traded_value = close * volume
rolling_median_traded_value_20 = median(last 20 PIT daily_traded_value rows)
```

Observability fields:

- `rolling_median_traded_value_20_authority`
- `rolling_median_traded_value_20_resolution`
- `capacity_source`
- `capacity_source_field`
- `capacity_ratio`
- `liquidity_capacity_status`
- `reentry_capacity_status`

PC consumer:

`portfolio_construction._resolve_low_price_reentry_allocation_guard`

Capacity ratio:

```text
capacity_ratio = proposed_target_notional / rolling_median_traded_value_20
```

## PIT Contract

The producer follows the existing technical feature contract:

- source rows are filtered to `target_date <= feature_date`;
- `feature_date` must not exceed `business_date`;
- no latest fallback is used;
- authority payload records `PIT_status=PASS` and `latest_fallback_used=false`.

Future rows remain rejected by the existing materialization `pit_validation` contract.

## 23880 Lifecycle

Focused regression now covers the 23880-style lifecycle:

```text
D0 current position exists
D1 full SELL closes campaign
D2 prior_exit_business_date=D1, semantic=REENTRY
D3 prior_exit_business_date=D1, semantic=REENTRY
D4 cooldown PASS, semantic=REENTRY
D5 temporary non-buy/exclude lifecycle still preserves prior EXIT and REENTRY awareness
D6 buy eligible again remains semantic=REENTRY
```

Semantic lifetime:

- Prior EXIT awareness persists after a closed campaign while there is no current position.
- It does not expire when cooldown passes.
- It should end only when a new current position/campaign supersedes the closed campaign state.

Cooldown lifetime:

- Cooldown is only a qualification gate on a REENTRY.
- It is not an expiry rule for prior EXIT awareness.

## Capacity Resolution Examples

Normal capacity:

- rolling traded value present and large;
- `capacity_ratio` resolved;
- `liquidity_capacity_status=NORMAL`;
- `reentry_capacity_status=NORMAL`;
- REENTRY can pass capacity.

Excessive participation:

- rolling traded value present but too small;
- `capacity_ratio > 0.03` or status `SEVERE`;
- recovery fails closed with `reentry_capacity_unavailable`.

Genuinely missing market evidence:

- missing/invalid volume or insufficient PIT traded-value window;
- `rolling_median_traded_value_20=null`;
- resolution status `REVIEW_REQUIRED`;
- PC capacity remains `UNKNOWN`;
- REENTRY remains fail-closed / review-required.

UNKNOWN was not changed to PASS.

## Regression Results

PASS:

```bash
PYTHONPATH=src python3 -m pytest tests/strategy/test_phase22_qe_input_materialization.py tests/strategy/test_phase29_l21k_prior_exit_materialization.py tests/strategy/test_phase22_e_portfolio_construction.py -q
```

Result:

```text
99 passed
```

PASS:

```bash
PYTHONPATH=src python3 -m pytest tests/strategy/test_phase22_j_position_sizing.py tests/strategy/test_phase22_g_runtime_planning.py -q
```

Result:

```text
125 passed
```

PASS:

```bash
PYTHONPYCACHEPREFIX=/tmp/ai-fund-lab-v2-pycache-l21r3 python3 -m py_compile src/ai_fund_lab_v2/strategy/input_materialization.py src/ai_fund_lab_v2/strategy/shadow_runtime.py src/ai_fund_lab_v2/strategy/portfolio_construction.py src/ai_fund_lab_v2/strategy/position_sizing.py
```

Static check:

```text
git diff --check: PASS
```

## BUY_NEW / BUY_ADD / SELL Regression

BUY_NEW:

- Normal BUY_NEW without prior EXIT remains BUY_NEW.
- No new universal BUY_NEW capacity hard gate was added.

BUY_ADD:

- Current-position ADD remains `BUY_ADD`.
- Prior EXIT materialization is still skipped for current positions.
- BUY_ADD incremental logic and Position Management ADD semantics were not changed.

SELL / REDUCE / EXIT:

- SELL, REDUCE, and EXIT authority paths were not changed.
- Existing PC focused regression for low-price sell/reduce/exit independence remains PASS.

## Remaining Gaps

No L21R3 implementation gap remains at focused-regression scope.

Remaining work is validation and later capital deployment policy design:

- user-operated fresh/long historical validation must measure aggregate REENTRY recovery and capital utilization impact;
- L21S still owns one-lot expression / capital deployment simplification;
- L21R3 does not force 80% utilization, change cash targets, change Safety caps, introduce one-lot fallback, or redistribute residual capital.

## L21S Readiness

`L21S_READY = YES`

Entry gate assessment:

- capacity authority resolves from real market data: YES;
- only missing market evidence remains UNKNOWN: YES;
- prior EXIT survives temporary EXCLUDE: YES;
- cooldown expiry does not delete prior EXIT awareness: YES;
- REENTRY classification persists until new campaign/current position: YES;
- BUY_NEW regression PASS: YES;
- BUY_ADD regression PASS: YES;
- SELL/REDUCE/EXIT regression PASS: YES.

Recommended next task:

`Phase29-L21S — Capital Deployment Simplification / One-Lot Expression Repair`

