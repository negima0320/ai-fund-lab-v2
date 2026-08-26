# Phase31-F1C — Canonical SELL Deterioration / Recovery Semantic Contract Design

Status: COMPLETE
Task type: DESIGN ONLY + PIT EVIDENCE MAPPING

## PRIMARY_JUDGMENT

```text
PHASE31_F1C_CANONICAL_SELL_SEMANTIC_CONTRACT_DEFINED_PIT_MAPPING_READY_FOR_SHADOW
```

F1C defines a canonical SELL deterioration / recovery semantic contract over existing PIT evidence. The contract is sufficient to move to a non-mutating shadow implementation / validation phase, but it does not authorize SELL behavior mutation, threshold tuning, REDUCE-count escalation, or Runtime/PS-created EXIT.

The key design decision is that aggregate Strategy Intelligence `PASS` fields are evidence-availability signals, not health signals. SELL state must be composed from PM action/reasons, PM intensity/confidence, nested SI continuation/downside/profit-protection states, campaign PIT lifecycle context, and same-day PM EXIT reason families.

## Evidence Scope

```text
TARGET_RUN_OR_ARTIFACT = reports/runtime_tests/runs/runtime-test-historical-extended-smoke-20260820T120909096218Z
TARGET_WINDOW = 2022-08-10 through 2022-10-12
DOCUMENTS_READ = F0, F1, F1A, F1B, position_management_decision_trace_contract.md
CURRENT_SOT_READ = strategy_intelligence.py, position_management.py, unrepresentable_reduce_exit_shadow.py
```

No fresh run, resume, replay, or long Historical execution was performed. Existing run artifacts were read only.

## CANONICAL_SELL_STATES

```text
HEALTHY_OR_RECOVERING
WEAKENING_BUT_INTACT
PERSISTENT_DETERIORATION
EXIT_GRADE
UNRESOLVED
```

State meanings:

| State | Contract meaning | Normal PM relationship |
|---|---|---|
| `HEALTHY_OR_RECOVERING` | HOLD/ADD-compatible evidence is current, or prior REDUCE pressure has been reset/decayed by fresh recovery evidence. | HOLD / ADD / preserve |
| `WEAKENING_BUT_INTACT` | De-risk evidence exists, but trend/opportunity is not broken and EXIT-grade evidence is absent. | REDUCE |
| `PERSISTENT_DETERIORATION` | Campaign-scoped fresh PIT evidence repeatedly shows unrepresentable REDUCE plus continuing deterioration dimensions, recovery guard absent, and no hidden deterioration debt. | PM EXIT candidate only after proof completeness |
| `EXIT_GRADE` | Same-day PM EXIT reason family or equivalent current PIT severe deterioration evidence is present. | EXIT |
| `UNRESOLVED` | Required PIT proof, representability family, recovery state, or deterioration sufficiency is incomplete. | preserve / review |

## STATE_FIELD_MAPPING

| Field | Source artifact / producer | Classification | Use in contract |
|---|---|---|---|
| `action` | `strategy/position_management.json` | PRIMARY | PM-owned current action boundary: HOLD/ADD/REDUCE/EXIT |
| `reason_codes` | `strategy/position_management.json` | PRIMARY | REDUCE vs EXIT semantic family; not independent authority outside PM |
| `intensity` | `strategy/position_management.json` | SUPPORTING | REDUCE strength context; never sufficient alone |
| `confidence` | `strategy/position_management.json` | SUPPORTING | Selected action score / confidence alias; not calibrated probability |
| `position_campaign_id` / `strategy_intelligence_campaign_id` | PM / SI artifacts | PRIMARY | Campaign-scoped fresh PIT reevaluation boundary |
| `reduce_execution_semantic` | `strategy/position_sizing.json` | PRIMARY | Representability family: discrete-lot vs minimum-notional vs representable |
| `current_quantity`, `trading_unit`, `raw_reduce_quantity`, `rounded_reduce_quantity`, `reduce_final_sell_quantity` | PS | PRIMARY | Determines whether partial REDUCE is representable |
| `strategy_intelligence_continuation_quality_status` | PM-attached SI | OBSERVABILITY_ONLY | Evidence sufficiency; not health, recovery, or EXIT block |
| `strategy_intelligence_downside_risk_status` | PM-attached SI | OBSERVABILITY_ONLY | Evidence sufficiency; not health, recovery, or EXIT block |
| `continuation_quality.trend_health.state` | SI | PRIMARY | SUPPORTIVE vs MIXED/WEAK trend component |
| `continuation_quality.persistence.state` | SI | PRIMARY | SUPPORTIVE/MIXED/WEAK continuation persistence component |
| `continuation_quality.acceleration_state.state` | SI | PRIMARY | ACCELERATING/MIXED/DECELERATING deterioration component |
| `continuation_quality.participation_quality.state` | SI | PRIMARY | SUPPORTIVE/MIXED/WEAK participation component |
| `continuation_quality.relative_strength.state` | SI | SUPPORTING | Relative strength context when connected |
| `downside_risk.participation_risk.state` | SI | PRIMARY | ELEVATED_RISK / HIGH_RISK deterioration component |
| `downside_risk.reversal_risk.state` | SI | SUPPORTING | Short-reversal context |
| `downside_risk.volatility_risk.state` | SI | SUPPORTING | Volatility risk context |
| `downside_risk.event_uncertainty.state` | SI | SUPPORTING | Special-risk / event uncertainty context |
| `entry_admission.entry_state` | SI | RECOVERY / PRIMARY | `HEALTHY_CONTINUATION_ENTRY` supports recovery; caution states support weakening |
| `entry_admission.admission_action` | SI | RECOVERY / PRIMARY | `ADD_ALLOWED` supports recovery; `ADD_REDUCED_ONLY` / `NO_ADD` supports caution |
| `profit_protection_evidence.continuation_deterioration_connection` | SI | PRIMARY | Existing deterioration dimensions: WEAK, DECELERATING, ELEVATED_RISK |
| `profit_protection_evidence.downside_risk_rise_connection` | SI | PRIMARY | Existing risk-rise dimensions: ELEVATED_RISK / HIGH_RISK |
| `strategy_intelligence_current_campaign_relative_return` | PM-attached SI lifecycle | SUPPORTING | Current PIT campaign context; not threshold-selected here |
| `strategy_intelligence_observed_campaign_mfe` | PM-attached SI lifecycle | SUPPORTING | PIT MFE context; no future MFE |
| `strategy_intelligence_observed_giveback` | PM-attached SI lifecycle | SUPPORTING | PIT giveback context; no future peak |
| PM HOLD/ADD reasons `structured_hold_worthiness_pass`, `trend_continuation`, `downside_risk_contained`, `positive_expected_edge`, `strong_trend_continuation`, `opportunity_rank_still_high` | PM | RECOVERY | Fresh recovery/reset/decay evidence |
| PM REDUCE reasons `risk_increased_but_trend_not_broken`, `peak_drawdown_warning` | PM | PRIMARY | Weakening while intact / risk review evidence |
| PM EXIT reasons `trend_and_opportunity_broken`, `weak_hold_score`, `profit_retention_break`, `hard_stop_current_return` | PM | PRIMARY | Same-day EXIT-grade reason families |
| Market Context regime | `strategy/market_context.json` | OBSERVABILITY_ONLY for F1C | Not connected as SELL authority in F1C |

## AGGREGATE_PASS_SEMANTICS

```text
AGGREGATE_PASS_SEMANTICS = EVIDENCE_AVAILABLE_NOT_HEALTH_SIGNAL
```

Contract:

- `continuation_quality_status = PASS` means required continuation evidence is sufficiently available / non-blocking.
- `downside_risk_status = PASS` means required downside evidence is sufficiently available / non-blocking.
- Neither field alone means `HEALTHY_OR_RECOVERING`.
- Neither field alone blocks `REDUCE`.
- Neither field alone blocks `EXIT_GRADE`.
- Neither field alone proves recovery.

This formalizes the F1B finding that PM REDUCE and aggregate SI PASS are not contradictory.

## PERSISTENT_DETERIORATION_DEFINITION

```text
PERSISTENT_DETERIORATION_DEFINITION = campaign-scoped repeated fresh unrepresentable PM REDUCE with current nested deterioration evidence, recovery guard absent, PIT proof complete, and no hidden deterioration debt
```

`PERSISTENT_DETERIORATION` is a semantic composition, not a numeric count rule. It requires all of:

1. Current PM action is `REDUCE`.
2. Current PS representability says the partial REDUCE cannot be represented, with family identified as `DISCRETE_LOT` or separately unresolved `MINIMUM_NOTIONAL`.
3. The same campaign has prior fresh PM REDUCE evidence before the current business date.
4. Current PM reason or nested SI/profit-protection evidence still shows deterioration or risk review.
5. No fresh recovery guard is present.
6. PIT proof is complete for the business date and does not use future-known data.

Deterioration dimensions may include:

- PM `risk_increased_but_trend_not_broken`;
- PM `peak_drawdown_warning`;
- SI participation `WEAK`;
- SI participation risk `ELEVATED_RISK`;
- SI acceleration `DECELERATING`;
- profit-protection continuation deterioration connection;
- profit-protection downside risk rise connection;
- PIT current relative return / observed giveback context.

F1C does not define "N of M dimensions" or select a duration threshold. If a numeric threshold becomes unavoidable, it remains parameter-unresolved for validation.

## EXIT_GRADE_DEFINITION

```text
EXIT_GRADE_DEFINITION = same-day PM EXIT reason family or equivalent current PIT severe deterioration state owned by PM
```

Current canonical EXIT-grade PM families:

- `trend_and_opportunity_broken`
- `weak_hold_score`
- `profit_retention_break`
- `hard_stop_current_return`

Trace-contract canonical equivalents:

- `trend_and_expected_edge_broken`
- `EXIT_BY_WEAK_HOLD_SCORE`
- `peak_drawdown_profit_retention_risk` when PM resolves it as EXIT-grade risk review
- `hard_stop_current_return` / `RISK_OVERRIDE`

Important boundary:

- If same-day `EXIT_GRADE` evidence is already present, PM should emit `EXIT` directly.
- Alternative G must not duplicate PM EXIT logic.
- Runtime and PS must never reinterpret REDUCE into EXIT.

## STATE_TRANSITION_CONTRACT

Allowed transitions:

| From | To | Condition |
|---|---|---|
| `HEALTHY_OR_RECOVERING` | `WEAKENING_BUT_INTACT` | fresh PM REDUCE / risk-review evidence appears |
| `WEAKENING_BUT_INTACT` | `HEALTHY_OR_RECOVERING` | fresh HOLD/ADD-compatible recovery evidence appears |
| `WEAKENING_BUT_INTACT` | `PERSISTENT_DETERIORATION` | repeated campaign-scoped unrepresentable REDUCE plus continuing deterioration, no recovery |
| `WEAKENING_BUT_INTACT` | `EXIT_GRADE` | same-day PM EXIT-grade reason family appears |
| `PERSISTENT_DETERIORATION` | `HEALTHY_OR_RECOVERING` | recovery guard reset/decay resolves the deterioration pressure |
| `PERSISTENT_DETERIORATION` | `EXIT_GRADE` | PM-owned severe deterioration evidence resolves |
| `EXIT_GRADE` | `EXIT` | PM emits EXIT; PS/Runtime faithfully materialize/execute |
| Any state | `UNRESOLVED` | PIT proof incomplete or representability/recovery/deterioration family ambiguous |

Forbidden transitions:

- `ONE_LOT` directly to `EXIT`.
- `REDUCE count >= N` directly to `EXIT`.
- Runtime-created `EXIT`.
- PS-created `EXIT`.
- Hidden accumulated deterioration debt that survives fresh recovery without explicit reset/decay state.

## RECOVERY_RESET_POLICY

```text
RECOVERY_RESET_POLICY = MIXED
```

Design:

- `RESET` when PM emits fresh `HOLD` or `ADD` with recovery-compatible reasons such as `structured_hold_worthiness_pass`, `trend_continuation`, `downside_risk_contained`, `positive_expected_edge`, `strong_trend_continuation`, or `opportunity_rank_still_high`, and no same-day EXIT-grade reason exists.
- `DECAY` when recovery evidence is partial or mixed: for example `HOLD` after REDUCE with remaining profit-protection risk connections, or `entry_admission` remains cautionary but PM no longer chooses REDUCE.
- `PRESERVE` when current action remains `REDUCE`, representability remains impossible, and no recovery-compatible PM or nested SI evidence appears.

This policy follows current HOLD/ADD semantics and the winner-protection objective. It is not selected from later performance.

## ESCALATION_OWNER

```text
ESCALATION_OWNER = PM
```

Responsibility boundary:

| Layer | Responsibility |
|---|---|
| Strategy Intelligence / semantic producer | Produce canonical SELL state from existing PIT evidence; no direct order authority |
| PM | Consume canonical SELL state and own final HOLD/ADD/REDUCE/EXIT action |
| PC / PS | Materialize quantity and representability; no EXIT invention |
| Runtime | Faithfully carry PM/PS decisions to planning/submission; no SELL semantic reinterpretation |
| Alternative G | PM escalation support / non-mutating shadow evidence until explicitly promoted |

## ALTERNATIVE_G_INTEGRATION_CONTRACT

Alternative G may advance to a PM EXIT candidate only when all conditions hold:

1. Current PM action is `REDUCE`.
2. Partial REDUCE is unrepresentable.
3. Canonical SELL state is `PERSISTENT_DETERIORATION` or `EXIT_GRADE`.
4. Recovery guard is absent.
5. PIT proof is complete.
6. PM owns and emits the final EXIT decision.

```text
ONE_LOT_AUTOMATIC_EXIT = NO
REDUCE_COUNT_ONLY_EXIT = NO
```

`ONE_LOT` is representability evidence only. REDUCE count is persistence observability only. Neither is action authority.

## 61750_STATE_MAPPING

61750 current-window evidence:

- 19 REDUCE rows from 2022-09-13 through 2022-10-12.
- All rows were `LIGHT` REDUCE.
- PM reasons were `risk_increased_but_trend_not_broken` plus SI sell-side evidence connection.
- Aggregate SI fields stayed `continuation_quality_status = PASS`, `downside_risk_status = PASS`, `profit_protection_status = OBSERVED`.
- PIT profit-protection evidence showed `WEAK` continuation connection on most rows and `ELEVATED_RISK` downside-risk-rise connection on most rows.
- Current campaign relative return remained near flat, and observed giveback rose to about 0.33%.
- No same-day PM EXIT-grade reason family appeared.

Dry mapping:

| Date | Canonical SELL state | Basis |
|---|---|---|
| 2022-09-13 | `WEAKENING_BUT_INTACT` | First REDUCE; risk increased but trend not broken; no prior persistence |
| 2022-09-14 | `PERSISTENT_DETERIORATION` / `UNRESOLVED_FOR_EXIT` | Prior unrepresentable REDUCE exists; no EXIT-grade reason; persistence parameter unresolved |
| 2022-09-15 | `PERSISTENT_DETERIORATION` / `UNRESOLVED_FOR_EXIT` | Same |
| 2022-09-16 | `PERSISTENT_DETERIORATION` / `UNRESOLVED_FOR_EXIT` | Same |
| 2022-09-20 | `PERSISTENT_DETERIORATION` / `UNRESOLVED_FOR_EXIT` | Same; deterioration connections include WEAK/DECELERATING/ELEVATED_RISK |
| 2022-09-21 | `PERSISTENT_DETERIORATION` / `UNRESOLVED_FOR_EXIT` | Same |
| 2022-09-22 | `PERSISTENT_DETERIORATION` / `UNRESOLVED_FOR_EXIT` | Same |
| 2022-09-26 | `PERSISTENT_DETERIORATION` / `UNRESOLVED_FOR_EXIT` | Same; relative return slightly negative and giveback higher, not threshold-selected |
| 2022-09-27 | `PERSISTENT_DETERIORATION` / `UNRESOLVED_FOR_EXIT` | Same |
| 2022-09-28 | `PERSISTENT_DETERIORATION` / `UNRESOLVED_FOR_EXIT` | Same |
| 2022-09-29 | `PERSISTENT_DETERIORATION` / `UNRESOLVED_FOR_EXIT` | Same |
| 2022-09-30 | `PERSISTENT_DETERIORATION` / `UNRESOLVED_FOR_EXIT` | Same |
| 2022-10-03 | `PERSISTENT_DETERIORATION` / `UNRESOLVED_FOR_EXIT` | Same |
| 2022-10-04 | `PERSISTENT_DETERIORATION` / `UNRESOLVED_FOR_EXIT` | Same |
| 2022-10-05 | `PERSISTENT_DETERIORATION` / `UNRESOLVED_FOR_EXIT` | Same; continuation connection absent but risk-rise remains elevated |
| 2022-10-06 | `PERSISTENT_DETERIORATION` / `UNRESOLVED_FOR_EXIT` | Same |
| 2022-10-07 | `PERSISTENT_DETERIORATION` / `UNRESOLVED_FOR_EXIT` | Same; downside-risk-rise connection absent but WEAK continuation remains |
| 2022-10-11 | `PERSISTENT_DETERIORATION` / `UNRESOLVED_FOR_EXIT` | Same |
| 2022-10-12 | `PERSISTENT_DETERIORATION` / `UNRESOLVED_FOR_EXIT` | Same |

```text
61750_EXIT_GRADE_REACHED = NO
```

61750 reaches persistent unresolved deterioration under the F1C semantic design, but it does not reach same-day `EXIT_GRADE` in the audited evidence. F1C therefore creates no EXIT date for 61750.

## Recovery Controls

```text
RECOVERY_CONTROL_COUNT = 17
RECOVERY_CONTROL_SEMANTIC_FALSE_ESCALATION_COUNT = 0
```

F1A identified 17 recovery-control campaigns. F1C preserves the same protection by requiring fresh recovery-compatible PM/HOLD/ADD or nested recovery evidence to reset/decay persistent pressure, and by forbidding unrepresentability-only EXIT.

The design does not tune itself to the recovery controls. It preserves the prior F1/F1A winner-protection rule as a first-principles contract.

## EXIT Controls

```text
EXIT_CONTROL_ALIGNMENT = PASS
```

The target run contains 60 PM EXIT rows. All 60 include at least one current PM EXIT-grade reason family:

| EXIT-grade reason | Count |
|---|---:|
| `trend_and_opportunity_broken` | 22 |
| `weak_hold_score` | 18 |
| `profit_retention_break` | 15 |
| `hard_stop_current_return` | 11 |

This confirms that same-day `EXIT_GRADE` can be aligned with current PM EXIT reason families without using later outcome.

## PARAMETER_UNRESOLVED

Remaining unresolved parameters:

- persistence minimum;
- recent-window length;
- deterioration composition sufficiency;
- recovery reset versus decay strength in mixed cases;
- representation-error materiality;
- minimum-notional escalation/materiality policy;
- whether PM trace score fields should be required before mutating behavior;
- validation acceptance criteria for shadow-to-mutation promotion.

These must not be selected from later PnL, later price, later delisting, or final campaign outcome.

## Minimum-Notional

```text
MINIMUM_NOTIONAL_POLICY_CHANGED = NO
```

Minimum-notional zero REDUCE remains a separate adjacent family. F1C may map it to SELL deterioration semantics for observability, but it does not merge minimum-notional execution policy with one-lot/discrete-lot escalation.

## Market Context

```text
MARKET_CONTEXT_LOGIC_CHANGED = NO
```

F0 found `MARKET_CONTEXT_SELL_AUTHORITY = NONE` in the current target run. F1C therefore does not connect Market Context as SELL authority. Canonical SELL deterioration/recovery is first defined from individual-symbol PIT evidence. Market Context SELL authority remains future F2 work.

## Implementation Boundary

F1C is design only. Future implementation should avoid legacy parallel authorities:

1. Strategy Intelligence or a dedicated semantic producer materializes canonical SELL state from existing PIT fields.
2. PM consumes that state and remains the only owner of HOLD/ADD/REDUCE/EXIT.
3. PS consumes PM intent and materializes quantity / representability only.
4. Runtime preserves the upstream action and never invents EXIT.
5. Alternative G remains non-mutating support until promoted by an explicit validation phase.

## Required Output

```text
PRIMARY_JUDGMENT = PHASE31_F1C_CANONICAL_SELL_SEMANTIC_CONTRACT_DEFINED_PIT_MAPPING_READY_FOR_SHADOW
CANONICAL_SELL_STATES = HEALTHY_OR_RECOVERING; WEAKENING_BUT_INTACT; PERSISTENT_DETERIORATION; EXIT_GRADE; UNRESOLVED
STATE_FIELD_MAPPING = PM action/reasons/intensity/confidence; PS representability fields; SI nested continuation/downside/profit-protection fields; lifecycle return/MFE/giveback; PM recovery and EXIT reason families
AGGREGATE_PASS_SEMANTICS = EVIDENCE_AVAILABLE_NOT_HEALTH_SIGNAL
PERSISTENT_DETERIORATION_DEFINITION = campaign-scoped repeated fresh unrepresentable PM REDUCE with current nested deterioration evidence, recovery guard absent, PIT proof complete, and no hidden deterioration debt
EXIT_GRADE_DEFINITION = same-day PM EXIT reason family or equivalent current PIT severe deterioration state owned by PM
STATE_TRANSITION_CONTRACT = HEALTHY_OR_RECOVERING <-> WEAKENING_BUT_INTACT; WEAKENING_BUT_INTACT -> PERSISTENT_DETERIORATION; PERSISTENT_DETERIORATION -> HEALTHY_OR_RECOVERING; PERSISTENT_DETERIORATION -> EXIT_GRADE; EXIT_GRADE -> EXIT; unresolved proof -> UNRESOLVED
RECOVERY_RESET_POLICY = MIXED
ESCALATION_OWNER = PM
ALTERNATIVE_G_INTEGRATION_CONTRACT = REDUCE + unrepresentable partial REDUCE + PERSISTENT_DETERIORATION/EXIT_GRADE + no recovery guard + PIT proof complete, with PM-owned final EXIT only
ONE_LOT_AUTOMATIC_EXIT = NO
REDUCE_COUNT_ONLY_EXIT = NO
61750_STATE_MAPPING = 2022-09-13 WEAKENING_BUT_INTACT; 2022-09-14 through 2022-10-12 PERSISTENT_DETERIORATION/UNRESOLVED_FOR_EXIT
61750_EXIT_GRADE_REACHED = NO
RECOVERY_CONTROL_COUNT = 17
RECOVERY_CONTROL_SEMANTIC_FALSE_ESCALATION_COUNT = 0
EXIT_CONTROL_ALIGNMENT = PASS
PARAMETER_UNRESOLVED = persistence minimum; recent-window length; deterioration composition sufficiency; recovery reset/decay strength; representation-error materiality; minimum-notional policy; trace-score requirement; validation acceptance criteria
MINIMUM_NOTIONAL_POLICY_CHANGED = NO
MARKET_CONTEXT_LOGIC_CHANGED = NO
FUTURE_INFORMATION_USED_FOR_DESIGN = NO
OUTCOME_USED_FOR_PARAMETER_SELECTION = NO
IMPLEMENTATION_CHANGED = NO
LONG_HISTORICAL_EXECUTED = NO
NEXT_TASK_RECOMMENDATION = Phase31-F1D non-mutating canonical SELL semantic shadow implementation / validation
```

## Final Questions

1. 既存PIT evidenceだけでSELL deterioration stateを定義できるか？

   Yes. Existing PIT evidence is sufficient to define the semantic state contract, though mutation parameters remain unresolved.

2. PASSを「健康」と誤解しない契約になったか？

   Yes. Aggregate PASS is formally `EVIDENCE_AVAILABLE_NOT_HEALTH_SIGNAL`.

3. WEAKENINGとPERSISTENT_DETERIORATIONを意味的に分離できるか？

   Yes. `WEAKENING_BUT_INTACT` is current de-risk pressure without persistence; `PERSISTENT_DETERIORATION` requires campaign-scoped repeated fresh unrepresentable REDUCE, continuing deterioration evidence, no recovery guard, and complete PIT proof. The exact mutation threshold remains unresolved.
