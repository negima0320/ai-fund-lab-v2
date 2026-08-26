# Phase31-G121 — Campaign-Level ADD Identity / Winner Scaling Actual-Path Audit

## PRIMARY_JUDGMENT

G121_CAMPAIGN_LEVEL_ADD_BINDING_DEFECT_CONFIRMED_READY_FOR_REPAIR

## Scope

- Task type: READ-ONLY ACTUAL-PATH AUDIT
- Primary run: `runtime-test-historical-extended-smoke-20260825T135619843503Z`
- Audit cutoff: run-state completed list read while run was still `RUNNING`
- Completed business dates audited: `217`
- Completed window: `2022-10-03` through `2023-08-18`
- Next job observed at cutoff: `2023-08-21:morning`
- Code/config/run mutation: NO
- Fresh-run/resume/replay/long Historical executed: NO

This audit uses completed immutable artifacts only. Historical outcome is used only to select top winner examples for post-hoc characterization, not as production decision authority.

## Required SoT Basis

Read and used:

- `docs/phase_reports/phase31_g120_post_g119_long_horizon_performance_capital_characterization.md`
- `docs/02_architecture/portfolio_construction_and_position_sizing_contract.md`
- `docs/02_architecture/strategy_intelligence_architecture_v1.md`
- `src/ai_fund_lab_v2/strategy/shadow_runtime.py`

Relevant SoT contract:

```text
positions/position_campaigns.json is the canonical campaign identity authority.
Additional BUY executions while the ledger campaign is open are ADD evidence on
the same campaign, not a new campaign.
REENTRY after a ledger-proven full EXIT starts a new deterministic campaign.
```

## Headline Reconciliation

G120 reported:

```text
symbol-level repeated BUY fills = 18
canonical multi-BUY campaign = 0
```

G121 verifies the same headline at the 217-BD cutoff:

```text
SYMBOL_LEVEL_REPEATED_BUY_COUNT = 18
CANONICAL_MULTI_BUY_CAMPAIGN_COUNT = 0
```

However, the 18 symbol-level repeated BUYs are not all true ADDs. Ledger net quantity before the repeated BUY shows:

- True active-position ADD fills: `5`
- Re-entry / separate new campaign after flat quantity: `13`

Therefore the G120 symbol-level heuristic over-counted actual ADD. The remaining defect is still real: all `5` true ADD fills preserved/opened the same campaign quantity, but none appended a second BUY event to canonical campaign history.

## Repeated BUY Classification

Classification rule:

- `B`: legitimate ADD but campaign event not appended
- `D`: legitimate REENTRY after prior campaign closed / symbol was flat before BUY

| Date | Symbol | Qty | Net qty before BUY | Open campaign before | Campaign after | Class |
|---|---:|---:|---:|---|---|---|
| 2022-10-12 | 94320 | 100 | 200 | `pc-e62b56d...-94320-0001` | same open campaign | B |
| 2022-10-12 | 94340 | 100 | 200 | `pc-1018b4...-94340-0001` | same open campaign | B |
| 2022-10-13 | 94340 | 100 | 300 | `pc-1018b4...-94340-0001` | same open campaign | B |
| 2023-02-15 | 54010 | 100 | 100 | `pc-ace730...-54010-0001` | same open campaign | B |
| 2023-05-31 | 30410 | 100 | 100 | `pc-935731...-30410-0001` | same open campaign | B |
| 2022-11-01 | 48330 | 100 | 0 | none | new/flat restart | D |
| 2022-11-11 | 76470 | 800 | 0 | none | new campaign `0002` | D |
| 2022-12-29 | 37790 | 100 | 0 | none | new campaign `0002` | D |
| 2023-01-11 | 45410 | 100 | 0 | none | new/flat restart | D |
| 2023-03-07 | 93180 | 2,600 | 0 | none | new campaign `0002` | D |
| 2023-04-14 | 45860 | 300 | 0 | none | new campaign `0002` | D |
| 2023-04-14 | 77760 | 100 | 0 | none | new/flat restart | D |
| 2023-04-14 | 94340 | 400 | 0 | none | new campaign `0002` | D |
| 2023-05-02 | 77190 | 100 | 0 | none | new campaign `0002` | D |
| 2023-05-15 | 76010 | 200 | 0 | none | new campaign `0002` | D |
| 2023-05-19 | 31370 | 200 | 0 | none | new campaign `0002` | D |
| 2023-06-05 | 21340 | 1,800 | 0 | none | new campaign `0002` | D |
| 2023-06-15 | 59550 | 500 | 0 | none | new campaign `0002` | D |

REPEATED_BUY_CLASSIFICATION_COUNTS:

```text
A = 0
B = 5
C = 0
D = 13
E = 0
F = 0
G = 0
H = 0
```

## Active Campaign Binding

BUY_ADD_WITH_OPEN_CAMPAIGN_COUNT = 5

BUY_ADD_WITHOUT_OPEN_CAMPAIGN_COUNT = 13

For the 5 open-campaign ADD fills:

- Same campaign identity preserved: `5 / 5`
- Quantity updated to include the ADD: `5 / 5`
- Campaign BUY event/history appended: `0 / 5`

ADD_FILL_SAME_CAMPAIGN_IDENTITY_RATE = 100% by campaign identity / quantity

CAMPAIGN_ADD_QUANTITY_RECONCILIATION_FAILURE_COUNT = 0

CAMPAIGN_ADD_EVENT_HISTORY_APPEND_FAILURE_COUNT = 5

The defect is not that ADD created a wrong campaign ID. The defect is narrower: canonical campaign lifecycle updates open-campaign quantity, but does not append the additional BUY execution to `events`, `buy_history_summary`, or ADD history for the same campaign.

## Producer Boundary

Confirmed producer boundary:

```text
src/ai_fund_lab_v2/strategy/shadow_runtime.py
_materialize_pre_action_position_campaigns()
```

The function builds strict-prior ledger campaign states via:

```text
_strict_prior_ledger_campaigns_by_symbol()
```

That helper does understand additional BUY while a ledger campaign is open:

```text
if before_quantity > 1e-6:
    campaign["add_history_summary"] = _history_increment(...)
events.append(_campaign_event_from_execution(... side="BUY" ...))
```

But the actual materialization path for an already-known open prior campaign does:

```text
row = _refresh_campaign_with_current(row, current_row=current_row, business_date=business_date)
```

`_refresh_campaign_with_current()` updates `current_quantity`, market value, average price, MFE/giveback, and valuation state, but it does not merge strict-prior ledger BUY executions that occurred after the prior campaign snapshot. This explains the observed artifact shape:

```text
open campaign quantity increased
same position_campaign_id preserved
events still contain only the initial BUY
buy_history_summary remains count = 1
```

CAMPAIGN_IDENTITY_ADD_BINDING_DEFECT = YES

## PM ADD Intent Frequency

Across completed dates at cutoff:

```text
held-position evaluations = 2,296
PM HOLD = 1,412
PM ADD = 202
PM REDUCE = 313
PM EXIT = 369
PM ADD rate = 8.80%
```

PM ADD symbols:

| Symbol | PM ADD count |
|---|---:|
| 94320 | 108 |
| 76470 | 27 |
| 99840 | 18 |
| 43880 | 12 |
| 21340 | 9 |
| 94340 | 7 |
| 40520 | 7 |
| 54010 | 6 |
| 59550 | 5 |
| 72730 | 1 |
| 59350 | 1 |
| 30410 | 1 |

PM_ADD_INTENT_SPARSITY = MEDIUM

PM does request ADD, and it requests it heavily for a small number of campaigns. Therefore weak campaign-level winner scaling is not explained by PM never asking for ADD.

## PM ADD to Fill Funnel

For 202 PM ADD intents:

| Stage / outcome | Count |
|---|---:|
| SAME_DAY_FILL | 5 |
| NEXT_DAY_FILL | 1 |
| AUTHORIZED_NO_FILL | 1 |
| COMPARABLE_DEFERRED | 3 |
| CASH_MARGINAL_PREFERRED | 2 |
| INSUFFICIENT_EVIDENCE | 190 |

Interpretation:

Most PM ADD intents do not become actual ADD fills. PC/G115 evidence is highly selective and often fail-closed or insufficient-evidence driven. This is a secondary winner-scaling limitation. It does not explain the headline `canonical multi-BUY campaign = 0`, because even the successful true ADD fills failed to append campaign BUY events.

G115_PRIMARY_CAUSE_OF_WEAK_WINNER_SCALING = PARTIAL

## Primary Symbol Timelines

| Symbol | PM action summary | Actual fill timeline | Classification |
|---|---|---|---|
| 94340 | HOLD 64, ADD 7, REDUCE 1, EXIT 2 | BUY 200 on 2022-10-03; true ADD 100 on 2022-10-12; true ADD 100 on 2022-10-13; REDUCE 100 on 2023-01-11; EXIT 300 on 2023-01-12; REENTRY 400 on 2023-04-14; EXIT 2023-04-25 | ADD event defect for 2022-10-12/13; later reentry |
| 94320 | HOLD 104, ADD 108, REDUCE 2 | BUY 200 on 2022-10-05; true ADD 100 on 2022-10-12 | ADD event defect |
| 48330 | EXIT 2 | BUY 2022-10-17; EXIT 2022-10-18; BUY 2022-11-01; EXIT 2022-11-02 | Reentry / separate campaign |
| 76470 | HOLD 21, ADD 27, EXIT 2 | BUY 2022-10-12; EXIT 2022-10-14; BUY 2022-11-11; EXIT 2023-01-24 | Reentry / separate campaign |
| 37790 | HOLD 1, EXIT 2 | BUY 2022-12-07; EXIT 2022-12-08; BUY 2022-12-29; EXIT 2023-01-04 | Reentry / separate campaign |
| 45410 | HOLD 1, EXIT 2 | BUY 2022-12-16; EXIT 2022-12-20; BUY 2023-01-11; EXIT 2023-01-12 | Reentry / separate campaign |
| 54010 | HOLD 44, ADD 6, EXIT 1 | BUY 2023-01-20; true ADD 2023-02-15; EXIT 2023-04-05 | ADD event defect |
| 93180 | HOLD 13, REDUCE 1, EXIT 2 | BUY 2022-10-25; EXIT 2022-10-27; BUY 2023-03-07; REDUCE 2023-03-27; EXIT 2023-03-28 | Reentry / separate campaign |
| 45860 | REDUCE 1, EXIT 2 | BUY 2023-01-24; EXIT 2023-01-25; BUY 2023-04-14; SELL 2023-04-18 | Reentry / separate campaign |
| 77760 | HOLD 10, REDUCE 1, EXIT 2 | BUY 2023-01-31; SELL 2023-02-16; BUY 2023-04-14; EXIT 2023-04-17 | Reentry / separate campaign |
| 21340 | HOLD 14, ADD 9, EXIT 2 | BUY 2023-05-16; EXIT 2023-05-17; BUY 2023-06-05; EXIT 2023-07-07 | Reentry / separate campaign |
| 59550 | HOLD 3, ADD 5, REDUCE 3, EXIT 2 | BUY 2023-05-29; REDUCE/EXIT 2023-06-05 to 2023-06-07; BUY 2023-06-15; REDUCE/EXIT 2023-06-22 to 2023-06-23 | Reentry / separate campaign |

## Winner Examples

TOP_WINNER_ADD_OPPORTUNITY_MATRIX:

| Symbol | Campaign | PM ADD during open campaign? | PM summary | Where scaling stopped |
|---|---|---|---|---|
| 44440 | 2023-03-16 to 2023-03-22 | NO | HOLD 2, EXIT 1 | PM never emitted ADD |
| 64240 | 2023-03-16 to 2023-03-23 | NO | HOLD 2, REDUCE 1, EXIT 1 | PM never emitted ADD |
| 80290 | 2022-11-15 to 2022-12-20 | NO | HOLD 23, EXIT 1 | PM never emitted ADD |
| 72140 | 2023-05-22 to 2023-05-26 | NO | HOLD 2, REDUCE 1, EXIT 1 | PM never emitted ADD |
| 88900 | 2023-05-22 to 2023-07-14 | NO | HOLD 38, EXIT 1 | PM never emitted ADD |
| 69730 | 2022-10-25 to 2022-12-05 | NO | HOLD 23, REDUCE 3, EXIT 1 | PM never emitted ADD |
| 40520 | 2023-06-15 to 2023-07-14 | YES | HOLD 11, ADD 7, REDUCE 2, EXIT 1 | PM ADD existed; no actual ADD fill |
| 93410 | 2023-05-30 to 2023-06-19 | NO | HOLD 13, EXIT 1 | PM never emitted ADD |

WINNER_RECOGNIZED_BUT_NOT_SCALED = PARTIAL

For most top winners, PM classified the position as HOLD-worthy but not ADD-worthy. For `40520`, PM did recognize ADD-worthiness repeatedly, but the ADD did not become an actual fill. This shows both semantic selectivity and downstream conversion loss.

## Re-entry vs ADD

REENTRY_SUBSTITUTING_FOR_ADD = PARTIAL

Most symbol-level repeated BUYs are not true ADDs. They occur after the symbol is flat and are better described as REENTRY / separate NEW_BUY by ledger quantity. However, some of these are short-cycle close/reopen patterns, so they may still represent winner lifecycle fragmentation at the investment-philosophy level. They are not campaign identity append defects.

## BULL / RANGE Connection

Characterization only:

| Regime | PM ADD | Same-symbol BUY_ADD heuristic | BUY_NEW | ADD / BUY_NEW |
|---|---:|---:|---:|---:|
| BULL | 84 | 9 | 149 | 0.060 |
| RANGE | 44 | 1 | 81 | 0.012 |

BULL_ADD_TO_NEW_BUY_RATIO = 0.060

RANGE_ADD_TO_NEW_BUY_RATIO = 0.012

Weak campaign-level ADD scaling is not isolated to BULL, but BULL has more PM ADD and more repeated BUY activity in absolute terms.

## Philosophy Conformance

WINNER_SCALING_PHILOSOPHY_CONFORMANCE = PARTIAL

The system partially conforms:

- It enters and exits campaigns.
- It recognizes HOLD / ADD distinction.
- It does not force ADD.
- It preserves same campaign identity and quantity for true open-campaign ADD fills.

It fails the full winner-scaling philosophy because:

- Canonical campaign event history does not record true ADD executions.
- Top winners mostly remain single-BUY campaigns.
- PM ADD intent is concentrated and frequently does not convert to fill.
- The canonical lifecycle cannot currently prove the intended `small initial entry -> confirmation -> ADD -> winner scaling` path, even when actual ADD fills occurred.

## Root Cause

G121_PRIMARY_ROOT_CAUSE = A

Primary:

```text
A = campaign identity/event materialization defect
```

The narrow confirmed defect is:

```text
actual BUY_ADD fill exists
+ open campaign exists
+ same campaign identity should apply
+ same campaign quantity is updated
BUT canonical campaign BUY event/history is not appended
```

Secondary contributors:

- PM ADD intent is medium-sparse overall and sparse for many top winners.
- G115/PC marginal competition is highly selective; most PM ADD intents classify as insufficient evidence before fill.
- Many symbol-level repeated BUYs are legitimate re-entry, not ADD.

## Repair Decision

REPAIR_REQUIRED = YES

RESEARCH_REQUIRED = NO_BEFORE_REPAIR

Repair should be narrow and limited to the campaign lifecycle materialization boundary. It should not change PM ADD thresholds, G115 marginal competition, Market Quality, Risk Pacing, Candidate ranking, Position Sizing ownership, Runtime priority, or SELL semantics.

## Required Final Fields

SYMBOL_LEVEL_REPEATED_BUY_COUNT = 18

CANONICAL_MULTI_BUY_CAMPAIGN_COUNT = 0

PM_ADD_INTENT_SPARSITY = MEDIUM

BUY_ADD_WITH_OPEN_CAMPAIGN_COUNT = 5

BUY_ADD_WITHOUT_OPEN_CAMPAIGN_COUNT = 13

ADD_FILL_SAME_CAMPAIGN_IDENTITY_RATE = 100%

CAMPAIGN_ADD_QUANTITY_RECONCILIATION_FAILURE_COUNT = 0

CAMPAIGN_ADD_EVENT_HISTORY_APPEND_FAILURE_COUNT = 5

WINNER_RECOGNIZED_BUT_NOT_SCALED = PARTIAL

REENTRY_SUBSTITUTING_FOR_ADD = PARTIAL

G115_PRIMARY_CAUSE_OF_WEAK_WINNER_SCALING = PARTIAL

CAMPAIGN_IDENTITY_ADD_BINDING_DEFECT = YES

WINNER_SCALING_PHILOSOPHY_CONFORMANCE = PARTIAL

BULL_ADD_TO_NEW_BUY_RATIO = 0.060

RANGE_ADD_TO_NEW_BUY_RATIO = 0.012

G121_PRIMARY_ROOT_CAUSE = A

REPAIR_REQUIRED = YES

RESEARCH_REQUIRED = NO_BEFORE_REPAIR

FUTURE_INFORMATION_USED_FOR_PRODUCTION_DECISION = NO

CODE_CHANGED = NO

CONFIG_CHANGED = NO

RUN_MUTATED_BY_CODEX = NO

FRESH_RUN_EXECUTED = NO

RESUME_EXECUTED = NO

REPLAY_EXECUTED = NO

LONG_HISTORICAL_EXECUTED = NO

## Next Task

PHASE31_G122_CAMPAIGN_LIFECYCLE_ADD_EVENT_HISTORY_MATERIALIZATION_REPAIR

Repair only the confirmed boundary:

```text
shadow_runtime._materialize_pre_action_position_campaigns()
```

When an existing open prior campaign is refreshed from current state and strict-prior ledger proves additional BUY executions occurred while the campaign was open, merge the canonical ledger campaign BUY events / `buy_history_summary` / `add_history_summary` into the same `position_campaign_id`. Preserve REENTRY-after-flat semantics and do not synthesize fake ADD events.

