"""Query Loop — the core Agent execution cycle.

Ref: Claude Code architecture, MiniCode Python reference.
Key improvement: Chinese-native system prompts + local model integration.
"""

import json
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

from loguru import logger

from .llm import LLMAdapter
from .tool_use import ToolRegistry, ToolResult

# ================================================================
# System Prompt (Chinese-native, concise)
# ================================================================
SYSTEM_PROMPT = """你是 MiniCode，一个本地 AI 编程助手。你运行在用户的终端中，可以直接操作文件、执行命令、搜索代码。

## 核心能力
- 读写编辑文件：修改代码、创建新文件、修复 bug
- 搜索代码库：grep 文本搜索、glob 文件名匹配
- 执行 Shell 命令：运行测试、安装依赖、构建项目
- Git 操作：查看状态、提交、创建分支
- 代码分析：解释代码逻辑、审查代码质量、提出优化建议

## 行为准则
1. 先理解再行动：先读相关文件，确认问题后再修改
2. 最小化改动：只改必要的部分，不做无关修改
3. 解释你的操作：每次工具调用前，简短说明你要做什么
4. 验证结果：修改后运行测试或检查确认改动正确
5. 中文回复：始终用中文与用户交流

## 当前工作目录
{cwd}

## 项目结构
{project_tree}

## 可用工具
{tools_description}
"""


@dataclass
class TurnResult:
    """Result of one agent turn."""
    role: str
    content: str
    tool_results: List[ToolResult] = field(default_factory=list)
    finish_reason: str = ""
    tokens_used: int = 0


class AgentLoop:
    """Main Agent execution loop."""

    def __init__(
        self,
        llm: LLMAdapter,
        tools: ToolRegistry,
        cwd: str = "",
        max_turns: int = 30,
    ):
        self.llm = llm
        self.tools = tools
        self.cwd = cwd
        self.max_turns = max_turns
        self._messages: List[Dict] = []
        self._history: List[TurnResult] = []
        self._total_tokens = 0

    def _build_system_message(self) -> Dict:
        """Build Chinese-native system prompt."""
        import os

        # Simple project tree (top 2 levels, max 50 entries)
        tree_lines = []
        try:
            for root, dirs, files in os.walk(self.cwd):
                # Skip hidden and venv
                dirs[:] = [d for d in dirs if not d.startswith(".") and d not in ("venv", ".venv", "node_modules", "__pycache__")]
                depth = root.replace(self.cwd, "").count(os.sep)
                if depth > 2:
                    continue
                prefix = "  " * depth + ("├─ " if depth > 0 else "")
                tree_lines.append(f"{prefix}{os.path.basename(root)}/")
                if depth < 2:
                    for f in sorted(files[:10]):
                        if not f.startswith("."):
                            tree_lines.append(f"  " * (depth + 1) + f"├─ {f}")
                if len(tree_lines) > 50:
                    tree_lines.append("  ... (更多文件省略)")
                    break
        except Exception:
            tree_lines = ["(无法读取目录结构)"]

        tools_desc = "\n".join(
            f"- **{t.name}**: {t.description}"
            for t in self.tools.list()
        )

        content = SYSTEM_PROMPT.format(
            cwd=self.cwd,
            project_tree="\n".join(tree_lines[:50]),
            tools_description=tools_desc,
        )
        return {"role": "system", "content": content}

    def run(self, user_input: str) -> TurnResult:
        """Execute one complete agent turn (may involve multiple tool calls)."""
        # Initialize messages on first call
        if not self._messages:
            self._messages = [self._build_system_message()]

        self._messages.append({"role": "user", "content": user_input})
        turn_count = 0
        last_result = None

        while turn_count < self.max_turns:
            turn_count += 1
            logger.info(f"Turn {turn_count}/{self.max_turns}")

            # Call LLM
            response = self.llm.chat(
                self._messages,
                tools=self.tools.list_schemas() if self.tools.list() else None,
            )

            # Track tokens
            usage = response.get("usage", {})
            self._total_tokens += usage.get("prompt_tokens", 0) + usage.get("completion_tokens", 0)

            content = response.get("content", "")
            tool_calls = response.get("tool_calls", [])
            finish = response.get("finish_reason", "")

            # Add assistant message
            self._messages.append({
                "role": "assistant",
                "content": content,
            })

            # If no tool calls, return the text response
            if not tool_calls:
                result = TurnResult(
                    role="assistant",
                    content=content,
                    finish_reason=finish,
                    tokens_used=self._total_tokens,
                )
                self._history.append(result)
                return result

            # Execute tools
            logger.info(f"Executing {len(tool_calls)} tool(s)")
            tool_results = self.tools.execute_multi(tool_calls)

            # Inject tool results into conversation
            for i, tr in enumerate(tool_results):
                tool_name = tool_calls[i]["name"]
                status = "✓" if tr.success else "✗"
                result_text = (
                    f"[工具 {tool_name} 执行{status}]\n"
                    f"{tr.output[:3000]}"  # Truncate for context
                )
                if tr.error:
                    result_text += f"\n错误: {tr.error}"
                self._messages.append({
                    "role": "user",
                    "content": result_text,
                })

            last_result = TurnResult(
                role="assistant",
                content=content,
                tool_results=tool_results,
                finish_reason="tool_use",
                tokens_used=self._total_tokens,
            )

        # Max turns reached
        return TurnResult(
            role="assistant",
            content="已达到最大执行轮数，任务可能未完成。",
            finish_reason="max_turns",
            tokens_used=self._total_tokens,
        )

    @property
    def history(self) -> List[TurnResult]:
        return self._history

    @property
    def total_tokens(self) -> int:
        return self._total_tokens
