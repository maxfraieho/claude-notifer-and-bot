"""
Система прогрес-індикаторів для Claude Bot
"""

import asyncio
from typing import Optional
from telegram import Message

class ProgressIndicator:
    """Клас для відображення прогресу операцій"""

    def __init__(self, message: Message):
        self.message = message
        self.is_running = False
        self.current_step = 0
        self.total_steps = 0

    async def start(self, total_steps: int, initial_text: str = "🔄 Обробка..."):
        """Розпочати відображення прогресу"""
        self.total_steps = total_steps
        self.current_step = 0
        self.is_running = True

        try:
            await self.message.edit_text(initial_text)
        except:
            pass

    async def update(self, step: int, text: str = ""):
        """Оновити прогрес"""
        if not self.is_running:
            return

        self.current_step = step
        percentage = int((step / self.total_steps) * 100) if self.total_steps > 0 else 0

        # Створюємо візуальний індикатор
        filled = "█" * (percentage // 10)
        empty = "░" * (10 - (percentage // 10))
        progress_bar = f"[{filled}{empty}] {percentage}%"

        message_text = f"⏳ {text}\n\n{progress_bar}\nКрок {step}/{self.total_steps}"

        try:
            await self.message.edit_text(message_text)
        except:
            pass

    async def complete(self, final_text: str = "✅ Завершено!"):
        """Завершити відображення прогресу"""
        self.is_running = False

        try:
            await self.message.edit_text(final_text)
        except:
            pass

class StatusMessage:
    """Клас для статусних повідомлень"""

    @staticmethod
    async def show_typing(message: Message, duration: int = 3):
        """Показати індикатор набору тексту"""
        try:
            await message._client.send_chat_action(message.chat.id, "typing")
            await asyncio.sleep(duration)
        except:
            pass

    @staticmethod
    async def show_processing(message: Message, text: str = "🔄 Обробка..."):
        """Показати повідомлення про обробку"""
        try:
            return await message.reply_text(text)
        except:
            return None

    @staticmethod
    async def update_status(status_message: Message, new_text: str):
        """Оновити статусне повідомлення"""
        try:
            await status_message.edit_text(new_text)
        except:
            pass

def create_progress_indicator(message: Message) -> ProgressIndicator:
    """Створити новий прогрес-індикатор"""
    return ProgressIndicator(message)
