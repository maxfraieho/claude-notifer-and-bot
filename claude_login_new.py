"""
Новий функціонал /login для Claude CLI авторизації з pexpect
"""

import asyncio
import structlog
import pexpect
import re
import time
from pathlib import Path
from typing import Optional, Tuple
from telegram import Update
from telegram.ext import ContextTypes

logger = structlog.get_logger()


async def extract_auth_url_from_claude_login() -> Tuple[bool, str, Optional[pexpect.spawn]]:
    """
    Запускає `claude login` та витягує URL для авторизації.

    Returns:
        Tuple з (успіх, URL_або_помилка, процес_pexpect)
    """
    try:
        logger.info("Starting claude login to extract auth URL")

        # Запускаємо процес claude login
        child = pexpect.spawn('claude login', encoding='utf-8', timeout=30)

        # Паттерни для пошуку URL
        url_patterns = [
            r'https://claude\.ai/login\?[^\s]*',  # Claude login URL
            r'https://[^\s]*anthropic[^\s]*',     # Anthropic URL
            r'https://[^\s]+',                    # Будь-який HTTPS URL
            pexpect.TIMEOUT,
            pexpect.EOF
        ]

        output_buffer = ""
        start_time = time.time()

        while time.time() - start_time < 30:  # 30 секунд timeout
            try:
                index = child.expect(url_patterns, timeout=5)

                # Збираємо весь вивід
                if child.before:
                    output_buffer += child.before
                if child.after and index < 3:  # URL знайдено
                    output_buffer += child.after

                logger.debug("Claude login output", index=index, output=output_buffer[-200:])

                if index < 3:  # URL знайдено
                    # Витягуємо URL з output_buffer
                    url_match = re.search(r'https://[^\s]+', output_buffer)
                    if url_match:
                        auth_url = url_match.group(0)
                        logger.info("Auth URL extracted successfully", url=auth_url[:50] + "...")
                        return True, auth_url, child

                elif index == 3:  # TIMEOUT
                    continue

                elif index == 4:  # EOF
                    break

            except pexpect.TIMEOUT:
                continue

        # Якщо URL не знайдено, перевіримо весь output
        url_match = re.search(r'https://[^\s]+', output_buffer)
        if url_match:
            auth_url = url_match.group(0)
            logger.info("Auth URL found in buffer", url=auth_url[:50] + "...")
            return True, auth_url, child

        logger.error("No auth URL found in claude login output", output=output_buffer)
        child.close()
        return False, f"No authentication URL found. Output: {output_buffer}", None

    except Exception as e:
        logger.error("Error extracting auth URL", error=str(e))
        if 'child' in locals() and child.isalive():
            child.close()
        return False, f"Error starting claude login: {str(e)}", None


async def submit_auth_code_to_claude(child: pexpect.spawn, auth_code: str) -> Tuple[bool, str]:
    """
    Надсилає код авторизації до процесу claude login.

    Args:
        child: Активний процес pexpect
        auth_code: Код авторизації від користувача

    Returns:
        Tuple з (успіх, результат_або_помилка)
    """
    try:
        logger.info("Submitting auth code to claude login")

        # Надсилаємо код
        child.sendline(auth_code)

        # Паттерни для очікування результату
        result_patterns = [
            r'(?i)success',           # Успіх
            r'(?i)authenticated',     # Автентифіковано
            r'(?i)logged.*in',        # Залогінено
            r'(?i)invalid.*code',     # Невірний код
            r'(?i)expired.*code',     # Код просрочений
            r'(?i)error',             # Помилка
            r'(?i)failed',            # Невдача
            pexpect.TIMEOUT,
            pexpect.EOF
        ]

        output_buffer = ""
        start_time = time.time()

        while time.time() - start_time < 60:  # 60 секунд на авторизацію
            try:
                index = child.expect(result_patterns, timeout=10)

                # Збираємо вивід
                if child.before:
                    output_buffer += child.before
                if child.after and index < 7:
                    output_buffer += child.after

                logger.debug("Auth code response", index=index, output=output_buffer[-200:])

                if index in [0, 1, 2]:  # Успіх
                    logger.info("Authentication successful")
                    child.close()
                    return True, "Authentication successful"

                elif index in [3, 4, 5, 6]:  # Помилка
                    logger.warning("Authentication failed", output=output_buffer)
                    child.close()
                    return False, f"Authentication failed: {output_buffer}"

                elif index == 7:  # TIMEOUT
                    continue

                elif index == 8:  # EOF
                    # Перевіряємо exit code
                    if child.exitstatus == 0:
                        logger.info("Process exited successfully")
                        return True, "Authentication completed successfully"
                    else:
                        logger.warning("Process exited with error", exit_code=child.exitstatus)
                        return False, f"Process failed with exit code {child.exitstatus}: {output_buffer}"

            except pexpect.TIMEOUT:
                logger.debug("Waiting for auth response...")
                continue

        # Timeout
        logger.error("Authentication timeout", output=output_buffer)
        child.close()
        return False, f"Authentication timed out: {output_buffer}"

    except Exception as e:
        logger.error("Error submitting auth code", error=str(e))
        if child and child.isalive():
            child.close()
        return False, f"Error during authentication: {str(e)}"


async def check_claude_auth_status() -> Tuple[bool, str]:
    """
    Перевіряє поточний статус авторизації Claude CLI.

    Returns:
        Tuple з (авторизований, опис_статусу)
    """
    try:
        logger.info("Checking Claude CLI auth status")

        # Перевіряємо файл з креденшиалами
        credentials_path = Path.home() / ".claude" / ".credentials.json"

        if not credentials_path.exists():
            return False, "Файл креденшиалів не знайдено"

        # Перевіряємо термін дії токену
        import json
        with open(credentials_path, 'r') as f:
            creds = json.load(f)
            oauth_data = creds.get("claudeAiOauth", {})
            expires_at = oauth_data.get("expiresAt", 0)
            current_time = time.time() * 1000

            if current_time >= expires_at:
                return False, f"Токен просрочений (до {expires_at})"

        # Тестуємо підключення
        test_result = await asyncio.create_subprocess_exec(
            "timeout", "10", "claude", "auth", "status",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await test_result.communicate()

        if test_result.returncode == 0:
            hours_remaining = (expires_at - current_time) / (1000 * 3600)
            return True, f"Авторизований (залишилось {hours_remaining:.1f} годин)"
        else:
            return False, f"Помилка підключення: {stderr.decode()[:100]}"

    except Exception as e:
        logger.error("Error checking auth status", error=str(e))
        return False, f"Помилка перевірки: {str(e)}"


async def login_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обробляє команду /login для авторизації Claude CLI."""
    user_id = update.effective_user.id
    message = update.effective_message

    if not user_id or not message:
        return

    try:
        # Перевіряємо чи не очікуємо вже код авторизації
        if context.user_data.get('claude_auth_waiting'):
            await message.reply_text(
                "⏳ **Вже очікую код авторизації**\n\n"
                "Надішліть код авторизації з браузера або використайте /cancel для скасування."
            )
            return

        # Перевіряємо поточний статус авторизації
        await message.reply_text("🔍 **Перевіряю поточний статус авторизації...**")

        is_auth, status_msg = await check_claude_auth_status()

        if is_auth:
            await message.reply_text(
                f"✅ **Claude CLI вже авторизований**\n\n"
                f"📊 Статус: {status_msg}\n\n"
                f"Авторизація не потрібна!"
            )
            return

        # Починаємо процес авторизації
        await message.reply_text(
            f"❌ **Claude CLI не авторизований**\n\n"
            f"📊 Статус: {status_msg}\n\n"
            f"🚀 Починаю процес авторизації..."
        )

        # Витягуємо URL авторизації
        success, result, child = await extract_auth_url_from_claude_login()

        if not success:
            await message.reply_text(
                f"❌ **Помилка запуску авторизації**\n\n"
                f"```\n{result}\n```\n\n"
                f"Спробуйте ще раз або зверніться до адміністратора."
            )
            return

        # Зберігаємо процес для подальшого використання
        context.user_data['claude_auth_waiting'] = True
        context.user_data['claude_auth_process'] = child
        context.user_data['claude_auth_url'] = result

        # Надсилаємо інструкції користувачу
        auth_url = result
        instructions = (
            f"🔐 **Авторизація Claude CLI**\n\n"
            f"**Крок 1:** Відкрийте це посилання у браузері:\n"
            f"👆 {auth_url}\n\n"
            f"**Крок 2:** Увійдіть у свій акаунт Claude\n\n"
            f"**Крок 3:** Скопіюйте код авторизації\n\n"
            f"**Крок 4:** Надішліть код у це повідомлення\n\n"
            f"⏳ **Очікую код авторизації...**\n\n"
            f"💡 Використайте /cancel для скасування"
        )

        await message.reply_text(instructions)

        logger.info("Claude login process started", user_id=user_id, url_length=len(auth_url))

    except Exception as e:
        logger.error("Error in login command", error=str(e), user_id=user_id, exc_info=True)

        # Очищуємо стан в разі помилки
        context.user_data.pop('claude_auth_waiting', None)
        if 'claude_auth_process' in context.user_data:
            try:
                context.user_data['claude_auth_process'].close()
            except:
                pass
            context.user_data.pop('claude_auth_process', None)

        await message.reply_text(
            f"❌ **Помилка виконання команди**\n\n"
            f"```\n{str(e)}\n```\n\n"
            f"Спробуйте ще раз."
        )


async def handle_auth_code_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """
    Обробляє повідомлення з кодом авторизації.

    Returns:
        True якщо повідомлення оброблено як код авторизації, False інакше
    """
    user_id = update.effective_user.id
    message = update.effective_message

    if not user_id or not message or not message.text:
        return False

    # Перевіряємо чи очікуємо код авторизації
    if not context.user_data.get('claude_auth_waiting'):
        return False

    auth_code = message.text.strip()

    # Перевіряємо формат коду (зазвичай це довгий рядок)
    if len(auth_code) < 10:
        await message.reply_text(
            "🤔 **Код занадто короткий**\n\n"
            "Код авторизації зазвичай довгий рядок.\n"
            "Перевірте та надішліть правильний код.\n\n"
            "💡 Використайте /cancel для скасування"
        )
        return True

    try:
        await message.reply_text("🔄 **Обробляю код авторизації...**")

        # Отримуємо збережений процес
        child = context.user_data.get('claude_auth_process')
        if not child or not child.isalive():
            await message.reply_text(
                "❌ **Сесія авторизації втрачена**\n\n"
                "Процес авторизації більше не активний.\n"
                "Виконайте /login знову."
            )
            # Очищуємо стан
            context.user_data.pop('claude_auth_waiting', None)
            context.user_data.pop('claude_auth_process', None)
            return True

        # Надсилаємо код до Claude CLI
        success, result = await submit_auth_code_to_claude(child, auth_code)

        # Очищуємо стан авторизації
        context.user_data.pop('claude_auth_waiting', None)
        context.user_data.pop('claude_auth_process', None)
        context.user_data.pop('claude_auth_url', None)

        if success:
            await message.reply_text(
                f"✅ **Авторизація успішна!**\n\n"
                f"🎉 Claude CLI тепер авторизований\n"
                f"📊 Результат: {result}\n\n"
                f"Тепер ви можете користуватися всіма функціями бота!"
            )
            logger.info("Claude CLI authentication successful", user_id=user_id)
        else:
            await message.reply_text(
                f"❌ **Помилка авторизації**\n\n"
                f"```\n{result}\n```\n\n"
                f"Спробуйте /login знову з новим кодом."
            )
            logger.warning("Claude CLI authentication failed", user_id=user_id, error=result)

        return True

    except Exception as e:
        logger.error("Error processing auth code", error=str(e), user_id=user_id, exc_info=True)

        # Очищуємо стан
        context.user_data.pop('claude_auth_waiting', None)
        if 'claude_auth_process' in context.user_data:
            try:
                context.user_data['claude_auth_process'].close()
            except:
                pass
            context.user_data.pop('claude_auth_process', None)

        await message.reply_text(
            f"❌ **Помилка обробки коду**\n\n"
            f"```\n{str(e)}\n```\n\n"
            f"Спробуйте /login знову."
        )
        return True


async def cancel_auth_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Скасовує поточний процес авторизації."""
    user_id = update.effective_user.id
    message = update.effective_message

    if not user_id or not message:
        return

    if not context.user_data.get('claude_auth_waiting'):
        await message.reply_text(
            "ℹ️ **Немає активного процесу авторизації**\n\n"
            "Немає що скасовувати."
        )
        return

    try:
        # Закриваємо процес якщо він є
        if 'claude_auth_process' in context.user_data:
            try:
                context.user_data['claude_auth_process'].close()
            except:
                pass
            context.user_data.pop('claude_auth_process', None)

        # Очищуємо стан
        context.user_data.pop('claude_auth_waiting', None)
        context.user_data.pop('claude_auth_url', None)

        await message.reply_text(
            "✅ **Авторизація скасована**\n\n"
            "Процес авторизації Claude CLI скасовано.\n"
            "Використайте /login для нової спроби."
        )

        logger.info("Claude CLI authentication cancelled", user_id=user_id)

    except Exception as e:
        logger.error("Error cancelling auth", error=str(e), user_id=user_id)
        await message.reply_text(
            f"❌ **Помилка скасування**\n\n"
            f"```\n{str(e)}\n```"
        )