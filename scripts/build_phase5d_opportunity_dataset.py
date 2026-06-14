#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from ai_fund_lab_v2.opportunity_ai.dataset_builder import build_opportunity_dataset  # noqa: E402

PHASE4BG_SUMMARY = Path("reports/candidate_ai/full_range/phase4bg_formal_candidate_inference_summary.json")
PHASE4BE_SUMMARY = Path("reports/candidate_ai/full_range/phase4be_long_history_dataset_rebuild_summary.json")
DEFAULT_OUTPUT_DIR = Path("reports/opportunity_ai/phase5d")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build Phase5-D Opportunity AI dataset from Candidate Top50.")
    parser.add_argument("--candidate-path", default=None)
    parser.add_argument("--feature-path", default=None)
    parser.add_argument("--label-path", default=None)
    parser.add_argument("--phase4bg-summary", default=str(PHASE4BG_SUMMARY))
    parser.add_argument("--phase4be-summary", default=str(PHASE4BE_SUMMARY))
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    args = parser.parse_args(argv)

    phase4bg = _read_json(Path(args.phase4bg_summary))
    phase4be = _read_json(Path(args.phase4be_summary))
    candidate_path = Path(args.candidate_path or phase4bg.get("top50_json_path") or phase4bg.get("candidate_output_path") or "")
    feature_path = Path(args.feature_path or phase4be.get("feature_table_path") or "")
    label_path = Path(args.label_path or phase4be.get("label_table_path") or "")
    summary = build_opportunity_dataset(
        candidate_path=candidate_path,
        feature_path=feature_path,
        label_path=label_path,
        output_dir=Path(args.output_dir),
    )
    print(json.dumps(summary, ensure_ascii=True, indent=2, sort_keys=True))
    return 0 if summary.get("status") in {"OK", "BLOCKED"} else 1


def _read_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    raise SystemExit(main())
