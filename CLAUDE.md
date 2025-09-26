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

**Localization System** (`src/localization/`):
- `i18n.py`: Core localization engine with fallback handling and **kwargs support
- `wrapper.py`: Thread-safe TTL cache for user locale preferences
- `storage.py`: User language preference persistence
- `translations/`: JSON translation files (uk.json, en.json)

**Enhanced Features** (`src/ui/`, `src/utils/`):
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

## Git SSH Configuration for Bot Environment

### Problem Description

When using the `/git` command through the Telegram bot, Git push operations may fail with authentication errors because:

1. **SSH Agent unavailable** - The bot process doesn't have access to SSH agent
2. **HTTPS repository URL** - Repository configured for HTTPS instead of SSH
3. **Missing SSH key context** - Claude CLI subprocess doesn't inherit SSH configuration

### Solution: Configure Git for SSH Authentication

#### 1. Switch Repository to SSH URL

```bash
# Change from HTTPS to SSH
git remote set-url origin git@github.com:username/repository.git

# Verify the change
git remote -v
```

#### 2. Configure Git SSH Command

```bash
# Set global Git SSH configuration
git config --global core.sshCommand "ssh -i ~/.ssh/id_ed25519 -o IdentitiesOnly=yes"

# Or set for current repository only
git config core.sshCommand "ssh -i ~/.ssh/id_ed25519 -o IdentitiesOnly=yes"
```

#### 3. Test SSH Connection

```bash
# Test GitHub SSH connection
ssh -T git@github.com -i ~/.ssh/id_ed25519 -o IdentitiesOnly=yes

# Expected output: "Hi username! You've successfully authenticated..."
```

#### 4. Set Environment Variable (Optional)

```bash
# For current session
export GIT_SSH_COMMAND="ssh -i ~/.ssh/id_ed25519 -o IdentitiesOnly=yes"

# Add to bot environment in .env file
echo 'GIT_SSH_COMMAND="ssh -i ~/.ssh/id_ed25519 -o IdentitiesOnly=yes"' >> .env
```

#### 5. Verify Git Push Works

```bash
# Test push operation
git push origin main

# Or current branch
git push origin $(git branch --show-current)
```

### Important Notes

- **SSH Key Path**: Replace `~/.ssh/id_ed25519` with your actual SSH key path
- **Repository URL**: Ensure you're using `git@github.com:username/repo.git` format
- **Bot Restart**: Restart the bot after configuration changes to apply environment variables
- **Security**: Keep SSH private keys secure and never expose them in logs

### Troubleshooting

**Error: "Permission denied (publickey)"**
- Verify SSH key is added to GitHub account
- Check SSH key permissions: `chmod 600 ~/.ssh/id_ed25519`
- Test SSH connection manually

**Error: "src refspec main does not match any"**
- Check current branch: `git branch -a`
- Push to correct branch: `git push origin your-current-branch`

**Error: "Could not open a connection to your authentication agent"**
- Use direct SSH key specification instead of SSH agent
- Configure `core.sshCommand` as shown above

## Localization System

### Architecture

The bot includes a robust localization system with the following components:

**Core Components:**
- `src/localization/i18n.py`: Main localization engine
- `src/localization/wrapper.py`: Async wrapper with user locale detection
- `src/localization/storage.py`: User language preference persistence
- `src/localization/translations/`: JSON translation files

**Supported Languages:**
- Ukrainian (`uk`) - Default
- English (`en`)

### Key Features

#### 1. Thread-Safe Caching
```python
# TTL Cache with asyncio.Lock for concurrent safety
class TTLCache:
    def __init__(self, ttl_seconds: int = 600):
        self._cache = OrderedDict()  # LRU behavior
        self._lock = asyncio.Lock()   # Thread safety
```

#### 2. Smart Fallback Chain
User locale detection follows this priority:
1. **Cache** - Previously detected locale (10 min TTL)
2. **Database** - User's saved language preference
3. **Telegram** - User's Telegram language code
4. **Default** - Ukrainian ("uk")

#### 3. Robust Translation Handling
```python
# Never returns raw keys - always user-friendly messages
result = i18n.get("missing.key", locale="uk")
# Returns: "[missing translation: missing.key | locale=uk]"

# Supports formatting with kwargs
result = i18n.get("welcome.message", locale="uk", user="John")
# Returns: "Привіт, John! Ласкаво просимо."
```

### Usage Examples

#### Basic Translation
```python
from src.localization.wrapper import t

# In handler
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = await t(context, user_id, "commands.start")
    await update.message.reply_text(text)
```

#### Translation with Variables
```python
# With formatting
text = await t(context, user_id, "welcome.user", username="John")

# Direct i18n usage
from src.localization.i18n import i18n
text = i18n.get("error.message", locale="uk", code=404)
```

### Adding New Translations

1. **Add to translation files:**
```json
// src/localization/translations/uk.json
{
  "commands": {
    "new_command": "Новий текст"
  }
}

// src/localization/translations/en.json
{
  "commands": {
    "new_command": "New text"
  }
}
```

2. **Use in code:**
```python
text = await t(context, user_id, "commands.new_command")
```

### Configuration

```bash
# Environment variables
DEFAULT_LOCALE=uk  # Default fallback locale
```

### Recent Improvements (2025-09-26)

✅ **Thread Safety**: TTL cache now uses asyncio.Lock for concurrent access
✅ **Fallback Handling**: Missing translations return descriptive messages instead of raw keys
✅ **Formatting Support**: Built-in **kwargs support for string formatting
✅ **LRU Management**: Automatic cache size management (1000 entries max)
✅ **Deprecated Methods**: Removed global set_locale() calls for multi-user safety

### Testing Localization

```bash
# Test basic functionality
PYTHONPATH=. python -c "
from src.localization.i18n import i18n
print(i18n.get('commands.start', locale='uk'))
print(i18n.get('missing.key', locale='uk'))  # Shows fallback
"

# Test TTL cache
PYTHONPATH=. python -c "
import asyncio
from src.localization.wrapper import TTLCache

async def test():
    cache = TTLCache(ttl_seconds=2)
    await cache.set('test', 'value')
    print(await cache.get('test'))

asyncio.run(test())
"
```

## Common Development Workflows

1. **Adding new bot commands**: Add handler in `src/bot/handlers/command.py` and register in `src/bot/core.py`
2. **Adding new middleware**: Create in `src/bot/middleware/` and register in `core.py`
3. **Extending Claude integration**: Modify `src/claude/facade.py` for high-level changes
4. **Adding new security providers**: Implement in `src/security/auth.py`
5. **Database schema changes**: Modify models in `src/storage/models.py`
6. **Adding localization**: Add keys to translation JSON files and use `await t()` wrapper