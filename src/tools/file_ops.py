"""File operation tools: read, write, edit."""

import os
from pathlib import Path

from ..core.tool_use import ToolDefinition, ToolRegistry


def _read_file(path: str, start_line: int = 1, end_line: int = -1) -> str:
    """Read a file with optional line range."""
    p = Path(path)
    if not p.exists():
        return f"文件不存在: {path}"
    if p.is_dir():
        return f"这是一个目录: {path}"
    try:
        with open(p, "r", encoding="utf-8", errors="replace") as f:
            lines = f.readlines()
        total = len(lines)
        if end_line == -1:
            end_line = total
        start_line = max(1, start_line)
        end_line = min(total, end_line)
        selected = lines[start_line - 1 : end_line]
        result = "".join(selected)
        header = f"[{path} 第{start_line}-{end_line}行，共{total}行]\n"
        return header + result
    except Exception as e:
        return f"读取失败: {e}"


def _write_file(path: str, content: str) -> str:
    """Write content to a file."""
    p = Path(path)
    try:
        p.parent.mkdir(parents=True, exist_ok=True)
        with open(p, "w", encoding="utf-8") as f:
            f.write(content)
        return f"已写入: {path} ({len(content)} 字符)"
    except Exception as e:
        return f"写入失败: {e}"


def _edit_file(path: str, old_string: str, new_string: str) -> str:
    """Replace old_string with new_string in file."""
    p = Path(path)
    if not p.exists():
        return f"文件不存在: {path}"
    try:
        with open(p, "r", encoding="utf-8") as f:
            original = f.read()
        if old_string not in original:
            return f"未找到要替换的内容。请确保 old_string 与文件中的内容完全一致（包括缩进和空格）。"
        count = original.count(old_string)
        updated = original.replace(old_string, new_string, 1)
        with open(p, "w", encoding="utf-8") as f:
            f.write(updated)
        return f"已替换: {path} (1处修改，共找到{count}处匹配，仅替换第1处)"
    except Exception as e:
        return f"编辑失败: {e}"


def register_file_tools(registry: ToolRegistry) -> None:
    registry.register(ToolDefinition(
        name="read_file",
        description="读取文件内容。可以指定行范围（start_line, end_line）。",
        parameters={
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "文件路径"},
                "start_line": {"type": "integer", "description": "起始行号，默认1"},
                "end_line": {"type": "integer", "description": "结束行号，-1表示读取全部"},
            },
            "required": ["path"],
        },
        handler=_read_file,
        category="file",
        require_confirm=False,
    ))
    registry.register(ToolDefinition(
        name="write_file",
        description="将内容写入文件（覆盖已有内容）。创建新文件时自动创建父目录。",
        parameters={
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "文件路径"},
                "content": {"type": "string", "description": "要写入的内容"},
            },
            "required": ["path", "content"],
        },
        handler=_write_file,
        category="file",
        require_confirm=True,
    ))
    registry.register(ToolDefinition(
        name="edit_file",
        description="精确替换文件中的一段文本。old_string 必须与原文完全匹配（含缩进）。",
        parameters={
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "文件路径"},
                "old_string": {"type": "string", "description": "要替换的原文本（必须精确匹配）"},
                "new_string": {"type": "string", "description": "替换后的新文本"},
            },
            "required": ["path", "old_string", "new_string"],
        },
        handler=_edit_file,
        category="file",
        require_confirm=True,
    ))
