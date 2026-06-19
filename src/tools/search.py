"""Code search tools: grep, glob."""

import glob as gb
import os
import subprocess
from pathlib import Path

from ..core.tool_use import ToolDefinition, ToolRegistry


def _grep(pattern: str, path: str = ".", max_results: int = 30) -> str:
    """Search for a pattern in files using ripgrep or Python fallback."""
    target = Path(path)
    if not target.exists():
        return f"路径不存在: {path}"

    # Try ripgrep first
    try:
        result = subprocess.run(
            ["rg", "--line-number", "--max-count", str(max_results), pattern, str(target)],
            capture_output=True, text=True, timeout=30,
        )
        output = result.stdout.strip()
        if output:
            return output[:5000]
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass

    # Python fallback
    results = []
    extensions = [".py", ".js", ".ts", ".jsx", ".tsx", ".go", ".rs", ".java",
                  ".c", ".cpp", ".h", ".yaml", ".yml", ".json", ".md", ".txt",
                  ".html", ".css", ".vue", ".rb", ".php", ".sh", ".bat", ".toml"]
    if target.is_file():
        files = [target]
    else:
        files = []
        for root, dirs, filenames in os.walk(target):
            dirs[:] = [d for d in dirs if not d.startswith(".") and d not in ("node_modules", "__pycache__", ".git", "venv", ".venv")]
            for f in filenames:
                if any(f.endswith(ext) for ext in extensions):
                    files.append(Path(root) / f)
            if len(files) > 500:
                break

    count = 0
    for f in files:
        if count >= max_results:
            break
        try:
            with open(f, "r", encoding="utf-8", errors="replace") as fh:
                for i, line in enumerate(fh, 1):
                    if pattern.lower() in line.lower():
                        results.append(f"{f}:{i}: {line.rstrip()[:200]}")
                        count += 1
                        if count >= max_results:
                            break
        except Exception:
            continue

    if results:
        return f"搜索 '{pattern}' 找到 {count} 处匹配:\n" + "\n".join(results[:5000])
    return f"未找到 '{pattern}' 的匹配"


def _glob(pattern: str, path: str = ".") -> str:
    """Find files matching a glob pattern."""
    target = Path(path)
    if not target.exists():
        return f"路径不存在: {path}"
    matches = sorted(target.rglob(pattern))
    matches = [m for m in matches if ".git" not in str(m) and "__pycache__" not in str(m)]
    if not matches:
        return f"未找到匹配 '{pattern}' 的文件"
    result = [f"找到 {len(matches)} 个文件:"]
    for m in matches[:50]:
        size = m.stat().st_size if m.is_file() else 0
        result.append(f"  {m} ({_fmt_size(size)})")
    if len(matches) > 50:
        result.append(f"  ... 还有 {len(matches) - 50} 个文件")
    return "\n".join(result)


def _fmt_size(size: int) -> str:
    for unit in ["B", "KB", "MB", "GB"]:
        if size < 1024:
            return f"{size}{unit}"
        size //= 1024
    return f"{size}GB"


def register_search_tools(registry: ToolRegistry) -> None:
    registry.register(ToolDefinition(
        name="grep",
        description="在代码库中搜索文本（大小写不敏感）。支持正则表达式。",
        parameters={
            "type": "object",
            "properties": {
                "pattern": {"type": "string", "description": "搜索模式（支持正则）"},
                "path": {"type": "string", "description": "搜索路径，默认为当前目录"},
                "max_results": {"type": "integer", "description": "最大结果数，默认30"},
            },
            "required": ["pattern"],
        },
        handler=_grep,
        category="search",
    ))
    registry.register(ToolDefinition(
        name="glob",
        description="按文件名模式查找文件（支持 ** 递归匹配）。",
        parameters={
            "type": "object",
            "properties": {
                "pattern": {"type": "string", "description": "Glob 模式，如 '**/*.py'"},
                "path": {"type": "string", "description": "搜索路径，默认为当前目录"},
            },
            "required": ["pattern"],
        },
        handler=_glob,
        category="search",
    ))
