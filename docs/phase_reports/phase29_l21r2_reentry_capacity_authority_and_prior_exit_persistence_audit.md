# Phase29-L21R2 — Re-entry Capacity Authority / Prior Exit Persistence Audit

Task ID: `Phase29-L21R2`  
Mode: READ-ONLY audit. No production, Strategy, PC, PS, RP, config, threshold, schema, runtime, pending, fresh-run, resume-run, historical-run, or current 4-year mutation was performed.  
Target run: `reports/runtime_tests/runs/runtime-test-historical-smoke-20260811T233614596811Z`  
Target focus: `23880`, `2022-08-30` through `2022-09-07`.

## Primary Judgment

`PHASE29_L21R2_REENTRY_CAPACITY_AND_PRIOR_EXIT_PERSISTENCE_GAPS_CONFIRMED`

Two independent gaps are confirmed:

1. REENTRY capacity is a hard recovery gate, but its canonical evidence source is not fully materialized or wired. `reentry_capacity_status=UNKNOWN` is therefore not evidence of excessive liquidity risk; it is missing capacity authority evidence.
2. `prior_exit_business_date` is correctly resolved from persistent execution history through `2022-09-05`, but disappears from the PC 23880 row on `2022-09-06` even though the input manifest still reports that the prior-exit state was supplied for 23880. That is a prior EXIT persistence / row-lifecycle gap, not cooldown expiry.

Implementation required: YES, but not in this task. The next task should be a focused L21R3 repair before any L21S capital deployment repair.

## 23880 Timeline

| Date | PC state | Prior EXIT | Cooldown | Recovery | Capacity | CA | Technical | Final planning |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `2022-08-30` | `REMOVE_CANDIDATE`, current qty `900` | blank | N/A | `not_reentry` | `UNKNOWN` | `NO_EVENT` | trend FAIL, momentum PASS | `SELL_EXIT`, qty `900` |
| `2022-08-31` | `EXCLUDE`, `BUY_NEW` | blank in PC | N/A | `not_reentry` | `UNKNOWN` | `NO_EVENT` | trend FAIL, momentum PASS | no order |
| `2022-09-01` | `ADD_CANDIDATE`, `REENTRY` | `2022-08-30` | `FAIL_CLOSED` | `REVIEW_REQUIRED`, `reentry_capacity_unavailable` | `UNKNOWN` | `NO_EVENT` | trend FAIL, momentum PASS | `NO_ORDER`, qty `0` |
| `2022-09-02` | `ADD_CANDIDATE`, `REENTRY` | `2022-08-30` | `FAIL_CLOSED` | `REVIEW_REQUIRED`, `reentry_capacity_unavailable` | `UNKNOWN` | `NO_EVENT` | trend PASS, momentum PASS | `NO_ORDER`, qty `0` |
| `2022-09-05` | `ADD_CANDIDATE`, `REENTRY` | `2022-08-30` | `PASS` | `REVIEW_REQUIRED`, `reentry_capacity_unavailable` | `UNKNOWN` | `NO_EVENT` | trend FAIL, momentum PASS | `NO_ORDER`, qty `0` |
| `2022-09-06` | `EXCLUDE`, `BUY_NEW` | blank in PC | N/A | `not_reentry` | `UNKNOWN` | `NO_EVENT` | trend FAIL, momentum PASS | no order |
| `2022-09-07` | no PC member row for 23880 | N/A | N/A | N/A | N/A | `NO_EVENT` source present | no technical row found | no order |

Important detail: on `2022-09-06`, `input_manifest.json` still reports `prior_closed_campaign_count=1`, `candidate_supplied_count=1`, `opportunity_supplied_count=1`, and `supplied_symbols=["23880"]`. The prior-exit resolver did not lose the ledger evidence before PC. The PC member row nevertheless has blank `prior_exit_business_date` and `semantic_buy_type=BUY_NEW`.

Persistent ledger evidence for 23880:

| Date | Side | Quantity |
| --- | --- | ---: |
| `2022-08-23` | BUY | `1200` |
| `2022-08-29` | SELL | `300` |
| `2022-08-30` | SELL | `900` |

The `2022-08-30` sell closes the remaining campaign. There is no later 23880 buy in the inspected persistent ledger.

## Re-entry Capacity Producer / Consumer Chain

Current PC capacity calculation is in `src/ai_fund_lab_v2/strategy/portfolio_construction.py`:

- Lines 994-1003 read capacity input from fields such as `rolling_median_traded_value_20`, `rolling_median_va_20`, `liquidity_rolling_median_traded_value_20`, `traded_value_median_20d`, or `rolling_median_turnover_value_20`.
- Lines 1004-1014 compute `proposed_notional`, `capacity_ratio`, and `liquidity_capacity_status`.
- Lines 1020-1021 send capacity into semantic REENTRY recovery.
- Lines 1220-1223 make missing `capacity_ratio` an unknown recovery blocker, and severe or `>0.03` capacity a fail-closed blocker.

L21R source evidence wiring attempts to copy `rolling_median_traded_value_20` from technical features in `src/ai_fund_lab_v2/strategy/shadow_runtime.py` lines 1273-1307.

However, the technical feature producer in `src/ai_fund_lab_v2/strategy/input_materialization.py` does not produce that field:

- `PM_TECHNICAL_REQUIRED_COLUMNS` only includes momentum, trend, volume momentum, and volatility fields.
- `_calculation_rows` emits `reference_price`, `price_momentum_return_5d`, `price_momentum_return_20d`, `trend_close_over_ma_20d`, `trend_ma_5_20_ratio`, `volume_momentum_ratio_5d`, and `volatility_return_std_20d`.
- It does not emit `rolling_median_traded_value_20` or equivalent traded-value median.

Therefore the current chain has a consumer and a copy hook, but lacks a canonical capacity producer or connected artifact.

## Why Capacity Is UNKNOWN

For 23880 on `2022-09-01`, `2022-09-02`, and `2022-09-05`:

- `normal_target_weight=0.18`;
- `rolling_median_traded_value_20=null`;
- `capacity_ratio=null`;
- `liquidity_capacity_status=UNKNOWN`;
- `reentry_capacity_status=UNKNOWN`;
- `reentry_recovery_reason=reentry_capacity_unavailable`;
- final target is zero.

This is not a same-day corporate action issue: same-day `corporate_event.json` marks 23880 as `known_no_event`. It is not missing technical trend/momentum evidence either: technical rows are present and available. The missing piece is capacity evidence.

Classification: `REENTRY_CAPACITY_AUTHORITY_WIRING_GAP_CONFIRMED`.

More precisely, this is a producer/authority gap plus wiring incompleteness:

- Source missing: no evidence was found in the current materialized technical artifact for traded-value rolling median.
- Wiring missing: the hook expects `rolling_median_traded_value_20`, but the upstream materializer does not provide it.
- Resolver unimplemented: no separate canonical liquidity/capacity resolver was found for REENTRY capacity authority.

## Whether UNKNOWN Is Legitimately Blocking

Capacity UNKNOWN is currently blocking because PC deliberately treats REENTRY recovery unknowns as non-PASS, then zeroes REENTRY target weight. This is mechanically legitimate under the current code, but semantically incomplete as a capital deployment authority:

- Safety hard authority: not implicated. No Safety cap breach evidence is needed to explain 23880's REENTRY zero.
- Liquidity capacity authority: intended authority exists as a rule, but the evidence producer is absent or not connected.
- Strategy allocation authority: 23880 had `normal_target_weight=0.18`, so Strategy allocation intent existed before the REENTRY recovery block.
- Diagnostic-only: capacity is not diagnostic-only today. It is a hard REENTRY recovery input.
- Missing evidence: confirmed. UNKNOWN means missing capacity evidence, not confirmed excessive participation.

The current fail-closed behavior is conservative and defensible for live trading, but it should not be treated as a validated business conclusion. For historical validation, UNKNOWN must be repaired to a resolved capacity authority before judging deployability.

## BUY_NEW / BUY_ADD / REENTRY Asymmetry

The asymmetry is confirmed.

REENTRY: missing capacity blocks via `_reentry_recovery_evidence`; PC sets final target to zero when recovery status is not PASS.

BUY_NEW / BUY_ADD: missing capacity is not a universal hard gate. PC only fail-closes missing liquidity evidence for low-price risk tiers when final buy-side allocation is positive. Otherwise missing capacity can coexist with positive allocation. In the L21O baseline, normal BUY_NEW positive allocation was `72`, while REENTRY positive allocation was `0 / 309`. In the current target run, positive BUY_NEW and BUY_ADD rows still carry missing capacity evidence.

This confirms that the `reentry_capacity_status=UNKNOWN` gate is REENTRY-specific in practice, apart from separate low-price liquidity guard behavior.

## Prior Exit Business Date Resolution Chain

Prior EXIT authority is implemented in `src/ai_fund_lab_v2/strategy/shadow_runtime.py`:

- `_supply_prior_exit_state` reads `.runtime/persistent_ledger/executions.jsonl`.
- `_resolve_prior_closed_campaigns_from_executions` consumes executions with `execution_business_date < decision business_date`.
- It tracks per-symbol campaign quantity and records a closed campaign when sell quantity reduces the campaign to zero.
- `_attach_prior_exit_to_summary` attaches `prior_exit_business_date` to candidate/opportunity rows when the symbol is not a current position and the row does not already have a prior-exit field.

The evidence explicitly reports:

```text
authority = persistent_ledger_execution_history
temporal_selection_rule = execution_business_date_strictly_less_than_decision_business_date
materialized_field = prior_exit_business_date
missing_prior_exit_behavior = normal_buy_new_unchanged
```

There is no cooldown-limited expiry rule in this resolver.

## Exact Reason Prior Exit Disappears On 2022-09-06

The exact downstream line of loss is not fully determinable without another instrumented run, which this READ-ONLY task forbids. The available evidence narrows it:

- The persistent ledger still contains the `2022-08-30` closing SELL.
- The `2022-09-06` input manifest still reports one prior closed campaign and supplies 23880 to candidate/opportunity.
- PC still has a 23880 member row on `2022-09-06`, but the row is `membership_intent=EXCLUDE`, `semantic_buy_type=BUY_NEW`, and `prior_exit_business_date=""`.

Therefore prior EXIT disappears after prior-exit supply and before or during PC member construction. The most likely mechanism is that PC constructs the member from a row path that does not preserve the supplied prior-exit fields once 23880 is no longer an eligible `ADD_CANDIDATE` opportunity. This is a row-lifecycle persistence gap, not ledger disappearance and not a cooldown rule.

Impact: if 23880 later becomes eligible again through the normal BUY_NEW path, it can be classified as ordinary BUY_NEW rather than REENTRY unless prior EXIT is rematerialized onto that row at the point of PC consumption.

## Semantic Re-entry Lifetime vs Cooldown Lifetime

Cooldown and prior EXIT awareness are separate concepts:

- Cooldown lifetime: a minimum wait rule. For 23880, `2022-09-05` is `PASS` because three completed business days have elapsed since `2022-08-30`.
- REENTRY semantic lifetime: awareness that a symbol was previously exited and a new buy is re-entering a closed campaign. This should persist until a new current position/campaign supersedes it, not expire when cooldown passes.

The current 23880 behavior violates that semantic separation: cooldown PASS on `2022-09-05` is followed by PC prior-exit blanking on `2022-09-06`.

## L21O 309-case Decomposition

The original L21O baseline is:

| Metric | Count |
| --- | ---: |
| PC candidates | `548` |
| Positive allocation | `72` |
| Zero allocation | `476` |
| REENTRY | `309` |
| REENTRY zeros | `309` |

L21O's original primary reasons were `193` corporate-action-status missing and `116` expected-edge-below-threshold. L21Q then reclassified the CA missing cases as `EXPLICIT_NO_EVENT_NOT_PROPAGATED`, not actual CA risk, and showed that the fixed absolute score threshold was semantically weak after L21I.

Post-L21R source-aware decomposition from existing evidence:

| Category | Count | Note |
| --- | ---: | --- |
| cooldown fail | `16` inferred | L21Q reports `293` cooldown-PASS rows out of `309`. |
| cooldown PASS | `293` | Candidate set after minimum wait. |
| capacity UNKNOWN in source-aware otherwise eligible subset | `264` | L21Q reports `264 / 293` policy-eligible before lot/Safety/Cash/Gross if CA and technical source evidence are consumed and the absolute score gate is removed; L21R preserves capacity fail-closed, and capacity evidence remains unavailable. |
| CA unresolved | `0` as actual CA risk for the 193 CA-missing group | L21Q found all 193 were source-side explicit no-event propagation gaps. |
| BQ fail | not dominant / not evidenced in L21O | L21O reports all 548 candidates were BQ non-reject: `FULL_ALLOCATION_ELIGIBLE` or `REDUCED_ALLOCATION_ONLY`. |
| trend / momentum fail | residual within `29` not source-aware eligible | Existing summaries do not safely split the remaining `293 - 264` without a fresh replay. |
| rank fail / other / multiple | residual within `29` plus cooldown-fail overlap | Existing summaries do not safely split these further without a fresh replay. |

Special subset requested:

```text
cooldown PASS
+ BQ FULL/REDUCED
+ CA NO_EVENT source authority
+ opportunity/rank requalified
+ trend or momentum recovered
+ capacity UNKNOWN
= 264 source-aware candidates before lot/Safety/Cash/Gross feasibility
```

The stricter `BQ FULL`-only count is not safely derivable from the current L21Q summary without reprocessing the old baseline under L21R semantics. It should be produced by L21R3 or a dedicated read-only replay script after capacity authority columns are defined.

## Capital Utilization Impact

Impact classification: `MATERIAL`, with upper-bound risk of `MAJOR`, but exact deployable notional is `NOT_QUANTIFIABLE` from current artifacts.

Rationale:

- L21O showed REENTRY was the dominant zero-allocation class: `309 / 476` zero candidates.
- L21Q showed up to `264` source-aware REENTRY candidates could become policy-eligible before execution feasibility if CA/technical/score semantics are repaired.
- L21R repaired CA and score semantics but intentionally preserved capacity fail-closed behavior.
- L21R2 confirms the remaining capacity evidence authority is still unresolved.

This can materially suppress capital deployment, but it must not be converted directly into a buy/notional estimate without lot, Safety, cash, gross exposure, and rank competition replay.

## Regression Status

Regression confirmed: YES, for prior EXIT persistence semantics.

The regression is not that a previous successful capacity authority was removed. Capacity is an incomplete authority/wiring gap.

For prior EXIT, L21K established persistent ledger-derived prior EXIT state. The target run shows that the resolver still supplies 23880 on `2022-09-06`, but PC loses it in the resulting row. That is a post-L21K persistence/lifecycle regression or incomplete integration.

## Implementation Required YES/NO

YES.

Required implementation should be constrained to a future L21R3 task:

- define and materialize canonical liquidity/capacity authority for REENTRY capacity;
- wire `rolling_median_traded_value_20` or the chosen canonical equivalent into PC rows;
- preserve prior EXIT fields through candidate/opportunity/member row lifecycle even when the row is temporarily `EXCLUDE`;
- add focused tests for 23880-like closed campaign persistence across cooldown PASS and temporary exclusion.

Do not solve this by:

- relaxing cooldown;
- treating historical-only missing capacity as PASS;
- changing Safety hard caps;
- forcing BUY_NEW;
- using latest/future market data;
- mutating pending/runtime state in-place.

## Recommended Next Task

`Phase29-L21R3 — Re-entry Capacity Authority Materialization + Prior Exit Row-Lifecycle Persistence Repair`

L21R3 should run before L21S capital deployment repair. L21S needs resolved capacity authority and durable prior EXIT semantics; otherwise it risks interpreting suppressed REENTRY rows as ordinary capital allocation scarcity or normal BUY_NEW behavior.

