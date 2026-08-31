# Phase32-BO - Profit Cushion Contextualization SHADOW Refinement & Re-Evaluation

## Scope

Target run:

`runtime-test-historical-extended-smoke-20260831T003243720082Z`

Fixed evaluation window:

- `2022-10-03` through `2024-05-01`
- completed business days evaluated: `388`

This phase refined only the non-mutating SHADOW interpretation for lot-blocked PM `REDUCE` binary materialization. No Production activation was performed.

No fresh-run, resume, recover, replay, long Historical, Runtime state mutation, Pending mutation, Ledger mutation, order submission, execution, Strategy parameter change, threshold change, weight change, model change, or new feature was performed.

## Evidence Basis

The BO refinement uses the semantic findings from Phase32-BL/BM/BN:

- BL introduced SHADOW-only binary materialization for one-lot / lot-blocked `REDUCE`.
- BM showed BL was conservative but did not reduce the 67310-linked large-loss tail.
- BN confirmed `PROFIT_CUSHION_OVERWEIGHTED_AS_HOLD_AUTHORITY = YES`.

Existing PM/Strategy Intelligence semantics treat current campaign profit as context for profit protection, not standalone action authority. BO preserves that boundary.

## Shadow Semantic Refinement

Changed:

- `current_campaign_relative_return > 0` no longer creates an independent HOLD-side vote.
- profit + intact/supportive continuation can add `CONTEXTUAL_HOLD_SUPPORT`.
- profit + weak/mixed continuation or elevated risk is recorded as `PROFIT_AT_RISK`.
- profit does not independently veto `SHADOW_FULL_EXIT`.
- no profit percentage threshold was added.
- no symbol/date/outcome-specific rule was added.

For profit-at-risk FULL_EXIT confirmation, BO requires current PIT deterioration strong enough to separate the 67310 shape from winner-protection controls:

- relative strength is `WEAK` or `DETERIORATING`
- trend health is `WEAK` or `DETERIORATING`
- participation quality is weak/deteriorating or risk is elevated
- no structural HOLD-side evidence is present

This is still SHADOW-only and does not create order/submit/execution authority.

## Files Changed

- `src/ai_fund_lab_v2/strategy/unrepresentable_reduce_exit_shadow.py`
- `tests/strategy/test_phase31_c0d_unrepresentable_reduce_exit_shadow.py`
- `docs/phase_reports/phase32_bo_profit_cushion_contextualized_shadow_refinement_evaluation.md`

## Focused Validation

Commands run:

```bash
PYTHONPYCACHEPREFIX=/private/tmp/pycache python3 -m py_compile src/ai_fund_lab_v2/strategy/unrepresentable_reduce_exit_shadow.py
python3 -m pytest tests/strategy/test_phase31_c0d_unrepresentable_reduce_exit_shadow.py -q
python3 -m pytest tests/strategy/test_phase31_c0d_unrepresentable_reduce_exit_shadow.py tests/strategy/test_phase31_g115_add_marginal_authoritative_binding.py tests/strategy/test_phase22_g_runtime_planning.py::test_phase32_f_runtime_does_not_resurrect_buy_wait_add_when_ps_delta_zero tests/strategy/test_phase32_x_recoverable_deterioration_episode.py tests/runtime_v2/test_phase31_f1w_item_scoped_partial_submit.py tests/runtime_v2/test_phase17_ab_current_valuation_pre_gate_authority.py tests/runtime_v2/test_phase30_ak9r27_pending_review_scope_authority.py tests/runtime_v2/test_phase30_ak9r28_historical_safety_temporal_authority.py -q
```

Results:

- py_compile: PASS
- direct SHADOW tests: `21 passed`
- focused adjacent regressions: `104 passed`

Covered cases:

- executable REDUCE unchanged
- non-lot / minimum-notional path unchanged
- BUY/HOLD/EXIT unaffected
- missing campaign provenance fail-closed
- stale/cross-run evidence fail-closed
- future evidence fail-closed
- profit alone cannot force HOLD
- profit alone cannot force SELL
- profit + strong continuation can support HOLD
- profit + 67310-type deterioration is not blocked from EXIT solely by profit cushion
- 74270/83040 winner-protection controls are not converted to FULL_EXIT merely because profit exists
- G129/KI-006/Winner Retention/AX/BA-adjacent focused regressions remain PASS

## Shadow Population

All eligible lot-blocked REDUCE rows before first-campaign episode de-duplication:

| Shadow decision | BO rows | BL/BM rows |
|---|---:|---:|
| `SHADOW_FULL_EXIT` | 46 | 38 |
| `SHADOW_HOLD` | 57 | 57 |
| `SHADOW_INSUFFICIENT_EVIDENCE` | 529 | 537 |

First non-overlapping episodes:

| Shadow decision | BO episodes | BL/BM episodes | Delta |
|---|---:|---:|---:|
| `SHADOW_FULL_EXIT` | 23 | 22 | +1 |
| `SHADOW_HOLD` | 23 | 23 | 0 |
| `SHADOW_INSUFFICIENT_EVIDENCE` | 297 | 298 | -1 |
| Total | 343 | 343 | 0 |

Ambiguity reduction vs BL/BM is real but small: `1` first episode, `8` raw rows.

## Economic Evaluation

Historical outcomes are used here only for post-hoc SHADOW evaluation, not as decision inputs.

| Metric | BO |
|---|---:|
| `SHADOW_FULL_EXIT` episodes | 23 |
| helped / harmful captured | 3 |
| hurt / false exits | 3 |
| neutral | 17 |
| avoided subsequent loss | 130,100 |
| false-exit / forfeited gain cost | 4,600 |
| net Full EXIT effect | +127,450 |

Comparison:

| Baseline | Net |
|---|---:|
| BL/BM `SHADOW_FULL_EXIT` | +77,770 |
| BO `SHADOW_FULL_EXIT` | +127,450 |
| Mechanical Policy A | +345,840 |

BO net vs BL: `+49,680`.

BO net vs Policy A: `-218,390`.

BO false-exit cost remains far below Policy A:

- Policy A: `518,140`
- BL/BM: `2,530`
- BO: `4,600`

BO recovers meaningful 67310 tail protection with only a small increase in false-exit cost, but it does not materially reduce the broad ambiguity population.

## HOLD Protection

| Metric | BO |
|---|---:|
| `SHADOW_HOLD` episodes | 23 |
| beneficial cases explicitly protected | 4 |
| harmful holds | 14 |
| neutral | 5 |
| preserved gain / recovery | 18,800 |
| avoidable loss left uncut | 95,860 |
| net HOLD value vs Full EXIT | +76,960 |

BO did not alter the `SHADOW_HOLD` episode count. The main change is contextual classification of profit, not expansion of HOLD authority.

## Large-Loss Tail

Days with `DAILY_PNL <= -100,000`:

| Date | Daily PnL | Dominant symbol | Dominant contribution | Prior lot-blocked REDUCE | Earliest BO shadow | Preventable by BO |
|---|---:|---|---:|---|---|---|
| 2023-05-11 | -120,270 | 49370 | -157,100 | NO | none | NO |
| 2023-06-08 | -116,600 | 67310 | -100,000 | YES | 2023-04-24 `SHADOW_FULL_EXIT` | YES |
| 2023-06-20 | -124,200 | 93410 | -216,000 | NO | none | NO |
| 2023-06-26 | -108,350 | 67310 | -100,000 | YES | 2023-04-24 `SHADOW_FULL_EXIT` | YES |
| 2023-06-30 | -100,930 | 67310 | -100,000 | YES | 2023-04-24 `SHADOW_FULL_EXIT` | YES |
| 2023-07-18 | -108,800 | 88900 | -296,800 | NO | none | NO |
| 2023-07-26 | -102,760 | 67310 | -100,000 | YES | 2023-04-24 `SHADOW_FULL_EXIT` | YES |
| 2023-08-08 | -103,820 | 67310 | -100,000 | YES | 2023-04-24 `SHADOW_FULL_EXIT` | YES |
| 2023-08-17 | -123,280 | 67310 | -100,000 | YES | 2023-04-24 `SHADOW_FULL_EXIT` | YES |

Summary:

| Metric | Value |
|---|---:|
| large-loss days | 9 |
| with prior lot-blocked REDUCE on dominant position | 6 |
| preventable by BO `SHADOW_FULL_EXIT` | 6 |
| estimated dominant-position tail reduction | 600,000 |

67310 tail captured: YES.

## Control Cases

### Beneficial Winner-Protection Controls

| Symbol | First blocked REDUCE | BO decision | Full EXIT effect | Read |
|---|---|---|---:|---|
| 62280 | 2023-12-22 | `SHADOW_INSUFFICIENT_EVIDENCE` | -26,330 | protected from false exit; profit context is `PROFIT_AT_RISK`, not standalone HOLD |
| 74270 | 2023-08-14 | `SHADOW_INSUFFICIENT_EVIDENCE` | -40,800 | protected; mixed relative strength prevents 67310-style confirmation |
| 92270 | 2022-10-24 | `SHADOW_INSUFFICIENT_EVIDENCE` | -22,800 | protected by structural HOLD-side evidence |
| 72140 | 2023-05-25 | `SHADOW_INSUFFICIENT_EVIDENCE` | -10,000 | protected by mixed/structural evidence |
| 83040 | 2024-02-21 | `SHADOW_INSUFFICIENT_EVIDENCE` | -4,100 | protected; mild deterioration is not enough for profit-at-risk FULL_EXIT |
| 69730 | 2022-11-04 | `SHADOW_HOLD` | -5,200 | explicit HOLD remains |

Mandatory winner-protection controls are not mechanically converted to FULL_EXIT.

### Harmful Controls

| Symbol | First blocked REDUCE | BO decision | Full EXIT benefit | Read |
|---|---|---|---:|---|
| 67310 | 2023-04-24 | `SHADOW_FULL_EXIT` | +100,000 | captured; profit is `PROFIT_AT_RISK` |
| 62310 | 2023-05-01 | `SHADOW_INSUFFICIENT_EVIDENCE` | +38,500 | still ambiguous due supportive trend/exhaustion |
| 74770 | 2023-10-04 | `SHADOW_INSUFFICIENT_EVIDENCE` | +4,900 | still ambiguous due strong structural evidence |
| 34160 | 2024-03-05 | `SHADOW_INSUFFICIENT_EVIDENCE` | +37,200 | still ambiguous due strong structural evidence |
| 36670 | 2023-06-16 | `SHADOW_FULL_EXIT` | +10,000 | captured |
| 51890 | 2023-04-14 | `SHADOW_INSUFFICIENT_EVIDENCE` | +3,750 | still ambiguous |

BO fixes the 67310 semantic regression case without encoding 67310-specific behavior.

## Unresolved Ambiguity

`SHADOW_INSUFFICIENT_EVIDENCE` first episodes:

| Metric | BO |
|---|---:|
| episodes | 297 |
| harmful unresolved | 69 |
| beneficial unresolved | 46 |
| neutral | 182 |
| unresolved Full EXIT counterfactual net | +184,770 |

The unresolved ambiguity remains economically material. BO reduces the key 67310 tail miss, but it does not solve the broader lot-blocked REDUCE ambiguity problem.

## Production Non-Interference

Confirmed in payload contract and focused tests:

- PM unchanged
- PC unchanged
- PS unchanged
- Runtime planning unchanged
- Pending unchanged
- Submit unchanged
- Execution unchanged
- Position/Cash unchanged
- shadow order authority: false
- shadow submit authority: false
- shadow execution authority: false
- `action_score` remains diagnostic only
- future outcome / future PnL / final campaign outcome is not used

Production behavior changed: NO.

## Required Final Answers

1. `PROFIT_CUSHION_STANDALONE_HOLD_AUTHORITY_REMOVED`: YES
2. `PROFIT_CUSHION_CONTEXTUALIZED`: YES
3. `NEW_FEATURE_ADDED`: NO
4. `NEW_MODEL_ADDED`: NO
5. `NEW_THRESHOLD_ADDED`: NO
6. `FUTURE_INFORMATION_USED`: NO
7. `PRODUCTION_BEHAVIOR_CHANGED`: NO
8. `67310_SHADOW_DECISION_AFTER_REFINEMENT`: `SHADOW_FULL_EXIT`
9. `SHADOW_FULL_EXIT_COUNT`: `23` first episodes; `46` raw eligible rows
10. `SHADOW_HOLD_COUNT`: `23` first episodes; `57` raw eligible rows
11. `SHADOW_INSUFFICIENT_EVIDENCE_COUNT`: `297` first episodes; `529` raw eligible rows
12. `AMBIGUITY_REDUCTION_VS_BL`: small; `-1` first episode and `-8` raw rows
13. `BO_AVOIDED_LOSS`: `130,100`
14. `BO_FALSE_EXIT_COST`: `4,600`
15. `BO_NET_EFFECT`: `+127,450`
16. `BO_NET_VS_BL`: `+49,680`
17. `BO_NET_VS_POLICY_A`: `-218,390`
18. `HARMFUL_CASE_CAPTURE_RATE`: `3 / 86 = 3.49%` in this BO re-evaluation; not materially improved as a broad-population rate
19. `BENEFICIAL_CASE_PROTECTION_RATE`: explicit `SHADOW_HOLD` protection `4 / 53 = 7.55%`
20. `LARGE_LOSS_DAYS_PREVENTABLE_BY_BO`: `6 / 9`
21. `ESTIMATED_LARGE_LOSS_TAIL_REDUCTION`: `600,000`
22. `67310_TAIL_CAPTURED`: YES
23. `UNRESOLVED_AMBIGUITY_NET`: `+184,770`
24. `IS_BO_SHADOW_ECONOMICALLY_SUPPORTED`: PARTIAL
25. `IS_PRODUCTION_CHANGE_JUSTIFIED_NOW`: NO
26. `NEXT_RECOMMENDED_STEP`: keep BO as SHADOW-only; use a follow-up PIT-only SHADOW refinement focused on the remaining high-net unresolved ambiguity without importing outcome labels or activating Production.
27. `FINAL_JUDGMENT`: `PHASE32_BO_PROFIT_CUSHION_CONTEXTUALIZED_SHADOW_REFINED_67310_TAIL_CAPTURED_PRODUCTION_NOT_JUSTIFIED_AMBIGUITY_REMAINS_MATERIAL`

## Final Judgment

`PHASE32_BO_PROFIT_CUSHION_CONTEXTUALIZED_SHADOW_REFINED_67310_TAIL_CAPTURED_PRODUCTION_NOT_JUSTIFIED_AMBIGUITY_REMAINS_MATERIAL`

