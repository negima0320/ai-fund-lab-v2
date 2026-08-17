# Phase30-AE0 - PC Campaign Identity / ADD Conversion Regression Lineage Audit

Task ID: `Phase30-AE0`

Target after run:

```text
runtime-test-historical-extended-smoke-20260816T045533779694Z
```

Comparison before run:

```text
runtime-test-historical-extended-smoke-20260816T023934342407Z
```

Boundary:

```text
READ_ONLY_AUDIT
NO_IMPLEMENTATION_AUTHORIZED_BY_PHASE30-AE0
NO_TARGET_RUN_MUTATION
NO_REPLAY
NO_RESUME
NO_AC_ROLLBACK
NO_LEGACY_FALLBACK_REINTRODUCTION
NO_STRATEGY_TUNING
NO_HISTORICAL_OUTCOME_FIT
```

## Primary Judgment

```text
REGRESSION_CONFIRMED
ADD_CONVERSION_REGRESSION = YES
```

Phase30-AC correctly retired legacy campaign fallbacks and established the
canonical campaign authority path for Strategy Intelligence. However, the
post-AC production chain does not propagate that canonical campaign identity
back into the Portfolio Construction current-position ADD bridge. As a result,
PM emits ADD actions, SI and PC hold the canonical campaign id, but PC's ADD
continuation check compares:

```text
current/PM campaign = runtime-current-94320
opportunity campaign = pc-24c0e765c71b953f-94320-0001
```

The mismatch forces `ADD_CAMPAIGN_CONTINUATION_FAIL`,
`ADD_INCREMENTAL_VALUE_UNKNOWN`, `target_weight_change = 0`, PS zero quantity,
Runtime `NO_ACTION`, and no BUY_ADD fills.

## Regression Classification

```text
PC_CURRENT_CAMPAIGN_ID_PROPAGATION = FAIL
PM_ADD_TO_PC_CONVERSION = FAIL
PC_TO_PS_ADD_CONVERSION = FAIL
PS_TO_RUNTIME_BUY_ADD = FAIL
PHASE30_S_HANDOFF_DEFECT_RECURRENCE = NO
PHASE29_ADD_CAPITAL_CONVERSION_DEFECT_RECURRENCE = NO
ADD_CONVERSION_REGRESSION = YES
```

Classification is `REGRESSION_CONFIRMED`, not intentional behavior change:

- AC-before run had `11` PM ADD actions for 94320 and `5` executed BUY_ADD fill
  days, totaling `1,000` added shares.
- AC/AD1-after run had `14` PM ADD actions for 94320 and `0` executed BUY_ADD
  fills.
- The after-run includes a healthy case on `2022-08-30` with
  `HEALTHY_CONTINUATION_ENTRY / ADD_ALLOWED`, Expected Edge `PASS`,
  opportunity cost `PASS`, no-loss averaging `PASS`, capital `PASS`, and
  execution feasibility `PASS`; it still receives zero incremental target only
  because campaign continuation fails.

## Historical ADD Contract

Canonical ADD conversion contract:

| Stage | Canonical field | Producer | Consumer | Required PASS |
| --- | --- | --- | --- | --- |
| PM ADD | `positions[].action = ADD` | Position Management | Portfolio Construction | PM action preserved as ADD |
| Current-position identity | `current_position_campaign_id` | Current / campaign authority adapter | PC member + ADD evidence | Same campaign as opportunity or authoritative explicit continuation |
| ADD-worthiness | `strategy_intelligence_add_worthiness_evidence` | Strategy Intelligence -> PM | PM / PC | `ADD_ALLOWED` or reduced ADD state, not `NO_ADD` |
| Incremental target | `target_weight_change > 0` | Portfolio Construction ADD bridge | Position Sizing | all ADD eligibility checks PASS |
| Concrete quantity | positive `quantity_delta` / transaction quantity | Position Sizing | Runtime Planning | lot/capital conversion produces positive delta |
| Runtime intent | `planning_intent = BUY_ADD` | Runtime Planning | Execution | existing position + positive BUY delta |
| Fill | BUY fill quantity | Execution | Ledger / Current | fill recorded and applied |

Prior established repairs:

- Phase28-D12 confirmed PM ADD propagation through PC, PS, Runtime BUY_ADD.
- Phase30-S repaired PC final artifact -> PS -> Runtime production quantity
  handoff.
- Phase30-W preserved one-lot admission and BUY_WAIT / NO_ADD behavior.
- Phase30-Z preserved REENTRY recovery authority independently of ADD.

## AC Before / After

AC-before, 94320:

```text
PM ADD count = 11
executed BUY_ADD fill days = 5
added quantity = 1,000
quantity path = 200 -> 400 -> 700 -> 900 -> 1100 -> 1200
campaign comparison used runtime-current style identity and passed
```

AC/AD1-after, 94320:

```text
PM ADD count = 14
executed BUY_ADD fill days = 0
added quantity = 0
quantity path = 200 -> 200
SI canonical campaign id = pc-24c0e765c71b953f-94320-0001
PC current_position_campaign_id = blank
PC pm_position_campaign_id = runtime-current-94320
PC opportunity_position_campaign_id = pc-24c0e765c71b953f-94320-0001
```

Phase30-AC changed campaign authority from legacy/current fallback semantics to
canonical `positions/position_campaigns.json` materialization. That was the
right authority direction, but the current-position input consumed by PC was not
updated to carry the canonical campaign id.

## PC Campaign Identity Root Cause

Lineage:

| Layer | Field | Observed value |
| --- | --- | --- |
| SI | `symbol_intelligence[94320].lifecycle_context.position_campaign_id` | `pc-24c0e765c71b953f-94320-0001` |
| PM | `positions[].strategy_intelligence_campaign_id` | `pc-24c0e765c71b953f-94320-0001` |
| PM legacy ref | `positions[].lifecycle_reference` | `runtime-current-94320` |
| PC current member | `current_position_campaign_id` | blank |
| PC PM member | `pm_position_campaign_id` | `runtime-current-94320` |
| PC opportunity member | `opportunity_position_campaign_id` | `pc-24c0e765c71b953f-94320-0001` |
| PC SI member | `strategy_intelligence_campaign_id` | `pc-24c0e765c71b953f-94320-0001` |

Exact locations:

- `src/ai_fund_lab_v2/strategy/shadow_runtime.py:1192` only preserves
  `row.position_campaign_id` into Current; the target run's current ledger rows
  do not carry that canonical field.
- `src/ai_fund_lab_v2/strategy/portfolio_construction.py:984` derives
  `current_position_campaign_id` only from Current `position_campaign_id` /
  `campaign_id`.
- `src/ai_fund_lab_v2/strategy/portfolio_construction.py:985` derives
  `pm_position_campaign_id` from PM `position_campaign_id`, `campaign_id`, then
  `lifecycle_reference`; because PM does not expose canonical
  `position_campaign_id`, `runtime-current-94320` is consumed.
- `src/ai_fund_lab_v2/strategy/add_investment_evidence.py:127` resolves
  campaign continuation by first choosing current / PM / position campaign
  fields and comparing them with opportunity campaign identity.
- `src/ai_fund_lab_v2/strategy/portfolio_construction.py:3062` requires
  `campaign == PASS` before incremental ADD target can increase.

This is `ACTION_EFFECTIVE_GAP`, not display-only or observability-only.

## PM ADD 14-Case Funnel

All after-run PM ADD cases are 94320.

| Date | PM ADD | Entry | EE | Campaign | Inc value | Target change | Runtime BUY_ADD | Fill | Classification |
| --- | --- | --- | --- | --- | --- | ---: | --- | ---: | --- |
| 2022-08-12 | ADD_REDUCED_ONLY | CONTINUATION_WITH_CAUTION / ADD_REDUCED_ONLY | FAIL_CLOSED | FAIL_CLOSED | FAIL_CLOSED | 0.0 | false | 0 | CAMPAIGN_ID_PROPAGATION_DROP |
| 2022-08-19 | ADD_REDUCED_ONLY | CONTINUATION_WITH_CAUTION / ADD_REDUCED_ONLY | PASS | FAIL_CLOSED | FAIL_CLOSED | 0.0 | false | 0 | CAMPAIGN_ID_PROPAGATION_DROP |
| 2022-08-22 | ADD_REDUCED_ONLY | CONTINUATION_WITH_CAUTION / ADD_REDUCED_ONLY | PASS | FAIL_CLOSED | FAIL_CLOSED | 0.0 | false | 0 | CAMPAIGN_ID_PROPAGATION_DROP |
| 2022-08-23 | ADD_REDUCED_ONLY | CONTINUATION_WITH_CAUTION / ADD_REDUCED_ONLY | PASS | FAIL_CLOSED | FAIL_CLOSED | 0.0 | false | 0 | CAMPAIGN_ID_PROPAGATION_DROP |
| 2022-08-24 | ADD_REDUCED_ONLY | CONTINUATION_WITH_CAUTION / ADD_REDUCED_ONLY | PASS | FAIL_CLOSED | FAIL_CLOSED | 0.0 | false | 0 | CAMPAIGN_ID_PROPAGATION_DROP |
| 2022-08-25 | ADD_REDUCED_ONLY | CONTINUATION_WITH_CAUTION / ADD_REDUCED_ONLY | FAIL_CLOSED | FAIL_CLOSED | FAIL_CLOSED | 0.0 | false | 0 | CAMPAIGN_ID_PROPAGATION_DROP |
| 2022-08-26 | ADD_REDUCED_ONLY | CONTINUATION_WITH_CAUTION / ADD_REDUCED_ONLY | FAIL_CLOSED | FAIL_CLOSED | FAIL_CLOSED | 0.0 | false | 0 | CAMPAIGN_ID_PROPAGATION_DROP |
| 2022-08-29 | ADD_REDUCED_ONLY | CONTINUATION_WITH_CAUTION / ADD_REDUCED_ONLY | FAIL_CLOSED | FAIL_CLOSED | FAIL_CLOSED | 0.0 | false | 0 | CAMPAIGN_ID_PROPAGATION_DROP |
| 2022-08-30 | ADD_ALLOWED | HEALTHY_CONTINUATION_ENTRY / ADD_ALLOWED | PASS | FAIL_CLOSED | FAIL_CLOSED | 0.0 | false | 0 | CAMPAIGN_ID_PROPAGATION_DROP |
| 2022-08-31 | NO_ADD | REVERSAL_RISK_ENTRY / NO_ADD | PASS | FAIL_CLOSED | FAIL_CLOSED | 0.0 | false | 0 | JUSTIFIED_NO_ADD |
| 2022-09-01 | ADD_REDUCED_ONLY | CONTINUATION_WITH_CAUTION / ADD_REDUCED_ONLY | PASS | FAIL_CLOSED | FAIL_CLOSED | 0.0 | false | 0 | CAMPAIGN_ID_PROPAGATION_DROP |
| 2022-09-02 | ADD_REDUCED_ONLY | CONTINUATION_WITH_CAUTION / ADD_REDUCED_ONLY | PASS | FAIL_CLOSED | FAIL_CLOSED | 0.0 | false | 0 | CAMPAIGN_ID_PROPAGATION_DROP |
| 2022-09-05 | ADD_REDUCED_ONLY | CONTINUATION_WITH_CAUTION / ADD_REDUCED_ONLY | FAIL_CLOSED | FAIL_CLOSED | FAIL_CLOSED | 0.0 | false | 0 | CAMPAIGN_ID_PROPAGATION_DROP |
| 2022-09-06 | ADD_REDUCED_ONLY | CONTINUATION_WITH_CAUTION / ADD_REDUCED_ONLY | PASS | FAIL_CLOSED | FAIL_CLOSED | 0.0 | false | 0 | CAMPAIGN_ID_PROPAGATION_DROP |

Counts:

```text
CAMPAIGN_ID_PROPAGATION_DROP = 13
JUSTIFIED_NO_ADD = 1
PC_INCREMENTAL_ALLOCATION_DROP = 0
LOT_CAPITAL_DROP = 0
PS_CONVERSION_DROP = 0
RUNTIME_MAPPING_DROP = 0
```

## 94320 Deep Dive

### 2022-08-19

```text
PM action = ADD
PM ADD state = ADD_REDUCED_ONLY
Entry = CONTINUATION_WITH_CAUTION / ADD_REDUCED_ONLY
Expected Edge = PASS
Opportunity cost = PASS
No-loss averaging = PASS
Campaign continuation = FAIL_CLOSED
Target change = 0.0
BUY_ADD fill = 0
```

AC-before comparable day produced a BUY_ADD fill of `200` shares. AC-after did
not because campaign identity mismatched.

### 2022-08-30

```text
PM action = ADD
PM ADD state = ADD_ALLOWED
Entry = HEALTHY_CONTINUATION_ENTRY / ADD_ALLOWED
Expected Edge = PASS
Opportunity cost = PASS
No-loss averaging = PASS
Capital availability = PASS
Execution feasibility = PASS
Campaign continuation = FAIL_CLOSED
Target change = 0.0
BUY_ADD fill = 0
```

This is the cleanest regression sentinel. It is not a correct NO_ADD case and
not a lot/capital conversion block.

### 2022-08-31

```text
PM ADD state = NO_ADD
Entry = REVERSAL_RISK_ENTRY / NO_ADD
BUY_ADD fill = 0
```

This case should remain no-add. A repair must preserve this behavior and must
not re-open blanket ADDs for reversal-risk or weak-survivor positions.

## Phase30-S / Phase29 Recurrence

```text
PHASE30_S_HANDOFF_DEFECT_RECURRENCE = NO
PHASE29_ADD_CAPITAL_CONVERSION_DEFECT_RECURRENCE = NO
```

Reason:

- PC never produces positive after-run ADD `target_weight_change`; therefore PS
  is not dropping a valid positive PC ADD.
- Runtime is not mis-mapping a positive PS ADD quantity; no positive PS ADD
  quantity exists.
- This is not the Phase29 lot/capital conversion defect. Lot/capital evidence
  is downstream of the present failure.

The broken contract is earlier: canonical campaign identity from SI/PM/Current
is not connected into the PC ADD continuation bridge.

## Capital Utilization Impact

Decision-time affected symbol:

```text
94320
```

AC-before realized ADD conversion:

```text
5 BUY_ADD fill days
1,000 added shares
```

AC-after realized ADD conversion:

```text
0 BUY_ADD fill days
0 added shares
```

The after-run blocked all incremental ADD notional before PS quantity
conversion. Exact executable notional is not asserted from future outcomes; the
decision-time proof is that positive ADD requests existed, but were zeroed at
PC due campaign continuation failure.

This materially contributes to AD2's low exposure / high cash behavior, but it
does not prove that all cash was wrong. Cash remains valid for genuine
BUY_WAIT, NO_ADD, lot infeasibility, or opportunity-scarcity cases.

## Correct NO_ADD Preservation

Correct behavior that must be preserved:

- `REVERSAL_RISK_ENTRY / NO_ADD` on 2022-08-31.
- Weak survivor no-add behavior introduced by AC.
- Phase30-W one-lot admission and BUY_WAIT behavior.
- Phase30-Z REENTRY recovery blocks.
- SELL / REDUCE / EXIT independence.

The recommended repair must connect canonical campaign identity for ADD
continuation without restoring legacy `runtime-current-*` as campaign authority
and without forcing ADD where Entry Admission says `NO_ADD`.

## Production Integrity

```text
PHASE30_AC_CAMPAIGN_LIFECYCLE_PRESERVED = YES
PHASE30_W_ENTRY_ADMISSION_PRESERVED = YES
PHASE30_Z_REENTRY_PRESERVED = YES
LEGACY_CAMPAIGN_FALLBACK_REFERENCE_COUNT = 0
ONE_PRODUCTION_CAMPAIGN_LIFECYCLE_PATH = YES
```

## Leakage

```text
FUTURE_INFORMATION_USED = FALSE
HISTORICAL_OUTCOME_USED_AS_RUNTIME_INPUT = FALSE
HISTORICAL_OUTCOME_USED_FOR_PRODUCTION_PARAMETER_SELECTION = FALSE
TEST_RESULT_USED_AS_STRATEGY_INPUT = FALSE
```

## Evidence

Generated read-only audit evidence:

```text
reports/phase_reports/phase30_ae0/add_funnel_evidence.json
reports/phase_reports/phase30_ae0_pc_campaign_identity_add_conversion_regression_lineage_audit.json
```

## Implementation Authorization

```text
NO IMPLEMENTATION AUTHORIZED BY PHASE30-AE0
```

## Recommended Next Task

```text
Phase30-AE1 - Canonical Campaign-Aware ADD Conversion Regression Repair
```

Repair scope should be narrow:

- propagate canonical current position campaign identity into PC current-position
  ADD continuation;
- ensure PM exposes canonical `position_campaign_id` when SI campaign identity
  is COMPLETE;
- do not reintroduce legacy campaign fallback authority;
- preserve `NO_ADD`, BUY_WAIT, one-lot admission, REENTRY, SELL/REDUCE/EXIT,
  Safety, thresholds, and Expected Edge uncalibrated semantics.
