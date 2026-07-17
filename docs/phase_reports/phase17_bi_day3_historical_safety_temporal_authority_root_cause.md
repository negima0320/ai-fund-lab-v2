# Phase17-BI Day3 Historical Safety Temporal Authority Root Cause

## Executive Summary

判定: `PHASE17_BI_ROOT_CAUSE_CONFIRMED`

2026-07-08 `data_readiness` は、Current / Current Valuation / Market / Quote / Feature / Pending がREADYである一方、Safety componentのみ `REVIEW_REQUIRED` となり停止した。

Root Causeは、Day2 `2026-07-07` の正式なEMPTY/no-action PendingがDay3開始時にも固定Pending slotへ残り、そのPending内の `safety_context` をDay3のHistorical Safety authority候補として再検証したことにある。実装はEMPTY Pendingでも `target_session_date == business_date` と `safety_context.safety_business_date == business_date` を要求するため、Day2用EMPTY PendingをDay3用Safety authorityとしては不一致と判断した。

これはSafety checkを緩めるべき問題ではない。Day3朝のHistorical neutral Safety authorityを生成または解決する正式AuthorityがRun sequence上に存在せず、前日EMPTY Pendingのsafety_contextに依存していることが問題である。

## Halt Evidence

対象Run:

```text
profile = historical-smoke
run_id = runtime-test-historical-smoke-20260715T111433056797Z
halt point = 2026-07-08:data_readiness
CLI exit code = 20
runner exit code = 30
```

Run StateではDay3 `market_refresh` はPASSし、次の `data_readiness` がexit code 20で停止している。

Day3 Data Readiness:

```text
overall_status = REVIEW_REQUIRED
review_reasons = ["historical_safety_temporal_authority_missing"]
safety_status = REVIEW_REQUIRED
effective_safety_status = REVIEW_REQUIRED
```

READYだったcomponent:

```text
current_status = READY
current_valuation_status = READY
market_status = READY
quote_status = READY
feature_status = READY
pending_status = READY
pending_slot_status = EMPTY
pending_active = false
```

Current Valuation:

```text
business_date = 2026-07-08
valuation_as_of = 2026-07-07
source_market_date = 2026-07-07
current_valuation_temporal_reason =
  previous_trading_day_close_is_latest_available_at_morning_evaluation
```

Pending:

```text
state = EMPTY
status = EMPTY
active_pending = false
target_session_date = 2026-07-07
no_action_reason = NO_SIGNAL:exit_ai_no_sell_signal
safety_context.safety_business_date = 2026-07-07
```

Day3 expected Safety date:

```text
safety_business_date_expected = 2026-07-08
mismatched_fields = [
  "safety_context.safety_business_date",
  "target_session_date"
]
pending authority reason = historical_pending_safety_authority_mismatch
```

`.runtime/runtime_state/safety/latest_safety_decision.json` did not exist at investigation time. `load_runtime_safety_decision()` therefore returns `SAFETY_MISSING`, which triggers Historical fallback authority resolution.

## Day1 / Day2 / Day3 Timeline

### Day1: 2026-07-06

Sequence:

```text
market_refresh PASS
data_readiness PASS
morning PASS
sell_planning PASS
submit PASS
execution PASS
current_valuation_refresh PASS
runtime_state_refresh PASS
```

Data Readiness observed:

```text
pending_slot_status = CONSUMED
pending_active = true
safety_status = READY
historical_safety_temporal_authority = historical_initial_no_external_effect
pending_safety_authority.status = READY
pending_safety_authority.safety_business_date_expected = 2026-07-06
```

Day1 passed because the Pending safety context matched the same business date. There was no cross-day EMPTY/no-action carry issue yet.

### Day2: 2026-07-07

Sequence after prior Phase fixes:

```text
market_refresh PASS
data_readiness PASS
morning PASS
sell_planning PASS
submit initially exit 10, later resume PASS
execution initially exit 20, later resume PASS
current_valuation_refresh initially exit 20, later resume PASS
runtime_state_refresh PASS
```

Day2 no-signal path:

```text
sell_planning pending_continuity_evidence.status = NO_SIGNAL
reason = NO_SIGNAL:exit_ai_no_sell_signal
Pending = EMPTY / active_pending=false / items=[]
Submit = NO_ACTION / submitted_count=0
Execution = NO_ACTION / pending_terminalization_status=ALREADY_TERMINAL
pending_mutated=false
```

Day2 Data Readiness observed:

```text
pending_slot_status = EMPTY
pending_active = false
safety_status = READY
pending_safety_authority.reason =
  historical_no_action_pending_safety_authority_ready
pending_safety_authority.safety_business_date_expected = 2026-07-07
```

Day2 passed because the EMPTY Pending was same-day (`target_session_date=2026-07-07`) and its embedded `safety_context.safety_business_date=2026-07-07` matched the expected Safety date.

Day2 `runtime_state_refresh` did not generate a Day3 Safety authority. Its manifest still had `safety_status=SAFETY_MISSING`. It refreshed Runtime State, not `.runtime/runtime_state/safety/latest_safety_decision.json`.

### Day3: 2026-07-08

Sequence:

```text
market_refresh PASS
data_readiness REVIEW_REQUIRED
```

Day3 Data Readiness read the fixed Pending slot, still containing the Day2 EMPTY/no-action payload:

```text
target_session_date = 2026-07-07
safety_context.safety_business_date = 2026-07-07
```

Because Day3 business_date is `2026-07-08`, `_historical_pending_safety_authority()` expected:

```text
safety_business_date_expected = 2026-07-08
target_session_date = 2026-07-08
```

The pending component itself stayed READY because EMPTY/non-active is a valid terminal slot. The Safety component rejected it as Day3 Safety authority, causing the halt.

## Design Contract

Historical Runtime uses the normal Runtime root and normal fixed paths. The Historical Runtime Test contract explicitly prohibits alternate Runtime roots and requires normal Current / Ledger / Pending / Runtime State authority.

Safety in normal Runtime is a Safety Runtime responsibility:

```text
safety_evaluation -> safety_refresh -> .runtime/runtime_state/safety/latest_safety_decision.json
```

Operational evidence docs identify `latest_safety_decision.json` as Runtime Safety Decision SoT generated by `safety_refresh`.

Historical smoke profile sequence is:

```text
market_refresh
data_readiness
morning
sell_planning
submit
execution
current_valuation_refresh
runtime_state_refresh
```

It does not include `safety_evaluation` or `safety_refresh`.

Phase17-X/AB introduced Historical neutral Safety authority for replay when latest Safety evidence is missing/stale. That authority is accepted only when run-scoped identity, business_date, policy, decision, source, broker_write=false, and external_delivery=false are validated.

Pending `safety_context` is therefore an audit and propagation vehicle for the Pending it belongs to. It is not clearly specified as the next business day’s standalone Safety SoT.

EMPTY/no-action Pending contract from Phase17-BF/BG:

- `EMPTY / active_pending=false / items=[]` is a formal terminal no-action state.
- It requires no Submit, no Execution, no broker write.
- Execution does not mutate or re-terminalize an already EMPTY Pending.
- It blocks neither next-day operation nor overwrites existing SELL Pending.

The missing design piece is how Day3 receives a fresh Historical neutral Safety authority when Day2 ended with EMPTY/no-action and no Safety producer runs.

## Producer / Consumer Map

| Artifact / Authority | Producer | Consumer | Day3 Observation |
|---|---|---|---|
| Market evidence | `market_refresh` | Data Readiness, Current Valuation | READY for 2026-07-08 |
| Feature artifacts/contract | `market_refresh` | Data Readiness, Morning | READY for 2026-07-08 |
| Current valuation | `current_valuation_refresh` | Day3 morning Data Readiness | READY as previous trading day close |
| Pending EMPTY | Sell Planning / Submit / Execution no-action path | Data Readiness, Submit/Execution | READY as terminal slot, but dated 2026-07-07 |
| Runtime State | `runtime_state_refresh` | Data Readiness | READY |
| Runtime Safety Decision latest pointer | `safety_refresh` in normal Runtime | Data Readiness / Submit Guard | Missing in this Historical sequence |
| Historical neutral Safety authority | Data Readiness fallback from initial current or Pending safety_context | Data Readiness and downstream historical steps | Missing for Day3 because fallback source was Day2 EMPTY Pending |

## Artifact Lifecycle

Day2 no-action lifecycle:

```text
sell_planning creates EMPTY/no-signal Pending for 2026-07-07
submit reads EMPTY and returns NO_ACTION
execution reads Submit NO_ACTION and returns NO_ACTION
execution does not mutate Pending
runtime_state_refresh does not mutate Pending or create Safety authority
```

Resulting Day3 input:

```text
pending_order_plan/pending_order_plan.json
  state = EMPTY
  active_pending = false
  target_session_date = 2026-07-07
  safety_context.safety_business_date = 2026-07-07
```

This is valid as a terminal Day2 Pending. It is not valid as Day3 Safety authority under the current implementation.

## Exact Root Cause

Exact code path:

1. `evaluate_runtime_data_readiness()` reads Pending via `_pending_readiness_payload()`.
2. `_pending_readiness_payload()` always computes `historical_pending_safety_authority`, even for `state=EMPTY and active_pending=false`.
3. For EMPTY, `_pending_readiness_payload()` returns Pending READY regardless of the embedded historical safety authority mismatch.
4. `_safety_readiness_payload()` loads `latest_safety_decision.json`.
5. Because the latest Safety decision is missing or not for the business date, Historical fallback is entered.
6. Initial-empty Current fallback does not apply because Current has positions.
7. `_safety_readiness_payload()` then requires `_historical_pending_safety_authority(...).status == READY`.
8. `_historical_pending_safety_authority()` sets `expected_safety_business_date = business_date` unless the Pending is consumed prior-session carry-forward.
9. Day3 Pending is EMPTY, not consumed. Therefore expected date is `2026-07-08`.
10. Day2 EMPTY Pending has `target_session_date=2026-07-07` and `safety_context.safety_business_date=2026-07-07`.
11. Mismatch fields are `safety_context.safety_business_date` and `target_session_date`.
12. Safety returns `historical_safety_temporal_authority_missing`.

Key implementation references:

- `src/ai_fund_lab_v2/runtime_v2/data_readiness.py:1332-1382`
- `src/ai_fund_lab_v2/runtime_v2/data_readiness.py:1513-1521`
- `src/ai_fund_lab_v2/runtime_v2/data_readiness.py:1549-1620`
- `src/ai_fund_lab_v2/runtime_v2/safety_decision.py:58-66`
- `config/runtime_tests/historical_smoke_5bd.json:26-44`

## Why Day1 and Day2 Passed

Day1 passed because its Pending safety authority was same-day and matched `2026-07-06`.

Day2 passed because its EMPTY/no-action Pending was generated for `2026-07-07` and consumed by same-day Data Readiness/Submit/Execution. Its `target_session_date` and `safety_context.safety_business_date` matched Day2.

Day2 did not need a Day3 Safety authority yet.

## Why Day3 Failed

Day3 failed because the fixed Pending slot still contained Day2 EMPTY/no-action evidence. EMPTY was valid as Pending terminal state, but its embedded Safety context remained Day2-scoped. Since no `safety_refresh` or equivalent Historical neutral Safety authority producer ran for `2026-07-08`, Data Readiness tried to reuse that Day2 Pending authority and correctly failed closed.

## Test Validity Assessment

The test is valid. It exposed a real Runtime continuity contract gap:

- no manual state edit occurred in the investigation,
- the stop is classified and reproducible from Run Evidence,
- Data Readiness did not weaken Safety,
- Pending stayed valid as Pending,
- Safety stayed fail-closed because same-day authority was missing.

The failure is not a performance issue and not a historical smoke-only nuisance. It is a Runtime authority lifecycle gap for no-action terminal days.

## Candidate Fixes Comparison

### 案A: EMPTY / active_pending=false Pendingは翌営業日のSafety authority候補から除外する

Assessment:

- Design consistency: Strong. EMPTY is terminal no-action state, not a next-day Safety SoT.
- SoT clarity: Strong if paired with a separate same-day Safety resolver.
- fail-closed: Strong. It must still fail when no same-day Safety authority exists.
- ACTIVE Pending impact: Low if limited strictly to EMPTY/non-active/items empty.
- Demo/Production impact: Conceptually safe; active Pending and explicit Safety remain unchanged.
- Historical-only risk: Medium unless expressed as common Pending lifecycle classification.
- Audit: Clear if evidence says previous EMPTY ignored as next-day safety source.
- Resume safety: Requires a fresh Day3 Safety source before resume can pass.
- Regression risk: Moderate; existing tests may rely on EMPTY Pending same-day authority only.

Conclusion: Good boundary, but insufficient alone. It prevents misleading reuse but does not create Day3 authority.

### 案B: 毎営業日のData Readinessで当日Historical neutral Safety authorityを新規生成する

Assessment:

- Design consistency: Strong for Historical replay if implemented as formal Historical environment capability, not as bypass.
- SoT clarity: Strong. Data Readiness becomes the generator/resolver of same-day Historical neutral authority when broker_write=false/external_delivery=false.
- fail-closed: Strong if it validates mode, broker environment, run id/profile/evidence root, business_date, no external effects, and required market/current/pending inputs.
- ACTIVE Pending impact: Low if active Pending still requires matching Pending/Approval/Safety context.
- Demo/Production impact: None if limited to historical environment composition; Production continues to require latest Safety Decision.
- Historical-only risk: Acceptable because Historical neutral authority is an environment capability replacing external Safety side effects, but it must be formalized.
- Audit: Strong if written into Data Readiness evidence with business_date and reason.
- Resume safety: High. Day3 can resume from data_readiness if same-day authority is generated during the gate.
- Regression risk: Low/moderate; must avoid granting submit/broker_write outside Historical replay.

Conclusion: Best correction boundary.

### 案C: runtime_state_refreshまたは前日terminal処理で翌営業日用Safety authorityを生成する

Assessment:

- Design consistency: Weak/medium. A job for Day2 should not predict Day3 Safety without Day3 market/current/feature context.
- SoT clarity: Medium; creates future-dated authority risk.
- fail-closed: Harder. Needs future business calendar and strict no-future-data guarantees.
- ACTIVE Pending impact: Medium; could accidentally carry authority across pending state changes.
- Demo/Production impact: Risky if generalized.
- Historical-only risk: High unless heavily scoped.
- Audit: Possible, but future-dated generation is awkward.
- Resume safety: Medium.
- Regression risk: High.

Conclusion: Not recommended.

### 案D: 前日のEMPTY Pending内Safety contextを翌営業日に持越し可能とする

Assessment:

- Design consistency: Weak. EMPTY Pending is terminal no-action evidence for its own target session.
- SoT clarity: Weak. It turns a prior-day no-action artifact into a new-day Safety authority.
- fail-closed: Weakens temporal authority unless many exceptions are added.
- ACTIVE Pending impact: Dangerous if generalized; must not apply to orders.
- Demo/Production impact: Risky conceptually.
- Historical-only risk: High.
- Audit: Ambiguous.
- Resume safety: Would pass too easily for the wrong reason.
- Regression risk: High.

Conclusion: Not recommended. This is close to simply relaxing business_date checks and should not be adopted.

## Recommended Correction Boundary

Recommended: combine A + B.

1. Treat EMPTY/non-active/no-action Pending from a previous session as valid terminal Pending but not as current-day Safety authority.
2. Introduce/centralize a formal Historical neutral Safety authority resolver for each business_date inside Data Readiness or a shared Safety authority helper.
3. Require:
   - `mode=historical`
   - `broker_environment=historical_simulated`
   - `broker_write=false`
   - `external_delivery=false`
   - runtime_test run/profile/evidence identity when present
   - business_date equality
   - no active Pending requiring prior approval/safety context unless that context matches
4. Keep ACTIVE Pending and APPROVED Pending fail-closed unless their own target_session_date and Safety context match.
5. Do not adopt Day2 EMPTY safety_context as Day3 authority.

This preserves Production/Demo safety semantics and gives Historical replay a per-day, auditable neutral Safety authority without relying on stale Pending context.

## Regression Risks

- Same-day EMPTY/no-action Submit and Execution must continue to PASS.
- ACTIVE Pending with mismatched target date must still stop.
- APPROVED Pending without matching Safety/Approval authority must still stop.
- Production missing Safety must still REVIEW_REQUIRED.
- Demo missing Safety must still REVIEW_REQUIRED.
- Historical external effects enabled must HALT/REVIEW_REQUIRED.
- Runtime test identity must remain evidence identity, not a trading permission by itself.
- Previous-day EMPTY Pending should not block Pending readiness, only Safety authority resolution.

## Resume Safety Assessment

Current run is halted at `2026-07-08:data_readiness`. Since this phase performs no fix, resume is not safe yet: the same `historical_safety_temporal_authority_missing` will recur.

After a future fix implementing the recommended boundary, resume may be safe from `2026-07-08:data_readiness` because Day3 market_refresh has already passed and the halted job did not mutate trading state. That future resume decision must re-check `.runtime` and Run Evidence at that time.

## Files Inspected

- `docs/02_architecture/runtime_architecture_v2.md`
- `docs/02_architecture/historical_runtime_test_contract.md`
- `docs/02_architecture/runtime_test_specification.md`
- `docs/02_architecture/runtime_temporal_freshness_contract.md`
- `docs/phase_reports/phase17_x_historical_sell_planning_temporal_authority_and_pending_pm_continuity_closure.md`
- `docs/phase_reports/phase17_ab_historical_current_valuation_pre_gate_authority_propagation_closure.md`
- `docs/phase_reports/phase17_ag_day2_sell_planning_integration_blocker_closure.md`
- `docs/phase_reports/phase17_bf_empty_pending_submit_contract_fix.md`
- `docs/phase_reports/phase17_bg_empty_no_action_execution_terminal_contract_fix.md`
- `docs/phase_reports/phase17_bh_current_valuation_refresh_temporal_contract_fix.md`
- `config/runtime_tests/historical_smoke_5bd.json`
- `src/ai_fund_lab_v2/runtime_v2/data_readiness.py`
- `src/ai_fund_lab_v2/runtime_v2/safety_decision.py`
- `src/ai_fund_lab_v2/runtime_v2/pending/reader.py`
- `src/ai_fund_lab_v2/runtime_v2/pending/lifecycle_runner.py`
- `reports/runtime_tests/runs/runtime-test-historical-smoke-20260715T111433056797Z/run_state.json`
- `reports/runtime_tests/runs/runtime-test-historical-smoke-20260715T111433056797Z/daily/2026-07-06/data_readiness/data_readiness.json`
- `reports/runtime_tests/runs/runtime-test-historical-smoke-20260715T111433056797Z/daily/2026-07-07/data_readiness/data_readiness.json`
- `reports/runtime_tests/runs/runtime-test-historical-smoke-20260715T111433056797Z/daily/2026-07-08/data_readiness/data_readiness.json`
- `.runtime/pending_order_plan/pending_order_plan.json`

## Commands Executed

Read-only commands only:

- `git status --short`
- `rg ...`
- `sed ...`
- `nl -ba ...`
- `python3 -m json.tool ...` against evidence files
- `python3 -c ...` for JSON field extraction

One read-only `json.tool` command for `.runtime/runtime_state/safety/latest_safety_decision.json` failed because the file does not exist; this confirmed `SAFETY_MISSING`.

## Prohibited Operations Confirmation

Not executed:

- code fix
- test addition
- `runtime_test.py run`
- `runtime_test.py resume`
- `runtime_test.py reset`
- `runtime_test.py rollback`
- `runtime_test.py backup`
- `runtime_test.py close`
- Frozen Run edit
- `.runtime` manual edit
- broker write
- external notification
- J-Quants fetch

## Final Judgment

`PHASE17_BI_ROOT_CAUSE_CONFIRMED`
