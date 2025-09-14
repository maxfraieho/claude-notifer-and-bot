# Overview

This is a Claude Code Telegram Bot that provides secure remote access to Claude CLI functionality through Telegram. The bot serves as a bridge between Telegram users and Claude Code, allowing developers to interact with their projects remotely through a terminal-like interface. The system includes comprehensive features like session management, multi-language support, security controls, rate limiting, and monitoring capabilities.

# User Preferences

Preferred communication style: Simple, everyday language.

# System Architecture

## Core Architecture

The project follows a modular architecture with clear separation of concerns:

**Bot Layer (`src/bot/`)**: Telegram bot implementation using python-telegram-bot library with feature-based organization. Includes handlers for commands, callbacks, and various features like file uploads, conversation enhancement, and quick actions.

**Claude Integration (`src/claude/`)**: Dual-mode Claude integration supporting both CLI subprocess execution and SDK-based communication. Features process management, session tracking, output parsing, and tool usage monitoring with security validation.

**Configuration System (`src/config/`)**: Pydantic-based settings management with environment-specific configurations, feature flags, and comprehensive validation. Supports development, testing, and production environments.

**Security Framework (`src/security/`)**: Multi-layered security with whitelist and token-based authentication, rate limiting using token bucket algorithm, input validation, path traversal prevention, and comprehensive audit logging.

**Storage Layer (`src/storage/`)**: Repository pattern implementation with SQLite backend. Includes user management, session persistence, message history, tool usage tracking, and analytics data.

**Localization System (`src/localization/`)**: Multi-language support with JSON-based translations (English and Ukrainian), user language preferences, and comprehensive message localization.

## Key Design Decisions

**Dual Claude Integration**: Supports both CLI subprocess execution (for authenticated environments) and SDK-based communication (for standalone deployments). This provides flexibility for different deployment scenarios while maintaining consistent functionality.

**Feature Flag System**: Extensive feature flags allow dynamic enabling/disabling of functionality like file uploads, git integration, MCP support, and telemetry based on deployment requirements.

**Security-First Approach**: Multi-layered security including user whitelisting, token authentication, rate limiting, input validation, and audit logging. All user inputs are validated for path traversal and injection attacks.

**Session Management**: Persistent session tracking across conversations with automatic cleanup, cost tracking, and tool usage monitoring. Sessions maintain state between bot restarts.

**Containerized Deployment**: Docker-based deployment with production-ready configurations, health checks, and proper volume mounting for Claude CLI authentication.

# External Dependencies

## Core Dependencies
- **python-telegram-bot**: Telegram bot API framework for handling updates, commands, and callbacks
- **Pydantic**: Settings management and data validation with type safety
- **aiosqlite**: Async SQLite database operations for persistent storage
- **structlog**: Structured logging with JSON output for production monitoring

## Claude Integration
- **claude-code-sdk**: Official Claude Code Python SDK for API-based communication
- **Claude CLI**: Command-line interface for Claude Code (mounted via Docker volumes)

## Development Tools
- **Poetry**: Dependency management and virtual environment handling
- **pytest**: Testing framework with async support and coverage reporting
- **black/isort/flake8/mypy**: Code formatting, import sorting, linting, and type checking

## Infrastructure
- **Docker**: Containerized deployment with multi-stage builds
- **Docker Compose**: Service orchestration for development and production
- **SQLite**: Embedded database for session and user data persistence

## Optional Integrations
- **Anthropic API**: Direct API access when not using CLI authentication
- **Git**: Repository operations for version control integration
- **Tenacity**: Retry logic for network operations and API calls