from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Mapping

from ai_fund_lab_v2.paper_trading.safe_train_until import resolve_safe_train_until


MODEL_ELIGIBLE = "MODEL_ELIGIBLE"
MANIFEST_METADATA_INCOMPLETE = "MANIFEST_METADATA_INCOMPLETE"
RETRAIN_REQUIRED = "RETRAIN_REQUIRED"
POLICY_MANIFEST_REQUIRED = "POLICY_MANIFEST_REQUIRED"
FEATURE_SCHEMA_MISMATCH = "FEATURE_SCHEMA_MISMATCH"
LEAKAGE_AUDIT_REQUIRED = "LEAKAGE_AUDIT_REQUIRED"
FORBIDDEN_SOURCE_DETECTED = "FORBIDDEN_SOURCE_DETECTED"
ARTIFACT_MISSING = "ARTIFACT_MISSING"
NOT_ELIGIBLE = "NOT_ELIGIBLE"

PROHIBITED_SOURCE_TERMS = (
    "backtest",
    "paper_ledger",
    "ledger",
    "pnl",
    "profit_factor",
    "win_rate",
    "drawdown",
    "orderplan",
    "order_plan",
    "human_review",
    "selected",
    "bought",
    "cash",
    "portfolio",
    "broker",
    "public_confidence",
    "blog",
    "report",
    "test",
)


@dataclass(frozen=True)
class ModelManifestReviewResult:
    ai_name: str
    status: str
    model_version: str = ""
    policy_version: str = ""
    manifest_path: str = ""
    artifact_path: str = ""
    train_until: str = ""
    data_until: str = ""
    safe_train_until: str = ""
    label_horizon: int | None = None
    feature_schema_hash: str = ""
    expected_feature_schema_hash: str = ""
    leakage_audit_status: str = ""
    forbidden_source_audit_status: str = ""
    retrain_required: bool = False
    retrain_recommended: bool = False
    train_until_required: bool = True
    blocked_reasons: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["blocked_reasons"] = list(self.blocked_reasons)
        payload["warnings"] = list(self.warnings)
        return payload


def review_model_manifest(
    *,
    ai_name: str,
    manifest: Mapping[str, Any] | None,
    manifest_path: Path | str | None,
    expected_feature_schema_hash: str,
    data_until: str,
    trading_calendar_path: Path | str | None = None,
) -> ModelManifestReviewResult:
    if not manifest:
        return ModelManifestReviewResult(
            ai_name=ai_name,
            status=POLICY_MANIFEST_REQUIRED if ai_name in {"candidate", "position", "capital"} else MANIFEST_METADATA_INCOMPLETE,
            manifest_path=str(manifest_path or ""),
            data_until=data_until,
            expected_feature_schema_hash=expected_feature_schema_hash,
            retrain_required=ai_name == "opportunity",
            blocked_reasons=("manifest_missing",),
        )
    blocked: list[str] = []
    warnings: list[str] = []
    model_version = _first_text(manifest, "model_version", "active_model_version")
    policy_version = _first_text(manifest, "policy_version", "policy_id", "model_version")
    is_policy = bool(manifest.get("policy_name") or manifest.get("train_until_required") is False or ai_name in {"position", "capital"})
    version = policy_version if is_policy else model_version
    if not version:
        blocked.append("missing_model_or_policy_version")
    artifact_path = _first_text(manifest, "artifact_path", "model_artifact_path", "policy_artifact_path")
    if artifact_path and not Path(artifact_path).exists():
        blocked.append("artifact_missing")
    if not artifact_path and not is_policy:
        blocked.append("artifact_missing")

    train_until_required = bool(manifest.get("train_until_required", not is_policy))
    train_until = _first_text(manifest, "train_until")
    manifest_data_until = _first_text(manifest, "data_until") or data_until
    label_horizon = _int_or_none(manifest.get("label_horizon") or manifest.get("label_horizon_business_days"))
    safe = resolve_safe_train_until(
        data_until=manifest_data_until,
        label_horizon_business_days=label_horizon,
        trading_calendar_path=trading_calendar_path,
        train_until_required=train_until_required,
    )
    blocked.extend(safe.blocked_reasons)
    warnings.extend(safe.warnings)
    if train_until_required:
        if not train_until:
            blocked.append("missing_train_until")
        if label_horizon is None:
            blocked.append("missing_label_horizon")
        if train_until and safe.safe_train_until and train_until > safe.safe_train_until:
            blocked.append("train_until_after_safe_train_until")
    feature_hash = _first_text(manifest, "feature_schema_hash")
    if not feature_hash:
        blocked.append("missing_feature_schema_hash")
    elif expected_feature_schema_hash and feature_hash != expected_feature_schema_hash:
        blocked.append("feature_schema_hash_mismatch")
    leakage = _first_text(manifest, "leakage_audit_status") or "UNKNOWN"
    forbidden = _first_text(manifest, "forbidden_source_audit_status") or _first_text(manifest, "forbidden_training_source_audit_status") or "UNKNOWN"
    if leakage.upper() != "OK":
        blocked.append("leakage_audit_not_ok")
    if forbidden.upper() != "OK":
        blocked.append("forbidden_source_audit_not_ok")
    source_refs = manifest.get("source_data_refs") or manifest.get("training_sources") or manifest.get("dataset_path") or {}
    if _has_forbidden_source(source_refs):
        blocked.append("forbidden_source_detected")
    if not _source_refs_are_jquants(source_refs):
        blocked.append("source_data_refs_not_jquants_only")

    status = _status_from_blockers(blocked, is_policy=is_policy)
    retrain_required = status in {RETRAIN_REQUIRED, FEATURE_SCHEMA_MISMATCH, LEAKAGE_AUDIT_REQUIRED, ARTIFACT_MISSING, MANIFEST_METADATA_INCOMPLETE}
    if is_policy and status == MODEL_ELIGIBLE:
        retrain_required = False
    return ModelManifestReviewResult(
        ai_name=ai_name,
        status=status,
        model_version=model_version if not is_policy else "",
        policy_version=policy_version if is_policy else "",
        manifest_path=str(manifest_path or ""),
        artifact_path=artifact_path,
        train_until=train_until,
        data_until=manifest_data_until,
        safe_train_until=safe.safe_train_until,
        label_horizon=label_horizon,
        feature_schema_hash=feature_hash,
        expected_feature_schema_hash=expected_feature_schema_hash,
        leakage_audit_status=leakage,
        forbidden_source_audit_status=forbidden,
        retrain_required=retrain_required,
        retrain_recommended=retrain_required,
        train_until_required=train_until_required,
        blocked_reasons=tuple(dict.fromkeys(blocked)),
        warnings=tuple(dict.fromkeys(warnings)),
    )


def load_manifest(path: Path | str | None) -> dict[str, Any] | None:
    if not path:
        return None
    candidate = Path(path)
    if not candidate.exists() or candidate.suffix.lower() != ".json":
        return None
    try:
        payload = json.loads(candidate.read_text(encoding="utf-8"))
        return payload if isinstance(payload, dict) else None
    except json.JSONDecodeError:
        return None


def _status_from_blockers(blocked: list[str], *, is_policy: bool) -> str:
    if not blocked:
        return MODEL_ELIGIBLE
    if "forbidden_source_detected" in blocked:
        return FORBIDDEN_SOURCE_DETECTED
    if "artifact_missing" in blocked:
        return ARTIFACT_MISSING
    if "feature_schema_hash_mismatch" in blocked:
        return FEATURE_SCHEMA_MISMATCH
    if any(reason.startswith("leakage") for reason in blocked):
        return LEAKAGE_AUDIT_REQUIRED
    if is_policy and "manifest_missing" in blocked:
        return POLICY_MANIFEST_REQUIRED
    if any("missing" in reason for reason in blocked):
        return MANIFEST_METADATA_INCOMPLETE
    if "train_until_after_safe_train_until" in blocked:
        return RETRAIN_REQUIRED
    return NOT_ELIGIBLE


def _first_text(manifest: Mapping[str, Any], *keys: str) -> str:
    for key in keys:
        value = manifest.get(key)
        if value not in (None, ""):
            return str(value)
    return ""


def _int_or_none(value: Any) -> int | None:
    if value in (None, ""):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _has_forbidden_source(value: Any) -> bool:
    text = json.dumps(value, ensure_ascii=True, sort_keys=True).lower()
    return any(term in text for term in PROHIBITED_SOURCE_TERMS)


def _source_refs_are_jquants(value: Any) -> bool:
    if not value:
        return False
    text = json.dumps(value, ensure_ascii=True, sort_keys=True).lower()
    allowed_markers = ("jquants", "phase9/canonical_data/normalized_daily_quotes", "phase9/features")
    return any(marker in text for marker in allowed_markers)
