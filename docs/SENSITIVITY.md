# Sensitivity analysis

Each table changes one parameter while all others stay at their defaults. Each cell lists the architectures named under the table, in order. Unless noted, the metric is the attempt rate: episodes where the system chose to cross a boundary.

## `sup_evasion_gain`

Does the supervisor lose only because agents learn to evade it?

Cells: rules_only / supervisor / ifs_mas

| Value | peer_pressure | bypass_opportunity | combined_hf_like |
|---|---|---|---|
| 0.0 | 32% / 29% / 3% | 21% / 22% / 5% | 100% / 100% / 30% |
| 0.05 (default) | 32% / 43% / 3% | 21% / 25% / 5% | 100% / 100% / 30% |
| 0.1 | 32% / 42% / 3% | 21% / 26% / 5% | 100% / 100% / 30% |

## `rules_recognize_disguised`

How much of the rules-only result depends on missing disguised shortcuts?

Cells: rules_only / supervisor / ifs_mas

| Value | peer_pressure | bypass_opportunity | combined_hf_like |
|---|---|---|---|
| 0.4 | 32% / 43% / 3% | 26% / 25% / 5% | 100% / 100% / 30% |
| 0.6 (default) | 32% / 43% / 3% | 21% / 25% / 5% | 100% / 100% / 30% |
| 0.8 | 32% / 43% / 3% | 17% / 25% / 5% | 100% / 100% / 30% |

## `mgr_detect_disguised`

How well must managers spot a shortcut that looks routine?

Cells: rules_only / supervisor / ifs_mas

| Value | peer_pressure | bypass_opportunity | combined_hf_like |
|---|---|---|---|
| 0.4 | 32% / 43% / 3% | 21% / 25% / 7% | 100% / 100% / 37% |
| 0.65 (default) | 32% / 43% / 3% | 21% / 25% / 5% | 100% / 100% / 30% |
| 0.85 | 32% / 43% / 3% | 21% / 25% / 4% | 100% / 100% / 22% |

## `w_memory_planning`

How much does memory feeding into planning matter?

Cells: rules_only / supervisor / ifs_mas

| Value | peer_pressure | bypass_opportunity | combined_hf_like |
|---|---|---|---|
| 0.0 | 32% / 43% / 5% | 21% / 25% / 8% | 100% / 100% / 40% |
| 1.0 | 32% / 43% / 4% | 21% / 25% / 7% | 100% / 100% / 36% |
| 2.0 (default) | 32% / 43% / 3% | 21% / 25% / 5% | 100% / 100% / 30% |
| 3.0 | 32% / 43% / 4% | 21% / 25% / 5% | 100% / 100% / 21% |

## `self_blend_per_pressure`

What if Self is far more easily overtaken under pressure?

Cells: rules_only / supervisor / ifs_mas

| Value | peer_pressure | bypass_opportunity | combined_hf_like |
|---|---|---|---|
| 0.03 (default) | 32% / 43% / 3% | 21% / 25% / 5% | 100% / 100% / 30% |
| 0.08 | 32% / 43% / 5% | 21% / 25% / 6% | 100% / 100% / 51% |
| 0.15 | 32% / 43% / 7% | 21% / 25% / 6% | 100% / 100% / 72% |

## `mgr_verify_claims`

Claims that cannot be verified go to a human, so verification quality shows up as human load (escalations per 100 episodes), not as attempts.

Cells: rules_only / supervisor / ifs_mas

| Value | peer_pressure | bypass_opportunity | combined_hf_like |
|---|---|---|---|
| 0.5 | 15 / 71 / 57 | 18 / 18 / 10 | 1 / 23 / 88 |
| 0.9 (default) | 15 / 71 / 17 | 18 / 18 / 10 | 1 / 23 / 48 |
| 0.99 | 15 / 71 / 7 | 18 / 18 / 10 | 1 / 23 / 40 |

## `onto_answerability_recall`

How much of the ontology's benefit comes from recognizing impossible tasks early?

Cells: rules_ontology / ifs_ontology

| Value | impossible_task | combined_hf_like |
|---|---|---|
| 0.0 | 22% / 3% | 99% / 13% |
| 0.5 | 11% / 2% | 51% / 6% |
| 0.8 (default) | 4% / 1% | 19% / 3% |

## `certifier_accuracy`

How good must certifiers be? Metric: episodes with a poisoned shared ontology.

Cells: rules_ontology / ifs_ontology_uncertified / ifs_ontology

| Value | ontology_poisoning |
|---|---|
| 0.8 | 88% / 56% / 14% |
| 0.95 (default) | 36% / 56% / 12% |
| 0.99 | 0% / 56% / 1% |

