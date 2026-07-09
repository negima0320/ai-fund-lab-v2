import pytest

from ai_fund_lab_v2.runtime_v2.pending.reader import read_pending_order_plan
from ai_fund_lab_v2.runtime_v2.pending.writer import (
    pending_order_plan_to_payload,
    write_pending_order_plan,
)

from tests.runtime_v2.pending_fixtures import make_pending_plan


def test_writer_writes_explicit_path(tmp_path):
    path = tmp_path / ".runtime/pending_order_plan/pending_order_plan.json"
    plan = make_pending_plan()

    written = write_pending_order_plan(path, plan)

    assert written == path
    assert path.exists()


def test_writer_keeps_raw_flags_false():
    payload = pending_order_plan_to_payload(make_pending_plan())

    assert payload["raw_request_saved"] is False
    assert payload["raw_response_saved"] is False
    assert payload["secret_saved"] is False


def test_reader_reads_fixed_pending_order_plan_path(tmp_path):
    path = tmp_path / ".runtime/pending_order_plan/pending_order_plan.json"
    plan = make_pending_plan()
    write_pending_order_plan(path, plan)

    result = read_pending_order_plan(
        mode="demo",
        environment="demo",
        base_dir=tmp_path,
    )

    assert result.classification == "VALID"
    assert result.plan.pending_plan_id == plan.pending_plan_id
    assert result.path == path


def test_missing_returns_missing(tmp_path):
    result = read_pending_order_plan(
        mode="demo",
        environment="demo",
        base_dir=tmp_path,
    )

    assert result.classification == "MISSING"
    assert result.exists is False


def test_reader_does_not_use_default_production_fallback(tmp_path):
    with pytest.raises(TypeError):
        read_pending_order_plan(environment="demo", base_dir=tmp_path)
