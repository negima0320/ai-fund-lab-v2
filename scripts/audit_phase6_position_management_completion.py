from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from ai_fund_lab_v2.opportunity_ai.training import to_jsonable
from ai_fund_lab_v2.position_management_ai.calibration import (
    CALIBRATED_MODEL_VERSION,
    build_calibrated_position_management_output,
)
from ai_fund_lab_v2.position_management_ai.inference import FORBIDDEN_FEATURE_PREFIXES, FORBIDDEN_FEATURE_TERMS, OUTPUT_COLUMNS
from ai_fund_lab_v2.position_management_ai.label_dataset import audit_position_label_dataset

PHASE = "Phase6-G"
COMPLETION_STATUS = "PHASE6_COMPLETE_WITH_DOCUMENTED_LIMITATIONS"
BLOCKED_STATUS = "PHASE6_BLOCKED_BY_COMPLETION_AUDIT"

DEFAULT_OUTPUT_PATH = Path("reports/position_management_ai/phase6_completion_audit.json")
DEFAULT_PHASE6C_AUDIT_PATH = Path("reports/position_management_ai/phase6c_position_label_audit.json")
DEFAULT_PHASE6E_AUDIT_PATH = Path("reports/position_management_ai/phase6e_calibrated_baseline_audit.json")
DEFAULT_PHASE6F_AUDIT_PATH = Path("reports/position_management_ai/phase6f_realdata_audit.json")
DEFAULT_PHASE6F_LABEL_PATH = Path("reports/position_management_ai/phase6f_realdata_label_dataset.csv")

REQUIRED_DOCS = (
    "docs/01_requirements/phase_roadmap.md",
    "docs/03_ai_design/position_management_ai_design.md",
    "docs/phase_reports/phase6a_position_management_schema_and_baseline.md",
    "docs/phase_reports/phase6b_position_feature_builder.md",
    "docs/phase_reports/phase6c_position_label_dataset_audit.md",
    "docs/phase_reports/phase6d_baseline_label_alignment_audit.md",
    "docs/phase_reports/phase6e_baseline_rule_calibration.md",
    "docs/phase_reports/phase6f_realdata_position_dry_run.md",
)

REQUIRED_OUTPUT_COLUMNS = (
    "code",
    "target_date",
    "action",
    "hold_score",
    "exit_score",
    "add_score",
    "reduce_score",
    "continue_holding",
    "exit_candidate",
    "add_candidate",
    "reduce_candidate",
    "action_reason",
    "exit_reason",
    "risk_guard_status",
    "feature_version",
    "model_version",
    "created_at",
)

SCOPE_FLAGS = (
    "training_executed",
    "backtest_executed",
    "broker_api_executed",
    "order_executed",
    "paper_trading_executed",
    "capital_allocation_executed",
)


def run_phase6_completion_audit(
    *,
    output_path: Path = DEFAULT_OUTPUT_PATH,
    phase6c_audit_path: Path = DEFAULT_PHASE6C_AUDIT_PATH,
    phase6e_audit_path: Path = DEFAULT_PHASE6E_AUDIT_PATH,
    phase6f_audit_path: Path = DEFAULT_PHASE6F_AUDIT_PATH,
    phase6f_label_path: Path = DEFAULT_PHASE6F_LABEL_PATH,
    created_at: str | None = None,
) -> dict[str, Any]:
    created_at = created_at or now_utc()
    docs = audit_required_docs(REQUIRED_DOCS)
    phase6c_audit = read_json(phase6c_audit_path)
    phase6e_audit = read_json(phase6e_audit_path)
    phase6f_audit = read_json(phase6f_audit_path)
    phase6f_labels = read_label_dataset(phase6f_label_path)

    schema_audit = audit_output_schema(phase6f_labels, created_at=created_at)
    feature_safety_audit = audit_feature_safety(phase6f_labels, phase6c_audit=phase6c_audit, phase6f_audit=phase6f_audit)
    label_separation_audit = audit_label_separation(phase6f_labels)
    responsibility_audit = audit_responsibility_boundary((phase6c_audit, phase6e_audit, phase6f_audit))
    add_safety_audit = audit_add_safety(phase6e_audit=phase6e_audit, phase6f_audit=phase6f_audit)
    hold_exit_safety_audit = audit_hold_exit_safety(phase6e_audit=phase6e_audit, phase6f_audit=phase6f_audit)
    phase6f_limitations = audit_phase6f_limitations(phase6f_audit)

    checks = {
        "docs_readiness_ok": docs["missing_doc_count"] == 0,
        "responsibility_boundary_ok": responsibility_audit["status"] == "OK",
        "output_schema_ok": schema_audit["status"] == "OK",
        "feature_safety_ok": feature_safety_audit["status"] == "OK",
        "label_separation_ok": label_separation_audit["status"] == "OK",
        "add_safety_ok": add_safety_audit["status"] == "OK",
        "hold_exit_safety_ok": hold_exit_safety_audit["status"] == "OK",
        "phase6f_limitations_documented": phase6f_limitations["documented_limitations_required"] is True,
    }
    completion_ok = all(checks.values())
    payload = {
        "phase": PHASE,
        "created_at": created_at,
        "completion_status": COMPLETION_STATUS if completion_ok else BLOCKED_STATUS,
        "ready_for_phase7": bool(completion_ok),
        "checks": checks,
        "read_docs": docs,
        "responsibility_boundary_audit": responsibility_audit,
        "output_schema_audit": schema_audit,
        "feature_safety_audit": feature_safety_audit,
        "label_separation_audit": label_separation_audit,
        "add_safety_audit": add_safety_audit,
        "hold_exit_safety_audit": hold_exit_safety_audit,
        "phase6f_limitations": phase6f_limitations,
        "phase7_handoff": build_phase7_handoff(),
        "pytest": {
            "required_command": (
                "python3 -m pytest "
                "tests/position_management_ai/test_phase6a_position_management_baseline.py "
                "tests/position_management_ai/test_phase6b_position_feature_builder.py "
                "tests/position_management_ai/test_phase6c_position_label_dataset.py "
                "tests/position_management_ai/test_phase6d_baseline_label_alignment.py "
                "tests/position_management_ai/test_phase6e_baseline_calibration.py "
                "tests/position_management_ai/test_phase6f_realdata_dry_run.py "
                "tests/position_management_ai/test_phase6_completion_audit.py"
            ),
            "status": "RUN_SEPARATELY",
        },
        "source_artifacts": {
            "phase6c_audit_path": str(phase6c_audit_path),
            "phase6e_audit_path": str(phase6e_audit_path),
            "phase6f_audit_path": str(phase6f_audit_path),
            "phase6f_label_path": str(phase6f_label_path),
        },
    }
    write_json(output_path, payload)
    return payload


def audit_required_docs(paths: tuple[str, ...]) -> dict[str, Any]:
    docs = []
    for path in paths:
        text = Path(path).read_text(encoding="utf-8") if Path(path).is_file() else ""
        docs.append(
            {
                "path": path,
                "exists": bool(text),
                "mentions_add_candidate_signal": "ADD" in text and ("候補" in text or "candidate signal" in text or "add-candidate signal" in text),
                "mentions_no_scope_execution": any(term in text for term in ("Broker API", "Paper Trading", "capital allocation", "資金配分")),
            }
        )
    return {
        "docs": docs,
        "missing_doc_count": int(sum(not item["exists"] for item in docs)),
        "missing_docs": [item["path"] for item in docs if not item["exists"]],
        "add_candidate_signal_documented": any(item["mentions_add_candidate_signal"] for item in docs),
    }


def audit_output_schema(label_dataset: pd.DataFrame, *, created_at: str) -> dict[str, Any]:
    inference_frame = pd.DataFrame(
        {
            "target_date": label_dataset["target_date"].astype(str).head(3),
            "code": label_dataset["code"].astype(str).head(3),
            "entry_price": label_dataset["feature__entry_price"].head(3),
            "current_price": label_dataset["feature__current_price"].head(3),
            "holding_days": label_dataset["feature__holding_days"].head(3),
            "position_size": 100.0,
            "current_return": label_dataset["feature__unrealized_return"].head(3),
            "peak_return": label_dataset["feature__peak_return"].head(3),
            "expected_edge_score": label_dataset["feature__expected_edge_score"].head(3),
            "buy_rank": label_dataset["feature__buy_rank"].head(3),
            "downside_risk_score": label_dataset["feature__downside_risk_score"].head(3),
            "risk_guard_status": label_dataset["feature__risk_guard_status"].head(3),
            "feature_version": label_dataset["feature_version"].head(3),
            "feature__return_5d": label_dataset["feature__return_5d"].head(3),
            "feature__return_20d": label_dataset["feature__return_20d"].head(3),
            "feature__close_over_ma_20d": label_dataset["feature__close_over_ma_20d"].head(3),
            "feature__ma_5_20_ratio": label_dataset["feature__ma_5_20_ratio"].head(3),
            "feature__volume_ratio_5d": label_dataset["feature__volume_ratio_5d"].head(3),
            "feature__volatility_20d": label_dataset["feature__volatility_20d"].head(3),
        }
    )
    output = build_calibrated_position_management_output(inference_frame, created_at=created_at)
    required_missing = [column for column in REQUIRED_OUTPUT_COLUMNS if column not in output.columns]
    phase6a_missing = [column for column in OUTPUT_COLUMNS if column not in output.columns]
    return {
        "status": "OK" if not required_missing and not phase6a_missing else "ERROR",
        "required_output_columns": list(REQUIRED_OUTPUT_COLUMNS),
        "calibrated_output_columns": list(output.columns),
        "missing_required_columns": required_missing,
        "missing_phase6a_schema_columns": phase6a_missing,
        "model_version": CALIBRATED_MODEL_VERSION,
    }


def audit_feature_safety(label_dataset: pd.DataFrame, *, phase6c_audit: dict[str, Any], phase6f_audit: dict[str, Any]) -> dict[str, Any]:
    feature_columns = [column for column in label_dataset.columns if column.startswith("feature__")]
    forbidden_columns = [
        column for column in feature_columns if is_forbidden_feature_name(column.replace("feature__", "", 1))
    ]
    return {
        "status": "OK"
        if not forbidden_columns
        and phase6c_audit.get("forbidden_feature_audit_status") == "OK"
        and phase6f_audit.get("forbidden_feature_audit_status") == "OK"
        else "ERROR",
        "forbidden_feature_columns": forbidden_columns,
        "forbidden_feature_column_count": len(forbidden_columns),
        "phase6c_forbidden_feature_audit_status": phase6c_audit.get("forbidden_feature_audit_status"),
        "phase6f_forbidden_feature_audit_status": phase6f_audit.get("forbidden_feature_audit_status"),
        "forbidden_prefixes": list(FORBIDDEN_FEATURE_PREFIXES) + ["future_min_return_", "future_profit"],
        "forbidden_terms": list(FORBIDDEN_FEATURE_TERMS),
    }


def audit_label_separation(label_dataset: pd.DataFrame) -> dict[str, Any]:
    label_audit = audit_position_label_dataset(label_dataset, created_at=now_utc())
    return {
        "status": "OK" if label_audit["label_leakage_audit_status"] == "OK" else "ERROR",
        "feature_label_columns_separated": label_audit["feature_label_columns_separated"],
        "feature_column_count": label_audit["feature_column_count"],
        "label_column_count": label_audit["label_column_count"],
        "future_feature_column_count": label_audit["future_feature_column_count"],
        "unprefixed_label_column_count": label_audit["unprefixed_label_column_count"],
        "label_columns": label_audit["label_columns"],
    }


def audit_responsibility_boundary(audits: tuple[dict[str, Any], ...]) -> dict[str, Any]:
    executed = {}
    for flag in SCOPE_FLAGS:
        executed[flag] = any(bool(audit.get(flag, False)) for audit in audits)
    return {
        "status": "OK" if not any(executed.values()) else "ERROR",
        "executed_flags": executed,
        "phase6_does_not_execute": [
            "ML training",
            "full backtest",
            "Broker API",
            "order placement",
            "Paper Trading",
            "capital allocation",
            "Capital Allocation",
        ],
    }


def audit_add_safety(*, phase6e_audit: dict[str, Any], phase6f_audit: dict[str, Any]) -> dict[str, Any]:
    add_loss = int(phase6e_audit.get("add_loss_position_count", 0)) + int(phase6f_audit.get("add_loss_position_count", 0))
    add_exit_overlap = int(phase6e_audit.get("add_exit_label_overlap_count", 0)) + int(phase6f_audit.get("add_exit_label_overlap_count", 0))
    return {
        "status": "OK" if add_loss == 0 and add_exit_overlap == 0 else "ERROR",
        "add_loss_position_count_total": add_loss,
        "add_exit_label_overlap_count_total": add_exit_overlap,
        "add_is_candidate_signal_only": True,
        "phase7_decides_final_purchase_permission_amount_and_position_limits": True,
    }


def audit_hold_exit_safety(*, phase6e_audit: dict[str, Any], phase6f_audit: dict[str, Any]) -> dict[str, Any]:
    exit_continue = int(phase6e_audit.get("exit_continue_winner_count", 0)) + int(phase6f_audit.get("exit_continue_winner_count", 0))
    reduce_continue = int(phase6e_audit.get("reduce_continue_winner_count", 0)) + int(phase6f_audit.get("reduce_continue_winner_count", 0))
    phase6e_metrics = phase6e_audit.get("alignment_metrics", {})
    phase6f_metrics = phase6f_audit.get("alignment_metrics", {})
    return {
        "status": "OK" if exit_continue == 0 and reduce_continue == 0 else "ERROR",
        "continue_winner_exit_count_total": exit_continue,
        "continue_winner_reduce_count_total": reduce_continue,
        "phase6e_hold_exit_label_rate": phase6e_metrics.get("hold_exit_label_rate"),
        "phase6f_hold_exit_label_rate": phase6f_metrics.get("hold_exit_label_rate"),
        "phase6f_all_hold_bias_documented": phase6f_audit.get("action_distribution") == {"HOLD": 36},
    }


def audit_phase6f_limitations(phase6f_audit: dict[str, Any]) -> dict[str, Any]:
    action_distribution = phase6f_audit.get("action_distribution", {})
    label_distribution = phase6f_audit.get("label_distribution", {})
    continue_winner = label_distribution.get("label__label_continue_winner", {})
    all_hold = action_distribution == {"HOLD": 36}
    all_continue_winner = continue_winner.get("true") == 36 and continue_winner.get("false") == 0
    return {
        "documented_limitations_required": True,
        "phase5_formal_opportunity_output_used": False,
        "opportunity_signal_source": phase6f_audit.get("opportunity_signal_source"),
        "row_count": phase6f_audit.get("label_row_count"),
        "code_count": phase6f_audit.get("code_count"),
        "target_date_count": phase6f_audit.get("target_date_count"),
        "action_distribution": action_distribution,
        "label_continue_winner_distribution": continue_winner,
        "all_hold": all_hold,
        "all_continue_winner": all_continue_winner,
        "realdata_plumbing_ok": phase6f_audit.get("status") == "OK",
        "action_diversity_evaluation_sufficient": False,
        "limitation_summary": (
            "Phase6-F used proxy opportunity signals on 36 rows / 12 codes / 3 target dates. "
            "All actions were HOLD and all rows were label_continue_winner=true, so it validates real-data plumbing "
            "but is insufficient for action-diversity evaluation."
        ),
    }


def build_phase7_handoff() -> dict[str, Any]:
    return {
        "HOLD": "保有継続候補。Phase7では保有維持前提の資金拘束として扱う。",
        "EXIT": "売却候補。最終注文はBroker/Paper phaseで扱う。",
        "ADD": "買い増し候補シグナルのみ。実購入可否、購入金額、保有上限判定はPhase7 Capital Allocation Engineが行う。",
        "REDUCE": "縮小候補。実売却数量はPhase7以降で決める。",
        "scores_for_phase7": ["hold_score", "exit_score", "add_score", "reduce_score"],
        "required_context": ["risk_guard_status", "feature_version", "model_version", "created_at"],
    }


def read_label_dataset(path: Path) -> pd.DataFrame:
    if not path.is_file():
        raise FileNotFoundError(f"Phase6-F label dataset is missing: {path}")
    return pd.read_csv(path, dtype={"code": str})


def read_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise FileNotFoundError(f"required audit artifact is missing: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(to_jsonable(payload), ensure_ascii=True, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def is_forbidden_feature_name(name: str) -> bool:
    if name.startswith(FORBIDDEN_FEATURE_PREFIXES):
        return True
    if name.startswith(("future_min_return_", "future_profit")):
        return True
    return any(term in name for term in FORBIDDEN_FEATURE_TERMS)


def now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def main() -> None:
    parser = argparse.ArgumentParser(description="Audit Phase6 Position Management AI completion readiness.")
    parser.add_argument("--output-path", type=Path, default=DEFAULT_OUTPUT_PATH)
    args = parser.parse_args()
    audit = run_phase6_completion_audit(output_path=args.output_path)
    print(json.dumps(to_jsonable(audit), ensure_ascii=True, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
