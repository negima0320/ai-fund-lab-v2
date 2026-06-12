from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ai_fund_lab_v2.candidate_ai.data_loader import CandidateRealDataLoaderAudit
from ai_fund_lab_v2.candidate_ai.paths import CandidateAIRuntimePaths
from ai_fund_lab_v2.runtime import RuntimePaths


@dataclass(frozen=True)
class CandidateLoaderManifest:
    loader_version: str
    schema_version: str
    created_at: str
    as_of_date: str
    source_snapshot_id: str
    input_source_path: str | None
    input_manifest_path: str | None
    input_row_count: int
    filtered_row_count: int
    dropped_future_row_count: int
    input_hash_optional: str | None
    output_path: str
    audit_path: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "loader_version": self.loader_version,
            "schema_version": self.schema_version,
            "created_at": self.created_at,
            "as_of_date": self.as_of_date,
            "source_snapshot_id": self.source_snapshot_id,
            "input_source_path": self.input_source_path,
            "input_manifest_path": self.input_manifest_path,
            "input_row_count": self.input_row_count,
            "filtered_row_count": self.filtered_row_count,
            "dropped_future_row_count": self.dropped_future_row_count,
            "input_hash_optional": self.input_hash_optional,
            "output_path": self.output_path,
            "audit_path": self.audit_path,
        }


def build_candidate_loader_manifest(
    *,
    audit: CandidateRealDataLoaderAudit,
    output_path: Path | str,
    audit_path: Path | str,
) -> CandidateLoaderManifest:
    return CandidateLoaderManifest(
        loader_version=audit.loader_version,
        schema_version=audit.schema_version,
        created_at=datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        as_of_date=audit.as_of_date,
        source_snapshot_id=audit.source_snapshot_id,
        input_source_path=audit.input_source_path,
        input_manifest_path=audit.input_manifest_path,
        input_row_count=audit.input_row_count,
        filtered_row_count=audit.filtered_row_count,
        dropped_future_row_count=audit.dropped_future_row_count,
        input_hash_optional=audit.input_hash_optional,
        output_path=str(output_path),
        audit_path=str(audit_path),
    )


def write_candidate_loader_contract_outputs(
    rows: list[dict[str, Any]],
    *,
    audit: CandidateRealDataLoaderAudit,
    runtime_dir: Path | str = ".runtime",
) -> dict[str, Path]:
    paths = CandidateAIRuntimePaths(RuntimePaths(runtime_dir=Path(runtime_dir)))
    paths.ensure_dirs()
    output_path = paths.tmp / f"candidate_loader_contract_rows_{audit.as_of_date}.json"
    audit_path = paths.audit / f"candidate_loader_contract_audit_{audit.as_of_date}.json"
    manifest_path = paths.manifests / f"candidate_loader_contract_manifest_{audit.as_of_date}.json"
    manifest = build_candidate_loader_manifest(audit=audit, output_path=output_path, audit_path=audit_path)
    _write_json(output_path, {"rows": rows})
    _write_json(audit_path, audit.to_dict())
    _write_json(manifest_path, manifest.to_dict())
    return {"rows": output_path, "audit": audit_path, "manifest": manifest_path}


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=True, indent=2, sort_keys=True) + "\n", encoding="utf-8")
