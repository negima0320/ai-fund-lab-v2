# Phase32-AC Position Campaign Identity Authority Split Root-Cause Deep Audit

## Executive Summary

This READ-ONLY audit examined `runtime-test-historical-extended-smoke-20260827T055917572299Z` after the Phase32-AB finding that 83060's 2022-10-03 BUY / 2022-10-04 EXIT lifecycle had three different campaign identities:

- PM daily snapshot: `pc-e6d857c27b1d386e-83060-0001`
- Strategy / Strategy Intelligence: `pc-621be524366e3fcd-83060-0001`
- Prior-exit reconstruction fallback: `ledger-derived-83060-0001`

The split is a real contract defect. Architecture says `positions/position_campaigns.json` is the canonical campaign identity / lifecycle authority, campaign identity represents one continuous open-position lifecycle, ADD / partial REDUCE / EXIT inherit that identity, and REENTRY after full EXIT starts a new deterministic campaign under the same authority. Strategy Intelligence must not silently invent a duplicate campaign id when canonical campaign identity is absent or conflicting.

The observed root cause is multiple independent campaign generators crossing authority boundaries:

1. Strategy Shadow canonical pre-action lifecycle bootstrap generates `pc-621...` from strict-prior execution identity.
2. Runtime-test performance observability generates `pc-e6d...` from `sha256(run_id)` plus symbol/sequence and uses that id in `daily/execution/fills.json`, `daily/execution/realized_slices.json`, and `daily/position_management/pm_decisions.json`.
3. Prior-exit semantic bridge generates `ledger-derived-83060-0001` only as a fallback when persistent execution rows do not carry a campaign id.

The strict-prior PM bridge itself is correctly trying to compare PM evidence against the closed execution campaign, but the actual evidence set is inconsistent: the PM snapshot campaign is `pc-e6d...`, the Strategy campaign is `pc-621...`, and the submitted/persistent execution path for 83060 has blank `position_campaign_id`. Therefore the bridge cannot match the PM EXIT reason to the prior close.

No code/config/runtime state was changed. The only file written by this audit is this report.

## Run Identity

| Field | Value |
|---|---|
| Run id | `runtime-test-historical-extended-smoke-20260827T055917572299Z` |
| Run status | `COMPLETED` in `run_state.json`; `REVIEW_REQUIRED` close summary |
| Period | 2022-10-03 through 2022-11-08 |
| Primary symbol | `83060` |
| Primary lifecycle | 2022-10-03 BUY, 2022-10-04 EXIT, later REENTRY candidate |

## Canonical Authority And Semantics

Evidence:

- `docs/02_architecture/strategy_intelligence_data_contract_v1.md:307-330`
- `docs/02_architecture/strategy_intelligence_architecture_v1.md:528-542`
- `docs/02_architecture/strategy_intelligence_architecture_v1.md:1324-1374`
- `docs/03_operations/runtime_test_command_guide.md:1228-1264`
- `docs/02_architecture/runtime_architecture_v2.md:979`

Canonical authority:

`positions/position_campaigns.json` is the canonical campaign identity and lifecycle-history authority at the decision-time / pre-action boundary. Persistent execution ledger is the accounting authority and must losslessly preserve available campaign/source decision provenance, but it is not supposed to invent a second campaign namespace. Current owns current quantity, average price, market value, and valuation-facing state; Current is not the campaign authority, but current rows must preserve a canonical campaign id when available so PM and planning can inherit it.

Campaign semantic:

`position_campaign_id` means one continuous open-position lifecycle. Initial `BUY_NEW` opens one campaign. Later BUY while the ledger campaign is open is ADD evidence on the same campaign. Partial SELL / REDUCE preserves the same campaign. Full EXIT closes that same campaign. A later BUY after the symbol is flat following a ledger-proven EXIT is REENTRY and starts a new campaign identity.

## 83060 BUY-Origin Trace

| Boundary | Artifact / Source | Observed `position_campaign_id` | Producer / Authority | Interpretation |
|---|---:|---|---|---|
| 2022-10-03 Candidate / PC | `daily/2022-10-03/strategy/portfolio_construction.json` | blank | Strategy pre-BUY candidate | Initial BUY candidate has no prior campaign. |
| 2022-10-03 Sizing | `daily/2022-10-03/strategy/position_sizing.json` | blank | Strategy sizing | Still pre-execution, no canonical open campaign yet. |
| 2022-10-03 Runtime planning | `daily/2022-10-03/strategy/runtime_planning.json` | blank | Strategy runtime planning | BUY_NEW plan does not carry a campaign id. |
| 2022-10-03 Pending / submit | `daily/2022-10-03/submit/runtime_manifest.json` | blank | Pending / submit | Pending item `strategy-222e83e9752ba16866cb`, side BUY, quantity 100; no campaign. |
| 2022-10-03 Execution fill observability | `daily/2022-10-03/execution/fills.json` | `pc-e6d857c27b1d386e-83060-0001` | `scripts/runtime_test.py` performance observability | Generated from run id hash, not from canonical pre-action campaign state. |
| 2022-10-04 Strategy Intelligence | `daily/2022-10-04/strategy/strategy_intelligence.json` | `pc-621be524366e3fcd-83060-0001` | Strategy Shadow strict-prior ledger bootstrap | Generated from strict-prior BUY execution id; marked `campaign_identity_authority_status=COMPLETE`. |
| 2022-10-04 Strategy PM | `daily/2022-10-04/strategy/position_management.json` | `pc-621be524366e3fcd-83060-0001` | Strategy PM consumes SI lifecycle | EXIT row inherits SI campaign. |
| 2022-10-04 PM daily snapshot | `daily/2022-10-04/position_management/pm_decisions.json` | `pc-e6d857c27b1d386e-83060-0001` | Runtime-test observability PM snapshot | Snapshot uses run-scoped observability `active_campaign_by_symbol`, not Strategy canonical id. |
| 2022-10-04 SELL pending / submit | `daily/2022-10-04/submit/runtime_manifest.json` | blank | Pending / submit | PM decision lineage present, but campaign blank. |
| 2022-10-04 SELL fill observability | `daily/2022-10-04/execution/fills.json` | `pc-e6d857c27b1d386e-83060-0001` | Runtime-test observability | Same run-id-derived observability campaign as BUY fill. |
| 2022-10-04 realized slice | `daily/2022-10-04/execution/realized_slices.json` | `pc-e6d857c27b1d386e-83060-0001` | Runtime-test observability | Realized PnL observability follows e6d id. |
| Prior-exit bridge close reconstruction | Strategy bridge state | `ledger-derived-83060-0001` | `_resolve_prior_closed_campaigns_from_executions()` fallback | Fallback used because execution ledger campaign was blank at semantic bridge input. |

The first nonblank campaign id observed in retained artifacts is `pc-e6d...` in execution fill observability. The first decision-time Strategy campaign id is `pc-621...` in Strategy Intelligence / Strategy PM. These are independent generators and are not equivalent.

## Campaign Generators Inventory

| Generator | Module / Function | Input | Deterministic | Authority | Intended consumer | Same lifecycle regeneration allowed |
|---|---|---|---|---|---|---|
| Strategy pre-action ledger bootstrap | `src/ai_fund_lab_v2/strategy/shadow_runtime.py::_new_campaign_from_execution()` | `symbol`, `campaign_index`, strict-prior `execution_id` / record id | Yes | Intended canonical pre-action campaign lifecycle | Strategy Intelligence, PM, PC, sizing | Only as idempotent reconstruction of the same canonical lifecycle from strict-prior ledger evidence. |
| Strategy pre-action materializer | `src/ai_fund_lab_v2/strategy/shadow_runtime.py::_materialize_pre_action_position_campaigns()` | prior campaign snapshot, strict-prior ledger executions, Current | Yes | `positions/position_campaigns.json` | Strategy input | Yes, only if it preserves canonical identity and temporal safety. |
| Runtime-test observability campaign replay | `scripts/runtime_test.py::_derive_position_campaign_state()` / `_position_campaign_id()` | run id, symbol, open/close sequence | Yes | Run-scoped performance observability, not decision authority | Summary/fills/realized slices/PM snapshots | No for decision authority; yes only for observability summaries if kept out of Strategy/PM identity matching. |
| Prior-exit fallback | `src/ai_fund_lab_v2/strategy/shadow_runtime.py::_resolve_prior_closed_campaigns_from_executions()` | execution order and symbol when execution campaign id is absent | Yes-ish by sequence | Fallback semantic bridge identity | Prior-exit context reconstruction | No as canonical campaign id; it is a missing-provenance fallback. |
| PM runtime adapter inheritance | `src/ai_fund_lab_v2/runtime_v2/position_management/producer.py::_current_position_campaign_id()` | Current positions' `position_campaign_id` / `campaign_id` | N/A | Derivative, should inherit Current/campaign authority | Runtime PM decision artifact | No generation; inheritance only. |
| Submit / pending lineage propagation | `src/ai_fund_lab_v2/runtime_v2/planning/strategy_authority.py` and submit models/guards | PM/plan lineage | N/A | Derivative | Pending, orders, execution | No generation; preservation only. |
| Ledger projection | `src/ai_fund_lab_v2/runtime_v2/execution/ledger_projection.py` | broker order/execution snapshots and lineage | N/A | Persistent execution provenance preservation | Persistent ledger / replay | No generation; preservation only. |

## pc-e6d vs pc-621 Root Cause

`pc-e6d857c27b1d386e-83060-0001`

- Exact producer: `scripts/runtime_test.py::_derive_position_campaign_state()` and `_position_campaign_id()`.
- Code evidence: `_position_campaign_id()` returns `pc-{_short_hash(run_id)}-{symbol}-{sequence:04d}` at `scripts/runtime_test.py:9550-9555`.
- Hash material: `sha256("runtime-test-historical-extended-smoke-20260827T055917572299Z")[:16] = e6d857c27b1d386e`.
- Business date first observed: 2022-10-03 execution fill observability.
- Input identity: run id + symbol + lifecycle sequence, not execution id.
- Why it differs: the hash does not include the BUY execution identity and is generated by the runtime-test observability layer.

`pc-621be524366e3fcd-83060-0001`

- Exact producer: `src/ai_fund_lab_v2/strategy/shadow_runtime.py::_new_campaign_from_execution()`.
- Code evidence: campaign id uses `sha256(f"{symbol}|{campaign_index}|{execution_ref}")[:16]` at `src/ai_fund_lab_v2/strategy/shadow_runtime.py:1617-1627`.
- Hash material: `sha256("83060|1|execution-equivalent:sha256:be8a930006961029cfbc72cc9537f1de994af0ff16607d2421bd4978e0796801")[:16] = 621be524366e3fcd`.
- Business date first observed: 2022-10-04 Strategy Intelligence pre-action artifact.
- Input identity: symbol + campaign index + strict-prior 2022-10-03 BUY execution id.
- Why it differs: Strategy derives campaign identity from execution identity; runtime-test observability derives it from run id.

`ledger-derived-83060-0001`

- Exact producer: `src/ai_fund_lab_v2/strategy/shadow_runtime.py::_resolve_prior_closed_campaigns_from_executions()`.
- Code evidence: BUY fallback creates `ledger-derived-{symbol}-{index:04d}` and close fallback uses row campaign, current state campaign, or `ledger-derived` fallback at `src/ai_fund_lab_v2/strategy/shadow_runtime.py:1908-1928`.
- Purpose: fallback bridge identity when persistent execution rows do not carry canonical campaign ids.
- It should not supersede a canonical campaign id.

## Strict Bridge Assessment

The strict PM exit match function checks decision id, date, symbol, and campaign compatibility. Code evidence at `src/ai_fund_lab_v2/strategy/shadow_runtime.py:1968-1985` rejects evidence when `evidence.position_campaign_id` conflicts with the reconstructed close campaign id.

That predicate is directionally correct because PM EXIT evidence for a close should refer to the same campaign as the closed execution. In this run, however, the predicate compares incompatible namespaces:

- PM evidence campaign: `pc-e6d857c27b1d386e-83060-0001`
- Strategy canonical campaign: `pc-621be524366e3fcd-83060-0001`
- Close fallback campaign: `ledger-derived-83060-0001`
- Submit / execution lineage campaign: blank

Therefore `pm_exit_reason_matched_close_count = 0` is explained by campaign identity split and campaign provenance blanking, not by absence of PM reason evidence.

## Current / PM / Ledger Persistence Findings

Current position campaign preservation is incomplete.

- `LedgerExecutionRecord` and `LedgerOrderRecord` have `position_campaign_id`.
- `LedgerPositionRecord` model in this tree does not expose `position_campaign_id` in the retained source excerpt, and `project_position_to_ledger_record()` does not populate it.
- Runtime PM derives campaign only from Current positions via `_current_position_campaign_id()`. If Current is blank, PM runtime artifact is blank.
- The 2022-10-04 pending item for 83060 carries `source_decision_id=pm-2022-10-04-83060-exit` and `source_pm_decision_id=pm-2022-10-04-83060-exit`, but `position_campaign_id` is blank.
- Historical support order/execution payloads preserve `position_campaign_id` only if pending item or lineage has it. Blank pending therefore leads to blank broker/order/execution campaign provenance.

Persistent ledger is designed to preserve campaign provenance when it exists. It is not the primary campaign identity generator. In this run it lacks the needed campaign value at the 83060 SELL path, so later bridge logic falls back to `ledger-derived`.

## Retained Artifact Timing Note

`daily/2022-10-04/strategy/input_manifest.json` reports `pre_action_campaign_lifecycle.bootstrap_open_campaign_count=7` and points to `daily/2022-10-04/positions/position_campaigns.json` as the Strategy input authority. The retained `daily/2022-10-04/positions/position_campaigns.json` now contains only four still-open campaigns after same-day sells and excludes 83060, 89180, and 37820. Strategy artifacts still retain the 83060 `pc-621...` decision-time context.

This means the retained date-level campaign artifact can be overwritten from a pre-action view to a post-execution open-only view. That is a separate materialization ambiguity: decision-time campaign authority and post-execution observability are sharing a path/name too closely.

## Multi-Symbol Evidence

The split is not isolated to 83060. On 2022-10-03, every BUY fill in the early sample used the same run-id hash prefix in fill/PM observability, while Strategy generated a distinct execution-id-based hash on 2022-10-04:

| Symbol | Fill / PM snapshot campaign | Strategy campaign hash seed result |
|---|---|---|
| 89180 | `pc-e6d857c27b1d386e-89180-0001` | `pc-6c95b224bc92007b-89180-0001` |
| 83060 | `pc-e6d857c27b1d386e-83060-0001` | `pc-621be524366e3fcd-83060-0001` |
| 93600 | `pc-e6d857c27b1d386e-93600-0001` | `pc-93a91296bf355f34-93600-0001` |
| 33700 | `pc-e6d857c27b1d386e-33700-0001` | `pc-a60ffc6f59289e0c-33700-0001` |
| 37820 | `pc-e6d857c27b1d386e-37820-0001` | `pc-b83669098e6e07fc-37820-0001` |
| 92420 | `pc-e6d857c27b1d386e-92420-0001` | `pc-e83c4fb9d5ffc367-92420-0001` |
| 94340 | `pc-e6d857c27b1d386e-94340-0001` | `pc-74b1f39beab11b03-94340-0001` |

Scope judgment: the defect is universal for the sampled first-day BUY campaigns in this run, not a one-symbol special case.

## Mode Parity / Resume-Recovery

Historical, Demo, and Production should share the same campaign authority semantics: one canonical campaign identity generated once and then preserved by Current/PM/pending/order/execution. The code has multiple mode-aware preservation points, but this run shows Historical still has an observability-only generator that can populate artifacts used later for review/bridge evidence.

Resume/recovery is not campaign-safe in the observed path. `pc-621...` is reproducible from strict-prior execution id, but `pc-e6d...` is reproducible from run id and does not reflect canonical strategy identity. Blank pending/execution campaign provenance forces `ledger-derived` fallback. A resumed/recovered process could therefore reconstruct a different identity depending on which artifact family it uses.

## Defect Judgment

This is a mandatory campaign identity authority defect:

- Same lifecycle has multiple campaign ids.
- PM daily snapshot and Strategy PM disagree.
- Runtime/current/pending/submit path has blank campaign provenance.
- Strict prior bridge cannot match PM EXIT reason to the close.
- The issue is multi-symbol in the early sample.

The preferred repair should not change REENTRY, Cash, PC/MCC, Risk Pacing, thresholds, or models. The minimal repair boundary is campaign identity materialization and preservation:

1. Ensure initial BUY campaign identity is generated by the canonical campaign authority, not separately by observability.
2. Ensure Current, PM runtime adapter, Strategy PM, pending, submit, order, execution, persistent ledger, fill observability, realized slices, and PM snapshots all inherit the same canonical id for the same open lifecycle.
3. Treat `ledger-derived-*` as missing-provenance fallback only, never as an authoritative campaign when a canonical campaign is required.
4. Separate decision-time pre-action campaign snapshots from post-execution observability snapshots or version them explicitly so same-day EXIT context remains retrievable.

## Final Judgments

PHASE32_AC_CANONICAL_CAMPAIGN_AUTHORITY = `positions/position_campaigns.json` decision-time canonical campaign lifecycle authority; persistent execution ledger preserves provenance, Current carries derivative current state.

PHASE32_AC_CAMPAIGN_SEMANTIC = one continuous open-position lifecycle from initial BUY through ADD/HOLD/partial REDUCE/full EXIT; REENTRY after flat/full EXIT starts a new campaign.

PHASE32_AC_FIRST_CAMPAIGN_GENERATOR = In retained artifacts, runtime-test observability `_derive_position_campaign_state()` first emits `pc-e6d...` on 2022-10-03 fills; canonical decision-time generator should be Strategy Shadow pre-action campaign materializer.

PHASE32_AC_PM_CAMPAIGN_GENERATOR = Runtime-test PM snapshot derives from observability `campaign_by_symbol`; Runtime PM adapter itself only inherits from Current via `_current_position_campaign_id()`.

PHASE32_AC_STRATEGY_ARTIFACT_CAMPAIGN_GENERATOR = `src/ai_fund_lab_v2/strategy/shadow_runtime.py::_new_campaign_from_execution()`.

PHASE32_AC_LEDGER_DERIVED_CAMPAIGN_SEMANTIC = fallback identity for prior-exit reconstruction when execution rows lack canonical campaign provenance; not canonical authority.

PHASE32_AC_PC_E6D_ORIGIN = `scripts/runtime_test.py::_position_campaign_id()`, seed `sha256(run_id)[:16]`, generated by performance observability for fills/realized slices/PM snapshots.

PHASE32_AC_PC_621_ORIGIN = `shadow_runtime.py::_new_campaign_from_execution()`, seed `83060|1|execution-equivalent:sha256:be8a930006961029cfbc72cc9537f1de994af0ff16607d2421bd4978e0796801`.

PHASE32_AC_MULTIPLE_GENERATOR_DEFECT = YES

PHASE32_AC_CURRENT_POSITION_CAMPAIGN_PERSISTED = PARTIAL

PHASE32_AC_BUY_TO_EXIT_CAMPAIGN_SHOULD_BE_STABLE = YES

PHASE32_AC_REENTRY_CREATES_NEW_CAMPAIGN = YES

PHASE32_AC_PM_SHOULD_INHERIT_CAMPAIGN = YES

PHASE32_AC_LEDGER_FALLBACK_CORRECT = PARTIAL

PHASE32_AC_STRICT_BRIDGE_CAMPAIGN_PREDICATE_CORRECT = PARTIAL

PHASE32_AC_MODE_PARITY = PARTIAL

PHASE32_AC_RESUME_RECOVERY_CAMPAIGN_SAFE = PARTIAL

PHASE32_AC_MULTI_SYMBOL_SCOPE = UNIVERSAL

PHASE32_AC_PRIMARY_DEFECT_CLASS = multiple campaign identity generators plus incomplete campaign provenance persistence across Current/PM/pending/order/execution/observability boundaries

PHASE32_AC_MANDATORY_DEFECT = YES

PHASE32_AC_PRODUCTION_REPAIR_JUSTIFIED = YES

PHASE32_AC_IMPLEMENTATION_READY = YES

PHASE32_AC_PREFERRED_REPAIR_OPTION = A

PHASE32_AC_MINIMAL_REPAIR_BOUNDARY = campaign identity authority / propagation only: canonical initial BUY campaign materialization, Current/PM/pending/order/execution preservation, runtime-test observability consumption of canonical ids, and strict fallback demotion; no strategy gate or threshold change.

PHASE32_AC_NEXT_STEP = Implement a narrow repair that makes one canonical `position_campaign_id` survive from initial BUY lifecycle authority through PM SELL_EXIT, pending, order, execution ledger, fill observability, realized slices, and PM decision snapshots, then run focused provenance/bridge tests before a user-operated fresh validation.
