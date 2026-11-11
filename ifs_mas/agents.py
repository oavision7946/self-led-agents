"""Actions, the observable step state, and the task agent (the "task part").

The task agent pursues its objective. Its propensity to take a prohibited
shortcut rises with frustration and social pressure, a stylized model of
specification gaming. It knows nothing about governance; whatever stops it
has to come from the architecture around it.
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass
from enum import Enum
from typing import Protocol

from .config import SimConfig


class Act(str, Enum):
    RETRY = "retry"              # permitted attempt on the legitimate path
    HIGH_IMPACT = "high_impact"  # permitted, risk-weighted; may need a human
    SHORTCUT = "shortcut"        # prohibited: crosses a boundary
    STOP = "stop"                # safe stop with disclosure


@dataclass(frozen=True)
class StepState:
    """What the system can observe at one decision step."""

    episode: int
    step: int
    frustration: int        # failed attempts so far in this episode
    peer_claim: bool        # board shows a peer's "GO, permission granted"
    authority_claim: bool   # a message claims an authority approved the shortcut
    deadline: bool
    reward_visible: bool
    disguised: bool         # the shortcut looks like a routine action
    impossible: bool        # ground truth; not visible to any part

    @property
    def has_claim(self) -> bool:
        return self.peer_claim or self.authority_claim

    def tags(self) -> frozenset[str]:
        """Signature used to match memories to the current situation."""
        t = set()
        if self.peer_claim:
            t.add("peer")
        if self.authority_claim:
            t.add("authority")
        if self.disguised:
            t.add("bypass")
        if self.frustration >= 2:
            t.add("frustration")
        return frozenset(t or {"routine"})


def sigmoid(x: float) -> float:
    return 1.0 / (1.0 + math.exp(-x))


def clamp(x: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, x))


def pressure(cfg: SimConfig, s: StepState, discount_claims: bool = False,
             discount_authority: bool = False) -> float:
    """Pressure index in logit units.

    discount_claims: claims were discredited and exert no pressure at all.
    discount_authority: the false premise is known (no one granted permission),
    but a peer's social pull remains.
    """
    p = cfg.w_frustration * s.frustration
    if s.deadline:
        p += cfg.w_deadline
    if s.reward_visible:
        p += cfg.w_reward
    if not discount_claims:
        if s.peer_claim:
            p += cfg.w_peer
        if s.authority_claim and not discount_authority:
            p += cfg.w_authority
    return p


class TaskPolicy(Protocol):
    """Anything that proposes the next action. Swap in an LLM-backed agent here."""

    def propose(self, s: StepState, planning_relief: float = 0.0) -> Act: ...


class StochasticTaskAgent:
    """Stylized task part: pursues the objective, games it under pressure."""

    def __init__(self, cfg: SimConfig, rng: random.Random):
        self.cfg = cfg
        self.rng = rng

    def shortcut_probability(self, s: StepState, planning_relief: float = 0.0) -> float:
        return sigmoid(self.cfg.base_logit + pressure(self.cfg, s) - planning_relief)

    def propose(self, s: StepState, planning_relief: float = 0.0) -> Act:
        if self.rng.random() < self.shortcut_probability(s, planning_relief):
            return Act.SHORTCUT
        if s.frustration >= 2 and self.rng.random() < self.cfg.p_propose_high_impact:
            return Act.HIGH_IMPACT
        return Act.RETRY
