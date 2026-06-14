from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

PHASE = "Phase5-D"
DATASET_VERSION = "opportunity_dataset_v1"
FEATURE_VERSION = "opportunity_feature_v1"
READY_FOR_OPPORTUNITY_TRAINING = "READY_FOR_OPPORTUNITY_TRAINING"
BLOCKED_BY_JOIN_COVERAGE = "BLOCKED_BY_JOIN_COVERAGE"
BLOCKED_BY_LEAKAGE_AUDIT = "BLOCKED_BY_LEAKAGE_AUDIT"
BLOCKED_BY_INPUT = "BLOCKED_BY_INPUT"

TRAIN_END = "2024-12-31"
VALIDATION_END = "2025-12-31"

CANDIDATE_COLUMNS = {
    "target_date",
    "code",
    "candidate_score",
    "candidate_rank",
    "candidate_reason",
    "model_version",
    "feature_snapshot_id",
    "candidate_inference_run_id",
}

FEATURE_META_COLUMNS = {
    "target_date",
    "as_of_date",
    "code",
    "feature_version",
    "feature_set_name",
    "source_snapshot_id",
    "data_start_date",
    "data_end_date",
    "created_at",
    "universe_eligible",
    "excluded_reason",
}

RAW_LABEL_COLUMNS = (
    "future_return_20d",
    "future_max_return_20d",
    "future_max_drawdown_20d",
    "downside_bad_20d",
    "top_decile_20d",
)

LABEL_COLUMNS = (
    "future_return_20d",
    "future_max_return_20d",
    "future_max_drawdown_20d",
    "downside_bad_20d",
    "top_decile_20d",
    "risk_adjusted_future_return_20d",
    "expected_edge_label_20d",
    "opportunity_positive_20d",
    "high_expected_edge_20d",
    "opportunity_rank_label_20d",
    "opportunity_quantile_label_20d",
    "is_top5_expected_edge_20d",
    "is_top10_expected_edge_20d",
    "is_top20_expected_edge_20d",
)

FORBIDDEN_FEATURE_PREFIXES = (
    "future_return_",
    "future_max_return_",
    "future_max_drawdown_",
    "downside_bad_",
    "top_decile_",
    "expected_edge_label_",
    "risk_adjusted_future_return_",
    "opportunity_rank_label_",
)

FORBIDDEN_FEATURE_TERMS = (
    "trade_result",
    "trade_profit",
    "selected",
    "bought",
    "sold",
    "cash",
    "portfolio",
    "annual_return",
    "final_assets",
    "backtest",
    "paper_trading",
    "pm_multiplier",
    "opportunity_output",
    "candidate_evaluation",
)


@dataclass(frozen=True)
class OpportunityDatasetBuildResult:
    dataset: pd.DataFrame
    summary: dict[str, Any]
    audit: dict[str, Any]


def build_opportunity_dataset(
    *,
    candidate_path: Path,
    feature_path: Path,
    label_path: Path,
    output_dir: Path = Path("reports/opportunity_ai/phase5d"),
    output_format: str = "parquet",
) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    dataset_path = output_dir / "opportunity_dataset.parquet"
    summary_path = output_dir / "opportunity_dataset_summary.json"
    audit_path = output_dir / "opportunity_dataset_audit.json"

    candidate = read_table(candidate_path)
    feature = read_table(feature_path)
    label = read_table(label_path)
    result = build_opportunity_dataset_frame(candidate_frame=candidate, feature_frame=feature, label_frame=label)

    if output_format != "parquet":
        raise ValueError("Phase5-D currently writes parquet only")
    result.dataset.to_parquet(dataset_path, index=False, engine="pyarrow")

    summary = {
        **result.summary,
        "dataset_output_path": str(dataset_path),
        "summary_path": str(summary_path),
        "audit_path": str(audit_path),
        "candidate_path": str(candidate_path),
        "feature_path": str(feature_path),
        "label_path": str(label_path),
    }
    write_json(summary_path, summary)
    write_json(audit_path, result.audit)
    return summary


def build_opportunity_dataset_frame(
    *,
    candidate_frame: pd.DataFrame,
    feature_frame: pd.DataFrame,
    label_frame: pd.DataFrame,
    created_at: str | None = None,
) -> OpportunityDatasetBuildResult:
    created_at = created_at or now_utc()
    candidate = normalize_key_columns(candidate_frame)
    feature = normalize_key_columns(feature_frame)
    label = normalize_key_columns(label_frame)
    label = ensure_phase5_labels(label)

    candidate = candidate.drop_duplicates(["target_date", "code"], keep="first")
    feature = feature.drop_duplicates(["target_date", "code"], keep="first")
    label = label.drop_duplicates(["target_date", "code"], keep="first")

    candidate_feature_columns = [column for column in ("candidate_score", "candidate_rank", "candidate_reason") if column in candidate.columns]
    jq_feature_columns = select_jquants_feature_columns(feature)
    label_columns = [column for column in LABEL_COLUMNS if column in label.columns]

    candidate_meta_columns = [column for column in ("target_date", "code", "model_version", "feature_snapshot_id", "candidate_inference_run_id") if column in candidate.columns]
    candidate_part = candidate[candidate_meta_columns + candidate_feature_columns].rename(
        columns={column: f"feature__{column}" for column in candidate_feature_columns}
    )
    feature_part = feature[["target_date", "code"] + _optional_columns(feature, ("as_of_date", "feature_version")) + jq_feature_columns].rename(
        columns={column: f"feature__{column}" for column in jq_feature_columns}
    )
    label_part = label[["target_date", "code"] + _optional_columns(label, ("label_version",)) + label_columns].rename(
        columns={column: f"label__{column}" for column in label_columns}
    )

    dataset = candidate_part.merge(feature_part, on=["target_date", "code"], how="inner", validate="one_to_one")
    dataset = dataset.merge(label_part, on=["target_date", "code"], how="inner", validate="one_to_one")
    dataset = add_relative_labels_to_dataset(dataset)
    if "as_of_date" not in dataset.columns:
        dataset["as_of_date"] = dataset["target_date"]
    if "feature_version" not in dataset.columns:
        dataset["feature_version"] = FEATURE_VERSION
    if "label_version" not in dataset.columns:
        dataset["label_version"] = "opportunity_label_v1"
    dataset["dataset_version"] = DATASET_VERSION
    dataset["split"] = dataset["target_date"].map(assign_time_series_split)
    dataset["created_at"] = created_at

    meta_columns = [
        "target_date",
        "as_of_date",
        "code",
        "dataset_version",
        "feature_version",
        "label_version",
        "split",
        "created_at",
    ]
    optional_meta = [column for column in ("model_version", "feature_snapshot_id", "candidate_inference_run_id") if column in dataset.columns]
    feature_columns = sorted(column for column in dataset.columns if column.startswith("feature__"))
    prefixed_label_columns = sorted(column for column in dataset.columns if column.startswith("label__"))
    dataset = dataset[meta_columns + optional_meta + feature_columns + prefixed_label_columns]

    audit = audit_opportunity_dataset(
        dataset,
        source_feature_columns=[str(column) for column in feature.columns],
        source_candidate_count=len(candidate),
        source_feature_count=len(feature),
        source_label_count=len(label),
    )
    split_counts = dataset["split"].value_counts().to_dict() if "split" in dataset.columns else {}
    readiness_status = READY_FOR_OPPORTUNITY_TRAINING
    if len(dataset) == 0:
        readiness_status = BLOCKED_BY_JOIN_COVERAGE
    elif audit["leakage_audit_status"] != "OK":
        readiness_status = BLOCKED_BY_LEAKAGE_AUDIT

    summary = {
        "phase": PHASE,
        "status": "OK" if readiness_status == READY_FOR_OPPORTUNITY_TRAINING else "BLOCKED",
        "readiness_status": readiness_status,
        "dataset_build_executed": True,
        "candidate_row_count": int(len(candidate)),
        "feature_row_count": int(len(feature)),
        "label_row_count": int(len(label)),
        "joined_row_count": int(len(dataset)),
        "join_success_rate": rate(len(dataset), len(candidate)),
        "train_row_count": int(split_counts.get("train", 0)),
        "validation_row_count": int(split_counts.get("validation", 0)),
        "test_row_count": int(split_counts.get("test", 0)),
        "feature_column_count": len(feature_columns),
        "label_column_count": len(prefixed_label_columns),
        "feature_columns": feature_columns,
        "label_columns": prefixed_label_columns,
        "leakage_audit_status": audit["leakage_audit_status"],
        "feature_label_columns_separated": audit["feature_label_columns_separated"],
        "target_date_split_separated": audit["target_date_split_separated"],
        "training_executed": False,
        "inference_executed": False,
        "backtest_executed": False,
        "paper_trading_executed": False,
        "broker_api_executed": False,
        "order_executed": False,
        "capital_allocation_executed": False,
        "promotion_performed": False,
        "reader_switch_performed": False,
        "recommended_next_action": "Phase5-E Opportunity Model Training." if readiness_status == READY_FOR_OPPORTUNITY_TRAINING else "Fix Phase5-D dataset blocker before training.",
    }
    return OpportunityDatasetBuildResult(dataset=dataset, summary=summary, audit=audit)


def ensure_phase5_labels(label: pd.DataFrame) -> pd.DataFrame:
    label = label.copy()
    required = {"future_return_20d", "future_max_return_20d", "future_max_drawdown_20d"}
    missing = sorted(required - set(label.columns))
    if missing:
        raise ValueError(f"label table is missing required columns: {', '.join(missing)}")
    if "downside_bad_20d" not in label.columns:
        label["downside_bad_20d"] = (label["future_max_drawdown_20d"] <= -0.10) | (label["future_return_20d"] <= -0.05)
    label["risk_adjusted_future_return_20d"] = (
        0.60 * label["future_return_20d"].clip(lower=-0.30, upper=0.50)
        + 0.30 * label["future_max_return_20d"].clip(lower=0.00, upper=0.80)
        - 0.30 * label["future_max_drawdown_20d"].abs().clip(upper=0.30)
        - 0.20 * label["downside_bad_20d"].astype(float)
    )
    label["expected_edge_label_20d"] = label["risk_adjusted_future_return_20d"]
    label["opportunity_positive_20d"] = (label["expected_edge_label_20d"] > 0) & (~label["downside_bad_20d"].astype(bool))
    return label


def add_relative_labels_to_dataset(dataset: pd.DataFrame) -> pd.DataFrame:
    if dataset.empty:
        for column in (
            "label__top_decile_20d",
            "label__high_expected_edge_20d",
            "label__opportunity_rank_label_20d",
            "label__opportunity_quantile_label_20d",
            "label__is_top5_expected_edge_20d",
            "label__is_top10_expected_edge_20d",
            "label__is_top20_expected_edge_20d",
        ):
            if column not in dataset.columns:
                dataset[column] = pd.Series(dtype="object")
        return dataset
    dataset = dataset.copy()
    grouped = dataset.groupby("target_date", group_keys=False)
    dataset["label__opportunity_rank_label_20d"] = grouped["label__expected_edge_label_20d"].rank(method="first", ascending=False).astype(int)
    group_sizes = grouped["code"].transform("count")
    top_decile_limit = (group_sizes * 0.10).clip(lower=1).round().astype(int)
    top20_limit = (group_sizes * 0.20).clip(lower=1).round().astype(int)
    dataset["label__top_decile_20d"] = dataset["label__opportunity_rank_label_20d"] <= top_decile_limit
    dataset["label__high_expected_edge_20d"] = dataset["label__opportunity_rank_label_20d"] <= top20_limit
    dataset["label__is_top5_expected_edge_20d"] = dataset["label__opportunity_rank_label_20d"] <= 5
    dataset["label__is_top10_expected_edge_20d"] = dataset["label__opportunity_rank_label_20d"] <= 10
    dataset["label__is_top20_expected_edge_20d"] = dataset["label__opportunity_rank_label_20d"] <= 20
    dataset["label__opportunity_quantile_label_20d"] = grouped["label__expected_edge_label_20d"].transform(_quantile_labels)
    return dataset


def _quantile_labels(values: pd.Series) -> pd.Series:
    ranks = values.rank(method="first", ascending=True)
    pct = ranks / len(values)
    return pd.cut(pct, bins=[0, 0.2, 0.4, 0.6, 0.8, 1.0], labels=["Q1", "Q2", "Q3", "Q4", "Q5"], include_lowest=True).astype(str)


def select_jquants_feature_columns(feature: pd.DataFrame) -> list[str]:
    return [
        column
        for column in feature.columns
        if column not in FEATURE_META_COLUMNS and not is_forbidden_feature_column(column)
    ]


def audit_opportunity_dataset(
    dataset: pd.DataFrame,
    *,
    source_feature_columns: list[str] | None = None,
    source_candidate_count: int,
    source_feature_count: int,
    source_label_count: int,
) -> dict[str, Any]:
    source_feature_columns = source_feature_columns or []
    columns = [str(column) for column in dataset.columns]
    feature_columns = [column for column in columns if column.startswith("feature__")]
    label_columns = [column for column in columns if column.startswith("label__")]
    forbidden_feature_columns = [
        column for column in feature_columns if is_forbidden_feature_column(column.replace("feature__", "", 1))
    ]
    unprefixed_label_columns = [column for column in columns if column in LABEL_COLUMNS or column in RAW_LABEL_COLUMNS]
    trade_result_columns = [column for column in feature_columns if contains_any(column, ("trade_result", "trade_profit"))]
    backtest_columns = [column for column in feature_columns if "backtest" in column.lower()]
    portfolio_columns = [column for column in feature_columns if contains_any(column, ("portfolio", "cash", "final_assets", "annual_return"))]
    ai_output_columns = [
        column
        for column in feature_columns
        if contains_any(column, ("opportunity_output", "candidate_evaluation", "expected_edge_score", "buy_rank"))
    ]
    source_operational_forbidden_columns = [
        column
        for column in source_feature_columns
        if contains_any(
            column,
            (
                "trade_result",
                "trade_profit",
                "selected",
                "bought",
                "sold",
                "cash",
                "portfolio",
                "annual_return",
                "final_assets",
                "backtest",
                "paper_trading",
                "pm_multiplier",
                "opportunity_output",
                "candidate_evaluation",
            ),
        )
    ]
    all_forbidden_feature_columns = forbidden_feature_columns + [
        f"feature__{column}" for column in source_operational_forbidden_columns
    ]
    as_of_violations = count_as_of_date_violations(dataset)
    split_dates = dataset[["target_date", "split"]].drop_duplicates() if {"target_date", "split"}.issubset(dataset.columns) else pd.DataFrame()
    target_date_split_separated = bool(split_dates.empty or split_dates["target_date"].value_counts().max() == 1)
    separated = bool(feature_columns) and bool(label_columns) and not unprefixed_label_columns
    leakage_ok = not (
        forbidden_feature_columns
        or trade_result_columns
        or backtest_columns
        or portfolio_columns
        or ai_output_columns
        or source_operational_forbidden_columns
        or unprefixed_label_columns
        or as_of_violations
    ) and separated and target_date_split_separated
    return {
        "phase": PHASE,
        "created_at": now_utc(),
        "source_candidate_count": int(source_candidate_count),
        "source_feature_count": int(source_feature_count),
        "source_label_count": int(source_label_count),
        "dataset_row_count": int(len(dataset)),
        "forbidden_feature_column_count": len(all_forbidden_feature_columns),
        "forbidden_feature_columns": all_forbidden_feature_columns,
        "source_operational_forbidden_columns": source_operational_forbidden_columns,
        "future_column_in_feature_count": len([column for column in forbidden_feature_columns if column.startswith("feature__future")]),
        "trade_result_column_in_feature_count": len(trade_result_columns)
        + len([column for column in source_operational_forbidden_columns if contains_any(column, ("trade_result", "trade_profit"))]),
        "backtest_column_in_feature_count": len(backtest_columns)
        + len([column for column in source_operational_forbidden_columns if "backtest" in column.lower()]),
        "ai_output_column_in_feature_count": len(ai_output_columns)
        + len([column for column in source_operational_forbidden_columns if contains_any(column, ("opportunity_output", "candidate_evaluation"))]),
        "portfolio_column_in_feature_count": len(portfolio_columns)
        + len([column for column in source_operational_forbidden_columns if contains_any(column, ("portfolio", "cash", "final_assets", "annual_return"))]),
        "unprefixed_label_column_count": len(unprefixed_label_columns),
        "unprefixed_label_columns": unprefixed_label_columns,
        "as_of_date_violation_count": as_of_violations,
        "missing_feature_rate": missing_feature_rate(dataset, feature_columns),
        "nan_rate": missing_feature_rate(dataset, columns),
        "feature_label_columns_separated": separated,
        "target_date_split_separated": target_date_split_separated,
        "leakage_audit_status": "OK" if leakage_ok else "ERROR",
    }


def assign_time_series_split(target_date: str) -> str:
    if target_date <= TRAIN_END:
        return "train"
    if target_date <= VALIDATION_END:
        return "validation"
    return "test"


def normalize_key_columns(frame: pd.DataFrame) -> pd.DataFrame:
    frame = frame.copy()
    if "target_date" not in frame.columns or "code" not in frame.columns:
        raise ValueError("table must contain target_date and code")
    frame["target_date"] = frame["target_date"].astype(str)
    frame["code"] = frame["code"].astype(str)
    return frame


def read_table(path: Path) -> pd.DataFrame:
    if path.suffix == ".parquet":
        return pd.read_parquet(path)
    if path.suffix == ".csv":
        return pd.read_csv(path, dtype={"code": str})
    payload = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(payload, dict) and isinstance(payload.get("rows"), list):
        return pd.DataFrame(payload["rows"])
    if isinstance(payload, list):
        return pd.DataFrame(payload)
    raise ValueError(f"Unsupported table payload: {path}")


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=True, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def count_as_of_date_violations(dataset: pd.DataFrame) -> int:
    if "as_of_date" not in dataset.columns or "target_date" not in dataset.columns:
        return 0
    as_of = pd.to_datetime(dataset["as_of_date"], errors="coerce")
    target = pd.to_datetime(dataset["target_date"], errors="coerce")
    return int(((as_of > target) | as_of.isna() | target.isna()).sum())


def missing_feature_rate(dataset: pd.DataFrame, columns: list[str]) -> float:
    if dataset.empty or not columns:
        return 0.0
    return round(float(dataset[columns].isna().sum().sum()) / float(len(dataset) * len(columns)), 6)


def is_forbidden_feature_column(column: str) -> bool:
    normalized = column.strip().lower().replace("-", "_")
    if normalized.startswith(FORBIDDEN_FEATURE_PREFIXES):
        return True
    return contains_any(normalized, FORBIDDEN_FEATURE_TERMS)


def contains_any(value: str, terms: tuple[str, ...]) -> bool:
    normalized = value.lower().replace("-", "_")
    return any(term in normalized for term in terms)


def _optional_columns(frame: pd.DataFrame, columns: tuple[str, ...]) -> list[str]:
    return [column for column in columns if column in frame.columns]


def now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def rate(numerator: int, denominator: int) -> float:
    return round(numerator / denominator, 6) if denominator else 0.0
