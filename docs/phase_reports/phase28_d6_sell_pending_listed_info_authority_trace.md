# Phase28-D6: SELL Pending listed_info Authority Trace Audit

Task ID: `Phase28-D6`

Task Type: `READ_ONLY DIAGNOSIS`

Status: `COMPLETE`

Implementation Changed: `false`

Resume Executed: `false`

Fresh Run Executed: `false`

Long Historical Executed: `false`

## Executive Summary

For `2023-04-10 / 43880 / SELL_EXIT`, `listed_info` did not disappear at
Submit. It was already `null` on the existing strategy pending item before
Sell Planning reconciliation.

The trace has two relevant producers/consumers:

1. Strategy pending producer:

```text
src/ai_fund_lab_v2/runtime_v2/planning/strategy_authority.py:473-488
src/ai_fund_lab_v2/runtime_v2/planning/strategy_authority.py:903-922
```

This producer creates `PendingOrderItem.listed_info` only from
`opportunity_authority`. For `43880`, the Runtime Planning plan had no
opportunity authority, so `_listed_info_from_opportunity_authority(...)`
returned `None`.

2. Sell Planning PM order producer:

```text
src/ai_fund_lab_v2/runtime_v2/planning/sell_pipeline.py:1073-1090
```

This producer did generate basic `listed_info` for the new PM EXIT item:

```text
pending_item_id: opi-sell-exit-pm-43880-001
listed_info: {code: 43880, market: 東証, product_category: 011, security_type: 011, current_listed: true}
```

However, Pending Composition/Reconciliation classified the new PM EXIT item as
a compatible update and preserved the existing strategy item:

```text
resolution_action: PRESERVE_EXISTING
existing_pending_item_id: strategy-d3ca3c09c7e90609497b
new_pending_item_id: opi-sell-exit-pm-43880-001
reason_code: PENDING_SELL_COMPATIBLE_UPDATE_MERGED
```

Therefore the `listed_info` that Sell Planning generated was not copied into
the preserved pending item. Submit consumed the preserved strategy item with
`listed_info: null`.

## Target

```text
run_id: runtime-test-historical-smoke-20260805T231619492537Z
business_date: 2023-04-10
symbol: 43880
side: SELL
intent: SELL_EXIT
pending_item_id: strategy-d3ca3c09c7e90609497b
decision/planning id: rp-2023-04-10-43880-sell_exit-721a37484a2e69ca
```

## Stage Trace

| Stage | 43880 listed_info | Evidence |
| --- | --- | --- |
| Morning | Not directly materialized in morning evidence | `morning/pending_generation_evidence.json` records pending written; no `listed_info` paths exist in morning evidence files. |
| Position Management | Not present | `position_management/pm_decisions.json` has no `listed_info` field for `43880`. |
| Portfolio Construction | Not present | `strategy/portfolio_construction.json` has no `listed_info`; `43880` also lacks opportunity / buy-quality keys. |
| Position Sizing | Not present | `strategy/position_sizing.json` has no `listed_info`; `43880` has empty opportunity and quality authority. |
| Runtime Planning | Not present as a field | `strategy/runtime_planning.json` plan `rp-2023-04-10-43880-sell_exit-721a37484a2e69ca` has `opportunity_artifact_path=""`, `opportunity_row_id=""`, `quality_decision_id=""`, `quality_status=REVIEW_REQUIRED`. |
| Strategy Pending Generation | First `null` | `strategy_authority._pending_item_from_strategy_plan(...)` calls `_listed_info_from_opportunity_authority(...)`; because opportunity authority is absent, the strategy pending item gets `listed_info=None`. |
| Sell Planning new PM order | Present | `.runtime/runtime_state/sell_pipeline/2023-04-10/order_plan.json` item `opi-sell-exit-pm-43880-001` has basic listed info. |
| Pending Composition | Preserved null item | `.runtime/runtime_state/sell_pipeline/2023-04-10/pending_sell_reconciliation_evidence.json` preserved `strategy-d3ca3c09c7e90609497b` and did not replace/copy from `opi-sell-exit-pm-43880-001`. |
| Pending Plan | Null | `.runtime/pending_order_plan/pending_order_plan.json` has `43880 listed_info=null`. |
| Approval | Null item approved by id | pending plan approved item ids include `strategy-d3ca3c09c7e90609497b`; approval does not materialize a replacement item payload. |
| Submit | Null | submit run manifest pending payload has `43880 listed_info=null`, leading to D5 `listed_info_missing`. |

## Comparison With PASS Symbols

Same-day strategy pending payload before reconciliation:

```text
43880 SELL SELL_EXIT listed_info_present=false
77760 BUY  BUY_NEW   listed_info_present=true
83060 SELL SELL_EXIT listed_info_present=true
94320 SELL SELL_EXIT listed_info_present=true
94340 BUY  BUY_NEW   listed_info_present=true
```

Runtime Planning comparison:

```text
43880 SELL_EXIT opportunity_present=false quality_status=REVIEW_REQUIRED
83060 SELL_EXIT opportunity_present=true  quality_status=PASS
94320 SELL_EXIT opportunity_present=true  quality_status=PASS
```

Submit comparison:

```text
43880 pending_item_id=strategy-d3ca3c09c7e90609497b listed_info=false
83060 pending_item_id=strategy-1bbb68491ed211227dfa listed_info=true
94320 pending_item_id=strategy-f1e2a3406c332000b498 listed_info=true
```

`83060` and `94320` have `listed_info` sourced from:

```text
.runtime/runtime_state/buy_ai/2023-04-10/opportunity_rankings.json
```

They also have populated quality decision ids:

```text
83060: bq-453e727fa17ab590ae224654
94320: bq-c792569c713b8fd6de4ed2a1
```

`43880` differs because it was not present in same-day opportunity ranking
authority and had no buy-quality authority:

```text
opportunity_artifact_path: ""
opportunity_row_id: ""
quality_decision_id: ""
quality_status: REVIEW_REQUIRED
```

## Code Evidence

Strategy pending item generation:

```text
strategy_authority.py:473-488
```

sets:

```text
listed_info=_listed_info_from_opportunity_authority(...)
```

`_listed_info_from_opportunity_authority(...)` returns `None` when:

```text
opportunity_authority is empty
artifact_path / artifact_hash / row_id is missing
```

Code location:

```text
strategy_authority.py:903-922
```

Sell Planning PM order generation always creates basic listed info:

```text
sell_pipeline.py:1073-1090
```

Pending Composition preserving existing item:

```text
pending/composition.py:276-316
```

When action is `PRESERVE_EXISTING`, the existing item is retained:

```text
resolved_by_id[existing_item.pending_item_id] = existing_item
```

The D6 artifact shows that exact action for `43880`:

```text
SAME_SYMBOL_COMPATIBLE_UPDATE
PRESERVE_EXISTING
PENDING_SELL_COMPATIBLE_UPDATE_MERGED
```

## Scope Assessment

43880-only: observed on this date, yes. Mechanistically, no. Any executable
strategy pending item without opportunity authority can get `listed_info=null`.

SELL_EXIT-only: observed halt is `SELL_EXIT`. Mechanistically, the initial
strategy pending producer is side/intent agnostic: it depends on opportunity
authority, not on SELL_EXIT specifically. However, the damaging D6 path requires
a later SELL reconciliation that preserves an existing null SELL item over a
new PM SELL item with valid listed info. That path is SELL-specific.

BUY / BUY_ADD: same-day BUY_NEW items had opportunity authority and valid
`listed_info`. A BUY/BUY_ADD plan without opportunity authority would also get
`listed_info=None` from the strategy pending producer, but this was not observed
in the target day evidence.

SELL_REDUCE: not observed in the target case. It shares the SELL reconciliation
risk class if a compatible existing SELL pending item is preserved over a newer
SELL item that carries better authority fields.

## Defect Classification

Producer defect: partial.

The strategy pending producer treats opportunity authority as the only
`listed_info` source. That makes executable SELL plans without opportunity
authority produce `listed_info=None`, even though broker normalization later
requires listed issue metadata.

Consumer/copy defect: primary for the D5 halt.

Sell Planning produced a PM EXIT item with valid listed info, but Pending
Composition preserved the existing null strategy item and did not merge/copy
the newer listed-info authority into the preserved item.

Condition defect: yes.

The compatible-update path considers lineage and quantity compatible, but does
not verify that preserving the existing item also preserves required submit
authorities such as `listed_info`.

## Final Judgment

```text
listed_info Producer:
strategy_authority._listed_info_from_opportunity_authority for strategy pending items;
sell_pipeline._pending_item for PM sell order items.

Producer generated for 43880:
Strategy producer: no, returned None due missing opportunity authority.
Sell Planning PM producer: yes, generated basic listed_info.

Morning:
No direct listed_info field materialized in morning evidence; Morning-generated strategy pending is seen as listed_info null at Sell Planning input.

Runtime Planning:
No listed_info field. 43880 has no opportunity authority and quality_status=REVIEW_REQUIRED.

Pending Generation:
43880 strategy pending item generated with listed_info null.

Pending Composition:
Preserved existing null strategy item; did not copy listed_info from new PM EXIT item.

Approval:
Approved preserved pending id strategy-d3ca3c09c7e90609497b; did not repair listed_info.

Submit:
Consumed preserved item with listed_info null.

First null location:
strategy_authority pending item generation for strategy-d3ca3c09c7e90609497b.

Affected consumer:
Submit Guard historical_simulated_broker_authority / broker issue-code normalization.

43880 limited:
Observed only 43880 on 2023-04-10, but mechanism is not symbol-specific.

SELL_EXIT limited:
Observed on SELL_EXIT. The preservation/drop risk is SELL reconciliation-specific; initial producer condition is opportunity-authority-specific.

Producer defect:
Partial, strategy pending listed_info source is too narrow for executable SELL.

Consumer defect:
Yes, Submit requires listed_info but upstream validation did not enforce it before broker normalization.

Copy defect:
Yes, compatible SELL pending reconciliation preserved existing null item and did not merge valid listed_info from the new PM item.

Minimal repair scope:
Pending SELL compatible-update reconciliation should preserve/merge required submit authorities, especially listed_info, when preserving an existing item; additionally strategy pending generation should have a non-opportunity listed-info authority for executable SELL items.

Phase28-C relation:
false direct causality.

Phase28-D3 relation:
directly related to D3 reconciliation behavior; D3 preserved existing compatible SELL pending without authority-field merge.

Next Phase:
Phase28-D7 SELL pending authority merge repair design.
```
