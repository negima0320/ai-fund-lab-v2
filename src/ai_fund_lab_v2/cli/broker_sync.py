from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Callable

from ai_fund_lab_v2.broker.runtime_paths import BrokerRuntimePaths
from ai_fund_lab_v2.broker.sanitizer import sanitize_mapping
from ai_fund_lab_v2.broker.snapshot_writer import BrokerSnapshotWriter
from ai_fund_lab_v2.broker.sync import BrokerSyncRunner, build_mock_broker_sync_runner
from ai_fund_lab_v2.runtime import RuntimePaths


RunnerFactory = Callable[[BrokerSnapshotWriter], BrokerSyncRunner]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run mock-only broker sync for Phase2 Broker Foundation.")
    parser.add_argument("--mode", choices=("mock",), default="mock", help="Only mock mode is supported in Phase2.")
    parser.add_argument("--runtime-dir", default=".runtime", help="Runtime directory for broker snapshots.")
    return parser


def main(argv: list[str] | None = None, runner_factory: RunnerFactory | None = None) -> int:
    args = build_parser().parse_args(argv)
    runtime_paths = RuntimePaths(runtime_dir=Path(args.runtime_dir))
    broker_paths = BrokerRuntimePaths(runtime_paths)
    writer = BrokerSnapshotWriter(broker_paths)
    factory = runner_factory or build_mock_broker_sync_runner
    runner = factory(writer)
    result = runner.run()
    output = sanitize_mapping(result.to_dict())
    print(json.dumps(output, ensure_ascii=True, sort_keys=True))
    return 0 if result.status == "success" else 1


if __name__ == "__main__":
    raise SystemExit(main())
