# Phase32-CT — REENTRY Dedicated Penalty Necessity / Legacy Safety Mechanism READ-ONLY Audit

## Scope

This is a READ-ONLY audit. No source code, configuration, runtime state, Pending state, Ledger state, or run artifact was modified.

Primary current-system run:

- `runtime-test-historical-extended-smoke-20260901T205837445258Z`

Supporting pre-CO long-horizon run:

- `runtime-test-historical-extended-smoke-20260831T234344371102Z`

Prior EXIT semantic source for pre-CO interpretation:

- Phase32-CN strict-prior reconstruction

Outcome data, future return, MFE/MAE, final campaign outcome, and Historical profitability were not used to judge REENTRY penalty necessity.

## Evidence Read

Phase reports reviewed:

- Phase32-CM — REENTRY zero-fill root cause / requalification suppression
- Phase32-CN — prior EXIT semantic provenance recovery / REENTRY requalification
- Phase32-CO — prior EXIT semantic provenance production repair
- Phase32-CP — REENTRY temporal lifecycle / prior-campaign relevance audit
- Phase32-CQ — REENTRY time + renewed PIT evidence NEW-equivalent lifecycle shadow contract
- Phase32-CR — fixed temporal floor necessity vs evidence-based REENTRY release
- Phase32-CS — post-CO first-divergence / REENTRY actual-path causal audit

Architecture / SoT material reviewed:

- `strategy_intelligence_architecture_v1.md`
- `dual_path_market_quality_and_capital_competition_contract.md`
- `strategy_architecture_v1.md`
- momentum-follow position lifecycle notes

Relevant architecture conclusions:

- REENTRY is preserved as a lifecycle concept, not blanket-banned.
- REENTRY must distinguish genuine recovery from churn/unresolved continuation.
- Generic or missing prior EXIT context remains fail-closed / review-required.
- HARD_STOP and unresolved severe prior causes require stronger recovery proof.
- Once eligible, REENTRY enters current capital competition without permanent discount or bonus.
- A fixed long cooldown is not the selected design in the capital competition contract.
- PC conflict policy, not Runtime duplicate guard, owns any re-entry cooldown semantics.

## Current Evidence Coverage

Latest post-CO completed date used:

- `2022-11-07`

Latest pre-CO completed date used:

- `2023-10-10` for long-horizon population characterization

Post-CO actual-path first material REENTRY divergence:

- `2022-10-25:strategy/portfolio_construction`
- Symbol: `83060`
- Prior EXIT: `2022-10-04`
- Prior class: `TREND_MOMENTUM`
- Elapsed: `14` business days
- Pre-CO state: scalar `EXIT` / insufficient prior context / REENTRY suppressed
- Post-CO state: semantic prior EXIT evidence connected / REENTRY PASS / PC target `0.067556`
- Resulting order path: BUY `100` at `712`
- New campaign: `pc-800e4a57dc576701-83060-0001`

Pre-CO long-horizon REENTRY population from CM/CN/CP/CR:

- Raw REENTRY rows: `5,376`
- Episodes: `267`
- Pre-CO REENTRY pass/plan/fill: `0`
- Restored semantic SHADOW pass: `25`
- Long-delay `>60BD` restored semantic pass: `6`
- Original non-generic prior EXITs: `229 / 267`
- Generic prior EXITs: `38 / 267`
- Broad renewed-PIT long-delay cases from CP: `74`

Short-horizon first-reappearance characterization from supporting run evidence:

- First REENTRY episodes: `267`
- `<=3BD`: `233`
- `4-10BD`: `4` in direct first-reappearance count; CR separately identified five evidence-only age `4-10BD` eligibility cases
- `11-20BD`: `4`
- `21-40BD`: `7`
- `>40BD`: `19`
- Short-horizon `<=40BD`: `248`
- Already blocked by ordinary modern authorities without a REENTRY-specific penalty: `67`
- Not blocked by the coarse ordinary-authority audit: `181`

Observed repeated BUY/SELL cycle evidence:

- Pre-CO long run had `3` same-symbol BUY -> SELL -> BUY -> SELL sequences.
- Post-CO current run had `1` early sequence, `83060`, through the evidence window.

These counts show residual churn/noise risk exists, but they do not by themselves justify a broad permanent REENTRY penalty.

## Responsibility Decomposition

REENTRY has multiple responsibilities that should not be collapsed into one legacy penalty:

- Lifecycle lineage: preserve prior campaign and prior EXIT semantics.
- Missing-context safety: fail closed when prior EXIT evidence is generic, missing, or not materialized.
- Immediate churn suppression: prevent same-thesis buy/sell oscillation when the prior campaign is too fresh or unresolved.
- Prior-cause recovery: require current PIT evidence that the prior EXIT cause is resolved.
- HARD_STOP recovery: require stricter renewed-thesis evidence after severe prior deterioration.
- Ordinary BUY authority: current rank, Entry Admission, BQ/downside, PC sizing, cash, and lot feasibility.
- Capital competition: eligible REENTRY competes like a current BUY_NEW candidate, without permanent ownership penalty.

## Responsibility Disposition

| Responsibility | Disposition |
| --- | --- |
| Lifecycle lineage | Keep |
| Missing/generic context fail-closed | Keep |
| Immediate churn floor | Keep as narrow residual guard |
| Prior EXIT cause recovery | Keep as context-specific evidence requirement |
| HARD_STOP recovery guard | Keep |
| REENTRY-specific rank penalty | Remove / merge into ordinary current rank authority |
| REENTRY-specific BQ/quality penalty | Remove / merge into ordinary BQ/downside/Entry Admission |
| Long-lived time penalty | Remove as overbroad prior-ownership penalty |
| Capital competition discount | Remove |

## Original Failure Mode

The original REENTRY failure mode was not that REENTRY itself was unsafe.

The original defect was semantic information loss:

1. Prior EXIT semantic evidence was collapsed into weak scalar labels such as `EXIT`.
2. REENTRY could not distinguish TREND/MOMENTUM recovery from generic or unresolved exits.
3. Prior campaign context could not reliably survive into later REENTRY evaluation.
4. The system compensated with broad suppression, producing zero actual REENTRY pass/plan/fill in the pre-CO baseline.

Phase32-CO repaired the production path for prior EXIT semantic provenance. Phase32-CS confirmed a real actual-path divergence where `83060` was correctly restored from REVIEW_REQUIRED to REENTRY PASS when semantic prior EXIT evidence was available.

Therefore the original failure mode is not still present as a structural production defect in the current architecture.

## Legacy Safety Mechanism Assessment

### Immediate / Near-Term Churn

CR found five `4-10BD` evidence-only eligibility cases that represent the main residual safety argument for a REENTRY-specific temporal guard:

| Date | Symbol | Elapsed BD | Rank | Trend | Momentum | BQ |
| --- | --- | ---: | ---: | ---: | ---: | --- |
| `2022-11-09` | `65790` | `4` | `18` | `1.170022` | `0.796667` | REDUCED |
| `2023-03-07` | `48810` | `6` | `20` | `1.050157` | `0.280255` | REDUCED |
| `2023-03-08` | `47720` | `4` | `20` | `1.037528` | `0.314685` | REDUCED |
| `2023-05-30` | `21340` | `8` | `10` | `1.880342` | `1.0` | REDUCED |
| `2023-08-04` | `59520` | `4` | `19` | `1.056058` | `0.168` | REDUCED |

These are the strongest evidence that pure context-only release without any short churn floor is too permissive. They justify a narrow near-term protection, not a broad permanent REENTRY rank/time/capital penalty.

The strongest actual-repeat example is `21340`, because same-symbol repeated cycle history was already observable by PIT context at the relevant time. This still supports a local churn guard rather than a global REENTRY discount.

### 83060 Post-CO Divergence

`83060` is the decisive counterexample against broad REENTRY suppression:

- It had semantic prior EXIT context.
- The prior cause was TREND/MOMENTUM rather than generic unknown.
- Elapsed time was `14BD`.
- The current evidence requalified under current PIT authorities.
- It displaced `21950` through ordinary capital competition.

A dedicated REENTRY penalty would mainly preserve the old prior-ownership suppression in this case. The audit found no unique safety value from adding a REENTRY-specific rank or capital penalty to `83060` beyond ordinary current BUY authorities and prior-cause recovery context.

### Long-Horizon Prior Ownership

CP/CR show material universe erosion from permanent or long-lived prior ownership penalty:

- CP found broad long-delay renewed PIT cases.
- CQ found `14` high-confidence NEW-equivalent shadow cases.
- CR found `21-40BD` and `>60BD` renewed evidence cases where a fixed long floor was overbroad.

This supports removing long-lived REENTRY penalty once prior cause recovery and ordinary BUY authorities pass.

## Model R vs Model C

Model R, interpreted as retaining a dedicated REENTRY penalty layer, is overbroad. It duplicates ordinary rank/BQ/Entry Admission/capital competition and preserves legacy prior-ownership suppression after semantic provenance has been repaired.

Model C, interpreted as context-only REENTRY with minimal residual protections, matches the current architecture:

- prior EXIT context is preserved,
- unresolved/generic context fails closed,
- immediate churn remains protected,
- HARD_STOP requires stricter renewed evidence,
- eligible REENTRY competes as current opportunity capital.

Model C is semantically viable only with the residual protections above. Pure penalty removal without missing-context and near-term churn guards would be too permissive.

## Required Final Answers

1. `LATEST_POST_CO_COMPLETED_DATE_USED`: `2022-11-07`
2. `LATEST_PRE_CO_COMPLETED_DATE_USED`: `2023-10-10`
3. `REENTRY_RESPONSIBILITY_DECOMPOSITION`: lifecycle lineage, missing-context safety, immediate churn suppression, prior-cause recovery, HARD_STOP recovery, ordinary BUY authority, and neutral capital competition are separate responsibilities.
4. `REENTRY_RESPONSIBILITY_DISPOSITION`: keep lineage / missing-context fail-closed / immediate churn / reason-specific recovery / HARD_STOP; remove or merge broad rank, BQ, long time, and capital penalties into ordinary authorities.
5. `ORIGINAL_REENTRY_FAILURE_MODE`: prior EXIT semantic provenance loss caused broad REENTRY suppression and zero pre-CO pass/plan/fill.
6. `ORIGINAL_FAILURE_MODE_STILL_PRESENT_IN_CURRENT_ARCHITECTURE`: `NO`; Phase32-CO/CS show actual semantic provenance survives on the current path.
7. `CURRENT_PM_NOISE_EXIT_RISK`: `MATERIAL_BUT_LOCALIZED`; repeated cycles and near-term candidates exist, but do not justify broad permanent penalty.
8. `ACTUAL_SHORT_HORIZON_REENTRY_POPULATION`: `248` first-reappearance episodes within `<=40BD`; `233` were `<=3BD`.
9. `ACTUAL_REPEATED_BUY_EXIT_BUY_EXIT_COUNT`: pre-CO `3`, post-CO current-window `1`.
10. `MODERN_ARCHITECTURE_BLOCKS_WITHOUT_REENTRY_PENALTY_COUNT`: `67 / 248` short-horizon first-reappearance cases were already blocked by ordinary authorities in the audit.
11. `REENTRY_UNIQUE_SAFETY_CASE_COUNT`: `5` near-term potential cases; `1` strongest actual repeated-cycle case.
12. `CR_4_10BD_FIVE_UNIQUE_REENTRY_SAFETY_ASSESSMENT`: they justify a narrow near-term churn floor, not a broad rank/time/capital REENTRY penalty.
13. `83060_REENTRY_PENALTY_VALUE_ASSESSMENT`: broad penalty value is `LOW/NEGATIVE`; ordinary authorities plus semantic prior-cause recovery were sufficient.
14. `CONTEXT_ONLY_REENTRY_MODEL_SEMANTICALLY_VIABLE`: `YES_WITH_RESIDUAL_CHURN_AND_HARD_STOP_GUARDS`.
15. `TREND_MOMENTUM_REENTRY_SPECIFIC_GATE_NEEDED`: `NO_GENERAL_GATE`; use prior-cause recovery context and ordinary current BUY authority.
16. `HARD_STOP_DEDICATED_RECOVERY_GUARD_NEEDED`: `YES`.
17. `GENERIC_MISSING_CONTEXT_POLICY_IF_REENTRY_PENALTY_REMOVED`: fail closed / REVIEW_REQUIRED; do not infer or fabricate prior semantics.
18. `REENTRY_SPECIFIC_RANK_PENALTY_UNIQUE_VALUE`: `NO_MATERIAL_UNIQUE_VALUE`; duplicates ordinary current rank/capital competition.
19. `REENTRY_TIME_PENALTY_UNIQUE_VALUE`: `YES_ONLY_FOR_IMMEDIATE_CHURN`; no unique value as long-lived prior ownership penalty.
20. `REENTRY_QUALITY_GATE_DUPLICATION`: `MATERIAL`; ordinary BQ/downside/Entry Admission already own current quality.
21. `PRIOR_OWNERSHIP_CAPITAL_COMPETITION_EFFECT_JUSTIFIED`: `NO`; eligible REENTRY should receive neither bonus nor penalty.
22. `REENTRY_PENALTY_UNIVERSE_EROSION_MATERIALITY`: `MATERIAL`, based on CP/CQ/CR restored renewed-PIT cases.
23. `MODEL_R_VS_MODEL_C_ARCHITECTURE_ASSESSMENT`: Model C is preferred; Model R is overbroad legacy suppression.
24. `DEDICATED_REENTRY_PENALTY_STATUS`: `PARTIALLY_NECESSARY`; only residual churn/missing-context/HARD_STOP protections remain justified.
25. `MINIMAL_RESIDUAL_REENTRY_PROTECTION`: prior lineage, semantic prior EXIT context, missing/generic fail-closed, short churn floor, prior-cause recovery proof, HARD_STOP enhanced proof.
26. `OUTCOME_DATA_USED_FOR_REENTRY_NECESSITY`: `NO`.
27. `REENTRY_LEGACY_CLASSIFICATION`: keep lineage/safety context; migrate recovery to ordinary BUY authority; deprecate broad prior-ownership penalty.
28. `NEW_COMPONENT_REQUIRED`: `NO`; existing provenance, Entry Admission, BQ, PC conflict, and capital competition components are sufficient.
29. `NEW_MODEL_REQUIRED`: `NO`.
30. `NEW_FEATURE_REQUIRED`: `NO`; only contract cleanup / policy decomposition is indicated.
31. `PRODUCTION_CHANGE_JUSTIFIED`: `YES`, to remove broad dedicated REENTRY penalty while preserving minimal residual guards.
32. `PRODUCTION_CHANGE_EXECUTED`: `NO`.
33. `TARGET_RUN_MUTATED`: `NO`.
34. `NEXT_RECOMMENDED_STEP`: design a narrow production contract that removes REENTRY-specific rank/BQ/capital penalties, keeps missing-context fail-closed and short churn/HARD_STOP guards, then validate with focused shadow and actual-path tests before any long run.
35. `FINAL_JUDGMENT`: `PHASE32_CT_DEDICATED_REENTRY_PENALTY_NOT_BROADLY_NECESSARY_MINIMAL_RESIDUAL_REENTRY_PROTECTION_REQUIRED`

## Repair Guidance

No repair was implemented in this phase.

Recommended future repair boundary:

- Do not create a new REENTRY model.
- Do not add a new prediction feature.
- Decompose legacy REENTRY penalty into explicit existing authority checks.
- Preserve strict-prior prior EXIT provenance.
- Preserve fail-closed behavior for generic/missing prior context.
- Preserve HARD_STOP stricter recovery.
- Preserve a short churn guard for unresolved same-thesis re-entry.
- Remove broad REENTRY-specific rank, BQ, time, and capital competition penalty.

## Final Judgment

`PHASE32_CT_DEDICATED_REENTRY_PENALTY_NOT_BROADLY_NECESSARY_MINIMAL_RESIDUAL_REENTRY_PROTECTION_REQUIRED`
