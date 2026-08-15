# Phase29-L21T-BF — Valuation Contamination Scope / Trading-State Impact Audit

## Task

- Task ID: Phase29-L21T-BF
- Mode: READ-ONLY audit
- Target run: `runtime-test-historical-extended-smoke-20260814T131647480030Z`
- Phase: Phase29 continued; Phase30 not entered

No fresh-run, resume, replay, recovery, or target runtime mutation was performed.

## Primary Judgment

`VALUATION_CONTAMINATION_REACHES_CAPITAL_AUTHORITY_FULL_FRESH_RUN_REQUIRED`

The BE-confirmed valuation authority defect was not limited to `67310`. The target run consumed `PriceSource=adjusted` rows as Current valuation prices without explicit economic valuation reconciliation across 104 held symbols and 299 audited days. The first contaminated Current snapshot was already present on `2022-08-10`, and the contaminated Current equity was used as the next trading day's portfolio/capital authority input.

Because the contamination reaches sizing equity, position weights, exposure, and later BUY/SELL quantity authority, the target run is not resume-safe and is not usable as clean performance evidence after the contamination boundary. No counterfactual replay was executed, so exact quantity deltas are not proven; the defensible classification is `CAPITAL_AUTHORITY_CONTAMINATED`, not merely display-only.

## Method

I scanned all completed daily Current valuation manifests and, for each held position, reopened the referenced valuation source parquet to verify the source row's `PriceSource` and economic reconciliation evidence.

Outputs:

- `reports/phase29_l21t_bf_valuation_contamination_scope_trading_state_impact_audit/summary.json`
- `reports/phase29_l21t_bf_valuation_contamination_scope_trading_state_impact_audit/contamination_events.csv`
- `reports/phase29_l21t_bf_valuation_contamination_scope_trading_state_impact_audit/contaminated_symbols.csv`
- `reports/phase29_l21t_bf_valuation_contamination_scope_trading_state_impact_audit/trading_state_propagation.csv`
- `reports/phase29_l21t_bf_valuation_contamination_scope_trading_state_impact_audit/performance_evidence_validity.csv`
- `reports/phase29_l21t_bf_valuation_contamination_scope_trading_state_impact_audit/recovery_boundary.csv`

## Scope Findings

| Item | Result |
| --- | --- |
| Audited days | 300 |
| Position valuation rows scanned | 1,975 |
| Contaminated event rows | 1,969 |
| Contaminated days | 299 |
| Contaminated symbols | 104 |
| Earliest contamination date | `2022-08-10` |
| Earliest contaminated symbol | `23700` |
| First affected Current equity | `2022-08-10` total equity `995,860.0` |
| Estimated false PnL gross magnitude | `2,300,000.0` |
| Estimated false PnL net magnitude | `100,000.0` |
| Largest single false-PnL step | `100,000.0` |

The estimated false-PnL magnitude is deliberately conservative: it only counts suspicious large exact-step valuation transitions such as the `67310` `2000 <-> 3000` pattern. The broader defect is the unqualified adjusted-price consumption itself.

## 67310 vs Other Symbols

`67310` is the symbol with the confirmed repeating false PnL pattern:

- Contaminated days: 66
- First date: `2023-05-23`
- Last date: `2023-10-26`
- Suspicious step days: 23
- Gross estimated false PnL: `2,300,000.0`
- Net estimated false PnL: `100,000.0`
- Max single event: `100,000.0`

However, `67310_only = false`. Other symbols also consumed adjusted source rows without economic reconciliation. Examples at the first contamination boundary include `23700`, `23880`, `45710`, `66590`, `76470`, `89180`, `93180`, `94320`, and `94340` on `2022-08-10`.

`78780` had one contaminated valuation row on `2022-08-24`; `53800` was not found in contamination events.

## Trading-State Propagation

The first same-day contaminated valuation occurred on `2022-08-10`. That same day's strategy sizing used starting equity `1,000,000.0`, while the post-valuation Current snapshot became:

- cash: `745,820.0`
- buying_power: `745,820.0`
- market_value: `250,040.0`
- total_equity: `995,860.0`

On `2022-08-12`, the contaminated `995,860.0` appeared as `portfolio_total_equity` / `portfolio_value` in position sizing. That day also had positive quantity authority and fills:

- runtime plan count: 31
- positive quantity plan count: 12
- pending item count: 7
- fill count: 8
- BUY fills: 3
- SELL fills: 5
- EXIT fills: 4
- REDUCE fills: 1

Across days after the contamination boundary, the audit observed:

- BUY fill days: 145
- SELL fill days: 151
- EXIT fill days: 124
- REDUCE fill days: 45
- Runtime planning days with BUY_NEW semantics: 172
- Runtime planning days with ADD semantics: 286
- Runtime planning days with REDUCE semantics: 194
- Runtime planning days with EXIT semantics: 124

This proves contaminated equity reached capital authority and downstream trading authority. It does not prove an exact counterfactual quantity difference, because no replay was run. Therefore:

- BUY_NEW affected: `POSSIBLE_NOT_COUNTERFACTUALLY_PROVEN`
- ADD affected: `POSSIBLE_NOT_COUNTERFACTUALLY_PROVEN`
- REDUCE affected: `POSSIBLE_NOT_COUNTERFACTUALLY_PROVEN`
- EXIT affected: `POSSIBLE_NOT_COUNTERFACTUALLY_PROVEN`

## Performance Evidence Validity

| Evidence | Validity |
| --- | --- |
| Equity curve | `INVALID_AFTER_BOUNDARY` |
| Daily PnL | `INVALID_AFTER_BOUNDARY` |
| Final Return | `INVALID_AFTER_BOUNDARY` |
| Max Drawdown | `INVALID_AFTER_BOUNDARY` |
| Cash | `PARTIALLY_CONTAMINATED` |
| Exposure | `INVALID_AFTER_BOUNDARY` |
| Position count | `PARTIALLY_CONTAMINATED` |
| BUY_NEW count | `INVALID_AFTER_BOUNDARY` |
| ADD count | `INVALID_AFTER_BOUNDARY` |
| SELL count | `INVALID_AFTER_BOUNDARY` |
| Regime attribution | `INVALID_AFTER_BOUNDARY` |
| Entry forward return analysis | `PARTIALLY_CONTAMINATED` |
| Winner giveback analysis | `INVALID_AFTER_BOUNDARY` |

Entry forward-return analysis may still be partly useful as symbol/date market outcome evidence, but not as clean portfolio allocation or performance evidence from this run.

## Recovery / Validation Recommendation

`full 4-year fresh-run required`

Reason: earliest contamination is on `2022-08-10`, the first audited trading day. Since contaminated Current equity is used by capital authority from the next trading day onward, bounded recovery from a later point cannot produce trustworthy performance evidence for the target run.

The target run must not be resumed as performance evidence. After BE, validation should start with a short fresh validation if desired, then a full 4-year fresh-run from the original start date.

## Validation

- `summary.json` parse: PASS
- read-only trace consistency: PASS
- Runtime mutation: none
- Strategy mutation: none
- Fresh-run / resume / replay / recovery: not executed

`py_compile` and `git diff --check` are tracked with the final command validation for this task.
