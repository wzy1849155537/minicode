"""Git operation tools."""

import subprocess

from ..core.tool_use import ToolDefinition, ToolRegistry


def _git_status() -> str:
    return _run_git(["status", "--short"])


def _git_diff() -> str:
    return _run_git(["diff", "--stat"]) + "\n" + _run_git(["diff", "--no-color"])


def _git_log(n: int = 10) -> str:
    return _run_git(["log", "--oneline", f"-{n}"])


def _git_branch() -> str:
    return _run_git(["branch", "-a"])


def _run_git(args: list) -> str:
    try:
        result = subprocess.run(
            ["git"] + args,
            capture_output=True, text=True, timeout=30,
        )
        output = result.stdout.strip()
        return output[:3000] if output else "(无输出)"
    except FileNotFoundError:
        return "Git 未安装或不在 PATH 中"
    except Exception as e:
        return f"Git 操作失败: {e}"


def register_git_tools(registry: ToolRegistry) -> None:
    registry.register(ToolDefinition(
        name="git_status",
        description="查看 Git 工作区状态（已修改、已暂存的文件）。",
        parameters={"type": "object", "properties": {}, "required": []},
        handler=lambda: _git_status(),
        category="git",
    ))
    registry.register(ToolDefinition(
        name="git_diff",
        description="查看当前未暂存的代码变更。",
        parameters={"type": "object", "properties": {}, "required": []},
        handler=lambda: _git_diff(),
        category="git",
    ))
    registry.register(ToolDefinition(
        name="git_log",
        description="查看最近的 Git 提交记录。",
        parameters={
            "type": "object",
            "properties": {"n": {"type": "integer", "description": "显示条数，默认10"}},
            "required": [],
        },
        handler=lambda n=10: _git_log(n),
        category="git",
    ))
    registry.register(ToolDefinition(
        name="git_branch",
        description="查看所有 Git 分支。",
        parameters={"type": "object", "properties": {}, "required": []},
        handler=lambda: _git_branch(),
        category="git",
    ))
