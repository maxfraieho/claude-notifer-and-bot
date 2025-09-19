# 🤖 Claude Code Telegram Bot - User Guide

## Overview

Claude Code Telegram Bot provides secure remote access to Claude CLI functionality through Telegram. This comprehensive guide covers all features and commands available to users.

## Quick Start

### Initial Setup
1. Start conversation with the bot
2. Type `/start` to initialize
3. Type `/help` for command overview
4. Use `/new` to start your first Claude session

### Basic Workflow
```
/new                    # Start new session
[Your prompt]          # Ask Claude anything
/status                # Check session info
/export                # Save conversation
/end                   # Close session
```

## 📋 Core Commands

### Session Management

#### `/new` - Start New Session
Creates a fresh Claude conversation session.
```
/new
/new What are Python decorators?
```
- Clears any previous context
- Starts with clean working directory
- Resets tool usage tracking

#### `/continue` - Resume Session
Continues your most recent session or finds an active one.
```
/continue
/continue Let's continue our React discussion
```
- Maintains conversation context
- Preserves working directory
- Keeps tool usage history

#### `/end` - End Session
Terminates the current session and cleans up resources.
```
/end
```
- Saves session to history
- Clears active context
- Provides usage summary

#### `/status` - Session Status
Shows detailed information about your current session.
```
/status
```
**Information displayed:**
- Session ID and duration
- Current working directory
- Tool usage statistics
- Cost tracking (if enabled)
- Rate limit status

#### `/export` - Export Session
Export your conversation in multiple formats.
```
/export
```
**Available formats:**
- **Markdown** (.md) - Human-readable format
- **HTML** (.html) - Web-friendly with styling
- **JSON** (.json) - Machine-readable with metadata

## 🗂️ Navigation Commands

### File System Navigation

#### `/ls` - List Files
Show contents of current directory.
```
/ls
```
**Features:**
- File sizes and permissions
- Type indicators (📁 folders, 📄 files)
- Interactive navigation buttons
- Hidden files toggle

#### `/cd` - Change Directory
Navigate to different directories.
```
/cd src
/cd ../parent
/cd /absolute/path
```
**Security features:**
- Path validation and sanitization
- Restricted to approved directories
- Prevents directory traversal attacks

#### `/pwd` - Current Directory
Display current working directory.
```
/pwd
```
Shows both relative and absolute paths.

#### `/projects` - Project Selection
Browse and select from available projects.
```
/projects
```
- Interactive project browser
- Quick project switching
- Project metadata display

## 🔧 Git Integration

### `/git` - Repository Status
Show comprehensive git repository information.
```
/git
```
**Information displayed:**
- Current branch and status
- Staged and unstaged changes
- Commit history (recent)
- Remote status
- Stash information

**Interactive features:**
- Quick action buttons
- File-specific actions
- Branch switching options

## 🔐 Authentication

### `/claude` - Claude CLI Authentication
Manage Claude CLI authentication status.
```
/claude
```
**Features:**
- Interactive authentication flow
- Status checking
- Token refresh
- Troubleshooting guidance

## ⚡ Quick Actions

### `/actions` - Context Actions
Show available quick actions based on current context.
```
/actions
```
**Context-aware actions:**
- **In git repository:** commit, push, pull, status
- **In project directory:** build, test, lint, deploy
- **With files selected:** edit, move, copy, delete
- **In session:** export, status, reset

## 📸 Image Processing

### `/img` - Image Analysis & Code Fixing
Process images with Claude AI, including a special Code Fix Mode.

#### Basic Image Analysis
```
/img
[upload images]
[describe what you want analyzed]
готово
```

#### Code Fix Mode (🔧 NEW!)
```
/img
[upload screenshot of interface problem]
запит                           # Activate fix mode
[describe the issue and requirements]
готово                          # Claude analyzes and fixes code
```

**Code Fix Capabilities:**
- Analyze UI/interface problems from screenshots
- Automatically explore your codebase
- Implement fixes in source code
- Support multiple technologies (React, Vue, Python, etc.)

[See detailed guide: IMAGE_PROCESSING_GUIDE.md]

## 📅 Scheduled Tasks

### `/schedules` - Manage Tasks
View and manage all scheduled tasks.
```
/schedules
```
**Task management:**
- List active tasks
- View task history
- Enable/disable tasks
- Delete tasks

### `/add_schedule` - Create Task
Create new scheduled task with interactive wizard.
```
/add_schedule
```
**Task types:**
- **DND periods** - Quiet hours configuration
- **Health checks** - System monitoring
- **Automated tasks** - Custom operations
- **Notifications** - Alert scheduling

## 🔌 MCP (Model Context Protocol)

### Server Management

#### `/mcpadd` - Add Server
Add new MCP server with interactive configuration.
```
/mcpadd
/mcpadd filesystem
```
**Server types:**
- **Filesystem** - File operation enhancement
- **Database** - SQL database integration
- **Web** - Web scraping and API access
- **Custom** - User-defined servers

#### `/mcplist` - List Servers
Show all configured MCP servers and their status.
```
/mcplist
```
**Information shown:**
- Server name and type
- Connection status
- Available tools
- Usage statistics

#### `/mcpselect` - Select Context
Choose active MCP context for enhanced capabilities.
```
/mcpselect filesystem
/mcpselect             # Interactive selection
```

#### `/mcpask` - Enhanced Queries
Ask questions with MCP context for enhanced responses.
```
/mcpask How many Python files are in this project?
```

#### `/mcpremove` - Remove Server
Safely remove MCP server configuration.
```
/mcpremove filesystem
/mcpremove             # Interactive removal
```

#### `/mcpstatus` - System Status
Show comprehensive MCP system status.
```
/mcpstatus
```

## 🛡️ Security Features

### Authentication System
- **Whitelist-based** - Approved user IDs only
- **Token-based** - Secure token authentication
- **Development mode** - Allow-all for testing

### Rate Limiting
- **Request limits** - Configurable requests per window
- **Burst protection** - Prevent rapid-fire requests
- **Cost tracking** - Monitor Claude API usage

### File Security
- **Path validation** - Prevent directory traversal
- **Approved directories** - Restrict file operations
- **Command filtering** - Block dangerous commands

### Audit Logging
- All user actions logged
- Security violations tracked
- Authentication attempts monitored

## 🌍 Localization

### Language Support
The bot supports multiple languages with automatic detection:

- **🇺🇦 Ukrainian** (`uk`) - Full localization
- **🇬🇧 English** (`en`) - Default language

### Language Features
- **Auto-detection** - Based on user's Telegram settings
- **User preferences** - Individual language selection
- **Fallback support** - English fallback for missing translations
- **Dynamic switching** - Change language during conversation

### Localized Elements
- Command descriptions and help text
- Error messages and notifications
- Button labels and UI elements
- Status messages and confirmations

## ⚙️ Configuration

### User Settings
Users can customize their experience through environment variables:

#### Basic Configuration
```bash
# Your user ID (get from @userinfobot)
ALLOWED_USERS=123456789

# Language preference
DEFAULT_LANGUAGE=uk

# Working directory
APPROVED_DIRECTORY=/your/project/path
```

#### Advanced Settings
```bash
# Rate limiting
RATE_LIMIT_REQUESTS=10
RATE_LIMIT_WINDOW=60

# Session management
SESSION_TIMEOUT_MINUTES=120
MAX_SESSIONS_PER_USER=3

# Feature toggles
ENABLE_IMAGE_PROCESSING=true
ENABLE_GIT_INTEGRATION=true
ENABLE_MCP=true
```

## 🚨 Troubleshooting

### Common Issues

#### "Access denied" / "Authentication failed"
**Cause:** Your user ID is not in the allowed users list
**Solution:** Add your Telegram user ID to `ALLOWED_USERS` environment variable

#### "Rate limit exceeded"
**Cause:** Too many requests in short time period
**Solution:** Wait for rate limit window to reset (usually 1 minute)

#### "Claude CLI недоступний" (Claude CLI unavailable)
**Cause:** Claude CLI not authenticated or not working
**Solution:**
1. Use `/claude` command to check authentication
2. Re-authenticate Claude CLI if needed
3. Check Claude CLI is installed and accessible

#### "Session not found"
**Cause:** Session expired or was cleaned up
**Solution:** Start new session with `/new`

#### "Directory not accessible"
**Cause:** Trying to access directory outside approved paths
**Solution:** Navigate within approved directory structure

### Debug Mode
Enable detailed logging for troubleshooting:
```bash
python -m src.main --debug
```

### Getting Help
1. **In-bot help:** `/help` - Quick command reference
2. **Status check:** `/status` - Current session information
3. **Documentation:** Check `docs/` folder for detailed guides
4. **Logs:** Enable debug mode for detailed error information

## 💡 Best Practices

### Session Management
1. **Start fresh** - Use `/new` for unrelated tasks
2. **Check status** - Regular `/status` checks for long sessions
3. **Export important work** - Use `/export` to save valuable conversations
4. **End cleanly** - Use `/end` to properly close sessions

### Security
1. **Verify permissions** - Check file access before operations
2. **Use relative paths** - Avoid absolute paths when possible
3. **Regular authentication** - Keep Claude CLI authentication current
4. **Monitor usage** - Check rate limits and costs regularly

### Productivity
1. **Use quick actions** - `/actions` for common operations
2. **Leverage git integration** - Use `/git` for repository management
3. **Organize projects** - Use `/projects` for project switching
4. **Schedule tasks** - Use `/schedules` for automation

### Image Processing
1. **Clear screenshots** - High quality, well-cropped images
2. **Detailed descriptions** - Explain context and requirements
3. **Use fix mode** - Try Code Fix Mode for interface issues
4. **Batch operations** - Process related images together

## 📈 Advanced Usage

### Workflow Automation
Combine commands for efficient workflows:

```bash
# Development workflow
/projects → select project → /git → /new → [development work] → /git → /export

# Code review workflow
/img → [upload screenshots] → запит → [describe issues] → готово → /git

# Daily standup workflow
/status → /git → /schedules → [team updates]
```

### Integration Patterns
- **CI/CD integration** - Use with deployment pipelines
- **Code review** - Screenshot-based code review process
- **Documentation** - Export sessions as documentation
- **Team collaboration** - Share exported sessions

### Power User Tips
1. **Keyboard shortcuts** - Learn common command patterns
2. **Context switching** - Use `/continue` to maintain context
3. **Multi-session workflow** - Use different sessions for different tasks
4. **Automation** - Set up scheduled tasks for routine operations

## 🔄 Updates and Changelog

### Latest Features
- **🔧 Code Fix Mode** - Screenshot-based code fixing
- **🌍 Full localization** - Ukrainian language support
- **📅 Scheduled tasks** - Automation and monitoring
- **🔌 MCP integration** - Enhanced context and tools

### Coming Soon
- **Video processing** - Support for video files
- **Real-time collaboration** - Multi-user sessions
- **Advanced analytics** - Usage insights and reporting
- **Mobile app** - Dedicated mobile application

---

## Quick Reference Card

| Command | Purpose | Example |
|---------|---------|---------|
| `/start` | Initialize bot | `/start` |
| `/help` | Show help | `/help` |
| `/new` | New session | `/new` |
| `/continue` | Resume session | `/continue` |
| `/end` | End session | `/end` |
| `/status` | Session info | `/status` |
| `/export` | Export chat | `/export` |
| `/ls` | List files | `/ls` |
| `/cd` | Change directory | `/cd src` |
| `/pwd` | Current directory | `/pwd` |
| `/projects` | Select project | `/projects` |
| `/git` | Git status | `/git` |
| `/claude` | Authentication | `/claude` |
| `/actions` | Quick actions | `/actions` |
| `/img` | Image processing | `/img` |
| `/schedules` | Manage tasks | `/schedules` |
| `/add_schedule` | Add task | `/add_schedule` |
| `/mcpadd` | Add MCP server | `/mcpadd` |
| `/mcplist` | List MCP servers | `/mcplist` |
| `/mcpselect` | Select MCP context | `/mcpselect` |
| `/mcpask` | MCP-enhanced query | `/mcpask` |
| `/mcpremove` | Remove MCP server | `/mcpremove` |
| `/mcpstatus` | MCP status | `/mcpstatus` |

**Need more help?** Type `/help` in the bot or check the documentation at `docs/`