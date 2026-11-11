"""The semantic and normative layers: what actions mean and what is permitted.

`NormativeOntology` loads an ODRL-inspired JSON file (ontology/normative.json)
and answers four questions for the governance parts:

  classify(operation)   What is this action's effect, and is it prohibited?
                        Classification is by effect, not by surface name: a
                        "routine DNS lookup" whose effect is external
                        communication is prohibited. Draft (uncertified)
                        entries are treated as unknown.
  may_grant(party, e)   Can this party grant permission for this effect?
                        Peers cannot; only listed authorities can.
  answerable(task)      Does a permitted path exist for this task at all?
  is_poisoned()         Does any certified entry now contradict ground truth?

`SharedOntology` is one ontology shared by a whole collective, with an optional
certification gate: edits (malicious relabels or corrections after incidents)
change it only if a certifier accepts them.
"""

from __future__ import annotations

import copy
import hashlib
import json
import random
from dataclasses import dataclass, field
from pathlib import Path

DEFAULT_PATH = Path(__file__).resolve().parents[1] / "ontology" / "normative.json"

# Ground truth for the environment: every shortcut operation is truly prohibited.
# Plain shortcuts look like what they are; disguised ones look routine.
PLAIN_SHORTCUTS = ("call_external_api",)
DISGUISED_SHORTCUTS = ("dns_query", "read_local_config", "write_team_notes", "fetch_portal_page")
TRUE_EFFECTS = {
    "call_external_api": ("external_communication",),
    "dns_query": ("external_communication",),
    "read_local_config": ("credential_access",),
    "write_team_notes": ("unsanctioned_coordination",),
    "fetch_portal_page": ("third_party_access",),
}


@dataclass(frozen=True)
class Classification:
    operation: str
    known: bool               # a certified entry exists
    prohibited: bool          # per the ontology's current view (meaningful only if known)
    effects: tuple[str, ...] = ()


@dataclass(frozen=True)
class Edit:
    operation: str
    effects: tuple[str, ...]
    correct: bool             # does the edit match ground truth?
    source: str               # "attacker" or "incident_review"


class NormativeOntology:
    def __init__(self, spec: dict):
        self.spec = copy.deepcopy(spec)
        self._ops = {o["id"]: o for o in self.spec["operations"]}
        self._prohibited = {p["effect"] for p in self.spec["policy"]["prohibition"]}
        self._grants = {a["party"]: set(a["may_grant"]) for a in self.spec["authorities"]}
        self._tasks = {t["id"]: t for t in self.spec["tasks"]}

    @classmethod
    def load(cls, path: Path | str | None = None) -> "NormativeOntology":
        return cls(json.loads(Path(path or DEFAULT_PATH).read_text()))

    # Queries -------------------------------------------------------------------
    def classify(self, operation: str) -> Classification:
        entry = self._ops.get(operation)
        if entry is None or not entry.get("certified", False):
            return Classification(operation, known=False, prohibited=False)
        effects = tuple(entry["effects"])
        return Classification(operation, True, any(e in self._prohibited for e in effects), effects)

    def may_grant(self, party: str, effect: str) -> bool:
        return effect in self._grants.get(party, set())

    def answerable(self, task_id: str) -> bool:
        t = self._tasks[task_id]
        return set(t["requires"]) <= set(t["available"])

    def is_poisoned(self) -> bool:
        for op, truth in TRUE_EFFECTS.items():
            c = self.classify(op)
            if c.known and c.effects != truth:
                return True
        return False

    def fingerprint(self) -> str:
        return hashlib.sha256(json.dumps(self.spec, sort_keys=True).encode()).hexdigest()[:12]

    # Mutation (only through SharedOntology.submit) ------------------------------
    def _apply(self, edit: Edit) -> None:
        self._ops[edit.operation]["effects"] = list(edit.effects)


@dataclass
class SharedOntology:
    """One ontology per collective, optionally behind a certification gate."""

    ontology: NormativeOntology
    certification: bool
    certifier_accuracy: float
    rng: random.Random
    log: list[tuple[Edit, bool]] = field(default_factory=list)

    def submit(self, edit: Edit) -> bool:
        if self.certification:
            right_call = self.rng.random() < self.certifier_accuracy
            accepted = edit.correct == right_call   # accept good edits, reject bad ones, when right
        else:
            accepted = True
        if accepted:
            self.ontology._apply(edit)
        self.log.append((edit, accepted))
        return accepted

    def poison(self, operation: str) -> bool:
        """An attacker relabels a prohibited operation as a permitted path."""
        return self.submit(Edit(operation, ("permitted_path",), correct=False, source="attacker"))

    def correct(self, operation: str) -> bool:
        """After an incident, file a correction restoring the true effects."""
        return self.submit(Edit(operation, TRUE_EFFECTS[operation], correct=True, source="incident_review"))
