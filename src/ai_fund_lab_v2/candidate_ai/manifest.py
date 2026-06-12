from __future__ import annotations

import json
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping

from ai_fund_lab_v2.candidate_ai.paths import CandidateAIRuntimePaths
from ai_fund_lab_v2.candidate_ai.schemas import CandidateFeatureAudit, CandidateFeatureManifest
from ai_fund_lab_v2.runtime import RuntimePaths


FEATURE_SCHEMA_VERSION = "candidate_feature_schema_v1"


def build_candidate_feature_manifest(
    rows: Iterable[Mapping[str, Any]],
    *,
    audit: CandidateFeatureAudit,
    output_path: Path | str,
    audit_path: Path | str,
    input_sources: tuple[str, ...] = ("mock_daily_quotes_normalized",),
    schema_version: str = FEATURE_SCHEMA_VERSION,
) -> CandidateFeatureManifest:
    materialized_rows = [dict(row) for row in rows]
    return CandidateFeatureManifest(
        feature_version=str(audit.feature_version or ""),
        created_at=datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        as_of_date=str(audit.as_of_date or ""),
        target_date=str(audit.target_date or ""),
        row_count=len(materialized_rows),
        eligible_count=audit.eligible_count,
        excluded_count=audit.excluded_count,
        source_snapshot_id=str(_first_value(materialized_rows, "source_snapshot_id") or ""),
        input_sources=input_sources,
        output_path=str(output_path),
        audit_path=str(audit_path),
        schema_version=schema_version,
        code_hash_optional=None,
    )


def write_candidate_feature_outputs(
    rows: Iterable[Mapping[str, Any]],
    *,
    audit: CandidateFeatureAudit,
    runtime_dir: Path | str = ".runtime",
) -> dict[str, Path]:
    return write_candidate_feature_outputs_with_prefix(
        rows,
        audit=audit,
        runtime_dir=runtime_dir,
        filename_prefix="candidate_features_mock",
        input_sources=("mock_daily_quotes_normalized",),
    )


def write_candidate_feature_outputs_with_prefix(
    rows: Iterable[Mapping[str, Any]],
    *,
    audit: CandidateFeatureAudit,
    runtime_dir: Path | str = ".runtime",
    filename_prefix: str,
    input_sources: tuple[str, ...],
    extra_manifest: Mapping[str, Any] | None = None,
    extra_audit: Mapping[str, Any] | None = None,
) -> dict[str, Path]:
    materialized_rows = [dict(row) for row in rows]
    paths = CandidateAIRuntimePaths(RuntimePaths(runtime_dir=Path(runtime_dir)))
    paths.ensure_dirs()
    as_of_date = str(audit.as_of_date or "unknown")
    feature_path = paths.features / f"{filename_prefix}_{as_of_date}.json"
    audit_path = paths.audit / f"{filename_prefix}_audit_{as_of_date}.json"
    manifest_path = paths.manifests / f"{filename_prefix}_manifest_{as_of_date}.json"

    manifest = build_candidate_feature_manifest(
        materialized_rows,
        audit=audit,
        output_path=feature_path,
        audit_path=audit_path,
        input_sources=input_sources,
    )
    audit_payload = audit.to_dict()
    if extra_audit:
        audit_payload.update(dict(extra_audit))
    manifest_payload = asdict(manifest)
    if extra_manifest:
        manifest_payload.update(dict(extra_manifest))
    _write_json(feature_path, {"rows": materialized_rows})
    _write_json(audit_path, audit_payload)
    _write_json(manifest_path, manifest_payload)
    return {"features": feature_path, "audit": audit_path, "manifest": manifest_path}


def _first_value(rows: list[Mapping[str, Any]], key: str) -> Any:
    for row in rows:
        value = row.get(key)
        if value is not None:
            return value
    return None


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=True, indent=2, sort_keys=True) + "\n", encoding="utf-8")
