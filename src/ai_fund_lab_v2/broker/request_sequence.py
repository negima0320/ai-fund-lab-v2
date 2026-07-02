from __future__ import annotations

from dataclasses import dataclass


@dataclass
class RequestSequenceManager:
    """Session-scoped Tachibana p_no counter."""

    current_no: int = 0

    def next_no(self) -> int:
        self.current_no += 1
        return self.current_no
