# 📚 Claude Code Telegram Bot Documentation

Welcome to the comprehensive documentation for Claude Code Telegram Bot - a sophisticated remote access system for Claude CLI functionality through Telegram.

## 📖 Documentation Overview

This documentation provides complete information for users, developers, and system administrators working with the Claude Code Telegram Bot.

### 🚀 Quick Links

| Document | Purpose | Audience |
|----------|---------|----------|
| [**User Guide**](USER_GUIDE.md) | Complete user manual with all commands | End Users |
| [**Image Processing Guide**](IMAGE_PROCESSING_GUIDE.md) | Detailed `/img` command and Code Fix Mode | Users, Developers |
| [**MCP Integration Guide**](MCP_INTEGRATION_GUIDE.md) | Model Context Protocol usage and setup | Advanced Users, Admins |
| [**Architecture Audit**](ARCHITECTURE_AUDIT.md) | Technical architecture analysis | Developers, Architects |

### 📋 What's New

#### ✨ Recent Features
- **🔧 Code Fix Mode** - Revolutionary screenshot-based code fixing
- **🌍 Full Localization** - Complete Ukrainian language support
- **🔌 MCP Integration** - Model Context Protocol for enhanced capabilities
- **📅 Scheduled Tasks** - Automated monitoring and operations
- **⚡ Enhanced Performance** - Improved response times and reliability

## 🎯 Getting Started

### For New Users
1. **Start here:** [User Guide](USER_GUIDE.md) - Complete walkthrough of all features
2. **Learn image processing:** [Image Processing Guide](IMAGE_PROCESSING_GUIDE.md) - Advanced visual analysis
3. **Explore MCP:** [MCP Integration Guide](MCP_INTEGRATION_GUIDE.md) - Extended capabilities

### For Developers
1. **Architecture overview:** [Architecture Audit](ARCHITECTURE_AUDIT.md) - Technical deep dive
2. **Configuration:** Check `src/config/settings.py` for all options
3. **Development setup:** See main `README.md` for development workflow

### For System Administrators
1. **Security model:** Review security sections in [Architecture Audit](ARCHITECTURE_AUDIT.md)
2. **Deployment:** Docker and configuration guides in main documentation
3. **Monitoring:** Performance and logging information in architecture docs

## 🎯 Feature Categories

### 🤖 Core Bot Features
- **Session Management** - Start, continue, and manage Claude conversations
- **File Navigation** - Browse directories, manage files, project switching
- **Git Integration** - Repository status, branch management, change tracking
- **Authentication** - Secure access control and user management

### 📸 Image Processing
- **Multi-image Analysis** - Batch processing with Claude AI
- **Code Fix Mode** - Revolutionary screenshot-based debugging
- **Visual Recognition** - Document analysis, UI review, technical diagrams
- **Batch Operations** - Process multiple images with context

### 🔌 Advanced Integration
- **MCP Protocol** - Extended capabilities through external tools
- **Dual Claude Modes** - CLI subprocess and Python SDK integration
- **Scheduled Tasks** - Automated operations and monitoring
- **Multi-language** - Ukrainian and English localization

### 🔒 Security & Administration
- **Multi-layer Authentication** - Whitelist and token-based access
- **Rate Limiting** - Smart usage controls and cost management
- **Audit Logging** - Comprehensive activity tracking
- **Permission System** - Granular access controls

## 📊 System Architecture

### High-Level Architecture
```
┌─────────────────────────────────────────┐
│           Telegram Bot API              │
├─────────────────────────────────────────┤
│              Bot Layer                  │ ← Handlers, Middleware
├─────────────────────────────────────────┤
│           Claude Integration            │ ← CLI/SDK, Sessions
├─────────────────────────────────────────┤
│           Storage & Security            │ ← Database, Auth
├─────────────────────────────────────────┤
│         Infrastructure Layer            │ ← Config, Logging
└─────────────────────────────────────────┘
```

### Key Components
- **Bot Layer** - Telegram interface, commands, middleware
- **Claude Integration** - Dual-mode execution with session management
- **Storage Layer** - SQLite database with repository patterns
- **Security Layer** - Authentication, authorization, rate limiting
- **MCP Layer** - Model Context Protocol integration

## 🔧 Configuration

### Environment Variables
```bash
# Required
TELEGRAM_BOT_TOKEN=your_bot_token
TELEGRAM_BOT_USERNAME=your_bot_username
APPROVED_DIRECTORY=/app/target_project

# Security
ALLOWED_USERS=123456789,987654321
ENABLE_TOKEN_AUTH=true
AUTH_TOKEN_SECRET=your_secret

# Features
ENABLE_IMAGE_PROCESSING=true
ENABLE_MCP=false
ENABLE_LOCALIZATION=true
```

### Feature Flags
```bash
# Core features
ENABLE_FILE_UPLOADS=true
ENABLE_GIT_INTEGRATION=true
ENABLE_QUICK_ACTIONS=true

# Advanced features
CLAUDE_AVAILABILITY_MONITOR=true
ENABLE_SESSION_EXPORT=true
ENABLE_CONVERSATION_ENHANCEMENT=true
```

## 🚨 Troubleshooting

### Common Issues

#### Authentication Problems
```
Error: "Access denied"
Solution: Check ALLOWED_USERS configuration
```

#### Claude CLI Issues
```
Error: "Claude CLI недоступний"
Solution: Use /claude command to re-authenticate
```

#### Rate Limiting
```
Error: "Rate limit exceeded"
Solution: Wait for rate limit window to reset
```

#### Image Processing
```
Error: "Image processing disabled"
Solution: Set ENABLE_IMAGE_PROCESSING=true
```

### Debug Mode
```bash
python -m src.main --debug
```

### Getting Help
- **In-bot:** `/help` command
- **Status:** `/status` for current session info
- **Documentation:** This docs folder
- **Logs:** Enable debug mode for detailed information

## 📈 Performance & Monitoring

### Key Metrics
- **Response Time** - Average command response time
- **Session Count** - Active concurrent sessions
- **Rate Limits** - Usage tracking and limits
- **Error Rates** - System reliability metrics

### Monitoring Tools
- **Structured Logging** - Comprehensive system logs
- **Health Checks** - Automated system monitoring
- **Usage Analytics** - User activity and feature usage
- **Cost Tracking** - Claude API usage monitoring

## 🔮 Roadmap

### Current Development (Q4 2024)
- **Enhanced Testing** - Comprehensive test coverage
- **Performance Optimization** - Caching and optimization
- **Monitoring Dashboard** - Grafana integration

### Upcoming Features (2025)
- **Video Processing** - Support for video file analysis
- **Real-time Collaboration** - Multi-user session support
- **Advanced Analytics** - Usage insights and reporting
- **Mobile App** - Dedicated mobile application

### Long-term Vision
- **Multi-tenant Architecture** - Organization and team support
- **Plugin Ecosystem** - Third-party plugin marketplace
- **AI Enhancement** - Advanced AI-powered features
- **Enterprise Features** - SSO, RBAC, compliance

## 🤝 Contributing

### Development Workflow
```bash
# Setup development environment
poetry install --with dev

# Code quality checks
poetry run black src/
poetry run isort src/
poetry run mypy src/

# Testing
poetry run pytest
```

### Documentation Updates
- Update relevant documentation for any feature changes
- Add examples for new functionality
- Update configuration references
- Keep troubleshooting guides current

## 📞 Support

### Documentation Hierarchy
1. **Quick answers:** In-bot `/help` command
2. **User questions:** [User Guide](USER_GUIDE.md)
3. **Technical issues:** [Architecture Audit](ARCHITECTURE_AUDIT.md)
4. **Advanced features:** Feature-specific guides

### Bug Reports
- Enable debug mode for detailed logs
- Include configuration (without secrets)
- Provide reproduction steps
- Include error messages and logs

## 📄 License & Legal

This project follows standard open source practices with comprehensive documentation and transparent architecture.

### Security Notice
- Review security sections before production deployment
- Follow configuration guidelines for production use
- Enable appropriate monitoring and logging
- Regular security updates recommended

---

## 📚 Document Index

### User Documentation
- [**User Guide**](USER_GUIDE.md) - Complete user manual
- [**Image Processing Guide**](IMAGE_PROCESSING_GUIDE.md) - Visual analysis features
- [**MCP Integration Guide**](MCP_INTEGRATION_GUIDE.md) - Advanced integrations

### Technical Documentation
- [**Architecture Audit**](ARCHITECTURE_AUDIT.md) - System design and analysis
- Main `README.md` - Development and deployment
- `CLAUDE.md` - Development guidelines and commands

### Quick Reference
| Feature | Command | Documentation |
|---------|---------|---------------|
| Start session | `/new` | User Guide |
| Image analysis | `/img` | Image Processing Guide |
| Code fixing | `/img` → `запит` | Image Processing Guide |
| MCP servers | `/mcpadd` | MCP Integration Guide |
| Git operations | `/git` | User Guide |
| System status | `/status` | User Guide |

**Last Updated:** September 2025
**Version:** 0.1.0