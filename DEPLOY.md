# 🚀 Production Deployment Guide - Claude Code Telegram Bot

> **Unified DevOps pipeline for remote server deployment with Docker Hub integration**  
> **Maintainer:** kroschu | **Docker Hub:** `kroschu/claude-code-telegram`

## 📦 Quick Remote Deployment (Recommended)

### Prerequisites on Remote Server
```bash
# Ensure Docker & Docker Compose are installed
docker --version && docker-compose --version

# Ensure you have Claude CLI authenticated
claude auth status
# If not authenticated, run: claude auth login
```

### 1. Download Production Files
```bash
# Create deployment directory
mkdir -p ~/claude-bot-deploy && cd ~/claude-bot-deploy

# Download production configuration
curl -O https://raw.githubusercontent.com/maxfraieho/claude-notifer-and-bot/main/docker-compose.prod.yml
curl -O https://raw.githubusercontent.com/maxfraieho/claude-notifer-and-bot/main/.env.example

# Create required directories
mkdir -p data target_project
```

### 2. Configure Environment
```bash
# Copy and edit environment file
cp .env.example .env
nano .env  # or vim .env
```

**Required .env configuration:**
```bash
# Telegram Bot Configuration
TELEGRAM_BOT_TOKEN=your_bot_token_here
TELEGRAM_BOT_USERNAME=your_bot_username

# Security Configuration (choose one or both)
ALLOWED_USERS=123456789,987654321  # Your Telegram user IDs
ENABLE_TOKEN_AUTH=true
AUTH_TOKEN_SECRET=your_secure_random_secret

# Claude Configuration
USE_SDK=true
ANTHROPIC_API_KEY=your_anthropic_api_key  # Optional if Claude CLI is authenticated
CLAUDE_MODEL=claude-3-5-sonnet-20241022

# Directory Configuration
APPROVED_DIRECTORY=/app/target_project
TARGET_PROJECT_PATH=/app/target_project
DATABASE_URL=sqlite:///app/data/bot.db
```

### 3. Deploy Bot
```bash
# Pull latest image and start the bot
docker-compose -f docker-compose.prod.yml pull
docker-compose -f docker-compose.prod.yml up -d

# Verify deployment
docker-compose -f docker-compose.prod.yml ps
docker-compose -f docker-compose.prod.yml logs -f claude_bot
```

### 4. Verify Deployment
```bash
# Check bot health
docker-compose -f docker-compose.prod.yml exec claude_bot python -c "
import src.main
from src.config.settings import Settings
print('✓ Bot is healthy and ready')
"

# Test Telegram bot with /start command
```

## 🔄 Version Updates & CI/CD Pipeline

### For Developers: Building & Releasing New Versions

#### 1. Bump Version & Commit Changes
```bash
# Update version in pyproject.toml
sed -i 's/version = ".*"/version = "0.1.2"/' pyproject.toml

# Commit changes
git add .
git commit -m "feat: add new feature XYZ

🤖 Generated with [Claude Code](https://claude.ai/code)

Co-Authored-By: Claude <noreply@anthropic.com>"

git push origin main
```

#### 2. Build & Push Docker Image
```bash
# Login to Docker Hub with kroschu credentials
docker login -u kroschu
# Password: gfhjkm 805235io. (with dot at the end)

# Build new image with version tags
VERSION=$(grep 'version = ' pyproject.toml | cut -d'"' -f2)
docker build -t kroschu/claude-code-telegram:v$VERSION -t kroschu/claude-code-telegram:latest .

# Push both tags to Docker Hub
docker push kroschu/claude-code-telegram:v$VERSION
docker push kroschu/claude-code-telegram:latest

# Verify upload
echo "✅ New version v$VERSION pushed to: https://hub.docker.com/r/kroschu/claude-code-telegram"
```

#### 3. Create GitHub Release
```bash
# Tag the release
git tag -a v$VERSION -m "Release version $VERSION with fixes and improvements"
git push origin v$VERSION

# Create release notes on GitHub with changelog
```

### For Operators: Updating Production

#### Rolling Update (Zero Downtime)
```bash
cd ~/claude-bot-deploy

# Pull latest image
docker-compose -f docker-compose.prod.yml pull

# Rolling update with health checks
docker-compose -f docker-compose.prod.yml up -d --no-deps claude_bot

# Monitor deployment
docker-compose -f docker-compose.prod.yml logs -f --tail=50 claude_bot

# Verify health
docker-compose -f docker-compose.prod.yml exec claude_bot python -c "
try:
    import src.main
    print('✅ Update successful')
except:
    print('❌ Update failed')
    exit(1)
"
```

#### Rollback Procedure
```bash
# If something goes wrong, rollback to previous version
docker-compose -f docker-compose.prod.yml down
docker pull kroschu/claude-code-telegram:v0.1.0  # previous version
sed -i 's/:latest/:v0.1.0/' docker-compose.prod.yml
docker-compose -f docker-compose.prod.yml up -d
```

## 🔒 Claude CLI Authentication Setup

### On Remote Server (Critical Step)

Claude CLI authentication is **required** and must be set up on the host machine:

```bash
# Install Claude CLI if not present
npm install -g @anthropic-ai/claude-code

# Authenticate (this creates ~/.claude with credentials)
claude auth login
# Follow the authentication flow

# Verify authentication
claude auth status
# Should show: ✅ Authenticated

# Check that ~/.claude directory exists with proper structure
ls -la ~/.claude/
# Should contain authentication files and will be mounted into container
```

**🚨 Security Notice:**  
- The `~/.claude` directory contains your authentication credentials
- It's mounted read-only into the container for security
- Never commit these credentials to git
- Ensure proper file permissions: `chmod 600 ~/.claude/*`

## 📊 Monitoring & Maintenance

### Health Monitoring
```bash
# Check container health
docker-compose -f docker-compose.prod.yml ps

# Monitor logs
docker-compose -f docker-compose.prod.yml logs claude_bot --since 1h

# Check resource usage
docker stats claude-code-bot-prod

# Advanced health check
curl -f http://localhost:8080/health || echo "Health check endpoint not configured"
```

### Log Management
```bash
# View recent logs
docker-compose -f docker-compose.prod.yml logs --tail=100 -f claude_bot

# Export logs for analysis
docker-compose -f docker-compose.prod.yml logs claude_bot > claude-bot-$(date +%Y%m%d).log

# Clean up old logs (logs rotate automatically, but manual cleanup available)
docker system prune --volumes -f
```

### Backup & Recovery
```bash
# Backup bot data
tar -czf claude-bot-backup-$(date +%Y%m%d_%H%M%S).tar.gz \
    data/ \
    .env \
    docker-compose.prod.yml

# Restore from backup
tar -xzf claude-bot-backup-YYYYMMDD_HHMMSS.tar.gz
docker-compose -f docker-compose.prod.yml up -d
```

## 🛠️ Troubleshooting

### Common Issues & Solutions

#### 1. Bot Not Responding
```bash
# Check container status
docker-compose -f docker-compose.prod.yml ps

# Check logs for errors
docker-compose -f docker-compose.prod.yml logs --tail=50 claude_bot

# Restart if needed
docker-compose -f docker-compose.prod.yml restart claude_bot
```

#### 2. Claude CLI Authentication Errors
```bash
# Verify host authentication
claude auth status

# Re-authenticate if needed
claude auth logout
claude auth login

# Check mounted volume
docker-compose -f docker-compose.prod.yml exec claude_bot ls -la /home/claudebot/.claude/
```

#### 3. Permission Issues
```bash
# Check file ownership
ls -la data/ target_project/
sudo chown -R 1001:1001 data/ target_project/
```

#### 4. Memory Issues
```bash
# Check resource usage
docker stats claude-code-bot-prod

# Adjust memory limits in docker-compose.prod.yml if needed
# Restart after changes:
docker-compose -f docker-compose.prod.yml up -d --force-recreate
```

## 🚦 Environment-Specific Configurations

### Development Environment
```bash
# Use local development setup
git clone https://github.com/maxfraieho/claude-notifer-and-bot.git
cd claude-notifer-and-bot
cp .env.example .env  # Edit with dev tokens
docker-compose up -d --build
```

### Staging Environment
```bash
# Use staging image tag if available
sed -i 's/:latest/:staging/' docker-compose.prod.yml
docker-compose -f docker-compose.prod.yml up -d
```

## 📈 Performance Optimization

### Resource Tuning
```yaml
# Adjust in docker-compose.prod.yml based on your server capacity
deploy:
  resources:
    limits:
      memory: 2G      # Increase if processing large codebases
      cpus: '2.0'     # Increase for faster responses
    reservations:
      memory: 1G      # Minimum guaranteed memory
      cpus: '0.5'     # Minimum guaranteed CPU
```

### Network Optimization
```bash
# Enable webhook mode for better performance (optional)
# Uncomment ports section in docker-compose.prod.yml
# Add webhook configuration to .env:
echo "WEBHOOK_URL=https://your-domain.com:8443/webhook" >> .env
```

## 🔐 Security Hardening

### Additional Security Measures
```bash
# Use Docker secrets for sensitive data (production servers)
echo "your_telegram_token" | docker secret create telegram_token -
echo "your_anthropic_key" | docker secret create anthropic_key -

# Enable Docker Content Trust
export DOCKER_CONTENT_TRUST=1

# Regular security updates
docker-compose -f docker-compose.prod.yml pull
docker system prune -a -f
```

### Firewall Configuration
```bash
# Open only necessary ports
sudo ufw allow 22      # SSH
sudo ufw allow 443     # HTTPS (if using webhooks)
sudo ufw enable
```

## 📞 Support & Updates

- **Repository:** https://github.com/maxfraieho/claude-notifer-and-bot
- **Docker Hub:** https://hub.docker.com/r/kroschu/claude-code-telegram
- **Issues:** https://github.com/maxfraieho/claude-notifer-and-bot/issues
- **Maintainer:** kroschu

---

**Last Updated:** $(date '+%Y-%m-%d %H:%M:%S %Z')  
**Version:** 0.1.1  
**Pipeline Status:** ✅ Production Ready