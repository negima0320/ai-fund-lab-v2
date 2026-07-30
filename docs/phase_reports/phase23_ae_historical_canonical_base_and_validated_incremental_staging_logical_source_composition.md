# Phase23-AE: Historical Canonical Base + Validated Incremental Staging Logical Source Composition

## Primary Judgment

`PHASE23_AE_HISTORICAL_CANONICAL_BASE_AND_VALIDATED_INCREMENTAL_STAGING_COMPOSITION_SHORT_VALIDATION_PASS`

## Phase23継続確認

Phase23-AD の J-Quants acquisition staging を canonical へ昇格せず、Historical logical input materialization でのみ compose する契約として修正した。既存HALT run は read-only で保持した。

## Exact Root Cause

Current resolver は target date を持つ acquisition staging を単一sourceとして選択し、canonical base の 2026-02-16..2026-07-14 lookback を合成しなかった。そのため 2026-07-15 の staging 3営業日だけでは calendar/lookback が不足した。

## Current Resolver Audit

単一source候補では operations canonical は target quote missing、acquisition staging は targetありだが warmup/calendar不足。修正後は単一PASSがなければ validated composition を試行する。

## Source Composition Contract

優先順は single source PASS、validated canonical base + validated incremental staging overlay、best single source blocker、source unavailable。canonical physical data は mutation しない。

## Staging Eligibility

`state.json` / `plan.json` / `final_validation` / normalized hash / duplicate=0 / future=0 / lineage PASS / schema runtime compatible を確認し、未検証stagingは fail-closed。

## Normalized Composition

Status: `PASS`。Logical max date は 2026-07-15、future rows は materialized logical から除外。

## Raw Composition

Status: `PASS`。normalized と同じ business-date cutoff で materialize。

## Trading Calendar Composition

Status: `PASS`。`HolDiv` / `HolidayDivision` の列差分と数値表現を吸収し、lookback authority を compose。

## Revision Semantics

Overlay wins by business key。`Date, Code`、calendar は `Date` で重複排除し、revision summary に overlay new/overlap/replaced keys と hashes を保存。

## Raw / Normalized Consistency

Status: `PASS`。target date availability が raw/normalized で一致。

## Logical Input Materialization

Evidence配下に isolated logical input を生成。canonical base と staging overlay は logical view にのみ反映し、`.runtime/operations` は変更していない。

## Evidence Truthfulness

既存HALT evidence は read-only。新しい PASS 判定は isolated reproduction と short regression の証跡として別ディレクトリに保存。

## 2026-07-15 Short Reproduction

`status=PASS` / `reason=historical_asof_composed_authority_ready` / `composition_used=True`。

## Regression Matrix

既存回帰10件に AE 2件を追加し、合計12件 PASS。

## Modified Files

- `src/ai_fund_lab_v2/runtime_v2/historical_support/asof.py`
- `tests/runtime_v2/test_phase17_l_historical_asof_and_evidence_isolation.py`
- Phase23-AE report/evidence files

## Short Validation

- py_compile: PASS
- targeted pytest: `12 passed in 1.91s`

## 未実施事項

J-Quants live fetch、canonical mutation/copy/replace/promotion、Runtime Switch、Broker Write、1BD fresh runtime、10BD、20BD、1y、3y、resume/abandon は未実施。

## Existing HALT Evidence Preservation

`reports/runtime_tests/runs/runtime-test-historical-smoke-20260729T082413647685Z/` は読み取りのみ。hash/status/reason は `existing_halt_evidence_preservation.json` に記録。

## 次のOperator Action

ChatGPT Evidence Review 後、Operator が 2026-07-15 の 1BD Historical rerun を実施可能。10BDは本Taskでは実施不可。
