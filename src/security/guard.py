"""Security guard — permission checking, injection detection, risk classification."""

import re
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional

from loguru import logger


class RiskLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class SecurityDecision:
    allowed: bool
    risk: RiskLevel
    reason: str
    requires_confirmation: bool = True


class SecurityGuard:
    """Multi-layer security review for Agent operations.

    Layer 1: Rule filter (whitelist/blacklist)
    Layer 2: Injection detection
    Layer 3: Risk classification
    """

    # Commands that are always safe
    SAFE_COMMANDS = {
        "read_file", "grep", "glob", "git_status", "git_diff",
        "git_log", "git_branch", "web_fetch",
    }

    # Commands that need confirmation
    CONFIRM_COMMANDS = {
        "write_file", "edit_file", "shell",
    }

    # Shell patterns that are dangerous
    DANGEROUS_PATTERNS = [
        r"rm\s+-rf\s+/",           # rm -rf /
        r"sudo\s+rm",              # sudo rm
        r">\s*/dev/sda",           # write to disk
        r"mkfs\.",                 # format
        r"dd\s+if=",               # raw disk write
        r":\(\)\s*\{\s*:\|:&\s*\}\s*;:",  # fork bomb
        r"chmod\s+777\s+/",        # chmod 777 /
        r"curl.*\|.*sh",           # curl pipe sh (suspicious)
        r"wget.*\|.*sh",           # wget pipe sh
    ]

    # Known injection patterns
    INJECTION_PATTERNS = [
        r"忽略.*(?:规则|指令|限制|安全)",
        r"ignore.*(?:previous|above|instruction|rule)",
        r"disregard.*(?:instruction|rule)",
        r"你是.*现在你是",
        r"扮演.*角色",
        r"system\s*:",             # pretend to be system message
        r"<\|im_start\|>",         # ChatML injection
        r"<\|im_end\|>",
    ]

    def check_tool(self, tool_name: str, arguments: Dict[str, Any]) -> SecurityDecision:
        """Check if a tool call is safe to execute."""

        # Layer 1: Safe tools pass through
        if tool_name in self.SAFE_COMMANDS:
            return SecurityDecision(
                allowed=True, risk=RiskLevel.LOW,
                reason="安全工具，自动批准",
                requires_confirmation=False,
            )

        # Layer 2: Injection detection
        for key, value in arguments.items():
            if isinstance(value, str):
                for pattern in self.INJECTION_PATTERNS:
                    if re.search(pattern, value, re.IGNORECASE):
                        return SecurityDecision(
                            allowed=False, risk=RiskLevel.CRITICAL,
                            reason=f"检测到注入攻击模式: {pattern}",
                            requires_confirmation=True,
                        )

        # Layer 3: Shell-specific danger check
        if tool_name == "shell":
            command = arguments.get("command", "")
            for pattern in self.DANGEROUS_PATTERNS:
                if re.search(pattern, command, re.IGNORECASE):
                    return SecurityDecision(
                        allowed=False, risk=RiskLevel.CRITICAL,
                        reason=f"危险命令: {pattern}",
                        requires_confirmation=True,
                    )

        # Default: confirm-required tools
        if tool_name in self.CONFIRM_COMMANDS:
            return SecurityDecision(
                allowed=True, risk=RiskLevel.MEDIUM,
                reason=f"需要确认: {tool_name}",
                requires_confirmation=True,
            )

        return SecurityDecision(
            allowed=True, risk=RiskLevel.LOW,
            reason="通过安全检查",
            requires_confirmation=False,
        )

    def check_content(self, text: str) -> SecurityDecision:
        """Check user input for injection attempts."""
        for pattern in self.INJECTION_PATTERNS:
            if re.search(pattern, text, re.IGNORECASE):
                return SecurityDecision(
                    allowed=False, risk=RiskLevel.HIGH,
                    reason=f"检测到潜在的提示注入: {pattern}",
                    requires_confirmation=True,
                )
        return SecurityDecision(
            allowed=True, risk=RiskLevel.LOW,
            reason="内容安全",
            requires_confirmation=False,
        )
