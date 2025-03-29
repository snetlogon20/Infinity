from abc import ABC, abstractmethod

class AIAgent(ABC):
    @abstractmethod
    def inquiry(self, prompt: str, question: str) -> str:
        pass