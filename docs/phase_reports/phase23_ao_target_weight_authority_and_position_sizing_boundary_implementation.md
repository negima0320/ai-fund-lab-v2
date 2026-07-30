# Phase23-AO Production-common Target Weight Authority and Position Sizing Boundary Implementation

## Primary Judgment

```text
PHASE23_AO_TARGET_WEIGHT_AUTHORITY_AND_POSITION_SIZING_BOUNDARY_IMPLEMENTATION_SHORT_VALIDATION_PASS
```

## Scope

Phase23-ANで確定した境界契約をProduction-common実装へ反映した。

- Portfolio Constructionが`target_weight`を生成する。
- Position Sizingは`target_weight`を唯一の正準weight入力として消費する。
- `runtime_opportunity_score`はranking / attribution / observabilityに限定する。
- `allocation_quality_score` / legacy `quality_score` pathはPosition Sizingのweight算出に使わない。
- BUY、最低1件、最低1単元は保証しない。

Historical fresh-run、1BD、10BD、20BD、Broker Write、J-Quants取得は実施していない。

## Existing Target Weight Method Review

既存実装では、Portfolio ConstructionからPosition Sizingへ渡す明示的な`target_weight` Authorityが存在せず、Position Sizing側がquality / score系の解決に依存しやすい構造だった。

Phase23-AOでは以下を禁止として確認した。

- raw score proportional weight
- clamp / sigmoid / min-max / percentile変換
- negative-to-zeroをweight transformとして扱うこと
- quality scoreをtarget weight aliasとして読むこと

Evidence:

```text
reports/phase23_ao_target_weight_authority_and_position_sizing_boundary_implementation/existing_weight_method_review.json
```

## Selected Weight Method

採用方式:

```text
production_v1_equal_weight_target_allocation
```

定義:

```text
target_gross_exposure / resolved_target_member_count
single_name_weight_capで上限制御
```

この方式はraw opportunity scoreをweightへ比例変換しない。scoreは候補順序・選抜・説明用のauthorityとして保持される。

## Portfolio Construction Implementation

`portfolio_construction.py`にProduction-commonのTarget Weight Authority生成を追加した。

主な出力:

- `target_membership`
- `target_weight`
- `target_weight_authority`
- `target_weight_resolution`
- `target_weight_method`
- `target_gross_exposure`
- `resolved_target_member_count`
- `single_name_weight_cap`
- `total_target_weight`

Lineageとして、business date、policy reference、dynamic position count reference、opportunity reference、existing position reference、source artifact hashesを保持する。

## Position Sizing Implementation

`position_sizing.py`に`resolve_target_weight()`を追加し、Position Sizingのweight入力を`target_weight`へ固定した。

解決成功時:

```text
target_weight
↓
target_notional
↓
target_quantity_candidate
↓
quantity_delta_candidate
```

解決失敗時:

```text
TARGET_WEIGHT_UNAVAILABLE
REVIEW_REQUIRED
target_notional = 0
```

minimum notional未満の場合は、`target_weight`と`target_notional`はAuthority解決結果として保持し、`target_quantity_candidate = 0` / `NO_ORDER_MINIMUM_NOTIONAL_UNMET`で執行不可を表現する。

## Raw Score / Weight Separation

`runtime_opportunity_score`を変更しても、同一`target_weight` authorityが渡る限り、Position Sizing結果の`target_weight`、`target_notional`、`target_quantity_candidate`は変化しないことを確認した。

Evidence:

```text
reports/phase23_ao_target_weight_authority_and_position_sizing_boundary_implementation/raw_score_weight_separation_validation.json
```

## Legacy Quality Path Classification

legacy quality pathは以下に分類した。

```text
NON_CANONICAL_OBSERVABILITY
```

Position Sizingのweight算出には使用しない。

## Negative Score Behavior

負の新規opportunityはtarget membershipへ強制採用しない。

```text
target_membership = false
target_weight = 0
weight_reason = negative_opportunity_not_selected
```

既存positionのPM retain等は別authorityで扱う。

## Zero-trade Behavior

target count zeroやexposure zeroでは、明示的にzero allocationを解決する。

BUY、最低1件、最低1単元は保証しない。

## Existing Position Delta

Position Sizingは`current_quantity`と`target_quantity_candidate`から`quantity_delta_candidate`を生成する。

```text
quantity_delta_candidate = target_quantity_candidate - current_quantity
```

## Short Validation

実施済み:

```text
PYTHONPYCACHEPREFIX=/private/tmp/ai_fund_lab_v2_pycache_phase23ao python3 -m py_compile src/ai_fund_lab_v2/strategy/portfolio_construction.py src/ai_fund_lab_v2/strategy/position_sizing.py
```

```text
python3 -m pytest tests/strategy/test_phase22_e_portfolio_construction.py tests/strategy/test_phase22_j_position_sizing.py
```

結果:

```text
46 passed
```

```text
python3 -m pytest tests/strategy/test_phase22_e_portfolio_construction.py tests/strategy/test_phase22_j_position_sizing.py tests/strategy/test_phase22_g_runtime_planning.py tests/strategy/test_phase22_pr_dynamic_capacity_asset_proportionality.py tests/strategy/test_phase22_qe_input_materialization.py
```

結果:

```text
71 passed
```

## Existing Run Preservation

以下の既存Runは読み取りhash確認のみ実施した。

```text
runtime-test-historical-smoke-20260729T224044624059Z
runtime-test-historical-smoke-20260729T220208972293Z
```

Runtime再実行、artifact mutation、reclassificationは実施していない。

## Modified Files

```text
src/ai_fund_lab_v2/strategy/portfolio_construction.py
src/ai_fund_lab_v2/strategy/position_sizing.py
tests/strategy/test_phase22_e_portfolio_construction.py
tests/strategy/test_phase22_j_position_sizing.py
tests/strategy/test_phase22_g_runtime_planning.py
tests/strategy/test_phase22_pr_dynamic_capacity_asset_proportionality.py
```

## Evidence

```text
reports/phase23_ao_target_weight_authority_and_position_sizing_boundary_implementation/
```

作成済み:

```text
existing_weight_method_review.json
selected_weight_method.json
target_weight_contract_validation.json
portfolio_construction_output_validation.json
position_sizing_input_validation.json
raw_score_weight_separation_validation.json
legacy_quality_path_classification.json
negative_score_validation.json
zero_trade_validation.json
existing_position_delta_validation.json
al_style_reproduction.json
no_forced_buy_validation.json
targeted_regression_results.json
expanded_regression_results.json
modified_file_inventory.json
existing_run_hash_preservation.json
```

## Remaining Gaps

長時間Runtime validationは未実施。OperatorによるEvidence Review後に、必要なら1BD以上のRuntime validationを実施する。

## Next Operator Action

ChatGPT Evidence Review後、OperatorがProduction-equivalent runtime validationへ進むか判断する。
