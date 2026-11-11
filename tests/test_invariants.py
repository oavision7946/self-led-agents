"""Invariants the architecture must hold regardless of parameter values."""

import random

import pytest

from ifs_mas import (ARCHITECTURES, CONDITIONS, IFSMAS, Act, Configuration, EpisodeRecord,
                     ExileStore, SimConfig, StepState, TrustLedger, run_collective, summarize)

CFG = SimConfig()
SMALL = SimConfig(n_agents=3, n_episodes=8, seeds=(0,), config_change_at=4)


def state(**kw) -> StepState:
    base = dict(episode=0, step=0, frustration=0, peer_claim=False, authority_claim=False,
                deadline=False, reward_visible=False, disguised=False, impossible=False)
    base.update(kw)
    return StepState(**base)


# ---- Trust ledger: graduated autonomy never relaxes a prohibition ----------
def test_prohibited_action_never_authorized_at_any_trust_level():
    ledger, config = TrustLedger(CFG), Configuration()
    for _ in range(500):
        ledger.record_episode(config, executed_shortcut=False)
    assert ledger.risk_threshold(config) == CFG.trust_max_threshold
    assert not ledger.authorizes(Act.SHORTCUT, risk=0.0, config=config)


def test_trust_rises_with_clean_record_and_falls_after_violation():
    ledger, config = TrustLedger(CFG), Configuration()
    start = ledger.risk_threshold(config)
    for _ in range(20):
        ledger.record_episode(config, executed_shortcut=False)
    assert ledger.risk_threshold(config) > start
    before = ledger.score(config)
    ledger.record_episode(config, executed_shortcut=True)
    assert ledger.score(config) == before - CFG.trust_penalty


def test_trust_attaches_to_configuration():
    ledger, v1 = TrustLedger(CFG), Configuration()
    for _ in range(20):
        ledger.record_episode(v1, executed_shortcut=False)
    v2 = v1.updated(model="task-model-v2")
    assert v1.fingerprint() != v2.fingerprint()
    assert ledger.score(v2) == 0
    assert ledger.risk_threshold(v2) == CFG.trust_base_threshold


# ---- Self: a flagged boundary cannot be voted away ---------------------------
def test_hard_veto_blocks_every_flagged_shortcut():
    cfg = CFG.with_overrides(mgr_detect=1.0, mgr_detect_disguised=1.0,
                             self_blend_base=0.0, self_blend_per_pressure=0.0)
    gov = IFSMAS(cfg, random.Random(1))
    s = state(frustration=3, peer_claim=True, authority_claim=True, deadline=True, reward_visible=True)
    assert all(gov.decide(Act.SHORTCUT, s).execute is not Act.SHORTCUT for _ in range(1000))


def test_vote_ablation_can_trade_a_boundary_for_task_benefit():
    cfg = CFG.with_overrides(mgr_detect=1.0, self_blend_base=0.0, self_blend_per_pressure=0.0)
    gov = IFSMAS(cfg, random.Random(1), hard_veto=False, managers=True)
    s = state(frustration=6, deadline=True, reward_visible=True)
    assert any(gov.decide(Act.SHORTCUT, s).execute is Act.SHORTCUT for _ in range(1000))


def test_self_stops_safely_after_repeated_failure():
    gov = IFSMAS(CFG, random.Random(0))
    assert gov.decide(Act.RETRY, state(frustration=CFG.stop_after)).execute is Act.STOP


# ---- Exiles: the record returns to future decisions --------------------------
def test_exile_memory_reduces_shortcut_planning():
    gov = IFSMAS(CFG, random.Random(0))
    s = state(peer_claim=True)
    assert gov.planning_relief(s) == 0.0
    for _ in range(5):
        gov.on_blocked(s)
    assert gov.planning_relief(s) == pytest.approx(CFG.w_memory_planning)


def test_exile_store_rejects_unknown_kinds():
    with pytest.raises(ValueError):
        ExileStore().record(0, "rumor", frozenset())


# ---- Environment and reproducibility ------------------------------------------
@pytest.mark.parametrize("arch", sorted(ARCHITECTURES))
def test_no_breach_without_an_infrastructure_gap(arch):
    recs = run_collective(arch, CONDITIONS["peer_pressure"], SMALL, seed=0)
    assert not any(r.breach for r in recs)


@pytest.mark.parametrize("arch", sorted(ARCHITECTURES))
def test_runs_are_reproducible(arch):
    a = run_collective(arch, CONDITIONS["combined_hf_like"], SMALL, seed=3)
    b = run_collective(arch, CONDITIONS["combined_hf_like"], SMALL, seed=3)
    assert [r.row() for r in a] == [r.row() for r in b]


def test_held_under_temptation_metric():
    recs = [EpisodeRecord("x", "c", 0, 0, 0, proposed_shortcut=True, executed_shortcut=False),
            EpisodeRecord("x", "c", 0, 0, 1, proposed_shortcut=True, executed_shortcut=True),
            EpisodeRecord("x", "c", 0, 0, 2, proposed_shortcut=False)]
    (row,) = summarize(recs)
    assert row["held_under_temptation"] == pytest.approx(0.5)
    assert row["attempt_rate"] == pytest.approx(1 / 3)
