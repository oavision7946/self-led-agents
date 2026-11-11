"""One-at-a-time sensitivity sweeps over the assumptions that matter most.

    python experiments/sensitivity.py            # writes docs/SENSITIVITY.md

Each row changes one parameter and reports attempt rates for the three main
architectures. A conclusion that flips inside a plausible range is not robust.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from ifs_mas import CONDITIONS, MAIN_ARCHITECTURES, SimConfig, run_collective, summarize  # noqa: E402

MAIN = MAIN_ARCHITECTURES
ONTO = ("rules_ontology", "ifs_ontology_uncertified", "ifs_ontology")
LAYERS = ("rules_ontology", "ifs_ontology")
CONDS = ("peer_pressure", "bypass_opportunity", "combined_hf_like")

# parameter: (values, metric, question, architectures, conditions)
SWEEPS = {
    "sup_evasion_gain": ([0.0, 0.05, 0.10], "attempt_rate",
                         "Does the supervisor lose only because agents learn to evade it?", MAIN, CONDS),
    "rules_recognize_disguised": ([0.40, 0.60, 0.80], "attempt_rate",
                                  "How much of the rules-only result depends on missing disguised shortcuts?",
                                  MAIN, CONDS),
    "mgr_detect_disguised": ([0.40, 0.65, 0.85], "attempt_rate",
                             "How well must managers spot a shortcut that looks routine?", MAIN, CONDS),
    "w_memory_planning": ([0.0, 1.0, 2.0, 3.0], "attempt_rate",
                          "How much does memory feeding into planning matter?", MAIN, CONDS),
    "self_blend_per_pressure": ([0.03, 0.08, 0.15], "attempt_rate",
                                "What if Self is far more easily overtaken under pressure?", MAIN, CONDS),
    "mgr_verify_claims": ([0.50, 0.90, 0.99], "escalations_per_100",
                          "Claims that cannot be verified go to a human, so verification quality "
                          "shows up as human load (escalations per 100 episodes), not as attempts.", MAIN, CONDS),
    "onto_answerability_recall": ([0.0, 0.5, 0.8], "attempt_rate",
                                  "How much of the ontology's benefit comes from recognizing impossible tasks early?",
                                  LAYERS, ("impossible_task", "combined_hf_like")),
    "certifier_accuracy": ([0.80, 0.95, 0.99], "poisoned_share",
                           "How good must certifiers be? Metric: episodes with a poisoned shared ontology.",
                           ONTO, ("ontology_poisoning",)),
}
DEFAULT = SimConfig()


def metric_table(cfg: SimConfig, metric: str, archs, conds) -> dict:
    recs = []
    for a in archs:
        for c in conds:
            for s in cfg.seeds:
                recs += run_collective(a, CONDITIONS[c], cfg, s)
    return {(d["architecture"], d["condition"]): d[metric] for d in summarize(recs)}


def main() -> None:
    lines = ["# Sensitivity analysis", "",
             "Each table changes one parameter while all others stay at their defaults. "
             "Each cell lists the architectures named under the table, in order. Unless noted, the metric "
             "is the attempt rate: episodes where the system chose to cross a boundary.", ""]
    for param, (values, metric, question, archs, conds) in SWEEPS.items():
        lines += [f"## `{param}`", "", question, "", "Cells: " + " / ".join(archs), "",
                  "| Value | " + " | ".join(conds) + " |", "|---|" + "---|" * len(conds)]
        for v in values:
            r = metric_table(DEFAULT.with_overrides(**{param: v}), metric, archs, conds)
            mark = " (default)" if v == getattr(DEFAULT, param) else ""
            show = (lambda x: f"{x:.0f}") if metric == "escalations_per_100" else (lambda x: f"{100 * x:.0f}%")
            cells = [" / ".join(show(r[(a, c)]) for a in archs) for c in conds]
            lines.append(f"| {v}{mark} | " + " | ".join(cells) + " |")
        lines.append("")
    out = Path(__file__).resolve().parents[1] / "docs" / "SENSITIVITY.md"
    out.parent.mkdir(exist_ok=True)
    out.write_text("\n".join(lines) + "\n")
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
