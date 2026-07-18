from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import pandas as pd

from scripts.build_phase4bc_long_history_features import build_long_history_feature_frame
from scripts.build_phase4bd_long_history_labels import build_long_history_label_frame
from scripts.build_phase4be_long_history_dataset import audit_dataset_frame, build_long_history_dataset_frame
from ai_fund_lab_v2.opportunity_ai.dataset_builder import build_opportunity_dataset_frame


@dataclass(frozen=True)
class AdapterBuildResult:
    dataset: pd.DataFrame
    feature_columns: list[str]
    label_columns: list[str]
    adapter_summary: dict[str, Any]
    adapter_audit: dict[str, Any]


def build_candidate_dataset_from_phase4(
    *,
    normalized_quotes: pd.DataFrame,
    label_safe_cutoff: str,
    source_snapshot_id: str,
    created_at: str,
) -> AdapterBuildResult:
    features = build_long_history_feature_frame(normalized_quotes, source_snapshot_id=source_snapshot_id)
    labels = build_long_history_label_frame(normalized_quotes, source_snapshot_id=source_snapshot_id)
    features = features[features["target_date"].astype(str) <= label_safe_cutoff].copy()
    labels = labels[labels["target_date"].astype(str) <= label_safe_cutoff].copy()
    dataset, feature_columns, label_columns = build_long_history_dataset_frame(feature_frame=features, label_frame=labels)
    dataset["created_at"] = created_at
    audit = audit_dataset_frame(dataset, feature_columns=feature_columns, label_columns=label_columns)
    return AdapterBuildResult(
        dataset=dataset,
        feature_columns=[f"feature__{column}" for column in feature_columns],
        label_columns=[f"label__{column}" for column in label_columns],
        adapter_summary={
            "adapter": "CandidateAdapter",
            "reused_components": ["Phase4-BC", "Phase4-BD", "Phase4-BE"],
            "feature_row_count": int(len(features)),
            "label_row_count": int(len(labels)),
            "joined_row_count": int(len(dataset)),
            "label_safe_cutoff": label_safe_cutoff,
        },
        adapter_audit=audit,
    )


def build_candidate_dataset_from_phase4_tables(
    *,
    feature_frame: pd.DataFrame,
    label_frame: pd.DataFrame,
    label_safe_cutoff: str,
    created_at: str,
) -> AdapterBuildResult:
    features = feature_frame[feature_frame["target_date"].astype(str) <= label_safe_cutoff].copy()
    labels = label_frame[label_frame["target_date"].astype(str) <= label_safe_cutoff].copy()
    dataset, feature_columns, label_columns = build_long_history_dataset_frame(feature_frame=features, label_frame=labels)
    dataset["created_at"] = created_at
    audit = audit_dataset_frame(dataset, feature_columns=feature_columns, label_columns=label_columns)
    return AdapterBuildResult(
        dataset=dataset,
        feature_columns=[f"feature__{column}" for column in feature_columns],
        label_columns=[f"label__{column}" for column in label_columns],
        adapter_summary={
            "adapter": "CandidateAdapter",
            "reused_components": ["Phase4-BC", "Phase4-BD", "Phase4-BE"],
            "real_artifact_mode": True,
            "feature_row_count": int(len(features)),
            "label_row_count": int(len(labels)),
            "joined_row_count": int(len(dataset)),
            "label_safe_cutoff": label_safe_cutoff,
        },
        adapter_audit=audit,
    )


def build_opportunity_dataset_from_phase5d(
    *,
    candidate_frame: pd.DataFrame,
    feature_frame: pd.DataFrame,
    label_frame: pd.DataFrame,
    label_safe_cutoff: str,
    candidate_source_ref: str,
    created_at: str,
) -> AdapterBuildResult:
    if "/" in candidate_source_ref or "\\" in candidate_source_ref:
        raise ValueError("candidate_source_ref must not be an absolute or path-like reference")
    candidate = _cutoff(candidate_frame, label_safe_cutoff)
    features = _cutoff(feature_frame, label_safe_cutoff)
    labels = _cutoff(label_frame, label_safe_cutoff)
    result = build_opportunity_dataset_frame(
        candidate_frame=candidate,
        feature_frame=features,
        label_frame=labels,
        created_at=created_at,
    )
    dataset = result.dataset.copy()
    dataset.insert(3, "candidate_source_ref", candidate_source_ref)
    feature_columns = sorted(column for column in dataset.columns if column.startswith("feature__"))
    label_columns = sorted(column for column in dataset.columns if column.startswith("label__"))
    return AdapterBuildResult(
        dataset=dataset,
        feature_columns=feature_columns,
        label_columns=label_columns,
        adapter_summary={
            **result.summary,
            "adapter": "OpportunityAdapter",
            "reused_components": ["Phase5-D", "Phase5P 32-feature contract"],
            "candidate_source_ref": candidate_source_ref,
            "label_safe_cutoff": label_safe_cutoff,
        },
        adapter_audit=result.audit,
    )


def _cutoff(frame: pd.DataFrame, label_safe_cutoff: str) -> pd.DataFrame:
    result = frame.copy()
    result["target_date"] = result["target_date"].astype(str)
    return result[result["target_date"] <= label_safe_cutoff].copy()
