# Phase32-ES — REENTRY Functional Necessity & Minimal Churn-Protection Boundary Audit

## Scope

- Target run: `runtime-test-historical-extended-smoke-20260902T060955933565Z`
- Evidence inspected read-only through available `2024-12-20` artifacts.
- Prior basis: Phase32-ER proved run-age dependent unbounded prior-exit / REENTRY history penalty.
- This task performs READ-ONLY / SHADOW analysis only.

No Production source/config/schema, threshold, weight, runtime state, Pending, Ledger, fresh-run, resume, replay, or long Historical was changed or executed.

Future price, return, MFE/MAE, campaign outcome, later SELL result, or Historical PnL was not used for Production judgment.

## References

- `docs/phase_reports/phase32_er_long_lived_historical_penalty_security_level_bias_exhaustive_read_only_audit.md`
- `docs/phase_reports/phase32_eq_long_run_state_history_accumulation_dependency_capital_suppression_root_cause_audit.md`
- `docs/phase_reports/phase32_cm_reentry_zero_fill_requalification_suppression_root_cause_read_only_audit.md`
- `docs/phase_reports/phase32_cp_reentry_temporal_lifecycle_prior_campaign_relevance_read_only_audit.md`
- `docs/phase_reports/phase32_cq_reentry_time_renewed_pit_new_equivalent_lifecycle_shadow_contract_design.md`
- `docs/phase_reports/phase32_cw_minimal_residual_reentry_unknown_context_production_repair.md`
- `src/ai_fund_lab_v2/strategy/portfolio_construction.py`
- `src/ai_fund_lab_v2/strategy/position_management.py`
- `src/ai_fund_lab_v2/strategy/marginal_capital_value.py`
- `src/ai_fund_lab_v2/strategy/shadow_runtime.py`

## Executive Judgment

REENTRY has two different roles that must be separated:

1. Permanent lineage / auditability: useful and should remain.
2. Permanent security-level decision penalty: not justified by current evidence.

The only clearly necessary independent protection is short-term churn prevention after an EXIT. Long-term REENTRY recovery logic is mostly redundant with existing current PIT controls or becomes a historical ownership penalty. A bounded `RECENT_EXIT_CHURN_GUARD` concept is architecturally feasible and better aligned with the investment philosophy that a symbol should not remain disadvantaged merely because it was once owned.

Recommended next design direction: `B. REENTRY semantic縮小 + recent-exit churn guardのみ`.

## 1. REENTRY Gate Functional Decomposition

Materialized REENTRY-block observations were extracted from recursive PC artifacts and normalized at the `business_date + symbol` level. The resulting population contains repeated daily observations; it is appropriate for gate-rate analysis, while prior Phase CM remains the cleaner episode-level reference.

| Classification | Count | Rate | Meaning |
|---|---:|---:|---|
| `REENTRY_ONLY_PROTECTION` | 460 | 3.03% | REENTRY cooldown/churn blocks a row that did not show another current PIT block in the extracted fields. |
| `ALREADY_BLOCKED_BY_CURRENT_EVIDENCE` | 4059 | 26.74% | Current BQ/Entry/trend/momentum/continuation/downside/CA/liquidity evidence already blocks or reviews it. |
| `PARTIALLY_REDUNDANT` | 5572 | 36.71% | REENTRY reason exists, but current PIT weakness also exists. |
| `HISTORICAL_ONLY_PENALTY` | 5087 | 33.51% | No extracted current PIT block; suppression is driven by prior EXIT context, unknown context, hard-stop new-thesis, or repeated-churn history. |
| Total | 15178 | 100.00% | Daily materialized REENTRY-block observations. |

`CURRENT_CONTROLS_ALREADY_COVER_MAJORITY = YES`

`ALREADY_BLOCKED_BY_CURRENT_EVIDENCE + PARTIALLY_REDUNDANT = 9631 / 15178 = 63.45%`.

Interpretation:

- Most rejected REENTRY rows would still be naturally controlled or at least materially questioned by current PIT controls.
- The real unique value of REENTRY is the short-term churn subset.
- The large `HISTORICAL_ONLY_PENALTY` subset is not explained by current PIT weakness and is the capital-suppression concern identified by ER/EQ.

## 2. Short-Term Churn Reality

Age-bucket analysis:

| days since EXIT | observations | BQ positive | Entry block | trend block | momentum block | REENTRY suppression | would pass extracted current controls | REENTRY-only protection |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| `1-2BD` | 1056 | 1046 | 97 | 523 | 230 | 1056 | 402 | 301 |
| `3-5BD` | 1191 | 1182 | 91 | 722 | 340 | 1191 | 344 | 0 |
| `6-10BD` | 1441 | 1426 | 102 | 857 | 474 | 1441 | 433 | 0 |
| `11-20BD` | 1425 | 1403 | 107 | 723 | 512 | 1425 | 495 | 0 |
| `21-60BD` | 2445 | 2372 | 195 | 1185 | 983 | 2445 | 912 | 0 |
| `61BD+` | 7044 | 6813 | 570 | 3418 | 2371 | 7044 | 2725 | 0 |
| unknown age | 576 | 560 | 57 | 270 | 119 | 576 | 236 | 159 |

Observations:

- Immediate post-EXIT churn risk is real. In the `1-2BD` bucket, 301 observations were REENTRY-only blocks and 402 had no extracted current PIT blocker.
- After the immediate bucket, current technical weakness is common, especially trend/momentum weakness. That means many cases do not need a separate long-lived historical penalty.
- The `61BD+` bucket has 2725 rows that would pass extracted current controls but remained REENTRY-blocked. That is not credible as simple short-term churn protection.

`TRUE_SHORT_TERM_CHURN_RISK_EXISTS = YES`

## 3. Controls That Remain Without Long-Term REENTRY Penalty

Even if the long-lived REENTRY penalty were removed or reduced, these current Production controls would remain:

| Architecture area | Current control |
|---|---|
| Candidate quality | rank / score / eligibility evidence |
| Buy Quality | `FULL_ALLOCATION_ELIGIBLE`, `REDUCED_ALLOCATION_ONLY`, wait/reject/review actions |
| Entry Quality | Entry Admission state/action/sufficiency |
| Trend / momentum | current close/MA and 20D momentum fields |
| Continuation Quality | current continuation status |
| Downside risk | current downside/risk status |
| Corporate Action | CA status/source authority |
| Liquidity/capacity | capacity ratio and liquidity severity |
| Market/regime | risk pacing and exposure/cash controls |
| Portfolio Construction | capital competition, caps, lot feasibility, headroom |
| PM current campaign | current open campaign controls for HOLD/ADD/REDUCE/EXIT |
| Runtime / Submit | Pending, idempotency, broker/safety/authority validation |

Therefore, weak symbols immediately after EXIT are not automatically bought if long-term REENTRY penalty is removed. They still must pass current PIT evidence and capital competition.

## 4. EXIT Reason Unique Value

| prior EXIT reason family | current PIT sufficient? | recent context adds value? | long-lived context justified? | ES judgment |
|---|---|---|---|---|
| `hard_stop` | MIXED | YES | only with fresh/current hard-stop relevance; not indefinite | `RECENT_EXIT_CONTEXT_ADDS_VALUE` near-term; `LONG_LIVED_EXIT_CONTEXT_UNJUSTIFIED` if old |
| technical deterioration | YES when current trend/momentum/Entry evidence is available | YES near-term | generally no after current recovery evidence is strong | `CURRENT_EVIDENCE_SUFFICIENT` after recovery |
| profit retention break | mostly YES via current PM/profit/continuation/risk evidence | limited near-term | no as a permanent future BUY discount | `LONG_LIVED_EXIT_CONTEXT_UNJUSTIFIED` |
| peak drawdown warning | mostly YES via current risk/downside/volatility and PM evidence | YES near-term | no without current downside/risk evidence | `RECENT_EXIT_CONTEXT_ADDS_VALUE` only while fresh |
| generic EXIT | NO unique semantic value | NO, unless provenance is needed for audit | no | `UNKNOWN_CONTEXT_SHOULD_NOT_PERSIST` |
| unknown prior context | current evidence may be enough for opportunity quality, but not to reconstruct old cause | audit value only | no as capital block | `UNKNOWN_CONTEXT_SHOULD_NOT_PERSIST` |

`EXIT_REASON_HISTORY_ADDS_UNIQUE_LONG_TERM_VALUE = MIXED`

It adds unique safety value in the recent/near-term window and for specific hard-stop or technical failure continuity. It does not justify an indefinite security-level penalty.

## 5. Minimal Churn Guard Feasibility

A reduced concept is feasible:

`RECENT_EXIT_CHURN_GUARD`

Required architecture properties:

- bounded;
- campaign-aware;
- time-decaying / explicit-expiry capable;
- preserves prior campaign lineage for audit;
- does not carry old ownership as a permanent current-opportunity classification penalty;
- after guard expiry, evaluates the security with ordinary current PIT controls and PC capital competition;
- does not use future outcome or PnL to choose boundaries.

This is consistent with Phase CP/CQ:

- permanent lineage is useful;
- permanent decision penalty is not;
- time-only reset is too weak;
- time + current PIT evidence is the proper family of designs;
- literal `BUY_NEW` relabel is unnecessary if capital treatment becomes NEW-equivalent after the guard/requalification lifecycle clears.

`MINIMAL_RECENT_EXIT_CHURN_GUARD_FEASIBLE = YES`

## 6. Architecture Impact Map

| Area | A. Keep current REENTRY + repair long-lived history | B. Shrink REENTRY to recent-exit guard | C. Full REENTRY concept removal |
|---|---|---|---|
| Candidate | still classifies old owned symbols as REENTRY; needs relevance repair | prior lineage can remain diagnostic; current opportunity is not permanently downgraded | all candidates current-only; churn context lost unless replaced elsewhere |
| BQ | mostly unchanged | unchanged | unchanged |
| Entry | remains current control plus REENTRY recovery consumer | current control remains; recent guard can reference it | current control remains |
| PC | smaller change if preserving existing REENTRY structure | clearer separation: guard blocks only recent/unsafe lifecycle; otherwise current PC competition | simplest PC path but loses explicit blocked-REENTRY observability |
| PM | current campaign ADD/REDUCE unaffected | unaffected | unaffected |
| campaign identity | permanent lineage retained | permanent lineage retained | lineage must still remain in campaign/ledger observability, outside REENTRY concept |
| Runtime | no direct order semantic change if PC outputs same authority shape | no direct change if PC publishes ordinary current authority after guard | no direct change, but CK-style bypass protections need replacement |
| Ledger | unchanged | unchanged | unchanged |
| Observability | preserves existing REENTRY fields | needs renamed/clear lifecycle: lineage vs guard vs ordinary current evaluation | lower semantic visibility unless new diagnostics added |
| Schema | likely least disruptive | moderate semantic cleanup | broadest cleanup |
| Safety | preserves too much | preserves real short churn with less stale penalty | highest risk: immediate churn protection can disappear |

Judgment:

- A is feasible but keeps the confusing permanent REENTRY branch.
- B is the best fit: keep lineage, shrink decision penalty to bounded recent-exit churn / unresolved-current-evidence cases.
- C is technically feasible, but Production risk is high unless a replacement guard is introduced. If a replacement guard is introduced, it effectively becomes B.

## Investment Philosophy Alignment

Investment philosophy statement:

`過去に一度保有したという事実だけで、現在の良いOpportunityが不利にならない`

Current long-lived REENTRY behavior is not fully aligned with this philosophy because old prior-exit identity can keep a symbol in a stricter branch for hundreds of business days. The legitimate part is not old ownership itself; it is recent churn risk and unresolved current weakness.

The philosophy is best satisfied by preserving historical lineage for audit while removing or expiring the decision penalty once the recent-exit / same-thesis risk is no longer current and PIT evidence is evaluated by ordinary controls.

## Required Outputs

- `REENTRY_ONLY_PROTECTION_COUNT = 460`
- `REENTRY_ONLY_PROTECTION_RATE = 3.03%`
- `CURRENT_CONTROLS_ALREADY_COVER_MAJORITY = YES`
- `TRUE_SHORT_TERM_CHURN_RISK_EXISTS = YES`
- `LONG_TERM_REENTRY_CONTEXT_NECESSARY = NO`
- `EXIT_REASON_HISTORY_ADDS_UNIQUE_LONG_TERM_VALUE = MIXED`
- `MINIMAL_RECENT_EXIT_CHURN_GUARD_FEASIBLE = YES`
- `REENTRY_FULL_REMOVAL_ARCHITECTURALLY_FEASIBLE = YES`
- `REENTRY_FULL_REMOVAL_RISK = HIGH`
- `NEXT_DESIGN_DIRECTION = B`
- `PRODUCTION_CHANGED = NO`
- `SHADOW_CHANGED = NO`
- `TARGET_RUN_MUTATED = NO`
- `RUNTIME_STATE_MUTATED = NO`
- `FUTURE_OUTCOME_USED_FOR_PRODUCTION_JUDGMENT = NO`

## Final Judgment

`PHASE32_ES_REENTRY_LONG_TERM_SECURITY_LEVEL_CONCEPT_NOT_FUNCTIONALLY_NECESSARY_MINIMAL_RECENT_EXIT_CHURN_GUARD_FEASIBLE_NEXT_DESIGN_DIRECTION_B`
