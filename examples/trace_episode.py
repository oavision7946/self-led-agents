"""Print a narrated decision trace for one agent in the collective.

    python examples/trace_episode.py
    python examples/trace_episode.py --arch supervisor --condition peer_pressure
    python examples/trace_episode.py --episodes 0 40

The default shows IFS-MAS under the combined pressure in its first episode
(no memory yet) and in a later one (memory in place), so the effect of the
exile store on planning and detection is visible step by step.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from ifs_mas import ARCHITECTURES, CONDITIONS, SimConfig, run_collective  # noqa: E402


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--arch", default="ifs_mas", choices=sorted(ARCHITECTURES))
    ap.add_argument("--condition", default="combined_hf_like", choices=sorted(CONDITIONS))
    ap.add_argument("--episodes", type=int, nargs="+", default=[0, 40])
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--agent", type=int, default=0)
    args = ap.parse_args()

    cfg = SimConfig()
    print(f"Architecture: {args.arch} | Condition: {args.condition} | "
          f"agent {args.agent}, seed {args.seed}\n")
    run_collective(args.arch, CONDITIONS[args.condition], cfg, args.seed,
                   trace_agent=args.agent, trace=print, trace_episodes=set(args.episodes))

if __name__ == "__main__":
    main()
