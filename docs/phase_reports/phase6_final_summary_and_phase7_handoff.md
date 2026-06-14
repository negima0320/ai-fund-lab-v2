# Phase6 Final Summary / Phase7 Handoff

## 1. Summary

Phase6 Position Management AI vNext is complete as a defensive / monitoring layer.

Final decision:

```text
PHASE6_COMPLETED_WITH_VALIDATED_DEFENSIVE_POSITION_AI
```

Meaning:

```text
Phase6 is not validated as an automatic sell optimizer yet.
Phase6 is validated as a defensive / monitoring layer.
```

The strongest current policy is:

```text
Buy candidates: Opportunity Top3
Holding posture: Top3 is basically hold-biased
Exit posture: EXIT signal is review / monitoring, not immediate sell
Risk posture: use Phase6 as a brake / anomaly detector
```

## 2. Read Docs

Core docs:

- `docs/01_requirements/phase_roadmap.md`
- `docs/03_ai_design/position_management_ai_design.md`
- `docs/03_ai_design/opportunity_ai_design.md`

Phase6 reports:

- `docs/phase_reports/phase6a_position_management_schema_and_baseline.md`
- `docs/phase_reports/phase6b_position_feature_builder.md`
- `docs/phase_reports/phase6c_position_label_dataset_audit.md`
- `docs/phase_reports/phase6d_baseline_label_alignment_audit.md`
- `docs/phase_reports/phase6e_baseline_rule_calibration.md`
- `docs/phase_reports/phase6f_realdata_position_dry_run.md`
- `docs/phase_reports/phase6_position_management_completion_audit.md`
- `docs/phase_reports/phase6h_position_historical_validation.md`
- `docs/phase_reports/phase6i_winner_holding_calibration.md`
- `docs/phase_reports/phase6j_random_yearly_e2e_smoke_test.md`
- `docs/phase_reports/phase6k_expanded_random_validation.md`
- `docs/phase_reports/phase6l_top3_policy_validation.md`
- `docs/phase_reports/phase6m_top3_fixed_vs_position_validation.md`
- `docs/phase_reports/phase6n_danger_only_exit_validation.md`
- `docs/phase_reports/phase6o_exit_confirmation_validation.md`

Phase5 handoff:

- `docs/phase_reports/phase5_final_handoff_for_phase6.md`
- `docs/phase_reports/phase5r_opportunity_ranking_quality_audit.md`
- `docs/phase_reports/phase5n_design_deviation_decision_record.md`

## 3. Created Files

- `docs/phase_reports/phase6_final_summary_and_phase7_handoff.md`
- `reports/position_management_ai/phase6_final_summary.json`
- `reports/position_management_ai/phase6_final_metrics_summary.csv`
- `reports/position_management_ai/phase6_final_handoff_checklist.json`

## 4. Phase6 Purpose

Phase6 Position Management AI judges how to handle a selected or held position:

```text
HOLD
EXIT
ADD
REDUCE
```

Phase6 does not do:

```text
Broker API
order placement
real trading
Paper Trading
Capital Allocation
purchase share count decision
fund allocation
live order
```

Important nuance:

```text
ADD is an add-candidate signal only.
REDUCE is a reduce-candidate signal only until later execution phases.
EXIT is a sell/review signal, not an order.
```

## 5. Phase4 / Phase5 / Phase6 Roles

Phase4 Candidate AI:

```text
All symbols -> Candidate Top50
Question: what should we monitor?
```

Phase5 Opportunity AI:

```text
Candidate Top50 -> Opportunity TopN
Question: what should become a buy candidate?
```

Phase6 Position Management AI:

```text
Held position / buy candidate -> HOLD / EXIT / ADD / REDUCE
Question: how should we hold it, and how should we handle danger?
```

Top3 / Top5 / Top10 validation was performed during Phase6, but this is primarily a Phase5 Opportunity policy finding. It informs Phase7 allocation, but it is not itself the core Position Management problem.

## 6. What Phase6 Implemented

Phase6-A:

```text
Position schema / baseline / forbidden feature audit / leakage audit
```

Phase6-B:

```text
Historical position fixture builder and feature builder extension
```

Phase6-C:

```text
Historical position label dataset and label leakage audit
```

Phase6-D:

```text
Baseline vs label alignment audit
```

Phase6-E:

```text
Rule baseline calibration
```

Phase6-F:

```text
Small historical real-data dry-run
```

Phase6-G:

```text
Completion audit through Phase6-A/F
```

Phase6-H:

```text
Historical validation of Opportunity-only vs Opportunity + Position Management
```

Phase6-I:

```text
Winner holding calibration
```

Phase6-J:

```text
Phase4 -> Phase5 -> buy decision yearly random E2E smoke test
```

Phase6-K:

```text
Expanded random validation across 5 random dates per year
```

Phase6-L:

```text
Top3 buy policy validation
```

Phase6-M:

```text
Top3 fixed hold vs Position AI validation
```

Phase6-N:

```text
Danger-only exit validation
```

Phase6-O:

```text
Exit confirmation validation
```

## 7. Key Results

### Phase6-I Winner Holding Calibration

Phase6-I improved winner holding behavior materially:

| metric | old | winner holding |
| --- | ---: | ---: |
| continue_winner_capture_rate | 0.021164 | 0.433862 |
| continue_winner wrong EXIT count | 7 | 0 |
| continue_winner over REDUCE count | 178 | 107 |
| false_exit_rate | 0.258883 | 0.221453 |
| average_return | 0.081954 | 0.081044 |

Interpretation:

```text
Winner holding got much better without materially damaging average return.
```

### Phase6-L Top3 Policy

TopN comparison:

| bucket | mean 20bd return |
| --- | ---: |
| Top3 | 0.169041 |
| Top5 | 0.093449 |
| Top10 | 0.060414 |
| Top4-5 | -0.019940 |
| Top6-10 | 0.027379 |

Recommended buy-candidate policy:

```text
Primary buy target: Top3
Backup watchlist: Top4-5
Avoid / no buy: Top6-10
Risk Guard bad: LOW_PRIORITY_REVIEW
```

Interpretation:

```text
Opportunity Top3 is the current strongest buy-candidate set.
Top4-5 is not equal priority.
Top6-10 should not be normal buy candidates.
```

### Phase6-M Fixed Hold vs Position Managed

| strategy | mean_return | worst_return | drawdown_avoidance_rate |
| --- | ---: | ---: | ---: |
| Fixed_20bd | 0.169041 | -0.267263 | 0.000000 |
| Position_Managed | 0.165223 | -0.223912 | 0.342105 |

Interpretation:

```text
Position AI loses slightly to Fixed_20bd on mean return,
but improves worst_return and drawdown avoidance.
```

2026 weak-regime result was important:

```text
Fixed_20bd mean_return: -0.019017
Position_Managed mean_return: -0.010893
Fixed_20bd worst_return: -0.267263
Position_Managed worst_return: -0.193095
```

Position AI has defensive value in weaker regimes.

### Phase6-N Danger-Only Exit

Danger-only exit was not validated.

| strategy | mean_return | false_exit_rate |
| --- | ---: | ---: |
| Fixed_20bd | 0.169041 | 0.000000 |
| Current_Position_Managed | 0.165223 | 0.611111 |
| Danger_Only_Exit | 0.166162 | 1.000000 |

Reason:

```text
Danger-only improved some risk metrics,
but false exits worsened and mean return stayed below Fixed_20bd.
```

### Phase6-O Exit Confirmation

Exit confirmation produced a useful finding, but not a fully validated automatic exit policy.

| strategy | mean_return | profit_retention_rate | confirmed_exit_count |
| --- | ---: | ---: | ---: |
| Fixed_20bd | 0.169041 | 0.206640 | 0 |
| Current_Position_Managed | 0.165223 | 0.192676 | 11 |
| Exit_Immediate | 0.164723 | 0.184417 | 13 |
| Exit_Confirm_2 | 0.167902 | 0.206640 | 5 |
| Exit_Confirm_3 | 0.169041 | 0.206640 | 2 |

Interpretation:

```text
Exit_Confirm_3 restores mean_return and profit retention to Fixed_20bd,
but automatic EXIT is still not validated because confirmed exits are not clearly high-quality.
```

Best use:

```text
Exit_Confirm_3-like signal should be monitoring / review, not automatic sell.
```

## 8. Recommended Current Policy

BUY:

```text
Use Phase5 Opportunity Top3 as primary buy target.
```

WATCH:

```text
Top4-5 is backup / watchlist.
```

NO BUY:

```text
Top6-10 is normally excluded.
```

HOLD:

```text
Top3 should be biased toward 20bd hold.
```

REDUCE:

```text
Do not auto-execute REDUCE for Top3.
Record as signal / review input.
```

EXIT:

```text
Do not use Phase6 EXIT as immediate sell.
Use Exit_Confirm_3-like behavior as monitoring / review signal.
```

Risk Guard bad:

```text
Do not auto-buy.
Do not necessarily discard permanently.
Treat as LOW_PRIORITY_REVIEW.
```

## 9. Important Learnings

Buy-candidate extraction is strong.

```text
Opportunity Top3 is materially stronger than Top5 and Top10.
```

Selling is much harder.

```text
Early exits can lower average return because Top3 names often recover or continue upward.
```

Position AI is not yet a profit maximizer.

```text
It is currently best used as a defensive / monitoring AI.
```

Top3 names are often stronger to hold than to trade.

```text
For Top3, selling requires much stronger evidence than buying required.
```

Phase6 succeeded as a brake / anomaly detector.

```text
It is not yet complete as an automatic sell AI.
```

## 10. Remaining Gaps

1. Full daily close path validation is still insufficient.

Current historical validations often use:

```text
5bd / 10bd / 20bd checkpoint approximation
```

2. EXIT signal quality is not good enough for automatic selling.

```text
false exit remains too high.
```

3. 2026-style weak-regime sensitivity remains.

```text
Even Top3 is weak in 2026.
```

4. Risk Guard policy is not final.

```text
LOW_PRIORITY_REVIEW is preferred over full skip,
but automatic rules are not yet settled.
```

5. Fixed Top3 20bd hold is very strong.

```text
Position AI has not beaten it as a profit maximizer.
```

6. Capital Allocation is not connected.

```text
Actual 1,000,000 JPY portfolio return is not validated.
```

7. Broker / Paper / live execution are not connected.

```text
Broker API, Paper Trading, live order, and real account updates remain out of scope.
```

## 11. Phase7 Handoff

### Inputs Phase7 Should Use

Opportunity signal:

```text
Opportunity Top3
expected_edge_score
buy_rank
downside_risk_score
risk_guard_status
```

Position signal:

```text
HOLD
EXIT signal
REDUCE signal
ADD signal
Exit confirmation count
risk/review status
```

### Recommended Phase7 Policy

```text
Top3 is primary allocation target.
Top4-5 is backup / watchlist.
Top6-10 is normally not bought.
Risk Guard bad is LOW_PRIORITY_REVIEW, not automatic buy.
Phase6 EXIT is review signal, not immediate sell.
REDUCE is not auto-executed for Top3.
ADD must be decided by Phase7 under budget and position constraints.
```

## 12. First Phase7 Tasks

Recommended Phase7-A starting point:

```text
Top3 primary allocation policy schema
1,000,000 JPY / Top3 equal-weight / 20bd simple portfolio simulation
Position AI as review / defensive layer comparison
2026 regime filter investigation
Risk Guard bad LOW_PRIORITY_REVIEW rule design
No Broker API
No order placement
No Paper Trading yet
```

## 13. Final Boundary Audit

Across Phase6:

```text
broker_api_executed: false
order_executed: false
paper_trading_executed: false
capital_allocation_executed: false
live_order_executed: false
real_account_updated: false
```

Final readiness:

```text
ready_for_phase7: true
phase7_scope: Capital Allocation Engine only
broker/order/paper/live: still prohibited until later phases
```
