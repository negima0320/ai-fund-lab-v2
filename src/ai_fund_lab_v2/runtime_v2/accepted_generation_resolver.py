from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


COMMITTED_TRANSACTION_STATE = "COMMITTED"
RUNTIME_ACCEPTED_POINTER = Path("runtime_state") / "accepted_buy_ai_bundle.json"


@dataclass(frozen=True)
class AcceptedGenerationMember:
    role: str
    artifact_path: str
    model_hash: str = ""
    schema_hash: str = ""
    source_generation_id: str = ""
    component_revision: str = ""
    reused: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class AcceptedGenerationResolution:
    resolution_status: str
    generation_id: str
    bundle_manifest_path: str
    authority_decision: str
    transaction_state: str
    effective_from: str
    accepted_at: str
    aggregate_hash: str
    candidate_member: AcceptedGenerationMember | None
    opportunity_member: AcceptedGenerationMember | None
    calibration_member: AcceptedGenerationMember | None
    runtime_baseline: dict[str, Any]
    freshness_metadata: dict[str, Any]
    rollback_reference: dict[str, Any]
    source_evidence: dict[str, Any]
    block_reason: str
    review_required: bool
    reason_codes: tuple[str, ...]

    @property
    def is_resolved(self) -> bool:
        return self.resolution_status == "RESOLVED_COMMITTED"

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["candidate_member"] = self.candidate_member.to_dict() if self.candidate_member else None
        payload["opportunity_member"] = self.opportunity_member.to_dict() if self.opportunity_member else None
        payload["calibration_member"] = self.calibration_member.to_dict() if self.calibration_member else None
        payload["reason_codes"] = list(self.reason_codes)
        return payload

    def artifact_paths(self) -> dict[str, Path]:
        paths: dict[str, Path] = {}
        if self.candidate_member and self.candidate_member.artifact_path:
            paths["candidate_model"] = Path(self.candidate_member.artifact_path)
            paths["candidate_model_manifest"] = Path("")
            paths["candidate_feature_schema"] = Path("")
        if self.opportunity_member and self.opportunity_member.artifact_path:
            paths["opportunity_model"] = Path(self.opportunity_member.artifact_path)
            metrics = _nested(self.source_evidence, "opportunity_metrics_path")
            paths["opportunity_metrics"] = Path(str(metrics)) if metrics else Path("")
            paths["opportunity_feature_schema"] = Path("")
        return paths


def resolve_accepted_generation(runtime_root: Path | str) -> AcceptedGenerationResolution:
    root = Path(runtime_root)
    pointer_path = root / RUNTIME_ACCEPTED_POINTER
    source = {
        "runtime_root": str(root),
        "pointer_path": str(pointer_path),
        "authority_contract": "current COMMITTED Runtime accepted generation pointer only",
        "legacy_component_fallback_used": False,
        "promotion_candidate_fallback_used": False,
        "manual_model_path_used": False,
    }
    if not pointer_path.exists():
        return _unresolved(
            "NO_ACCEPTED_GENERATION",
            "NO_ACCEPTED_GENERATION_BOOTSTRAP",
            source,
            ("accepted_generation_pointer_missing", "NO_ACCEPTED_GENERATION_BOOTSTRAP"),
        )
    try:
        pointer = _read_json_strict(pointer_path)
    except Exception:
        return _unresolved(
            "INVALID_MANIFEST",
            "accepted_generation_pointer_unreadable",
            source,
            ("accepted_generation_pointer_unreadable",),
            pointer_path=pointer_path,
        )
    transaction_state = str(pointer.get("transaction_state") or "")
    if transaction_state != COMMITTED_TRANSACTION_STATE:
        reason = "accepted_generation_pointer_not_committed" if transaction_state else "accepted_generation_pointer_transaction_state_missing"
        return _unresolved(
            "REVIEW_REQUIRED",
            reason,
            {**source, "transaction_state": transaction_state},
            (reason,),
            pointer_path=pointer_path,
        )
    ref = pointer.get("bundle_manifest_path") or pointer.get("accepted_bundle_path") or pointer.get("accepted_bundle_ref")
    if not ref:
        return _unresolved(
            "INVALID_MANIFEST",
            "accepted_generation_manifest_ref_missing",
            {**source, "transaction_state": transaction_state},
            ("accepted_generation_manifest_ref_missing",),
            pointer_path=pointer_path,
        )
    manifest_path = Path(str(ref))
    if not manifest_path.is_absolute():
        manifest_path = root.parent / manifest_path if str(ref).startswith(".runtime/") else root / manifest_path
    if "promotion_candidates" in manifest_path.parts:
        return _unresolved(
            "INVALID_MANIFEST",
            "promotion_candidate_forbidden_for_runtime",
            {**source, "transaction_state": transaction_state, "bundle_manifest_path": str(manifest_path)},
            ("promotion_candidate_forbidden_for_runtime",),
            pointer_path=pointer_path,
        )
    if not manifest_path.is_file():
        return _unresolved(
            "INVALID_MANIFEST",
            "accepted_generation_manifest_missing",
            {**source, "transaction_state": transaction_state, "bundle_manifest_path": str(manifest_path)},
            ("accepted_generation_manifest_missing",),
            pointer_path=pointer_path,
        )
    try:
        manifest = _read_json_strict(manifest_path)
    except Exception:
        return _unresolved(
            "INVALID_MANIFEST",
            "accepted_generation_manifest_unreadable",
            {**source, "transaction_state": transaction_state, "bundle_manifest_path": str(manifest_path)},
            ("accepted_generation_manifest_unreadable",),
            pointer_path=pointer_path,
        )
    aggregate_hash = _aggregate_hash(manifest)
    if not aggregate_hash:
        return _unresolved(
            "INVALID_MANIFEST",
            "accepted_generation_aggregate_hash_missing",
            {**source, "transaction_state": transaction_state, "bundle_manifest_path": str(manifest_path)},
            ("accepted_generation_aggregate_hash_missing",),
            pointer_path=pointer_path,
        )
    if not _aggregate_hash_matches(manifest, aggregate_hash):
        return _unresolved(
            "HASH_MISMATCH",
            "accepted_generation_aggregate_hash_mismatch",
            {**source, "transaction_state": transaction_state, "bundle_manifest_path": str(manifest_path)},
            ("accepted_generation_aggregate_hash_mismatch",),
            pointer_path=pointer_path,
        )
    pointer_hash = str(pointer.get("aggregate_hash") or pointer.get("accepted_generation_hash") or "").replace("sha256:", "")
    if pointer_hash and pointer_hash != aggregate_hash:
        return _unresolved(
            "HASH_MISMATCH",
            "accepted_generation_pointer_hash_mismatch",
            {**source, "transaction_state": transaction_state, "bundle_manifest_path": str(manifest_path)},
            ("accepted_generation_pointer_hash_mismatch",),
            pointer_path=pointer_path,
        )
    candidate = _member(manifest, manifest_path.parent, "candidate_model", "candidate_member", "candidate")
    opportunity = _member(manifest, manifest_path.parent, "opportunity_model", "opportunity_member", "opportunity")
    missing_members = []
    if candidate is None:
        missing_members.append("candidate_member_missing")
    if opportunity is None:
        missing_members.append("opportunity_member_missing")
    if missing_members:
        return _unresolved(
            "INCOMPATIBLE_GENERATION",
            ",".join(missing_members),
            {**source, "transaction_state": transaction_state, "bundle_manifest_path": str(manifest_path)},
            tuple(missing_members),
            pointer_path=pointer_path,
        )
    member_reasons = _member_integrity_reasons(candidate, opportunity)
    if member_reasons:
        return _unresolved(
            "HASH_MISMATCH" if any("hash_mismatch" in reason for reason in member_reasons) else "INVALID_MANIFEST",
            ",".join(member_reasons),
            {**source, "transaction_state": transaction_state, "bundle_manifest_path": str(manifest_path)},
            tuple(member_reasons),
            pointer_path=pointer_path,
        )
    source_evidence = {
        **source,
        "pointer_path": str(pointer_path),
        "bundle_manifest_path": str(manifest_path),
        "pointer_hash": _stable_hash(pointer),
        "manifest_content_hash": _file_hash(manifest_path),
        "opportunity_metrics_path": _relative_member_path(
            manifest,
            manifest_path.parent,
            "opportunity_metrics",
            "metrics",
            "opportunity_metrics_ref",
        )
        or _accepted_opportunity_metrics_path(manifest),
    }
    return AcceptedGenerationResolution(
        resolution_status="RESOLVED_COMMITTED",
        generation_id=str(manifest.get("generation_id") or manifest.get("buy_ai_bundle_id") or manifest.get("artifact_set_id") or ""),
        bundle_manifest_path=str(manifest_path),
        authority_decision=str(manifest.get("authority_decision") or manifest.get("authority_decision_ref") or pointer.get("authority_decision") or ""),
        transaction_state=transaction_state,
        effective_from=str(manifest.get("effective_from") or pointer.get("effective_from") or ""),
        accepted_at=str(manifest.get("accepted_at") or pointer.get("accepted_at") or ""),
        aggregate_hash=aggregate_hash,
        candidate_member=candidate,
        opportunity_member=opportunity,
        calibration_member=_member(manifest, manifest_path.parent, "calibration", "calibration_member", "calibration_ref"),
        runtime_baseline=_runtime_baseline(manifest),
        freshness_metadata=_freshness_metadata(manifest),
        rollback_reference=_dict_field(manifest, "rollback_reference", "previous_generation_ref"),
        source_evidence=source_evidence,
        block_reason="",
        review_required=False,
        reason_codes=(),
    )


def _unresolved(
    status: str,
    reason: str,
    source_evidence: dict[str, Any],
    reason_codes: tuple[str, ...],
    *,
    pointer_path: Path | None = None,
) -> AcceptedGenerationResolution:
    return AcceptedGenerationResolution(
        resolution_status=status,
        generation_id="",
        bundle_manifest_path="",
        authority_decision="",
        transaction_state="",
        effective_from="",
        accepted_at="",
        aggregate_hash="",
        candidate_member=None,
        opportunity_member=None,
        calibration_member=None,
        runtime_baseline={},
        freshness_metadata={},
        rollback_reference={},
        source_evidence={**source_evidence, "accepted_state_ref": str(pointer_path or source_evidence.get("pointer_path") or "")},
        block_reason=reason,
        review_required=True,
        reason_codes=reason_codes,
    )


def _member(manifest: dict[str, Any], base_dir: Path, *keys: str) -> AcceptedGenerationMember | None:
    payload = _member_payload(manifest, *keys)
    if payload is None:
        return None
    path = _path_value(payload)
    if not path:
        return None
    artifact_path = _resolve_artifact_path(Path(path), base_dir)
    return AcceptedGenerationMember(
        role=str(payload.get("role") or payload.get("member_role") or keys[0]),
        artifact_path=str(artifact_path),
        model_hash=str(payload.get("model_hash") or payload.get("content_hash") or payload.get("artifact_hash") or ""),
        schema_hash=str(payload.get("schema_hash") or ""),
        source_generation_id=str(payload.get("source_generation_id") or ""),
        component_revision=str(payload.get("component_revision") or ""),
        reused=bool(payload.get("reused") or payload.get("reused_flag")),
    )


def _member_payload(manifest: dict[str, Any], *keys: str) -> dict[str, Any] | None:
    for key in keys:
        value = manifest.get(key)
        if isinstance(value, dict):
            return value
        if isinstance(value, str):
            return {"artifact_path": value, "role": key}
    members = manifest.get("members")
    if isinstance(members, dict):
        for key in keys:
            value = members.get(key)
            if isinstance(value, dict):
                return value
            if isinstance(value, str):
                return {"artifact_path": value, "role": key}
    if isinstance(members, list):
        lowered = {key.lower() for key in keys}
        for item in members:
            if not isinstance(item, dict):
                continue
            role = str(item.get("role") or item.get("member_role") or item.get("name") or "").lower()
            if role in lowered:
                return item
    return None


def _member_integrity_reasons(*members: AcceptedGenerationMember | None) -> list[str]:
    reasons: list[str] = []
    for member in members:
        if member is None:
            continue
        path = Path(member.artifact_path)
        if not path.is_file():
            reasons.append(f"{member.role}_artifact_missing")
            continue
        expected = member.model_hash.replace("sha256:", "")
        if expected and _file_hash(path) != expected:
            reasons.append(f"{member.role}_hash_mismatch")
    return reasons


def _member_path(manifest: dict[str, Any], *keys: str) -> str:
    payload = _member_payload(manifest, *keys)
    return _path_value(payload or {})


def _relative_member_path(manifest: dict[str, Any], base_dir: Path, *keys: str) -> str:
    value = _member_path(manifest, *keys)
    if not value:
        return ""
    path = Path(value)
    return str(_resolve_artifact_path(path, base_dir))


def _accepted_opportunity_metrics_path(manifest: dict[str, Any]) -> str:
    """Resolve accepted Opportunity metrics authority without latest/manual fallback."""

    dual_gate_hash = _nested(manifest, "dual_gate_ref", "hashes", "dual_gate_artifact_file_sha256") or _nested(
        manifest,
        "dual_gate_ref",
        "hashes",
        "manifest_sha256",
    )
    candidates = (
        Path("reports/phase19_aj_formal_corrective_reevaluation/opportunity_dual_gate_artifact.json"),
        Path("reports/phase19_ah_dual_gate_implementation_and_runtime_separation/dual_gate_fixture_artifact.json"),
    )
    for path in candidates:
        if not path.is_file():
            continue
        if dual_gate_hash:
            payload = _read_json_strict(path)
            inventory = payload.get("hash_inventory") if isinstance(payload.get("hash_inventory"), dict) else {}
            observed = _nested(inventory, "dual_gate_artifact_file_sha256", "sha256") or _nested(
                inventory,
                "manifest_sha256",
                "sha256",
            )
            if observed and str(observed) != str(dual_gate_hash):
                continue
        return str(path)
    return ""


def _resolve_artifact_path(path: Path, base_dir: Path) -> Path:
    if path.is_absolute():
        return path
    if path.parts and path.parts[0] in {".runtime", "reports", "docs", "schemas"}:
        repo_root = _repo_root_from_manifest_base(base_dir)
        return repo_root / path
    return base_dir / path


def _repo_root_from_manifest_base(base_dir: Path) -> Path:
    for parent in (base_dir, *base_dir.parents):
        if parent.name == ".runtime":
            return parent.parent
    return base_dir


def _path_value(payload: dict[str, Any]) -> str:
    for key in ("artifact_path", "physical_path", "model_file", "model_path", "artifact_file", "path", "ref"):
        value = payload.get(key)
        if value:
            return str(value)
    return ""


def _runtime_baseline(manifest: dict[str, Any]) -> dict[str, Any]:
    value = manifest.get("runtime_baseline") or manifest.get("materialized_drift_baseline")
    if isinstance(value, dict):
        return value
    ref = manifest.get("runtime_baseline_ref")
    if isinstance(ref, dict):
        return ref
    return {"runtime_baseline_ref": str(ref or "")}


def _freshness_metadata(manifest: dict[str, Any]) -> dict[str, Any]:
    value = manifest.get("freshness_metadata") or manifest.get("freshness")
    return value if isinstance(value, dict) else {"freshness_metadata_ref": str(manifest.get("freshness_metadata_ref") or "")}


def _dict_field(manifest: dict[str, Any], *keys: str) -> dict[str, Any]:
    for key in keys:
        value = manifest.get(key)
        if isinstance(value, dict):
            return value
        if value:
            return {key: value}
    return {}


def _aggregate_hash(manifest: dict[str, Any]) -> str:
    return str(manifest.get("aggregate_hash") or manifest.get("joint_bundle_hash") or manifest.get("bundle_hash") or "").replace("sha256:", "")


def _aggregate_hash_matches(manifest: dict[str, Any], expected: str) -> bool:
    if manifest.get("aggregate_hash"):
        canonical = _stable_hash({key: value for key, value in manifest.items() if key != "aggregate_hash"})
        if canonical == expected:
            return True
        aq_canonical = _stable_hash({key: value for key, value in manifest.items() if key not in {"aggregate_hash", "manifest_hash"}})
        return aq_canonical == expected
    if manifest.get("joint_bundle_hash"):
        return _stable_hash({key: value for key, value in manifest.items() if key != "joint_bundle_hash"}) == expected
    if manifest.get("bundle_hash"):
        return _stable_hash({key: value for key, value in manifest.items() if key != "bundle_hash"}) == expected
    return False


def _nested(payload: dict[str, Any], *keys: str) -> Any:
    current: Any = payload
    for key in keys:
        if not isinstance(current, dict):
            return None
        current = current.get(key)
    return current


def _read_json_strict(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("JSON payload must be an object")
    return payload


def _file_hash(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _stable_hash(payload: Any) -> str:
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True, default=str).encode("utf-8")
    ).hexdigest()
