# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a Claude Code Telegram Bot that provides remote access to Claude CLI functionality via Telegram. The bot includes comprehensive features like session management, security controls, rate limiting, and availability monitoring.

## Development Commands

### Using Poetry (Primary)

```bash
# Install dependencies
poetry install

# Install development dependencies
poetry install --with dev

# Run the bot
poetry run python -m src.main

# Run with debug logging
poetry run python -m src.main --debug

# Run tests
poetry run pytest

# Code formatting and linting
poetry run black src/
poetry run isort src/
poetry run flake8 src/
poetry run mypy src/

# Type checking with verbose output
poetry run mypy --show-error-codes --pretty src/
```

### Using Docker (Recommended for Production)

```bash
# Build and start the container
docker-compose up -d --build

# View logs
docker-compose logs -f claude_bot

# Stop the container
docker-compose down

# Rebuild and restart
docker-compose up -d --build
```

## Architecture Overview

### Core Components

The application follows a layered architecture with clear separation of concerns:

**Main Entry Point** (`src/main.py`):
- Application initialization and dependency injection
- Graceful shutdown handling
- Structured logging setup

**Bot Layer** (`src/bot/`):
- `core.py`: Main bot orchestrator with handler registration
- `handlers/`: Command handlers, message handlers, callback handlers
- `middleware/`: Authentication, rate limiting, security validation
- `features/`: Modular features like availability monitoring, git integration
- `ui/`: Enhanced UI components (navigation, progress indicators)
- `integration/`: Integration layer for enhanced modules
- `utils/`: Enhanced utilities (error handling)

**Claude Integration Layer** (`src/claude/`):
- `facade.py`: High-level integration facade with tool validation
- `integration.py`: Process management and command execution
- `sdk_integration.py`: Claude Python SDK integration
- `session.py`: Session management and persistence
- `monitor.py`: Tool usage monitoring and validation

**Storage Layer** (`src/storage/`):
- `facade.py`: Unified storage interface
- `database.py`: SQLite database management
- `repositories/`: Data access objects for different entities
- `models/`: Pydantic models for database entities

**Security Layer** (`src/security/`):
- `auth.py`: Authentication providers (whitelist, token-based)
- `rate_limiter.py`: Token bucket rate limiting
- `validators.py`: Security validation for file paths and commands
- `audit.py`: Security event logging

**Configuration** (`src/config/`):
- `settings.py`: Pydantic settings with environment variable loading
- `loader.py`: Configuration loading and validation
- `features.py`: Feature flag management

**Enhanced Features** (`src/locales/`, `src/localization/`):
- `locales/`: Translation files for multiple languages (UA/EN)
- `localization/i18n.py`: Dynamic localization system
- `ui/navigation.py`: Advanced navigation with breadcrumbs and grouping
- `ui/progress.py`: Visual progress indicators for long operations
- `utils/error_handler.py`: Centralized error handling with user-friendly messages

### Key Design Patterns

**Dependency Injection**: All components receive their dependencies through constructor injection, managed in `src/main.py`.

**Facade Pattern**: `ClaudeIntegration` provides a simplified interface to the complex Claude CLI/SDK subsystem.

**Repository Pattern**: Data access is abstracted through repository classes in `src/storage/repositories/`.

**Strategy Pattern**: Multiple authentication providers can be configured and used interchangeably.

**Observer Pattern**: Tool monitoring system validates and tracks tool usage across the application.

### Session Management

Sessions are managed with the following characteristics:
- Persistent storage in SQLite database
- Automatic cleanup of expired sessions
- Support for both CLI subprocess and SDK execution modes
- Tool usage tracking and validation per session
- Cost tracking and user quota management

### Security Model

Multi-layered security approach:
1. **Authentication**: User whitelist or token-based authentication
2. **Authorization**: Per-tool access control with configurable allowed/disallowed lists  
3. **Path Validation**: Restricts file operations to approved directories
4. **Rate Limiting**: Token bucket algorithm with configurable limits
5. **Audit Logging**: Comprehensive logging of all security events

## Configuration

### Environment Variables (.env)

Critical settings that must be configured:

```bash
# Required
TELEGRAM_BOT_TOKEN=your_bot_token_here
TELEGRAM_BOT_USERNAME=your_bot_username
APPROVED_DIRECTORY=/app/target_project

# Security (choose one or both)
ALLOWED_USERS=123456789,987654321  # Telegram user IDs
ENABLE_TOKEN_AUTH=true
AUTH_TOKEN_SECRET=your_secret_here

# Claude settings
USE_SDK=true  # Use Python SDK instead of CLI subprocess
ANTHROPIC_API_KEY=your_api_key  # Optional if logged into Claude CLI
CLAUDE_MODEL=claude-3-5-sonnet-20241022

# Availability monitoring
CLAUDE_AVAILABILITY_MONITOR=true
CLAUDE_AVAILABILITY_NOTIFY_CHAT_IDS=-1001234567890
CLAUDE_AVAILABILITY_CHECK_INTERVAL=60

# Target project path
TARGET_PROJECT_PATH=/app/target_project
```

### Tool Configuration

Claude tool access is controlled via:
- `CLAUDE_ALLOWED_TOOLS`: Comma-separated list of allowed tools
- `CLAUDE_DISALLOWED_TOOLS`: Explicit tool/command blacklist
- Default allowed tools include: Read, Write, Edit, Bash, Glob, Grep, etc.

## Special Features

### Claude Availability Monitoring

The bot includes sophisticated monitoring of Claude CLI availability:
- Periodic health checks with configurable intervals
- Rate limit detection and recovery tracking
- DND (Do Not Disturb) time windows
- Telegram notifications with detailed status information
- Persistent state tracking in JSON files

### Dual Execution Modes

The application supports both execution modes with automatic fallback:
1. **Claude Python SDK**: Primary mode for better integration
2. **CLI Subprocess**: Fallback mode for compatibility
3. **Adaptive Fallback**: Automatically switches on JSON decode errors

### Volume Mounting for Target Projects

The Docker setup includes volume mounting for target projects:
- Host directory `./target_project` maps to `/app/target_project` in container
- Allows Claude CLI to operate on external codebases
- Enables real-time file synchronization between host and container

## Testing

Run the test suite:
```bash
poetry run pytest
poetry run pytest --cov=src --cov-report=html
```

## Debugging

Enable debug mode for detailed logging:
```bash
poetry run python -m src.main --debug
```

## Claude CLI Authentication Transfer

### Transferring Auth from Host to Container

When Claude CLI authentication expires in the container, you can transfer working credentials from the host:

```bash
# 1. Create archive of working Claude auth files from host
tar -czf claude-auth-latest.tar.gz -C /home/vokov .claude

# 2. Copy auth archive to Docker container
docker cp claude-auth-latest.tar.gz claude-code-bot:/tmp/claude-auth.tar.gz

# 3. Extract auth files in container home directory
docker exec claude-code-bot bash -c "cd /home/claudebot && tar -xzf /tmp/claude-auth.tar.gz"

# 4. Verify authentication works
docker exec claude-code-bot bash -c "claude --version"

# 5. Rebuild and restart system
docker compose down
docker compose up -d --build
```

### ВАЖЛИВО: Тільки метод архівування

**НЕ використовуємо SDK mode!** Тільки архівування `.claude` налаштувань з хосту:

1. Завжди `USE_SDK=false` в `.env`
2. Тільки архівуємо та розархівовуємо `.claude` директорію з хосту
3. Ніяких API ключів або SDK режимів не потрібно

Система працює ТІЛЬКИ через архівування робочих Claude CLI налаштувань.

## Common Development Workflows

1. **Adding new bot commands**: Add handler in `src/bot/handlers/command.py` and register in `src/bot/core.py`
2. **Adding new middleware**: Create in `src/bot/middleware/` and register in `core.py`  
3. **Extending Claude integration**: Modify `src/claude/facade.py` for high-level changes
4. **Adding new security providers**: Implement in `src/security/auth.py`
5. **Database schema changes**: Modify models in `src/storage/models.py`