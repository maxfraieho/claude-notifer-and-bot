"""
Покращена система навігації для Claude Bot
"""

from typing import List, Dict, Any, Optional
from telegram import InlineKeyboardButton, InlineKeyboardMarkup

class NavigationManager:
    """Менеджер навігації з breadcrumbs та групуванням"""

    def __init__(self):
        self.navigation_stack = []
        self.menu_groups = {
            "main": {
                "title": "🏠 Головне меню",
                "buttons": [
                    ("🚀 Почати роботу", "action:start_coding"),
                    ("📋 Швидкі дії", "action:quick_actions"),
                    ("📊 Статус", "action:status"),
                    ("⚙️ Налаштування", "action:settings")
                ]
            },
            "quick_actions": {
                "title": "⚡ Швидкі дії",
                "buttons": [
                    ("📁 Файли", "quick:files"),
                    ("🔍 Пошук", "quick:search"),
                    ("💾 Git", "quick:git"),
                    ("🧪 Тести", "quick:tests")
                ]
            },
            "file_operations": {
                "title": "📁 Операції з файлами",
                "buttons": [
                    ("📖 Читати", "file:read"),
                    ("✏️ Редагувати", "file:edit"),
                    ("➕ Створити", "file:create"),
                    ("🗑️ Видалити", "file:delete")
                ]
            }
        }

    def get_main_menu(self) -> InlineKeyboardMarkup:
        """Отримати головне меню"""
        return self.create_menu("main")

    def create_menu(self, group_key: str, add_navigation: bool = True) -> InlineKeyboardMarkup:
        """Створити меню для групи"""
        if group_key not in self.menu_groups:
            return InlineKeyboardMarkup([[]])

        group = self.menu_groups[group_key]
        keyboard = []

        # Додаємо кнопки групи
        for text, callback_data in group["buttons"]:
            keyboard.append([InlineKeyboardButton(text, callback_data=callback_data)])

        # Додаємо навігаційні кнопки
        if add_navigation:
            nav_row = []

            # Кнопка "Назад"
            if len(self.navigation_stack) > 0:
                nav_row.append(InlineKeyboardButton("🔙 Назад", callback_data="nav:back"))

            # Кнопка "Головне меню"
            if group_key != "main":
                nav_row.append(InlineKeyboardButton("🏠 Головне", callback_data="nav:main"))

            if nav_row:
                keyboard.append(nav_row)

        return InlineKeyboardMarkup(keyboard)

    def push_navigation(self, current_menu: str):
        """Додати поточне меню до стеку навігації"""
        self.navigation_stack.append(current_menu)

    def pop_navigation(self) -> Optional[str]:
        """Повернутися до попереднього меню"""
        if self.navigation_stack:
            return self.navigation_stack.pop()
        return None

    def get_breadcrumb(self) -> str:
        """Отримати breadcrumb навігації"""
        if not self.navigation_stack:
            return "🏠"

        breadcrumb = "🏠"
        for menu in self.navigation_stack:
            if menu in self.menu_groups:
                title = self.menu_groups[menu]["title"]
                breadcrumb += f" → {title}"

        return breadcrumb

# Глобальний менеджер навігації
nav_manager = NavigationManager()
