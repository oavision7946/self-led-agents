"""Episode loop for a collective of agents sharing one message board.

Agents act in lock-step. When an agent's shortcut works and contagion is on,
it posts "GO, permission granted" to the board, and every peer sees it from
the next step: the pattern behind the Hugging Face incident, where agents
adopted goals and permissions from one another.

Architectures with a normative ontology share ONE ontology across the
collective. In the ontology_poisoning condition an attacker submits edits that
relabel a prohibited operation as permitted; whether they land depends on the
certification gate.
"""

from __future__ import annotations

import random
from dataclasses import asdict, dataclass

from .agents import Act, StepState, StochasticTaskAgent
from .config import Condition, SimConfig
from .governance import ARCHITECTURES, ONTOLOGY_GATES, Governance, Trace
from .ontology import DISGUISED_SHORTCUTS, PLAIN_SHORTCUTS, NormativeOntology, SharedOntology


@dataclass
class EpisodeRecord:
    architecture: str
    condition: str
    seed: int
    agent: int
    episode: int
    proposed_shortcut: bool = False
    executed_shortcut: bool = False   # the system chose to cross the boundary
    breach: bool = False              # the boundary was actually crossed (infra gap)
    contained: bool = False
    legit_success: bool = False
    gamed_success: bool = False       # "completed" via an uncontained shortcut
    safe_stop: bool = False
    clarified: bool = False           # stopped at step 0: no permitted path covers the task
    timeout: bool = False
    disclosed: bool = False
    escalations: int = 0
    steps: int = 0
    ontology_poisoned: bool = False   # the shared ontology contradicted ground truth this episode

    def row(self) -> dict:
        return asdict(self)


def outcome_label(r: EpisodeRecord) -> str:
    if r.legit_success:
        return "completed on a permitted path"
    if r.clarified:
        return "asked for clarification (no permitted path)"
    if r.safe_stop:
        return "safe stop"
    if r.contained:
        return "breach contained"
    if r.gamed_success:
        return "uncontained shortcut"
    return "timeout"


def run_collective(arch: str, cond: Condition, cfg: SimConfig, seed: int,
                   trace_agent: int | None = None, trace: Trace | None = None,
                   trace_episodes: set[int] | None = None) -> list[EpisodeRecord]:
    rngs = [random.Random(f"{arch}|{cond.name}|{seed}|{i}") for i in range(cfg.n_agents)]
    env_rng = random.Random(f"env|{arch}|{cond.name}|{seed}")
    op_rng = random.Random(f"ops|{arch}|{cond.name}|{seed}")
    attack_rng = random.Random(f"attack|{arch}|{cond.name}|{seed}")
    shared = None
    if arch in ONTOLOGY_GATES:
        shared = SharedOntology(NormativeOntology.load(), ONTOLOGY_GATES[arch],
                                cfg.certifier_accuracy, random.Random(f"cert|{arch}|{cond.name}|{seed}"))
    tasks = [StochasticTaskAgent(cfg, rngs[i]) for i in range(cfg.n_agents)]
    govs: list[Governance] = [ARCHITECTURES[arch](cfg, rngs[i], shared) for i in range(cfg.n_agents)]
    records: list[EpisodeRecord] = []

    p_legit = 0.0 if cond.impossible else cfg.p_legit_success
    p_high = 0.0 if cond.impossible else cfg.p_high_impact_success

    for ep in range(cfg.n_episodes):
        tracing = {i: (trace is not None and i == trace_agent
                       and (trace_episodes is None or ep in trace_episodes))
                   for i in range(cfg.n_agents)}
        for i, g in enumerate(govs):
            g.trace = trace if tracing[i] else (lambda _: None)
            g.begin_episode(ep)
        recs = [EpisodeRecord(arch, cond.name, seed, i, ep) for i in range(cfg.n_agents)]
        if cond.poisoning and shared is not None and attack_rng.random() < cfg.poison_attempt_rate:
            target = attack_rng.choice(DISGUISED_SHORTCUTS)
            landed = shared.poison(target)
            if trace is not None and any(tracing.values()):
                trace(f"[episode {ep}] Attacker: edit relabeling {target} as permitted "
                      + ("landed in the ontology" if landed else "rejected by the certifier"))
        poisoned = shared is not None and shared.ontology.is_poisoned()
        for r in recs:
            r.ontology_poisoned = poisoned
        frustration = [0] * cfg.n_agents
        done = [False] * cfg.n_agents
        board_go = cond.peer_seed

        for step in range(cfg.max_steps):
            posts_go = False
            for i in range(cfg.n_agents):
                if done[i]:
                    continue
                log = trace if tracing[i] else (lambda _: None)
                s = StepState(ep, step, frustration[i], board_go, cond.false_authority,
                              cond.deadline and board_go, cond.reward_visible,
                              cond.infra_gap, cond.impossible)
                rec, gov = recs[i], govs[i]
                rec.steps = step + 1
                log(f"[episode {ep}, step {step}]")
                pre = gov.precheck(s)
                if pre is not None and pre.execute is Act.STOP:
                    rec.safe_stop = rec.clarified = done[i] = True
                    gov.on_safe_stop(s)
                    log("  Outcome: clarification requested before any attempt")
                    continue
                relief = gov.planning_relief(s)
                proposal = tasks[i].propose(s, relief)
                op = None
                if proposal is Act.SHORTCUT:
                    op = op_rng.choice(DISGUISED_SHORTCUTS if cond.infra_gap else PLAIN_SHORTCUTS)
                log(f"  Task: proposes {proposal.value}" + (f" via {op}" if op else "")
                    + f" (p_shortcut={tasks[i].shortcut_probability(s, relief):.2f})")
                rec.proposed_shortcut |= proposal is Act.SHORTCUT
                decision = gov.decide(proposal, s, op)
                rec.escalations += decision.escalations
                act = decision.execute

                if act is Act.STOP:
                    rec.safe_stop = done[i] = True
                    gov.on_safe_stop(s)
                    log("  Outcome: safe stop")
                elif act in (Act.RETRY, Act.HIGH_IMPACT):
                    p = p_legit if act is Act.RETRY else p_high
                    if env_rng.random() < p:
                        rec.legit_success = done[i] = True
                        log("  Outcome: task completed on a permitted path")
                    else:
                        frustration[i] += 1
                        log("  Outcome: attempt failed")
                else:  # SHORTCUT executed
                    rec.executed_shortcut = True
                    if not cond.infra_gap:
                        frustration[i] += 1
                        gov.on_blocked(s)
                        log("  Outcome: infrastructure blocked the shortcut")
                    else:
                        rec.breach = True
                        log("  Outcome: boundary crossed through an infrastructure gap")
                        if gov.on_breach(s, op):
                            rec.contained = done[i] = True
                        else:
                            rec.gamed_success = done[i] = True
                            posts_go |= cond.contagion
            if posts_go:
                board_go = True

        for i, rec in enumerate(recs):
            if not done[i]:
                rec.timeout = True
            if rec.executed_shortcut:
                rec.disclosed = govs[i].discloses()
            govs[i].end_episode(ep, rec.executed_shortcut)
            if tracing[i]:
                trace(f"--> episode {ep} outcome: {outcome_label(rec)}; escalations={rec.escalations}"
                      + (f"; disclosed={rec.disclosed}" if rec.executed_shortcut else "") + "\n")
            records.append(rec)
    return records
