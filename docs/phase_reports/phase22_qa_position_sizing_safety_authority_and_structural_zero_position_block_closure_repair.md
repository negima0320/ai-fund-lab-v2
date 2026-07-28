# Phase22-QA Position Sizing Safety Authority and Structural Zero-Position BLOCK Closure Repair

## Executive Summary

Primary Judgment:

```text
PHASE22_QA_STRUCTURAL_ZERO_POSITION_ROOT_CAUSE_REPAIRED_OPERATOR_VALIDATION_REQUIRED
```

Phase22-PZで確認された構造的ゼロポジションBLOCKの直接原因を修復した。Runtime Switch、Artifact lifecycle promotion、Consumer Eligibility promotion、新規5BD、Broker接続、Broker writeは実行していない。

Final status:

| Item | Judgment |
|---|---|
| Root Cause Identified | YES |
| Production Common Repair | YES |
| Structural Zero Direct Cause Repaired | YES |
| Operator 5BD Validation Required | YES |
| Phase22 Closure | NO |
| Phase23 Entry | NO |
| Runtime Switch Ready | NO |
| Strategy Production Ready | NO |

Evidence:

```text
reports/phase22_qa_position_sizing_safety_authority_and_structural_zero_position_block_closure_repair/
```

## Root Cause

Primary root cause:

```text
POSITION_SIZING_WIRING_DEFECT
```

Secondary:

```text
DESERIALIZATION_DEFAULT_ZERO
FAIL_CLOSED_ZERO_WITHOUT_REASON
```

The latest 5BD evidence already contained the correct Safety authority under:

```text
position_sizing.upstream_artifacts.safety_limit.summary.concentration.maximum_position_weight = 0.25
```

However, `Position Sizing` read only:

```text
safety_limit_summary.summary.maximum_position_weight
```

That top-level field was missing in the canonical Safety contract payload, so the implementation converted the missing value to `0.0`. The result was a false config-vs-safety violation:

```text
strategy_maximum_position_weight = 0.18
safety_maximum_position_weight = 0.0
configured_max_position_weight_above_safety_cap
```

This was not a real Safety policy of zero concentration. It was missing nested-field wiring plus default-zero normalization.

## Authority Trace

Formal Safety authority:

| Field | Value |
|---|---|
| Source | `configs/safety/portfolio_limits.json` |
| Pointer | `concentration.maximum_position_weight` |
| Value | `0.25` |
| Owner | `Safety Layer` |
| Scope | `production`, `demo`, `historical` |

Strategy configured maximum:

| Field | Value |
|---|---|
| Source | `configs/strategy/position_sizing.json` |
| Pointer | `strategy_maximum_position_weight` |
| Value | `0.18` |

Legacy active Runtime config remains separate:

| Source | Field | Value | Used as Strategy authority |
|---|---|---:|---|
| `configs/runtime_v2/capital_deployment.json` | `max_position_weight` | `0.20` | NO |

## Design Contract

The repaired contract separates three values:

```text
strategy configured maximum position weight
safety maximum allowed position weight
actual produced position weight
```

The effective cap is:

```text
effective_maximum_position_weight = min(strategy_maximum_position_weight, safety_maximum_position_weight)
```

Normal case:

```text
strategy_max = 0.18
safety_max = 0.25
effective_max = 0.18
```

Strategy config violation:

```text
strategy_max = 0.30
safety_max = 0.25
reason = configured_max_position_weight_above_safety_cap
```

Missing Safety authority:

```text
safety_max = null
reason = missing_safety_maximum_position_weight_authority
```

Explicit zero cap:

```text
safety_max = 0.0
requires explicit_zero_cap / emergency_brake_active / hard_risk_off_active
```

Produced overweight:

```text
reason = produced_position_weight_above_safety_cap
```

This reason is only valid when an actual generated `target_weight` exceeds the resolved Safety cap.

## Production Commonality

The fix is in:

```text
src/ai_fund_lab_v2/strategy/position_sizing.py
```

It is not a historical-only override, not a Runtime Test override, not date-specific, and not a cap bypass. The Safety comparison remains active. Runtime Switch, Broker path, artifact lifecycle, and consumer eligibility were not changed.

`src/ai_fund_lab_v2/strategy/shadow_runtime.py` was also updated only to add Strategy Evidence Index pointers for the new Position Sizing authority fields.

## Modified Files

- `src/ai_fund_lab_v2/strategy/position_sizing.py`
- `src/ai_fund_lab_v2/strategy/shadow_runtime.py`
- `tests/strategy/test_phase22_j_position_sizing.py`

## Position Sizing Derivation

Position Sizing now records:

- `strategy_maximum_position_weight`
- `strategy_maximum_position_weight_source`
- `safety_maximum_position_weight`
- `safety_maximum_position_weight_source`
- `safety_authority_status`
- `effective_maximum_position_weight`
- `effective_maximum_position_weight_derivation`
- `explicit_zero_cap`
- `emergency_brake_active`
- `market_context_risk_state`
- `dynamic_position_count`
- `dynamic_cash_exposure`
- `aggregate_exposure_cap`
- `safety_authority_resolution`

Strategy Evidence Index now maps these under:

```text
position_sizing_safety_authority
```

## Market Context / Dynamic Policy Alignment

Confirmed:

- Position Sizing uses the effective cap from Strategy and Safety authorities.
- Dynamic Position Count is recorded in the Position Sizing artifact.
- Dynamic Cash Exposure and aggregate exposure cap are recorded.
- Aggregate target weight remains bounded by target gross exposure.
- Share quantity, lot rounding, order price, Pending, Submit, Execution, and Broker authority remain downstream Runtime responsibilities.

Remaining review:

- Market Context does not currently mutate the Safety concentration cap.
- Existing 5BD artifacts still have Dynamic Position Count, Dynamic Cash Exposure, Portfolio Construction, Position Management, Capital Deployment, and price volatility in `REVIEW_REQUIRED`.

## Historical Accepted Generation Assessment

The PZ Accepted Generation issue remains separate:

```text
Historical dates = 2026-07-06 through 2026-07-10
Accepted Generation effective_from = 2026-07-20T00:00:00+09:00
```

The Safety cap repair does not use Accepted Generation and does not introduce future leakage. This issue remains `REVIEW_REQUIRED` for Runtime Switch / historical PIT Strategy validation and should be handled separately.

## Test Results

PASS:

| Command | Result |
|---|---|
| `env PYTHONPATH=src python3 -m pytest tests/strategy/test_phase22_j_position_sizing.py -q` | `13 passed` |
| `env PYTHONPATH=src python3 -m pytest tests/strategy -q` | `137 passed` |
| `env PYTHONPATH=src python3 -m pytest tests/runtime_v2/test_phase17_bq_run_feature_date_authority_boundary.py tests/runtime_v2/test_phase22_p_strategy_shadow_wiring.py tests/runtime_v2/test_phase19_ax_system_status.py tests/runtime_v2/test_phase22_m_strategy_summarize_scope.py tests/runtime_v2/test_phase22_pu_historical_submit_source_identity.py -q` | `21 passed` |
| `env PYTHONPATH=src python3 -m pytest tests/strategy/test_phase22_ps_source_manifest.py tests/strategy/test_phase22_pr_dynamic_capacity_asset_proportionality.py -q` | `11 passed` |
| `env PYTHONPYCACHEPREFIX=/private/tmp/phase22_qa_pycache python3 -m compileall scripts/runtime_test.py src/ai_fund_lab_v2/strategy src/ai_fund_lab_v2/runtime_v2/historical_support` | PASS |

No skip or xfail additions were made. No assert relaxation, fixture-only repair, historical-only override, Safety bypass, Runtime Switch change, or Broker path change was made.

## Existing 5BD Offline Reassessment

Existing run:

```text
runtime-test-historical-smoke-20260728T012308064153Z
```

Method:

Existing daily Position Sizing upstream artifacts were re-evaluated offline with the repaired code. No run evidence was overwritten.

Result for all five dates:

| Field | Value |
|---|---|
| safety_maximum_position_weight | `0.25` |
| effective_maximum_position_weight | `0.18` |
| configured_max_position_weight_above_safety_cap | absent |
| missing_safety_maximum_position_weight_authority | absent |
| producer_result_status | `REVIEW_REQUIRED` |

The existing run remains zero-target offline because upstream Strategy artifacts remain `REVIEW_REQUIRED` and were not regenerated. The false Position Sizing Safety cap BLOCK is removed.

## Remaining Blockers

- Operator 5BD validation after QA repair is not yet executed.
- Existing 5BD upstream Strategy artifacts remain `REVIEW_REQUIRED`.
- Corporate Event coverage remains `PARTIAL`.
- Historical Accepted Generation PIT authority remains unresolved for Runtime Switch readiness.
- Artifact lifecycle acceptance and consumer eligibility promotion remain unperformed.

## Operator Validation Requirements

Codex did not run a new 5BD. Operator validation command:

```bash
env PYTHONPATH=src python3 scripts/runtime_test.py fresh-run --profile historical-smoke --business-days 5 --start-date 2026-07-06 --initial-cash 1000000 --confirm --explicit-mutation-confirm --json
```

Then inspect:

```bash
env PYTHONPATH=src python3 scripts/runtime_test.py run-status --profile historical-smoke --json
env PYTHONPATH=src python3 scripts/runtime_test.py show --run-id <NEW_RUN_ID> --artifact run --json
```

Validation must confirm:

- no Runtime Switch
- no Broker write
- `safety_maximum_position_weight = 0.25`
- `effective_maximum_position_weight = 0.18`
- `configured_max_position_weight_above_safety_cap` absent unless Strategy config truly exceeds Safety cap
- `strategy_evidence_index.json` maps `position_sizing_safety_authority`

## Phase22 Closure Eligibility

Phase22 Closure:

```text
NO
```

QA repaired the direct structural-zero root cause, but Phase22 closure still requires operator validation and remaining Strategy artifact blockers to be reviewed.

## Runtime Switch Eligibility

Runtime Switch Ready:

```text
NO
```

No Runtime Switch gate was executed or approved.

## Recommended Next Task

Recommended:

```text
Phase22-QB - Operator 5BD Post-QA Shadow Validation Review
```

Scope:

- User/operator runs the 5BD validation command if they choose.
- Codex reviews only the resulting evidence.
- Confirm Position Sizing Safety Authority resolution in real Runtime Test evidence.
- Keep Runtime Switch disabled and Strategy artifacts non-production-consumable.
