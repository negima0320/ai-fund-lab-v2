# Phase32-EU — REENTRY Recent-Exit Guard Replacement Architecture Design

## Scope

This is an architecture design phase only.

- Prior basis: Phase32-EQ, ER, ES, and ET.
- Target concern: REENTRY long-lived prior-history bias in current BUY capitalization.
- Production changed: NO.
- SHADOW changed: NO.
- Source/config/schema changed: NO.
- Runtime/Pending/Ledger mutated: NO.
- Fresh-run/resume/replay/long Historical executed: NO.
- Future return, later price, MFE/MAE, final campaign outcome, and Historical PnL used for design selection: NO.

The design below is based on Architecture/SoT, current source inspection, and decision-time/PIT evidence principles only.

## Design Summary

Recommended architecture:

```text
Permanent audit lineage
+ bounded recent-exit churn guard
+ ordinary current BUY evaluation after guard is no longer materially relevant
```

REENTRY should stop being an independent current investment decision semantic. It should remain as retained lineage and observability: prior campaign id, prior EXIT date, prior EXIT reason/provenance, and prior ledger/PM evidence stay auditable. But old ownership alone must not force a permanently stricter branch for rank, target weight, capital competition, or unknown-context review.

The replacement concept is:

```text
FLAT SYMBOL
  |
  +-- no prior full EXIT
  |      -> ordinary current BUY evaluation
  |
  +-- recent prior full EXIT still materially relevant
  |      -> RECENT_EXIT_CHURN_GUARD
  |
  +-- prior EXIT no longer materially relevant, or current PIT evidence requalifies
         -> ordinary current BUY evaluation with retained audit lineage
```

No concrete business-day threshold is selected in EU.

## 1. REENTRY Semantic Lifecycle Decomposition

| Bucket | Current contents | Future treatment |
|---|---|---|
| `A. AUDIT_LINEAGE_KEEP` | prior campaign id, prior EXIT date, EXIT reason/reason_codes/provenance, fills, ledger, PM evidence, campaign history | Keep permanently for observability and traceability. Must not by itself alter rank/target/allocation. |
| `B. RECENT_EXIT_CHURN_GUARD_KEEP_OR_REPLACE` | immediate rebuy prevention, same-thesis short round-trip prevention, unresolved breakdown right after EXIT | Replace current long-lived REENTRY decision branch with bounded `RECENT_EXIT_CHURN_GUARD`. |
| `C. CURRENT_DECISION_REMOVE` | old EXIT as permanent REENTRY classification, old prior reason as current target suppression, generic/unknown old context as long REVIEW_REQUIRED, ever-held vs never-held asymmetry, REENTRY-only rank/target penalty | Remove from current BUY authority once recent guard/requalification is not applicable. |
| `D. LEGACY_REMOVE` | REENTRY-only consumers that require `REENTRY_ELIGIBLE` for old symbols, old unknown-context fail-closed as current capital block, REENTRY-specific fallback/bypass guards whose only purpose is permanent branch consistency | Remove or convert to lineage/guard observability in implementation. |

## 2. New Current BUY Semantic

Future current BUY semantics should be action-neutral for flat symbols:

```text
current_buy_semantic =
  BUY_CURRENT_OPPORTUNITY
```

with independent annotations:

```text
ownership_lineage = NEVER_HELD | PRIOR_EXIT_LINEAGE_PRESENT
recent_exit_guard_state =
  NOT_APPLICABLE
  ACTIVE_RECENT_EXIT_GUARD
  CURRENT_PIT_REQUALIFIED
  EXPIRED_NOT_CURRENT_DECISION_AUTHORITY
```

This avoids the current problem:

```text
old EXIT -> permanent REENTRY -> stricter recovery branch -> target zero
```

and replaces it with:

```text
recent EXIT -> bounded guard
old EXIT -> retained lineage only unless current PIT/recent-risk contract says otherwise
```

## 3. Recent Exit Guard End Conditions

EU compares four conceptual families. No numeric parameter is selected here.

| Candidate ending concept | Strength | Risk | EU judgment |
|---|---|---|---|
| finite business-day TTL only | simple, bounded | may release weak same-thesis rebounds solely by age | insufficient alone |
| current PIT trend/momentum recovery only | uses existing evidence | may release very-near-term churn too quickly | insufficient alone |
| new thesis / renewed strength evidence | aligns with opportunity philosophy | needs strict current-evidence contract | useful |
| hard-stop/breakdown recovery | preserves safety after severe EXIT | could become another permanent penalty if unbounded | useful only while recent/material |
| combination | bounded + evidence-based + explainable | implementation must separate lineage from authority | preferred |

Preferred guard philosophy:

```text
recent-exit relevance must be bounded;
within the bounded relevance period, current PIT recovery/renewed-strength evidence can release or reduce the guard;
outside the relevance period, prior ownership remains audit lineage, not current BUY authority.
```

Existing PIT evidence to reuse:

- MA5 / short trend where available;
- close/MA trend;
- 20D momentum and short-horizon momentum;
- Entry Admission;
- Buy Quality;
- Continuation Quality;
- Downside Risk;
- Corporate Action / broker / capacity authority;
- Market/regime/risk pacing;
- PC capital competition and lot/headroom feasibility.

## 4. Identity / Campaign Semantics

REENTRY label does not need to remain as current investment decision semantic.

Recommended identity contract:

- audit identity may retain `prior_exit_lineage` and optionally legacy `reentry_lineage` for observability;
- current investment decision semantic should be ordinary flat-symbol BUY after guard expiry/requalification;
- accepted BUY after flat state always creates a new campaign id;
- old campaign id remains linked as `prior_campaign_id` / `prior_exit_campaign_id`;
- prior campaign MFE/giveback/ADD/REDUCE/EXIT history must not become current campaign state;
- BUY_ADD remains separate and applies only to currently open positions;
- flat -> buy campaign id generation remains Runtime/PC lineage driven and must not reuse closed campaign id;
- current open campaign ADD/REDUCE history remains campaign-local.

Recommended naming:

```text
current_action_type: BUY_NEW
lineage_context: PRIOR_EXIT_LINEAGE_PRESENT | NONE
recent_exit_guard_state: ...
prior_campaign_id: ...
```

The legacy word `REENTRY` may stay in audit fields, but not as the current capital-allocation branch.

## 5. History Retention vs Decision Authority

Contract:

```text
HISTORY RETENTION != CURRENT DECISION AUTHORITY
```

| Field/state | retain? | current decision consumer? | TTL / relevance | campaign scope | security scope |
|---|---|---|---|---|---|
| `prior_campaign_id` | YES | only guard/audit, not target/rank after guard | bounded for guard, permanent for audit | prior closed campaign | same symbol lineage |
| `prior_exit_business_date` | YES | YES only to evaluate recent guard state | bounded relevance | prior campaign | same symbol |
| `business_days_since_exit` | YES | YES only guard/relevance classifier | bounded relevance | derived from prior campaign | same symbol |
| `prior_exit_reason` / codes | YES | YES only while recent/material or hard-stop recovery is current | bounded/material relevance | prior campaign | same symbol |
| `source_pm_decision_id` / `source_decision_id` | YES | audit/provenance, fail-closed only for lineage materialization where required | permanent audit | prior campaign | same symbol |
| generic/unknown old context | YES | NO indefinite capital block | audit only after guard irrelevance | prior campaign | same symbol |
| `reentry_semantic_state` | transition/legacy only | remove as current BUY gate | migrate to guard/lineage fields | n/a | n/a |
| `add_history_summary` | YES | YES | current open campaign lifecycle | current campaign | no security-level inheritance |
| `reduce_history_summary` | YES | YES | current open campaign lifecycle | current campaign | no security-level inheritance |
| `prior_unrepresentable_reduce_summary` | YES | YES | active soft-deterioration episode only | current campaign | no security-level inheritance |
| order/Pending/submit history | YES | YES | order lifecycle | n/a | n/a |
| market feature history | YES | YES | rolling PIT feature windows | n/a | security market data |

## 6. Run-Age Scaling Design Target

Current hot path:

```text
_supply_prior_exit_state
-> read all executions.jsonl
-> scan strict-prior PM EXIT decisions
-> build prior_by_symbol
-> attach prior_exit_context to candidate/opportunity
-> PC REENTRY gate consumes it for current target/allocation
```

Future target:

```text
current decision hot path
-> needs only recent/material exit guard index
-> does not scan full prior history for every old symbol as current BUY authority

audit path
-> may reconstruct full prior lineage on demand or in separate evidence/indexing responsibility
```

`WHOLE_RUN_REENTRY_SCAN_REMOVABLE_FROM_HOT_PATH = PARTIAL`

Reason:

- Full audit lineage may still be useful and retained.
- Current BUY authority should not need all historical prior-exit evidence once only recent/material guard is decision-active.
- A compact run-scoped recent-exit guard index or bounded prior-exit authority can replace whole-run scans in the current decision path.
- Campaign/current-position materialization still legitimately needs current open campaign state and idempotency-safe ledger authority.

## 7. Removal Reference Graph

| Producer | Field/state | Consumer | Current behavior | New behavior | Action | Migration concern | Validation requirement |
|---|---|---|---|---|---|---|---|
| `_supply_prior_exit_state` | `prior_exit_context` | candidate/opportunity -> PC | attaches prior exit context for all strict-prior closed symbols | expose retained lineage plus bounded recent-exit guard authority; do not make all old prior exits current BUY authority | MODIFY | old artifacts still contain prior context | old-history symbols evaluate like ordinary current BUY after guard irrelevance |
| `_strict_prior_pm_exit_decision_evidence_by_campaign` | prior EXIT reason/provenance | REENTRY recovery | scans all prior PM artifacts for current recovery gate | audit/on-demand or bounded guard source; not mandatory for old non-guard BUY | MODIFY | recoverable old provenance defects must not block old current BUY indefinitely | unknown old context no long-lived review |
| `_semantic_reentry_evidence` | `semantic_buy_type=REENTRY` | PC target member | every old flat symbol becomes REENTRY | emit lineage + guard state; current action remains ordinary flat BUY unless active guard | MODIFY | legacy consumers expect REENTRY fields | compatibility fields must be audit-only or mapped |
| `_reentry_recovery_evidence` | recovery reason/status | PC eligibility | old prior reason controls target suppression indefinitely | only active inside bounded recent guard or material hard-stop recovery window | MODIFY/REMOVE | reason-specific tests need rewrite | recent hard-stop and weak recovery remain protected |
| `_canonical_reentry_semantic_eligibility` | `REENTRY_ELIGIBLE` / NOT_ELIGIBLE | PC final target | non-PASS forces target zero | replace with `recent_exit_guard_result`; old lineage non-guard does not zero target | MODIFY | CK bypass tests need new invariant | blocked recent guard cannot be relabeled executable |
| MCV `_evidence_completeness_state` | `reentry_not_currently_eligible` | unified marginal capital evidence | REENTRY_NEXT_LOT incomplete unless REENTRY_ELIGIBLE | consume guard state only; old lineage does not make opportunity incomplete | MODIFY | shadow/MCV comparison fields | old-exit vs never-held equivalence |
| PM `_cooldown_state` | `days_since_exit` | PM policy | finite cooldowns for PM rows | keep finite recent context | KEEP | avoid duplicate/conflicting guard owner | PM/PC cooldown ownership explicit |
| campaign materialization | open/closed campaign history | SI/PM/PC | reconstructs prior/current campaigns | keep current open campaign; prior closed lineage audit/index separated from current BUY authority | MODIFY | no closed campaign state inheritance | current campaign ADD/REDUCE unchanged |
| CK blocked-REENTRY bypass guard | blocked REENTRY cannot become BUY_NEW | PC rebatch | prevents invalid positive BUY_NEW after REENTRY fail | convert to guard: active blocked guard cannot become executable current BUY | MODIFY | avoid reintroducing bypass | recent blocked symbol remains blocked |
| Runtime Planning/Pending/Submit | action/provenance/campaign ids | runtime execution | consumes PC action authority | should be unchanged for ordinary BUY_NEW; guard-blocked item not submitted | KEEP | schema field compatibility | no submit for guard-blocked rows |

## 8. Safety Invariants

The future implementation must prove:

- recent EXIT churn protection remains possible;
- recent unresolved breakdown can still block/review;
- old ownership alone cannot suppress current BUY;
- unknown old EXIT context cannot indefinitely fail/review current BUY;
- never-held and sufficiently-old-exited symbols use equivalent current evidence;
- current open campaign ADD/REDUCE history remains campaign-local;
- prior closed campaign history is never inherited into new campaign state;
- accepted flat BUY after prior EXIT creates a new campaign id;
- prior campaign lineage remains auditable;
- Runtime authority, idempotency, Pending, Submit, and Ledger fail-closed behavior remain intact;
- future information remains prohibited;
- historical PnL/outcome is not used for design, threshold, ranking, or allocation.

## 9. Migration Strategy

Recommended rollout sequence:

1. Add/accept architecture and tests for lineage-vs-authority separation.
2. Introduce new guard/lineage fields while keeping legacy REENTRY fields readable for old artifacts.
3. Convert PC current decision logic from permanent REENTRY branch to bounded recent-exit guard result.
4. Update MCV/CK-style consumers to use guard state rather than `REENTRY_ELIGIBLE` as a permanent old-history requirement.
5. Preserve Runtime Planning/Pending/Submit contracts by publishing ordinary BUY_NEW authority only when guard is not active.
6. Keep prior EXIT context in audit artifacts and optional indexes.
7. Regenerate accepted artifact generation through canonical acceptance/registry path if source/schema changes are made in a later phase.

Migration judgment:

- Existing run artifacts can be read for audit.
- Old artifacts should not be rewritten.
- Fresh-run validation is likely required for Production acceptance because PC/MCV action authority artifacts change.
- Same-run source transition may be possible only through existing canonical source-transition tooling if accepted by Runtime contract; EU does not choose or execute it.
- Manual baseline edit or guard bypass is not allowed.

`MIGRATION_REQUIRED = PARTIAL`

Reason: no ledger/Pending backfill should be required for clean fresh evidence, but PC/MCV/strategy artifact schema/semantics and accepted artifact authority likely need formal transition.

## 10. Validation Plan

Focused tests required after implementation:

| Case | Setup | Expected |
|---|---|---|
| A | never-held symbol with valid PIT evidence | ordinary current BUY evaluation |
| B | very recent EXIT symbol | recent guard may block/review |
| C | old EXIT symbol | old ownership alone does not reduce rank/target/allocation |
| D | old EXIT + unknown prior context | unknown old context remains audit lineage, not indefinite BUY review |
| E | old EXIT + prior hard-stop + current strong PIT recovery | ordinary current controls own decision after guard/relevance clears; hard-stop not permanent |
| F | recent EXIT + unresolved weakness | guard blocks/reviews |
| G | current open campaign ADD | ADD/G129 and campaign-local history unchanged |
| H | current campaign REDUCE/soft deterioration | current campaign persistence/recovery unchanged |

Additional focused validation:

- active guard cannot leak into Submit;
- inactive old lineage cannot create target zero by itself;
- old-history vs never-held equivalence for matched current PIT evidence;
- CK bypass replacement: guard-blocked item cannot be rebatch-promoted as executable BUY_NEW;
- missing/malformed recent guard authority fail-closes only within current guard scope;
- historical lineage remains materialized in audit fields;
- no cross-campaign ADD/REDUCE history inheritance;
- no prior closed campaign MFE/giveback inherited into new campaign;
- whole-run strict-prior scan removed or bounded in current decision hot path;
- per-day artifact size and elapsed time tracked before/after without using PnL.

No long Historical should be run by Codex in the implementation phase. User-operated fresh/long validation can follow focused acceptance.

## Final Required Answers

- `REENTRY_CURRENT_DECISION_SEMANTIC_REMOVE = YES`
- `AUDIT_REENTRY_LINEAGE_KEEP = YES`
- `RECENT_EXIT_CHURN_GUARD_REQUIRED = YES`
- `RECENT_EXIT_GUARD_BOUNDED = YES`
- `OLD_EXIT_CURRENT_DECISION_AUTHORITY_REMOVED = YES`
- `NEVER_HELD_OLD_EXIT_EQUIVALENCE_DESIGNED = YES`
- `WHOLE_RUN_REENTRY_SCAN_REMOVABLE_FROM_HOT_PATH = PARTIAL`
- `CAMPAIGN_LOCAL_HISTORY_PRESERVED = YES`
- `MIGRATION_REQUIRED = PARTIAL`
- `IMPLEMENTATION_READY = YES`

## Recommended Architecture

Choose one architecture:

`B. REENTRY semantic縮小 + recent-exit churn guardのみ`

Why:

- It preserves the valid safety purpose: recent churn and unresolved same-thesis rebuy prevention.
- It preserves audit lineage and campaign traceability.
- It removes the proven defect: old ownership / unknown prior EXIT context as effectively permanent current BUY suppression.
- It aligns with the investment philosophy that a symbol is not penalized forever simply because it was previously held.
- It reuses existing PIT evidence rather than adding outcome-derived tuning.
- It gives a clean path to remove whole-run prior-exit scans from the current decision hot path while keeping audit reconstruction available.
- It avoids the high safety risk of full REENTRY removal without a replacement guard.

## Final Judgment

`PHASE32_EU_REENTRY_CURRENT_DECISION_SEMANTIC_REMOVE_AUDIT_LINEAGE_KEEP_BOUNDED_RECENT_EXIT_CHURN_GUARD_ARCHITECTURE_READY_FOR_IMPLEMENTATION`
