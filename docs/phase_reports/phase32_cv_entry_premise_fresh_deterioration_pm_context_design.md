# Phase32-CV Entry Premise / Fresh Deterioration PM Context Design

## Executive Summary

This is a design-only report. No Production code, config, threshold, runtime state, fresh-run, resume, replay, backtest, model, PM action threshold, or minimum holding period was changed.

Phase32-CU confirmed an `ENTRY_PM_CONTEXT_MIGRATION_GAP`: BUY_NEW / REENTRY may enter with `CONTINUATION_WITH_CAUTION` and `REDUCED_ALLOCATION_ONLY`, meaning weak/risk evidence is explicitly known and capitalized at entry, but PM does not receive a structured campaign-entry baseline that lets it prove whether later weakness is fresh.

Phase32-CV defines a narrow semantic repair:

```text
BUY_NEW / REENTRY fill
-> immutable campaign_entry_premise_snapshot.v1
-> PM decision date current evidence
-> entry_premise_delta.v1
-> PM classifies known-at-entry vs fresh/persistent/hard-failure evidence
-> PM preserves existing REDUCE / EXIT authority
```

The design preserves immediate EXIT for hard stop, true breakdown, Safety/Risk hard block, and genuinely fresh deterioration. It forbids only the semantic shortcut where entry-known caution alone becomes T+1 REDUCE/EXIT escalation without a fresh-delta or hard-failure classification.

## Design Sources

- `docs/phase_reports/phase32_cu_entry_premise_vs_pm_fresh_deterioration_semantic_audit.md`
- `docs/phase_reports/phase32_ct_old_vs_post_cs_5bd_capital_lifecycle_delta_audit.md`
- `docs/02_architecture/strategy_intelligence_architecture_v1.md`

Relevant SoT anchors:

- PM remains existing-position directional Action Authority.
- `positions/position_campaigns.json` is canonical campaign identity and lifecycle-history authority.
- Required campaign lifecycle facts include opened business date, campaign age, ADD history, REDUCE history, entry thesis/state, observed MFE, observed giveback, and current campaign-relative return.
- Entry thesis metadata is Strategy evidence at entry, copied with provenance, immutable except versioned annotation.
- Shared intelligence is not shared action authority.
- REDUCE/EXIT hard protections remain PM-owned and independent from BUY-side state.

## Problem Statement

Current artifact shape can show:

```text
T0 entry:
  CONTINUATION_WITH_CAUTION
  REDUCED_ALLOCATION_ONLY
  WEAK / ELEVATED_RISK evidence known

T+1 PM:
  REDUCE / EXIT
  deterioration dimensions contain WEAK / ELEVATED_RISK
```

But it does not materialize:

```text
Was the T+1 evidence new?
Was it already known and sized at entry?
Did it persist long enough to become sell-relevant?
Was there a hard failure independent of entry premise?
```

The repair should not decide that early exits are invalid. It should make the decision evidence auditable and fail-closed when the distinction cannot be made.

## Authority Ownership

| Artifact / contract | Owner | Role |
| --- | --- | --- |
| `campaign_entry_premise_snapshot.v1` | Canonical campaign lifecycle authority, sourced from Entry / Buy Quality / PC / fill lineage | Immutable entry premise for the open campaign |
| `entry_premise_delta.v1` | Strategy Intelligence / PM context adapter | PIT-safe comparison of immutable entry premise vs current PM evidence |
| PM final action | Position Management | HOLD / ADD / REDUCE / EXIT action authority remains unchanged |
| Safety / Risk Pacing | Existing guardrail authorities | Hard blocks preserved |
| Persistent ledger / campaign lifecycle | Existing ledger/campaign authority | Storage and resume continuity |

The durable SoT should be campaign-scoped, not symbol-scoped. A same symbol can have multiple campaigns across full EXIT and REENTRY.

## Entry Premise Snapshot

On every Production BUY_NEW / REENTRY fill that opens a new campaign, materialize:

```text
campaign_entry_premise_snapshot.v1
```

Minimum fields:

| Field | Meaning |
| --- | --- |
| `schema_name` | `campaign_entry_premise_snapshot` |
| `schema_version` | `v1` |
| `business_date` | entry decision / fill business date |
| `symbol` | security code |
| `position_campaign_id` | canonical campaign identity |
| `entry_semantic_type` | `BUY_NEW` / `REENTRY` |
| `entry_admission_action` | e.g. `BUY_NEW_REDUCED_ONLY`, `BUY_NEW_ALLOWED` |
| `entry_admission_state` | e.g. `CONTINUATION_WITH_CAUTION`, `HEALTHY_CONTINUATION_ENTRY` |
| `candidate_reference` | candidate lineage |
| `opportunity_rank` | decision-time rank authority |
| `opportunity_score` | uncalibrated opportunity score / expected-edge role |
| `buy_quality_action` | `FULL_ALLOCATION_ELIGIBLE`, `REDUCED_ALLOCATION_ONLY`, `BUY_WAIT`, etc. |
| `buy_quality_score` / `buy_quality_band` | Buy Quality evidence |
| `pre_quality_base_target_weight` | pre-quality PC target |
| `quality_authorized_target_weight` | Buy Quality-authorized target |
| `accepted_target_weight` / `accepted_quantity` / `accepted_notional` | actual capital premise |
| `entry_state_reason_codes` | admission reasons |
| `accepted_caution_reason_codes` | known accepted caution/risk reasons |
| `trend_state` | normalized trend health |
| `momentum_state` | normalized momentum / acceleration state |
| `relative_strength_state` | normalized relative strength |
| `participation_state` | participation quality/risk |
| `persistence_state` | entry persistence quality |
| `downside_risk_status` | entry downside risk |
| `regime_state` / `market_context_state` | PIT market/regime context |
| `risk_vector` | normalized risk dimensions and statuses |
| `source_artifacts` / `source_hashes` | Entry, Buy Quality, PC, Strategy Intelligence, fill, campaign evidence |
| `future_information_used` | `false` |
| `historical_outcome_used` | `false` |
| `snapshot_status` | `PASS` / `REVIEW_REQUIRED` |

Snapshot rules:

- Immutable after campaign open except additive versioned annotation.
- Created only after an actual opening BUY_NEW / REENTRY fill proves the campaign exists.
- Stored under the canonical campaign lifecycle path and copied into future `positions/position_campaigns.json` snapshots.
- Same-campaign ADD does not create a new entry premise; it may append ADD evidence separately.
- Full EXIT closes the campaign and freezes the snapshot for audit.
- Later REENTRY creates a new campaign and a new entry premise snapshot. Prior campaign context may be referenced as prior-exit context but must not overwrite the new campaign premise.

## PM Delta Contract

For each PM decision date and open campaign, materialize:

```text
entry_premise_delta.v1
```

Inputs:

- campaign entry premise snapshot,
- current `positions/position_campaigns.json`,
- current Strategy Intelligence,
- current technical features,
- current opportunity/rank evidence,
- current Buy Quality where applicable as evidence only,
- current PM baseline/action evidence,
- current Safety/Risk Pacing/corporate-action evidence.

Minimum output fields:

| Field | Meaning |
| --- | --- |
| `symbol` / `position_campaign_id` | campaign identity |
| `entry_business_date` / `pm_business_date` | comparison dates |
| `entry_snapshot_status` | `PASS` / `MISSING` / `AMBIGUOUS` |
| `current_evidence_status` | `PASS` / `MISSING` / `AMBIGUOUS` |
| `known_at_entry_risk` | normalized risk dimensions already accepted |
| `current_risk` | current normalized risk dimensions |
| `new_risk_dimensions` | dimensions that became worse since entry |
| `improved_dimensions` | dimensions improved since entry |
| `persistent_weakness_dimensions` | entry-known weak dimensions still present after allowed semantic confirmation, not time delay |
| `true_breakdown_dimensions` | thesis-break dimensions independent of entry premise |
| `hard_failure_status` | hard stop / hard block status |
| `fresh_deterioration_status` | `PASS` / `NO_FRESH_DETERIORATION` / `AMBIGUOUS` |
| `entry_known_only_status` | whether current sell evidence is entirely known-at-entry |
| `comparison_confidence` | `HIGH` / `MEDIUM` / `LOW` |
| `reason_codes` | exact semantic reasons |
| `recommended_pm_context_class` | one of the classes below |
| `future_information_used` | `false` |
| `historical_outcome_used` | `false` |

## PM Context Classes

### KNOWN_AT_ENTRY

Definition:

```text
Current weakness/risk dimension was already present in the immutable entry
premise and was explicitly accepted through caution/reduced sizing.
```

Decision semantics:

- Not sufficient alone for new REDUCE/EXIT escalation.
- May remain a caution/watch input.
- May combine with fresh deterioration or persistence evidence.
- Must not suppress hard stop or true breakdown.

### FRESH_DETERIORATION

Definition:

```text
Current evidence introduces new or materially worse weakness/risk not present
in the entry premise.
```

Decision semantics:

- PM may use it as REDUCE/EXIT evidence.
- T+1 immediate action is allowed if the evidence is genuinely fresh.

### PERSISTENT_DETERIORATION

Definition:

```text
Entry-known caution persists and current evidence confirms that it remains
sell-relevant rather than merely re-observed.
```

Decision semantics:

- PM may escalate when persistence is explicitly proven.
- Persistence proof must be campaign-scoped and PIT-safe.
- This is not a minimum holding period. It is a semantic comparison of repeated evidence.

### HARD_FAILURE

Definition:

```text
Hard stop, hard loss, hard Safety/Risk/corporate-action block, or equivalent
sell-authoritative failure.
```

Decision semantics:

- Entry premise does not protect the position.
- Immediate EXIT/REDUCE is preserved.
- `89180`-style hard stop remains valid.

### TRUE_BREAKDOWN

Definition:

```text
Thesis materially broken: trend/opportunity/continuation evidence crosses from
accepted caution into invalid or broken state.
```

Decision semantics:

- PM REDUCE/EXIT preserved.
- Requires explicit current breakdown evidence, not generic reuse of entry-known weakness.

### IMPROVEMENT

Definition:

```text
Entry caution has improved, or current evidence supports positive expected edge,
contained downside, recovery, or ADD-worthiness.
```

Decision semantics:

- May support HOLD.
- May feed ADD-worthiness, but ADD remains separately gated and PC-owned for capital.
- `94340` control path maps here.

### AMBIGUOUS_REVIEW_REQUIRED

Definition:

```text
Entry premise missing, comparison impossible, source conflict, stale evidence,
or incompatible campaign identity.
```

Decision semantics:

- Fail closed to review.
- No fail-open HOLD rescue.
- No silent PM escalation from missing comparison evidence.

## Decision Integration

The delta contract is a PM context input, not a replacement PM model.

Recommended integration:

```text
PM baseline evidence
+ canonical sell semantic evidence
+ entry_premise_delta.v1
-> PM action mapping
```

Rules:

- If `HARD_FAILURE` or `TRUE_BREAKDOWN`, preserve immediate PM action.
- If `FRESH_DETERIORATION`, PM may REDUCE/EXIT according to existing PM semantics.
- If `PERSISTENT_DETERIORATION`, PM may escalate when persistence is explicit.
- If `KNOWN_AT_ENTRY` only, do not escalate REDUCE/EXIT solely from that evidence.
- If `IMPROVEMENT`, allow HOLD/ADD evidence to remain visible.
- If `AMBIGUOUS_REVIEW_REQUIRED`, fail closed.

This design does not tune PM thresholds. It only provides the missing semantic comparison authority.

## Representative Cases

| Case | Entry premise | Current PM evidence | Designed classification | PM action implication |
| --- | --- | --- | --- | --- |
| `37820` | Reduced/caution; weak trend, weak participation, elevated risk known | T+1 `trend_and_opportunity_broken`, continuation/downside PASS, profitable | `KNOWN_AT_ENTRY` or `AMBIGUOUS_REVIEW_REQUIRED` unless fresh break is proven | Do not escalate solely from known entry caution |
| `67860` | Reduced/caution; weak risk family known | T+1 `trend_and_opportunity_broken`, continuation/downside PASS, profitable | `KNOWN_AT_ENTRY` / `AMBIGUOUS_REVIEW_REQUIRED` | Same |
| `76470` | Reduced/caution; weak hold inputs largely known | T+1 `weak_hold_score`, continuation/downside PASS | `KNOWN_AT_ENTRY` / `AMBIGUOUS_REVIEW_REQUIRED` | Same |
| `96100` | Reduced/caution; weak/elevated risk known, one-lot admitted | T+1 `trend_and_opportunity_broken`, profitable, continuation/downside PASS | `KNOWN_AT_ENTRY` / `AMBIGUOUS_REVIEW_REQUIRED` | Same |
| `89180` | Reduced/caution with already weak price momentum | T+1 `hard_stop_current_return` | `HARD_FAILURE` | Immediate EXIT preserved |
| `33500` | Reduced/caution but some supportive trend/relative strength | T+1 REDUCE, then persistent deterioration by 10/06 | 10/04 partial `KNOWN_AT_ENTRY`; later `PERSISTENT_DETERIORATION` | Initial escalation needs fresh proof; later escalation allowed |
| `82540` | Reduced/caution, one-lot admitted, supportive relative strength | T+1 REDUCE, T+2 persistent deterioration | 10/04 first-observation caution; 10/05 `PERSISTENT_DETERIORATION` | Later REDUCE allowed if persistence proven |
| `94340` | High quality, rank 3, manageable participation risk | T+1 HOLD, later ADD evidence | `IMPROVEMENT` / `HEALTHY_OR_RECOVERING` | HOLD/ADD path preserved |

## Persistence And Resume Safety

Storage owner:

```text
canonical campaign lifecycle / persistent campaign ledger
```

Preferred materialization:

- `positions/position_campaigns.json` contains a compact `entry_premise_snapshot` object for open campaigns.
- Persistent ledger stores the immutable source payload or hash-addressed reference at campaign-open fill.
- PM daily artifact includes `entry_premise_delta.v1` and references the immutable snapshot.

Resume safety requirements:

- Snapshot must survive restart/resume through persistent campaign identity.
- Recomputed daily Strategy Intelligence must not overwrite the immutable entry premise.
- If a resume sees an open campaign without a premise snapshot, PM emits `AMBIGUOUS_REVIEW_REQUIRED` unless a strict-prior ledger/campaign source reconstructs it PIT-safely.
- Same-day future execution and EOD reconstruction remain forbidden as decision input.

Resume safety is PARTIAL until implementation proves snapshot write/read and legacy open-campaign handling.

## Fail-Closed Conditions

`entry_premise_delta.v1` must be `AMBIGUOUS_REVIEW_REQUIRED` when:

- campaign identity missing or conflicting,
- entry premise snapshot missing for an open campaign,
- symbol-only join would be required,
- entry snapshot source hashes conflict,
- current evidence stale/missing,
- current evidence cannot be normalized to entry dimensions,
- fill lineage does not prove the opening BUY_NEW / REENTRY,
- future or historical outcome fields appear in runtime input,
- REENTRY prior campaign context is mixed into the new campaign premise.

## Preservation

Preserved:

- PM remains action authority.
- Hard stop and true breakdown remain immediate sell-authoritative.
- Safety and Risk Pacing hard blocks remain authoritative.
- Canonical SELL semantics remain in place.
- ADD semantics remain distinct from HOLD and from BUY_NEW.
- Entry/Buy Quality semantics remain owned by their current authorities.
- No minimum holding period is introduced.
- No SELL threshold tuning is introduced.
- No historical PnL/Return or winner outcome label is used.
- Historical/Demo/Production use the same PIT contract shape.

## Implementation Readiness

Implementation should be narrow and staged:

1. Add schema/materialization for `campaign_entry_premise_snapshot.v1` at campaign-open BUY_NEW / REENTRY fill.
2. Store/carry the snapshot under canonical campaign lifecycle identity.
3. Add a PM context adapter that emits `entry_premise_delta.v1`.
4. Add PM action-mapping guardrails so `KNOWN_AT_ENTRY` alone does not escalate, while `HARD_FAILURE`, `TRUE_BREAKDOWN`, `FRESH_DETERIORATION`, and `PERSISTENT_DETERIORATION` remain actionable.
5. Add focused tests for the representative cases above.

Implementation is PARTIAL-ready because the semantic contract is defined, but exact code insertion points and legacy open-campaign bootstrap behavior need a narrow implementation pass.

## Final Judgments

PHASE32_CV_ENTRY_PREMISE_CONTRACT_DEFINED = YES

PHASE32_CV_PM_DELTA_CONTRACT_DEFINED = YES

PHASE32_CV_KNOWN_CAUTION_SEPARATED = YES

PHASE32_CV_FRESH_DETERIORATION_SEPARATED = YES

PHASE32_CV_HARD_FAILURE_PRESERVED = YES

PHASE32_CV_PERSISTENT_DETERIORATION_SUPPORTED = YES

PHASE32_CV_RESUME_SAFE = PARTIAL

PHASE32_CV_IMPLEMENTATION_READY = PARTIAL

PHASE32_CV_PRODUCTION_CHANGE_THIS_TASK = NO

PHASE32_CV_NEXT_STEP = Implement a narrow campaign-entry premise snapshot plus PM entry_premise_delta materialization; do not change PM thresholds, add minimum holding days, or weaken hard-stop/true-breakdown exits.
