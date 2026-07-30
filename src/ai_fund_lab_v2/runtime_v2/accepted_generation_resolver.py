from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


COMMITTED_TRANSACTION_STATE = "COMMITTED"
RUNTIME_ACCEPTED_POINTER = Path("runtime_state") / "accepted_buy_ai_bundle.json"
ACCEPTED_GENERATION_HISTORY = Path("ai_lifecycle") / "authority_history" / "accepted_generation_history.jsonl"
ACCEPTED_GENERATION_DIR = Path("ai_lifecycle") / "generations"


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


def resolve_accepted_generation(
    runtime_root: Path | str,
    business_date: str | None = None,
    fixed_authority_path: Path | str | None = None,
) -> AcceptedGenerationResolution:
    root = Path(runtime_root)
    if fixed_authority_path:
        return _resolve_fixed_historical_evaluation_authority(root, Path(fixed_authority_path))
    pointer_path = root / RUNTIME_ACCEPTED_POINTER
    source = {
        "runtime_root": str(root),
        "pointer_path": str(pointer_path),
        "authority_contract": "business-date-bound Accepted Generation ledger" if business_date else "current COMMITTED Runtime accepted generation pointer only",
        "legacy_component_fallback_used": False,
        "promotion_candidate_fallback_used": False,
        "manual_model_path_used": False,
    }
    if business_date:
        return _resolve_business_date_bound_generation(root, business_date=business_date, source=source, pointer_path=pointer_path)
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
    temporal_reasons = _temporal_authority_reasons(manifest, pointer, business_date=business_date)
    if temporal_reasons:
        return _unresolved(
            "REVIEW_REQUIRED",
            ",".join(temporal_reasons),
            {**source, "transaction_state": transaction_state, "bundle_manifest_path": str(manifest_path), "business_date": str(business_date or "")},
            tuple(temporal_reasons),
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
        "business_date": str(business_date or ""),
        "temporal_authority_status": "PASS" if business_date else "NOT_REQUESTED",
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


def _resolve_fixed_historical_evaluation_authority(
    root: Path,
    authority_path: Path,
) -> AcceptedGenerationResolution:
    source = {
        "runtime_root": str(root),
        "authority_contract": "run-start fixed Historical Evaluation Accepted Generation authority",
        "historical_evaluation_authority_path": str(authority_path),
        "legacy_component_fallback_used": False,
        "promotion_candidate_fallback_used": False,
        "manual_model_path_used": False,
        "latest_fallback_used": False,
        "business_date_temporal_comparison_applied": False,
    }
    if not authority_path.is_file():
        return _unresolved(
            "INVALID_MANIFEST",
            "historical_evaluation_authority_missing",
            source,
            ("historical_evaluation_authority_missing",),
        )
    try:
        authority = _read_json_strict(authority_path)
    except Exception:
        return _unresolved(
            "INVALID_MANIFEST",
            "historical_evaluation_authority_unreadable",
            source,
            ("historical_evaluation_authority_unreadable",),
        )
    manifest_ref = str(authority.get("bundle_manifest_path") or authority.get("manifest_path") or "")
    if not manifest_ref:
        return _unresolved(
            "INVALID_MANIFEST",
            "historical_evaluation_authority_manifest_ref_missing",
            source,
            ("historical_evaluation_authority_manifest_ref_missing",),
        )
    manifest_path = _resolve_manifest_path(Path(manifest_ref), root)
    if "promotion_candidates" in manifest_path.parts:
        return _unresolved(
            "INVALID_MANIFEST",
            "promotion_candidate_forbidden_for_runtime",
            {**source, "bundle_manifest_path": str(manifest_path)},
            ("promotion_candidate_forbidden_for_runtime",),
        )
    if not manifest_path.is_file():
        return _unresolved(
            "INVALID_MANIFEST",
            "accepted_generation_manifest_missing",
            {**source, "bundle_manifest_path": str(manifest_path)},
            ("accepted_generation_manifest_missing",),
        )
    try:
        manifest = _read_json_strict(manifest_path)
    except Exception:
        return _unresolved(
            "INVALID_MANIFEST",
            "accepted_generation_manifest_unreadable",
            {**source, "bundle_manifest_path": str(manifest_path)},
            ("accepted_generation_manifest_unreadable",),
        )
    aggregate_hash = _aggregate_hash(manifest)
    expected_hash = str(authority.get("aggregate_hash") or authority.get("run_authority_hash") or "").replace("sha256:", "")
    reasons: list[str] = []
    if not aggregate_hash:
        reasons.append("accepted_generation_aggregate_hash_missing")
    elif not _aggregate_hash_matches(manifest, aggregate_hash):
        reasons.append("accepted_generation_aggregate_hash_mismatch")
    if expected_hash and expected_hash != aggregate_hash:
        reasons.append("historical_evaluation_authority_hash_mismatch")
    expected_generation_id = str(authority.get("generation_id") or authority.get("accepted_generation_id") or "")
    generation_id = str(manifest.get("generation_id") or manifest.get("buy_ai_bundle_id") or manifest.get("artifact_set_id") or "")
    if expected_generation_id and expected_generation_id != generation_id:
        reasons.append("historical_evaluation_authority_generation_id_mismatch")
    candidate = _member(manifest, manifest_path.parent, "candidate_model", "candidate_member", "candidate")
    opportunity = _member(manifest, manifest_path.parent, "opportunity_model", "opportunity_member", "opportunity")
    if candidate is None:
        reasons.append("candidate_member_missing")
    if opportunity is None:
        reasons.append("opportunity_member_missing")
    reasons.extend(_member_integrity_reasons(candidate, opportunity))
    scaler_reasons, artifact_hashes = _member_scaler_integrity(manifest, manifest_path.parent)
    reasons.extend(scaler_reasons)
    if reasons:
        return _unresolved(
            "HASH_MISMATCH" if any("hash_mismatch" in reason for reason in reasons) else "INVALID_MANIFEST",
            ",".join(sorted(set(reasons))),
            {**source, "bundle_manifest_path": str(manifest_path), "generation_id": generation_id},
            tuple(sorted(set(reasons))),
        )
    source_evidence = {
        **source,
        "bundle_manifest_path": str(manifest_path),
        "generation_id": generation_id,
        "temporal_authority_status": "RUN_START_FIXED",
        "manifest_content_hash": _file_hash(manifest_path),
        "artifact_hashes": artifact_hashes,
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
        generation_id=generation_id,
        bundle_manifest_path=str(manifest_path),
        authority_decision=str(manifest.get("authority_decision") or manifest.get("authority_decision_ref") or authority.get("accepted_decision") or ""),
        transaction_state=COMMITTED_TRANSACTION_STATE,
        effective_from=str(manifest.get("effective_from") or authority.get("effective_from") or ""),
        accepted_at=str(manifest.get("accepted_at") or authority.get("accepted_at") or ""),
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


def _resolve_business_date_bound_generation(
    root: Path,
    *,
    business_date: str,
    source: dict[str, Any],
    pointer_path: Path,
) -> AcceptedGenerationResolution:
    business = _date_part(business_date)
    if not business:
        return _unresolved("REVIEW_REQUIRED", "business_date_invalid", source, ("business_date_invalid",), pointer_path=pointer_path)
    candidates, discovery_rejections = _accepted_generation_candidates(root, pointer_path=pointer_path)
    evaluated = [
        _evaluate_candidate(root, candidate, business_date=business)
        for candidate in candidates
    ]
    eligible = [item for item in evaluated if item["selection_status"] == "ELIGIBLE"]
    selection_evidence = {
        **source,
        "business_date": business,
        "history_path": str(root / ACCEPTED_GENERATION_HISTORY),
        "generation_directory": str(root / ACCEPTED_GENERATION_DIR),
        "candidate_count": len(evaluated),
        "eligible_candidate_count": len(eligible),
        "rejected_candidates": [item for item in evaluated if item["selection_status"] != "ELIGIBLE"],
        "discovery_rejections": discovery_rejections,
        "selection_rule": "max(effective_from_date, accepted_at_date, generation_id) among PIT-eligible accepted generation manifests",
        "latest_fallback_used": False,
        "future_generation_used": False,
    }
    if not evaluated:
        return _unresolved(
            "NO_ACCEPTED_GENERATION",
            "NO_ACCEPTED_GENERATION_BOOTSTRAP",
            selection_evidence,
            ("accepted_generation_history_empty", "NO_ACCEPTED_GENERATION_BOOTSTRAP"),
            pointer_path=pointer_path,
        )
    if not eligible:
        reason_counts: dict[str, int] = {}
        for item in evaluated:
            for reason in item["rejection_reasons"]:
                reason_counts[reason] = reason_counts.get(reason, 0) + 1
        reason_codes = tuple(sorted(reason_counts)) or ("no_pit_eligible_accepted_generation",)
        return _unresolved(
            "REVIEW_REQUIRED",
            ",".join(reason_codes),
            selection_evidence,
            reason_codes,
            pointer_path=pointer_path,
        )
    selected = sorted(
        eligible,
        key=lambda item: (
            _date_part(item.get("effective_from") or ""),
            _date_part(item.get("accepted_at") or ""),
            str(item.get("generation_id") or ""),
        ),
    )[-1]
    manifest_path = Path(str(selected["manifest_path"]))
    manifest = _read_json_strict(manifest_path)
    pointer = selected.get("pointer") if isinstance(selected.get("pointer"), dict) else {}
    aggregate_hash = _aggregate_hash(manifest)
    candidate = _member(manifest, manifest_path.parent, "candidate_model", "candidate_member", "candidate")
    opportunity = _member(manifest, manifest_path.parent, "opportunity_model", "opportunity_member", "opportunity")
    source_evidence = {
        **selection_evidence,
        "selected_generation_id": selected["generation_id"],
        "selected_manifest_path": str(manifest_path),
        "selected_source": selected["source"],
        "temporal_authority_status": "PASS",
        "manifest_content_hash": _file_hash(manifest_path),
        "artifact_hashes": selected.get("artifact_hashes") or {},
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
        authority_decision=str(manifest.get("authority_decision") or manifest.get("authority_decision_ref") or pointer.get("authority_decision") or "business-date-bound Accepted Generation ledger"),
        transaction_state=str(pointer.get("transaction_state") or COMMITTED_TRANSACTION_STATE),
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


def _accepted_generation_candidates(root: Path, *, pointer_path: Path) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    candidates: list[dict[str, Any]] = []
    rejected: list[dict[str, Any]] = []
    seen: set[str] = set()

    def add(path: Path, *, source: str, pointer: dict[str, Any] | None = None, history_event: dict[str, Any] | None = None) -> None:
        resolved = _resolve_manifest_path(path, root)
        key = str(resolved)
        if key in seen:
            return
        seen.add(key)
        candidates.append({"manifest_path": resolved, "source": source, "pointer": pointer or {}, "history_event": history_event or {}})

    if pointer_path.exists():
        try:
            pointer = _read_json_strict(pointer_path)
        except Exception as exc:
            rejected.append({"source": "current_pointer", "path": str(pointer_path), "rejection_reasons": ["accepted_generation_pointer_unreadable"], "error": str(exc)})
        else:
            transaction_state = str(pointer.get("transaction_state") or "")
            ref = pointer.get("bundle_manifest_path") or pointer.get("accepted_bundle_path") or pointer.get("accepted_bundle_ref")
            if transaction_state != COMMITTED_TRANSACTION_STATE:
                rejected.append({"source": "current_pointer", "path": str(pointer_path), "transaction_state": transaction_state, "rejection_reasons": ["accepted_generation_pointer_not_committed" if transaction_state else "accepted_generation_pointer_transaction_state_missing"]})
            elif not ref:
                rejected.append({"source": "current_pointer", "path": str(pointer_path), "rejection_reasons": ["accepted_generation_manifest_ref_missing"]})
            else:
                add(Path(str(ref)), source="current_pointer", pointer=pointer)

    history_path = root / ACCEPTED_GENERATION_HISTORY
    if history_path.exists():
        for index, line in enumerate(history_path.read_text(encoding="utf-8").splitlines(), start=1):
            if not line.strip():
                continue
            try:
                event = json.loads(line)
            except Exception as exc:
                rejected.append({"source": "authority_history", "line": index, "rejection_reasons": ["accepted_generation_history_event_unreadable"], "error": str(exc)})
                continue
            if not isinstance(event, dict):
                rejected.append({"source": "authority_history", "line": index, "rejection_reasons": ["accepted_generation_history_event_not_object"]})
                continue
            ref = event.get("bundle_manifest_path") or event.get("manifest_path") or event.get("accepted_generation_manifest")
            generation_id = str(event.get("generation_id") or event.get("accepted_generation_id") or "")
            if ref:
                add(Path(str(ref)), source="authority_history", history_event=event)
            elif generation_id:
                add(root / ACCEPTED_GENERATION_DIR / generation_id / "accepted_generation_manifest.json", source="authority_history", history_event=event)
            else:
                rejected.append({"source": "authority_history", "line": index, "rejection_reasons": ["accepted_generation_history_ref_missing"]})

    generation_dir = root / ACCEPTED_GENERATION_DIR
    if generation_dir.exists():
        for manifest_path in sorted(generation_dir.glob("*/accepted_generation_manifest.json")):
            add(manifest_path, source="accepted_generation_directory")
    return candidates, rejected


def _evaluate_candidate(root: Path, candidate: dict[str, Any], *, business_date: str) -> dict[str, Any]:
    path = Path(str(candidate["manifest_path"]))
    result = {
        "source": candidate["source"],
        "manifest_path": str(path),
        "generation_id": "",
        "accepted_at": "",
        "effective_from": "",
        "effective_until": "",
        "selection_status": "REJECTED",
        "rejection_reasons": [],
        "artifact_hashes": {},
    }
    reasons: list[str] = result["rejection_reasons"]
    if "promotion_candidates" in path.parts:
        reasons.append("promotion_candidate_forbidden_for_runtime")
        return result
    if not path.is_file():
        reasons.append("accepted_generation_manifest_missing")
        return result
    try:
        manifest = _read_json_strict(path)
    except Exception:
        reasons.append("accepted_generation_manifest_unreadable")
        return result
    pointer = candidate.get("pointer") if isinstance(candidate.get("pointer"), dict) else {}
    generation_id = str(manifest.get("generation_id") or manifest.get("accepted_generation_id") or manifest.get("buy_ai_bundle_id") or path.parent.name)
    result.update(
        {
            "generation_id": generation_id,
            "accepted_at": str(manifest.get("accepted_at") or pointer.get("accepted_at") or ""),
            "effective_from": str(manifest.get("effective_from") or pointer.get("effective_from") or ""),
            "effective_until": str(manifest.get("effective_until") or pointer.get("effective_until") or ""),
        }
    )
    aggregate_hash = _aggregate_hash(manifest)
    if not aggregate_hash:
        reasons.append("accepted_generation_aggregate_hash_missing")
    elif not _aggregate_hash_matches(manifest, aggregate_hash):
        reasons.append("accepted_generation_aggregate_hash_mismatch")
    pointer_hash = str(pointer.get("aggregate_hash") or pointer.get("accepted_generation_hash") or "").replace("sha256:", "")
    if pointer_hash and pointer_hash != aggregate_hash:
        reasons.append("accepted_generation_pointer_hash_mismatch")
    reasons.extend(_temporal_authority_reasons(manifest, pointer, business_date=business_date))
    reasons.extend(_temporal_closure_reasons(manifest, pointer, business_date=business_date))
    candidate_member = _member(manifest, path.parent, "candidate_model", "candidate_member", "candidate")
    opportunity_member = _member(manifest, path.parent, "opportunity_model", "opportunity_member", "opportunity")
    if candidate_member is None:
        reasons.append("candidate_member_missing")
    if opportunity_member is None:
        reasons.append("opportunity_member_missing")
    member_reasons = _member_integrity_reasons(candidate_member, opportunity_member)
    reasons.extend(member_reasons)
    scaler_reasons, artifact_hashes = _member_scaler_integrity(manifest, path.parent)
    reasons.extend(scaler_reasons)
    result["artifact_hashes"] = artifact_hashes
    if not reasons:
        result["selection_status"] = "ELIGIBLE"
    result["rejection_reasons"] = sorted(set(reasons))
    return result


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


def _member_scaler_integrity(manifest: dict[str, Any], base_dir: Path) -> tuple[list[str], dict[str, str]]:
    reasons: list[str] = []
    artifact_hashes: dict[str, str] = {}
    for role, keys in (
        ("candidate", ("candidate_model", "candidate_member", "candidate")),
        ("opportunity", ("opportunity_model", "opportunity_member", "opportunity")),
    ):
        payload = _member_payload(manifest, *keys)
        if payload is None:
            continue
        scaler_ref = str(payload.get("scaler_file") or payload.get("scaler_path") or payload.get("scaler_ref") or "")
        scaler_hash = str(payload.get("scaler_hash") or "").replace("sha256:", "")
        feature_hash = str(payload.get("feature_schema_hash") or payload.get("feature_order_hash") or "")
        has_scaler_or_feature_contract = bool(
            scaler_ref
            or scaler_hash
            or feature_hash
            or "scaler_file" in payload
            or "scaler_path" in payload
            or "scaler_ref" in payload
            or "feature_schema_hash" in payload
            or "feature_order_hash" in payload
        )
        if not has_scaler_or_feature_contract:
            continue
        if not feature_hash:
            reasons.append(f"{role}_feature_schema_hash_missing")
        artifact_hashes[f"{role}_feature_schema_hash"] = feature_hash
        if not scaler_ref:
            reasons.append(f"{role}_scaler_reference_missing")
            continue
        scaler_path = _resolve_artifact_path(Path(scaler_ref), base_dir)
        artifact_hashes[f"{role}_scaler_path"] = str(scaler_path)
        artifact_hashes[f"{role}_scaler_hash"] = scaler_hash
        if not scaler_path.is_file():
            reasons.append(f"{role}_scaler_artifact_missing")
            continue
        if not scaler_hash:
            reasons.append(f"{role}_scaler_hash_missing")
        elif _file_hash(scaler_path) != scaler_hash:
            reasons.append(f"{role}_scaler_hash_mismatch")
    return reasons, artifact_hashes


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


def _temporal_authority_reasons(manifest: dict[str, Any], pointer: dict[str, Any], *, business_date: str | None) -> list[str]:
    if not business_date:
        return []
    reasons: list[str] = []
    business = _date_part(business_date)
    if not business:
        return ["business_date_invalid"]
    accepted = _date_part(str(manifest.get("accepted_at") or pointer.get("accepted_at") or ""))
    effective = _date_part(str(manifest.get("effective_from") or pointer.get("effective_from") or ""))
    if not accepted:
        reasons.append("accepted_generation_accepted_at_missing_or_invalid")
    elif accepted > business:
        reasons.append("accepted_generation_accepted_at_after_business_date")
    if not effective:
        reasons.append("accepted_generation_effective_from_missing_or_invalid")
    elif effective > business:
        reasons.append("accepted_generation_effective_from_after_business_date")
    return reasons


def _temporal_closure_reasons(manifest: dict[str, Any], pointer: dict[str, Any], *, business_date: str | None) -> list[str]:
    if not business_date:
        return []
    business = _date_part(business_date)
    if not business:
        return []
    reasons: list[str] = []
    effective_until = _date_part(str(manifest.get("effective_until") or pointer.get("effective_until") or ""))
    superseded_at = _date_part(str(manifest.get("superseded_at") or pointer.get("superseded_at") or ""))
    revoked_at = _date_part(str(manifest.get("revoked_at") or pointer.get("revoked_at") or ""))
    status = str(manifest.get("status") or manifest.get("accepted_status") or pointer.get("status") or "").upper()
    if effective_until and effective_until < business:
        reasons.append("accepted_generation_effective_until_before_business_date")
    if superseded_at and superseded_at <= business:
        reasons.append("accepted_generation_superseded_at_lte_business_date")
    if revoked_at and revoked_at <= business:
        reasons.append("accepted_generation_revoked_at_lte_business_date")
    if status in {"REVOKED", "REJECTED", "SUPERSEDED"}:
        reasons.append(f"accepted_generation_status_{status.lower()}")
    return reasons


def _date_part(value: str) -> str:
    if not value:
        return ""
    text = str(value)
    if len(text) >= 10 and text[4] == "-" and text[7] == "-":
        return text[:10]
    return ""


def _resolve_manifest_path(path: Path, runtime_root: Path) -> Path:
    if path.is_absolute():
        return path
    if path.parts and path.parts[0] == ".runtime":
        return runtime_root.parent / path
    return runtime_root / path


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
