from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

import pandas as pd

from .adapters import (
    build_candidate_dataset_from_phase4,
    build_candidate_dataset_from_phase4_tables,
    build_opportunity_dataset_from_phase5d,
)
from .bundle import DatasetBundleWriter, FailureArtifactWriter
from .cutoff import LabelSafeCutoff
from .source_authority import SourceAuthorityBundle, stable_identity_ref
from .validators import validate_dataset_bundle_inputs, validation_status


Component = Literal["Candidate", "Opportunity"]


@dataclass(frozen=True)
class DatasetRebuildRequest:
    component: Component
    final_dir: Path
    source_authority: SourceAuthorityBundle
    cutoff: LabelSafeCutoff
    normalized_quotes: pd.DataFrame | None = None
    feature_frame: pd.DataFrame | None = None
    label_frame: pd.DataFrame | None = None
    candidate_frame: pd.DataFrame | None = None
    candidate_dataset_identity: dict[str, Any] | None = None
    created_at: str = "2026-07-17T00:00:00+00:00"
    failure_report_dir: Path = Path("reports/phase18_b_common_pit_dataset_rebuild_pipeline_implementation/failures")


def rebuild_common_pit_dataset(request: DatasetRebuildRequest) -> dict[str, Any]:
    writer = DatasetBundleWriter(final_dir=request.final_dir)
    failure_writer = FailureArtifactWriter(report_dir=request.failure_report_dir)
    try:
        if request.component == "Candidate":
            if request.feature_frame is not None and request.label_frame is not None:
                adapter_result = build_candidate_dataset_from_phase4_tables(
                    feature_frame=request.feature_frame,
                    label_frame=request.label_frame,
                    label_safe_cutoff=request.cutoff.label_safe_cutoff,
                    created_at=request.created_at,
                )
            else:
                if request.normalized_quotes is None:
                    raise ValueError("Candidate rebuild requires normalized_quotes or feature_frame+label_frame")
                adapter_result = build_candidate_dataset_from_phase4(
                    normalized_quotes=request.normalized_quotes,
                    label_safe_cutoff=request.cutoff.label_safe_cutoff,
                    source_snapshot_id="phase18b:source_authority",
                    created_at=request.created_at,
                )
            uniqueness_keys = ["target_date", "code"]
        elif request.component == "Opportunity":
            if request.candidate_frame is None or request.feature_frame is None or request.label_frame is None:
                raise ValueError("Opportunity rebuild requires candidate_frame, feature_frame, and label_frame")
            candidate_source_ref = _candidate_source_ref(request.candidate_dataset_identity)
            adapter_result = build_opportunity_dataset_from_phase5d(
                candidate_frame=request.candidate_frame,
                feature_frame=request.feature_frame,
                label_frame=request.label_frame,
                label_safe_cutoff=request.cutoff.label_safe_cutoff,
                candidate_source_ref=candidate_source_ref,
                created_at=request.created_at,
            )
            uniqueness_keys = ["target_date", "code", "candidate_source_ref"]
        else:
            raise ValueError(f"unsupported component: {request.component}")

        validations = validate_dataset_bundle_inputs(
            component=request.component,
            dataset=adapter_result.dataset,
            feature_columns=adapter_result.feature_columns,
            label_columns=adapter_result.label_columns,
            uniqueness_keys=uniqueness_keys,
            cutoff=request.cutoff,
            source_authority=request.source_authority,
            adapter_audit=adapter_result.adapter_audit,
        )
        if validation_status(validations) != "PASS":
            failed = [result.to_dict() for result in validations if result.status != "PASS"]
            raise ValueError(f"validation failed: {failed}")

        bundle = writer.write_and_publish(
            component=request.component,
            dataset=adapter_result.dataset,
            feature_columns=adapter_result.feature_columns,
            label_columns=adapter_result.label_columns,
            uniqueness_keys=uniqueness_keys,
            cutoff=request.cutoff,
            source_authority=request.source_authority,
            validations=validations,
            adapter_summary=adapter_result.adapter_summary,
            created_at=request.created_at,
        )
        return {
            "status": "PASS",
            "component": request.component,
            "final_dir": str(bundle.final_dir),
            "hash_manifest": bundle.hash_manifest,
            "validations": [result.to_dict() for result in validations],
            "files": bundle.files,
        }
    except Exception as exc:
        failure_path = failure_writer.write(
            component=request.component,
            stage="rebuild",
            error=str(exc),
            final_dir=request.final_dir,
            temp_dir=request.final_dir.parent / f".{request.final_dir.name}.tmp",
        )
        return {
            "status": "FAIL",
            "component": request.component,
            "final_dir": str(request.final_dir),
            "failure_artifact": str(failure_path),
            "error": str(exc),
        }


def _candidate_source_ref(identity: dict[str, Any] | None) -> str:
    identity = identity or {}
    explicit = str(identity.get("candidate_source_ref") or "")
    if explicit:
        if "/" in explicit or "\\" in explicit:
            raise ValueError("candidate_source_ref must not be path-like")
        return explicit
    return stable_identity_ref(
        component="candidate",
        dataset_hash=str(identity.get("dataset_hash") or ""),
        dataset_version=str(identity.get("dataset_version") or "unknown"),
    )
