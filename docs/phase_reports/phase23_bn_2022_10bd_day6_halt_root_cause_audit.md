# Phase23-BN 2022年10BD Day-6 HALT Root Cause Audit

## Primary Judgment

`PHASE23_BN_2022_10BD_DAY6_HALT_ROOT_CAUSE_AUDIT_COMPLETE`

## Mandatory First Confirmation

- halt_business_date: `2022-07-08`
- halt_stage: `morning`
- inner_runtime_exit_code: `20`
- aggregate exit_code: `30`
- direct_halt_reason: `strategy_planning_authority_unresolved`
- lowest_level_reason: `strategy_plan_price_missing:94320`
- first_invalid_artifact: `daily/2022-07-08/morning/strategy_planning_authority_evidence.json`

## Root Cause

Day-6で初めて実行可能なBUY planが生成された。対象は`94320`で、Runtime Planningは以下を出力していた。

- `planning_intent = BUY_NEW`
- `order_side_intent = BUY`
- `planned_quantity = 1100`
- `quantity_status = RESOLVED_EXECUTABLE`

一方、Strategy Planning AuthorityがPending itemを生成する際、planから価格を解決できず、`strategy_plan_price_missing:94320`でfail-closedした。

重要なのは、Position Sizing側では価格は欠損していない点である。`position_sizing.json` の`94320`には以下が存在する。

- `reference_price = 153.2`
- `reference_price_resolution.status = PASS`
- `reference_price_authority.PIT_status = PASS`
- source path: run-scoped Historical As-of OHLCV

したがってRoot Causeは、Reference Priceそのものではなく、`Position Sizing -> Runtime Planning -> Strategy Planning Authority` の executable plan price authority propagation gapである。

## Day-by-day Differential

完了5営業日では、全て no submitted / no fills / no positions だった。SELL経路も未到達。

最初の実質差分は`2022-07-08`で、Portfolio Policyが`target_position_count=1`になり、初めて`BUY_NEW`が発生したこと。

`2022-07-07`:

- target_position_count: `0`
- Runtime Planning: `NO_ORDER`のみ
- Strategy Planning Authority: `NO_ORDER_AUTHORIZED`

`2022-07-08`:

- target_position_count: `1`
- Runtime Planning: `94320 BUY_NEW planned_quantity=1100`
- Strategy Planning Authority: `REVIEW_REQUIRED`

## Classification

- `PRODUCTION_CONTRACT_VIOLATION`
- `SUBMIT_GUARD_FAILURE`

該当しないもの:

- Multi-day Position continuity failureではない
- Current Position membership failureではない
- SELL Planning failureではない
- Pending lifecycle failureではない
- Historical source binding recurrenceではない
- Cash/Ledger/Valuation continuity failureではない

## BM Source Authority

BMで修正したHistorical As-of source authorityは6日目も維持されていた。

- run-scoped Historical authority: `PASS`
- latest fallback: `false`
- Source Manifest PIT: `PASS`
- future row rejection: `0`

## Trading State Integrity

`TRADING_STATE_VALID = YES`

完了5営業日はno-order/no-fillのため、cash/ledger/position/current valuationは整合している。Run state破損は見えない。ただし未修正でresumeすると同じmorning blockerへ戻るため、`RESUME_SAFE = NO_BEFORE_REPAIR`。

## Required Next Action

`READY_FOR_2022_10BD_RUNTIME_RERUN = NO`

次Task候補:

`Phase23-BO Runtime Planning Executable Plan Price Authority Propagation Repair`

Runtime Planningの実行可能BUY/SELL planへ、Position Sizingの`reference_price` / `reference_price_authority` / `reference_price_resolution`を伝播する、またはStrategy Planning Authorityが`quantity_reference`からPosition Sizingの価格Authorityを解決する最小修正が必要。

## Deliverables

- Machine: `reports/phase_reports/phase23_bn_2022_10bd_day6_halt_root_cause_audit.json`
- Evidence: `reports/phase23_bn_2022_10bd_day6_halt_root_cause_audit/`

## Prohibited Actions

Production code変更、test変更、Runtime rerun、fresh-run、resume、Broker Write、J-Quants取得は実施していない。
