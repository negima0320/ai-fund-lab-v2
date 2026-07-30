# Phase23-AQ Portfolio Policy Consolidation

## Primary Judgment

`PHASE23_AQ_PORTFOLIO_POLICY_CONSOLIDATION_SHORT_VALIDATION_PASS`

## Supporting Judgment

`PORTFOLIO_POLICY_CANONICAL_OWNER`, `TARGET_POSITION_COUNT_OWNER`, `TARGET_GROSS_EXPOSURE_OWNER`, `CASH_RESERVE_OWNER`, `RUNTIME_WIRING_SIMPLIFIED`, `ARTIFACT_REDUCTION`, `PRODUCTION_COMMON_VALIDITY`, `READY_FOR_AR`

## Scope

AQではPortfolio Policy、Dynamic Position Count、Dynamic Cash / Exposureのみを対象にした。Portfolio Construction、Position Sizing、Runtime Planning、Strategy Planning Authority、Pending、Submit、Safety、Broker、Historical Runtimeの実装変更は行っていない。

## Implementation

Portfolio Policyをportfolio-level decision ownerとして更新し、`target_position_count`、`target_gross_exposure_ratio` / `target_gross_exposure`、`cash_reserve_ratio` / `cash_reserve`、`single_name_weight_cap`、`deployment_posture`をPortfolio Policy artifact上でmaterializeする契約にした。

Dynamic Position CountとDynamic Cash / Exposureは独立Runtime moduleではなく、Portfolio Policy内部resolverとして既存ロジックを再利用する。公開Runtime artifact生成は削除し、lineageはPortfolio Policyの`source_hashes`と`upstream_artifacts.internal_policy_resolvers`に保持する。

Shadow Runtimeの公開call pathは `Market Context -> Portfolio Policy -> Position Management -> Portfolio Construction -> Position Sizing` に整理した。Position Sizingへは互換引数名のままPortfolio Policy summaryを渡すため、Position Sizing実装自体は変更していない。

## Artifact Policy

`dynamic_position_count.json` と `dynamic_cash_exposure.json` はcanonical runtime artifactから除外した。既存Evidence review用に明示的に渡された旧artifactはObservabilityで`NON_CANONICAL_OBSERVABILITY`として読むが、strategy decision pathには使用しない。

## Validation

- compile: PASS
- targeted regression: 37 passed
- expanded regression: 103 passed
- Runtime wiring regression: PASS
- JSON evidence generation: PASS

Out-of-scope観測として、`tests/runtime_v2/test_phase23_i_strategy_planning_authority.py` は3件失敗を確認した。理由は `review_required_quantity_authority` / `INCOMPATIBLE_SCHEMA` 系で、AQで明示的に除外されたStrategy Planning Authority境界のため、AQ acceptance blockerにはしない。

## Existing Run Preservation

指定runへの書き込みは行っていない。hash evidenceは `existing_run_hash_preservation.json` に読み取り記録した。

## Deliverables

- Human: `docs/phase_reports/phase23_aq_portfolio_policy_consolidation.md`
- Machine: `reports/phase_reports/phase23_aq_portfolio_policy_consolidation.json`
- Evidence: `reports/phase23_aq_portfolio_policy_consolidation/`

## Next

Phase23-ARでEvidence Review可能。
