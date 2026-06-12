from pathlib import Path

from ai_fund_lab_v2.broker import BrokerRuntimePaths
from ai_fund_lab_v2.runtime import RuntimePaths


def test_broker_runtime_paths_are_under_runtime_broker(tmp_path: Path) -> None:
    runtime = RuntimePaths(runtime_dir=tmp_path / "runtime")
    paths = BrokerRuntimePaths(runtime)

    paths.ensure_dirs()

    assert paths.broker_root == tmp_path / "runtime" / "broker"
    assert paths.balance_snapshots == paths.broker_root / "snapshots" / "balance"
    assert paths.positions_snapshots == paths.broker_root / "snapshots" / "positions"
    assert paths.orders_snapshots == paths.broker_root / "snapshots" / "orders"
    assert paths.logs == paths.broker_root / "logs"
    assert all(path.is_dir() for path in paths.iter_dirs())
    assert all(str(path).startswith(str(tmp_path / "runtime" / "broker")) for path in paths.iter_dirs())
