# Phase22-PT - PIT-covered Historical Strategy Source Foundation

## Judgment

Phase22-PT establishes a production-common Historical Strategy source coverage inventory and preflight, and proves a PIT-covered 1BD isolated Strategy shadow source probe.

Runtime switch: `NO`

Active Runtime consumer promotion: `NO`

Legacy Runtime retirement: `NO`

Codex 5BD execution: `NO`

## Implemented

- Added `ai_fund_lab_v2.strategy.historical_source_foundation`.
- Added machine-readable source coverage inventory for J-Quants trading calendar, daily quotes, listed information, sector source, corporate-event optional sources, Candidate output, Opportunity output, portfolio state, pending state, and Accepted Generation pointer.
- Added Historical Strategy source preflight with `requested_start_date`, `required_warmup_start`, `evaluation_end_date`, coverage checks, eligible/blocked dates, `first_eligible_start_date`, root blockers, and `operator_ready`.
- Embedded Strategy source preflight into `runtime_test.py plan` under `strategy_shadow.source_preflight`.
- Separated source PIT validity from Strategy producer BLOCK propagation in `source_manifest.json`.
- Established PIT sector fields: `sector_source_status`, `sector_pit_available`, `sector_effective_as_of`, `sector_coverage_start`, `sector_coverage_end`, `sector_fallback_used`.
- Preserved Corporate Event partial coverage semantics: partial optional event coverage remains `SOURCE_PARTIAL`, not `NO_EVENT_CONFIRMED`.

## Source Coverage

Current canonical `.runtime` inventory:

- Daily quotes: J-Quants normalized parquet, `2026-02-16` to `2026-07-14`, 426,689 rows, 4,375 symbols.
- Listed information / Sector source: J-Quants listed issues parquet, `2026-07-06` to `2026-07-15`, 22,193 rows, 4,444 symbols.
- Trading calendar: J-Quants calendar parquet, `2026-02-16` to `2026-07-15`.
- Candidate / Opportunity daily outputs: available for the tested 5BD window `2026-07-06` to `2026-07-10`.
- Corporate-event optional sources for corporate actions, earnings schedule, and financial statements are not present in the current canonical root; coverage is therefore `PARTIAL`.

`2022-09-15` remains not eligible for PIT-covered Strategy source generation because market/listed canonical coverage starts in 2026. The preflight does not silently shift that requested date.

## Concrete 5BD Start Date

The first operator-ready 5BD start date from the current source coverage inventory is:

```text
2026-07-06
```

The covered 5BD window is:

```text
2026-07-06, 2026-07-07, 2026-07-08, 2026-07-09, 2026-07-10
```

Codex did not execute the 5BD run. User-operated command:

```bash
PYTHONPATH=src python3 scripts/runtime_test.py fresh-run \
  --profile historical-smoke \
  --start-date 2026-07-06 \
  --business-days 5 \
  --initial-cash 1000000 \
  --confirm \
  --yes-i-understand-this-mutates-trading-state
```

## 1BD Isolated Probe

Codex executed a PIT-covered isolated 1BD Strategy shadow probe for `2026-07-06` under `/private/tmp`.

Probe results:

- `source_manifest.pit_validation.status`: `PASS`
- `source_manifest.pit_validation.pit_valid`: `true`
- `latest_fallback_used`: `false`
- `current_state_leakage_detected`: `false`
- `runtime_mutation_performed`: `false`
- `broker_write_performed`: `false`
- `strategy_fixed_position_cap_used`: `false`
- `strategy_fixed_jpy_exposure_cap_used`: `false`
- Strategy validation checks: `PASS`

The Strategy shadow judgment itself remains `BLOCK` with `shadow_consumer_eligibility=REVIEW_REQUIRED` because downstream Strategy artifact readiness and Corporate Event partial coverage are still review/block conditions. This is acceptable for PT source foundation and does not authorize active Runtime consumer use.

## Evidence

Machine-readable evidence:

```text
reports/phase22_pt_pit_covered_historical_strategy_source_foundation/
```

Required short checks:

```bash
PYTHONPATH=src PYTHONPYCACHEPREFIX=/private/tmp/pycache python3 -m pytest tests/strategy -q
PYTHONPATH=src PYTHONPYCACHEPREFIX=/private/tmp/pycache python3 -m pytest tests/runtime_v2/test_phase22_p_strategy_shadow_wiring.py tests/runtime_v2/test_phase22_m_strategy_summarize_scope.py tests/runtime_v2/test_phase19_ax_system_status.py -q
PYTHONPATH=src PYTHONPYCACHEPREFIX=/private/tmp/pycache python3 -m pytest tests/strategy/test_phase22_pr_dynamic_capacity_asset_proportionality.py -q
PYTHONPATH=src PYTHONPYCACHEPREFIX=/private/tmp/pycache python3 -m compileall -q src scripts tests
```

Results:

- `tests/strategy`: `130 passed`
- Runtime Strategy/System Status regression: `8 passed`
- Phase22-PR dynamic capacity regression: `5 passed`
- Compile: PASS

## Final Judgment

Primary Judgment: `PHASE22_PT_HISTORICAL_SOURCE_FOUNDATION_COMPLETE_WITH_REVIEW_CONDITIONS`

Source Coverage Inventory: `PASS`

Historical Date Eligibility: `PASS`

Canonical Source Materialization: `PASS`

Market Quote PIT Coverage: `PASS`

Listed Information PIT Coverage: `PASS`

Sector Historical PIT: `PASS`

Corporate Event Historical Coverage: `PARTIAL`

Candidate Historical Generation: `PASS`

Opportunity Historical Generation: `PASS`

Portfolio State Isolation: `PASS`

Preflight Operator Readiness: `PASS`

PIT-valid 1BD Probe: `PASS`

Latest Fallback: `NOT_USED`

Current State Leakage: `NOT_DETECTED`

Fixed Position Cap: `NOT_USED`

Fixed JPY Exposure Cap: `NOT_USED`

Asset-Proportional Capital Allocation: `PASS`

Runtime Mutation: `NONE`

Broker Write: `NONE`

Shadow Consumer Eligibility: `REVIEW_REQUIRED`

Active Runtime Consumer Eligibility: `NO`

Runtime Switch Performed: `NO`

Legacy Authority Active: `YES`

5BD Operator Validation Ready: `YES`

Concrete 5BD Start Date: `2026-07-06`

Blocking Gaps: `0`

Non-blocking Gaps: `2`

- Corporate Event optional source coverage is `PARTIAL`.
- Strategy shadow downstream artifacts remain non-production-consumable and can still produce Strategy `BLOCK`.

Phase22 Closure Recommendation: `REVIEW_REQUIRED`

Next Task: `Phase22-PU - User-operated 5BD Strategy Shadow Validation and Review Condition Closure`
