"""Database connection and initialization.

Features:
- Connection pooling
- Automatic migrations
- Health checks
- Schema versioning
"""

import asyncio
from contextlib import asynccontextmanager
from pathlib import Path
from typing import AsyncIterator, List, Tuple

import aiosqlite
import structlog

logger = structlog.get_logger()

# Initial schema migration
INITIAL_SCHEMA = """
-- Core Tables

-- Users table
CREATE TABLE users (
    user_id INTEGER PRIMARY KEY,
    telegram_username TEXT,
    first_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_active TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    is_allowed BOOLEAN DEFAULT FALSE,
    total_cost REAL DEFAULT 0.0,
    message_count INTEGER DEFAULT 0,
    session_count INTEGER DEFAULT 0
);

-- Sessions table
CREATE TABLE sessions (
    session_id TEXT PRIMARY KEY,
    user_id INTEGER NOT NULL,
    project_path TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_used TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    total_cost REAL DEFAULT 0.0,
    total_turns INTEGER DEFAULT 0,
    message_count INTEGER DEFAULT 0,
    is_active BOOLEAN DEFAULT TRUE,
    FOREIGN KEY (user_id) REFERENCES users(user_id)
);

-- Messages table
CREATE TABLE messages (
    message_id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL,
    user_id INTEGER NOT NULL,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    prompt TEXT NOT NULL,
    response TEXT,
    cost REAL DEFAULT 0.0,
    duration_ms INTEGER,
    error TEXT,
    FOREIGN KEY (session_id) REFERENCES sessions(session_id),
    FOREIGN KEY (user_id) REFERENCES users(user_id)
);

-- Tool usage table
CREATE TABLE tool_usage (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL,
    message_id INTEGER,
    tool_name TEXT NOT NULL,
    tool_input JSON,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    success BOOLEAN DEFAULT TRUE,
    error_message TEXT,
    FOREIGN KEY (session_id) REFERENCES sessions(session_id),
    FOREIGN KEY (message_id) REFERENCES messages(message_id)
);

-- Audit log table
CREATE TABLE audit_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    event_type TEXT NOT NULL,
    event_data JSON,
    success BOOLEAN DEFAULT TRUE,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    ip_address TEXT,
    FOREIGN KEY (user_id) REFERENCES users(user_id)
);

-- User tokens table (for token auth)
CREATE TABLE user_tokens (
    token_id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    token_hash TEXT NOT NULL UNIQUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP,
    last_used TIMESTAMP,
    is_active BOOLEAN DEFAULT TRUE,
    FOREIGN KEY (user_id) REFERENCES users(user_id)
);

-- Cost tracking table
CREATE TABLE cost_tracking (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    date DATE NOT NULL,
    daily_cost REAL DEFAULT 0.0,
    request_count INTEGER DEFAULT 0,
    UNIQUE(user_id, date),
    FOREIGN KEY (user_id) REFERENCES users(user_id)
);

-- Context entries table for persistent conversation memory
CREATE TABLE context_entries (
    entry_id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    project_path TEXT NOT NULL,
    content TEXT NOT NULL,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    session_id TEXT NOT NULL,
    message_type TEXT NOT NULL CHECK(message_type IN ('user', 'assistant', 'system', 'summary')),
    importance INTEGER DEFAULT 2 CHECK(importance IN (1, 2, 3)),
    metadata JSON,
    FOREIGN KEY (user_id) REFERENCES users(user_id),
    FOREIGN KEY (session_id) REFERENCES sessions(session_id)
);

-- Indexes for performance
CREATE INDEX idx_sessions_user_id ON sessions(user_id);
CREATE INDEX idx_sessions_project_path ON sessions(project_path);
CREATE INDEX idx_messages_session_id ON messages(session_id);
CREATE INDEX idx_messages_timestamp ON messages(timestamp);
CREATE INDEX idx_audit_log_user_id ON audit_log(user_id);
CREATE INDEX idx_audit_log_timestamp ON audit_log(timestamp);
CREATE INDEX idx_cost_tracking_user_date ON cost_tracking(user_id, date);
CREATE INDEX idx_context_entries_user_project ON context_entries(user_id, project_path);
CREATE INDEX idx_context_entries_timestamp ON context_entries(timestamp);
CREATE INDEX idx_context_entries_importance ON context_entries(importance);
CREATE INDEX idx_context_entries_content ON context_entries(content);
"""


class DatabaseManager:
    """Manage database connections and initialization."""

    def __init__(self, database_url: str):
        """Initialize database manager."""
        self.database_path = self._parse_database_url(database_url)
        self._connection_pool = []
        self._pool_size = 5
        self._pool_lock = asyncio.Lock()

    def _parse_database_url(self, database_url: str) -> Path:
        """Parse database URL to path."""
        if database_url.startswith("sqlite:///"):
            return Path(database_url[10:])
        elif database_url.startswith("sqlite://"):
            return Path(database_url[9:])
        else:
            return Path(database_url)

    async def initialize(self):
        """Initialize database and run migrations."""
        logger.info("Initializing database", path=str(self.database_path))

        # Ensure directory exists
        self.database_path.parent.mkdir(parents=True, exist_ok=True)

        # Run migrations
        await self._run_migrations()

        # Initialize connection pool
        await self._init_pool()

        logger.info("Database initialization complete")

    async def _run_migrations(self):
        """Run database migrations."""
        async with aiosqlite.connect(self.database_path) as conn:
            conn.row_factory = aiosqlite.Row

            # Enable foreign keys
            await conn.execute("PRAGMA foreign_keys = ON")

            # Get current version
            current_version = await self._get_schema_version(conn)
            logger.info("Current schema version", version=current_version)

            # Run migrations
            migrations = self._get_migrations()
            for version, migration in migrations:
                if version > current_version:
                    logger.info("Running migration", version=version)
                    await conn.executescript(migration)
                    await self._set_schema_version(conn, version)

            await conn.commit()

    async def _get_schema_version(self, conn: aiosqlite.Connection) -> int:
        """Get current schema version."""
        await conn.execute(
            """
            CREATE TABLE IF NOT EXISTS schema_version (
                version INTEGER PRIMARY KEY
            )
        """
        )

        cursor = await conn.execute("SELECT MAX(version) FROM schema_version")
        row = await cursor.fetchone()
        return row[0] if row and row[0] else 0

    async def _set_schema_version(self, conn: aiosqlite.Connection, version: int):
        """Set schema version."""
        await conn.execute(
            "INSERT INTO schema_version (version) VALUES (?)", (version,)
        )

    def _get_migrations(self) -> List[Tuple[int, str]]:
        """Get migration scripts."""
        return [
            (1, INITIAL_SCHEMA),
            (
                2,
                """
                -- Add MCP Management System
                CREATE TABLE IF NOT EXISTS mcp_server_templates (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    server_type TEXT UNIQUE NOT NULL,
                    display_name TEXT NOT NULL,
                    description TEXT,
                    command_template TEXT NOT NULL,
                    args_template TEXT,
                    env_template TEXT,
                    config_schema TEXT,
                    setup_instructions TEXT,
                    is_active BOOLEAN DEFAULT 1,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );

                CREATE TABLE IF NOT EXISTS user_mcp_servers (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    server_name TEXT NOT NULL,
                    server_type TEXT NOT NULL,
                    server_command TEXT NOT NULL,
                    server_args TEXT,
                    server_env TEXT,
                    config TEXT,
                    is_active BOOLEAN DEFAULT 1,
                    is_enabled BOOLEAN DEFAULT 1,
                    status TEXT DEFAULT 'inactive',
                    last_used TIMESTAMP,
                    last_status_check TIMESTAMP,
                    error_message TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(user_id, server_name),
                    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
                );

                CREATE TABLE IF NOT EXISTS user_active_context (
                    user_id INTEGER PRIMARY KEY,
                    selected_server TEXT,
                    context_settings TEXT,
                    selected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
                );

                CREATE TABLE IF NOT EXISTS mcp_usage_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    server_name TEXT,
                    query TEXT,
                    response_time INTEGER,
                    success BOOLEAN,
                    error_message TEXT,
                    cost REAL DEFAULT 0.0,
                    session_id TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
                );

                CREATE INDEX IF NOT EXISTS idx_user_mcp_servers_user_id ON user_mcp_servers(user_id);
                CREATE INDEX IF NOT EXISTS idx_user_mcp_servers_status ON user_mcp_servers(status);
                CREATE INDEX IF NOT EXISTS idx_user_mcp_servers_type ON user_mcp_servers(server_type);
                CREATE INDEX IF NOT EXISTS idx_mcp_usage_log_user_id ON mcp_usage_log(user_id);
                CREATE INDEX IF NOT EXISTS idx_mcp_usage_log_created_at ON mcp_usage_log(created_at);

                INSERT OR IGNORE INTO mcp_server_templates (server_type, display_name, description, command_template, args_template, env_template, config_schema, setup_instructions) VALUES
                ('github', 'GitHub Integration', 'Доступ до GitHub репозиторіїв, issues, pull requests та іншого', 'npx', '["-y", "@modelcontextprotocol/server-github"]', '{"GITHUB_PERSONAL_ACCESS_TOKEN": "${input:github_token}"}', '{"type": "object", "properties": {"github_token": {"type": "string", "description": "GitHub Personal Access Token", "required": true}}}', '1. Перейдіть до GitHub Settings > Developer settings > Personal access tokens\n2. Створіть новий токен з доступом до репозиторіїв\n3. Скопіюйте токен'),
                ('filesystem', 'File System Access', 'Читання та запис файлів у вказаних директоріях', 'npx', '["-y", "@modelcontextprotocol/server-filesystem", "${config:allowed_path}"]', '{}', '{"type": "object", "properties": {"allowed_path": {"type": "string", "description": "Шлях до дозволеної директорії", "required": true}}}', 'Вкажіть повний шлях до директорії, де Claude може читати/писати файли'),
                ('postgres', 'PostgreSQL Database', 'Запити та управління PostgreSQL базами даних', 'npx', '["-y", "@modelcontextprotocol/server-postgres", "${config:connection_string}"]', '{}', '{"type": "object", "properties": {"connection_string": {"type": "string", "description": "Рядок підключення PostgreSQL", "required": true}}}', 'Формат: postgresql://username:password@host:port/database'),
                ('sqlite', 'SQLite Database', 'Запити та управління SQLite базами даних', 'npx', '["-y", "@modelcontextprotocol/server-sqlite", "${config:database_path}"]', '{}', '{"type": "object", "properties": {"database_path": {"type": "string", "description": "Шлях до файлу SQLite бази даних", "required": true}}}', 'Вкажіть повний шлях до файлу вашої SQLite бази даних'),
                ('git', 'Git Repository Tools', 'Git операції та управління репозиторіями', 'uvx', '["mcp-server-git", "--repository", "${config:repo_path}"]', '{}', '{"type": "object", "properties": {"repo_path": {"type": "string", "description": "Шлях до git репозиторію", "required": true}}}', 'Вкажіть шлях до вашого git репозиторію'),
                ('playwright', 'Web Automation', 'Автоматизація браузера та веб-скрапінг', 'npx', '["-y", "@modelcontextprotocol/server-playwright"]', '{}', '{"type": "object", "properties": {}}', 'Додаткова конфігурація не потрібна');
                """
            ),
            (
                3,
                """
                -- Add analytics views
                CREATE VIEW IF NOT EXISTS daily_stats AS
                SELECT 
                    date(timestamp) as date,
                    COUNT(DISTINCT user_id) as active_users,
                    COUNT(*) as total_messages,
                    SUM(cost) as total_cost,
                    AVG(duration_ms) as avg_duration
                FROM messages
                GROUP BY date(timestamp);

                CREATE VIEW IF NOT EXISTS user_stats AS
                SELECT 
                    u.user_id,
                    u.telegram_username,
                    COUNT(DISTINCT s.session_id) as total_sessions,
                    COUNT(m.message_id) as total_messages,
                    SUM(m.cost) as total_cost,
                    MAX(m.timestamp) as last_activity
                FROM users u
                LEFT JOIN sessions s ON u.user_id = s.user_id
                LEFT JOIN messages m ON u.user_id = m.user_id
                GROUP BY u.user_id;
                """,
            ),
            (
                4,
                """
                -- Add image processing tables
                CREATE TABLE IF NOT EXISTS image_uploads (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    session_id TEXT,
                    message_id INTEGER,
                    filename TEXT NOT NULL,
                    original_filename TEXT,
                    file_size INTEGER NOT NULL,
                    format TEXT NOT NULL,
                    width INTEGER NOT NULL,
                    height INTEGER NOT NULL,
                    file_hash TEXT NOT NULL,
                    caption TEXT,
                    uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    processed_at TIMESTAMP,
                    processing_status TEXT DEFAULT 'uploaded',
                    processing_error TEXT,
                    metadata TEXT,
                    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE,
                    FOREIGN KEY (session_id) REFERENCES sessions(session_id) ON DELETE SET NULL,
                    FOREIGN KEY (message_id) REFERENCES messages(message_id) ON DELETE SET NULL
                );

                CREATE TABLE IF NOT EXISTS image_sessions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT UNIQUE NOT NULL,
                    user_id INTEGER NOT NULL,
                    instruction TEXT,
                    status TEXT DEFAULT 'active',
                    images_count INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    expires_at TIMESTAMP,
                    completed_at TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
                );

                -- Indexes for performance
                CREATE INDEX IF NOT EXISTS idx_image_uploads_user_id ON image_uploads(user_id);
                CREATE INDEX IF NOT EXISTS idx_image_uploads_session_id ON image_uploads(session_id);  
                CREATE INDEX IF NOT EXISTS idx_image_uploads_hash ON image_uploads(file_hash);
                CREATE INDEX IF NOT EXISTS idx_image_uploads_status ON image_uploads(processing_status);
                CREATE INDEX IF NOT EXISTS idx_image_sessions_user_id ON image_sessions(user_id);
                CREATE INDEX IF NOT EXISTS idx_image_sessions_status ON image_sessions(status);
                CREATE INDEX IF NOT EXISTS idx_image_sessions_expires_at ON image_sessions(expires_at);
                """,
            ),
        ]

    async def _init_pool(self):
        """Initialize connection pool."""
        logger.info("Initializing connection pool", size=self._pool_size)

        async with self._pool_lock:
            for _ in range(self._pool_size):
                conn = await aiosqlite.connect(self.database_path)
                conn.row_factory = aiosqlite.Row
                await conn.execute("PRAGMA foreign_keys = ON")
                self._connection_pool.append(conn)

    @asynccontextmanager
    async def get_connection(self) -> AsyncIterator[aiosqlite.Connection]:
        """Get database connection from pool."""
        async with self._pool_lock:
            if self._connection_pool:
                conn = self._connection_pool.pop()
            else:
                conn = await aiosqlite.connect(self.database_path)
                conn.row_factory = aiosqlite.Row
                await conn.execute("PRAGMA foreign_keys = ON")

        try:
            yield conn
        finally:
            async with self._pool_lock:
                if len(self._connection_pool) < self._pool_size:
                    self._connection_pool.append(conn)
                else:
                    await conn.close()

    async def close(self):
        """Close all connections in pool."""
        logger.info("Closing database connections")

        async with self._pool_lock:
            for conn in self._connection_pool:
                await conn.close()
            self._connection_pool.clear()

    async def health_check(self) -> bool:
        """Check database health."""
        try:
            async with self.get_connection() as conn:
                await conn.execute("SELECT 1")
                return True
        except Exception as e:
            logger.error("Database health check failed", error=str(e))
            return False
