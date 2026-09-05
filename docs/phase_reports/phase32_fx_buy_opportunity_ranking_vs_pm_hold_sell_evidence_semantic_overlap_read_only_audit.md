# Phase32-FX — BUY Opportunity Ranking vs PM HOLD/SELL Evidence Semantic Overlap READ-ONLY Audit

## Scope

- Primary evidence run: `runtime-test-historical-extended-smoke-20260903T213011268067Z`
- Completed evidence window: `2022-10-03` through `2023-08-04`, `208BD`
- Starting point: Phase32-FW Top50 dropout cohort, `52` episodes / `49` unique campaigns.

READ-ONLY confirmation:

- Production changed: NO
- SHADOW changed: NO
- Source/config/schema changed: NO
- Runtime/Pending/Ledger state mutated: NO
- fresh-run/resume/replay/recover executed: NO
- future return / PnL / MFE / MAE used for Production design judgment: NO

## Required Prior Reports Read

- `docs/phase_reports/phase32_fw_top50_dropout_hold_profit_giveback_capital_rotation_read_only_audit.md`
- `docs/phase_reports/phase32_fu_early_middle_late_buy_new_purchased_candidate_quality_composition_read_only_audit.md`

## BUY Opportunity Ranking Reconstruction

`BUY_RANKING_FEATURE_LINEAGE_COMPLETE = YES`

Canonical BUY ranking contract:

- Canonical owner: Runtime BUY AI Opportunity Ranking Producer.
- Canonical source artifact: `.runtime/runtime_state/buy_ai/<business_date>/opportunity_rankings.json`.
- Canonical rank field: `buy_rank`, consumed as `opportunity_buy_rank`.
- Portfolio Construction copy: `input_opportunity_rank`.
- Sort contract from Architecture: `expected_edge_score DESC`, then `code ASC`.
- Failure behavior: missing/invalid/conflicting opportunity rank must fail closed for opportunity rows; no fallback to candidate rank, array index, or recomputed rank.

Source-level reconstruction:

- `position_management_ai/historical_validation.py` scores opportunity rows with a model and ranks each `target_date` by `expected_edge_score`.
- `position_management_ai/realdata_dry_run.py` shows the same rank semantic in the real-data dry-run path: sort by `target_date`, `expected_edge_score DESC`, `code ASC`, then assign `buy_rank`.
- `strategy_architecture_v1.md` and `runtime_architecture_v2.md` define propagation into Portfolio Construction, Position Sizing, Runtime Planning, and Pending lineage.

BUY Ranking meaning:

- It is relative opportunity evidence.
- It is not calibrated expected return.
- It is not a SELL action authority.
- Top50 membership is a participation universe / relative rank materialization, not an absolute deterioration threshold.

`BUY_RANKING_HAS_CROSS_SECTIONAL_RELATIVE_OPPORTUNITY_EVIDENCE = YES`

## PM HOLD/REDUCE/EXIT Reconstruction

`PM_FEATURE_LINEAGE_COMPLETE = YES`

PM current action authority consumes:

- current position state: quantity, average cost, holding days, current return, peak return, drawdown from peak;
- market/technical features: 5D/20D return, close over MA20, MA5/MA20, volume ratio, volatility;
- opportunity fields: `expected_edge_score`, `buy_rank`, `downside_risk_score`, `risk_guard_status`;
- campaign-local state: observed campaign MFE, giveback, current campaign relative return, ADD history, prior unrepresentable REDUCE count;
- Strategy Intelligence semantic evidence: continuation quality, downside risk, recovery, deterioration, profit protection;
- market context / regime compatibility as supporting evidence.

PM action construction in source:

- `hold_score = trend + opportunity_continuation + profit + inverse risk`
- `exit_score = trend break + drawdown + current loss + downside`
- `add_score = current profit + trend + expected edge + rank + downside`
- `reduce_score = risk / drawdown / downside deterioration`
- `classify_position_action` emits HOLD/REDUCE/EXIT/ADD.

Important overlap:

- PM already consumes `buy_rank` and `expected_edge_score`.
- PM already sees trend, momentum, downside, continuation, recovery, deterioration, and profit giveback.
- PM does not appear to compare the existing holding against same-day alternative candidates as a portfolio-level capital rotation authority.

`PM_HAS_RELATIVE_OPPORTUNITY_AUTHORITY = PARTIAL`

PM has per-symbol relative rank and expected-edge fields, but not a clean same-day cross-sectional opportunity-cost allocator for deciding whether capital should remain in an incumbent versus be rotated to a stronger current opportunity.

## Feature Overlap Matrix

`FEATURE_OVERLAP_MATRIX_COMPLETE = YES`

| Evidence / Feature | BUY Ranking | PM | Same raw source? | Derived relation | Semantic role |
|---|---|---|---|---|---|
| `expected_edge_score` | YES | YES | YES | IDENTICAL / DERIVED_OVERLAP | BUY rank sort input; PM opportunity continuation and HOLD/REDUCE/EXIT guard |
| `buy_rank` / `opportunity_buy_rank` | YES | YES | YES | IDENTICAL field, different authority | BUY relative order; PM ADD/HOLD support, not full rotation authority |
| Top50 membership | YES | PARTIAL | YES via rank | BUY_ONLY as explicit universe membership | Candidate participation / relative opportunity displacement |
| 5D / 20D return | YES via model/features | YES | PARTIAL | DERIVED_OVERLAP | Momentum / persistence / trend |
| close over MA20 / MA5-MA20 | YES via model/features | YES | PARTIAL | DERIVED_OVERLAP | Trend health / exit score |
| volume / traded value | YES via model/features | YES | PARTIAL | DERIVED_OVERLAP | participation / reliability |
| downside risk score | YES supporting/risk | YES | YES | IDENTICAL / PARTIAL_OVERLAP | BUY quality/risk; PM reduce/exit risk |
| volatility | YES via risk/quality | YES | PARTIAL | DERIVED_OVERLAP | downside/risk |
| market regime | YES supporting | YES supporting | YES | PARTIAL_OVERLAP | regime compatibility / risk context |
| current return | NO for flat BUY_NEW ranking | YES | NO | PM_ONLY | campaign-local profit/loss |
| peak return / giveback | NO | YES | NO | PM_ONLY | profit retention / winner protection |
| holding days | NO | YES | NO | PM_ONLY | lifecycle state |
| current position size | NO | YES | NO | PM_ONLY | position risk and ADD/no-loss constraints |
| same-day alternatives available | YES implicitly via rank universe | NO/PARTIAL | NO direct PM authority | BUY_ONLY / gap | opportunity cost / rotation candidate |
| cash scarcity / capital competition | PC, not BUY rank | NO | N/A | PM lacks final capital allocator | portfolio rotation context |

## Overlap Judgments

`MOMENTUM_EVIDENCE_DUPLICATED_SEMANTICALLY = PARTIAL`

Both BUY and PM use recent returns / momentum-like features, but BUY uses them inside a cross-sectional opportunity score and rank; PM uses them to judge continuation or deterioration of an incumbent campaign.

`TREND_EVIDENCE_DUPLICATED_SEMANTICALLY = PARTIAL`

Both consume MA/trend evidence. The semantic roles differ: BUY asks whether the security is attractive now; PM asks whether the current campaign thesis remains intact or requires REDUCE/EXIT.

`CONTINUATION_EVIDENCE_DUPLICATED_SEMANTICALLY = PARTIAL`

Continuation Quality is intentionally shared evidence, but Architecture explicitly says shared intelligence is not shared action authority.

`RISK_EVIDENCE_DUPLICATED_SEMANTICALLY = PARTIAL`

Downside/risk evidence overlaps substantially. PM uniquely adds campaign-local drawdown/giveback; BUY/PC uniquely handle current candidate eligibility and capital competition.

## Top50 Membership Semantic

`TOP50_MEMBERSHIP_SEMANTIC = B + D, with C-like behavior downstream`

Interpretation:

- B. relative ranking only: `buy_rank` is a same-day cross-sectional ordering by uncalibrated expected-edge score.
- D. participation universe materialization: Top50 defines which opportunities are carried into downstream artifacts.
- C-like hybrid downstream: BQ/Entry/MCV add quality/risk/eligibility semantics after rank materialization, but Top50 itself is not an absolute strength threshold.

Top50 dropout can express:

- relative opportunity deterioration;
- cross-sectional displacement by stronger alternatives;
- current candidate evidence no longer materialized into the participation universe;
- simple rank boundary noise.

It may also coincide with momentum/trend deterioration, but it is not guaranteed to be the same evidence.

## Double Counting Risk

`TOP50_AS_SELL_EVIDENCE_DOUBLE_COUNTING_RISK = MEDIUM`

Reason:

- PM already consumes `buy_rank`, `expected_edge_score`, trend, momentum, and downside evidence.
- Adding Top50 dropout naively as an independent bearish score would double-count some of the same raw evidence.
- However, Top50 dropout also carries relative opportunity / universe displacement information that PM does not currently transform into portfolio rotation authority.

Safe implication:

- Do not use Top50 dropout as a hard SELL rule.
- Do not add it as another trend/momentum deterioration point.
- If used later, it should be framed as soft relative-opportunity / opportunity-cost evidence and combined with churn protection and winner retention.

## Incremental Information Test

Observed over all held rows in the 208BD completed run:

| Case | Definition | Count |
|---|---|---:|
| A | Top50 OUT + PM deterioration present | 625 daily rows |
| B | Top50 OUT + PM HOLD with recovery/continuation support | 472 daily rows |
| C | Top50 IN + PM deterioration present | 1,988 daily rows |
| D | Top50 OUT + PM HOLD + strong alternative present | 236 daily rows |

Observed within the FW 52 dropout episodes:

- FW episode HOLD action-days: `252`
- Top50 OUT + PM strong/recovery HOLD: `252`
- Top50 OUT + PM deterioration HOLD: `251`
- Top50 OUT + PM strong and deterioration HOLD: `251`
- Top50 OUT + PM HOLD + strong alternatives present: `124`
- Top50 OUT + PM HOLD + strong alternatives + cash scarce: `33`

`TOP50_INCREMENTAL_INFORMATION_EXISTS = YES`

The incremental information is not "this security has weak momentum." PM often already knows deterioration and still sees recovery/continuation. The incremental information is that the security is no longer in the same-day cross-sectional opportunity universe while other current opportunities may exist.

## FW Dropout Cohort Reclassification

Episode-level reclassification:

| Classification | Episodes |
|---|---:|
| `OVERLAP_DROPOUT` | 21 |
| `RELATIVE_ONLY_DROPOUT` | 0 |
| `MIXED` | 31 |
| `PM_ONLY_DETERIORATION` | 0 |
| `INSUFFICIENT` | 0 |

`FW_OVERLAP_DROPOUT_COUNT = 21`

`FW_RELATIVE_ONLY_DROPOUT_COUNT = 0`

`FW_MIXED_DROPOUT_COUNT = 31`

Interpretation:

- Pure relative-only dropout was not observed in this cohort under the inspected classification.
- Most economically interesting episodes are mixed: PM sees both deterioration and recovery/continuation, while Top50 dropout adds cross-sectional displacement / opportunity-cost context.

Representative mixed cases:

| Date | Symbol | Campaign | Duration | PM evidence | Opportunity context |
|---|---:|---|---:|---|---|
| 2022-11-18 | 83060 | `pc-353ffefc940505e3-83060-0001` | 1 | `HEALTHY_OR_RECOVERING`, structured hold | strong alternative present, cash scarce |
| 2022-12-01 | 66320 | `pc-1e69517642382008-66320-0001` | 14 | trend continuation / hold-worthiness | strong alternatives present |
| 2022-12-01 | 78860 | `pc-28eff802cdbfca54-78860-0001` | 5 | trend continuation / hold-worthiness | strong alternatives present |
| 2022-12-14 | 61440 | `pc-f6c0c498c31daa25-61440-0001` | 68 | persistent HOLD/REDUCE/EXIT lifecycle | strong alternatives present at dropout |
| 2023-01-18 | 58090 | `pc-35b6d019bb4ac067-58090-0001` | 8 | HOLD/REDUCE/EXIT lifecycle | strong alternative present |

## Strong Alternative / Cash Interaction

All outside-Top50 HOLD rows:

- `TOP50_OUT_PM_STRONG_HOLD_COUNT = 472`
- `TOP50_OUT_PM_WEAK_HOLD_COUNT = 466`
- `TOP50_OUT_STRONG_ALTERNATIVE_PRESENT_COUNT = 236`
- `TOP50_OUT_STRONG_ALTERNATIVE_PLUS_CASH_SCARCE_COUNT = 79`

Within FW dropout episodes:

- strong/recovery HOLD rows: `252`
- weak/deterioration HOLD rows: `251`
- strong alternative present: `124`
- strong alternative + cash scarce: `33`

The most relevant design signal is the intersection:

```text
outside Top50 incumbent
+ PM still says HOLD due to recovery/continuation
+ PM also has deterioration/giveback evidence
+ same-day stronger alternatives exist
+ sometimes cash is scarce
```

This is a rotation-review problem, not a simple SELL problem.

## Incumbency / BUY-SELL Asymmetry

`INCUMBENCY_BIAS_RISK_FOUND = PARTIAL`

The current PM does not blindly preserve incumbents. It exits and reduces many positions. But it evaluates HOLD primarily through current campaign-local continuation/recovery and downside evidence. It does not appear to ask, as a first-class authority:

```text
Would this security win the next marginal unit of capital against today's alternatives?
```

`BUY_SELL_SEMANTIC_ASYMMETRY_FOUND = YES`

BUY path:

- current opportunity strength;
- relative rank;
- market context;
- entry quality;
- PC/MCV capital competition.

HOLD/SELL path:

- campaign-local continuation;
- deterioration/recovery;
- profit retention;
- downside/risk;
- current position lifecycle.

This asymmetry is partly intentional: existing holdings should not be mechanically forced through BUY_NEW eligibility. But the absence of a clean current-opportunity re-evaluation / opportunity-cost layer creates a rotation gap.

## Churn And Winner Retention

Churn protection remains necessary if relative opportunity evidence is added:

- one-day Top50 boundary noise exists;
- `5 / 52` FW dropout episodes later re-entered Top50;
- winner retention can be valid when trend is robust, continuation/recovery is present, downside is contained, and there is no material giveback or stronger opportunity-cost pressure.

`WINNER_RETENTION_CAN_BE_PRESERVED_WITH_RELATIVE_OPPORTUNITY_EVIDENCE = YES`

But only if Top50/rank evidence remains soft, persistent, and context-aware rather than a hard exit trigger.

## Evidence Integration Options

| Option | Assessment |
|---|---|
| A. Add Top50 membership as soft SELL evidence | Useful but medium double-count risk if treated as momentum/trend deterioration |
| B. Add relative opportunity rank/quality as soft evidence | Cleaner than binary Top50; better preserves relative opportunity semantics |
| C. Integrate current security opportunity re-evaluation into PM | Strong philosophy fit, but needs careful action-authority separation |
| D. Separate opportunity-cost-aware rotation layer | Cleanest authority boundary; compares incumbent, new candidate, ADD, and cash without making BUY rank a SELL action |
| E. Existing PM only | Leaves FW capital lock/giveback/rotation gap unaddressed |

`TOP50_HARD_EXIT_READY = NO`

## Architecture Gap Judgment

`RELATIVE_OPPORTUNITY_COST_GAP_FOUND = YES`

`ARCHITECTURE_GAP_JUDGMENT = BOTH_RELATIVE_AND_ROTATION_GAP`

This is not because PM lacks all ranking information. PM has `buy_rank`. The gap is that PM does not use same-day cross-sectional opportunity evidence as a clean capital rotation authority for incumbent holdings.

## Correctness vs Design

- `CORRECTNESS_DEFECT_FOUND = NO`
- Evidence duplication risk: YES, medium, if Top50 is added naively.
- Missing relative opportunity semantic: YES.
- Capital rotation gap: YES.
- Winner retention risk from hard Top50 exit: HIGH.
- `DESIGN_REFINEMENT_JUSTIFIED = YES`
- `PRODUCTION_REPAIR_JUSTIFIED = NO`

## Required Final Answers

- `BUY_RANKING_FEATURE_LINEAGE_COMPLETE = YES`
- `PM_FEATURE_LINEAGE_COMPLETE = YES`
- `FEATURE_OVERLAP_MATRIX_COMPLETE = YES`
- `MOMENTUM_EVIDENCE_DUPLICATED_SEMANTICALLY = PARTIAL`
- `TREND_EVIDENCE_DUPLICATED_SEMANTICALLY = PARTIAL`
- `CONTINUATION_EVIDENCE_DUPLICATED_SEMANTICALLY = PARTIAL`
- `RISK_EVIDENCE_DUPLICATED_SEMANTICALLY = PARTIAL`
- `BUY_RANKING_HAS_CROSS_SECTIONAL_RELATIVE_OPPORTUNITY_EVIDENCE = YES`
- `PM_HAS_RELATIVE_OPPORTUNITY_AUTHORITY = PARTIAL`
- `RELATIVE_OPPORTUNITY_COST_GAP_FOUND = YES`
- `TOP50_MEMBERSHIP_SEMANTIC = RELATIVE_RANKING + PARTICIPATION_UNIVERSE_MATERIALIZATION`
- `TOP50_AS_SELL_EVIDENCE_DOUBLE_COUNTING_RISK = MEDIUM`
- `TOP50_INCREMENTAL_INFORMATION_EXISTS = YES`
- `FW_OVERLAP_DROPOUT_COUNT = 21`
- `FW_RELATIVE_ONLY_DROPOUT_COUNT = 0`
- `FW_MIXED_DROPOUT_COUNT = 31`
- `TOP50_OUT_PM_STRONG_HOLD_COUNT = 472`
- `TOP50_OUT_PM_WEAK_HOLD_COUNT = 466`
- `TOP50_OUT_STRONG_ALTERNATIVE_PRESENT_COUNT = 236`
- `TOP50_OUT_STRONG_ALTERNATIVE_PLUS_CASH_SCARCE_COUNT = 79`
- `INCUMBENCY_BIAS_RISK_FOUND = PARTIAL`
- `BUY_SELL_SEMANTIC_ASYMMETRY_FOUND = YES`
- `WINNER_RETENTION_CAN_BE_PRESERVED_WITH_RELATIVE_OPPORTUNITY_EVIDENCE = YES`
- `TOP50_HARD_EXIT_READY = NO`
- `TOP50_SOFT_EVIDENCE_REVIEW_JUSTIFIED = YES`
- `CURRENT_OPPORTUNITY_REEVALUATION_REVIEW_JUSTIFIED = YES`
- `OPPORTUNITY_COST_ROTATION_REVIEW_JUSTIFIED = YES`
- `ARCHITECTURE_GAP_JUDGMENT = BOTH_RELATIVE_AND_ROTATION_GAP`
- `CORRECTNESS_DEFECT_FOUND = NO`
- `DESIGN_REFINEMENT_JUSTIFIED = YES`
- `PRODUCTION_REPAIR_JUSTIFIED = NO`
- `NEXT_DESIGN_DIRECTION = opportunity-cost-aware rotation layer using relative opportunity as soft evidence, not hard Top50 exit`
- `LONG_HORIZON_VALIDATION_SAFE_TO_CONTINUE = YES`

Final Judgment: `PHASE32_FX_BUY_RANKING_AND_PM_EVIDENCE_PARTIALLY_OVERLAP_RELATIVE_OPPORTUNITY_ROTATION_GAP_CONFIRMED_NO_PRODUCTION_REPAIR`
