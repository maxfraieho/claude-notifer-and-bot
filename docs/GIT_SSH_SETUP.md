# Git SSH Configuration Guide for Claude Code Telegram Bot

## Overview

This guide explains how to configure Git SSH authentication for the Claude Code Telegram Bot environment, enabling the `/git` command to perform push operations successfully.

## Problem Description

When using Git operations through the Telegram bot, you may encounter authentication failures during push operations:

```
Репозиторій налаштований на HTTPS. Потрібно або використати SSH або встановити токен доступу GitHub.
```

This happens because:
1. The bot process runs in an isolated environment without SSH agent access
2. Repository may be configured for HTTPS instead of SSH
3. Claude CLI subprocess doesn't inherit SSH configuration from the host

## Step-by-Step Solution

### 1. Check Current Git Configuration

```bash
# Check current remote URL
git remote -v

# If output shows HTTPS URL like:
# origin  https://github.com/username/repository.git (fetch)
# origin  https://github.com/username/repository.git (push)
# Then you need to switch to SSH
```

### 2. Switch to SSH Remote URL

```bash
# Replace with your repository URL
git remote set-url origin git@github.com:username/repository.git

# Verify the change
git remote -v
# Should now show:
# origin  git@github.com:username/repository.git (fetch)
# origin  git@github.com:username/repository.git (push)
```

### 3. Configure Git SSH Command

```bash
# Set Git to use specific SSH key (replace with your key path)
git config --global core.sshCommand "ssh -i ~/.ssh/id_ed25519 -o IdentitiesOnly=yes"

# Or for current repository only:
git config core.sshCommand "ssh -i ~/.ssh/id_ed25519 -o IdentitiesOnly=yes"
```

### 4. Test SSH Connection

```bash
# Test GitHub SSH connection
ssh -T git@github.com -i ~/.ssh/id_ed25519 -o IdentitiesOnly=yes

# Expected successful output:
# Hi username! You've successfully authenticated, but GitHub does not provide shell access.
```

### 5. Set Environment Variable for Bot

```bash
# Set for current session
export GIT_SSH_COMMAND="ssh -i ~/.ssh/id_ed25519 -o IdentitiesOnly=yes"

# Or add to .env file for permanent configuration
echo 'GIT_SSH_COMMAND="ssh -i ~/.ssh/id_ed25519 -o IdentitiesOnly=yes"' >> .env
```

### 6. Test Git Push

```bash
# Test push operation manually first
git add .
git commit -m "Test commit for SSH configuration"
git push origin main

# Or push to current branch
git push origin $(git branch --show-current)
```

### 7. Restart the Bot

After configuration changes, restart the bot to apply environment variables:

```bash
# If running directly
pkill -f "python.*main.py"
python3 -m src.main

# If using Docker
docker-compose down
docker-compose up -d --build
```

## Verification

Test the Git functionality through the Telegram bot:

1. Send `/git` command to the bot
2. Choose "📤 Push Changes" option
3. The operation should now complete successfully

## Common SSH Key Types

| Key Type | File Name | Command Example |
|----------|-----------|-----------------|
| RSA | `id_rsa` | `ssh -i ~/.ssh/id_rsa` |
| Ed25519 | `id_ed25519` | `ssh -i ~/.ssh/id_ed25519` |
| ECDSA | `id_ecdsa` | `ssh -i ~/.ssh/id_ecdsa` |

## Troubleshooting

### Error: "Permission denied (publickey)"

**Causes:**
- SSH key not added to GitHub account
- Incorrect SSH key permissions
- Wrong SSH key path

**Solutions:**
```bash
# Check SSH key permissions
ls -la ~/.ssh/
chmod 600 ~/.ssh/id_ed25519  # Set correct permissions

# Test SSH key
ssh -T git@github.com -i ~/.ssh/id_ed25519 -v  # Verbose output

# Verify key is added to GitHub account
cat ~/.ssh/id_ed25519.pub
# Copy and add to GitHub → Settings → SSH and GPG keys
```

### Error: "src refspec main does not match any"

**Cause:** Trying to push to wrong branch

**Solution:**
```bash
# Check current branch
git branch -a

# Push to correct branch
git push origin your-current-branch-name
```

### Error: "Could not open a connection to your authentication agent"

**Cause:** SSH agent not available

**Solution:** Use direct SSH key specification (already covered in main configuration)

### SSH Connection Times Out

**Causes:**
- Network firewall blocking SSH port 22
- GitHub SSH service issues

**Solutions:**
```bash
# Try SSH over HTTPS port
ssh -T -p 443 git@ssh.github.com

# Configure Git to use HTTPS port for SSH
git config --global url."ssh://git@ssh.github.com:443/".insteadOf "git@github.com:"
```

## Security Best Practices

1. **Key Permissions**: Ensure SSH private keys have correct permissions (600)
2. **Key Storage**: Never expose private keys in logs or configuration files
3. **Key Rotation**: Regularly rotate SSH keys
4. **Access Control**: Use deploy keys for repository-specific access when possible

## Environment Variables Summary

Add these to your `.env` file for persistent configuration:

```bash
# Git SSH configuration
GIT_SSH_COMMAND="ssh -i ~/.ssh/id_ed25519 -o IdentitiesOnly=yes"

# Optional: Git user configuration
GIT_AUTHOR_NAME="Your Name"
GIT_AUTHOR_EMAIL="your.email@example.com"
GIT_COMMITTER_NAME="Your Name"
GIT_COMMITTER_EMAIL="your.email@example.com"
```

## Integration with Bot Features

After successful configuration, the following bot features will work seamlessly:

- `/git` command with push operations
- Automated Git operations through Claude CLI
- Git status and history commands
- Commit and branch operations

## Need Help?

If you continue experiencing issues:

1. Check bot logs for detailed error messages
2. Test Git operations manually outside the bot first
3. Verify SSH key configuration on GitHub
4. Ensure all environment variables are properly set

For additional support, refer to the main project documentation or create an issue in the repository.