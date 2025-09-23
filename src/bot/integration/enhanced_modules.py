"""
Enhanced Modules Integration
Інтеграція нових модулів створених Moon Architect Bot
"""

import logging
from typing import Dict, Any, Optional

from telegram import Update
from telegram.ext import ContextTypes

from ..ui.navigation import NavigationManager, nav_manager
from ..ui.progress import ProgressIndicator, StatusMessage, create_progress_indicator
from ..utils.error_handler import ErrorHandler, error_handler, safe_execute
from ...localization.i18n import i18n, _

logger = logging.getLogger(__name__)

class EnhancedModulesIntegration:
    """Інтеграція покращених модулів в основну архітектуру бота"""

    def __init__(self):
        self.navigation_manager = nav_manager
        self.i18n = i18n
        self.error_handler = ErrorHandler()

    async def initialize(self):
        """Ініціалізація покращених модулів"""
        logger.info("Initializing enhanced modules integration")

        # Ініціалізуємо локалізацію
        self.i18n.load_translations()

        # Встановлюємо українську мову за замовчуванням
        self.i18n.set_locale("uk")

        logger.info("Enhanced modules initialized successfully")

    def get_navigation_manager(self) -> NavigationManager:
        """Отримати менеджер навігації"""
        return self.navigation_manager

    def get_localization(self):
        """Отримати систему локалізації"""
        return self.i18n

    def create_progress_indicator(self, message) -> ProgressIndicator:
        """Створити індикатор прогресу"""
        return create_progress_indicator(message)

    async def handle_navigation_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обробити callback навігації"""
        query = update.callback_query
        await query.answer()

        callback_data = query.data

        if callback_data == "nav:back":
            # Повернутися до попереднього меню
            previous_menu = self.navigation_manager.pop_navigation()
            if previous_menu:
                keyboard = self.navigation_manager.create_menu(previous_menu)
                breadcrumb = self.navigation_manager.get_breadcrumb()

                text = f"{breadcrumb}\n\n{_('messages.navigation_back')}"
                await query.edit_message_text(text, reply_markup=keyboard)
            else:
                # Якщо немає попереднього меню, повернутися до головного
                await self.show_main_menu(update, context)

        elif callback_data == "nav:main":
            # Повернутися до головного меню
            await self.show_main_menu(update, context)

    async def show_main_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Показати головне меню"""
        keyboard = self.navigation_manager.get_main_menu()
        text = f"🏠 {_('commands.start')}\n\n{_('messages.welcome')}"

        if update.callback_query:
            await update.callback_query.edit_message_text(text, reply_markup=keyboard)
        else:
            await update.message.reply_text(text, reply_markup=keyboard)

    async def show_quick_actions_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Показати меню швидких дій"""
        self.navigation_manager.push_navigation("main")
        keyboard = self.navigation_manager.create_menu("quick_actions")
        breadcrumb = self.navigation_manager.get_breadcrumb()

        text = f"{breadcrumb}\n\n⚡ {_('buttons.quick_actions')}\n\n{_('messages.quick_actions_help')}"

        if update.callback_query:
            await update.callback_query.edit_message_text(text, reply_markup=keyboard)
        else:
            await update.message.reply_text(text, reply_markup=keyboard)

    @error_handler
    async def enhanced_command_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Покращений обробник команд з прогрес-індикаторами"""

        # Показуємо статус обробки
        await StatusMessage.show_typing(update.message, 2)

        # Створюємо прогрес-індикатор
        progress = self.create_progress_indicator(update.message)

        try:
            await progress.start(3, _('messages.processing'))

            # Симуляція обробки команди
            await progress.update(1, _('messages.analyzing'))
            # Тут була б реальна логіка команди

            await progress.update(2, _('messages.generating_response'))
            # Більше логіки

            await progress.update(3, _('messages.completing'))
            # Завершення

            await progress.complete(_('messages.completed'))

        except Exception as e:
            await self.error_handler.handle_error(e, update.message, {
                "command": "enhanced_command",
                "user_id": update.effective_user.id
            })

    def setup_enhanced_handlers(self, application):
        """Налаштувати покращені обробники"""
        from telegram.ext import CallbackQueryHandler

        # Додаємо обробники навігації
        nav_handler = CallbackQueryHandler(
            self.handle_navigation_callback,
            pattern="^nav:"
        )
        application.add_handler(nav_handler)

        logger.info("Enhanced handlers registered successfully")

    async def switch_language(self, language: str, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Перемкнути мову інтерфейсу"""
        if language in ["uk", "en"]:
            self.i18n.set_locale(language)

            # Зберігаємо вибір мови в контекст користувача
            if not hasattr(context, 'user_data'):
                context.user_data = {}
            context.user_data['language'] = language

            success_message = _('messages.language_changed')

            if update.callback_query:
                await update.callback_query.answer(success_message)
                await self.show_main_menu(update, context)
            else:
                await update.message.reply_text(success_message)
        else:
            error_message = _('messages.language_not_supported')
            await update.message.reply_text(error_message)

    def get_user_language(self, context: ContextTypes.DEFAULT_TYPE) -> str:
        """Отримати мову користувача"""
        if hasattr(context, 'user_data') and 'language' in context.user_data:
            return context.user_data['language']
        return 'uk'  # За замовчуванням українська

    async def create_enhanced_keyboard(self, menu_type: str = "main"):
        """Створити покращену клавіатуру з локалізацією"""
        keyboard = self.navigation_manager.create_menu(menu_type)
        return keyboard

# Глобальний екземпляр інтеграції
enhanced_integration = EnhancedModulesIntegration()

async def initialize_enhanced_modules():
    """Ініціалізація покращених модулів"""
    await enhanced_integration.initialize()

def get_enhanced_integration() -> EnhancedModulesIntegration:
    """Отримати екземпляр інтеграції"""
    return enhanced_integration