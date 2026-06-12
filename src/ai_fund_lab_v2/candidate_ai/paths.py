from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from ai_fund_lab_v2.runtime import RuntimePaths


@dataclass(frozen=True)
class CandidateAIRuntimePaths:
    runtime_paths: RuntimePaths

    @property
    def candidate_ai_root(self) -> Path:
        return self.runtime_paths.runtime_dir / "candidate_ai"

    @property
    def features(self) -> Path:
        return self.candidate_ai_root / "features"

    @property
    def manifests(self) -> Path:
        return self.candidate_ai_root / "manifests"

    @property
    def audit(self) -> Path:
        return self.candidate_ai_root / "audit"

    @property
    def reports(self) -> Path:
        return self.candidate_ai_root / "reports"

    @property
    def tmp(self) -> Path:
        return self.candidate_ai_root / "tmp"

    def iter_dirs(self) -> tuple[Path, ...]:
        return (
            self.candidate_ai_root,
            self.features,
            self.manifests,
            self.audit,
            self.reports,
            self.tmp,
        )

    def ensure_dirs(self) -> None:
        for path in self.iter_dirs():
            path.mkdir(parents=True, exist_ok=True)
