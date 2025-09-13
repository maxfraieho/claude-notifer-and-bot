# Claude CLI Authentication Fix - Complete Log

**Date**: 2025-09-13  
**Issue**: Claude CLI authentication failed in Docker container  
**Status**: ✅ FIXED

## Problem Analysis

### Initial Issue
- Telegram bot responded: "❌ Claude Code Error - Failed to process your request: Claude Code exited with code 1"
- Container logs showed: "Claude CLI unavailable (timeout/not found)"
- Claude CLI auth status: "Invalid API key · Fix external API key"

### Root Causes Discovered
1. **Wrong execution mode**: Container was running with `USE_SDK=true` instead of `USE_SDK=false`
2. **Expired OAuth token**: The `.claude/.credentials.json` file contained expired OAuth token
3. **Mixed configuration**: System had both SDK and CLI settings mixed together
4. **Environment variables mismatch**: Container retained old environment variables after config changes

## Solution Process

### Step 1: Clarify Architecture Requirements
**User requirement**: Use ONLY `.claude` archive method, NO SDK mode
- Set `USE_SDK=false` in `.env`
- Remove all `ANTHROPIC_API_KEY` references
- Use only Claude CLI with archived credentials

### Step 2: Fix Configuration
```bash
# In .env file
USE_SDK=false
# NO API KEYS NEEDED - only .claude archive method
```

### Step 3: Container Environment Issue
**Problem**: Container still had old environment variables even after `.env` changes
```bash
# Container had wrong values:
USE_SDK=true
ANTHROPIC_API_KEY=sk-ant-oat01-...
```

**Solution**: Complete container rebuild
```bash
docker compose down
docker compose up -d --build
```

### Step 4: OAuth Token Refresh
**Problem**: OAuth token in `.claude/.credentials.json` was expired
```bash
# Token from Sep 12 was expired
-rw------- 1 claudebot claudebot 364 Sep 12 05:43 .credentials.json
```

**Solution**: Use current host credentials
```bash
# Create fresh archive from host
tar -czf claude-auth-current.tar.gz -C /home/vokov .claude

# Transfer to container
docker cp claude-auth-current.tar.gz claude-code-bot:/tmp/claude-auth.tar.gz

# Extract in container
docker exec claude-code-bot bash -c "cd /home/claudebot && tar -xzf /tmp/claude-auth.tar.gz"

# Restart container
docker compose restart
```

## Final Working Solution

### Correct Configuration
```env
# .env file settings
USE_SDK=false
# NO API KEYS NEEDED - only .claude archive method
```

### Authentication Method
1. Archive working `.claude` directory from host
2. Transfer archive to container
3. Extract in container's `/home/claudebot/.claude/`
4. Restart container

### Verification Commands
```bash
# Test Claude CLI in container
docker exec claude-code-bot bash -c "claude ask 'hello'"
# Response: "I'm ready to help! What would you like me to do with the Claude Code Telegram Bot project?"
```

## Key Learnings

### What Works ✅
- Archive method with current host credentials
- `USE_SDK=false` configuration
- Complete container rebuild after config changes

### What Doesn't Work ❌
- Old expired OAuth tokens
- Mixed SDK/CLI configurations
- Container restart without rebuild after env changes

### Critical Commands for Future
```bash
# Full auth refresh process:
tar -czf claude-auth-current.tar.gz -C /home/vokov .claude
docker cp claude-auth-current.tar.gz claude-code-bot:/tmp/claude-auth.tar.gz
docker exec claude-code-bot bash -c "cd /home/claudebot && tar -xzf /tmp/claude-auth.tar.gz"
docker compose restart
```

## Updated Documentation

Updated `CLAUDE.md` with IMPORTANT section:
```markdown
### ВАЖЛИВО: Тільки метод архівування

**НЕ використовуємо SDK mode!** Тільки архівування `.claude` налаштувань з хосту:

1. Завжди `USE_SDK=false` в `.env`
2. Тільки архівуємо та розархівовуємо `.claude` директорію з хосту
3. Ніяких API ключів або SDK режимів не потрібно

Система працює ТІЛЬКИ через архівування робочих Claude CLI налаштувань.
```

## Current Status ✅

- Claude CLI responds correctly in container
- Telegram bot should work with `USE_SDK=false` 
- System uses only archive method as requested
- All documentation updated

## Test Results
```bash
docker exec claude-code-bot bash -c "claude ask 'hello'"
# Output: I'm ready to help! What would you like me to do with the Claude Code Telegram Bot project?
```

**Final verification**: Ready for Telegram bot testing