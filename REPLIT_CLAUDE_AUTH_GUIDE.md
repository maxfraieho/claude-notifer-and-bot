# Claude CLI Authentication Setup for Replit

**Target**: Implement Claude CLI authentication in Python Replit environment  
**Context**: Claude Code Telegram Bot deployed without Docker  
**Date**: 2025-09-13

## Overview

This guide explains how to implement Claude CLI authentication in a Replit Python environment where the Claude Code Telegram Bot is deployed without Docker containers.

## Prerequisites

- Replit Python project with Claude Code Telegram Bot
- Claude CLI auth archive (`claude-auth-current.tar.gz`) from working system
- Access to Replit console/shell

## Authentication Architecture

### Method Used: Archive Extraction
- **NO SDK mode**: `USE_SDK=false` in configuration
- **NO API keys**: System relies only on Claude CLI credentials
- **Archive method**: Extract `.claude` directory with working credentials

### Key Files in Archive
- `.claude/.credentials.json` - OAuth token and session data
- `.claude/settings.local.json` - Claude CLI settings
- `.claude/plugins/` - Claude CLI plugins configuration
- `.claude/projects/` - Project history and sessions
- `.claude/todos/` - Claude CLI todo/session data

## Implementation Steps

### Step 1: Environment Configuration

**File**: `.env` or environment settings
```bash
# Critical settings for CLI mode
USE_SDK=false
# DO NOT SET ANTHROPIC_API_KEY - not needed for CLI mode

# Other required settings
TELEGRAM_BOT_TOKEN=your_telegram_bot_token
TELEGRAM_BOT_USERNAME=your_bot_username
ALLOWED_USERS=your_telegram_user_id
```

### Step 2: Prepare Replit Environment

**In Replit Console/Shell:**
```bash
# Check if Claude CLI is installed
which claude || echo "Claude CLI not found"

# If not installed, install Claude CLI
npm install -g @anthropic-ai/claude-code

# Verify installation
claude --version
```

### Step 3: Extract Auth Archive

**Method 1: Direct upload to Replit**
1. Upload `claude-auth-current.tar.gz` to Replit files
2. Extract in Replit console:
```bash
# Extract to home directory
cd ~
tar -xzf /path/to/claude-auth-current.tar.gz

# Verify extraction
ls -la ~/.claude/
ls -la ~/.claude/.credentials.json
```

**Method 2: Download via URL (if archive hosted)**
```bash
# If archive available via URL
cd ~
curl -L -o claude-auth.tar.gz "YOUR_ARCHIVE_URL"
tar -xzf claude-auth.tar.gz
rm claude-auth.tar.gz
```

### Step 4: Set Correct Permissions

**In Replit Console:**
```bash
# Set proper permissions for credentials
chmod 600 ~/.claude/.credentials.json
chmod -R 700 ~/.claude/

# Verify permissions
ls -la ~/.claude/.credentials.json
```

### Step 5: Verify Claude CLI Authentication

**Test commands in Replit console:**
```bash
# Test Claude CLI
claude --version

# Test authentication
claude auth status

# Test simple query
claude ask "hello"
```

**Expected responses:**
- `claude --version` → `1.0.113 (Claude Code)` 
- `claude auth status` → Should show authenticated status
- `claude ask "hello"` → Should return Claude response

### Step 6: Application Configuration

**In your Python application:**

Ensure the application uses CLI mode:
```python
# In config/settings.py or equivalent
USE_SDK = False  # Critical: forces CLI mode

# Verify no SDK fallback
ANTHROPIC_API_KEY = None  # Should be None/empty
```

### Step 7: Test Integration

**Test the bot with Claude CLI:**
1. Start your Replit application
2. Send test message to Telegram bot
3. Check Replit logs for Claude CLI execution
4. Verify bot responds correctly

## Troubleshooting

### Problem: "Invalid API key" error
**Solution**: 
```bash
# Re-extract archive
cd ~
tar -xzf claude-auth-current.tar.gz --overwrite
chmod 600 ~/.claude/.credentials.json
```

### Problem: "Claude CLI not found"
**Solution**:
```bash
# Install Claude CLI
npm install -g @anthropic-ai/claude-code
# Add to PATH if needed
export PATH=$PATH:~/.npm-global/bin
```

### Problem: "Authentication failed"
**Solution**:
1. Verify archive contains valid credentials
2. Check file permissions
3. Ensure `USE_SDK=false` in configuration

### Problem: Bot uses SDK instead of CLI
**Solution**:
```python
# Force CLI mode in settings
USE_SDK = False
# Remove any ANTHROPIC_API_KEY settings
```

## Verification Checklist

- [ ] Claude CLI installed and accessible
- [ ] Archive extracted to `~/.claude/`
- [ ] Credentials file has correct permissions (600)
- [ ] `claude auth status` shows authenticated
- [ ] `claude ask "test"` returns response
- [ ] Application configured with `USE_SDK=false`
- [ ] No `ANTHROPIC_API_KEY` in environment
- [ ] Telegram bot responds to test messages

## File Structure After Setup

```
~/.claude/
├── .credentials.json          # OAuth token (600 permissions)
├── settings.local.json        # Claude CLI settings
├── plugins/                   # Claude CLI plugins
│   └── config.json
├── projects/                  # Project sessions
│   └── [various session files]
└── todos/                     # Claude CLI todos/sessions
    └── [session files]
```

## Important Notes

### Archive Source
- Use `claude-auth-current.tar.gz` from working Docker system
- Archive contains OAuth token with expiration date
- May need periodic updates when token expires

### Environment Differences
- Replit uses different user/path structure than Docker
- Extract to user home directory (`~/.claude/`)
- Verify PATH includes npm global binaries

### Security Considerations
- Keep credentials file permissions restrictive (600)
- Do not commit `.claude/` directory to version control
- Archive contains sensitive authentication data

## Success Criteria

**System working correctly when:**
1. Claude CLI commands work in Replit console
2. Telegram bot responds to messages
3. Bot logs show CLI execution (not SDK)
4. No authentication errors in logs

**File path**: `/home/user/.claude/.credentials.json` (typical Replit structure)
**Configuration**: `USE_SDK=false` enforced
**Mode**: Pure CLI integration without Docker containers