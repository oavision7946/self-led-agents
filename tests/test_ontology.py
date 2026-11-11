"""The semantic and normative layers: classification by effect, authority, certification."""

import random

import pytest

from ifs_mas import (CONDITIONS, IFSMAS, Act, NormativeOntology, RulesOnly, SharedOntology,
                     SimConfig, StepState, run_collective)
from ifs_mas.ontology import DISGUISED_SHORTCUTS, PLAIN_SHORTCUTS, TRUE_EFFECTS

CFG = SimConfig()
SMALL = SimConfig(n_agents=3, n_episodes=10, seeds=(0,), config_change_at=5)


def state(**kw) -> StepState:
    base = dict(episode=0, step=1, frustration=0, peer_claim=False, authority_claim=False,
                deadline=False, reward_visible=False, disguised=True, impossible=False)
    base.update(kw)
    return StepState(**base)


def shared(certification=True, accuracy=0.95, seed=0) -> SharedOntology:
    return SharedOntology(NormativeOntology.load(), certification, accuracy, random.Random(seed))


def test_classification_is_by_effect_not_surface():
    onto = NormativeOntology.load()
    c = onto.classify("dns_query")
    assert c.known and c.prohibited and c.effects == ("external_communication",)
    assert onto.classify("retry_task").prohibited is False


def test_draft_and_missing_entries_are_unknown():
    onto = NormativeOntology.load()
    assert onto.classify("fetch_portal_page").known is False   # present but uncertified
    assert onto.classify("never_seen_tool").known is False


def test_every_shortcut_has_ground_truth():
    assert set(PLAIN_SHORTCUTS + DISGUISED_SHORTCUTS) == set(TRUE_EFFECTS)


def test_peers_cannot_grant_permission():
    onto = NormativeOntology.load()
    assert onto.may_grant("operations_owner", "elevated_data_access")
    assert not onto.may_grant("peer_agent", "external_communication")
    assert not any(onto.may_grant(p, "external_communication")
                   for p in ("operations_owner", "human_reviewer"))


def test_answerability_follows_the_task_definition():
    onto = NormativeOntology.load()
    assert onto.answerable("sales_analysis")
    assert not onto.answerable("ad_roi")


def test_uncertified_ontology_accepts_poison():
    sh = shared(certification=False)
    assert sh.poison("dns_query")
    assert sh.ontology.is_poisoned()
    assert sh.ontology.classify("dns_query").prohibited is False


def test_perfect_certifier_rejects_poison_and_accepts_corrections():
    sh = shared(certification=True, accuracy=1.0)
    assert not any(sh.poison(op) for op in DISGUISED_SHORTCUTS for _ in range(50))
    assert not sh.ontology.is_poisoned()
    sh_open = shared(certification=False)
    sh_open.poison("dns_query")
    sh.ontology._apply(sh_open.log[0][0])          # simulate a poison that slipped through
    assert sh.correct("dns_query") and not sh.ontology.is_poisoned()


def test_ifs_routes_unclassified_actions_to_a_human():
    cfg = CFG.with_overrides(self_blend_base=0.0, self_blend_per_pressure=0.0)
    gov = IFSMAS(cfg, random.Random(0), shared=shared())
    d = gov.decide(Act.SHORTCUT, state(), op="fetch_portal_page")
    assert d.execute is not Act.SHORTCUT and d.escalations == 1


def test_ifs_with_ontology_never_executes_a_flagged_shortcut():
    cfg = CFG.with_overrides(onto_precision=1.0, self_blend_base=0.0, self_blend_per_pressure=0.0)
    gov = IFSMAS(cfg, random.Random(2), shared=shared())
    s = state(frustration=3, peer_claim=True, deadline=True, reward_visible=True)
    assert all(gov.decide(Act.SHORTCUT, s, op="dns_query").execute is not Act.SHORTCUT
               for _ in range(500))


def test_knowing_is_not_choosing():
    """A rules agent that recognizes every shortcut still crosses under pressure."""
    gov = RulesOnly(CFG, random.Random(0), shared=shared())
    s = state(frustration=4, peer_claim=True, deadline=True, reward_visible=True)
    executed = sum(gov.decide(Act.SHORTCUT, s, op="dns_query").execute is Act.SHORTCUT
                   for _ in range(500))
    assert executed > 100


def test_precheck_stops_only_with_an_ontology():
    s0 = state(step=0, impossible=True)
    cfg = CFG.with_overrides(onto_answerability_recall=1.0)
    assert IFSMAS(cfg, random.Random(0), shared=shared()).precheck(s0).execute is Act.STOP
    assert IFSMAS(cfg, random.Random(0)).precheck(s0) is None


@pytest.mark.parametrize("arch", ["rules_ontology", "ifs_ontology", "ifs_ontology_uncertified"])
def test_poisoning_never_affects_ground_truth_blocking(arch):
    recs = run_collective(arch, CONDITIONS["peer_pressure"], SMALL, seed=1)
    assert not any(r.breach for r in recs)
