"""Consumer-specific feature schema readiness checks for Runtime v2."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import pandas as pd

from ai_fund_lab_v2.runtime_v2.current_position_authority import resolve_current_position_authority


CANONICAL_SCHEMA_VERSION = "runtime_v2_feature_contract_v2"

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

OPPORTUNITY_MODEL_DECISION_COLUMNS: tuple[str, ...] = (
    "feature__candidate_rank",
    "feature__candidate_reason",
    "feature__candidate_score",
)

OPPORTUNITY_REQUIRED_COLUMNS: tuple[str, ...] = (
    "target_date",
    "code",
    "liquidity_avg_volume_20d",
    "market_breadth_20d",
    "market_breadth_5d",
    "market_downtrend_context",
    "market_downtrend_flag",
    "market_ma_5_20_ratio",
    "market_return_20d",
    "market_return_5d",
    "market_risk_flag",
    "market_volatility_20d",
    "missing_flags_insufficient_history",
    "missing_flags_price",
    "missing_flags_volume",
    "price_momentum_return_20d",
    "price_momentum_return_5d",
    "price_momentum_return_60d",
    "sector_breadth_20d",
    "sector_momentum_flag",
    "sector_rank_20d",
    "sector_return_20d",
    "sector_return_5d",
    "sector_weak_flag",
    "stock_vs_sector_return_20d",
    "trend_close_over_ma_20d",
    "trend_ma_20_60_ratio",
    "trend_ma_5_20_ratio",
    "volatility_return_std_20d",
    "volume_momentum_ratio_1d_20d",
    "volume_momentum_ratio_5d",
)

PM_REQUIRED_COLUMNS: tuple[str, ...] = (
    "target_date",
    "feature_as_of_date",
    "position_state_as_of",
    "entry_date",
    "code",
    "broker_issue_code",
    "holding_days",
    "average_price",
    "current_price",
    "unrealized_return",
    "quantity",
    "price_momentum_return_5d",
    "price_momentum_return_20d",
    "trend_close_over_ma_20d",
    "trend_ma_5_20_ratio",
    "volume_momentum_ratio_5d",
    "volatility_return_std_20d",
    "feature_source_artifact",
    "feature_source_hash",
    "required_features",
    "optional_features",
    "missing_features",
    "defaulted_features",
    "temporal_validation_status",
    "feature_version",
    "data_until",
    "created_at",
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
            or column
            in {
                "market_downtrend_context",
                "market_downtrend_flag",
                "market_risk_flag",
                "sector_momentum_flag",
                "sector_weak_flag",
            }
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
    evidence: dict[str, Any] | None = None

    def to_payload(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["required_columns"] = list(self.required_columns)
        payload["missing_columns"] = list(self.missing_columns)
        payload["unexpected_prefixed_columns"] = list(self.unexpected_prefixed_columns)
        payload["alias_mismatches"] = dict(self.alias_mismatches or {})
        payload["evidence"] = dict(self.evidence or {})
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
    feature_target_date = _feature_target_date(frame) or artifact_path.parent.name
    current_authority = _current_authority(runtime_root, target_data_until=feature_target_date)
    current_position_count = int(current_authority.get("current_position_count") or 0)
    has_no_position_reason = "no_position_reason" in columns
    required_columns = PM_REQUIRED_COLUMNS if current_position_count > 0 else ("target_date", "code")
    missing = tuple(column for column in required_columns if column not in columns)
    authority_status = str(current_authority.get("current_authority_status") or "")
    if authority_status not in {"READY", "READY_EMPTY"}:
        status = "REVIEW_REQUIRED"
        reason = str(current_authority.get("reason") or "current_authority_not_ready")
    elif current_position_count > 0 and len(frame) == 0:
        status = "REVIEW_REQUIRED"
        reason = "position_feature_current_output_mismatch"
    elif current_position_count > 0 and missing:
        status = "REVIEW_REQUIRED"
        reason = "required_pm_feature_columns_missing"
    elif current_position_count == 0 and len(frame) == 0 and not has_no_position_reason:
        status = "REVIEW_REQUIRED"
        reason = "pm_feature_empty_without_no_position_reason"
    elif missing:
        status = "REVIEW_REQUIRED"
        reason = "required_pm_feature_columns_missing"
    else:
        status = "READY"
        reason = "consumer_schema_ready_empty_position" if authority_status == "READY_EMPTY" and current_position_count == 0 else "consumer_schema_ready"
    position_state_as_of = str(current_authority.get("current_position_state_as_of") or "")
    no_fill_carry_used = bool(position_state_as_of and feature_target_date and position_state_as_of < feature_target_date)
    return ConsumerSchemaResult(
        name="pm",
        schema_name="runtime_v2_pm_feature_input",
        schema_version=CANONICAL_SCHEMA_VERSION,
        status=status,
        artifact_path=str(artifact_path),
        required_columns=required_columns,
        missing_columns=missing,
        row_count=len(frame),
        reason=reason,
        evidence={
            **current_authority,
            "feature_target_date": feature_target_date,
            "input_symbol_count": current_position_count,
            "matched_symbol_count": int(len(frame)),
            "unmatched_symbols": [],
            "output_row_count": int(len(frame)),
            "no_fill_carry_used": no_fill_carry_used,
            "position_feature_status": "READY_EMPTY" if authority_status == "READY_EMPTY" and int(len(frame)) == 0 else "FEATURES_READY",
            "position_feature_reason": "current_positions_confirmed_empty" if authority_status == "READY_EMPTY" and int(len(frame)) == 0 else "position_feature_ready",
            "pm_consumer_status": "NOT_REQUIRED" if authority_status == "READY_EMPTY" and current_position_count == 0 else status,
            "pm_inference_required": not (authority_status == "READY_EMPTY" and current_position_count == 0),
            "runtime_continuation_status": "PASS" if status == "READY" else "REVIEW_REQUIRED",
            "reason": reason,
        },
    )


def _current_authority(runtime_root: Path, *, target_data_until: str) -> dict[str, Any]:
    authority = resolve_current_position_authority(runtime_root=runtime_root, target_data_until=target_data_until)
    return {
        **authority,
        "reason": "current_authority_ready_empty" if authority["status"] == "READY_EMPTY" else authority["reason"],
    }


def _read_json_or_empty(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    return payload if isinstance(payload, dict) else {}


def _feature_target_date(frame: pd.DataFrame) -> str:
    if "target_date" not in frame.columns or frame.empty:
        return ""
    values = [str(value) for value in frame["target_date"].dropna().astype(str).tolist() if value]
    return max(values) if values else ""
