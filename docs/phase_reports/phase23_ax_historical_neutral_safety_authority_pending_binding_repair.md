# Phase23-AX Historical Neutral Safety Authority Pending Binding Repair

## Primary Judgment

```text
PHASE23_AX_HISTORICAL_NEUTRAL_SAFETY_PENDING_BINDING_SHORT_VALIDATION_PASS
```

## Design Decision

採用Contract:

```text
Option A — Canonical NEUTRAL
```

Historical neutral safety authorityでは、`NEUTRAL`を正準Safety Decisionとする。

```text
NEUTRAL = no external safety event exists / historical replay is permitted / Safety Authority is resolved
```

`ALLOW`形のhistorical pending safety contextは既存互換として受理するが、新規materializationは`NEUTRAL`を出す。

## Root Cause

Phase23-AWで確認された不整合は以下。

```text
Morning Data Readiness: safety_decision = NEUTRAL
Morning pending producer: ALLOW onlyでsafety_context付与
active pending: safety_context = null
Sell Planning Data Readiness: historical_pending_safety_authority_mismatch
```

ProducerとconsumerでHistorical neutral Safety Authorityの意味が一致していなかった。

## Repair Summary

Runtime Pending Safety Authorityの共通helperを追加した。

```text
src/ai_fund_lab_v2/runtime_v2/pending/safety_authority.py
```

修正内容:

- Historical neutral Safety Authorityの正準decisionを`NEUTRAL`として定義。
- `ALLOW`はlegacy compatible decisionとして明示受理。
- pending producerが`NEUTRAL`/`ALLOW`どちらでも、有効なHistorical neutral authorityなら`pending.safety_context`をmaterialize。
- active approved pendingでは、`safety_context.safety_decision_id`を必須化。
- Data Readiness consumerが同じcanonical representationを受理。
- missing / mismatchは引き続きfail-closed。
- Production / Demoのmissing safetyは従来通りREVIEW_REQUIRED。

## Required Metadata

active pendingでは以下をmaterializeする。

```text
safety_context
safety_decision
safety_decision_id
safety_policy_version
safety_authority
safety_source
safety_business_date
temporal_authority_business_date
runtime_test_run_id
runtime_test_profile_id
runtime_test_evidence_root
```

Historical neutral decision idは以下の決定的ID。

```text
historical-neutral-safety:<business_date>
```

## Producer / Consumer Boundary

```text
Morning Data Readiness Safety Authority
↓
Morning Strategy Planning Authority pending producer
↓
pending_order_plan current slot
↓
Sell Planning Data Readiness consumer
```

Canonical owner:

```text
Runtime Pending Safety Authority
```

## Isolated AW Reproduction

AW対象Runのactive pending payloadを一時領域へコピーし、既存Runは変更せず、AX contractに従ってSafety Authority metadataだけをmaterializeした。

結果:

```text
active pending count = 9
pending safety_context missing count = 0
historical_pending_safety_authority_mismatch = 0
historical_safety_temporal_authority_missing = false
pending_safety_evidence_missing = false
Sell Planning Data Readiness = READY
```

## Previous Blockers

再発なし。

```text
target_weight_authority_unresolved
invalid_quality_score
review_required_quantity_authority
REVIEW_REQUIRED_MISSING_PRICE
strategy_plan_quantity_unresolved
historical_trading_calendar_authority_missing
current_valuation_previous_trading_date_missing
```

AW blockers resolved in isolated reproduction:

```text
historical_pending_safety_authority_mismatch
historical_safety_temporal_authority_missing
pending_safety_evidence_missing
```

## Validation

Compile:

```text
py_compile targeted runtime pending/safety/data_readiness modules: PASS
```

Targeted regression:

```text
22 passed
```

Expanded Runtime/Data Readiness regression:

```text
53 passed, 60 warnings
```

Reference Price / Position Sizing / Strategy Planning regression:

```text
49 passed
```

Warnings are existing pandas/pyarrow related warnings from fixture execution, not AX contract failures.

## Existing Run Preservation

以下の既存Runは変更していない。

```text
runtime-test-historical-smoke-20260730T030213466506Z
runtime-test-historical-smoke-20260730T014900699579Z
runtime-test-historical-smoke-20260730T012530808938Z
```

Hash preservation evidenceを作成済み。

## Deliverables

Human:

```text
docs/phase_reports/phase23_ax_historical_neutral_safety_authority_pending_binding_repair.md
```

Machine:

```text
reports/phase_reports/phase23_ax_historical_neutral_safety_authority_pending_binding_repair.json
```

Evidence:

```text
reports/phase23_ax_historical_neutral_safety_authority_pending_binding_repair/
```

## Gate

```text
READY_FOR_1BD_RUNTIME_RERUN = YES
```

Runtime rerunは実施していない。Operator実施待ち。
