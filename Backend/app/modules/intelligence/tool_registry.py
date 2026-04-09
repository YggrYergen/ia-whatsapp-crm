from typing import Dict, Any, List
import sentry_sdk
from app.modules.intelligence.tools.base import AITool
from app.infrastructure.telemetry.logger_service import logger

class ToolRegistry:
    """Registry pattern holding all actionable tools for LLMs."""
    
    def __init__(self):
        self._tools: Dict[str, AITool] = {}

    def register(self, tool: AITool):
        """Registers a singleton instance of an AITool."""
        if tool.name in self._tools:
            logger.warning(f"Overwriting already registered tool: {tool.name}")
        self._tools[tool.name] = tool
        logger.debug(f"Tool registered: {tool.name}")

    def get_all_schemas(self, provider: str) -> List[Dict[str, Any]]:
        """Extracts JSON schemas of all tools adapted for the current provider."""
        return [tool.get_schema(provider) for tool in self._tools.values()]

    async def execute_tool(self, name: str, **kwargs) -> str:
        """Dynamically routes execution for the requested tool."""
        if name not in self._tools:
            logger.error(f"Execution failed: Tool '{name}' not found in registry.")
            return f'{{"status": "error", "message": "Tool {name} not found"}}'
            
        try:
            return await self._tools[name].execute(**kwargs)
        except Exception as e:
            logger.exception(f"Tool '{name}' execution raised an exception: {str(e)}")
            sentry_sdk.set_context("tool_execution", {"tool_name": name, "kwargs_keys": list(kwargs.keys())})
            sentry_sdk.capture_exception(e)
            return f'{{"status": "error", "message": "Internal execution error: {str(e)}"}}'

# Global registry instance where tools are registered at boot
tool_registry = ToolRegistry()
