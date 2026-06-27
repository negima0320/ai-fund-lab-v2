from __future__ import annotations

from dataclasses import dataclass, field, replace

from ai_fund_lab_v2.runtime.runtime_context import RuntimeContext


@dataclass(frozen=True)
class RuntimeRunLock:
    runtime_id: str
    business_date: str
    locked: bool = True
    owner: str = "runtime"
    reason: str = ""

    @classmethod
    def acquire(cls, context: RuntimeContext, *, owner: str = "runtime", reason: str = "") -> "RuntimeRunLock":
        return cls(runtime_id=context.runtime_id, business_date=context.business_date, owner=owner, reason=reason)

    def release(self) -> "RuntimeRunLock":
        return replace(self, locked=False)

    def conflicts_with(self, context: RuntimeContext) -> bool:
        return self.locked and self.business_date == context.business_date and self.runtime_id != context.runtime_id

    def to_dict(self) -> dict[str, object]:
        return {
            "runtime_id": self.runtime_id,
            "business_date": self.business_date,
            "locked": self.locked,
            "owner": self.owner,
            "reason": self.reason,
        }


@dataclass
class InMemoryRunLockStore:
    current_lock: RuntimeRunLock | None = field(default=None)

    def acquire(self, context: RuntimeContext, *, owner: str = "runtime", reason: str = "") -> RuntimeRunLock:
        if self.current_lock and self.current_lock.conflicts_with(context):
            raise RuntimeError("runtime_run_lock_conflict")
        self.current_lock = RuntimeRunLock.acquire(context, owner=owner, reason=reason)
        return self.current_lock

    def release(self, context: RuntimeContext) -> RuntimeRunLock:
        if not self.current_lock or self.current_lock.runtime_id != context.runtime_id:
            raise RuntimeError("runtime_run_lock_not_owned")
        self.current_lock = self.current_lock.release()
        return self.current_lock
