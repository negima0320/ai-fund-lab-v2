# Phase23-L: Historical Accepted Generation Authority Resolution Repair

## Primary Judgment

`PHASE23_L_PARTIAL_REPAIR_10BD_GATE_NOT_READY`

Business-date-bound resolver gapはProduction-commonに修正した。`business_date`指定時はcurrent pointerだけでなく、Runtime Authority配下のAccepted Generation履歴とgeneration manifest directoryをPIT候補として評価する。

一方、対象10BD期間 `2026-06-29` から `2026-07-10` には、canonical `.runtime` Authority上でPIT eligibleなAccepted Generationが存在しない。現在のAccepted Generationは `accepted_at=2026-07-20T00:00:00+09:00` / `effective_from=2026-07-20T00:00:00+09:00` のため、対象期間への遡及適用は禁止のままfail-closedとする。

## Secondary Judgments

- `CURRENT_POINTER_ONLY_RESOLVER_GAP_REPAIRED`
- `NO_PIT_ELIGIBLE_ACCEPTED_GENERATION_FOR_TARGET_PERIOD`
- `FUTURE_GENERATION_REJECTION_MAINTAINED`
- `CONTROLLED_1BD_DAILY_ENTRYPOINT_PASS`
- `LONG_RUNTIME_VALIDATION_NOT_RUN`
- `RUNTIME_SWITCH_NOT_PERFORMED`
- `BROKER_WRITE_NOT_PERFORMED`

## Accepted Generation保存構造

確認したRuntime Authority store:

- Current pointer: `.runtime/runtime_state/accepted_buy_ai_bundle.json`
- Accepted Generation manifests: `.runtime/ai_lifecycle/generations/*/accepted_generation_manifest.json`
- Authority history ledger: `.runtime/ai_lifecycle/authority_history/accepted_generation_history.jsonl`
- Promotion candidates: `.runtime/artifact_registry/promotion_candidates/`

Promotion candidatesはRuntime Authorityとして使用しない。Reports配下の履歴はEvidenceとしてのみ扱い、Runtime resolverのAuthorityには使わない。

## Historical Generation Timeline

canonical `.runtime` 上で確認できるAccepted Generationは `phase19_aq_accepted_generation_641e6e313543f013`。

- `accepted_at`: `2026-07-20T00:00:00+09:00`
- `effective_from`: `2026-07-20T00:00:00+09:00`
- target 10BD全日より未来

## 対象10日Eligibility結果

全10日で `NO_ACCEPTED_GENERATION_EXISTED_AS_OF_DATE` 相当。

対象日:

```text
2026-06-29
2026-06-30
2026-07-01
2026-07-02
2026-07-03
2026-07-06
2026-07-07
2026-07-08
2026-07-09
2026-07-10
```

全日でPIT eligible candidate countは0。未来Acceptedを許可せず、fail-closed。

## Resolver Call Graph

修正前:

```text
resolve_accepted_generation(runtime_root, business_date)
→ runtime_state/accepted_buy_ai_bundle.json
→ current pointer manifest
→ accepted_at/effective_from PIT check
→ futureなら REVIEW_REQUIRED
```

修正後:

```text
resolve_accepted_generation(runtime_root, business_date)
→ current pointer候補
→ ai_lifecycle/authority_history/accepted_generation_history.jsonl
→ ai_lifecycle/generations/*/accepted_generation_manifest.json
→ PIT / revoked / superseded / expired / hash / member binding検査
→ deterministic selection
```

`business_date`なしの通常current pointer resolverは互換維持。

## PIT Selection Contract

任意business date Dについて、以下を満たすGenerationのみeligible:

- `accepted_at <= D`
- `effective_from <= D`
- `effective_until`未設定、またはD以前に失効していない
- `revoked_at` / `superseded_at` がD時点で有効化していない
- promotion candidateではない
- manifest aggregate hashが一致
- candidate/opportunity model artifact hashが一致
- scaler fieldがある場合はscaler artifact/hashも一致
- feature schema hashがある場合はbindingを保持

複数eligible時は `max(effective_from_date, accepted_at_date, generation_id)` で決定する。

## Runtime Integration結果

controlled 1BD daily morning entrypointで確認した。

```text
run_daily_operation.main --job morning
→ business-date-bound resolver
→ old-generation selected
→ Strategy Planning Authority
→ Pending Order Plan
```

Broker Writeなし。Runtime Switchなし。

## 10BD Rerun Gate

`NOT_READY_FOR_OPERATOR_PRODUCTION_EQUIVALENT_10BD_RERUN`

理由:

- target 10BD全日にPIT eligible Accepted Generationが存在しない。
- 現在のAccepted Generationは2026-07-20開始で、対象期間へ遡及適用不可。
- target 10BDは未再実行。

## Evidence

Evidence directory:

`reports/phase23_l_historical_accepted_generation_authority_resolution_repair/`

Human:

`docs/phase_reports/phase23_l_historical_accepted_generation_authority_resolution_repair.md`

Machine:

`reports/phase_reports/phase23_l_historical_accepted_generation_authority_resolution_repair.json`

## Short Tests

実施:

```text
python3 -m pytest tests/runtime_v2/test_phase19_ad_u1_a_accepted_generation_resolver.py tests/runtime_v2/test_phase23_l_historical_accepted_generation_entrypoint.py -q
PYTHONPYCACHEPREFIX=/private/tmp/ai_fund_lab_pycache python3 -m compileall -q src/ai_fund_lab_v2/runtime_v2/accepted_generation_resolver.py tests/runtime_v2/test_phase23_l_historical_accepted_generation_entrypoint.py
python3 -m pytest tests/runtime_v2/test_phase23_i_strategy_planning_authority.py tests/runtime_v2/test_phase23_j_strategy_authority_gate.py tests/strategy/test_phase22_d_position_management.py -q
```

結果:

```text
17 passed
compile PASS
19 passed
```

## Not Run

10BD / 20BD / 1y / 3y Runtime Test、Production Submit、Demo Submit、Broker Write、Runtime Switchは実施していない。
