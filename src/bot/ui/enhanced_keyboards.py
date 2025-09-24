"""
Enhanced Interactive Keyboard System for DevClaude_bot

Implements advanced keyboard functionality as recommended by the analysis report.
Provides context-aware, dynamic keyboards with improved usability.
"""

import logging
from typing import Dict, List, Optional, Tuple, Any, Callable
from dataclasses import dataclass
from enum import Enum
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton

logger = logging.getLogger(__name__)


class KeyboardType(Enum):
    """Types of keyboards available"""
    INLINE = "inline"
    REPLY = "reply"
    PERSISTENT = "persistent"


class ButtonStyle(Enum):
    """Button styling options"""
    PRIMARY = "🔵"
    SUCCESS = "🟢"
    WARNING = "🟡"
    DANGER = "🔴"
    INFO = "⚪"
    SECONDARY = "⚫"


@dataclass
class EnhancedButton:
    """Enhanced button with metadata and styling"""
    text: str
    callback_data: str
    style: ButtonStyle = ButtonStyle.PRIMARY
    emoji: Optional[str] = None
    description: Optional[str] = None
    enabled: bool = True
    requires_confirmation: bool = False
    tooltip: Optional[str] = None


@dataclass
class KeyboardContext:
    """Context for keyboard generation"""
    user_id: int
    current_directory: Optional[str] = None
    session_active: bool = False
    project_type: Optional[str] = None
    available_commands: List[str] = None
    user_preferences: Dict[str, Any] = None


class EnhancedKeyboardManager:
    """
    Advanced keyboard management system with context-aware generation
    """

    def __init__(self):
        self.keyboard_templates = self._init_keyboard_templates()
        self.context_rules = self._init_context_rules()
        self.user_preferences = {}

    def _init_keyboard_templates(self) -> Dict[str, Dict[str, Any]]:
        """Initialize keyboard templates"""
        return {
            "main_menu": {
                "type": KeyboardType.INLINE,
                "layout": "2x4",
                "buttons": [
                    EnhancedButton("🚀 Start Coding", "action:start_coding", ButtonStyle.SUCCESS,
                                 description="Begin a new coding session with Claude"),
                    EnhancedButton("📁 Browse Files", "action:browse_files", ButtonStyle.INFO,
                                 description="Navigate through project files"),
                    EnhancedButton("🔍 Quick Search", "action:quick_search", ButtonStyle.INFO,
                                 description="Search files and content"),
                    EnhancedButton("💾 Git Status", "action:git_status", ButtonStyle.PRIMARY,
                                 description="Check repository status"),
                    EnhancedButton("📊 Project Stats", "action:project_stats", ButtonStyle.INFO,
                                 description="View project statistics"),
                    EnhancedButton("🧪 Run Tests", "action:run_tests", ButtonStyle.WARNING,
                                 description="Execute test suite"),
                    EnhancedButton("⚙️ Settings", "action:settings", ButtonStyle.SECONDARY,
                                 description="Bot configuration"),
                    EnhancedButton("❓ Help", "action:help", ButtonStyle.INFO,
                                 description="Get help and documentation")
                ],
                "footer_buttons": [
                    EnhancedButton("🔄 Refresh", "action:refresh", ButtonStyle.SECONDARY),
                    EnhancedButton("📋 Commands", "action:show_commands", ButtonStyle.INFO)
                ]
            },

            "file_operations": {
                "type": KeyboardType.INLINE,
                "layout": "3x2",
                "buttons": [
                    EnhancedButton("📖 Read File", "file:read", ButtonStyle.INFO),
                    EnhancedButton("✏️ Edit File", "file:edit", ButtonStyle.PRIMARY),
                    EnhancedButton("📝 Create File", "file:create", ButtonStyle.SUCCESS),
                    EnhancedButton("📋 Copy File", "file:copy", ButtonStyle.INFO),
                    EnhancedButton("🗑️ Delete File", "file:delete", ButtonStyle.DANGER,
                                 requires_confirmation=True),
                    EnhancedButton("📊 File Info", "file:info", ButtonStyle.INFO)
                ],
                "navigation": True
            },

            "project_actions": {
                "type": KeyboardType.INLINE,
                "layout": "2x3",
                "context_dependent": True,
                "buttons": [
                    EnhancedButton("🏗️ Build", "project:build", ButtonStyle.WARNING),
                    EnhancedButton("▶️ Run", "project:run", ButtonStyle.SUCCESS),
                    EnhancedButton("🧪 Test", "project:test", ButtonStyle.INFO),
                    EnhancedButton("📦 Package", "project:package", ButtonStyle.PRIMARY),
                    EnhancedButton("🚀 Deploy", "project:deploy", ButtonStyle.SUCCESS),
                    EnhancedButton("📊 Analyze", "project:analyze", ButtonStyle.INFO)
                ]
            },

            "git_operations": {
                "type": KeyboardType.INLINE,
                "layout": "2x4",
                "buttons": [
                    EnhancedButton("📊 Status", "git:status", ButtonStyle.INFO),
                    EnhancedButton("📥 Pull", "git:pull", ButtonStyle.PRIMARY),
                    EnhancedButton("📤 Push", "git:push", ButtonStyle.SUCCESS),
                    EnhancedButton("📝 Commit", "git:commit", ButtonStyle.WARNING),
                    EnhancedButton("🌿 Branch", "git:branch", ButtonStyle.INFO),
                    EnhancedButton("🔀 Merge", "git:merge", ButtonStyle.WARNING),
                    EnhancedButton("📜 Log", "git:log", ButtonStyle.INFO),
                    EnhancedButton("🏷️ Tag", "git:tag", ButtonStyle.SECONDARY)
                ]
            },

            "quick_actions": {
                "type": KeyboardType.PERSISTENT,
                "layout": "1x6",
                "buttons": [
                    EnhancedButton("/pwd", "cmd:pwd", ButtonStyle.INFO, "📍"),
                    EnhancedButton("/ls", "cmd:ls", ButtonStyle.INFO, "📁"),
                    EnhancedButton("/status", "cmd:status", ButtonStyle.INFO, "📊"),
                    EnhancedButton("/help", "cmd:help", ButtonStyle.INFO, "❓"),
                    EnhancedButton("/actions", "cmd:actions", ButtonStyle.PRIMARY, "⚡"),
                    EnhancedButton("/git", "cmd:git", ButtonStyle.WARNING, "💾")
                ]
            }
        }

    def _init_context_rules(self) -> Dict[str, Callable[[KeyboardContext], bool]]:
        """Initialize context-based rules for keyboard generation"""
        return {
            "has_git": lambda ctx: ctx.current_directory and ".git" in str(ctx.current_directory),
            "has_tests": lambda ctx: ctx.project_type in ["python", "javascript", "typescript"],
            "is_coding": lambda ctx: ctx.session_active,
            "is_admin": lambda ctx: ctx.user_id in [123456789],  # Admin user IDs
            "has_package_manager": lambda ctx: ctx.project_type is not None,
        }

    def generate_keyboard(self, template_name: str, context: KeyboardContext,
                         custom_buttons: Optional[List[EnhancedButton]] = None) -> InlineKeyboardMarkup:
        """
        Generate context-aware keyboard from template

        Args:
            template_name: Name of the keyboard template
            context: Current context for decision making
            custom_buttons: Optional additional buttons

        Returns:
            InlineKeyboardMarkup: Generated keyboard
        """
        if template_name not in self.keyboard_templates:
            logger.warning(f"Unknown keyboard template: {template_name}")
            return self._create_fallback_keyboard()

        template = self.keyboard_templates[template_name]

        # Filter buttons based on context
        available_buttons = self._filter_buttons_by_context(
            template.get("buttons", []), context
        )

        # Add custom buttons if provided
        if custom_buttons:
            available_buttons.extend(custom_buttons)

        # Generate keyboard based on layout
        layout = template.get("layout", "2x4")
        keyboard_markup = self._create_keyboard_layout(
            available_buttons, layout, template.get("type", KeyboardType.INLINE)
        )

        # Add navigation if required
        if template.get("navigation", False):
            keyboard_markup = self._add_navigation_buttons(keyboard_markup, context)

        # Add footer buttons
        footer_buttons = template.get("footer_buttons", [])
        if footer_buttons:
            keyboard_markup = self._add_footer_buttons(keyboard_markup, footer_buttons, context)

        return keyboard_markup

    def _filter_buttons_by_context(self, buttons: List[EnhancedButton],
                                  context: KeyboardContext) -> List[EnhancedButton]:
        """Filter buttons based on current context"""
        filtered_buttons = []

        for button in buttons:
            # Check if button should be enabled based on context
            if self._should_show_button(button, context):
                # Apply context-specific modifications
                modified_button = self._modify_button_for_context(button, context)
                filtered_buttons.append(modified_button)

        return filtered_buttons

    def _should_show_button(self, button: EnhancedButton, context: KeyboardContext) -> bool:
        """Determine if button should be shown based on context"""
        # Always show if no specific rules
        if not hasattr(button, 'context_rules'):
            return button.enabled

        # Check context rules if defined
        context_rules = getattr(button, 'context_rules', [])
        for rule in context_rules:
            if rule in self.context_rules:
                if not self.context_rules[rule](context):
                    return False

        return button.enabled

    def _modify_button_for_context(self, button: EnhancedButton,
                                  context: KeyboardContext) -> EnhancedButton:
        """Modify button based on current context"""
        # Create a copy to avoid modifying the original
        modified_button = EnhancedButton(
            text=button.text,
            callback_data=button.callback_data,
            style=button.style,
            emoji=button.emoji,
            description=button.description,
            enabled=button.enabled,
            requires_confirmation=button.requires_confirmation,
            tooltip=button.tooltip
        )

        # Context-specific modifications
        if context.session_active and "Start" in button.text:
            modified_button.text = "🔄 Continue Session"
            modified_button.style = ButtonStyle.WARNING

        if context.current_directory and "Browse" in button.text:
            dir_name = str(context.current_directory).split("/")[-1]
            modified_button.text = f"📁 Browse {dir_name[:10]}"

        return modified_button

    def _create_keyboard_layout(self, buttons: List[EnhancedButton],
                               layout: str, keyboard_type: KeyboardType) -> InlineKeyboardMarkup:
        """Create keyboard with specified layout"""
        if not buttons:
            return InlineKeyboardMarkup([[]])

        # Parse layout (e.g., "2x4" means 2 columns, up to 4 rows)
        try:
            cols, max_rows = map(int, layout.split('x'))
        except (ValueError, AttributeError):
            cols, max_rows = 2, 4

        keyboard_rows = []
        current_row = []

        for i, button in enumerate(buttons):
            # Format button text with emoji and style
            button_text = self._format_button_text(button)

            inline_button = InlineKeyboardButton(
                text=button_text,
                callback_data=button.callback_data
            )

            current_row.append(inline_button)

            # Start new row when reaching column limit or max buttons per row
            if len(current_row) >= cols or i == len(buttons) - 1:
                keyboard_rows.append(current_row)
                current_row = []

            # Respect max rows limit
            if len(keyboard_rows) >= max_rows:
                break

        return InlineKeyboardMarkup(keyboard_rows)

    def _format_button_text(self, button: EnhancedButton) -> str:
        """Format button text with emoji and styling"""
        text = button.text

        # Add emoji if specified
        if button.emoji and button.emoji not in text:
            text = f"{button.emoji} {text}"

        # Add style indicator if needed
        if button.style != ButtonStyle.PRIMARY:
            style_emoji = button.style.value
            if style_emoji not in text:
                text = f"{style_emoji} {text}"

        # Add confirmation indicator
        if button.requires_confirmation:
            text = f"⚠️ {text}"

        # Limit length to prevent UI issues
        if len(text) > 30:
            text = text[:27] + "..."

        return text

    def _add_navigation_buttons(self, keyboard: InlineKeyboardMarkup,
                               context: KeyboardContext) -> InlineKeyboardMarkup:
        """Add navigation buttons to keyboard"""
        nav_buttons = []

        # Back button
        nav_buttons.append(InlineKeyboardButton("🔙 Back", callback_data="nav:back"))

        # Home button
        nav_buttons.append(InlineKeyboardButton("🏠 Home", callback_data="nav:home"))

        # Refresh button
        nav_buttons.append(InlineKeyboardButton("🔄 Refresh", callback_data="nav:refresh"))

        # Add navigation row
        keyboard.inline_keyboard.append(nav_buttons)
        return keyboard

    def _add_footer_buttons(self, keyboard: InlineKeyboardMarkup,
                           footer_buttons: List[EnhancedButton],
                           context: KeyboardContext) -> InlineKeyboardMarkup:
        """Add footer buttons to keyboard"""
        footer_row = []

        for button in footer_buttons[:3]:  # Limit to 3 footer buttons
            if self._should_show_button(button, context):
                button_text = self._format_button_text(button)
                footer_row.append(InlineKeyboardButton(
                    text=button_text,
                    callback_data=button.callback_data
                ))

        if footer_row:
            keyboard.inline_keyboard.append(footer_row)

        return keyboard

    def _create_fallback_keyboard(self) -> InlineKeyboardMarkup:
        """Create a basic fallback keyboard when template is not found"""
        fallback_buttons = [
            [InlineKeyboardButton("🏠 Home", callback_data="nav:home")],
            [InlineKeyboardButton("📋 Commands", callback_data="action:help")]
        ]
        return InlineKeyboardMarkup(fallback_buttons)

    def create_confirmation_keyboard(self, action: str, context: KeyboardContext) -> InlineKeyboardMarkup:
        """Create confirmation keyboard for dangerous actions"""
        confirm_buttons = [
            [
                InlineKeyboardButton("✅ Confirm", callback_data=f"confirm:{action}"),
                InlineKeyboardButton("❌ Cancel", callback_data="confirm:cancel")
            ],
            [InlineKeyboardButton("🏠 Home", callback_data="nav:home")]
        ]
        return InlineKeyboardMarkup(confirm_buttons)

    def create_contextual_keyboard(self, context: KeyboardContext) -> InlineKeyboardMarkup:
        """Create keyboard based purely on current context"""
        buttons = []

        # Add context-specific buttons
        if context.session_active:
            buttons.extend([
                EnhancedButton("💬 Continue Chat", "action:continue_chat", ButtonStyle.SUCCESS),
                EnhancedButton("⏸️ Pause Session", "action:pause_session", ButtonStyle.WARNING),
            ])
        else:
            buttons.append(EnhancedButton("🚀 Start Session", "action:start_session", ButtonStyle.SUCCESS))

        if context.current_directory:
            buttons.extend([
                EnhancedButton("📁 Browse Files", "action:browse_files", ButtonStyle.INFO),
                EnhancedButton("🔍 Search Here", "action:search_current", ButtonStyle.INFO),
            ])

        # Add project-specific buttons
        if context.project_type == "python":
            buttons.extend([
                EnhancedButton("🐍 Python Shell", "action:python_shell", ButtonStyle.PRIMARY),
                EnhancedButton("🧪 Run Tests", "action:pytest", ButtonStyle.WARNING),
            ])
        elif context.project_type == "javascript":
            buttons.extend([
                EnhancedButton("📦 NPM Install", "action:npm_install", ButtonStyle.PRIMARY),
                EnhancedButton("▶️ NPM Run", "action:npm_run", ButtonStyle.SUCCESS),
            ])

        return self._create_keyboard_layout(buttons, "2x4", KeyboardType.INLINE)

    def get_user_preferences(self, user_id: int) -> Dict[str, Any]:
        """Get user preferences for keyboard customization"""
        return self.user_preferences.get(user_id, {
            "keyboard_style": "full",
            "show_tooltips": True,
            "confirm_dangerous": True,
            "preferred_layout": "2x4"
        })

    def set_user_preference(self, user_id: int, key: str, value: Any) -> bool:
        """Set user preference"""
        if user_id not in self.user_preferences:
            self.user_preferences[user_id] = {}

        self.user_preferences[user_id][key] = value
        return True

    def create_adaptive_keyboard(self, user_id: int, context: KeyboardContext,
                                base_template: str = "main_menu") -> InlineKeyboardMarkup:
        """
        Create adaptive keyboard that learns from user behavior

        Args:
            user_id: User identifier
            context: Current context
            base_template: Base template to adapt

        Returns:
            InlineKeyboardMarkup: Adaptive keyboard
        """
        # Get user preferences
        preferences = self.get_user_preferences(user_id)

        # Generate base keyboard
        keyboard = self.generate_keyboard(base_template, context)

        # Apply user preferences (simplified example)
        if preferences.get("keyboard_style") == "minimal":
            # Reduce to essential buttons only
            keyboard = self._create_minimal_keyboard(context)
        elif preferences.get("keyboard_style") == "comprehensive":
            # Add more detailed options
            keyboard = self._create_comprehensive_keyboard(context)

        return keyboard

    def _create_minimal_keyboard(self, context: KeyboardContext) -> InlineKeyboardMarkup:
        """Create minimal keyboard with essential functions only"""
        essential_buttons = [
            EnhancedButton("💬 Chat", "action:chat", ButtonStyle.SUCCESS),
            EnhancedButton("📁 Files", "action:files", ButtonStyle.INFO),
            EnhancedButton("⚙️ Settings", "action:settings", ButtonStyle.SECONDARY),
        ]
        return self._create_keyboard_layout(essential_buttons, "1x3", KeyboardType.INLINE)

    def _create_comprehensive_keyboard(self, context: KeyboardContext) -> InlineKeyboardMarkup:
        """Create comprehensive keyboard with advanced options"""
        # This would include more detailed buttons based on context
        return self.generate_keyboard("main_menu", context)


# Global keyboard manager instance
enhanced_keyboard_manager = EnhancedKeyboardManager()


# Convenience functions for easy integration
def get_main_keyboard(user_id: int, context: KeyboardContext) -> InlineKeyboardMarkup:
    """Get main menu keyboard for user"""
    return enhanced_keyboard_manager.create_adaptive_keyboard(user_id, context, "main_menu")


def get_contextual_keyboard(user_id: int, context: KeyboardContext) -> InlineKeyboardMarkup:
    """Get context-aware keyboard"""
    return enhanced_keyboard_manager.create_contextual_keyboard(context)


def get_file_operations_keyboard(user_id: int, context: KeyboardContext) -> InlineKeyboardMarkup:
    """Get file operations keyboard"""
    return enhanced_keyboard_manager.generate_keyboard("file_operations", context)


def get_git_keyboard(user_id: int, context: KeyboardContext) -> InlineKeyboardMarkup:
    """Get git operations keyboard"""
    return enhanced_keyboard_manager.generate_keyboard("git_operations", context)