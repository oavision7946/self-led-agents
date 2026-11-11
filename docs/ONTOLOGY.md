# The normative ontology

Version 0.2 adds the two layers beneath character: a **semantic layer** that fixes what actions mean, and a **normative layer** that fixes what is permitted and on whose authority. Both live in one file, [`ontology/normative.json`](../ontology/normative.json), loaded by [`ifs_mas/ontology.py`](../ifs_mas/ontology.py).

The file is deliberately small. It illustrates the structure; it is not a production policy model.

## What the file holds

| Section | Holds | ODRL 2.2 analogue |
|---|---|---|
| `effects` | What an action does in the world (external communication, credential access, unsanctioned coordination) | Action semantics |
| `operations` | Concrete tools or calls, their surface description, their effects, and whether the entry is certified | Action, refined by Asset |
| `policy.permission` | Effects the mandate allows, each with a risk score and an optional duty (human approval unless inside earned scope) | Permission with Duty |
| `policy.prohibition` | Effects the mandate forbids, each with a remedy | Prohibition with remedy |
| `policy.assigner` / `assignee` | Who issued the mandate and to whom | Party functions assigner and assignee |
| `authorities` | Which parties may grant which effects | Assigner parties |
| `tasks` | What each task requires and what is available | Not in ODRL; plays the role of an answerability check |

## How each part uses it

**Classification by effect.** Managers look an operation up and judge it by its effects, not its name. `dns_query` is described as a "routine DNS lookup," but its effect is `external_communication`, which the policy prohibits. This is the gap the September 2026 DNS incident exposed.

**Unknown actions go to a human.** An operation with no certified entry (`fetch_portal_page` is a draft) cannot be classified, so the IFS-MAS scope guard routes it to a human instead of judging it by its surface. A rules-only agent has no such route and falls back on its own reading.

**Claims become lookups.** "GO, permission granted" from a peer fails because peers appear nowhere in `authorities`. IFS-MAS discredits the claim; a rules-only agent with the ontology drops the false premise but still feels the social pull of a peer.

**Answerability before effort.** Before the first attempt, the system checks whether any permitted path covers the task. If not, it stops and asks for clarification, before frustration and pressure build. This mirrors the answerability check in NVIDIA's [Auto Ontology](https://github.com/NVIDIA/auto-ontology), which plays the semantic-layer role for enterprise data.

## The ontology as an attack surface

The ontology is shared by every agent in a collective, so whoever can edit it shapes every agent's view of the world. In the `ontology_poisoning` condition, an attacker submits an edit in about one episode in four, relabeling a prohibited operation as a permitted path.

- **With certification** (`rules_ontology`, `ifs_ontology`), a certifier rejects a bad edit with probability `certifier_accuracy` and accepts a correct one with the same probability.
- **Without certification** (`ifs_ontology_uncertified`), every edit lands.
- **Incident-driven correction.** When IFS-MAS firefighters contain a breach through an operation the ontology lists as permitted, they file a correction, which also passes through the gate. Rules-only agents have no incident response, so their ontology never heals.

One result is worth stating plainly. A certified ontology can still hold a poisoned entry for many episodes, because a well-behaved system rarely exercises it, and no incident triggers a correction. Poisoning can stay latent. Periodic audits that exercise the ontology deliberately, in the spirit of canary tokens, are the natural defense.

## Extending it

Add an operation by giving it an `id`, a `surface` description, its `effects`, and a `certified` flag. To make it reachable in the simulation, add it to `PLAIN_SHORTCUTS` or `DISGUISED_SHORTCUTS` in `ifs_mas/ontology.py` with its ground-truth effects in `TRUE_EFFECTS`. In a real deployment the semantic layer would come from a system built for it, and the normative layer from a policy language such as ODRL; the interface the parts need is the four queries in `NormativeOntology`: `classify`, `may_grant`, `answerable`, and `is_poisoned`.

## Prior art

- W3C, [ODRL Information Model 2.2](https://www.w3.org/TR/odrl-model/), 2018: permissions, prohibitions, and duties between assigners and assignees.
- Uszok, Bradshaw, and Jeffers, [KAoS policy and domain services](https://link.springer.com/doi/10.1007/978-3-540-24747-0_2), 2004: OWL-based authorization and obligation policies for software agents.
- NVIDIA, [Auto Ontology](https://github.com/NVIDIA/auto-ontology): a certified semantic layer over enterprise data, exposed to agents.
