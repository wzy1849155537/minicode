"""Skill router — 2-stage recall + rerank for task-skill matching."""

import json
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from loguru import logger


@dataclass
class Skill:
    """A reusable high-level skill."""
    name: str
    description: str
    category: str
    keywords: List[str] = field(default_factory=list)
    tools: List[str] = field(default_factory=list)
    instructions: str = ""
    examples: List[str] = field(default_factory=list)
    success_rate: float = 0.0

    def match_score(self, query: str) -> float:
        """Simple keyword-based matching score."""
        q = query.lower()
        score = 0.0
        for kw in self.keywords:
            if kw.lower() in q:
                score += 1.0
        if any(w in q for w in self.description.lower().split()):
            score += 0.5
        return score


class SkillRouter:
    """2-stage skill matching: keyword recall → score ranking."""

    def __init__(self):
        self._skills: Dict[str, Skill] = {}
        self._load_builtin()

    def _load_builtin(self):
        """Register built-in skills."""
        builtins = [
            Skill(
                name="fix_bug",
                description="系统性地定位并修复代码中的 bug",
                category="debug",
                keywords=["修复", "bug", "错误", "报错", "异常", "fix", "error", "调试", "debug"],
                tools=["read_file", "grep", "shell", "edit_file"],
                instructions="1. 先用 grep 搜索错误信息定位文件\n2. 用 read_file 读取相关代码\n3. 分析根因\n4. 用 edit_file 精确修复\n5. 用 shell 运行测试验证",
                examples=["修复 auth 模块的导入错误", "这个 TypeError 怎么修"],
            ),
            Skill(
                name="add_feature",
                description="按照需求添加新功能",
                category="feature",
                keywords=["添加", "新增", "创建", "实现", "开发", "add", "create", "implement", "feature"],
                tools=["read_file", "write_file", "edit_file", "grep", "shell"],
                instructions="1. 先理解现有代码结构\n2. 确定需要修改的文件\n3. 用 edit_file 或 write_file 添加代码\n4. 确保风格与现有代码一致\n5. 运行测试确认",
                examples=["添加用户登录功能", "创建一个 REST API 接口"],
            ),
            Skill(
                name="refactor",
                description="重构代码，改善结构而不改变行为",
                category="refactor",
                keywords=["重构", "优化", "整理", "改进", "refactor", "clean", "improve"],
                tools=["read_file", "grep", "edit_file", "shell"],
                instructions="1. 先用 grep 找到所有引用点\n2. 逐个文件修改\n3. 保持接口兼容\n4. 运行全量测试",
                examples=["重构这个函数的参数", "把重复代码提取成公共函数"],
            ),
            Skill(
                name="explain_code",
                description="解释代码逻辑、架构和设计决策",
                category="understand",
                keywords=["解释", "说明", "分析", "介绍", "是什么", "怎么工作", "explain", "analyze", "understand", "how"],
                tools=["read_file", "grep", "glob"],
                instructions="1. 先读取关键文件\n2. 用 grep 找到入口点\n3. 梳理调用链\n4. 用中文清晰解释",
                examples=["这个项目是做什么的", "解释 auth.py 的登录流程"],
            ),
            Skill(
                name="write_test",
                description="为现有代码编写测试用例",
                category="test",
                keywords=["测试", "test", "unittest", "pytest", "用例", "覆盖率", "coverage"],
                tools=["read_file", "write_file", "grep", "shell"],
                instructions="1. 读取要测试的代码\n2. 确定测试框架\n3. 编写测试用例\n4. 运行测试确认通过",
                examples=["给这个模块写单元测试", "增加登录功能的测试覆盖率"],
            ),
            Skill(
                name="fix_import",
                description="修复 Python 导入错误和模块依赖问题",
                category="debug",
                keywords=["import", "导入", "模块", "找不到", "ModuleNotFound", "No module"],
                tools=["read_file", "grep", "shell", "edit_file"],
                instructions="1. grep 搜索 import 语句\n2. 检查 sys.path 和项目结构\n3. 修复导入路径或安装依赖\n4. 验证导入成功",
                examples=["ModuleNotFoundError: No module named 'src'", "导入路径报错"],
            ),
        ]
        for s in builtins:
            self._skills[s.name] = s
        logger.info(f"Loaded {len(builtins)} built-in skills")

    def route(self, query: str, top_k: int = 3) -> List[Skill]:
        """Find the best matching skills for a query.

        Stage 1: Keyword recall (coarse filtering)
        Stage 2: Score ranking + success rate bonus
        """
        # Stage 1: Recall all skills with any keyword match
        candidates = []
        for skill in self._skills.values():
            score = skill.match_score(query)
            if score > 0:
                candidates.append((score, skill))

        # Stage 2: Rank by score × (1 + success_rate bonus)
        ranked = sorted(
            candidates,
            key=lambda x: x[0] * (1 + x[1].success_rate * 0.3),
            reverse=True,
        )

        result = [s for _, s in ranked[:top_k]]
        if result:
            logger.info(f"Skill route: {query[:40]} → {[s.name for s in result]}")

        return result if result else list(self._skills.values())[:2]

    def get_instructions(self, skill_names: List[str]) -> str:
        """Build instructions string for selected skills."""
        lines = ["## 匹配到的技能指南\n"]
        for name in skill_names:
            s = self._skills.get(name)
            if s:
                lines.append(f"### {s.name}: {s.description}")
                lines.append(s.instructions)
                if s.examples:
                    lines.append("示例: " + ", ".join(s.examples))
                lines.append("")
        return "\n".join(lines)
