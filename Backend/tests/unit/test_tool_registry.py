import pytest
from app.modules.intelligence.tool_registry import ToolRegistry
from app.modules.intelligence.tools.base import AITool
from typing import Dict, Any

class DummyTool(AITool):
    name = "dummy_tool"
    description = "Test tool"
    def get_schema(self, provider: str) -> Dict[str, Any]:
        return {"name": self.name}
    async def execute(self, **kwargs) -> str:
        return '{"success": true}'

@pytest.mark.asyncio
async def test_registry_registration_and_execution():
    registry = ToolRegistry()
    registry.register(DummyTool())
    
    schemas = registry.get_all_schemas("openai")
    assert len(schemas) == 1
    assert schemas[0] == {"name": "dummy_tool"}
    
    result = await registry.execute_tool("dummy_tool")
    assert result == '{"success": true}'
    
@pytest.mark.asyncio
async def test_registry_missing_execution():
    registry = ToolRegistry()
    result = await registry.execute_tool("missing_tool")
    assert "error" in result
