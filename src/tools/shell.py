"""Shell execution tool."""

import subprocess
import platform

from ..core.tool_use import ToolDefinition, ToolRegistry


def _run_shell(command: str, timeout: int = 60) -> str:
    """Execute a shell command and return the output."""
    try:
        shell_flag = True if platform.system() == "Windows" else False
        result = subprocess.run(
            command,
            shell=shell_flag,
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=".",
        )
        output = result.stdout.strip()
        stderr = result.stderr.strip()
        if result.returncode != 0:
            return (
                f"[退出码: {result.returncode}]\n"
                f"{output}\n"
                f"{'─' * 40}\n"
                f"标准错误:\n{stderr}"
            )[:5000]
        return output[:5000] if output else "(命令执行成功，无输出)"
    except subprocess.TimeoutExpired:
        return f"命令超时 ({timeout}秒): {command}"
    except Exception as e:
        return f"命令执行失败: {e}"


def register_shell_tools(registry: ToolRegistry) -> None:
    registry.register(ToolDefinition(
        name="shell",
        description="执行 Shell 命令。用于运行测试、安装依赖、构建项目、查看文件等。",
        parameters={
            "type": "object",
            "properties": {
                "command": {"type": "string", "description": "要执行的 Shell 命令"},
                "timeout": {"type": "integer", "description": "超时秒数，默认60"},
            },
            "required": ["command"],
        },
        handler=_run_shell,
        category="system",
        require_confirm=True,
    ))
