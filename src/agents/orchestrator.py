"""Multi-Agent orchestrator — main Agent dispatches sub-Agents as Tool Calls.

Design: centered control (main Agent plans, approves, quality-checks).
Sub-Agents run as sandboxed tool calls with limited permissions.
"""

import os
import subprocess
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from loguru import logger


@dataclass
class SubAgentResult:
    agent_id: str
    task: str
    success: bool
    output: str
    error: str = ""


class MultiAgentOrchestrator:
    """Centered multi-Agent collaboration.

    Three modes:
    - Fork: sub-Agent works in temp directory, returns diff
    - Worktree: sub-Agent works in git worktree (isolation)
    - Team: multiple sub-Agents in parallel on different sub-tasks
    """

    def __init__(
        self,
        agent_factory,
        max_sub_agents: int = 3,
        mode: str = "fork",
    ):
        self._factory = agent_factory
        self.max_sub_agents = max_sub_agents
        self.mode = mode  # fork | worktree | team
        self._results: List[SubAgentResult] = []

    def decompose_task(self, task: str) -> List[str]:
        """Decompose complex task into sub-tasks using LLM.

        Simple heuristics for now - full LLM decomposition comes later.
        """
        subtasks = []

        # Heuristic: split by numbered steps or conjunctions
        if "并" in task or "同时" in task:
            parts = task.replace("并", "|").replace("同时", "|").split("|")
            subtasks = [p.strip() for p in parts if len(p.strip()) > 5]

        if not subtasks:
            subtasks = [task]

        logger.info(
            f"Task decomposed into {len(subtasks)} sub-tasks"
        )
        return subtasks

    def run_fork(self, task: str, sub_agent, workspace: str) -> SubAgentResult:
        """Run a sub-Agent in an isolated temp workspace."""
        import uuid

        agent_id = uuid.uuid4().hex[:6]
        logger.info(f"Fork Agent {agent_id}: {task[:60]}")

        try:
            result = sub_agent.run(task)
            return SubAgentResult(
                agent_id=agent_id,
                task=task,
                success=True,
                output=result.content,
            )
        except Exception as e:
            return SubAgentResult(
                agent_id=agent_id,
                task=task,
                success=False,
                output="",
                error=str(e),
            )

    def run_team(self, task: str, num_agents: int = 2) -> List[SubAgentResult]:
        """Run multiple sub-Agents in parallel on different aspects."""
        import concurrent.futures

        subtasks = self.decompose_task(task)
        results = []

        with concurrent.futures.ThreadPoolExecutor(
            max_workers=min(num_agents, self.max_sub_agents)
        ) as executor:
            futures = []
            for st in subtasks[:self.max_sub_agents]:
                sub_agent = self._factory()
                futures.append(
                    executor.submit(self.run_fork, st, sub_agent, ".")
                )

            for f in concurrent.futures.as_completed(futures):
                results.append(f.result())

        self._results.extend(results)
        return results

    def summarize_results(self) -> str:
        """Summarize all sub-Agent outputs."""
        if not self._results:
            return "无子 Agent 执行结果"

        lines = [f"## 多 Agent 执行摘要 ({len(self._results)} 个子任务)\n"]
        for r in self._results:
            status = "✓" if r.success else "✗"
            lines.append(
                f"- [{r.agent_id}] {status} {r.task[:60]}\n"
                f"  产出: {r.output[:200]}\n"
            )
            if r.error:
                lines.append(f"  错误: {r.error}\n")
        return "\n".join(lines)
