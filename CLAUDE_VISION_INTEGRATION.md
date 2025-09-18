# Claude Vision API Integration Guide

## Проблема

Команда `/img` в Telegram боті не працює через фундаментальну помилку в `src/claude/facade.py` - SDK метод не передає зображення в Claude API.

## Поточна Реалізація (НЕПРАВИЛЬНА)

```python
# src/claude/facade.py:306-310
text_prompt = f"{prompt}\n\nПримітка: Зображення надіслані у вкладених повідомленнях."
response = await self.sdk_manager.execute_command(
    text_prompt, working_directory, user_id, session_id, on_stream
)
```

**Проблема**: Замість передачі зображень, додається лише текстова примітка!

## Правильна Реалізація

### 1. Виправлення SDK методу

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
    """Run command with images using SDK with proper image support."""

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

    # Прямий виклик Anthropic Messages API
    import anthropic
    import time

    client = anthropic.Anthropic(api_key=self.config.anthropic_api_key)

    try:
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

        # Логування використання зображень
        if response.session_id:
            await self._log_image_usage(user_id, response.session_id, images)

        return response

    except Exception as e:
        logger.error("SDK image processing failed", error=str(e))
        raise ClaudeError(f"Failed to process images with SDK: {str(e)}")
```

### 2. Альтернативний метод через ClaudeSDKManager

Якщо потрібно розширити `ClaudeSDKManager`:

```python
# src/claude/sdk_integration.py

async def execute_with_images(
    self,
    content: List[Dict[str, Any]],
    working_directory: Path,
    user_id: int,
    session_id: Optional[str] = None,
    on_stream: Optional[Callable[[StreamUpdate], None]] = None,
) -> ClaudeResponse:
    """Execute command with image content."""

    try:
        response = self.client.messages.create(
            model=self.config.claude_model,
            max_tokens=self.config.claude_max_tokens,
            messages=[{"role": "user", "content": content}]
        )

        # Обробка відповіді
        response_text = "".join([
            block.text for block in response.content
            if hasattr(block, 'text')
        ])

        # Створення Claude Response
        return ClaudeResponse(
            content=response_text,
            session_id=session_id or self._generate_session_id(user_id),
            success=True,
            working_directory=working_directory
        )

    except Exception as e:
        raise ClaudeError(f"SDK image execution failed: {str(e)}")
```

## Налаштування

### Environment Variables

```bash
# .env
ANTHROPIC_API_KEY=sk-ant-...
CLAUDE_MODEL=claude-3-5-sonnet-20241022
USE_SDK=true
CLAUDE_SUPPORTS_IMAGES=true
```

### Settings Configuration

```python
# src/config/settings.py
class Settings(BaseSettings):
    # ... інші налаштування

    claude_supports_images: bool = True
    anthropic_api_key: Optional[str] = None
    claude_model: str = "claude-3-5-sonnet-20241022"
```

## Тестування

### 1. Запуск тестового скрипта

```bash
python debug_image_processing.py
```

### 2. Ручне тестування

```python
import anthropic
import base64

client = anthropic.Anthropic(api_key="sk-ant-...")

# Тестове зображення 1x1 PNG
test_image = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChAI9hFTxTAAAAABJRU5ErkJggg=="

content = [
    {
        "type": "image",
        "source": {
            "type": "base64",
            "media_type": "image/png",
            "data": test_image
        }
    },
    {
        "type": "text",
        "text": "Що ти бачиш на цьому зображенні?"
    }
]

response = client.messages.create(
    model="claude-3-5-sonnet-20241022",
    max_tokens=300,
    messages=[{"role": "user", "content": content}]
)

print(response.content[0].text)
```

## Розбір Помилок

### Помилка 1: "Image processing is not enabled"

```python
# Перевірити settings
if not self.config.claude_supports_images:
    raise ClaudeToolValidationError("Image processing is not enabled")
```

**Рішення**: Встановити `CLAUDE_SUPPORTS_IMAGES=true` в .env

### Помилка 2: "API key not found"

```python
client = anthropic.Anthropic(api_key=self.config.anthropic_api_key)
```

**Рішення**: Встановити `ANTHROPIC_API_KEY=sk-ant-...` в .env

### Помилка 3: "Model does not support images"

**Рішення**: Використовувати модель з підтримкою Vision:
- `claude-3-5-sonnet-20241022`
- `claude-3-opus-20240229`
- `claude-3-sonnet-20240229`

## Архітектурні Патерни

### 1. Content Builder Pattern

```python
class ImageContentBuilder:
    def __init__(self):
        self.content = []

    def add_image(self, base64_data: str, media_type: str):
        self.content.append({
            "type": "image",
            "source": {
                "type": "base64",
                "media_type": media_type,
                "data": base64_data
            }
        })
        return self

    def add_text(self, text: str):
        self.content.append({
            "type": "text",
            "text": text
        })
        return self

    def build(self):
        return self.content
```

### 2. Response Factory Pattern

```python
class ClaudeResponseFactory:
    @staticmethod
    def from_anthropic_response(
        api_response,
        session_id: str,
        working_directory: Path
    ) -> ClaudeResponse:
        response_text = "".join([
            block.text for block in api_response.content
            if hasattr(block, 'text')
        ])

        return ClaudeResponse(
            content=response_text,
            session_id=session_id,
            success=True,
            working_directory=working_directory
        )
```

## Кращі Практики

### 1. Обробка Помилок

```python
try:
    response = await self._process_with_images(content)
except anthropic.APIError as e:
    logger.error("Anthropic API error", error=str(e))
    raise ClaudeError(f"API error: {e}")
except Exception as e:
    logger.error("Unexpected error", error=str(e))
    raise ClaudeError(f"Unexpected error: {e}")
```

### 2. Валідація Зображень

```python
def validate_image(self, image: ProcessedImage):
    # Перевірка формату
    if image.format.upper() not in ['PNG', 'JPEG', 'JPG', 'GIF', 'WEBP']:
        raise ValueError(f"Unsupported image format: {image.format}")

    # Перевірка розміру
    if len(image.data) > self.config.image_max_file_size:
        raise ValueError("Image too large")
```

### 3. Логування

```python
logger.info(
    "Processing images with Claude",
    user_id=user_id,
    image_count=len(images),
    model=self.config.claude_model,
    session_id=session_id
)
```

## Моніторинг і Метрики

```python
# Трекінг використання зображень
await self._log_image_usage(user_id, session_id, images)

# Метрики продуктивності
start_time = time.time()
response = await self._process_images(content)
processing_time = time.time() - start_time

logger.info(
    "Image processing completed",
    processing_time=processing_time,
    image_count=len(images),
    response_length=len(response.content)
)
```