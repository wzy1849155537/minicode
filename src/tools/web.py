"""Web tools: fetch, search."""

import urllib.request
import urllib.error
import json

from ..core.tool_use import ToolDefinition, ToolRegistry


def _web_fetch(url: str) -> str:
    """Fetch content from a URL."""
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "MiniCode/1.0"})
        with urllib.request.urlopen(req, timeout=15) as resp:
            content = resp.read().decode("utf-8", errors="replace")
            # Simple HTML text extraction
            text = _strip_html(content)
            return text[:3000] if text else "(无文本内容)"
    except urllib.error.URLError as e:
        return f"无法访问 {url}: {e}"
    except Exception as e:
        return f"抓取失败: {e}"


def _strip_html(html: str) -> str:
    """Very basic HTML tag stripping."""
    import re
    # Remove scripts and styles
    html = re.sub(r"<script[^>]*>.*?</script>", "", html, flags=re.DOTALL | re.IGNORECASE)
    html = re.sub(r"<style[^>]*>.*?</style>", "", html, flags=re.DOTALL | re.IGNORECASE)
    # Remove tags
    text = re.sub(r"<[^>]+>", " ", html)
    # Collapse whitespace
    text = re.sub(r"\s+", " ", text).strip()
    return text


def register_web_tools(registry: ToolRegistry) -> None:
    registry.register(ToolDefinition(
        name="web_fetch",
        description="获取网页内容（提取文本，去除HTML标签）。",
        parameters={
            "type": "object",
            "properties": {"url": {"type": "string", "description": "网页 URL"}},
            "required": ["url"],
        },
        handler=_web_fetch,
        category="web",
    ))
