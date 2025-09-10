# 🚀 Production Deployment Guide

## Server Requirements

### System Requirements
- **OS**: Ubuntu 20.04+ / Debian 11+ / CentOS 8+
- **RAM**: Minimum 2GB, Recommended 4GB+
- **CPU**: 2+ cores
- **Storage**: 10GB+ free space
- **Network**: Stable internet connection

### Software Requirements
- Docker 20.10+
- Docker Compose 2.0+
- Node.js 18+ (for Claude CLI)
- git (for updates)

## Quick Deployment Commands

After pushing your image, run these commands on your server:

```bash
# 1. Install Docker and Docker Compose (if not installed)
curl -fsSL https://get.docker.com -o get-docker.sh && sudo sh get-docker.sh
sudo usermod -aG docker $USER
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# 2. Login to Docker Hub
docker login

# 3. Create project directory
mkdir -p ~/claude-bot-prod && cd ~/claude-bot-prod

# 4. Create required directories
mkdir -p data target_project
chmod 755 data target_project

# 5. Install and authenticate Claude CLI (CRITICAL STEP)
curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
sudo apt-get install -y nodejs
sudo npm install -g @anthropic-ai/claude-code

# Authenticate Claude CLI
claude auth login

# Verify authentication
claude auth status

# 6. Pull the image
docker pull kroschu/claude-notifer-chat-amd64:latest

# 7. Copy your config files to server:
# - docker-compose.remote.yml
# - .env (with production settings)

# 8. Deploy the bot
docker-compose -f docker-compose.remote.yml up -d

# 9. Verify deployment
docker-compose -f docker-compose.remote.yml ps
docker-compose -f docker-compose.remote.yml logs -f
```

## Detailed Step-by-Step Instructions

### 1. Server Preparation

#### Install Docker & Docker Compose:
```bash
# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER

# Install Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# Logout and login again for group changes to take effect
```

#### Install Node.js and Claude CLI:
```bash
# Install Node.js 18+
curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
sudo apt-get install -y nodejs

# Install Claude CLI globally
sudo npm install -g @anthropic-ai/claude-code

# Verify installation
claude --version
```

### 2. Claude CLI Authentication (CRITICAL)

```bash
# Login to Claude CLI (this creates ~/.claude directory)
claude auth login

# Follow the prompts to authenticate with your Anthropic account
# This step is MANDATORY - the bot cannot function without Claude CLI auth

# Verify authentication
claude auth status
# Should show: ✓ Authenticated as your@email.com

# Check that ~/.claude directory exists
ls -la ~/.claude
```

### 3. Project Setup

```bash
# Create project directory
mkdir -p ~/claude-bot-prod
cd ~/claude-bot-prod

# Create required directories with proper permissions
mkdir -p data target_project
chmod 755 data target_project

# The data directory will store:
# - SQLite database (bot.db)
# - Session files
# - Logs and cache
```

### 4. Configuration Files

Transfer these files to your server's `~/claude-bot-prod/` directory:

1. **docker-compose.remote.yml** - Production compose configuration
2. **.env** - Environment variables (update for production)

#### Production .env Template:
```bash
# Telegram Configuration
TELEGRAM_BOT_TOKEN=your_production_bot_token
TELEGRAM_BOT_USERNAME=your_bot_username

# Security (IMPORTANT: Set for production)
ALLOWED_USERS=123456789,987654321  # Your Telegram user IDs
ENABLE_TOKEN_AUTH=false            # Or true with token secret

# Paths (use container paths)
APPROVED_DIRECTORY=/app/target_project
TARGET_PROJECT_PATH=/app/target_project

# Claude Settings
USE_SDK=true
CLAUDE_MODEL=claude-3-5-sonnet-20241022
ANTHROPIC_API_KEY=your_api_key_if_needed

# Monitoring
CLAUDE_AVAILABILITY_MONITOR=true
CLAUDE_AVAILABILITY_NOTIFY_CHAT_IDS=-1001234567890
CLAUDE_AVAILABILITY_CHECK_INTERVAL=300  # 5 minutes

# Production Settings
DEBUG=false
LOG_LEVEL=INFO
DEVELOPMENT_MODE=false

# Database
DATABASE_URL=sqlite:////app/data/bot.db
```

### 5. Docker Hub Authentication

```bash
# Login to Docker Hub
docker login
# Enter your Docker Hub username and password/token
```

### 6. Deployment

```bash
# Pull the latest image
docker pull kroschu/claude-notifer-chat-amd64:latest

# Start the bot
docker-compose -f docker-compose.remote.yml up -d

# Verify container is running
docker-compose -f docker-compose.remote.yml ps
```

### 7. Verification and Monitoring

```bash
# Check container status
docker-compose -f docker-compose.remote.yml ps

# View logs
docker-compose -f docker-compose.remote.yml logs -f claude_bot

# Check health status
docker-compose -f docker-compose.remote.yml exec claude_bot python -c "
try:
    from src.config.settings import Settings
    settings = Settings()
    print('✓ Configuration loaded successfully')
    print(f'✓ Bot: {settings.telegram_bot_username}')
    print(f'✓ Database: {settings.database_url}')
except Exception as e:
    print(f'✗ Error: {e}')
"

# Test Telegram bot response (send /start to your bot)
```

## Management Commands

### Update Deployment:
```bash
# Pull latest image
docker-compose -f docker-compose.remote.yml pull

# Recreate containers with new image
docker-compose -f docker-compose.remote.yml up -d

# Remove old images
docker image prune -f
```

### View Logs:
```bash
# Real-time logs
docker-compose -f docker-compose.remote.yml logs -f

# Last 100 lines
docker-compose -f docker-compose.remote.yml logs --tail=100

# Logs for specific service
docker-compose -f docker-compose.remote.yml logs claude_bot
```

### Restart Services:
```bash
# Restart bot
docker-compose -f docker-compose.remote.yml restart claude_bot

# Restart all services
docker-compose -f docker-compose.remote.yml restart
```

### Stop Services:
```bash
# Stop but keep containers
docker-compose -f docker-compose.remote.yml stop

# Stop and remove containers
docker-compose -f docker-compose.remote.yml down

# Stop and remove containers + volumes
docker-compose -f docker-compose.remote.yml down -v
```

## Troubleshooting

### Common Issues:

1. **Bot not responding to commands:**
   ```bash
   # Check if container is running
   docker-compose -f docker-compose.remote.yml ps
   
   # Check logs for errors
   docker-compose -f docker-compose.remote.yml logs claude_bot
   
   # Verify .env configuration
   docker-compose -f docker-compose.remote.yml exec claude_bot env | grep TELEGRAM
   ```

2. **Claude CLI authentication issues:**
   ```bash
   # Re-authenticate Claude CLI on host
   claude auth login
   claude auth status
   
   # Verify ~/.claude directory permissions
   ls -la ~/.claude
   
   # Restart container after re-auth
   docker-compose -f docker-compose.remote.yml restart
   ```

3. **Database connection errors:**
   ```bash
   # Check if data directory exists and is writable
   ls -la ./data/
   
   # Check container permissions
   docker-compose -f docker-compose.remote.yml exec claude_bot ls -la /app/data/
   ```

4. **Memory/CPU issues:**
   ```bash
   # Monitor resource usage
   docker stats
   
   # Adjust limits in docker-compose.remote.yml if needed
   ```

### Logs Location:
- **Container logs**: `docker-compose logs`
- **Application logs**: `./data/` directory
- **System logs**: `/var/log/` on host

## Security Checklist

- [ ] Claude CLI properly authenticated
- [ ] .env file contains production tokens
- [ ] ALLOWED_USERS configured with your Telegram ID
- [ ] Container running as non-root user (1001:1001)
- [ ] ~/.claude directory mounted read-only
- [ ] Firewall configured (only necessary ports open)
- [ ] Docker daemon secured
- [ ] Regular backups configured

## Backup Strategy

### Manual Backup:
```bash
# Create backup of critical data
tar -czf "claude-bot-backup-$(date +%Y%m%d-%H%M).tar.gz" \
    data/ \
    target_project/ \
    ~/.claude/ \
    .env \
    docker-compose.remote.yml
```

### Automated Backup Script:
```bash
#!/bin/bash
# backup.sh - Add to crontab for automated backups

BACKUP_DIR="/var/backups/claude-bot"
DATE=$(date +%Y%m%d-%H%M)

mkdir -p "$BACKUP_DIR"

# Backup application data
tar -czf "$BACKUP_DIR/claude-bot-$DATE.tar.gz" \
    -C ~/claude-bot-prod \
    data/ target_project/ .env docker-compose.remote.yml

# Backup Claude CLI auth
tar -czf "$BACKUP_DIR/claude-auth-$DATE.tar.gz" \
    -C ~/ .claude/

# Keep only last 7 days of backups
find "$BACKUP_DIR" -name "*.tar.gz" -mtime +7 -delete

echo "Backup completed: $BACKUP_DIR/claude-bot-$DATE.tar.gz"
```

### Add to Crontab:
```bash
# Edit crontab
crontab -e

# Add daily backup at 2 AM
0 2 * * * /path/to/backup.sh >> /var/log/claude-bot-backup.log 2>&1
```