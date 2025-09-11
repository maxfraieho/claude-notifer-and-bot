# Claude Telegram Bot - Deployment Guide

## Quick Deployment on New Server

This guide will help you deploy the working Claude Telegram Bot on a new server.

## Prerequisites

- Docker and Docker Compose installed
- Telegram Bot Token from @BotFather
- Your Telegram User ID (get from @userinfobot)
- Claude CLI authenticated on your local machine

## Step 1: Prepare Claude CLI Authentication

**On your current working machine** (where Claude CLI is authenticated):

```bash
# Copy your authenticated Claude config
tar -czf claude-config.tar.gz ~/.claude
```

Transfer this file to your new server.

## Step 2: Server Setup

**On your new server:**

1. **Install Docker and Docker Compose:**
```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER

# Install Docker Compose
sudo apt install docker-compose-plugin

# Logout and login again for group changes to take effect
```

2. **Create project directory:**
```bash
mkdir claude-telegram-bot
cd claude-telegram-bot
```

3. **Download deployment files:**
```bash
# Download the deployment configuration
curl -o docker-compose.yml https://raw.githubusercontent.com/maxfraieho/claude-notifer-and-bot/main/docker-compose.deploy.yml
curl -o .env.template https://raw.githubusercontent.com/maxfraieho/claude-notifer-and-bot/main/.env.template
```

## Step 3: Configure Environment

1. **Create environment file:**
```bash
cp .env.template .env
nano .env
```

2. **Fill in required values in .env:**
```bash
# REQUIRED - Get from @BotFather
TELEGRAM_BOT_TOKEN=1234567890:ABCdefGHIjklMNOpqrsTUVwxyz

# REQUIRED - Your bot username (without @)
TELEGRAM_BOT_USERNAME=YourBotName_bot

# REQUIRED - Your Telegram user ID (get from @userinfobot)
ALLOWED_USERS=123456789

# OPTIONAL - Chat ID for notifications
CLAUDE_AVAILABILITY_NOTIFY_CHAT_IDS=123456789
```

## Step 4: Set Up Claude Authentication

1. **Extract Claude config:**
```bash
# Extract the claude-config.tar.gz you transferred from working machine
tar -xzf claude-config.tar.gz
mv .claude claude-config
```

2. **Create required directories:**
```bash
mkdir -p data target_project
```

## Step 5: Deploy

1. **Start the bot:**
```bash
docker-compose up -d
```

2. **Check logs:**
```bash
docker-compose logs -f claude_bot
```

3. **Test the bot:**
Send a message to your Telegram bot to verify it's working.

## Directory Structure

After setup, your directory should look like:

```
claude-telegram-bot/
├── docker-compose.yml
├── .env
├── claude-config/           # Claude CLI authentication
│   ├── .credentials.json
│   └── ...
├── data/                    # Bot data persistence
├── target_project/         # Your project files
└── claude-config.tar.gz    # Original backup
```

## Managing the Bot

### Start/Stop
```bash
# Start
docker-compose up -d

# Stop
docker-compose down

# Restart
docker-compose restart
```

### View Logs
```bash
# Follow logs
docker-compose logs -f claude_bot

# View recent logs
docker-compose logs --tail=100 claude_bot
```

### Update Bot
```bash
# Pull latest image
docker-compose pull

# Restart with new image
docker-compose up -d
```

## Troubleshooting

### Bot shows "Claude Code exited with code 1"

1. Check Claude authentication:
```bash
docker exec claude-code-bot-prod claude auth status
```

2. If authentication failed, fix permissions:
```bash
docker exec -u root claude-code-bot-prod chown claudebot:claudebot /home/claudebot/.claude/.credentials.json
docker-compose restart
```

### Bot not responding to messages

1. Check bot is running:
```bash
docker-compose ps
```

2. Check logs for errors:
```bash
docker-compose logs claude_bot
```

3. Verify your user ID is in ALLOWED_USERS

### Performance Issues

1. Check resource usage:
```bash
docker stats claude-code-bot-prod
```

2. Adjust resource limits in docker-compose.yml if needed

## Security Notes

- Keep your `.env` file secure and never commit it to version control
- The `claude-config` directory contains sensitive authentication data
- Consider setting up firewall rules if the server is public-facing
- Regularly update the Docker image for security patches

## Support

If you encounter issues:
1. Check the troubleshooting section above
2. Review logs for specific error messages
3. Ensure all environment variables are correctly set
4. Verify Claude CLI authentication is working

## Image Versions

- **Production**: `kroschu/claude-code-telegram:v0.1.2-working`
- **Latest**: `kroschu/claude-code-telegram:latest`

The `v0.1.2-working` tag contains the tested and verified working version.