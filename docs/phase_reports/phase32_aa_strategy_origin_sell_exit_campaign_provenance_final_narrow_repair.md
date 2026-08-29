# Phase32-AA Strategy-Origin SELL_EXIT Campaign Provenance Final Narrow Repair

## Executive Summary

Phase32-AA repaired the remaining strategy-origin `SELL_EXIT` campaign provenance break on the authoritative actual path:

```text
same-day PM EXIT
  -> strategy-origin SELL_EXIT Pending
  -> persistent order
  -> persistent execution
  -> strict-prior bridge
  -> non-GENERIC prior exit context
```

The first campaign drop boundary was the PM runtime adapter projection. The authoritative daily PM artifact carried the EXIT campaign, but the runtime PM projection omitted `position_campaign_id`. A second materialization gap left strategy-origin SELL pending top-level campaign blank even when source PM lineage had a campaign. A resolver robustness issue also made identical PM EXIT identity rows appear ambiguous when one row had the campaign and one legacy projection row was blank.

The repair is intentionally narrow:

- PM runtime adapter emits the explicit current-position `position_campaign_id` into PM EXIT payloads.
- SELL planning preserves PM campaign on Pending top-level fields, shallow `strategy_authority_lineage`, and `quantity_contract`.
- Strategy planning merges identical same-day PM EXIT identities with one blank legacy projection and one explicit authoritative campaign, while conflicting nonblank campaigns still fail closed.
- Persistent order, persistent execution, and strict-prior re-entry reason materialization are verified through a production-equivalent regression.

No REENTRY, Cash, PC/MCC, Risk Pacing, sizing, threshold, or model logic was changed.

## Inherited Evidence

Phase32-Z actual-path audit of:

```text
runtime-test-historical-extended-smoke-20260827T045032683611Z
```

showed symbol `83060` on `2022-10-04` had:

| Artifact | PM id | Campaign |
|---|---|---|
| Daily PM artifact | `pm-2022-10-04-83060-exit` | `pc-9147a5f91c842b2f-83060-0001` |
| Runtime PM projection | `pm-2022-10-04-83060-exit` | blank |
| Serialized Pending | `pm-2022-10-04-83060-exit` | blank |
| Persistent order | `pm-2022-10-04-83060-exit` | blank |
| Persistent execution | `pm-2022-10-04-83060-exit` | blank |
| Strict-prior PM close match | `0` | not matched |

Therefore Phase32-Y PM id provenance was present, but campaign provenance was not lossless enough for strict-prior PM reason matching.

## Root Cause

`src/ai_fund_lab_v2/runtime_v2/position_management/producer.py` materialized PM decision identity and reason but did not include the explicit current-position campaign in `_decision_payload()`. This made the runtime PM projection a legacy/blank-campaign alias of the same authoritative PM EXIT.

`src/ai_fund_lab_v2/runtime_v2/planning/sell_pipeline.py` then preserved source PM id and PM business date but did not set Pending top-level `position_campaign_id` in `_pending_item_with_sell_decision_lineage()`.

`src/ai_fund_lab_v2/runtime_v2/planning/strategy_authority.py` already looked for same-day PM EXIT evidence, but it treated identical PM ids with different campaign blankness as ambiguous because campaign was part of uniqueness. That blocked recovery from the authoritative daily PM artifact when paired with a blank runtime projection.

## Repair

### PM Runtime Adapter

`_decision_payload()` now materializes `position_campaign_id` from the explicit same-symbol current position. Missing or conflicting current-position campaign evidence returns blank rather than inferring from date, quantity, symbol history, or later ledger state.

### SELL Planning

`_pending_item_with_sell_decision_lineage()` now propagates PM EXIT campaign into:

- Pending item top-level `position_campaign_id`
- shallow `strategy_authority_lineage.position_campaign_id`
- `quantity_contract.position_campaign_id`

### Strategy-Origin SELL_EXIT Resolver

Same-day PM EXIT resolution now treats source decision id, decision type, and business date as the unique PM identity. Blank legacy projection campaign can be completed by a single explicit authoritative PM campaign. Multiple conflicting nonblank campaigns remain unresolved, so the path fails closed.

## Architecture Contract

Updated:

```text
docs/02_architecture/runtime_architecture_v2.md
```

The contract now states that strategy-origin `SELL_EXIT` must preserve the same-day PM EXIT campaign through Pending, lineage, quantity contract, persistent order, and persistent execution for strict-prior re-entry reconstruction. It also states that missing, conflicting, wrong-date, wrong-symbol, future-date, or ambiguous campaign evidence must fail closed and must not be inferred.

## Regression Evidence

Focused verification:

```text
7 passed in 44.49s
```

Covered tests:

- PM runtime adapter payload materializes explicit current campaign.
- Multiple strategy-origin SELL_EXIT symbols materialize PM provenance.
- Strategy-origin SELL_EXIT materializes PM provenance to ledger and strict-prior bridge.
- Phase32-AA actual failing shape: authoritative daily PM campaign present, runtime PM projection blank, nested `runtime-current-*` alias preserved, Pending initially lacks campaign, then Pending/order/execution carry the PM campaign and strict-prior PM reason match becomes non-GENERIC.
- Fail-closed controls for missing PM, wrong symbol, wrong date, future date, ambiguous PM EXIT, and campaign mismatch.
- Partial REDUCE and legacy pending shapes remain safe.
- Phase32-T actual sell path persistent ledger PM/campaign provenance remains preserved.

Compile and whitespace checks:

```text
py_compile: PASS
git diff --check: PASS
```

## Registry Refresh

Because `producer.py` is the accepted `POSITION_MANAGEMENT_POLICY_SET:RUNTIME_ADAPTER`, Phase32-AA used the existing formal PM adapter acceptance writer workflow based on:

```text
scripts/phase17_b1i_b_pm_adapter_authority_resolution.py
```

AA evidence id:

```text
control_position_management_accepted_current_path_phase32_aa
```

Registry identity:

| Field | Before | After |
|---|---:|---:|
| PM set | `control.position_management.accepted_set@sha256-c3849b55a8a4f9f4` | `control.position_management.accepted_set@sha256-987be698d39a6887` |
| Accepted runtime adapter hash | `96b55567877f26f12444439261c00c2afa5105d97512be2c2306283e474a14a2` | `ae3aaae66273d5ed149ef4064659f5ec9f88d4ef05c0770ec6f759311b95e5cc` |
| Actual `producer.py` hash | `ae3aaae66273d5ed149ef4064659f5ec9f88d4ef05c0770ec6f759311b95e5cc` | `ae3aaae66273d5ed149ef4064659f5ec9f88d4ef05c0770ec6f759311b95e5cc` |

Only this member changed:

```text
control.position_management.accepted_set.runtime_adapter
```

All other PM accepted-set member hashes were unchanged.

Post-refresh authority guard:

```text
accepted_path = src/ai_fund_lab_v2/runtime_v2/position_management/producer.py
accepted_hash = ae3aaae66273d5ed149ef4064659f5ec9f88d4ef05c0770ec6f759311b95e5cc
executing_source_hash = ae3aaae66273d5ed149ef4064659f5ec9f88d4ef05c0770ec6f759311b95e5cc
artifact_instance_id = control.position_management.accepted_set@sha256-987be698d39a6887
authority_mode = ACCEPTED_CURRENT_PATH
```

## State and Scope

No fresh run, resume, replay, backtest, long Historical run, threshold change, model change, runtime-state repair, or strategy-logic change was executed.

The formal registry writer recorded protected runtime state hashes as unchanged for Current, Pending, and Ledger during acceptance refresh.

## Final Judgments

PHASE32_AA_FIRST_CAMPAIGN_DROP_BOUNDARY = PM runtime adapter `_decision_payload()` omitted explicit current-position `position_campaign_id`; secondary materialization gap was Pending top-level campaign propagation.

PHASE32_AA_CAMPAIGN_PROVENANCE_DEFECT_REPAIRED = YES

PHASE32_AA_PENDING_CAMPAIGN_POPULATED = YES

PHASE32_AA_ORDER_CAMPAIGN_POPULATED = YES

PHASE32_AA_EXECUTION_CAMPAIGN_POPULATED = YES

PHASE32_AA_STRICT_PM_MATCH = PASS

PHASE32_AA_NON_GENERIC_PRIOR_CONTEXT = PASS

PHASE32_AA_CAMPAIGN_MISMATCH_FAIL_CLOSED = YES

PHASE32_AA_PARTIAL_REDUCE_SAFE = YES

PHASE32_AA_REENTRY_LOGIC_CHANGED = NO

PHASE32_AA_CASH_LOGIC_CHANGED = NO

PHASE32_AA_PC_MCC_CHANGED = NO

PHASE32_AA_RISK_PACING_CHANGED = NO

PHASE32_AA_REGRESSION_STATUS = PASS

PHASE32_AA_SHORT_FRESH_VALIDATION_READY = YES

PHASE32_AA_NEXT_STEP = User-operated short fresh Historical validation from the refreshed PM adapter accepted registry state; do not resume prior halted or pre-AA runs as acceptance evidence.
