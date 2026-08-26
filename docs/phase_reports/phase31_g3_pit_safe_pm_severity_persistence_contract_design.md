# Phase31-G3 — PIT-Safe PM Severity / Persistence Contract Design

## Scope

Task type: READ-ONLY ARCHITECTURE / STRATEGY CONTRACT DESIGN.

Target run:

`runtime-test-historical-extended-smoke-20260821T095536206137Z`

Read:

- `docs/phase_reports/phase31_g0_clean_100bd_strategy_performance_causal_decomposition_audit.md`
- `docs/phase_reports/phase31_g1_pit_safe_pm_failure_winner_retention_separability_audit.md`
- `docs/phase_reports/phase31_g2_pit_safe_pm_severity_persistence_hold_regret_audit.md`
- `src/ai_fund_lab_v2/strategy/sell_semantic_state.py`
- `src/ai_fund_lab_v2/strategy/position_management.py`
- `src/ai_fund_lab_v2/strategy/shadow_runtime.py`
- F1E/F1G canonical SELL semantic reports

No implementation, Strategy mutation, PM behavior mutation, SELL rule mutation, threshold tuning, weight tuning, config mutation, feature addition, model retraining, Runtime mutation, fresh-run, resume, replay, or Historical rerun was performed.

## Primary Judgment

`PRIMARY_JUDGMENT = PHASE31_G3_PM_SEVERITY_PERSISTENCE_CONTRACT_READY_FOR_FOCUSED_IMPLEMENTATION`

G3 design is ready for a focused implementation phase because it does not require a 100BD-derived numeric threshold, does not introduce a second SELL classifier, preserves F1F/F1I authority, explicitly protects winners, uses strict-prior persistence, and keeps recovery/de-escalation in the contract.

## Authority Preservation

Current Production owner:

- canonical SELL semantic owner: `strategy.sell_semantic_state`
- contract version: `phase31_f1f_pm_canonical_sell_semantic_integration_v1`
- PM mutation point: `position_management._apply_canonical_sell_semantics`
- campaign lifecycle/history authority: `positions/position_campaigns.json`, with strict-prior PM evidence from F1I
- final PM action authority: PM
- execution feasibility / quantity: PS and Runtime SELL planning

G3 must extend the existing PM-owned semantic layer. It must not create PS/Runtime EXIT invention and must not consume diagnostic shadow artifacts as Production authority.

`CANONICAL_SELL_STATE_OWNER_PRESERVED = YES`

`F1F_F1I_AUTHORITY_PRESERVED = YES`

`PS_RUNTIME_EXIT_INVENTION = NO`

## State vs Severity

G3 separates the semantic condition from PM reaction strength:

| Layer | Meaning | Owner |
| --- | --- | --- |
| `SELL_STATE` | What condition exists: healthy, weakening, persistent deterioration, exit-grade. | `strategy.sell_semantic_state` |
| `PM_SEVERITY` | How strongly PM should react given campaign economics, persistence, recovery, and regime context. | PM severity contract consumed by PM |
| `PM_ACTION` | Final action: HOLD, ADD, REDUCE, EXIT, UNRESOLVED. | PM |

State alone must not create faster EXIT.

`STATE_SEVERITY_SEPARATION = YES`

`STATE_ALONE_ESCALATION = PROHIBITED`

## Campaign Return Role

`current_campaign_relative_return` has architectural meaning as campaign-basis economics: above basis means PM is managing a profitable campaign and must preserve winner optionality; below basis means the position is both semantically deteriorating and failing relative to its own acquisition basis.

It must not become:

```text
if current_campaign_relative_return < 0: EXIT
```

It may only modify severity when paired with canonical deterioration state and current PIT evidence.

`CAMPAIGN_RETURN_ROLE = SEVERITY_MODIFIER_NOT_PRIMARY_SELL_SIGNAL`

`CAMPAIGN_BASIS_SIGN_SEMANTIC_JUSTIFICATION = SUPPORTED`

This support is philosophical and architectural, not optimized from G2: profit/loss relative to campaign basis is a natural PM distinction between protecting a winner and recovering capital from a failed position.

## Persistence Contract

Persistence must use strict-prior campaign evidence. Same-day current evidence may classify today's state, but it must not count itself as prior persistence.

Allowed persistence concepts:

| Persistence state | Meaning |
| --- | --- |
| `FIRST_OBSERVATION` | Current deterioration observed, no strict-prior active deterioration evidence. |
| `REPEATED_OBSERVATION` | Strict-prior same-campaign deterioration evidence exists, but no worsening/persistent classification yet. |
| `PERSISTENT` | Strict-prior same-campaign deterioration plus current deterioration, recovery absent, campaign identity complete. |
| `WORSENING` | Current state is stronger than strict-prior state, e.g. WEAKENING -> PERSISTENT/EXIT_GRADE. |
| `RECOVERED` | Strict-prior pressure is cleared or decayed by fresh recovery evidence. |

Strict-prior evidence sources:

- prior `positions/position_campaigns.json`
- strict-prior PM decision evidence events from F1I
- prior same-campaign `canonical_sell_state`
- prior same-campaign PM action / representability evidence
- recovery boundaries where `same_day_self_count_protected = true`

`PERSISTENCE_USES_STRICT_PRIOR_EVIDENCE = YES`

`SAME_DAY_SELF_COUNT = NO`

`REDUCE_COUNT_ALONE_ESCALATION = PROHIBITED`

## Recovery Reset

Recovery must be able to de-escalate severity. A position cannot carry permanent hidden deterioration debt.

Reset types:

| Reset type | Meaning |
| --- | --- |
| `FULL` | Fresh `HEALTHY_OR_RECOVERING` with recovery-compatible reasons clears active persistence pressure. |
| `PARTIAL` | Mixed evidence reduces severity but retains trace evidence for audit; later escalation needs fresh current deterioration. |
| `STATE_DEPENDENT` | Stronger prior states may require explicit recovery boundary or repeated healthy evidence before full reset. |

Current architecture already has `recovery_state`, `recovery_dimensions.reset_policy`, and F1I `RECOVERY_BOUNDARY` events. G3 should use those instead of inventing a new recovery source.

`RECOVERY_CAN_DEESCALATE_SEVERITY = YES`

`RECOVERY_RESET_TYPE = STATE_DEPENDENT`

## Invariants

Winner preservation invariant:

- profitable weakening must not automatically become EXIT
- mixed evidence should preserve optionality
- full EXIT requires canonical EXIT authority or a strict severity/persistence gate
- observed-to-date giveback may justify profit-protection REDUCE, not future-peak-based EXIT

`WINNER_PRESERVATION_INVARIANT = YES`

Loser capital-recovery invariant:

- if a campaign is deteriorating, economically failing, not recovering, and persistently weak, PM may escalate severity toward capital recovery
- PM must not issue ineffective REDUCE forever when PIT evidence supports stronger deterioration
- lot constraints, minimum-notional constraints, execution feasibility, and safety authority remain preserved

`LOSER_CAPITAL_RECOVERY_INVARIANT = YES`

Healthy pullback protection:

- temporary non-healthy state
- still-positive campaign economics
- continuation/downside evidence not structurally broken
- no strict-prior persistent worsening

should avoid premature full EXIT.

`HEALTHY_PULLBACK_PROTECTION = YES`

## Winner Profit Protection

For profitable campaigns, only observed-to-date profit/giveback may affect severity. Future MFE, final PnL, and future return are prohibited.

Profitable weakening may support:

- WATCH / CAUTION when deterioration is first observed
- REDUCE / profit-protection when giveback is observed to date and deterioration persists
- EXIT candidate only when canonical SELL state reaches `EXIT_GRADE` or a separate strict PM gate is satisfied

No numeric giveback threshold is selected in G3.

`WINNER_PROFIT_PROTECTION_USES_OBSERVED_TO_DATE_ONLY = YES`

## Regime Role

Market Context is a severity confirmation modifier, not SELL authority.

Same deterioration may carry higher severity confidence in RANGE/CORRECTION/BEAR than in BULL/RECOVERY, but:

```text
REGIME == BEAR -> EXIT
```

is forbidden.

`REGIME_ROLE = SEVERITY_CONFIRMATION_MODIFIER`

## PM Severity State Machine

Minimal severity states:

| PM severity | Required evidence family | Allowed actions | Escalation | De-escalation | Winner protection |
| --- | --- | --- | --- | --- | --- |
| `PM_SEVERITY_NORMAL` | `HEALTHY_OR_RECOVERING` or no deterioration; PIT proof PASS | HOLD / ADD / existing PM action | new deterioration appears | recovery remains present | default winner preservation |
| `PM_SEVERITY_CAUTION` | `WEAKENING_BUT_INTACT` or non-healthy first observation; campaign return positive or mixed; continuation/downside not broken | HOLD / REDUCE | negative campaign economics, adverse regime confirmation, or repeated deterioration | return to `HEALTHY_OR_RECOVERING`, recovery boundary, deterioration reasons disappear | no full EXIT from state alone |
| `PM_SEVERITY_DEFENSIVE` | non-healthy state plus economic failure relative to campaign basis, or repeated unrecovered weakening; PIT proof PASS | REDUCE; preserve optionality if representable and recovery possible | strict-prior persistence, worsening state, no recovery, representability constraints | recovery boundary or positive/mixed economics with restored continuation | REDUCE preferred before EXIT unless EXIT authority exists |
| `PM_SEVERITY_EXIT_CANDIDATE` | `EXIT_GRADE`, or `PERSISTENT_DETERIORATION` plus PM-owned gate evidence; recovery absent; campaign identity complete; PIT proof PASS | EXIT where PM authority supports it | final PM EXIT through `_apply_canonical_sell_semantics` | de-escalate only if current evidence resolves before materialization; otherwise EXIT | no EXIT if evidence missing/ambiguous |
| `PM_SEVERITY_UNRESOLVED` | missing/ambiguous campaign, PIT, state, return, or conflicting recovery/deterioration | preserve / review | none | evidence repair | no silent EXIT |

`PM_SEVERITY_STATE_MACHINE = NORMAL; CAUTION; DEFENSIVE; EXIT_CANDIDATE; UNRESOLVED`

## Action Mapping

| Severity | PM action mapping |
| --- | --- |
| `NORMAL` | preserve baseline HOLD/ADD/REDUCE/EXIT authority |
| `CAUTION` | HOLD or REDUCE; no automatic full EXIT |
| `DEFENSIVE` | REDUCE when representable; if unrepresentable, preserve lineage and require persistence/PM gate before EXIT |
| `EXIT_CANDIDATE` | EXIT only through canonical PM authority: direct `EXIT_GRADE` or F1F-compatible PM gate |
| `UNRESOLVED` | REVIEW_REQUIRED / preserve; no silent EXIT |

Severity must not override hard safety, corporate action, execution feasibility, minimum-notional, Pending, Submit, or Runtime safety contracts.

`PM_SEVERITY_ACTION_MAPPING = NORMAL->HOLD/ADD; CAUTION->HOLD/REDUCE; DEFENSIVE->REDUCE; EXIT_CANDIDATE->PM_EXIT_WHEN_AUTHORIZED; UNRESOLVED->REVIEW_OR_PRESERVE`

## Authority Map

| Concern | Owner | Notes |
| --- | --- | --- |
| Canonical SELL state | `strategy.sell_semantic_state` | No second classifier. |
| Campaign economic severity | PM severity contract consuming Strategy Intelligence campaign fields | Modifier only. |
| Persistence history | `positions/position_campaigns.json` plus F1I strict-prior PM evidence | Same-day self count prohibited. |
| Recovery boundary | canonical SELL semantic + F1I recovery event | Can reset/de-escalate. |
| Regime modifier | Market Context | Modifier only, no SELL authority. |
| Final PM action | `position_management` | Only PM mutates REDUCE -> EXIT. |
| Quantity/representability | PS / sell planning | No EXIT invention. |
| Execution feasibility | Runtime / Pending / Submit | No SELL authority creation. |

`PM_SEVERITY_AUTHORITY_MAP = SELL_STATE:strategy.sell_semantic_state; SEVERITY:PM_CONTRACT; HISTORY:positions/position_campaigns+F1I; REGIME:Market_Context_modifier; ACTION:PM; FEASIBILITY:PS/Runtime`

## Failure Modes

| Missing/ambiguous evidence | Required behavior |
| --- | --- |
| Missing canonical SELL state | `PM_SEVERITY_UNRESOLVED`; no EXIT |
| Missing campaign history | review/preserve; no persistence escalation |
| Missing current campaign return | state may still REDUCE/EXIT if canonical authority exists, but severity modifier unavailable; no severity-based EXIT |
| Ambiguous basis | review/preserve |
| Missing Market Context | continue without regime modifier or review if contract requires regime; no EXIT from missing regime |
| Malformed state | review/preserve |
| Execution unavailable | respect Runtime/Pending terminal semantics; no PM invention |
| Recovery ambiguity | do not escalate beyond existing PM action without explicit lineage |

`MISSING_EVIDENCE_AUTO_EXIT = NO`

## Future Winner Preservation Test Gate

Future implementation must include tests proving:

- state-only weakening does not force EXIT
- profitable weakening can preserve optionality
- recovery de-escalates severity
- strict-prior persistence only; same-day self count is rejected
- persistent deteriorating loser can escalate
- regime alone cannot force EXIT
- REDUCE count alone cannot force EXIT
- observed-to-date giveback is allowed, future MFE/final PnL is not
- missing campaign return does not auto-EXIT
- F1F/F1I discrete-lot escalation remains preserved

`FUTURE_WINNER_PRESERVATION_TEST_GATE = REQUIRED`

## Cross-Window Validation Contract

Future implementation must not be accepted solely because this 100BD window improves. Acceptance must include:

- at least one additional time window
- long-horizon validation
- regime diversity
- winner collateral accounting
- loss reduction accounting
- MDD/drawdown review
- turnover/churn review
- no future-information production inputs

No numeric pass threshold is selected in G3.

`CROSS_WINDOW_VALIDATION_REQUIRED = YES`

## Implementation Readiness

`IMPLEMENTATION_READINESS = READY_FOR_FOCUSED_IMPLEMENTATION`

Allowed future implementation scope:

- extend canonical PM evidence with `pm_severity` and evidence lineage
- consume existing `canonical_sell_state`, campaign economics, F1I strict-prior history, recovery state, and Market Context modifier
- update focused PM tests

Forbidden:

- BUY changes
- Candidate changes
- model retraining
- new indicators
- 100BD-derived numeric thresholds
- PS/Runtime EXIT invention
- fresh-run/resume/replay as part of design

## Required Summary Output

`PRIMARY_JUDGMENT = PHASE31_G3_PM_SEVERITY_PERSISTENCE_CONTRACT_READY_FOR_FOCUSED_IMPLEMENTATION`

`CANONICAL_SELL_STATE_OWNER_PRESERVED = YES`

`STATE_SEVERITY_SEPARATION = YES`

`CAMPAIGN_RETURN_ROLE = SEVERITY_MODIFIER_NOT_PRIMARY_SELL_SIGNAL`

`CAMPAIGN_BASIS_SIGN_SEMANTIC_JUSTIFICATION = SUPPORTED`

`PERSISTENCE_USES_STRICT_PRIOR_EVIDENCE = YES`

`SAME_DAY_SELF_COUNT = NO`

`RECOVERY_CAN_DEESCALATE_SEVERITY = YES`

`RECOVERY_RESET_TYPE = STATE_DEPENDENT`

`WINNER_PRESERVATION_INVARIANT = YES`

`LOSER_CAPITAL_RECOVERY_INVARIANT = YES`

`REDUCE_COUNT_ALONE_ESCALATION = PROHIBITED`

`WINNER_PROFIT_PROTECTION_USES_OBSERVED_TO_DATE_ONLY = YES`

`REGIME_ROLE = SEVERITY_CONFIRMATION_MODIFIER`

`HEALTHY_PULLBACK_PROTECTION = YES`

`PM_SEVERITY_STATE_MACHINE = NORMAL; CAUTION; DEFENSIVE; EXIT_CANDIDATE; UNRESOLVED`

`PM_SEVERITY_ACTION_MAPPING = NORMAL->HOLD/ADD; CAUTION->HOLD/REDUCE; DEFENSIVE->REDUCE; EXIT_CANDIDATE->PM_EXIT_WHEN_AUTHORIZED; UNRESOLVED->REVIEW_OR_PRESERVE`

`PM_SEVERITY_AUTHORITY_MAP = SELL_STATE:strategy.sell_semantic_state; SEVERITY:PM_CONTRACT; HISTORY:positions/position_campaigns+F1I; REGIME:Market_Context_modifier; ACTION:PM; FEASIBILITY:PS/Runtime`

`F1F_F1I_AUTHORITY_PRESERVED = YES`

`PS_RUNTIME_EXIT_INVENTION = NO`

`MISSING_EVIDENCE_AUTO_EXIT = NO`

`FUTURE_WINNER_PRESERVATION_TEST_GATE = REQUIRED`

`CROSS_WINDOW_VALIDATION_REQUIRED = YES`

`NEW_FEATURE_REQUIRED_NOW = NO`

`PRODUCTION_NUMERIC_THRESHOLD_SELECTED = NO`

`FUTURE_INFORMATION_USED_AS_PRODUCTION_INPUT = NO`

`IMPLEMENTATION_CHANGED = NO`

`FRESH_RUN_EXECUTED = NO`

`RESUME_EXECUTED = NO`

`LONG_HISTORICAL_EXECUTED = NO`

`IMPLEMENTATION_READINESS = READY_FOR_FOCUSED_IMPLEMENTATION`

`NEXT_TASK_RECOMMENDATION = Phase31-G4 focused implementation of the architecture-defined PM severity/persistence contract, limited to PM evidence/action severity, strict-prior persistence, recovery de-escalation, and focused winner-preservation tests`

