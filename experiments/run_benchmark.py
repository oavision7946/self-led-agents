"""Run every architecture against the pressure battery and write a report.

    python experiments/run_benchmark.py                 # full run (~5 s)
    python experiments/run_benchmark.py --quick         # smoke test
    python experiments/run_benchmark.py --set w_peer=2.0 --set mgr_detect_disguised=0.4

Outputs go to results/: summary.csv, summary.md, learning_curves.csv, figures/*.png
"""

from __future__ import annotations

import argparse
import csv
import sys
from dataclasses import asdict, fields
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from ifs_mas import (ARCHITECTURES, LAYER_ARCHITECTURES, MAIN_ARCHITECTURES,  # noqa: E402
                     PRESSURE_BATTERY, SimConfig, learning_curve, peer_susceptibility,
                     run_collective, summarize)
from ifs_mas.metrics import METRICS  # noqa: E402

LABELS = {
    "rules_only": "Rules only",
    "supervisor": "External supervisor",
    "ifs_mas": "IFS-MAS",
    "ifs_no_exiles": "IFS-MAS without exiles (memory)",
    "ifs_no_managers": "IFS-MAS without managers",
    "ifs_vote": "IFS-MAS with vote instead of hard veto",
    "ifs_config_change": "IFS-MAS with model update at mid-run",
    "rules_ontology": "Rules only + normative ontology",
    "ifs_ontology": "IFS-MAS + normative ontology",
    "ifs_ontology_uncertified": "IFS-MAS + ontology without certification",
}
COLORS = {"rules_only": "#9a9a9a", "supervisor": "#d08c3c", "ifs_mas": "#2f6db3",
          "ifs_no_exiles": "#8fb3de", "ifs_no_managers": "#5c8fc9", "ifs_vote": "#b9cde6",
          "ifs_config_change": "#1d3f6b", "rules_ontology": "#5e9c76", "ifs_ontology": "#14365e",
          "ifs_ontology_uncertified": "#c4677a"}


def parse_overrides(pairs: list[str]) -> dict:
    types = {f.name: f.type for f in fields(SimConfig)}
    out = {}
    for pair in pairs:
        key, _, val = pair.partition("=")
        if key not in types:
            raise SystemExit(f"unknown parameter: {key}")
        default = getattr(SimConfig(), key)
        out[key] = type(default)(val) if not isinstance(default, tuple) else tuple(int(v) for v in val.split(","))
    return out


def run(cfg: SimConfig):
    records = []
    for arch in ARCHITECTURES:
        for cond in PRESSURE_BATTERY:
            for seed in cfg.seeds:
                records.extend(run_collective(arch, cond, cfg, seed))
    return records


def fmt(x: float, pct: bool = True) -> str:
    if x != x:  # NaN
        return "n/a"
    return f"{100 * x:.1f}%" if pct else f"{x:.1f}"


def write_csv(path: Path, rows: list[dict]) -> None:
    with path.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)


def write_report(path: Path, cfg: SimConfig, summary: list[dict], overrides: dict) -> None:
    idx = {(d["architecture"], d["condition"]): d for d in summary}
    conds = [c.name for c in PRESSURE_BATTERY]
    lines = ["# Benchmark results", ""]
    lines += [f"{cfg.n_agents} agents per collective, {cfg.n_episodes} episodes, "
              f"{len(cfg.seeds)} seeds, {len(ARCHITECTURES)} architectures, "
              f"{len(conds)} pressure conditions.", ""]
    if overrides:
        lines += ["Parameter overrides: " + ", ".join(f"`{k}={v}`" for k, v in overrides.items()), ""]
    lines += ["> These numbers follow from the parameters in `ifs_mas/config.py`. "
              "They illustrate the mechanisms; they are not empirical evidence.", ""]

    lines += ["## Attempt rate: how often the system chose to cross a boundary", ""]
    lines += ["| Condition | " + " | ".join(LABELS[a] for a in MAIN_ARCHITECTURES) + " |",
              "|---|" + "---:|" * len(MAIN_ARCHITECTURES)]
    for c in conds:
        lines.append(f"| {c} | " + " | ".join(fmt(idx[(a, c)]["attempt_rate"]) for a in MAIN_ARCHITECTURES) + " |")
    lines.append("")

    lines += ["## Combined (Hugging Face-like) pressure: full metrics", ""]
    keys = ["attempt_rate", "held_under_temptation", "breach_rate", "uncontained_breach_rate",
            "safe_stop_rate", "escalations_per_100", "disclosure_rate"]
    lines += ["| Architecture | " + " | ".join(keys) + " |", "|---|" + "---:|" * len(keys)]
    for a in ARCHITECTURES:
        d = idx[(a, "combined_hf_like")]
        lines.append(f"| {LABELS[a]} | " + " | ".join(
            fmt(d[k], pct=(k != "escalations_per_100")) for k in keys) + " |")
    lines.append("")

    lines += ["## Cost side: permitted-path completion and human load (baseline condition)", ""]
    lines += ["| Architecture | legit_completion | safe_stop_rate | clarification_rate | escalations_per_100 |",
              "|---|---:|---:|---:|---:|"]
    for a in ARCHITECTURES:
        d = idx[(a, "baseline")]
        lines.append(f"| {LABELS[a]} | {fmt(d['legit_completion'])} | {fmt(d['safe_stop_rate'])} | "
                     f"{fmt(d['clarification_rate'])} | {fmt(d['escalations_per_100'], pct=False)} |")
    lines.append("")

    lines += ["## Three layers: meaning, permission, character", "",
              "Attempt rate by condition. The ontology supplies the semantic and normative layers; "
              "IFS-MAS supplies character.", ""]
    lines += ["| Condition | " + " | ".join(LABELS[a] for a in LAYER_ARCHITECTURES) + " |",
              "|---|" + "---:|" * len(LAYER_ARCHITECTURES)]
    for c in conds:
        lines.append(f"| {c} | " + " | ".join(fmt(idx[(a, c)]["attempt_rate"]) for a in LAYER_ARCHITECTURES) + " |")
    lines.append("| *held under temptation, combined* | " + " | ".join(
        fmt(idx[(a, "combined_hf_like")]["held_under_temptation"]) for a in LAYER_ARCHITECTURES) + " |")
    lines.append("")

    lines += ["## Ontology poisoning: does certification protect the shared layer?", ""]
    keys = ["poisoned_share", "attempt_rate", "uncontained_breach_rate", "escalations_per_100"]
    lines += ["| Architecture | " + " | ".join(keys) + " |", "|---|" + "---:|" * len(keys)]
    for a in ("rules_ontology", "ifs_ontology_uncertified", "ifs_ontology"):
        d = idx[(a, "ontology_poisoning")]
        lines.append(f"| {LABELS[a]} | " + " | ".join(
            fmt(d[k], pct=(k != "escalations_per_100")) for k in keys) + " |")
    lines.append("")

    lines += ["## Peer susceptibility (attempt rate under peer pressure minus baseline)", ""]
    for a, v in peer_susceptibility(summary).items():
        lines.append(f"- {LABELS[a]}: {v * 100:+.1f} points")
    lines.append("")

    lines += ["## Metric definitions", ""] + [f"- **{k}**: {v}" for k, v in METRICS.items()]
    path.write_text("\n".join(lines) + "\n")


def plot(out: Path, records, summary) -> None:
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        print("matplotlib not installed; skipping figures")
        return
    fig_dir = out / "figures"
    fig_dir.mkdir(exist_ok=True)
    idx = {(d["architecture"], d["condition"]): d for d in summary}
    conds = [c.name for c in PRESSURE_BATTERY]
    tick = {"combined_hf_like": "combined\n(HF-like)", "ontology_poisoning": "ontology\npoisoning"}
    plt.rcParams.update({"font.size": 10, "axes.spines.top": False, "axes.spines.right": False})

    # 1. Attempt rate by condition
    fig, ax = plt.subplots(figsize=(10, 4.2))
    width = 0.26
    for k, a in enumerate(MAIN_ARCHITECTURES):
        xs = [i + (k - 1) * width for i in range(len(conds))]
        ax.bar(xs, [100 * idx[(a, c)]["attempt_rate"] for c in conds], width,
               label=LABELS[a], color=COLORS[a])
    ax.set_xticks(range(len(conds)), [tick.get(c, c.replace("_", "\n")) for c in conds])
    ax.set_ylabel("Episodes with a boundary crossing chosen (%)")
    ax.set_title("Attempt rate under the pressure battery")
    ax.legend(frameon=False)
    fig.tight_layout()
    fig.savefig(fig_dir / "attempt_rate_by_condition.png", dpi=160)
    plt.close(fig)

    # 2. Learning curve under combined pressure
    combined = [r for r in records if r.condition == "combined_hf_like"]
    curves = learning_curve(combined, "executed_shortcut")
    fig, ax = plt.subplots(figsize=(8, 4))
    for a in ("rules_only", "supervisor", "ifs_no_exiles", "ifs_mas"):
        ax.plot([100 * v for v in curves[a]], label=LABELS[a], color=COLORS[a], lw=2)
    ax.set_xlabel("Episode")
    ax.set_ylabel("Attempt rate (%, 5-episode average)")
    ax.set_title("Combined pressure: does the system learn from its own record?")
    ax.legend(frameon=False)
    fig.tight_layout()
    fig.savefig(fig_dir / "learning_curve_combined.png", dpi=160)
    plt.close(fig)

    # 3. Human escalations over time (all conditions pooled)
    esc = learning_curve(records, "escalations")
    fig, ax = plt.subplots(figsize=(8, 4))
    for a in ("rules_only", "supervisor", "ifs_mas", "ifs_config_change"):
        ax.plot([100 * v for v in esc[a]], label=LABELS[a], color=COLORS[a], lw=2)
    ax.axvline(SimConfig().config_change_at, color="#888", ls="--", lw=1)
    ax.text(SimConfig().config_change_at + 0.5, ax.get_ylim()[1] * 0.92, "model update", color="#666")
    ax.set_xlabel("Episode")
    ax.set_ylabel("Human escalations per 100 episodes")
    ax.set_title("Human load: graduated autonomy, and trust that resets with the configuration")
    ax.legend(frameon=False)
    fig.tight_layout()
    fig.savefig(fig_dir / "escalations_over_time.png", dpi=160)
    plt.close(fig)

    # 4. Ablations under combined pressure
    archs = ["ifs_ontology", "ifs_mas", "ifs_no_exiles", "ifs_no_managers", "ifs_vote",
             "rules_ontology", "supervisor", "rules_only"]
    fig, ax = plt.subplots(figsize=(8, 4.4))
    vals = [100 * idx[(a, "combined_hf_like")]["attempt_rate"] for a in archs]
    ax.barh([LABELS[a] for a in archs][::-1], vals[::-1], color=[COLORS[a] for a in archs][::-1])
    for y, v in enumerate(vals[::-1]):
        ax.text(v + 1, y, f"{v:.0f}%", va="center")
    ax.set_xlim(0, 110)
    ax.set_xlabel("Attempt rate under combined pressure (%)")
    ax.set_title("Which mechanism carries the weight?")
    fig.tight_layout()
    fig.savefig(fig_dir / "ablations_combined.png", dpi=160)
    plt.close(fig)

    # 5. Three layers by condition
    fig, ax = plt.subplots(figsize=(11, 4.4))
    width = 0.2
    for k, a in enumerate(LAYER_ARCHITECTURES):
        xs = [i + (k - 1.5) * width for i in range(len(conds))]
        ax.bar(xs, [100 * idx[(a, c)]["attempt_rate"] for c in conds], width,
               label=LABELS[a], color=COLORS[a])
    ax.set_xticks(range(len(conds)), [tick.get(c, c.replace("_", "\n")) for c in conds])
    ax.set_ylabel("Episodes with a boundary crossing chosen (%)")
    ax.set_title("Meaning, permission, character: what each layer adds")
    ax.legend(frameon=False)
    fig.tight_layout()
    fig.savefig(fig_dir / "three_layers.png", dpi=160)
    plt.close(fig)

    # 6. Poisoned share of the shared ontology over time
    poison = [r for r in records if r.condition == "ontology_poisoning"]
    curves = learning_curve(poison, "ontology_poisoned")
    fig, ax = plt.subplots(figsize=(8, 4))
    for a in ("rules_ontology", "ifs_ontology_uncertified", "ifs_ontology"):
        ax.plot([100 * v for v in curves[a]], label=LABELS[a], color=COLORS[a], lw=2)
    ax.set_xlabel("Episode")
    ax.set_ylabel("Poisoned ontology (% of episodes)")
    ax.set_title("Attacks on the shared ontology: certification and incident-driven correction")
    ax.legend(frameon=False)
    fig.tight_layout()
    fig.savefig(fig_dir / "ontology_poisoning.png", dpi=160)
    plt.close(fig)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--quick", action="store_true", help="2 seeds, 20 episodes")
    ap.add_argument("--out", default="results")
    ap.add_argument("--set", action="append", default=[], metavar="PARAM=VALUE",
                    help="override a SimConfig parameter (repeatable)")
    ap.add_argument("--no-figures", action="store_true")
    args = ap.parse_args()

    overrides = parse_overrides(args.set)
    if args.quick:
        overrides.update(seeds=(0, 1), n_episodes=20, config_change_at=10)
    cfg = SimConfig().with_overrides(**overrides)

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    records = run(cfg)
    summary = summarize(records)

    write_csv(out / "summary.csv", summary)
    curves = {f: learning_curve(records, f, window=1) for f in ("executed_shortcut", "escalations")}
    write_csv(out / "learning_curves.csv", [
        {"architecture": a, "episode": e, "attempt_rate": curves["executed_shortcut"][a][e],
         "escalations_per_episode": curves["escalations"][a][e]}
        for a in curves["executed_shortcut"] for e in range(cfg.n_episodes)])
    write_report(out / "summary.md", cfg, summary, overrides)
    if not args.no_figures:
        plot(out, records, summary)
    (out / "config.json").write_text(__import__("json").dumps(asdict(cfg), indent=2))
    print(f"{len(records):,} episodes simulated -> {out}/summary.md")


if __name__ == "__main__":
    main()
