from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import pytest

from ai_fund_lab_v2.ai_lifecycle.training_pipeline import transform_features
from ai_fund_lab_v2.runtime_v2.accepted_generation_resolver import resolve_accepted_generation
from ai_fund_lab_v2.runtime_v2.buy_ai.generation_bound_inference import (
    GenerationBoundInferenceError,
    generation_bound_matrix,
    load_generation_bound_binding,
    predict_generation_bound_scores,
)
from ai_fund_lab_v2.runtime_v2.buy_ai.producer import produce_buy_ai_decisions


RUNTIME_ROOT = Path(".runtime")
FEATURE_ROOT = Path(".runtime/operations/feature_artifacts")
FEATURE_DATE = "2026-07-14"


def test_phase19_br_opportunity_runtime_inference_matches_generation_bound_reference() -> None:
    _require_real_generation()
    resolution = resolve_accepted_generation(RUNTIME_ROOT)
    binding = load_generation_bound_binding(resolution=resolution, component="opportunity", repo_root=Path("."))
    frame = _opportunity_frame()

    observed = predict_generation_bound_scores(binding, frame)

    raw = transform_features(frame, list(binding.feature_order), binding.model_payload["preprocessing"])
    expected_matrix = np.array(raw, dtype=np.float64, copy=True)
    index_by_feature = {feature: idx for idx, feature in enumerate(binding.scaler_payload["input_feature_columns"])}
    scaled_indices = [index_by_feature[column] for column in binding.scaler_payload["scaled_feature_columns"]]
    expected_matrix[:, scaled_indices] = binding.scaler_payload["scaler"].transform(expected_matrix[:, scaled_indices])
    expected = binding.model_payload["model"].predict(expected_matrix)

    assert np.allclose(observed, expected)
    assert float(np.nanmax(np.abs(observed))) < 2.0


def test_phase19_br_missing_scaler_fails_closed(tmp_path: Path) -> None:
    manifest_path = _mutated_manifest(tmp_path, lambda payload: payload["opportunity_member"].update({"scaler_file": ""}))
    resolution = _resolution_for_manifest(manifest_path)

    with pytest.raises(GenerationBoundInferenceError) as exc:
        load_generation_bound_binding(resolution=resolution, component="opportunity", repo_root=Path("."))

    assert exc.value.reason_code == "missing_scaler"


def test_phase19_br_scaler_hash_mismatch_fails_closed(tmp_path: Path) -> None:
    manifest_path = _mutated_manifest(
        tmp_path,
        lambda payload: payload["opportunity_member"].update({"scaler_hash": "0" * 64}),
    )
    resolution = _resolution_for_manifest(manifest_path)

    with pytest.raises(GenerationBoundInferenceError) as exc:
        load_generation_bound_binding(resolution=resolution, component="opportunity", repo_root=Path("."))

    assert exc.value.reason_code in {"member_hash_mismatch", "scaler_hash_mismatch"}


def test_phase19_br_feature_order_mismatch_fails_closed() -> None:
    _require_real_generation()
    resolution = resolve_accepted_generation(RUNTIME_ROOT)
    binding = load_generation_bound_binding(resolution=resolution, component="opportunity", repo_root=Path("."))
    frame = _opportunity_frame().drop(columns=[binding.feature_order[0]])

    with pytest.raises(GenerationBoundInferenceError) as exc:
        generation_bound_matrix(binding, frame)

    assert exc.value.reason_code == "feature_order_mismatch"


def test_phase19_br_runtime_producer_uses_generation_bound_scaler_without_legacy_fallback(tmp_path: Path) -> None:
    _require_real_generation()
    runtime_root = _runtime_root_with_pointer(tmp_path / "runtime")

    result = produce_buy_ai_decisions(
        runtime_root=runtime_root,
        business_date="2099-01-02",
        feature_root=FEATURE_ROOT,
        feature_date=FEATURE_DATE,
        selected_rank_limit=5,
    )

    payload = json.loads(Path(result.opportunity_artifact_path).read_text(encoding="utf-8"))
    scores = [float(row["expected_edge_score"]) for row in payload["rankings"]]
    assert result.status == "PASS"
    assert payload["transformation_stage"] == "accepted_generation_bound_imputer_scaler_model"
    assert payload["legacy_fallback_used"] is False
    assert payload["generation_bound_inference"]["scaler_hash"] == _manifest()["opportunity_member"]["scaler_hash"]
    assert max(scores) < 2.0


def test_phase19_br_historical_demo_production_share_same_inference_logic(tmp_path: Path) -> None:
    _require_real_generation()
    distributions: list[tuple[float, float, float]] = []
    for mode in ("historical_mode", "demo_mode", "production_mode"):
        runtime_root = _runtime_root_with_pointer(tmp_path / mode / ".runtime")
        result = produce_buy_ai_decisions(
            runtime_root=runtime_root,
            business_date="2099-01-03",
            feature_root=FEATURE_ROOT,
            feature_date=FEATURE_DATE,
            selected_rank_limit=5,
        )
        payload = json.loads(Path(result.opportunity_artifact_path).read_text(encoding="utf-8"))
        scores = [float(row["expected_edge_score"]) for row in payload["rankings"]]
        distributions.append((min(scores), float(np.median(scores)), max(scores)))
        assert payload["generation_bound_inference"]["preprocessing_contract"] == (
            "model_payload_preprocessing_then_generation_bound_standard_scaler"
        )

    assert distributions[0] == distributions[1] == distributions[2]


def _opportunity_frame() -> pd.DataFrame:
    from ai_fund_lab_v2.opportunity_ai.inference import build_inference_feature_frame

    candidate = pd.DataFrame(
        [
            {
                "target_date": FEATURE_DATE,
                "code": "10010",
                "candidate_score": 0.8,
                "candidate_rank": 1,
                "candidate_reason": "fixture",
            },
            {
                "target_date": FEATURE_DATE,
                "code": "10020",
                "candidate_score": 0.5,
                "candidate_rank": 2,
                "candidate_reason": "fixture",
            },
        ]
    )
    feature = pd.read_parquet(FEATURE_ROOT / FEATURE_DATE / "opportunity_feature_input.parquet")
    feature = feature[feature["target_date"].astype(str) == FEATURE_DATE].head(2).copy()
    feature["code"] = ["10010", "10020"]
    return build_inference_feature_frame(candidate_frame=candidate, feature_frame=feature)


def _require_real_generation() -> None:
    if not (RUNTIME_ROOT / "runtime_state" / "accepted_buy_ai_bundle.json").is_file():
        pytest.skip("Accepted Generation runtime pointer is not available")
    if not (FEATURE_ROOT / FEATURE_DATE / "opportunity_feature_input.parquet").is_file():
        pytest.skip("Runtime feature artifacts are not available")


def _manifest() -> dict[str, Any]:
    _require_real_generation()
    resolution = resolve_accepted_generation(RUNTIME_ROOT)
    return json.loads(Path(resolution.bundle_manifest_path).read_text(encoding="utf-8"))


def _mutated_manifest(tmp_path: Path, mutate: Any) -> Path:
    payload = _manifest()
    for member_name in ("candidate_member", "opportunity_member"):
        member = payload[member_name]
        for key in ("model_file", "scaler_file"):
            if member.get(key):
                member[key] = str(Path(member[key]).resolve())
    mutate(payload)
    payload["aggregate_hash"] = _stable_hash(
        {key: value for key, value in payload.items() if key not in {"aggregate_hash", "manifest_hash"}}
    )
    path = tmp_path / "accepted_generation_manifest.json"
    path.write_text(json.dumps(payload, sort_keys=True), encoding="utf-8")
    return path


def _resolution_for_manifest(manifest_path: Path):
    runtime_root = manifest_path.parent / ".runtime"
    _write_pointer(runtime_root, manifest_path, json.loads(manifest_path.read_text(encoding="utf-8"))["aggregate_hash"])
    resolution = resolve_accepted_generation(runtime_root)
    assert resolution.is_resolved
    return resolution


def _runtime_root_with_pointer(runtime_root: Path) -> Path:
    manifest_path = Path(resolve_accepted_generation(RUNTIME_ROOT).bundle_manifest_path).resolve()
    _write_pointer(runtime_root, manifest_path, _manifest()["aggregate_hash"])
    return runtime_root


def _write_pointer(runtime_root: Path, manifest_path: Path, aggregate_hash: str) -> None:
    pointer_path = runtime_root / "runtime_state" / "accepted_buy_ai_bundle.json"
    pointer_path.parent.mkdir(parents=True, exist_ok=True)
    pointer_path.write_text(
        json.dumps(
            {
                "transaction_state": "COMMITTED",
                "bundle_manifest_path": str(manifest_path),
                "aggregate_hash": aggregate_hash,
            },
            sort_keys=True,
        ),
        encoding="utf-8",
    )


def _stable_hash(payload: Any) -> str:
    return __import__("hashlib").sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True, default=str).encode("utf-8")
    ).hexdigest()
