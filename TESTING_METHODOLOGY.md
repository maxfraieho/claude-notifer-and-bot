# Методика тестування DevClaude Bot v2.1

## Огляд тестової архітектури

Ця методика покриває комплексне тестування enterprise-grade архітектури DevClaude Bot з:
- Dependency Injection (DI) Container
- Role-Based Access Control (RBAC)
- Enhanced Error Handling
- Багаторівневі тести: Unit → Integration → E2E

## 1. Структура тестів

```
tests/
├── conftest.py                    # Глобальні фікстури та конфігурація
├── unit/                          # Модульні тести
│   ├── test_di_container.py       # Тести DI контейнера
│   ├── test_rbac.py               # Тести RBAC системи
│   ├── test_errors.py             # Тести обробки помилок
│   ├── test_auth.py               # Тести аутентифікації
│   └── test_security.py           # Тести безпеки
├── integration/                   # Інтеграційні тести
│   ├── test_bot_integration.py    # Тести інтеграції бота
│   ├── test_claude_integration.py # Тести інтеграції з Claude
│   └── test_storage_integration.py# Тести інтеграції сховища
└── e2e/                          # End-to-end тести
    ├── test_user_workflows.py     # Тести користувацьких сценаріїв
    └── test_admin_workflows.py    # Тести адміністративних сценаріїв
```

## 2. Запуск тестів

### Базові команди
```bash
# Всі тести
pytest

# Модульні тести
pytest tests/unit/

# Інтеграційні тести
pytest tests/integration/

# E2E тести
pytest tests/e2e/

# З покриттям коду
pytest --cov=src --cov-report=html

# Детальний вивід
pytest -v -s

# Конкретний тест
pytest tests/unit/test_rbac.py::test_permission_hierarchy
```

### Тестування за категоріями
```bash
# RBAC тести
pytest -k "rbac"

# DI Container тести
pytest -k "di_container"

# Error Handling тести
pytest -k "error"

# Security тести
pytest -k "security"
```

## 3. Тестові фікстури

### Основні фікстури (conftest.py)

```python
@pytest.fixture
async def test_config():
    """Тестова конфігурація"""
    return Settings(
        telegram_token="test_token",
        development_mode=True,
        allowed_users=[12345, 67890],
        enable_rbac=True,
        database_url="sqlite:///test.db"
    )

@pytest.fixture
async def di_container(test_config):
    """DI контейнер для тестів"""
    container = ApplicationContainer()
    await container.initialize(test_config)
    yield container
    await container.shutdown()

@pytest.fixture
async def rbac_manager(di_container):
    """RBAC менеджер"""
    return di_container.get("rbac_manager")

@pytest.fixture
async def auth_manager(di_container):
    """Authentication менеджер"""
    return di_container.get("auth_manager")
```

## 4. Тестування RBAC системи

### Модульні RBAC тести

```python
class TestRBAC:
    async def test_permission_hierarchy(self, rbac_manager):
        """Тест ієрархії дозволів"""
        user_id = 12345

        # Призначаємо роль user
        await rbac_manager.assign_role(user_id, "user")

        # Перевіряємо базові дозволи
        assert rbac_manager.has_permission(user_id, Permission.BASIC_ACCESS)
        assert rbac_manager.has_permission(user_id, Permission.SEND_MESSAGE)

        # Перевіряємо відсутність admin дозволів
        assert not rbac_manager.has_permission(user_id, Permission.MANAGE_USERS)

    async def test_role_inheritance(self, rbac_manager):
        """Тест успадкування ролей"""
        user_id = 67890

        # Призначаємо роль developer
        await rbac_manager.assign_role(user_id, "developer")

        # Повинен мати дозволи user + developer
        assert rbac_manager.has_permission(user_id, Permission.BASIC_ACCESS)  # user
        assert rbac_manager.has_permission(user_id, Permission.EXECUTE_CODE)  # developer

        # Не повинен мати admin дозволи
        assert not rbac_manager.has_permission(user_id, Permission.SYSTEM_ADMIN)

    async def test_permission_caching(self, rbac_manager):
        """Тест кешування дозволів"""
        user_id = 11111

        # Призначаємо роль та перевіряємо кешування
        await rbac_manager.assign_role(user_id, "user")

        # Перший виклик - створює кеш
        result1 = rbac_manager.has_permission(user_id, Permission.BASIC_ACCESS)

        # Другий виклик - використовує кеш
        result2 = rbac_manager.has_permission(user_id, Permission.BASIC_ACCESS)

        assert result1 == result2 == True
```

### Інтеграційні RBAC тести

```python
class TestRBACIntegration:
    async def test_auth_rbac_integration(self, auth_manager, rbac_manager):
        """Тест інтеграції аутентифікації з RBAC"""
        user_id = 12345

        # Аутентифікуємо користувача
        session = await auth_manager.authenticate(user_id)
        assert session is not None

        # Перевіряємо автоматичне призначення ролі
        user_roles = rbac_manager.get_user_roles(user_id)
        assert len(user_roles) > 0
        assert any(ur.role_name == "user" for ur in user_roles)

    async def test_session_permissions(self, auth_manager):
        """Тест дозволів через сесію"""
        user_id = 12345

        session = await auth_manager.authenticate(user_id)

        # Тестуємо методи сесії
        assert session.has_permission(Permission.BASIC_ACCESS)
        assert session.check_permission(Permission.SEND_MESSAGE)

        roles = session.get_roles()
        assert "user" in roles
```

## 5. Тестування DI Container

### Модульні тести DI

```python
class TestDIContainer:
    def test_value_provider(self):
        """Тест ValueProvider"""
        container = DIContainer()
        test_value = "test_config"

        container.value("config", test_value)
        assert container.get("config") == test_value

    def test_factory_provider(self):
        """Тест FactoryProvider"""
        container = DIContainer()

        def create_service():
            return {"type": "service"}

        container.factory("service", create_service)

        # Кожен виклик створює новий екземпляр
        service1 = container.get("service")
        service2 = container.get("service")

        assert service1 == service2  # За змістом однакові
        assert service1 is not service2  # Але різні об'єкти

    def test_singleton_provider(self):
        """Тест SingletonProvider"""
        container = DIContainer()

        def create_singleton():
            return {"id": id(object())}

        container.singleton("singleton", create_singleton)

        # Повинен повертати той самий екземпляр
        obj1 = container.get("singleton")
        obj2 = container.get("singleton")

        assert obj1 is obj2

    def test_dependency_resolution(self):
        """Тест розв'язання залежностей"""
        container = DIContainer()

        # Базова залежність
        container.value("config", {"db_url": "test://db"})

        # Сервіс, що залежить від config
        def create_db_service():
            config = container.get("config")
            return {"connection": config["db_url"]}

        container.factory("db_service", create_db_service)

        service = container.get("db_service")
        assert service["connection"] == "test://db"
```

### Інтеграційні тести DI

```python
class TestDIIntegration:
    async def test_full_application_wiring(self, di_container):
        """Тест повного підключення залежностей"""
        # Перевіряємо, що всі основні компоненти зареєстровані
        assert di_container.has("storage")
        assert di_container.has("auth_manager")
        assert di_container.has("rbac_manager")
        assert di_container.has("claude_integration")
        assert di_container.has("bot")

    async def test_dependency_chain(self, di_container):
        """Тест ланцюга залежностей"""
        # Отримуємо бота (вершина ланцюга)
        bot = di_container.get("bot")
        assert bot is not None

        # Перевіряємо, що всі залежності правильно ін'єктовані
        auth_manager = di_container.get("auth_manager")
        assert auth_manager is not None

        # Перевіряємо, що RBAC підключений до auth
        rbac_manager = di_container.get("rbac_manager")
        assert rbac_manager is not None
```

## 6. Тестування Error Handling

### Модульні тести помилок

```python
class TestErrorHandling:
    async def test_retry_decorator(self):
        """Тест декоратора повторів"""
        call_count = 0

        @retry_on_failure(max_retries=3, delay=0.1)
        async def failing_function():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise DevClaudeError("Temporary failure")
            return "success"

        result = await failing_function()
        assert result == "success"
        assert call_count == 3

    async def test_fallback_decorator(self):
        """Тест декоратора fallback"""
        @with_fallback(fallback_value="fallback_result")
        async def failing_function():
            raise DevClaudeError("Always fails")

        result = await failing_function()
        assert result == "fallback_result"

    async def test_error_context_manager(self):
        """Тест контекстного менеджера помилок"""
        context = ErrorContextManager()

        with context.operation("test_operation"):
            context.add_context("user_id", 12345)
            context.add_context("action", "test_action")

        assert context.get_context("user_id") == 12345
        assert context.get_context("action") == "test_action"
```

### Інтеграційні тести помилок

```python
class TestErrorIntegration:
    async def test_auth_error_handling(self, auth_manager):
        """Тест обробки помилок аутентифікації"""
        # Тест з неіснуючим користувачем
        session = await auth_manager.authenticate(99999)
        assert session is None

    async def test_rbac_error_handling(self, rbac_manager):
        """Тест обробки помилок RBAC"""
        user_id = 12345

        # Тест з неіснуючою роллю
        with pytest.raises(SecurityError):
            await rbac_manager.assign_role(user_id, "nonexistent_role")
```

## 7. E2E тестування

### Користувацькі сценарії

```python
class TestUserWorkflows:
    async def test_new_user_registration_flow(self, di_container):
        """Тест реєстрації нового користувача"""
        user_id = 99999
        auth_manager = di_container.get("auth_manager")
        rbac_manager = di_container.get("rbac_manager")

        # 1. Аутентифікація нового користувача
        session = await auth_manager.authenticate(user_id)
        assert session is not None

        # 2. Автоматичне призначення базової ролі
        user_roles = rbac_manager.get_user_roles(user_id)
        assert len(user_roles) > 0

        # 3. Перевірка базових дозволів
        assert session.has_permission(Permission.BASIC_ACCESS)
        assert session.has_permission(Permission.SEND_MESSAGE)

    async def test_user_session_lifecycle(self, di_container):
        """Тест життєвого циклу сесії користувача"""
        user_id = 12345
        auth_manager = di_container.get("auth_manager")

        # 1. Створення сесії
        session = await auth_manager.authenticate(user_id)
        assert auth_manager.is_authenticated(user_id)

        # 2. Оновлення активності
        assert auth_manager.refresh_session(user_id)

        # 3. Завершення сесії
        auth_manager.end_session(user_id)
        assert not auth_manager.is_authenticated(user_id)
```

### Адміністративні сценарії

```python
class TestAdminWorkflows:
    async def test_role_management_workflow(self, di_container):
        """Тест управління ролями"""
        rbac_manager = di_container.get("rbac_manager")
        user_id = 12345
        admin_id = 67890

        # 1. Призначення admin ролі
        await rbac_manager.assign_role(admin_id, "admin")

        # 2. Admin змінює роль користувача
        await rbac_manager.assign_role(user_id, "developer")

        # 3. Перевірка змін
        user_roles = rbac_manager.get_user_roles(user_id)
        assert any(ur.role_name == "developer" for ur in user_roles)

    async def test_system_monitoring_workflow(self, di_container):
        """Тест моніторингу системи"""
        auth_manager = di_container.get("auth_manager")

        # 1. Створення кількох сесій
        for user_id in [111, 222, 333]:
            await auth_manager.authenticate(user_id)

        # 2. Перевірка активних сесій
        active_count = auth_manager.get_active_sessions_count()
        assert active_count == 3

        # 3. Очистка сесій
        await auth_manager.cleanup()
```

## 8. Тестування продуктивності

### Навантажувальні тести

```python
class TestPerformance:
    async def test_rbac_performance(self, rbac_manager):
        """Тест продуктивності RBAC"""
        import time

        user_id = 12345
        await rbac_manager.assign_role(user_id, "user")

        # Тест швидкості перевірки дозволів
        start_time = time.time()

        for _ in range(1000):
            rbac_manager.has_permission(user_id, Permission.BASIC_ACCESS)

        elapsed = time.time() - start_time
        assert elapsed < 1.0  # Має виконуватися менше ніж за секунду

    async def test_di_container_performance(self, di_container):
        """Тест продуктивності DI контейнера"""
        import time

        start_time = time.time()

        for _ in range(100):
            storage = di_container.get("storage")
            auth_manager = di_container.get("auth_manager")
            rbac_manager = di_container.get("rbac_manager")

        elapsed = time.time() - start_time
        assert elapsed < 0.5  # Має виконуватися менше ніж за 0.5 секунди
```

## 9. Тестові звіти та метрики

### Покриття коду
```bash
# Генерація HTML звіту
pytest --cov=src --cov-report=html --cov-report=term

# Мінімальне покриття (90%)
pytest --cov=src --cov-fail-under=90
```

### Метрики якості
- **Unit Tests Coverage**: ≥ 95%
- **Integration Tests Coverage**: ≥ 85%
- **RBAC System Coverage**: 100%
- **Error Handling Coverage**: 100%
- **DI Container Coverage**: 100%

## 10. Continuous Integration

### GitHub Actions конфігурація

```yaml
name: Tests
on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: [3.10, 3.11, 3.12]

    steps:
    - uses: actions/checkout@v4
    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: ${{ matrix.python-version }}

    - name: Install dependencies
      run: |
        pip install poetry
        poetry install

    - name: Run tests
      run: |
        poetry run pytest --cov=src --cov-report=xml

    - name: Upload coverage
      uses: codecov/codecov-action@v3
```

## 11. Налагодження тестів

### Корисні команди
```bash
# Запуск з детальним виводом
pytest -v -s --tb=long

# Запуск конкретного тесту з налагодженням
pytest -v -s tests/unit/test_rbac.py::test_permission_hierarchy --pdb

# Профілювання тестів
pytest --profile

# Параралельний запуск
pytest -n auto
```

### Логування в тестах
```python
import structlog
logger = structlog.get_logger(__name__)

def test_with_logging():
    logger.info("Starting test", test_name="example")
    # тест код...
    logger.info("Test completed successfully")
```

## Висновок

Ця методика забезпечує:
- ✅ Комплексне покриття всіх компонентів
- ✅ Автоматизоване тестування в CI/CD
- ✅ Метрики якості та покриття
- ✅ Тестування продуктивності
- ✅ E2E сценарії користувачів
- ✅ Простоту налагодження та підтримки

Використовуйте цю методику для забезпечення високої якості та надійності DevClaude Bot v2.1 enterprise architecture.