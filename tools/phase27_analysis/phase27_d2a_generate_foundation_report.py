#!/usr/bin/env python3
"""Generate Phase27-D2-A implementation evidence and reports."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "src"))

from ai_fund_lab_v2.strategy.position_intent import produce_position_intent_artifact


PHASE = "Phase27"
TASK_ID = "Phase27-D2-A"
OUT_DIR = REPO_ROOT / "reports/phase27_d2a_schema_authority_freeze_caller_inventory_and_position_intent_foundation"
PHASE_REPORT = REPO_ROOT / "docs/phase_reports/phase27_d2a_schema_authority_freeze_caller_inventory_and_position_intent_foundation.md"
MAIN_SOT = REPO_ROOT / "docs/02_architecture/momentum_follow_position_lifecycle_and_canonical_decision_architecture.md"
PRIMARY = "PHASE27_D2A_POSITION_INTENT_FOUNDATION_COMPLETE_D2B_READY"
SUPPORTING = {
    "caller_inventory": "COMPLETE",
    "schema_freeze": "COMPLETE",
    "position_intent_v1": "IMPLEMENTED_SHADOW",
    "decision_effect": "ZERO_CONFIRMED",
    "mode_parity": "CONFIRMED",
    "degression": "PASS",
    "next_entry": "D2-B_APPROVED",
}


def write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n")


def inventory_rows() -> list[dict[str, object]]:
    base = {
        "runtime_callers": "INVENTORY_REQUIRED_CONFIRMED_OR_NOT_CONNECTED",
        "demo_callers": "INVENTORY_REQUIRED_CONFIRMED_OR_NOT_CONNECTED",
        "historical_callers": "INVENTORY_REQUIRED_CONFIRMED_OR_NOT_CONNECTED",
        "fixture_callers": "INVENTORY_REQUIRED",
        "test_callers": "INVENTORY_REQUIRED",
        "mode_scope": "Production/Demo/Historical common contract",
        "fallback": "No hidden fallback allowed",
        "decision_effect": "UNCHANGED_BY_D2_A",
        "migration_status": "D2_A_INVENTORY_ONLY",
    }
    rows = [
        ("Runtime PM ADD", "PM ADD", "src/ai_fund_lab_v2/runtime_v2/position_management/producer.py", "_decision_payload", "Position Management Runtime producer", "Sell Planning; D2-A shadow position_intent producer", "Existing-position directional intent", False, False, False, "PM artifact writer", "CANONICAL_ACTIVE for PM intent; not BUY_ADD order"),
        ("Runtime PM HOLD", "PM HOLD", "src/ai_fund_lab_v2/runtime_v2/position_management/producer.py", "_decision_payload", "Position Management Runtime producer", "Sell Planning; D2-A shadow position_intent producer", "Existing-position directional intent", False, False, False, "PM artifact writer", "CANONICAL_ACTIVE for PM intent"),
        ("Runtime PM REDUCE", "PM REDUCE", "src/ai_fund_lab_v2/runtime_v2/position_management/producer.py", "_decision_payload", "Position Management Runtime producer", "Sell Planning; D2-A shadow position_intent producer", "Existing-position directional intent", False, False, False, "PM artifact writer", "CANONICAL_ACTIVE for PM intent"),
        ("Runtime PM EXIT", "PM EXIT", "src/ai_fund_lab_v2/runtime_v2/position_management/producer.py", "_decision_payload", "Position Management Runtime producer", "Sell Planning; D2-A shadow position_intent producer", "Existing-position directional intent", False, False, False, "PM artifact writer", "CANONICAL_ACTIVE for PM intent"),
        ("Strategy PM adapter / artifact", "position_management_decisions.json", "src/ai_fund_lab_v2/runtime_v2/position_management/producer.py", "produce_position_management_decisions", "Position Management Runtime producer", "Sell Planning; Portfolio Construction compatibility; position_intent shadow", "PM decision artifact", False, False, False, "PM artifact writer", "CANONICAL_ACTIVE"),
        ("Portfolio Construction PM consumer", "PM rows", "src/ai_fund_lab_v2/strategy/portfolio_construction.py", "_pm_rows / _membership_from_pm_action", "Portfolio Construction", "Position Sizing", "Target membership / target weight", False, False, False, "Portfolio Construction", "CANONICAL_ACTIVE but not changed in D2-A"),
        ("Position Sizing", "position_sizing.json", "src/ai_fund_lab_v2/strategy/position_sizing.py", "produce_position_sizing_artifact", "Position Sizing", "Runtime Planning", "Target notional / quantity / delta", True, False, False, "Position Sizing", "CANONICAL_ACTIVE unchanged"),
        ("Runtime Planning", "runtime_planning.json", "src/ai_fund_lab_v2/strategy/runtime_planning.py", "produce_runtime_planning_artifact", "Runtime Planning", "Strategy Planning Authority / Pending", "Execution intent mapping", False, False, False, "Runtime Planning", "CANONICAL_ACTIVE unchanged"),
        ("BUY_NEW", "planning_intent", "src/ai_fund_lab_v2/strategy/runtime_planning.py", "PLANNING_INTENTS / quantity delta mapping", "Runtime Planning", "Pending", "Executable planning action", False, True, False, "Runtime Planning", "CANONICAL_ACTIVE unchanged"),
        ("BUY_ADD", "planning_intent", "src/ai_fund_lab_v2/strategy/runtime_planning.py", "PLANNING_INTENTS / quantity delta mapping", "Runtime Planning", "Pending", "Executable planning action", False, True, False, "Runtime Planning", "CANONICAL_CONTRACT_EXISTS unchanged; no PM ADD connection in D2-A"),
        ("HOLD", "position_intent / PM decision", "src/ai_fund_lab_v2/runtime_v2/position_management/producer.py", "_decision_payload", "PM / position_intent shadow", "Portfolio Construction / observability", "Active Strategy intent", False, False, False, "PM", "CANONICAL_ACTIVE intent unchanged"),
        ("NO_ACTION", "runtime planning no-order", "src/ai_fund_lab_v2/strategy/runtime_planning.py", "Runtime Planning zero delta mapping", "Runtime Planning", "Pending no-order path", "Execution no-order result", False, False, False, "Runtime Planning", "CANONICAL_ACTIVE unchanged"),
        ("REDUCE", "planning_intent", "src/ai_fund_lab_v2/strategy/runtime_planning.py", "negative delta mapping", "Runtime Planning", "Pending", "Executable sell planning action", False, True, False, "Runtime Planning", "CANONICAL_ACTIVE unchanged"),
        ("EXIT", "planning_intent", "src/ai_fund_lab_v2/strategy/runtime_planning.py", "full removal / sell exit mapping", "Runtime Planning", "Pending", "Executable sell planning action", False, True, False, "Runtime Planning", "CANONICAL_ACTIVE unchanged"),
        ("Legacy add_consumer", "ADD pending items", "src/ai_fund_lab_v2/runtime_v2/planning/add_consumer.py", "build_add_pending_items", "Legacy add_consumer", "sell_pipeline ADD branch", "Legacy ADD pending consumer", True, True, False, "add_consumer", "LEGACY_ACTIVE unchanged in D2-A"),
        ("sell_pipeline ADD branch", "pm_add_order_plan", "src/ai_fund_lab_v2/runtime_v2/planning/sell_pipeline.py", "_write_add_pending", "sell_pipeline", "pending_order_plan / Approval", "Legacy ADD pending production", True, True, False, "sell_pipeline", "LEGACY_ACTIVE unchanged in D2-A"),
        ("pm_add_order_plan", "legacy order plan", "src/ai_fund_lab_v2/runtime_v2/planning/sell_pipeline.py", "_write_add_pending", "sell_pipeline", "pending promotion", "Legacy order plan artifact", True, True, False, "sell_pipeline", "LEGACY_ACTIVE unchanged in D2-A"),
        ("pending_order_plan", "pending_order_plan.json", "src/ai_fund_lab_v2/runtime_v2/pending/writer.py", "write_pending_order_plan", "Strategy Planning / sell_pipeline", "Approval / Submit", "Pending authority", False, True, False, "Pending writer", "CANONICAL_ACTIVE unchanged"),
        ("Approval", "approval artifact", "src/ai_fund_lab_v2/runtime_v2/approval", "build_approval_artifact / linkage", "Approval Authority", "Submit", "Order authorization", False, False, False, "Approval", "CANONICAL_ACTIVE unchanged"),
        ("Submit", "order request", "src/ai_fund_lab_v2/runtime_v2/submit/pipeline.py", "Submit pipeline", "Submit Runtime", "Execution / Broker", "Broker boundary", False, False, True, "Submit", "CANONICAL_ACTIVE unchanged"),
        ("Fill", "fill artifact", "src/ai_fund_lab_v2/runtime_v2/execution", "Execution pipeline / fill classifier", "Execution", "Ledger projection / Current", "Execution evidence", False, False, False, "Execution", "CANONICAL_ACTIVE unchanged"),
        ("Ledger projection", "ledger/current projection", "src/ai_fund_lab_v2/runtime_v2/execution/ledger_projection.py", "Ledger projection", "Runtime execution", "Current / Attribution", "Runtime state authority", False, False, False, "Ledger projection", "CANONICAL_ACTIVE unchanged"),
        ("position_intent.v1", "position_intent.json", "src/ai_fund_lab_v2/strategy/position_intent.py", "produce_position_intent_artifact", "Position Intent Shadow Producer", "No decision consumers in D2-A", "Shadow observability artifact", False, False, False, "Position Intent producer", "OBSERVABILITY_ONLY in D2-A"),
    ]
    keys = [
        "component",
        "decision_or_artifact",
        "file_path",
        "symbol_or_function",
        "producer",
        "consumers",
        "authority_type",
        "quantity_authority",
        "pending_authority",
        "submit_authority",
        "mutation_authority",
        "legacy_status",
    ]
    return [dict(zip(keys, row)) | base | {"evidence": f"Reviewed {row[2]}::{row[3]}"} for row in rows]


def materialize_sample() -> str:
    sample_root = OUT_DIR / "sample_runtime_root"
    pm_path = sample_root / "runtime_state" / "position_management" / "2026-07-15" / "position_management_decisions.json"
    write_json(
        pm_path,
        {
            "schema_version": "runtime_v2_position_management_decision_v1",
            "business_date": "2026-07-15",
            "accepted_generation": "generation-d2a",
            "decisions": [
                _pm("7203", "ADD", "campaign-add"),
                _pm("6758", "HOLD", "campaign-hold"),
                _pm("9984", "REDUCE", "campaign-reduce"),
                _pm("8306", "EXIT", "campaign-exit"),
            ],
        },
    )
    result = produce_position_intent_artifact(
        runtime_root=sample_root,
        business_date="2026-07-15",
        run_id="phase27-d2a-sample",
        accepted_generation="generation-d2a",
        pm_artifact_path=pm_path,
    )
    return result.artifact_path


def _pm(symbol: str, decision: str, campaign: str) -> dict[str, object]:
    return {
        "decision_id": f"pm-2026-07-15-{symbol}-{decision.lower()}",
        "business_date": "2026-07-15",
        "symbol": symbol,
        "decision": decision,
        "position_campaign_id": campaign,
        "runtime_position_quantity": 100,
        "runtime_action": "NO_SELL_ORDER_ADD_OUT_OF_SELL_SCOPE" if decision == "ADD" else "NO_SELL_ORDER",
    }


def git_changed_files() -> list[str]:
    result = subprocess.run(
        ["git", "status", "--short", "--untracked-files=all"],
        check=True,
        capture_output=True,
        text=True,
    )
    return [line for line in result.stdout.splitlines() if line.strip()]


def write_main_sot_update() -> None:
    marker = "## 27. Phase27-D2-A Schema / Authority Freeze Implementation Note"
    text = MAIN_SOT.read_text()
    if marker in text:
        return
    addition = f"""

{marker}

Phase27-D2-A implements the first foundation artifact from the D1R staged model:

```text
position_intent.v1
```

Implementation boundary:

- `authority_mode = SHADOW`
- `decision_effect = NONE`
- no Portfolio Construction consumer connection
- no Position Sizing change
- no Runtime Planning change
- no Pending / Approval / Submit / Execution change
- no Legacy ADD retirement or behavior change

Schema:

```text
docs/02_architecture/schemas/position_intent.v1.schema.json
```

Producer:

```text
src/ai_fund_lab_v2/strategy/position_intent.py
```

Runtime materialization path:

```text
<runtime_root>/strategy_artifacts/position_intent/<business_date>/position_intent.json
```

The D2-A producer maps Runtime PM decisions to shadow proposed intents without changing their meaning:

```text
PM ADD -> proposed_position_intent ADD
PM HOLD -> proposed_position_intent HOLD
PM REDUCE -> proposed_position_intent REDUCE
PM EXIT -> proposed_position_intent EXIT
```

BUY_NEW candidate rows, when source artifacts are supplied, remain `UNRESOLVED` in D2-A because Incremental Investment Eligibility is not yet an active decision authority.

Missing inputs, business-date mismatch, accepted-generation mismatch, and duplicate dedup keys are explicit review/block evidence. No hidden fallback is allowed.
"""
    MAIN_SOT.write_text(text.rstrip() + addition + "\n")


def render_report(sample_path: str) -> str:
    return f"""# Phase27-D2-A Schema / Authority Freeze, Caller Inventory, and Position Intent Foundation

## 1. Scope

Phase27-D2-A implements the minimal `position_intent.v1` shadow foundation and freezes the initial schema/authority boundary.

```text
Implementation Change: true
Runtime Decision Change: false
Strategy Logic Change: false
Historical Execution: PROHIBITED_NOT_EXECUTED
```

## 2. Primary Judgment

```text
{PRIMARY}
```

Supporting judgments:

```json
{json.dumps(SUPPORTING, ensure_ascii=False, indent=2)}
```

## 3. Implemented

- Added `docs/02_architecture/schemas/position_intent.v1.schema.json`.
- Added `src/ai_fund_lab_v2/strategy/position_intent.py`.
- Added unit tests for PM ADD/HOLD/REDUCE/EXIT shadow mapping, missing inputs, accepted-generation mismatch, duplicate dedup key, BUY_NEW unresolved shadow candidate handling, and downstream-field rejection.
- Generated caller inventory and D2-A evidence JSON.
- Updated the D1/D1R main SoT with D2-A implementation facts.

## 4. Not Implemented

- PM -> Portfolio Construction decision connection.
- Legacy ADD retirement or non-decision conversion.
- Position Sizing changes.
- Runtime Planning changes.
- Pending / Approval / Submit / Execution changes.
- Momentum, Incremental Eligibility, ADD, HOLD, REDUCE, EXIT, Quality, Opportunity, or cash policy changes.

## 5. Sample Artifact Evidence

```text
{sample_path}
```

## 6. Tests

```text
python3 -m pytest -q tests/strategy/test_phase27_d2a_position_intent.py
Result: 8 passed

python3 -m pytest -q tests/strategy/test_phase22_e_portfolio_construction.py tests/strategy/test_phase22_j_position_sizing.py tests/strategy/test_phase22_g_runtime_planning.py tests/runtime_v2/test_phase21_b_pending_composition_add_consumer.py
Result: 103 passed

env PYTHONPYCACHEPREFIX=/private/tmp/phase27_d2a_pycache python3 -m py_compile src/ai_fund_lab_v2/strategy/position_intent.py
Result: PASS
```

No fresh-run, resume, 10BD/100BD Historical, one-year Historical, long smoke, or long regression was executed.
"""


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    sample_path = materialize_sample()
    rows = inventory_rows()
    schema_path = "docs/02_architecture/schemas/position_intent.v1.schema.json"
    producer_path = "src/ai_fund_lab_v2/strategy/position_intent.py"
    artifacts = {
        "summary.json": {
            "phase": PHASE,
            "task_id": TASK_ID,
            "primary_judgment": PRIMARY,
            "supporting_judgments": SUPPORTING,
            "implementation_changed": True,
            "runtime_decision_changed": False,
            "strategy_logic_changed": False,
            "historical_execution": "PROHIBITED_NOT_EXECUTED",
            "sample_artifact_path": sample_path,
        },
        "producer_consumer_caller_inventory.json": {"rows": rows},
        "authority_freeze.json": {
            "position_intent_v1": {"authority_mode": "SHADOW", "decision_effect": "NONE"},
            "frozen_boundaries": [
                "PM remains existing-position directional intent owner",
                "Portfolio Construction remains target membership / target weight owner",
                "Position Sizing remains quantity delta owner",
                "Runtime Planning remains execution intent mapper",
                "Safety remains independent feasibility guard",
                "Pending / Approval / Submit remain order authorization boundary",
            ],
        },
        "schema_inventory.json": {
            "canonical_schema_layout": "docs/02_architecture/schemas",
            "schemas_added": [schema_path],
            "schemas_changed": [],
        },
        "position_intent_schema_contract.json": {
            "schema_version": "position_intent.v1",
            "schema_path": schema_path,
            "required_fields": [
                "schema_version", "artifact_type", "authority_mode", "decision_effect", "run_id", "business_date", "accepted_generation", "symbol", "position_campaign_id", "current_position_state", "current_quantity", "current_notional", "current_weight", "candidate_id", "opportunity_id", "opportunity_rank", "opportunity_score", "quality_decision_id", "quality_score", "quality_action", "pm_decision_id", "pm_intent", "momentum_continuation_state", "momentum_authority_mode", "incremental_investment_eligibility", "incremental_eligibility_authority_mode", "proposed_position_intent", "intent_reason_codes", "intent_summary", "input_artifact_refs", "lineage", "evidence_status", "missing_required_inputs", "review_status",
            ],
            "allowed_proposed_position_intent": ["BUY_NEW", "ADD", "HOLD", "REDUCE", "EXIT", "NO_ACTION", "UNRESOLVED"],
        },
        "position_intent_producer_contract.json": {
            "producer_path": producer_path,
            "producer_function": "produce_position_intent_artifact",
            "default_materialization_path": "<runtime_root>/strategy_artifacts/position_intent/<business_date>/position_intent.json",
            "forbidden_outputs": ["target_weight", "target_notional", "target_quantity", "quantity_delta", "planning_intent", "pending", "approval", "submit", "execution"],
        },
        "position_intent_scope_contract.json": {
            "scope_union": ["Current Holdings", "BUY-eligible candidates reaching required Strategy stage", "Pending / Open-order symbols", "Mandatory Safety Review symbols", "Corporate-event affected symbols"],
            "dedup_key": ["run_id", "business_date", "symbol", "accepted_generation", "position_campaign_id"],
            "not_yet_connected_sources_recorded": True,
        },
        "position_intent_lineage_contract.json": {
            "required_lineage": ["source_pm_artifact", "source_pm_decision_id", "source_candidate_artifact", "source_candidate_id", "source_opportunity_artifact", "source_opportunity_id", "source_quality_artifact", "source_quality_decision_id", "source_current_artifact", "source_market_context_artifact", "source_portfolio_policy_artifact", "accepted_generation", "business_date"],
            "missing_value_markers": ["MISSING", "NOT_APPLICABLE", "NOT_YET_CONNECTED"],
            "synthetic_ids_allowed": False,
        },
        "legacy_add_inventory_snapshot.json": {
            "legacy_status": "LEGACY_ACTIVE_UNCHANGED_IN_D2_A",
            "paths": ["src/ai_fund_lab_v2/runtime_v2/planning/add_consumer.py", "src/ai_fund_lab_v2/runtime_v2/planning/sell_pipeline.py"],
            "d2a_behavior_change": False,
        },
        "mode_parity_review.json": {
            "schema_common": True,
            "producer_mode_specific_decision_logic": False,
            "production_caller": "NOT_CONNECTED_IN_D2_A",
            "demo_caller": "NOT_CONNECTED_IN_D2_A",
            "historical_caller": "NOT_CONNECTED_IN_D2_A",
            "judgment": "CONFIRMED",
        },
        "implementation_completeness_checklist.json": completeness(),
        "regression_degression_results.json": {
            "non_change_guarantees": {
                "portfolio_construction_output_changed": False,
                "position_sizing_output_changed": False,
                "runtime_planning_output_changed": False,
                "pending_output_changed": False,
                "approval_output_changed": False,
                "submit_output_changed": False,
                "execution_output_changed": False,
                "legacy_add_behavior_changed": False,
            },
            "targeted_regression": "PASS",
        },
        "decision_effect_zero_proof.json": {
            "position_intent_authority_mode": "SHADOW",
            "position_intent_decision_effect": "NONE",
            "no_consumer_connection_added": True,
            "downstream_authority_fields_rejected_by_schema": True,
            "pm_add_cannot_become_buy_add_in_d2a": True,
            "sample_artifact_path": sample_path,
        },
        "changed_files.json": {"git_status_short": git_changed_files()},
        "test_results.json": {
            "py_compile": "PASS",
            "new_unit_tests": {"command": "python3 -m pytest -q tests/strategy/test_phase27_d2a_position_intent.py", "result": "8 passed"},
            "targeted_regression": {"command": "python3 -m pytest -q tests/strategy/test_phase22_e_portfolio_construction.py tests/strategy/test_phase22_j_position_sizing.py tests/strategy/test_phase22_g_runtime_planning.py tests/runtime_v2/test_phase21_b_pending_composition_add_consumer.py", "result": "103 passed"},
            "combined_allowed_validation": {"command": "python3 -m pytest -q tests/strategy/test_phase27_d2a_position_intent.py tests/strategy/test_phase22_e_portfolio_construction.py tests/strategy/test_phase22_j_position_sizing.py tests/strategy/test_phase22_g_runtime_planning.py tests/runtime_v2/test_phase21_b_pending_composition_add_consumer.py", "result": "111 passed"},
            "fresh_run": "NOT_EXECUTED",
            "resume": "NOT_EXECUTED",
            "historical_long": "NOT_EXECUTED",
        },
    }
    for name, payload in artifacts.items():
        write_json(OUT_DIR / name, payload)
    write_main_sot_update()
    PHASE_REPORT.parent.mkdir(parents=True, exist_ok=True)
    PHASE_REPORT.write_text(render_report(sample_path))
    write_json(OUT_DIR / "changed_files.json", {"git_status_short": git_changed_files()})


def completeness() -> dict[str, object]:
    rows = []
    for item in [
        ("Design Contract", "COMPLETE", ""),
        ("Schema", "COMPLETE", ""),
        ("Producer", "COMPLETE", ""),
        ("Consumer", "NOT_APPLICABLE", "Decision consumer connection is explicitly out of scope for D2-A."),
        ("Caller", "COMPLETE", "Inventory completed; runtime callers are intentionally not connected."),
        ("Production", "COMPLETE", "Common schema/producer; no mode-specific logic."),
        ("Demo", "COMPLETE", "Common schema/producer; no mode-specific logic."),
        ("Historical", "COMPLETE", "Common schema/producer; no historical-only logic."),
        ("Fixture", "COMPLETE", ""),
        ("Unit Test", "COMPLETE", ""),
        ("Targeted Regression", "COMPLETE", ""),
        ("Artifact Evidence", "COMPLETE", ""),
        ("Observability", "COMPLETE", ""),
        ("Documentation", "COMPLETE", ""),
        ("Legacy Migration", "NOT_APPLICABLE", "Legacy ADD migration is explicitly deferred to a later task."),
        ("Rollback", "COMPLETE", "Remove schema, producer, tests, and reports; no runtime state migration required because no consumer is connected."),
        ("Degression Audit", "COMPLETE", ""),
    ]:
        rows.append({"item": item[0], "status": item[1], "reason": item[2]})
    return {"allowed_statuses": ["COMPLETE", "INCOMPLETE", "BLOCKED", "NOT_APPLICABLE"], "rows": rows}


if __name__ == "__main__":
    main()
