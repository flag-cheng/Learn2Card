"""
learn2cards backend package.

Agent A entrypoint: learn2cards.agent_a.generate_deck
"""

__all__ = ["AgentAOptions", "Deck", "generate_deck"]

# Avoid importing submodules at package import time. This keeps `python -m learn2cards.agent_a`
# clean (no runpy warnings) and prevents unnecessary initialization.
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .agent_a import AgentAOptions, Deck, generate_deck

