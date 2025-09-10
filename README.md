# 🚀 Claude Code Telegram Bot

A production-ready Telegram bot that provides secure remote access to Claude CLI functionality with comprehensive session management, availability monitoring, and security controls.

## 🔥 Latest Updates

**🚀 Version 0.1.1 Released!** (September 10, 2025)

**✨ Key Features:**
- 🐳 **Docker Hub Ready**: Available at `kroschu/claude-code-telegram:latest`
- 📦 **Production Optimized**: Unified deployment with `docker-compose.prod.yml`
- 🔒 **Enterprise Security**: Multi-layered authentication and authorization
- 📊 **Advanced Monitoring**: Claude CLI availability tracking with intelligent notifications
- 🎯 **Session Management**: Persistent sessions with tool usage tracking

**🛠️ Critical Fixes in v0.1.1:**
- ✅ **Fixed log duplication** - Clean, readable logging
- ✅ **Fixed Claude CLI directory creation** - No more ENOENT errors
- ✅ **Improved Telegram message parsing** - Resolved entity parsing issues
- ✅ **Enhanced error handling** - Better user experience

**Current Status:**
- 🟢 All critical issues resolved
- 🟢 Production deployment ready
- 🟢 Available on Docker Hub

## ⚡ Quick Start (Production)

For production deployment, see detailed instructions in [DEPLOY.md](./DEPLOY.md).

**One-liner deployment:**
```bash
# Download and deploy from Docker Hub
mkdir -p ~/claude-bot-deploy && cd ~/claude-bot-deploy
curl -O https://raw.githubusercontent.com/maxfraieho/claude-notifer-and-bot/main/docker-compose.prod.yml
curl -O https://raw.githubusercontent.com/maxfraieho/claude-notifer-and-bot/main/.env.example
cp .env.example .env
# Edit .env with your configuration
docker-compose -f docker-compose.prod.yml up -d
```

## 🔧 Development Setup

```bash
# Clone repository
git clone https://github.com/maxfraieho/claude-notifer-and-bot.git
cd claude-notifer-and-bot

# Configure environment
cp .env.example .env
# Edit .env with your tokens

# Start development environment
docker-compose up -d --build
```

## 🏗️ Architecture Overview

This bot features a layered architecture with clear separation of concerns:

- **Bot Layer** (`src/bot/`): Telegram bot handlers, middleware, and features
- **Claude Integration** (`src/claude/`): Claude CLI/SDK integration with session management
- **Storage Layer** (`src/storage/`): SQLite database with repository pattern
- **Security Layer** (`src/security/`): Multi-factor authentication and validation
- **Configuration** (`src/config/`): Environment-based settings management

## 🔐 Security Features

- **Multi-layered Authentication**: User whitelist + token-based auth
- **Path Validation**: Restricts file operations to approved directories
- **Rate Limiting**: Token bucket algorithm with configurable limits
- **Audit Logging**: Comprehensive security event tracking
- **Tool Access Control**: Configurable allowed/disallowed tool lists

## 📚 Documentation

- **[DEPLOY.md](./DEPLOY.md)** - Complete production deployment guide
- **[CLAUDE.md](./CLAUDE.md)** - Development guide and architecture details
- **Docker Hub**: https://hub.docker.com/r/kroschu/claude-code-telegram

## 🔧 Configuration

Essential environment variables:

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
```

## 🤖 Bot Features

### Claude CLI Integration
- **Dual execution modes**: Python SDK (primary) with CLI subprocess fallback
- **Session persistence**: SQLite-based session management
- **Tool validation**: Configurable allowed/disallowed tool lists
- **Real-time monitoring**: Health checks with availability notifications

### Availability Monitoring
- **Intelligent notifications**: DND time windows and rate limit detection  
- **Status persistence**: JSON-based state tracking with transition history
- **Multi-chat support**: Broadcast notifications to multiple Telegram chats
- **Recovery tracking**: Automatic detection of service restoration

### Security & Access Control
- **Multi-factor authentication**: Whitelist + token-based security
- **Path restrictions**: Operations limited to approved directories
- **Rate limiting**: Token bucket algorithm with configurable thresholds
- **Audit trails**: Comprehensive logging of all security events

## 🚀 Quick Commands

### Claude CLI Authentication Setup
```bash
# Install Claude CLI on host
npm install -g @anthropic-ai/claude-code

# Authenticate (creates ~/.claude directory)
claude auth login

# Verify authentication
claude auth status
```

### Development Commands
```bash
# Using Poetry (recommended)
poetry install
poetry run python -m src.main

# Run tests
poetry run pytest

# Code formatting
poetry run black src/ && poetry run isort src/

# Type checking
poetry run mypy src/
```

## 💡 Support & Contributing

- **Repository**: https://github.com/maxfraieho/claude-notifer-and-bot
- **Docker Hub**: https://hub.docker.com/r/kroschu/claude-code-telegram  
- **Issues**: https://github.com/maxfraieho/claude-notifer-and-bot/issues

---

**License**: MIT | **Version**: 0.1.1 | **Maintainer**: kroschu