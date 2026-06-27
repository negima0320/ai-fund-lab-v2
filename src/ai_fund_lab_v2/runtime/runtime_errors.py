from __future__ import annotations


class RuntimeStateMachineError(ValueError):
    """Base error for runtime state machine validation failures."""


class UnknownRuntimeStateError(RuntimeStateMachineError):
    """Raised when a state cannot be parsed into a known runtime state."""


class InvalidRuntimeTransitionError(RuntimeStateMachineError):
    """Raised when a requested state transition is not allowed."""


class RuntimeContextError(RuntimeStateMachineError):
    """Raised when runtime context is incomplete or inconsistent."""
