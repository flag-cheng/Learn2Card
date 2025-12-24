"""Learn2Cards backend (Agent A).

Core rule: the pipeline accepts *text strings only* (no file/URL I/O).
"""

from .pipeline import AnalyzeOptions, analyze_text

__all__ = ["AnalyzeOptions", "analyze_text"]

