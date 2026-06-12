from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from ai_fund_lab_v2.candidate_ai import (  # noqa: E402
    DEFAULT_MOCK_AS_OF_DATE,
    build_candidate_features_mock_with_audit,
    build_mock_daily_quotes_normalized,
    write_candidate_feature_outputs,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build Phase4-E mock Candidate AI features.")
    parser.add_argument("--runtime-dir", default=".runtime", help="Runtime directory for generated artifacts.")
    parser.add_argument("--as-of-date", default=DEFAULT_MOCK_AS_OF_DATE, help="Feature observation date.")
    parser.add_argument("--target-date", default=None, help="Candidate target date. Defaults to as-of-date.")
    args = parser.parse_args(argv)

    source_rows = build_mock_daily_quotes_normalized(as_of_date=args.as_of_date)
    result = build_candidate_features_mock_with_audit(
        source_rows,
        as_of_date=args.as_of_date,
        target_date=args.target_date,
    )
    output_paths = write_candidate_feature_outputs(result.rows, audit=result.audit, runtime_dir=args.runtime_dir)
    summary = {
        "status": result.audit.status,
        "row_count": result.audit.row_count,
        "eligible_count": result.audit.eligible_count,
        "excluded_count": result.audit.excluded_count,
        "forbidden_feature_detected": result.audit.forbidden_feature_detected,
        "features_path": str(output_paths["features"]),
        "manifest_path": str(output_paths["manifest"]),
        "audit_path": str(output_paths["audit"]),
    }
    print(json.dumps(summary, ensure_ascii=True, indent=2, sort_keys=True))
    return 0 if result.validation.is_valid and result.audit.status == "OK" else 1


if __name__ == "__main__":
    raise SystemExit(main())
