"""Thread-safe parameter storage for live control surfaces.

The :class:`ParamStore` acts as the bridge between control inputs (sliders,
MIDI CC, OSC) and the render loop.  Values are plain Python floats stored in
a dict — reads and writes are atomic under the GIL so no locks are needed on
the hot render path.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Iterator, Optional


@dataclass
class ParamEntry:
    """Metadata + live value for a single controllable parameter."""

    name: str
    group: str
    default: float
    min: float
    max: float
    description: str
    value: float = 0.0

    def __post_init__(self) -> None:
        if self.value == 0.0:
            self.value = self.default


class ParamStore:
    """Central parameter hub shared between control surfaces and the render loop."""

    def __init__(self) -> None:
        self._entries: dict[str, ParamEntry] = {}
        self._on_change: Optional[Callable[[str, float], None]] = None

    def register(
        self,
        name: str,
        *,
        group: str = "default",
        default: float = 0.0,
        min: float = 0.0,
        max: float = 1.0,
        description: str = "",
    ) -> None:
        key = f"{group}.{name}"
        self._entries[key] = ParamEntry(
            name=name,
            group=group,
            default=default,
            min=min,
            max=max,
            description=description,
        )

    def set(self, key: str, value: float) -> None:
        if key in self._entries:
            entry = self._entries[key]
            entry.value = max(entry.min, min(entry.max, value))
            if self._on_change is not None:
                self._on_change(key, entry.value)

    def get(self, key: str) -> float:
        return self._entries[key].value

    def bind(self, key: str) -> Callable[[], float]:
        """Return a zero-alloc callable for use as a ParamFloat."""
        entries = self._entries
        return lambda: entries[key].value

    def groups(self) -> list[str]:
        seen: dict[str, None] = {}
        for e in self._entries.values():
            seen[e.group] = None
        return list(seen)

    def entries_for_group(self, group: str) -> list[ParamEntry]:
        return [e for e in self._entries.values() if e.group == group]

    def all_entries(self) -> Iterator[ParamEntry]:
        return iter(self._entries.values())

    def __contains__(self, key: str) -> bool:
        return key in self._entries

    def __len__(self) -> int:
        return len(self._entries)

    # -- Persistence ----------------------------------------------------------

    def save(self, path: str | Path) -> None:
        """Save current values to a JSON preset file."""
        data = {k: e.value for k, e in self._entries.items()}
        Path(path).write_text(json.dumps(data, indent=2))

    def load(self, path: str | Path) -> None:
        """Load values from a JSON preset file."""
        data = json.loads(Path(path).read_text())
        for k, v in data.items():
            if k in self._entries:
                self.set(k, v)
