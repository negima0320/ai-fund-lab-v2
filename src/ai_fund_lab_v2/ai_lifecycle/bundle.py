from __future__ import annotations

import hashlib
import json
import os
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd

from .cutoff import LabelSafeCutoff
from .source_authority import SourceAuthorityBundle
from .validators import ValidationResult, schema_hash, validation_status


REQUIRED_BUNDLE_FILES = (
    "dataset.parquet",
    "dataset_metadata.json",
    "feature_schema.json",
    "target_schema.json",
    "lineage.json",
    "data_quality.json",
    "date_coverage.json",
    "drop_reasons.csv",
    "hash_manifest.json",
    "status.json",
)


@dataclass(frozen=True)
class BundleWriteResult:
    final_dir: Path
    temp_dir: Path
    status: str
    hash_manifest: dict[str, Any]
    files: list[str]


class DatasetBundleWriter:
    def __init__(self, *, final_dir: Path, tmp_parent: Path | None = None) -> None:
        self.final_dir = final_dir
        self.tmp_parent = tmp_parent or final_dir.parent

    def write_and_publish(
        self,
        *,
        component: str,
        dataset: pd.DataFrame,
        feature_columns: list[str],
        label_columns: list[str],
        uniqueness_keys: list[str],
        cutoff: LabelSafeCutoff,
        source_authority: SourceAuthorityBundle,
        validations: list[ValidationResult],
        adapter_summary: dict[str, Any],
        created_at: str,
    ) -> BundleWriteResult:
        tmp_dir = self.tmp_parent / f".{self.final_dir.name}.tmp"
        if tmp_dir.exists():
            shutil.rmtree(tmp_dir)
        tmp_dir.mkdir(parents=True, exist_ok=False)

        dataset_path = tmp_dir / "dataset.parquet"
        ordered = dataset.copy()
        ordered.to_parquet(dataset_path, index=False, engine="pyarrow")

        feature_schema = _schema_payload(feature_columns, "feature")
        target_schema = _schema_payload(label_columns, "target")
        lineage = {"source_authority": source_authority.to_dict(), "adapter": adapter_summary}
        quality = _quality_payload(dataset, feature_columns, label_columns, validations)
        coverage = _coverage_payload(dataset, cutoff)
        drop_reasons = _drop_reasons(dataset)
        metadata = {
            "component": component,
            "created_at": created_at,
            "dataset_version": dataset_version_for(component=component, dataset=ordered, feature_columns=feature_columns, label_columns=label_columns),
            "row_count": int(len(ordered)),
            "input_artifacts": source_authority.to_dict(),
            "source_authority": source_authority.to_dict(),
            "pit_business_date": cutoff.latest_trading_date,
            "label_safe_cutoff": cutoff.to_dict(),
            "feature_schema_version": feature_schema["schema_hash"],
            "target_schema_version": target_schema["schema_hash"],
            "row_uniqueness_keys": uniqueness_keys,
            "missing_policy": "missing labels inside label-safe window block publication; missing features are reported",
            "drop_policy": "rows without labels after label-safe cutoff are excluded before publication",
            "lineage_refs_and_hashes": lineage,
            "builder_version": "phase18_b_common_pit_dataset_rebuild_pipeline_v1",
            "output_location": str(self.final_dir),
            "training_executed": False,
            "promotion_performed": False,
            "runtime_switch_performed": False,
            "broker_write_executed": False,
        }

        _write_json(tmp_dir / "feature_schema.json", feature_schema)
        _write_json(tmp_dir / "target_schema.json", target_schema)
        _write_json(tmp_dir / "lineage.json", lineage)
        _write_json(tmp_dir / "data_quality.json", quality)
        _write_json(tmp_dir / "date_coverage.json", coverage)
        drop_reasons.to_csv(tmp_dir / "drop_reasons.csv", index=False)

        hash_manifest = _hash_manifest(tmp_dir, dataset_path, feature_schema, target_schema, metadata)
        metadata["content_hash"] = hash_manifest["dataset_hash"]
        metadata["schema_hash"] = hash_manifest["schema_hash"]
        _write_json(tmp_dir / "dataset_metadata.json", metadata)
        hash_manifest = _hash_manifest(tmp_dir, dataset_path, feature_schema, target_schema, metadata)
        _write_json(tmp_dir / "hash_manifest.json", hash_manifest)
        status_payload = {
            "status": "PASS",
            "component": component,
            "validations": [result.to_dict() for result in validations],
            "validation_status": validation_status(validations),
            "published": True,
        }
        _write_json(tmp_dir / "status.json", status_payload)

        missing = [name for name in REQUIRED_BUNDLE_FILES if not (tmp_dir / name).is_file()]
        if missing:
            raise ValueError(f"bundle publication blocked; missing files: {', '.join(missing)}")
        if validation_status(validations) != "PASS":
            raise ValueError("bundle publication blocked by validation failure")

        if self.final_dir.exists():
            shutil.rmtree(self.final_dir)
        os.replace(tmp_dir, self.final_dir)
        return BundleWriteResult(
            final_dir=self.final_dir,
            temp_dir=tmp_dir,
            status="PUBLISHED",
            hash_manifest=hash_manifest,
            files=sorted(REQUIRED_BUNDLE_FILES),
        )


class FailureArtifactWriter:
    def __init__(self, *, report_dir: Path) -> None:
        self.report_dir = report_dir

    def write(self, *, component: str, stage: str, error: str, final_dir: Path, temp_dir: Path | None = None) -> Path:
        self.report_dir.mkdir(parents=True, exist_ok=True)
        path = self.report_dir / f"{component.lower()}_{stage}_failure.json"
        _write_json(
            path,
            {
                "status": "FAILED",
                "component": component,
                "stage": stage,
                "error": error,
                "final_bundle_created": final_dir.exists(),
                "temp_dir": str(temp_dir) if temp_dir else None,
            },
        )
        return path


def _schema_payload(columns: list[str], kind: str) -> dict[str, Any]:
    return {
        "kind": kind,
        "columns": [{"name": column} for column in sorted(columns)],
        "schema_hash": schema_hash(columns),
    }


def _quality_payload(dataset: pd.DataFrame, feature_columns: list[str], label_columns: list[str], validations: list[ValidationResult]) -> dict[str, Any]:
    return {
        "row_count": int(len(dataset)),
        "feature_column_count": len(feature_columns),
        "label_column_count": len(label_columns),
        "missing_feature_cell_count": int(dataset[feature_columns].isna().sum().sum()) if feature_columns else 0,
        "missing_label_cell_count": int(dataset[label_columns].isna().sum().sum()) if label_columns else 0,
        "validations": [result.to_dict() for result in validations],
    }


def _coverage_payload(dataset: pd.DataFrame, cutoff: LabelSafeCutoff) -> dict[str, Any]:
    dates = sorted(dataset["target_date"].astype(str).unique().tolist()) if "target_date" in dataset else []
    return {
        "target_date_min": dates[0] if dates else None,
        "target_date_max": dates[-1] if dates else None,
        "target_date_count": len(dates),
        "code_count": int(dataset["code"].nunique()) if "code" in dataset else 0,
        "latest_trading_date": cutoff.latest_trading_date,
        "label_safe_cutoff": cutoff.label_safe_cutoff,
        "dataset_lag_business_days": cutoff.dataset_lag_business_days,
        "model_training_lag_business_days": cutoff.model_training_lag_business_days,
        "model_acceptance_age_business_days": cutoff.model_acceptance_age_business_days,
    }


def _drop_reasons(dataset: pd.DataFrame) -> pd.DataFrame:
    if "feature__excluded_reason" not in dataset.columns:
        return pd.DataFrame([{"drop_reason": "none", "row_count": 0}])
    counts = dataset["feature__excluded_reason"].fillna("").replace("", "none").value_counts().reset_index()
    counts.columns = ["drop_reason", "row_count"]
    return counts


def dataset_version_for(*, component: str, dataset: pd.DataFrame, feature_columns: list[str], label_columns: list[str]) -> str:
    payload = {
        "component": component,
        "columns": sorted(dataset.columns),
        "feature_schema_hash": schema_hash(feature_columns),
        "target_schema_hash": schema_hash(label_columns),
    }
    encoded = json.dumps(payload, ensure_ascii=True, sort_keys=True, separators=(",", ":"))
    return f"{component.lower()}_dataset_{hashlib.sha256(encoded.encode('utf-8')).hexdigest()[:16]}"


def _hash_manifest(
    tmp_dir: Path,
    dataset_path: Path,
    feature_schema: dict[str, Any],
    target_schema: dict[str, Any],
    metadata: dict[str, Any],
) -> dict[str, Any]:
    file_hashes = {path.name: _file_hash(path) for path in sorted(tmp_dir.iterdir()) if path.is_file()}
    schema_payload = {
        "feature_schema_hash": feature_schema["schema_hash"],
        "target_schema_hash": target_schema["schema_hash"],
        "metadata_keys_hash": _json_hash(sorted(metadata.keys())),
    }
    return {
        "dataset_hash": _file_hash(dataset_path),
        "schema_hash": _json_hash(schema_payload),
        "feature_schema_hash": feature_schema["schema_hash"],
        "target_schema_hash": target_schema["schema_hash"],
        "file_hashes": file_hashes,
    }


def _file_hash(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _json_hash(payload: Any) -> str:
    encoded = json.dumps(payload, ensure_ascii=True, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def _write_json(path: Path, payload: Any) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=True, indent=2, sort_keys=True) + "\n", encoding="utf-8")
