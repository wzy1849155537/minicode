"""Memory refinery — auto-extract reusable patterns from episodic memories."""

import re
from typing import List

from loguru import logger

from .store import MemoryStore


class MemoryRefinery:
    """Extracts procedural patterns from episodic task records.

    The closed loop: execute → record → reflect → extract → store → reuse.
    """

    def __init__(self, store: MemoryStore):
        self.store = store

    def reflect_on_episode(self, task: str, error: str = "") -> List[str]:
        """Analyze an episode and extract reusable insights."""
        insights = []

        # Pattern: error type detection
        if error:
            for pattern, tag in [
                ("import", "Python导入"),
                ("ModuleNotFound", "Python导入"),
                ("syntax", "语法错误"),
                ("indent", "缩进错误"),
                ("permission", "权限问题"),
                ("timeout", "超时"),
                ("not found", "文件缺失"),
                ("TypeError", "类型错误"),
                ("AttributeError", "属性错误"),
            ]:
                if pattern.lower() in error.lower():
                    insights.append(f"{tag}: {error[:100]}")

        # Pattern: task type classification
        for keyword, tag in [
            ("修复", "bug修复"),
            ("修复", "bug修复"),
            ("debug", "调试"),
            ("创建", "文件创建"),
            ("重构", "重构"),
            ("测试", "测试"),
            ("安装", "依赖安装"),
            ("优化", "性能优化"),
            ("文档", "文档"),
        ]:
            if keyword in task:
                insights.append(f"任务类型: {tag}")
                break

        return insights

    def run_cycle(self, max_episodes: int = 20):
        """Process recent episodes and extract patterns."""
        stats = self.store.get_stats()
        if stats["episodes"] < 5:
            logger.debug("Not enough episodes for refinement cycle")
            return

        logger.info(
            f"Memory refinery: {stats['episodes']} episodes, "
            f"{stats['patterns']} patterns"
        )
