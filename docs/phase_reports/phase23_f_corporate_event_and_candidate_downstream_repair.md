# Phase23-F: Corporate Event Coverage and Candidate Downstream Eligibility Repair

## Primary Judgment

`PHASE23_F_CONTRACT_REPAIR_COMPLETE_SOURCE_IMPLEMENTATION_REMAINS`

## Secondary Judgments

- `LONG_RUNTIME_VALIDATION_NOT_RUN`
- `HORIZONTAL_AUDIT_PASS`
- `READY_FOR_CHATGPT_EVIDENCE_REVIEW`

## Root Cause再確認

Phase23-A evidenceから、`P23A-CE-001` は Corporate Event の source coverage が `PARTIAL` のまま `REVIEW_REQUIRED / UNRESOLVED` として伝播していたことを再確認した。これは eventなしではなく event不明/部分Authorityである。

`P23A-CAND-001` は、2026-07-10 の Candidate / Opportunity source artifact が各50行存在し、Accepted GenerationもPITで解決していた一方、Strategy Shadow側が `candidate_decisions.json` の `rows` payloadを読まず、下流membershipが0件または `SOURCE_UNAVAILABLE` として扱われていたことを再確認した。

## Corporate Event Source Inventory

J-Quantsのみを対象に、`listed_issues` と `trading_calendar` は既存実装済み、`earnings_schedule`、`financial_statements`、`corporate_actions` は design-referenced but not implemented と分類した。外部Sourceは追加していない。

## Corporate Event Coverage Contract

`coverage_contract` と `source_coverage_semantics` をCorporate Event artifactに追加した。

- `FULL`: event absence authorized
- `PARTIAL`: event-sensitive rules only review/blocking scope
- `NONE / UNRESOLVED`: event absence not authorized

`PARTIAL` を `PASS` に変換せず、missing sourceを no-event に変換しない。

## Downstream Blocking Scope

Corporate Event `PARTIAL` は下流のevent-independent calculationを `CALCULATION_ALLOWED_WITH_REVIEW` として継続可能にし、event-sensitive ruleはreview対象として残す。Portfolio Policy / Construction / Runtime Planning のProduction接続やBroker Writeは変更していない。

## Candidate Pipeline修正内容

`shadow_runtime._ai_output_summary` で `rows` payloadを正式に読み込み、Candidate / Opportunity downstream adapterとして以下を行単位でMaterializeするよう修正した。

- `security_code`, `symbol`
- `business_date`, `feature_date`, `source_row_date`
- `candidate_id` / `opportunity_id`
- `accepted_generation_id`, `accepted_generation_hash`
- `feature_contract_hash`
- `technical_features_join_key`
- `eligibility_status`, `candidate_membership_status`
- `rejection_reason`, `reason_codes`
- `source_hash`, `artifact_hash`

Candidateを非ゼロにする固定行注入はしていない。既存source rowを正式に下流Contractへ変換した。

## Candidate Row-count Decomposition

2026-07-10 evidenceでは Candidate source 50行、Opportunity source 50行。修正後のadapterは `rows` を読むため、Candidate adapter output 50行、Opportunity adapter output 50行として保持する。

## Candidate Rejection Reason Distribution

adapter summaryに `rejection_reason_distribution` を追加した。2026-07-10 fixture相当では `ACCEPTED: 50`。0件時もsource missing / schema mismatch / PIT invalid / policy rejected等の理由分布を保持する契約とした。

## Portfolio Policyとの関係

`configs/strategy/portfolio_policy.json` のAuthorityは維持。`maximum_position_weight=0.25` の正式Authorityを固定fallbackに置換していない。Runtime position/cashは運用制約としてのみ扱い、市場予測特徴量へ混入させていない。

## Accepted Generation / PIT結果

Phase23-Bの business-date-bound resolverを維持し、`resolve_accepted_generation(runtime_root, business_date=business_date)` を利用。Candidate row / Opportunity row / feature_date は `<= business_date`、latest fallback / future generation / future feature は不使用。

## Production / Demo / Historical共通性

Historical専用if、Demo強制Candidate、Production専用Source要求はいずれも追加していない。同一adapterとcoverage contractで成立する。

## Silent Default Audit

`candidate rows missing -> []` のsilent fallbackを修正し、`rows` payloadを明示的に読む。Corporate Event missing/PARTIALを no-event に変換しない。policy missing fixed default、latest artifact fallback、exception empty artifactは追加していない。

## Horizontal Audit

Corporate Event producer/validator、Portfolio Policy、Dynamic Position Count、Dynamic Cash Exposure、Portfolio Construction、Capital Deployment、Position Sizing、Opportunity、Candidate Decision、Strategy Shadow、Data Readiness、Accepted Generation、Current Holdings/PM、Runtime Planning、Consumer Eligibilityを確認し、Phase23-F範囲では `PASS`。

## 修正対象ファイル

- `src/ai_fund_lab_v2/strategy/corporate_event.py`
- `src/ai_fund_lab_v2/strategy/shadow_runtime.py`
- `tests/strategy/test_phase22_aa_corporate_event.py`
- `tests/runtime_v2/test_phase22_p_strategy_shadow_wiring.py`

## 成果物

- Human: `docs/phase_reports/phase23_f_corporate_event_and_candidate_downstream_repair.md`
- Machine: `reports/phase_reports/phase23_f_corporate_event_and_candidate_downstream_repair.json`
- Evidence: `reports/phase23_f_corporate_event_and_candidate_downstream_repair/`

## 短時間テスト結果

- `tests/strategy/test_phase22_aa_corporate_event.py tests/runtime_v2/test_phase22_p_strategy_shadow_wiring.py`: 11 passed
- Phase23-B〜E regression subset: 84 passed
- `compileall`: PASS
- JSON validation: PASS

## Controlled Short Validation

追加の長期Runtime profileは実施していない。局所fixture/unit regressionのみ実施した。

## 未実施長時間テスト

10BD / 20BD / 1年 / 3年 Runtime Testは実施していない。

## 残存Gap

J-Quants `earnings_schedule`、`financial_statements`、`corporate_actions` のcanonical ingestion実装はPhase23-Fでは追加していない。そのためPrimary Judgmentは source implementation remains とする。

## 10BD再実行可否

`READY_FOR_10BD_RERUN_AFTER_FINAL_HORIZONTAL_REVIEW`

## 次Task候補

- Independent Horizontal Evidence Review
- J-Quants Corporate Event source implementation task

## Runtime Switch禁止状態

Runtime Switchなし。Broker Writeなし。Production/Demo Submitなし。
