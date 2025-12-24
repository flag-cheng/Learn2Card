"""Learn2Cards backend package (Agent A).

This package implements the core text-to-deck pipeline (pure text in, JSON-ready out),
plus CLI utilities and a small API server.
"""

from .models import Deck, DeckOptions  # re-export

__all__ = ["Deck", "DeckOptions"]

