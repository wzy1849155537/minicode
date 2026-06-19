"""SQLite-based memory store — 3-tier: episodic, procedural, user profile."""

import json
import sqlite3
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from loguru import logger


class MemoryStore:
    """Persistent memory for cross-session knowledge retention.

    Three tiers:
    - Episodic: past task records (what was done, result)
    - Procedural: reusable patterns (fix steps, best practices)
    - User profile: preferences, common mistakes, code style
    """

    def __init__(self, db_path: str = "./data/memory.db"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(self.db_path))
        self._create_tables()

    def _create_tables(self):
        self._conn.executescript("""
            CREATE TABLE IF NOT EXISTS episodic (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                task TEXT NOT NULL,
                tool_calls TEXT,
                outcome TEXT,
                error TEXT,
                created_at REAL NOT NULL,
                tags TEXT
            );
            CREATE TABLE IF NOT EXISTS procedural (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                pattern TEXT NOT NULL,
                steps TEXT NOT NULL,
                context TEXT,
                success_count INTEGER DEFAULT 0,
                total_count INTEGER DEFAULT 0,
                tags TEXT,
                created_at REAL NOT NULL
            );
            CREATE TABLE IF NOT EXISTS user_profile (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL,
                updated_at REAL NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_episodic_tags ON episodic(tags);
            CREATE INDEX IF NOT EXISTS idx_procedural_tags ON procedural(tags);
        """)
        self._conn.commit()

    # ---- Episodic ----
    def record_episode(self, task: str, tool_calls: List[str],
                       outcome: str, error: str = "", tags: str = ""):
        self._conn.execute(
            "INSERT INTO episodic (task, tool_calls, outcome, error, created_at, tags) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (task, json.dumps(tool_calls), outcome, error, time.time(), tags),
        )
        self._conn.commit()

    def search_episodes(self, keyword: str, limit: int = 5) -> List[Dict]:
        rows = self._conn.execute(
            "SELECT task, tool_calls, outcome, error, tags, created_at "
            "FROM episodic WHERE task LIKE ? OR tags LIKE ? "
            "ORDER BY created_at DESC LIMIT ?",
            (f"%{keyword}%", f"%{keyword}%", limit),
        ).fetchall()
        return [{
            "task": r[0], "tool_calls": json.loads(r[1]) if r[1] else [],
            "outcome": r[2], "error": r[3], "tags": r[4],
            "created_at": r[5],
        } for r in rows]

    # ---- Procedural ----
    def save_pattern(self, pattern: str, steps: List[str],
                     context: str = "", tags: str = ""):
        """Save a reusable pattern (e.g., 'fix Python import error')."""
        existing = self._conn.execute(
            "SELECT id, success_count, total_count FROM procedural "
            "WHERE pattern = ?", (pattern,)
        ).fetchone()
        if existing:
            self._conn.execute(
                "UPDATE procedural SET steps=?, context=?, total_count=total_count+1 "
                "WHERE id=?",
                (json.dumps(steps), context, existing[0]),
            )
        else:
            self._conn.execute(
                "INSERT INTO procedural (pattern, steps, context, tags, created_at) "
                "VALUES (?, ?, ?, ?, ?)",
                (pattern, json.dumps(steps), context, tags, time.time()),
            )
        self._conn.commit()

    def find_patterns(self, keyword: str, limit: int = 5) -> List[Dict]:
        rows = self._conn.execute(
            "SELECT pattern, steps, context, tags, success_count, total_count "
            "FROM procedural WHERE pattern LIKE ? OR tags LIKE ? "
            "ORDER BY success_count * 1.0 / MAX(total_count, 1) DESC LIMIT ?",
            (f"%{keyword}%", f"%{keyword}%", limit),
        ).fetchall()
        return [{
            "pattern": r[0],
            "steps": json.loads(r[1]) if r[1] else [],
            "context": r[2], "tags": r[3],
            "success_rate": r[4] / max(r[5], 1) if r[5] > 0 else 0,
        } for r in rows]

    def mark_pattern_success(self, pattern: str, success: bool = True):
        if success:
            self._conn.execute(
                "UPDATE procedural SET success_count=success_count+1, "
                "total_count=total_count+1 WHERE pattern=?", (pattern,)
            )
        else:
            self._conn.execute(
                "UPDATE procedural SET total_count=total_count+1 WHERE pattern=?",
                (pattern,)
            )
        self._conn.commit()

    # ---- User Profile ----
    def set_profile(self, key: str, value: str):
        self._conn.execute(
            "INSERT OR REPLACE INTO user_profile (key, value, updated_at) "
            "VALUES (?, ?, ?)", (key, value, time.time())
        )
        self._conn.commit()

    def get_profile(self, key: str) -> Optional[str]:
        row = self._conn.execute(
            "SELECT value FROM user_profile WHERE key=?", (key,)
        ).fetchone()
        return row[0] if row else None

    def get_all_profiles(self) -> Dict[str, str]:
        rows = self._conn.execute(
            "SELECT key, value FROM user_profile"
        ).fetchall()
        return {r[0]: r[1] for r in rows}

    # ---- Stats ----
    def get_stats(self) -> Dict[str, int]:
        ep = self._conn.execute("SELECT COUNT(*) FROM episodic").fetchone()[0]
        pr = self._conn.execute("SELECT COUNT(*) FROM procedural").fetchone()[0]
        return {"episodes": ep, "patterns": pr}
