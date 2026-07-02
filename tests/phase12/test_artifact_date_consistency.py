from __future__ import annotations

from pathlib import Path

from ai_fund_lab_v2.operations.io import OperationPaths, write_json
from ai_fund_lab_v2.operations.operations import _artifact_date_consistency


def test_artifact_date_mismatch_requires_review(tmp_path: Path) -> None:
    paths = OperationPaths(tmp_path)
    write_json(paths.dated("approval_artifact", "2026-07-01", "approval_artifact.json"), {"business_date": "2026-06-30", "status": "APPROVED"})

    result = _artifact_date_consistency(paths, "2026-07-01")

    assert result["pass"] is False
    assert any("approval_date=2026-06-30" in item for item in result["mismatches"])


def test_next_morning_submit_previous_business_day_source_is_allowed(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("TACHIBANA_API_ENV", "demo")
    paths = OperationPaths(tmp_path)
    write_json(
        paths.dated("submitted_orders", "2026-07-02", "submitted_orders.json"),
        {
            "business_date": "2026-07-02",
            "submit_run_date": "2026-07-02",
            "order_plan_source_date": "2026-07-01",
            "approval_source_date": "2026-07-01",
            "status": "PASS",
        },
    )

    result = _artifact_date_consistency(paths, "2026-07-02")

    assert result["pass"] is True
