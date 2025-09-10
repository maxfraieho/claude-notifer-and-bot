# 🚀 Deployment Guide for Claude Code Telegram Bot

## 📦 Docker Hub Image

The latest stable version of the bot is available on Docker Hub:

```bash
# Latest stable version
docker pull maxfraieho/claude-code-telegram:latest

# Specific version
docker pull maxfraieho/claude-code-telegram:v0.1.1
```

## 🔧 Quick Deployment

### 1. Download deployment files

```bash
# Download the docker-compose.yml and example .env
curl -O https://raw.githubusercontent.com/maxfraieho/claude-notifer-and-bot/main/docker-compose.prod.yml
curl -O https://raw.githubusercontent.com/maxfraieho/claude-notifer-and-bot/main/.env.example
```

### 2. Configure environment

```bash
# Copy and edit the environment file
cp .env.example .env
nano .env
```

Required configuration:
```bash
# Telegram Bot Configuration
TELEGRAM_BOT_TOKEN=your_bot_token_here
TELEGRAM_BOT_USERNAME=your_bot_username

# Security (choose one or both)
ALLOWED_USERS=123456789,987654321  # Telegram user IDs
ENABLE_TOKEN_AUTH=true
AUTH_TOKEN_SECRET=your_secret_here

# Claude settings
USE_SDK=true  # Use Python SDK instead of CLI subprocess
ANTHROPIC_API_KEY=your_api_key  # Optional if logged into Claude CLI
CLAUDE_MODEL=claude-3-5-sonnet-20241022

# Directory settings
APPROVED_DIRECTORY=/app/target_project
TARGET_PROJECT_PATH=/app/target_project
```

### 3. Deploy with Docker Compose

```bash
# Start the bot
docker-compose -f docker-compose.prod.yml up -d

# Check logs
docker-compose -f docker-compose.prod.yml logs -f claude_bot

# Stop the bot
docker-compose -f docker-compose.prod.yml down
```

## 🐳 Production Docker Compose

Save this as `docker-compose.prod.yml`:

```yaml
services:
  claude_bot:
    image: maxfraieho/claude-code-telegram:latest
    container_name: claude-code-bot-prod
    restart: unless-stopped
    env_file:
      - .env
    volumes:
      - ./data:/app/data
      - ./target_project:/app/target_project
    working_dir: /app
    healthcheck:
      test: ["CMD", "python", "-c", "import sys; sys.exit(0) if __import__('src.main') else sys.exit(1)"]
      interval: 60s
      timeout: 10s
      retries: 3
      start_period: 30s
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"

volumes:
  data:
```

## 🔄 Updating to Latest Version

```bash
# Pull the latest image
docker-compose -f docker-compose.prod.yml pull

# Restart with new image
docker-compose -f docker-compose.prod.yml up -d

# Clean up old images (optional)
docker image prune
```

## 📊 Monitoring and Maintenance

### Check bot status
```bash
# View logs
docker-compose -f docker-compose.prod.yml logs claude_bot

# Check container health
docker-compose -f docker-compose.prod.yml ps

# Enter container for debugging
docker-compose -f docker-compose.prod.yml exec claude_bot bash
```

### Backup data
```bash
# Backup database and data
tar -czf bot-backup-$(date +%Y%m%d).tar.gz data/
```

## 🚨 Version 0.1.1 Changes

This version includes critical fixes:

- ✅ **Fixed duplicated logging output** - Clean, readable logs
- ✅ **Resolved Claude CLI directory creation** - No more ENOENT errors  
- ✅ **Improved Telegram message parsing** - No more entity parsing errors
- ✅ **Enhanced error handling** - Better user experience

## 🔒 Security Notes

1. **Use HTTPS URLs** for webhooks in production
2. **Regularly rotate** your `AUTH_TOKEN_SECRET`
3. **Limit user access** with `ALLOWED_USERS` or token auth
4. **Monitor logs** for suspicious activity
5. **Keep the container updated** to latest versions

## 📞 Support

- 📖 **Documentation**: [GitHub Repository](https://github.com/maxfraieho/claude-notifer-and-bot)
- 🐛 **Issues**: [GitHub Issues](https://github.com/maxfraieho/claude-notifer-and-bot/issues)
- 💬 **Discussions**: [GitHub Discussions](https://github.com/maxfraieho/claude-notifer-and-bot/discussions)

## 📈 Next Steps

After deployment:

1. Test bot with `/start` command in Telegram
2. Use `/projects` to see available projects
3. Try sending a simple coding request
4. Monitor logs for any issues
5. Set up monitoring and alerts if needed

---

*Last updated: $(date "+%Y-%m-%d")*