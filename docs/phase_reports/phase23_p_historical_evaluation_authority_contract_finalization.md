# Phase23-P: Historical Evaluation Authority Contract Finalization

## Primary Judgment

`PHASE23_P_HISTORICAL_EVALUATION_AUTHORITY_CONTRACT_FINALIZED_SHORT_VALIDATION_PASS`

## Secondary Judgments

- Production / Demo の date-local Accepted Generation Authority は維持した。
- Historical Runtime は run 開始時に Human Accepted 済み Accepted Generation を 1 件固定する契約へ正式化した。
- Historical business date への `accepted_at` / `effective_from` 比較は、Historical fixed authority scope では適用しない。
- Historical の日次 PIT 対象は Market Data / Financial Data / Corporate Event / Feature / Calendar に限定した。
- Strategy / AI Consumer / Planning / PM / Sizing / Safety / Submit Decision は Production-common のまま維持した。
- Historical 専用 Strategy、Historical 専用 AI 判断、latest fallback、Runtime Switch、Broker Write は追加していない。
- Historical Performance は Runtime Performance Evaluation であり、Strict Out-of-Sample AI Performance とは区別する。

## Contract Finalization

Historical Runtime Evaluation は、現在完成している Production-common Runtime を historical point-in-time input に流し、判断・売買・資金管理・Performance を評価するものとして正式化した。

Run 開始時に次を保存する。

```text
reports/runtime_tests/runs/<run_id>/historical_evaluation_authority.json
```

この Authority は以下を保持する。

```text
generation_id
candidate model
opportunity model
scaler
feature schema
accepted decision
accepted_at
effective_from
training cutoff
dataset revision / freshness metadata
component hashes
run_authority_hash
evaluation_mode
evaluation_period
training_overlap
```

Run 中に current pointer が変わっても、Historical Run は `historical_evaluation_authority.json` と `run_authority_hash` を検証し続ける。

## Production Authority

Production / Demo は従来どおり。

```text
accepted_at <= business_date
effective_from <= business_date
```

`resolve_accepted_generation(runtime_root, business_date=...)` の date-local selection は維持した。

## Historical Authority

Historical は run-start fixed authority を明示的に渡す。

```text
--historical-evaluation-authority <path>
```

BUY AI producer と Strategy shadow は、この固定 Authority を使う場合だけ Accepted Generation の business-date 比較を行わない。Production / Demo ではこの引数を拒否する。

## Future Information Boundary

禁止:

```text
future OHLCV
future financial data
future corporate event
future feature
latest fallback
Historical-only Strategy
Historical-only AI judgment
Accepted日時改ざん
Broker Write
Runtime Switch
```

許可:

```text
Run開始時に固定したHuman Accepted Generation
```

ただしこれは Strict OOS AI Performance ではなく Runtime Performance Evaluation として扱う。

## Summary Contract

Final Summary に以下を追加した。

```text
evaluation_mode
training_cutoff
evaluation_period
training_overlap
```

training overlap がある場合、`STRICT_OOS` とは表示しない。

## Modified Files

- `docs/02_architecture/historical_runtime_test_contract.md`
- `docs/02_architecture/runtime_architecture_v2.md`
- `docs/02_architecture/ai_training_and_generation_lifecycle.md`
- `docs/02_architecture/runtime_test_specification.md`
- `scripts/runtime_test.py`
- `src/ai_fund_lab_v2/runtime_v2/accepted_generation_resolver.py`
- `src/ai_fund_lab_v2/runtime_v2/buy_ai/producer.py`
- `src/ai_fund_lab_v2/runtime_v2/cli/run_daily_operation.py`
- `src/ai_fund_lab_v2/strategy/shadow_runtime.py`
- `tests/runtime_v2/test_phase19_ad_u1_a_accepted_generation_resolver.py`
- `tests/runtime_v2/test_phase23_p_historical_evaluation_authority.py`

## Evidence

Evidence directory:

```text
reports/phase23_p_historical_evaluation_authority_contract_finalization/
```

Key evidence:

- `run_start_authority_fixed.json`
- `acceptance_gate_validation.json`
- `production_authority_maintained.json`
- `historical_authority_contract.json`
- `current_pointer_change_ignored.json`
- `historical_input_pit_boundary.json`
- `production_common_runtime_matrix.json`
- `summary_contract.json`
- `short_validation_results.json`
- `modified_files.json`

Machine report:

```text
reports/phase_reports/phase23_p_historical_evaluation_authority_contract_finalization.json
```

## Short Validation

実施済み:

```text
py_compile
targeted pytest
run-start authority materialization
authority gate validation
```

結果:

```text
20 passed
Authority validation PASS
```

## Not Performed

以下は実施していない。

```text
10BD
20BD
1年
3年
4年
Runtime Switch
Broker Write
データMaterialization
```

## 10BD Gate

`READY_FOR_OPERATOR_PRODUCTION_EQUIVALENT_10BD_RERUN`

根拠:

- Historical Authority 固定済み。
- Production-common Runtime chain 維持。
- Historical input PIT 境界を契約化。
- Acceptance Gate PASS。
- 今回範囲の known blocker なし。

10BD はユーザー実行待ち。
