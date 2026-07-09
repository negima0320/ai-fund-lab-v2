"""Generate Runtime v2 Markdown/Public reports for Phase14-E6.

This script reads only canonical Runtime v2 Current paths and writes derived
report artifacts. It does not call Broker APIs, submit orders, send
notifications, or touch launchd/plist files.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from ai_fund_lab_v2.runtime_v2.report.public_report_writer import (
    generate_public_report_from_current,
)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--runtime-root", default=".runtime")
    parser.add_argument("--business-date", required=True)
    parser.add_argument("--runtime-output-root", default="reports/runtime_v2")
    parser.add_argument("--public-output-root", default="reports/public/runtime_v2")
    args = parser.parse_args()

    business_date = args.business_date
    runtime_output_dir = Path(args.runtime_output_root) / business_date
    public_output_dir = Path(args.public_output_root) / business_date

    result = generate_public_report_from_current(
        runtime_root=Path(args.runtime_root),
        runtime_output_dir=runtime_output_dir,
        public_output_dir=public_output_dir,
        business_date=business_date,
        write_latest=True,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if result["redaction_scan"]["passed"] else 20


if __name__ == "__main__":
    raise SystemExit(main())
