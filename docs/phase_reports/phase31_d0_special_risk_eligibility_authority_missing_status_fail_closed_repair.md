# Phase31-D0 — Special-Risk Eligibility Authority / Missing-Status Fail-Closed Repair

## PRIMARY_JUDGMENT

PHASE31_D0_SPECIAL_RISK_ELIGIBILITY_AUTHORITY_FAIL_CLOSED_REPAIR_COMPLETE

## ROOT_CAUSE

MISSING_SPECIAL_RISK_AUTHORITY + MISSING_STATUS_FAIL_OPEN.

A9's failing condition was reproduced as a family-wide contract defect: required special-risk event coverage could be `symbol_coverage_status = UNKNOWN` while Strategy Intelligence still emitted `eligibility.status = PASS`. That allowed ordinary listed eligibility to stand in for missing supervisory / alert / caution / governance / delisting-risk authority.

## CANONICAL_AUTHORITY_OWNER

Production-common owner:

- `ai_fund_lab_v2.strategy.corporate_event.build_symbol_event_coverage`
- consumed and normalized by `ai_fund_lab_v2.strategy.strategy_intelligence._event_uncertainty`
- exposed to BUY consumers through `strategy_intelligence.symbol_intelligence.<symbol>.eligibility.special_risk_authority`

Runtime market-status guard support:

- `ai_fund_lab_v2.runtime_v2.market_status.buy_eligibility.evaluate_buy_eligibility`

This keeps the authority in the existing market-status / corporate-event / Strategy Intelligence eligibility family instead of adding a duplicate symbol blacklist or ranking rule.

## SOURCE DISCOVERY

| Path | Classification | Notes |
|---|---:|---|
| `src/ai_fund_lab_v2/strategy/corporate_event.py` | CANONICAL/PARTIAL | Builds PIT symbol event coverage; extracts `DELISTING_PENDING`, `SUPERVISION_STATUS`, and `LIQUIDATION_STATUS` from listed rows where present. |
| `corporate_event.symbol_event_facts` | CANONICAL | Per-symbol business-date coverage/status artifact consumed by Strategy Intelligence. |
| `src/ai_fund_lab_v2/runtime_v2/market_status/buy_eligibility.py` | CANONICAL | Runtime BUY listed/status eligibility guard; now also consumes explicit special-risk coverage/risk fields when supplied. |
| J-Quants listed issues fields | PARTIAL | Supports ordinary listed status and some listed-row supervision/delisting fields when present. Does not prove full JPX alert / special caution / governance-risk family coverage. |
| Candidate/feature catalog supervision and delisting flags | LEGACY/PARTIAL | Design-level feature concepts, not sufficient as D0 runtime authority by themselves. |
| B10 marginal capital value authority | UNUSED for eligibility | Orders already-eligible incremental capital; not an eligibility source. |

## SPECIAL_RISK_SOURCE_AVAILABLE

PARTIAL.

The current foundation can materialize some PIT special-risk evidence through `corporate_event` and listed-issues-derived event facts, but it does not prove complete authoritative historical coverage for the full JPX alert / special caution / governance-risk family. D0 therefore implements evidence-backed typed coverage semantics and fail-closed consumption of unknown coverage instead of fabricating `NORMAL`.

## SPECIAL_RISK_SOURCE

`corporate_event.symbol_event_facts.<symbol>` with:

- `coverage_status`
- `event_status`
- `event_facts`
- `business_date`

Explicit listed/status fields supplied to `evaluate_buy_eligibility` are also consumed:

- `special_risk_coverage_state`
- `special_risk_state`
- `special_risk_eligibility`
- `special_risk_status`
- `alert_status`
- `special_caution_status`
- `governance_risk_status`
- `listing_review_status`

## PIT_MATERIALIZATION_IMPLEMENTED

YES.

The Strategy Intelligence evidence records the canonical producer/artifact/field and temporal binding:

`corporate_event.business_date <= strategy_intelligence.business_date; no future event facts consumed`

The Runtime market-status guard now rejects authority dated after `business_date` as `market_status_future_authority_rejected` without setting `future_authority_used`.

## COVERAGE_STATE_TYPED

YES.

Strategy Intelligence now materializes:

- `coverage_state = KNOWN`
- `coverage_state = UNKNOWN`

Runtime market-status guard now materializes:

- `special_risk_coverage_state`

## RISK_STATE_TYPED

YES.

Strategy Intelligence now materializes:

- `risk_state = NORMAL`
- `risk_state = UNKNOWN`
- `risk_state = REVIEW_REQUIRED`

Runtime market-status guard now materializes:

- `special_risk_state`
- `special_risk_eligibility`

## CANONICAL ELIGIBILITY SEMANTICS

| State | D0 behavior |
|---|---|
| Known safe coverage, no facts | `eligibility.status = PASS`, `eligibility_implication = BUY_ALLOWED` |
| Known special-risk fact | `eligibility.status = REVIEW_REQUIRED`, no normal BUY admission |
| Unknown/missing/partial coverage | `eligibility.status = REVIEW_REQUIRED`, no silent executable BUY |
| Future-dated authority | `REVIEW_REQUIRED`, authority rejected as non-PIT |

## UNKNOWN_COVERAGE_CAN_PASS

NO.

`EVENT_COVERAGE_INCOMPLETE` is no longer removed from blocking review facts. It now makes Strategy Intelligence eligibility `REVIEW_REQUIRED`.

## KNOWN_SAFE_CAN_PASS

YES.

Focused known-safe control passes with authoritative coverage and normal risk state.

## KNOWN_RISK_BUY_NEW_BLOCKED_OR_REVIEWED

YES.

Known `SUPERVISION_STATUS` event facts produce `SPECIAL_RISK_PRESENT` and `eligibility.status = REVIEW_REQUIRED`.

## KNOWN_RISK_BUY_ADD_BLOCKED_OR_REVIEWED

YES.

For held ADD context, the same Strategy Intelligence eligibility authority makes `entry_admission.lifecycle_intent = BUY_ADD` and `admission_action = REVIEW_REQUIRED`, not `ADD_ALLOWED`.

## SELL_INDEPENDENCE_PRESERVED

YES.

PM REDUCE / EXIT interpretation precedence is preserved even when BUY eligibility is `REVIEW_REQUIRED`. D0 does not add forced liquidation and does not block SELL authority.

## NORMAL_PRODUCTION_BUY_CONTINUITY_AFTER_D0

CONDITIONAL.

Normal BUY continuity is preserved when canonical per-symbol special-risk coverage is materialized as known safe. If production source coverage is unknown or partial for a required special-risk family, D0 intentionally converts that to review instead of SAFE. This is the expected fail-closed operational implication of the current SoT.

## STRATEGY_INTELLIGENCE_UNKNOWN_PLUS_PASS_ELIMINATED

YES.

The repaired path eliminates:

`symbol_coverage_status = UNKNOWN` + `eligibility.status = PASS`

for required special-risk authority.

## SPECIAL_RISK_ELIGIBILITY_BYPASS_COUNT

0 found in the focused active BUY path.

Evidence:

- Strategy Intelligence emits `eligibility.status != PASS`.
- Portfolio Construction consumes `strategy_intelligence_eligibility_not_pass` for non-current-position BUY membership.
- Entry Admission blocks BUY_NEW / BUY_ADD admission with `REVIEW_REQUIRED`.
- Runtime market-status guard and Submit guard continue to evaluate BUY market-status eligibility.
- B10 only orders eligible incremental capital and was not changed.

## B10_LOGIC_CHANGED

NO.

No marginal-capital priority formula or ordering code was modified.

## POSITION_SIZING_LOGIC_CHANGED

NO.

No lot, cap, low-price, residual reallocation, Strategy cap, Safety cap, or liquidity capacity logic was modified.

## ALPHA_RANKING_LOGIC_CHANGED

NO.

No Candidate score, Expected Edge, BUY Quality score, momentum, trend, rank, or regime scoring logic was modified.

## PRODUCTION_COMMON_IMPLEMENTATION

YES.

Changes are in common Strategy Intelligence and Runtime market-status BUY eligibility modules. No Historical-only rule was added.

## HISTORICAL_ONLY_RULE_ADDED

NO.

## SYMBOL_SPECIFIC_BLACKLIST_ADDED

NO.

No 93180 or 61750 production rule was added.

## FUTURE_INFORMATION_USED

NO.

Future-dated Runtime market-status authority is rejected, and Strategy Intelligence evidence carries `future_information_used = False`.

## FILES CHANGED

- `src/ai_fund_lab_v2/strategy/strategy_intelligence.py`
- `src/ai_fund_lab_v2/runtime_v2/market_status/buy_eligibility.py`
- `tests/strategy/test_phase31_d0_special_risk_eligibility.py`
- `tests/strategy/test_phase30_j_strategy_intelligence.py`

## FOCUSED_TEST_RESULT

PASS:

```text
PYTHONPYCACHEPREFIX=/private/tmp/phase31_d0_pycache python3 -m pytest -q tests/strategy/test_phase31_d0_special_risk_eligibility.py tests/strategy/test_phase30_j_strategy_intelligence.py tests/strategy/test_phase30_l_strategy_intelligence_gap_repair.py tests/runtime_v2/test_phase17_bv14_market_status_buy_eligibility_guard.py tests/strategy/test_phase31_b10_alternative_c_marginal_capital_priority.py
```

Result:

```text
30 passed in 1.73s
```

## COMPILE_RESULT

PASS:

```text
PYTHONPYCACHEPREFIX=/private/tmp/phase31_d0_pycache python3 -m py_compile src/ai_fund_lab_v2/runtime_v2/market_status/buy_eligibility.py src/ai_fund_lab_v2/strategy/strategy_intelligence.py tests/strategy/test_phase31_d0_special_risk_eligibility.py tests/strategy/test_phase30_j_strategy_intelligence.py
```

## GIT_DIFF_CHECK

PASS:

```text
git diff --check
```

## LONG_HISTORICAL_EXECUTED

NO.

No fresh-run, resume, replay, or long Historical execution was run.

## USER_RUN_READY

YES.

## FINAL QUESTIONS

1. Did D0 eliminate `symbol_coverage_status = UNKNOWN` + `eligibility.status = PASS` for required special-risk authority?
   YES.

2. Can a properly covered normal security still BUY normally?
   YES.

3. Can a known special-risk security enter normal BUY_NEW?
   NO.

4. Can it enter normal BUY_ADD?
   NO.

5. If special-risk coverage is unknown, can the system silently treat it as SAFE?
   NO.

6. Does blocking/reviewing BUY still allow valid REDUCE / EXIT?
   YES.

7. Did D0 change B10 capital-priority behavior?
   NO.

8. Did D0 change position sizing because 93180 had 8300 shares?
   NO.

9. Did D0 add any symbol-specific rule for 93180 or 61750?
   NO.

10. Is the repair Production-common and PIT-safe?
    YES.

11. Is a fresh user-operated validation run appropriate after D0?
    YES.

## NEXT_TASK_RECOMMENDATION

Phase31-D1 focused authority/source repair continuation.

Reason: D0 correctly stops missing special-risk coverage from becoming SAFE, but source availability remains PARTIAL. D1 should decide whether to add or connect an authoritative JPX alert / special caution / governance-risk source so normal production BUY continuity does not depend on unknown coverage being reviewed.
