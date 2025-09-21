"""Quick Actions feature implementation.

Provides context-aware quick action suggestions for common development tasks.
"""

import logging
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional

from telegram import InlineKeyboardButton, InlineKeyboardMarkup

from src.storage.models import SessionModel

logger = logging.getLogger(__name__)


@dataclass
class QuickAction:
    """Represents a quick action suggestion."""

    id: str
    name: str
    description: str
    command: str
    icon: str
    category: str
    context_required: List[str]  # Required context keys
    priority: int = 0  # Higher = more important


class QuickActionManager:
    """Manages quick action suggestions based on context."""

    def __init__(self) -> None:
        """Initialize the quick action manager."""
        self.actions = self._create_default_actions()
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

    def _create_default_actions(self) -> Dict[str, QuickAction]:
        """Create default quick actions."""
        return {
            "test": QuickAction(
                id="test",
                name="Run Tests",
                description="Run project tests",
                command="test",
                icon="🧪",
                category="testing",
                context_required=["has_tests"],
                priority=10,
            ),
            "install": QuickAction(
                id="install",
                name="Install Dependencies",
                description="Install project dependencies",
                command="install",
                icon="📦",
                category="setup",
                context_required=["has_package_manager"],
                priority=9,
            ),
            "format": QuickAction(
                id="format",
                name="Format Code",
                description="Format code with project formatter",
                command="format",
                icon="🎨",
                category="quality",
                context_required=["has_formatter"],
                priority=7,
            ),
            "lint": QuickAction(
                id="lint",
                name="Lint Code",
                description="Check code quality",
                command="lint",
                icon="🔍",
                category="quality",
                context_required=["has_linter"],
                priority=8,
            ),
            "security": QuickAction(
                id="security",
                name="Security Scan",
                description="Run security vulnerability scan",
                command="security",
                icon="🔒",
                category="security",
                context_required=["has_dependencies"],
                priority=6,
            ),
            "optimize": QuickAction(
                id="optimize",
                name="Optimize",
                description="Optimize code performance",
                command="optimize",
                icon="⚡",
                category="performance",
                context_required=["has_code"],
                priority=5,
            ),
            "document": QuickAction(
                id="document",
                name="Generate Docs",
                description="Generate documentation",
                command="document",
                icon="📝",
                category="documentation",
                context_required=["has_code"],
                priority=4,
            ),
            "refactor": QuickAction(
                id="refactor",
                name="Refactor",
                description="Suggest code improvements",
                command="refactor",
                icon="🔧",
                category="quality",
                context_required=["has_code"],
                priority=3,
            ),
            # NEW FUNCTIONAL ACTIONS
            "ls": QuickAction(
                id="ls",
                name="Show Files",
                description="List files in current directory",
                command="ls -la",
                icon="📋",
                category="navigation",
                context_required=[],  # Always available
                priority=15,
            ),
            "pwd": QuickAction(
                id="pwd",
                name="Current Location",
                description="Show current directory path",
                command="pwd",
                icon="🏠",
                category="navigation",
                context_required=[],
                priority=14,
            ),
            "git_status": QuickAction(
                id="git_status",
                name="Git Status",
                description="Show git repository status",
                command="git status",
                icon="💾",
                category="git",
                context_required=[],
                priority=13,
            ),
            "grep": QuickAction(
                id="grep",
                name="Search TODOs",
                description="Find TODO, FIXME, BUG comments",
                command="grep -r \"TODO\\|FIXME\\|BUG\" . --include=\"*.py\" --include=\"*.js\" --include=\"*.ts\" || echo 'No TODO/FIXME/BUG found'",
                icon="🔍",
                category="search",
                context_required=[],
                priority=12,
            ),
            "find_files": QuickAction(
                id="find_files",
                name="Find Code Files",
                description="Find Python, JS, TS files",
                command="find . -type f -name \"*.py\" -o -name \"*.js\" -o -name \"*.ts\" | head -20",
                icon="🔍",
                category="search",
                context_required=[],
                priority=11,
            ),
        }

    async def get_suggestions(
        self, session: SessionModel, limit: int = 6
    ) -> List[QuickAction]:
        """Get quick action suggestions based on session context.

        Args:
            session: Current session
            limit: Maximum number of suggestions

        Returns:
            List of suggested actions
        """
        try:
            # Analyze context
            context = await self._analyze_context(session)

            # Filter actions based on context
            available_actions = []
            for action in self.actions.values():
                if self._is_action_available(action, context):
                    available_actions.append(action)

            # Sort by priority and return top N
            available_actions.sort(key=lambda x: x.priority, reverse=True)
            return available_actions[:limit]

        except Exception as e:
            self.logger.error(f"Error getting suggestions: {e}")
            return []

    async def _analyze_context(self, session: SessionModel) -> Dict[str, Any]:
        """Analyze session context to determine available actions.

        Args:
            session: Current session

        Returns:
            Context dictionary
        """
        context = {
            "has_code": True,  # Default assumption
            "has_tests": False,
            "has_package_manager": False,
            "has_formatter": False,
            "has_linter": False,
            "has_dependencies": False,
        }

        # Simplified context analysis without session.context dependency
        # Just return functional actions that are always available
        context.update({
            "has_tests": True,  # Always suggest test actions
            "has_package_manager": True,  # Always suggest install actions
            "has_formatter": True,  # Always suggest format actions
            "has_linter": True,  # Always suggest lint actions
            "has_dependencies": True,  # Always suggest security actions
        })

        # File-based context analysis could be added here
        # For now, we'll use heuristics based on session history

        return context

    def _is_action_available(
        self, action: QuickAction, context: Dict[str, Any]
    ) -> bool:
        """Check if an action is available in the given context.

        Args:
            action: The action to check
            context: Current context

        Returns:
            True if action is available
        """
        # Check all required context keys
        for key in action.context_required:
            if not context.get(key, False):
                return False
        return True

    def create_inline_keyboard(
        self, actions: List[QuickAction], columns: int = 2, localization=None, user_lang=None
    ) -> InlineKeyboardMarkup:
        """Create inline keyboard for quick actions with localization support.

        Args:
            actions: List of actions to display
            columns: Number of columns in keyboard
            localization: Localization manager (optional)
            user_lang: User language code (optional)

        Returns:
            Inline keyboard markup
        """
        keyboard = []
        row = []

        for i, action in enumerate(actions):
            # Try to get localized action name, fallback to default
            if localization and user_lang:
                translation_key = f"quick_actions.{action.id}.name"
                action_text = localization.get(translation_key, language=user_lang)
                # If translation not found, localization.get() returns the key itself
                if not action_text or action_text == translation_key:
                    action_text = f"{action.icon} {action.name}"
            else:
                action_text = f"{action.icon} {action.name}"
                
            button = InlineKeyboardButton(
                text=action_text,
                callback_data=f"quick_action:{action.id}",
            )
            row.append(button)

            # Add row when full or last item
            if len(row) >= columns or i == len(actions) - 1:
                keyboard.append(row)
                row = []

        return InlineKeyboardMarkup(keyboard)

    async def execute_action(
        self, action_id: str, session: SessionModel, callback: Optional[Callable] = None
    ) -> str:
        """Execute a quick action.

        Args:
            action_id: ID of action to execute
            session: Current session
            callback: Optional callback for command execution

        Returns:
            Command to execute
        """
        action = self.actions.get(action_id)
        if not action:
            raise ValueError(f"Unknown action: {action_id}")

        self.logger.info(
            f"Executing quick action: {action.name} for session {session.id}"
        )

        # Return the command - actual execution is handled by the bot
        return action.command
