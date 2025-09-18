# Debugging Guide: /img Command Issues

## 🚨 Головна Проблема

**Команда `/img` не передає зображення в Claude API!**

Локація: `src/claude/facade.py:306-310`

```python
# НЕПРАВИЛЬНО:
text_prompt = f"{prompt}\n\nПримітка: Зображення надіслані у вкладених повідомленнях."
response = await self.sdk_manager.execute_command(
    text_prompt, working_directory, user_id, session_id, on_stream
)
```

## 🔍 Діагностика Кроки

### 1. Швидка Перевірка API

```bash
# Тест Anthropic API
python3 -c "
import anthropic, os, base64
client = anthropic.Anthropic(api_key=os.environ.get('ANTHROPIC_API_KEY'))
test_img = 'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChAI9hFTxTAAAAABJRU5ErkJggg=='
content = [{'type': 'image', 'source': {'type': 'base64', 'media_type': 'image/png', 'data': test_img}}, {'type': 'text', 'text': 'Що тут?'}]
resp = client.messages.create(model='claude-3-5-sonnet-20241022', max_tokens=100, messages=[{'role': 'user', 'content': content}])
print('✅ API працює:', resp.content[0].text)
"
```

### 2. Перевірка Конфігурації

```bash
# Перевірка .env файлу
echo "ANTHROPIC_API_KEY: $(echo $ANTHROPIC_API_KEY | cut -c1-10)..."
echo "USE_SDK: $USE_SDK"
echo "CLAUDE_SUPPORTS_IMAGES: $CLAUDE_SUPPORTS_IMAGES"

# Перевірка в коді
python3 -c "
from src.config.settings import Settings
s = Settings()
print(f'SDK: {s.use_sdk}')
print(f'Images: {s.claude_supports_images}')
print(f'Model: {s.claude_model}')
print(f'API Key: {s.anthropic_api_key[:10] if s.anthropic_api_key else None}...')
"
```

### 3. Запуск Повного Тесту

```bash
python debug_image_processing.py
```

## 🛠️ Кроки Виправлення

### Крок 1: Резервна Копія

```bash
cp src/claude/facade.py src/claude/facade.py.backup
```

### Крок 2: Виправлення SDK Методу

Замінити метод `_run_command_with_images_sdk` в `src/claude/facade.py`:

```python
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
    import anthropic
    import time

    # Перевірка API ключа
    if not self.config.anthropic_api_key:
        raise ClaudeError("ANTHROPIC_API_KEY not configured")

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

        # Логування використання зображень
        if response.session_id:
            await self._log_image_usage(user_id, response.session_id, images)

        return response

    except anthropic.APIError as e:
        logger.error("Anthropic API error", error=str(e), user_id=user_id)
        raise ClaudeError(f"API error: {str(e)}")
    except Exception as e:
        logger.error("SDK image processing failed", error=str(e), user_id=user_id)
        raise ClaudeError(f"Failed to process images: {str(e)}")
```

### Крок 3: Додати Імпорти

Переконатися, що в топі `facade.py` є:

```python
import time
# інші імпорти...
```

### Крок 4: Перевірка Налаштувань

Оновити `.env`:

```bash
# Обов'язкові налаштування
ANTHROPIC_API_KEY=sk-ant-your-key-here
USE_SDK=true
CLAUDE_SUPPORTS_IMAGES=true
CLAUDE_MODEL=claude-3-5-sonnet-20241022

# Додаткові налаштування зображень
IMAGE_MAX_BATCH_SIZE=5
IMAGE_MAX_FILE_SIZE=20971520
IMAGE_SESSION_TIMEOUT_MINUTES=10
```

## 🧪 Тестування Після Виправлення

### 1. Тест Юніт

```python
# test_image_fix.py
import asyncio
from src.claude.facade import ClaudeIntegration
from src.config.settings import Settings

async def test_fix():
    settings = Settings()
    claude = ClaudeIntegration(settings)

    # Мок ProcessedImage
    class MockImage:
        format = "PNG"
        async def get_base64_data(self):
            return "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChAI9hFTxTAAAAABJRU5ErkJggg=="

    images = [MockImage()]
    response = await claude._run_command_with_images_sdk(
        "Що на зображенні?", images, Path("."), 123
    )
    print("✅ Тест пройшов:", response.content[:100])

asyncio.run(test_fix())
```

### 2. Тест Telegram

1. Запустити бота: `python -m src.main`
2. Надіслати `/img` в чат
3. Прикріпити PNG/JPEG зображення
4. Написати "готово" або "process"
5. Перевірити відповідь

## 🔍 Діагностика Логів

### Включити Детальне Логування

```python
# src/main.py
import structlog
structlog.configure(
    wrapper_class=structlog.make_filtering_bound_logger(20),  # DEBUG level
    logger_factory=structlog.WriteLoggerFactory(),
    processors=[
        structlog.processors.TimeStamper(fmt="ISO"),
        structlog.dev.ConsoleRenderer()
    ]
)
```

### Шукати в Логах

```bash
# Успішні запити
tail -f bot.log | grep "Claude API response received"

# Помилки API
tail -f bot.log | grep "Anthropic API error"

# Обробка зображень
tail -f bot.log | grep "Sending images to Claude API"
```

## 🚨 Типові Помилки і Рішення

### Помилка: "API key not configured"

```bash
echo 'ANTHROPIC_API_KEY=sk-ant-your-key-here' >> .env
```

### Помилка: "Model does not support images"

Перевірити модель в .env:
```bash
echo 'CLAUDE_MODEL=claude-3-5-sonnet-20241022' >> .env
```

### Помилка: "Image processing is not enabled"

```bash
echo 'CLAUDE_SUPPORTS_IMAGES=true' >> .env
```

### Помилка: "SDK image processing failed"

1. Перевірити інтернет з'єднання
2. Перевірити валідність API ключа
3. Перевірити формат зображення (PNG/JPEG)

## 🔄 Fallback на CLI

Якщо SDK не працює, бот автоматично перемикається на CLI метод:

```python
# Це в facade.py вже є
except Exception as e:
    logger.warning("SDK image processing failed, falling back to CLI", error=str(e))
    self._sdk_failed_count += 1

# Fallback to CLI with enhanced prompt and image copying
return await self._run_command_with_images_cli(
    prompt, images, working_directory, user_id, session_id, on_stream
)
```

CLI метод копіює зображення у робочу директорію і передає шляхи до файлів.

## 📊 Моніторинг Роботи

### Метрики для Відстеження

```python
# Додати в facade.py
self._image_processing_count = 0
self._sdk_success_count = 0
self._cli_fallback_count = 0

# В кінці методу
self._image_processing_count += 1
if success:
    self._sdk_success_count += 1
```

### Dashboard Команда

```python
# Додати команду /imgstats
async def img_stats_command(update, context):
    facade = context.bot_data.get('claude_integration')
    stats = f"""
📊 Image Processing Stats:
Total: {facade._image_processing_count}
SDK Success: {facade._sdk_success_count}
CLI Fallback: {facade._cli_fallback_count}
Success Rate: {facade._sdk_success_count/max(facade._image_processing_count,1)*100:.1f}%
"""
    await update.message.reply_text(stats)
```