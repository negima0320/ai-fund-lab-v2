#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from ai_fund_lab_v2.capital_allocation_ai.audit import run_phase7a_capital_allocation_audit  # noqa: E402
from ai_fund_lab_v2.capital_allocation_ai.engine import (  # noqa: E402
    AUDIT_FILENAME,
    DECISION_CSV_FILENAME,
    DEFAULT_OUTPUT_DIR,
    SUMMARY_FILENAME,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Audit Phase7-A Capital Allocation Engine dry-run outputs.")
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    args = parser.parse_args(argv)
    output_dir = Path(args.output_dir)
    audit = run_phase7a_capital_allocation_audit(
        summary_path=output_dir / SUMMARY_FILENAME,
        audit_path=output_dir / AUDIT_FILENAME,
        output_path=output_dir / DECISION_CSV_FILENAME,
    )
    print(json.dumps(audit, ensure_ascii=True, indent=2, sort_keys=True))
    return 0 if audit.get("completion_status") == "PHASE7A_CAPITAL_ALLOCATION_ENGINE_READY" else 1


if __name__ == "__main__":
    raise SystemExit(main())
