# Phase32-AG — ADD Zero-Winner Root-Cause Characterization

## Scope

- Target run: `runtime-test-historical-extended-smoke-20260830T081425790243Z`
- Evidence window: `2022-10-03` through `2023-10-10`
- Business days used: `252`
- Prior report: `docs/phase_reports/phase32_af_stuck_capital_new_add_cash_marginal_equivalence_audit.md`
- Mode: READ-ONLY root-cause characterization

No code, config, runtime state, Strategy parameter, threshold, weight, ADD tier, Cash policy, BQ, Risk Pacing, PC, PS, or Runtime changes were made. No resume, recover, replay, fresh-run, or long Historical command was executed.

Future price, future return, final campaign outcome, Historical profitability, and hindsight were not used to judge whether a decision should have been different.

## Executive Conclusion

ADD won zero PC daily winner slots because almost all ADD candidates were noncompetitive before the final daily winner selection.

Observed 252BD funnel:

```text
PM ADD decisions: 118
-> PC ADD competitors: 99
-> ADD competitors selected by PC: 11
-> PC daily ADD winner: 0
-> Runtime BUY_ADD positive plans: 11
-> BUY_ADD fills: 9
```

The dominant causes were:

1. PC/BQ/ADD evidence made most ADD competitors `BLOCKED` or `INSUFFICIENT`.
2. 81 of the 82 days with both NEW and ADD had ADD eliminated before the final deployable winner comparison.
3. Only 1 ADD row reached a final deployable comparison against NEW; it lost to a stronger/higher accepted-weight NEW candidate.
4. Cash dominance was material, especially under cautious market/risk optionality, but Cash mostly beat already marginal or non-deployable ADD candidates.
5. The marginal-capital semantic gap exists and contributes to interpretability/architecture risk, but the actual evidence does not show it as the primary cause of ADD winner zero.

Final classification:

```text
ADD_SCARCITY_MIXED_CAUSES
```

with semantic materiality:

```text
CONTRIBUTING_CAUSE
```

## A — Complete ADD Competitor Inventory Summary

All 99 PC ADD competitors were reconstructed from `capital_competition.market_candidate_cash_interaction.competitor_set` and joined to PM, BQ, PC competitor, ADD authority, Risk Pacing, Cash, and winner evidence.

### Quality Classes

| ADD Quality | Count |
| --- | ---: |
| `BLOCKED` | `47` |
| `INSUFFICIENT` | `30` |
| `COMPARABLE_MARGINAL` | `22` |

### Interaction Classes

| Interaction | Count |
| --- | ---: |
| `BLOCKED` | `50` |
| `FAIL_CLOSED` | `38` |
| `CASH_PREFERRED` | `10` |
| `DEPLOY_ELIGIBLE` | `1` |

### PC Competitor Status

| Status | Count |
| --- | ---: |
| `COMPETITOR_REJECTED_RECONSIDERABLE` | `84` |
| `COMPETITOR_SELECTED` | `11` |
| `COMPETITOR_REJECTED_TERMINAL` | `4` |

### Primary First-Loss Classification

Each ADD competitor received exactly one primary first-loss classification:

| First Loss | Count |
| --- | ---: |
| `PC_BLOCKED_NON_ELIGIBLE` | `47` |
| `ADD_TIER_OR_EVIDENCE_INSUFFICIENT` | `30` |
| `PC_COMPETITOR_NOT_SELECTED` | `11` |
| `LOST_TO_CASH_OPTIONALITY` | `10` |
| `FINAL_LOST_TO_NEW_BUY` | `1` |
| `ADD_WINNER` | `0` |

This distribution is the central explanation for zero ADD daily winners: ADD usually did not reach the final deployable frontier.

## B — BLOCKED 47

All 47 `BLOCKED` ADD competitors carried:

```text
BLOCKED_NON_ELIGIBLE
```

The immediate authority was Portfolio Construction interaction classification. Current source maps `quality_class == "BLOCKED"` to interaction `BLOCKED` with reason `BLOCKED_NON_ELIGIBLE` in `_interaction_result_for_quality`.

Underlying canonical ADD competitor states:

| Eligibility / Value / Opportunity Cost State | Count |
| --- | ---: |
| `eligibility=FAIL_CLOSED`, `incremental_value=UNKNOWN/FAIL_CLOSED`, `opportunity_cost=NEW_BUY_SUPERIOR/FAIL_CLOSED` | `30` |
| `eligibility=FAIL_CLOSED`, `incremental_value=UNKNOWN/FAIL_CLOSED`, `opportunity_cost=PASS` | `14` |
| `eligibility=PASS`, `incremental_value=POSITIVE/PASS`, `opportunity_cost=PASS` but final row still `BLOCKED` | `3` |

Interpretation:

- The 30-row largest group is plausibly justified: ADD lacked positive incremental value evidence and same-day opportunity cost said NEW_BUY was superior.
- The 14-row group is mixed: opportunity cost passed, but ADD incremental value/eligibility still failed closed.
- The 3-row group is a semantic/compression concern: lower-level positive evidence existed, yet the final interaction row became `BLOCKED`.

Classification by major group:

| Group | Count | Classification |
| --- | ---: | --- |
| unknown incremental value + NEW_BUY superior | `30` | `PLAUSIBLY_JUSTIFIED` |
| unknown incremental value + opportunity cost pass | `14` | `POSSIBLE_OVER_SUPPRESSION` |
| positive ADD evidence but final `BLOCKED` | `3` | `SEMANTIC_COMPRESSION_ARTIFACT` |

`BLOCKED` does not always mean hard safety non-investability. In this evidence it often means ADD-specific incremental evidence was insufficient or failed closed before final PC interaction.

## C — INSUFFICIENT 30

All 30 `INSUFFICIENT` ADD competitors carried:

```text
INSUFFICIENT_FAIL_CLOSED
```

Underlying canonical ADD competitor states:

| Eligibility / Value / Opportunity Cost State | Count |
| --- | ---: |
| `eligibility=FAIL_CLOSED`, `incremental_value=UNKNOWN/FAIL_CLOSED`, `opportunity_cost=NEW_BUY_SUPERIOR/FAIL_CLOSED` | `29` |
| `eligibility=FAIL_CLOSED`, `incremental_value=UNKNOWN/FAIL_CLOSED`, `opportunity_cost=PASS` | `1` |

Critical finding:

`INSUFFICIENT` primarily means ADD incremental investment value was unknown/fail-closed, not that later outcomes were bad. Most rows also had same-day NEW_BUY opportunity cost superiority.

Classification:

- Genuinely missing/insufficient ADD-specific evidence: `29`
- Evidence existed upstream but final ADD positive value remained unavailable: `1`
- Negative future evidence used: `0`

Overall:

```text
PLAUSIBLY_JUSTIFIED_WITH_ADD_EVIDENCE_RESOLUTION_GAP
```

`INSUFFICIENT` appears mostly intentional and fail-closed, but it also acts as an ADD scarcity mechanism because ADD requires incremental-position evidence that NEW candidates do not need in the same form.

## D — COMPARABLE_MARGINAL 22

The 22 `COMPARABLE_MARGINAL` ADD rows are the only serious candidates for “ADD reached meaningful competition but still never won.”

### Outcome Summary

| ADD Interaction / Winner | Count |
| --- | ---: |
| `CASH_PREFERRED` / Cash winner | `8` |
| `FAIL_CLOSED` / Cash winner | `7` |
| `CASH_PREFERRED` / NEW winner | `2` |
| `BLOCKED` / NEW winner | `2` |
| `FAIL_CLOSED` / NEW winner | `1` |
| `BLOCKED` / Cash winner | `1` |
| `DEPLOY_ELIGIBLE` / NEW winner | `1` |

Primary loss classification:

| Classification | Count |
| --- | ---: |
| `PC_COMPETITOR_NOT_SELECTED` | `11` |
| `LOST_TO_CASH_OPTIONALITY` | `10` |
| `FINAL_LOST_TO_NEW_BUY` | `1` |

### Representative Rows

| Date | Symbol | ADD Accepted Weight | Interaction | Winner | Explanation |
| --- | --- | ---: | --- | --- | --- |
| `2022-10-06` | `94340` | `0.013786` | `CASH_PREFERRED` | Cash | Cautious deployment; marginal ADD lost to elevated Cash optionality. |
| `2022-10-11` | `94340` | `0.013676` | `CASH_PREFERRED` | Cash | Same marginal/Cash-preferred pattern; later Submit capacity also blocked fill. |
| `2022-10-28` | `94320` | `0.015528` | `CASH_PREFERRED` | `NEW_BUY 72020` | NEW `72020` was `STRONG`, `DEPLOY_ELIGIBLE`, accepted weight `0.162217`. |
| `2022-11-01` | `94320` | `0.015304` | `CASH_PREFERRED` | Cash | Cautious deployment; ADD valid but Cash preferred. |
| `2022-11-29` | `76470` | `0.002405` | `DEPLOY_ELIGIBLE` | `NEW_BUY 76920` | Only true deployable ADD final comparison; NEW had `COMPARABLE_HIGH`, accepted weight `0.014957`. |
| `2022-12-02` | `76470` | `0.002321` | `CASH_PREFERRED` | `NEW_BUY 64880` | NEW was `STRONG`, `SELECTIVE_COMPETITION`, accepted weight `0.058924`. |
| `2023-05-10` | `67310` | `0.0` | `FAIL_CLOSED` | Cash | Comparable marginal positive semantics existed, but current PC context did not select ADD. |

### Conclusion for the 22

Only 1 of the 22 became a deployable ADD competitor in final comparison. It lost to a stronger NEW candidate by quality class and accepted weight. The remaining 21 were defeated earlier by Cash preference, non-selection, or fail-closed/block semantics.

Classification:

```text
MOSTLY_LOST_BEFORE_FINAL_COMPARISON
```

with one case:

```text
LOST_TO_GENUINELY_STRONGER_NEW
```

## E — 82 Days With Both NEW and ADD

AF found 82 days containing both NEW and ADD competitors.

Winner distribution:

| Winner | Days |
| --- | ---: |
| Cash | `55` |
| NEW | `27` |
| ADD | `0` |

AG classification:

| Day Classification | Days |
| --- | ---: |
| ADD eliminated before final deployable competition | `81` |
| ADD final competitor but NEW won | `1` |
| ADD final competitor but Cash won | `0` |
| tie-break cases | `0` |
| ambiguous/non-equivalent final comparison cases | `0` |

This strongly favors the explanation that ADD was already noncompetitive before final winner selection, rather than repeatedly losing fair final tie-breaks.

## F — Cash Dominance Root Cause

Cash won `170 / 252` days and `55 / 82` NEW+ADD days.

Cash semantic states on Cash-win days:

| Cash Semantic | Count |
| --- | ---: |
| `OPTIONALITY_ELEVATED` | `146` |
| `OPTIONALITY_NEUTRAL` | `23` |
| `OPTIONALITY_LOW` | `1` |

Top Cash reason codes on all Cash-win days:

| Reason | Count |
| --- | ---: |
| `MARGINAL_OPPORTUNITY_SET` | `152` |
| `CAUTIOUS_MARKET_OPTIONALITY_ELEVATED` | `138` |
| `LOT_RESIDUAL_OPTIONALITY` | `116` |
| `UNAVOIDABLE_LOT_RESIDUAL` | `116` |
| `RECOVERY_INCOMPLETE_OPTIONALITY_ELEVATED` | `30` |
| `NO_VALID_COMPETITOR` | `28` |
| `VALID_POLICY_RESERVE` | `26` |
| `CONCENTRATION_BLOCK` | `25` |
| `CONCENTRATION_OPTIONALITY` | `25` |
| `STRONG_OPPORTUNITY_PRESENT` | `18` |

Primary Cash-win characterization:

| Primary Category | Days |
| --- | ---: |
| cautious market/risk optionality | `96` |
| no valid competitor / deployable gap | `35` |
| recovery caution | `25` |
| concentration | `14` |

Cash often won even when some selected securities existed. However, for ADD specifically, Cash usually faced ADD rows that were already marginal, not selected, fail-closed, or Cash-preferred.

Cash classification:

```text
MIXED
```

Cash dominance is partly justified by decision-time risk/optionality/residual evidence and partly a performance architecture concern because Cash is not on the same high-resolution marginal capital value scale as NEW/ADD.

## G — Post-Entry Confirmation Compression

PM ADD evidence is present and canonical. The PM trace contract lists ADD triggers including:

- `strong_trend_continuation`
- `opportunity_rank_still_high`
- `no_loss_averaging`
- `add_downside_risk_contained`

Actual PM ADD decisions repeatedly carried:

```text
strong_trend_continuation
opportunity_rank_still_high
no_loss_averaging
```

First compression boundary:

```text
PM ADD evidence -> PC competitor/opportunity quality classification
```

Current PC source takes member-level opportunity quality evidence and reduces it into `canonical_opportunity_quality_class`. The interaction layer then uses only coarse classes such as `BLOCKED`, `INSUFFICIENT`, `COMPARABLE_MARGINAL`, `COMPARABLE_HIGH`, and `STRONG` together with Risk Pacing. For cautious or gradual deployment, `COMPARABLE_MARGINAL` maps directly to `CASH_PREFERRED`.

Observed compression modes:

| Boundary | Status |
| --- | --- |
| PM reasons preserved as PM evidence | `YES` |
| ADD investment evidence records no-loss/opportunity-cost concepts | `PARTIAL` |
| PC opportunity quality retains high-resolution PM confirmation | `NO`, bucketed |
| interaction class retains confirmation details | `NO`, reduced to coarse quality + risk pacing |
| final winner comparison values confirmation as marginal capital value | `NO` |

Classification:

```text
POST_ENTRY_CONFIRMATION_BUCKETED_AND_UNDERREPRESENTED
```

This is a performance architecture concern, but AG does not prove it alone caused ADD winner zero.

## H — Semantic Gap Causal Materiality

AF proved semantic non-equivalence. AG asks whether it actually caused ADD scarcity.

Evidence:

- 77 of 99 ADD competitors were `BLOCKED` or `INSUFFICIENT`.
- 11 more were not selected by PC despite comparable-marginal lineage.
- Only 1 ADD competitor reached `DEPLOY_ELIGIBLE` final comparison.
- That 1 final-comparison ADD lost to NEW with stronger quality class and higher accepted weight.
- Cash beat many marginal ADDs through risk/optionality semantics, not through calibrated marginal-yen value.

Classification:

```text
CONTRIBUTING_CAUSE
```

Rationale:

The semantic gap materially limits interpretability and may suppress marginal ADDs under Cash-preferred and coarse-bucket conditions. But the actual zero-winner result is not primarily explained by non-equivalent final comparison; most ADD rows were eliminated before final competition by ADD-specific evidence, eligibility, or selection boundaries.

## I — Is ADD Structurally Suppressed?

| Question | Answer |
| --- | --- |
| Is ADD explicitly penalized because it is ADD? | `NO_DIRECT_ACTION_TYPE_PENALTY_FOUND` |
| Is ADD implicitly penalized by requiring different evidence than NEW? | `YES` |
| Does ADD encounter gates NEW does not? | `YES`: current position, incremental value, no-loss averaging, opportunity cost, headroom/current exposure, ADD tier |
| Are those extra gates justified by incremental-position risk? | `MOSTLY_YES` |
| Is existing exposure/concentration a real difference rather than bias? | `YES` |
| Does ADD receive incumbent advantage? | `YES_PARTIAL`: PM ADD intent and campaign continuation can authorize ADD-specific consideration |

Final classification:

```text
MIXED
```

Structural ADD suppression as an unjustified action-type bias is not confirmed. ADD is structurally harder because it is an increment on an existing position, and many of those extra checks are legitimate. However, the current representation may under-value post-entry confirmation and may over-compress ADD quality into fail-closed or Cash-preferred buckets.

## J — PM ADD 118 -> PC ADD 99 Gap

19 PM ADD decisions did not materialize as PC ADD competitors.

All 19 were symbol `76470` between `2022-12-07` and `2023-01-16`.

BQ state for the 19:

| BQ Action | Count |
| --- | ---: |
| `REDUCED_ALLOCATION_ONLY` | `13` |
| `FULL_ALLOCATION_ELIGIBLE` | `5` |
| `BUY_WAIT` | `1` |

BQ band:

| BQ Band | Count |
| --- | ---: |
| `HIGH` | `18` |
| `BUY_WAIT` | `1` |

Observed boundary:

- PM emitted `ADD`.
- BQ often remained `PASS` and high-quality.
- PC `competitors`, `canonical_deployment_set`, and `canonical_multi_allocation_deployment_set` contained no `76470` ADD competitor record for these dates.
- PS carried `76470` only as existing-position baseline with:

```text
existing_position_baseline_preserved_no_transaction_delta
existing_position_baseline_quantity_authoritative
membership_intent:RETAIN
pm_action:HOLD
```

Classification:

```text
PM_TO_PC_ADD_MATERIALIZATION_GAP
```

Likely nature:

- not a final capital competition loss;
- not a Runtime/Submit defect;
- not a post-hoc performance finding;
- a materialization/positive-increment gating boundary where PM ADD did not survive as executable ADD competitor.

Repair is not performed in AG. This is a high-priority next investigation item because the 19 include high BQ states and strong PM continuation evidence.

## K — Runtime 11 -> Fill 9

Runtime BUY_ADD positive plans were observed on:

| Date | Symbol |
| --- | --- |
| `2022-10-06` | `94340` |
| `2022-10-11` | `94340` |
| `2022-10-12` | `94340` |
| `2022-10-13` | `94340` |
| `2022-10-28` | `94320` |
| `2022-11-01` | `94320` |
| `2022-11-29` | `76470` |
| `2022-11-30` | `76470` |
| `2022-12-01` | `76470` |
| `2022-12-02` | `76470` |
| `2022-12-06` | `76470` |

BUY_ADD fills occurred on 9 of these dates. The two non-filled cases were:

| Date | Symbol | Classification |
| --- | --- | --- |
| `2022-10-11` | `94340` | Expected Submit/capacity review: reserved notional exceeded dynamic cash capacity. |
| `2022-10-28` | `94320` | PC lineage retained ADD as Cash-preferred defeated competitor; no final executable fill was created. |

This is secondary to PC root cause. No Runtime duplicate, authority mismatch, or G129 regression was found from these two cases.

## L — Root-Cause Ranking

| Rank | Cause | Affected Count | First-Loss Count | Confidence | Correctness Defect | Performance Architecture Concern |
| ---: | --- | ---: | ---: | --- | --- | --- |
| 1 | ADD evidence/eligibility insufficient or blocked | `77` | `77` | `HIGH` | `NO / PARTIAL_UNCONFIRMED` | `YES` |
| 2 | PM->PC ADD materialization gap | `19` | outside PC competitor set | `HIGH` | `UNCONFIRMED` | `YES` |
| 3 | Cash optionality/risk pacing defeats marginal ADD | `55` NEW+ADD Cash-win days; `10` selected ADD Cash-preferred rows | `10` | `HIGH` | `NO` | `YES` |
| 4 | ADD post-entry confirmation compression | PM ADD evidence in `118`; coarse PC result in many ADD rows | indirect | `MEDIUM` | `NO` | `YES` |
| 5 | Semantic non-equivalence of NEW/ADD/Cash | global | causal in some marginal cases | `MEDIUM` | `NO` | `YES` |
| 6 | Stronger NEW competition | `27` NEW wins on NEW+ADD days; only `1` direct final ADD loss | `1` | `HIGH` | `NO` | `NO / LOW` |
| 7 | Runtime/Submit narrowing | `2` | `2` | `HIGH` | `NO` | `LOW` |
| 8 | Lot/quantity feasibility | embedded in PC/PS | not primary in ADD zero-winner | `MEDIUM` | `NO` | `LOW` |

## Design Work Justification

Design work is justified, but not because AG proves “valid ADDs were unfairly blocked across the board.”

Justified next work:

- characterize and possibly repair the PM->PC ADD materialization gap for the 19 `76470` cases;
- audit the 3 `BLOCKED` rows where lower-level ADD evidence was `PASS/POSITIVE`;
- shadow-test how post-entry confirmation would be preserved into PC marginal value;
- keep any new comparator design read-only until its causal value is proven.

Not justified by AG:

- changing ADD thresholds;
- changing BUY quality weights;
- changing Cash policy;
- increasing ADD allocation by parameter tuning;
- using later PnL to select parameters.

## Final Judgment

1. `WHY_DID_ADD_WIN_ZERO_PC_DAYS`: Because 98 of 99 ADD competitors were eliminated or made non-deployable before any final ADD win; only one reached deployable final comparison and it lost to a stronger NEW candidate.
2. `WHAT_EXPLAINS_BLOCKED_47`: All carried `BLOCKED_NON_ELIGIBLE`; 30 had unknown/fail-closed incremental value plus NEW_BUY-superior opportunity cost, 14 had unknown incremental value despite opportunity-cost pass, and 3 show positive lower-level evidence compressed to final `BLOCKED`.
3. `WHAT_EXPLAINS_INSUFFICIENT_30`: All carried `INSUFFICIENT_FAIL_CLOSED`; 29 had unknown/fail-closed ADD incremental value plus NEW_BUY-superior opportunity cost, 1 had opportunity-cost pass but ADD value still unavailable.
4. `WHY_DID_COMPARABLE_MARGINAL_22_NOT_WIN`: 11 were not selected, 10 were Cash-preferred, and only 1 was deployable; that one lost to `NEW_BUY 76920` with stronger quality and higher accepted weight.
5. `WHAT_HAPPENED_ON_THE_82_NEW_PLUS_ADD_DAYS`: Cash won 55, NEW won 27, ADD won 0; ADD was eliminated before final deployable competition on 81 days and lost a true final deployable comparison on 1 day.
6. `IS_CASH_DOMINANCE_JUSTIFIED`: `MIXED`; mostly supported by risk/optionality/residual/concentration evidence, but Cash remains semantically non-equivalent to NEW/ADD marginal value.
7. `WHERE_IS_POST_ENTRY_CONFIRMATION_COMPRESSED`: At PM ADD evidence -> PC opportunity quality / ADD competitor classification, then further into risk-paced interaction classes.
8. `IS_THE_MARGINAL_CAPITAL_SEMANTIC_GAP_CAUSALLY_MATERIAL`: `CONTRIBUTING_CAUSE`, not primary.
9. `IS_ADD_STRUCTURALLY_SUPPRESSED`: `MIXED`; unjustified explicit ADD bias not confirmed, but ADD-specific evidence/gates and compression materially reduce ADD participation.
10. `WHY_DID_19_PM_ADDS_NOT_REACH_PC`: All were `76470` PM ADDs; PC did not materialize ADD competitors and PS treated the position as baseline HOLD/no-transaction-delta despite high or reduced BQ states.
11. `WHY_DID_11_RUNTIME_ADDS_BECOME_9_FILLS`: One was Submit/cash-capacity reviewed (`2022-10-11 94340`), and one remained non-executable/defeated in PC lineage (`2022-10-28 94320`); no Runtime duplicate or authority mismatch was identified.
12. `WHAT_ARE_THE_TOP_ROOT_CAUSES_IN_ORDER`: ADD evidence/eligibility insufficiency, PM->PC ADD materialization gap, Cash/risk optionality, post-entry confirmation compression, semantic non-equivalence, stronger NEW competition, Runtime/Submit narrowing.
13. `IS_DESIGN_WORK_JUSTIFIED_YET`: `YES`, but only as read-only/shadow architecture characterization and targeted materialization-gap investigation, not parameter tuning.
14. `WHAT_SHOULD_BE_INVESTIGATED_NEXT`: The 19 `76470` PM ADD -> PC missing cases and the 3 positive-evidence-but-final-BLOCKED cases should be audited before designing or activating a new comparator.

Final classification:

```text
ADD_SCARCITY_MIXED_CAUSES
```
