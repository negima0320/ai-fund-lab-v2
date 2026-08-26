# Phase31-G6 — G4 PM Severity Controlled 100BD Behavioral Activation / No-Delta Root-Cause Audit

## Scope

Task type: READ-ONLY old-vs-new controlled comparison / activation audit.

No implementation, threshold tuning, PM mutation, Strategy mutation, feature addition, fresh-run, resume, replay, or Historical rerun was performed.

Compared:

- OLD baseline: `runtime-test-historical-extended-smoke-20260821T095536206137Z`
- NEW G4 run: `runtime-test-historical-extended-smoke-20260822T044211130517Z`

Both runs used:

- `profile = historical-extended-smoke`
- `start-date = 2022-08-15`
- `business-days = 100`
- `initial-cash = 1,000,000`

## Primary Judgment

`PRIMARY_JUDGMENT = PHASE31_G6_G4_SEVERITY_MATERIALIZED_NO_ACTION_DELTA_EXPECTED`

G4 PM severity did materialize across the NEW 100BD run, including `DEFENSIVE` and `EXIT_CANDIDATE` rows. The no-delta result is not caused by missing severity evidence. It is caused by G4 being production-observable but not connected as an independent action mutation input. The final PM action still comes from the existing canonical SELL / F1F-F1I gate, and every OLD-vs-NEW PM action matched.

## Portfolio Equality

`PORTFOLIO_OUTPUT_EQUAL = YES`

| Metric | OLD | NEW | Delta |
| --- | ---: | ---: | ---: |
| Final equity | 1,171,580 | 1,171,580 | 0 |
| Total return | +17.158% | +17.158% | 0.000pp |
| Final cash | 361,610 | 361,610 | 0 |
| Final market value | 809,970 | 809,970 | 0 |
| Final position count | 9 | 9 | 0 |

`DAILY_EQUITY_DELTA_COUNT = 0`

`HOLDINGS_DELTA_DAY_COUNT = 0`

`FILL_DELTA_COUNT = 0`

`ORDER_DELTA_COUNT = 0`

`REALIZED_PNL_DELTA_COUNT = 0`

Execution/economic signatures were equal:

| Metric | OLD | NEW |
| --- | ---: | ---: |
| BUY fills | 166 | 166 |
| SELL fills | 176 | 176 |
| BUY quantity | 42,300 | 42,300 |
| SELL quantity | 40,200 | 40,200 |
| Realized slices | 176 | 176 |
| Gross realized PnL | 145,740 | 145,740 |

## PM Severity Materialization

`PM_SEVERITY_MATERIALIZED = YES`

NEW run PM rows: `905`.

`PM_SEVERITY_DISTRIBUTION = PM_SEVERITY_NORMAL 617; PM_SEVERITY_CAUTION 84; PM_SEVERITY_DEFENSIVE 47; PM_SEVERITY_EXIT_CANDIDATE 157; PM_SEVERITY_UNRESOLVED 0`

`PERSISTENCE_STATE_DISTRIBUTION = RECOVERED 617; FIRST_OBSERVATION 130; REPEATED_OBSERVATION 1; PERSISTENT 61; WORSENING 96`

PM action distributions were identical:

| Action | OLD | NEW |
| --- | ---: | ---: |
| HOLD | 543 | 543 |
| ADD | 74 | 74 |
| REDUCE | 131 | 131 |
| EXIT | 157 | 157 |

## PM Decision Diff

`PM_ACTION_DELTA_COUNT = 0`

`PM_ACTION_DELTA_TABLE = NONE`

No symbol/date PM row had an OLD vs NEW action or final PM action difference.

## Severity Without Action Delta

`SEVERITY_WITHOUT_ACTION_DELTA_COUNT = 204`

These were all NEW rows with `PM_SEVERITY_DEFENSIVE` or `PM_SEVERITY_EXIT_CANDIDATE` where OLD and NEW actions matched.

Representative rows:

| Date | Symbol | State | Severity | Persistence | Campaign return | OLD | NEW | Why unchanged |
| --- | --- | --- | --- | --- | ---: | --- | --- | --- |
| 2022-10-05 | 21380 | WEAKENING_BUT_INTACT | PM_SEVERITY_DEFENSIVE | FIRST_OBSERVATION | -3.04% | REDUCE | REDUCE | DEFENSIVE has no direct EXIT authority; baseline PM action already matched. |
| 2022-09-28 | 44220 | WEAKENING_BUT_INTACT | PM_SEVERITY_DEFENSIVE | FIRST_OBSERVATION | -4.14% | REDUCE | REDUCE | DEFENSIVE has no direct EXIT authority; baseline PM action already matched. |
| 2022-11-01 | 65790 | WEAKENING_BUT_INTACT | PM_SEVERITY_DEFENSIVE | FIRST_OBSERVATION | -6.22% | REDUCE | REDUCE | DEFENSIVE has no direct EXIT authority; baseline PM action already matched. |
| 2022-09-01 | 21950 | EXIT_GRADE | PM_SEVERITY_EXIT_CANDIDATE | WORSENING | -19.19% | EXIT | EXIT | Existing PM EXIT-grade authority already produced EXIT in OLD and NEW. |
| 2022-11-02 | 65790 | PERSISTENT_DETERIORATION | PM_SEVERITY_EXIT_CANDIDATE | PERSISTENT | -6.04% | EXIT | EXIT | Existing F1F/F1I gate already produced EXIT in OLD and NEW. |
| 2022-12-08 | 37790 | EXIT_GRADE | PM_SEVERITY_EXIT_CANDIDATE | WORSENING | -26.09% | EXIT | EXIT | Existing PM EXIT-grade authority already produced EXIT in OLD and NEW. |
| 2022-11-17 | 97310 | WEAKENING_BUT_INTACT | PM_SEVERITY_CAUTION | FIRST_OBSERVATION | +0.12% | REDUCE | REDUCE | Winner-protection label materialized, but baseline action was already REDUCE. |
| 2022-08-29 | 27670 | WEAKENING_BUT_INTACT | PM_SEVERITY_CAUTION | FIRST_OBSERVATION | +3.18% | REDUCE | REDUCE | Winner-protection label materialized, but baseline action was already REDUCE. |

## G4 Action-Mutation Connection

Code trace:

- `sell_semantic_state.evaluate_position_sell_semantic` computes `escalation = _escalation_decision(...)` before severity evidence is built.
- `_escalation_decision` consumes action, canonical state, representability, recovery, PIT, campaign validity, minimum-notional, and conflict flags. It does not consume `pm_severity`.
- `position_management._apply_canonical_sell_semantics` sets row `action` from `evidence["final_pm_action"]`, then attaches `pm_severity`, `pm_severity_reasons`, `pm_severity_evidence`, and `persistence_state`.

`PM_SEVERITY_PRODUCTION_CONSUMER = position_management._apply_canonical_sell_semantics materializes pm_severity fields; final action consumer remains canonical SELL/F1F evidence["final_pm_action"]`

`PM_SEVERITY_ACTION_MUTATION_CONNECTED = NO`

G4 is production-visible observability. It does not independently modify PM action or intensity.

## G3 Semantic Families in NEW Run

Using only NEW-run PIT evidence:

`ECONOMIC_FAILURE_SEVERITY_ROWS = 119`

`STRICT_PRIOR_PERSISTENT_ROWS = 61`

`WINNER_PROTECTION_CAUTION_ROWS = 84`

`RECOVERY_DEESCALATION_ROWS = 617`

`EXIT_CANDIDATE_ROWS = 157`

The intended G3 families do occur. They simply do not produce different final actions in G4.

## Representative G2 Cases

Loser / deterioration examples:

| Symbol | Timeline result |
| --- | --- |
| 21950 | 2022-09-01 `EXIT_GRADE / EXIT_CANDIDATE`, OLD EXIT = NEW EXIT. |
| 21380 | 2022-10-05 `WEAKENING / DEFENSIVE`, OLD REDUCE = NEW REDUCE; 2022-10-06 `EXIT_GRADE / EXIT_CANDIDATE`, OLD EXIT = NEW EXIT. |
| 65790 | 2022-11-01 `WEAKENING / DEFENSIVE`, OLD REDUCE = NEW REDUCE; 2022-11-02 `PERSISTENT / EXIT_CANDIDATE`, OLD EXIT = NEW EXIT. |
| 44220 | 2022-09-28 `WEAKENING / DEFENSIVE`, OLD REDUCE = NEW REDUCE; 2022-09-29 `EXIT_GRADE / EXIT_CANDIDATE`, OLD EXIT = NEW EXIT. |
| 96100 | 2022-09-01 `EXIT_GRADE / EXIT_CANDIDATE`, OLD EXIT = NEW EXIT. |
| 92420 | 2022-10-12 positive-return `WEAKENING / CAUTION`, OLD REDUCE = NEW REDUCE; 2022-10-13 `EXIT_GRADE / EXIT_CANDIDATE`, OLD EXIT = NEW EXIT. |
| 37790 | 2022-12-08 `EXIT_GRADE / EXIT_CANDIDATE`, OLD EXIT = NEW EXIT. |

Winner / optionality examples:

| Symbol | Timeline result |
| --- | --- |
| 62490 | Mostly `HEALTHY / NORMAL / RECOVERED`; OLD HOLD = NEW HOLD through inspected rows. |
| 69730 | 2022-11-15 and 2022-11-21 positive-return `WEAKENING / CAUTION`, OLD REDUCE = NEW REDUCE; recovery rows OLD HOLD = NEW HOLD. |
| 27670 | 2022-08-29 positive-return `WEAKENING / CAUTION`, OLD REDUCE = NEW REDUCE; later recovery rows OLD HOLD = NEW HOLD. |
| 27880 | 2022-08-31 and 2022-09-08 positive-return `WEAKENING / CAUTION`, OLD REDUCE = NEW REDUCE; 2022-09-09 `PERSISTENT / EXIT_CANDIDATE`, OLD EXIT = NEW EXIT. |
| 97310 | 2022-11-17 and 2022-12-14 positive-return `WEAKENING / CAUTION`, OLD REDUCE = NEW REDUCE; recovery rows OLD HOLD = NEW HOLD. |

G4 recognized the intended distinctions but left final actions unchanged.

## Existing PM Policy Equivalence

`PRE_G4_ACTION_POLICY_ALREADY_EQUIVALENT = YES`

For this controlled 100BD window, pre-G4 PM actions already matched the G4-labeled action surface:

- `WEAKENING_BUT_INTACT + negative return` already mapped to REDUCE, now labeled `DEFENSIVE`.
- `EXIT_GRADE` already mapped to EXIT, now labeled `EXIT_CANDIDATE`.
- F1F/F1I `PERSISTENT_DETERIORATION` already mapped to EXIT where the existing gate fired, now labeled `EXIT_CANDIDATE`.
- Positive-return weakening already remained REDUCE/HOLD behaviorally, now labeled `CAUTION`.
- Recovery already returned to HOLD/healthy behavior, now labeled `NORMAL / RECOVERED`.

## F1F Gate Interaction

`F1F_ESCALATION_OLD_COUNT = 61`

`F1F_ESCALATION_NEW_COUNT = 61`

`F1F_ESCALATION_DELTA_COUNT = 0`

G4 severity did not add or remove F1F/F1I escalations. The same campaigns reached the existing gate in both runs.

## Downstream Neutralization

`DOWNSTREAM_NEUTRALIZATION_COUNT = 0`

No PM action differences existed, so there was nothing for PS, SELL Planning, Pending, Submit, or Execution to neutralize. Downstream equality is a consequence of PM equality, not downstream cancellation.

## No-Delta Classification

`NO_DELTA_ROOT_CAUSE_CLASSIFICATION = MIXED`

Detailed classification:

- `EXPECTED_OBSERVABILITY_ONLY`: YES. G4 severity is materialized into PM evidence but is not an action mutation input.
- `EXPECTED_EXISTING_POLICY_EQUIVALENCE`: YES. In this 100BD window, OLD PM actions already matched all NEW severity-labeled rows.
- `IMPLEMENTATION_NOT_ACTION_CONNECTED`: YES, as a design fact, not necessarily a defect.
- `INSUFFICIENT_ACTIVATION_CASES`: NO. Activation cases existed: 204 DEFENSIVE/EXIT_CANDIDATE rows.
- `DOWNSTREAM_NEUTRALIZED`: NO. No PM deltas existed to neutralize.
- `IMPLEMENTATION_DEFECT`: NO evidence in G6. Severity materialized as designed by G4/G5.

## Performance Conclusion

`FINAL_EQUITY_OLD = 1,171,580`

`FINAL_EQUITY_NEW = 1,171,580`

`FINAL_EQUITY_DELTA = 0`

`TOTAL_RETURN_OLD = +17.158%`

`TOTAL_RETURN_NEW = +17.158%`

`TOTAL_RETURN_DELTA = 0.000pp`

`WINNER_DAMAGE_DELTA = 0`

`LOSER_LOSS_DELTA = 0`

Because PM, fills, holdings, and daily equity are equal, G4 provides no performance improvement or degradation in this controlled 100BD run.

## Next Design Gate

`NEXT_DESIGN_GATE = C`

`NEXT_TASK_RECOMMENDATION = Do not tune parameters. If behavioral change is desired, design a focused PM severity action-mapping implementation that explicitly connects PM_SEVERITY_DEFENSIVE / PM_SEVERITY_EXIT_CANDIDATE to PM-owned action changes while preserving G3 winner-protection and F1F/F1I authority.`

## Required Summary Output

`OLD_RUN_ID = runtime-test-historical-extended-smoke-20260821T095536206137Z`

`NEW_RUN_ID = runtime-test-historical-extended-smoke-20260822T044211130517Z`

`PORTFOLIO_OUTPUT_EQUAL = YES`

`FINAL_EQUITY_OLD = 1,171,580`

`FINAL_EQUITY_NEW = 1,171,580`

`FINAL_EQUITY_DELTA = 0`

`TOTAL_RETURN_DELTA = 0.000pp`

`DAILY_EQUITY_DELTA_COUNT = 0`

`HOLDINGS_DELTA_DAY_COUNT = 0`

`FILL_DELTA_COUNT = 0`

`PM_SEVERITY_MATERIALIZED = YES`

`PM_SEVERITY_DISTRIBUTION = PM_SEVERITY_NORMAL 617; PM_SEVERITY_CAUTION 84; PM_SEVERITY_DEFENSIVE 47; PM_SEVERITY_EXIT_CANDIDATE 157; PM_SEVERITY_UNRESOLVED 0`

`PERSISTENCE_STATE_DISTRIBUTION = RECOVERED 617; FIRST_OBSERVATION 130; REPEATED_OBSERVATION 1; PERSISTENT 61; WORSENING 96`

`PM_ACTION_DELTA_COUNT = 0`

`SEVERITY_WITHOUT_ACTION_DELTA_COUNT = 204`

`PM_SEVERITY_PRODUCTION_CONSUMER = position_management._apply_canonical_sell_semantics materializes evidence only; final PM action still follows canonical SELL/F1F evidence["final_pm_action"]`

`PM_SEVERITY_ACTION_MUTATION_CONNECTED = NO`

`PRE_G4_ACTION_POLICY_ALREADY_EQUIVALENT = YES`

`F1F_ESCALATION_DELTA_COUNT = 0`

`DOWNSTREAM_NEUTRALIZATION_COUNT = 0`

`WINNER_DAMAGE_DELTA = 0`

`LOSER_LOSS_DELTA = 0`

`NO_DELTA_ROOT_CAUSE_CLASSIFICATION = MIXED`

`IMPLEMENTATION_CHANGED = NO`

`FRESH_RUN_EXECUTED = NO`

`RESUME_EXECUTED = NO`

`LONG_HISTORICAL_EXECUTED = NO`

`GIT_DIFF_CHECK = PASS`
