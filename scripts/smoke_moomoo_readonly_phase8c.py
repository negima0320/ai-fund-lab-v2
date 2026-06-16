from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from ai_fund_lab_v2.broker.moomoo.readonly_smoke import run_moomoo_readonly_smoke


def main() -> int:
    parser = argparse.ArgumentParser(description="Phase8-C moomoo read-only smoke runner.")
    parser.add_argument("--runtime-dir", default=".runtime")
    parser.add_argument("--reports-dir", default="reports/phase_reports")
    parser.add_argument("--run-readonly-smoke", action="store_true")
    parser.add_argument("--continue-on-readonly-failure", action="store_true")
    parser.add_argument("--trd-env", choices=("SIMULATE", "REAL"), default="SIMULATE")
    args = parser.parse_args()

    env_enabled = os.environ.get("AI_FUND_LAB_MOOMOO_READONLY_SMOKE") == "1"
    smoke_env = dict(os.environ)
    smoke_env["AI_FUND_LAB_MOOMOO_ENV"] = args.trd_env
    result = run_moomoo_readonly_smoke(
        runtime_dir=Path(args.runtime_dir),
        reports_dir=Path(args.reports_dir),
        run_enabled=bool(args.run_readonly_smoke and env_enabled),
        env=smoke_env,
        continue_on_failure=bool(args.continue_on_readonly_failure),
    )
    print(
        json.dumps(
            {
                "status": result.status,
                "executed": result.executed,
                "report_path": str(result.report_path),
                "counts": result.counts or {},
                "message": result.message,
            },
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
