"""High-level Claude Code integration facade.

Provides simple interface for bot handlers.
"""

from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Union, TYPE_CHECKING

import structlog

from ..config.settings import Settings
from .exceptions import ClaudeToolValidationError
from .integration import ClaudeProcessManager, ClaudeResponse, StreamUpdate
from .monitor import ToolMonitor
from .sdk_integration import ClaudeSDKManager
from .session import SessionManager

if TYPE_CHECKING:
    from ..bot.features.image_processor import ProcessedImage

logger = structlog.get_logger()


class ClaudeIntegration:
    """Main integration point for Claude Code."""

    def __init__(
        self,
        config: Settings,
        process_manager: Optional[ClaudeProcessManager] = None,
        sdk_manager: Optional[ClaudeSDKManager] = None,
        session_manager: Optional[SessionManager] = None,
        tool_monitor: Optional[ToolMonitor] = None,
    ):
        """Initialize Claude integration facade."""
        self.config = config

        # Initialize both managers for fallback capability
        self.sdk_manager = (
            sdk_manager or ClaudeSDKManager(config) if config.use_sdk else None
        )
        self.process_manager = process_manager or ClaudeProcessManager(config)

        # Use SDK by default if configured
        if config.use_sdk:
            self.manager = self.sdk_manager
        else:
            self.manager = self.process_manager

        self.session_manager = session_manager
        self.tool_monitor = tool_monitor
        self._sdk_failed_count = 0  # Track SDK failures for adaptive fallback

    async def run_command(
        self,
        prompt: str,
        working_directory: Path,
        user_id: int,
        session_id: Optional[str] = None,
        on_stream: Optional[Callable[[StreamUpdate], None]] = None,
    ) -> ClaudeResponse:
        """Run Claude Code command with full integration."""
        # Add Ukrainian language instruction to prompt
        enhanced_prompt = f"""ВАЖЛИВО: Відповідай ТІЛЬКИ українською мовою. Користувач з України і очікує відповіді українською.

{prompt}

ОБОВ'ЯЗКОВО відповідай українською мовою!"""
        logger.info(
            "Running Claude command",
            user_id=user_id,
            working_directory=str(working_directory),
            session_id=session_id,
            prompt_length=len(enhanced_prompt),
        )

        # Get or create session
        session = await self.session_manager.get_or_create_session(
            user_id, working_directory, session_id
        )

        # Track streaming updates and validate tool calls
        tools_validated = True
        validation_errors = []
        blocked_tools = set()

        async def stream_handler(update: StreamUpdate):
            nonlocal tools_validated

            # Validate tool calls
            if update.tool_calls:
                for tool_call in update.tool_calls:
                    tool_name = tool_call["name"]
                    valid, error = await self.tool_monitor.validate_tool_call(
                        tool_name,
                        tool_call.get("input", {}),
                        working_directory,
                        user_id,
                    )

                    if not valid:
                        tools_validated = False
                        validation_errors.append(error)

                        # Track blocked tools
                        if "Tool not allowed:" in error:
                            blocked_tools.add(tool_name)

                        logger.error(
                            "Tool validation failed",
                            tool_name=tool_name,
                            error=error,
                            user_id=user_id,
                        )

                        # For critical tools, we should fail fast
                        if tool_name in ["Task", "Read", "Write", "Edit"]:
                            # Create comprehensive error message
                            admin_instructions = self._get_admin_instructions(
                                list(blocked_tools)
                            )
                            error_msg = self._create_tool_error_message(
                                list(blocked_tools),
                                self.config.claude_allowed_tools or [],
                                admin_instructions,
                            )

                            raise ClaudeToolValidationError(
                                error_msg,
                                blocked_tools=list(blocked_tools),
                                allowed_tools=self.config.claude_allowed_tools or [],
                            )

            # Pass to caller's handler
            if on_stream:
                try:
                    await on_stream(update)
                except Exception as e:
                    logger.warning("Stream callback failed", error=str(e))

        # Execute command
        try:
            # Only continue session if it's not a new session
            should_continue = bool(session_id) and not getattr(
                session, "is_new_session", False
            )

            # For new sessions, don't pass the temporary session_id to Claude Code
            claude_session_id = (
                None
                if getattr(session, "is_new_session", False)
                else session.session_id
            )

            response = await self._execute_with_fallback(
                prompt=enhanced_prompt,
                working_directory=working_directory,
                session_id=claude_session_id,
                continue_session=should_continue,
                stream_callback=stream_handler,
            )

            # Check if tool validation failed
            if not tools_validated:
                logger.error(
                    "Command completed but tool validation failed",
                    validation_errors=validation_errors,
                )
                # Mark response as having errors and include validation details
                response.is_error = True
                response.error_type = "tool_validation_failed"

                # Extract blocked tool names for user feedback
                blocked_tools = []
                for error in validation_errors:
                    if "Tool not allowed:" in error:
                        tool_name = error.split("Tool not allowed: ")[1]
                        blocked_tools.append(tool_name)

                # Create user-friendly error message
                if blocked_tools:
                    tool_list = ", ".join(f"`{tool}`" for tool in blocked_tools)
                    response.content = (
                        f"🚫 **Tool Access Blocked**\n\n"
                        f"Claude tried to use tools not allowed:\n"
                        f"{tool_list}\n\n"
                        f"**What you can do:**\n"
                        f"• Contact the administrator to request access to these tools\n"
                        f"• Try rephrasing your request to use different approaches\n"
                        f"• Check what tools are currently available with `/status`\n\n"
                        f"**Currently allowed tools:**\n"
                        f"{', '.join(f'`{t}`' for t in self.config.claude_allowed_tools or [])}"
                    )
                else:
                    response.content = (
                        f"🚫 **Tool Validation Failed**\n\n"
                        f"Tools failed security validation. Try different approach.\n\n"
                        f"Details: {'; '.join(validation_errors)}"
                    )

            # Update session (this may change the session_id for new sessions)
            old_session_id = session.session_id
            await self.session_manager.update_session(session.session_id, response)

            # For new sessions, get the updated session_id from the session manager
            if hasattr(session, "is_new_session") and response.session_id:
                # The session_id has been updated to Claude's session_id
                final_session_id = response.session_id
            else:
                # Use the original session_id for continuing sessions
                final_session_id = old_session_id

            # Ensure response has the correct session_id
            response.session_id = final_session_id

            logger.info(
                "Claude command completed",
                session_id=response.session_id,
                cost=response.cost,
                duration_ms=response.duration_ms,
                num_turns=response.num_turns,
                is_error=response.is_error,
            )

            return response

        except Exception as e:
            logger.error(
                "Claude command failed",
                error=str(e),
                user_id=user_id,
                session_id=session.session_id,
            )
            raise

    async def run_command_with_images(
        self,
        prompt: str,
        images: List["ProcessedImage"],
        working_directory: Path,
        user_id: int,
        session_id: Optional[str] = None,
        on_stream: Optional[Callable[[StreamUpdate], None]] = None,
    ) -> ClaudeResponse:
        """Run Claude Code command with image attachments."""
        logger.info(
            "Running Claude command with images",
            user_id=user_id,
            working_directory=str(working_directory),
            session_id=session_id,
            prompt_length=len(prompt),
            image_count=len(images),
        )

        if not self.config.claude_supports_images:
            raise ClaudeToolValidationError(
                "Image processing is not enabled for Claude CLI. "
                "Please contact the administrator to enable image support."
            )

        # Try SDK first if available and supports images
        if self.config.use_sdk and self.sdk_manager:
            try:
                return await self._run_command_with_images_sdk(
                    prompt, images, working_directory, user_id, session_id, on_stream
                )
            except Exception as e:
                logger.warning("SDK image processing failed, falling back to CLI", error=str(e))
                self._sdk_failed_count += 1

        # Fallback to CLI with enhanced prompt and image copying
        return await self._run_command_with_images_cli(
            prompt, images, working_directory, user_id, session_id, on_stream
        )

    async def _run_command_with_images_sdk(
        self,
        prompt: str,
        images: List["ProcessedImage"],
        working_directory: Path,
        user_id: int,
        session_id: Optional[str] = None,
        on_stream: Optional[Callable[[StreamUpdate], None]] = None,
    ) -> ClaudeResponse:
        """Run command with images using SDK with PROPER image support."""
        import time

        # Перевірка API ключа
        if not self.config.anthropic_api_key:
            raise ClaudeToolValidationError("ANTHROPIC_API_KEY not configured")

        try:
            import anthropic
        except ImportError:
            logger.error("anthropic module not available, falling back to CLI")
            raise ClaudeToolValidationError("anthropic module not installed")

        client = anthropic.Anthropic(api_key=self.config.anthropic_api_key)

        # Будуємо контент з зображеннями
        content = []

        # Додаємо зображення спочатку
        for image in images:
            base64_data = await image.get_base64_data()
            content.append({
                "type": "image",
                "source": {
                    "type": "base64",
                    "media_type": f"image/{image.format.lower()}",
                    "data": base64_data
                }
            })

        # Додаємо текстовий промпт
        content.append({
            "type": "text",
            "text": prompt
        })

        logger.info("Sending images to Claude API", image_count=len(images), user_id=user_id)

        try:
            # Прямий виклик Anthropic Messages API
            api_response = client.messages.create(
                model=self.config.claude_model or "claude-3-5-sonnet-20241022",
                max_tokens=4000,
                messages=[{"role": "user", "content": content}]
            )

            # Конвертуємо в ClaudeResponse
            response_text = "".join([
                block.text for block in api_response.content
                if hasattr(block, 'text')
            ])

            response = ClaudeResponse(
                content=response_text,
                session_id=session_id or f"sdk_img_{user_id}_{int(time.time())}",
                success=True,
                working_directory=working_directory
            )

            logger.info("Claude API response received",
                       response_length=len(response_text),
                       session_id=response.session_id)

            # Track image usage
            if response.session_id:
                await self._log_image_usage(user_id, response.session_id, images)

            return response

        except anthropic.APIError as e:
            logger.error("Anthropic API error", error=str(e), user_id=user_id)
            raise ClaudeToolValidationError(f"API error: {str(e)}")
        except Exception as e:
            logger.error("SDK image processing failed", error=str(e), user_id=user_id)
            raise ClaudeToolValidationError(f"Failed to process images: {str(e)}")

    async def _run_command_with_images_cli(
        self,
        prompt: str,
        images: List["ProcessedImage"],
        working_directory: Path,
        user_id: int,
        session_id: Optional[str] = None,
        on_stream: Optional[Callable[[StreamUpdate], None]] = None,
    ) -> ClaudeResponse:
        """Run command with images using CLI (copies images to working directory)."""
        # Copy images to working directory for Claude CLI access
        copied_images = []
        try:
            for i, image in enumerate(images):
                # Create unique filename in working directory
                image_filename = f"uploaded_image_{i+1}_{image.filename}"
                target_path = working_directory / image_filename

                # Copy image file
                import shutil
                shutil.copy2(image.file_path, target_path)
                copied_images.append((target_path, image))
                logger.debug("Copied image for CLI", src=str(image.file_path), dst=str(target_path))

            # Create enhanced prompt with references to copied images
            enhanced_prompt = await self._create_image_prompt_with_paths(prompt, copied_images)

            # Run command with CLI
            response = await self.run_command(
                prompt=enhanced_prompt,
                working_directory=working_directory,
                user_id=user_id,
                session_id=session_id,
                on_stream=on_stream,
            )

            # Track image usage
            if response.session_id:
                await self._log_image_usage(user_id, response.session_id, images)

            return response

        finally:
            # Clean up copied images
            for copied_path, _ in copied_images:
                try:
                    if copied_path.exists():
                        copied_path.unlink()
                        logger.debug("Cleaned up copied image", path=str(copied_path))
                except Exception as e:
                    logger.warning("Failed to cleanup copied image", path=str(copied_path), error=str(e))

    async def _create_image_prompt(
        self, 
        prompt: str, 
        images: List["ProcessedImage"]
    ) -> str:
        """Create enhanced prompt with image context information."""
        if not images:
            return prompt

        image_info = []
        for i, img in enumerate(images, 1):
            info = f"Image {i}: {img.filename} ({img.format}, {img.dimensions[0]}x{img.dimensions[1]}, {img.file_size / 1024:.1f}KB)"
            if img.caption:
                info += f" - Caption: {img.caption}"
            image_info.append(info)

        enhanced_prompt = f"""ВАЖЛИВО: Відповідай ТІЛЬКИ українською мовою. Користувач з України і очікує відповіді українською.

{prompt}

Я надаю тобі {len(images)} зображень для аналізу:
{chr(10).join(image_info)}

Будь ласка, проаналізуй ці зображення в контексті мого запиту вище. Врахуй:
1. Зміст і контекст кожного зображення
2. Будь-який текст, код або елементи UI, що видимі
3. Технічні аспекти, якщо релевантні (архітектура, діаграми, фрагменти коду)
4. Зв'язки між зображеннями, якщо їх кілька
5. Конкретні практичні рекомендації

Примітка: Хоча я не можу безпосередньо прикріпити файли зображень до цього промпту, будь ласка, надай свій найкращий аналіз і рекомендації на основі наданого контексту і назв файлів.

ОБОВ'ЯЗКОВО відповідай українською мовою!"""

        return enhanced_prompt

    async def _create_image_prompt_with_paths(
        self,
        prompt: str,
        copied_images: List[tuple]  # (Path, ProcessedImage)
    ) -> str:
        """Create enhanced prompt with image file paths for CLI access."""
        if not copied_images:
            return prompt

        image_info = []
        image_paths = []
        for i, (path, img) in enumerate(copied_images, 1):
            info = f"Image {i}: {path.name} ({img.format}, {img.dimensions[0]}x{img.dimensions[1]}, {img.file_size / 1024:.1f}KB)"
            if img.caption:
                info += f" - Caption: {img.caption}"
            image_info.append(info)
            image_paths.append(str(path.name))

        enhanced_prompt = f"""ВАЖЛИВО: Відповідай ТІЛЬКИ українською мовою. Користувач з України і очікує відповіді українською.

{prompt}

Я надаю тобі {len(copied_images)} зображень для аналізу. Файли зображень доступні в робочій директорії:
{chr(10).join(image_info)}

Ти можеш використовувати Read tool для перегляду цих зображень:
{', '.join(image_paths)}

Будь ласка, проаналізуй ці зображення в контексті мого запиту вище. Врахуй:
1. Зміст і контекст кожного зображення
2. Будь-який текст, код або елементи UI, що видимі
3. Технічні аспекти, якщо релевантні (архітектура, діаграми, фрагменти коду)
4. Зв'язки між зображеннями, якщо їх кілька
5. Конкретні практичні рекомендації

Використай Read tool для перегляду зображень і надай детальний аналіз.

ОБОВ'ЯЗКОВО відповідай українською мовою!"""

        return enhanced_prompt

    async def _log_image_usage(
        self, 
        user_id: int, 
        session_id: str, 
        images: List["ProcessedImage"]
    ) -> None:
        """Log image usage for tracking purposes."""
        try:
            total_size = sum(img.file_size for img in images)
            logger.info(
                "Image processing completed",
                user_id=user_id,
                session_id=session_id,
                image_count=len(images),
                total_size_mb=round(total_size / (1024 * 1024), 2),
                formats=[img.format for img in images],
            )
        except Exception as e:
            logger.warning("Failed to log image usage", error=str(e))

    async def _execute_with_fallback(
        self,
        prompt: str,
        working_directory: Path,
        session_id: Optional[str] = None,
        continue_session: bool = False,
        stream_callback: Optional[Callable] = None,
    ) -> ClaudeResponse:
        """Execute command with SDK->subprocess fallback on JSON decode errors."""
        # Try SDK first if configured
        if self.config.use_sdk and self.sdk_manager:
            try:
                logger.debug("Attempting Claude SDK execution")
                response = await self.sdk_manager.execute_command(
                    prompt=prompt,
                    working_directory=working_directory,
                    session_id=session_id,
                    continue_session=continue_session,
                    stream_callback=stream_callback,
                )
                # Reset failure count on success
                self._sdk_failed_count = 0
                return response

            except Exception as e:
                error_str = str(e)
                # Check if this is a JSON decode error that indicates SDK issues
                if (
                    "Failed to decode JSON" in error_str
                    or "JSON decode error" in error_str
                    or "TaskGroup" in error_str
                    or "ExceptionGroup" in error_str
                ):
                    self._sdk_failed_count += 1
                    logger.warning(
                        "Claude SDK failed with JSON/TaskGroup error, falling back to subprocess",
                        error=error_str,
                        failure_count=self._sdk_failed_count,
                        error_type=type(e).__name__,
                    )

                    # Use subprocess fallback
                    try:
                        logger.info("Executing with subprocess fallback")
                        response = await self.process_manager.execute_command(
                            prompt=prompt,
                            working_directory=working_directory,
                            session_id=session_id,
                            continue_session=continue_session,
                            stream_callback=stream_callback,
                        )
                        logger.info("Subprocess fallback succeeded")
                        return response

                    except Exception as fallback_error:
                        logger.error(
                            "Both SDK and subprocess failed",
                            sdk_error=error_str,
                            subprocess_error=str(fallback_error),
                        )
                        # Re-raise the original SDK error since it was the primary method
                        raise e
                else:
                    # For non-JSON errors, re-raise immediately
                    logger.error(
                        "Claude SDK failed with non-JSON error", error=error_str
                    )
                    raise
        else:
            # Use subprocess directly if SDK not configured
            logger.debug("Using subprocess execution (SDK disabled)")
            return await self.process_manager.execute_command(
                prompt=prompt,
                working_directory=working_directory,
                session_id=session_id,
                continue_session=continue_session,
                stream_callback=stream_callback,
            )

    async def continue_session(
        self,
        user_id: int,
        working_directory: Path,
        prompt: Optional[str] = None,
        on_stream: Optional[Callable[[StreamUpdate], None]] = None,
    ) -> Optional[ClaudeResponse]:
        """Continue the most recent session."""
        logger.info(
            "Continuing session",
            user_id=user_id,
            working_directory=str(working_directory),
            has_prompt=bool(prompt),
        )

        # Get user's sessions
        sessions = await self.session_manager._get_user_sessions(user_id)

        # Find most recent session in this directory (exclude temporary sessions)
        matching_sessions = [
            s
            for s in sessions
            if s.project_path == working_directory
            and not s.session_id.startswith("temp_")
        ]

        if not matching_sessions:
            logger.info("No matching sessions found", user_id=user_id)
            return None

        # Get most recent
        latest_session = max(matching_sessions, key=lambda s: s.last_used)

        # Continue session
        return await self.run_command(
            prompt=prompt or "",
            working_directory=working_directory,
            user_id=user_id,
            session_id=latest_session.session_id,
            on_stream=on_stream,
        )

    async def get_session_info(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get session information."""
        return await self.session_manager.get_session_info(session_id)

    async def get_user_sessions(self, user_id: int) -> List[Dict[str, Any]]:
        """Get all sessions for a user."""
        sessions = await self.session_manager._get_user_sessions(user_id)
        return [
            {
                "session_id": s.session_id,
                "project_path": str(s.project_path),
                "created_at": s.created_at.isoformat(),
                "last_used": s.last_used.isoformat(),
                "total_cost": s.total_cost,
                "message_count": s.message_count,
                "tools_used": s.tools_used,
                "expired": s.is_expired(self.config.session_timeout_hours),
            }
            for s in sessions
        ]

    async def cleanup_expired_sessions(self) -> int:
        """Clean up expired sessions."""
        return await self.session_manager.cleanup_expired_sessions()

    async def get_tool_stats(self) -> Dict[str, Any]:
        """Get tool usage statistics."""
        return self.tool_monitor.get_tool_stats()

    async def get_user_summary(self, user_id: int) -> Dict[str, Any]:
        """Get comprehensive user summary."""
        session_summary = await self.session_manager.get_user_session_summary(user_id)
        tool_usage = self.tool_monitor.get_user_tool_usage(user_id)

        return {
            "user_id": user_id,
            **session_summary,
            **tool_usage,
        }

    async def shutdown(self) -> None:
        """Shutdown integration and cleanup resources."""
        logger.info("Shutting down Claude integration")

        # Kill any active processes
        await self.manager.kill_all_processes()

        # Clean up expired sessions
        await self.cleanup_expired_sessions()

        logger.info("Claude integration shutdown complete")

    def _get_admin_instructions(self, blocked_tools: List[str]) -> str:
        """Generate admin instructions for enabling blocked tools."""
        instructions = []

        # Check if settings file exists
        settings_file = Path(".env")

        if blocked_tools:
            # Get current allowed tools and create merged list without duplicates
            current_tools = [
                "Read",
                "Write",
                "Edit",
                "Bash",
                "Glob",
                "Grep",
                "LS",
                "Task",
                "MultiEdit",
                "NotebookRead",
                "NotebookEdit",
                "WebFetch",
                "TodoRead",
                "TodoWrite",
                "WebSearch",
            ]
            merged_tools = list(
                dict.fromkeys(current_tools + blocked_tools)
            )  # Remove duplicates while preserving order
            merged_tools_str = ",".join(merged_tools)
            merged_tools_py = ", ".join(f'"{tool}"' for tool in merged_tools)

            instructions.append("**For Administrators:**")
            instructions.append("")

            if settings_file.exists():
                instructions.append(
                    "To enable these tools, add them to your `.env` file:"
                )
                instructions.append("```")
                instructions.append(f'CLAUDE_ALLOWED_TOOLS="{merged_tools_str}"')
                instructions.append("```")
            else:
                instructions.append("To enable these tools:")
                instructions.append("1. Create a `.env` file in your project root")
                instructions.append("2. Add the following line:")
                instructions.append("```")
                instructions.append(f'CLAUDE_ALLOWED_TOOLS="{merged_tools_str}"')
                instructions.append("```")

            instructions.append("")
            instructions.append("Or modify the default in `src/config/settings.py`:")
            instructions.append("```python")
            instructions.append("claude_allowed_tools: Optional[List[str]] = Field(")
            instructions.append(f"    default=[{merged_tools_py}],")
            instructions.append('    description="List of allowed Claude tools",')
            instructions.append(")")
            instructions.append("```")

        return "\n".join(instructions)

    def _create_tool_error_message(
        self,
        blocked_tools: List[str],
        allowed_tools: List[str],
        admin_instructions: str,
    ) -> str:
        """Create a comprehensive error message for tool validation failures."""
        tool_list = ", ".join(f"`{tool}`" for tool in blocked_tools)
        allowed_list = (
            ", ".join(f"`{tool}`" for tool in allowed_tools)
            if allowed_tools
            else "None"
        )

        message = [
            "🚫 **Tool Access Blocked**",
            "",
            f"Claude tried to use tools that are not currently allowed:",
            f"{tool_list}",
            "",
            "**Why this happened:**",
            "• Claude needs these tools to complete your request",
            "• These tools are not in the allowed tools list",
            "• This is a security feature to control what Claude can do",
            "",
            "**What you can do:**",
            "• Contact the administrator to request access to these tools",
            "• Try rephrasing your request to use different approaches",
            "• Use simpler requests that don't require these tools",
            "",
            "**Currently allowed tools:**",
            f"{allowed_list}",
            "",
            admin_instructions,
        ]

        return "\n".join(message)
