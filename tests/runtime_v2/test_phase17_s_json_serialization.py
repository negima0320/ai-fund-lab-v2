from __future__ import annotations

import json
from datetime import date, datetime
from enum import Enum
from pathlib import Path

import pytest

from ai_fund_lab_v2.runtime_v2.buy_ai.producer import _write_json
from ai_fund_lab_v2.runtime_v2.cli.run_daily_operation import _historical_safety_manifest_override
from ai_fund_lab_v2.runtime_v2.storage.json_safe import JsonSerializationContractError, to_json_safe


class FixtureEnum(Enum):
    READY = "READY"


class Unsupported:
    pass


def test_phase17s_path_values_are_normalized_at_json_boundary(tmp_path):
    payload = {
        "artifact_path": Path(".runtime/operations/feature_artifacts/2026-07-06/candidate_features.parquet"),
        "generated_at": datetime.fromisoformat("2026-07-06T08:30:00+09:00"),
        "business_date": date.fromisoformat("2026-07-06"),
        "status": FixtureEnum.READY,
        "items": (Path("reports/runtime_tests/run.json"),),
    }

    safe = to_json_safe(payload)

    assert safe["artifact_path"] == ".runtime/operations/feature_artifacts/2026-07-06/candidate_features.parquet"
    assert safe["generated_at"] == "2026-07-06T08:30:00+09:00"
    assert safe["business_date"] == "2026-07-06"
    assert safe["status"] == "READY"
    assert safe["items"] == ["reports/runtime_tests/run.json"]


def test_phase17s_unsupported_type_fails_closed_with_field_path():
    with pytest.raises(JsonSerializationContractError) as exc_info:
        to_json_safe({"candidate_result": {"artifact_path": Unsupported()}})

    assert exc_info.value.field_path == "$.candidate_result.artifact_path"
    assert exc_info.value.python_type == "Unsupported"


def test_phase17s_buy_ai_write_json_normalizes_metrics_path(tmp_path):
    path = tmp_path / "opportunity_rankings.json"

    _write_json(
        path,
        {
            "schema_version": "runtime_v2_opportunity_ranking_v1",
            "metrics_validation": {
                "status": "HALT",
                "metrics_model_path": Path("reports/opportunity_ai/phase5p/models/opportunity_model.pkl"),
            },
        },
    )

    payload = json.loads(path.read_text(encoding="utf-8"))
    assert payload["metrics_validation"]["metrics_model_path"] == "reports/opportunity_ai/phase5p/models/opportunity_model.pkl"


def test_phase17s_historical_safety_summary_uses_data_readiness_authority():
    class Args:
        mode = "historical"

    payload = _historical_safety_manifest_override(
        args=Args(),
        data_readiness_manifest={
            "data_readiness_safety_authority": "historical_initial_no_external_effect",
            "data_readiness_safety_reason": "historical_neutral_no_event_safety_ready",
            "data_readiness_ignored_latest_safety_decision": ".runtime/runtime_state/safety/latest_safety_decision.json",
        },
    )

    assert payload["safety_authority"] == "historical_initial_no_external_effect"
    assert payload["safety_artifact_path"] == ""
    assert payload["safety_decision"] == "NEUTRAL"
    assert payload["ignored_latest_safety_decision"] == ".runtime/runtime_state/safety/latest_safety_decision.json"

