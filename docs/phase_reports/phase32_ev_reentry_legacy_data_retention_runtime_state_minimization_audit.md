# Phase32-EV — REENTRY Legacy Data Retention / Runtime State Minimization Audit

## Scope

- Basis: Phase32-EU architecture design, Phase32-EQ/ER/ES/ET read-only findings, current source inspection.
- Target run context: `runtime-test-historical-extended-smoke-20260902T060955933565Z`.
- Purpose: define the minimum data-retention boundary after removing REENTRY as current-decision semantic authority.
- Production changed: NO.
- SHADOW changed: NO.
- Source/config/schema changed: NO.
- Target run mutated: NO.
- Runtime/Pending/Ledger mutated: NO.
- Fresh-run/resume/replay/long Historical executed: NO.
- Future return, later price, MFE/MAE, final campaign outcome, and Historical PnL used for Production judgment: NO.

This is a design/audit report only. It does not implement the EU architecture.

## Executive Judgment

The permanent audit lineage minimum is small and identifiable:

```text
canonical immutable sources
  - ledger orders/executions/positions/cash/events
  - PM EXIT decision artifact and hash/path
  - campaign materialization artifact at the decision date
  - prior closed campaign id/date/decision provenance pointer

bounded runtime current-decision state
  - symbol
  - most recent full EXIT business date
  - prior campaign id
  - guard-relevant recent EXIT class
  - recent-exit guard state and expiry/requalification state
  - minimal source pointer/hash
```

Full prior PM EXIT evidence, full nested `prior_exit_context`, REENTRY recovery evidence, and `REENTRY_ELIGIBLE` materialization are not required as unbounded daily runtime state. They should be retained as canonical immutable evidence or derived on demand for audit/replay.

Therefore:

- `HISTORY RETENTION != CURRENT DECISION AUTHORITY`
- `AUDITABILITY != DAILY RUNTIME DUPLICATION`
- old prior ownership may remain auditable, but must not require daily current-decision reconstruction or PC/MCV target-zero eligibility state after the recent/material guard is no longer active.

## Evidence Sources

Phase reports:

- `docs/phase_reports/phase32_eq_long_run_state_history_accumulation_dependency_capital_suppression_root_cause_audit.md`
- `docs/phase_reports/phase32_er_long_lived_historical_penalty_security_level_bias_exhaustive_read_only_audit.md`
- `docs/phase_reports/phase32_es_reentry_functional_necessity_minimal_churn_protection_boundary_audit.md`
- `docs/phase_reports/phase32_et_cross_cutting_long_lived_history_decision_bias_exhaustive_read_only_audit.md`
- `docs/phase_reports/phase32_eu_reentry_recent_exit_guard_replacement_architecture_design.md`

Source paths inspected:

- `src/ai_fund_lab_v2/strategy/shadow_runtime.py`
- `src/ai_fund_lab_v2/strategy/portfolio_construction.py`
- `src/ai_fund_lab_v2/strategy/position_sizing.py`
- `src/ai_fund_lab_v2/runtime_v2/position_sizing_authority.py`
- Architecture references in `docs/02_architecture/strategy_architecture_v1.md` and `docs/02_architecture/strategy_intelligence_architecture_v1.md`.

## Current Producer / Consumer / Persistence Path

Current hot path:

```text
shadow_runtime._supply_prior_exit_state
-> read persistent_ledger/executions.jsonl
-> resolve latest strict-prior closed campaign by symbol
-> scan strict-prior PM EXIT decisions for reason/provenance
-> attach prior_exit_context to candidate and opportunity summaries
-> portfolio_construction._semantic_reentry_evidence
-> _reentry_recovery_evidence
-> _canonical_reentry_semantic_eligibility
-> PC target/member output
-> PS/runtime authority and MCV completeness consumers
```

The problematic retention pattern is not the immutable history itself. The problem is daily runtime re-materialization of whole-run prior-exit lineage into current candidate/opportunity/PC rows, where it remains a current target/allocation authority.

## A. Permanent Audit Lineage Minimum

Permanent audit lineage must preserve enough evidence to reconstruct:

- what campaign was previously closed;
- when the EXIT happened;
- which PM EXIT decision and lifecycle/execution evidence authorized it;
- what reason/reason_codes were emitted at that time;
- whether a future current-decision artifact was PIT-correct and did not use future information.

It does not require daily candidate/opportunity/PC artifacts to embed the full prior PM EXIT payload forever.

Minimum permanent source set:

| Evidence | Keep as canonical source? | Runtime daily duplication required? | Notes |
|---|---:|---:|---|
| Ledger executions/orders/positions/cash/events | YES | NO | Immutable replay/accounting source. |
| PM EXIT artifact row and artifact hash/path | YES | NO | Source of prior EXIT reason/provenance. |
| Campaign id/date/materialization artifact | YES | NO | Needed for audit and campaign identity reconstruction. |
| Prior closed campaign pointer in later audit artifact | PARTIAL | PARTIAL | Pointer useful while recent guard is active; old lineage can be derived on demand. |
| Full prior PM EXIT evidence payload in current PC row | NO | NO | Derive from canonical PM artifact when auditing. |
| Full nested `prior_exit_context` in every candidate/opportunity row | NO | NO | Replace with bounded guard annotation or lineage pointer only. |

Conclusion:

`PERMANENT_AUDIT_LINEAGE_MINIMUM_IDENTIFIED = YES`

## B. Recent-Exit Guard Minimal Runtime State

The current decision hot path only needs enough state to answer:

```text
Is this symbol still inside a recent/material post-EXIT churn guard,
and if yes, has current PIT evidence requalified it?
```

Minimal bounded state:

| Field | Required in current hot path? | Retention |
|---|---:|---|
| `symbol` | YES | bounded guard index |
| `most_recent_full_exit_business_date` | YES | bounded guard index |
| `prior_campaign_id` | YES as pointer | bounded guard index; permanent in canonical source |
| `guard_relevant_exit_class` | YES | coarse current guard class, not full old PM payload |
| `guard_state` | YES | `NOT_APPLICABLE` / `ACTIVE` / `CURRENT_PIT_REQUALIFIED` / `EXPIRED` |
| `guard_expiry_or_requalification_status` | YES | bounded |
| `source_pm_decision_id` / `source_decision_id` | YES as pointer | bounded pointer; full evidence derived |
| source artifact path/hash/run/date binding | YES | bounded pointer for validation |
| full reason_codes/context payload | NO | canonical source / derive on demand |
| historical same-symbol campaign list | NO | audit path only |

This means old prior EXIT reason is not current runtime authority after guard irrelevance. A recent/material classification may use a coarse guard-relevant class, but full old reason/reason_codes should remain canonical source data, not a permanent daily decision payload.

Conclusion:

`RECENT_EXIT_GUARD_MINIMAL_STATE_IDENTIFIED = YES`

## C. Whole-Run Scan Removal From Current Decision Hot Path

Reverification against EU:

| Path | Current whole-run dependency | Can be removed from current decision hot path? | Replacement |
|---|---|---:|---|
| Candidate generation | attaches `prior_exit_context` for all strict-prior old symbols | YES | no old REENTRY classification; optional bounded guard index lookup |
| PC | consumes `semantic_buy_type=REENTRY` and `REENTRY_ELIGIBLE` | YES | consume `recent_exit_guard_state` only |
| MCV | marks `REENTRY_NEXT_LOT` incomplete unless eligible | YES | consume bounded guard state; old lineage is not incompleteness |
| PM | current open campaign controls | NOT REENTRY-SPECIFIC | keep current campaign-local history |
| Runtime planning | campaign/provenance/order authority | NOT REENTRY-SPECIFIC | unchanged; guard-blocked items remain non-submittable |
| Audit/reconstruction | may scan ledger/PM/campaign history | NO need to remove | allowed outside daily current-decision hot path |

Conclusion:

`WHOLE_RUN_REENTRY_SCAN_FULLY_REMOVABLE_FROM_CURRENT_DECISION_HOT_PATH = YES`

Important qualifier: full history remains valid for audit/replay/reconstruction. The `YES` applies to current daily investment decision hot path, not to offline forensic tools.

## D. Run-Age Artifact Growth Relation

EQ found daily artifact size growth from about `112.8MB` early to `251.5MB` late, and elapsed time growth from about `106.63s/day` in days 1-100 to `284.42s/day` in days 501-end. Correlations were high for run age, campaign count, and closed campaign count versus elapsed time.

REENTRY/prior-exit-related growth mechanisms:

| Mechanism | Growth order | EV judgment |
|---|---|---|
| `executions.jsonl` full read and closed-campaign reconstruction | `O(executions)` per day | contributes to runtime scaling |
| strict-prior PM EXIT scan | `O(run age x PM artifact rows)` unless indexed | contributes to runtime scaling |
| attaching prior_exit_context to candidate/opportunity rows | `O(candidates x context size)` per day | unnecessary daily duplication after EU |
| PC `semantic_reentry_authority` nested per REENTRY member | `O(REENTRY candidate rows)` per day | removable legacy current-decision materialization |
| MCV reentry completeness fields | `O(REENTRY candidate rows)` per day | removable or guard-only |
| campaign materialization carrying closed/current summaries | `O(campaigns)` where serialized | partly legitimate, but closed prior lineage should not be duplicated for BUY authority |
| accepted-generation artifacts | `O(generations)` | canonical authority, not daily runtime duplication |

Conclusion:

`RUN_AGE_ARTIFACT_GROWTH_REENTRY_RELATED = MIXED`

Reason: REENTRY/prior-exit duplication is a real component, but not the only source of artifact growth. Market refresh, daily manifests, submit/runtime observability, and general campaign/ledger artifacts also scale.

## E. Runtime Slowdown Relation

History-dependent code paths that can affect runtime:

- `shadow_runtime._supply_prior_exit_state` reads all `executions.jsonl` and attaches prior exit state every day.
- `_resolve_prior_closed_campaigns_from_executions` sorts/walks strict-prior executions.
- `_strict_prior_pm_exit_decision_evidence_by_campaign` scans prior PM artifacts.
- `_materialize_pre_action_position_campaigns` discovers/carries prior campaign artifacts.
- Runtime/report/recovery tooling also performs run-level daily glob and ledger scans.

REENTRY/prior-exit is structurally related to slowdown, especially in `morning` strategy materialization. It is not the sole cause: EQ showed `market_refresh` and `submit` also dominate late-run elapsed increases.

Conclusion:

`RUN_AGE_RUNTIME_SLOWDOWN_REENTRY_RELATED = MIXED`

## EU Keep Targets Reclassified

| EU target / current field or state | EV classification | Current-decision retention after EU | Notes |
|---|---|---|---|
| Ledger executions/orders/positions/cash/events | `KEEP_CANONICAL_SOURCE` | not daily duplicated | Immutable audit/replay/accounting source. |
| PM EXIT artifact row | `KEEP_CANONICAL_SOURCE` | pointer only while guard active | Full reason/provenance derives on demand. |
| campaign materialization for actual BUY/SELL lifecycle | `KEEP_CANONICAL_SOURCE` | current open campaign only | Closed campaign lineage audit source remains. |
| accepted artifact registry/checkpoint | `KEEP_CANONICAL_SOURCE` | authority resolver only | Not a decision history penalty. |
| `prior_campaign_id` | `BOUNDED_RUNTIME_KEEP` + `KEEP_CANONICAL_SOURCE` | guard pointer while active | Permanent in canonical audit source; old lineage derive on demand. |
| `prior_exit_business_date` | `BOUNDED_RUNTIME_KEEP` + `KEEP_CANONICAL_SOURCE` | needed for guard age/relevance | Permanent source remains PM/ledger/campaign. |
| `business_days_since_exit` | `DERIVE_ON_DEMAND` / bounded computed value | compute from exit date and current date | Do not store indefinitely per daily row. |
| `prior_exit_reason` | `BOUNDED_RUNTIME_KEEP` + `DERIVE_ON_DEMAND` | coarse guard class only while material | Full old reason is canonical PM source. |
| `reason_codes` | `DERIVE_ON_DEMAND` | no full daily duplication | Use for audit/replay, not permanent current target block. |
| `source_pm_decision_id` | `BOUNDED_RUNTIME_KEEP` + `KEEP_CANONICAL_SOURCE` | pointer only | Full PM row derived on demand. |
| `source_decision_id` | `BOUNDED_RUNTIME_KEEP` + `KEEP_CANONICAL_SOURCE` | pointer only | Needed for lineage validation. |
| full `prior_exit_context` nested in candidate/opportunity | `DERIVE_ON_DEMAND` / `REMOVE_LEGACY` from hot path | no | Replace with minimal guard pointer/status. |
| candidate/opportunity prior-exit lineage duplication | `REMOVE_LEGACY` for old non-guard rows; `BOUNDED_RUNTIME_KEEP` for active guard | bounded only | Audit can reconstruct. |
| `semantic_buy_type=REENTRY` | `REMOVE_LEGACY` | no current BUY branch | Replace by ordinary BUY plus lineage/guard annotation. |
| `reentry_semantic_state` | `REMOVE_LEGACY` | no | Replace with `recent_exit_guard_state`. |
| `REENTRY_ELIGIBLE` | `REMOVE_LEGACY` | no | Eligibility becomes ordinary current BUY unless guard active. |
| `reentry_recovery_status/reason` | `BOUNDED_RUNTIME_KEEP` for active guard; otherwise `REMOVE_LEGACY` | bounded only | Old recovery evidence audit-only. |
| `reentry_unknown_prior_context_status` | `REMOVE_LEGACY` as long-lived block | no | Unknown old context must not persist as capital block. |
| MCV `reentry_not_currently_eligible` | `REMOVE_LEGACY` | no | Replace with guard-state incompleteness only. |
| CK blocked-REENTRY bypass guard | `REMOVE_LEGACY` / guard rewrite | active guard only | Prevent active guard bypass, not old lineage penalty. |
| PM current open-campaign add/reduce history | `KEEP_CANONICAL_SOURCE` / `BOUNDED_RUNTIME_KEEP` | yes, campaign-local | Not REENTRY legacy; preserve current campaign controls. |
| Runtime Pending/order idempotency history | `KEEP_CANONICAL_SOURCE` / lifecycle bounded keep | yes, order-local | Not security-level penalty. |
| whole-run PM EXIT scan for current BUY | `DERIVE_ON_DEMAND` | no | Offline audit/replay only or bounded indexed source. |
| whole-run `executions.jsonl` scan for prior-exit BUY classification | `DERIVE_ON_DEMAND` / replace in hot path | no | Current decision should use bounded guard index. |
| reentry recovery evidence in daily PC/PS rows | `REMOVE_LEGACY` outside active guard | no | Old artifacts can remain historically readable. |
| MCV reentry completeness state | `REMOVE_LEGACY` outside active guard | no | Unified opportunity evidence should be action-neutral. |
| caches/indexes/state files for recent exits | `BOUNDED_RUNTIME_KEEP` | yes | Explicit TTL/requalification/run binding required. |

## Minimal Data-Retention Contract

Recommended boundary:

```text
1. Immutable audit sources remain append-only:
   Ledger + PM artifacts + campaign materialization + registry/hash evidence.

2. Current decision hot path keeps only bounded recent-exit guard index:
   symbol, most recent full EXIT date, prior campaign pointer, coarse guard class,
   guard state, expiry/requalification status, source pointer/hash.

3. Daily candidate/opportunity/PC/MCV artifacts do not embed full old prior-exit
   PM evidence after guard irrelevance.

4. Offline audit/replay tools may reconstruct prior EXIT lineage by scanning
   immutable sources, but this reconstruction is not Production current-decision authority.
```

## Fail-Closed Boundaries Preserved

This minimization must still fail closed for:

- malformed guard index;
- stale run/date/source binding;
- future EXIT date used as prior evidence;
- missing source pointer while guard is active;
- active recent-exit guard being silently converted to executable BUY;
- duplicate or ambiguous canonical EXIT evidence inside the active guard;
- current campaign ADD/REDUCE/EXIT identity mismatch;
- Pending/order/submit/execution idempotency ambiguity.

It should not fail closed forever for:

- old prior ownership with expired/non-material guard relevance;
- old unknown/generic EXIT context when current PIT evidence is being evaluated as ordinary BUY;
- missing full old PM payload when canonical pointer exists and current guard no longer needs it.

## Implementation Scope Minimization

EV supports a smaller implementation than a broad schema/history rewrite:

1. Introduce or materialize bounded `recent_exit_guard_state` / guard index.
2. Stop classifying every old same-symbol prior EXIT as current `semantic_buy_type=REENTRY`.
3. Convert PC/PS/MCV consumers from `REENTRY_ELIGIBLE` to active guard state.
4. Keep lineage pointers, not full nested prior EXIT payload, in current hot-path artifacts.
5. Move full prior-exit reconstruction to audit/replay/on-demand utilities or an indexed canonical authority source.
6. Preserve current open-campaign PM/ADD/REDUCE/EXIT history unchanged.

No Strategy threshold, rank, weight, candidate selection, BQ, cash policy, risk pacing, SELL/REDUCE, G129, or runtime idempotency semantic change is justified by EV.

## Required Answers

- `PERMANENT_AUDIT_LINEAGE_MINIMUM_IDENTIFIED = YES`
- `DAILY_RUNTIME_DUPLICATION_REQUIRED = PARTIAL`
- `OLD_PRIOR_EXIT_REASON_RUNTIME_RETENTION_REQUIRED = PARTIAL`
- `FULL_PRIOR_PM_EVIDENCE_RUNTIME_RETENTION_REQUIRED = NO`
- `RECENT_EXIT_GUARD_MINIMAL_STATE_IDENTIFIED = YES`
- `WHOLE_RUN_REENTRY_SCAN_FULLY_REMOVABLE_FROM_CURRENT_DECISION_HOT_PATH = YES`
- `LEGACY_REENTRY_DATA_REMOVABLE = PARTIAL`
- `RUN_AGE_ARTIFACT_GROWTH_REENTRY_RELATED = MIXED`
- `RUN_AGE_RUNTIME_SLOWDOWN_REENTRY_RELATED = MIXED`
- `IMPLEMENTATION_SCOPE_CAN_BE_MINIMIZED = YES`
- `IMPLEMENTATION_READY_AFTER_EV = YES`

## Final Judgment

`PHASE32_EV_REENTRY_LEGACY_RUNTIME_DUPLICATION_MINIMIZATION_BOUNDARY_DEFINED_IMPLEMENTATION_READY_NO_PRODUCTION_CHANGE`
