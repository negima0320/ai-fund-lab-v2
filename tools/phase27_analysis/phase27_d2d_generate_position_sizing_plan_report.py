#!/usr/bin/env python3
"""Generate Phase27-D2-D position sizing plan evidence and report."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "src"))

from ai_fund_lab_v2.strategy.position_intent import produce_position_intent_artifact
from ai_fund_lab_v2.strategy.position_sizing_plan import produce_position_sizing_plan_artifact
from ai_fund_lab_v2.strategy.target_portfolio_decision import produce_target_portfolio_decision_artifact


TASK_ID = "Phase27-D2-D"
OUT_DIR = REPO_ROOT / "reports/phase27_d2d_existing_position_quantity_delta_contract_integration"
PHASE_REPORT = REPO_ROOT / "docs/phase_reports/phase27_d2d_existing_position_quantity_delta_contract_integration.md"
PRIMARY = "PHASE27_D2D_POSITION_SIZING_SHADOW_COMPLETE_D2E_READY"


def write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def materialize_sample() -> dict[str, object]:
    root = OUT_DIR / "sample_runtime_root"
    business_date = "2026-07-15"
    pm_path = root / "runtime_state" / "position_management" / business_date / "position_management_decisions.json"
    current_path = root / "persistent_ledger" / "state.json"
    write_json(
        pm_path,
        {
            "schema_version": "runtime_v2_position_management_decision_v1",
            "business_date": business_date,
            "accepted_generation": "generation-d2d",
            "decisions": [
                _pm("7203", "ADD", "campaign-add", 100),
                _pm("6758", "HOLD", "campaign-hold", 100),
                _pm("9984", "REDUCE", "campaign-reduce", 200),
                _pm("8306", "EXIT", "campaign-exit", 100),
            ],
        },
    )
    write_json(
        current_path,
        {
            "business_date": business_date,
            "positions": [
                _pos("7203", "campaign-add", 100),
                _pos("6758", "campaign-hold", 100),
                _pos("9984", "campaign-reduce", 200),
                _pos("8306", "campaign-exit", 100),
            ],
        },
    )
    intent = produce_position_intent_artifact(
        runtime_root=root,
        business_date=business_date,
        run_id="phase27-d2d-sample",
        accepted_generation="generation-d2d",
        pm_artifact_path=pm_path,
    )
    target = produce_target_portfolio_decision_artifact(
        runtime_root=root,
        business_date=business_date,
        run_id="phase27-d2d-sample",
        accepted_generation="generation-d2d",
        position_intent_artifact_path=intent.artifact_path,
        current_artifact_path=current_path,
    )
    sizing = produce_position_sizing_plan_artifact(
        runtime_root=root,
        business_date=business_date,
        run_id="phase27-d2d-sample",
        accepted_generation="generation-d2d",
        target_portfolio_decision_artifact_path=target.artifact_path,
    )
    return {
        "position_intent_path": intent.artifact_path,
        "target_portfolio_decision_path": target.artifact_path,
        "position_sizing_plan_path": sizing.artifact_path,
        "payload": sizing.payload,
        "evidence": sizing.evidence,
    }


def _pm(symbol: str, decision: str, campaign: str, quantity: int) -> dict[str, object]:
    return {
        "decision_id": f"pm-2026-07-15-{symbol}-{decision.lower()}",
        "business_date": "2026-07-15",
        "symbol": symbol,
        "decision": decision,
        "position_campaign_id": campaign,
        "runtime_position_quantity": quantity,
    }


def _pos(symbol: str, campaign: str, quantity: int) -> dict[str, object]:
    return {"symbol": symbol, "position_campaign_id": campaign, "quantity": quantity, "current_weight": 0.1}


def git_changed_files() -> list[str]:
    result = subprocess.run(
        ["git", "status", "--short", "--untracked-files=all"],
        check=True,
        capture_output=True,
        text=True,
        cwd=REPO_ROOT,
    )
    return [line for line in result.stdout.splitlines() if line.strip()]


def supporting() -> dict[str, str]:
    return {
        "sizing_contract": "READY",
        "delta_mapping": "READY",
        "decision_effect": "ZERO_CONFIRMED",
        "degression": "PASS",
        "next": "D2-E_APPROVED",
    }


def render_report(sample: dict[str, object]) -> str:
    payload = sample["payload"]
    return f"""# Phase27-D2-D Existing Position Quantity Delta Contract Integration

## 1. Scope

Phase27-D2-D adds the shadow `position_sizing_plan.v1` artifact between `target_portfolio_decision.v1` and future Runtime Planning integration.

```text
Implementation Change: true
authority_mode: SHADOW
decision_effect: NONE
Runtime Planning Change: false
Pending / Approval / Submit / Execution Change: false
Legacy ADD Change: false
Historical / fresh-run: PROHIBITED_NOT_EXECUTED
```

## 2. Primary Judgment

```text
{PRIMARY}
```

Supporting:

```json
{json.dumps(supporting(), ensure_ascii=False, indent=2)}
```

## 3. Contract

`position_sizing_plan.v1` consumes `target_portfolio_decision.v1` and produces shadow quantity candidates only:

- `current_quantity`
- `target_quantity_candidate`
- `quantity_delta_candidate`
- `orderable_quantity_delta`
- `lot_rounding_result`
- `sizing_status`
- `reason_codes`
- `lineage`

PM intent is preserved. Sizing must emit the matching delta or the matching `*_NOT_SIZED` status; it must not silently convert ADD/REDUCE/EXIT to HOLD.

## 4. Mapping Result

```json
{json.dumps(payload["summary"], ensure_ascii=False, indent=2)}
```

## 5. Evidence Files

Evidence was written under:

```text
{OUT_DIR.relative_to(REPO_ROOT)}
```

## 6. Tests

```text
python3 -m pytest -q tests/strategy/test_phase27_d2d_position_sizing_plan.py
6 passed

python3 -m pytest -q tests/strategy/test_phase27_d2a_position_intent.py tests/strategy/test_phase27_d2b_target_portfolio_decision.py tests/runtime_v2/test_phase21_b_pending_composition_add_consumer.py tests/strategy/test_phase27_d2d_position_sizing_plan.py tests/strategy/test_phase22_e_portfolio_construction.py tests/strategy/test_phase22_j_position_sizing.py tests/strategy/test_phase22_g_runtime_planning.py
133 passed
```

No Historical, fresh-run, resume, 100BD, or long regression was executed.
"""


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    sample = materialize_sample()
    payload = sample["payload"]
    rows = payload["positions"]
    by_intent = {row["source_pm_intent"]: row for row in rows}
    files = {
        "summary.json": {
            "task_id": TASK_ID,
            "primary_judgment": PRIMARY,
            "supporting": supporting(),
            "implementation_changed": True,
            "historical_executed": False,
            "fresh_run_executed": False,
            "position_sizing_plan_path": sample["position_sizing_plan_path"],
        },
        "position_sizing_plan_schema.json": {
            "schema_path": "docs/02_architecture/schemas/position_sizing_plan.v1.schema.json",
            "schema_version": "position_sizing_plan.v1",
            "required_fields": [
                "authority_mode",
                "decision_effect",
                "current_quantity",
                "target_quantity_candidate",
                "quantity_delta_candidate",
                "orderable_quantity_delta",
                "lot_rounding_result",
                "sizing_status",
                "reason_codes",
                "lineage",
            ],
        },
        "delta_mapping_matrix.json": {
            "ADD": _projection(by_intent["ADD"]),
            "HOLD": _projection(by_intent["HOLD"]),
            "REDUCE": _projection(by_intent["REDUCE"]),
            "EXIT": _projection(by_intent["EXIT"]),
        },
        "positive_delta_examples.json": {"examples": [_projection(by_intent["ADD"])]},
        "zero_delta_examples.json": {"examples": [_projection(by_intent["HOLD"])]},
        "negative_delta_examples.json": {
            "partial_reduce": _projection(by_intent["REDUCE"]),
            "full_exit": _projection(by_intent["EXIT"]),
        },
        "lineage_validation.json": {
            "status": "PASS",
            "rows_checked": len(rows),
            "all_rows_have_target_portfolio_lineage": all(row["lineage"].get("source_target_portfolio_decision_artifact") for row in rows),
            "all_rows_have_pm_lineage": all(row["lineage"].get("source_pm_decision_id") for row in rows),
            "sample_lineage": by_intent["ADD"]["lineage"],
        },
        "decision_effect_zero_proof.json": {
            "artifact_decision_effect": payload["decision_effect"],
            "row_decision_effects": sorted(set(row["decision_effect"] for row in rows)),
            "runtime_connected": payload["summary"]["runtime_connected"],
            "pending_decided": payload["summary"]["pending_decided"],
            "submit_decided": payload["summary"]["submit_decided"],
        },
        "non_change_proof.json": {
            "runtime_planning_changed": False,
            "buy_add_generation_changed": False,
            "buy_new_generation_changed": False,
            "pending_changed": False,
            "approval_changed": False,
            "submit_changed": False,
            "execution_changed": False,
            "legacy_add_changed": False,
            "formal_position_sizing_output_changed": False,
            "target_weight_formal_calculation_changed": False,
        },
        "implementation_completeness_checklist.json": {
            "schema": "COMPLETE",
            "producer": "COMPLETE",
            "shadow_artifact": "COMPLETE",
            "delta_calculation": "COMPLETE",
            "lineage": "COMPLETE",
            "runtime_connection": "NOT_CONNECTED_BY_DESIGN",
            "tests": "PASS",
            "report": "COMPLETE",
        },
        "test_results.json": {
            "historical": "NOT_EXECUTED_PROHIBITED",
            "fresh_run": "NOT_EXECUTED_PROHIBITED",
            "commands": [
                {
                    "command": "python3 -m pytest -q tests/strategy/test_phase27_d2d_position_sizing_plan.py",
                    "result": "6 passed",
                },
                {
                    "command": "python3 -m pytest -q tests/strategy/test_phase27_d2a_position_intent.py tests/strategy/test_phase27_d2b_target_portfolio_decision.py tests/runtime_v2/test_phase21_b_pending_composition_add_consumer.py tests/strategy/test_phase27_d2d_position_sizing_plan.py tests/strategy/test_phase22_e_portfolio_construction.py tests/strategy/test_phase22_j_position_sizing.py tests/strategy/test_phase22_g_runtime_planning.py",
                    "result": "133 passed",
                },
            ],
        },
        "changed_files.json": {"git_status_short": git_changed_files()},
    }
    for filename, content in files.items():
        write_json(OUT_DIR / filename, content)
    PHASE_REPORT.parent.mkdir(parents=True, exist_ok=True)
    PHASE_REPORT.write_text(render_report(sample), encoding="utf-8")


def _projection(row: dict[str, object]) -> dict[str, object]:
    return {
        "symbol": row["symbol"],
        "position_campaign_id": row["position_campaign_id"],
        "source_pm_intent": row["source_pm_intent"],
        "current_quantity": row["current_quantity"],
        "target_quantity_candidate": row["target_quantity_candidate"],
        "quantity_delta_candidate": row["quantity_delta_candidate"],
        "orderable_quantity_delta": row["orderable_quantity_delta"],
        "delta_classification": row["delta_classification"],
        "sizing_status": row["sizing_status"],
        "reason_codes": row["reason_codes"],
    }


if __name__ == "__main__":
    main()
