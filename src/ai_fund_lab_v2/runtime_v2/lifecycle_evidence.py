from __future__ import annotations

import hashlib
import json
import math
from dataclasses import asdict, dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Any, Iterable

import pandas as pd

from ai_fund_lab_v2.runtime_v2.ai_lifecycle_gates import parse_date


@dataclass(frozen=True)
class RuntimeLifecycleAuthorityDesign:
    freshness_authority: str
    drift_baseline_authority: str
    runtime_current_authority: str
    trading_calendar_authority: str
    accepted_artifact_authority: str
    runtime_decision_authority: str

    def to_dict(self) -> dict[str, str]:
        return asdict(self)


@dataclass(frozen=True)
class RuntimeLifecycleEvidence:
    status: str
    reason_codes: tuple[str, ...]
    accepted_bundle_id: str
    baseline_identity: str
    current_window_identity: str
    freshness: dict[str, Any]
    drift: dict[str, Any]
    freshness_evidence: dict[str, Any]
    baseline_evidence: dict[str, Any]
    current_evidence: dict[str, Any]
    integrity_evidence: dict[str, Any]

    def to_gate_input(self) -> dict[str, Any]:
        return {"integrity": self.integrity_evidence, "freshness": self.freshness, "drift": self.drift}

    def to_artifact_fields(self) -> dict[str, Any]:
        return {
            "accepted_bundle_id": self.accepted_bundle_id,
            "baseline_identity": self.baseline_identity,
            "current_window_identity": self.current_window_identity,
            "freshness_evidence": self.freshness_evidence,
            "baseline_evidence": self.baseline_evidence,
            "current_evidence": self.current_evidence,
            "integrity_evidence": self.integrity_evidence,
            "reason_codes": list(self.reason_codes),
        }

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "reason_codes": list(self.reason_codes),
            "gate_input": self.to_gate_input(),
            "artifact_fields": self.to_artifact_fields(),
        }


def authority_design() -> RuntimeLifecycleAuthorityDesign:
    return RuntimeLifecycleAuthorityDesign(
        freshness_authority="Accepted Dataset Bundle metadata, Accepted Training Bundle metadata, Registry accepted_at, formal trading calendar, and Runtime decision date.",
        drift_baseline_authority="Accepted Atomic BUY AI Bundle materialized runtime baseline distributions, lineage, schema, and hash evidence.",
        runtime_current_authority="Current Runtime BUY AI producer candidate rows and opportunity rankings generated in the normal job.",
        trading_calendar_authority="Formal trading calendar source_ref recorded in accepted dataset metadata; Production weekday fallback is forbidden.",
        accepted_artifact_authority="Registry accepted state resolving one accepted Atomic BUY AI Bundle. Promotion candidates, latest directories, and manual path fallback are forbidden in Production.",
        runtime_decision_authority="ai_lifecycle_gate_decision.json written by the normal Runtime Control Plane before BUY planning.",
    )


def build_runtime_lifecycle_evidence(
    *,
    runtime_root: Path | str,
    business_date: str,
    feature_date: str,
    runtime_id: str,
    candidate_payload: dict[str, Any],
    opportunity_payload: dict[str, Any],
    artifact_paths: dict[str, Path] | None = None,
    accepted_bundle_path: Path | str | None = None,
) -> RuntimeLifecycleEvidence:
    root = Path(runtime_root)
    resolution = _resolve_accepted_bundle(root, accepted_bundle_path)
    accepted_bundle = Path(str(resolution.get("accepted_bundle_ref"))) if resolution.get("accepted_bundle_ref") else None
    bundle_payload = _read_json(accepted_bundle) if accepted_bundle else {}
    reason_codes: list[str] = []
    integrity = _integrity_evidence(accepted_bundle, bundle_payload, resolution)
    if integrity["status"] != "PASS":
        reason_codes.extend(integrity.get("reason_codes") or [str(integrity["reason"])])

    freshness = _resolve_freshness(
        business_date=business_date,
        bundle=bundle_payload,
        accepted_bundle_path=accepted_bundle,
        artifact_paths=artifact_paths or {},
    )
    if freshness["status"] != "PASS":
        reason_codes.extend(freshness["reason_codes"])

    baseline = _resolve_baseline(bundle_payload, accepted_bundle)
    if baseline["status"] != "PASS":
        reason_codes.extend(baseline["reason_codes"])

    current = _build_current_window_evidence(
        runtime_id=runtime_id,
        feature_date=feature_date,
        candidate_payload=candidate_payload,
        opportunity_payload=opportunity_payload,
    )
    if current["status"] != "PASS":
        reason_codes.extend(current["reason_codes"])

    drift = {
        "baseline_identity": baseline.get("baseline_identity") or "",
        "current_window_identity": current.get("current_window_identity") or "",
        "evidence_ref": current.get("evidence_ref") or "",
        "baseline_prediction_scores": baseline.get("prediction_distribution_values") or [],
        "current_prediction_scores": current.get("prediction_distribution_values") or [],
        "baseline_feature_values": baseline.get("feature_distribution_values") or [],
        "current_feature_values": current.get("feature_distribution_values") or [],
        "baseline_positive_coverage": baseline.get("positive_coverage"),
        "current_positive_coverage": current.get("positive_coverage"),
        "baseline_candidate_population": baseline.get("candidate_population"),
        "current_candidate_population": current.get("candidate_population"),
        "all_negative_consecutive_business_days": current.get("all_negative_consecutive_business_days"),
    }
    accepted_bundle_id = str(bundle_payload.get("buy_ai_bundle_id") or bundle_payload.get("artifact_set_id") or "")
    return RuntimeLifecycleEvidence(
        status="PASS" if not reason_codes else "REVIEW_REQUIRED",
        reason_codes=tuple(dict.fromkeys(reason_codes)),
        accepted_bundle_id=accepted_bundle_id,
        baseline_identity=str(baseline.get("baseline_identity") or ""),
        current_window_identity=str(current.get("current_window_identity") or ""),
        freshness={
            "dataset_lag_business_days": freshness.get("dataset_lag_business_days"),
            "model_training_lag_business_days": freshness.get("model_training_lag_business_days"),
            "model_acceptance_age_business_days": freshness.get("model_acceptance_age_business_days"),
            "source_data_age_business_days": freshness.get("source_data_age_business_days"),
            "feature_data_age_business_days": freshness.get("feature_data_age_business_days"),
            "reason_codes": freshness.get("reason_codes") or [],
        },
        drift=drift,
        freshness_evidence=freshness,
        baseline_evidence=baseline,
        current_evidence=current,
        integrity_evidence=integrity,
    )


def _resolve_accepted_bundle_path(runtime_root: Path, explicit: Path | str | None) -> Path | None:
    resolved = _resolve_accepted_bundle(runtime_root, explicit)
    ref = resolved.get("accepted_bundle_ref")
    return Path(str(ref)) if ref else None


def _resolve_accepted_bundle(runtime_root: Path, explicit: Path | str | None) -> dict[str, Any]:
    prod_root = _is_production_runtime_root(runtime_root)
    if explicit:
        explicit_path = Path(explicit)
        if prod_root:
            return {
                "status": "INSUFFICIENT_EVIDENCE",
                "reason_codes": ["manual_accepted_bundle_path_forbidden"],
                "accepted_bundle_ref": "",
                "accepted_state_ref": "",
                "accepted_event_identity": "",
                "accepted_state_identity": "",
            }
        return _accepted_resolution_from_path(explicit_path, accepted_state_ref="", isolated=True)
    state_path = runtime_root / "runtime_state" / "accepted_buy_ai_bundle.json"
    if not state_path.exists() and runtime_root != Path(".runtime"):
        state_path = Path(".runtime") / "runtime_state" / "accepted_buy_ai_bundle.json"
    if not state_path.exists():
        return {
            "status": "INSUFFICIENT_EVIDENCE",
            "reason_codes": ["accepted_state_missing"],
            "accepted_bundle_ref": "",
            "accepted_state_ref": str(state_path),
            "accepted_event_identity": "",
            "accepted_state_identity": "",
        }
    state = _read_json(state_path)
    ref_value = state.get("accepted_bundle_path") or state.get("accepted_bundle_ref") or state.get("bundle_path")
    if ref_value:
        bundle_path = Path(str(ref_value))
        if not bundle_path.is_absolute():
            bundle_path = Path.cwd() / bundle_path
        resolved = _accepted_resolution_from_path(bundle_path, accepted_state_ref=str(state_path), isolated=False)
        return {
            **resolved,
            "accepted_event_identity": str(state.get("accepted_event_id") or state.get("accepted_event_identity") or resolved.get("accepted_event_identity") or ""),
            "accepted_state_identity": str(state.get("accepted_state_hash") or state.get("accepted_state_identity") or _stable_hash(state)),
        }
    resolved = _accepted_resolution_from_path(state_path, accepted_state_ref=str(state_path), isolated=False)
    return {
        **resolved,
        "accepted_event_identity": str(state.get("accepted_event_id") or state.get("accepted_event_identity") or resolved.get("accepted_event_identity") or ""),
        "accepted_state_identity": str(state.get("accepted_state_hash") or state.get("accepted_state_identity") or _stable_hash(state)),
    }


def _accepted_resolution_from_path(path: Path, *, accepted_state_ref: str, isolated: bool) -> dict[str, Any]:
    if not path.exists():
        return {
            "status": "INSUFFICIENT_EVIDENCE",
            "reason_codes": ["accepted_bundle_missing"],
            "accepted_bundle_ref": "",
            "accepted_state_ref": accepted_state_ref,
            "accepted_event_identity": "",
            "accepted_state_identity": "",
        }
    if "promotion_candidates" in path.parts and not isolated:
        return {
            "status": "INSUFFICIENT_EVIDENCE",
            "reason_codes": ["promotion_candidate_forbidden_for_runtime"],
            "accepted_bundle_ref": "",
            "accepted_state_ref": accepted_state_ref,
            "accepted_event_identity": "",
            "accepted_state_identity": "",
        }
    payload = _read_json(path)
    return {
        "status": "PASS" if payload else "INSUFFICIENT_EVIDENCE",
        "reason_codes": [] if payload else ["accepted_bundle_unreadable"],
        "accepted_bundle_ref": str(path),
        "accepted_state_ref": accepted_state_ref,
        "accepted_event_identity": str(payload.get("accepted_event_id") or payload.get("accepted_event_identity") or payload.get("registry_event_id") or ""),
        "accepted_state_identity": str(payload.get("accepted_state_hash") or payload.get("accepted_state_identity") or ""),
        "isolated_review_input": isolated,
    }


def _resolve_freshness(*, business_date: str, bundle: dict[str, Any], accepted_bundle_path: Path | None, artifact_paths: dict[str, Path]) -> dict[str, Any]:
    reasons: list[str] = []
    candidate_dataset_dir = _path_from(bundle, "candidate_dataset", "dataset_dir")
    opportunity_dataset_dir = _path_from(bundle, "opportunity_dataset", "dataset_dir")
    candidate_training_dir = _path_from(bundle, "candidate_training", "training_dir")
    opportunity_training_dir = _path_from(bundle, "opportunity_training", "training_dir")
    dataset_meta = _read_json((opportunity_dataset_dir or candidate_dataset_dir or Path()) / "dataset_metadata.json") if (opportunity_dataset_dir or candidate_dataset_dir) else {}
    candidate_dataset_meta = _read_json(candidate_dataset_dir / "dataset_metadata.json") if candidate_dataset_dir else {}
    training_meta = _read_json((opportunity_training_dir or candidate_training_dir or Path()) / "training_metadata.json") if (opportunity_training_dir or candidate_training_dir) else {}
    label_safe_cutoff = _nested(dataset_meta, "label_safe_cutoff", "label_safe_cutoff") or _nested(candidate_dataset_meta, "label_safe_cutoff", "label_safe_cutoff")
    training_dataset_max_date = _source_max_target_date(dataset_meta) or _source_max_target_date(candidate_dataset_meta)
    model_training_cutoff = _model_training_cutoff(training_meta, dataset_meta, candidate_dataset_meta)
    model_accepted_at = _accepted_at(bundle, accepted_bundle_path)
    trading_calendar_ref = _nested(dataset_meta, "input_artifacts", "trading_calendar", "source_ref") or _nested(candidate_dataset_meta, "input_artifacts", "trading_calendar", "source_ref")
    calendar_dates = _load_trading_calendar(trading_calendar_ref)
    calendar_status = _calendar_status(calendar_dates, trading_calendar_ref)
    if calendar_status != "PASS":
        reasons.append(calendar_status)
    if not label_safe_cutoff:
        reasons.append("missing_label_safe_cutoff")
    if not training_dataset_max_date:
        reasons.append("missing_training_dataset_max_date")
    if not model_training_cutoff:
        reasons.append("missing_model_training_cutoff")
    if not model_accepted_at:
        reasons.append("missing_model_accepted_at")
    decision = parse_date(business_date)
    label_safe = parse_date(label_safe_cutoff)
    dataset_max = parse_date(training_dataset_max_date)
    training_cutoff = parse_date(model_training_cutoff)
    accepted_at = parse_date(model_accepted_at)
    range_reasons = _calendar_range_reasons(calendar_dates, [value for value in (label_safe, dataset_max, training_cutoff, accepted_at, decision) if value is not None])
    reasons.extend(range_reasons)
    dataset_lag = _bdiff(calendar_dates, dataset_max, label_safe)
    training_lag = _bdiff(calendar_dates, training_cutoff, label_safe)
    acceptance_age = _bdiff(calendar_dates, accepted_at, decision)
    if dataset_lag is not None and dataset_lag < 0:
        reasons.append("negative_dataset_lag")
    if training_lag is not None and training_lag < 0:
        reasons.append("negative_model_training_lag")
    if acceptance_age is not None and acceptance_age < 0:
        reasons.append("negative_model_acceptance_age")
    return {
        "status": "PASS" if not reasons else "REVIEW_REQUIRED",
        "reason_codes": reasons,
        "accepted_bundle_id": bundle.get("buy_ai_bundle_id") or "",
        "accepted_bundle_ref": str(accepted_bundle_path or ""),
        "dataset_bundle_id": _nested(dataset_meta, "dataset_version") or _nested(candidate_dataset_meta, "dataset_version") or "",
        "training_bundle_id": training_meta.get("training_version") or "",
        "label_safe_cutoff": label_safe_cutoff,
        "training_dataset_max_date": training_dataset_max_date,
        "model_training_cutoff": model_training_cutoff,
        "model_accepted_at": model_accepted_at,
        "decision_date": business_date,
        "trading_calendar_ref": trading_calendar_ref or "",
        "trading_calendar_identity": _calendar_identity(calendar_dates, trading_calendar_ref),
        "dataset_lag_business_days": dataset_lag,
        "model_training_lag_business_days": training_lag,
        "model_acceptance_age_business_days": acceptance_age,
        "thresholds": {
            "dataset_lag_block_business_days": 20,
            "model_training_lag_review_business_days": 5,
            "model_training_lag_block_business_days": 20,
            "model_acceptance_age_review_business_days": 60,
            "model_acceptance_age_block_business_days": 120,
        },
        "reason": ",".join(reasons) if reasons else "freshness authority resolved from accepted artifacts",
    }


def _resolve_baseline(bundle: dict[str, Any], bundle_path: Path | None) -> dict[str, Any]:
    reasons: list[str] = []
    baseline = _materialized_baseline(bundle, bundle_path)
    if not baseline:
        reasons.append("missing_materialized_runtime_baseline")
        baseline = {}
    expected_hash = str(baseline.get("baseline_hash") or "")
    actual_hash = _stable_hash({key: value for key, value in baseline.items() if key != "baseline_hash"}) if baseline else ""
    if expected_hash and actual_hash and expected_hash != actual_hash:
        reasons.append("baseline_hash_mismatch")
    prediction_values = _finite_numbers(baseline.get("prediction_distribution_values") or baseline.get("prediction_scores") or [])
    feature_values = _finite_numbers(baseline.get("feature_distribution_values") or baseline.get("feature_values") or [])
    if len(prediction_values) < 5:
        reasons.append("insufficient_prediction_baseline_sample")
    if len(feature_values) < 5:
        reasons.append("insufficient_feature_baseline_sample")
    population = baseline.get("candidate_population")
    if population is None:
        reasons.append("missing_candidate_population_baseline")
    positive = baseline.get("positive_coverage")
    if positive is None:
        reasons.append("missing_positive_coverage_baseline")
    baseline_hash = expected_hash or actual_hash
    identity = f"{bundle.get('buy_ai_bundle_id') or 'accepted_bundle'}:{baseline_hash[:16]}" if bundle else ""
    return {
        "status": "PASS" if not reasons else "REVIEW_REQUIRED",
        "reason_codes": reasons,
        "baseline_identity": identity,
        "baseline_hash": baseline_hash,
        "baseline_source_refs": baseline.get("lineage") or {"accepted_bundle": str(bundle_path or "")},
        "baseline_date_range": baseline.get("baseline_date_range") or {},
        "baseline_row_count": baseline.get("row_count"),
        "prediction_distribution_values": prediction_values,
        "feature_distribution_values": feature_values,
        "positive_coverage": positive,
        "candidate_population": population,
        "reason": ",".join(reasons) if reasons else "accepted baseline resolved",
    }


def _build_current_window_evidence(*, runtime_id: str, feature_date: str, candidate_payload: dict[str, Any], opportunity_payload: dict[str, Any]) -> dict[str, Any]:
    reasons: list[str] = []
    candidate_rows = list(candidate_payload.get("rows") or [])
    rankings = list(opportunity_payload.get("rankings") or [])
    candidate_scores = _finite_numbers(row.get("candidate_score") for row in candidate_rows)
    scores = _finite_numbers((row.get("opportunity_score") if row.get("opportunity_score") is not None else row.get("expected_edge_score")) for row in rankings)
    positive_count = sum(1 for score in scores if score > 0)
    if not candidate_scores:
        reasons.append("missing_current_candidate_scores")
    if not scores:
        reasons.append("missing_current_prediction_scores")
    return {
        "status": "PASS" if not reasons else "REVIEW_REQUIRED",
        "reason_codes": reasons,
        "current_window_identity": f"{runtime_id}:{feature_date}:{_stable_hash({'candidate_count': len(candidate_rows), 'ranking_count': len(rankings), 'scores': scores[:20]})[:16]}",
        "evidence_ref": str(opportunity_payload.get("artifact_path") or ""),
        "candidate_population": len(candidate_rows),
        "prediction_distribution_values": scores,
        "feature_distribution_values": candidate_scores,
        "positive_coverage": positive_count / len(scores) if scores else None,
        "all_negative_consecutive_business_days": 1 if scores and positive_count == 0 else 0,
        "reason": ",".join(reasons) if reasons else "current runtime evidence resolved",
    }


def _integrity_evidence(path: Path | None, bundle: dict[str, Any], resolution: dict[str, Any]) -> dict[str, Any]:
    reasons: list[str] = list(resolution.get("reason_codes") or [])
    if not path or not path.exists():
        return {
            "status": "INSUFFICIENT_EVIDENCE",
            "reason": "missing_accepted_bundle_ref",
            "reason_codes": reasons or ["missing_accepted_bundle_ref"],
            "accepted_bundle_ref": "",
            "accepted_event_identity": resolution.get("accepted_event_identity") or "",
            "accepted_state_identity": resolution.get("accepted_state_identity") or "",
        }
    if not bundle:
        reasons.append("accepted_bundle_unreadable")
    bundle_hash = bundle.get("joint_bundle_hash") or bundle.get("bundle_hash") or ""
    if not bundle_hash:
        reasons.append("missing_joint_bundle_hash")
    elif _stable_hash({key: value for key, value in bundle.items() if key != "joint_bundle_hash"}) != bundle_hash:
        reasons.append("joint_bundle_hash_mismatch")
    for component, hash_key in (
        ("candidate_dataset", "dataset_hash"),
        ("opportunity_dataset", "dataset_hash"),
        ("candidate_training", "bundle_hash"),
        ("opportunity_training", "bundle_hash"),
    ):
        _verify_component_hash(bundle, component, hash_key, reasons)
    _verify_training_dataset_reference(bundle, "candidate", reasons)
    _verify_training_dataset_reference(bundle, "opportunity", reasons)
    _verify_calibration_artifact(bundle, reasons)
    compat = bundle.get("compatibility_evidence") or {}
    for key in (
        "candidate_and_opportunity_promoted_atomically",
        "candidate_dataset_hash_matches_training",
        "opportunity_dataset_hash_matches_training",
        "feature_contract_preserved",
        "opportunity_target_preserved",
        "bv15_preserved",
    ):
        if compat.get(key) is not True:
            reasons.append(f"compatibility_{key}_not_pass")
    if not resolution.get("accepted_event_identity"):
        reasons.append("missing_accepted_event_identity")
    return {
        "status": "PASS" if not reasons else "CRITICAL_AUTHORITY_VIOLATION" if any("mismatch" in reason or "forbidden" in reason for reason in reasons) else "INSUFFICIENT_EVIDENCE",
        "reason": "accepted bundle verified" if not reasons else ",".join(reasons),
        "reason_codes": list(dict.fromkeys(reasons)),
        "accepted_bundle_ref": str(path),
        "accepted_event_identity": resolution.get("accepted_event_identity") or "",
        "accepted_state_identity": resolution.get("accepted_state_identity") or "",
        "accepted_state_ref": resolution.get("accepted_state_ref") or "",
        "accepted_bundle_hash": bundle_hash,
        "content_hash": _file_hash(path),
    }


def _path_from(payload: dict[str, Any], *keys: str) -> Path | None:
    value = _nested(payload, *keys)
    return Path(str(value)) if value else None


def _nested(payload: dict[str, Any], *keys: str) -> Any:
    current: Any = payload
    for key in keys:
        if not isinstance(current, dict) or key not in current:
            return None
        current = current[key]
    return current


def _source_max_target_date(*metas: dict[str, Any]) -> str | None:
    for meta in metas:
        for source in ("candidate_source", "formal_candidate_dataset", "opportunity_source", "candidate_label_source"):
            value = _nested(meta, "input_artifacts", source, "max_target_date")
            if value:
                return str(value)
    return None


def _model_training_cutoff(training_meta: dict[str, Any], *dataset_metas: dict[str, Any]) -> str | None:
    for key in ("model_training_cutoff", "training_cutoff", "training_data_cutoff"):
        if training_meta.get(key):
            return str(training_meta[key])
    return None


def _accepted_at(bundle: dict[str, Any], path: Path | None) -> str | None:
    for key in ("model_accepted_at", "accepted_at", "registered_at"):
        if bundle.get(key):
            return str(bundle[key])
    tx = path.parent / "transaction.json" if path else None
    if tx and tx.exists():
        payload = _read_json(tx)
        for group in ("previous_reference", "promotion_candidate"):
            value = _find_first(payload.get(group), "accepted_at") or _find_first(payload.get(group), "registered_at")
            if value:
                return str(value)
    return None


def _find_first(payload: Any, key: str) -> Any:
    if isinstance(payload, dict):
        if key in payload:
            return payload[key]
        for value in payload.values():
            found = _find_first(value, key)
            if found:
                return found
    elif isinstance(payload, list):
        for item in payload:
            found = _find_first(item, key)
            if found:
                return found
    return None


def _load_trading_calendar(ref: str | None) -> list[date]:
    if not ref:
        return []
    path = Path(str(ref).replace("artifact:", ""))
    if not path.exists():
        return []
    try:
        if path.suffix == ".parquet":
            frame = pd.read_parquet(path)
        elif path.suffix == ".csv":
            frame = pd.read_csv(path)
        else:
            return []
    except Exception:
        return []
    for column in ("Date", "date", "target_date", "business_date"):
        if column in frame.columns:
            dates = [parse_date(value) for value in frame[column].dropna().astype(str).tolist()]
            return sorted({value for value in dates if value is not None})
    return []


def _calendar_status(calendar_dates: list[date], ref: str | None) -> str:
    if not ref:
        return "missing_formal_trading_calendar"
    if str(ref) == "weekday_fallback":
        return "weekday_fallback_forbidden"
    if not calendar_dates:
        return "formal_trading_calendar_unavailable"
    return "PASS"


def _calendar_range_reasons(calendar_dates: list[date], required_dates: list[date]) -> list[str]:
    if not calendar_dates or not required_dates:
        return []
    reasons: list[str] = []
    if min(required_dates) < calendar_dates[0]:
        reasons.append("calendar_range_start_insufficient")
    if max(required_dates) > calendar_dates[-1]:
        reasons.append("calendar_range_end_insufficient")
    return reasons


def _bdiff(calendar_dates: list[date], start: date | None, end: date | None) -> int | None:
    if start is None or end is None:
        return None
    if calendar_dates:
        if end < start:
            return -_bdiff(calendar_dates, end, start)  # type: ignore[arg-type]
        return sum(1 for item in calendar_dates if start < item <= end)
    return None


def _calendar_identity(calendar_dates: list[date], ref: str | None) -> str:
    payload = {"ref": ref or "weekday_fallback", "count": len(calendar_dates), "min": str(calendar_dates[0]) if calendar_dates else "", "max": str(calendar_dates[-1]) if calendar_dates else ""}
    return _stable_hash(payload)


def _date_range_from_metadata(meta: dict[str, Any]) -> dict[str, Any]:
    return {
        "min_target_date": _nested(meta, "input_artifacts", "candidate_source", "min_target_date"),
        "max_target_date": _nested(meta, "input_artifacts", "candidate_source", "max_target_date"),
    }


def _materialized_baseline(bundle: dict[str, Any], bundle_path: Path | None) -> dict[str, Any]:
    inline = bundle.get("runtime_baseline") or bundle.get("materialized_drift_baseline")
    if isinstance(inline, dict):
        return inline
    ref = bundle.get("runtime_baseline_ref") or bundle.get("materialized_drift_baseline_ref")
    if not ref:
        return {}
    path = Path(str(ref))
    if not path.is_absolute() and bundle_path is not None:
        path = bundle_path.parent / path
    return _read_json(path)


def _verify_component_hash(bundle: dict[str, Any], component: str, hash_key: str, reasons: list[str]) -> None:
    payload = bundle.get(component) or {}
    expected = payload.get(hash_key)
    directory = payload.get("dataset_dir") or payload.get("training_dir")
    manifest = _read_json(Path(str(directory)) / "hash_manifest.json") if directory else {}
    actual = manifest.get(hash_key)
    if not expected:
        reasons.append(f"missing_{component}_{hash_key}")
    elif actual and actual != expected:
        reasons.append(f"{component}_{hash_key}_mismatch")
    if directory and not Path(str(directory)).exists():
        reasons.append(f"{component}_directory_missing")
    for schema_key in ("feature_schema_hash", "target_schema_hash"):
        expected_schema = payload.get(schema_key) or _nested(payload, "dataset_reference", schema_key)
        actual_schema = manifest.get(schema_key)
        if expected_schema and actual_schema and expected_schema != actual_schema:
            reasons.append(f"{component}_{schema_key}_mismatch")
    if directory and not (Path(str(directory)) / "lineage.json").is_file():
        reasons.append(f"{component}_lineage_missing")


def _verify_training_dataset_reference(bundle: dict[str, Any], name: str, reasons: list[str]) -> None:
    training = bundle.get(f"{name}_training") or {}
    dataset = bundle.get(f"{name}_dataset") or {}
    ref = training.get("dataset_reference") or {}
    if not ref:
        reasons.append(f"{name}_training_dataset_reference_missing")
        return
    for key in ("dataset_hash", "feature_schema_hash", "target_schema_hash"):
        if ref.get(key) and dataset.get(key) and ref.get(key) != dataset.get(key):
            reasons.append(f"{name}_training_dataset_reference_{key}_mismatch")


def _verify_calibration_artifact(bundle: dict[str, Any], reasons: list[str]) -> None:
    training_dir = _path_from(bundle, "opportunity_training", "training_dir")
    if not training_dir:
        reasons.append("opportunity_training_dir_missing")
        return
    manifest = _read_json(training_dir / "hash_manifest.json")
    for name in ("calibration_model.pkl", "calibration_parameters.json", "calibration_schema.json", "calibration_metadata.json"):
        if not (training_dir / name).is_file():
            reasons.append(f"{name}_missing")
        elif manifest.get("file_hashes", {}).get(name) and _file_hash(training_dir / name) != manifest["file_hashes"][name]:
            reasons.append(f"{name}_hash_mismatch")


def _finite_numbers(values: Iterable[Any]) -> list[float]:
    out: list[float] = []
    for value in values:
        try:
            number = float(value)
        except (TypeError, ValueError):
            continue
        if math.isfinite(number):
            out.append(number)
    return out


def _float(value: Any) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return math.nan


def _read_json(path: Path) -> dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _file_hash(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _stable_hash(payload: Any) -> str:
    return hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True, default=str).encode("utf-8")).hexdigest()


def _is_production_runtime_root(runtime_root: Path) -> bool:
    try:
        return runtime_root.resolve() == Path(".runtime").resolve()
    except OSError:
        return str(runtime_root) == ".runtime"
