from pathlib import Path

import pytest

from ai_fund_lab_v2.paper_trading.run_manifest import DailyRunManifest, load_daily_run_manifest, write_daily_run_manifest


def test_daily_run_manifest_writes_and_loads(tmp_path: Path) -> None:
    manifest = DailyRunManifest(
        run_date="2026-06-16",
        data_until="2026-06-16",
        train_until="2026-06-12",
        decision_for="2026-06-16",
        virtual_order_date="2026-06-17",
        virtual_execution_date="2026-06-17",
        safety_status="OK",
        human_review_status="pending",
        report_status="OK",
        warnings=("late_data",),
    )

    path = write_daily_run_manifest(manifest, tmp_path / ".runtime")
    loaded = load_daily_run_manifest(path)

    assert path.exists()
    assert loaded.run_id == manifest.run_id
    assert loaded.warnings == ("late_data",)


def test_daily_run_manifest_rejects_broker_order_api_called() -> None:
    with pytest.raises(ValueError, match="broker order APIs"):
        DailyRunManifest(
            run_date="2026-06-16",
            data_until="2026-06-16",
            train_until="2026-06-12",
            decision_for="2026-06-16",
            virtual_order_date="2026-06-17",
            virtual_execution_date="2026-06-17",
            safety_status="OK",
            human_review_status="pending",
            report_status="OK",
            broker_order_api_called=True,
        )

