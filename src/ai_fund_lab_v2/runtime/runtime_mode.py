from __future__ import annotations

from enum import Enum


class RuntimeMode(str, Enum):
    PAPER = "paper"
    DEMO = "demo"
    PRODUCTION = "production"


RuntimeEnvironment = RuntimeMode
