from ai_fund_lab_v2.runtime_v2.pending.reader import read_pending_order_plan
from ai_fund_lab_v2.runtime_v2.pending.writer import write_pending_order_plan
from tests.runtime_v2.pending_fixtures import make_pending_plan


def test_reader_does_not_read_order_plan_date_directory(tmp_path):
    write_pending_order_plan(
        tmp_path / "order_plan/2026-07-07/pending_order_plan.json",
        make_pending_plan(),
    )

    result = read_pending_order_plan(mode="demo", environment="demo", base_dir=tmp_path)

    assert result.classification == "MISSING"
    assert result.path == tmp_path / ".runtime/demo/pending_order_plan/pending_order_plan.json"


def test_reader_does_not_read_approval_artifact_date_directory(tmp_path):
    write_pending_order_plan(
        tmp_path / "approval_artifact/2026-07-07/pending_order_plan.json",
        make_pending_plan(),
    )

    result = read_pending_order_plan(mode="demo", environment="demo", base_dir=tmp_path)

    assert result.classification == "MISSING"


def test_reader_uses_current_pending_path_when_history_exists(tmp_path):
    write_pending_order_plan(
        tmp_path / "order_plan/2026-07-07/pending_order_plan.json",
        make_pending_plan(pending_plan_id="history-plan"),
    )
    write_pending_order_plan(
        tmp_path / ".runtime/demo/pending_order_plan/pending_order_plan.json",
        make_pending_plan(pending_plan_id="current-plan"),
    )

    result = read_pending_order_plan(mode="demo", environment="demo", base_dir=tmp_path)

    assert result.classification == "VALID"
    assert result.plan.pending_plan_id == "current-plan"

