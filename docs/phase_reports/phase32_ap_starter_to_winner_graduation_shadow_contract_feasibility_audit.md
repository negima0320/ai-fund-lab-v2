# Phase32-AP — Starter-to-Winner Graduation Shadow Contract Feasibility Audit

## Scope

Task type: READ-ONLY / SHADOW CONTRACT STUDY.

Target trusted run:

`runtime-test-historical-extended-smoke-20260830T081425790243Z`

Evidence window:

`2022-10-03` through `2023-10-10`, `252BD`.

Current source identity:

`git rev-parse --short HEAD = ff1d231`

No source code, config, runtime state, Strategy parameter, Strategy threshold, Strategy weight, BUY_NEW sizing, ADD, HOLD, REDUCE/EXIT, Cash, Risk Pacing, PC, PS, Runtime behavior, cap, or Production architecture was changed. No fresh-run, resume, replay, recover, rollback, or long Historical command was executed.

## Source Material Read

- `docs/phase_reports/phase32_af_stuck_capital_new_add_cash_marginal_equivalence_audit.md`
- `docs/phase_reports/phase32_ag_add_zero_winner_root_cause_characterization.md`
- `docs/phase_reports/phase32_ah_add_intent_quality_pm_pc_materialization_root_cause_audit.md`
- `docs/phase_reports/phase32_ai_pm_add_signal_predictiveness_ai_evidence_characterization.md`
- `docs/phase_reports/phase32_aj_fresh_incremental_add_current_architecture_falsification_audit.md`
- `docs/phase_reports/phase32_ak_existing_component_add_semantic_refactor_study.md`
- `docs/phase_reports/phase32_al_model2_add_semantic_shadow_validation.md`
- `docs/phase_reports/phase32_am_winner_growth_capitalization_lifecycle_root_cause_audit.md`
- `docs/phase_reports/phase32_an_durable_winner_capital_competition_deep_root_cause_audit.md`
- `docs/phase_reports/phase32_ao_initial_sizing_position_graduation_architecture_root_cause_audit.md`
- `docs/phase_reports/phase32_u_acceleration_activation_winner_retention_joint_audit.md`
- `docs/phase_reports/phase32_v_winner_retention_premature_deacceleration_predictability_audit.md`
- `docs/phase_reports/phase32_w_winner_retention_deterioration_recovery_exit_confirmation_design.md`
- `docs/phase_reports/phase32_x_winner_retention_recoverable_deterioration_minimum_implementation.md`
- relevant Phase28/29 ADD, lot-first, and capital recycling reports
- `docs/00_vision/investment_philosophy.md`
- `docs/03_ai_design/capital_deployment_design.md`
- `docs/02_architecture/strategy_intelligence_architecture_v1.md`
- `docs/02_architecture/portfolio_construction_and_position_sizing_contract.md`
- `docs/02_architecture/high_resolution_marginal_capital_value_and_portfolio_rotation_architecture.md`
- target run actual artifacts for PM, SI, BQ, PC, PS/runtime planning, fills, campaign state, Cash, Risk Pacing, and positions

## Architecture Baseline

The current SoT supports a cautious hybrid:

- `BUY_NEW` creates new-position target exposure.
- `ADD` is an existing-position target-weight increase candidate.
- `HOLD-worthy != ADD-worthy`.
- ADD requires incremental continuation quality, downside risk, opportunity cost, existing exposure, lot feasibility, and no-loss-averaging evidence.
- Cash remains a valid allocation destination.
- Residual capital may go to BUY_NEW, BUY_ADD, REENTRY, or Cash only when Production evidence supports the marginal JPY.
- `BUY_ADD` quantity authority remains G129 order-increment scoped at Submit.
- Strategy Intelligence may produce interpretation evidence; PC owns capital allocation; PS owns discrete executable quantity; Runtime must consume PS-bound quantity.

There is still no accepted SoT state named `POSITION_GRADUATION`, `STARTER`, `CONFIRMED_HOLD`, or `GRADUATION_CONSIDERATION`.

## Shadow Semantics Used For This Audit

These labels are diagnostic only and not Production rules.

| Shadow label | Diagnostic meaning | Existing evidence used | Action authority |
|---|---|---|---|
| `STARTER` | New/small position whose post-entry evidence has not established stronger capital entitlement | BUY_NEW fill, open campaign, no later confirmation/ADD evidence | none |
| `CONFIRMED_HOLD` | Continued ownership is justified, but incremental capital is not authorized | PM/SI hold-worthiness, continuation quality, downside risk, PM HOLD/REDUCE/EXIT context | none |
| `GRADUATION_CONSIDERATION` | Existing evidence is stronger than ordinary HOLD and may be presented to PC for incremental-capital consideration | PM ADD plus PC-visible ADD eligibility / ADD investment evidence / ADD marginal-capital evidence | non-final consideration only |
| `GRADUATED_POSITION` | Observed position quantity increased through existing BUY_ADD authority | actual BUY_ADD fills and same campaign continuity | observed result only |

Conservative audit rule:

`PM ADD` alone is not sufficient for `GRADUATION_CONSIDERATION`.

The minimum existing-authority surface used for a campaign-day to count as `GRADUATION_CONSIDERATION` is:

```text
current_position=true
AND PM/PC semantic is BUY_ADD or PM ADD
AND PC/ADD evidence says add_allocation_eligibility_status=PASS
    or add_investment_evidence.final_add_eligibility=PASS
```

This preserves the key AO property that weak/non-durable starters should stay small.

## Run Evidence Summary

| Metric | Count |
|---|---:|
| Completed audited business days | `252` |
| Execution fills | `835` |
| BUY_NEW campaigns | `395` |
| REENTRY entry campaigns in this window | `0` |
| Non-growing campaigns | `392` |
| Growing campaigns | `3` |
| 100-share BUY_NEW initial entries | `324` |
| PM position rows | `2,748` |
| PM HOLD rows | `1,748` |
| PM REDUCE rows | `507` |
| PM EXIT rows | `394` |
| PM ADD rows in current artifacts | `99` |
| Conservative `GRADUATION_CONSIDERATION` campaign-days | `25` |
| Conservative `GRADUATION_CONSIDERATION` campaigns | `6` |
| BUY_ADD fills through 2023-10-10 | `9` |

Note: earlier AF/AH reports also refer to broader Runtime PM ADD intent counts such as `118`. The current target run's final Strategy PM artifact rows materialize `99` PM ADD rows, and AP classification uses the final canonical artifacts in the target window.

BUY_ADD fills observed:

| Date | Symbol | Campaign | Quantity |
|---|---|---|---:|
| 2022-10-06 | `94340` | `pc-f3bd989f40c52bdf-94340-0001` | `100` |
| 2022-10-12 | `94340` | `pc-f3bd989f40c52bdf-94340-0001` | `100` |
| 2022-10-13 | `94340` | `pc-f3bd989f40c52bdf-94340-0001` | `100` |
| 2022-11-01 | `94320` | `pc-f6f650ff3364b80b-94320-0001` | `100` |
| 2022-11-29 | `76470` | `pc-8b52b4c89fd002ad-76470-0001` | `100` |
| 2022-11-30 | `76470` | `pc-8b52b4c89fd002ad-76470-0001` | `100` |
| 2022-12-01 | `76470` | `pc-8b52b4c89fd002ad-76470-0001` | `100` |
| 2022-12-02 | `76470` | `pc-8b52b4c89fd002ad-76470-0001` | `100` |
| 2022-12-06 | `76470` | `pc-8b52b4c89fd002ad-76470-0001` | `100` |

## A — Graduation Semantics, Not Rules

The four conceptual states can be described using existing evidence, but only as shadow interpretation.

`STARTER` and `GRADUATED_POSITION` are easiest to reconstruct:

- `STARTER`: derived from BUY_NEW fill and campaign creation.
- `GRADUATED_POSITION`: derived from actual BUY_ADD fill continuity.

`CONFIRMED_HOLD` and `GRADUATION_CONSIDERATION` are partially reconstructable:

- `CONFIRMED_HOLD` maps cleanly to PM/SI hold-worthiness and continuation evidence.
- `GRADUATION_CONSIDERATION` can be conservatively represented only when PM ADD reaches PC-visible ADD eligibility / ADD investment evidence.

No Production `FRESH_INCREMENTAL_OPPORTUNITY` rule is defined. AL already found deterministic freshness not ready.

## B — STARTER To CONFIRMED_HOLD

`CAN_EXISTING_PIT_EVIDENCE_DETERMINISTICALLY_CONFIRM_A_STARTER: PARTIAL`

Evidence:

- BUY_NEW fill and campaign creation are deterministic.
- SI lifecycle context exposes campaign age, current return, current quantity, position campaign id, hold-worthiness, continuation quality, downside risk, PM decision history, and no future-information flags.
- In actual PM rows, continued positions almost immediately carry structured hold-worthiness / continuation evidence.

Boundary limitation:

- There is no canonical `STARTER` state field.
- The first post-entry PM evaluation often already appears as HOLD/ADD/REDUCE/EXIT with SI context. The system can identify an entry and later hold-worthiness, but it does not explicitly materialize a STARTER-to-CONFIRMED transition.

## C — CONFIRMED_HOLD To GRADUATION_CONSIDERATION

`CAN_IT_DISTINGUISH_CONFIRMED_HOLD_FROM_GRADUATION_CONSIDERATION: PARTIAL`

Existing labels can separate a conservative subset:

- PM ADD gives a stronger-than-HOLD lifecycle signal.
- ADD investment evidence can require campaign continuation, expected-edge improvement, incremental value, no-loss averaging, and opportunity cost.
- PC can keep `GRADUATION_CONSIDERATION != CAPITAL_ENTITLEMENT` because Cash, NEW, Risk Pacing, headroom, lot feasibility, broker, corporate action, and Safety remain active.

Ambiguities:

- PM ADD is broad. AH found it often means strong continuation/rank/no-loss rather than a fresh next-lot opportunity.
- Many PM ADD rows fail PC ADD materialization with `add_target_weight_unchanged` or `buy_quality_blocks_incremental_add`.
- PC/Cash/NEW competition is coarse; AF found NEW/ADD/Cash are not yet on one high-resolution marginal-capital-value scale.
- The contract distinguishes "may be considered" from "should buy", but not yet "new evidence episode" from "persistent unchanged strength" as a formal state.

Therefore reconstruction is not `DETERMINISTIC`; it is `PARTIAL`.

## D — 387 Negative Controls

AO's protected negative-control set:

```text
392 non-growing campaigns
- 5 durable no-growth challenge campaigns
= 387 negative controls
```

Conservative shadow classification:

| Classification | Campaign count |
|---|---:|
| `STARTER` only | `0` |
| `CONFIRMED_HOLD` only | `385` |
| `GRADUATION_CONSIDERATION` surfaced | `2` |
| `AMBIGUOUS` only | `0` |

`HOW_MANY_OF_387_NEGATIVE_CONTROLS_SURFACE_AS_GRADUATION_CONSIDERATION: 2`

`WHAT_IS_THE_FALSE_GRADUATION_CONSIDERATION_RATE: 2 / 387 = 0.5168%`

Surfaced negative controls:

| Symbol | Campaign | Initial qty | Max qty | Notes |
|---|---|---:|---:|---|
| `67310` | `pc-47f89bc0fb3b790c-67310-0001` | `100` | `100` | PC ADD consideration surfaced on 2023-05-10 and 2023-05-29, but no quantity growth |
| `99840` | `pc-925de11083435873-99840-0001` | `100` | `100` | repeated PM ADD / PC consideration surfaces in November 2022, but no retained growth |

Interpretation:

The conservative contract strongly preserves weak-starter protection. However, because it can surface two non-growing controls, the contract is not perfectly deterministic as a Production gate. That is acceptable for shadow feasibility, not for activation.

## E — Seven Durable Winner Positive / Challenge Set

| Symbol | Main campaign | Shadow classification | First confirmed hold | First graduation consideration | Actual growth | Stop / failure reason |
|---|---|---|---|---|---:|---|
| `76470` | `pc-8b52b4c89fd002ad-76470-0001` | `GRADUATION_CONSIDERATION` then `GRADUATED_POSITION` | 2022-11-28 | 2022-11-29 | `1300 -> 1800` | later deployment blocked by prior ADD history / target unchanged plus Cash/NEW competition |
| `54010` | `pc-3aaff341fad7ae34-54010-0001` | `CONFIRMED_HOLD`, PM ADD observed but no conservative PC graduation | 2023-01-23 | none | `100 -> 100` | semantic recognition / PM-to-PC materialization gap, then Cash/NEW / BQ filtering |
| `21340` | `pc-f3186b6520780cea-21340-0001` | `GRADUATION_CONSIDERATION` but not graduated | 2023-06-06 | 2023-06-20 | `2200 -> 2200` | PC ADD surfaced but lot-aware increment stayed zero / NEW won final capital path |
| `43880` | `pc-df47de7d57274254-43880-0001` | `CONFIRMED_HOLD`, PM ADD observed but no conservative PC graduation | 2023-03-17 | none | `100 -> 100` | PM ADD did not survive as PC-positive ADD; later risk/REDUCE context |
| `40520` | `pc-21eead760e37aeb3-40520-0001` | `CONFIRMED_HOLD`, PM ADD observed but no conservative PC graduation | 2023-06-16 | none | `100 -> 100` | NEW/Cash competition and no retained ADD quantity growth |
| `94340` | `pc-f3bd989f40c52bdf-94340-0001` | `GRADUATION_CONSIDERATION` then `GRADUATED_POSITION` | 2022-10-04 | 2022-10-06 | `200 -> 500` | positive structural control; later Cash optionality limited further growth |
| `77760` | `pc-9d71e709a18ea961-77760-0001` | `CONFIRMED_HOLD` | 2023-02-01 | none | `100 -> 100` | no actual PC ADD competitor; PM HOLD-only / no ADD materialization |

`HOW_DO_THE_7_DURABLE_WINNERS_CLASSIFY: 2 graduated, 1 graduation-considered but not grown, 4 confirmed-hold / challenge cases without conservative PC graduation materialization.`

## F — 94340 Positive Control

`DOES_THE_CONTRACT_CORRECTLY_REPRESENT_94340: YES`

Trace:

```text
2022-10-03 BUY_NEW 200
2022-10-04 CONFIRMED_HOLD
2022-10-06 GRADUATION_CONSIDERATION
2022-10-06 BUY_ADD fill 100
2022-10-12 BUY_ADD fill 100
2022-10-13 BUY_ADD fill 100
observed state: 200 -> 500
```

The shadow label appears before/during the existing BUY_ADD sequence. It uses PIT evidence:

- PM ADD
- continuation quality PASS
- downside risk PASS
- current campaign relative return observed
- expected edge improving versus strict-prior same-campaign baseline
- incremental value POSITIVE
- no-loss averaging PASS
- opportunity cost PASS
- PC ADD evidence / lot authority

The contract therefore represents the known positive structural control coherently.

## G — Five Durable No-Growth Challenge Cases

`WHY_DID_THE_5_DURABLE_NO_GROWTH_WINNERS_FAIL`

| Symbol | Failure class | Detail |
|---|---|---|
| `54010` | semantic recognition / PM-to-PC materialization plus allocation rejection | PM ADD appeared, but conservative PC graduation did not materialize; later Cash/NEW and BQ filters prevented positive ADD |
| `21340` | legitimate capital allocation rejection after recognition | PC graduation consideration surfaced on 2023-06-20, but no retained lot increment; NEW won final capital path |
| `43880` | semantic recognition / PM-to-PC materialization | repeated PM ADD existed, but PC-positive graduation did not form; local risk/REDUCE later mattered |
| `40520` | mixed semantic recognition and allocation competition | PM ADD existed, but no retained positive ADD quantity; NEW/Cash competition remained active |
| `77760` | no graduation consideration formed | confirmed HOLD existed, but no PM/PC ADD consideration; not a PC allocation failure |

Separation:

- `semantic recognition failure`: `54010`, `43880`, `40520`, `77760`.
- `legitimate capital allocation rejection after consideration`: `21340`.

## H — 76470 Special Case

`CAN_76470_BE_CONSIDERED_WHILE_REMAINING_GATE_BLOCKED: YES`

The shadow contract can express:

```text
GRADUATION_CONSIDERATION exists
AND DEPLOYMENT_BLOCKED_BY_EXISTING_GATE
```

Evidence:

- Main campaign `pc-8b52b4c89fd002ad-76470-0001` first confirms on 2022-11-28.
- Conservative graduation consideration appears from 2022-11-29.
- BUY_ADD fills occur five times, 2022-11-29 through 2022-12-06.
- Later PM ADD-like strength does not justify weakening the prior ADD gate. AH/AG found post-2022-12-06 cases are blocked by prior ADD history / target unchanged / Strategy PM-to-PC materialization and Cash/NEW competition.

The key point is that consideration is not entitlement and must not bypass prior ADD history.

## I — Graduation Episode Persistence

`DOES_GRADUATION_CONSIDERATION_AVOID_REPEATED_BUY_SEMANTICS: PARTIAL`

Observed conservative consideration surfaces:

| Campaign | Rows | Sequence shape |
|---|---:|---|
| `94340` main | `4` | 2022-10-06, 2022-10-11 to 2022-10-13 |
| `94320` | `6` | scattered October/November 2022 |
| `99840` | `7` | scattered plus short November persistence |
| `76470` main | `5` | 2022-11-29 to 2022-12-02, 2022-12-06 |
| `67310` | `2` | 2023-05-10 and 2023-05-29 |
| `21340` main | `1` | 2023-06-20 |

The current system already avoids automatic repeated buys because each actual BUY_ADD still requires PC, PS, Runtime, Cash, lot, and Submit authority. However, the semantic label can persist or recur without a formal "fresh graduation episode" lifecycle. Therefore it is safe as non-authoritative consideration, but not ready as a repeated-buy instruction.

Required distinction:

```text
eligibility to compete != fresh instruction to buy
```

## J — Model 2 Integration Study

`IS_MODEL2_CORE_MATERIAL_OPTIONAL_OR_NOT_MATERIAL: MATERIAL_SUPPORT`

Model 2:

```text
PM owns position lifecycle
SI/ADD evidence exposes graduation consideration
PC owns incremental capital allocation
```

Findings:

- Graduation does not strictly require Model 2 to exist as a new component.
- Model 2 materially improves semantic clarity by separating lifecycle retention from ADD consideration.
- Graduation can work without changing PM ADD authority if PM ADD remains evidence and PC remains final capital authority.
- Model 2 would reduce PM/SI ambiguity, especially where PM ADD currently means persistent continuation/rank/no-loss rather than next-lot value.

Status remains DEFERRED / ON HOLD.

## K — PC Compatibility

`CAN_PC_CONSUME_GRADUATION_CONSIDERATION_WITH_EXISTING_GATES: YES_FOR_SHADOW / PARTIAL_FOR_PRODUCTION`

PC can structurally receive a non-authoritative `GRADUATION_CONSIDERATION` because current PC already consumes:

- PM ADD intent
- ADD investment evidence
- opportunity cost
- incremental value
- campaign continuation
- no-loss averaging
- BQ
- Cash competitor
- NEW competition
- Risk Pacing
- concentration/headroom
- lot feasibility
- broker, corporate action, Safety

Mandatory property preserved:

```text
GRADUATION_CONSIDERATION != CAPITAL_ENTITLEMENT
```

PC must remain free to choose NEW or Cash.

## L — Initial Sizing Relationship

`CAN_GRADUATION_BE_VALIDATED_WITHOUT_CHANGING_INITIAL_SIZING: YES_FOR_SHADOW`

Path A is feasible:

```text
Keep current starter sizing unchanged.
Add only a non-authoritative graduation semantic / audit label.
Validate whether it preserves weak-starter protection and identifies durable winners.
```

Path B is not proven mandatory. AO found initial sizing and graduation are both material, but AP evidence does not prove they must be changed together. Minimal blast radius favors validating graduation semantics independently before touching BUY_NEW sizing.

## M — Starter Saturation Interaction

`IS_STARTER_SATURATION_STILL_MATERIAL: YES`

Evidence:

- 395 BUY_NEW campaigns.
- 324 started at 100 shares.
- 392 never grew beyond initial quantity.
- On consideration days, position count commonly ranged around the high 20s to mid 30s.
- PC frontier often included Cash plus NEW competitors, and Cash/NEW remained binding.
- AF/AG found Cash won many NEW+ADD days and ADD was usually eliminated before final deployable comparison.

Interpretation:

Graduation failure is not purely semantic. It is also a portfolio-capacity / fragmentation / capital-competition problem.

## N — Weak-Starter Protection

`ARE_WEAK_STARTER_PROTECTIONS_PRESERVED: YES_IN_SHADOW`

The conservative contract preserves:

- weak positions staying small
- no loss averaging
- no forced deployment
- Cash optionality
- Risk Pacing
- concentration controls
- SELL independence
- broker / corporate-action / Safety boundaries
- fail-closed behavior
- G129 order-increment BUY_ADD quantity authority

The false-graduation surface on the 387 negative controls is `2` campaigns, `0.5168%`, and even those did not become forced buys.

## O — Current Architecture Sufficiency

| Hypothesis | Evidence for | Evidence against | Judgment |
|---|---|---|---|
| H0 current implicit distributed graduation is sufficient | 94340 and 76470 prove the system can graduate when PM/PC/PS/Runtime align; weak-starter protection is strong | durable winners often remain small; no explicit transition state; PM ADD is broad | `PARTIAL` |
| H1 existing components contain sufficient evidence, but explicit semantic contract is missing | SI/PM/PC artifacts expose hold-worthiness, ADD evidence, expected edge, no-loss, opportunity cost, and campaign history; negative false surface is low under conservative contract | challenge winners are missed unless PM/PC boundary is clarified | `STRONG` |
| H2 existing components lack sufficient PIT evidence | freshness is not deterministic; relative sector strength and calibrated marginal-value units remain incomplete | 94340, 76470, 21340 and low false rate show some usable PIT evidence exists | `PARTIAL` |
| H3 graduation semantics are adequate; PC/Cash/NEW is the real bottleneck | Cash/NEW repeatedly beat or narrow ADD; starter saturation is material | semantic PM ADD / PC materialization ambiguity remains real | `PARTIAL` |
| H4 both semantic contract and capital competition contribute | matches AO/AN/AF/AG evidence; explains both missed durable winners and valid Cash/NEW gates | does not yet specify a Production fix | `BEST_EXPLANATION` |

`WHICH_HYPOTHESIS_H0_H4_BEST_EXPLAINS_THE_EVIDENCE: H4`

## P — Shadow Divergence Surface

Compared with current behavior:

| Divergence surface | Count |
|---|---:|
| current PM HOLD -> shadow `GRADUATION_CONSIDERATION` | `0` |
| current PM ADD -> shadow `GRADUATION_CONSIDERATION` | `25` campaign-days |
| current PM ADD -> only `CONFIRMED_HOLD` / blocked consideration | `74` campaign-days |
| negative controls incorrectly surfaced | `2` campaigns |
| durable winners surfaced | `3` of 7 campaigns (`94340`, `76470`, `21340`) |
| actually graduated durable winners represented | `2` of 2 main graduated controls (`94340`, `76470`) |

This is a small but non-zero semantic blast radius. It is appropriate for shadow study, not Production activation.

## Q — POST_HOC Diagnostic Only

This section is descriptive only. It did not alter classifications.

| Shadow / observed state | Descriptive outcome |
|---|---|
| `STARTER` / broad one-lot entries | most did not grow; this preserved weak-starter protection |
| `CONFIRMED_HOLD` | many retained ownership but did not receive more capital |
| `GRADUATION_CONSIDERATION` | 25 campaign-days across 6 campaigns; only some converted to BUY_ADD |
| `GRADUATED_POSITION` | observed on `94340`, `94320`, and `76470`; durable-positive controls are `94340` and `76470` |

No future price path, future return, final campaign outcome, MFE/MAE after the decision, or Historical PnL was used to form the shadow labels.

## R — Feasibility Gate

`IS_AN_EXPLICIT_GRADUATION_CONTRACT_JUSTIFIED: YES_FOR_SHADOW_ARCHITECTURE`

`IS_ANY_PRODUCTION_BEHAVIOR_CHANGE_JUSTIFIED: NO`

Gate:

```text
GRADUATION_SHADOW_CONTRACT_PARTIAL
```

Reason:

- Existing PIT evidence can safely define a conservative graduation-consideration surface.
- It represents the positive 94340 control and 76470 special case.
- It preserves the 387-control protection with only 2 false surfaced campaigns and no forced buys.
- It misses several durable no-growth challenge cases and cannot yet deterministically separate persistent strength from a fresh graduation episode.
- Capital-allocation feasibility remains partial because NEW/ADD/Cash do not yet share a high-resolution marginal-capital-value unit.

## Deferred / Open Architecture Tracks

### Model 2

```text
Model 2 — PM Position Lifecycle + PC ADD Consideration
Status: DEFERRED / ON HOLD
Rejected: NO
Production activation: NOT AUTHORIZED
Reason: shadow partially validated, but broader Graduation architecture remains under investigation
Revisit trigger: completion of starter-to-winner graduation feasibility/architecture study
```

Suggested durable SoT location for a future record:

`docs/02_architecture/strategy_intelligence_architecture_v1.md`

Rationale: that file already owns HOLD vs ADD semantics, PM/SI/PC/PS boundaries, G129 BUY_ADD authority, Cash preservation, and high-resolution marginal capital roadmap pointers.

### Starter-To-Winner Graduation Track

```text
Starter-to-Winner Graduation Contract
Status: OPEN / SHADOW_ONLY
Rejected: NO
Production activation: NOT AUTHORIZED
Reason: conservative PIT reconstruction is feasible but partial; fresh episode semantics and PC marginal-value comparison remain unresolved
Revisit trigger: shadow audit of explicit graduation episode lifecycle and high-resolution NEW/ADD/Cash marginal-value comparison
```

## What Remains Unproven

`WHAT_REMAINS_UNPROVEN`

- A canonical STARTER state transition.
- A deterministic fresh graduation episode contract.
- A robust split between persistent PM ADD strength and renewed incremental next-lot opportunity.
- A high-resolution marginal capital value unit comparable across NEW, ADD, and Cash.
- Whether durable no-growth challenge cases can be surfaced without increasing false graduation among weak starters.
- Whether PC can improve graduation without weakening Cash optionality, Risk Pacing, concentration, lot feasibility, or G129.

## Recommended Next Investigation

`WHAT_SHOULD_BE_INVESTIGATED_NEXT`

Run a read-only architecture/shadow study for:

```text
explicit graduation episode lifecycle
```

Minimum questions:

- Can a non-authoritative `GRADUATION_EPISODE` be materialized from existing PIT evidence without arbitrary numeric thresholds?
- Can it distinguish first confirmation, persistence, stale repeated strength, renewed evidence, and deployment-blocked state?
- Can it expose durable no-growth winners like `54010`, `43880`, `40520`, and `77760` without materially raising the 387-control false-graduation rate?
- Can it feed PC as consideration only, while preserving NEW/Cash competition and G129 order-increment authority?

No parameter recommendation is made here.

## Required Final Answers

1. `CAN_EXISTING_PIT_EVIDENCE_DETERMINISTICALLY_CONFIRM_A_STARTER`

   `PARTIAL`. BUY_NEW/campaign creation and later hold-worthiness are deterministic, but no canonical STARTER state is materialized.

2. `CAN_IT_DISTINGUISH_CONFIRMED_HOLD_FROM_GRADUATION_CONSIDERATION`

   `PARTIAL`. Conservative PM ADD + PC-visible ADD evidence separates a safe subset, but PM ADD is broad and freshness remains unresolved.

3. `HOW_MANY_OF_387_NEGATIVE_CONTROLS_SURFACE_AS_GRADUATION_CONSIDERATION`

   `2`.

4. `WHAT_IS_THE_FALSE_GRADUATION_CONSIDERATION_RATE`

   `2 / 387 = 0.5168%`.

5. `HOW_DO_THE_7_DURABLE_WINNERS_CLASSIFY`

   `94340` and `76470` classify as `GRADUATION_CONSIDERATION -> GRADUATED_POSITION`; `21340` classifies as `GRADUATION_CONSIDERATION` but deployment did not increase quantity; `54010`, `43880`, `40520`, and `77760` classify as `CONFIRMED_HOLD` / challenge cases under the conservative contract.

6. `DOES_THE_CONTRACT_CORRECTLY_REPRESENT_94340`

   `YES`.

7. `WHY_DID_THE_5_DURABLE_NO_GROWTH_WINNERS_FAIL`

   Mostly semantic recognition / PM-to-PC materialization gaps, plus legitimate Cash/NEW/BQ/risk/lot allocation filtering. `21340` is the clearest allocation rejection after recognition.

8. `CAN_76470_BE_CONSIDERED_WHILE_REMAINING_GATE_BLOCKED`

   `YES`.

9. `DOES_GRADUATION_CONSIDERATION_AVOID_REPEATED_BUY_SEMANTICS`

   `PARTIAL`. It is safe as non-authoritative consideration, but a formal episode lifecycle is still needed to prevent persistent strength from becoming daily buy semantics.

10. `IS_MODEL2_CORE_MATERIAL_OPTIONAL_OR_NOT_MATERIAL`

    `MATERIAL_SUPPORT`.

11. `CAN_PC_CONSUME_GRADUATION_CONSIDERATION_WITH_EXISTING_GATES`

    `YES_FOR_SHADOW / PARTIAL_FOR_PRODUCTION`.

12. `CAN_GRADUATION_BE_VALIDATED_WITHOUT_CHANGING_INITIAL_SIZING`

    `YES_FOR_SHADOW`.

13. `IS_STARTER_SATURATION_STILL_MATERIAL`

    `YES`.

14. `ARE_WEAK_STARTER_PROTECTIONS_PRESERVED`

    `YES_IN_SHADOW`.

15. `WHICH_HYPOTHESIS_H0_H4_BEST_EXPLAINS_THE_EVIDENCE`

    `H4`: both missing explicit semantic contract and capital competition / portfolio capacity contribute.

16. `IS_AN_EXPLICIT_GRADUATION_CONTRACT_JUSTIFIED`

    `YES_FOR_SHADOW_ARCHITECTURE`, not Production activation.

17. `IS_ANY_PRODUCTION_BEHAVIOR_CHANGE_JUSTIFIED`

    `NO`.

18. `WHAT_REMAINS_UNPROVEN`

    canonical STARTER state, fresh graduation episode semantics, PM ADD freshness separation, NEW/ADD/Cash high-resolution marginal comparability, and low-false-positive recovery of the durable no-growth challenge cases.

19. `WHAT_SHOULD_BE_INVESTIGATED_NEXT`

    explicit non-authoritative `GRADUATION_EPISODE` lifecycle shadow audit.

20. `IS_MODEL2_EXPLICITLY_RECORDED_AS_DEFERRED_AND_OPEN`

    `YES`, in this AP report. Future durable SoT recording should be added to `docs/02_architecture/strategy_intelligence_architecture_v1.md` only after a separate accepted architecture update.

## Final Judgment

```text
PHASE32_AP_GRADUATION_SHADOW_CONTRACT_PARTIAL_NO_PRODUCTION_CHANGE
```

Current strengths to preserve:

- weak starter protection
- no loss averaging
- Cash optionality
- Risk Pacing
- concentration and headroom controls
- SELL independence
- fail-closed evidence boundaries
- G129 BUY_ADD order-increment authority

Semantic feasibility:

`PARTIAL`. Existing PIT evidence can define a conservative graduation-consideration shadow label, but not a full deterministic STARTER-to-WINNER production contract.

Capital-allocation feasibility:

`PARTIAL`. PC can consume consideration without changing final authority, but NEW/ADD/Cash marginal-value comparability remains incomplete.

Unresolved ambiguity:

Persistent PM ADD strength versus renewed/fresh graduation episode remains unresolved.

Deferred architecture tracks:

Model 2 remains `DEFERRED / ON HOLD`, not rejected, not Production-authorized. Starter-to-Winner Graduation remains `OPEN / SHADOW_ONLY`.
