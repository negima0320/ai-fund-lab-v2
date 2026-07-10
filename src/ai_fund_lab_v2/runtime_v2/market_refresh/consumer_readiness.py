"""Consumer-specific feature schema readiness checks for Runtime v2."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import pandas as pd


CANONICAL_SCHEMA_VERSION = "runtime_v2_feature_contract_v1"

CANDIDATE_REQUIRED_COLUMNS: tuple[str, ...] = (
    "target_date",
    "code",
    "liquidity_avg_volume_20d",
    "missing_flags_insufficient_history",
    "missing_flags_price",
    "missing_flags_volume",
    "price_momentum_return_20d",
    "price_momentum_return_5d",
    "price_momentum_return_60d",
    "trend_close_over_ma_20d",
    "trend_ma_20_60_ratio",
    "trend_ma_5_20_ratio",
    "volatility_return_std_20d",
    "volume_momentum_ratio_1d_20d",
    "volume_momentum_ratio_5d",
)

OPPORTUNITY_REQUIRED_COLUMNS: tuple[str, ...] = CANDIDATE_REQUIRED_COLUMNS

PM_REQUIRED_COLUMNS: tuple[str, ...] = (
    "target_date",
    "code",
)

CANONICAL_ALIAS_POLICY: dict[str, str] = {
    "missing_flags_insufficient_lookback": "missing_flags_insufficient_history",
}


@dataclass(frozen=True)
class CanonicalFeatureSchema:
    schema_name: str
    schema_version: str
    required_columns: tuple[str, ...]
    optional_columns: tuple[str, ...]
    dtype: dict[str, str]
    nullable: dict[str, bool]
    column_alias: dict[str, str]
    prefix_policy: str


def _dtype_map(columns: tuple[str, ...]) -> dict[str, str]:
    return {
        column: (
            "string"
            if column in {"target_date", "code"}
            else "bool"
            if column.startswith("missing_flags_")
            else "float"
        )
        for column in columns
    }


CANONICAL_FEATURE_SCHEMAS: dict[str, CanonicalFeatureSchema] = {
    "candidate": CanonicalFeatureSchema(
        schema_name="runtime_v2_candidate_feature_input",
        schema_version=CANONICAL_SCHEMA_VERSION,
        required_columns=CANDIDATE_REQUIRED_COLUMNS,
        optional_columns=(),
        dtype=_dtype_map(CANDIDATE_REQUIRED_COLUMNS),
        nullable={column: False for column in CANDIDATE_REQUIRED_COLUMNS},
        column_alias=CANONICAL_ALIAS_POLICY,
        prefix_policy="artifact_unprefixed_consumer_maps_feature_prefix_once",
    ),
    "opportunity": CanonicalFeatureSchema(
        schema_name="runtime_v2_opportunity_feature_input",
        schema_version=CANONICAL_SCHEMA_VERSION,
        required_columns=OPPORTUNITY_REQUIRED_COLUMNS,
        optional_columns=(),
        dtype=_dtype_map(OPPORTUNITY_REQUIRED_COLUMNS),
        nullable={column: False for column in OPPORTUNITY_REQUIRED_COLUMNS},
        column_alias=CANONICAL_ALIAS_POLICY,
        prefix_policy="artifact_unprefixed_consumer_maps_feature_prefix_once",
    ),
    "pm": CanonicalFeatureSchema(
        schema_name="runtime_v2_pm_feature_input",
        schema_version=CANONICAL_SCHEMA_VERSION,
        required_columns=PM_REQUIRED_COLUMNS,
        optional_columns=("no_position_reason",),
        dtype={"target_date": "string", "code": "string", "no_position_reason": "string"},
        nullable={"target_date": False, "code": False, "no_position_reason": True},
        column_alias={},
        prefix_policy="artifact_unprefixed",
    ),
}


@dataclass(frozen=True)
class ConsumerSchemaResult:
    name: str
    schema_name: str
    schema_version: str
    status: str
    artifact_path: str
    required_columns: tuple[str, ...]
    missing_columns: tuple[str, ...]
    unexpected_prefixed_columns: tuple[str, ...] = ()
    alias_mismatches: dict[str, str] | None = None
    row_count: int | None = None
    reason: str = ""

    def to_payload(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["required_columns"] = list(self.required_columns)
        payload["missing_columns"] = list(self.missing_columns)
        payload["unexpected_prefixed_columns"] = list(self.unexpected_prefixed_columns)
        payload["alias_mismatches"] = dict(self.alias_mismatches or {})
        return payload


@dataclass(frozen=True)
class FeatureConsumerReadiness:
    status: str
    reason: str
    consumer_ready: bool
    schema_version: str
    candidate: ConsumerSchemaResult
    opportunity: ConsumerSchemaResult
    pm: ConsumerSchemaResult
    readiness_artifact_path: str = ""

    @property
    def candidate_schema_status(self) -> str:
        return self.candidate.status

    @property
    def opportunity_schema_status(self) -> str:
        return self.opportunity.status

    @property
    def pm_schema_status(self) -> str:
        return self.pm.status

    @property
    def candidate_missing_columns(self) -> tuple[str, ...]:
        return self.candidate.missing_columns

    def to_payload(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "reason": self.reason,
            "consumer_ready": self.consumer_ready,
            "schema_version": self.schema_version,
            "candidate_schema_status": self.candidate_schema_status,
            "candidate_missing_columns": list(self.candidate_missing_columns),
            "opportunity_schema_status": self.opportunity_schema_status,
            "pm_schema_status": self.pm_schema_status,
            "readiness_artifact_path": self.readiness_artifact_path,
            "schemas": {
                "candidate": self.candidate.to_payload(),
                "opportunity": self.opportunity.to_payload(),
                "pm": self.pm.to_payload(),
            },
        }


def validate_feature_consumer_readiness(
    *,
    operations_root: Path | str,
    feature_date: str,
) -> FeatureConsumerReadiness:
    root = Path(operations_root)
    feature_dir = root / "feature_artifacts" / feature_date
    candidate = _validate_required_columns(
        name="candidate",
        schema_name=CANONICAL_FEATURE_SCHEMAS["candidate"].schema_name,
        artifact_path=feature_dir / "candidate_features.parquet",
        required_columns=CANONICAL_FEATURE_SCHEMAS["candidate"].required_columns,
        forbid_prefixed_columns=False,
    )
    opportunity = _validate_required_columns(
        name="opportunity",
        schema_name=CANONICAL_FEATURE_SCHEMAS["opportunity"].schema_name,
        artifact_path=feature_dir / "opportunity_feature_input.parquet",
        required_columns=CANONICAL_FEATURE_SCHEMAS["opportunity"].required_columns,
        forbid_prefixed_columns=True,
    )
    pm = _validate_pm_feature(
        artifact_path=feature_dir / "position_feature_input.parquet",
        runtime_root=root.parent,
    )
    results = (candidate, opportunity, pm)
    failed = tuple(result.name for result in results if result.status != "READY")
    if failed:
        status = "REVIEW_REQUIRED"
        reason = "consumer_schema_review_required:" + ",".join(failed)
    else:
        status = "READY"
        reason = "consumer_feature_schema_ready"
    return FeatureConsumerReadiness(
        status=status,
        reason=reason,
        consumer_ready=status == "READY",
        schema_version=CANONICAL_SCHEMA_VERSION,
        candidate=candidate,
        opportunity=opportunity,
        pm=pm,
    )


def write_feature_consumer_readiness(
    *,
    operations_root: Path | str,
    feature_date: str,
    readiness: FeatureConsumerReadiness,
) -> Path:
    path = Path(operations_root) / "feature_consumer_readiness" / f"{feature_date}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = readiness.to_payload()
    payload["readiness_artifact_path"] = str(path)
    path.write_text(json.dumps(payload, ensure_ascii=False, sort_keys=True), encoding="utf-8")
    return path


def _validate_required_columns(
    *,
    name: str,
    schema_name: str,
    artifact_path: Path,
    required_columns: tuple[str, ...],
    forbid_prefixed_columns: bool,
) -> ConsumerSchemaResult:
    if not artifact_path.is_file():
        return ConsumerSchemaResult(
            name=name,
            schema_name=schema_name,
            schema_version=CANONICAL_SCHEMA_VERSION,
            status="REVIEW_REQUIRED",
            artifact_path=str(artifact_path),
            required_columns=required_columns,
            missing_columns=required_columns,
            reason="feature_artifact_missing",
        )
    frame = pd.read_parquet(artifact_path)
    columns = tuple(str(column) for column in frame.columns)
    missing = tuple(column for column in required_columns if column not in columns)
    alias_mismatches = {
        alias: canonical
        for alias, canonical in CANONICAL_ALIAS_POLICY.items()
        if alias in columns and canonical not in columns
    }
    unexpected_prefixed = tuple(column for column in columns if column.startswith("feature__"))
    if forbid_prefixed_columns and unexpected_prefixed:
        reason = "feature_prefix_policy_violation"
        status = "REVIEW_REQUIRED"
    elif missing:
        reason = "required_feature_columns_missing"
        status = "REVIEW_REQUIRED"
    elif alias_mismatches:
        reason = "feature_column_alias_mismatch"
        status = "REVIEW_REQUIRED"
    else:
        reason = "consumer_schema_ready"
        status = "READY"
    return ConsumerSchemaResult(
        name=name,
        schema_name=schema_name,
        schema_version=CANONICAL_SCHEMA_VERSION,
        status=status,
        artifact_path=str(artifact_path),
        required_columns=required_columns,
        missing_columns=missing,
        unexpected_prefixed_columns=unexpected_prefixed if forbid_prefixed_columns else (),
        alias_mismatches=alias_mismatches,
        row_count=len(frame),
        reason=reason,
    )


def _validate_pm_feature(*, artifact_path: Path, runtime_root: Path) -> ConsumerSchemaResult:
    if not artifact_path.is_file():
        return ConsumerSchemaResult(
            name="pm",
            schema_name="runtime_v2_pm_feature_input",
            schema_version=CANONICAL_SCHEMA_VERSION,
            status="REVIEW_REQUIRED",
            artifact_path=str(artifact_path),
            required_columns=PM_REQUIRED_COLUMNS,
            missing_columns=PM_REQUIRED_COLUMNS,
            reason="feature_artifact_missing",
        )
    frame = pd.read_parquet(artifact_path)
    columns = tuple(str(column) for column in frame.columns)
    missing = tuple(column for column in PM_REQUIRED_COLUMNS if column not in columns)
    current_position_count = _current_position_count(runtime_root)
    has_no_position_reason = "no_position_reason" in columns
    if missing:
        status = "REVIEW_REQUIRED"
        reason = "required_pm_feature_columns_missing"
    elif current_position_count > 0 and len(frame) == 0:
        status = "REVIEW_REQUIRED"
        reason = "pm_feature_empty_with_current_positions"
    elif current_position_count == 0 and len(frame) == 0 and not has_no_position_reason:
        status = "REVIEW_REQUIRED"
        reason = "pm_feature_empty_without_no_position_reason"
    else:
        status = "READY"
        reason = "consumer_schema_ready"
    return ConsumerSchemaResult(
        name="pm",
        schema_name="runtime_v2_pm_feature_input",
        schema_version=CANONICAL_SCHEMA_VERSION,
        status=status,
        artifact_path=str(artifact_path),
        required_columns=PM_REQUIRED_COLUMNS,
        missing_columns=missing,
        row_count=len(frame),
        reason=reason,
    )


def _current_position_count(runtime_root: Path) -> int:
    current_path = runtime_root / "persistent_ledger" / "state.json"
    if not current_path.is_file():
        return 0
    try:
        payload = json.loads(current_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return 0
    positions = payload.get("positions")
    return len(positions) if isinstance(positions, list) else 0
