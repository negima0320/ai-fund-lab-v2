from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
SRC_DIR = ROOT_DIR / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from ai_fund_lab_v2.opportunity_ai.completion_audit import audit_phase5_completion


def main() -> None:
    parser = argparse.ArgumentParser(description="Run Phase5-L Opportunity AI completion audit.")
    parser.add_argument("--phase-reports-dir", type=Path, default=Path("docs/phase_reports"))
    parser.add_argument("--ai-design-dir", type=Path, default=Path("docs/03_ai_design"))
    parser.add_argument("--requirements-dir", type=Path, default=Path("docs/01_requirements"))
    parser.add_argument("--opportunity-reports-dir", type=Path, default=Path("reports/opportunity_ai"))
    parser.add_argument("--output-dir", type=Path, default=Path("reports/opportunity_ai/phase5l"))
    args = parser.parse_args()

    result = audit_phase5_completion(
        phase_reports_dir=args.phase_reports_dir,
        ai_design_dir=args.ai_design_dir,
        requirements_dir=args.requirements_dir,
        opportunity_reports_dir=args.opportunity_reports_dir,
        output_dir=args.output_dir,
    )
    print(f"readiness_status={result.summary['readiness_status']}")
    print(f"promotion_ready={result.summary['promotion_ready']}")
    print(f"phase5_complete={result.summary['phase5_complete']}")


if __name__ == "__main__":
    main()
