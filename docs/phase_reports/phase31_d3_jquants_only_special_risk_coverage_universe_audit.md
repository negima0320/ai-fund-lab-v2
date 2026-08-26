# Phase31-D3 — J-Quants-Only Special-Risk Coverage Universe Audit

## PRIMARY_JUDGMENT

PHASE31_D3_SPECIAL_RISK_UNKNOWN_COVERAGE_MATERIAL_IMPACT

D3 used the current J-Quants + D0/D1 canonical special-risk authority only. No implementation, eligibility change, D0/D1 rollback, JPX/external source integration, fresh-run, resume, replay, or long Historical execution was performed.

The representative real Universe artifact shows `UNKNOWN_COUNT = 0`, but `PARTIAL_COUNT = 4,437 / 4,437 = 100.00%`. Candidate coverage is also `PARTIAL = 50 / 50 = 100.00%`. Under D0/D1 semantics, PARTIAL is not SAFE and would become review/block for normal new BUY authority. This is material impact for BUY continuity.

## TARGET_RUN_OR_ARTIFACT

`.runtime/strategy_artifacts/corporate_event/2026-07-06/corporate_event.json`

Selected because it is an existing real `corporate_event` artifact with `symbol_event_facts` for the listed universe and matching existing `candidate_decisions.json` / `opportunity_rankings.json` for the same date.

Nearby artifacts:

- `2026-07-14`: `symbol_event_facts = 0`, not useful for Universe count.
- `2026-07-15`: `symbol_event_facts = 0`, not useful for Universe count.

## TARGET_DATE

2026-07-06

## SOURCE STATUS

`corporate_event` source status:

- `producer_result_status = REVIEW_REQUIRED`
- `coverage_status = PARTIAL`
- `source_coverage_semantics = PARTIAL`
- `coverage_contract.event_absence_authorized = false`
- `reason_codes = ["corporate_event_source_coverage_incomplete", "future_earnings_calendar_row_rejected", "jquants_corporate_actions_not_implemented_or_missing"]`

`source_coverage` showed implemented/available J-Quants listed issues, trading calendar, earnings calendar, and fins summary. Missing source coverage was:

- `jquants_corporate_actions_not_implemented_or_missing`

## UNIVERSE COVERAGE COUNT

| Metric | Count | Rate |
|---|---:|---:|
| TOTAL_SYMBOLS | 4,437 | 100.00% |
| KNOWN_SAFE_COUNT | 0 | 0.00% |
| KNOWN_RISK_COUNT | 0 | 0.00% |
| UNKNOWN_COUNT | 0 | 0.00% |
| PARTIAL_COUNT | 4,437 | 100.00% |
| STALE_COUNT | 0 | 0.00% |
| COVERAGE_RATE | 0 | 0.00% |
| UNKNOWN_RATE | 0 | 0.00% |
| PARTIAL_OR_UNKNOWN_RATE | 4,437 | 100.00% |

`COVERAGE_RATE = (KNOWN_SAFE + KNOWN_RISK) / TOTAL_SYMBOLS`.

## BUY-RELEVANT COVERAGE

Candidate artifact:

`.runtime/runtime_state/buy_ai/2026-07-06/candidate_decisions.json`

Opportunity artifact:

`.runtime/runtime_state/buy_ai/2026-07-06/opportunity_rankings.json`

| Metric | Count | Rate |
|---|---:|---:|
| TOTAL_CANDIDATE_SYMBOLS | 50 | 100.00% |
| KNOWN_SAFE_CANDIDATE_COUNT | 0 | 0.00% |
| KNOWN_RISK_CANDIDATE_COUNT | 0 | 0.00% |
| UNKNOWN_CANDIDATE_COUNT | 0 | 0.00% |
| PARTIAL_CANDIDATE_COUNT | 50 | 100.00% |
| UNKNOWN_CANDIDATE_RATE | 0 | 0.00% |
| PARTIAL_OR_UNKNOWN_CANDIDATE_RATE | 50 | 100.00% |

Opportunity symbols matched the same count:

- `TOTAL_OPPORTUNITY_SYMBOLS = 50`
- `PARTIAL_OPPORTUNITY_COUNT = 50`
- `PARTIAL_OR_UNKNOWN_OPPORTUNITY_RATE = 100.00%`

Actual BUY_NEW / BUY_ADD PC or Runtime Planning artifacts were not present for 2026-07-06, so D3 does not separately claim BUY_NEW vs BUY_ADD realized counts for this target date.

## OPERATIONAL IMPACT ESTIMATE

Candidate Universe emphasis:

- `BUY_BLOCK_OR_REVIEW_SYMBOL_COUNT = 50`
- `BUY_BLOCK_OR_REVIEW_RATE = 100.00%`

Universe-wide:

- `UNIVERSE_REVIEW_SYMBOL_COUNT = 4,437`
- `UNIVERSE_REVIEW_RATE = 100.00%`

Reason: all symbols are PARTIAL under the D0/D1 canonical authority, and PARTIAL must not be converted to SAFE.

## UNKNOWN_BY_CAUSE

Strict UNKNOWN count is zero.

Because the observed issue is PARTIAL rather than UNKNOWN, the applicable cause breakdown is:

| Cause | Count |
|---|---:|
| universe coverage partial: `jquants_corporate_actions_not_implemented_or_missing` | 4,411 |
| universe coverage partial with non-special event only | 26 |

The 26 known-event rows were ordinary non-special-risk events, mainly earnings/financial statement disclosure facts; they do not prove special-risk safety because universe-level special-risk absence was not authorized.

## UNKNOWN_SYMBOLS

No strict UNKNOWN symbols.

PARTIAL is too large to list fully. Representative PARTIAL examples:

- `13010`
- `13050`
- `13060`
- `13080`
- `13090`
- `130A0`
- `13110`
- `13190`
- `131A0`
- `13200`
- `13210`
- `13220`
- `186A0`
- `19420`
- `195A0`
- `23000`
- `25930`
- `27890`
- `31600`
- `31860`
- `32220`
- `33210`
- `39970`
- `42380`

Representative candidate symbols affected:

- `186A0`
- `218A0`
- `23450`
- `23880`
- `278A0`
- `285A0`
- `31330`
- `34360`
- `34440`
- `38250`
- `41790`
- `43780`
- `45640`
- `45960`
- `45970`
- `460A0`
- `462A0`
- `48330`
- `485A0`
- `50160`

## 93180_STATUS

UNRESOLVED.

`93180` is not present in the 2026-07-06 target Universe artifact, candidate artifact, or opportunity artifact. No 2022-08-10 `corporate_event` artifact was found in existing runtime artifacts. D3 did not use future delisting/outcome data.

## 61750_STATUS

UNRESOLVED.

`61750` is not present in the 2026-07-06 target Universe artifact, candidate artifact, or opportunity artifact. No relevant historical PIT `corporate_event` artifact was found in existing runtime artifacts. D3 did not use the 2022-12-16 delisting as backfilled evidence.

## D0_D1_SEMANTICS_CHANGED

NO.

## JPX_SOURCE_USED

NO.

## FUTURE_INFORMATION_USED

NO.

## LONG_HISTORICAL_EXECUTED

NO.

## COMMANDS RUN

Read-only artifact inspection and aggregation only. No canonical artifact was modified.

Key focused aggregation was run against:

```text
.runtime/strategy_artifacts/corporate_event/2026-07-06/corporate_event.json
.runtime/runtime_state/buy_ai/2026-07-06/candidate_decisions.json
.runtime/runtime_state/buy_ai/2026-07-06/opportunity_rankings.json
```

## RECOMMENDATION

J-Quants-only gate scope redesign required.

Under the current D0/D1 scope, J-Quants-only evidence leaves the real 2026-07-06 Universe and Candidate Universe at 100% PARTIAL. Continuing with UNKNOWN/PARTIAL as REVIEW_REQUIRED is semantically correct but would materially impair normal BUY continuity. D3 does not recommend converting PARTIAL to SAFE; it recommends a focused design decision on whether the required special-risk family can be narrowed under J-Quants-only SoT, or whether external source integration remains necessary before clean validation.

## FINAL QUESTIONS

1. 全Universe中UNKNOWNは何件・何%か？
   0件、0.00%。ただし PARTIAL は4,437件、100.00%。

2. Candidate Universe中UNKNOWNは何件・何%か？
   0件、0.00%。ただし PARTIAL は50件、100.00%。

3. BUY continuityへ実質的な影響は小さいか大きいか？
   大きい。Candidate/Opportunity Universeの100%がPARTIALで、D0/D1後はnormal BUYへ進めない可能性がある。

4. UNKNOWNが少数なら、そのままREVIEW_REQUIRED除外で問題なさそうか？
   今回はUNKNOWNではなくPARTIALが全件なので、単純な少数除外では済まない。

5. JPXなし・J-Quantsのみで次のclean validationへ進めそうか？
   Source-complete acceptance目的ではNO。D0/D1 mechanics確認目的ならCONDITIONALだが、BUY continuity評価としてはJ-Quants-only gate scope redesignが必要。
