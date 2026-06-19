"""Tool Use parser and dispatcher."""

import json
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

from loguru import logger


@dataclass
class ToolDefinition:
    """A tool that the LLM can call."""
    name: str
    description: str
    parameters: Dict[str, Any]  # JSON Schema
    handler: Callable
    category: str = "general"
    require_confirm: bool = False

    def to_openai_schema(self) -> Dict[str, Any]:
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters,
            },
        }


@dataclass
class ToolResult:
    """Result of a tool execution."""
    tool_name: str
    success: bool
    output: str
    error: Optional[str] = None
    duration_ms: float = 0.0


class ToolRegistry:
    """Manages all available tools."""

    def __init__(self):
        self._tools: Dict[str, ToolDefinition] = {}

    def register(self, tool: ToolDefinition) -> None:
        self._tools[tool.name] = tool
        logger.debug(f"Tool registered: {tool.name}")

    def get(self, name: str) -> Optional[ToolDefinition]:
        return self._tools.get(name)

    def list(self) -> List[ToolDefinition]:
        return list(self._tools.values())

    def list_schemas(self) -> List[Dict]:
        return [t.to_openai_schema() for t in self._tools.values()]

    def execute(self, name: str, arguments: Dict[str, Any]) -> ToolResult:
        """Execute a tool by name with arguments."""
        tool = self._tools.get(name)
        if not tool:
            return ToolResult(name, False, "", f"未知工具: {name}")

        start = time.perf_counter()
        try:
            result = tool.handler(**arguments)
            elapsed = (time.perf_counter() - start) * 1000
            output = str(result) if not isinstance(result, str) else result
            return ToolResult(name, True, output, duration_ms=elapsed)
        except Exception as e:
            elapsed = (time.perf_counter() - start) * 1000
            logger.error(f"Tool {name} failed: {e}")
            return ToolResult(name, False, "", str(e), duration_ms=elapsed)

    def execute_multi(
        self, tool_calls: List[Dict[str, Any]]
    ) -> List[ToolResult]:
        """Execute multiple tool calls sequentially."""
        results = []
        for tc in tool_calls:
            r = self.execute(tc["name"], tc.get("arguments", {}))
            results.append(r)
        return results
