# Strategy Intelligence Legacy Retirement Contract v1

Created: 2026-08-16

## 1. Scope

This contract defines how old Strategy logic, consumers, adapters, fallbacks,
schemas, configs, tests, and docs are retired after Strategy Intelligence
Production migration.

No implementation is authorized by this document.

## 2. Classification Vocabulary

Every inventoried element must use exactly one classification:

```text
KEEP
MIGRATE
DEPRECATE_DURING_MIGRATION
REMOVE_AFTER_MIGRATION
```

Ambiguous classifications such as `KEEP_FOR_NOW`, `MAYBE_REMOVE`, or
`JUST_IN_CASE` are prohibited.

## 3. No Permanent Dual Strategy

Migration may temporarily run non-authoritative comparison evidence, but final
Production must converge to:

```text
ONE PRODUCTION STRATEGY AUTHORITY PATH
```

No old Strategy path, old consumer, old fallback, shadow Strategy simulation, or
temporary feature flag may remain as permanent insurance.

## 4. Retirement Completion Gate

Retirement is complete only after this ordered gate passes:

```text
new consumer implemented
-> E2E connection proven
-> focused regression PASS
-> Production authority migration
-> old consumer reference count = 0
-> old fallback reference count = 0
-> remove old implementation
-> remove obsolete config/schema/test/docs
-> post-removal regression PASS
```

Deleting code without proving references, configs, schemas, tests, and docs are
clean is not sufficient.

## 5. Shadow Retirement

| Current element | Final treatment |
|---|---|
| `strategy_intelligence_interpretation` | PROMOTE_TO_PRODUCTION_EVIDENCE |
| `proposed_decision_if_authorized` | REMOVE after Production consumers no longer need the backward-compatible alias |
| `shadow_only` / `production_authority` markers | KEEP_AS_OBSERVABILITY_ONLY only while evidence is not authoritative; replace with production lifecycle markers after migration |
| shadow comparison reports | KEEP_AS_OBSERVABILITY_ONLY during migration; do not preserve as second Strategy |
| shadow-specific consumer path | REMOVE after Production consumers use the shared SI producer |

## 6. BUY Quality Retirement Policy

BUY Quality is not automatically removed. Its responsibilities are split:

| Responsibility | Final treatment |
|---|---|
| PIT source summaries and score provenance | KEEP or MIGRATE as upstream evidence |
| relative opportunity evidence based on uncalibrated score | MIGRATE to SI Expected Edge / BUY-side consumer |
| market context quality modifier | MIGRATE or KEEP only if responsibility differs from SI regime compatibility |
| signal reliability | KEEP as source/accepted-generation integrity evidence |
| execution feasibility | KEEP where it belongs to PC/sizing/execution feasibility |
| portfolio fit | KEEP under Portfolio Construction |
| momentum trajectory BUY_WAIT interpretation | MIGRATE to SI Continuation Quality / BUY_WAIT semantics |
| duplicated CQ/Risk penalties | REMOVE_AFTER_MIGRATION after consumer references are zero |

Double-penalty of the same evidence through BUY Quality and SI is prohibited.

## 7. runtime_opportunity_score Policy

`runtime_opportunity_score` remains legitimate as an uncalibrated relative model
score and source-ranked opportunity signal.

It must be retired only from consumers that treat it as calibrated expected
return or absolute economic threshold. Such consumers must migrate to SI
Expected Edge semantics.

## 8. Fallback Retirement Policy

After a new SI evidence family becomes mandatory, missing SI evidence must not
silently fall back to old Strategy logic.

Fallbacks may remain only if they are:

- non-production demo/testing authorities,
- explicit observability,
- existing non-Strategy operational fallbacks still covered by their own
  contracts,
- migration-stage limited with an expiry condition.

## 9. Config / Schema / Adapter / Test / Doc Retirement

After Production migration:

- obsolete config keys must be removed with loader, validation, examples, and
  docs,
- obsolete schema fields must be removed from writers, readers, validators, and
  fixtures,
- compatibility adapters must be removed when consumer reference count is zero,
- old behavior-freezing tests must be migrated or removed,
- invariant tests such as BUY / SELL independence, valuation/basis, campaign
  identity, fail-closed behavior, and leakage firewall must be kept,
- durable Architecture docs must describe only the current authority path.

Historical phase reports remain as record artifacts.

## 10. Reference-Zero Audit

Before declaring legacy removal complete, the implementation task must search
and report references across:

- imports,
- config keys,
- schema fields,
- adapters,
- runtime call sites,
- fixtures,
- tests,
- durable docs.

The removal target is not complete until Production reference count is zero and
post-removal regression passes.
