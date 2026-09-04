# Phase32-FA — EZ First Legitimate Divergence / Recent-Exit Guard Expiry Actual-Path Acceptance Audit

## Scope

- Current run: `runtime-test-historical-extended-smoke-20260903T213011268067Z`
- Reference run: `runtime-test-historical-extended-smoke-20260902T060955933565Z`
- Reference evidence source: `docs/phase_reports/phase32_ex_preserved_old_run_evidence/`
- Production changed: NO
- SHADOW changed: NO
- Source/config/schema changed: NO
- Target run mutated: NO
- Runtime/Pending/Ledger mutated: NO
- Fresh-run/resume/replay/recover executed: NO
- Future outcome used for Production judgment: NO

This audit uses current-run actual artifacts, Phase32-EX preserved old-run summaries, and the Phase32-EU/EV/EW/EY/EZ architecture and repair reports. The old reference run daily symbol-level artifacts were intentionally removed in Phase32-EX; therefore old symbol-level details such as the historical `76470:800` row cannot be independently reconstructed from preserved old-run raw artifacts. They are treated as operator-observed comparison facts, while current-run acceptance is proven from current canonical artifacts.

## Evidence Sources

- `docs/phase_reports/phase32_eu_reentry_recent_exit_guard_replacement_architecture_design.md`
- `docs/phase_reports/phase32_ev_reentry_legacy_data_retention_runtime_state_minimization_audit.md`
- `docs/phase_reports/phase32_ew_reentry_current_decision_semantic_removal_recent_exit_guard_implementation.md`
- `docs/phase_reports/phase32_ey_ew_fresh_run_early_first_divergence_read_only_audit.md`
- `docs/phase_reports/phase32_ez_bounded_recent_exit_guard_materialization_connectivity_repair.md`
- `docs/phase_reports/phase32_ex_preserved_old_run_evidence/old_run_daily_metrics.csv`
- `docs/phase_reports/phase32_ex_preserved_old_run_evidence/old_run_reentry_history_bias_minimal_evidence.json`
- Current run artifacts under `reports/runtime_tests/runs/runtime-test-historical-extended-smoke-20260903T213011268067Z/`

## Run Coverage

The current run is `RUNNING` with completed business days from `2022-10-03` through `2022-10-31`; `run_state.json` shows next job `2022-11-01:morning`. The historical evaluation authority is `PASS`, accepted generation `phase19_aq_accepted_generation_641e6e313543f013`, source commit `1f64f49ee9a8dd48280007e4df656e5f03e231ca`, `source_dirty=true`.

Current-run guard lineage is run-scoped:

- `semantic_buy_type=REENTRY` in current PC artifacts through available coverage: `0`
- active guard PC members: `66`
- expired guard PC members: `16`
- recent-exit guard materialization rows bound to current run: `109`
- stale/cross-run recent-exit guard rows: `0`

## Exact First Divergence

User-observed comparison:

| Field | Value |
|---|---|
| `FIRST_DIVERGENCE_DATE` | `2022-10-12` |
| `FIRST_DIVERGENCE_SYMBOL` | `76470` |
| old quantity | `800` |
| new quantity | `600` |
| `FIRST_DIVERGENCE_EVENT` | BUY_NEW quantity materialization differs |
| `FIRST_DIVERGENCE_STAGE` | `2022-10-12:morning` PC/PS quantity materialization, visible at Pending/Submit/Execution |

Current-run proof for the new side:

- `daily/2022-10-12/strategy/portfolio_construction.json`: `76470` is `semantic_buy_type=BUY_NEW`, `recent_exit_guard_state=NOT_APPLICABLE`, `canonical_marginal_capital_priority_index=6`.
- PC target resolution shows `base_weight=0.021765`, quality reduced target `0.0146`, incremental budget reconciliation reduced accepted increment to `0.0`, with residual reconsideration / capital competition evidence.
- `daily/2022-10-12/morning/planning_evidence.json`: `76470` executable quantity `600`, `planning_submit_feasibility_pass`.
- `daily/2022-10-12/submit/runtime_manifest.json`: `76470` Pending item `strategy-e9c926e1a28193111e09`, state `APPROVED`, side `BUY`, quantity `600`, source decision type `BUY_NEW`.
- `daily/2022-10-12/execution/fills.json`: `76470` BUY fill quantity `600`, execution price `27.0`, source decision id `rp-2022-10-12-76470-buy_new-b9c82a390eba02d3`, campaign `pc-c5e0986109845fbb-76470-0001`.

EX preserved old evidence confirms aggregate early-run comparability, but not old raw symbol-level rows. Therefore the old `76470:800` quantity is accepted only as the operator-observed old-run fact, not as independently preserved raw evidence.

## 76470 Decision Pipeline Trace

| Boundary | Current run evidence | Old comparison |
|---|---|---|
| Candidate | candidate eligible; opportunity rank preserved | symbol-level raw evidence unavailable after EX cleanup |
| BQ | `REDUCED_ALLOCATION_ONLY` | symbol-level raw evidence unavailable |
| Entry | `BUY_NEW_REDUCED_ONLY`, `CONTINUATION_WITH_CAUTION`, tick quantization caution | symbol-level raw evidence unavailable |
| PM | no PM source for BUY_NEW; not an ADD/REENTRY PM action | symbol-level raw evidence unavailable |
| PC | `BUY_NEW`, `NOT_APPLICABLE` recent-exit guard, rank 6, target ultimately `0.0` before residual/reconsideration path | symbol-level raw evidence unavailable |
| MCV | `ELIGIBLE_COMPARABLE`, `COMPARABLE_MARGINAL`; capital competition and residual reconsideration involved | symbol-level raw evidence unavailable |
| Runtime planning | positive quantity candidate resolved | symbol-level raw evidence unavailable |
| Pending/Submit | `APPROVED`, quantity `600`, reference/reservation price PASS | old observed quantity `800` |
| Execution | BUY fill `600` | old observed quantity `800` |

## 76470 Difference Causality

Classification: `C. PC / MCV capital competition derived difference`.

The 76470 current-run path does not show active recent-exit suppression or old-history penalty. The row is ordinary `BUY_NEW` with `recent_exit_guard_state=NOT_APPLICABLE`. The current evidence shows that 76470 quantity is shaped by PC/MCV capital competition, residual reconsideration, dynamic cash capacity, and lot/quantity materialization. Because the old raw PC/PS row is no longer preserved, the exact old `800 -> 600` boundary cannot be fully replayed from reference artifacts.

Acceptance judgment: `76470_DIFFERENCE_EXPECTED = YES_WITH_EVIDENCE_LIMITATION`.

Rationale: after EW/EZ, candidate/capital competition is expected to diverge once old REENTRY suppression no longer permanently removes prior-held symbols from current capital competition. The current 76470 path is PIT/current-evidence based and does not reveal a state, generation, or old-history authority defect.

## 83060 Expiry Acceptance Case

### 2022-10-04 EXIT

Actual current-run artifacts:

- `daily/2022-10-04/position_management/pm_decisions.json`: `83060` PM `EXIT`, `pm-2022-10-04-83060-exit`, campaign `pc-44641d6e44d5f85b-83060-0001`, reason `trend_and_opportunity_broken`.
- `daily/2022-10-04/execution/fills.json`: `83060` SELL `100`, source decision type `SELL_EXIT`, source decision id `rp-2022-10-04-83060-sell_exit-c7e80fc2f81f2482`.
- `daily/2022-10-04/execution/recent_exit_guard_materialization.json`: materialized guard row for `83060`, status `FAIL_CLOSED`, state `ACTIVE_RECENT_EXIT_GUARD`, TTL `3`, run id bound to the current run.

### 2022-10-05 Guard Active

Actual current-run PC row:

- `semantic_buy_type=BUY_NEW`
- `recent_exit_guard_state=ACTIVE_RECENT_EXIT_GUARD`
- `recent_exit_guard_status=FAIL_CLOSED`
- `business_days_since_exit=0`
- `prior_exit_business_date=2022-10-04`
- `prior_campaign_id=pc-44641d6e44d5f85b-83060-0001`
- `target_weight=0.0`
- `accepted_buy_new_weight=0.0`
- `lot_aware_accepted_buy_new_weight=0.0`

Runtime planning for `83060` on `2022-10-05` produced `no_order_zero_quantity_delta`; no BUY fill exists. This confirms the short-term guard blocks churn while preserving ordinary BUY_NEW semantics rather than restoring old REENTRY semantics.

### Expiry Before 2022-10-14

`recent_exit_guard.py` defines `RECENT_EXIT_GUARD_TTL_BUSINESS_DAYS = 3`. On `2022-10-11`, current PC shows `83060` as:

- `semantic_buy_type=BUY_NEW`
- `recent_exit_guard_state=EXPIRED_NOT_CURRENT_DECISION_AUTHORITY`
- `recent_exit_guard_status=PASS`
- `business_days_since_exit=4`
- `target_weight=0.0`

The execution materialization for `2022-10-11` reports `expired_count=5`, and later guard materializations no longer carry `83060` as an active row. Thus the `2022-10-04` guard expired before the `2022-10-14` BUY.

### 2022-10-14 BUY_NEW

Actual current-run artifacts:

- PC row: `83060` `semantic_buy_type=BUY_NEW`, `recent_exit_guard_state=NOT_APPLICABLE`, `recent_exit_guard_status=NOT_APPLICABLE`, no prior-exit date, no prior campaign id, `canonical_marginal_capital_priority_index=3`.
- BQ/Entry: `REDUCED_ALLOCATION_ONLY`, `BUY_NEW_REDUCED_ONLY`, `CONTINUATION_WITH_CAUTION`; current PIT evidence is sufficient and future information is false.
- PC target: `target_weight=0.063738`, lot-aware accepted weight `0.063738`.
- Planning: `planning_submit_feasibility_pass`, executable quantity `100`.
- Submit: feasibility PASS for `83060`.
- Execution: BUY fill `100`, source decision type `BUY_NEW`, source decision id `rp-2022-10-14-83060-buy_new-3cfe8756319108ce`, new campaign `pc-353ffefc940505e3-83060-0001`.

## Never-Held Equivalence After Expiry

For `83060` on `2022-10-14`, current BUY authority is not based on old EXIT reason, unknown prior context, prior ownership, hard-stop penalty, REENTRY rank downgrade, or REENTRY target suppression.

Evidence:

- `semantic_buy_type=BUY_NEW`
- `recent_exit_guard_state=NOT_APPLICABLE`
- `recent_exit_guard_status=NOT_APPLICABLE`
- `prior_exit_business_date=""`
- no prior campaign id in the PC BUY_NEW row
- source decision id is current opportunity-derived: `opportunity-2022-10-14-83060-f518d8d53341784c413e`
- no `semantic_buy_type=REENTRY` rows exist in current PC artifacts through available coverage
- no stale cross-run guard rows exist

Judgment: `NEVER_HELD_EQUIVALENCE_AFTER_EXPIRY = YES`.

## Short-Term Churn Protection

The two-sided contract is confirmed on actual path:

```text
2022-10-04 full EXIT
-> guard materialized from committed execution
-> 2022-10-05 ordinary BUY_NEW row exists but active guard target/quantity is zero
-> guard expires
-> 2022-10-14 ordinary BUY_NEW can be capitalized and executed
```

Judgment: `SHORT_TERM_CHURN_PROTECTION_CONFIRMED = YES`.

## Path Dependency After 2022-10-14

The `2022-10-14` `83060` rebuy is not a stale REENTRY rebatch. It is an ordinary BUY_NEW after guard expiry. It is still embedded in normal capital competition, cash capacity, lot feasibility, and the already-diverged portfolio path.

Therefore:

- Primary semantic divergence observed: removal of old long-lived REENTRY current-decision authority and replacement by bounded recent-exit guard behavior for prior-exit symbols.
- Downstream path dependency observed: once 76470 quantity and later holdings/cash diverge, later capital competition and position composition naturally diverge.

`83060_REBUY_PRIMARY_OR_DERIVED = PRIMARY_SEMANTIC_WITH_DOWNSTREAM_CAPITAL_COMPETITION_DEPENDENCY`.

## Required Final Answers

- `FIRST_DIVERGENCE_DATE = 2022-10-12`
- `FIRST_DIVERGENCE_SYMBOL = 76470`
- `FIRST_DIVERGENCE_STAGE = morning/PC-PS quantity materialization; visible at execution fill`
- `FIRST_DIVERGENCE_CAUSE = PC_MCV_CAPITAL_COMPETITION_DERIVED_DIFFERENCE_AFTER_REENTRY_HISTORY_AUTHORITY_REMOVAL`
- `76470_DIFFERENCE_EXPECTED = YES_WITH_EVIDENCE_LIMITATION`
- `83060_EXIT_DATE = 2022-10-04`
- `83060_GUARD_ACTIVE_ON_2022_10_05 = YES`
- `83060_GUARD_EXPIRED_BEFORE_2022_10_14 = YES`
- `83060_BUY_NEW_ON_2022_10_14 = YES`
- `OLD_REENTRY_SEMANTIC_PRESENT = NO`
- `OLD_EXIT_HISTORY_CURRENT_AUTHORITY_PRESENT = NO`
- `NEVER_HELD_EQUIVALENCE_AFTER_EXPIRY = YES`
- `SHORT_TERM_CHURN_PROTECTION_CONFIRMED = YES`
- `PRIMARY_SEMANTIC_DIVERGENCE_COUNT = 1`
- `DOWNSTREAM_PATH_DEPENDENCY_CONFIRMED = YES`
- `83060_REBUY_PRIMARY_OR_DERIVED = PRIMARY_SEMANTIC_WITH_DOWNSTREAM_CAPITAL_COMPETITION_DEPENDENCY`
- `STATE_OR_GENERATION_DEFECT_FOUND = NO`
- `PRODUCTION_REPAIR_JUSTIFIED = NO`
- `LONGER_FRESH_VALIDATION_READY = YES`

## Acceptance Classification

`A. INTENDED_BOUNDED_GUARD_BEHAVIOR_CONFIRMED`

with explicit downstream path dependency after the first quantity divergence.

## Limitations

The old reference run raw daily symbol-level artifacts were deleted in Phase32-EX. This prevents independent raw reconstruction of the old `76470:800` PC/PS/Execution row. The audit therefore separates:

- old-run aggregate preserved evidence and operator-observed first divergence; and
- current-run canonical actual-path proof that the new behavior is bounded-guard/ordinary-BUY_NEW based and not stale REENTRY authority.

This limitation does not weaken the 83060 acceptance finding, which is fully supported by current-run actual artifacts.

## Final Judgment

`PHASE32_FA_BOUNDED_RECENT_EXIT_GUARD_ACTUAL_PATH_SHORT_TERM_PROTECTION_AND_EXPIRY_REENTRY_REMOVAL_BEHAVIOR_CONFIRMED_LONGER_FRESH_VALIDATION_READY`
