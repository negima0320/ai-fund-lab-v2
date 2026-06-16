from pathlib import Path

import pytest

from ai_fund_lab_v2.paper_trading.run_lock import RunLockError, acquire_run_lock, force_release_run_lock, read_run_lock, release_run_lock


def test_run_lock_blocks_duplicate_and_releases(tmp_path: Path) -> None:
    root = tmp_path / "operation"
    lock = acquire_run_lock(run_id="run1", run_date="2026-06-17", mode="dry-run", operation_root=root)
    assert read_run_lock(root) == lock
    with pytest.raises(RunLockError):
        acquire_run_lock(run_id="run2", run_date="2026-06-17", mode="dry-run", operation_root=root)
    assert release_run_lock(run_id="run1", operation_root=root) is True
    assert read_run_lock(root) is None


def test_force_unlock_replaces_existing_lock(tmp_path: Path) -> None:
    root = tmp_path / "operation"
    acquire_run_lock(run_id="run1", run_date="2026-06-17", mode="dry-run", operation_root=root)
    lock = acquire_run_lock(run_id="run2", run_date="2026-06-17", mode="dry-run", operation_root=root, force_unlock=True)
    assert lock.run_id == "run2"
    assert force_release_run_lock(root) is True

