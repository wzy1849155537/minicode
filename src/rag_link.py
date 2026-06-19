"""RAG knowledge base integration — connect to multimodal-rag-kb for project knowledge.

This allows MiniCode to search the user's personal knowledge base
for relevant documentation, code examples, and past project context.
"""

import os
import sys
from pathlib import Path
from typing import List, Optional

from loguru import logger


class RAGConnector:
    """Bridge to the multimodal RAG knowledge base."""

    def __init__(self, rag_path: Optional[str] = None):
        # Auto-find the RAG project
        if rag_path:
            self.rag_path = Path(rag_path)
        else:
            # Look in sibling directories
            candidates = [
                Path(__file__).parent.parent.parent / "multimodal-rag-kb",
                Path(os.getcwd()) / ".." / "multimodal-rag-kb",
            ]
            self.rag_path = None
            for c in candidates:
                if (c / "src" / "pipeline.py").exists():
                    self.rag_path = c.resolve()
                    break

        self._pipeline = None
        self._available = self.rag_path is not None

        if self._available:
            logger.info(f"RAG connector: {self.rag_path}")
        else:
            logger.info("RAG connector: not available (multimodal-rag-kb not found)")

    def _get_pipeline(self):
        """Lazy-load the RAG pipeline."""
        if self._pipeline is not None:
            return self._pipeline
        if not self._available:
            return None

        try:
            rag_src = str(self.rag_path)
            if rag_src not in sys.path:
                sys.path.insert(0, rag_src)
            from src.pipeline import RAGPipeline
            # Use same API key as MiniCode
            api_key = os.environ.get("SILICONFLOW_API_KEY") or os.environ.get("OPENAI_API_KEY", "")
            p = RAGPipeline()
            p.config._data["embedder"] = "siliconflow"
            p.config._data["indexer"] = "dense"
            p.config._data["llm"] = {
                "default": "siliconflow",
                "providers": {"siliconflow": {
                    "api_base": "https://api.siliconflow.cn/v1",
                    "api_key": api_key,
                    "model": "Qwen/Qwen2.5-32B-Instruct",
                }},
            }
            p.config._data["generation"] = {
                "llm_model": "Qwen/Qwen2.5-32B-Instruct",
                "llm_temperature": 0.3, "max_context_tokens": 4096,
            }
            p._initialized = False
            self._pipeline = p
            logger.info("RAG pipeline loaded")
        except Exception as e:
            logger.warning(f"RAG pipeline load failed: {e}")
            self._available = False
        return self._pipeline

    def search(self, query: str, top_k: int = 5) -> List[dict]:
        """Search the knowledge base for relevant context."""
        p = self._get_pipeline()
        if not p:
            return []

        try:
            answer = p.query(query, top_k=top_k)
            return answer.sources
        except Exception as e:
            logger.error(f"RAG search failed: {e}")
            return []

    def get_context_for_task(self, task: str) -> str:
        """Get relevant knowledge base context for a coding task."""
        sources = self.search(task, top_k=3)
        if not sources:
            return ""

        lines = ["## 知识库相关内容\n"]
        for i, src in enumerate(sources, 1):
            lines.append(
                f"### [{i}] {src.get('doc_name', 'Unknown')} "
                f"(相关度: {src.get('score', 0):.2f})\n"
                f"{src.get('content_snippet', '')[:500]}\n"
            )
        return "\n".join(lines)
