"""Graduated autonomy bound to a verifiable configuration.

Trust expands the agent's authorized scope (the risk it may take without a
human) as clean episodes accumulate. It never relaxes a prohibition, and it
attaches to a specific configuration: change the model, instructions, tools,
or permissions and the record starts over.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field, replace

from .agents import Act
from .config import SimConfig


@dataclass(frozen=True)
class Configuration:
    model: str = "task-model-v1"
    instructions: str = "mandate-v1"
    tools: tuple[str, ...] = ("search", "fetch", "analyze")
    permissions: tuple[str, ...] = ("read:public",)

    def fingerprint(self) -> str:
        return hashlib.sha256(repr(self).encode()).hexdigest()[:12]

    def updated(self, **changes) -> "Configuration":
        return replace(self, **changes)


@dataclass
class TrustLedger:
    cfg: SimConfig
    scores: dict[str, int] = field(default_factory=dict)

    def score(self, config: Configuration) -> int:
        return self.scores.get(config.fingerprint(), 0)

    def record_episode(self, config: Configuration, executed_shortcut: bool) -> None:
        key = config.fingerprint()
        delta = -self.cfg.trust_penalty if executed_shortcut else 1
        self.scores[key] = max(0, self.scores.get(key, 0) + delta)

    def risk_threshold(self, config: Configuration) -> float:
        tiers = self.score(config) // self.cfg.trust_points_per_tier
        return min(self.cfg.trust_max_threshold,
                   self.cfg.trust_base_threshold + self.cfg.trust_step * tiers)

    def authorizes(self, action: Act, risk: float, config: Configuration) -> bool:
        """Is the action inside the earned scope? Prohibited actions never are."""
        if action is Act.SHORTCUT:
            return False
        return risk <= self.risk_threshold(config)
