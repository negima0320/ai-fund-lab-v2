import json
from pathlib import Path

from ai_fund_lab_v2.runtime_v2.current_state.reader import read_current_state


def test_reader_does_not_look_into_order_plan_date_directory(tmp_path):
    _write_json(
        tmp_path / "order_plan/2026-07-07/runtime_state.json",
        _runtime_state_payload(),
    )

    result = read_current_state(
        mode="demo",
        environment="demo",
        object_type="runtime_state",
        base_dir=tmp_path,
    )

    assert result.classification == "MISSING"
    assert result.path == tmp_path / ".runtime/runtime_state/current_state.json"


def test_reader_does_not_look_into_approval_artifact_date_directory(tmp_path):
    _write_json(
        tmp_path / "approval_artifact/2026-07-07/current_state.json",
        _runtime_state_payload(),
    )

    result = read_current_state(
        mode="demo",
        environment="demo",
        object_type="runtime_state",
        base_dir=tmp_path,
    )

    assert result.classification == "MISSING"


def test_reader_does_not_look_into_reports_date_directory(tmp_path):
    _write_json(
        tmp_path / "reports/2026-07-07/current_state.json",
        _runtime_state_payload(),
    )

    result = read_current_state(
        mode="demo",
        environment="demo",
        object_type="runtime_state",
        base_dir=tmp_path,
    )

    assert result.classification == "MISSING"


def test_reader_does_not_look_into_phase13_directories(tmp_path):
    _write_json(
        tmp_path / "phase13/runtime_state/current_state.json",
        _runtime_state_payload(),
    )

    result = read_current_state(
        mode="demo",
        environment="demo",
        object_type="runtime_state",
        base_dir=tmp_path,
    )

    assert result.classification == "MISSING"


def test_reader_uses_current_path_when_it_exists_even_if_history_exists(tmp_path):
    _write_json(
        tmp_path / "order_plan/2026-07-07/current_state.json",
        {**_runtime_state_payload(), "state": "HISTORY_SHOULD_NOT_WIN"},
    )
    _write_json(
        tmp_path / ".runtime/runtime_state/current_state.json",
        _runtime_state_payload(),
    )

    result = read_current_state(
        mode="demo",
        environment="demo",
        object_type="runtime_state",
        base_dir=tmp_path,
    )

    assert result.classification == "VALID"
    assert result.payload["state"] == "IDLE"


def test_current_state_reader_does_not_import_legacy_runtime_resolver():
    source = Path("src/ai_fund_lab_v2/runtime_v2/current_state/reader.py").read_text(
        encoding="utf-8"
    )

    assert "resolve_latest_order_plan" not in source
    assert "resolve_current_from_date_dir" not in source
    assert "resolve_current_from_phase_dir" not in source
    assert "from ai_fund_lab_v2.runtime " not in source
    assert "from ai_fund_lab_v2.runtime." not in source
    assert "import ai_fund_lab_v2.runtime" not in source
    assert "from ai_fund_lab_v2.operations " not in source
    assert "from ai_fund_lab_v2.operations." not in source
    assert "import ai_fund_lab_v2.operations" not in source


def _runtime_state_payload():
    return {
        "schema_version": "1",
        "runtime_id": "runtime-demo",
        "run_id": "run-1",
        "state": "IDLE",
        "environment": "demo",
        "updated_at": "2026-07-07T00:00:00Z",
    }


def _write_json(path: Path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")
