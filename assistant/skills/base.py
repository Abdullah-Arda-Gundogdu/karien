from abc import ABC, abstractmethod
from typing import Dict, Any, List

class Skill(ABC):
    @property
    @abstractmethod
    def name(self) -> str:
        pass

    @property
    @abstractmethod
    def description(self) -> str:
        pass

    @property
    def commands(self) -> List[str]:
        """List of command keys this skill handles."""
        return []

    @abstractmethod
    def execute(self, command: str, params: List[str]) -> bool:
        pass
