# Phase32-FK Post-Deterioration Re-ADD Authority / Long-Lived History Bias Exhaustive READ-ONLY Audit

## Scope

- Target run: `runtime-test-historical-extended-smoke-20260903T213011268067Z`
- Audit snapshot: `187` completed business days, `2022-10-03` through `2023-07-05`
- Run state during audit: `RUNNING`, next job `2023-07-06:market_refresh`
- Evidence sources: daily `position_management/pm_decisions.json`, `strategy/position_management.json`, `strategy/strategy_intelligence.json`, `strategy/portfolio_construction.json`, `strategy/position_sizing.json`, `strategy/runtime_planning.json`, `execution/fills.json`, source code, Architecture SoT, and Phase32 EQ/ER/ES/ET/EU/EV/EW/EZ/FA/FB/FJ/AH references.

This was READ-ONLY. No Production, SHADOW, config, schema, runtime state, Pending, Ledger, fresh-run, resume, recover, or replay mutation was executed.

## Executive Summary

The audit found no REENTRY-style security-level or cross-campaign long-lived re-ADD bias. Old deterioration in a prior closed campaign did not leak into a new campaign's ADD authority in the inspected actual paths.

However, two re-ADD design issues are present:

1. `RE-ADD confirmation gap`: post-deterioration ADD uses the same current ADD trigger semantics as ordinary ADD: `strong_trend_continuation`, `opportunity_rank_still_high`, and `no_loss_averaging`. Actual re-ADD fills had current CQ/risk/add-worthiness PASS, but no distinct "re-strengthened after deterioration" contract is binding.
2. `Campaign-local ADD history cap`: once an open campaign reaches `add_history_summary.event_count >= 5`, Strategy PM / PC converts further ADD to NO_ADD via `prior_add_history_limits_incremental_add`. This is not security-level lifetime bias, but it is an effective indefinite open-campaign ADD suppression until campaign closure.

Therefore the primary judgment is `H. MIXED`: no cross-campaign/old-history correctness defect, but re-ADD confirmation and campaign-local history semantics deserve design refinement.

## Re-ADD Definition

For this audit, re-ADD means:

```text
same open campaign
-> prior deterioration / warning / REDUCE evidence
-> later PM ADD intent or actual BUY_ADD fill
```

Deterioration evidence included PM `REDUCE` / `EXIT` and reason codes such as `peak_drawdown_warning`, `profit_retention_break`, `risk_increased_but_trend_not_broken`, `hard_stop_current_return`, `trend_and_opportunity_broken`, and related canonical deterioration aliases.

This definition does not treat past deterioration as a penalty. It is only an audit anchor for checking whether later ADD authority is owned by current PIT evidence.

## Re-ADD Population

| Metric | Value |
|---|---:|
| `POST_DETERIORATION_READD_CAMPAIGN_COUNT` | 10 |
| Post-deterioration re-ADD symbol count | 10 |
| `POST_DETERIORATION_READD_INTENT_COUNT` | 87 |
| `POST_DETERIORATION_ACTUAL_ADD_COUNT` | 3 |
| Post-deterioration actual BUY_ADD notional | 211,200 |
| `MULTIPLE_READD_CYCLE_CAMPAIGNS` | 8 |
| Max re-ADD intent cycles in one campaign | 36 |

Re-strengthening classification from actual PM reason evidence:

| Classification | Count |
|---|---:|
| `CLEAR_RESTRENGTHENING` | 87 |
| `PARTIAL_RESTRENGTHENING` | 0 |
| `RANK_STILL_HIGH_ONLY` | 0 |
| `MIXED_OR_UNRESOLVED` | 0 |
| `DETERIORATION_STILL_ACTIVE` | 0 |
| `UNKNOWN` | 0 |

Every extracted re-ADD intent carried all three PM reason codes:

- `strong_trend_continuation`
- `opportunity_rank_still_high`
- `no_loss_averaging`

No rank-only re-ADD was observed.

## Actual Re-ADD Fills

| Re-ADD date | Symbol | Campaign | Prior deterioration anchor | PM ADD reason | Strategy ADD worthiness | Quantity | Notional | Classification |
|---|---|---|---|---|---|---:|---:|---|
| 2023-03-30 | 43880 | `pc-64642ec31e0f55ef-43880-0001` | 2023-03-27 HOLD `profit_retention_break`; earlier 2023-03-23 REDUCE `peak_drawdown_warning` | `strong_trend_continuation`, `opportunity_rank_still_high`, `no_loss_averaging` | PASS | 100 | 122,900 | `CLEAR_RESTRENGTHENING` |
| 2023-04-04 | 83060 | `pc-353ffefc940505e3-83060-0001` | 2022-12-20 REDUCE `peak_drawdown_warning` | same three ADD reasons | PASS | 100 | 85,800 | `CLEAR_RESTRENGTHENING` |
| 2023-06-13 | 21340 | `pc-0774f425fe6b09c1-21340-0001` | 2023-06-12 HOLD `profit_retention_break` | same three ADD reasons | PASS | 100 | 2,500 | `CLEAR_RESTRENGTHENING` |

Deep evidence examples:

- `43880` on 2023-03-30 had `campaign_identity_authority_status=COMPLETE`, `continuation_quality_status=PASS`, `downside_risk_status=PASS`, `current_campaign_relative_return=1.09%`, `observed_campaign_mfe=23.57%`, and `observed_giveback=22.48%`. `add_history_summary.event_count=0`, `reduce_history_summary.event_count=0`; the earlier REDUCE was present in `prior_unrepresentable_reduce_summary.last_reduce_date=2023-03-23`, but not as executed reduce history.
- `83060` on 2023-04-04 had `current_campaign_relative_return=30.67%`, `observed_campaign_mfe=51.51%`, `observed_giveback=26.60%`, and ADD worthiness PASS. Prior PM REDUCE history was visible as unrepresentable/recovered context, not as a blocking executed reduce history.
- `21340` on 2023-06-13 had `current_campaign_relative_return=47.06%`, `observed_campaign_mfe=47.06%`, `observed_giveback=0`, and ADD worthiness PASS.

## Producer / Consumer Reference Graph

| Stage | Producer | Consumer | Current PIT evidence | Historical / campaign state | Decision effect |
|---|---|---|---|---|---|
| Runtime PM trigger | `runtime_v2/position_management/producer.py:1040-1057` | Runtime PM decision artifact | `add_score >= 0.72`, `buy_rank <= 5`, `current_return > 0` | no prior deterioration count used here | emits ADD reason codes |
| Strategy Intelligence lifecycle | `strategy/strategy_intelligence.py:1408-1457`, `2144-2158` | Strategy PM / PC | current position, current price, current campaign | same open campaign add/reduce/sell summaries | materializes campaign-local state |
| Strategy PM ADD worthiness | `strategy/position_management.py:1635-1678` | Strategy PM action normalization | CQ status, downside risk, campaign identity | same-campaign ADD/REDUCE event counts | PASS or converts ADD to HOLD / NO_ADD |
| PC ADD worthiness | `strategy/portfolio_construction.py:9466-9492` | PC membership / target | entry action, CQ, risk, profit status | same-campaign ADD/REDUCE event counts | ADD_ALLOWED / NO_ADD |
| MCV / increment authority | `strategy/marginal_capital_value.py:1993-2078` | Shadow / PC evidence | BQ, Entry, expected edge, incremental value, opportunity cost, headroom, PIT status | campaign id and current position only | classifies positive increment demand; shadow-only fields remain non-authoritative unless already connected |
| Position Sizing | `strategy/position_sizing.py:2140-2285` | Runtime Planning | price, target/current weight, lot, cap, safety headroom | current position quantity | executable BUY_ADD quantity |
| Runtime Planning / Fill | `strategy/runtime_planning.py`, `runtime_v2/planning/add_consumer.py` | Pending / execution | accepted PC/PS authority | current position membership | BUY_ADD order increment only |

## Current Evidence vs Historical Context Separation

| Consumer | A. Current PIT evidence | B. Campaign-local state | C. Old campaign history | D. Security lifetime history | E. Run-wide history | Judgment |
|---|---|---|---|---|---|---|
| Runtime PM ADD trigger | YES | current return/position | NO | NO | NO | current-only trigger |
| Strategy PM ADD worthiness | YES | YES: same-campaign ADD/REDUCE counts | NO | NO | NO | campaign-local cap/review |
| PC ADD worthiness | YES | YES: same-campaign ADD/REDUCE counts | NO | NO | NO | campaign-local cap/review |
| MCV ADD increment evidence | YES | current position/campaign id/headroom | NO | NO | NO | history-free increment check, but consumes upstream PM/PC state |
| Runtime Planning / execution | YES | current position membership | NO | NO | NO | consumer-only |
| Campaign materialization | strict-prior current campaign facts | YES | closed campaigns for audit/reconstruction | not used as ADD score/rank authority | can scan/carry run artifacts | performance/materialization dependency, not direct re-ADD decision authority |

## Long-Lived History Bias Search

Search terms covered prior/last/historical ADD/REDUCE, warning/deterioration, cooldown/recovery, campaign/security history, and re-strengthening concepts across Production paths.

Findings:

- No evidence that prior closed campaign ADD/REDUCE/warning history changes current re-ADD score, rank, weight, or eligibility.
- No evidence that old security-level ADD success/failure gives a current campaign a bonus.
- No evidence that old security-level deterioration creates a current campaign re-ADD penalty.
- Unknown or missing prior deterioration history is not a separate long-lived ADD block in the inspected source. Missing current campaign identity or incomplete current evidence fails closed to `NO_ADD`, but that is current authority completeness, not old-history penalty.
- Same open campaign history is used. `add_history_summary.event_count >= 5` blocks further ADD. `reduce_history_summary.event_count > 0` is coded as a block/review, but was not observed as the active reason in the current snapshot.

## Permanent Penalty / Bonus

`EFFECTIVE_PERMANENT_READD_PENALTY_FOUND`: YES, but limited to same open campaign ADD-count saturation.

Evidence:

- Strategy PM emits `prior_add_history_limits_incremental_add` at `strategy/position_management.py:1654-1655`.
- PC independently encodes the same state at `strategy/portfolio_construction.py:9481-9486`.
- Actual artifacts showed `176` Strategy ADD-worthiness `NO_ADD` rows, all explained by `prior_add_history_limits_incremental_add`.
- Example: `76470` on 2023-06-13 had `add_history_summary.event_count=5`, current CQ/risk PASS, current return +18.59%, observed MFE +18.59%, but Strategy ADD worthiness was `NO_ADD`.
- Example: `94320` on 2023-05-11 had `add_history_summary.event_count=5`, current return +10.69%, current MFE +11.42%, but Strategy ADD worthiness was `NO_ADD`.

This is not REENTRY-style security-level permanent bias because it resets with a new campaign. It is still a long-lived open-campaign ADD-history dependency and should be reviewed in the design phase.

`EFFECTIVE_PERMANENT_READD_BONUS_FOUND`: NO. Prior ADD success does not automatically increase current ADD rank/target; actual positive ADD still required PM ADD reason, ADD worthiness, PC/PS quantity, and runtime binding.

## Cross-Campaign Leak

Representative checks:

- `76470` reopened as `pc-86cc29266f5b880a-76470-0001` after many prior 76470 campaigns. On 2023-04-24 its new campaign had `add_history_summary.event_count=0`, `reduce_history_summary.event_count=0`, and ADD worthiness PASS. Prior 76470 campaigns did not poison the new campaign.
- `94320` has separate campaigns; the later open campaign carries its own ADD count, not the prior closed campaign's REDUCE/ADD lifecycle.
- `43880` re-ADD on 2023-03-30 used current campaign `pc-64642...`; no old 43880 closed campaign state was consumed as ADD penalty or bonus.

`CROSS_CAMPAIGN_READD_HISTORY_LEAK_FOUND`: NO.

## Re-Strengthening Evidence Inventory

Actual re-ADD rows carried:

- PM current ADD reasons: `strong_trend_continuation`, `opportunity_rank_still_high`, `no_loss_averaging`
- Strategy Intelligence ADD worthiness: `status=PASS`
- Continuation quality: `PASS`
- Downside risk: `PASS`
- Current campaign return: positive in all actual re-ADD fills
- Observed campaign MFE / giveback: material in 43880 and 83060
- PC/MCV: additive increment rows existed; actual fills passed through PC/PS/Runtime as BUY_ADD order increments
- Cash/lot/headroom: sufficient for exactly one BUY_ADD fill in each actual case

The current evidence exists and is used, but it is not framed as "re-strengthening after prior deterioration." It is framed as ordinary ADD continuation.

## 43880 Deep Dive

Path:

```text
2023-03-23 REDUCE peak_drawdown_warning
2023-03-27 HOLD positive_expected_edge + profit_retention_break
2023-03-30 ADD strong_trend_continuation + opportunity_rank_still_high + no_loss_averaging
2023-03-30 BUY_ADD fill 100 shares / 122,900
2023-04-07 REDUCE peak_drawdown_warning
2023-04-10 EXIT trend_and_opportunity_broken
```

Judgment: 43880 re-ADD was not rank-only. It had current continuation and no-loss evidence, and Strategy ADD worthiness PASS. The gap is that `profit_retention_break` / prior warning did not require a separate resolved/re-strengthened state beyond ordinary current ADD signals.

## 76470 Deep Dive

`76470` confirms both separation and the campaign-local cap:

- Prior 76470 campaigns did not leak into the new 2023-04-21 campaign; early in that campaign the ADD history was reset to zero.
- The 2023-04/06 campaign later accumulated 5 ADD fills.
- After that, further ADD worthiness was blocked by `prior_add_history_limits_incremental_add`, even when current CQ/risk and campaign return evidence were positive.

Judgment: no cross-campaign old-history leak; yes campaign-local ADD-history cap.

## 94320 Deep Dive

`94320` is the better-capture comparison case from FJ. The later open campaign retained profits better than 76470, but after 5 ADDs it also showed Strategy PM ADD-worthiness `NO_ADD` due `prior_add_history_limits_incremental_add`.

Judgment: good retention does not exempt the same campaign-local cap. There is no proof of a historical bonus; the cap is symmetric and count-based.

## ADD / REDUCE Evidence Symmetry

`ADD_REDUCE_EVIDENCE_ASYMMETRY_PROVEN`: YES.

Evidence:

- Runtime PM ADD returns when current `add_score`, top-rank persistence, and no-loss are satisfied.
- REDUCE / EXIT uses deterioration thresholds such as drawdown, downside, weak hold, exit score, and later canonical sell-severity persistence.
- Actual PM intent had 87 post-deterioration ADD reappearances, while actual post-deterioration BUY_ADD fills were only 3 due downstream PC/PS/cash/lot/cap filtering.
- PM short-term churn was rare: one REDUCE -> ADD -> REDUCE intent sequence in 45940 over 2BD; no actual fill-level ADD/SELL/ADD or SELL/ADD/SELL cycles.

Interpretation: current architecture already prevents many PM ADD intents from becoming actual BUY_ADD, but the semantic confirmation required to emit ADD intent is not explicitly "re-strengthening after deterioration." REDUCE/EXIT has more explicit deterioration/persistence semantics.

## Rank-Still-High Dependency

`RANK_STILL_HIGH_CAN_RESTORE_ADD`: YES, as one required PM/MCV input.

`RANK_STILL_HIGH_ONLY_READD_FOUND`: NO.

`opportunity_rank_still_high` is not observed as a sole re-ADD authority. It appears alongside `strong_trend_continuation` and `no_loss_averaging`. Still, Architecture should avoid treating "still ranked high" as equivalent to "re-strengthened after deterioration."

## History-Free Re-ADD Feasibility

`HISTORY_FREE_CURRENT_EVIDENCE_READD_FEASIBLE`: YES.

The existing evidence set is sufficient to define a history-free re-ADD confirmation concept if needed:

- current momentum / continuation quality
- current Entry ADD action
- current downside/risk status
- current expected edge / incremental investment value
- current opportunity cost / capital competition
- current headroom, lot, and cash feasibility
- current campaign identity and position membership

If prior context is needed, it should be bounded same-campaign transition context, not security-level lifetime history.

`BOUNDED_RECENT_TRANSITION_CONTEXT_REQUIRED`: PARTIAL. It is useful to know that a prior deterioration episode occurred so the audit can ask for re-strengthening, but current eligibility should not depend on old deterioration as a penalty.

## Whole-Run / Runtime Scaling

`WHOLE_RUN_READD_HISTORY_DEPENDENCY_FOUND`: YES, but not as direct security-level re-ADD bias.

The current decision hot path depends on daily campaign materialization and strategy-intelligence lifecycle summaries. Those are campaign-local and strict-prior, but the surrounding machinery can scan/carry prior daily artifacts and campaign histories. This is similar to the performance side of EQ/EV, not the semantic defect pattern of old REENTRY.

## Comparison With REENTRY Lessons

Reusable principle:

```text
Past ownership/history itself must not alter current decision.
Past deterioration/history itself must not alter current re-ADD decision.
Current PIT evidence owns current authority.
```

Same pattern as REENTRY:

- There is a risk that historical facts become durable current-decision gates.
- Audit lineage and current decision authority must be separated.

Different pattern:

- REENTRY used old security-level prior-exit history across campaigns and across long run age.
- re-ADD uses same open-campaign local history. Cross-campaign leak was not found.
- The observed issue is a confirmation gap and open-campaign ADD saturation cap, not a stale old ownership penalty.

## Required Answers

- `POST_DETERIORATION_READD_CAMPAIGN_COUNT`: 10
- `POST_DETERIORATION_READD_INTENT_COUNT`: 87
- `POST_DETERIORATION_ACTUAL_ADD_COUNT`: 3
- `MULTIPLE_READD_CYCLE_CAMPAIGNS`: 8
- `EFFECTIVE_PERMANENT_READD_PENALTY_FOUND`: YES, same-open-campaign ADD-count cap only
- `EFFECTIVE_PERMANENT_READD_BONUS_FOUND`: NO
- `UNKNOWN_CONTEXT_LONG_LIVED_READD_EFFECT`: NO
- `CROSS_CAMPAIGN_READD_HISTORY_LEAK_FOUND`: NO
- `SECURITY_LEVEL_READD_HISTORY_BIAS_FOUND`: NO
- `WHOLE_RUN_READD_HISTORY_DEPENDENCY_FOUND`: YES, materialization/performance dependency; not direct security-level decision bias
- `CURRENT_RESTRENGTHENING_EVIDENCE_EXISTS`: YES
- `CURRENT_RESTRENGTHENING_EVIDENCE_IS_BINDING`: PARTIAL; current ADD evidence is binding, but no separate re-strengthening-after-deterioration contract is binding
- `RANK_STILL_HIGH_CAN_RESTORE_ADD`: YES, but only with other evidence in observed rows
- `RANK_STILL_HIGH_ONLY_READD_FOUND`: NO
- `DETERIORATION_STILL_ACTIVE_AT_READD_FOUND`: NO in extracted actual re-ADD rows
- `ADD_REDUCE_EVIDENCE_ASYMMETRY_PROVEN`: YES
- `HISTORY_FREE_CURRENT_EVIDENCE_READD_FEASIBLE`: YES
- `BOUNDED_RECENT_TRANSITION_CONTEXT_REQUIRED`: PARTIAL
- `SHORT_TERM_READD_CHURN_EXISTS`: YES at PM intent level, very limited; NO at actual fill level
- `READD_CONFIRMATION_GAP_PROVEN`: YES
- `READD_HISTORY_BIAS_PROVEN`: YES, campaign-local ADD-count cap; NO for security-level/cross-campaign long-lived bias
- `CORRECTNESS_DEFECT_FOUND`: NO
- `DESIGN_REFINEMENT_JUSTIFIED`: YES
- `PRODUCTION_REPAIR_JUSTIFIED`: NO, not from this READ-ONLY audit alone
- `DESIGN_PHASE_READY`: YES
- `LONG_HORIZON_VALIDATION_SAFE_TO_CONTINUE`: YES

## No Mutation Confirmation

- `PRODUCTION_CHANGED`: NO
- `SHADOW_CHANGED`: NO
- `CONFIG_CHANGED`: NO
- `SCHEMA_CHANGED`: NO
- `TARGET_RUN_MUTATED`: NO
- `RUNTIME_STATE_MUTATED`: NO
- `FRESH_RUN_EXECUTED`: NO
- `RESUME_EXECUTED`: NO
- `REPLAY_EXECUTED`: NO
- `FUTURE_OUTCOME_USED_FOR_PRODUCTION_JUDGMENT`: NO

## Final Judgment

`PHASE32_FK_MIXED_READD_CONFIRMATION_GAP_AND_CAMPAIGN_LOCAL_ADD_HISTORY_CAP_FOUND_NO_SECURITY_LEVEL_LONG_LIVED_HISTORY_BIAS_NO_CORRECTNESS_DEFECT`
