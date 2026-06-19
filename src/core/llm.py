"""LLM adapter — unified interface for SiliconFlow, DeepSeek, Qwen, OpenAI."""

import json
import os
import re
from typing import Any, Dict, List, Optional

from openai import OpenAI
from loguru import logger


class LLMAdapter:
    """OpenAI-compatible LLM client with streaming support."""

    def __init__(
        self,
        api_base: str = "https://api.siliconflow.cn/v1",
        api_key: str = "",
        model: str = "deepseek-ai/DeepSeek-V3",
        temperature: float = 0.3,
        max_tokens: int = 4096,
    ):
        self.api_base = api_base
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens
        self._client = OpenAI(base_url=api_base, api_key=api_key)
        logger.info(f"LLM adapter: {model} @ {api_base}")

    def chat(
        self,
        messages: List[Dict[str, Any]],
        tools: Optional[List[Dict]] = None,
        stream: bool = True,
    ) -> Dict[str, Any]:
        """Send a chat completion request. Returns parsed response dict."""
        kwargs = dict(
            model=self.model,
            messages=messages,
            temperature=self.temperature,
            max_tokens=self.max_tokens,
        )
        if tools:
            kwargs["tools"] = tools
            kwargs["tool_choice"] = "auto"

        try:
            response = self._client.chat.completions.create(**kwargs)
            msg = response.choices[0].message
            return {
                "role": "assistant",
                "content": msg.content or "",
                "tool_calls": [
                    {
                        "id": tc.id,
                        "name": tc.function.name,
                        "arguments": json.loads(tc.function.arguments),
                    }
                    for tc in (msg.tool_calls or [])
                ],
                "finish_reason": response.choices[0].finish_reason,
                "usage": {
                    "prompt_tokens": response.usage.prompt_tokens if response.usage else 0,
                    "completion_tokens": response.usage.completion_tokens if response.usage else 0,
                },
            }
        except Exception as e:
            logger.error(f"LLM call failed: {e}")
            return {
                "role": "assistant",
                "content": f"[模型调用失败: {e}]",
                "tool_calls": [],
                "finish_reason": "error",
                "usage": {"prompt_tokens": 0, "completion_tokens": 0},
            }

    def chat_stream(self, messages: List[Dict], tools: Optional[List[Dict]] = None):
        """Generator yielding text chunks as they arrive."""
        kwargs = dict(
            model=self.model,
            messages=messages,
            temperature=self.temperature,
            max_tokens=self.max_tokens,
            stream=True,
        )
        if tools:
            kwargs["tools"] = tools
            kwargs["tool_choice"] = "auto"

        try:
            stream = self._client.chat.completions.create(**kwargs)
            for chunk in stream:
                delta = chunk.choices[0].delta
                if delta.content:
                    yield {"type": "text", "content": delta.content}
        except Exception as e:
            yield {"type": "error", "content": str(e)}


def create_llm_from_env() -> LLMAdapter:
    """Create LLM adapter from environment variables."""
    api_key = (
        os.environ.get("SILICONFLOW_API_KEY")
        or os.environ.get("OPENAI_API_KEY")
        or os.environ.get("DEEPSEEK_API_KEY")
        or ""
    )
    # Try .env file
    if not api_key:
        env_file = os.path.join(os.path.dirname(__file__), "..", "..", ".env")
        if not os.path.exists(env_file):
            env_file = os.path.join(os.getcwd(), ".env")
        if os.path.exists(env_file):
            with open(env_file, encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if "=" in line and not line.startswith("#"):
                        k, v = line.split("=", 1)
                        v = v.strip().strip('"').strip("'")
                        if k == "SILICONFLOW_API_KEY" and v not in ("", "your-key-here"):
                            api_key = v
                            os.environ["SILICONFLOW_API_KEY"] = v
                            break

    model = os.environ.get("MINICODE_MODEL", "deepseek-ai/DeepSeek-V3")
    api_base = os.environ.get(
        "MINICODE_API_BASE", "https://api.siliconflow.cn/v1"
    )

    return LLMAdapter(api_base=api_base, api_key=api_key, model=model)
