# Phase32-EH - PC Security Opportunity SHADOW Consumer / Production Preservation Audit

## Scope

EH added a SHADOW-only PC diagnostic consumer for:

`security_opportunity_evidence.v1`

The current Production system remains the control. EH did not connect the
consumer to Production allocation, ordering, sizing, Runtime Planning, target
weights, quantities, Candidate ranking, PM, SELL/REDUCE, BQ/Entry, REENTRY, Risk
Pacing, Cash, caps, or lot rules.

EH did not execute fresh-run, resume, recover, replay, source transition, or
long Historical. The source run was not written to. Analysis output was written
only under `reports/runtime_tests/analysis/...`.

Target/source run:

- `runtime-test-historical-extended-smoke-20260902T060955933565Z`

Window:

- `2022-10-03` through `2023-10-26`

Primary output:

- `reports/runtime_tests/analysis/phase32_eh_pc_security_opportunity_shadow_20260903T014000`

## Implementation

Changed / added for EH:

- `src/ai_fund_lab_v2/strategy/marginal_capital_value.py`
  - added `pc_security_opportunity_shadow_consumer.v1`
  - added PC-owned diagnostic row alignment between
    `security_opportunity_evidence.v1` and existing unified marginal-capital
    SHADOW rows
  - kept `authoritative_consumer_count = 0`
- `scripts/runtime_test.py`
  - added `shadow-backfill-pc-security-opportunity`
  - writes isolated daily/manifest/summary artifacts under analysis output only
- `tests/strategy/test_phase32_eh_pc_security_opportunity_shadow_consumer.py`
- `tests/runtime_v2/test_phase32_eh_pc_security_opportunity_backfill.py`
- this report

The consumer is diagnostic only:

- Production allocation consumer: `false`
- Production ordering consumer: `false`
- Production sizing consumer: `false`
- Runtime consumer: `false`
- authoritative consumer count: `0`
- membership authority: `false`
- target-weight authority: `false`
- quantity authority: `false`

## Backfill Result

Command executed:

```bash
PYTHONPATH=src:. PYTHONPYCACHEPREFIX=/private/tmp/pycache-phase32-eh python3 scripts/runtime_test.py shadow-backfill-pc-security-opportunity --source-run-id runtime-test-historical-extended-smoke-20260902T060955933565Z --start-date 2022-10-03 --end-date 2023-10-26 --output-root reports/runtime_tests/analysis/phase32_eh_pc_security_opportunity_shadow_20260903T014000 --confirm --json
```

Result:

- status: `PASS`
- business days: `264`
- diagnostic rows: `7831`
- `production_change_executed = false`
- `target_run_mutated = false`
- `runtime_state_mutated = false`
- `future_information_used = false`
- `historical_outcome_used = false`

Manifest:

- source commit: `1f64f49ee9a8dd48280007e4df656e5f03e231ca`
- `marginal_capital_value.py` sha256:
  `87c584b59b2ded76b43cf4522080458ae812fff1448cf3cee6faa03561980608`
- `portfolio_construction.py` sha256:
  `37a9cb6d93ce70260312138d7c5bd345a5c0e7c4ec11b23353798db0c522f5d7`
- `source_run_artifact_mutated = false`
- `runtime_state_mutated = false`

## Production Preservation

`PRODUCTION_PC_PATH_UNCHANGED = PASS`

EH does not replace existing PC inputs. It reads existing source-run PC
artifacts, reconstructs EG Security Opportunity evidence, and joins it to the
existing DQ/EE marginal-capital SHADOW rows. No PC target, membership,
competitor, accepted weight, PS quantity, Pending item, or Runtime plan is
modified.

Production preservation count:

- `PRODUCTION_PRESERVED = 264 / 264`

## NEW Preservation Gate

`BUY_NEW_PRODUCTION_EQUIVALENCE = PASS`

Backfill summary:

- `buy_new_equivalence_counts = {"PASS": 264}`

The diagnostic consumer preserves:

- Candidate/rank consistency
- runtime opportunity score consistency
- BQ/Entry consistency
- PC membership consistency
- target-weight consistency
- BUY_NEW action consistency
- PS quantity consistency where materialized

No unexplained material NEW divergence was observed.

## REENTRY Preservation

`REENTRY_PRODUCTION_EQUIVALENCE = PASS`

Backfill summary:

- `reentry_equivalence_counts = {"PASS": 264}`

The consumer does not erase prior-EXIT semantics and does not introduce a
blanket REENTRY penalty. REENTRY provenance remains action/lifecycle evidence,
not intrinsic Security Opportunity evidence.

## ADD UNKNOWN Diagnostic

EG established:

- EE ADD `incremental_value = UNKNOWN`: `116 / 116`
- Security Opportunity evidence for those rows: `COMPLETE = 116 / 116`

EH PC diagnostic reclassification:

| Class | Count |
| --- | ---: |
| `BLOCKED` | 54 |
| `COMPARABLE_NEGATIVE` | 62 |
| `COMPARABLE_POSITIVE` | 0 |
| `COMPARABLE_NEUTRAL` | 0 |
| `INSUFFICIENT` | 0 |

`ADD_UNKNOWN_116_PC_SHADOW_RECLASSIFICATION = BLOCKED_54_COMPARABLE_NEGATIVE_62`

Interpretation:

Complete Security Opportunity evidence materially improves observability: the
116 rows no longer look like an opaque absence of security evidence. However,
once PC combines that evidence with position relationship, PM/BQ/Entry, current
weight, headroom/concentration, ADD-specific evidence, risk, and next executable
lot evidence, the current audited set remains blocked or negative. EH therefore
does not justify new ADD demand.

## Weak ADD Controls

`WEAK_ADD_NEGATIVE_CONTROLS_PRESERVED = PASS`

All `116` ADD-UNKNOWN rows remained either:

- `BLOCKED`, or
- `COMPARABLE_NEGATIVE`

No ADD row was rescued solely because Security Opportunity evidence existed.
This preserves the legitimate negative/risky incumbent controls.

## Winner Controls

Mandatory controls:

| Symbol | Diagnostic rows | ADD UNKNOWN rows | EH reclassification | Observability |
| --- | ---: | ---: | --- | --- |
| `43880` | 30 | 12 | `BLOCKED=3`, `COMPARABLE_NEGATIVE=9` | improved |
| `54010` | 99 | 5 | `BLOCKED=1`, `COMPARABLE_NEGATIVE=4` | improved |
| `83060` | 103 | 13 | `BLOCKED=6`, `COMPARABLE_NEGATIVE=7` | improved |
| `94320` | 82 | 33 | `BLOCKED=19`, `COMPARABLE_NEGATIVE=14` | improved |
| `94340` | 147 | 16 | `BLOCKED=6`, `COMPARABLE_NEGATIVE=10` | improved |
| `99840` | 104 | 15 | `BLOCKED=9`, `COMPARABLE_NEGATIVE=6` | improved |

The improvement is diagnostic observability, not capital allocation. EH makes
the reason for non-ADD clearer without changing whether these rows receive
funding.

Unique affected campaigns:

- `15`

Repeated comparable ADD campaigns:

- `11`

Top affected campaigns:

- `94320|pc-7c5bd9294d48b016-94320-0001`: `9`
- `43880|pc-77b04ae8a6085bfd-43880-0001`: `9`
- `94340|pc-8d0b3d71adb1e835-94340-0001`: `8`
- `45940|pc-d849118022b497c9-45940-0001`: `7`
- `94320|pc-401763653bc4df1d-94320-0001`: `5`
- `99840|pc-5a5765b1c257b5b8-99840-0001`: `5`
- `83060|pc-090162015342d58a-83060-0001`: `5`

## June-September 2023

EG proved Security Opportunity evidence was `COMPLETE` for all 20 ADD rows in
June through September 2023.

EH PC SHADOW ADD profile for the same period:

| Class | Count |
| --- | ---: |
| `BLOCKED` | 14 |
| `COMPARABLE_NEGATIVE` | 4 |
| `INSUFFICIENT` | 2 |

`2023_JUN_SEP_PC_SHADOW_ADD_PROFILE = BLOCKED_14_COMPARABLE_NEGATIVE_4_INSUFFICIENT_2`

Interpretation: shared Security Opportunity evidence is visible during the
period, but PC-level ADD marginal-capital evidence still does not support a
positive ADD classification.

## Neutral Capital Comparison

`ACTION_NEUTRAL_PC_SHADOW_COMPARISON = PASS`

EH preserves the neutral comparison boundary:

- no fixed action bonus
- no fixed ADD rescue
- NEW / REENTRY / ADD / Cash remain distinct competitors
- Cash remains preserved through the upstream unified marginal-capital SHADOW
- incomplete or blocked ADD rows cannot become funded merely by representation

## Failure Isolation

`EH_SHADOW_FAILURE_ISOLATION = PASS`

Focused failure-injection coverage confirms that a missing Security Opportunity
record is diagnostic only and cannot block Production PC generation. The
consumer emits `MISSING` diagnostic evidence while retaining:

- `production_pc_path_unchanged = true`
- `consumer_failure_blocks_production = false`
- `authoritative_consumer_count = 0`

## Validation

EH / EG focused tests:

```bash
PYTHONPATH=src:. PYTHONPYCACHEPREFIX=/private/tmp/pycache-phase32-eh python3 -m pytest -q tests/strategy/test_phase32_eh_pc_security_opportunity_shadow_consumer.py tests/runtime_v2/test_phase32_eh_pc_security_opportunity_backfill.py tests/strategy/test_phase32_eg_security_opportunity_evidence.py tests/runtime_v2/test_phase32_eg_security_opportunity_backfill.py
```

Result:

- `9 passed`

Full focused adjacent regression:

```bash
PYTHONPATH=src:. PYTHONPYCACHEPREFIX=/private/tmp/pycache-phase32-eh python3 -m pytest -q tests/strategy/test_phase32_eh_pc_security_opportunity_shadow_consumer.py tests/runtime_v2/test_phase32_eh_pc_security_opportunity_backfill.py tests/strategy/test_phase32_eg_security_opportunity_evidence.py tests/runtime_v2/test_phase32_eg_security_opportunity_backfill.py tests/strategy/test_phase32_dq_unified_marginal_capital_shadow.py tests/runtime_v2/test_phase32_dt_shadow_backfill_marginal_capital.py tests/strategy/test_phase31_g115_add_marginal_authoritative_binding.py tests/strategy/test_phase31_g119_pc_final_authority_ps_consistency.py tests/strategy/test_phase31_g44_add_reentry_lot_binding_integration.py tests/strategy/test_phase31_g63_runtime_executable_binding.py tests/strategy/test_phase31_g43_risk_pacing_economic_binding.py tests/runtime_v2/test_phase30_ak9r27_pending_review_scope_authority.py tests/runtime_v2/test_phase31_f1w_item_scoped_partial_submit.py
```

Result:

- `79 passed`

Compile check:

```bash
PYTHONPATH=src:. PYTHONPYCACHEPREFIX=/private/tmp/pycache-phase32-eh python3 -m py_compile scripts/runtime_test.py src/ai_fund_lab_v2/strategy/marginal_capital_value.py
```

Result:

- `PASS`

## Required Final Answers

- `PC_SECURITY_OPPORTUNITY_SHADOW_CONSUMER = PASS`
- `PRODUCTION_PC_PATH_UNCHANGED = PASS`
- `BUY_NEW_PRODUCTION_EQUIVALENCE = PASS`
- `REENTRY_PRODUCTION_EQUIVALENCE = PASS`
- `ADD_UNKNOWN_116_PC_SHADOW_RECLASSIFICATION = BLOCKED_54_COMPARABLE_NEGATIVE_62`
- `WEAK_ADD_NEGATIVE_CONTROLS_PRESERVED = PASS`
- `2023_JUN_SEP_PC_SHADOW_ADD_PROFILE = BLOCKED_14_COMPARABLE_NEGATIVE_4_INSUFFICIENT_2`
- `ACTION_NEUTRAL_PC_SHADOW_COMPARISON = PASS`
- `EH_ONE_YEAR_SHADOW_BACKFILL = PASS`
- `EH_SHADOW_FAILURE_ISOLATION = PASS`
- `PRODUCTION_CHANGE_EXECUTED = NO`
- `PRODUCTION_PROMOTION_EXECUTED = NO`
- `TARGET_RUN_MUTATED = NO`
- `RUNTIME_STATE_MUTATED = NO`
- `LONG_RUNTIME_EXECUTED = NO`
- `FUTURE_OUTCOME_USED = NO`
- `HISTORICAL_PNL_USED_FOR_TUNING = NO`
- `NEXT_RECOMMENDED_STEP = READ_ONLY_REVIEW_EH_DIVERGENCE_ROWS_BEFORE_ANY_FURTHER_SHADOW_CONSUMER_PROMOTION`
- `FINAL_JUDGMENT = PHASE32_EH_PC_SECURITY_OPPORTUNITY_SHADOW_CONSUMER_ACCEPTED_PRODUCTION_PRESERVED_ADD_OBSERVABILITY_IMPROVED_NO_PROMOTION`

## Final Judgment

`PHASE32_EH_PC_SECURITY_OPPORTUNITY_SHADOW_CONSUMER_ACCEPTED_PRODUCTION_PRESERVED_ADD_OBSERVABILITY_IMPROVED_NO_PROMOTION`

EH confirms that a PC-owned diagnostic consumer can read shared Security
Opportunity evidence while preserving current Production behavior. NEW and
REENTRY equivalence pass. ADD observability improves materially, but the
audited ADD UNKNOWN set remains blocked or comparable-negative after PC
position/action constraints are applied. This supports further analysis, not
Production promotion.
