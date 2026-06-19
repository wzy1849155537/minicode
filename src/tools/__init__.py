"""Built-in tools for MiniCode."""
from .file_ops import register_file_tools
from .search import register_search_tools
from .shell import register_shell_tools
from .git_ops import register_git_tools
from .web import register_web_tools
from ..core.tool_use import ToolRegistry


def register_all_tools(registry: ToolRegistry) -> None:
    """Register all built-in tools."""
    register_file_tools(registry)
    register_search_tools(registry)
    register_shell_tools(registry)
    register_git_tools(registry)
    register_web_tools(registry)
