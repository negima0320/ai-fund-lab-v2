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

from ai_fund_lab_v2.candidate_ai import ControlledExecutionFailureInjection, build_full_range_controlled_summary  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Execute one controlled full-range Candidate feature chunk.")
    parser.add_argument("--runtime-dir", default=".runtime")
    parser.add_argument("--report-dir", default="reports/candidate_ai/full_range")
    parser.add_argument("--input-format", choices=("auto", "jsonl", "parquet"), default="auto")
    parser.add_argument("--max-codes-per-chunk", type=int, default=30)
    parser.add_argument("--max-chunks-to-execute", type=int, default=1)
    parser.add_argument("--data-source-type", choices=("mock", "real_runtime", "skipped"), default=None)
    parser.add_argument("--run-id", default=None)
    parser.add_argument("--force-schema-validation-failure", action="store_true")
    parser.add_argument("--force-leakage-audit-failure", action="store_true")
    parser.add_argument("--force-write-failure", action="store_true")
    parser.add_argument("--force-atomic-move-failure", action="store_true")
    args = parser.parse_args(argv)
    failure_injection = ControlledExecutionFailureInjection(
        force_schema_validation_failure=args.force_schema_validation_failure,
        force_leakage_audit_failure=args.force_leakage_audit_failure,
        force_write_failure=args.force_write_failure,
        force_atomic_move_failure=args.force_atomic_move_failure,
    )
    summary = build_full_range_controlled_summary(
        runtime_dir=args.runtime_dir,
        report_dir=args.report_dir,
        input_format=args.input_format,
        max_codes_per_chunk=args.max_codes_per_chunk,
        max_chunks_to_execute=args.max_chunks_to_execute,
        data_source_type=args.data_source_type,
        run_id=args.run_id,
        failure_injection=failure_injection,
    )
    print(json.dumps(summary, ensure_ascii=True, indent=2, sort_keys=True))
    return 0 if summary["status"] in {"OK", "BLOCKED", "SKIPPED"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
