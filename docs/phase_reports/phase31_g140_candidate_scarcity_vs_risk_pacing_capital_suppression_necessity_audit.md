# Phase31-G140 - Candidate Scarcity vs Risk Pacing Capital Suppression Necessity Audit

## Final Decision

`G140_RISK_PACING_INDEPENDENT_VALUE_CONFIRMED_PHASE31_RE_CLOSE_READY`

Phase31 was temporarily reopened only for this narrow READ-ONLY audit. The
audit does not invalidate G139 globally and does not enter Phase32.

The hypothesis that Candidate / Opportunity scarcity alone naturally creates
enough weak-market de-risking is not supported by the target run artifacts.
Candidate count remains fixed at 50, BUY-admissible evidence remains material
across regimes, and BEAR / CORRECTION days often retain valid security demand.
Risk Pacing / MCC therefore has independent architecture value as
portfolio-level participation and optional-Cash authority.

Some overlap exists because weak markets can simultaneously reduce candidate
quality and raise portfolio-level risk. That correlation is expected and is not
by itself a defect. The audit found a small observability follow-up surface
around zero-security allocation days with plentiful candidates, but did not
prove redundant or excessive second-order suppression requiring G141 repair.

## Phase Status

```text
PHASE31_TEMPORARILY_REOPENED_FOR_FINAL_RISK_PACING_NECESSITY_AUDIT = YES
G139_GLOBAL_CLOSURE_INVALIDATED = NO
PHASE32_ENTERED = NO
```

Reopened scope was limited to:

```text
ARCHITECTURE NECESSITY /
REDUNDANT RISK SUPPRESSION /
AUTHORITY INTERACTION AUDIT
```

Not reopened:

- High-Resolution Marginal Value implementation;
- Portfolio Rotation;
- BULL performance tuning;
- general Strategy optimization.

## Scope

Task type: READ-ONLY audit.

Primary run:

```text
runtime-test-historical-extended-smoke-20260825T235520054579Z
```

Completed immutable artifacts audited at G140 inspection time:

```text
completed_dates = 225
first_completed_date = 2022-10-03
latest_completed_date = 2023-08-30
```

The run was not resumed, replayed, stopped, or mutated.

## Source Basis

Read and used:

- `docs/phase_reports/phase31_g139_phase31_final_closure_performance_improvement_completion.md`
- `docs/phase_reports/phase31_final_summary_and_phase32_handoff.md`
- `docs/phase_reports/phase31_g138_march_april_profit_formation_strategy_causality_audit.md`
- `docs/phase_reports/phase31_g137_high_resolution_capital_value_architecture_ambiguity_hardening.md`
- `docs/phase_reports/phase31_g136_high_resolution_capital_value_rotation_permanent_architecture_sot_materialization.md`
- `docs/02_architecture/dual_path_market_quality_and_capital_competition_contract.md`
- `docs/02_architecture/portfolio_construction_and_position_sizing_contract.md`
- relevant current Strategy / Runtime architecture SoT under
  `docs/02_architecture/`.

Implementation / artifact authorities inspected read-only:

- Candidate / BUY Quality: `strategy/buy_quality_decisions.json`
- Market Quality / regime: `strategy/market_context.json`
- Risk Pacing / budget: `strategy/portfolio_policy.json`
- Market-Candidate-Cash / PC: `strategy/portfolio_construction.json`
- G61 / PS consumption: `strategy/position_sizing.json`
- Runtime / Pending generation: `morning/planning_evidence.json`
- valuation / exposure: `current_valuation_refresh/valuation_projection.json`

## Design Responsibility Map

Design responsibilities remain distinct:

| Layer | Intended question | Observed authority evidence |
| --- | --- | --- |
| Candidate / Strategy Intelligence | Which securities are valid / attractive opportunities? | fixed top-50, BUY Quality action distribution, rank / score / entry evidence |
| Market Quality / Regime | What is the market environment? | `regime_state`, `market_quality_state`, PIT market component evidence |
| Risk Pacing | How much portfolio capital may prudently participate? | `risk_pacing_intent`, `incremental_capital_budget_envelope` |
| MCC / Capital Competition | Given market, opportunity, and Cash, how should marginal capital participate? | `market_candidate_cash_interaction`, Cash preference, security deferrals |
| PC | Where should allowed capital be allocated? | `canonical_multi_allocation_deployment_set.security_allocations` |
| PS | What discrete quantity is executable? | G61 compatibility consumption and quantity rows |
| Runtime | Consume executable plans, preserve lineage, write Pending | morning planning / pending generation evidence |

Design conclusion:

```text
DESIGN_RESPONSIBILITIES_DISTINCT = YES
```

Actual economic effects are partially overlapping but not reducible to one
signal:

```text
ACTUAL_ECONOMIC_EFFECT_DISTINCT = YES
```

## Candidate Scarcity by Regime

The closest authoritative contemporaneous candidate-side evidence is BUY
Quality plus upstream Candidate / Opportunity summaries. Candidate capacity is
fixed-width, so true raw-universe scarcity cannot be inferred from candidate
count alone.

| Regime | Days | Avg candidate count | Avg eligible count | Avg high-quality count | Avg BUY-admissible count | Avg NEW opportunity count | Avg ADD opportunity count |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| BEAR | 28 | 50.0 | 50.0 | 3.36 | 32.25 | 25.11 | 0.36 |
| BULL | 93 | 50.0 | 50.0 | 4.73 | 30.84 | 21.01 | 0.66 |
| CORRECTION | 15 | 50.0 | 50.0 | 5.13 | 30.20 | 23.93 | 0.27 |
| RANGE | 45 | 50.0 | 50.0 | 4.67 | 30.87 | 22.53 | 0.56 |
| RECOVERY | 44 | 50.0 | 50.0 | 3.98 | 30.16 | 20.68 | 0.41 |

Interpretation:

- Candidate count and eligible count are not strongly regime-dependent in this
  artifact family.
- BUY-admissible count remains around 30 across regimes.
- BEAR does not naturally collapse opportunity supply; in this run BEAR has
  slightly higher average BUY-admissible count and NEW opportunity count than
  BULL.
- High-quality count varies, but not enough to prove scarcity-driven Cash as
  the dominant weak-market control.

```text
CANDIDATE_SCARCITY_STRONGLY_REGIME_DEPENDENT = NO
```

## Pre-Pacing vs Post-Pacing Capital Demand

Evidence definition:

- `AVG_PRE_PACING_DEMAND` is reconstructed from requested allocation weight in
  `security_allocations + cash_preferred_security_deferrals` where available.
  This is a structural same-artifact demand proxy, not a simulated portfolio
  without Risk Pacing.
- `AVG_POST_PACING_DEMAND` is final authorized security allocation weight.
- `AVG_CASH_ALLOC` is explicit authorized Cash allocation in the multi-allocation
  deployment set.

| Regime | Avg pre-pacing demand | Avg post-pacing demand | Avg budget | Avg Cash allocation | Avg Cash | Avg exposure | Avg position count |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| BEAR | 0.388 | 0.190 | 0.310 | 0.120 | 501,006 | 56.46% | 9.18 |
| BULL | 0.292 | 0.186 | 0.340 | 0.154 | 329,127 | 78.27% | 11.24 |
| CORRECTION | 0.271 | 0.125 | 0.250 | 0.125 | 489,355 | 70.15% | 10.33 |
| RANGE | 0.380 | 0.176 | 0.349 | 0.173 | 296,779 | 79.07% | 10.62 |
| RECOVERY | 0.309 | 0.145 | 0.339 | 0.195 | 330,231 | 78.61% | 11.66 |

The weak-market pattern is not "no candidate demand." BEAR and RANGE both show
material pre-pacing security demand. Post-pacing security allocation is lower,
while Cash is explicitly retained.

```text
CANDIDATE_SCARCITY_ALONE_OFTEN_LIMITS_DEPLOYMENT = NO
STRUCTURAL_NO_PACING_DEMAND_ASSESSMENT = PARTIAL
```

## Risk Pacing Incremental Effect

Material suppression shape:

```text
pre_demand - post_demand > 0.05
and cash_preferred_security_deferrals > 0
```

Observed:

| Metric | Count |
| --- | ---: |
| Risk Pacing / MCC material suppression days | 167 |
| Independent risk-value shaped days | 155 |
| Effectively redundant shaped days | 0 |
| Potentially over-suppressive shaped days | 4 |
| Partial / mixed shaped days | 8 |

The dominant pattern is not redundancy. Most material suppression days still
had plentiful candidate-side demand and non-zero security participation while
explicitly retaining Cash. This is consistent with independent portfolio-risk
authority: securities can remain valid while total participation is paced down.

```text
RISK_PACING_HAS_MATERIAL_INCREMENTAL_EFFECT = YES
RISK_PACING_EFFECT_CLASSIFICATION = INDEPENDENT
```

## Multi-Layer Market Weakness Consumption

Market weakness is consumed in multiple layers:

| Layer | Input evidence | Semantic purpose | Output effect | Capital effect |
| --- | --- | --- | --- | --- |
| BUY Quality | candidate / opportunity / entry evidence plus market context | security-level admission / quality | `FULL_ALLOCATION_ELIGIBLE`, `REDUCED_ALLOCATION_ONLY`, `BUY_WAIT`, `REJECT` | affects candidate-side opportunity quality |
| Market Context | PIT market direction, breadth, volatility, confidence | market environment and Market Quality | `regime_state`, `market_quality_state` | no direct quantity or exposure |
| Portfolio Policy / Risk Pacing | Market Quality plus portfolio state and policy constraints | deployment-intensity authority | `risk_pacing_intent`, budget envelope | caps / paces incremental capital |
| MCC | candidate quality + market/cash semantics | security/Cash partition | `CASH_PREFERRED`, `DEPLOY_ELIGIBLE`, deferrals | allocates part of marginal capital to Cash |
| PC final allocation | capital competition + constraints | allocation owner | security allocation rows | final target allocation to securities |

This is multi-layer consumption, but the observed design purposes are distinct.
No evidence was found that Candidate eligibility or rank was mutated by Risk
Pacing:

```text
market_quality_hard_buy_gate_created = 0
candidate_eligibility_mutation_count = 0
candidate_rank_mutation_count = 0
```

Therefore:

```text
MARKET_WEAKNESS_MULTI_LAYER_CONSUMPTION = YES
REDUNDANT_MARKET_WEAKNESS_MULTIPLICATION = NO
```

## Representative BEAR Traces

| Date | Regime | MQ | Risk Pacing | Candidate / eligible | Full / reduced | NEW / ADD opp | Pre / post / Cash allocation | Cash | Exposure | Positions | Primary low-exposure cause |
| --- | --- | --- | --- | ---: | ---: | ---: | --- | ---: | ---: | ---: | --- |
| 2022-12-20 | BEAR | SHORT_TERM_BREADTH_BREAKDOWN | CAUTIOUS_DEPLOYMENT | 50 / 50 | 3 / 25 | 23 / 0 | 0.569 / 0.375 / 0.172 | 872,980 | 19.1% | 4 | MULTI_CAUSAL: PM SELL exits + cautious Cash retention + still-positive security deployment |
| 2023-01-13 | BEAR | CONFLICTED_MARKET_STRUCTURE | CAUTIOUS_DEPLOYMENT | 50 / 47 | 3 / 28 | 23 / 0 | 0.492 / 0.208 / 0.256 | 748,890 | 32.5% | 8 | MULTI_CAUSAL: PM SELL exits + MCC Cash preference + security participation |
| 2023-04-05 | BEAR | SHORT_TERM_BREADTH_BREAKDOWN | CAUTIOUS_DEPLOYMENT | 50 / 47 | 2 / 25 | 19 / 1 | 0.171 / 0.034 / 0.130 | 687,160 | 59.6% | 4 | RISK_PACING / MCC + PM de-risking; not candidate scarcity |
| 2023-04-06 | BEAR | SHORT_TERM_BREADTH_BREAKDOWN | CAUTIOUS_DEPLOYMENT | 50 / 47 | 4 / 25 | 24 / 1 | 0.402 / 0.250 / 0.078 | 907,760 | 48.9% | 5 | MULTI_CAUSAL: cautious Cash retention plus selected security deployment |
| 2023-04-07 | BEAR | SHORT_TERM_BREADTH_BREAKDOWN | CAUTIOUS_DEPLOYMENT | 50 / 48 | 3 / 23 | 19 / 0 | 0.337 / 0.199 / 0.079 | 560,760 | 66.9% | 6 | MCC / Cash preference with continued participation |

These BEAR traces directly refute a pure candidate-scarcity explanation. Even
when exposure was low, candidate-side evidence often remained plentiful.

## BULL Structural Comparison

| Regime | Avg BUY-admissible | Avg pre demand | Avg post demand | Avg Cash | Avg exposure |
| --- | ---: | ---: | ---: | ---: | ---: |
| BEAR | 32.25 | 0.388 | 0.190 | 501,006 | 56.46% |
| BULL | 30.84 | 0.292 | 0.186 | 329,127 | 78.27% |

BULL has higher exposure, but not because it has clearly more candidate supply
in this evidence family. BULL's higher exposure is better explained by prior
portfolio state, realized position retention, less persistent PM de-risking,
and capital pacing context. Opportunity supply contributes, but it is not the
primary distinguishing metric in this artifact set.

```text
BULL_HIGHER_EXPOSURE_PRIMARILY_FROM_OPPORTUNITY_SUPPLY = NO
BULL_HIGHER_EXPOSURE_PRIMARILY_FROM_PACING = PARTIAL
```

## Cash Formation Analysis

Weak-market Cash formation is multi-causal:

- PM REDUCE / EXIT creates cash on representative BEAR days.
- Candidate scarcity is not the dominant cause because candidate and
  BUY-admissible counts remain material.
- Risk Pacing / MCC explicitly retains Cash via `OPTIONALITY_ELEVATED`,
  `CASH_PREFERRED`, and Cash allocation rows.
- Lot / cap / residual constraints also contribute but are not the primary
  explanatory surface in the sampled BEAR days.

```text
WEAK_MARKET_CASH_IS_PRIMARILY_NATURAL_SCARCITY = NO
WEAK_MARKET_CASH_IS_PRIMARILY_EXPLICIT_RISK_SUPPRESSION = PARTIAL
```

The better conclusion is:

```text
WEAK_MARKET_CASH_FORMATION = MULTI_CAUSAL
```

## Independent Portfolio-Risk Evidence

Risk Pacing preserves Cash when candidate supply remains strong and Market
Quality is weak or conflicted. Representative examples:

- `2022-12-20`: 50 candidates, 28 full/reduced rows, 23 NEW opportunities,
  BEAR / breadth breakdown, 0.172 Cash allocation, 4 security allocations.
- `2023-01-13`: 47 eligible opportunities, 31 full/reduced rows, BEAR /
  conflicted, 0.256 Cash allocation, 2 security allocations.
- `2023-04-06`: 47 eligible opportunities, 29 full/reduced rows, BEAR /
  breadth breakdown, 0.078 Cash allocation, 2 security allocations.

These are decision-time portfolio-risk decisions, not later-return
justifications.

```text
INDEPENDENT_PORTFOLIO_RISK_INFORMATION_EXISTS = YES
VALID_OPPORTUNITIES_SUPPRESSED_BY_PACING = YES
SUPPRESSION_SEMANTIC = INTENDED
```

## Redundancy / Double-De-Risking Assessment

Four days had the strongest potentially over-suppressive shape:

| Date | Regime | MQ | Risk Pacing | Eligible | Full / reduced | Pre demand | Post demand | Deferrals | Exposure |
| --- | --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 2022-10-06 | RANGE | CONFLICTED_MARKET_STRUCTURE | CAUTIOUS_DEPLOYMENT | 47 | 5 / 27 | 0.523 | 0.000 | 15 | 92.5% |
| 2022-10-17 | BEAR | SHORT_TERM_BREADTH_BREAKDOWN | CAUTIOUS_DEPLOYMENT | 46 | 4 / 29 | 0.357 | 0.000 | 6 | 55.3% |
| 2023-05-01 | RECOVERY | RECOVERY_CONFIRMATION_INCOMPLETE | GRADUAL_REDEPLOYMENT | 47 | 2 / 24 | 0.310 | 0.000 | 5 | 73.1% |
| 2023-07-18 | CORRECTION | CONFLICTED_MARKET_STRUCTURE | CAUTIOUS_DEPLOYMENT | 45 | 2 / 25 | 0.446 | 0.000 | 10 | 75.8% |

These days are worth future observability, but they are not sufficient to
prove a mandatory defect:

- the count is small relative to 225 completed days;
- several have already-high exposure where zero incremental deployment can be
  reasonable;
- the audit did not establish that the same economic risk was counted twice
  without distinct authority purpose;
- no return outcome was used to judge them.

```text
BURDEN_OF_PROOF_FOR_CHANGE_MET = NO
DEFECT_CLASS = NO_DEFECT
MANDATORY_OR_CLEAR_ARCHITECTURAL_DEFECT = NO
```

## Repair Necessity

No G141 repair is required.

Allowed future work:

- add observability that explicitly reports scarcity-driven Cash vs
  risk-budget-driven Cash;
- expose pre-demand / post-demand / deferral summaries in a compact daily
  diagnostic;
- continue treating Cash as first-class without changing Strategy behavior.

Not allowed from this audit alone:

- removing Risk Pacing;
- forcing higher BEAR exposure;
- changing Market Quality thresholds;
- changing Candidate thresholds;
- changing MCC behavior;
- optimizing based on Historical return.

## Phase31 Re-Closure Recommendation

```text
PHASE31_REQUIRES_FINAL_G141_REPAIR = NO
PHASE31_CAN_RE_CLOSE_WITHOUT_REPAIR = YES
```

G139 remains valid after this narrow reopening. Phase31 can be re-closed on the
current Strategy baseline, and Phase32 should not be entered by G140 itself.

## Required Final Judgments

DESIGN_RESPONSIBILITIES_DISTINCT = `YES`

ACTUAL_ECONOMIC_EFFECT_DISTINCT = `YES`

CANDIDATE_SCARCITY_STRONGLY_REGIME_DEPENDENT = `NO`

CANDIDATE_SCARCITY_ALONE_OFTEN_LIMITS_DEPLOYMENT = `NO`

RISK_PACING_HAS_MATERIAL_INCREMENTAL_EFFECT = `YES`

RISK_PACING_EFFECT_CLASSIFICATION = `INDEPENDENT`

MARKET_WEAKNESS_MULTI_LAYER_CONSUMPTION = `YES`

REDUNDANT_MARKET_WEAKNESS_MULTIPLICATION = `NO`

INDEPENDENT_PORTFOLIO_RISK_INFORMATION_EXISTS = `YES`

VALID_OPPORTUNITIES_SUPPRESSED_BY_PACING = `YES`

SUPPRESSION_SEMANTIC = `INTENDED`

WEAK_MARKET_CASH_IS_PRIMARILY_NATURAL_SCARCITY = `NO`

WEAK_MARKET_CASH_IS_PRIMARILY_EXPLICIT_RISK_SUPPRESSION = `PARTIAL`

RISK_PACING_ARCHITECTURALLY_NECESSARY = `YES`

BURDEN_OF_PROOF_FOR_CHANGE_MET = `NO`

DEFECT_CLASS = `NO_DEFECT`

MANDATORY_OR_CLEAR_ARCHITECTURAL_DEFECT = `NO`

REPAIR_REQUIRED = `NO`

PHASE31_REQUIRES_FINAL_G141_REPAIR = `NO`

PHASE31_CAN_RE_CLOSE_WITHOUT_REPAIR = `YES`

FUTURE_INFORMATION_USED_FOR_JUDGMENT = `NO`

HISTORICAL_RETURN_USED_FOR_TUNING = `NO`

CODE_CHANGED = `NO`

RUN_MODIFIED = `NO`

PHASE32_ENTERED = `NO`

FRESH_RUN_EXECUTED = `NO`

RESUME_EXECUTED = `NO`

REPLAY_EXECUTED = `NO`

LONG_HISTORICAL_EXECUTED = `NO`

GIT_DIFF_CHECK = `PASS`

## Evidence Limitations

- Candidate count is fixed top-50 capacity; raw universe scarcity is not
  directly measured by this count.
- Pre-pacing demand is reconstructed from same-artifact requested allocation
  and deferral rows. It is not a full no-Risk-Pacing simulation.
- The audit intentionally avoids hypothetical PnL and return counterfactuals.
- The four zero-post-demand days are observability candidates, not proven
  defects.

## G141 Scope

Not applicable. No G141 repair contract is required.

