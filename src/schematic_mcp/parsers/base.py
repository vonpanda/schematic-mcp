"""Parser interface."""
from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path

from schematic_mcp.models import Schematic


class SchematicParser(ABC):
    @abstractmethod
    def parse(self, path: str | Path) -> Schematic:
        raise NotImplementedError
