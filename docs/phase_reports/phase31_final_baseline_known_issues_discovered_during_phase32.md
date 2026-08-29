# Phase31 Final Accepted Baseline Known Issues Discovered During Phase32

## 1. Purpose

This document records known issues and latent defects that were discovered during Phase32 but belong to the Phase31 final accepted baseline.

It is a documentation-only known-issues record. It does not describe how to repair the issues, does not recommend Phase32 code migration, and does not change the Phase31 accepted status.

Intended future use:

- known-issues reference for any reconstruction from the Phase31 final accepted baseline;
- defect-requirements source for correctness-only reconstruction work;
- guard against accidentally importing Phase32-only strategy/capital-allocation behavior.

## 2. Phase31 Baseline Identity

Phase31 final accepted baseline:

- Commit: `887a336`
- Accepted run: `runtime-test-historical-extended-smoke-20260825T235520054579Z`
- Strategy status: `CURRENT_STRATEGY_BASELINE_ACCEPTED = YES`
- Phase31 status: `PHASE31_CLOSED = YES`
- Phase32 entry purpose: Demo / Production readiness

Authoritative basis:

- `docs/phase_reports/phase31_g139_phase31_final_closure_performance_improvement_completion.md`
- `docs/phase_reports/phase31_final_summary_and_phase32_handoff.md`
- `docs/phase_reports/phase31_to_phase32_chatgpt_handoff.md`
- `docs/phase_reports/phase32_de_phase31_final_baseline_latent_defect_extraction_audit.md`

The Phase31 accepted baseline remains accepted. This document records latent correctness and architecture issues discovered after closure; it does not reopen Phase31 performance acceptance.

## 3. Scope / Evidence Standard

Included issues are limited to Phase32-DE classifications:

- `P31_LATENT_CONFIRMED`
- `P31_LATENT_PARTIAL`
- `P32_AMPLIFIED_PREEXISTING`, Phase31 root portion only

Excluded:

- `P32_INTRODUCED`
- `NOT_PROVEN`
- Phase32-only regressions
- Phase32-only common-frontier, BF, and active consumer-switch defects
- Phase32-only PM semantic extensions

This record captures what was wrong in the Phase31 baseline. It intentionally does not include implementation instructions.

## 4. Executive Known-Issue Summary

| Issue | Status | Short Description |
|---|---|---|
| P31-KI-001 | CONFIRMED | Prior EXIT semantic information could be lost before REENTRY evaluation |
| P31-KI-002 | CONFIRMED | Source decision and campaign provenance could weaken across Runtime lifecycle boundaries |
| P31-KI-003 | PARTIAL | Campaign identity authority was not fully unified across lifecycle artifacts |
| P31-KI-004 | PARTIAL | REENTRY safety reason classification had ambiguity risk |
| P31-KI-005 | PARTIAL | BUY_ADD positive quantity authority origin was not fully unambiguous |
| P31-KI-006 | CONFIRMED | Adaptive Buy Quality reduced targets could be re-expanded downstream |
| P31-KI-007 | PREEXISTING_ROOT | PC continuous target magnitude and 100-share lot granularity had a resolution gap |

## 5. Known Issue 1 — Prior-Exit Semantic Information Loss

Issue ID: `P31-KI-001`

Status: `CONFIRMED`

Affected subsystem: Position Management, REENTRY prior-exit context, campaign lifecycle provenance.

What was wrong:

Phase31 could produce detailed Position Management EXIT reasons, but later REENTRY evaluation could receive a strict-prior context where that information was reduced to bare `EXIT` / `GENERIC` prior context. Detailed reason, reason codes, and exit authority/context were not always preserved into the downstream REENTRY semantic surface.

Observable consequence:

Later REENTRY candidates could be evaluated without knowing whether the prior exit was, for example, a detailed deterioration reason rather than a generic exit. This could cause REENTRY recovery logic to operate on lossy prior-exit context.

Why it matters for Production:

Production REENTRY decisions require point-in-time prior campaign context. If prior exit semantics are lost, REENTRY auditability and semantic eligibility are weakened even when the original PM decision was correctly generated.

Phase31 evidence:

Phase32-DE classified this as `P31_LATENT_CONFIRMED`, based on Phase32 K/L/P/W/Z findings against the Phase31 accepted run family.

What this issue is NOT:

- It is not a REENTRY threshold defect.
- It is not a request to loosen recovery gates.
- It is not evidence that REENTRY should always be bought.
- It is not a Phase32 common-frontier issue.

## 6. Known Issue 2 — Source Decision / Campaign Provenance Loss

Issue ID: `P31-KI-002`

Status: `CONFIRMED`

Affected subsystem: Runtime lifecycle, pending, order, execution, fill, persistent ledger, campaign observability.

What was wrong:

Some lifecycle boundaries could drop or weaken:

- `source_decision_id`
- `source_decision_type`
- `campaign_id`

The affected path was:

```text
Strategy decision
-> pending
-> order
-> execution
-> fill
-> persistent ledger
```

Observable consequence:

Downstream consumers could lose the ability to trace a fill or lifecycle event back to the exact Strategy decision and campaign identity that produced it.

Why it matters for Production:

Production operation depends on auditability, lifecycle continuity, restart/resume observability, ADD/SELL provenance, and REENTRY prior-context integrity. Weak provenance is not primarily an investment-selection defect; it is a lineage and control defect.

Phase31 evidence:

Phase32-DE classified this as `P31_LATENT_CONFIRMED`, using Phase32-Q/X and related provenance audits that identified persistent execution ledger provenance drops and serialized strategy-origin pending lineage weakening.

What this issue is NOT:

- It is not evidence that Candidate selection was wrong.
- It is not a target-weight or Cash policy defect.
- It is not a request to import Phase32 BF authority schemas.
- It is not a performance optimization issue.

## 7. Known Issue 3 — Campaign Identity Authority Split

Issue ID: `P31-KI-003`

Status: `PARTIAL`

Affected subsystem: Campaign lifecycle, Current position state, PM, pending/order/execution, realized/closed campaign context.

What was wrong:

Phase31 had multiple paths that could handle or derive campaign identity. Campaign identity authority was not fully centralized across:

- Current position
- Position Management
- pending/order/execution
- lifecycle artifacts
- realized or closed campaign context

This created latent risk that one real campaign could split across boundaries.

Observable consequence:

Campaign continuity could become ambiguous for ADD, partial REDUCE, full EXIT, and later REENTRY. The same symbol could appear to belong to different campaign identities depending on which artifact a downstream consumer used.

Why it matters for Production:

Production lifecycle decisions must be campaign-scoped. Symbol-only continuity is insufficient for auditability, sell attribution, REENTRY context, and restart/resume correctness.

Phase31 evidence:

Phase32-DE classified this as `P31_LATENT_PARTIAL`. Phase32-AC identified multiple campaign identity generators and incomplete persistence. Phase31 also had earlier campaign identity and ADD event-history repair history.

What this issue is NOT:

- It is not proof that all Phase31 campaign identities were wrong.
- It is not a Phase32 entry-premise snapshot requirement.
- It is not a new investment strategy rule.
- It is not a reason to use symbol-only joins.

## 8. Known Issue 4 — REENTRY Safety Reason Classification Ambiguity

Issue ID: `P31-KI-004`

Status: `PARTIAL`

Affected subsystem: REENTRY safety classification, broker/safety reason-code interpretation.

What was wrong:

The REENTRY safety path could classify textual or reason-code evidence ambiguously. Supportive or informational evidence could be misread as negative safety blocking evidence when classification relied on broad reason text semantics.

Observable consequence:

Some REENTRY candidates could be blocked by a safety label even when the underlying evidence was not a true negative safety, broker, or corporate-action block.

Why it matters for Production:

Safety must remain authoritative, but safety classification must distinguish positive/supportive, informational, unknown, and genuinely negative evidence. Otherwise, valid Production decisions can be blocked for the wrong safety reason, and audits cannot tell whether Safety actually intervened.

Phase31 evidence:

Phase32-DE classified this as `P31_LATENT_PARTIAL`. The predicate weakness existed in the Phase31 path, but Phase32 prior-context repairs made the actual impact clearer.

What this issue is NOT:

- It is not evidence that Safety should be weakened.
- It is not evidence that genuine safety blocks were invalid.
- It is not a REENTRY threshold or ranking issue.
- It is not a Cash or capital allocation issue.

## 9. Known Issue 5 — BUY_ADD Explicit Authority Ambiguity

Issue ID: `P31-KI-005`

Status: `PARTIAL`

Affected subsystem: PM ADD intent, Portfolio Construction, Position Sizing, Runtime BUY_ADD quantity authority.

What was wrong:

Phase31 had a BUY_ADD actual path, and Phase31-G129 repaired important execution connectivity. However, the authority boundary between:

- PM ADD intent
- PC/PS quantity authority
- Runtime positive BUY_ADD quantity

was not fully unambiguous. There was residual risk that a positive BUY_ADD quantity could originate from fallback or residual quantity mechanics rather than a single clear authoritative source.

Observable consequence:

BUY_ADD could become difficult to audit end to end: PM intent might exist, but the exact source of positive order quantity could be ambiguous.

Why it matters for Production:

ADD changes exposure in an existing campaign. Production must know whether an ADD order quantity comes from an authoritative capital/quantity decision, not from residual or fallback mechanics.

Phase31 evidence:

Phase32-DE classified this as `P31_LATENT_PARTIAL`. The Phase31 G129 area confirms BUY_ADD actual-path repair history; Phase32 later clarified related authority ambiguity in a different architecture.

What this issue is NOT:

- It is not a Phase32 BF-only authority issue.
- It is not evidence that Phase32 ADD expected-edge requirements existed in Phase31.
- It is not a request to change ADD thresholds.
- It is not proof that all Phase31 BUY_ADD fills were invalid.

## 10. Known Issue 6 — Adaptive Buy Quality Target Re-Expansion

Issue ID: `P31-KI-006`

Status: `CONFIRMED`

Affected subsystem: Adaptive Buy Quality, Portfolio Construction target resolution, budget/lot processing, final deployable target.

What was wrong:

In the Phase31 / OLD path, Adaptive Buy Quality could reduce an entry allocation target, but later Portfolio Construction, budget, or lot processing could re-expand the final deployable target toward the pre-quality/base target.

Observable consequence:

The effective final target could fail to preserve the sizing reduction produced by Adaptive Buy Quality. Phase32-CG/DE cite representative examples such as:

- `89180`: base about `3.3636%`, quality-adjusted about `1.9686%`, final restored toward base
- `76470`: base about `4.0000%`, quality-adjusted about `2.4384%`, final restored toward base
- `17570`: base about `3.8462%`, quality-adjusted about `2.1632%`, final restored toward base
- `37770`: base about `3.2258%`, quality-adjusted about `1.6113%`, final restored toward base

Why it matters for Production:

Buy Quality is an authority over entry quality and allocation adjustment. If its reduced target can be silently re-expanded, Production loses a decision-time risk/sizing control without explicit override.

Phase31 evidence:

Phase32-DE classified this as `P31_LATENT_CONFIRMED`. Phase32-CG explicitly found the reduction re-expansion behavior in both OLD and CURRENT paths.

What this issue is NOT:

- It is not proof that those symbols were bad selections.
- It is not a performance-based reason to reduce exposure.
- It is not a Phase32 one-lot policy.
- It is not a request to import Phase32 CH implementation.

## 11. Known Issue 7 — PC Target Magnitude / Discrete Lot Granularity

Issue ID: `P31-KI-007`

Status: `PREEXISTING_ROOT`

Affected subsystem: Portfolio Construction target magnitude, Position Sizing discrete quantity conversion, Japanese 100-share lot execution.

What was wrong:

Phase31 had a root resolution gap between continuous PC target magnitude and discrete 100-share executable quantity. A positive target weight could be economically smaller or larger than one executable trading unit, causing realized quantity to diverge from intended target magnitude.

Observable consequence:

The final executable quantity could be coarser than PC's intended target magnitude. This could manifest as one-lot dominance, target compression, or target overshoot depending on price and target size.

Why it matters for Production:

Japanese-equity execution granularity is not incidental. Production must be able to explain how continuous target weights become discrete executable quantities without silently changing the investment meaning.

Phase31 evidence:

Phase32-DE classified this as `P32_AMPLIFIED_PREEXISTING` and extracted only the Phase31 root. Phase32-AN observed target-weight compression and 100-share dominance before later Phase32 frontier changes amplified the issue.

What this issue is NOT:

- It is not a Phase32 multi-lot frontier requirement.
- It is not a Phase32 one-lot authority policy.
- It is not a fixed position-count problem.
- It is not a reason to choose thresholds from historical returns.

## 12. Explicit Non-Phase31 Issues

The following are not recorded as Phase31 final baseline known issues:

- active common marginal frontier defects;
- BF aggregated target authority defects;
- Phase32 Cash weight/notional bug;
- Phase32 frontier PIT flag omission;
- Phase32 repeated ADD lot progression bug;
- Phase32 marginal-lot cap propagation bug;
- BG non-deployable NEW promotion;
- Phase32 FAIL_CLOSED ADD frontier acceptance bug;
- Phase32 CH/CJ zero-collapse;
- Phase32 one-lot pre-zero/materialization issues;
- Phase32 `COMPARABLE_MARGINAL` one-lot block;
- CW/CY entry-premise snapshot/delta issues;
- DB blocked marginal-value candidate acceptance bug.

These were introduced by, or depended on, Phase32 architecture and consumer migration. They are not automatic Phase31 reconstruction requirements.

Also excluded:

- entry-known caution vs fresh deterioration as a Phase31 known issue.

Phase32-DE classified that item as `NOT_PROVEN` for the Phase31 final baseline.

## 13. Reconstruction Boundary

The reconstruction base is the Phase31 final accepted baseline, not the current Phase32 implementation.

Phase32 may contribute:

- evidence that a Phase31 latent issue existed;
- issue descriptions;
- reproduction conditions;
- violated contracts;
- required invariants.

Phase32 must not automatically contribute:

- implementation code;
- active common-frontier semantics;
- BF-only consumer switch semantics;
- Phase32-only PM entry-premise context;
- Phase32-only ADD value requirements;
- Phase32-created regression repairs;
- performance-driven threshold, rank, weight, Cash, or exposure choices.

The Phase31 accepted Strategy status remains valid unless a future formal audit explicitly changes it.

## 14. Final Record

PHASE32_DF_PHASE31_KNOWN_ISSUES_DOCUMENTED = YES

PHASE32_DF_CONFIRMED_ISSUES = 3

PHASE32_DF_PARTIAL_ISSUES = 3

PHASE32_DF_PREEXISTING_ROOT_ISSUES = 1

PHASE32_DF_PHASE32_ONLY_ISSUES_EXCLUDED = YES

PHASE32_DF_FIX_DESIGN_INCLUDED = NO

PHASE32_DF_PHASE31_BASELINE_REMAINS_ACCEPTED = YES

PHASE32_DF_RECONSTRUCTION_KNOWLEDGE_SOURCE_READY = YES

PHASE32_DF_NEXT_STEP = Freeze this issue record and discard Phase32-only strategy/capital-allocation implementation history from the reconstruction path.
