# Phase31-D1 — Authoritative Special-Risk Source Coverage / Production BUY Continuity Repair

## PRIMARY_JUDGMENT

PHASE31_D1_SPECIAL_RISK_SOURCE_AUTHORITY_GAP_REMAINS_WITH_CANONICAL_COVERAGE_CONSUMPTION_REPAIRED

D1 repaired the evidence-backed internal source consumption gap: Strategy Intelligence now consumes the canonical list-form `corporate_event.symbol_event_facts` emitted by `build_symbol_event_coverage`, materializes universe-level coverage, negative-evidence safety, stale/conflict states, and preserves D0 fail-closed BUY semantics.

The larger external authority gap remains: the repository still does not contain a complete machine-consumable authoritative JPX / exchange source for the full alert / special caution / governance-risk family. No fail-open rollback or invented source was added.

## REQUIRED_RISK_FAMILIES

| RISK_CONCEPT | CANONICAL_REQUIRED | CURRENT_SOURCE | CURRENT_FIELD | HISTORICAL_PIT_AVAILABLE | PRODUCTION_AVAILABLE | CURRENT_COVERAGE | ELIGIBILITY_IMPLICATION |
|---|---:|---|---|---:|---:|---|---|
| Current listed membership | YES | J-Quants listed issues / Runtime listed snapshot | `Code`, `Date`, listed presence, `current_listed` | YES/PARTIAL by stored snapshots | YES if refreshed | PARTIAL_ACTIVE | absent/not listed blocks new BUY |
| Supervision / supervisory status | YES where source exists | listed-issues-derived corporate events | `SupervisionStatus`, `supervision_status`, `SUPERVISION_STATUS` | PARTIAL | PARTIAL | PARTIAL_ACTIVE | REVIEW_REQUIRED / INELIGIBLE by guard contract |
| Scheduled delisting / delisting risk | YES | listed-issues-derived corporate events + Runtime market status | `DelistingStatus`, `FinalTradingDate`, `scheduled_delisting_date`, `DELISTING_PENDING` | PARTIAL | PARTIAL | PARTIAL_ACTIVE | REVIEW_REQUIRED / INELIGIBLE |
| Liquidation status | YES where source exists | listed-issues-derived corporate events | `LiquidationStatus`, `liquidation_status` | PARTIAL | PARTIAL | PARTIAL_ACTIVE | REVIEW_REQUIRED |
| Alert / securities on alert | YES where source exists | no canonical machine source found | none active | NO | NO | SOURCE_GAP | UNKNOWN -> REVIEW_REQUIRED |
| Special caution / special treatment | YES where source exists | no canonical machine source found | none active | NO | NO | SOURCE_GAP | UNKNOWN -> REVIEW_REQUIRED |
| Listing review | YES where source exists | Runtime guard can consume explicit field; no canonical source found | `listing_review_status` if supplied | NO/PARTIAL | NO/PARTIAL | DISCONNECTED_SCHEMA_SUPPORT | UNKNOWN -> REVIEW_REQUIRED |
| Governance-related exchange restriction | YES where source exists | Runtime guard can consume explicit field; no canonical source found | `governance_risk_status` if supplied | NO/PARTIAL | NO/PARTIAL | DISCONNECTED_SCHEMA_SUPPORT | UNKNOWN -> REVIEW_REQUIRED |
| Ordinary earnings/dividend/split CA | NO as special-risk eligibility | Corporate Event authority | event taxonomy | YES/PARTIAL | YES/PARTIAL | NOT_SPECIAL_RISK_GATE | not a company/listing trust exclusion by itself |

## CANONICAL_AUTHORITY_OWNER

- Source/coverage producer: `ai_fund_lab_v2.strategy.corporate_event.build_symbol_event_coverage`
- Per-symbol BUY eligibility consumer/materializer: `ai_fund_lab_v2.strategy.strategy_intelligence._event_uncertainty`
- Runtime defense-in-depth market-status guard: `ai_fund_lab_v2.runtime_v2.market_status.buy_eligibility.evaluate_buy_eligibility`

## AUTHORITATIVE_EXCHANGE_SOURCE_AVAILABLE

PARTIAL.

The existing repository can consume listed-issues-derived supervision, delisting, and liquidation facts when present. It does not contain a complete authoritative JPX alert / special caution / governance-risk source with historical PIT reconstruction and Production refresh semantics.

## SPECIAL_RISK_SOURCE_AVAILABLE

PARTIAL.

## SOURCE_COMPLETENESS_CONTRACT_DEFINED

YES.

`corporate_event.coverage_contract.event_absence_authorized = true` plus `coverage_status = AVAILABLE` means the source contract may support negative evidence for the supported risk family/date. If coverage is partial, missing, stale, conflicting, or date-mismatched, symbol absence does not imply normal.

## NEGATIVE_EVIDENCE_SAFE_TO_USE

CONDITIONAL.

Safe only when all are true:

- `corporate_event.coverage_status = AVAILABLE`
- `coverage_contract.event_absence_authorized = true`
- `symbol_event_facts.<symbol>.event_status = KNOWN_NO_EVENT`
- `symbol_event_facts.<symbol>.coverage_status = AVAILABLE`
- source business date equals Strategy Intelligence business date
- no source conflict reason/status exists
- no future leakage flag/date mismatch exists

## UNIVERSE_LEVEL_COVERAGE_IMPLEMENTED

YES.

Strategy Intelligence now exposes `universe_coverage_state`:

- `KNOWN_COMPLETE`
- `KNOWN_PARTIAL`
- `UNKNOWN`
- `STALE`

## SYMBOL_LEVEL_RISK_STATE_IMPLEMENTED

YES.

Strategy Intelligence now consumes canonical list-form `symbol_event_facts` and exposes:

- `coverage_state`
- `risk_state`
- `eligibility_implication`
- `negative_evidence_safe_to_use`

## KNOWN_SAFE_PROOF

Complete universe coverage plus per-symbol `KNOWN_NO_EVENT` supports:

- `coverage_state = KNOWN`
- `universe_coverage_state = KNOWN_COMPLETE`
- `risk_state = NORMAL`
- `eligibility_implication = BUY_ALLOWED`
- `eligibility.status = PASS`

## KNOWN_RISK_PROOF

Per-symbol canonical `event_types` or `event_facts` containing supported special-risk families such as `SUPERVISION_STATUS` or `DELISTING_PENDING` supports:

- `state = SPECIAL_RISK_PRESENT`
- `risk_state = REVIEW_REQUIRED`
- `eligibility.status = REVIEW_REQUIRED`

## UNKNOWN_PROOF

Partial/missing/stale/conflicting source coverage produces:

- `coverage_state = UNKNOWN`, `STALE`, or `CONFLICT`
- `risk_state = UNKNOWN`
- `eligibility_implication = REVIEW_REQUIRED`
- `eligibility.status = REVIEW_REQUIRED`

## KNOWN_SAFE_CAN_PASS

YES.

## KNOWN_RISK_CAN_NORMAL_BUY

NO.

## UNKNOWN_CAN_NORMAL_BUY

NO.

## D0_FAIL_CLOSED_SEMANTICS_PRESERVED

YES.

## D0_FAIL_CLOSED_ROLLBACK

NO.

## NORMAL_PRODUCTION_BUY_CONTINUITY_AFTER_D1

CONDITIONAL.

Known-safe securities can proceed when the canonical source proves complete coverage for the supported family/date. Production continuity remains conditional because full JPX alert / special caution / governance-risk source coverage is not yet implemented.

## PRODUCTION_BUY_CONTINUITY

PARTIAL.

## COVERAGE DIAGNOSTIC

Added read-only diagnostic:

```text
python3 -m ai_fund_lab_v2.strategy.special_risk_coverage_diagnostic <strategy_intelligence_artifact>
```

It prints:

```text
DATE        TOTAL_SYMBOLS KNOWN_SAFE KNOWN_RISK UNKNOWN PARTIAL STALE COVERAGE_RATE
```

This is not a business authority. It only reads canonical Strategy Intelligence evidence.

## TOTAL_SYMBOLS_CHECKED

11 focused synthetic/canonical fixture rows.

## KNOWN_SAFE_COUNT

3.

## KNOWN_RISK_COUNT

1.

## UNKNOWN_COUNT

4.

## PARTIAL_COUNT

1.

## STALE_COUNT

2.

## COVERAGE_RATE

36.36% across the focused D1 fixture scenarios.

No existing checked-in `strategy_intelligence.json` or `corporate_event.json` run artifact was found with `rg --files`; no fresh Historical run was executed.

## STRATEGY_RUNTIME_ELIGIBILITY_CONSISTENCY

PASS/PARTIAL.

PASS for shared semantics: known-safe can pass; known-risk/unknown/stale/future/conflict cannot silently become normal BUY. PARTIAL because Runtime market-status guard can only consume explicit special-risk fields supplied to it; full source provenance still originates upstream in Corporate Event / Strategy Intelligence.

## SPECIAL_RISK_ELIGIBILITY_BYPASS_COUNT

0 found in focused active BUY path.

## ACTIVE_FAIL_OPEN_FALLBACK_COUNT

0 found for the repaired Strategy Intelligence special-risk authority path.

## BUY_AUTHORITY_OUTAGE_SELL_CONTINUATION

PASS.

Focused test proves source outage/unknown BUY authority preserves EXIT context and current action.

## BUY_NEW_GUARD

PASS.

## BUY_ADD_GUARD

PASS.

## SELL_INDEPENDENCE_PRESERVED

YES.

## B10_LOGIC_CHANGED

NO.

## POSITION_SIZING_LOGIC_CHANGED

NO.

## ALPHA_RANKING_LOGIC_CHANGED

NO.

## C0_ALTERNATIVE_G_LOGIC_CHANGED

NO.

## SYMBOL_SPECIFIC_RULE_COUNT

0.

## NATIONALITY_BASED_RULE_ADDED

NO.

## FUNDAMENTAL_QUALITY_FILTER_ADDED

NO.

## HISTORICAL_PIT_SAFE

PARTIAL.

The implemented consumer semantics are PIT-safe: source dates must align and future-dated source artifacts do not become safe evidence. Historical PIT reconstruction remains partial because the complete authoritative external exchange source for alert/special-caution/governance risk is not present.

## HISTORICAL_SPECIAL_RISK_BACKFILL_REQUIRED

PARTIAL/YES for full clean validation.

Historical validation that wants complete alert / special caution / governance-risk authority needs a PIT-safe backfill or archived effective-state source. D1 did not perform a backfill.

## PRODUCTION_SPECIAL_RISK_REFRESH_REQUIRED

YES for full source closure.

The refresh should be owned by existing source/materialization or Data Readiness infrastructure, not by ad-hoc Runtime web lookup.

## DATA_READINESS_INTEGRATION

Recommended ownership:

- Data Readiness: universe-level source readiness, date alignment, freshness, completeness, source conflict, fallback usage.
- Corporate Event: canonical per-symbol event/status materialization.
- Strategy Intelligence eligibility: per-symbol BUY implication.
- Runtime/Pending/Submit: defense-in-depth, not primary discovery when precomputable.

D1 did not add a new readiness scheduler.

## SOURCE_MANIFEST_LINEAGE_IMPLEMENTED

PARTIAL.

The canonical artifact lineage is consumed and surfaced from Strategy Intelligence. A complete new external source manifest was not implemented because no authoritative source contract was available in repo.

## LATEST_FALLBACK_USED

NO for D1 decision authority.

## PREVIOUS_DAY_COPY_USED

NO.

No blind carry-forward was implemented.

## FUTURE_INFORMATION_USED

NO.

## 93180_CONTROL_STATUS

UNKNOWN.

From contemporaneous canonical machine-consumable repository evidence, D1 still cannot prove 2022-08-10 alert/special-risk status for 93180. Public context remains a source-gap indicator, not a backfilled production authority.

## 61750_CONTROL_STATUS

UNKNOWN.

From contemporaneous canonical machine-consumable repository evidence, D1 still cannot prove pre-decision supervisory / alert / delisting-risk state for 61750 without an external PIT authority source.

## KNOWN_SAFE_CONTROL_STATUS

PASS.

Complete coverage plus `KNOWN_NO_EVENT` passes.

## GOVERNANCE_RISK_AUTHORITY

UNAVAILABLE.

Runtime guard can consume explicit `governance_risk_status` if supplied, but no canonical machine-consumable source was found.

## SOURCE_CONFLICT_POLICY

Source conflict is not permissive. Any `CONFLICT` source status or reason produces typed review evidence:

- `coverage_state = CONFLICT`
- `missing_inputs = conflicting_event_coverage_authority`
- `eligibility.status = REVIEW_REQUIRED`

## EARLIEST_PRECOMPUTABLE_CONSUMER

Strategy Intelligence eligibility, fed by Corporate Event coverage.

Downstream PC/Planning/Pending/Submit are defense-in-depth or consumers of canonical eligibility, not primary source discovery.

## PRODUCTION_COMMON_IMPLEMENTATION

YES.

## HISTORICAL_ONLY_RULE_ADDED

NO.

## C0F_VALIDATION_RUN_MUST_BE_POST_D1

YES.

D0/D1 change BUY eligibility and therefore future composition. C0F validation should be generated only after D1 closure and any accepted source-authority decision.

## FOCUSED_TEST_RESULT

PASS:

```text
PYTHONPYCACHEPREFIX=/private/tmp/phase31_d1_pycache python3 -m pytest -q tests/strategy/test_phase31_d1_special_risk_source_coverage.py tests/strategy/test_phase31_d0_special_risk_eligibility.py tests/strategy/test_phase30_j_strategy_intelligence.py tests/strategy/test_phase30_l_strategy_intelligence_gap_repair.py tests/strategy/test_phase22_aa_corporate_event.py tests/runtime_v2/test_phase17_bv14_market_status_buy_eligibility_guard.py tests/strategy/test_phase31_b10_alternative_c_marginal_capital_priority.py
```

Result:

```text
58 passed in 1.78s
```

## D0_REGRESSION_RESULT

Included in the focused test command above:

- `tests/strategy/test_phase31_d0_special_risk_eligibility.py`
- D0 semantics remained green.

## COMPILE_RESULT

PASS:

```text
PYTHONPYCACHEPREFIX=/private/tmp/phase31_d1_pycache python3 -m py_compile src/ai_fund_lab_v2/strategy/strategy_intelligence.py src/ai_fund_lab_v2/strategy/special_risk_coverage_diagnostic.py src/ai_fund_lab_v2/runtime_v2/market_status/buy_eligibility.py tests/strategy/test_phase31_d1_special_risk_source_coverage.py tests/strategy/test_phase31_d0_special_risk_eligibility.py tests/strategy/test_phase30_j_strategy_intelligence.py
```

## GIT_DIFF_CHECK

PASS:

```text
git diff --check
```

## LONG_HISTORICAL_EXECUTED

NO.

## USER_RUN_READY

CONDITIONAL.

The code is focused-test ready. A clean long validation run should wait until the user accepts the remaining source-authority status or schedules an external authoritative source/backfill task.

## FINAL QUESTIONS

1. Can the system now prove that an ordinary security is KNOWN SAFE rather than merely "no risk data found"?
   CONDITIONAL. Yes only when complete universe coverage and `KNOWN_NO_EVENT` are present.

2. Can the system distinguish KNOWN SAFE, KNOWN SPECIAL RISK, and UNKNOWN / PARTIAL COVERAGE with typed evidence?
   YES for the canonical supported artifact states; PARTIAL for full external JPX family coverage.

3. Is absence from the special-risk source allowed to imply SAFE?
   CONDITIONAL. Only when `SOURCE_COMPLETE_FOR_DATE = true` through `coverage_status = AVAILABLE`, `event_absence_authorized = true`, date alignment, no conflict, and per-symbol `KNOWN_NO_EVENT`.

4. Can a known-safe security still proceed through normal BUY_NEW?
   YES.

5. Can a known-safe held security still proceed through normal BUY_ADD?
   YES, subject to ordinary ADD/PC/PS rules.

6. Can a known-risk security proceed through normal BUY_NEW or BUY_ADD?
   NO.

7. Can an UNKNOWN / PARTIAL security proceed through normal BUY_NEW or BUY_ADD?
   NO.

8. If special-risk BUY authority is unavailable for the morning, can valid REDUCE / EXIT still proceed?
   YES.

9. Did D1 weaken D0 fail-closed semantics in order to preserve BUY volume?
   NO.

10. Did D1 add any nationality, foreign-company, low-price, profitability, or fundamental-quality exclusion?
    NO.

11. Did D1 use future-known delisting or later company outcomes to classify Historical eligibility?
    NO.

12. Is the current source coverage sufficient for normal Production BUY continuity?
    CONDITIONAL/PARTIAL. It is sufficient only for supported complete `corporate_event` coverage. It is not sufficient for the full alert / special caution / governance-risk family.

13. Does Historical require a special-risk authority backfill before clean long validation?
    PARTIAL/YES for full source closure.

14. Does Production require a new/refined morning special-risk refresh?
    YES for full source closure.

15. Must the previously planned C0F validation run be generated only after D1 closes?
    YES.

16. Is a new Historical fresh-run appropriate immediately after D1?
    CONDITIONAL. It can validate D0/D1 mechanics, but it cannot prove full special-risk source completeness until the external source/backfill gap is resolved.

17. If not, what exact source/authority blocker remains?
    No complete authoritative machine-consumable JPX/exchange source is connected for historical and Production alert / special caution / governance-risk effective-state coverage.

18. What should Phase31-D2 be if D1 succeeds?
    Phase31-D2 existing-holding special-risk lifecycle audit.

## NEXT_TASK_RECOMMENDATION

authoritative source integration task.

Define and connect a complete PIT-safe exchange special-risk source covering alert / special caution / governance-risk effective states, with Data Readiness and source manifest lineage, before a clean long validation run is used for acceptance.
