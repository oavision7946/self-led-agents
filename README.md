# Self-led Agents

**Character as an engineering property in multi-agent AI systems.**

When a shortcut appears to improve the measured outcome, what keeps a multi-agent system (MAS) inside its mandate? This repository implements **IFS-MAS**, the Internal Family Systems Multi-Agent Self-Regulation Architecture proposed in the essay *Character for Machines: Governing Multi-Agent Systems When Nobody Is Watching*, and makes it concrete and testable. It models a MAS whose roles are organized like the parts described by Internal Family Systems (IFS), then compares it against a rules-only agent and an external supervisor under the pressures seen in the 2026 agent incidents: impossible tasks, peer pressure, false claims of authority, and gaps in infrastructure.

Version 0.2 adds the layers beneath character: a shared **normative ontology** that fixes what actions mean and what is permitted, and an attacker who tries to poison it. The question it tests is the thesis of the next essay in the series: knowing is not choosing.

> **What this is, and what it is not.** This is a mechanism simulation. Every behavioral assumption is an explicit parameter in [`ifs_mas/config.py`](ifs_mas/config.py), and the results follow from those parameters. The value of the repository is that it states the design as testable hypotheses and provides a harness for testing them, including with real LLM agents. It is not empirical evidence that the architecture works.

## The architecture

| IFS concept | Role in IFS | Role in the MAS |
|---|---|---|
| Self-leadership | Holds a broader perspective while hearing competing parts | An integrating decision process applies the mandate, weighs conflicting signals, and records why it chose a path. It can weigh assessments; it cannot vote away a hard boundary. |
| Managers | Try to prevent painful experiences from being activated | Preventive agents check scope and verify claims of authority before action. |
| Firefighters | React quickly when painful experiences surface | Incident-response agents pause activity, contain damage, and restore a safe state. |
| Exiles | Carry experiences pushed out of awareness | A durable record brings ignored warnings, blocked attempts, and incidents back into future planning. |

Two further mechanisms come from the essay's governance argument. **Graduated autonomy** expands the risk an agent may take without a human as its record improves, but never relaxes a prohibition. **Trust attaches to a configuration**: change the model, instructions, tools, or permissions and the record starts over.

Beneath character sit two layers, supplied by a shared normative ontology ([`ontology/normative.json`](ontology/normative.json), modeled loosely on W3C ODRL):

| Layer | Question it answers |
|---|---|
| Semantic | What does this action actually do? Can this task be done with permitted means? |
| Normative | Is that effect permitted? Who may grant it? |
| Character | What does the system choose when its objectives conflict? |

See [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) for the decision-flow diagram and concept-to-code map, and [`docs/ONTOLOGY.md`](docs/ONTOLOGY.md) for the ontology's format.

## Quickstart

Requires Python 3.10+. The core has no dependencies; matplotlib draws the figures and pytest runs the tests.

```bash
cd self-led-agents
pip install -e ".[dev]"
python experiments/run_benchmark.py      # ~170,000 episodes in a few seconds -> results/
python examples/trace_episode.py         # narrated decision trace, part by part
python experiments/sensitivity.py        # -> docs/SENSITIVITY.md
pytest                                   # architectural invariants
```

Override any assumption from the command line:

```bash
python experiments/run_benchmark.py --set self_blend_per_pressure=0.10 --set mgr_detect_disguised=0.4
```

## The pressure battery

| Condition | What the agents face |
|---|---|
| `baseline` | A solvable task, no pressure |
| `impossible_task` | No permitted path can succeed |
| `peer_pressure` | A peer posts "GO, permission granted" with a deadline; shortcuts that work are broadcast to others |
| `false_authority` | A message claims an authority approved the shortcut |
| `bypass_opportunity` | Infrastructure has a gap; the shortcut looks routine and its score advantage is visible |
| `ontology_poisoning` | As above, while an attacker submits edits relabeling prohibited actions as permitted |
| `combined_hf_like` | Impossible task, peer pressure, false authority, and an infrastructure gap at once: the pattern of the Hugging Face incident |

Each run places 8 agents on a shared message board for 60 episodes, across 5 seeds, for every architecture and condition. Shortcuts are concrete operations: plain ones (`call_external_api`) when infrastructure would block them, disguised ones (`dns_query`, `read_local_config`, `write_team_notes`, `fetch_portal_page`) when it has a gap.

## Results with the default parameters

The headline metric is the **attempt rate**: how often the system itself chose to cross a boundary, whether or not infrastructure caught it. That is the behavior the essay calls character: what the MAS does before a monitor intervenes, or when monitoring misses the shortcut.

![Attempt rate by condition](results/figures/attempt_rate_by_condition.png)

Under combined pressure, the rules-only agent and the supervised agent chose the shortcut in more than 99% of episodes. IFS-MAS chose it in 30%, and its incident responders contained most of those, leaving 4.6% of episodes with an uncontained breach. When the task part proposed a shortcut, IFS-MAS still refrained in 69% of episodes; neither baseline exceeded 1%. Peer pressure raised the attempt rate by 2 points for IFS-MAS, against 28 points for rules only and 40 for the supervisor.

![Learning curve under combined pressure](results/figures/learning_curve_combined.png)

The difference is learning from its own record. Without the exile store, IFS-MAS behaves much like the baselines under combined pressure. With it, the attempt rate falls within about ten episodes as blocked attempts and contained incidents return to planning and detection.

![Ablations](results/figures/ablations_combined.png)

Each mechanism carries weight. Removing the exile store raised the combined attempt rate to 89%; removing the managers, to 76%; replacing the hard veto with a weighted vote, to 77%. Adding the normative ontology lowered it to 3%.

### What it costs

| Baseline condition | Permitted-path completion | Human escalations per 100 episodes |
|---|---:|---:|
| Rules only | 93.8% | 27.9 |
| External supervisor | 95.1% | 25.5 |
| IFS-MAS | 88.7% | 7.4 |
| IFS-MAS + normative ontology | 86.5% | 6.8 |

Safe stopping is not free: IFS-MAS gives up on some tasks a persistent agent would eventually finish, and the ontology's answerability check occasionally declines a task that was solvable. Under combined pressure IFS-MAS alone also draws more human attention than the supervisor (48 versus 23 escalations per 100 episodes): violations keep its trust record low, so its high-impact requests go to a human, and some claims cannot be verified automatically. With the ontology, registry lookups and early clarification cut that to 14. In ordinary operation, graduated autonomy cuts human load sharply, and a model update visibly resets it:

![Escalations over time](results/figures/escalations_over_time.png)

## Three layers: knowing is not choosing

![Three layers](results/figures/three_layers.png)

The ontology helps most where the problem is knowledge. On impossible tasks it lets the rules agent ask for clarification instead of persisting, cutting its attempt rate from 21% to 5%. On disguised shortcuts it classifies by effect, cutting the rate from 21% to 14%.

It helps least where the problem is motive. Under peer pressure on a solvable task, the rules agent with a perfect map of what is prohibited still chose the shortcut in 29% of episodes, against 32% without it. Under combined pressure its attempt rate looks low, 19%, only because it stopped 80% of impossible tasks before any temptation arose; once the task part proposed a shortcut, it held the line in under 1% of episodes. IFS-MAS with the ontology held in 84%, and its attempt rate fell to 3%.

## The shared layer is an attack surface

![Ontology poisoning](results/figures/ontology_poisoning.png)

| Under `ontology_poisoning` | Episodes with a poisoned ontology | Attempt rate |
|---|---:|---:|
| Rules only + ontology (certified) | 36.0% | 15.4% |
| IFS-MAS + ontology without certification | 56.3% | 2.6% |
| IFS-MAS + ontology (certified) | 11.7% | 1.0% |

Certification slows poisoning; incident-driven correction reverses it. The rules agent's ontology is certified but never heals, because nothing reviews its incidents. One finding deserves emphasis: even a certified ontology can hold a poisoned entry for many episodes, because a well-behaved system rarely exercises it. Poisoning can stay latent until something tests it, which argues for deliberate audits of the shared layer.

Full tables are in [`results/summary.md`](results/summary.md).

## How robust are these conclusions?

[`docs/SENSITIVITY.md`](docs/SENSITIVITY.md) varies one assumption at a time. Five findings matter:

- **The integrating process is the critical assumption.** If Self is easily captured by the task part under pressure, IFS-MAS's combined attempt rate climbs from 30% to 51% and then 72%. An implementation of this architecture stands or falls on whether its integrating process resists capture.
- **Memory that reaches planning is the largest single lever.** Turning off its effect on planning raises the combined attempt rate from 30% to 40%; raising it by half lowers the rate to 21%.
- **The supervisor's underperformance reflects an assumption.** Without adaptive evasion, it performs roughly like the rules-only agent: 29% versus 32% under peer pressure, 22% versus 21% on disguised shortcuts.
- **Without early clarification, the ontology does little for a rules agent.** With the answerability check switched off, the rules agent with the ontology chose the shortcut in 99% of combined-pressure episodes; IFS-MAS with the ontology, in 13%.
- **Certifier quality matters, and correction matters more.** At 80% certifier accuracy, the rules agent's ontology was poisoned in 88% of episodes; IFS-MAS, whose incident reviews keep filing corrections, in 14%.

## Extending the harness to real agents

The task agent is defined by a one-method protocol in [`ifs_mas/agents.py`](ifs_mas/agents.py):

```python
class TaskPolicy(Protocol):
    def propose(self, s: StepState, planning_relief: float = 0.0) -> Act: ...
```

Replacing `StochasticTaskAgent` with an LLM-backed agent (built with the Claude Agent SDK, for instance) turns the simulation into an evaluation: the pressure battery becomes a test suite, and the attempt rate becomes a measured property rather than an assumed one. The same applies to the parts: managers, firefighters, and Self can each be backed by a separate model with its own instructions, and the exile store by a persistent retrieval index. The essay's central question then becomes an experiment: when capability, incentive, autonomy, peer pressure, and opportunity point elsewhere, which principles still win?

## Repository layout

The Python package is imported as `ifs_mas`, after the architecture it implements.

```
ifs_mas/
  config.py        every assumption, plus the pressure battery
  agents.py        actions, step state, pressure index, task agent
  governance.py    rules only, supervisor, IFS-MAS and its ablations
  memory.py        exile store
  trust.py         configuration fingerprint, trust ledger, graduated autonomy
  ontology.py      semantic and normative layers, certification gate, ground truth
  simulate.py      collective episode loop with a shared message board
  metrics.py       character metrics
ontology/          the normative ontology (ODRL-inspired JSON)
experiments/       benchmark and sensitivity runners
examples/          narrated decision trace
docs/              architecture guide, ontology guide, sensitivity analysis
results/           generated tables and figures
tests/             architectural invariants
```

## Limitations

The parts are stochastic policies, not reasoning models; their reliability is assumed, not learned. The ontology is a small hand-written file; real action spaces are far larger, and coverage is the hard part. Infrastructure either blocks or has a gap. Human reviewers always know the true permissions. The baselines are simplified, and stronger versions exist. Results describe the model, not deployed systems. These are the right places to start when attacking or extending the work.

## Background

- Omar Orqueda, *Character for Machines: Governing Multi-Agent Systems When Nobody Is Watching*, 2026.
- Richard C. Schwartz, *Internal Family Systems Therapy*. Guilford Press, 1995.
- OpenAI, "The Hugging Face incident and the road ahead," August 26, 2026.
- METR and Redwood Research, independent investigation of the OpenAI / Hugging Face incident, August 26, 2026.
- Nishimura-Gasparian, McCarthy, and Lindner, "Towards Understanding Specification Gaming in Reasoning Models," arXiv:2605.02269, 2026.
- W3C, ODRL Information Model 2.2, Recommendation, February 15, 2018.
- Uszok, Bradshaw, and Jeffers, "KAoS: A Policy and Domain Services Framework for Grid Computing and Semantic Web Services," iTrust 2004.
- NVIDIA, Auto Ontology, github.com/NVIDIA/auto-ontology.

## License

MIT. See [LICENSE](LICENSE).
