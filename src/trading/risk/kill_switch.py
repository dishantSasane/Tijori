"""Kill switch: manual + automatic, global/sleeve/instance scoped.

docs/RISK_SPEC.md §4, §8; docs/specs/RISK_ENGINE_SPEC.md §8. Backed by
`trading.storage.state_store.StateStore` so engagement survives a restart
(invariant I12-adjacent: a kill switch that only lives in memory is useless).
Resuming is a *separate* call (`disengage`), never reachable from the normal
check()/route() path (invariant I10: relax only by explicit human action).
"""

from __future__ import annotations

from dataclasses import dataclass

from trading.core.clock import Clock
from trading.storage.state_store import StateStore

KillScope = str  # "global" | f"sleeve:{name}" | f"instance:{strategy_id}:{market}"

GLOBAL_SCOPE: KillScope = "global"


def sleeve_scope(sleeve: str) -> KillScope:
    return f"sleeve:{sleeve}"


def instance_scope(strategy_id: str, market: str) -> KillScope:
    return f"instance:{strategy_id}:{market}"


@dataclass(frozen=True)
class KillState:
    engaged: bool
    reason: str | None
    actor: str | None


class KillSwitch:
    """Thin wrapper over `StateStore`'s `kill_switch_state`/`audit_log` tables."""

    def __init__(self, store: StateStore, *, clock: Clock) -> None:
        self._store = store
        self._clock = clock

    def engage(self, scope: KillScope, reason: str, *, actor: str = "system") -> None:
        now = self._clock.now()
        self._store.set_kill_switch(scope, engaged=True, reason=reason, ts=now)
        self._store.write_audit(
            event_type="kill_switch_engaged",
            actor=actor,
            payload={"scope": scope, "reason": reason},
            ts=now,
        )

    def disengage(self, scope: KillScope, *, actor: str) -> None:
        """Explicit human action only (I10) — never called from `check()`/`route()`."""
        now = self._clock.now()
        self._store.set_kill_switch(scope, engaged=False, reason=None, ts=now)
        self._store.write_audit(
            event_type="kill_switch_released",
            actor=actor,
            payload={"scope": scope},
            ts=now,
        )

    def is_engaged(self, scope: KillScope) -> bool:
        return self._store.get_kill_switch(scope)

    def any_engaged(self, scopes: tuple[KillScope, ...]) -> KillScope | None:
        """First engaged scope in the given order (check 1: global, sleeve, instance)."""
        for scope in scopes:
            if self.is_engaged(scope):
                return scope
        return None
