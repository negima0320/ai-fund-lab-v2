from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any

import pandas as pd

from .cutoff import LabelSafeCutoff
from .source_authority import SourceAuthorityBundle


@dataclass(frozen=True)
class ValidationResult:
    name: str
    status: str
    evidence: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {"name": self.name, "status": self.status, "evidence": self.evidence}


def validate_dataset_bundle_inputs(
    *,
    component: str,
    dataset: pd.DataFrame,
    feature_columns: list[str],
    label_columns: list[str],
    uniqueness_keys: list[str],
    cutoff: LabelSafeCutoff,
    source_authority: SourceAuthorityBundle,
    adapter_audit: dict[str, Any],
) -> list[ValidationResult]:
    return [
        validate_schema(dataset=dataset, feature_columns=feature_columns, label_columns=label_columns),
        validate_pit(dataset=dataset, cutoff=cutoff),
        validate_leakage(dataset=dataset, feature_columns=feature_columns, adapter_audit=adapter_audit),
        validate_uniqueness(dataset=dataset, keys=uniqueness_keys),
        validate_coverage(dataset=dataset, component=component),
        validate_missing(dataset=dataset, feature_columns=feature_columns, label_columns=label_columns),
        validate_lineage(source_authority=source_authority),
    ]


def validation_status(results: list[ValidationResult]) -> str:
    return "PASS" if all(result.status == "PASS" for result in results) else "FAIL"


def validate_schema(*, dataset: pd.DataFrame, feature_columns: list[str], label_columns: list[str]) -> ValidationResult:
    missing = sorted(column for column in ("target_date", "code", "dataset_version") if column not in dataset.columns)
    bad_features = sorted(column for column in feature_columns if not column.startswith("feature__"))
    bad_labels = sorted(column for column in label_columns if not column.startswith("label__"))
    status = "PASS" if not missing and feature_columns and label_columns and not bad_features and not bad_labels else "FAIL"
    return ValidationResult(
        "Schema",
        status,
        {
            "row_count": int(len(dataset)),
            "feature_column_count": len(feature_columns),
            "label_column_count": len(label_columns),
            "missing_required_columns": missing,
            "bad_feature_columns": bad_features,
            "bad_label_columns": bad_labels,
            "feature_schema_hash": schema_hash(feature_columns),
            "target_schema_hash": schema_hash(label_columns),
        },
    )


def validate_pit(*, dataset: pd.DataFrame, cutoff: LabelSafeCutoff) -> ValidationResult:
    if dataset.empty:
        violations = 1
        max_date = None
    else:
        target = dataset["target_date"].astype(str)
        max_date = target.max()
        violations = int((target > cutoff.label_safe_cutoff).sum())
        if "as_of_date" in dataset.columns:
            violations += int((dataset["as_of_date"].astype(str) > target).sum())
    return ValidationResult(
        "PIT",
        "PASS" if violations == 0 else "FAIL",
        {"label_safe_cutoff": cutoff.label_safe_cutoff, "max_target_date": max_date, "violation_count": violations},
    )


def validate_leakage(*, dataset: pd.DataFrame, feature_columns: list[str], adapter_audit: dict[str, Any]) -> ValidationResult:
    forbidden_terms = (
        "future_return_",
        "future_max_return_",
        "future_max_drawdown_",
        "expected_edge_label_",
        "risk_adjusted_future_return_",
        "opportunity_rank_label_",
        "trade_result",
        "backtest",
        "paper_trading",
    )
    bad = sorted(column for column in feature_columns if any(term in column.replace("feature__", "", 1) for term in forbidden_terms))
    audit_status = adapter_audit.get("status") or adapter_audit.get("leakage_audit_status")
    status = "PASS" if not bad and audit_status in {"OK", None} else "FAIL"
    return ValidationResult(
        "Leakage",
        status,
        {
            "no_leakage_status": "NO_LEAKAGE_PASS" if status == "PASS" else "NO_LEAKAGE_FAIL",
            "forbidden_feature_columns": bad,
            "adapter_leakage_status": audit_status,
        },
    )


def validate_uniqueness(*, dataset: pd.DataFrame, keys: list[str]) -> ValidationResult:
    missing = [key for key in keys if key not in dataset.columns]
    duplicates = int(dataset.duplicated(keys).sum()) if not missing else len(dataset)
    return ValidationResult(
        "Uniqueness",
        "PASS" if not missing and duplicates == 0 else "FAIL",
        {"keys": keys, "missing_keys": missing, "duplicate_row_count": duplicates},
    )


def validate_coverage(*, dataset: pd.DataFrame, component: str) -> ValidationResult:
    dates = sorted(dataset["target_date"].astype(str).unique().tolist()) if "target_date" in dataset else []
    codes = int(dataset["code"].nunique()) if "code" in dataset else 0
    status = "PASS" if len(dataset) > 0 and dates and codes > 0 else "FAIL"
    return ValidationResult(
        "Coverage",
        status,
        {"component": component, "row_count": int(len(dataset)), "code_count": codes, "target_date_min": dates[0] if dates else None, "target_date_max": dates[-1] if dates else None},
    )


def validate_missing(*, dataset: pd.DataFrame, feature_columns: list[str], label_columns: list[str]) -> ValidationResult:
    required = feature_columns + label_columns
    missing_labels = int(dataset[label_columns].isna().sum().sum()) if label_columns else 1
    missing_feature_rate = round(float(dataset[feature_columns].isna().sum().sum()) / max(len(dataset) * max(len(feature_columns), 1), 1), 6)
    status = "PASS" if required and missing_labels == 0 else "FAIL"
    return ValidationResult(
        "Missing",
        status,
        {"missing_label_cell_count": missing_labels, "missing_feature_rate": missing_feature_rate},
    )


def validate_lineage(*, source_authority: SourceAuthorityBundle) -> ValidationResult:
    evidence = source_authority.to_dict()
    missing_hashes = sorted(name for name, item in evidence.items() if not item.get("content_hash") or not item.get("schema_hash"))
    return ValidationResult(
        "Lineage",
        "PASS" if not missing_hashes else "FAIL",
        {"authority_count": len(evidence), "missing_hash_authorities": missing_hashes},
    )


def schema_hash(columns: list[str]) -> str:
    payload = json.dumps(sorted(columns), ensure_ascii=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()
