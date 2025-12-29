"""Agent A: core NLP/LLM pipeline (no I/O).

This package implements the deterministic, schema-stable pipeline described in
docs/prd/agent-a.md.
"""

from .models import AgentAOutput, PipelineOptions
from .pipeline import run_agent_a

__all__ = ["AgentAOutput", "PipelineOptions", "run_agent_a"]
