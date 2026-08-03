# Phase25-A3R Capital Authority Conflict Review

## 1. Executive Summary

Phase25-A3R reviewed the capital authority conflict found by Phase25-A3. No Production code, Runtime code, Strategy code, schema, CLI, or config was changed.

Primary finding:

```text
Position Sizing and Dynamic Cash / Exposure are designed around current_total_equity.
Active Runtime Capital Deployment / Planning feasibility still enforce fixed initial-capital JPY caps.
```

This is not a confirmed Runtime crash defect. It is an unresolved design authority conflict that can block compound reinvestment once current equity grows enough for the dynamic target to exceed the fixed JPY cap.

## 2. Primary Judgment

```text
PHASE25_A3R_CAPITAL_AUTHORITY_CONFLICT_REVIEW_COMPLETE_DESIGN_REPAIR_REQUIRED
```

Additional judgments:

```text
Compound Reinvestment Design: PARTIAL
Fixed 1,000,000 Authority: MISNAMED
Fixed 850,000 Max Exposure: LEGACY_CAP
```

## 3. Scope and Method

Reviewed:

- Phase25-AA / A1 / A2 / A3 reports.
- Runtime Architecture v2.
- Strategy Architecture v1.
- Phase22 Dynamic Position Count, Dynamic Cash / Exposure, and Position Sizing reports.
- Phase24-HR exposure authority audit.
- Capital Deployment, Portfolio Policy, Position Sizing, Runtime Planning, Planning Submit Feasibility, Submit Guard, Current, Runtime-owned fill projection, and Safety limit code.
- Existing 2024-01-18 Daily Evaluation Evidence and Capital Efficiency Trace.

Allowed validation only was performed: `rg`, static code inspection, existing artifact inspection, static scenario calculation, JSON validation, and markdown/report creation.

## 4. Capital Field Inventory

| Field | Current Definition | Producer | Authority | Consumers | Dynamic / Fixed | Layer | Necessity | Conflict | Recommended Disposition |
|---|---|---|---|---|---|---|---|---|---|
| `initial_capital` | Starting capital for run/evaluation baseline | Run setup / evidence summary | Initialization authority | Performance return denominator, diagnostics | Fixed | INITIALIZATION | REQUIRED | None if kept separate | KEEP |
| `runtime_evaluation_capital` | Stored fixed 1,000,000 in Current/runtime state | Current bootstrap / projection metadata | Ambiguous; behaves as initial operating capital | Runtime-owned fill projection fallback, evidence, reports | Fixed | LEGACY / EVALUATION_ONLY | AMBIGUOUS | Conflicts with current_total_equity naming | RENAME |
| `current_total_equity` | Current cash + current market value | Current / valuation refresh / fill projection | Current portfolio authority | Performance, Strategy summaries, Position Sizing | Dynamic | CURRENT_PORTFOLIO_AUTHORITY | REQUIRED | Conflicts only if treated same as evaluation_capital | KEEP |
| `cash` | Current cash in Current SoT | Current / fill projection | Current portfolio authority | Planning budget, Dynamic Cash / Exposure, Performance | Dynamic | CURRENT_PORTFOLIO_AUTHORITY / BROKER_LIMIT | REQUIRED | None | KEEP |
| `buying_power` | Current deployable buying power | Current / broker or projection | Broker/current feasibility authority | Planning, Submit feasibility, Performance | Dynamic | BROKER_LIMIT | REQUIRED | None | KEEP |
| `market_value` | Sum of open Runtime-owned position market value | Current valuation | Current exposure authority | Planning feasibility, Performance, exposure | Dynamic | CURRENT_PORTFOLIO_AUTHORITY | REQUIRED | None | KEEP |
| `capital_deployment_evaluation_capital` | Policy `evaluation_capital=1,000,000` | `configs/runtime_v2/capital_deployment.json` | Active Capital Deployment Policy | Morning planning, ADD, Planning Submit Feasibility, Pending metadata | Fixed | CAPITAL_DEPLOYMENT | AMBIGUOUS | Conflicts with dynamic equity-based Strategy target | REDEFINE |
| `capital_deployment_max_exposure` | Policy `max_exposure=850,000` | `configs/runtime_v2/capital_deployment.json` | Active Runtime hard deployment cap | Morning planning, ADD, Planning Submit Feasibility | Fixed | CAPITAL_DEPLOYMENT / LEGACY | REQUIRED until migration | Conflicts with dynamic target at higher equity | REDEFINE |
| `target_gross_exposure_ratio` | Strategy target exposure ratio | Portfolio Policy / Dynamic Cash Exposure | Strategy target authority | Portfolio Construction, Position Sizing, Performance evidence | Dynamic | STRATEGY_TARGET | REQUIRED | Constrained downstream by fixed max_exposure | KEEP |
| `cash_reserve_ratio` | Strategy target cash reserve ratio | Portfolio Policy / Dynamic Cash Exposure | Strategy target authority | Portfolio Construction, Position Sizing, Performance evidence | Dynamic | STRATEGY_TARGET | REQUIRED | Distinct from operational cash buffer | KEEP |
| `position_sizing_capital_base` | `portfolio_total_equity` used for target notional | Position Sizing | Position Sizing quantity candidate authority | Runtime Planning / evidence | Dynamic | POSITION_SIZING | REQUIRED | Conflicts with fixed policy capital only downstream | KEEP |
| `aggregate_feasibility_capital_base` | Current cash/buying_power/exposure plus active policy caps | Planning Submit Feasibility | Planning feasibility authority | Pending approval eligibility | Mixed | PLANNING_FEASIBILITY | REQUIRED | Fixed cap can override dynamic target | DEFINE |
| `submit_capital_limit` | Final broker-bound feasibility from Pending/approval/source current | Submit Guard / Planning preflight evidence | Submit feasibility authority | Broker boundary | Mixed | SUBMIT_FEASIBILITY / BROKER_LIMIT | REQUIRED | Not fully materialized as one field | DEFINE |

Full inventory is mirrored in `reports/phase25_a3r_capital_authority_conflict_review/capital_field_inventory.md`.

## 5. Producer and Consumer Trace

Key trace:

```text
Current cash + market_value
  -> Dynamic Cash / Exposure portfolio_total_equity
  -> Portfolio Policy target_gross_exposure_ratio / cash_reserve_ratio
  -> Position Sizing target_notional = target_weight * portfolio_total_equity
  -> Runtime Planning planned quantity / no-order reason
  -> Planning Submit Feasibility active CapitalDeploymentPolicy
  -> Pending / Approval
  -> Submit Guard / Broker boundary
  -> Ledger / Current
```

Confirmed consumers:

| Consumer | Capital Input | Fallback / Default | Fixed Cap | Ratio Cap | Business-date Authority |
|---|---|---|---|---|---|
| Portfolio Policy | Current cash/exposure summaries, internal dynamic resolvers | No latest fallback; unresolved -> review/block | None in canonical artifact | Yes | `business_date` |
| Dynamic Cash / Exposure | `current_cash + current_market_value` | Missing source -> review/block | Explicitly marks legacy max exposure unused | Yes | `business_date` |
| Portfolio Construction | Portfolio Policy, Current, candidate/opportunity | Not audited as mutating cap | None observed | Uses target weights | `business_date` |
| Position Sizing | `portfolio_total_equity` | Missing/zero -> review | No JPY 850,000 cap | Yes, target weight and safety weight cap | `business_date` |
| Runtime Planning | Position Sizing quantity candidate | No recomputed target notional | Carries policy metadata | No target recompute | `business_date` |
| Planning Submit Feasibility | Current cash/buying_power/exposure + CapitalDeploymentPolicy | Missing cash/BP -> review | `max_exposure`, `evaluation_capital * max_position_weight`, `max_positions` | Indirect only | Current state at planning |
| Pending Promotion | Approved order plan items | No capital recompute | Carries policy context | No | Pending target session |
| Submit Preflight | Pending, approval, broker capability, lifecycle | No capital recompute in guard file; relies on approved Pending and final submit guards | Not direct here | No | Pending target session |
| Runtime-owned Fill Projection | `runtime_evaluation_capital or cash` for cash projection start | `runtime_evaluation_capital` before cash if present | Fixed initial capital can persist in projection semantics | No | current state / executions |
| Historical Safety | Safety decision and portfolio limits | Historical neutral safety context where explicitly materialized | Not 850,000 | Safety ratio 0.9 | business date |
| Current Projection | cash, buying_power, market_value, total_equity | no latest fallback; review on invalid projection | no exposure cap | no | current state |

## 6. Fallback Audit

| Fallback | Location / Evidence | Classification | Judgment |
|---|---|---|---|
| `runtime_evaluation_capital or cash` | `runtime_owned_fill_projection.py` | LEGACY_COMPATIBILITY | Acceptable as bootstrap/projection compatibility only; misleading if treated as current capital. |
| `cash / buying_power / capability.default_evaluation_capital` | `morning_pipeline._available_cash` | BOOTSTRAP_ONLY | Explicitly documented as initial operating fallback when Current lacks usable cash/BP. |
| `config evaluation_capital=1_000_000` | `capital_deployment.json` | LEGACY_COMPATIBILITY | Active policy authority today, but not aligned with dynamic equity target. |
| `default max_exposure=850_000` | `capital_deployment.json` | LEGACY_COMPATIBILITY | Active hard deployment cap today; legacy relative to Phase22 dynamic design. |
| `total_equity or evaluation_capital` | A3 evidence question | AMBIGUOUS | No single current consumer should silently substitute these as equivalent. |

## 7. Capital Layer Classification

| Constraint | Layer | Classification |
|---|---|---|
| `initial_capital` | INITIALIZATION | Valid baseline. |
| `current_total_equity` | CURRENT_PORTFOLIO_AUTHORITY | Dynamic current SoT. |
| `target_gross_exposure_ratio` | STRATEGY_TARGET | Dynamic Strategy target. |
| `cash_reserve_ratio` | STRATEGY_TARGET | Dynamic Strategy target. |
| `position_sizing_capital_base` | POSITION_SIZING | Dynamic equity base. |
| `capital_deployment_evaluation_capital` | CAPITAL_DEPLOYMENT / LEGACY | Fixed active deployment base. |
| `capital_deployment_max_exposure=850000` | CAPITAL_DEPLOYMENT / LEGACY | Active hard deployment cap, not Safety hard cap. |
| `planning_submit_feasibility` | PLANNING_FEASIBILITY | Uses Current plus active policy. |
| Submit preflight | SUBMIT_FEASIBILITY / BROKER_LIMIT | Final boundary, no Strategy recompute. |
| `portfolio_limits.cash_exposure.maximum_gross_exposure_ratio=0.9` | SAFETY_HARD_CAP | Independent Safety cap. |

## 8. runtime_evaluation_capital Judgment

`runtime_evaluation_capital` is not Current Capital. It currently behaves as fixed initial operating/evaluation capital and legacy projection compatibility.

Answers:

1. It is closer to Initial Capital than Current Capital.
2. It should not need daily Current storage as a changing capital authority.
3. It should not be the primary Cash Projection base once Current cash exists.
4. If retained, it should be renamed or redefined as `initial_evaluation_capital` / `bootstrap_evaluation_capital`.

Judgment:

```text
MISNAMED
```

## 9. capital_deployment_evaluation_capital Judgment

`capital_deployment_evaluation_capital=1,000,000` currently limits:

- target planning budget via `evaluation_capital * target_investment_ratio`;
- operational cash buffer via `evaluation_capital * cash_buffer`;
- per-position cap via `evaluation_capital * max_position_weight`;
- policy validity with `max_exposure <= evaluation_capital`.

This is an active Capital Deployment input, not evaluation-only. Its correct future role should be split into initial baseline, active deployment capital, and independent safety limits.

Judgment:

```text
AMBIGUOUS_ACTIVE_LEGACY_POLICY
```

## 10. max_exposure Judgment

`max_exposure=850,000` is currently an active Runtime hard deployment cap under Capital Deployment Policy and Planning Submit Feasibility. Phase24-HR confirmed it as an expected valid guard.

It is not the independent Safety hard maximum. Safety hard maximum is defined separately as `maximum_gross_exposure_ratio=0.9` in `configs/safety/portfolio_limits.json`.

Judgment:

```text
LEGACY_CAP
```

## 11. Compound Reinvestment Design Judgment

```text
COMPOUND_REINVESTMENT_DESIGN_PARTIAL
```

Confirmed:

- Sizing layer uses current equity: target notional is based on `portfolio_total_equity`.
- Dynamic Cash / Exposure computes equity as `current_cash + current_market_value`.

Not confirmed:

- Planning and Submit feasibility still enforce fixed `max_exposure=850,000`.
- Morning legacy planning budget still uses `evaluation_capital * target_investment_ratio`.
- ADD consumer uses `evaluation_capital * max_position_weight` and fixed max exposure.

Therefore compound reinvestment is supported at the Strategy sizing layer but not fully established across Planning/Submit authority.

## 12. Scenario Analysis

Assumptions:

```text
fixed max_exposure = 850,000
available headroom = min(dynamic target headroom, fixed max exposure headroom)
reinvestment blocked amount = dynamic target headroom - available headroom
```

| Scenario | Total Equity | Target Exposure | Market Value | Dynamic Target Amount | Fixed Max Exposure | Dynamic Headroom | Fixed Headroom | Binding Constraint | Reinvestment Blocked |
|---|---:|---:|---:|---:|---:|---:|---:|---|---:|
| A | 1,000,000 | 79% | 0 | 790,000 | 850,000 | 790,000 | 850,000 | Dynamic target | 0 |
| B | 1,067,660 | 79% | 679,650 | 843,451.40 | 850,000 | 163,801.40 | 170,350 | Dynamic target | 0 |
| C | 1,200,000 | 90% | 850,000 | 1,080,000 | 850,000 | 230,000 | 0 | Fixed max exposure | 230,000 |
| D | 1,500,000 | 90% | 850,000 | 1,350,000 | 850,000 | 500,000 | 0 | Fixed max exposure | 500,000 |

The fixed cap does not bind in the inspected 2024-01-18 case, but it blocks reinvestment once market value reaches 850,000 while dynamic target exposure is higher.

## 13. Safety Relationship

Removing or changing the fixed 850,000 cap without a replacement contract would be unsafe. However, the current Safety hard maximum already exists independently:

```text
minimum_cash_ratio = 0.10
maximum_gross_exposure_ratio = 0.90
maximum_position_weight = 0.25
```

The correct separation is:

- Strategy desired exposure: ratio × current_total_equity.
- Capital Deployment operational cap: active deployable capital policy.
- Safety hard maximum: independent ratio or emergency cap, not copied from legacy 850,000.
- Broker feasibility: cash / buying_power / broker availability.
- Concentration: independent single-name Safety cap plus Strategy sizing cap.
- Position count: Strategy target and explicit policy, not hidden fixed Runtime count.

## 14. Options Considered

| Option | Summary | Production Correctness | Compound Reinvestment | Safety Preservation | Compatibility | Migration Risk | Regression Risk | Observability |
|---|---|---|---|---|---|---|---|---|
| A | Keep current fixed 1M / 850k | Works with current Runtime | Partial / blocked at higher equity | Preserved but legacy conflated | High | Low | Low | Medium |
| B | Set `runtime_evaluation_capital=current_total_equity` | Naming improves but conflates fields | Better | Risky if used as initial baseline | Medium | Medium | Medium | Medium |
| C | Separate `initial_capital`, `current_total_equity`, `active_deployment_capital` | Strong | Strong | Strong if safety independent | Medium | Medium | Medium | High |
| D | Dynamic Strategy + independent Safety Cap | Strong | Strong | Strong | Medium | Medium-high | High | High |
| E | Other: keep 850k as named operator capital ceiling | Correct only if intentional capital lock | Not full compound | Strong | High | Low | Low | Medium |

## 15. Recommended Design

Recommended:

```text
Option C followed by Option D migration
```

Design:

```text
initial_capital = immutable run/account baseline
current_total_equity = Current SoT cash + market value
active_deployment_capital = explicit operator/strategy deployment base
strategy_target_exposure_amount = target_gross_exposure_ratio * current_total_equity
safety_max_exposure_amount = safety maximum_gross_exposure_ratio * current_total_equity, or explicit operator hard cap when approved
planning/submit limit = min(strategy target headroom, active deployment headroom, safety headroom, cash, buying_power, broker constraints)
```

`max_exposure=850,000` should not be silently removed. It should either be reclassified as an explicitly named operator hard deployment ceiling or migrated to a dynamic formula with an independent Safety cap remaining in force.

## 16. Required Migration

Design repair task before implementation:

1. Rename/redefine `runtime_evaluation_capital` as non-current baseline authority.
2. Define `active_deployment_capital` and whether it is dynamic or operator-fixed.
3. Define `max_exposure` semantics: operator hard cap vs dynamic deployment cap vs legacy compatibility.
4. Update Capital Deployment Contract without changing Strategy behavior.
5. Add evidence fields for active deployment cap, safety cap amount, strategy target amount, and binding cap.
6. Implement only after regression scope is approved.

## 17. Required Regression Scope

Minimum regression before any implementation:

- Capital Deployment policy loader and manifest hash tests.
- Morning planning budget tests.
- ADD consumer capacity tests.
- Planning Submit Feasibility aggregate reservation tests.
- Submit Guard / Pending approval boundary tests.
- Safety portfolio limits tests.
- Current / fill projection tests for cash and total equity.
- Historical/Demo/Production mode compatibility tests.
- Phase24-HR exposure-block reproduction as a non-regression expectation under old policy or migrated explicit policy.

No long Historical Test should be run by Codex.

## 18. Blocking Gaps

No blocking gap for completing this review.

## 19. Non-Blocking Gaps

- `active_deployment_capital` is not yet a formal field.
- Submit capital limit is not materialized as one canonical numeric field.
- Same-day SELL crediting remains explicitly not allowed unless future contract changes it.
- The current A3 sample has no BUY/ADD after profit, so execution-level compound reinvestment confirmation remains unavailable.

## 20. Recommended Next Task

```text
Phase25-A3R-D1 Capital Authority Design Repair Contract
```

The next task should be design-only and user-approved before implementation. It should decide the new capital field names, active deployment formula, fixed cap migration policy, and regression gate.

