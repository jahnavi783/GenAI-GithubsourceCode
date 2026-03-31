"""Base class for all repo metrics."""
from abc import ABC, abstractmethod


class BaseMetrics(ABC):

    @abstractmethod
    def compute(self, file_tree: list[str], key_file_contents: dict[str, str]) -> list[dict]:
        """
        Returns a list of metric dicts:
        [
            {"metric": "Lint Score", "value": "8.5/10", "status": "Good"},
            ...
        ]
        """
        pass

    def _status(self, score: float, good: float, warn: float) -> str:
        if score >= good:
            return "✅ Good"
        elif score >= warn:
            return "⚠️ Average"
        return "❌ Needs Attention"
