"""
Pytest configuration and fixtures for DevClaude_bot tests.

Implements comprehensive testing framework as recommended by Enhanced Architect Bot.
"""

import asyncio
import pytest
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, Mock
from typing import AsyncGenerator, Generator

from src.config.settings import Settings
from src.di import ApplicationContainer, initialize_di
from src.security.rbac import RBACManager, Permission
from src.security.auth import AuthenticationManager
from src.storage.facade import Storage
from src.claude.facade import ClaudeIntegration


@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for session."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def temp_dir() -> Generator[Path, None, None]:
    """Create temporary directory for tests."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def test_config(temp_dir: Path) -> Settings:
    """Create test configuration."""
    return Settings(
        # Bot settings
        bot_token="test_token",
        allowed_users=[123456789, 987654321],
        development_mode=True,

        # Database
        database_url=f"sqlite:///{temp_dir}/test.db",

        # Directory settings
        approved_directory=str(temp_dir),

        # Feature flags
        enable_localization=True,
        enable_image_processing=False,
        enable_token_auth=False,

        # Claude settings
        use_sdk=False,
        claude_session_timeout=300,

        # Security
        auth_token_secret="test_secret",
        security_flexible_mode=True,

        # Rate limiting
        rate_limit_requests=100,
        rate_limit_window=60,
    )


@pytest.fixture
async def storage(test_config: Settings) -> AsyncGenerator[Storage, None]:
    """Create test storage."""
    storage = Storage(test_config.database_url)
    await storage.initialize()
    yield storage
    await storage.close()


@pytest.fixture
def rbac_manager(storage: Storage) -> RBACManager:
    """Create test RBAC manager."""
    return RBACManager(storage=storage)


@pytest.fixture
async def auth_manager(test_config: Settings, rbac_manager: RBACManager) -> AsyncGenerator[AuthenticationManager, None]:
    """Create test authentication manager."""
    from src.security.auth import WhitelistAuthProvider

    providers = [
        WhitelistAuthProvider(test_config.allowed_users, allow_all_dev=True)
    ]
    auth_manager = AuthenticationManager(providers, rbac_manager=rbac_manager)
    yield auth_manager
    await auth_manager.cleanup()


@pytest.fixture
def mock_claude_integration() -> Mock:
    """Create mock Claude integration."""
    mock = Mock(spec=ClaudeIntegration)
    mock.is_available.return_value = True
    mock.execute_command = AsyncMock(return_value="Mock response")
    mock.health_check = AsyncMock(return_value=True)
    mock.shutdown = AsyncMock()
    return mock


@pytest.fixture
async def di_container(test_config: Settings) -> AsyncGenerator[ApplicationContainer, None]:
    """Create test DI container."""
    container = await initialize_di(test_config)
    yield container
    await container.shutdown()


@pytest.fixture
def mock_update():
    """Create mock Telegram update."""
    from unittest.mock import Mock

    update = Mock()
    update.effective_user.id = 123456789
    update.effective_user.username = "testuser"
    update.effective_user.language_code = "en"
    update.effective_chat.id = 123456789
    update.message.text = "/test"
    update.message.reply_text = AsyncMock()
    return update


@pytest.fixture
def mock_context():
    """Create mock Telegram context."""
    from unittest.mock import Mock

    context = Mock()
    context.args = []
    context.bot = Mock()
    return context


# Test user fixtures
@pytest.fixture
def test_user_id() -> int:
    """Test user ID."""
    return 123456789


@pytest.fixture
def test_admin_user_id() -> int:
    """Test admin user ID."""
    return 987654321


@pytest.fixture
async def authenticated_user(auth_manager: AuthenticationManager, test_user_id: int):
    """Create authenticated user session."""
    session = await auth_manager.authenticate(test_user_id)
    return session


@pytest.fixture
async def admin_user(auth_manager: AuthenticationManager, rbac_manager: RBACManager, test_admin_user_id: int):
    """Create admin user with permissions."""
    # Authenticate user
    session = await auth_manager.authenticate(test_admin_user_id)

    # Assign admin role
    await rbac_manager.assign_role(test_admin_user_id, "admin")

    return session


# Async test helpers
@pytest.fixture
def async_mock():
    """Create async mock helper."""
    def _async_mock(*args, **kwargs):
        return AsyncMock(*args, **kwargs)
    return _async_mock


# Test data fixtures
@pytest.fixture
def sample_permissions() -> list[Permission]:
    """Sample permissions for testing."""
    return [
        Permission.HELP,
        Permission.STATUS,
        Permission.LS,
        Permission.PWD,
        Permission.CLAUDE_BASIC,
    ]


@pytest.fixture
def test_file_content() -> str:
    """Sample file content for testing."""
    return """
# Test File
This is a test file for DevClaude_bot testing.

## Features
- File reading
- File writing
- Git operations
- Claude integration
"""


@pytest.fixture
def create_test_file(temp_dir: Path):
    """Helper to create test files."""
    def _create_file(filename: str, content: str = "test content") -> Path:
        file_path = temp_dir / filename
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text(content)
        return file_path
    return _create_file


# Error testing fixtures
@pytest.fixture
def mock_error():
    """Create mock error for testing."""
    from src.errors import DevClaudeError
    return DevClaudeError(
        message="Test error",
        error_code="TEST_ERROR",
        user_message="Test error occurred"
    )


# Performance testing fixtures
@pytest.fixture
def performance_timer():
    """Timer for performance testing."""
    import time

    class Timer:
        def __init__(self):
            self.start_time = None
            self.end_time = None

        def start(self):
            self.start_time = time.time()

        def stop(self):
            self.end_time = time.time()

        @property
        def elapsed(self):
            if self.start_time is None or self.end_time is None:
                return None
            return self.end_time - self.start_time

    return Timer()


# Database testing fixtures
@pytest.fixture
async def db_session(storage: Storage):
    """Database session for testing."""
    async with storage.db_manager.get_connection() as conn:
        yield conn


@pytest.fixture
def db_cleanup(storage: Storage):
    """Helper for database cleanup."""
    async def _cleanup():
        async with storage.db_manager.get_connection() as conn:
            # Clean up test data
            await conn.execute("DELETE FROM user_sessions")
            await conn.execute("DELETE FROM user_roles")
            await conn.execute("DELETE FROM audit_logs")
            await conn.commit()

    return _cleanup