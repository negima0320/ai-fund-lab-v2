# Phase32-AG - REENTRY Safety False-Positive Structured Predicate Narrow Repair

## Executive Summary

Phase32-AG repaired the Phase32-AF mandatory false-positive defect in the narrow allowed boundary:

`src/ai_fund_lab_v2/strategy/portfolio_construction.py::_reentry_safety_status(...)`

The old predicate failed closed on generic substring matches across free text and positive support reason codes. The actual false-positive was:

`BROKER_PRODUCT_CATEGORY_SUPPORTED -> contains "broker" -> REENTRY_NOT_ELIGIBLE_SAFETY`

The new predicate fails closed only on explicit negative structured statuses, explicit negative boolean fields, or canonical blocking reason codes. Positive support evidence containing words like `broker`, `cash`, or `safety` no longer blocks REENTRY by noun presence alone. `liquidity_status=UNKNOWN` remains `REVIEW_REQUIRED`.

No cooldown, recovery, rank, BUY Quality, Cash, PC/MCC, Risk Pacing, sizing, model, or SELL logic was changed. No fresh Historical, resume, replay, or backtest was run.

## Inherited Defect

Inherited from Phase32-AF:

- `PHASE32_AF_STALE_SAFETY_STATE_DEFECT = YES`
- `PHASE32_AF_REENTRY_CONTRACT_OVER_SUPPRESSION = YES`
- `PHASE32_AF_PRODUCTION_REPAIR_JUSTIFIED = YES`
- `PHASE32_AF_IMPLEMENTATION_READY = YES`
- Primary positive control: `83060 / 2022-10-25`
- Secondary control: `83060 / 2022-10-26`

## Old Predicate

The old safety predicate was:

```python
text = " ".join([reason_text, " ".join(str(item) for item in row.get("reason_codes") or [])]).lower()
if any(token in text for token in ("safety", "broker", "cash", "buying_power", "corporate_action_blocking")):
    return "FAIL_CLOSED"
```

This treated `BROKER_PRODUCT_CATEGORY_SUPPORTED` as a safety failure solely because it contains `broker`.

## New Structured Predicate

The repaired predicate precedence is:

1. Explicit blocking status fields fail closed:
   `broker_eligibility_status`, `broker_product_category_status`, `product_category_status`, `buying_power_status`, `cash_buying_power_status`, `safety_status`, `safety_hard_cap_status`, `safety_hard_cap_preservation_status`, `execution_safety_status`, `corporate_action_blocking_status`, `corporate_event_blocking_status`.
2. Explicit negative boolean fields fail closed when false:
   `broker_eligible`, `broker_product_category_supported`, `tradable`, `safety_hard_cap_preserved`.
3. Canonical explicit blocking codes fail closed, including:
   `broker_product_category_unsupported`, `broker_product_unsupported`, `broker_security_unsupported`, `broker_unsupported`, `broker_blocked`, `listed_info_not_current`, `listed_info_code_mismatch`, `buying_power_blocked`, `insufficient_buying_power`, `buying_power_after_cash_buffer`, `safety_hard_cap_violation`, `minimum_lot_exceeds_safety_hard_cap`, `corporate_action_blocking`, `corporate_event_blocking`, `reentry_corporate_action_blocking`, `execution_safety_block`, `execution_safety_blocked`, `explicit_safety_prohibition`, `safety_block`, `safety_blocked`.
4. `liquidity_status == "UNKNOWN"` returns `REVIEW_REQUIRED`.
5. Otherwise return `PASS`.

Positive support codes are not matched by generic noun substring.

## Positive Controls

Focused tests now prove:

- `BROKER_PRODUCT_CATEGORY_SUPPORTED` does not safety-block.
- Positive Cash availability / optionality text does not safety-block.
- Safety-pass / safety-preserved support text does not safety-block.
- Normal liquidity / capacity remains PASS.

Primary 83060-shaped fixture:

```text
reason_codes includes BROKER_PRODUCT_CATEGORY_SUPPORTED
cooldown PASS
recovery PASS
candidate PASS
liquidity NORMAL
corporate_action NO_EVENT
renewed current evidence PASS
```

Expected and verified:

```text
_reentry_safety_status = PASS
reentry_semantic_state = REENTRY_ELIGIBLE
```

## Negative Controls

Focused tests preserve fail-closed behavior for:

- explicit broker eligibility failure
- `broker_product_category_unsupported`
- `buying_power_blocked`
- safety hard-cap violation
- `corporate_action_blocking`
- explicit safety prohibition
- `liquidity_status=UNKNOWN` as `REVIEW_REQUIRED`

## 83060 10/25 Proof

A non-mutating predicate proof was run against the captured actual-path 2022-10-25 PC row from:

`reports/runtime_tests/runs/runtime-test-historical-extended-smoke-20260827T071407047414Z/daily/2022-10-25/strategy/portfolio_construction.json`

Result after repaired predicate:

```text
2022-10-25 {'safety': 'PASS', 'state': 'REENTRY_ELIGIBLE', 'eligibility': 'PASS'}
```

This is a focused function proof against captured PIT fields, not a fresh Historical run.

## 10/26 Proof

The same non-mutating proof was run against the captured 2022-10-26 row:

```text
2022-10-26 {'safety': 'PASS', 'state': 'REENTRY_ELIGIBLE', 'eligibility': 'PASS'}
```

10/26 has additional caution evidence, but no legitimate current-evidence predicate blocks it in the captured row when the false broker Safety block is removed.

## Regression Coverage

Added tests in:

`tests/strategy/test_phase30_z_reentry_genuine_recovery.py`

Coverage:

- positive broker support code no longer Safety-blocks
- positive Cash / Safety support text no longer Safety-blocks
- explicit broker, buying-power, safety hard-cap, corporate-action, and execution/safety blocks still fail closed
- liquidity unknown remains review
- temporal -> cooldown -> recovery -> current candidate -> Safety precedence remains unchanged
- existing genuine recovered REENTRY tests remain preserved

## Architecture Update

Updated:

`docs/02_architecture/strategy_intelligence_architecture_v1.md`

Clarification added: REENTRY Safety gating must consume explicit negative / blocking evidence and must not infer Safety failure from generic nouns inside positive support reason codes such as broker eligibility support, Cash availability / optionality observations, or Safety-pass evidence.

## Registry Status

Registry refresh was not required. Search of `.runtime/artifact_registry` accepted manifests and evidence found no membership for:

`src/ai_fund_lab_v2/strategy/portfolio_construction.py`

Therefore no accepted artifact hash was refreshed and no manual registry edit was performed.

## Changed Files

- `src/ai_fund_lab_v2/strategy/portfolio_construction.py`
- `tests/strategy/test_phase30_z_reentry_genuine_recovery.py`
- `docs/02_architecture/strategy_intelligence_architecture_v1.md`
- `docs/phase_reports/phase32_ag_reentry_safety_false_positive_structured_predicate_narrow_repair.md`

## Verification

Commands run:

```text
PYTHONPATH=src PYTHONPYCACHEPREFIX=/private/tmp/phase32_ag_pycache python3 -m pytest tests/strategy/test_phase30_z_reentry_genuine_recovery.py tests/strategy/test_phase22_e_portfolio_construction.py::test_phase29_l16_semantic_reentry_cooldown_and_recovery_hurdle -q
```

Result:

```text
13 passed
```

```text
PYTHONPATH=src PYTHONPYCACHEPREFIX=/private/tmp/phase32_ag_pycache python3 -m pytest tests/strategy/test_phase22_e_portfolio_construction.py -k 'phase29_l16 or phase31_g26' -q
```

Result:

```text
9 passed, 113 deselected
```

```text
PYTHONPATH=src PYTHONPYCACHEPREFIX=/private/tmp/phase32_ag_pycache python3 -m pytest tests/strategy/test_phase22_e_portfolio_construction.py tests/strategy/test_phase30_z_reentry_genuine_recovery.py -q
```

Result:

```text
134 passed
```

```text
PYTHONPYCACHEPREFIX=/private/tmp/phase32_ag_pycache python3 -m py_compile src/ai_fund_lab_v2/strategy/portfolio_construction.py tests/strategy/test_phase30_z_reentry_genuine_recovery.py
```

Result:

```text
PASS
```

## Fresh Validation Recommendation

User-operated short fresh validation is ready. Primary acceptance row should be:

`83060 / 2022-10-25`

Expected semantic change:

```text
REENTRY_NOT_ELIGIBLE_SAFETY -> REENTRY_ELIGIBLE
```

No fill or profitability assertion is part of AG acceptance.

## Final Judgments

PHASE32_AG_FALSE_BROKER_SUBSTRING_DEFECT_REPAIRED = YES

PHASE32_AG_STRUCTURED_SAFETY_PREDICATE = YES

PHASE32_AG_POSITIVE_BROKER_SUPPORT_SAFE = YES

PHASE32_AG_EXPLICIT_BROKER_BLOCK_FAIL_CLOSED = YES

PHASE32_AG_BUYING_POWER_BLOCK_FAIL_CLOSED = YES

PHASE32_AG_SAFETY_HARD_CAP_FAIL_CLOSED = YES

PHASE32_AG_CORPORATE_ACTION_BLOCK_FAIL_CLOSED = YES

PHASE32_AG_LIQUIDITY_UNKNOWN_REVIEW = YES

PHASE32_AG_83060_10_25_SAFETY_PASS = YES

PHASE32_AG_83060_10_25_REENTRY_ELIGIBLE = YES

PHASE32_AG_83060_10_26_FALSE_BROKER_BLOCK_REMOVED = YES

PHASE32_AG_CHURN_GATE_CHANGED = NO

PHASE32_AG_RECOVERY_GATE_CHANGED = NO

PHASE32_AG_CURRENT_EVIDENCE_GATE_CHANGED = NO

PHASE32_AG_CASH_LOGIC_CHANGED = NO

PHASE32_AG_PC_MCC_CHANGED = NO

PHASE32_AG_RISK_PACING_CHANGED = NO

PHASE32_AG_REGRESSION_STATUS = PASS

PHASE32_AG_SHORT_FRESH_VALIDATION_READY = YES

PHASE32_AG_NEXT_STEP = User-operated short fresh validation on the post-AG code path, with 83060 / 2022-10-25 as the primary acceptance row and no profitability/fill requirement.
