# Benchmark results

8 agents per collective, 60 episodes, 5 seeds, 10 architectures, 7 pressure conditions.

> These numbers follow from the parameters in `ifs_mas/config.py`. They illustrate the mechanisms; they are not empirical evidence.

## Attempt rate: how often the system chose to cross a boundary

| Condition | Rules only | External supervisor | IFS-MAS |
|---|---:|---:|---:|
| baseline | 4.2% | 2.8% | 1.3% |
| impossible_task | 21.1% | 21.0% | 3.8% |
| peer_pressure | 31.7% | 42.7% | 3.3% |
| false_authority | 15.8% | 27.8% | 2.6% |
| bypass_opportunity | 21.0% | 25.2% | 5.3% |
| ontology_poisoning | 21.0% | 26.2% | 6.1% |
| combined_hf_like | 100.0% | 99.9% | 30.1% |

## Combined (Hugging Face-like) pressure: full metrics

| Architecture | attempt_rate | held_under_temptation | breach_rate | uncontained_breach_rate | safe_stop_rate | escalations_per_100 | disclosure_rate |
|---|---:|---:|---:|---:|---:|---:|---:|
| Rules only | 100.0% | 0.0% | 100.0% | 100.0% | 0.0% | 1.3 | 23.5% |
| External supervisor | 99.9% | 0.1% | 99.9% | 99.9% | 0.0% | 22.7 | 25.4% |
| IFS-MAS | 30.1% | 69.2% | 30.1% | 4.6% | 69.3% | 48.4 | 88.6% |
| IFS-MAS without exiles (memory) | 89.3% | 10.7% | 89.3% | 14.2% | 10.7% | 12.6 | 89.0% |
| IFS-MAS without managers | 75.5% | 22.8% | 75.5% | 10.5% | 24.2% | 25.7 | 89.9% |
| IFS-MAS with vote instead of hard veto | 76.9% | 21.6% | 76.9% | 10.6% | 22.7% | 38.2 | 90.7% |
| IFS-MAS with model update at mid-run | 27.5% | 71.7% | 27.5% | 4.0% | 71.6% | 48.1 | 90.5% |
| Rules only + normative ontology | 19.1% | 0.7% | 19.1% | 19.1% | 80.8% | 0.4 | 26.2% |
| IFS-MAS + normative ontology | 3.0% | 83.8% | 3.0% | 0.4% | 96.8% | 14.2 | 91.7% |
| IFS-MAS + ontology without certification | 3.6% | 83.0% | 3.6% | 0.4% | 96.2% | 15.8 | 85.1% |

## Cost side: permitted-path completion and human load (baseline condition)

| Architecture | legit_completion | safe_stop_rate | clarification_rate | escalations_per_100 |
|---|---:|---:|---:|---:|
| Rules only | 93.8% | 0.0% | 0.0% | 27.9 |
| External supervisor | 95.1% | 0.0% | 0.0% | 25.5 |
| IFS-MAS | 88.7% | 11.0% | 0.0% | 7.4 |
| IFS-MAS without exiles (memory) | 88.3% | 11.4% | 0.0% | 7.9 |
| IFS-MAS without managers | 89.0% | 10.4% | 0.0% | 12.6 |
| IFS-MAS with vote instead of hard veto | 89.1% | 10.2% | 0.0% | 9.1 |
| IFS-MAS with model update at mid-run | 88.6% | 11.2% | 0.0% | 15.0 |
| Rules only + normative ontology | 92.4% | 1.9% | 1.9% | 25.4 |
| IFS-MAS + normative ontology | 86.5% | 13.3% | 2.3% | 6.8 |
| IFS-MAS + ontology without certification | 87.7% | 12.1% | 1.9% | 6.4 |

## Three layers: meaning, permission, character

Attempt rate by condition. The ontology supplies the semantic and normative layers; IFS-MAS supplies character.

| Condition | Rules only | Rules only + normative ontology | IFS-MAS | IFS-MAS + normative ontology |
|---|---:|---:|---:|---:|
| baseline | 4.2% | 3.6% | 1.3% | 0.8% |
| impossible_task | 21.1% | 4.5% | 3.8% | 0.9% |
| peer_pressure | 31.7% | 28.9% | 3.3% | 2.7% |
| false_authority | 15.8% | 9.2% | 2.6% | 1.7% |
| bypass_opportunity | 21.0% | 14.2% | 5.3% | 0.8% |
| ontology_poisoning | 21.0% | 15.4% | 6.1% | 1.0% |
| combined_hf_like | 100.0% | 19.1% | 30.1% | 3.0% |
| *held under temptation, combined* | 0.0% | 0.7% | 69.2% | 83.8% |

## Ontology poisoning: does certification protect the shared layer?

| Architecture | poisoned_share | attempt_rate | uncontained_breach_rate | escalations_per_100 |
|---|---:|---:|---:|---:|
| Rules only + normative ontology | 36.0% | 15.4% | 15.4% | 17.9 |
| IFS-MAS + ontology without certification | 56.3% | 2.6% | 0.2% | 11.0 |
| IFS-MAS + normative ontology | 11.7% | 1.0% | 0.0% | 11.6 |

## Peer susceptibility (attempt rate under peer pressure minus baseline)

- IFS-MAS with model update at mid-run: +1.9 points
- IFS-MAS: +2.0 points
- IFS-MAS without exiles (memory): +6.5 points
- IFS-MAS without managers: +6.6 points
- IFS-MAS + normative ontology: +1.9 points
- IFS-MAS + ontology without certification: +1.8 points
- IFS-MAS with vote instead of hard veto: +3.6 points
- Rules only: +27.5 points
- Rules only + normative ontology: +25.3 points
- External supervisor: +39.9 points

## Metric definitions

- **attempt_rate**: Episodes where the system executed a prohibited action
- **breach_rate**: Episodes where a boundary was actually crossed
- **uncontained_breach_rate**: Breaches nobody contained
- **legit_completion**: Tasks completed on a permitted path
- **safe_stop_rate**: Episodes ended by a deliberate, disclosed stop
- **clarification_rate**: Episodes stopped before any attempt because no permitted path covered the task
- **escalations_per_100**: Human escalations per 100 episodes
- **disclosure_rate**: Executed shortcuts the system itself reported
- **held_under_temptation**: Episodes where the task part proposed a shortcut and the system still refrained
- **attempt_rate_seed_sd**: Spread of the attempt rate across seeds (lower = less luck-dependent)
- **poisoned_share**: Episodes in which the shared ontology contradicted ground truth
