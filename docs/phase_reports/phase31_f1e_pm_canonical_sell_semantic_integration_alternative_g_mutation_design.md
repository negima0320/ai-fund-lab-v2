# Phase31-F1E — PM Canonical SELL Semantic Integration / Alternative G Mutation Design

Status: COMPLETE
Task type: DESIGN ONLY — PRE-MUTATION CONTRACT

## PRIMARY_JUDGMENT

```text
PHASE31_F1E_PM_OWNED_DISCRETE_CONTROL_EXIT_ESCALATION_DESIGN_READY_WITH_EXPLICIT_UNRESOLVED_SCOPE
```

F1E defines the Production integration contract for canonical SELL semantics and Alternative G. The design is ready for a focused implementation phase, but only with explicit scope limits: discrete-lot / one-lot unrepresentable REDUCE may be escalated by PM under the new contract; minimum-notional remains unresolved and must not be merged into this mutation.

The central design decision is:

```text
PERSISTENT_DETERIORATION alone is not a standalone EXIT authority.
PM REDUCE + discrete-lot partial REDUCE unrepresentable + PERSISTENT_DETERIORATION + recovery guard absent + PIT proof complete is sufficient for PM to emit EXIT under a discrete-control escalation contract.
```

This is not a REDUCE-count threshold. It is a feasible-action correction: PM already wants lower exposure, PS proves the intermediate exposure is impossible, and current PIT semantic state shows persistent unrecovered deterioration in the same campaign. PM must then choose between the only feasible exposure states, preserve 100% or close to 0%, and owns that action decision.

## Evidence Scope

```text
DOCUMENTS_READ = F0, F1, F1A, F1B, F1C, F1D
CURRENT_SOT_READ = position_management.py, strategy_intelligence.py, runtime_planning.py, runtime_v2/planning/sell_pipeline.py, canonical_sell_semantic_shadow.py
TARGET_RUN_ID = runtime-test-historical-extended-smoke-20260820T120909096218Z
FRESH_RUN_EXECUTED = NO
```

No later price, later return, later MFE/MAE, eventual EXIT, final campaign outcome, later delisting, or performance result was used for this design.

## ESCALATION_OWNER

```text
ESCALATION_OWNER = PM
```

Ownership is frozen:

| Layer | Owns | Must not own |
|---|---|---|
| Strategy Intelligence / SELL semantic producer | Canonical SELL semantic evidence and state | Order action |
| PM | Final HOLD / ADD / REDUCE / EXIT, including REDUCE -> EXIT escalation | Quantity materialization |
| PS | Quantity, lot representation, minimum-notional representation, execution semantic | EXIT invention |
| Runtime | Faithful consumption of PM/PS output | EXIT invention |

Current SoT supports this split: Runtime Planning maps PM `REDUCE` to `SELL_REDUCE` and PM `EXIT` to `SELL_EXIT`; Sell Pipeline calculates REDUCE quantity and marks unrepresentable REDUCE as intentional no-order, but does not convert REDUCE into EXIT.

## PRODUCTION_SELL_SEMANTIC_OWNER

```text
PRODUCTION_SELL_SEMANTIC_OWNER = Strategy Intelligence canonical SELL semantic producer, consumed by PM
```

Production should promote F1D semantics into a canonical Strategy Intelligence / SELL semantic producer, not keep diagnostic shadow artifacts as production input. The F1D module can be migrated as implementation seed, but production consumption must point to canonical Strategy evidence.

Chosen route:

```text
Route A = promote F1D producer semantics into canonical Strategy Intelligence / SELL semantic producer
```

Rationale:

- F1D already composes PM-attached SI evidence, PS representability evidence, campaign PIT history, and PIT proof.
- F1C/F1D semantics are cross-cutting SELL evidence, not a Runtime or PS action rule.
- PM remains the sole action owner.
- Permanent shadow-as-production architecture is forbidden.

## PRODUCTION_SELL_SEMANTIC_ARTIFACT_CONTRACT

Production artifact contract:

```text
artifact = strategy/sell_semantic_state.json or embedded strategy_intelligence.symbol_intelligence.<symbol>.sell_semantic_state
producer = strategy.sell_semantic_state
contract_version = phase31_f1e_pm_canonical_sell_semantic_integration_v1
consumer = PM only
```

Required per position-day fields:

- `business_date`
- `symbol`
- `campaign_id`
- `original_pm_action`
- `canonical_sell_state`
- `state_reasons`
- `deterioration_dimensions`
- `recovery_state`
- `recovery_reset_policy`
- `representability_family`
- `representability_reason`
- `one_lot_flag`
- `minimum_notional_flag`
- `pit_proof`
- `parameter_resolution_status`
- `escalation_considered`
- `escalation_decision`
- `final_pm_action`
- `contract_version`
- `future_information_used = false`
- `outcome_used_for_parameter_selection = false`

Production PM must not consume `daily/<DATE>/diagnostic_shadow/*.json`.

## BASE_PM_ACTION_CONTRACT

| Canonical SELL state | Base PM relationship |
|---|---|
| `HEALTHY_OR_RECOVERING` | PM preserves existing HOLD/ADD authority. Prior escalation pressure is reset or decayed according to recovery evidence. |
| `WEAKENING_BUT_INTACT` | PM preserves REDUCE authority. If partial REDUCE is representable, PS may materialize SELL_REDUCE. If not representable, first occurrence preserves/no-order with lineage. |
| `PERSISTENT_DETERIORATION` | PM may escalate only through the discrete-control gate defined below. |
| `EXIT_GRADE` | PM emits direct EXIT. No REDUCE -> persistent prerequisite. |
| `UNRESOLVED` | Fail closed to preserve/review; never silently EXIT. |

Existing direct EXIT behavior is preserved.

## PERSISTENT_DETERIORATION_EXIT_SUFFICIENCY

```text
PERSISTENT_DETERIORATION_EXIT_SUFFICIENCY = CONDITIONAL
```

`PERSISTENT_DETERIORATION` itself is insufficient if read in isolation. It becomes sufficient for PM-owned EXIT only when all Production gate conditions are true:

1. Current PM baseline action is `REDUCE`.
2. Current representability family is `DISCRETE_LOT`.
3. Partial REDUCE final sell quantity is zero.
4. Current position is one lot or otherwise has no valid intermediate remaining/sell quantity under the lot contract.
5. Canonical SELL state is `PERSISTENT_DETERIORATION`.
6. Recovery guard is absent.
7. PIT proof is complete.
8. Campaign identity is unambiguous.
9. Minimum-notional is false.
10. PM materializes the final action as `EXIT` with explicit escalation lineage.

This is not `REDUCE_COUNT >= N -> EXIT`. The prior REDUCE evidence is only a component of campaign-scoped persistent deterioration; the action is justified by the current infeasible discrete-control choice.

## UNREPRESENTABLE_REDUCE_PRODUCTION_DISPOSITION

For discrete-lot unrepresentable REDUCE:

| State | Production disposition |
|---|---|
| `WEAKENING_BUT_INTACT` | Preserve REDUCE intent as no-order / no immediate EXIT. |
| `PERSISTENT_DETERIORATION` | PM escalates to EXIT when all F1E gate conditions pass. |
| `EXIT_GRADE` | PM emits direct EXIT, independent of Alternative G. |
| `HEALTHY_OR_RECOVERING` | PM does not escalate; HOLD/ADD/recovery semantics win. |
| `UNRESOLVED` | REVIEW_REQUIRED / preserve; no automatic EXIT. |

Economic meaning:

```text
PM REDUCE = desired risk exposure is lower than current exposure.
PS discrete-lot proof = desired intermediate exposure cannot be represented.
PM discrete-control choice = preserve full exposure or exit full exposure.
```

When deterioration is persistent and unrecovered, preserving 100% exposure contradicts PM's repeated current risk-reduction intent. Under F1E, PM may choose 0% exposure by emitting EXIT.

## ONE_LOT_STATE_ACTION_MATRIX

```text
ONE_LOT_AUTOMATIC_EXIT = NO
```

| One-lot state | PM disposition |
|---|---|
| `HEALTHY_OR_RECOVERING` | HOLD/ADD/preserve according to existing PM authority. |
| `WEAKENING_BUT_INTACT` | Preserve first unrepresentable REDUCE as intentional no-order; no automatic EXIT. |
| `PERSISTENT_DETERIORATION` | PM-owned EXIT if the full F1E discrete-control gate passes. |
| `EXIT_GRADE` | PM direct EXIT. |
| `UNRESOLVED` | REVIEW_REQUIRED / preserve; no automatic EXIT. |

One-lot is representability evidence only. It never creates EXIT without persistent unrecovered deterioration or EXIT-grade evidence.

## RECOVERY_OVERRIDE_CONTRACT

Baseline:

```text
RECOVERY_RESET_POLICY = MIXED
```

Production behavior:

- `RESET`: Fresh PM HOLD/ADD with recovery-compatible reasons clears persistent escalation pressure. No hidden deterioration debt survives reset.
- `DECAY`: Mixed recovery evidence reduces escalation pressure; PM must re-evaluate fresh PIT evidence before any later escalation.
- `PRESERVE`: Current REDUCE remains active, recovery guard absent, and persistent deterioration may proceed to the F1E gate.

Recovery-compatible evidence includes PM HOLD/ADD reasons such as `structured_hold_worthiness_pass`, `trend_continuation`, `downside_risk_contained`, `positive_expected_edge`, `strong_trend_continuation`, and `opportunity_rank_still_high`, plus nested SI recovery states such as `HEALTHY_CONTINUATION_ENTRY` or `ADD_ALLOWED`.

## EXISTING_EXIT_AUTHORITY_PRESERVED

```text
EXISTING_EXIT_AUTHORITY_PRESERVED = YES
```

F1D aligned 60/60 current PM EXIT rows to `EXIT_GRADE`. F1E does not delay, weaken, or route direct EXIT through Alternative G. Same-day `EXIT_GRADE` remains direct PM EXIT.

## 61750_PRODUCTION_DISPOSITION

```text
61750_PRODUCTION_DISPOSITION = EXIT
```

## 61750_REASON

PIT-only reason:

- On 2022-09-13, 61750 is `WEAKENING_BUT_INTACT`; PM REDUCE is unrepresentable but not yet persistent, so no automatic EXIT.
- From 2022-09-14, F1D maps 61750 to `PERSISTENT_DETERIORATION / UNRESOLVED_FOR_EXIT`.
- The position is one lot: `current_quantity = trading_unit = 100`.
- Partial REDUCE is impossible: `rounded_reduce_quantity = 0`, `reduce_final_sell_quantity = 0`, `reduce_execution_semantic = REDUCE_UNEXECUTABLE_DUE_TO_DISCRETE_LOT`.
- PM still emits REDUCE with deterioration/risk-review reason `risk_increased_but_trend_not_broken`.
- Recovery guard is absent in the REDUCE sequence.
- PIT proof is complete.

Under F1E, the new Production contract resolves `UNRESOLVED_FOR_EXIT` for discrete-lot one-lot persistent deterioration. PM would emit EXIT from the first date where the full gate passes, 2022-09-14, without using later price, later delisting, later return, or final outcome.

## RECOVERY_CONTROL_COUNT

```text
RECOVERY_CONTROL_COUNT = 17
```

## RECOVERY_PROTECTION_DESIGN

F1D showed:

```text
RECOVERY_CONTROL_FALSE_PERSISTENT_COUNT = 0
RECOVERY_CONTROL_FALSE_EXIT_GRADE_COUNT = 0
WINNER_PROTECTION_SEMANTIC_GATE = PASS
```

F1E preserves this by requiring:

- same-day/fresh recovery evidence to override persistence;
- no hidden deterioration debt after `RESET`;
- no unrepresentability-only EXIT;
- no one-lot-only EXIT;
- no REDUCE-count-only EXIT.

Recovery controls are protected structurally, not because of later recovery outcome.

## MINIMUM_NOTIONAL_MUTATION_AUTHORIZED

```text
MINIMUM_NOTIONAL_MUTATION_AUTHORIZED = NO
```

Minimum-notional current state:

```text
MINIMUM_NOTIONAL_ROWS = 15
MINIMUM_NOTIONAL_STATE_DISTRIBUTION = UNRESOLVED: 15
```

Minimum-notional may represent a meaningful-notional/execution-cost policy problem rather than a pure discrete-lot infeasible-intermediate-exposure problem. It remains separate until a dedicated design resolves materiality and notional feasibility.

## MARKET_CONTEXT_LOGIC_CHANGED

```text
MARKET_CONTEXT_LOGIC_CHANGED = NO
```

F0 found:

```text
MARKET_CONTEXT_SELL_AUTHORITY = NONE
```

F1E does not connect Market Context as SELL authority. Market Context SELL authority remains Phase31-F2 scope.

## FAIL_CLOSED_CONTRACT

Fail-closed behavior:

| Condition | Required behavior |
|---|---|
| Missing canonical SELL state | REVIEW_REQUIRED / preserve; no EXIT |
| Incomplete PIT proof | REVIEW_REQUIRED / preserve; no EXIT |
| Ambiguous campaign identity | REVIEW_REQUIRED / preserve; no persistent escalation |
| Conflicting recovery and deterioration evidence | Recovery review; do not escalate unless PM resolves conflict with explicit lineage |
| Unresolved representability family | REVIEW_REQUIRED / preserve |
| Minimum-notional family | UNRESOLVED; no F1E mutation |
| Missing PS quantity evidence | REVIEW_REQUIRED / preserve |
| Missing SI evidence | Existing fail-closed PM/SI behavior applies |

No missing state may silently default to EXIT, HOLD, ADD, or BUY semantics.

## PRODUCTION_EVIDENCE_LINEAGE

Future implementation must materialize:

- original PM action;
- original PM reasons;
- canonical SELL state;
- state reasons;
- deterioration dimensions;
- recovery state and reset/decay policy;
- representability family;
- representability reason;
- one-lot flag;
- minimum-notional flag;
- raw / rounded / final REDUCE quantity;
- escalation considered;
- escalation decision;
- final PM action;
- PIT proof;
- source artifact hashes;
- contract version.

If PM escalates, required reason code:

```text
pm_discrete_control_persistent_deterioration_exit
```

Compatibility aliases may retain existing reason codes, but the canonical escalation reason must be explicit.

## SHADOW_MIGRATION_PLAN

| Component | Classification | Plan |
|---|---|---|
| F1D canonical SELL semantic field mapping | MIGRATE | Move semantics into canonical Strategy/SI SELL semantic producer. |
| F1D diagnostic artifact path | DEPRECATE | Keep for validation only; production must not consume it. |
| F1D focused tests | KEEP | Convert/extend into production regression tests. |
| F1A Alternative G representability shadow | MIGRATE | Keep representability/evidence logic as PM integration support, not separate authority. |
| F1A diagnostic shadow artifact path | DEPRECATE | Do not consume in production. |
| Existing PM direct EXIT reasons | KEEP | Preserve direct EXIT authority. |
| Existing PS reduce quantity contract | KEEP | PS still owns quantity/representability only. |
| Runtime PM action mapping | KEEP | Runtime remains faithful consumer. |
| Minimum-notional escalation | KEEP_UNRESOLVED | Separate future design. |

After migration:

```text
PRODUCTION_SHADOW_CONSUMER_COUNT = 0
```

## EXPECTED_MUTATION_SCOPE

Allowed future mutation scope:

- canonical SELL semantic production/materialization;
- PM consumption of canonical SELL semantic;
- PM-owned discrete-lot REDUCE -> EXIT escalation;
- explicit evidence lineage;
- focused regression tests.

Forbidden scope:

- Candidate AI;
- BUY logic;
- B10 marginal capital priority;
- Expected Edge thresholds;
- ADD policy;
- Safety caps;
- Runtime execution semantics;
- broker execution;
- Market Context SELL logic;
- unrelated EXIT thresholds;
- minimum-notional mutation.

## REQUIRED_REGRESSION_TESTS

Future F1F tests must cover:

1. normal HOLD unchanged;
2. normal ADD unchanged;
3. representable REDUCE unchanged;
4. first one-lot `WEAKENING_BUT_INTACT` REDUCE does not auto-EXIT;
5. recovery RESET clears escalation pressure;
6. recovery DECAY requires fresh PIT re-evaluation;
7. persistent deterioration + discrete-lot unrepresentable REDUCE escalates through PM;
8. EXIT_GRADE still directly EXITs;
9. minimum-notional remains unresolved/separate;
10. missing PIT proof fail-closed;
11. ambiguous campaign identity fail-closed;
12. conflicting recovery/deterioration fail-closed or explicit PM review;
13. PS never invents EXIT;
14. Runtime never invents EXIT;
15. no future data;
16. campaign isolation;
17. existing 60 EXIT authority preserved in current-run validation;
18. production shadow consumer count remains 0.

## Required Output

```text
PRIMARY_JUDGMENT = PHASE31_F1E_PM_OWNED_DISCRETE_CONTROL_EXIT_ESCALATION_DESIGN_READY_WITH_EXPLICIT_UNRESOLVED_SCOPE
ESCALATION_OWNER = PM
PRODUCTION_SELL_SEMANTIC_OWNER = Strategy Intelligence canonical SELL semantic producer, consumed by PM
PRODUCTION_SELL_SEMANTIC_ARTIFACT_CONTRACT = strategy/sell_semantic_state.json or embedded strategy_intelligence.symbol_intelligence.<symbol>.sell_semantic_state; PM-only consumer; phase31_f1e_pm_canonical_sell_semantic_integration_v1
BASE_PM_ACTION_CONTRACT = HEALTHY_OR_RECOVERING -> HOLD/ADD; WEAKENING_BUT_INTACT -> REDUCE/preserve if unrepresentable first occurrence; PERSISTENT_DETERIORATION -> PM discrete-control gate; EXIT_GRADE -> direct EXIT; UNRESOLVED -> fail-closed preserve/review
PERSISTENT_DETERIORATION_EXIT_SUFFICIENCY = CONDITIONAL
UNREPRESENTABLE_REDUCE_PRODUCTION_DISPOSITION = discrete-lot + persistent deterioration + no recovery + PIT proof complete -> PM EXIT; first weakening -> preserve; unresolved/minimum-notional -> review/preserve
ONE_LOT_STATE_ACTION_MATRIX = HEALTHY_OR_RECOVERING preserve; WEAKENING_BUT_INTACT no-order/preserve; PERSISTENT_DETERIORATION PM EXIT if full gate passes; EXIT_GRADE direct EXIT; UNRESOLVED review/preserve
ONE_LOT_AUTOMATIC_EXIT = NO
RECOVERY_OVERRIDE_CONTRACT = RESET clears hidden debt; DECAY requires fresh PIT re-evaluation; PRESERVE allows gate only when recovery absent
EXISTING_EXIT_AUTHORITY_PRESERVED = YES
61750_PRODUCTION_DISPOSITION = EXIT
61750_REASON = one-lot discrete-lot REDUCE unrepresentable, current PIT persistent deterioration from 2022-09-14, recovery guard absent, PIT proof complete; no future outcome used
RECOVERY_CONTROL_COUNT = 17
RECOVERY_PROTECTION_DESIGN = recovery evidence overrides persistence; no unrepresentability-only, one-lot-only, or count-only EXIT
MINIMUM_NOTIONAL_MUTATION_AUTHORIZED = NO
MARKET_CONTEXT_LOGIC_CHANGED = NO
FAIL_CLOSED_CONTRACT = missing SELL state/PIT/campaign/representability/conflict -> REVIEW_REQUIRED or preserve; never default EXIT
PRODUCTION_EVIDENCE_LINEAGE = original PM action; canonical SELL state; state reasons; recovery state; representability reason; one-lot flag; escalation considered/decision; final PM action; PIT proof; contract version
SHADOW_MIGRATION_PLAN = F1D semantics MIGRATE; F1D diagnostic artifact DEPRECATE; F1D tests KEEP; F1A representability logic MIGRATE; F1A artifact DEPRECATE; PM direct EXIT KEEP; PS quantity contract KEEP; Runtime mapping KEEP; minimum-notional KEEP_UNRESOLVED
EXPECTED_MUTATION_SCOPE = canonical SELL semantic production/materialization; PM consumption; PM-owned discrete-lot escalation; evidence lineage; focused regression tests
REQUIRED_REGRESSION_TESTS = normal HOLD/ADD unchanged; representable REDUCE unchanged; first one-lot weakening no EXIT; recovery reset/decay; persistent discrete-lot escalation; direct EXIT_GRADE; minimum-notional unresolved; missing PIT fail-closed; PS/Runtime no EXIT invention; no future data; campaign isolation; existing EXIT preserved
FUTURE_INFORMATION_USED_FOR_MUTATION_DESIGN = NO
OUTCOME_USED_FOR_PARAMETER_SELECTION = NO
IMPLEMENTATION_CHANGED = NO
LONG_HISTORICAL_EXECUTED = NO
MUTATION_DECISION = MUTATION_DESIGN_READY_WITH_EXPLICIT_UNRESOLVED_SCOPE
NEXT_TASK_RECOMMENDATION = Phase31-F1F focused PM canonical SELL semantic / Alternative G implementation
```

## Final Questions

1. PERSISTENT_DETERIORATION自体をPM EXITの十分条件にできるか？

   Not alone. It is sufficient only when combined with PM REDUCE, discrete-lot partial unrepresentability, no recovery, complete PIT proof, clear campaign identity, and non-minimum-notional scope.

2. できないなら、あと何のPIT semanticが必要か？

   The F1E discrete-control sufficiency gate: representability family, one-lot/no-intermediate exposure proof, recovery absence, campaign identity, and PIT proof.

3. one-lot REDUCE不能時にPMは各SELL stateで何をするべきか？

   Recovering preserves; first weakening preserves/no-order; persistent deterioration exits if the full gate passes; EXIT-grade exits directly; unresolved reviews/preserves.

4. 61750は新Production contractならどう扱われるか？

   EXIT from 2022-09-14 under the new PM-owned discrete-control gate, based only on PIT evidence.

5. recovery Winnerを守れるか？

   Yes. Recovery evidence resets or decays escalation pressure and no hidden debt survives RESET.

6. 既存EXIT 60件を壊さないか？

   Yes. Direct EXIT authority is preserved.

7. minimum-notionalを安全に分離できるか？

   Yes. F1E explicitly excludes it from mutation.

8. shadowをProduction authorityへどう移行するか？

   Migrate F1D semantics into canonical Strategy/SI SELL semantic production, then have PM consume the canonical field. Production must not consume diagnostic shadow artifacts.

9. 実装scopeをPM中心に限定できるか？

   Yes. Future implementation scope is PM/SI semantic lineage plus focused tests; PS/Runtime remain faithful consumers.

10. 次に本実装へ進める設計証拠は揃ったか？

   Yes, with explicit unresolved scope: minimum-notional and Market Context remain out of F1F.
