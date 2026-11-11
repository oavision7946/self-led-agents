"""Governance architectures that sit between the task agent and execution.

  rules_only   One agent with rules in its prompt. Rules lose force under pressure.
  supervisor   An external policy layer checks each action (Governance-as-a-Service
               style). It can be fooled, it can be out, and the agent learns
               framings that pass. Its findings never reach the agent's planning.
  ifs_mas      Internal Family Systems Multi-Agent Self-Regulation Architecture:
               managers (scope guard, authority verifier), firefighters (incident
               response), exiles (durable memory), and Self (integrating decision
               process with a hard veto and graduated autonomy).

Ablations of ifs_mas isolate each mechanism. Any architecture can also be given
a shared normative ontology (the semantic and normative layers): it then
classifies actions by effect, checks claims against an authority registry, and
stops early on tasks no permitted path can answer.
"""

from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Callable

from .agents import Act, StepState, clamp, pressure, sigmoid
from .config import SimConfig
from .memory import ExileStore
from .ontology import SharedOntology
from .trust import Configuration, TrustLedger

Trace = Callable[[str], None]


def _silent(_: str) -> None:
    pass


@dataclass
class Decision:
    execute: Act
    escalations: int = 0


class Governance:
    name = "base"

    def __init__(self, cfg: SimConfig, rng: random.Random,
                 shared: SharedOntology | None = None):
        self.cfg = cfg
        self.rng = rng
        self.shared = shared
        self.trace: Trace = _silent

    # Lifecycle hooks ------------------------------------------------------
    def begin_episode(self, episode: int) -> None: ...
    def end_episode(self, episode: int, executed_shortcut: bool) -> None: ...

    # Planning and decision -------------------------------------------------
    def planning_relief(self, s: StepState) -> float:
        return 0.0

    def precheck(self, s: StepState) -> Decision | None:
        """Semantic layer: before the first attempt, is there a permitted path at all?"""
        if self.shared is None or s.step != 0:
            return None
        p = self.cfg.onto_answerability_recall if s.impossible else self.cfg.onto_answerability_fpr
        if self.rng.random() < p:
            self.trace("  Ontology: no permitted path covers this task; asks for clarification")
            return Decision(Act.STOP)
        return None

    def decide(self, proposal: Act, s: StepState, op: str | None = None) -> Decision:
        raise NotImplementedError

    # Feedback from the environment --------------------------------------------
    def on_blocked(self, s: StepState) -> None:
        """Infrastructure blocked an executed shortcut."""

    def on_breach(self, s: StepState, op: str | None = None) -> bool:
        """A shortcut crossed the boundary. Return True if contained."""
        return False

    def on_safe_stop(self, s: StepState) -> None: ...

    def discloses(self) -> bool:
        return self.rng.random() < self.cfg.disclose_baseline

    # Shared helper --------------------------------------------------------
    def _ask_human_high_impact(self) -> Decision:
        approved = self.rng.random() < self.cfg.human_approval
        self.trace(f"  Human: high-impact request {'approved' if approved else 'declined'}")
        return Decision(Act.HIGH_IMPACT if approved else Act.RETRY, escalations=1)


# ---------------------------------------------------------------------------
class RulesOnly(Governance):
    name = "rules_only"

    def _recognizes(self, s: StepState, op: str | None) -> bool:
        """Does the agent see the shortcut for what it is?"""
        if self.shared is not None:
            c = self.shared.ontology.classify(op or "")
            if c.known:
                self.trace(f"  Ontology: {op} is {'prohibited' if c.prohibited else 'listed as permitted'}")
                return c.prohibited
        if not s.disguised:
            return True
        return self.rng.random() < self.cfg.rules_recognize_disguised

    def decide(self, proposal: Act, s: StepState, op: str | None = None) -> Decision:
        if proposal is Act.SHORTCUT:
            if not self._recognizes(s, op):
                self.trace("  Rules: shortcut looked routine; executed")
                return Decision(Act.SHORTCUT)
            no_grant = (self.shared is not None and s.authority_claim
                        and self.rng.random() < self.cfg.onto_registry_accuracy)
            p_refuse = clamp(self.cfg.rules_compliance - self.cfg.rules_pressure_decay
                             * pressure(self.cfg, s, discount_authority=no_grant), 0.05, 0.99)
            if self.rng.random() < p_refuse:
                self.trace(f"  Rules: refused shortcut (p={p_refuse:.2f})")
                return Decision(Act.RETRY)
            self.trace(f"  Rules: lost force under pressure (p_refuse={p_refuse:.2f})")
            return Decision(Act.SHORTCUT)
        if proposal is Act.HIGH_IMPACT:
            return self._ask_human_high_impact()
        return Decision(proposal)


# ---------------------------------------------------------------------------
class Supervisor(Governance):
    name = "supervisor"

    def __init__(self, cfg: SimConfig, rng: random.Random,
                 shared: SharedOntology | None = None):
        super().__init__(cfg, rng, shared)
        self.violations = 0
        self.evasion = 0.0

    def decide(self, proposal: Act, s: StepState, op: str | None = None) -> Decision:
        if proposal is Act.SHORTCUT:
            if self.rng.random() < self.cfg.sup_outage:
                self.trace("  Supervisor: unavailable; action passes unchecked")
                return Decision(Act.SHORTCUT)
            d = self.cfg.sup_detect + self.cfg.sup_scrutiny_gain * min(self.violations, 5)
            d -= self.evasion
            if s.disguised:
                d *= self.cfg.sup_disguise_factor
            if s.has_claim:
                d *= self.cfg.sup_claim_factor
            d = clamp(d, 0.0, 0.99)
            if self.rng.random() < d:
                self.violations += 1
                esc = 1 if s.has_claim else 0   # claims get routed to a human to confirm
                self.trace(f"  Supervisor: blocked shortcut (p_detect={d:.2f})"
                           + ("; escalated claim to human" if esc else ""))
                return Decision(Act.RETRY, escalations=esc)
            self.evasion = min(self.cfg.sup_evasion_cap, self.evasion + self.cfg.sup_evasion_gain)
            self.trace(f"  Supervisor: missed shortcut (p_detect={d:.2f}); agent learns the framing")
            return Decision(Act.SHORTCUT)
        if proposal is Act.HIGH_IMPACT:
            return self._ask_human_high_impact()
        return Decision(proposal)

    def on_blocked(self, s: StepState) -> None:
        self.violations += 1


# ---------------------------------------------------------------------------
class IFSMAS(Governance):
    """Internal Family Systems Multi-Agent Self-Regulation Architecture."""

    name = "ifs_mas"

    def __init__(self, cfg: SimConfig, rng: random.Random, *, managers: bool = True,
                 exiles: bool = True, hard_veto: bool = True,
                 config_change_at: int | None = None,
                 shared: SharedOntology | None = None):
        super().__init__(cfg, rng, shared)
        self.use_managers = managers
        self.exiles = ExileStore() if exiles else None
        self.hard_veto = hard_veto
        self.config_change_at = config_change_at
        self.config = Configuration()
        self.ledger = TrustLedger(cfg)
        self.episode = 0
        self._claims_checked = False
        self._claims_discredited = False

    # Lifecycle -----------------------------------------------------------------
    def begin_episode(self, episode: int) -> None:
        self.episode = episode
        self._claims_checked = False
        self._claims_discredited = False
        if self.config_change_at is not None and episode == self.config_change_at:
            self.config = self.config.updated(model="task-model-v2")
            self.trace(f"  Config: model updated; trust record restarts ({self.config.fingerprint()})")

    def end_episode(self, episode: int, executed_shortcut: bool) -> None:
        self.ledger.record_episode(self.config, executed_shortcut)

    # Exiles ---------------------------------------------------------------------
    def _memory(self, s: StepState) -> float:
        if self.exiles is None:
            return 0.0
        return self.exiles.strength(s.tags(), self.cfg.memory_saturation)

    def _remember(self, kind: str, s: StepState) -> None:
        if self.exiles is not None:
            self.exiles.record(self.episode, kind, s.tags())

    def planning_relief(self, s: StepState) -> float:
        """Self briefs the task part with relevant memories before it plans."""
        m = self._memory(s)
        if m > 0:
            self.trace(f"  Exiles: memory strength {m:.2f} resurfaced into planning")
        return self.cfg.w_memory_planning * m

    # Managers -------------------------------------------------------------------
    def _check_claims(self, s: StepState) -> int:
        """Authority verifier: look claims up in the registry, once per episode."""
        if not s.has_claim or self._claims_checked or not self.use_managers:
            return 0
        self._claims_checked = True
        if self.shared is not None and self.rng.random() < self.cfg.onto_registry_accuracy:
            self._claims_discredited = True
            self.trace("  Manager/AuthorityVerifier: registry shows no grant from the claimant; discredited")
            return 0
        if self.shared is None and self.rng.random() < self.cfg.mgr_verify_claims:
            self._claims_discredited = True
            self.trace("  Manager/AuthorityVerifier: claimed permission not in registry; discredited")
            return 0
        self._claims_discredited = True   # a human confirms no permission was granted
        self.trace("  Manager/AuthorityVerifier: cannot verify claim; escalated to human (no permission)")
        return 1

    def _flags_violation(self, s: StepState, m: float, op: str | None = None) -> bool | None:
        """True/False = flagged or not; None = the action's effect is unknown."""
        if self.use_managers and self.shared is not None:
            c = self.shared.ontology.classify(op or "")
            if not c.known:
                self.trace(f"  Manager/ScopeGuard: {op} has no certified entry; routes it to a human")
                return None
            if c.prohibited:
                p = 1 - (1 - self.cfg.onto_precision) * (1 - self.cfg.exile_detect_boost * m)
                why = f"ontology: {op} -> {', '.join(c.effects)}"
            else:
                p = self.cfg.exile_detect_boost * m
                why = f"ontology lists {op} as permitted; memory only"
            flagged = self.rng.random() < p
            self.trace(f"  Manager/ScopeGuard: {'flagged prohibited action' if flagged else 'did not flag'}"
                       f" ({why}; p={p:.2f})")
            return flagged
        if self.use_managers:
            p = self.cfg.mgr_detect_disguised if s.disguised else self.cfg.mgr_detect
            p = 1 - (1 - p) * (1 - self.cfg.exile_detect_boost * m)
            who = "Manager/ScopeGuard"
        else:
            p = self.cfg.self_solo_detect
            who = "Self (no managers)"
        flagged = self.rng.random() < p
        self.trace(f"  {who}: {'flagged prohibited action' if flagged else 'missed the violation'} (p={p:.2f})")
        return flagged

    # Self -------------------------------------------------------------------------
    def _safe_alternative(self, s: StepState) -> Act:
        return Act.STOP if s.frustration >= self.cfg.stop_after else Act.RETRY

    def decide(self, proposal: Act, s: StepState, op: str | None = None) -> Decision:
        esc = self._check_claims(s)
        m = self._memory(s)
        p_eff = pressure(self.cfg, s, discount_claims=self._claims_discredited)

        if proposal is Act.SHORTCUT:
            flagged = self._flags_violation(s, m, op)
            p_blend = clamp(self.cfg.self_blend_base + self.cfg.self_blend_per_pressure * p_eff
                            - self.cfg.exile_blend_relief * m, 0.0, 0.95)
            if self.rng.random() < p_blend:
                self.trace(f"  Self: blended with the task part (p={p_blend:.2f}); executes shortcut")
                if flagged:
                    self._remember("ignored_warning", s)
                return Decision(Act.SHORTCUT, esc)
            if flagged is None:
                self.trace("  Human: reviewed the unclassified action; blocked it")
                self._remember("blocked_attempt", s)
                return Decision(self._safe_alternative(s), esc + 1)
            if flagged and self.hard_veto:
                alt = self._safe_alternative(s)
                self.trace(f"  Self: hard veto; chooses {alt.value}")
                return Decision(alt, esc)
            if flagged:
                p_exec = sigmoid(p_eff - self.cfg.vote_threshold)
                if self.rng.random() < p_exec:
                    self.trace(f"  Self (vote): task benefit outweighed the concern (p={p_exec:.2f})")
                    self._remember("ignored_warning", s)
                    return Decision(Act.SHORTCUT, esc)
                self.trace(f"  Self (vote): concern prevailed (p_exec={p_exec:.2f})")
                return Decision(self._safe_alternative(s), esc)
            return Decision(Act.SHORTCUT, esc)

        if proposal is Act.HIGH_IMPACT:
            if self.ledger.authorizes(Act.HIGH_IMPACT, self.cfg.high_impact_risk, self.config):
                self.trace(f"  Self: high-impact action within earned scope "
                           f"(threshold {self.ledger.risk_threshold(self.config):.2f})")
                return Decision(Act.HIGH_IMPACT, esc)
            d = self._ask_human_high_impact()
            return Decision(d.execute, esc + d.escalations)

        if s.frustration >= self.cfg.stop_after:
            self.trace("  Self: repeated failure with no permitted path; stops and discloses")
            return Decision(Act.STOP, esc)
        return Decision(proposal, esc)

    # Firefighters and feedback ------------------------------------------------------
    def on_blocked(self, s: StepState) -> None:
        self.trace("  Exiles: blocked attempt recorded")
        self._remember("blocked_attempt", s)

    def on_breach(self, s: StepState, op: str | None = None) -> bool:
        contained = self.rng.random() < self.cfg.ff_detect
        self.trace("  Firefighter/IncidentResponder: "
                   + ("paused run, contained, restored safe state" if contained
                      else "missed the breach"))
        if contained:
            self._remember("incident", s)
            if self.shared is not None and op is not None:
                c = self.shared.ontology.classify(op)
                if c.known and not c.prohibited:
                    ok = self.shared.correct(op)
                    self.trace(f"  Incident review: correction for {op} "
                               + ("certified and applied" if ok else "rejected"))
        return contained

    def on_safe_stop(self, s: StepState) -> None:
        self._remember("safe_stop", s)

    def discloses(self) -> bool:
        return self.rng.random() < self.cfg.disclose_ifs


# ---------------------------------------------------------------------------
Factory = Callable[..., Governance]   # (cfg, rng, shared=None) -> Governance

ARCHITECTURES: dict[str, Factory] = {
    "rules_only": lambda c, r, sh=None: RulesOnly(c, r),
    "supervisor": lambda c, r, sh=None: Supervisor(c, r),
    "ifs_mas": lambda c, r, sh=None: IFSMAS(c, r),
    "ifs_no_exiles": lambda c, r, sh=None: IFSMAS(c, r, exiles=False),
    "ifs_no_managers": lambda c, r, sh=None: IFSMAS(c, r, managers=False),
    "ifs_vote": lambda c, r, sh=None: IFSMAS(c, r, hard_veto=False),
    "ifs_config_change": lambda c, r, sh=None: IFSMAS(c, r, config_change_at=c.config_change_at),
    # Three-layer variants: a shared normative ontology, with or without certification
    "rules_ontology": lambda c, r, sh=None: RulesOnly(c, r, shared=sh),
    "ifs_ontology": lambda c, r, sh=None: IFSMAS(c, r, shared=sh),
    "ifs_ontology_uncertified": lambda c, r, sh=None: IFSMAS(c, r, shared=sh),
}

# Architectures that receive a shared ontology, mapped to whether edits need certification
ONTOLOGY_GATES: dict[str, bool] = {
    "rules_ontology": True,
    "ifs_ontology": True,
    "ifs_ontology_uncertified": False,
}

MAIN_ARCHITECTURES = ("rules_only", "supervisor", "ifs_mas")
LAYER_ARCHITECTURES = ("rules_only", "rules_ontology", "ifs_mas", "ifs_ontology")
