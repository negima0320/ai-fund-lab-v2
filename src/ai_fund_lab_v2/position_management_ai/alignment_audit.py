from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

from ai_fund_lab_v2.opportunity_ai.training import to_jsonable
from ai_fund_lab_v2.position_management_ai.inference import audit_position_feature_frame, build_position_management_output
from ai_fund_lab_v2.position_management_ai.label_dataset import (
    DEFAULT_OUTPUT_CSV_PATH as DEFAULT_PHASE6C_DATASET_PATH,
    audit_position_label_dataset,
    run_phase6c_position_label_dataset_dry_run,
)

PHASE = "Phase6-D"
READY_FOR_PHASE6E_BASELINE_REVIEW = "READY_FOR_PHASE6E_BASELINE_REVIEW"
BLOCKED_BY_LABEL_DATASET = "BLOCKED_BY_LABEL_DATASET"
BLOCKED_BY_LEAKAGE_AUDIT = "BLOCKED_BY_LEAKAGE_AUDIT"

DEFAULT_ALIGNMENT_CSV_PATH = Path("reports/position_management_ai/phase6d_baseline_label_alignment.csv")
DEFAULT_ALIGNMENT_JSON_PATH = Path("reports/position_management_ai/phase6d_baseline_label_alignment.json")
DEFAULT_MISMATCH_CSV_PATH = Path("reports/position_management_ai/phase6d_baseline_label_mismatches.csv")
DEFAULT_AUDIT_PATH = Path("reports/position_management_ai/phase6d_baseline_label_audit.json")

DECISION_LABELS = (
    "label__label_continue_winner",
    "label__label_exit_before_drawdown",
    "label__label_add_candidate",
    "label__label_reduce_candidate",
)


@dataclass(frozen=True)
class Phase6DAlignmentResult:
    alignment: pd.DataFrame
    mismatches: pd.DataFrame
    summary: dict[str, Any]
    audit: dict[str, Any]


def run_phase6d_baseline_label_alignment_audit(
    *,
    dataset_path: Path = DEFAULT_PHASE6C_DATASET_PATH,
    alignment_csv_path: Path = DEFAULT_ALIGNMENT_CSV_PATH,
    alignment_json_path: Path = DEFAULT_ALIGNMENT_JSON_PATH,
    mismatch_csv_path: Path = DEFAULT_MISMATCH_CSV_PATH,
    audit_path: Path = DEFAULT_AUDIT_PATH,
    created_at: str | None = None,
) -> Phase6DAlignmentResult:
    created_at = created_at or now_utc()
    if not dataset_path.is_file():
        run_phase6c_position_label_dataset_dry_run(created_at=created_at)
    if not dataset_path.is_file():
        audit = blocked_audit(BLOCKED_BY_LABEL_DATASET, created_at)
        summary = build_summary(
            alignment=pd.DataFrame(),
            mismatches=pd.DataFrame(),
            audit=audit,
            dataset_path=dataset_path,
            alignment_csv_path=alignment_csv_path,
            alignment_json_path=alignment_json_path,
            mismatch_csv_path=mismatch_csv_path,
            audit_path=audit_path,
            created_at=created_at,
            readiness_status=BLOCKED_BY_LABEL_DATASET,
        )
        write_json(alignment_json_path, summary)
        write_json(audit_path, audit)
        return Phase6DAlignmentResult(alignment=pd.DataFrame(), mismatches=pd.DataFrame(), summary=summary, audit=audit)

    dataset = pd.read_csv(dataset_path, dtype={"code": str})
    result_frame = apply_baseline_to_label_dataset(dataset, created_at=created_at)
    label_audit = audit_position_label_dataset(dataset, created_at=created_at)
    feature_audit = audit_position_feature_frame(dataset_to_inference_frame(dataset), input_holding_count=len(dataset), created_at=created_at)
    if label_audit["label_leakage_audit_status"] != "OK" or feature_audit["leakage_audit_status"] != "OK":
        readiness_status = BLOCKED_BY_LEAKAGE_AUDIT
    else:
        readiness_status = READY_FOR_PHASE6E_BASELINE_REVIEW

    alignment = build_alignment_table(result_frame)
    mismatches = extract_mismatches(result_frame)
    audit = {
        "phase": PHASE,
        "created_at": created_at,
        "readiness_status": readiness_status,
        "row_count": int(len(result_frame)),
        "action_distribution": action_distribution(result_frame),
        "label_distribution": label_distribution(result_frame),
        "alignment_metrics": alignment_metrics(result_frame),
        "mismatch_count": int(len(mismatches)),
        "add_loss_position_count": int(((result_frame["action"] == "ADD") & (result_frame["feature__unrealized_return"] <= 0)).sum()),
        "add_exit_label_overlap_count": int(((result_frame["action"] == "ADD") & (result_frame["label__label_exit_before_drawdown"])).sum()),
        "label_audit": label_audit,
        "feature_audit": feature_audit,
        "forbidden_feature_audit_status": "OK" if feature_audit["leakage_audit_status"] == "OK" and label_audit["forbidden_feature_audit_status"] == "OK" else "ERROR",
        "leakage_audit_status": "OK" if readiness_status == READY_FOR_PHASE6E_BASELINE_REVIEW else "ERROR",
        "training_executed": False,
        "backtest_executed": False,
        "paper_trading_executed": False,
        "broker_api_executed": False,
        "order_executed": False,
        "capital_allocation_executed": False,
    }
    summary = build_summary(
        alignment=alignment,
        mismatches=mismatches,
        audit=audit,
        dataset_path=dataset_path,
        alignment_csv_path=alignment_csv_path,
        alignment_json_path=alignment_json_path,
        mismatch_csv_path=mismatch_csv_path,
        audit_path=audit_path,
        created_at=created_at,
        readiness_status=readiness_status,
    )
    alignment_csv_path.parent.mkdir(parents=True, exist_ok=True)
    alignment.to_csv(alignment_csv_path, index=False)
    mismatches.to_csv(mismatch_csv_path, index=False)
    write_json(alignment_json_path, summary)
    write_json(audit_path, audit)
    return Phase6DAlignmentResult(alignment=alignment, mismatches=mismatches, summary=summary, audit=audit)


def apply_baseline_to_label_dataset(dataset: pd.DataFrame, *, created_at: str) -> pd.DataFrame:
    inference_frame = dataset_to_inference_frame(dataset)
    output = build_position_management_output(
        inference_frame,
        created_at=created_at,
        inference_run_id=f"phase6d_{created_at.replace(':', '').replace('+', 'Z')}",
    )
    label_columns = ["target_date", "entry_date", "code", *DECISION_LABELS]
    return dataset[label_columns + ["feature__unrealized_return"]].merge(
        output[
            [
                "target_date",
                "code",
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
            ]
        ],
        on=["target_date", "code"],
        how="inner",
        validate="one_to_one",
    )


def dataset_to_inference_frame(dataset: pd.DataFrame) -> pd.DataFrame:
    frame = pd.DataFrame(
        {
            "target_date": dataset["target_date"].astype(str),
            "entry_date": dataset["entry_date"].astype(str),
            "code": dataset["code"].astype(str),
            "entry_price": dataset["feature__entry_price"],
            "current_price": dataset["feature__current_price"],
            "holding_days": dataset["feature__holding_days"],
            "position_size": 100.0,
            "current_return": dataset["feature__unrealized_return"],
            "peak_return": dataset["feature__peak_return"],
            "expected_edge_score": dataset["feature__expected_edge_score"],
            "buy_rank": dataset["feature__buy_rank"],
            "downside_risk_score": dataset["feature__downside_risk_score"],
            "risk_guard_status": dataset["feature__risk_guard_status"],
            "feature_version": dataset["feature_version"],
        }
    )
    feature_passthrough = (
        "return_1d",
        "return_5d",
        "return_20d",
        "volume_ratio_5d",
        "volume_ratio_20d",
        "close_over_ma_5d",
        "close_over_ma_20d",
        "ma_5_20_ratio",
        "ma_20_60_ratio",
        "volatility_20d",
        "trend_strength_score",
    )
    for column in feature_passthrough:
        frame[f"feature__{column}"] = dataset[f"feature__{column}"]
    return frame


def build_alignment_table(frame: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for action, group in frame.groupby("action"):
        row: dict[str, Any] = {"action": action, "row_count": int(len(group))}
        for label in DECISION_LABELS:
            true_count = int(group[label].astype(bool).sum())
            row[f"{label}_true_count"] = true_count
            row[f"{label}_true_rate"] = round(true_count / len(group), 6) if len(group) else 0.0
        rows.append(row)
    return pd.DataFrame(rows).sort_values("action").reset_index(drop=True)


def extract_mismatches(frame: pd.DataFrame) -> pd.DataFrame:
    rows: list[pd.DataFrame] = []
    specs = [
        ("HOLD", "label__label_continue_winner", False, "hold_without_continue_winner"),
        ("HOLD", "label__label_exit_before_drawdown", True, "hold_on_exit_label"),
        ("EXIT", "label__label_exit_before_drawdown", False, "exit_without_exit_label"),
        ("EXIT", "label__label_continue_winner", True, "exit_on_continue_winner"),
        ("ADD", "label__label_add_candidate", False, "add_without_add_label"),
        ("ADD", "label__label_exit_before_drawdown", True, "add_on_exit_label"),
        ("REDUCE", "label__label_reduce_candidate", False, "reduce_without_reduce_label"),
        ("REDUCE", "label__label_continue_winner", True, "reduce_on_continue_winner"),
    ]
    for action, label, expected_value, reason in specs:
        mask = (frame["action"] == action) & (frame[label].astype(bool) == expected_value)
        part = frame[mask].copy()
        if not part.empty:
            part["mismatch_reason"] = reason
            rows.append(part)
    loss_add = frame[(frame["action"] == "ADD") & (frame["feature__unrealized_return"] <= 0)].copy()
    if not loss_add.empty:
        loss_add["mismatch_reason"] = "add_on_loss_position"
        rows.append(loss_add)
    if not rows:
        return pd.DataFrame(columns=list(frame.columns) + ["mismatch_reason"])
    return pd.concat(rows, ignore_index=True)


def alignment_metrics(frame: pd.DataFrame) -> dict[str, Any]:
    return {
        "hold_continue_winner_rate": action_label_rate(frame, "HOLD", "label__label_continue_winner"),
        "hold_exit_label_rate": action_label_rate(frame, "HOLD", "label__label_exit_before_drawdown"),
        "exit_exit_label_rate": action_label_rate(frame, "EXIT", "label__label_exit_before_drawdown"),
        "exit_continue_winner_rate": action_label_rate(frame, "EXIT", "label__label_continue_winner"),
        "add_add_label_rate": action_label_rate(frame, "ADD", "label__label_add_candidate"),
        "add_exit_label_rate": action_label_rate(frame, "ADD", "label__label_exit_before_drawdown"),
        "reduce_reduce_label_rate": action_label_rate(frame, "REDUCE", "label__label_reduce_candidate"),
        "reduce_continue_winner_rate": action_label_rate(frame, "REDUCE", "label__label_continue_winner"),
    }


def action_label_rate(frame: pd.DataFrame, action: str, label: str) -> float:
    group = frame[frame["action"] == action]
    if group.empty:
        return 0.0
    return round(float(group[label].astype(bool).mean()), 6)


def action_distribution(frame: pd.DataFrame) -> dict[str, int]:
    return {str(action): int(count) for action, count in frame["action"].value_counts().sort_index().items()}


def label_distribution(frame: pd.DataFrame) -> dict[str, dict[str, int]]:
    distribution: dict[str, dict[str, int]] = {}
    for label in DECISION_LABELS:
        counts = frame[label].astype(bool).value_counts().to_dict()
        distribution[label] = {"true": int(counts.get(True, 0)), "false": int(counts.get(False, 0))}
    return distribution


def build_summary(
    *,
    alignment: pd.DataFrame,
    mismatches: pd.DataFrame,
    audit: dict[str, Any],
    dataset_path: Path,
    alignment_csv_path: Path,
    alignment_json_path: Path,
    mismatch_csv_path: Path,
    audit_path: Path,
    created_at: str,
    readiness_status: str,
) -> dict[str, Any]:
    return {
        "phase": PHASE,
        "status": "OK" if readiness_status == READY_FOR_PHASE6E_BASELINE_REVIEW else "BLOCKED",
        "readiness_status": readiness_status,
        "created_at": created_at,
        "dataset_path": str(dataset_path),
        "alignment_csv_path": str(alignment_csv_path),
        "alignment_json_path": str(alignment_json_path),
        "mismatch_csv_path": str(mismatch_csv_path),
        "audit_path": str(audit_path),
        "row_count": int(audit.get("row_count", 0)),
        "action_distribution": audit.get("action_distribution", {}),
        "label_distribution": audit.get("label_distribution", {}),
        "alignment_metrics": audit.get("alignment_metrics", {}),
        "alignment_rows": alignment.to_dict(orient="records"),
        "mismatch_count": int(len(mismatches)),
        "add_loss_position_count": int(audit.get("add_loss_position_count", 0)),
        "add_exit_label_overlap_count": int(audit.get("add_exit_label_overlap_count", 0)),
        "forbidden_feature_audit_status": audit.get("forbidden_feature_audit_status", "NOT_RUN"),
        "leakage_audit_status": audit.get("leakage_audit_status", "NOT_RUN"),
        "training_executed": False,
        "backtest_executed": False,
        "paper_trading_executed": False,
        "broker_api_executed": False,
        "order_executed": False,
        "capital_allocation_executed": False,
    }


def blocked_audit(readiness_status: str, created_at: str) -> dict[str, Any]:
    return {
        "phase": PHASE,
        "created_at": created_at,
        "readiness_status": readiness_status,
        "row_count": 0,
        "action_distribution": {},
        "label_distribution": {},
        "alignment_metrics": {},
        "mismatch_count": 0,
        "forbidden_feature_audit_status": "NOT_RUN",
        "leakage_audit_status": "NOT_RUN",
    }


def now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(to_jsonable(payload), ensure_ascii=True, indent=2, sort_keys=True) + "\n", encoding="utf-8")
