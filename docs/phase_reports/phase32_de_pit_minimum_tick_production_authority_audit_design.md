# Phase32-DE - PIT Minimum-Tick Production Authority Audit / Design

## Scope

This is a READ-ONLY / DESIGN audit for the Production-grade minimum-tick
authority required before promoting the Phase32-DC tick-quantization contract
into Candidate, BUY Quality, Entry, and Portfolio Construction decisions.

No code, configuration, runtime state, Pending state, Ledger state, run evidence,
fresh-run, resume, recover, replay, hard minimum price rule, symbol blacklist, or
Historical PnL tuning was used or changed in this phase.

Primary local references:

- `docs/phase_reports/phase32_da_9318_ultra_low_price_momentum_entry_quality_attribution_read_only_audit.md`
- `docs/phase_reports/phase32_db_ultra_low_price_tick_quantization_cross_sectional_multi_period_shadow_audit.md`
- `docs/phase_reports/phase32_dc_tick_quantization_aware_momentum_trend_evidence_shadow_design.md`
- `docs/phase_reports/phase32_dd_post_cw_tick_quantization_affected_security_funded_position_inventory_read_only_audit.md`
- `src/ai_fund_lab_v2/strategy/portfolio_construction.py`
- `src/ai_fund_lab_v2/strategy/shadow_runtime.py`
- `src/ai_fund_lab_v2/strategy/position_sizing.py`

External exchange references consulted for tick-rule dimensions:

- JPX English tick-size page: https://www.jpx.co.jp/english/equities/trading/domestic/07.html
- JPX FAQ tick-size table identifiers: https://faqsd.jpx.co.jp/faq/show/19577

## Current Evidence Coverage

`LATEST_COMPLETED_DATE_USED = 2023-04-26`

The DE revalidation scanned the currently available completed daily evidence for
the active post-CW/Post-DD lineage through `2023-04-26`.

The DD report previously recorded:

`DEFAULT_TICK_ASSUMPTION_CASE_COUNT = 555 joined observations`

DE revalidated the broader PC decision-material fallback surface and found:

`CURRENT_DEFAULT_TICK_FALLBACK_COUNT = 7561 PC decision-material rows`

Breakdown:

| Metric | Count |
| --- | ---: |
| Completed business dates scanned | 140 |
| First completed date | 2022-10-03 |
| Latest completed date | 2023-04-26 |
| PC rows using implicit default tick | 7561 |
| Unique symbols with implicit default tick | 804 |
| Funded-date rows with implicit default tick | 231 |

Price-bucket breakdown:

| Price bucket | Fallback rows |
| --- | ---: |
| `>50` | 6501 |
| `UNKNOWN` | 561 |
| `21-50` | 224 |
| `<=5` | 140 |
| `6-10` | 112 |
| `11-20` | 23 |

Representative repeated fallback symbols:

| Symbol | Fallback rows |
| --- | ---: |
| 94320 | 140 |
| 94340 | 140 |
| 93180 | 140 |
| 76470 | 140 |
| 83060 | 139 |
| 89180 | 118 |
| 76920 | 103 |
| 99840 | 96 |
| 67310 | 94 |
| 91070 | 75 |

The DE count is intentionally broader than the DD count. DD counted a narrower
joined shadow-analysis population. DE counts all PC decision-material rows where
the effective minimum tick came from the current silent fallback path.

## Current Minimum-Tick Authority Map

`CURRENT_MINIMUM_TICK_AUTHORITY_MAP =`

| Field / value | Current producer | Artifact / schema | Provenance | Fallback behavior | Consumer | Decision-material |
| --- | --- | --- | --- | --- | --- | --- |
| `minimum_tick` | May be present in Technical Features rows and copied by `strategy/shadow_runtime.py` | Technical Features-derived source row | Partial; no canonical tick-rule artifact or source hash was found in the current path | If absent, PC substitutes `DEFAULT_MINIMUM_TICK` | PC low-price guard; later PS context preservation | YES when present |
| `tick_size` | Accepted as alternate input by PC row parser | PC input row | Unclear; no canonical authority owner found | If absent, fallback continues | PC low-price guard | YES if used |
| `price_tick` | Accepted as alternate input by PC row parser | PC input row | Unclear; no canonical authority owner found | If absent, fallback continues | PC low-price guard | YES if used |
| `DEFAULT_MINIMUM_TICK = 1.0` | `strategy/portfolio_construction.py` constant | In-code fallback, not an evidence artifact | No symbol/date/price/security-class provenance | Silent substitution whenever row tick fields are absent | PC computes `single_tick_pct` and tick risk tier | YES today |
| `single_tick_pct` | `strategy/portfolio_construction.py` | PC output / order context | Derived from row tick or fallback tick divided by `reference_price` | Inherits silent default if no upstream tick exists | PC cap, PS context, reports, shadow diagnostics | YES |
| `price_tick_risk_tier` | `strategy/portfolio_construction.py` | PC output / authority context | Derived from `single_tick_pct` | Inherits silent default | PC cap and downstream context | YES |
| `price_tick_cap_weight` | `strategy/portfolio_construction.py` | PC low-price allocation authority | Derived from tier via `PRICE_TICK_RISK_CAPS` | Inherits silent default | Final PC target cap | YES |

Current source mechanics:

- `portfolio_construction.py` defines `DEFAULT_MINIMUM_TICK = 1.0`.
- PC resolves `minimum_tick` from `minimum_tick`, `tick_size`, or `price_tick`.
- If none are positive, PC silently substitutes the default.
- PC computes `single_tick_pct = minimum_tick / reference_price`.
- PC maps `single_tick_pct` into `NORMAL`, `WATCH`, `ELEVATED`, `SEVERE`, or
  `EXTREME`.
- PC applies tick-risk caps only in the buy-side allocation path.
- `shadow_runtime.py` can recover `minimum_tick` from Technical Features into
  source rows when Technical Features happens to contain it.
- `position_sizing.py` preserves tick fields in sizing context but is not the
  tick authority producer.

Conclusion: the current decision-material authority is PC-local and fallback
driven. It is acceptable for SHADOW inventory, but not sufficient for Production
Candidate/BQ/Entry authority.

## JPX Tick Semantics

`JPX_TICK_RULE_DIMENSIONS = price band + instrument/security class + special table eligibility + rule version + execution venue/broker constraints`

JPX rules are not a universal one-yen table. Based on the JPX tick-size pages,
tick size depends on the traded issue class and the price level. The current
JPX page separates at least these tables:

- TOPIX500 constituents, including TOPIX100 and TOPIX Mid400.
- ETFs / ETNs / leveraged / inverse instruments with trading unit 1.
- Other listed issues.

For the 2022-2023 Historical period relevant to the audited run, the practical
cash-equity rule dimensions needed by this system are:

| Dimension | Required use |
| --- | --- |
| Symbol / issue code | Resolve the security being evaluated |
| Decision date | Select PIT-valid issue metadata and rule version |
| Reference price | Select the correct price band |
| Product/security type | Separate domestic common stock, ETF, ETN, REIT, preferred, right, warrant, etc. |
| Exchange / venue / market segment | Ensure the JPX table applies |
| TOPIX500 / TOPIX100 / TOPIX Mid400 eligibility | Select fine tick table where applicable |
| ETF trading-unit class | Distinguish ETF-style table applicability |
| Rule effective date range | Avoid current metadata rewriting historical decisions |
| Broker execution constraints | Validate order acceptability if broker imposes a stricter executable increment |

`TICK_RULE_TEMPORAL_VERSIONING_REQUIRED = YES`

Reason:

- JPX tick-size tables have changed historically and JPX has announced a future
  table-methodology change from March 1, 2027.
- Production authority must therefore carry a rule id and effective date range.
- For Phase32 2022-2023 Historical evidence, the correct rule can be represented
  as a dated JPX/TSE cash-equity table version, but it must still be explicitly
  versioned instead of implied by current source code.

## Canonical Source Selection

`CANONICAL_MINIMUM_TICK_SOURCE = deterministic JPX tick table resolved from PIT security metadata, with broker/execution metadata as submit-time validation`

Priority order:

| Priority | Source | DE judgment |
| ---: | --- | --- |
| 1 | Broker/execution metadata | Strong for actual order acceptance and post-submit validation, but too late/circular for Strategy-time Candidate/BQ/Entry evidence. Use as an execution-side check, not the only Strategy authority. |
| 2 | Exchange/security metadata already available to the system | Preferred if it contains PIT product type, venue, listing status, and special tick-table eligibility. |
| 3 | J-Quants PIT-compatible metadata | Acceptable if it provides or can prove product/security class and date-valid issue attributes. |
| 4 | Deterministic validated JPX tick table | Required calculation layer once metadata class and reference price are known. |

The canonical authority should not be PC itself. PC may consume and preserve the
authority, but Candidate/BQ/Entry need the same upstream value before PC exists.

## PIT Contract

`MINIMUM_TICK_PIT_CONTRACT = minimum_tick(symbol, decision_date, reference_price) resolves from PIT-valid security classification and JPX rule version, or returns explicit non-authoritative status`

Required inputs:

- `symbol`
- `decision_date`
- `reference_price`
- `reference_price_source`
- `security_type`
- `exchange_or_market`
- `tick_table_class`
- `metadata_as_of_date`
- `rule_version`

Required output statuses:

- `KNOWN`
- `NOT_APPLICABLE`
- `INSUFFICIENT_EVIDENCE`

The contract must use only metadata and price evidence available as of the
decision time. Present-day product membership, current index membership, current
ETF classification, current listing state, or future rule changes must not
silently rewrite historical Strategy evidence.

## Reference Price Authority

`TICK_REFERENCE_PRICE_AUTHORITY = Strategy decision-time reference price, normally the same PIT close/reference price used by Technical Features and Candidate/BQ/Entry evidence`

Rules:

- For Strategy-time tick quantization, the price-band reference must be the
  decision-time reference price already available to the strategy layer.
- It must not depend on future execution price, fill price, or same-day future
  intraday data unavailable at the decision boundary.
- PC may continue to compute `single_tick_pct` from the canonical tick divided
  by its existing `reference_price`, but the source and timestamp of that
  reference price must be explicit.
- Submit/order validation may separately verify that the planned order price is
  aligned with broker/exchange tick constraints. That does not replace
  Strategy-time evidence.

## Security Coverage

`MINIMUM_TICK_SECURITY_COVERAGE = domestic JPX cash equities first; ETFs/ETNs and other special instruments only when product-type and tick-table class are proven`

Initial Production-supported coverage:

| Security class | Status |
| --- | --- |
| Domestic JPX common stock / ordinary listed equity | Supported when product/security metadata and table class are PIT-known |
| TOPIX500/TOPIX100/TOPIX Mid400 issues | Supported only when date-valid table eligibility is known |
| ETFs / ETNs / leveraged / inverse instruments | Conditional; supported only with explicit product class and trading-unit table |
| REITs / infrastructure funds / preferred shares / rights / warrants / unknown instruments | `INSUFFICIENT_EVIDENCE` until mapped to a validated JPX table |
| Delisted / suspended / ambiguous mapping | `INSUFFICIENT_EVIDENCE` or existing tradability block |

Unknown or unsupported security types must not inherit `1.0`.

## Missing Authority Policy

`MINIMUM_TICK_MISSING_POLICY = explicit status, no silent default for decision-material Candidate/BQ/Entry/PC paths`

Policy:

| Condition | Status | Decision-material behavior |
| --- | --- | --- |
| Tick resolves with PIT metadata, price band, and rule version | `KNOWN` | Consumers may use `minimum_tick` and derived fields |
| Instrument not governed by this tick contract | `NOT_APPLICABLE` | Consumer must use its own explicit contract or decline tick-based gating |
| Metadata class, reference price, date binding, or rule version is missing/ambiguous | `INSUFFICIENT_EVIDENCE` | Candidate/BQ/Entry must not treat the symbol as tick-robust; PC may not silently substitute default for cap authority |
| Tick materiality is provably irrelevant for a diagnostic-only report | diagnostic-only fallback allowed | Must be marked non-authoritative |

For the DC Production path, missing tick authority should lead to symbol-scoped
`BUY_WAIT`, `REVIEW_REQUIRED`, or evidence-confidence reduction according to the
future consumer contract. It must not become a global runtime HALT unless the
component cannot safely separate affected items.

## Artifact Contract

`MINIMUM_TICK_ARTIFACT_CONTRACT = minimum_tick_authority.v1`

Recommended artifact fields:

| Field | Required | Meaning |
| --- | --- | --- |
| `schema_version` | YES | `minimum_tick_authority.v1` |
| `symbol` | YES | Runtime symbol/security code |
| `business_date` | YES | Strategy decision date |
| `as_of_date` | YES | PIT metadata/evidence date |
| `reference_price` | YES for `KNOWN` | Price used for band selection |
| `reference_price_source` | YES | Source artifact/field |
| `minimum_tick` | YES for `KNOWN` | Resolved executable price increment |
| `single_tick_pct` | YES for `KNOWN` | `minimum_tick / reference_price` |
| `tick_rule_id` | YES | Rule table id |
| `tick_rule_version` | YES | Effective dated table version |
| `tick_rule_effective_from` | YES | Start date of the rule version |
| `tick_rule_effective_to` | YES when known | End date of the rule version |
| `security_type` | YES | PIT security/product class |
| `exchange` / `market_segment` | YES when available | Venue/segment basis |
| `tick_table_class` | YES | `TOPIX500`, `ETF_UNIT_1`, `OTHER_ISSUES`, etc. |
| `classification_source` | YES | Security master / J-Quants / exchange metadata |
| `classification_source_as_of` | YES | PIT timestamp/date |
| `resolution_status` | YES | `KNOWN`, `NOT_APPLICABLE`, `INSUFFICIENT_EVIDENCE` |
| `resolution_reason_codes` | YES | Machine-readable reason list |
| `source_artifact_id` | YES when artifact-backed | Parent evidence id |
| `source_artifact_hash` | YES when artifact-backed | Hash for reproducibility |
| `runtime_run_id` | YES for run artifacts | Prevent cross-run reuse |
| `producer` | YES | Owning component |
| `created_at` | YES | Materialization timestamp |
| `pit_status` | YES | `PASS` / fail-closed status |

The artifact must be hashable and included in downstream evidence manifests so
Candidate, BQ, Entry, PC, PS, and runtime reports can prove that they consumed
the same tick authority.

## Producer Owner

`MINIMUM_TICK_PRODUCER_OWNER = Technical Features / market-security authority layer, backed by PIT security metadata and deterministic JPX rule resolver`

Rationale:

- Candidate/BQ/Entry need tick authority before PC.
- PC is currently the only decision-material fallback producer, but that makes
  upstream consumers either blind or forced to recalculate.
- Technical Features already functions as the market-data evidence bridge and
  `shadow_runtime.py` already recovers Technical Features fields into Strategy
  source rows.

Recommended ownership boundary:

1. Market/security metadata loader owns PIT security classification.
2. Deterministic tick-table resolver owns `minimum_tick(symbol, date, price)`.
3. Technical Features publishes `minimum_tick_authority.v1` and derived
   tick-normalized fields.
4. Strategy Intelligence, Candidate, BQ, Entry, PC, and PS consume without
   independent fallback.

## Consumer Contract

`MINIMUM_TICK_CONSUMER_CONTRACT = all decision-material consumers accept canonical tick authority with provenance, or mark the item insufficient; no independent silent recalculation`

Consumer behavior:

| Consumer | Required behavior |
| --- | --- |
| Technical Features | Publish `minimum_tick_authority.v1`, `single_tick_pct`, close-level/tick-normalized diagnostics, and PIT status |
| Strategy Intelligence | Use canonical tick to compute tick-normalized trend/momentum robustness |
| Candidate | Use tick robustness as reliability / evidence-confidence modifier, not as a hard price floor |
| BUY Quality | Independently validate strong opportunity classification against tick robustness |
| Entry | Convert quantized-caution / insufficient tick evidence into reduce/wait/review according to DC contract |
| PC | Consume canonical `minimum_tick` and preserve existing cap semantics |
| PS | Preserve tick provenance in sizing/order context; do not author tick authority |
| Runtime planning / order validation | Check order-price increment compatibility if an executable price is generated |

Every consumer must persist:

- `minimum_tick`
- `single_tick_pct`
- `minimum_tick_authority_status`
- `minimum_tick_authority_source`
- `minimum_tick_authority_hash`
- `tick_rule_version`
- `reference_price_source`

## PC Migration Contract

`PC_MINIMUM_TICK_MIGRATION_CONTRACT = PC keeps current cap thresholds and allocation semantics, but replaces silent fallback with canonical authority consumption`

Migration:

1. PC input rows receive canonical tick authority fields from Technical Features
   / Strategy source rows.
2. If `resolution_status = KNOWN`, PC computes the same derived
   `single_tick_pct`, tier, and cap using the existing formulas.
3. If status is `INSUFFICIENT_EVIDENCE`, PC must not silently substitute
   `DEFAULT_MINIMUM_TICK` for decision-material caps.
4. PC should emit an explicit authority status and reason code in
   `low_price_risk_allocation_authority`.
5. Existing cap values stay unchanged:
   - `WATCH`: 12%
   - `ELEVATED`: 10%
   - `SEVERE`: 8%
   - `EXTREME`: 5%
6. Existing allocation thresholds, weights, rankings, BUY decisions, and cash
   policy are not changed in DE.

This is an authority migration, not a Strategy retune.

## Default Fallback Production Status

`DEFAULT_MINIMUM_TICK_PRODUCTION_STATUS = REMOVE_FROM_DECISION_MATERIAL_PATHS; RETAIN_ONLY_FOR_NON_AUTHORITATIVE_DIAGNOSTICS_OR_LEGACY_TEST_FIXTURES`

`DEFAULT_MINIMUM_TICK = 1.0` may remain in source temporarily only if all of the
following are true:

- The path is diagnostic, test-only, or explicitly marked non-authoritative.
- The emitted evidence records `minimum_tick_authority_status != KNOWN`.
- Candidate/BQ/Entry/PC Production decisions cannot mistake it for canonical
  PIT authority.

It is not acceptable as Production authority for all JPX securities and price
bands.

## DD Control Set Minimum-Tick Resolution

`DD_CONTROL_SET_MINIMUM_TICK_RESOLUTION = PARTIAL; current fallback often matches Other Issues low-price table, but Production proof is incomplete without PIT table-class metadata`

Observed current effective tick for each control row:

| Case | Reference price | Current effective tick | Current `single_tick_pct` | Current state | Canonical DE resolution |
| --- | ---: | ---: | ---: | --- | --- |
| 89180 / 2022-10-03 | 9.0 | 1.0 | 11.111111% | Funded BUY_NEW reduced | Conditional match if `OTHER_ISSUES`; unresolved until PIT table class is proven |
| 33500 / 2022-10-07 | 39.8 | 1.0 | 2.512563% | Funded BUY_NEW reduced | Conditional match if `OTHER_ISSUES`; unresolved until PIT table class is proven |
| 76470 / 2022-10-12 | 28.0 | 1.0 | 3.571429% | Funded BUY_NEW reduced | Conditional match if `OTHER_ISSUES`; unresolved until PIT table class is proven |
| 76470 / 2022-11-22 | 27.0 | 1.0 | 3.703704% | Target zero, high rank/BQ pollution case | Conditional match if `OTHER_ISSUES`; unresolved until PIT table class is proven |
| 76470 / 2022-11-25 | 27.0 | 1.0 | 3.703704% | BQ FULL, target positive but not confirmed funded | Conditional match if `OTHER_ISSUES`; unresolved until PIT table class is proven |
| 93180 / 2023-02-21 | 2.0 | 1.0 | 50.000000% | Rejected/zero target | Conditional match if `OTHER_ISSUES`; material tier differs if special fine-tick table applied |
| 93180 / 2023-03-15 | 3.0 | 1.0 | 33.333333% | Funded BUY_NEW, dominant QC case | Conditional match if `OTHER_ISSUES`; material tier differs if special fine-tick table applied |
| 94320 / 2023-03-15 | 157.9 | 1.0 | 0.633312% | Funded normal-price comparator | Potential mismatch if special TOPIX500 fine-tick table applied; likely tier remains `NORMAL` |
| 76920 / 2023-03-15 | 563.7 | 1.0 | 0.177399% | Normal-price comparator | Potential mismatch if special TOPIX500 fine-tick table applied; likely tier remains `NORMAL` |
| 83060 / representative 2023-03-15 | 861.5 | 1.0 | 0.116077% | Normal-price comparator | Potential mismatch if special TOPIX500 fine-tick table applied; likely tier remains `NORMAL` |
| 67400 / 2023-04-13 | 50.0 | 1.0 | 2.000000% | Funded BUY_NEW control | Conditional match if `OTHER_ISSUES`; unresolved until PIT table class is proven |

Important distinction:

- Several low-price domestic-equity cases probably resolve to `1.0` under the
  JPX Other Issues table for the relevant price bands.
- That does not make the current fallback canonical. It is a coincidence unless
  the run can prove PIT security class, table class, rule version, and reference
  price binding.
- Normal-price symbols such as 94320 and 83060 are exactly why a universal
  fallback is unsafe: if the TOPIX500 fine table applies, the true tick at those
  prices may be smaller than 1.0.

## Current vs Canonical Tick Difference

`CURRENT_VS_CANONICAL_TICK_DIFF = CONFIRMED_AUTHORITY_GAP; value mismatch is control-case dependent`

Resolved comparison:

| Case group | Current value | Canonical value under proven `OTHER_ISSUES` | Canonical value if special fine table applies | Materiality |
| --- | ---: | ---: | ---: | --- |
| Low-price Other Issues <= 3,000 JPY | 1.0 | 1.0 | Could be smaller for special fine-tick class | Value may match, provenance currently missing |
| 93180 at 2-3 JPY | 1.0 | 1.0 if Other Issues | Could be 0.1 if fine-tick special class applied | Potentially tier-changing, must prove table class |
| 94320 / 83060 normal-price large names | 1.0 | 1.0 if Other Issues | Could be 0.1 in sub-1,000 TOPIX500 bands | Likely remains `NORMAL`, but current value may be 10x too large |
| 76920 normal-price comparator | 1.0 | 1.0 if Other Issues | Could be 0.1 depending table class | Likely low Strategy impact, but authority must prove it |

Current SHADOW classifications:

- The extreme-tick findings for 93180/89180/76470 remain valid as SHADOW
  diagnostics under the current fallback-backed evidence.
- They are not ready to become Production Candidate/BQ/Entry gates until the
  underlying minimum tick is authoritative.
- DD's dominant risk finding remains: tick materiality is real and
  decision-relevant, but Production promotion requires source authority repair
  first.

## Regression Surface

`MINIMUM_TICK_REGRESSION_SURFACE = broad but authority-local`

Affected contracts/tests:

| Area | Regression risk |
| --- | --- |
| PC low-price guard | Current tests may assume implicit `1.0`; must be updated to pass canonical authority or assert explicit diagnostic fallback |
| Candidate | New upstream consumer of tick robustness; must not hard-reject solely on price |
| BUY Quality | Must consume tick robustness as independent validation without changing accepted weights in DE |
| Entry | Must distinguish `QUANTIZED_CAUTION`, `BUY_WAIT`, and `REVIEW_REQUIRED` without a hard minimum price |
| Technical Features | New authority artifact/schema/hash surface |
| Strategy Intelligence | Tick-normalized trend/momentum fields must be PIT and reproducible |
| Position Sizing | Preserve provenance, do not generate fallback |
| Runtime historical fresh-run | New evidence field requirements must not create broad HALT when item-scoped insufficiency is possible |
| Demo/Production | Must reject missing/stale/cross-run/current-date-incompatible authority without silently accepting `1.0` |
| Order-price validation | If shared with executable price validation, ensure Strategy-time tick and submit-time tick are separate but compatible |
| Existing G129/KI-006/Winner Retention | Must remain unaffected except for consuming additional preserved context |

Required focused tests for Phase32-DF:

- Known Other Issues low-price cases resolve to `1.0` with provenance.
- TOPIX500/fine-table fixture resolves to smaller tick where applicable.
- Missing table class yields `INSUFFICIENT_EVIDENCE`.
- Plan/current metadata without PIT proof is rejected.
- Future rule version does not rewrite 2022-2023 evidence.
- PC cap output is unchanged when canonical tick equals previous fallback.
- PC does not silently fallback in decision-material path.
- Candidate/BQ/Entry receive and preserve the same authority hash.
- Diagnostic fallback remains non-authoritative if retained.

## Implementation Readiness

`MINIMUM_TICK_PRODUCTION_AUTHORITY_READY = CONDITIONAL`

Ready:

- The required authority contract is clear.
- The current producer/consumer gap is identified.
- JPX rule dimensions are understood at design level.
- DD control cases are sufficient as regression fixtures.
- The repair can be isolated from Strategy parameter/threshold/weight changes.

Prerequisites before Production promotion:

1. Identify an existing PIT security metadata source for product type, venue, and
   tick-table class.
2. If TOPIX500 / TOPIX100 / TOPIX Mid400 membership is needed, prove
   date-valid membership for Historical decisions.
3. Encode the dated JPX tick table as a deterministic versioned resolver.
4. Publish `minimum_tick_authority.v1` from the market/security/Technical
   Features layer.
5. Migrate PC away from silent decision-material fallback.
6. Add focused fixtures covering low-price, normal-price, special-table,
   missing-metadata, stale-metadata, and future-version cases.

`MINIMUM_TICK_PRODUCTION_AUTHORITY_READY` is therefore not `YES` yet, because
the exact local PIT metadata source and special-table classification coverage
still need to be connected and tested.

## Phase32-DF Implementation Scope

`PHASE32_DF_IMPLEMENTATION_SCOPE = authority-only first; do not promote DC Candidate/BQ/Entry until minimum-tick authority is accepted`

Narrow DF sequence:

1. Add deterministic `minimum_tick_authority.v1` resolver using a dated JPX rule
   table and PIT security metadata.
2. Materialize the authority in Technical Features / market-security evidence.
3. Expose the authority to Strategy Intelligence and source rows with artifact
   hash/provenance.
4. Migrate PC to consume the canonical value and emit the same derived cap
   fields.
5. Preserve PS/runtime context.
6. Run focused authority and PC equivalence tests.
7. Only after authority acceptance, promote DC tick-normalized Candidate/BQ/Entry
   behavior in a separate phase.

No DC Candidate/BQ/Entry production behavior should be implemented in DE.

## Required Answers

1. `LATEST_COMPLETED_DATE_USED = 2023-04-26`
2. `CURRENT_MINIMUM_TICK_AUTHORITY_MAP = PC-local row-field-or-default producer; Technical Features may supply minimum_tick opportunistically; PS preserves derived context; no canonical PIT tick authority artifact currently governs all consumers`
3. `CURRENT_DEFAULT_TICK_FALLBACK_COUNT = 7561 PC decision-material rows; 804 symbols; 231 funded-date rows; DD 555 was narrower joined shadow population`
4. `JPX_TICK_RULE_DIMENSIONS = price band, issue/security class, exchange/venue, TOPIX500/TOPIX100/TOPIX Mid400 or ETF table applicability, trading-unit/product class, broker execution constraints, and dated rule version`
5. `CANONICAL_MINIMUM_TICK_SOURCE = deterministic JPX tick table resolved from PIT security metadata, with broker/execution metadata as submit-time validation`
6. `MINIMUM_TICK_PIT_CONTRACT = minimum_tick(symbol, decision_date, reference_price) using only PIT-valid metadata/rule version/reference price; otherwise explicit NOT_APPLICABLE or INSUFFICIENT_EVIDENCE`
7. `TICK_RULE_TEMPORAL_VERSIONING_REQUIRED = YES`
8. `TICK_REFERENCE_PRICE_AUTHORITY = Strategy decision-time reference price from PIT Technical Features/source evidence; not future execution/fill price`
9. `MINIMUM_TICK_SECURITY_COVERAGE = domestic JPX cash equities first when PIT table class is known; ETFs/ETNs/special instruments conditional; unknown unsupported types do not inherit 1.0`
10. `MINIMUM_TICK_MISSING_POLICY = KNOWN / NOT_APPLICABLE / INSUFFICIENT_EVIDENCE; no silent Production fallback`
11. `MINIMUM_TICK_ARTIFACT_CONTRACT = minimum_tick_authority.v1 with symbol/date/reference_price/minimum_tick/single_tick_pct/rule_version/table_class/source/hash/PIT/run-binding/status fields`
12. `MINIMUM_TICK_PRODUCER_OWNER = Technical Features / market-security authority layer backed by PIT security metadata and deterministic JPX resolver`
13. `MINIMUM_TICK_CONSUMER_CONTRACT = Technical Features, SI, Candidate, BQ, Entry, PC, PS, and Runtime consume the same canonical value/provenance or mark insufficiency`
14. `PC_MINIMUM_TICK_MIGRATION_CONTRACT = preserve existing PC cap formulas and thresholds but replace silent fallback with canonical authority`
15. `DEFAULT_MINIMUM_TICK_PRODUCTION_STATUS = remove from decision-material paths; retain only non-authoritative diagnostics/tests if needed`
16. `DD_CONTROL_SET_MINIMUM_TICK_RESOLUTION = PARTIAL; low-price controls conditionally match 1.0 under Other Issues table, normal/special-table controls require PIT class proof`
17. `CURRENT_VS_CANONICAL_TICK_DIFF = authority gap confirmed; value mismatch unconfirmed for low-price Other Issues cases, likely mismatch possible for TOPIX500/fine-table normal-price cases`
18. `MINIMUM_TICK_REGRESSION_SURFACE = PC low-price guard, Candidate/BQ/Entry future consumers, Technical Features, SI, PS context, Historical Runtime, Demo/Production, and order-price validation if shared`
19. `STRATEGY_BEHAVIOR_CHANGED = NO`
20. `MINIMUM_TICK_PRODUCTION_AUTHORITY_READY = CONDITIONAL`
21. `PHASE32_DF_IMPLEMENTATION_SCOPE = canonical minimum-tick authority -> Technical Features evidence -> SI propagation -> PC authority migration; defer DC Candidate/BQ/Entry promotion until authority accepted`
22. `HARD_MINIMUM_PRICE_RULE = NO`
23. `SYMBOL_BLACKLIST = NO`
24. `HISTORICAL_PNL_USED = NO`
25. `PHASE32_REPAIR_REQUIRED = YES`
26. `PRODUCTION_CHANGE_EXECUTED = NO`
27. `TARGET_RUN_MUTATED = NO`
28. `NEXT_RECOMMENDED_STEP = Phase32-DF authority-only implementation of PIT minimum-tick resolver/artifact and PC migration tests; no hard price floor, no blacklist, no PnL tuning`
29. `FINAL_JUDGMENT = PHASE32_DE_PIT_MINIMUM_TICK_PRODUCTION_AUTHORITY_DESIGNED_REPAIR_REQUIRED_BEFORE_DC_PRODUCTION_PROMOTION`

## Final Judgment

`PHASE32_DE_PIT_MINIMUM_TICK_PRODUCTION_AUTHORITY_DESIGNED_REPAIR_REQUIRED_BEFORE_DC_PRODUCTION_PROMOTION`

The current `DEFAULT_MINIMUM_TICK = 1.0` path is sufficient for SHADOW
diagnostics and was useful for DA/DD inventory, but it is not a Production
authority. Some audited low-price cases may truly have a 1 JPY tick under the
JPX Other Issues table, but the current artifacts do not prove PIT table class,
rule version, or reference-price authority. Conversely, normal-price and
special-table securities can require different tick increments, so a universal
fallback is unsafe.

Phase32 should repair this before closure. The next phase should implement only
the canonical PIT minimum-tick authority and PC migration surface first. DC's
Candidate/BQ/Entry behavior should be promoted only after that authority is
accepted.
