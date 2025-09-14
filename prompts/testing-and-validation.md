# Промпт: Тестування та валідація

## Опис процесу
Цей промпт автоматизує комплексне тестування функціональності Claude Telegram Bot, включаючи unit тести, інтеграційні тести та ручне тестування через Telegram.

## Діалог з Claude Code

**Користувач:**
```
test-all
```

**Claude Code відповідає:**
Я виконаю повне тестування системи. Процес включає:

1. Перевірка залежностей та середовища
2. Виконання unit тестів
3. Тестування інтеграції з Claude API
4. Валідація Telegram Bot функціональності
5. Перевірка безпеки та rate limiting
6. Тестування Docker контейнера

Почнемо тестування:

*Виконує послідовність команд:*

```bash
# 1. Перевірка середовища
poetry --version
python --version

# 2. Встановлення dev залежностей
poetry install --with dev

# 3. Linting та форматування
poetry run black --check src/
poetry run isort --check-only src/
poetry run flake8 src/

# 4. Type checking
poetry run mypy src/

# 5. Unit тести з покриттям
poetry run pytest tests/ -v --cov=src --cov-report=html --cov-report=term

# 6. Інтеграційні тести (якщо є)
poetry run pytest tests/integration/ -v -m integration
```

**Результат тестування:**
- ✅ Code style: PASSED
- ✅ Type checking: PASSED  
- ✅ Unit tests: 45/45 PASSED
- ✅ Coverage: 87%
- ⚠️ [При наявності проблем] Потребує виправлення

Чи хочете запустити додаткові тести або виправити знайдені проблеми?

## Варіанти тестування

**Тільки швидкі unit тести:**
```
test-unit
```

**Тестування конкретного модуля:**
```
test-module claude
```

**Інтеграційне тестування з реальним API:**
```
test-integration
```

**Ручне тестування функціональності:**
```
test-manual
```

**Навантажувальне тестування:**
```
test-load
```

**Тестування безпеки:**
```
test-security
```

## Claude Code відповідає на варіанти:

### test-unit:
```bash
# Швидкі unit тести без інтеграційних
poetry run pytest tests/unit/ -v --tb=short
```

### test-module claude:
```bash
# Тестування тільки Claude модуля
poetry run pytest tests/ -v -k "claude" --cov=src.claude
```

### test-integration:
```bash
# Тести з реальним API (потребують налаштування)
echo "Запускаю інтеграційні тести..."
poetry run pytest tests/integration/ -v -s --tb=long

# Тестування Claude API підключення
poetry run python -c "
from src.claude.facade import ClaudeIntegration
from src.config.settings import get_settings
settings = get_settings()
claude = ClaudeIntegration(settings)
result = claude.execute_command('echo test', session_id='test')
print(f'Claude API Test: {\"PASSED\" if result else \"FAILED\"}')
"
```

### test-manual:
Я створю інтерактивний діалог для ручного тестування основних функцій:

```python
# Створення тестового скрипту для ручного тестування
```

**Інструкції для ручного тестування:**
1. Відправте `/start` боту в Telegram
2. Спробуйте команду `/help`  
3. Виконайте простий запит: "напиши привіт світ"
4. Протестуйте загрузку файлу
5. Перевірте роботу quick actions

### test-load:
```bash
# Простий навантажувальний тест
echo "Запускаю навантажувальні тести..."

for i in {1..10}; do
  echo "Request $i"
  docker exec claude-code-bot python -c "
from src.bot.core import create_application
import asyncio
async def test():
    app = create_application()
    # Симуляція запиту
    print(f'Test {$i}: OK')
asyncio.run(test())
  " &
done

wait
echo "Навантажувальний тест завершено"
```

### test-security:
```bash
echo "=== Security Testing ==="

# Тест аутентифікації  
echo "1. Authentication test:"
python -c "
from src.security.auth import create_auth_provider
from src.config.settings import get_settings
provider = create_auth_provider(get_settings())
print(f'Auth configured: {provider is not None}')
"

# Тест rate limiting
echo "2. Rate limiting test:"
python -c "
from src.security.rate_limiter import RateLimiter
limiter = RateLimiter(requests_per_minute=10)
for i in range(15):
    allowed = limiter.is_request_allowed('test_user')
    if not allowed:
        print(f'Rate limit triggered at request {i}')
        break
"

# Тест валідації шляхів
echo "3. Path validation test:"
python -c "
from src.security.validators import PathValidator
validator = PathValidator(['/app/target_project'])
print(f'Safe path: {validator.is_safe_path(\"/app/target_project/test.py\")}')
print(f'Unsafe path: {validator.is_safe_path(\"/etc/passwd\")}')
"
```

## Автоматичне тестування CI/CD

**Користувач:**
```
setup-ci-testing  
```

**Claude Code створює GitHub Actions workflow:**
```yaml
# .github/workflows/test.yml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      - name: Install Poetry
        run: curl -sSL https://install.python-poetry.org | python3 -
      - name: Install dependencies  
        run: poetry install --with dev
      - name: Lint
        run: |
          poetry run black --check src/
          poetry run isort --check-only src/
          poetry run flake8 src/
      - name: Type check
        run: poetry run mypy src/
      - name: Test
        run: poetry run pytest --cov=src --cov-report=xml
      - name: Upload coverage
        uses: codecov/codecov-action@v3
```

## Тестування після деплою

**Користувач:**
```  
test-production
```

**Claude Code:**
```bash
echo "=== Production Testing ==="

# Healthcheck контейнера
echo "1. Container health:"
docker inspect claude-code-bot --format='{{.State.Health.Status}}'

# Тест API endpoints
echo "2. Telegram API test:"
docker exec claude-code-bot python -c "
import requests, os
token = os.getenv('TELEGRAM_BOT_TOKEN')
resp = requests.get(f'https://api.telegram.org/bot{token}/getMe')
print(f'Telegram API: {\"OK\" if resp.status_code == 200 else \"FAILED\"}')
"

# Тест Claude CLI
echo "3. Claude CLI test:"
docker exec claude-code-bot claude auth status

# Тест базових функцій
echo "4. Core functionality test:"
docker exec claude-code-bot python -c "
from src.main import create_bot_application
import asyncio
print('Bot initialization: OK')
"

# Моніторинг логів на помилки
echo "5. Error monitoring:"
docker-compose logs --since=5m claude_bot 2>&1 | grep -i error || echo "No errors found"
```

## Коли використовувати
- Перед кожним коммітом (test-unit)
- Перед деплоєм в продакшен (test-all)
- Після змін в критичних модулях (test-module)
- При підозрі на проблеми з безпекою (test-security)
- Після оновлення залежностей
- При налаштуванні нового середовища

## Метрики якості
- Code coverage > 80%
- Всі type hints валідні
- Відсутність critical security issues
- Час відповіді API < 2s
- Memory usage < 512MB
- Zero critical bugs в production