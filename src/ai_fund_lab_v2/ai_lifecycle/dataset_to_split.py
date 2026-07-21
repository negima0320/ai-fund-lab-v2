from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Literal


SufficiencyStatus = Literal["SUFFICIENT", "INSUFFICIENT", "REVIEW_REQUIRED"]
LineageStatus = Literal["PASS", "FAIL", "REVIEW_REQUIRED"]

SUFFICIENT: SufficiencyStatus = "SUFFICIENT"
INSUFFICIENT: SufficiencyStatus = "INSUFFICIENT"
REVIEW_REQUIRED: SufficiencyStatus = "REVIEW_REQUIRED"
NO_RETRAIN_INSUFFICIENT_NEW_DATA = "NO_RETRAIN_INSUFFICIENT_NEW_DATA"

DATASET_REVISION_SCHEMA_VERSION = "phase19_ad_u2_a_dataset_revision.v1"
DATA_SUFFICIENCY_POLICY_VERSION = "phase19_ad_u2_a_data_sufficiency.v1"
ROLLING_SPLIT_SCHEMA_VERSION = "phase19_ad_u2_a_versioned_rolling_split.v1"


@dataclass(frozen=True)
class DatasetRevisionMetadata:
    dataset_identity: str
    dataset_revision: str
    component: str
    dataset_path: str
    dataset_hash: str
    schema_hash: str
    row_count: int
    target_date_min: str | None
    target_date_max: str | None
    label_safe_cutoff: str | None
    source_lineage_hash: str
    previous_dataset_revision: str | None = None
    schema_version: str = DATASET_REVISION_SCHEMA_VERSION

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class DataSufficiencyPolicy:
    min_incremental_business_days: int
    min_incremental_rows: int
    required_schema_hash: str
    comparison_logic: str = "AND"
    effective_from: str | None = None
    authority: str = "Phase19-AD-U2 data sufficiency policy"
    policy_version: str = DATA_SUFFICIENCY_POLICY_VERSION

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["policy_hash"] = stable_json_hash({key: value for key, value in payload.items() if key != "policy_hash"})
        return payload


def build_dataset_revision_metadata(
    *,
    component: str,
    dataset_path: Path | str,
    dataset_hash: str,
    schema_hash: str,
    row_count: int,
    target_date_min: str | None,
    target_date_max: str | None,
    label_safe_cutoff: str | None,
    source_lineage: dict[str, Any],
    previous_dataset_revision: str | None = None,
) -> DatasetRevisionMetadata:
    dataset_identity = stable_json_hash(
        {
            "component": component,
            "dataset_path": str(dataset_path),
            "schema_hash": schema_hash,
        }
    )
    source_lineage_hash = stable_json_hash(source_lineage)
    revision_hash = stable_json_hash(
        {
            "component": component,
            "dataset_hash": dataset_hash,
            "schema_hash": schema_hash,
            "row_count": int(row_count),
            "target_date_max": target_date_max,
            "label_safe_cutoff": label_safe_cutoff,
            "source_lineage_hash": source_lineage_hash,
            "previous_dataset_revision": previous_dataset_revision,
        }
    )
    return DatasetRevisionMetadata(
        dataset_identity=f"{component.lower()}:{dataset_identity[:16]}",
        dataset_revision=f"{component.lower()}_dataset_revision_{revision_hash[:16]}",
        component=component,
        dataset_path=str(dataset_path),
        dataset_hash=dataset_hash,
        schema_hash=schema_hash,
        row_count=int(row_count),
        target_date_min=target_date_min,
        target_date_max=target_date_max,
        label_safe_cutoff=label_safe_cutoff,
        source_lineage_hash=source_lineage_hash,
        previous_dataset_revision=previous_dataset_revision,
    )


def validate_dataset_lineage(
    *,
    current: DatasetRevisionMetadata | dict[str, Any],
    expected_dataset_hash: str | None = None,
    previous: DatasetRevisionMetadata | dict[str, Any] | None = None,
) -> dict[str, Any]:
    current_payload = _payload(current)
    missing = sorted(
        field
        for field in (
            "dataset_identity",
            "dataset_revision",
            "dataset_hash",
            "schema_hash",
            "row_count",
            "target_date_max",
            "source_lineage_hash",
        )
        if current_payload.get(field) in (None, "")
    )
    checks: dict[str, bool] = {
        "required_fields_present": not missing,
        "dataset_path_present": bool(current_payload.get("dataset_path")),
        "revision_not_self_referential": current_payload.get("previous_dataset_revision") != current_payload.get("dataset_revision"),
    }
    if expected_dataset_hash is not None:
        checks["dataset_hash_match"] = current_payload.get("dataset_hash") == expected_dataset_hash
    if previous is not None:
        previous_payload = _payload(previous)
        checks["schema_continuity"] = current_payload.get("schema_hash") == previous_payload.get("schema_hash")
        checks["lineage_continuity"] = current_payload.get("source_lineage_hash") == previous_payload.get("source_lineage_hash")
        checks["revision_continuity"] = (
            current_payload.get("previous_dataset_revision") == previous_payload.get("dataset_revision")
        )
        checks["date_monotonicity"] = str(current_payload.get("target_date_max") or "") >= str(previous_payload.get("target_date_max") or "")
    status: LineageStatus = "PASS" if checks and all(checks.values()) else "FAIL"
    return {
        "status": status,
        "reason_codes": [name for name, passed in checks.items() if not passed],
        "missing_fields": missing,
        "checks": checks,
        "dataset_revision": current_payload.get("dataset_revision"),
    }


def validate_dataset_revision_binding(
    *,
    revision: DatasetRevisionMetadata | dict[str, Any],
    dataset_file_exists: bool | None = None,
    actual_dataset_hash: str | None = None,
) -> dict[str, Any]:
    payload = _payload(revision)
    path = Path(str(payload.get("dataset_path") or ""))
    exists = path.is_file() if dataset_file_exists is None else bool(dataset_file_exists)
    actual_hash = _file_hash(path) if actual_dataset_hash is None and exists else actual_dataset_hash
    checks = {
        "dataset_path_present": bool(payload.get("dataset_path")),
        "dataset_file_exists": exists,
        "actual_dataset_hash_matches_revision": bool(actual_hash) and actual_hash == payload.get("dataset_hash"),
        "schema_hash_present": bool(payload.get("schema_hash")),
        "source_lineage_hash_present": bool(payload.get("source_lineage_hash")),
    }
    return {
        "status": "PASS" if all(checks.values()) else "FAIL",
        "reason_codes": [name for name, passed in checks.items() if not passed],
        "checks": checks,
        "dataset_path": str(path) if payload.get("dataset_path") else "",
        "declared_dataset_hash": payload.get("dataset_hash"),
        "actual_dataset_hash": actual_hash,
    }


def evaluate_label_safe_availability(
    *,
    dataset_revision: DatasetRevisionMetadata | dict[str, Any],
    latest_trading_date: str | None,
    label_safe_cutoff: str | None,
    target_horizon_business_days: int = 20,
    trading_calendar_dates: list[str] | tuple[str, ...] | None = None,
    unavailable_label_rows: int = 0,
) -> dict[str, Any]:
    payload = _payload(dataset_revision)
    dataset_max = payload.get("target_date_max")
    missing = sorted(
        name
        for name, value in {
            "dataset_target_date_max": dataset_max,
            "latest_trading_date": latest_trading_date,
            "label_safe_cutoff": label_safe_cutoff,
        }.items()
        if not value
    )
    if missing:
        return {
            "status": REVIEW_REQUIRED,
            "reason_codes": ["label_safe_inputs_missing"],
            "missing_fields": missing,
            "target_horizon_business_days": target_horizon_business_days,
        }
    calendar_result = _business_day_horizon_check(
        dataset_max=str(dataset_max),
        latest_trading_date=str(latest_trading_date),
        label_safe_cutoff=str(label_safe_cutoff),
        target_horizon_business_days=target_horizon_business_days,
        trading_calendar_dates=trading_calendar_dates,
    )
    checks = {
        "dataset_max_not_after_cutoff": str(dataset_max) <= str(label_safe_cutoff),
        "dataset_not_after_latest_trading_date": str(dataset_max) <= str(latest_trading_date),
        "business_day_horizon_covered": calendar_result["status"] == "PASS",
        "per_symbol_labels_available": int(unavailable_label_rows) == 0,
    }
    return {
        "status": "PASS" if all(checks.values()) else REVIEW_REQUIRED,
        "reason_codes": [name for name, passed in checks.items() if not passed],
        "checks": checks,
        "dataset_target_date_max": dataset_max,
        "latest_trading_date": latest_trading_date,
        "label_safe_cutoff": label_safe_cutoff,
        "target_horizon_business_days": target_horizon_business_days,
        "business_day_horizon": calendar_result,
        "unavailable_label_rows": int(unavailable_label_rows),
    }


def evaluate_data_sufficiency(
    *,
    current: DatasetRevisionMetadata | dict[str, Any],
    previous: DatasetRevisionMetadata | dict[str, Any] | None,
    policy: DataSufficiencyPolicy | dict[str, Any],
    label_safe_availability: dict[str, Any],
    incremental_business_days: int | None = None,
    incremental_rows: int | None = None,
) -> dict[str, Any]:
    current_payload = _payload(current)
    previous_payload = _payload(previous) if previous is not None else None
    policy_payload = _payload(policy)
    lineage = validate_dataset_lineage(current=current_payload, previous=previous_payload)
    schema_ok = current_payload.get("schema_hash") == policy_payload.get("required_schema_hash")
    label_safe_ok = label_safe_availability.get("status") == "PASS"
    incremental_business_days = _infer_incremental_business_days(
        current_payload,
        previous_payload,
        explicit=incremental_business_days,
    )
    incremental_rows = _infer_incremental_rows(current_payload, previous_payload, explicit=incremental_rows)
    min_days = int(policy_payload.get("min_incremental_business_days") or 0)
    min_rows = int(policy_payload.get("min_incremental_rows") or 0)
    comparison_logic = str(policy_payload.get("comparison_logic") or "AND").upper()
    minimum_incremental_requirement = (
        incremental_business_days >= min_days and incremental_rows >= min_rows
        if comparison_logic == "AND"
        else incremental_business_days >= min_days or incremental_rows >= min_rows
    )
    checks = {
        "dataset_revision_present": bool(current_payload.get("dataset_revision")),
        "label_safe_availability": label_safe_ok,
        "minimum_incremental_business_days": incremental_business_days >= min_days,
        "minimum_incremental_rows": incremental_rows >= min_rows,
        "minimum_incremental_requirement": minimum_incremental_requirement,
        "schema_compatibility": schema_ok,
        "dataset_lineage_continuity": lineage["status"] == "PASS",
        "policy_binding_present": bool(policy_payload.get("policy_hash")) and bool(policy_payload.get("policy_version")),
    }
    failed = [name for name, passed in checks.items() if not passed]
    if not checks["dataset_revision_present"] or not schema_ok or lineage["status"] != "PASS":
        status: SufficiencyStatus = REVIEW_REQUIRED
    elif failed:
        status = INSUFFICIENT
    else:
        status = SUFFICIENT
    reason_codes = list(failed)
    if status == INSUFFICIENT:
        reason_codes.insert(0, NO_RETRAIN_INSUFFICIENT_NEW_DATA)
    return {
        "status": status,
        "decision_code": NO_RETRAIN_INSUFFICIENT_NEW_DATA if status == INSUFFICIENT else status,
        "reason_codes": reason_codes,
        "checks": checks,
        "policy": policy_payload,
        "incremental_business_days": incremental_business_days,
        "incremental_rows": incremental_rows,
        "lineage": lineage,
        "label_safe_availability": label_safe_availability,
        "training_executed": False,
        "runtime_mutation_performed": False,
        "broker_write_executed": False,
    }


def build_versioned_rolling_split_contract(
    *,
    dataset_revision: DatasetRevisionMetadata | dict[str, Any],
    train_start: str,
    train_end: str,
    validation_start: str,
    validation_end: str,
    policy_version: str,
    embargo_business_days: int = 20,
    target_horizon_business_days: int = 20,
    trading_calendar_identity: str | None = None,
    policy_hash: str | None = None,
    split_id: str | None = None,
) -> dict[str, Any]:
    payload = _payload(dataset_revision)
    policy_hash = policy_hash or stable_json_hash(
        {
            "policy_version": policy_version,
            "embargo_business_days": embargo_business_days,
            "target_horizon_business_days": target_horizon_business_days,
            "trading_calendar_identity": trading_calendar_identity,
        }
    )
    split_identity = {
        'dataset_revision': payload.get('dataset_revision'),
        'train_start': train_start,
        'train_end': train_end,
        'validation_start': validation_start,
        'validation_end': validation_end,
        'policy_version': policy_version,
        'policy_hash': policy_hash,
        'embargo_business_days': embargo_business_days,
        'target_horizon_business_days': target_horizon_business_days,
        'trading_calendar_identity': trading_calendar_identity,
        'schema_hash': payload.get('schema_hash'),
    }
    split_id = split_id or f"split_{stable_json_hash(split_identity)[:16]}"
    return {
        "schema_version": ROLLING_SPLIT_SCHEMA_VERSION,
        "split_id": split_id,
        "dataset_revision": payload.get("dataset_revision"),
        "train_start": train_start,
        "train_end": train_end,
        "validation_start": validation_start,
        "validation_end": validation_end,
        "policy_version": policy_version,
        "policy_hash": policy_hash,
        "embargo_business_days": int(embargo_business_days),
        "target_horizon_business_days": int(target_horizon_business_days),
        "trading_calendar_identity": trading_calendar_identity,
        "schema_hash": payload.get("schema_hash"),
        "runtime_consumed": False,
        "generation_input_artifact": True,
    }


def validate_versioned_split_contract(
    *,
    split: dict[str, Any],
    dataset_revision: DatasetRevisionMetadata | dict[str, Any],
    trading_calendar_dates: list[str] | tuple[str, ...] | None = None,
) -> dict[str, Any]:
    payload = _payload(dataset_revision)
    missing = sorted(
        field
        for field in (
            "split_id",
            "dataset_revision",
            "train_start",
            "train_end",
            "validation_start",
            "validation_end",
            "policy_version",
            "policy_hash",
            "embargo_business_days",
            "target_horizon_business_days",
            "schema_hash",
        )
        if not split.get(field)
    )
    embargo_gap = _business_day_gap(
        str(split.get("train_end") or ""),
        str(split.get("validation_start") or ""),
        trading_calendar_dates=trading_calendar_dates,
    )
    checks = {
        "required_fields_present": not missing,
        "schema_version_match": split.get("schema_version") == ROLLING_SPLIT_SCHEMA_VERSION,
        "dataset_revision_match": split.get("dataset_revision") == payload.get("dataset_revision"),
        "schema_hash_match": split.get("schema_hash") == payload.get("schema_hash"),
        "policy_hash_present": bool(split.get("policy_hash")),
        "ordered_train_window": str(split.get("train_start") or "") <= str(split.get("train_end") or ""),
        "ordered_validation_window": str(split.get("validation_start") or "") <= str(split.get("validation_end") or ""),
        "non_overlapping_train_validation": str(split.get("train_end") or "") < str(split.get("validation_start") or ""),
        "embargo_gap_satisfied": embargo_gap >= int(split.get("embargo_business_days") or 0),
        "validation_end_not_after_label_safe_max": str(split.get("validation_end") or "") <= str(payload.get("label_safe_cutoff") or payload.get("target_date_max") or ""),
        "generation_input_only": split.get("generation_input_artifact") is True and split.get("runtime_consumed") is False,
    }
    return {
        "status": "PASS" if all(checks.values()) else "FAIL",
        "reason_codes": [name for name, passed in checks.items() if not passed],
        "missing_fields": missing,
        "checks": checks,
        "embargo_gap_business_days": embargo_gap,
    }


def load_dataset_revision_from_bundle(
    *,
    component: str,
    dataset_dir: Path | str,
    previous_dataset_revision: str | None = None,
) -> DatasetRevisionMetadata:
    root = Path(dataset_dir)
    metadata = _read_json(root / "dataset_metadata.json")
    manifest = _read_json(root / "hash_manifest.json")
    coverage = _read_json(root / "date_coverage.json")
    lineage = _read_json(root / "lineage.json")
    return build_dataset_revision_metadata(
        component=component,
        dataset_path=root / "dataset.parquet",
        dataset_hash=str(manifest.get("dataset_hash") or ""),
        schema_hash=str(manifest.get("schema_hash") or metadata.get("schema_hash") or ""),
        row_count=int(metadata.get("row_count") or 0),
        target_date_min=coverage.get("target_date_min"),
        target_date_max=coverage.get("target_date_max"),
        label_safe_cutoff=(metadata.get("label_safe_cutoff") or {}).get("label_safe_cutoff"),
        source_lineage=lineage,
        previous_dataset_revision=previous_dataset_revision,
    )


def stable_json_hash(payload: Any) -> str:
    encoded = json.dumps(payload, ensure_ascii=True, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def _file_hash(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _payload(value: DatasetRevisionMetadata | DataSufficiencyPolicy | dict[str, Any] | None) -> dict[str, Any]:
    if value is None:
        return {}
    if hasattr(value, "to_dict"):
        return value.to_dict()
    return dict(value)


def _business_day_horizon_check(
    *,
    dataset_max: str,
    latest_trading_date: str,
    label_safe_cutoff: str,
    target_horizon_business_days: int,
    trading_calendar_dates: list[str] | tuple[str, ...] | None,
) -> dict[str, Any]:
    dates = sorted(str(item) for item in (trading_calendar_dates or []) if str(item))
    if not dates:
        return {"status": REVIEW_REQUIRED, "reason": "trading_calendar_missing"}
    if latest_trading_date not in dates:
        return {"status": REVIEW_REQUIRED, "reason": "latest_trading_date_not_in_calendar"}
    eligible = [date for date in dates if date <= latest_trading_date]
    latest_index = eligible.index(latest_trading_date)
    cutoff_index = latest_index - int(target_horizon_business_days)
    if cutoff_index < 0:
        return {"status": REVIEW_REQUIRED, "reason": "calendar_shorter_than_target_horizon"}
    computed_cutoff = eligible[cutoff_index]
    return {
        "status": "PASS" if computed_cutoff == label_safe_cutoff and dataset_max <= computed_cutoff else REVIEW_REQUIRED,
        "reason": "business_day_horizon_covered" if computed_cutoff == label_safe_cutoff and dataset_max <= computed_cutoff else "business_day_horizon_mismatch",
        "computed_label_safe_cutoff": computed_cutoff,
        "declared_label_safe_cutoff": label_safe_cutoff,
        "dataset_target_date_max": dataset_max,
        "latest_trading_date": latest_trading_date,
        "target_horizon_business_days": int(target_horizon_business_days),
    }


def _business_day_gap(
    left: str,
    right: str,
    *,
    trading_calendar_dates: list[str] | tuple[str, ...] | None,
) -> int:
    if not left or not right or right <= left:
        return 0
    dates = sorted(str(item) for item in (trading_calendar_dates or []) if str(item))
    if dates:
        return len([date for date in dates if left < date < right])
    from datetime import date, timedelta

    current = date.fromisoformat(left) + timedelta(days=1)
    end = date.fromisoformat(right)
    count = 0
    while current < end:
        if current.weekday() < 5:
            count += 1
        current += timedelta(days=1)
    return count


def _infer_incremental_business_days(
    current: dict[str, Any],
    previous: dict[str, Any] | None,
    *,
    explicit: int | None,
) -> int:
    if explicit is not None:
        return max(0, int(explicit))
    if previous is None:
        return 0
    current_max = str(current.get("target_date_max") or "")
    previous_max = str(previous.get("target_date_max") or "")
    if not current_max or not previous_max or current_max <= previous_max:
        return 0
    return 1


def _infer_incremental_rows(
    current: dict[str, Any],
    previous: dict[str, Any] | None,
    *,
    explicit: int | None,
) -> int:
    if explicit is not None:
        return max(0, int(explicit))
    if previous is None:
        return 0
    return max(0, int(current.get("row_count") or 0) - int(previous.get("row_count") or 0))
