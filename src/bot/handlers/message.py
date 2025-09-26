"""Message handlers for non-command inputs."""

import asyncio
from typing import Optional

import structlog
from telegram import Update
from telegram.ext import ContextTypes

from ...claude.exceptions import ClaudeToolValidationError
from ...config.settings import Settings
from ...security.audit import AuditLogger
from ...security.rate_limiter import RateLimiter
from ...security.validators import SecurityValidator
from .command import handle_claude_auth_code

logger = structlog.get_logger()


async def _handle_context_import_document(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle document upload for context import."""
    document = update.message.document

    # Validate file type
    if not document.file_name.endswith('.json'):
        await update.message.reply_text(
            "❌ **Неправильний тип файлу**\n\n"
            "Для імпорту контексту потрібен JSON файл.",
            parse_mode="Markdown"
        )
        context.user_data.pop("awaiting_context_import", None)
        return

    try:
        # Download file
        file = await document.get_file()
        file_bytes = await file.download_as_bytearray()
        file_content = file_bytes.decode('utf-8')

        # Get context commands instance and handle import
        container = context.bot_data.get("di_container")
        if container:
            context_commands = container.get("context_commands")
            await context_commands.handle_context_import_file(update, context, file_content)
        else:
            await update.message.reply_text(
                "❌ **Системна помилка**\n\n"
                "Не вдалося отримати доступ до системи контексту.",
                parse_mode="Markdown"
            )

    except Exception as e:
        logger.error("Failed to process context import document", error=str(e))
        await update.message.reply_text(
            "❌ **Помилка обробки файлу**\n\n"
            "Спробуйте пізніше або зверніться до адміністратора.",
            parse_mode="Markdown"
        )
    finally:
        # Clear state
        context.user_data.pop("awaiting_context_import", None)


async def _format_progress_update(update_obj) -> Optional[str]:
    """Format progress updates with enhanced context and visual indicators."""
    if update_obj.type == "tool_result":
        # Show tool completion status
        tool_name = "Unknown"
        if update_obj.metadata and update_obj.metadata.get("tool_use_id"):
            # Try to extract tool name from context if available
            tool_name = update_obj.metadata.get("tool_name", "Tool")

        if update_obj.is_error():
            return f"❌ **{tool_name} failed**\n\n_{update_obj.get_error_message()}_"
        else:
            execution_time = ""
            if update_obj.metadata and update_obj.metadata.get("execution_time_ms"):
                time_ms = update_obj.metadata["execution_time_ms"]
                execution_time = f" ({time_ms}ms)"
            return f"✅ **{tool_name} completed**{execution_time}"

    elif update_obj.type == "progress":
        # Handle progress updates
        progress_text = f"🔄 **{update_obj.content or 'Working...'}**"

        percentage = update_obj.get_progress_percentage()
        if percentage is not None:
            # Create a simple progress bar
            filled = int(percentage / 10)  # 0-10 scale
            bar = "█" * filled + "░" * (10 - filled)
            progress_text += f"\n\n`{bar}` {percentage}%"

        if update_obj.progress:
            step = update_obj.progress.get("step")
            total_steps = update_obj.progress.get("total_steps")
            if step and total_steps:
                progress_text += f"\n\nStep {step} of {total_steps}"

        return progress_text

    elif update_obj.type == "error":
        # Handle error messages
        return f"❌ **Error**\n\n_{update_obj.get_error_message()}_"

    elif update_obj.type == "assistant" and update_obj.tool_calls:
        # Show when tools are being called
        tool_names = update_obj.get_tool_names()
        if tool_names:
            tools_text = ", ".join(tool_names)
            return f"🔧 **Using tools:** {tools_text}"

    elif update_obj.type == "assistant" and update_obj.content:
        # Regular content updates with preview
        content_preview = (
            update_obj.content[:150] + "..."
            if len(update_obj.content) > 150
            else update_obj.content
        )
        return f"🤖 **Claude is working...**\n\n_{content_preview}_"

    elif update_obj.type == "system":
        # System initialization or other system messages
        if update_obj.metadata and update_obj.metadata.get("subtype") == "init":
            tools = update_obj.metadata.get("tools", [])
            tools_count = len(tools) if tools is not None else 0
            model = update_obj.metadata.get("model", "Claude")
            return f"🚀 **Starting {model}** with {tools_count} tools available"

    return None


def _format_error_message(error_str: str) -> str:
    """Format error messages for user-friendly display."""
    if "usage limit reached" in error_str.lower():
        # Usage limit error - already user-friendly from integration.py
        return error_str
    elif "tool not allowed" in error_str.lower():
        # Tool validation error - already handled in facade.py
        return error_str
    elif "no conversation found" in error_str.lower():
        return (
            f"🔄 **Session Not Found**\n\n"
            f"The Claude session could not be found or has expired.\n\n"
            f"**What you can do:**\n"
            f"• Use `/new` to start a fresh session\n"
            f"• Try your request again\n"
            f"• Use `/status` to check your current session"
        )
    elif "rate limit" in error_str.lower():
        return (
            f"⏱️ **Rate Limit Reached**\n\n"
            f"Too many requests in a short time period.\n\n"
            f"**What you can do:**\n"
            f"• Wait a moment before trying again\n"
            f"• Use simpler requests\n"
            f"• Check your current usage with `/status`"
        )
    elif "timeout" in error_str.lower():
        return (
            f"⏰ **Request Timeout**\n\n"
            f"Your request took too long to process and timed out.\n\n"
            f"**What you can do:**\n"
            f"• Try breaking down your request into smaller parts\n"
            f"• Use simpler commands\n"
            f"• Try again in a moment"
        )
    else:
        # Generic error handling
        return (
            f"❌ **Claude Code Error**\n\n"
            f"Failed to process your request: {error_str}\n\n"
            f"Please try again or contact the administrator if the problem persists."
        )


async def handle_text_message(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Handle regular text messages as Claude prompts."""
    user_id = update.effective_user.id
    message_text = update.message.text

    logger.debug("handle_text_message called", user_id=user_id,
                message_text=(message_text[:50] + "...") if message_text and len(message_text) > 50 else message_text)
    settings: Settings = context.bot_data["settings"]

    # Get services
    rate_limiter: Optional[RateLimiter] = context.bot_data.get("rate_limiter")
    audit_logger: Optional[AuditLogger] = context.bot_data.get("audit_logger")

    logger.info(
        "Processing text message", user_id=user_id, message_length=len(message_text)
    )

    # Check if user is in context search mode
    if context.user_data.get("awaiting_context_search"):
        context.user_data["awaiting_context_search"] = False
        context_commands = context.bot_data.get("context_commands")
        if context_commands:
            await context_commands.handle_context_search_query(update, context, message_text)
            return
        else:
            await update.message.reply_text(
                "❌ **Система контекстної пам'яті недоступна**\n\n"
                "Пошук в контексті тимчасово недоступний.",
                parse_mode="Markdown"
            )
            return

    # First check if this is a Claude authentication code
    if await handle_claude_auth_code(update, context):
        return

    # Check if user is creating a scheduled task
    if context.user_data and context.user_data.get('creating_task'):
        await handle_task_creation_dialogue(update, context)
        return

    # Check if user is in file editing workflow
    if context.user_data and context.user_data.get('file_action'):
        await handle_file_action_message(update, context)
        return

    # Check if user has active image session and handle it
    if context.user_data and context.user_data.get('awaiting_images'):
        logger.info("Text message for user with active image session", user_id=user_id, message_text=message_text)
        image_command_handler = context.bot_data.get('image_command_handler')
        if image_command_handler:
            logger.info("Routing text message to image_command_handler", user_id=user_id)
            await image_command_handler.handle_text_message(update, context)
            return
        else:
            logger.error("Image command handler not found for text message", user_id=user_id)

    try:
        # Check rate limit with estimated cost for text processing
        estimated_cost = _estimate_text_processing_cost(message_text)

        if rate_limiter:
            allowed, limit_message = await rate_limiter.check_rate_limit(
                user_id, estimated_cost
            )
            if not allowed:
                await update.message.reply_text(f"⏱️ {limit_message}")
                return

        # Перевірка доступності Claude (згідно з планом)
        availability_monitor = context.bot_data.get("claude_availability_monitor")
        if availability_monitor:
            is_available, status_details = await availability_monitor.check_availability_with_details()
            if not is_available:
                await send_unavailable_message(update, status_details)
                return

        # Send typing indicator
        await update.message.chat.send_action("typing")

        # Create progress message
        progress_msg = await update.message.reply_text(
            "🤔 Processing your request...",
            reply_to_message_id=update.message.message_id,
        )

        # Get Claude integration and storage from context
        claude_integration = context.bot_data.get("claude_integration")
        storage = context.bot_data.get("storage")

        if not claude_integration:
            await update.message.reply_text(
                "❌ **Claude integration not available**\n\n"
                "The Claude Code integration is not properly configured. "
                "Please contact the administrator.",
                parse_mode=None,
            )
            return

        # Get current directory
        current_dir = context.user_data.get(
            "current_directory", settings.approved_directory
        )

        # Get existing session ID
        session_id = context.user_data.get("claude_session_id")

        # Enhanced stream updates handler with progress tracking
        async def stream_handler(update_obj):
            try:
                progress_text = await _format_progress_update(update_obj)
                if progress_text:
                    await progress_msg.edit_text(progress_text, parse_mode="Markdown")
            except Exception as e:
                logger.warning("Failed to update progress message", error=str(e))

        # Run Claude command
        claude_response = None
        try:
            claude_response = await claude_integration.run_command(
                prompt=message_text,
                working_directory=current_dir,
                user_id=user_id,
                session_id=session_id,
                on_stream=stream_handler,
            )

            # Update session ID
            context.user_data["claude_session_id"] = claude_response.session_id

            # Check if Claude changed the working directory and update our tracking
            _update_working_directory_from_claude_response(
                claude_response, context, settings, user_id
            )

            # Log interaction to storage
            if storage:
                try:
                    await storage.save_claude_interaction(
                        user_id=user_id,
                        session_id=claude_response.session_id,
                        prompt=message_text,
                        response=claude_response,
                        ip_address=None,  # Telegram doesn't provide IP
                    )
                except Exception as e:
                    logger.warning("Failed to log interaction to storage", error=str(e))

            # Format response
            from ..utils.formatting import ResponseFormatter

            formatter = ResponseFormatter(settings)
            formatted_messages = formatter.format_claude_response(
                claude_response.content
            )

        except ClaudeToolValidationError as e:
            # Tool validation error with detailed instructions
            logger.error(
                "Tool validation error",
                error=str(e),
                user_id=user_id,
                blocked_tools=e.blocked_tools,
            )
            # Error message already formatted, create FormattedMessage
            from ..utils.formatting import FormattedMessage

            formatted_messages = [FormattedMessage(str(e), parse_mode=None)]
        except Exception as e:
            logger.error("Claude integration failed", error=str(e), user_id=user_id)
            # Format error and create FormattedMessage
            from ..utils.formatting import FormattedMessage

            formatted_messages = [
                FormattedMessage(_format_error_message(str(e)), parse_mode=None)
            ]

        # Delete progress message - TEMPORARILY DISABLED FOR DEBUGGING
        # await progress_msg.delete()

        # Send formatted responses (may be multiple messages)
        for i, message in enumerate(formatted_messages):
            try:
                await update.message.reply_text(
                    message.text,
                    parse_mode=message.parse_mode,
                    reply_markup=message.reply_markup,
                    reply_to_message_id=update.message.message_id if i == 0 else None,
                )

                # Small delay between messages to avoid rate limits
                if i < len(formatted_messages) - 1:
                    await asyncio.sleep(0.5)

            except Exception as e:
                logger.error(
                    "Failed to send response message", 
                    error=str(e), 
                    message_index=i,
                    message_text=message.text[:200],
                    parse_mode=message.parse_mode
                )
                # Try to send error message
                await update.message.reply_text(
                    "❌ Failed to send response. Please try again.",
                    reply_to_message_id=update.message.message_id if i == 0 else None,
                )

        # Update session info
        context.user_data["last_message"] = update.message.text

        # Add conversation enhancements if available
        features = context.bot_data.get("features")
        conversation_enhancer = (
            features.get_conversation_enhancer() if features else None
        )

        if conversation_enhancer and claude_response:
            try:
                # Update conversation context
                conversation_enhancer.update_context(user_id, claude_response)

                # Check if we should show follow-up suggestions
                if conversation_enhancer.should_show_suggestions(claude_response):
                    # Get conversation context
                    conversation_context = conversation_enhancer.get_context(user_id)

                    # Generate follow-up suggestions
                    suggestions = conversation_enhancer.generate_follow_up_suggestions(
                        claude_response.content,
                        claude_response.tools_used or [],
                        conversation_context,
                    )

                    if suggestions:
                        # Create keyboard with suggestions
                        suggestion_keyboard = (
                            conversation_enhancer.create_follow_up_keyboard(suggestions)
                        )

                        # Send follow-up suggestions
                        await update.message.reply_text(
                            "💡 **What would you like to do next?**",
                            parse_mode=None,
                            reply_markup=suggestion_keyboard,
                        )

            except Exception as e:
                logger.warning(
                    "Conversation enhancement failed", error=str(e), user_id=user_id
                )

        # Log successful message processing
        if audit_logger:
            await audit_logger.log_command(
                user_id=user_id,
                command="text_message",
                args=[update.message.text[:100]],  # First 100 chars
                success=True,
            )

        logger.info("Text message processed successfully", user_id=user_id)

    except Exception as e:
        # Clean up progress message if it exists
        try:
            # TEMPORARILY DISABLED: await progress_msg.delete()
            pass
        except Exception as e:
            logger.debug("Failed to delete progress message during error handling", error=str(e))
            pass

        error_msg = f"❌ **Error processing message**\n\n{str(e)}"
        await update.message.reply_text(error_msg, parse_mode=None)

        # Log failed processing
        if audit_logger:
            await audit_logger.log_command(
                user_id=user_id,
                command="text_message",
                args=[update.message.text[:100]],
                success=False,
            )

        logger.error("Error processing text message", error=str(e), user_id=user_id)


async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle file uploads."""
    user_id = update.effective_user.id
    document = update.message.document
    settings: Settings = context.bot_data["settings"]

    # First check if user is in file editing workflow
    if context.user_data and context.user_data.get('file_action'):
        await handle_document_message(update, context)
        return

    # Get services
    security_validator: Optional[SecurityValidator] = context.bot_data.get(
        "security_validator"
    )
    audit_logger: Optional[AuditLogger] = context.bot_data.get("audit_logger")
    rate_limiter: Optional[RateLimiter] = context.bot_data.get("rate_limiter")

    logger.info(
        "Processing document upload",
        user_id=user_id,
        filename=document.file_name,
        file_size=document.file_size,
    )

    try:
        # Validate filename using security validator
        if security_validator:
            valid, error = security_validator.validate_filename(document.file_name)
            if not valid:
                await update.message.reply_text(
                    f"❌ **File Upload Rejected**\n\n{error}"
                )

                # Log security violation
                if audit_logger:
                    await audit_logger.log_security_violation(
                        user_id=user_id,
                        violation_type="invalid_file_upload",
                        details=f"Filename: {document.file_name}, Error: {error}",
                        severity="medium",
                    )
                return

        # Check file size limits
        max_size = 10 * 1024 * 1024  # 10MB
        if document.file_size > max_size:
            await update.message.reply_text(
                f"❌ **File Too Large**\n\n"
                f"Maximum file size: {max_size // 1024 // 1024}MB\n"
                f"Your file: {document.file_size / 1024 / 1024:.1f}MB"
            )
            return

        # Check rate limit for file processing
        file_cost = _estimate_file_processing_cost(document.file_size)
        if rate_limiter:
            allowed, limit_message = await rate_limiter.check_rate_limit(
                user_id, file_cost
            )
            if not allowed:
                await update.message.reply_text(f"⏱️ {limit_message}")
                return

        # Send processing indicator
        await update.message.chat.send_action("upload_document")

        progress_msg = await update.message.reply_text(
            f"📄 Processing file: `{document.file_name}`...", parse_mode=None
        )

        # Check if enhanced file handler is available
        features = context.bot_data.get("features")
        file_handler = features.get_file_handler() if features else None

        if file_handler:
            # Use enhanced file handler
            try:
                processed_file = await file_handler.handle_document_upload(
                    document,
                    user_id,
                    update.message.caption or "Please review this file:",
                )
                prompt = processed_file.prompt

                # Update progress message with file type info
                await progress_msg.edit_text(
                    f"📄 Processing {processed_file.type} file: `{document.file_name}`...",
                    parse_mode=None,
                )

            except Exception as e:
                logger.warning(
                    "Enhanced file handler failed, falling back to basic handler",
                    error=str(e),
                )
                file_handler = None  # Fall back to basic handling

        if not file_handler:
            # Fall back to basic file handling
            file = await document.get_file()
            file_bytes = await file.download_as_bytearray()

            # Try to decode as text
            try:
                content = file_bytes.decode("utf-8")

                # Check content length
                max_content_length = 50000  # 50KB of text
                if len(content) > max_content_length:
                    content = (
                        content[:max_content_length]
                        + "\n... (file truncated for processing)"
                    )

                # Create prompt with file content
                caption = update.message.caption or "Please review this file:"
                prompt = f"{caption}\n\n**File:** `{document.file_name}`\n\n```\n{content}\n```"

            except UnicodeDecodeError:
                await progress_msg.edit_text(
                    "❌ **File Format Not Supported**\n\n"
                    "File must be text-based and UTF-8 encoded.\n\n"
                    "**Supported formats:**\n"
                    "• Source code files (.py, .js, .ts, etc.)\n"
                    "• Text files (.txt, .md)\n"
                    "• Configuration files (.json, .yaml, .toml)\n"
                    "• Documentation files"
                )
                return

        # Delete progress message - TEMPORARILY DISABLED FOR DEBUGGING
        # await progress_msg.delete()

        # Create a new progress message for Claude processing
        claude_progress_msg = await update.message.reply_text(
            "🤖 Processing file with Claude...", parse_mode=None
        )

        # Get Claude integration from context
        claude_integration = context.bot_data.get("claude_integration")

        if not claude_integration:
            await claude_progress_msg.edit_text(
                "❌ **Claude integration not available**\n\n"
                "The Claude Code integration is not properly configured.",
                parse_mode=None,
            )
            return

        # Get current directory and session
        current_dir = context.user_data.get(
            "current_directory", settings.approved_directory
        )
        session_id = context.user_data.get("claude_session_id")

        # Process with Claude
        try:
            claude_response = await claude_integration.run_command(
                prompt=prompt,
                working_directory=current_dir,
                user_id=user_id,
                session_id=session_id,
            )

            # Update session ID
            context.user_data["claude_session_id"] = claude_response.session_id

            # Check if Claude changed the working directory and update our tracking
            _update_working_directory_from_claude_response(
                claude_response, context, settings, user_id
            )

            # Format and send response
            from ..utils.formatting import ResponseFormatter

            formatter = ResponseFormatter(settings)
            formatted_messages = formatter.format_claude_response(
                claude_response.content
            )

            # Delete progress message - TEMPORARILY DISABLED FOR DEBUGGING
            # await claude_progress_msg.delete()

            # Send responses
            for i, message in enumerate(formatted_messages):
                await update.message.reply_text(
                    message.text,
                    parse_mode=message.parse_mode,
                    reply_markup=message.reply_markup,
                    reply_to_message_id=(update.message.message_id if i == 0 else None),
                )

                if i < len(formatted_messages) - 1:
                    await asyncio.sleep(0.5)

        except Exception as e:
            await claude_progress_msg.edit_text(
                _format_error_message(str(e)), parse_mode=None
            )
            logger.error("Claude file processing failed", error=str(e), user_id=user_id)

        # Log successful file processing
        if audit_logger:
            await audit_logger.log_file_access(
                user_id=user_id,
                file_path=document.file_name,
                action="upload_processed",
                success=True,
                file_size=document.file_size,
            )

    except Exception as e:
        try:
            # TEMPORARILY DISABLED FOR DEBUGGING: await progress_msg.delete()
            pass
        except:
            pass

        error_msg = f"❌ **Error processing file**\n\n{str(e)}"
        await update.message.reply_text(error_msg, parse_mode=None)

        # Log failed file processing
        if audit_logger:
            await audit_logger.log_file_access(
                user_id=user_id,
                file_path=document.file_name,
                action="upload_failed",
                success=False,
                file_size=document.file_size,
            )

        logger.error("Error processing document", error=str(e), user_id=user_id)


async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle photo uploads."""
    user_id = update.effective_user.id
    settings: Settings = context.bot_data["settings"]

    logger.debug("handle_photo called", user_id=user_id,
                has_photo=update.message.photo is not None if update.message else False,
                has_text=update.message.text is not None if update.message else False,
                message_text=update.message.text if update.message and update.message.text else None,
                message_type=type(update.message).__name__ if update.message else None)

    # Check if user has active image session
    logger.debug("Checking image session",
                 user_id=user_id,
                 has_user_data=context.user_data is not None,
                 user_data_keys=list(context.user_data.keys()) if context.user_data else [],
                 awaiting_images=context.user_data.get('awaiting_images', False) if context.user_data else False,
                 has_image_command_handler='image_command_handler' in context.bot_data)

    if context.user_data and context.user_data.get('awaiting_images'):
        logger.info("User has active image session - routing to image_command_handler", user_id=user_id)
        image_command_handler = context.bot_data.get('image_command_handler')
        if image_command_handler:
            logger.info("Calling image_command_handler.handle_image_upload", user_id=user_id)
            await image_command_handler.handle_image_upload(update, context)
            return
        else:
            logger.error("Image command handler not found in bot_data", user_id=user_id)
    else:
        logger.debug("No active image session for user", user_id=user_id,
                    has_user_data=context.user_data is not None,
                    awaiting_images=context.user_data.get('awaiting_images', False) if context.user_data else False)

    # Check if enhanced image handler is available
    features = context.bot_data.get("features")
    image_handler = features.get_image_handler() if features else None

    if image_handler:
        try:
            # Send processing indicator
            progress_msg = await update.message.reply_text(
                "📸 Processing image...", parse_mode=None
            )

            # Get the largest photo size
            if not update.message.photo:
                await progress_msg.edit_text("❌ No photo found in message.")
                return
            photo = update.message.photo[-1]

            # Process image with enhanced handler
            processed_image = await image_handler.process_image(
                photo, update.message.caption
            )

            # Delete progress message - TEMPORARILY DISABLED FOR DEBUGGING
            # await progress_msg.delete()

            # Create Claude progress message
            claude_progress_msg = await update.message.reply_text(
                "🤖 Analyzing image with Claude...", parse_mode=None
            )

            # Get Claude integration
            claude_integration = context.bot_data.get("claude_integration")

            if not claude_integration:
                await claude_progress_msg.edit_text(
                    "❌ **Claude integration not available**\n\n"
                    "The Claude Code integration is not properly configured.",
                    parse_mode=None,
                )
                return

            # Get current directory and session
            current_dir = context.user_data.get(
                "current_directory", settings.approved_directory
            )
            session_id = context.user_data.get("claude_session_id")

            # Process with Claude
            try:
                claude_response = await claude_integration.run_command(
                    prompt=processed_image.prompt,
                    working_directory=current_dir,
                    user_id=user_id,
                    session_id=session_id,
                )

                # Update session ID
                context.user_data["claude_session_id"] = claude_response.session_id

                # Format and send response
                from ..utils.formatting import ResponseFormatter

                formatter = ResponseFormatter(settings)
                formatted_messages = formatter.format_claude_response(
                    claude_response.content
                )

                # Delete progress message - TEMPORARILY DISABLED FOR DEBUGGING
                # await claude_progress_msg.delete()

                # Send responses
                for i, message in enumerate(formatted_messages):
                    await update.message.reply_text(
                        message.text,
                        parse_mode=message.parse_mode,
                        reply_markup=message.reply_markup,
                        reply_to_message_id=(
                            update.message.message_id if i == 0 else None
                        ),
                    )

                    if i < len(formatted_messages) - 1:
                        await asyncio.sleep(0.5)

            except Exception as e:
                await claude_progress_msg.edit_text(
                    _format_error_message(str(e)), parse_mode=None
                )
                logger.error(
                    "Claude image processing failed", error=str(e), user_id=user_id
                )

        except Exception as e:
            logger.error("Image processing failed", error=str(e), user_id=user_id)
            await update.message.reply_text(
                f"❌ **Error processing image**\n\n{str(e)}", parse_mode=None
            )
    else:
        # Fall back to unsupported message
        await update.message.reply_text(
            "📸 **Photo Upload**\n\n"
            "Photo processing is not yet supported.\n\n"
            "**Currently supported:**\n"
            "• Text files (.py, .js, .md, etc.)\n"
            "• Configuration files\n"
            "• Documentation files\n\n"
            "**Coming soon:**\n"
            "• Image analysis\n"
            "• Screenshot processing\n"
            "• Diagram interpretation"
        )


def _estimate_text_processing_cost(text: str) -> float:
    """Estimate cost for processing text message."""
    # Base cost
    base_cost = 0.001

    # Additional cost based on length
    length_cost = len(text) * 0.00001

    # Additional cost for complex requests
    complex_keywords = [
        "analyze",
        "generate",
        "create",
        "build",
        "implement",
        "refactor",
        "optimize",
        "debug",
        "explain",
        "document",
    ]

    text_lower = text.lower()
    complexity_multiplier = 1.0

    for keyword in complex_keywords:
        if keyword in text_lower:
            complexity_multiplier += 0.5

    return (base_cost + length_cost) * min(complexity_multiplier, 3.0)


def _estimate_file_processing_cost(file_size: int) -> float:
    """Estimate cost for processing uploaded file."""
    # Base cost for file handling
    base_cost = 0.005

    # Additional cost based on file size (per KB)
    size_cost = (file_size / 1024) * 0.0001

    return base_cost + size_cost


async def _generate_placeholder_response(
    message_text: str, context: ContextTypes.DEFAULT_TYPE
) -> dict:
    """Generate placeholder response until Claude integration is implemented."""
    settings: Settings = context.bot_data["settings"]
    current_dir = getattr(
        context.user_data, "current_directory", settings.approved_directory
    )
    relative_path = current_dir.relative_to(settings.approved_directory)

    # Analyze the message for intent
    message_lower = message_text.lower()

    if any(
        word in message_lower for word in ["list", "show", "see", "directory", "files"]
    ):
        response_text = (
            f"🤖 **Claude Code Response** _(Placeholder)_\n\n"
            f"I understand you want to see files. Try using the `/ls` command to list files "
            f"in your current directory (`{relative_path}/`).\n\n"
            f"**Available commands:**\n"
            f"• `/ls` - List files\n"
            f"• `/cd <dir>` - Change directory\n"
            f"_Note: Full Claude Code integration will be available in the next phase._"
        )

    elif any(word in message_lower for word in ["create", "generate", "make", "build"]):
        response_text = (
            f"🤖 **Claude Code Response** _(Placeholder)_\n\n"
            f"I understand you want to create something! Once the Claude Code integration "
            f"is complete, I'll be able to:\n\n"
            f"• Generate code files\n"
            f"• Create directory structures\n"
            f"• Write documentation\n"
            f"• Build complete applications\n\n"
            f"**Current directory:** `{relative_path}/`\n\n"
            f"_Full functionality coming soon!_"
        )

    elif any(word in message_lower for word in ["help", "how", "what", "explain"]):
        response_text = (
            f"🤖 **Claude Code Response** _(Placeholder)_\n\n"
            f"I'm here to help! Try using `/help` for available commands.\n\n"
            f"**What I can do now:**\n"
            f"• Navigate directories (`/cd`, `/ls`, `/pwd`)\n"
            f"• Manage sessions (`/new`, `/status`)\n\n"
            f"**Coming soon:**\n"
            f"• Full Claude Code integration\n"
            f"• Code generation and editing\n"
            f"• File operations\n"
            f"• Advanced programming assistance"
        )

    else:
        response_text = (
            f"🤖 **Claude Code Response** _(Placeholder)_\n\n"
            f"I received your message: \"{message_text[:100]}{'...' if len(message_text) > 100 else ''}\"\n\n"
            f"**Current Status:**\n"
            f"• Directory: `{relative_path}/`\n"
            f"• Bot core: ✅ Active\n"
            f"• Claude integration: 🔄 Coming soon\n\n"
            f"Once Claude Code integration is complete, I'll be able to process your "
            f"requests fully and help with coding tasks!\n\n"
            f"For now, try the available commands like `/ls`, `/cd`, and `/help`."
        )

    return {"text": response_text, "parse_mode": "Markdown"}


def _update_working_directory_from_claude_response(
    claude_response, context, settings, user_id
):
    """Update the working directory based on Claude's response content."""
    import re
    from pathlib import Path

    # Look for directory changes in Claude's response
    # This searches for common patterns that indicate directory changes
    patterns = [
        r"(?:^|\n).*?cd\s+([^\s\n]+)",  # cd command
        r"(?:^|\n).*?Changed directory to:?\s*([^\s\n]+)",  # explicit directory change
        r"(?:^|\n).*?Current directory:?\s*([^\s\n]+)",  # current directory indication
        r"(?:^|\n).*?Working directory:?\s*([^\s\n]+)",  # working directory indication
    ]

    content = claude_response.content.lower()
    current_dir = context.user_data.get(
        "current_directory", settings.approved_directory
    )

    for pattern in patterns:
        matches = re.findall(pattern, content, re.MULTILINE | re.IGNORECASE)
        for match in matches:
            try:
                # Clean up the path
                new_path = match.strip().strip("\"'`")

                # Handle relative paths
                if new_path.startswith("./") or new_path.startswith("../"):
                    new_path = (current_dir / new_path).resolve()
                elif not new_path.startswith("/"):
                    # Relative path without ./
                    new_path = (current_dir / new_path).resolve()
                else:
                    # Absolute path
                    new_path = Path(new_path).resolve()

                # Validate that the new path is within the approved directory
                if (
                    new_path.is_relative_to(settings.approved_directory)
                    and new_path.exists()
                ):
                    context.user_data["current_directory"] = new_path
                    logger.info(
                        "Updated working directory from Claude response",
                        old_dir=str(current_dir),
                        new_dir=str(new_path),
                        user_id=user_id,
                    )
                    return  # Take the first valid match

            except (ValueError, OSError) as e:
                # Invalid path, skip this match
                logger.debug(
                    "Invalid path in Claude response", path=match, error=str(e)
                )
                continue


async def handle_task_creation_dialogue(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle task creation multi-step dialogue."""
    from telegram import InlineKeyboardButton, InlineKeyboardMarkup
    from datetime import datetime, timedelta
    import uuid

    user_id = update.effective_user.id
    message_text = update.message.text
    task_data = context.user_data.get('creating_task', {})
    step = task_data.get('step', 'prompt')

    if step == 'prompt':
        # Step 1: User sent prompt text
        task_data['prompt'] = message_text
        task_data['step'] = 'schedule'
        context.user_data['creating_task'] = task_data

        keyboard = [
            [
                InlineKeyboardButton("⏰ Зараз (під час DND)", callback_data="schedule:time:dnd"),
                InlineKeyboardButton("🌅 Завтра вранці", callback_data="schedule:time:morning")
            ],
            [
                InlineKeyboardButton("🕘 Завтра ввечері", callback_data="schedule:time:evening"),
                InlineKeyboardButton("📅 Щоденно", callback_data="schedule:time:daily")
            ],
            [
                InlineKeyboardButton("🔄 Щотижня", callback_data="schedule:time:weekly"),
                InlineKeyboardButton("⚙️ Налаштувати час", callback_data="schedule:time:custom")
            ],
            [InlineKeyboardButton("❌ Скасувати", callback_data="schedule:cancel_create")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await update.message.reply_text(
            f"✅ **Промпт збережено:**\n`{message_text[:100]}{'...' if len(message_text) > 100 else ''}`\n\n"
            f"**Крок 2 з 3: Коли виконувати?**\n\n"
            f"Оберіть час виконання завдання:",
            reply_markup=reply_markup
        )

    elif step == 'custom_time':
        # Step 2b: User sent custom time
        try:
            # Parse time like "14:30", "9:00", "23:00"
            import re
            time_match = re.match(r'^(\d{1,2}):(\d{2})$', message_text.strip())
            if not time_match:
                await update.message.reply_text(
                    "❌ **Невірний формат часу**\n\n"
                    "Введіть час у форматі ГГ:ХХ (наприклад, 14:30, 09:00, 23:15)\n\n"
                    "Або скасуйте створення завдання:",
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("❌ Скасувати", callback_data="schedule:cancel_create")]
                    ])
                )
                return

            hour, minute = int(time_match.group(1)), int(time_match.group(2))
            if hour > 23 or minute > 59:
                await update.message.reply_text(
                    "❌ **Невірний час**\n\n"
                    "Година повинна бути від 00 до 23, хвилини від 00 до 59\n\n"
                    "Спробуйте ще раз або скасуйте:",
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("❌ Скасувати", callback_data="schedule:cancel_create")]
                    ])
                )
                return

            task_data['custom_time'] = f"{hour:02d}:{minute:02d}"
            task_data['step'] = 'confirm'
            context.user_data['creating_task'] = task_data

            await _show_task_confirmation(update, task_data)

        except Exception as e:
            logger.error("Error parsing custom time", error=str(e))
            await update.message.reply_text(
                "❌ **Помилка обробки часу**\n\n"
                "Спробуйте ще раз або скасуйте створення завдання:",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("❌ Скасувати", callback_data="schedule:cancel_create")]
                ])
            )


async def _show_task_confirmation(update, task_data):
    """Show task confirmation with all details."""
    from telegram import InlineKeyboardButton, InlineKeyboardMarkup

    prompt = task_data.get('prompt', '')
    schedule_type = task_data.get('schedule_type', 'dnd')
    custom_time = task_data.get('custom_time', '')

    # Format schedule description
    schedule_desc = {
        'dnd': 'Під час DND періоду (23:00-08:00)',
        'morning': 'Завтра о 08:00',
        'evening': 'Завтра о 20:00',
        'daily': 'Щоденно о 08:00',
        'weekly': 'Щотижня (понеділок о 09:00)',
        'custom': f'Щоденно о {custom_time}' if custom_time else 'Налаштований час'
    }

    message = (
        f"📝 **Підтвердження створення завдання**\n\n"
        f"**Завдання:**\n`{prompt[:200]}{'...' if len(prompt) > 200 else ''}`\n\n"
        f"**Розклад:** {schedule_desc.get(schedule_type, 'Не вказано')}\n\n"
        f"**Крок 3 з 3:** Підтвердіть створення завдання"
    )

    keyboard = [
        [
            InlineKeyboardButton("✅ Створити завдання", callback_data="schedule:confirm_task"),
            InlineKeyboardButton("✏️ Редагувати", callback_data="schedule:edit_task")
        ],
        [InlineKeyboardButton("❌ Скасувати", callback_data="schedule:cancel_create")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    if hasattr(update, 'message') and update.message:
        await update.message.reply_text(message, reply_markup=reply_markup)
    else:
        # Called from callback, need to edit message
        await update.edit_message_text(message, reply_markup=reply_markup)


async def handle_file_action_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle text messages during file editing workflow."""
    from telegram import InlineKeyboardButton, InlineKeyboardMarkup
    from pathlib import Path

    user_id = update.effective_user.id
    message_text = update.message.text
    file_action = context.user_data.get('file_action', {})
    action_type = file_action.get('type')
    step = file_action.get('step')

    settings: Settings = context.bot_data["settings"]
    current_dir = context.user_data.get("current_directory", settings.approved_directory)

    logger.info("Handling file action message", user_id=user_id, action_type=action_type, step=step, filename=message_text)

    if step == "waiting_filename":
        # User sent filename for reading or editing
        filename = message_text.strip()

        # Basic filename validation
        if not filename:
            await update.message.reply_text(
                "❌ **Порожня назва файлу**\n\n"
                "Введіть назву файлу:",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("❌ Скасувати", callback_data="action:quick_actions")]
                ])
            )
            return

        # Security check - prevent path traversal
        if ".." in filename or filename.startswith("/"):
            await update.message.reply_text(
                "❌ **Недозволена назва файлу**\n\n"
                "Назва файлу не може містити '..' або починатися з '/'.\n"
                "Введіть відносну назву файлу в поточній директорії:",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("❌ Скасувати", callback_data="action:quick_actions")]
                ])
            )
            return

        file_path = current_dir / filename

        if action_type == "read":
            # Handle file reading
            try:
                if not file_path.exists():
                    await update.message.reply_text(
                        f"❌ **Файл не знайдено**\n\n"
                        f"Файл `{filename}` не існує в поточній директорії.\n"
                        f"Перевірте назву та спробуйте ще раз:",
                        reply_markup=InlineKeyboardMarkup([
                            [InlineKeyboardButton("🔙 Назад", callback_data="file_edit:select_read")]
                        ])
                    )
                    return

                if not file_path.is_file():
                    await update.message.reply_text(
                        f"❌ **Це не файл**\n\n"
                        f"`{filename}` є директорією, а не файлом.\n"
                        f"Введіть назву файлу:",
                        reply_markup=InlineKeyboardMarkup([
                            [InlineKeyboardButton("🔙 Назад", callback_data="file_edit:select_read")]
                        ])
                    )
                    return

                # Check file size
                file_size = file_path.stat().st_size
                if file_size > 1024 * 1024:  # 1MB limit for reading
                    await update.message.reply_text(
                        f"❌ **Файл занадто великий**\n\n"
                        f"Файл `{filename}` має розмір {file_size:,} байт.\n"
                        f"Максимальний розмір для читання: 1MB.\n\n"
                        f"Використайте команди Claude для роботи з великими файлами.",
                        reply_markup=InlineKeyboardMarkup([
                            [InlineKeyboardButton("🔙 Назад", callback_data="file_edit:select_read")]
                        ])
                    )
                    return

                # Read file content
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                except UnicodeDecodeError:
                    # Try with different encoding
                    with open(file_path, 'r', encoding='latin-1') as f:
                        content = f.read()

                # Truncate content if too long for Telegram message
                max_length = 3500  # Leave room for formatting
                if len(content) > max_length:
                    content = content[:max_length] + "\n\n... (файл обрізано)"

                response_text = (
                    f"📖 **Вміст файлу:** `{filename}`\n\n"
                    f"```\n{content}\n```\n\n"
                    f"📏 **Розмір:** {file_size:,} байт"
                )

                await update.message.reply_text(
                    response_text,
                    reply_markup=InlineKeyboardMarkup([
                        [
                            InlineKeyboardButton("✏️ Редагувати файл", callback_data="file_edit:select_edit"),
                            InlineKeyboardButton("📋 Меню", callback_data="action:quick_actions")
                        ]
                    ])
                )

                # Clear file action state
                context.user_data.pop("file_action", None)

            except Exception as e:
                logger.error("Error reading file", error=str(e), filename=filename)
                await update.message.reply_text(
                    f"❌ **Помилка читання файлу**\n\n"
                    f"Не вдалося прочитати файл `{filename}`:\n"
                    f"```\n{str(e)}\n```",
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("🔙 Назад", callback_data="file_edit:select_read")]
                    ])
                )

        elif action_type == "edit":
            # Handle file editing - download file for user
            try:
                if not file_path.exists():
                    await update.message.reply_text(
                        f"❌ **Файл не знайдено**\n\n"
                        f"Файл `{filename}` не існує в поточній директорії.\n"
                        f"Перевірте назву та спробуйте ще раз:",
                        reply_markup=InlineKeyboardMarkup([
                            [InlineKeyboardButton("🔙 Назад", callback_data="file_edit:select_edit")]
                        ])
                    )
                    return

                if not file_path.is_file():
                    await update.message.reply_text(
                        f"❌ **Це не файл**\n\n"
                        f"`{filename}` є директорією, а не файлом.\n"
                        f"Введіть назву файлу:",
                        reply_markup=InlineKeyboardMarkup([
                            [InlineKeyboardButton("🔙 Назад", callback_data="file_edit:select_edit")]
                        ])
                    )
                    return

                # Check file size
                file_size = file_path.stat().st_size
                if file_size > 20 * 1024 * 1024:  # 20MB limit for editing
                    await update.message.reply_text(
                        f"❌ **Файл занадто великий**\n\n"
                        f"Файл `{filename}` має розмір {file_size:,} байт.\n"
                        f"Максимальний розмір для редагування: 20MB.",
                        reply_markup=InlineKeyboardMarkup([
                            [InlineKeyboardButton("🔙 Назад", callback_data="file_edit:select_edit")]
                        ])
                    )
                    return

                # Send file for editing
                progress_msg = await update.message.reply_text(
                    f"📤 **Надсилаю файл для редагування...**\n\n"
                    f"📁 Файл: `{filename}`\n"
                    f"📏 Розмір: {file_size:,} байт"
                )

                def _format_file_size(size: int) -> str:
                    """Format file size in human-readable format."""
                    for unit in ["B", "KB", "MB", "GB"]:
                        if size < 1024:
                            return f"{size:.1f}{unit}" if unit != "B" else f"{size}B"
                        size /= 1024
                    return f"{size:.1f}TB"

                # Send the file
                with open(file_path, 'rb') as file:
                    await update.message.reply_document(
                        document=file,
                        filename=filename,
                        caption=(
                            f"✏️ **Файл для редагування**\n\n"
                            f"📁 Назва: `{filename}`\n"
                            f"📏 Розмір: {_format_file_size(file_size)}\n\n"
                            f"🔄 **Як редагувати:**\n"
                            f"1. Завантажте цей файл\n"
                            f"2. Відредагуйте у вашому редакторі\n"
                            f"3. Надішліть відредагований файл назад як документ\n"
                            f"4. Я збережу зміни\n\n"
                            f"💾 Очікую відредагований файл..."
                        )
                    )

                # Update state to wait for edited file
                context.user_data["file_action"] = {
                    "type": "edit",
                    "step": "waiting_edited_file",
                    "filename": filename,
                    "original_path": str(file_path)
                }

                # Update progress message
                await progress_msg.edit_text(
                    f"✅ **Файл надіслано**\n\n"
                    f"📁 Файл `{filename}` надіслано вище.\n\n"
                    f"📝 Відредагуйте файл та надішліть його назад як документ.\n\n"
                    f"💡 **Підказка:** Переконайтеся що зберегли файл з тією ж назвою!",
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("❌ Скасувати редагування", callback_data="file_edit:cancel")]
                    ])
                )

            except Exception as e:
                logger.error("Error preparing file for editing", error=str(e), filename=filename)
                await update.message.reply_text(
                    f"❌ **Помилка обробки файлу**\n\n"
                    f"Не вдалося підготувати файл `{filename}` для редагування:\n"
                    f"```\n{str(e)}\n```",
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("🔙 Назад", callback_data="file_edit:select_edit")]
                    ])
                )

    else:
        # Unknown step or state
        logger.warning("Unknown file action step", user_id=user_id, step=step, action_type=action_type)
        context.user_data.pop("file_action", None)
        await update.message.reply_text(
            "❌ **Помилка стану**\n\n"
            "Стан редагування файлу порушено. Почніть спочатку.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("📋 Швидкі дії", callback_data="action:quick_actions")]
            ])
        )


async def handle_document_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle document uploads for file editing workflow."""
    from telegram import InlineKeyboardButton, InlineKeyboardMarkup
    from pathlib import Path
    import shutil

    user_id = update.effective_user.id
    file_action = context.user_data.get('file_action', {})

    # Check if user is awaiting context import
    if context.user_data.get("awaiting_context_import"):
        await _handle_context_import_document(update, context)
        return

    # Check if user is in file editing workflow
    if not file_action or file_action.get('step') != 'waiting_edited_file':
        # User sent document but not in editing workflow - ignore or provide guidance
        await update.message.reply_text(
            "📄 **Документ отримано**\n\n"
            "Щоб редагувати файл, використайте швидкі дії:\n"
            "1. Натисніть 📋 Швидкі дії\n"
            "2. Оберіть ✏️ Редагувати файл\n"
            "3. Введіть назву файлу\n\n"
            "Документ не збережено.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("📋 Швидкі дії", callback_data="action:quick_actions")]
            ])
        )
        return

    settings: Settings = context.bot_data["settings"]
    current_dir = context.user_data.get("current_directory", settings.approved_directory)
    expected_filename = file_action.get('filename')
    original_path = Path(file_action.get('original_path', ''))

    document = update.message.document
    uploaded_filename = document.file_name

    logger.info("Processing uploaded document", user_id=user_id,
                uploaded_filename=uploaded_filename, expected_filename=expected_filename)

    try:
        # Validate filename matches expected
        if uploaded_filename != expected_filename:
            await update.message.reply_text(
                f"⚠️ **Невідповідність назви файлу**\n\n"
                f"Очікував: `{expected_filename}`\n"
                f"Отримав: `{uploaded_filename}`\n\n"
                f"Файл буде збережено з очікуваною назвою.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("✅ Продовжити", callback_data="file_edit:confirm_save")],
                    [InlineKeyboardButton("❌ Скасувати", callback_data="file_edit:cancel")]
                ])
            )

        # Check file size (Telegram limit)
        if document.file_size > 20 * 1024 * 1024:  # 20MB
            await update.message.reply_text(
                f"❌ **Файл занадто великий**\n\n"
                f"Розмір файлу: {document.file_size:,} байт\n"
                f"Максимальний розмір: 20MB\n\n"
                f"Зменшіть розмір файлу та спробуйте ще раз.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔙 Назад", callback_data="file_edit:select_edit")]
                ])
            )
            return

        # Show processing message
        progress_msg = await update.message.reply_text(
            f"💾 **Зберігаю відредагований файл...**\n\n"
            f"📁 Файл: `{expected_filename}`\n"
            f"📏 Розмір: {document.file_size:,} байт\n\n"
            f"⏳ Зачекайте..."
        )

        # Download and save file
        file_obj = await context.bot.get_file(document.file_id)

        # Create backup of original file
        backup_path = original_path.with_suffix(original_path.suffix + '.backup')
        if original_path.exists():
            shutil.copy2(original_path, backup_path)

        # Save new file content
        await file_obj.download_to_drive(original_path)

        # Clear file action state
        context.user_data.pop("file_action", None)

        # Show success message
        await progress_msg.edit_text(
            f"✅ **Файл успішно збережено!**\n\n"
            f"📁 Файл: `{expected_filename}`\n"
            f"📏 Новий розмір: {document.file_size:,} байт\n"
            f"💾 Резервна копія: `{backup_path.name}`\n\n"
            f"🎉 Редагування завершено!",
            reply_markup=InlineKeyboardMarkup([
                [
                    InlineKeyboardButton("📖 Перевірити зміни", callback_data="file_edit:select_read"),
                    InlineKeyboardButton("📋 Меню", callback_data="action:quick_actions")
                ]
            ])
        )

        logger.info("File editing completed successfully", user_id=user_id, filename=expected_filename,
                   original_size=original_path.stat().st_size if original_path.exists() else 0,
                   new_size=document.file_size)

    except Exception as e:
        logger.error("Error saving edited file", error=str(e), user_id=user_id, filename=expected_filename)

        # Clear state on error
        context.user_data.pop("file_action", None)

        await update.message.reply_text(
            f"❌ **Помилка збереження файлу**\n\n"
            f"Не вдалося зберегти файл `{expected_filename}`:\n"
            f"```\n{str(e)}\n```\n\n"
            f"Файл не змінено.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 Повернутися", callback_data="action:quick_actions")]
            ])
        )


async def send_unavailable_message(update: Update, status_details: dict) -> None:
    """Надіслати повідомлення про недоступність Claude згідно з планом."""
    try:
        # Отримати статусне повідомлення
        status_message = status_details.get("status_message", "🔴 Claude зараз недоступний")

        # Побудувати повне повідомлення
        message_parts = [status_message]

        if "estimated_recovery" in status_details:
            message_parts.append(f"\n⏳ {status_details['estimated_recovery']}")

        message_parts.append("\n\n💡 Я повідомлю в групу, коли Claude стане доступний")
        message_parts.append("\n📋 Використайте /claude_status для перевірки")

        full_message = "".join(message_parts)

        # Надіслати повідомлення
        await update.message.reply_text(full_message, parse_mode=None)

        logger.info("Claude unavailable message sent",
                   user_id=update.effective_user.id,
                   reason=status_details.get("reason"))

    except Exception as e:
        logger.error(f"Error sending unavailable message: {e}")
        # Fallback повідомлення
        await update.message.reply_text(
            "🔴 Claude зараз недоступний\n\n"
            "Спробуйте пізніше або використайте /claude_status для перевірки.",
            parse_mode=None
        )
