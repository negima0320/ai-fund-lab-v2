#!/usr/bin/env python3
"""Run Phase19-AT latest J-Quants dataset-to-runtime E2E validation."""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(".").resolve()))

from ai_fund_lab_v2.ai_lifecycle.at_latest_jquants_e2e_validation import run_phase19_at_validation


def main() -> int:
    result = run_phase19_at_validation(repo_root=Path("."))
    print(json.dumps(result.final_judgment, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
