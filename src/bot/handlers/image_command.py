"""Main /img command handler for image processing.

Features:
- Multi-image upload support  
- Batch processing with Claude CLI
- Session management for image contexts
- Progress indicators and error handling
"""

import asyncio
import uuid
from pathlib import Path
from typing import Dict, List, Optional, cast
import structlog
from telegram import Update
from telegram.ext import ContextTypes

from ...claude.facade import ClaudeIntegration
from ...claude.exceptions import ClaudeError, ClaudeTimeoutError, ClaudeProcessError
from ...config.settings import Settings
from ...exceptions import SecurityError
from ...localization.util import t, get_user_id, get_effective_message
from ..features.image_processor import ImageProcessor, ProcessedImage
from ..utils.error_handler import safe_user_error

logger = structlog.get_logger(__name__)

class ImageCommandHandler:
    """Handler for /img command and image processing workflow."""

    def __init__(self, settings: Settings, image_processor: ImageProcessor):
        """Initialize image command handler."""
        self.settings = settings
        self.image_processor = image_processor
        self.active_sessions: Dict[int, 'ImageSession'] = {}
        self.max_images_per_batch = settings.image_max_batch_size
        self.session_timeout = settings.image_session_timeout_minutes * 60

    async def handle_img_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /img command to start image processing session."""
        logger.debug("handle_img_command called", update_type=type(update).__name__)

        user_id = get_user_id(update)
        message = get_effective_message(update)

        logger.debug("handle_img_command data", user_id=user_id, has_message=message is not None)

        if not user_id or not message:
            logger.warning("handle_img_command: missing user_id or message")
            return

        # Check if image processing is enabled
        if not self.settings.enable_image_processing:
            logger.warning("Image processing disabled in settings")
            error_text = await t(context, user_id, "errors.image_processing_disabled")
            await message.reply_text(error_text)
            return

        logger.info("Starting image command session", user_id=user_id)

        # Extract initial instruction from command
        message_text = message.text or ""
        parts = message_text.split(maxsplit=1) if message_text else []
        initial_instruction = parts[1] if len(parts) > 1 else None

        # Create new image session
        session = ImageSession(
            user_id=user_id,
            initial_instruction=initial_instruction,
            timeout=self.session_timeout
        )
        self.active_sessions[user_id] = session

        # Send instruction message
        instruction_text = await self._get_instruction_message(context, user_id)
        await message.reply_text(
            instruction_text,
            parse_mode=None
        )

        # Set user state for image collection
        if context.user_data is not None:
            context.user_data['awaiting_images'] = True
            context.user_data['image_session_id'] = session.session_id
        else:
            context.user_data = {
                'awaiting_images': True,
                'image_session_id': session.session_id
            }

        # Schedule session cleanup
        asyncio.create_task(self._cleanup_session_after_timeout(user_id, session.session_id))

    async def handle_image_upload(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle image uploads during an active session."""
        logger.debug("handle_image_upload called", update_type=type(update).__name__)

        user_id = get_user_id(update)
        message = get_effective_message(update)

        logger.debug("handle_image_upload data", user_id=user_id, has_message=message is not None,
                     user_in_sessions=user_id in self.active_sessions if user_id else False)

        if not user_id or not message or user_id not in self.active_sessions:
            logger.warning("handle_image_upload: missing user_id/message or no active session")
            return

        session = self.active_sessions[user_id]

        if not session.is_active():
            logger.warning("Session expired for user", user_id=user_id)
            await self._cleanup_session(user_id, context)
            error_text = await t(context, user_id, "commands.img.session_expired")
            await message.reply_text(error_text)
            return

        try:
            # Process the uploaded image
            logger.debug("Processing image upload", has_photo=hasattr(message, 'photo') and message.photo is not None,
                        photo_type=type(message.photo).__name__ if hasattr(message, 'photo') and message.photo else None)

            photo = None
            logger.debug("Photo check details",
                        has_photo=bool(message.photo),
                        photo_type=type(message.photo).__name__ if message.photo else None,
                        photo_length=len(message.photo) if message.photo else 0,
                        is_list=isinstance(message.photo, list) if message.photo else False,
                        is_tuple=isinstance(message.photo, tuple) if message.photo else False)

            if message.photo and (isinstance(message.photo, (list, tuple))) and len(message.photo) > 0:
                photo = message.photo[-1]
                logger.debug("Selected photo", photo_id=photo.file_id if photo else None)

            if photo:
                processed_image = await self.image_processor.process_telegram_photo(
                    photo, 
                    message.caption,
                    user_id
                )
                session.add_image(processed_image)

                # Send confirmation
                confirmation_text = await t(
                    context, user_id, "commands.img.image_received",
                    current=len(session.images),
                    max=self.max_images_per_batch
                )
                await message.reply_text(confirmation_text)

                # Check if batch is full
                if len(session.images) >= self.max_images_per_batch:
                    await self._process_session_images(update, context, session)

        except SecurityError as e:
            logger.warning("Security error processing image", error=str(e), user_id=user_id)
            await message.reply_text(f"❌ Security error: {str(e)}")
        except Exception as e:
            logger.error("Error processing image upload", error=str(e), user_id=user_id)
            await safe_user_error(message, f"Error processing image: {str(e)}")

    async def handle_text_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle text messages during image session."""
        user_id = get_user_id(update)
        message = get_effective_message(update)
        
        if not user_id or not message or user_id not in self.active_sessions:
            return

        session = self.active_sessions[user_id]
        message_text = (message.text or "").strip().lower()

        if message_text in ['done', 'готово', 'процес', 'process']:
            logger.info("User requested processing", user_id=user_id, images_count=len(session.images))
            if session.images:
                await self._process_session_images(update, context, session)
            else:
                logger.info("No images in session for processing", user_id=user_id)
                no_images_text = await t(context, user_id, "commands.img.no_images")
                await message.reply_text(no_images_text)
        elif message_text in ['cancel', 'скасувати', 'відміна']:
            await self._cleanup_session(user_id, context)
            cancelled_text = await t(context, user_id, "commands.img.cancelled")
            await message.reply_text(cancelled_text)
        elif message_text in ['запит', 'query', 'fix', 'фікс']:
            # Set special mode for UI/code improvement requests
            session.set_ui_fix_mode(True)
            session.set_instruction(message.text)
            fix_mode_text = await t(context, user_id, "commands.img.fix_mode_activated")
            await message.reply_text(fix_mode_text)
        else:
            # Update session instruction
            session.set_instruction(message.text)
            updated_text = await t(
                context, user_id, "commands.img.instruction_updated",
                count=len(session.images)
            )
            await message.reply_text(updated_text)

    async def _process_session_images(
        self, 
        update: Update, 
        context: ContextTypes.DEFAULT_TYPE, 
        session: 'ImageSession'
    ) -> None:
        """Process all images in session with Claude CLI."""
        user_id = get_user_id(update)
        message = get_effective_message(update)
        
        if not user_id or not message or not session.images:
            error_text = await t(context, user_id, "commands.img.no_images")
            await message.reply_text(error_text)
            return

        processing_text = await t(
            context, user_id, "commands.img.processing",
            count=len(session.images)
        )
        progress_msg = await message.reply_text(processing_text)

        try:
            # Get Claude integration
            claude_integration = context.bot_data.get('claude_integration')
            if not claude_integration:
                await progress_msg.edit_text("❌ Claude integration not available.")
                return

            # Build prompt with image references
            prompt = self._build_claude_prompt(session)

            # Get current working directory
            settings = context.bot_data.get("settings")
            if not settings:
                current_dir = Path.cwd()
            else:
                settings_typed = cast(Settings, settings)
                current_dir = context.user_data.get(
                    'current_directory', 
                    settings_typed.approved_directory
                ) if context.user_data else settings_typed.approved_directory

            # Process with Claude
            claude_integration_typed = cast(ClaudeIntegration, claude_integration)
            claude_response = await claude_integration_typed.run_command_with_images(
                prompt=prompt,
                images=session.images,
                working_directory=current_dir,
                user_id=user_id,
                session_id=context.user_data.get('claude_session_id') if context.user_data else None
            )

            # Update session ID
            if context.user_data:
                context.user_data['claude_session_id'] = claude_response.session_id

            # Check if response is empty
            if not claude_response.content or not claude_response.content.strip():
                logger.warning("Empty response from Claude", user_id=user_id)
                error_text = await t(context, user_id, "commands.img.error", error="Claude не повернув відповідь")
                await self._safe_edit_or_send_error(progress_msg, message, error_text)
                return

            # Format and send response
            from ..utils.formatting import ResponseFormatter
            formatter = ResponseFormatter(self.settings)
            formatted_messages = formatter.format_claude_response(claude_response.content)

            # Check if formatted messages are empty
            if not formatted_messages or all(not msg.text.strip() for msg in formatted_messages):
                logger.warning("Empty formatted messages", user_id=user_id)
                error_text = await t(context, user_id, "commands.img.error", error="Відповідь не вдалося відформатувати")
                await self._safe_edit_or_send_error(progress_msg, message, error_text)
                return

            # TEMPORARILY DISABLED: Delete progress message safely
            try:
                # await progress_msg.delete()  # TEMP: keep messages for context debugging
                pass
            except Exception as e:
                logger.warning("Could not delete progress message", error=str(e))

            # Send responses
            for i, response_msg in enumerate(formatted_messages):
                try:
                    await message.reply_text(
                        response_msg.text,
                        parse_mode=response_msg.parse_mode,
                        reply_markup=response_msg.reply_markup,
                        reply_to_message_id=message.message_id if i == 0 else None
                    )
                except Exception as e:
                    logger.error("Failed to send response message", error=str(e), message_index=i)
                    # Try to send a fallback message
                    try:
                        await message.reply_text(f"Частина відповіді #{i+1}: {response_msg.text[:1000]}")
                    except Exception as e:
                        logger.error("Failed to send fallback message for response part", part_index=i+1, error=str(e))
                        pass

                if i < len(formatted_messages) - 1:
                    await asyncio.sleep(0.5)

        except ClaudeTimeoutError as e:
            logger.error("Claude timeout processing images", error=str(e))
            error_text = await t(context, user_id, "commands.img.error", error="Timeout - спробуйте пізніше")
            await self._safe_edit_or_send_error(progress_msg, message, error_text)
        except ClaudeProcessError as e:
            logger.error("Claude process error processing images", error=str(e))
            error_text = await t(context, user_id, "commands.img.error", error="Claude CLI недоступний")
            await self._safe_edit_or_send_error(progress_msg, message, error_text)
        except ClaudeError as e:
            logger.error("Claude error processing images", error=str(e))
            error_text = await t(context, user_id, "commands.img.error", error=str(e))
            await self._safe_edit_or_send_error(progress_msg, message, error_text)
        except Exception as e:
            logger.error("Unexpected error processing images with Claude", error=str(e))
            error_text = await t(context, user_id, "commands.img.error", error="Непередбачена помилка")
            await self._safe_edit_or_send_error(progress_msg, message, error_text)

        finally:
            # Clean up session
            await self._cleanup_session(session.user_id, context)

    def _build_claude_prompt(self, session: 'ImageSession') -> str:
        """Build Claude prompt with image context."""
        base_instruction = session.instruction or "Please analyze these images and provide insights."

        image_info = []
        for i, img in enumerate(session.images, 1):
            info = f"Image {i}: {img.filename}"
            if img.caption:
                info += f" (Caption: {img.caption})"
            image_info.append(info)

        if session.ui_fix_mode:
            # Load detailed prompt from bot-cli-prompts directory
            try:
                prompt_path = Path(__file__).parent.parent.parent.parent / "bot-cli-prompts" / "prompt-clean.md"
                with open(prompt_path, 'r', encoding='utf-8') as f:
                    detailed_prompt = f.read().strip()

                logger.debug("Loaded clean prompt successfully", prompt_length=len(detailed_prompt))

            except Exception as e:
                logger.warning("Could not load detailed prompt, using fallback", error=str(e))
                detailed_prompt = self._get_fallback_fix_mode_prompt()

            prompt = f"""{detailed_prompt}

**КОНТЕКСТ КОРИСТУВАЧА:**
{base_instruction}

**ЗОБРАЖЕННЯ ДЛЯ АНАЛІЗУ:**
{chr(10).join(image_info)}

**ІНСТРУКЦІЯ:** Проаналізуйте зображення згідно з наведеною структурою, враховуючи контекст користувача."""

        else:
            # For non-fix mode, use simplified fallback prompt
            detailed_prompt = self._get_fallback_general_prompt()

            prompt = f"""{detailed_prompt}

**КОНТЕКСТ КОРИСТУВАЧА:**
{base_instruction}

**ЗОБРАЖЕННЯ ДЛЯ АНАЛІЗУ:**
{chr(10).join(image_info)}

**ІНСТРУКЦІЯ:** Проаналізуйте зображення згідно з наведеною структурою та надайте детальний опис."""

        return prompt

    def _get_fallback_fix_mode_prompt(self) -> str:
        """Fallback prompt for fix mode if file loading fails."""
        return """**ВАЖЛИВИЙ КОНТЕКСТ:**
Ви Claude Code з повними можливостями розробки. Ви можете аналізувати скріншоти та модифікувати вихідний код для виправлення проблем.

**ЗАВДАННЯ - ДЕТАЛЬНИЙ АНАЛІЗ ЗОБРАЖЕНЬ:**
Проаналізуйте надане(і) зображення та надайте максимально детальний опис усіх проблем, помилок, недоліків та спостережень.

**СТРУКТУРА ВІДПОВІДІ:**

## 🔍 ДЕТАЛЬНИЙ АНАЛІЗ ЗОБРАЖЕНЬ

### ⚠️ ВИЯВЛЕНІ ПРОБЛЕМИ

#### Критичні проблеми:
- [Перелічіть всі критичні помилки, баги, збої]

#### Проблеми UI/UX:
- [Опишіть проблеми з інтерфейсом користувача]

#### Технічні недоліки:
- [Виявлені помилки в коді, якщо код видно]

### 💡 РЕКОМЕНДАЦІЇ ДЛЯ ВИПРАВЛЕННЯ

#### Пріоритетні виправлення:
1. [Найважливіші проблеми що потребують негайного вирішення]

### 🔧 ПОДАЛЬШІ КРОКИ

## ❓ ЗАПИТ НА ДОЗВІЛ

Чи можу я почати впровадження цих змін? Чи потрібні додаткові уточнення?"""

    def _get_fallback_general_prompt(self) -> str:
        """Fallback prompt for general analysis if file loading fails."""
        return """**ВАЖЛИВИЙ КОНТЕКСТ:**
Ви Claude Code з можливостями аналізу, що працює через Telegram бот. Користувач надіслав зображення(я) для детального аналізу та отримання інсайтів.

**ЗАВДАННЯ - ДЕТАЛЬНИЙ АНАЛІЗ ЗОБРАЖЕНЬ:**
Проаналізуйте надане(і) зображення та надайте максимально детальний опис усіх спостережень та інсайтів.

**СТРУКТУРА ВІДПОВІДІ:**

## 🔍 ДЕТАЛЬНИЙ АНАЛІЗ ЗОБРАЖЕНЬ

### 📋 Загальний огляд
- Тип контенту та основні компоненти

### 🎯 КОНКРЕТНІ СПОСТЕРЕЖЕННЯ
- Детальний опис елементів
- Текстовий контент та особливості

### 💡 ВИСНОВКИ ТА РЕКОМЕНДАЦІЇ
- Основні інсайти та пропозиції"""

    async def _get_instruction_message(self, context: ContextTypes.DEFAULT_TYPE, user_id: int) -> str:
        """Get localized instruction message."""
        try:
            return await t(
                context, user_id, "commands.img.instructions",
                max_images=self.max_images_per_batch,
                max_size=self.settings.image_max_file_size // (1024 * 1024)
            )
        except Exception as e:
            logger.debug("Failed to get localized instructions, using default", error=str(e))
            return (
                f"📸 **Image Processing Mode**\n\n"
                f"Please send your images (up to {self.max_images_per_batch} files). "
                "You can send them one by one or all at once.\n\n"
                "**Supported formats:** PNG, JPG, JPEG, GIF, WebP\n"
                f"**Max file size:** {self.settings.image_max_file_size // (1024 * 1024)}MB per image\n\n"
                "After uploading, type your instructions or 'done' to process.\n\n"
                "Type 'cancel' to stop."
            )

    async def _cleanup_session(self, user_id: int, context: Optional[ContextTypes.DEFAULT_TYPE] = None) -> None:
        """Clean up user's image session."""
        if user_id in self.active_sessions:
            session = self.active_sessions[user_id]
            await session.cleanup()
            del self.active_sessions[user_id]
            logger.info("Cleaned up image session", user_id=user_id)

        # Clear user_data flags that control message routing
        if context and context.user_data:
            context.user_data.pop('awaiting_images', None)
            context.user_data.pop('image_session_id', None)
            logger.info("Cleared user_data image session flags", user_id=user_id)

    async def _cleanup_session_after_timeout(self, user_id: int, session_id: str) -> None:
        """Clean up session after timeout."""
        await asyncio.sleep(self.session_timeout)

        if (user_id in self.active_sessions and
            self.active_sessions[user_id].session_id == session_id):
            await self._cleanup_session(user_id)
            logger.info("Session cleaned up after timeout", user_id=user_id, session_id=session_id)

    async def _safe_edit_or_send_error(self, progress_msg, message, error_text: str) -> None:
        """Safely edit progress message or send new error message."""
        try:
            await progress_msg.edit_text(error_text)
        except Exception as e:
            logger.warning("Could not edit progress message, sending new message", error=str(e))
            try:
                await message.reply_text(error_text)
            except Exception as e2:
                logger.error("Could not send error message", error=str(e2))


class ImageSession:
    """Represents an active image processing session."""

    def __init__(self, user_id: int, initial_instruction: Optional[str] = None, timeout: int = 300):
        """Initialize image session."""
        self.session_id = str(uuid.uuid4())
        self.user_id = user_id
        self.instruction = initial_instruction
        self.images: List[ProcessedImage] = []
        self.created_at = asyncio.get_event_loop().time()
        self.timeout = timeout
        self.ui_fix_mode = False

    def add_image(self, image: ProcessedImage) -> None:
        """Add processed image to session."""
        self.images.append(image)

    def set_instruction(self, instruction: str) -> None:
        """Set or update instruction."""
        self.instruction = instruction

    def set_ui_fix_mode(self, enabled: bool) -> None:
        """Enable or disable UI fix mode."""
        self.ui_fix_mode = enabled

    def is_active(self) -> bool:
        """Check if session is still active."""
        return (asyncio.get_event_loop().time() - self.created_at) < self.timeout

    async def cleanup(self) -> None:
        """Clean up session resources."""
        for image in self.images:
            await image.cleanup()
        self.images.clear()