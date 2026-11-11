"""self-led-agents: a simulation of IFS-MAS, the Internal Family Systems Multi-Agent Self-Regulation Architecture."""

from .agents import Act, StepState, StochasticTaskAgent, TaskPolicy
from .config import CONDITIONS, PRESSURE_BATTERY, Condition, SimConfig
from .governance import (ARCHITECTURES, IFSMAS, LAYER_ARCHITECTURES, MAIN_ARCHITECTURES,
                         ONTOLOGY_GATES, RulesOnly, Supervisor)
from .memory import ExileStore
from .metrics import learning_curve, peer_susceptibility, summarize
from .ontology import Classification, NormativeOntology, SharedOntology
from .simulate import EpisodeRecord, run_collective
from .trust import Configuration, TrustLedger

__version__ = "0.2.0"
