# Claude Code Telegram Bot - Deployment Guide

## Quick Deployment (Standalone Mode)

**NEW**: For easy deployment on any server without volume mounting complexity.

### Using Docker Compose (Recommended)

1. **Clone the repository:**
```bash
git clone https://github.com/maxfraieho/claude-notifer-and-bot.git
cd claude-notifer-and-bot
```

2. **Create environment file:**
```bash
cp .env.example .env
# Edit .env with your settings
```

3. **Required environment variables:**
```bash
# Required
TELEGRAM_BOT_TOKEN=your_bot_token_here
TELEGRAM_BOT_USERNAME=your_bot_username
APPROVED_DIRECTORY=/app/target_project

# Authentication (choose one or both)
ALLOWED_USERS=123456789,987654321  # Telegram user IDs
ENABLE_TOKEN_AUTH=true
AUTH_TOKEN_SECRET=your_secret_here

# Claude Authentication (for standalone mode)
ANTHROPIC_API_KEY=your_anthropic_api_key  # Recommended for standalone deployment
```

4. **Deploy:**
```bash
docker-compose up -d
```

### Using Docker Hub Image (Simplest)

```bash
# Pull the standalone image
docker pull kroschu/claude-code-telegram:1.0.4-standalone

# Run with minimal configuration
docker run -d \
  --name claude-code-bot \
  --restart unless-stopped \
  -e TELEGRAM_BOT_TOKEN=your_bot_token \
  -e TELEGRAM_BOT_USERNAME=your_bot_username \
  -e ANTHROPIC_API_KEY=your_api_key \
  -e ALLOWED_USERS=your_telegram_user_id \
  -v ./target_project:/app/target_project \
  kroschu/claude-code-telegram:1.0.4-standalone
```

## Authentication Options

### 1. Standalone Mode (Default - Recommended)
- ✅ No volume mounting required
- ✅ Uses `ANTHROPIC_API_KEY` environment variable
- ✅ Container handles Claude CLI authentication internally
- ✅ Perfect for clean deployments on new servers
- ✅ No permission issues

### 2. Host Authentication Mount (Advanced)
If you already have Claude CLI configured on host:
```yaml
# Uncomment in docker-compose.yml
volumes:
  - ~/.claude:/home/claudebot/.claude
```

## Version Comparison

| Version | Description | Volume Mount | Use Case |
|---------|-------------|--------------|----------|
| `1.0.4-standalone` | **Self-contained** | Optional | **✅ Production deployment** |
| `latest` | Current with host auth | Required | Local development |
| `1.0.3` | Legacy with mounting | Required | Existing setups |

## Quick Start for New Server

**Minimal setup for new server deployment:**

1. **Install Docker:**
```bash
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER
# Logout and login again
```

2. **Create deployment directory:**
```bash
mkdir claude-bot && cd claude-bot
```

3. **Create docker-compose.yml:**
```yaml
version: '3.8'
services:
  claude_bot:
    image: kroschu/claude-code-telegram:1.0.4-standalone
    container_name: claude-code-bot
    restart: unless-stopped
    environment:
      - TELEGRAM_BOT_TOKEN=your_bot_token
      - TELEGRAM_BOT_USERNAME=your_bot_username  
      - ANTHROPIC_API_KEY=your_api_key
      - ALLOWED_USERS=your_telegram_user_id
      - APPROVED_DIRECTORY=/app/target_project
    volumes:
      - ./data:/app/data
      - ./target_project:/app/target_project
    healthcheck:
      test: ["CMD", "python", "-c", "import sys; sys.exit(0) if __import__('src.main') else sys.exit(1)"]
      interval: 60s
      timeout: 10s
      retries: 3
```

4. **Start:**
```bash
mkdir -p data target_project
docker-compose up -d
```

## Troubleshooting

### Permission Issues
- ✅ Use standalone mode (no volume mounting)
- ✅ Ensure `ANTHROPIC_API_KEY` is set
- ❌ No Docker user mapping issues

### Authentication Problems
1. Verify `ANTHROPIC_API_KEY` is valid
2. Check bot token and username
3. Ensure user IDs are correct in `ALLOWED_USERS`

### Migration from Previous Versions
```bash
# Update image to standalone
docker-compose down
# Edit docker-compose.yml: image: kroschu/claude-code-telegram:1.0.4-standalone
# Add ANTHROPIC_API_KEY to environment
# Comment out ~/.claude volume mount
docker-compose up -d
```

## Legacy Deployment (with Host Authentication)

<details>
<summary>Click to expand legacy deployment method</summary>

### Prerequisites (Legacy)
- Docker and Docker Compose installed
- Telegram Bot Token from @BotFather  
- Your Telegram User ID (get from @userinfobot)
- **ВАЖЛИВО**: Автентифікований Claude CLI (папка ~/.claude з вашої робочої машини)

### Step 1: Prepare Claude CLI Authentication
**On your current working machine** (where Claude CLI is authenticated):
```bash
tar -czf claude-config.tar.gz ~/.claude
```

### Step 2-5: [Previous deployment steps remain the same]
</details>

## Support

- **Recommended**: Use `1.0.4-standalone` for new deployments
- For issues: Check logs with `docker-compose logs claude_bot`
- Authentication: Standalone mode handles it automatically with `ANTHROPIC_API_KEY`