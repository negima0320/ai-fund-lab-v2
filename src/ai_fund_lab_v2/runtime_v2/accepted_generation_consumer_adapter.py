from __future__ import annotations

import hashlib
import json
import pickle
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


BUY_ONLY_BLOCK_REASONS = {
    "manifest_schema_mismatch",
    "aggregate_hash_mismatch",
    "member_hash_mismatch",
    "missing_scaler",
    "missing_calibration",
    "feature_order_mismatch",
    "candidate_dependency_mismatch",
    "model_load_failure",
    "scaler_load_failure",
    "calibration_load_failure",
    "prediction_non_finite",
}


@dataclass(frozen=True)
class LoadedGenerationMember:
    component: str
    model_ref: str
    model_file: str
    model_hash: str
    scaler_ref: str
    scaler_file: str
    scaler_hash: str
    calibration_ref: str
    calibration_hash: str
    feature_order_hash: str
    feature_order: tuple[str, ...]
    prediction_schema: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["feature_order"] = list(self.feature_order)
        return payload


@dataclass(frozen=True)
class AcceptedGenerationConsumerCompatibility:
    status: str
    reason_codes: tuple[str, ...]
    block_buy: bool
    block_sell: bool
    candidate: LoadedGenerationMember | None
    opportunity: LoadedGenerationMember | None
    manifest_hash: str
    aggregate_hash: str
    runtime_baseline_hash: str
    freshness_metadata_hash: str
    legacy_fallback_used: bool
    manual_path_used: bool

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["reason_codes"] = list(self.reason_codes)
        payload["candidate"] = self.candidate.to_dict() if self.candidate else None
        payload["opportunity"] = self.opportunity.to_dict() if self.opportunity else None
        return payload


def validate_manifest_compatibility(
    manifest: dict[str, Any],
    *,
    repo_root: Path | str,
    load_pickles: bool = True,
) -> AcceptedGenerationConsumerCompatibility:
    root = Path(repo_root)
    reasons: list[str] = []
    is_preview = manifest.get("accepted") is False and manifest.get("runtime_eligibility") is False
    is_accepted = (
        manifest.get("accepted") is True
        and manifest.get("runtime_eligibility") is True
        and manifest.get("generation_status") == "ACCEPTED"
        and manifest.get("runtime_eligibility_status") == "RUNTIME_ELIGIBLE_ACCEPTED_ONLY"
    )
    if not (is_preview or is_accepted):
        reasons.append("manifest_schema_mismatch")
    expected_hash = manifest.get("aggregate_hash_preview") or manifest.get("aggregate_hash") or manifest.get("manifest_hash")
    actual_hash = _expected_content_hash(manifest)
    if expected_hash and expected_hash != actual_hash:
        reasons.append("aggregate_hash_mismatch")
    candidate = _load_member(manifest.get("candidate_member"), "candidate", root, reasons, load_pickles=load_pickles)
    opportunity = _load_member(manifest.get("opportunity_member"), "opportunity", root, reasons, load_pickles=load_pickles)
    if opportunity and opportunity.component == "opportunity":
        dependency = (manifest.get("opportunity_member") or {}).get("candidate_dependency_ref")
        if dependency != "CandidateTop50":
            reasons.append("candidate_dependency_mismatch")
    return AcceptedGenerationConsumerCompatibility(
        status="PASS" if not reasons else "BUY_ONLY_BLOCK",
        reason_codes=tuple(dict.fromkeys(reasons)),
        block_buy=bool(reasons),
        block_sell=False,
        candidate=candidate,
        opportunity=opportunity,
        manifest_hash=actual_hash,
        aggregate_hash=str(expected_hash or ""),
        runtime_baseline_hash=str((manifest.get("runtime_baseline_ref") or {}).get("content_hash") or ""),
        freshness_metadata_hash=str((manifest.get("freshness_metadata") or {}).get("content_hash") or ""),
        legacy_fallback_used=False,
        manual_path_used=False,
    )


def enforce_feature_order(columns: list[str] | tuple[str, ...], expected_order: list[str] | tuple[str, ...]) -> dict[str, Any]:
    observed = list(columns)
    expected = list(expected_order)
    missing = [col for col in expected if col not in observed]
    unexpected = [col for col in observed if col not in expected]
    order_match = observed == expected
    return {
        "status": "PASS" if not missing and not unexpected and order_match else "BUY_ONLY_BLOCK",
        "missing_columns": missing,
        "unexpected_columns": unexpected,
        "order_match": order_match,
        "failure_behavior": "BUY_ONLY_BLOCK" if missing or unexpected or not order_match else "",
    }


def _load_member(
    payload: Any,
    component: str,
    root: Path,
    reasons: list[str],
    *,
    load_pickles: bool,
) -> LoadedGenerationMember | None:
    if not isinstance(payload, dict):
        reasons.append(f"{component}_member_missing")
        return None
    for key, reason in (("scaler_file", "missing_scaler"), ("calibration_ref", "missing_calibration")):
        if not payload.get(key):
            reasons.append(reason)
    model_file = root / str(payload.get("model_file") or "")
    scaler_file = root / str(payload.get("scaler_file") or "")
    model_hash = str(payload.get("model_hash") or "")
    scaler_hash = str(payload.get("scaler_hash") or "")
    if not _file_matches(model_file, model_hash):
        reasons.append("member_hash_mismatch" if model_file.exists() else "model_load_failure")
    if not _file_matches(scaler_file, scaler_hash):
        reasons.append("member_hash_mismatch" if scaler_file.exists() else "scaler_load_failure")
    calibration_ref = root / str(payload.get("calibration_ref") or "")
    if not calibration_ref.is_file():
        reasons.append("calibration_load_failure")
    elif not _json_artifact_hash_matches(calibration_ref, str(payload.get("calibration_hash") or "")):
        reasons.append("member_hash_mismatch")
    if load_pickles:
        _try_pickle_load(model_file, "model_load_failure", reasons)
        _try_pickle_load(scaler_file, "scaler_load_failure", reasons)
    feature_order = tuple(str(item) for item in payload.get("feature_order") or ())
    if not feature_order:
        reasons.append("feature_order_mismatch")
    expected_hash = str(payload.get("feature_order_hash") or "")
    if expected_hash and _stable_hash(list(feature_order)) != expected_hash:
        # Older artifacts use schema-hash-as-feature-order-hash; allow exact
        # artifact-bound hash equality when the hash is present in source refs.
        source_hash = str(payload.get("feature_schema_hash") or "")
        if source_hash != expected_hash:
            reasons.append("feature_order_mismatch")
    return LoadedGenerationMember(
        component=component,
        model_ref=str(payload.get("model_ref") or ""),
        model_file=str(model_file),
        model_hash=model_hash,
        scaler_ref=str(payload.get("scaler_ref") or ""),
        scaler_file=str(scaler_file),
        scaler_hash=scaler_hash,
        calibration_ref=str(payload.get("calibration_ref") or ""),
        calibration_hash=str(payload.get("calibration_hash") or ""),
        feature_order_hash=expected_hash,
        feature_order=feature_order,
        prediction_schema=dict(payload.get("prediction_schema") or {}),
    )


def _try_pickle_load(path: Path, reason: str, reasons: list[str]) -> None:
    try:
        with path.open("rb") as fh:
            pickle.load(fh)
    except Exception:
        reasons.append(reason)


def _file_matches(path: Path, expected_hash: str) -> bool:
    return path.is_file() and (not expected_hash or _file_hash(path) == expected_hash)


def _json_artifact_hash_matches(path: Path, expected_hash: str) -> bool:
    if not expected_hash:
        return True
    raw_hash = _file_hash(path)
    if raw_hash == expected_hash:
        return True
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return False
    if not isinstance(payload, dict):
        return False
    hash_inventory = payload.get("hash_inventory")
    candidates = [payload.get("content_hash")]
    if isinstance(hash_inventory, dict):
        for key in ("artifact_file_sha256", "manifest_sha256", "content_sha256"):
            value = hash_inventory.get(key)
            if isinstance(value, dict):
                candidates.append(value.get("sha256"))
            elif isinstance(value, str):
                candidates.append(value)
    return expected_hash in {str(candidate) for candidate in candidates if candidate}


def _file_hash(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _content_hash(payload: dict[str, Any], hash_field: str) -> str:
    return _stable_hash({key: value for key, value in payload.items() if key != hash_field})


def _expected_content_hash(payload: dict[str, Any]) -> str:
    if "aggregate_hash_preview" in payload:
        return _content_hash(payload, "aggregate_hash_preview")
    if "aggregate_hash" in payload:
        return _stable_hash({key: value for key, value in payload.items() if key not in {"aggregate_hash", "manifest_hash"}})
    return _content_hash(payload, "manifest_hash")


def _stable_hash(payload: Any) -> str:
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True, default=str).encode("utf-8")
    ).hexdigest()
