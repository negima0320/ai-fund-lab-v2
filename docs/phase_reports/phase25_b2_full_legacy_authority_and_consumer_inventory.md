# Phase25-B2 Full Legacy Authority and Consumer Inventory

## 1. Executive Summary

Phase25-B2 completed a read-only repository-wide inventory of Legacy Authority and Consumer candidates. The review confirms that several legacy capital and position-count authorities are not merely old strings: they remain active in Production / Demo / Historical common Runtime paths.

No code, Strategy, Runtime behavior, config, schema, fallback, or legacy item was modified or removed.

## 2. Primary Judgment

`PHASE25_B2_LEGACY_AUTHORITY_AND_CONSUMER_INVENTORY_COMPLETE`

Critical legacy paths were confirmed, but the inventory objective was completed.

## 3. Scope and Method

Reviewed mandatory Phase25 pivot/B1 docs, Phase25 capital reports, Runtime/Strategy architecture, performance evaluation architecture, roadmap, Phase21-Phase24 legacy/migration documents, configs, schemas, Runtime modules, Strategy schema/producers, tests, fixtures, and existing runtime evidence.

The investigation followed:

```text
Definition -> Producer -> Config/Schema -> Loader -> Consumer -> Runtime Branch -> Mode Activation -> Evidence -> Replacement Contract -> Retirement Status
```

## 4. Legacy Definition Contract

For this task, a Legacy item is a retired, transitional, shadow-era, compatibility, fixed, fallback, old-authority, or misleading metadata element that may still affect Runtime decisions, test expectations, or future migration interpretation.

String existence alone was not treated as a defect.

## 5. Capital Legacy Inventory

Confirmed active:

- `P25-LEG-CAP-001`: fixed `evaluation_capital=1000000`
- `P25-LEG-CAP-002`: fixed `max_exposure=850000`
- `P25-LEG-CAP-003`: fixed `target_investment_ratio=0.85` and `cash_buffer=0.05`
- `P25-LEG-CAP-004`: fixed `max_position_weight=0.20`
- `P25-LEG-CAP-005`: ambiguous `runtime_evaluation_capital`

These are consumed by planning, ADD, feasibility, submit policy evidence, pending metadata, projection, and performance evidence.

## 6. Position Count Legacy Inventory

`P25-LEG-POS-001` confirms fixed `max_positions=5` remains active through Runtime capital policy and planning feasibility. This conflicts with the Dynamic Position Count migration target.

## 7. Cash / Exposure Legacy Inventory

Fixed cash/exposure policy remains active through:

- `target_investment_ratio=0.85`
- `cash_buffer=0.05`
- `max_exposure=850000`

The replacement is dynamic Strategy target exposure/cash reserve plus independent Safety hard limits.

## 8. Shadow-era Metadata Inventory

Confirmed conflicts:

- `P25-LEG-SCHEMA-001`: `runtime_consumer_eligibility=NOT_ELIGIBLE` remains while Runtime consumes `runtime_planning.json` and `position_sizing.json`.
- `P25-LEG-SCHEMA-002`: `production_consumer_connected=false` / `runtime_switch_performed=false` remain schema-required in several Strategy artifacts.

## 9. Accepted Generation and Model Fallback Inventory

Findings:

- `P25-LEG-GEN-001`: Accepted Generation resolver is active, but old fallback-zero is not fully proven mode-by-mode.
- `P25-LEG-GEN-002`: Historical isolated root has a default accepted generation id fallback.

No model was changed. No Accepted Generation pointer was modified.

## 10. Current / Ledger / Broker Fallback Inventory

Confirmed:

- `runtime_owned_fill_projection.py` uses `runtime_evaluation_capital or cash`.
- `default_evaluation_capital=1_000_000` exists as bootstrap compatibility.
- Broker latest snapshot promotion candidate requires stronger evidence classification.

## 11. Latest-path and Shared-state Inventory

Classified latest-path candidates:

- Feature-date latest carryover: suspected, potentially valid if business-date bounded.
- Market latest pointer fallback: suspected, potentially valid if run-scoped and temporal-checked.
- Runtime-test latest run/backup helpers: suspected reporting/operator context, not confirmed Runtime trading authority.

## 12. Historical / Demo / Test-only Logic Inventory

Confirmed acceptable:

- Historical neutral safety authority: historical-only and mode-locked.
- Non-trading-day demo override: demo-only and blocked in Production.

No Safety, Submit, or Corporate Action guard bypass was confirmed.

## 13. Config Inventory

Active legacy config authority:

- `configs/runtime_v2/capital_deployment.json`
- `configs/runtime_v2/capital_deployment_demo.json`

Non-legacy active Safety config:

- `configs/safety/portfolio_limits.json`

Strategy configs provide replacement evidence paths but are not fully connected as active consumers.

## 14. Schema and Field Inventory

Fields requiring Phase26 treatment:

- `runtime_consumer_eligibility`
- `production_consumer_connected`
- `runtime_switch_performed`
- `legacy_authority_active`
- `legacy_active_max_positions`
- `legacy_max_exposure_authority_used`
- `runtime_evaluation_capital`

## 15. Fixture and Test Expectation Inventory

Confirmed:

- Runtime tests assert fixed policy fields such as `max_positions=5`.
- Strategy tests assert shadow-era `NOT_ELIGIBLE` and `runtime_switch_performed=false`.

These tests must be migrated carefully, preserving safety and pre-switch regression coverage.

## 16. Documentation Inventory

Historical phase reports contain old capital and position-count values. They are not deletion targets, but Phase26-J should label or cross-link documents that search may confuse with current authority.

## 17. Dead Code and Compatibility Alias Inventory

No active policy loader, schema validator, accepted generation resolver, or historical safety authority was classified as dead code.

Compatibility-only items include bootstrap capital and shadow-foundation tests.

## 18. Production Active Legacy Items

Production active or suspected active:

- `P25-LEG-CAP-001`
- `P25-LEG-CAP-002`
- `P25-LEG-CAP-003`
- `P25-LEG-CAP-004`
- `P25-LEG-POS-001`
- `P25-LEG-CAP-005`
- `P25-LEG-SCHEMA-001`
- `P25-LEG-SCHEMA-002`
- `P25-LEG-CUR-001`
- `P25-LEG-LATEST-001`
- `P25-LEG-LATEST-002`

## 19. Demo Active Legacy Items

Demo active or suspected active:

- All Production items above
- `P25-LEG-CAP-006`
- `P25-LEG-CUR-002`

## 20. Historical Active Legacy Items

Historical active or suspected active:

- All core capital and schema items
- `P25-LEG-CAP-006`
- `P25-LEG-GEN-001`
- `P25-LEG-GEN-002`
- `P25-LEG-LATEST-001`
- `P25-LEG-LATEST-002`
- `P25-LEG-MODE-001`
- `P25-LEG-CLI-001`

## 21. Performance-impacting Legacy Items

Highest impact:

- fixed `evaluation_capital`
- fixed `max_exposure`
- fixed `target_investment_ratio` / `cash_buffer`
- fixed `max_positions`
- ambiguous `runtime_evaluation_capital`
- Accepted Generation fallback uncertainty

## 22. Safety / Temporal-impacting Legacy Items

Safety-sensitive:

- fixed capital caps must not be removed before Safety hard limits are preserved.
- Accepted Generation latest/default fallback could be temporal-critical if unbound.
- latest market/feature paths require bounded lookup evidence.

No direct guard bypass was confirmed.

## 23. Removal and Migration Dependencies

Retirement dependencies:

1. Define active deployment capital.
2. Switch position-count consumers.
3. Switch cash/exposure consumers.
4. Reconcile Strategy lifecycle metadata.
5. Rename/redefine `runtime_evaluation_capital`.
6. Prove Accepted Generation old fallback zero.
7. Update tests after new authority contract exists.

## 24. Phase26 Retirement Task Mapping

See `reports/phase25_b2_full_legacy_authority_and_consumer_inventory/phase26_retirement_mapping.md`.

## 25. Confirmed Gaps

Added to Gap Inventory:

- `P25-GAP-LEG-CAP-001`
- `P25-GAP-LEG-POS-001`
- `P25-GAP-LEG-EXP-001`
- `P25-GAP-LEG-SCHEMA-001`
- `P25-GAP-LEG-CAP-002`

## 26. Suspected Gaps

Added to Gap Inventory:

- `P25-GAP-LEG-GEN-001`
- `P25-GAP-LEG-TMP-001`

## 27. Non-Gaps

- Safety `portfolio_limits.json` independent hard limits are not legacy copies.
- Historical neutral safety authority is valid historical-only capability when mode-locked.
- Non-trading-day demo override is not legacy if kept demo-only and Production-blocked.
- Deterministic `sorted()` usage is not a latest fallback.

## 28. Blocking Gaps

Blocking:

- fixed active deployment capital
- fixed active max exposure/cash buffer/investment ratio
- fixed active max positions
- shadow-era metadata conflict for active Strategy Authority consumers

## 29. Non-Blocking Gaps

Non-blocking but required:

- accepted-generation old fallback-zero evidence
- latest-path bounded lookup evidence
- bootstrap capital naming/trace cleanup
- documentation labeling
- legacy test expectation migration

## 30. Recommended Next Task

`Phase25-B3 Authority Conflict Inventory`

Add an independent evidence audit candidate for Accepted Generation / latest fallback if B3 needs stronger mode-by-mode proof.

## 31. Validation

Validation performed:

- mandatory reading review
- repository-wide `rg` scans
- config inventory
- schema/field inventory
- runtime activation tracing
- runtime evidence index
- gap inventory update
- JSON validation

Validation not performed:

- no Runtime change
- no Strategy change
- no config/schema change
- no legacy/fallback removal
- no broker connection
- no long Historical test
