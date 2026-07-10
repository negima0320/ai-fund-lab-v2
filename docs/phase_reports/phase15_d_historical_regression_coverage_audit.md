# Phase15-D Historical Regression Coverage Audit

## Summary

Phase15-D inventories historical Runtime v2 failures, regressions, and review misclassifications, then audits whether Phase15 already covers them as fix targets, regression targets, or acceptance targets.

Purpose:

```text
過去に発覚した Runtime v2 の問題が、Phase15 の修正・Regression・Acceptance に落ちているかを確認すること
```

This audit is static and evidence-based. It reviewed Phase14/Phase15 reports, architecture contracts, source code, and test files. It did not run Runtime, Submit, Broker Write, Demo order, Production order, Notification real send, launchd/plist changes, Current direct edits, Runtime bypass creation, or fake-adapter Full Runtime acceptance.

Final judgment: **PHASE15D_HISTORICAL_REGRESSION_COVERAGE_AUDIT_COMPLETE**

## Reviewed Evidence

Primary historical evidence:

- `docs/phase_reports/phase14_e53_buy_sell_submit_guard_regression_audit.md`
- `docs/phase_reports/phase14_e54_instruction_regression_failure_postmortem.md`
- `docs/phase_reports/phase14_e51_sell_submit_execution_cleanup_cycle.md`
- `docs/phase_reports/phase14_e52_sell_submit_guard_contract_audit.md`
- `docs/phase_reports/phase14_e46_execution_current_projection_audit.md`
- `docs/phase_reports/phase14_e47_execution_current_projection_runtime_connection_fix.md`
- `docs/phase_reports/phase14_e50_sell_planning_runtime_connection.md`
- `docs/phase_reports/phase14_e33_runtime_v2_review_level_contract.md`
- `docs/phase_reports/phase14_final_summary_and_phase15_handoff.md`

Phase15 coverage evidence:

- `docs/phase_reports/phase15_a_purpose_goal_definition.md`
- `docs/phase_reports/phase15_b_runtime_architecture_v2_purpose_based_design_review.md`
- `docs/phase_reports/phase15_c_runtime_architecture_design_implementation_gap_audit.md`
- `docs/02_architecture/runtime_architecture_v2.md`

Implementation / regression evidence:

- `src/ai_fund_lab_v2/runtime_v2/submit/pipeline.py`
- `src/ai_fund_lab_v2/runtime_v2/submit/guards.py`
- `src/ai_fund_lab_v2/runtime_v2/planning/morning_pipeline.py`
- `src/ai_fund_lab_v2/runtime_v2/cli/run_daily_operation.py`
- `tests/runtime_v2/test_phase14e17_submit_pipeline_connection.py`
- `tests/runtime_v2/test_phase14e32_sell_runtime_io_contract.py`
- `tests/runtime_v2/test_phase14e50_sell_planning_runtime_connection.py`
- `tests/runtime_v2/test_phase13_l_path_resolver.py`
- `tests/runtime_v2/test_phase13_m_current_state_no_history_fallback.py`
- `tests/runtime_v2/test_phase14e6_runtime_v2_public_report_output.py`
- `tests/runtime_v2/test_phase14e34_notification_component_completion.py`

## Historical Regression Coverage Matrix

| Past Failure | Phase / Evidence | Root Cause | Failure Type | Phase15 Coverage | Regression Coverage | Remaining Risk | Severity | Required Follow-up |
|---|---|---|---|---|---|---|---|---|
| `max_order_amount=100000` hidden Submit cap | Phase14-E53, E54, Phase15-C; implementation still present in `submit/pipeline.py` | Runtime kept fixed policy after Capital Allocation/Pending | `HIDDEN_POLICY` | `COVERED_BY_PHASE15_B` / `COVERED_BY_PHASE15_C` / `NEEDS_PHASE15_FIX` | `REGRESSION_MISSING` for BUY/SELL over 100k regular CLI | Capital Allocation and SELL liquidation can still be blocked silently | `BLOCKER` | Remove/contractualize cap, split BUY/SELL policy, emit active policy manifest, add CLI regressions |
| BUY and SELL share same notional guard | Phase14-E51/E52/E53 | SELL risk reduction reused BUY risk-intake cap | `SELL_CONTRACT_GAP` | `COVERED_BY_PHASE15_B` / `NEEDS_PHASE15_FIX` | `REGRESSION_MISSING` for SELL liquidation above BUY cap | Runtime-owned SELL cleanup remains blocked or misclassified | `BLOCKER` | Implement side-specific guard contract and SELL liquidation regression |
| Morning Planning `max_orders=5` default | Phase15-C; implementation in `morning_pipeline.py` | Position count policy lives in Runtime default | `HIDDEN_POLICY` | `COVERED_BY_PHASE15_C` / `NEEDS_PHASE15_FIX` | `REGRESSION_MISSING` | Runtime can cap deployment independently of Risk Policy | `BLOCKER` | Move to Capital Deployment Contract or explicit policy source, emit manifest |
| Morning Planning per-order `100000` cap | Phase15-C; implementation in `morning_pipeline.py` | Runtime sizing logic reintroduced fixed allocation | `HIDDEN_POLICY` | `COVERED_BY_PHASE15_C` / `NEEDS_PHASE15_FIX` | `REGRESSION_MISSING` | Yearly return objective can be structurally throttled | `BLOCKER` | Derive order size from Capital Deployment Contract and price/lot constraints |
| `estimated_price=1000` fallback planning | Phase14-E26/E27/E28/E54 | Numeric value accepted without source/unit/date contract | `HIDDEN_POLICY` | `PARTIALLY_COVERED` by Phase15-B hidden policy rule | `REGRESSION_PARTIAL` | Fallback price can return through fixtures or legacy helper paths | `HIGH` | Add no-fallback-price regression and manifest price source evidence |
| Runtime cash buffer / target investment ratio defaults | Phase15-B/C | Capital deployment policy not fully implemented as explicit contract | `HIDDEN_POLICY` | `COVERED_BY_PHASE15_B` / `PARTIALLY_COVERED` by C | `REGRESSION_MISSING` | Runtime may under-deploy or over-deploy outside designed policy | `HIGH` | Define and load Capital Deployment Contract; emit active values |
| Runtime-owned max exposure / position sizing defaults | Phase15-B/C | Runtime can accidentally become allocation policy owner | `HIDDEN_POLICY` | `COVERED_BY_PHASE15_B` | `REGRESSION_MISSING` | Hidden policy can conflict with AI/Risk Policy | `HIGH` | Prohibit Runtime-local defaults and add static/no-hidden-policy checks |
| Fixture/test defaults flow into regular Runtime | Phase14-E54, Phase15-B/C | Friendly test values became operational assumptions | `REGRESSION_DESIGN_GAP` | `COVERED_BY_PHASE15_B` / `COVERED_BY_PHASE15_C` | `REGRESSION_PARTIAL` | Small fixtures can continue hiding real notional failures | `HIGH` | Add hostile fixtures: over 100k, more than 5 symbols, SELL liquidation, missing price source |
| CLI default becomes policy | Phase14-E53; regular CLI cannot override cap | Policy not represented as named contract | `CLI_PATH_GAP` | `COVERED_BY_PHASE15_C` | `CLI_REGRESSION_MISSING` | Operator cannot see or control active policy from normal entry | `HIGH` | CLI manifest must show policy source and values; tests must invoke regular CLI |
| Component PASS treated as Flow/Full PASS | Phase14-E33/E54 | Review Level was not enforced | `REVIEW_LEVEL_MISCLASSIFICATION` | `COVERED_BY_PHASE15_A` / `COVERED_BY_PHASE15_B` | `LEVEL3_EVIDENCE_MISSING` | Acceptance can overstate operational readiness | `HIGH` | Require Level1/2/3 label in every report and matrix |
| `tests pass` treated as acceptance | Phase14-E54 | Regression suite lacked Runtime evidence requirements | `REVIEW_LEVEL_MISCLASSIFICATION` | `COVERED_BY_PHASE15_A` / `COVERED_BY_PHASE15_B` | `REGRESSION_PARTIAL` | Test green can hide manifest/Broker/Current/Report gaps | `HIGH` | Add acceptance rule: tests are evidence, not final PASS |
| Fake adapter / fixture path treated as Full Runtime | Phase14-E54 | Test-only boundary overclassified | `REVIEW_LEVEL_MISCLASSIFICATION` | `COVERED_BY_PHASE15_A` / `COVERED_BY_PHASE15_B` | `LEVEL3_EVIDENCE_MISSING` | Broker-boundary schema/normalization bugs can recur | `HIGH` | Mark fake adapter evidence as Level1/limited Level2 only |
| Saved artifact or manifest `exit_code=0` treated as operational PASS | Phase14-E54 | Artifact existence was confused with work performed | `REVIEW_LEVEL_MISCLASSIFICATION` | `COVERED_BY_PHASE15_A` | `REGRESSION_PARTIAL` | CHECKPOINT-only jobs may pass without doing work | `HIGH` | Acceptance must require semantic counters and downstream state changes |
| Pending -> Submit was CHECKPOINT-only | Phase14-E17/E54 | Regular job did not perform operational Submit | `CLI_PATH_GAP` | `PARTIALLY_COVERED` by Phase15-C | `REGRESSION_PARTIAL` | Similar checkpoint-only regression can recur in jobs | `HIGH` | Require job-specific work evidence, not stage presence |
| Market Refresh CHECKPOINT-only | Phase14-E35/E36/E41/E54 | Stage recorded without feature artifacts | `CLI_PATH_GAP` | `PARTIALLY_COVERED`; current tests cover artifact generation | `REGRESSION_PRESENT` for component/flow artifact | Runtime network/error classification still needs Level3 evidence | `MEDIUM` | Keep artifact existence and review-required classifications in regression |
| Direct pipeline tests substituted for CLI regular path | Phase14-E53/E54, Phase15-C | Tests monkeypatched or bypassed `run_daily_operation` path | `CLI_PATH_GAP` | `COVERED_BY_PHASE15_C` | `CLI_REGRESSION_MISSING` | Runtime wiring can diverge from tested function behavior | `HIGH` | Add regular CLI tests for morning, sell_planning, submit, execution, report/notification tail |
| Phase-only/demo-only bypass accepted as Runtime path | Phase14-E54 | Temporary scripts were not separated from regular Runtime | `CLI_PATH_GAP` | `COVERED_BY_PHASE15_A` / `COVERED_BY_PHASE15_B` | `REGRESSION_MISSING` | Bypass can mask production path gaps | `HIGH` | Ban bypass PASS; require call graph evidence |
| Current SoT confused with per-run artifact | Phase14-D19-D22/E54 | History/Evidence artifacts treated as Current | `CURRENT_SOT_GAP` | `COVERED_BY_PHASE15_C` | `REGRESSION_PRESENT` for fixed path/no history fallback | Future reports can still misstate scope | `MEDIUM` | Preserve Current fixed-path tests and report source labels |
| `.runtime/persistent_ledger/state.json` not updated after execution | Phase14-E46/E47/E54 | Execution wrote ledger but did not call Current projection | `CURRENT_SOT_GAP` | `PARTIALLY_COVERED`; Phase15-C says path exists but Level3 re-review needed | `REGRESSION_PARTIAL` | Execution success may not prove asset state change in live/demo | `HIGH` | Add regular CLI Execution -> Current projection regression and manifest before/after summary |
| Execution-equivalent evidence treated as Production | Phase14-E54 | Demo/read-only/projection evidence level was overstated | `REVIEW_LEVEL_MISCLASSIFICATION` | `COVERED_BY_PHASE15_A` | `LEVEL3_EVIDENCE_MISSING` | Production readiness may be inferred too early | `HIGH` | Keep production unlock as separate acceptance gate |
| Broker-only positions sold or counted as Runtime-owned | Phase14-E50/E51 | Current ownership boundary needed explicit tests | `SELL_CONTRACT_GAP` | `PARTIALLY_COVERED`; SELL planning excludes broker-only | `REGRESSION_PRESENT` for planning, `REGRESSION_MISSING` for submit/execution | Submit and execution still need broker read-only evidence separation | `HIGH` | Add end-to-end SELL source Current-only and Broker-only exclusion regression |
| Demo cash copy / Current direct edit risk | Phase14-E54/handoff | Current was tempting to patch manually after demo operations | `CURRENT_SOT_GAP` | `COVERED_BY_PHASE15_A` / `COVERED_BY_PHASE15_C` | `REGRESSION_PARTIAL` | Manual correction can hide ledger/projection bugs | `HIGH` | Require ledger-derived Current and prohibit direct Current edits in acceptance |
| Ledger History vs Today mixed in reports | Phase14-E27/E30/E54 | Report scope labels were insufficient | `REPORT_SCOPE_GAP` | `PARTIALLY_COVERED`; Phase15-B/C require scope separation | `REGRESSION_PRESENT` for some public report scope/redaction | Semantic drift remains possible as report evolves | `MEDIUM` | Add report semantic regression for Current/Today/Run/History boundaries |
| `Report generated` treated as semantic Report PASS | Phase14-E54, Phase15-A/B | Existence check overclassified | `REPORT_SCOPE_GAP` | `COVERED_BY_PHASE15_A` / `COVERED_BY_PHASE15_B` | `REGRESSION_PARTIAL` | Generated report can carry wrong state or scope | `MEDIUM` | Require source refs, scope counts, and semantic assertions |
| Public/Internal boundary and Blog source unverified | Phase14 handoff/E54 | Public surface was not proven from Current SoT/Runtime report | `REPORT_SCOPE_GAP` | `PARTIALLY_COVERED` | `REGRESSION_MISSING` for Blog/Public pipeline | Public output can leak internal fields or stale history | `MEDIUM` | Add Public Report/Blog policy and redaction/source regressions |
| Notification payload treated as delivery PASS | Phase14-E34/E54, Phase15-C | Payload/queue/send/delivery/audit levels collapsed | `NOTIFICATION_SCOPE_GAP` | `COVERED_BY_PHASE15_A/B/C` | `REGRESSION_PARTIAL` for payload/ledger; `LEVEL3_EVIDENCE_MISSING` for real delivery | Operator may think notification was sent when only payload exists | `MEDIUM` | Keep payload-only label; add queue/sender/delivery/audit acceptance before send |
| Notification queue/sender/delivery/audit not connected to regular CLI | Phase15-C | CLI tail generates payload, reports `notification_sent=false` | `NOTIFICATION_SCOPE_GAP` | `COVERED_BY_PHASE15_C` | `REGRESSION_PARTIAL` | Delivery lifecycle not operationally proven | `MEDIUM` | Define notification delivery policy and regular CLI delivery evidence |
| Broker Accepted treated as Runtime PASS | Phase14-E54, Phase15-A/B | Broker boundary success over-weighted against Runtime path evidence | `BROKER_BOUNDARY_GAP` | `COVERED_BY_PHASE15_A` / `COVERED_BY_PHASE15_B` | `LEVEL3_EVIDENCE_MISSING` | Current/Report/Notification can remain wrong after Broker success | `HIGH` | PASS requires Broker evidence plus Current/Report/Notification/regression alignment |
| Broker issue code normalization missing | Phase14-E18/E19/E54 | Internal 5-character symbol sent to broker boundary | `BROKER_BOUNDARY_GAP` | `PARTIALLY_COVERED`; Phase15-C did not deeply re-audit broker schema | `REGRESSION_PARTIAL` | Boundary unit/schema regression can recur | `HIGH` | Add broker request schema regression for issue code, shares, lot, price, account |
| OrderListDetail optional evidence treated as mandatory | Phase14-D9-D11/E23/E54 | Evidence policy unclear | `BROKER_BOUNDARY_GAP` | `PARTIALLY_COVERED` by architecture evidence policy | `REGRESSION_PARTIAL` | Optional API outage may stop valid reconciliation | `MEDIUM` | Encode required vs optional broker evidence policy |
| Position mapping semantic gap | Phase14-D12/D13/E54 | Fetch success lacked normalized semantic checks | `BROKER_BOUNDARY_GAP` | `PARTIALLY_COVERED` | `REGRESSION_PARTIAL` | Broker rows can be present but unusable | `HIGH` | Regression must assert symbol, quantity, account, market, price/value |
| `POST_SEND_UNKNOWN` auto-resend risk | Architecture v2, Phase15-B/C | Non-idempotent submit state must never auto-repeat | `BROKER_BOUNDARY_GAP` | `COVERED_BY_PHASE15_B` | `REGRESSION_MISSING` | Duplicate orders under network ambiguity | `BLOCKER` | Add submit state-machine/idempotency regression |
| Raw request/response/secret persistence risk | Architecture v2, Phase12/14 evidence | Debug evidence can leak secrets or raw broker payloads | `BROKER_BOUNDARY_GAP` | `PARTIALLY_COVERED` by architecture and existing broker tests | `REGRESSION_PARTIAL` | Sensitive data can leak in artifacts | `HIGH` | Add Runtime artifact secret/raw response scan regression |
| SELL component existed but was not CLI connected | Phase14-E50/E54 | Component completion overclassified before `sell_planning` job | `SELL_CONTRACT_GAP` | `PARTIALLY_COVERED`; CLI now has `sell_planning` | `REGRESSION_PRESENT` for planning only | Submit/execution SELL path still not Level3 accepted | `HIGH` | Require SELL Pending -> Submit -> Broker -> Current -> Report/Notification flow evidence |
| SELL cleanup failed because hidden cap blocked all SELLs | Phase14-E51/E52 | SELL liquidation used default BUY-sized cap | `SELL_CONTRACT_GAP` | `COVERED_BY_PHASE15_C` / `NEEDS_PHASE15_FIX` | `REGRESSION_MISSING` | Cannot liquidate Runtime-owned positions above 100k | `BLOCKER` | Implement SELL liquidation policy and high-notional SELL regression |
| SELL after Current zero / cash update not proven | Phase14-E51 | Flow stopped before Broker write and Current projection | `SELL_CONTRACT_GAP` | `PARTIALLY_COVERED` | `LEVEL3_EVIDENCE_MISSING` | SELL success may not reduce positions/correct cash | `HIGH` | Add demo Level3 SELL operation after guard fix |
| Position Management AI not connected to SELL Runtime | Phase14 handoff/E54 | Exit logic and cleanup SELL were separate | `SELL_CONTRACT_GAP` | `NOT_COVERED` except as future contract item | `REGRESSION_MISSING` | SELL may remain cleanup-only rather than strategy-driven exit | `MEDIUM` | Define Position Management AI -> SELL Planning contract |
| Cleanup SELL mistaken for normal SELL acceptance | Phase14-E51/E54 | Emergency/manual cleanup and normal exit policy conflated | `SELL_CONTRACT_GAP` | `PARTIALLY_COVERED` | `REGRESSION_MISSING` | Acceptance can overstate normal SELL capability | `MEDIUM` | Label cleanup vs normal SELL; test both contracts separately |
| launchd moved ahead of acceptance | Phase14-E16/handoff/E54 | Scheduler readiness can be confused with Runtime readiness | `OPERATION_RUNBOOK_GAP` | `PARTIALLY_COVERED` by Phase15-A/B prohibitions | `LEVEL3_EVIDENCE_MISSING` | Automation may repeat unsafe operation | `HIGH` | launchd readiness policy after Runtime Level3 acceptance |
| Carryover/stale/holiday/date/network/J-Quants/demo-time cases under-specified | Phase14-E54/handoff | Operational runbook did not fully encode adverse conditions | `OPERATION_RUNBOOK_GAP` | `PARTIALLY_COVERED` | `REGRESSION_MISSING` | Automated runs can make wrong day/state decisions | `HIGH` | Add operation readiness matrix and stale/holiday/network regressions |
| Retry / non-idempotent behavior under-specified | Architecture v2 and Phase14 failures | Submit and notification are side-effecting operations | `OPERATION_RUNBOOK_GAP` | `PARTIALLY_COVERED` | `REGRESSION_MISSING` | Duplicate submit/send under retry | `BLOCKER` | Add idempotency ledger checks for Submit and Notification Send |
| Small fixtures all under 100k | Phase14-E53/E54 | Regression values never challenged real contract | `REGRESSION_DESIGN_GAP` | `COVERED_BY_PHASE15_C` | `REGRESSION_MISSING` | Hidden caps remain invisible | `HIGH` | Add above-cap BUY and SELL fixtures |
| 5-symbol fixture masks `max_positions=5` | Phase15-C and Phase14 fixture pattern | Fixture shape matched hidden default | `REGRESSION_DESIGN_GAP` | `COVERED_BY_PHASE15_C` | `REGRESSION_MISSING` | Hidden position cap can look intentional | `HIGH` | Add 6+ candidate regression and explicit max_positions manifest test |
| Submit active policy manifest missing | Phase15-C | Guard result does not expose policy source/values | `REGRESSION_DESIGN_GAP` | `COVERED_BY_PHASE15_C` / `NEEDS_PHASE15_FIX` | `REGRESSION_MISSING` | Operator cannot audit why Submit allowed/blocked | `HIGH` | Implement and test active policy manifest fields |
| Historical failures not mapped to regression suite | Phase14-E54 -> Phase15-D | Lessons were documented but not fully converted to tests | `REGRESSION_DESIGN_GAP` | `COVERED_BY_PHASE15_D` | `REGRESSION_MISSING` | Same class can recur with different symptom | `HIGH` | Maintain this matrix as Phase15 regression backlog |
| Production endpoint guard / unlock risk | Phase12/14 reports, architecture | Demo readiness can be mistaken for production readiness | `PRODUCTION_READINESS_GAP` | `PARTIALLY_COVERED` by architecture/prohibitions | `LEVEL3_EVIDENCE_MISSING` | Accidental production order or wrong endpoint | `BLOCKER` | Separate Production Unlock contract with explicit operator approval |
| Credentials/secrets/account mapping/NISA/account type/broker capability differences | Phase12/14 broker reports | Broker account semantics not part of Runtime Level3 evidence yet | `PRODUCTION_READINESS_GAP` | `PARTIALLY_COVERED` | `REGRESSION_PARTIAL` | Correct demo behavior may fail in production or wrong account | `HIGH` | Add broker capability/account contract before production |
| Order type, fees/taxes, buying-power hold not fully accepted | Phase12/14 broker and Phase15-B capital deployment concerns | Estimated amount and actual broker constraints can diverge | `PRODUCTION_READINESS_GAP` | `PARTIALLY_COVERED` | `REGRESSION_MISSING` | Orders may be rejected or over-allocate cash | `HIGH` | Add broker constraint policy and buying-power hold regression |
| API downtime/maintenance handling incomplete | Phase14 market/broker postmortems | Runtime needs review-required semantics for unavailable APIs | `PRODUCTION_READINESS_GAP` | `PARTIALLY_COVERED` | `REGRESSION_PARTIAL` | Runtime can continue on stale or incomplete evidence | `HIGH` | Add maintenance/network failure runbook and tests |

## Regression Hotspot Matrix

This section lists likely future regression points, including areas that have not necessarily failed yet but have the shape of previous Runtime regressions.

| Hotspot | Why Regression Is Likely | Evidence Checked | Existing Test | Missing Test | Severity | Required Follow-up |
|---|---|---|---|---|---|---|
| Submit amount policy default | `run_submit_pipeline(... max_order_amount=100_000.0)` is still a hidden regular-path default and applies after Pending/Approval | `src/ai_fund_lab_v2/runtime_v2/submit/pipeline.py`; Phase15-C | Direct submit pipeline tests exist with small amounts | Regular CLI BUY >100k and SELL >100k with active policy manifest | `BLOCKER` | Replace hidden default with explicit BUY/SELL policy source and test normal CLI |
| Morning `--max-orders` CLI default | CLI default `--max-orders=5` and pipeline default `max_orders=5` can become policy without Risk/Capital source | `run_daily_operation.py`, `morning_pipeline.py`, Phase15-C | Morning connection tests exist | 6+ candidate BUY test proving policy source/decision is emitted | `BLOCKER` | Move count policy to Capital Deployment Contract or emit explicit operator policy |
| Morning per-order sizing cap | `per_order_budget = min(planning_budget / max_orders, 100_000.0)` can silently under-deploy capital | `morning_pipeline.py`; Phase15-C | Small fixture planning tests | Capital deployment test where intended order amount exceeds 100k | `BLOCKER` | Derive sizing from explicit capital contract; assert no hidden cap |
| SELL planning `max_orders=5` | SELL liquidation may leave positions unsold because same count default is reused | `sell_pipeline.py`, `run_daily_operation.py` | SELL planning Current-only test | SELL Current with 6+ Runtime-owned positions and explicit liquidation policy | `HIGH` | Separate SELL liquidation batching policy from BUY position-count policy |
| Submit Broker available quantity evidence | Submit passes `broker_available_quantity=sell_position_quantity` from Current, not Broker ReadOnly | `submit/pipeline.py`, `submit/guards.py`, Phase15-C | SELL planning excludes broker-only positions | Regular submit test where Broker available quantity is lower than Current quantity | `HIGH` | Connect/read Broker available quantity evidence or mark missing as Review Required |
| Pending-only source guard semantics | Guard checks source path string, but manifest does not expose full source contract/policy source | `submit/guards.py`, `submit/models.py` | Pending source guard tests partially exist | Manifest assertion for source path, source hash, policy source, and manual review flag | `HIGH` | Emit Submit source contract in manifest/report/audit |
| Submit active policy manifest | Item results include reasons but not guard policy version/source/side-specific policy values | `SubmitPipelineResult.to_stage_details`, CLI manifest, Phase15-C | None for active policy manifest | Manifest regression for `guard_policy_version`, side, cap source, Current/Broker source | `HIGH` | Add active guard policy object to submit result and CLI manifest |
| Direct pipeline vs regular CLI coverage | Several tests call pipeline functions or monkeypatch CLI internals, so normal args/defaults can drift | `tests/runtime_v2/test_phase14e17_submit_pipeline_connection.py`, Phase15-C | Direct pipeline and monkeypatch tests | Subprocess or `main(argv)` tests with real CLI args and generated manifest assertions | `HIGH` | Add CLI regular-path regression suite |
| Fake adapter broker boundary | Fake/demo adapters can pass while Tachibana fields, issue code, account, and order type fail | Phase14-E54; submit models; broker normalizer evidence | Some normalizer and fake adapter tests | Broker boundary schema regression for request fields without real write | `HIGH` | Add adapter preflight contract tests with sanitized request diagnostics |
| BUY-only evidence reused for SELL | BUY execution/current/report path has more demo evidence than SELL; SELL stopped before Broker in E51 | Phase14-E48, E51, E52 | BUY flow evidence; SELL planning tests | SELL Submit -> Broker evidence -> Execution -> Current -> Report/Notification Level3 demo after guard fix | `BLOCKER` | Do not mark SELL Runtime PASS until full SELL chain is proven |
| SELL-only Current source rules not mirrored for BUY | SELL has Current-only source tests; BUY deployment source/policy manifest is weaker | Phase15-C; sell planning tests | SELL Current-only source test | BUY Capital Allocation -> Pending -> Submit policy-source regression | `HIGH` | Add BUY source/policy provenance fields and tests |
| Report/Notification tail stages always PASS | CLI appends report/notification/audit PASS stages even when they are payload-only or generated artifacts | `run_daily_operation.py` tail stages | Report and notification component tests | Semantic stage status tests: generated vs delivered vs audited, and redaction failure path | `MEDIUM` | Split artifact generation from semantic PASS in manifest |
| Audit aggregator not regular CLI job | CLI records `audit` stage but Phase15-C found no standalone audit job/aggregator call | `run_daily_operation.py`, Phase15-C | Audit component checks | CLI audit artifact content regression and standalone audit contract if required | `MEDIUM` | Clarify audit tail artifact vs Audit Runtime job |
| Daily rehearsal checkpoint-only path | `daily_rehearsal` records many hooks but performs no component work, making PASS easy to misread | `_job_checkpoints` in `run_daily_operation.py` | CLI smoke/checkpoint tests | Test that daily rehearsal is labeled checkpoint-only and never Level2/3 PASS | `MEDIUM` | Add manifest `review_level=checkpoint_only` or equivalent |
| Feature refresh as folded job | Architecture reviews `feature_refresh`, but CLI exposes only `market_refresh` with feature artifacts folded in | `ALLOWED_JOBS`, market refresh tests, Phase15-C | Market refresh artifact test | CLI/manifest assertion that feature refresh is covered by market_refresh or separate job exists | `MEDIUM` | Clarify job contract or add `feature_refresh` job |
| Demo-only mode guard | CLI parser includes production choice, then `_validate_rehearsal_args` blocks non-demo; future code may bypass validation | `run_daily_operation.py` | Some config guard tests | Production-mode rejection test for every side-effecting job | `HIGH` | Keep production unlock separate and assert rejection in CLI tests |
| Current / History / Derived reconvergence | Report/notification/audit derived artifacts are close to Current paths and can be reused accidentally | `report`, `notification`, `audit` models/checks; Phase15-C | Fixed Current/no-history tests exist | Negative tests that Report/Notification/Audit cannot become Submit or Planning source | `HIGH` | Keep derived artifacts marked `not_submit_source` and enforce at readers |
| Broker orders fallback production-equivalent flag | `broker_orders_fallback` exists as source and production-equivalent false logic must not be lost | `asset/builder.py`, `broker_readonly/normalizer.py`, `ledger/models.py` | Some broker fallback tests outside runtime_v2 | Runtime v2 regression that fallback source produces Review Required, not Current PASS | `HIGH` | Add runtime-level fallback source acceptance test |
| POST_SEND_UNKNOWN rerun/idempotency | State exists, but retry/rerun behavior is easy to break around pending consume and order ledger | `submit/pipeline.py`, state machine, architecture | Partial state-machine tests | Submit rerun test for POST_SEND_UNKNOWN and duplicate pending/order dedup | `BLOCKER` | Add idempotency regression before real submit expansion |
| Notification delivery idempotency | Payload-only is safe, but send-enabled future path needs delivery ledger and retry semantics | `notification/delivery_ledger.py`, Phase15-C | Delivery ledger component test | CLI delivery rerun test proving no duplicate real send | `HIGH` | Keep send disabled until delivery ledger Level3 evidence exists |
| Boundary values absent from fixtures | Existing fixtures are often 5 symbols, <=100k, and small SELL notionals; boundaries remain untested | Phase14-E53/E54; test files | Small-value component tests | Boundary suite: 99,999 / 100,000 / 100,001, zero cash, fractional/lot rounding, 6+ symbols, oversell | `HIGH` | Add hostile fixture set as Phase15 regression pack |
| Policy source absent from report/audit | Even when stage details include amounts, policy source/version may not flow to report/audit | `run_daily_operation.py`, report writer, Phase15-C | Report generation tests | Report/audit semantic test for active policy source and guard decision | `HIGH` | Thread policy source through manifest -> report -> audit |

## Coverage Summary

Phase15-A/B/C already cover the largest historical failure classes at the design and audit level:

- hidden Runtime policy/default prohibition
- BUY / SELL guard separation
- Submit Guard Active Policy Manifest requirement
- Review Level separation
- Evidence First / No Guess / Evidence Request rules
- tests/Broker Accepted/Report generated/Payload generated are not Acceptance
- Current fixed path and no History-derived Current
- fake adapter and test-only path cannot be Full Runtime PASS

However, historical regression coverage is not yet sufficient. The remaining critical gaps are:

1. Hidden caps are still implemented in the regular Runtime path.
2. Above-100k BUY and SELL liquidation regressions are missing.
3. Regular CLI regressions are missing for several acceptance-critical paths.
4. Submit active policy manifest is missing.
5. SELL liquidation is not Level3 accepted.
6. Notification remains payload/partial delivery lifecycle, not send acceptance.
7. launchd/demo operation readiness still needs an explicit runbook and evidence policy.
8. Production readiness must remain a separate locked phase.

## Phase15 Must-Not-Repeat Checklist

- [ ] Do not treat `tests pass` as Runtime Acceptance.
- [ ] Do not treat `Broker Accepted` as Runtime PASS.
- [ ] Do not treat `Report generated` as Report semantic PASS.
- [ ] Do not treat `Payload generated` as Notification PASS.
- [ ] Do not treat Component PASS as Flow PASS.
- [ ] Do not treat Flow PASS as Full Runtime Operation PASS.
- [ ] Do not treat fake adapter, fixture, monkeypatch, or test-only path as Full Runtime evidence.
- [ ] Do not accept CHECKPOINT-only output for jobs that must perform work.
- [ ] Do not allow Runtime-local hidden caps such as `max_order_amount=100000`.
- [ ] Do not allow Runtime-local hidden limits such as `max_orders=5` or `max_positions=5`.
- [ ] Do not allow `estimated_price=1000` or any price fallback without explicit source/unit/date/fallback policy.
- [ ] Do not allow Runtime-local cash buffer, investment ratio, exposure, or position sizing policy.
- [ ] Do not let Submit Guard rewrite Capital Allocation.
- [ ] Do not reuse BUY notional caps for SELL liquidation unless explicitly contracted.
- [ ] Do not SELL broker-only positions as Runtime-owned positions.
- [ ] Do not mark SELL PASS without Current-owned source, Broker quantity evidence, Broker/Execution evidence, Current update, Report, and Notification evidence.
- [ ] Do not use History, Report, Audit, or per-run artifacts as Current input.
- [ ] Do not directly edit Current to make an operation look complete.
- [ ] Do not use `broker_orders` as asset SoT.
- [ ] Do not save raw broker request, raw broker response, or secrets in artifacts.
- [ ] Do not auto-resend after `POST_SEND_UNKNOWN`.
- [ ] Do not collapse Notification Payload, Queue, Sender, Delivery Result, Audit, and Real Send into one PASS label.
- [ ] Do not bootstrap launchd before Runtime Level3 acceptance and runbook readiness.
- [ ] Do not unlock Production from Demo evidence alone.
- [ ] Do not ask Operator for a large command bundle when evidence is missing; request the minimum command needed.

## Evidence Needed Later

The following are intentionally not executed in Phase15-D, but should be requested later as minimal evidence when Phase15 reaches operational testing:

```text
python3 -m ai_fund_lab_v2.runtime_v2.cli.run_daily_operation --job morning
python3 -m ai_fund_lab_v2.runtime_v2.cli.run_daily_operation --job submit
python3 -m ai_fund_lab_v2.runtime_v2.cli.run_daily_operation --job execution
python3 -m ai_fund_lab_v2.runtime_v2.cli.run_daily_operation --job sell_planning
```

These commands should only be run in the appropriate demo/safe mode with the Phase15 guard fixes, explicit policy manifest, and operator approval conditions in place.

## Final Judgment

```text
PHASE15D_HISTORICAL_REGRESSION_COVERAGE_AUDIT_COMPLETE
```
