"""Exiles: a durable record of ignored warnings, blocked attempts, and incidents.

In IFS, exiles carry experiences pushed out of awareness. Here the exile store
does the opposite of forgetting: it brings those events back into the next
decision, so a repeated warning changes planning before the next boundary is
tested.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .agents import clamp

KINDS = ("ignored_warning", "blocked_attempt", "incident", "safe_stop")


@dataclass(frozen=True)
class Memory:
    episode: int
    kind: str
    tags: frozenset[str]


@dataclass
class ExileStore:
    window: int = 40                       # most recent memories considered
    records: list[Memory] = field(default_factory=list)

    def record(self, episode: int, kind: str, tags: frozenset[str]) -> None:
        if kind not in KINDS:
            raise ValueError(f"unknown memory kind: {kind}")
        self.records.append(Memory(episode, kind, tags))

    def relevance(self, tags: frozenset[str]) -> float:
        """Matching memories count fully; other boundary memories count half."""
        score = 0.0
        for m in self.records[-self.window:]:
            if m.kind == "safe_stop":
                continue
            score += 1.0 if (m.tags & tags) else 0.5
        return score

    def strength(self, tags: frozenset[str], saturation: float) -> float:
        return clamp(self.relevance(tags) / saturation, 0.0, 1.0)

    def __len__(self) -> int:
        return len(self.records)
