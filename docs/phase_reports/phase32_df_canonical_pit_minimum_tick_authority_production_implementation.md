# Phase32-DF - Canonical PIT Minimum-Tick Authority Production Implementation

## Scope

Phase32-DF implemented the Phase32-DE canonical PIT minimum-tick authority as an
authority-only Production foundation.

DF answers:

- "What is one tick for this symbol/date/reference price?"

DF does not answer:

- "Should this stock be bought?"

No DC Candidate / BUY Quality / Entry promotion was implemented. No Strategy
threshold, weight, rank semantics, hard minimum price rule, symbol blacklist, or
Historical PnL tuning was introduced.

No fresh-run, resume, recover, replay, or long Historical command was executed.
The active target run `runtime-test-historical-extended-smoke-20260901T223409325599Z`
was not mutated.

## Root Implementation

Implemented a new deterministic authority module:

- `src/ai_fund_lab_v2/strategy/minimum_tick_authority.py`

Core contract:

```text
resolve_minimum_tick(
    symbol,
    business_date,
    reference_price,
    security_metadata,
)
```

Outputs:

- `KNOWN`
- `NOT_APPLICABLE`
- `INSUFFICIENT_EVIDENCE`

The authority emits `minimum_tick_authority.v1` with:

- symbol/date/reference price
- minimum tick
- `single_tick_pct`
- JPX rule id/version/effective date range
- security type
- market/segment
- tick table class
- classification source/as-of
- resolution status and reason codes
- source artifact/hash
- runtime run binding
- PIT status
- stable `authority_hash`

## PIT Security Metadata Source

`PIT_SECURITY_METADATA_SOURCE = existing J-Quants listed issues / historical listed issues snapshot evidence`

The implementation uses existing listed-issues metadata when it is provided to
the Technical Features materializer:

- `ProdCat`
- `MktNm`
- `ScaleCat`
- `Date`
- source path/hash

The runtime Strategy shadow materialization now passes:

- `strategy_sources["paths"]["listed_issues"]`

to:

- `produce_pm_technical_feature_artifact(...)`

This keeps ownership at the market/security / Technical Features boundary, not
inside PC.

If listed/security metadata is not available or cannot prove a table class, the
authority returns explicit `INSUFFICIENT_EVIDENCE`. It does not invent metadata.

## Versioned JPX Tick Resolver

`CANONICAL_MINIMUM_TICK_RESOLVER_IMPLEMENTED = YES`

Implemented version:

- `tick_rule_id = JPX_TSE_CASH_EQUITY_PRICE_INCREMENT`
- `tick_rule_version = JPX_TSE_CASH_TICK_TABLE_PRE_2027`
- `effective_from = 2014-07-22`
- `effective_to = 2027-02-28`

Supported classes:

- `OTHER_ISSUES`
- `TOPIX500`
- `ETF_UNIT_1`

Current classification rules:

| Metadata shape | Tick table class |
| --- | --- |
| `ProdCat=011` and `ScaleCat` in `TOPIX Core30`, `TOPIX Large70`, `TOPIX Mid400` | `TOPIX500` |
| `ProdCat=011` and not TOPIX500-scale | `OTHER_ISSUES` |
| Explicit `tick_table_class` / `minimum_tick_table_class` fixture | That explicit supported class |
| Missing security type / unsupported class | `INSUFFICIENT_EVIDENCE` or `NOT_APPLICABLE` |

This is not a universal 1 JPY rule.

## Historical PIT Safety

`HISTORICAL_TICK_RULE_PIT_SAFETY = PASS`

The resolver selects rule version from `business_date`. Future rule versions are
not used for 2022-2023 decisions. Dates after the implemented pre-2027 rule
window return explicit insufficiency until a future JPX rule resolver is added.

`TICK_REFERENCE_PRICE_PIT_SAFE = YES`

Technical Features uses the same decision-time PIT reference price already
materialized from J-Quants daily quotes. The resolver does not use future fill
price, execution price, or unavailable intraday data.

## Technical Features Artifact

`MINIMUM_TICK_AUTHORITY_ARTIFACT_IMPLEMENTED = YES`

`strategy/input_materialization.py` now:

- accepts optional `listed_issues_path` and `runtime_run_id`
- reads PIT listed metadata rows not after `feature_date`
- emits row-level `minimum_tick_authority`
- emits `minimum_tick_authority_status`
- emits `minimum_tick_authority_hash`
- emits `minimum_tick_resolution`
- records listed issues source/hash in upstream hashes when provided

Missing tick authority is item-scoped evidence, not a global Technical Features
producer failure while DC behavior remains unpromoted.

`CANONICAL_TICK_PRODUCER_OWNER = Technical Features / market-security evidence boundary`

## Strategy Context Propagation

`CANONICAL_TICK_CONTEXT_PROPAGATED = YES`

Propagation added through:

- `strategy/shadow_runtime.py`
- `strategy/portfolio_construction.py`
- `strategy/position_sizing.py`

The Strategy shadow runtime now supplies Technical Features minimum-tick fields
into Strategy source rows. PC preserves them into member fields and
`low_price_risk_allocation_authority`. PS preserves them in sizing context.

Behavior not changed:

- `CANDIDATE_BEHAVIOR_CHANGED = NO`
- `BQ_BEHAVIOR_CHANGED = NO`
- `ENTRY_BEHAVIOR_CHANGED = NO`
- `DC_STRATEGY_PROMOTION_EXECUTED = NO`

## PC Migration

`PC_CANONICAL_TICK_MIGRATION = PASS`

PC now uses canonical tick only when:

- `minimum_tick_authority_status = KNOWN`

or the nested authority/resolution status is `KNOWN`.

When KNOWN, existing PC formulas are preserved:

```text
single_tick_pct = minimum_tick / reference_price
price_tick_risk_tier = existing tier map
price_tick_cap_weight = existing PRICE_TICK_RISK_CAPS
```

Unchanged cap thresholds:

| Tier | Cap |
| --- | ---: |
| `WATCH` | 0.12 |
| `ELEVATED` | 0.10 |
| `SEVERE` | 0.08 |
| `EXTREME` | 0.05 |

`PC_LOW_PRICE_ALLOCATION_SEMANTICS_CHANGED = NO`

When canonical tick equals the previous effective tick, focused PC tests confirm
the same tier/cap/target allocation semantics.

## Silent Fallback Removal

`SILENT_DEFAULT_TICK_DECISION_PATH_REMOVED = YES`

`DEFAULT_MINIMUM_TICK = 1.0` remains as a legacy constant in source, but PC no
longer silently uses it to create decision-material tick authority when no
canonical authority is present.

Legacy explicit `minimum_tick` / `tick_size` / `price_tick` fields without
authority are treated as non-authoritative for the PC decision-material tick cap
path.

`MISSING_TICK_AUTHORITY_FAIL_CLOSED = EXPLICIT_ITEM_SCOPED`

Because Candidate/BQ/Entry behavior is not promoted in DF, unresolved tick
authority is propagated as explicit row evidence. It does not globally HALT the
runtime while item-scoped handling is possible.

## DD Control Set Revalidation

`DD_CONTROL_SET_CANONICAL_TICK_REVALIDATION = PASS_WITH_RESOLVED_PIT_LISTED_METADATA`

Using existing J-Quants historical listed-issues snapshots, the DD control set
resolved as follows:

| Date | Symbol | Reference price | PIT `ProdCat` | PIT `ScaleCat` | Tick class | Canonical tick | `single_tick_pct` |
| --- | --- | ---: | --- | --- | --- | ---: | ---: |
| 2023-03-15 | 93180 | 3.0 | 011 | `-` | `OTHER_ISSUES` | 1.0 | 0.33333333 |
| 2023-02-21 | 93180 | 2.0 | 011 | `-` | `OTHER_ISSUES` | 1.0 | 0.5 |
| 2022-10-03 | 89180 | 9.0 | 011 | `TOPIX Small 2` | `OTHER_ISSUES` | 1.0 | 0.11111111 |
| 2022-11-22 | 76470 | 27.0 | 011 | `-` | `OTHER_ISSUES` | 1.0 | 0.03703704 |
| 2022-11-25 | 76470 | 27.0 | 011 | `-` | `OTHER_ISSUES` | 1.0 | 0.03703704 |
| 2022-10-07 | 33500 | 39.8 | 011 | `-` | `OTHER_ISSUES` | 1.0 | 0.02512563 |
| 2022-10-12 | 76470 | 28.0 | 011 | `-` | `OTHER_ISSUES` | 1.0 | 0.03571429 |
| 2023-04-13 | 67400 | 50.0 | 011 | `TOPIX Small 1` | `OTHER_ISSUES` | 1.0 | 0.02 |
| 2023-03-15 | 76920 | 563.7 | 011 | `-` | `OTHER_ISSUES` | 1.0 | 0.00177399 |
| 2023-03-15 | 94320 | 157.9 | 011 | `TOPIX Core30` | `TOPIX500` | 0.1 | 0.00063331 |
| 2023-03-15 | 83060 | 861.5 | 011 | `TOPIX Core30` | `TOPIX500` | 0.1 | 0.00011608 |

Key result:

- The low-price DD controls resolve to 1.0 JPY with actual PIT listed metadata.
- 94320 and 83060 resolve to 0.1 JPY under the TOPIX500 fine-tick table.
- This confirms that the previous universal fallback was not Production-safe
  even though it happened to match several low-price Other Issues cases.

## Validation Results

`FOCUSED_REGRESSION_RESULT = PASS`

Commands run:

```text
PYTHONPYCACHEPREFIX=/private/tmp/pycache python3 -m py_compile src/ai_fund_lab_v2/strategy/minimum_tick_authority.py src/ai_fund_lab_v2/strategy/input_materialization.py src/ai_fund_lab_v2/strategy/portfolio_construction.py src/ai_fund_lab_v2/strategy/shadow_runtime.py src/ai_fund_lab_v2/strategy/position_sizing.py
```

Result:

```text
PASS
```

```text
PYTHONPATH=src PYTHONPYCACHEPREFIX=/private/tmp/pycache python3 -m pytest -q tests/strategy/test_phase32_df_minimum_tick_authority.py tests/strategy/test_phase22_qe_input_materialization.py tests/strategy/test_phase22_e_portfolio_construction.py tests/strategy/test_phase22_j_position_sizing.py tests/runtime_v2/test_phase26_step4_position_sizing_authority.py tests/strategy/test_phase31_g44_add_reentry_lot_binding_integration.py tests/strategy/test_phase31_b4_marginal_capital_value_shadow.py
```

Result:

```text
274 passed
```

Focused coverage:

| Requirement | Result |
| --- | --- |
| Canonical resolver | PASS |
| Artifact/schema | PASS |
| Technical Features propagation | PASS |
| PC migration | PASS |
| PS context preservation | PASS |
| Historical PIT rule version | PASS |
| Missing metadata explicit insufficiency | PASS |
| Special fine-tick fixture | PASS |
| Other Issues low-price fixture | PASS |
| Stale/cross-run rejection | PASS |
| Existing PC low-price guard | PASS |
| G129/BUY_ADD adjacent ADD/lot regressions | PASS |

## Files Changed

- `src/ai_fund_lab_v2/strategy/minimum_tick_authority.py`
- `src/ai_fund_lab_v2/strategy/input_materialization.py`
- `src/ai_fund_lab_v2/strategy/shadow_runtime.py`
- `src/ai_fund_lab_v2/strategy/portfolio_construction.py`
- `src/ai_fund_lab_v2/strategy/position_sizing.py`
- `tests/strategy/test_phase32_df_minimum_tick_authority.py`
- `tests/strategy/test_phase22_e_portfolio_construction.py`
- `docs/phase_reports/phase32_df_canonical_pit_minimum_tick_authority_production_implementation.md`

## Required Answers

1. `PIT_SECURITY_METADATA_SOURCE = existing J-Quants listed issues / historical listed issues snapshots; ProdCat/MktNm/ScaleCat/Date source path/hash used as PIT security metadata`
2. `CANONICAL_MINIMUM_TICK_RESOLVER_IMPLEMENTED = YES`
3. `HISTORICAL_TICK_RULE_PIT_SAFETY = PASS`
4. `TICK_REFERENCE_PRICE_PIT_SAFE = YES`
5. `MINIMUM_TICK_AUTHORITY_ARTIFACT_IMPLEMENTED = YES`
6. `CANONICAL_TICK_PRODUCER_OWNER = Technical Features / market-security evidence boundary`
7. `CANONICAL_TICK_CONTEXT_PROPAGATED = YES`
8. `CANDIDATE_BEHAVIOR_CHANGED = NO`
9. `BQ_BEHAVIOR_CHANGED = NO`
10. `ENTRY_BEHAVIOR_CHANGED = NO`
11. `PC_CANONICAL_TICK_MIGRATION = PASS`
12. `SILENT_DEFAULT_TICK_DECISION_PATH_REMOVED = YES`
13. `MISSING_TICK_AUTHORITY_FAIL_CLOSED = EXPLICIT_ITEM_SCOPED`
14. `PC_CANONICAL_EQUIVALENCE_PASS = PASS`
15. `SPECIAL_FINE_TICK_RESOLUTION_TEST = PASS`
16. `OTHER_ISSUES_LOW_PRICE_TICK_TEST = PASS`
17. `MISSING_TABLE_CLASS_TEST = INSUFFICIENT_EVIDENCE_PASS`
18. `TICK_RULE_TEMPORAL_VERSION_TEST = PASS`
19. `DD_CONTROL_SET_CANONICAL_TICK_REVALIDATION = PASS_WITH_RESOLVED_PIT_LISTED_METADATA`
20. `MINIMUM_TICK_AUTHORITY_HASH_CONSISTENCY = PASS`
21. `STALE_OR_CROSS_RUN_TICK_AUTHORITY_REJECTED = PASS`
22. `PC_LOW_PRICE_ALLOCATION_SEMANTICS_CHANGED = NO`
23. `DC_STRATEGY_PROMOTION_EXECUTED = NO`
24. `FOCUSED_REGRESSION_RESULT = PASS; 274 passed`
25. `HISTORICAL_PNL_USED = NO`
26. `HARD_MINIMUM_PRICE_RULE = NO`
27. `SYMBOL_BLACKLIST = NO`
28. `PRODUCTION_CHANGE_EXECUTED = YES_AUTHORITY_ONLY`
29. `TARGET_RUN_MUTATED = NO`
30. `LONG_RUNTIME_EXECUTION = NO`
31. `MINIMUM_TICK_AUTHORITY_PRODUCTION_ACCEPTED = YES`
32. `PHASE32_DG_READY = YES`
33. `NEXT_RECOMMENDED_STEP = Phase32-DG: promote the already-designed DC tick-normalized trend / momentum confidence contract into Technical Features / SI / Candidate / BQ / Entry using the accepted canonical tick authority`
34. `FINAL_JUDGMENT = PHASE32_DF_CANONICAL_PIT_MINIMUM_TICK_AUTHORITY_PRODUCTION_ACCEPTED_DG_READY`

## Final Judgment

`PHASE32_DF_CANONICAL_PIT_MINIMUM_TICK_AUTHORITY_PRODUCTION_ACCEPTED_DG_READY`

The system now has a canonical, PIT-bound, versioned minimum-tick authority that
is produced at the Technical Features / market-security boundary, propagated
through Strategy context, consumed by PC, and preserved by PS. Silent
decision-material `DEFAULT_MINIMUM_TICK = 1.0` fallback has been removed from
the PC tick-cap path.

Phase32-DG can now promote DC's tick-normalized opportunity-quality behavior
using this accepted authority.
