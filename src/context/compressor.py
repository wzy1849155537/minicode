"""Layered context compressor — prevent long conversations from overflowing."""

import hashlib
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from loguru import logger


@dataclass
class CompressionStats:
    original_tokens: int
    compressed_tokens: int
    savings_pct: float


class ContextCompressor:
    """3-tier compression strategy for tool outputs and conversation history.

    Tier 1: Small output (<500 chars) → keep as-is
    Tier 2: Medium (500-3000) → summarize with key info
    Tier 3: Large (>3000) → externalize, store reference, keep summary only
    """

    def __init__(self, max_context_tokens: int = 8000, threshold: int = 6000):
        self.max_tokens = max_context_tokens
        self.threshold = threshold
        self._external_store: Dict[str, str] = {}  # hash -> full content

    def compress_tool_output(self, tool_name: str, output: str) -> str:
        """Compress a single tool output based on size."""
        size = len(output)

        # Tier 1: keep as-is
        if size < 500:
            return output

        # Tier 2: medium compression
        if size < 3000:
            return self._medium_compress(output, tool_name)

        # Tier 3: externalize
        return self._deep_compress(output, tool_name)

    def _medium_compress(self, output: str, tool_name: str) -> str:
        """Keep first N lines + last M lines + summary."""
        lines = output.split("\n")
        if len(lines) <= 50:
            return output

        head = "\n".join(lines[:20])
        tail = "\n".join(lines[-20:])
        return (
            f"## {tool_name} 输出 (共 {len(lines)} 行，已压缩)\n"
            f"{head}\n"
            f"... 省略 {len(lines) - 40} 行 ...\n"
            f"{tail}"
        )

    def _deep_compress(self, output: str, tool_name: str) -> str:
        """Externalize full content, return summary only."""
        content_hash = hashlib.md5(output.encode()).hexdigest()[:12]
        self._external_store[content_hash] = output

        lines = output.split("\n")
        # Extract key info: error lines, file paths, numbers
        errors = [l for l in lines if "error" in l.lower() or "错误" in l]
        summary = (
            f"## {tool_name} 输出 (已外置存储，ID: {content_hash})\n"
            f"总行数: {len(lines)} | 总字符: {len(output)}\n"
        )
        if errors:
            summary += f"关键错误信息 ({len(errors)} 条):\n"
            summary += "\n".join(errors[:5])
        summary += f"\n前 10 行预览:\n" + "\n".join(lines[:10])
        summary += "\n(完整内容可按 ID {content_hash} 检索)"
        return summary

    def compress_messages(
        self, messages: List[Dict], max_tokens: Optional[int] = None
    ) -> List[Dict]:
        """Compress conversation history if it exceeds threshold."""
        max_t = max_tokens or self.max_tokens
        threshold = self.threshold

        # Estimate current token count
        total_chars = sum(len(str(m.get("content", ""))) for m in messages)
        estimated_tokens = total_chars // 3  # rough for Chinese

        if estimated_tokens <= threshold:
            return messages

        logger.info(
            f"Compressing: {estimated_tokens} tokens → target {max_t}"
        )

        # Strategy: keep system message + last 5 messages intact,
        # compress middle messages to summaries
        compressed = []
        keep_last = 5

        for i, msg in enumerate(messages):
            if i == 0:  # system message
                compressed.append(msg)
            elif i >= len(messages) - keep_last:  # last N
                compressed.append(msg)
            else:
                # Compress old tool outputs
                content = str(msg.get("content", ""))
                role = msg.get("role", "")
                if role == "user" and content.startswith("[工具"):
                    # Compress tool results
                    compressed.append({
                        "role": "user",
                        "content": self.compress_tool_output("history", content),
                    })
                elif len(content) > 500:
                    compressed.append({
                        **msg,
                        "content": content[:200] + f"... (已压缩 {len(content)} 字符)",
                    })
                else:
                    compressed.append(msg)

        new_chars = sum(len(str(m.get("content", ""))) for m in compressed)
        logger.info(
            f"Compressed: {total_chars} → {new_chars} chars "
            f"({(1 - new_chars / max(total_chars, 1)) * 100:.0f}% savings)"
        )

        return compressed

    def stats(self) -> CompressionStats:
        total_original = sum(len(v) for v in self._external_store.values())
        return CompressionStats(
            original_tokens=total_original // 3,
            compressed_tokens=len(self._external_store),
            savings_pct=0.0,  # computed per compression
        )
