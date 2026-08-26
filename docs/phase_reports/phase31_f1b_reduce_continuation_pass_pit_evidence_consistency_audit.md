# Phase31-F1B — REDUCE vs Continuation-PASS PIT Evidence Consistency Audit

Status: COMPLETE
Task type: READ-ONLY PIT / SELL-EVIDENCE AUDIT

## PRIMARY_JUDGMENT

```text
PHASE31_F1B_REDUCE_PASS_NOT_CONFLICT_SI_AGGREGATE_TOO_COARSE_FOR_ESCALATION
```

F1B audited why PM can emit `REDUCE` while Strategy Intelligence reports `continuation_quality_status = PASS` and `downside_risk_status = PASS`. The result is not a true PM/SI contradiction. `PASS` means evidence is sufficiently available and not fail-closed; it does not mean "no risk" or "EXIT impossible".

The unresolved gap is semantic granularity: the aggregate SI PASS fields are too coarse for Alternative G escalation. The useful PIT deterioration evidence already exists in nested fields, for example participation weakness, elevated participation risk, entry caution, observed giveback, and PM reason codes, but the current PM/SI/Alternative-G surface does not materialize a canonical SELL deterioration sufficiency state.

## Evidence Scope

```text
TARGET_RUN = reports/runtime_tests/runs/runtime-test-historical-extended-smoke-20260820T120909096218Z
TARGET_WINDOW = 2022-08-10 through 2022-10-12
REPORTS_READ = F0, F1, F1A
CURRENT_SOT_READ = position_management.py, strategy_intelligence.py, position_management_decision_trace_contract.md
```

No future return, later price, later MFE/MAE, eventual EXIT, delisting outcome, or final campaign outcome was used for judgment.

## Producer / Consumer Trace

| Field | SOURCE | PRODUCER | MATERIALIZED FIELD | PM CONSUMER |
|---|---|---|---|---|
| `continuation_quality_status` | technical features + Market Context | `strategy_intelligence._continuation_quality` | `strategy_intelligence.symbol_intelligence.<symbol>.continuation_quality.status`; copied to PM as `strategy_intelligence_continuation_quality_status` | `position_management._attach_strategy_intelligence_positions`; copied/observed, not action authority |
| `downside_risk_status` | technical volatility/risk, corporate-event uncertainty, Market Context | `strategy_intelligence._downside_risk` | `strategy_intelligence.symbol_intelligence.<symbol>.downside_risk.status`; copied to PM as `strategy_intelligence_downside_risk_status` | copied/observed, not action authority |
| `profit_protection_status` | lifecycle context, current position, continuation/downside substates | `strategy_intelligence._profit_protection_evidence` | `profit_protection_evidence.status`; copied to PM as `strategy_intelligence_profit_protection_status` | copied/observed, not action authority |
| `observed_giveback` | `positions/position_campaigns.json` via lifecycle context | `strategy_intelligence._lifecycle_context` and `_profit_protection_evidence` | `lifecycle_context.observed_giveback`; PM `strategy_intelligence_observed_giveback` | copied/observed, no threshold authority |
| `current_campaign_relative_return` | campaign/current position lifecycle context | `strategy_intelligence._lifecycle_context` | `lifecycle_context.current_campaign_relative_return`; PM `strategy_intelligence_current_campaign_relative_return` | copied/observed |
| hold score | PM decision trace contract requires it, but current PM rows do not materialize it | existing PM accepted generation / PM decision source | nonempty count in REDUCE/EXIT rows = 0 | unavailable for F1B classification |
| trend/opportunity state | PM trace contract expects decomposition; SI nested fields expose trend/participation/entry caution | SI and PM source decisions | SI nested states exist; PM rows expose only broad reason codes | partially consumed/attached |
| PM REDUCE reason | existing PM decision source + `position_management` artifact | `position_management.build_position_management_payload` / existing PM decisions | PM `reason_codes` | authoritative PM explanation |
| PM EXIT reason | existing PM decision source + `position_management` artifact | same | PM `reason_codes` | authoritative PM explanation |

Important SoT points:

- `strategy_intelligence` marks these fields as `not_action_authority`.
- `position_management._attach_strategy_intelligence_positions` appends SI evidence but does not convert REDUCE to HOLD or EXIT.
- The PM decision trace contract says `risk_increased_but_trend_not_broken` is a broad legacy alias that should be split into more specific causes in future trace work.

## REDUCE + PASS Classification

```text
TOTAL_REDUCE_ROWS = 154
CONSISTENT_WEAKENING_BUT_INTACT_COUNT = 0
SI_TOO_COARSE_COUNT = 154
PM_SI_SEMANTIC_CONFLICT_COUNT = 0
MISSING_DETERIORATION_MATERIALIZATION_COUNT = 0
CONSUMER_GAP_COUNT = 0
INSUFFICIENT_EVIDENCE_COUNT = 0
```

All 154 REDUCE rows are classified as `SI_TOO_COARSE`. This does not mean PM and SI conflict. It means the aggregate SI PASS fields are not granular enough for Alternative G escalation sufficiency.

Evidence:

| REDUCE evidence | Count |
|---|---:|
| `continuation_quality_status = PASS` | 154 |
| `downside_risk_status = PASS` | 154 |
| `profit_protection_status = OBSERVED` | 154 |
| PM reason `risk_increased_but_trend_not_broken` | 135 |
| PM reason `peak_drawdown_warning` | 19 |
| profit-protection continuation connection `WEAK` | 129 |
| profit-protection continuation connection `ELEVATED_RISK` | 83 |
| profit-protection continuation connection `DECELERATING` | 49 |
| profit-protection downside risk rise `ELEVATED_RISK` | 148 |

Interpretation:

```text
PASS = evidence sufficient / not blocking
REDUCE = PM de-risk intent while campaign optionality remains
```

These can coexist. The defect is that F1A cannot safely decide persistent EXIT from the aggregate PASS fields alone.

## PM REDUCE Trigger Fields

```text
PM_REDUCE_TRIGGER_FIELDS = PM action; PM intensity; PM confidence; PM reason_codes; accepted PM decision source; strategy_intelligence_sell_side_evidence_connected; nested SI continuation/downside/profit-protection context
```

In the current run, PM REDUCE is directly represented by PM fields:

- `action = REDUCE`
- `intensity = LIGHT / MEDIUM / STRONG`
- `confidence`
- `reason_codes`

The immediate PM reasons were:

| Reason | Count |
|---|---:|
| `risk_increased_but_trend_not_broken` | 135 |
| `peak_drawdown_warning` | 19 |
| `strategy_intelligence_sell_side_evidence_connected` | 154 |

Why REDUCE can coexist with SI PASS:

- SI `PASS` means required evidence exists and is not fail-closed.
- SI nested fields can still show weak participation, elevated participation risk, mixed persistence, or entry caution.
- PM reason `risk_increased_but_trend_not_broken` means de-risk pressure while trend/opportunity is not fully broken.
- `position_management_decision_trace_contract.md` explicitly treats this reason as a broad fallback / legacy alias, not a contradiction.

Current PM rows do not materialize nonempty `hold_score`, `exit_score`, `reduce_score`, `dominant_cause`, `canonical_decision_reason_codes`, or `reason_semantics_contract_version` in REDUCE/EXIT rows. That prevents a clean score-based reconstruction in F1B.

## REDUCE vs EXIT PIT Comparison

```text
REDUCE_EXIT_PIT_SEPARABILITY = PARTIAL
```

Aggregate comparison:

| Field | REDUCE | EXIT |
|---|---:|---:|
| Rows | 154 | 60 |
| SI continuation PASS | 154 | 60 |
| SI downside PASS | 154 | 60 |
| SI profit protection OBSERVED | 154 | 60 |
| Median confidence | 0.3255 | 0.3463 |
| Median current campaign relative return | 0.0003 | 0.0000 |
| Median observed giveback | 0.0052 | 0.0084 |

Reason boundary:

| REDUCE reasons | Count |
|---|---:|
| `risk_increased_but_trend_not_broken` | 135 |
| `peak_drawdown_warning` | 19 |

| EXIT reasons | Count |
|---|---:|
| `trend_and_opportunity_broken` | 22 |
| `weak_hold_score` | 18 |
| `profit_retention_break` | 15 |
| `hard_stop_current_return` | 11 |

There is a PIT semantic boundary in PM reason codes. There is not yet a sufficient boundary in aggregate SI PASS fields. Therefore separability is `PARTIAL`.

## Persistent REDUCE Progression

```text
PERSISTENT_DETERIORATION_PROGRESS_OBSERVABLE = PARTIAL
```

F1A found 29 persistent campaigns. F1B found PIT movement in 27 of 29 using PM reason changes and PIT-observed lifecycle/profit-protection fields such as current campaign relative return and observed giveback. But this movement is not yet a canonical deterioration sufficiency state and cannot select an EXIT threshold.

Representative persistent progression:

| Symbol | REDUCE rows | First | Last | PIT progression observed |
|---|---:|---|---|---|
| 61750 | 19 | 2022-09-13 | 2022-10-12 | giveback increases; relative return oscillates near flat |
| 83060 | 9 | 2022-08-16 | 2022-08-26 | giveback/relative-return movement |
| 32710 | 8 | 2022-09-07 | 2022-09-22 | reason changes plus giveback/relative-return movement |
| 39890 | 7 | 2022-08-31 | 2022-09-09 | reason changes plus giveback/relative-return movement |
| 33500 | 6 | 2022-09-30 | 2022-10-11 | giveback/relative-return movement; includes minimum-notional family |
| 27880 | 5 | 2022-08-31 | 2022-09-27 | recovery-protected despite repeated REDUCE |

Conclusion: progression exists as evidence, but not as a resolved production escalation criterion.

## 61750 Deep Dive

```text
61750_SEMANTIC_JUDGMENT = CONSISTENT_BUT_INSUFFICIENT_GRANULARITY
```

61750 repeated 19 REDUCE rows because the PM state remained:

```text
REDUCE + risk_increased_but_trend_not_broken + LIGHT intensity
```

while SI aggregate state remained:

```text
continuation_quality_status = PASS
downside_risk_status = PASS
profit_protection_status = OBSERVED
```

This is not a true conflict. The exact 2022-09-13 SI evidence shows the pattern:

- `trend_health = SUPPORTIVE`
- `participation_quality = WEAK`
- `participation_risk = ELEVATED_RISK`
- `entry_state = CONTINUATION_WITH_CAUTION`
- `admission_action = ADD_REDUCED_ONLY`
- `profit_protection_evidence.continuation_deterioration_connection = [WEAK]`
- `profit_protection_evidence.downside_risk_rise_connection = [ELEVATED_RISK]`

For 61750, current relative return stayed around -0.11% to +0.22%, observed giveback increased from about 0.11% to about 0.33%, and PM reason stayed the same. That is weak/persistent caution, not EXIT-grade breakdown. F1B therefore cannot justify a PIT EXIT date for 61750.

## Recovery Controls

```text
RECOVERY_SEPARATION_FIELDS = PM action transitions HOLD/ADD; PM HOLD/ADD reason codes; SI entry_state; SI admission_action; trend_health; participation_quality; participation_risk; current_campaign_relative_return; observed_giveback; profit_protection continuation/risk connections
```

F1A recovery controls had no false shadow EXIT. F1B confirms why: recovery or winner cases often show PM HOLD/ADD-compatible reason codes and improved/healthy PIT context, but aggregate SI PASS alone cannot distinguish them from persistent unresolved REDUCE. The useful separation fields are nested and semantic, not the top-level PASS flags.

## Deterioration Sufficiency

```text
DETERIORATION_SUFFICIENCY = EXISTING_FIELDS_NEED_REFINED_SEMANTICS
```

Existing PIT fields are not empty. They include:

- PM REDUCE/EXIT reasons;
- PM intensity/confidence;
- SI nested continuation dimensions;
- SI nested downside dimensions;
- profit-protection connections;
- lifecycle relative return/MFE/giveback;
- entry admission caution states.

The gap is not primarily missing data and not merely an Alternative G consumer-only bug. The main gap is that existing fields need a canonical SELL-side semantic refinement that maps nested PIT states into:

- weakening but intact;
- recovery/reset;
- persistent deterioration unresolved;
- EXIT-grade deterioration.

## Repair Candidates

PIT-supported repair candidates:

1. Phase31-F1C SELL evidence semantic refinement design.
2. Add or materialize PM decision trace semantics for REDUCE/EXIT dominant cause, including `canonical_decision_reason_codes`, score fields where already produced, and explicit legacy alias mapping.
3. Refine Alternative G shadow to consume nested SI states instead of aggregate `continuation_quality_status` / `downside_risk_status` alone.
4. Keep minimum-notional policy separate.
5. Keep Market Context SELL authority as separate F2 work.

Not supported in F1B:

- REDUCE-count threshold selection;
- SELL threshold tuning;
- automatic REDUCE -> EXIT;
- using later 61750 outcome;
- treating SI PASS as contradiction.

## Required Output

```text
PRIMARY_JUDGMENT = PHASE31_F1B_REDUCE_PASS_NOT_CONFLICT_SI_AGGREGATE_TOO_COARSE_FOR_ESCALATION
TOTAL_REDUCE_ROWS = 154
CONSISTENT_WEAKENING_BUT_INTACT_COUNT = 0
SI_TOO_COARSE_COUNT = 154
PM_SI_SEMANTIC_CONFLICT_COUNT = 0
MISSING_DETERIORATION_MATERIALIZATION_COUNT = 0
CONSUMER_GAP_COUNT = 0
INSUFFICIENT_EVIDENCE_COUNT = 0
PM_REDUCE_TRIGGER_FIELDS = action; intensity; confidence; reason_codes; accepted PM decision source; SI nested continuation/downside/profit-protection context
REDUCE_EXIT_PIT_SEPARABILITY = PARTIAL
PERSISTENT_DETERIORATION_PROGRESS_OBSERVABLE = PARTIAL
61750_SEMANTIC_JUDGMENT = CONSISTENT_BUT_INSUFFICIENT_GRANULARITY
RECOVERY_SEPARATION_FIELDS = PM action transitions; PM HOLD/ADD reasons; SI entry/admission; nested continuation/downside states; lifecycle return/giveback; profit-protection connections
DETERIORATION_SUFFICIENCY = EXISTING_FIELDS_NEED_REFINED_SEMANTICS
ALTERNATIVE_G_REFINEMENT_DIRECTION = consume canonical nested SI deterioration/recovery states and PM reason semantics; do not use aggregate PASS as escalation blocker or trigger by itself
REPAIR_CANDIDATES = SELL evidence semantic refinement; PM decision trace materialization/alias cleanup; Alternative G nested-state refinement; minimum-notional separate design; Market Context SELL authority later
MARKET_CONTEXT_LOGIC_CHANGED = NO
FUTURE_INFORMATION_USED_FOR_JUDGMENT = NO
OUTCOME_USED_FOR_THRESHOLD_SELECTION = NO
IMPLEMENTATION_CHANGED = NO
LONG_HISTORICAL_EXECUTED = NO
```

## NEXT_TASK_RECOMMENDATION

```text
Phase31-F1C SELL evidence semantic refinement design
```

F1C should define a canonical SELL-side semantic layer over existing PIT fields before further Alternative G mutation work. The target is not new alpha; it is clearer interpretation of already materialized PM/SI evidence.

## FINAL QUESTIONS

1. PM REDUCEとSI PASSは本当に矛盾しているのか？

   No. PASS is aggregate evidence sufficiency, not "healthy enough to block REDUCE".

2. PMは何を見てREDUCEを出しているのか？

   Current artifacts expose PM action/intensity/confidence/reason codes from the accepted PM decision source. Direct REDUCE reasons are `risk_increased_but_trend_not_broken` and `peak_drawdown_warning`, with SI sell-side evidence attached afterward.

3. REDUCEとEXITを分けるPIT evidenceは既に存在するか？

   Partially. PM reason-code families separate REDUCE from EXIT, but aggregate SI PASS does not.

4. persistent REDUCEで「悪化の進行」を観測できるか？

   Partially. 27/29 persistent campaigns show PIT movement, but not a canonical EXIT sufficiency state.

5. 61750が19回同じ状態になった本当の理由は何か？

   It stayed in weak-but-intact caution: LIGHT REDUCE, trend not broken, SI PASS, weak participation/elevated participation risk, and no EXIT-grade semantic resolution.

6. recovery caseとpersistent deteriorationを分ける既存fieldはあるか？

   Yes, but mostly nested: PM HOLD/ADD transitions, entry/admission state, trend/participation/risk substates, relative return, giveback, and profit-protection connections.

7. Alternative Gに足りないのはthresholdか、semanticか、dataか、consumerか？

   Primarily semantic. Thresholds should wait until SELL deterioration semantics are canonical.

8. 次に修正すべき具体的なSELL-side gapは何か？

   SELL evidence semantic refinement: split broad PM REDUCE aliases and expose canonical deterioration/recovery sufficiency states from existing PIT fields.
