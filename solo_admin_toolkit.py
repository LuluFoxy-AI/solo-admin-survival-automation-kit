from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Union


__all__ = [
    "SoloAdminToolkit",
    "SoloAdminSurvivalAutomationKit",
    "get_toolkit",
]


def _ts() -> str:
    return datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")


def _coerce_when(when: Optional[Union[str, datetime]]) -> str:
    if when is None:
        return _ts()
    if isinstance(when, datetime):
        return when.strftime("%Y-%m-%dT%H:%M:%SZ")
    # assume string; leave as-is to avoid strict parsing dependency
    return str(when)


@dataclass
class SoloAdminToolkit:
    """
    A lightweight, side-effect-free toolkit for solo admin automation scenarios.

    This module intentionally avoids top-level side effects (no prints, no I/O)
    so it is safe to import in test environments.
    """
    maintenance_mode: bool = False
    backups: List[Dict[str, Any]] = field(default_factory=list)
    pending_updates: List[str] = field(default_factory=list)
    logs: List[str] = field(default_factory=list)

    # Internal logging
    def _log(self, event: str, *, meta: Optional[Dict[str, Any]] = None) -> None:
        parts: List[str] = [_ts(), event]
        if meta:
            for k in sorted(meta.keys()):
                parts.append(f"{k}={meta[k]}")
        self.logs.append(" ".join(parts))

    # Maintenance mode controls
    def enable_maintenance(self) -> None:
        if not self.maintenance_mode:
            self.maintenance_mode = True
            self._log("maintenance.enabled")

    def disable_maintenance(self) -> None:
        if self.maintenance_mode:
            self.maintenance_mode = False
            self._log("maintenance.disabled")

    def set_maintenance(self, state: bool) -> None:
        if state:
            self.enable_maintenance()
        else:
            self.disable_maintenance()

    # Backup scheduling
    def schedule_backup(
        self,
        destination: str,
        when: Optional[Union[str, datetime]] = None,
        *,
        label: Optional[str] = None,
        dry_run: bool = False,
    ) -> Dict[str, Any]:
        job = {
            "destination": destination,
            "when": _coerce_when(when),
            "label": label or f"backup-{len(self.backups) + 1}",
            "created_at": _ts(),
            "dry_run": bool(dry_run),
            "status": "scheduled" if not dry_run else "planned",
        }
        if not dry_run:
            self.backups.append(job)
            self._log("backup.scheduled", meta={"label": job["label"], "dest": destination})
        else:
            self._log("backup.planned", meta={"label": job["label"], "dest": destination})
        return job

    # Update management
    def add_update(self, name: str) -> None:
        if name and name not in self.pending_updates:
            self.pending_updates.append(name)
            self._log("update.added", meta={"name": name})

    def remove_update(self, name: str) -> bool:
        try:
            self.pending_updates.remove(name)
            self._log("update.removed", meta={"name": name})
            return True
        except ValueError:
            return False

    def apply_updates(self) -> Dict[str, Any]:
        applied = list(self.pending_updates)
        result: Dict[str, Any] = {
            "applied": applied,
            "count": len(applied),
            "applied_at": _ts() if applied else None,
        }
        if applied:
            # Clear pending and log events
            self.pending_updates.clear()
            for name in applied:
                self._log("update.applied", meta={"name": name})
            self._log("updates.applied", meta={"count": len(applied)})
        else:
            self._log("updates.none")
        return result


# Public alias for compatibility with expected API
SoloAdminSurvivalAutomationKit = SoloAdminToolkit


def get_toolkit(*, maintenance: bool = False) -> SoloAdminToolkit:
    """
    Convenience factory to obtain a toolkit instance.

    Parameters:
    - maintenance: If True, returns an instance with maintenance mode enabled.
    """
    kit = SoloAdminToolkit(maintenance_mode=bool(maintenance))
    return kit