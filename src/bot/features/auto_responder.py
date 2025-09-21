"""Auto-responder for Claude CLI system prompts."""

import re
import structlog
from typing import Dict, List, Optional, Tuple

logger = structlog.get_logger()


class AutoResponder:
    """Automatically responds to Claude CLI system prompts during task execution."""

    def __init__(self):
        """Initialize auto-responder with predefined response patterns."""
        self.response_patterns = self._initialize_response_patterns()
        self.confirmation_responses = self._initialize_confirmation_responses()
        self.enabled = True

    def _initialize_response_patterns(self) -> Dict[str, str]:
        """Initialize patterns that should trigger auto-responses."""
        return {
            # Confirmation prompts
            r"(?i)(do\s+you\s+want\s+to\s+continue|continue\s*\?|proceed\s*\?)": "yes",
            r"(?i)(are\s+you\s+sure|confirm|confirmation)": "yes",
            r"(?i)(yes\s*/\s*no|y\s*/\s*n|\[y/n\])": "y",

            # File operations
            r"(?i)(overwrite|replace)\s+.*\s*\?": "yes",
            r"(?i)(create\s+file|create\s+directory).*\s*\?": "yes",
            r"(?i)(delete|remove)\s+.*\s*\?": "yes",

            # Git operations
            r"(?i)(commit\s+changes|add\s+files).*\s*\?": "yes",
            r"(?i)(push\s+to\s+remote|pull\s+from\s+remote).*\s*\?": "yes",

            # Package/dependency management
            r"(?i)(install\s+packages|update\s+dependencies).*\s*\?": "yes",
            r"(?i)(upgrade\s+packages|downgrade\s+packages).*\s*\?": "yes",

            # Permission/authentication
            r"(?i)(allow\s+access|grant\s+permission).*\s*\?": "yes",
            r"(?i)(authenticate|login).*\s*\?": "yes",

            # System operations
            r"(?i)(restart\s+service|reload\s+configuration).*\s*\?": "yes",
            r"(?i)(apply\s+changes|save\s+configuration).*\s*\?": "yes",

            # Time/wait prompts
            r"(?i)(press\s+enter|press\s+any\s+key)": "\n",
            r"(?i)(wait\s+for|continue\s+when\s+ready)": "\n",

            # Ukrainian patterns
            r"(?i)(продовжити|продовжувати).*\s*\?": "так",
            r"(?i)(ви\s+впевнені|підтвердження).*\s*\s*\?": "так",
            r"(?i)(так\s*/\s*ні|т\s*/\s*н|\[т/н\])": "т",
            r"(?i)(перезаписати|замінити).*\s*\?": "так",
            r"(?i)(створити\s+файл|створити\s+каталог).*\s*\?": "так",
            r"(?i)(видалити|вилучити).*\s*\?": "так",
        }

    def _initialize_confirmation_responses(self) -> Dict[str, List[str]]:
        """Initialize contextual confirmation responses."""
        return {
            "file_operations": ["yes", "y", "так", "т"],
            "git_operations": ["yes", "y", "так", "т"],
            "package_management": ["yes", "y", "так", "т"],
            "system_operations": ["yes", "y", "так", "т"],
            "general_confirmation": ["yes", "y", "так", "т"],
            "continue_prompts": ["", "\n", "так", "yes"],
        }

    def should_auto_respond(self, message: str, context: Optional[str] = None) -> bool:
        """Determine if message requires an auto-response."""
        if not self.enabled:
            return False

        # Check if message contains any response patterns
        for pattern in self.response_patterns.keys():
            if re.search(pattern, message):
                logger.debug("Auto-response pattern matched", pattern=pattern, message=message[:100])
                return True

        # Check for other indicators that suggest user input is needed
        if self._is_input_prompt(message):
            logger.debug("Input prompt detected", message=message[:100])
            return True

        return False

    def get_auto_response(self, message: str, context: Optional[str] = None) -> str:
        """Generate automatic response for the given message."""
        if not self.enabled:
            return ""

        # Try pattern matching first
        for pattern, response in self.response_patterns.items():
            if re.search(pattern, message):
                logger.info("Auto-responding with pattern", pattern=pattern, response=response)
                return response

        # Contextual responses based on content analysis
        response = self._analyze_and_respond(message, context)
        if response:
            logger.info("Auto-responding with analysis", message=message[:100], response=response)
            return response

        # Default safe response for confirmation prompts
        if self._is_confirmation_prompt(message):
            default_response = "yes"
            logger.info("Auto-responding with default", response=default_response)
            return default_response

        # Last resort - enter key for continue prompts
        logger.info("Auto-responding with enter key")
        return "\n"

    def _is_input_prompt(self, message: str) -> bool:
        """Check if message is asking for user input."""
        input_indicators = [
            r"(?i)enter\s+",
            r"(?i)input\s+",
            r"(?i)type\s+",
            r"(?i)provide\s+",
            r"(?i)specify\s+",
            r"\?\s*$",  # Ends with question mark
            r":\s*$",   # Ends with colon
            r">\s*$",   # Ends with greater than
            r"\[.*\]\s*$",  # Ends with brackets
            # Ukrainian
            r"(?i)введіть\s+",
            r"(?i)надайте\s+",
            r"(?i)вкажіть\s+",
        ]

        return any(re.search(pattern, message) for pattern in input_indicators)

    def _is_confirmation_prompt(self, message: str) -> bool:
        """Check if message is asking for confirmation."""
        confirmation_indicators = [
            r"(?i)(yes|no)",
            r"(?i)(y/n)",
            r"(?i)confirm",
            r"(?i)sure",
            r"(?i)proceed",
            r"(?i)continue",
            r"(?i)agree",
            # Ukrainian
            r"(?i)(так|ні)",
            r"(?i)(т/н)",
            r"(?i)підтвердити",
            r"(?i)впевнені",
            r"(?i)продовжити",
            r"(?i)згодні",
        ]

        return any(re.search(pattern, message) for pattern in confirmation_indicators)

    def _analyze_and_respond(self, message: str, context: Optional[str] = None) -> Optional[str]:
        """Analyze message content and generate contextual response."""
        message_lower = message.lower()

        # File operation context
        if any(word in message_lower for word in ["file", "directory", "folder", "create", "delete", "modify"]):
            if any(word in message_lower for word in ["overwrite", "replace", "exists"]):
                return "yes"  # Safe to overwrite in automated context

        # Git operation context
        if any(word in message_lower for word in ["git", "commit", "push", "pull", "merge", "branch"]):
            if any(word in message_lower for word in ["push", "commit", "add"]):
                return "yes"  # Proceed with git operations

        # Package management context
        if any(word in message_lower for word in ["install", "update", "upgrade", "package", "dependency"]):
            return "yes"  # Proceed with package operations

        # Permission/security context (be more cautious)
        if any(word in message_lower for word in ["permission", "security", "auth", "login", "password"]):
            # For auth prompts, we might need specific handling
            if "password" in message_lower or "token" in message_lower:
                return None  # Don't auto-respond to password prompts
            return "yes"

        # Time-based operations
        if any(word in message_lower for word in ["wait", "timeout", "retry", "continue"]):
            return "yes"

        return None

    def configure_patterns(self, custom_patterns: Dict[str, str]) -> None:
        """Configure custom response patterns."""
        self.response_patterns.update(custom_patterns)
        logger.info("Updated auto-response patterns", new_patterns=custom_patterns)

    def add_pattern(self, pattern: str, response: str) -> None:
        """Add a single response pattern."""
        self.response_patterns[pattern] = response
        logger.info("Added auto-response pattern", pattern=pattern, response=response)

    def remove_pattern(self, pattern: str) -> bool:
        """Remove a response pattern."""
        if pattern in self.response_patterns:
            del self.response_patterns[pattern]
            logger.info("Removed auto-response pattern", pattern=pattern)
            return True
        return False

    def enable(self) -> None:
        """Enable auto-responses."""
        self.enabled = True
        logger.info("Auto-responder enabled")

    def disable(self) -> None:
        """Disable auto-responses."""
        self.enabled = False
        logger.info("Auto-responder disabled")

    def get_status(self) -> Dict[str, any]:
        """Get current auto-responder status."""
        return {
            "enabled": self.enabled,
            "pattern_count": len(self.response_patterns),
            "patterns": list(self.response_patterns.keys())
        }

    def test_response(self, message: str, context: Optional[str] = None) -> Tuple[bool, str]:
        """Test what response would be generated for a message."""
        should_respond = self.should_auto_respond(message, context)
        response = ""

        if should_respond:
            response = self.get_auto_response(message, context)

        return should_respond, response

    def get_safe_responses(self) -> List[str]:
        """Get list of responses considered safe for automation."""
        return [
            "yes", "y", "так", "т",
            "no", "n", "ні", "н",
            "\n", "", "continue", "продовжити"
        ]

    def is_dangerous_prompt(self, message: str) -> bool:
        """Check if prompt might be dangerous to auto-respond to."""
        dangerous_indicators = [
            r"(?i)(delete\s+all|remove\s+everything|format\s+disk)",
            r"(?i)(sudo\s+rm|rm\s+-rf)",
            r"(?i)(drop\s+database|truncate\s+table)",
            r"(?i)(factory\s+reset|system\s+restore)",
            r"(?i)(password|secret|key|token)",
            # Ukrainian
            r"(?i)(видалити\s+все|форматувати\s+диск)",
            r"(?i)(пароль|секрет|ключ|токен)",
        ]

        return any(re.search(pattern, message) for pattern in dangerous_indicators)

    def validate_response_safety(self, message: str, response: str) -> bool:
        """Validate if the auto-response is safe for the given prompt."""
        # Never auto-respond to dangerous prompts
        if self.is_dangerous_prompt(message):
            logger.warning("Dangerous prompt detected, blocking auto-response", message=message[:100])
            return False

        # Check if response is in safe list
        if response.lower().strip() not in [r.lower() for r in self.get_safe_responses()]:
            logger.warning("Unsafe auto-response detected", response=response, message=message[:100])
            return False

        return True