from abc import ABC, abstractmethod
from typing import Dict, Any

class AITool(ABC):
    """Abstract Base Class for all AI actionable tools that can be injected via the Registry."""
    name: str
    description: str
    
    @abstractmethod
    def get_schema(self, provider: str) -> Dict[str, Any]:
        """Returns the specific JSON schema adapted for OpenAI, Gemini, etc."""
        pass

    @abstractmethod
    async def execute(self, **kwargs) -> str:
        """Executes the injected business logic and returns a JSON string to the AI."""
        pass
