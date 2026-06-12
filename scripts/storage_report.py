#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from ai_fund_lab_v2.config import load_settings


def main() -> int:
    parser = argparse.ArgumentParser(description="Show AI Fund Lab runtime storage usage.")
    parser.add_argument("--runtime-dir", type=Path, help="Override AI_FUND_LAB_RUNTIME_DIR for this report.")
    args = parser.parse_args()

    settings = load_settings()
    paths = settings.runtime_paths
    if args.runtime_dir:
        paths = type(paths)(runtime_dir=args.runtime_dir)

    rows = [
        ("data/raw", paths.raw_data),
        ("data/raw_norm", paths.raw_normalized_data),
        ("data/features", paths.feature_data),
        ("data/labels", paths.label_data),
        ("logs", paths.logs),
        ("cache", paths.cache),
        ("reports", paths.reports),
        ("tmp", paths.tmp),
    ]

    print("AI Fund Lab runtime storage report")
    print(f"runtime_dir: {paths.runtime_dir}")
    total = 0
    for label, path in rows:
        size = directory_size(path)
        total += size
        print(f"{label:14} {format_bytes(size):>10}  {path}")
    print(f"{'total':14} {format_bytes(total):>10}")
    return 0


def directory_size(path: Path) -> int:
    if not path.exists():
        return 0
    if path.is_file():
        return path.stat().st_size
    return sum(item.stat().st_size for item in path.rglob("*") if item.is_file())


def format_bytes(size: int) -> str:
    units = ("B", "KB", "MB", "GB", "TB")
    value = float(size)
    for unit in units:
        if value < 1024 or unit == units[-1]:
            return f"{value:.1f}{unit}"
        value /= 1024
    return f"{size}B"


if __name__ == "__main__":
    raise SystemExit(main())
