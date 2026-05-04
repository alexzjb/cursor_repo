from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timezone
from typing import Callable

from .types import MemoryEntry, SessionState


Clock = Callable[[], str]


def iso_now() -> str:
    return datetime.now(timezone.utc).isoformat()


class MemoryStore:
    def __init__(self, clock: Clock | None = None) -> None:
        self._clock = clock or iso_now
        self._messages: dict[str, list[MemoryEntry]] = defaultdict(list)
        self._notes: dict[str, list[str]] = defaultdict(list)

    def append(self, session_id: str, role: str, text: str) -> MemoryEntry:
        entry = MemoryEntry(role=role, text=text, at=self._clock())
        self._messages[session_id].append(entry)
        return entry

    def history(self, session_id: str) -> list[MemoryEntry]:
        return list(self._messages.get(session_id, []))

    def remember(self, session_id: str, note: str) -> None:
        self._notes[session_id].append(note)

    def notes(self, session_id: str) -> list[str]:
        return list(self._notes.get(session_id, []))

    def session_ids(self) -> list[str]:
        ids = set(self._messages) | set(self._notes)
        return sorted(ids)

    def sessions(self) -> list[SessionState]:
        return [
            SessionState(
                id=session_id,
                messages=tuple(self._messages.get(session_id, [])),
                notes=tuple(self._notes.get(session_id, [])),
            )
            for session_id in self.session_ids()
        ]


class InMemoryStore(MemoryStore):
    """Backward-compatible alias for the default memory implementation."""

    def __init__(self) -> None:
        super().__init__()
