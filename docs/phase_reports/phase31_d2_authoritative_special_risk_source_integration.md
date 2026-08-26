# Phase31-D2 — Authoritative Special-Risk Source Integration

## PRIMARY_JUDGMENT

PHASE31_D2_AUTHORITATIVE_SOURCE_GAP_REMAINS

D2 did not integrate a new special-risk source. The repository does not currently contain an evidence-backed, complete, machine-consumable, PIT-reconstructable JPX / exchange source for the full special-risk family: alert / securities-on-alert, special caution / special treatment, listing review, and governance-related exchange restrictions.

Implementing an ad-hoc web scraper, manual list, symbol blacklist, or future-known delisting dataset would violate the D2 source authority contract. D0/D1 fail-closed semantics remain the active repair.

## AUTHORITATIVE_SOURCE

Current canonical owner remains:

- `ai_fund_lab_v2.strategy.corporate_event.build_symbol_event_coverage`
- `ai_fund_lab_v2.strategy.strategy_intelligence._event_uncertainty`
- Runtime defense-in-depth: `ai_fund_lab_v2.runtime_v2.market_status.buy_eligibility.evaluate_buy_eligibility`

Current source authority:

- J-Quants `listed_issues` / `/v2/equities/master` for ordinary listed membership and any explicit listed-row supervision/delisting/liquidation fields where present.

Missing source authority:

- complete JPX / exchange special-risk effective-state source for alert / special caution / governance / listing-review family.

## EXISTING REPOSITORY SOURCE INVENTORY

| Source / Path | Classification | Finding |
|---|---:|---|
| `scripts/fetch_jquants_daily.py` | CANONICAL_ACTIVE | Supports only `daily_quotes`, `listed_issues`, `earnings_calendar`, `trading_calendar`, `fins_summary`. |
| `src/ai_fund_lab_v2/data_sources/jquants/raw_ingestion.py` | CANONICAL_ACTIVE | `ENDPOINT_PATHS` has the same five J-Quants endpoints; no alert/special-caution/governance endpoint. |
| `src/ai_fund_lab_v2/data/jquants_fetch_policy.py` | CANONICAL_ACTIVE | Defines `/v2/equities/master`, bars, earnings calendar, market calendar, fins summary only. |
| `docs/03_operations/jquants_data_operations_runbook.md` | CANONICAL_ACTIVE | Source inventory lists the same five endpoints; TDnet/corporate_actions/fins_details are optional/not implemented. |
| `src/ai_fund_lab_v2/strategy/corporate_event.py` | CANONICAL_PARTIAL | Can materialize listed-issues-derived `DELISTING_PENDING`, `SUPERVISION_STATUS`, `LIQUIDATION_STATUS` where fields exist. |
| `.runtime/**/listed_issues` | PARTIAL | Existing runtime artifacts are listed-issues/master sources, not a complete special-risk universe. |
| JPX alert / special caution / governance adapter | NOT_AVAILABLE | No repository fetcher, schema, manifest, readiness integration, or PIT backfill path found. |
| Runtime `buy_eligibility.py` explicit fields | CANONICAL_DISCONNECTED_SCHEMA_SUPPORT | Can consume explicit `alert_status`, `special_caution_status`, `governance_risk_status`, `listing_review_status`, but no canonical source supplies them. |

## JQUANTS_SUFFICIENT

PARTIAL.

J-Quants is sufficient for ordinary listed membership and partial listed-row-derived status facts. It is not sufficient, from the repository's implemented API contract, for the complete JPX alert / securities-on-alert / special caution / governance-risk family.

## JPX_OR_EXTERNAL_SOURCE_REQUIRED

YES.

Full source closure requires an explicit exchange-level source or an equivalent authoritative vendor/source with:

- complete daily/effective-state designation universe,
- designation/effective/removal dates,
- Production refresh semantics,
- Historical PIT reconstruction,
- source manifest and Data Readiness lineage.

## PRODUCTION_SOURCE_AVAILABLE

PARTIAL.

Production can refresh existing J-Quants sources. It cannot currently refresh a complete exchange special-risk source.

## HISTORICAL_PIT_SOURCE_AVAILABLE

PARTIAL.

Historical listed-issues snapshots exist, but no complete special-risk backfill/source exists for the alert/special-caution/governance family.

## SOURCE_COMPLETENESS_PROVABLE

NO for the full required family.

YES only for the narrower supported Corporate Event coverage contract when `coverage_status = AVAILABLE`, `coverage_contract.event_absence_authorized = true`, and symbol-level `KNOWN_NO_EVENT` is present.

## NEGATIVE_EVIDENCE_SAFE

CONDITIONAL.

Safe only under the D1 contract:

```text
SOURCE_COMPLETE_FOR_DATE = true
+ symbol absent from active risk set
+ symbol_event_facts.<symbol>.event_status = KNOWN_NO_EVENT
+ source date == decision date
+ no conflict/stale/future fallback
= KNOWN_SAFE
```

If the source is partial/missing/stale/conflicting, absence from the risk list remains UNKNOWN, not SAFE.

## AUTHORITATIVE SOURCE DECISION MATRIX

| Risk Family | Authoritative Source | Production | Historical PIT | Completeness |
|---|---|---:|---:|---:|
| supervision | J-Quants listed-issues-derived field where present | PARTIAL | PARTIAL | PARTIAL |
| alert / securities on alert | no repo source | NO | NO | NO |
| special caution / special treatment | no repo source | NO | NO | NO |
| scheduled delisting | J-Quants listed-issues-derived field where present + Runtime listed status | PARTIAL | PARTIAL | PARTIAL |
| liquidation | J-Quants listed-issues-derived field where present | PARTIAL | PARTIAL | PARTIAL |
| listing review | explicit guard field support only; no source | NO/PARTIAL | NO/PARTIAL | NO |
| governance-related exchange restriction | explicit guard field support only; no source | NO | NO | NO |

## PRODUCTION_BUY_CONTINUITY

PARTIAL.

Known-safe can pass when supported complete canonical coverage exists. Full normal Production BUY continuity is not source-complete for all required special-risk families.

## HISTORICAL_BACKFILL_REQUIRED

YES for full source closure.

Required backfill definition:

- Source: authoritative JPX/exchange or equivalent licensed/vendor effective-state source for alert/special caution/listing review/governance restriction.
- Date range: at minimum the Historical validation range that includes Phase31 target windows, including 2022-08-10 and 61750 relevant BUY dates.
- Semantics: designation active from announcement/effective date until authoritative removal/resolution date; no later outcome backfill before public/effective date.
- Materialization path: source artifact -> manifest/readiness -> Corporate Event `symbol_event_facts` -> Strategy Intelligence.
- Integrity checks: source date <= business date, complete universe proof, no latest fallback, no conflict, schema validation, hash/source manifest identity.

No large backfill was executed in D2.

## DATA_READINESS_CONNECTED

NO for a new external special-risk source.

D0/D1 readiness semantics can consume source status once such a source exists, but D2 did not connect a new source.

## SOURCE_MANIFEST_CONNECTED

NO for a new external special-risk source.

Existing J-Quants manifest remains available for implemented endpoints only.

## 93180_CONTROL_STATUS

UNKNOWN.

For 2022-08-10, the repository still lacks contemporaneous canonical machine-consumable PIT evidence proving 93180's alert/special-risk state. Later delisting/outcome data was not used.

## 61750_CONTROL_STATUS

UNKNOWN.

The repository still lacks contemporaneous canonical machine-consumable PIT evidence proving 61750's special-risk state at the relevant BUY decision time. The 2022-12-16 delisting was not projected backward.

## KNOWN_SAFE_CONTROL_STATUS

PASS.

D1/D0 focused controls still prove `KNOWN_NO_EVENT` under complete canonical coverage can pass.

## D0_FAIL_CLOSED_ROLLBACK

NO.

## BUY_SELL_INDEPENDENCE

PASS.

## B10_LOGIC_CHANGED

NO.

## POSITION_SIZING_LOGIC_CHANGED

NO.

## ALPHA_RANKING_LOGIC_CHANGED

NO.

## C0_ALTERNATIVE_G_LOGIC_CHANGED

NO.

## FUTURE_INFORMATION_USED

NO.

## LONG_HISTORICAL_EXECUTED

NO.

## FOCUSED_TEST_RESULT

PASS:

```text
PYTHONPYCACHEPREFIX=/private/tmp/phase31_d2_pycache python3 -m pytest -q tests/strategy/test_phase31_d1_special_risk_source_coverage.py tests/strategy/test_phase31_d0_special_risk_eligibility.py tests/strategy/test_phase30_j_strategy_intelligence.py tests/strategy/test_phase30_l_strategy_intelligence_gap_repair.py tests/strategy/test_phase22_aa_corporate_event.py tests/runtime_v2/test_phase17_bv14_market_status_buy_eligibility_guard.py tests/strategy/test_phase31_b10_alternative_c_marginal_capital_priority.py
```

Result:

```text
58 passed in 4.64s
```

## COMPILE_RESULT

PASS:

```text
PYTHONPYCACHEPREFIX=/private/tmp/phase31_d2_pycache python3 -m py_compile src/ai_fund_lab_v2/strategy/strategy_intelligence.py src/ai_fund_lab_v2/strategy/special_risk_coverage_diagnostic.py src/ai_fund_lab_v2/runtime_v2/market_status/buy_eligibility.py tests/strategy/test_phase31_d1_special_risk_source_coverage.py tests/strategy/test_phase31_d0_special_risk_eligibility.py tests/strategy/test_phase30_j_strategy_intelligence.py
```

## GIT_DIFF_CHECK

PASS:

```text
git diff --check
```

## USER_ACTION_REQUIRED

YES.

One safe operator command to confirm the currently implemented J-Quants endpoint inventory without network writes:

```bash
AI_FUND_LAB_RAW_STORAGE_FORMAT=parquet python3 scripts/fetch_jquants_daily.py --endpoint all --from-date 2022-08-10 --to-date 2022-08-10 --dry-run
```

This does not solve the source gap; it only verifies that the current fetch plan still lacks a special-risk endpoint.

## CLEAN_FRESH_RUN_READY

NO for source-complete acceptance.

CONDITIONAL for validating D0/D1 mechanics only.

## FINAL QUESTIONS

1. 普通の銘柄を「risk情報が無い」ではなく、本当にKNOWN_SAFEと証明できるようになったか？
   CONDITIONAL. D1 semantics can prove this only when complete canonical coverage exists; D2 did not add the missing external complete source.

2. 93180の2022-08-10 special-risk状態をPITで証明できるか？
   NO. Current repository evidence remains UNKNOWN.

3. 61750のBUY時点の状態をPITで証明できるか？
   NO. Current repository evidence remains UNKNOWN.

4. sourceが不完全な場合、UNKNOWNをSAFEに戻していないか？
   YES. UNKNOWN remains REVIEW_REQUIRED; no fail-open rollback was added.

5. Production morningでsource completenessを確認できるか？
   PARTIAL. Existing J-Quants source completeness can be checked; missing exchange special-risk source completeness cannot because the source is not integrated.

6. Historicalで未来情報なしに同じauthorityを再構築できるか？
   PARTIAL. Existing listed-issues authority can be PIT; complete special-risk authority requires backfill/source integration.

7. clean fresh-runを開始してよい状態か？
   NO for source-complete acceptance. It is only conditional for mechanical regression after acknowledging the source gap.

## NEXT_TASK_RECOMMENDATION

authoritative source integration continuation.

Before Phase31-D3 or clean long validation, define and approve the missing exchange/vendor source contract for alert / securities-on-alert / special caution / listing review / governance restrictions, including license, fetch/materialization, historical PIT backfill, Data Readiness, and source manifest lineage.
