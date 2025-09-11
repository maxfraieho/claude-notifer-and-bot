#!/bin/bash

# Claude Telegram Bot - Quick Deployment Script
# This script prepares everything needed for deployment on a new server

set -e

echo "🚀 Claude Telegram Bot - Deployment Preparation"
echo "=============================================="

# Check if we're in the correct directory
if [[ ! -f "docker-compose.prod.yml" ]]; then
    echo "❌ Error: Run this script from the project root directory"
    exit 1
fi

# Create deployment package directory
DEPLOY_DIR="deployment-package"
echo "📦 Creating deployment package..."
rm -rf "$DEPLOY_DIR"
mkdir -p "$DEPLOY_DIR"

# Copy deployment files
cp docker-compose.deploy.yml "$DEPLOY_DIR/docker-compose.yml"
cp .env.template "$DEPLOY_DIR/"
cp DEPLOYMENT.md "$DEPLOY_DIR/"

# Create Claude config archive
echo "🔐 Creating Claude configuration archive..."
if [[ -d "claude-config" ]]; then
    tar -czf "$DEPLOY_DIR/claude-config.tar.gz" -C . claude-config/
    echo "✅ Claude config archived successfully"
else
    echo "⚠️  Warning: claude-config directory not found"
    echo "   You'll need to transfer your Claude CLI config manually"
fi

# Create quick setup script
cat > "$DEPLOY_DIR/quick-setup.sh" << 'EOF'
#!/bin/bash

# Quick Setup Script for Claude Telegram Bot
set -e

echo "🚀 Setting up Claude Telegram Bot..."

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo "❌ Docker not found. Please install Docker first:"
    echo "   curl -fsSL https://get.docker.com -o get-docker.sh"
    echo "   sudo sh get-docker.sh"
    exit 1
fi

# Check if Docker Compose is available
if ! docker compose version &> /dev/null; then
    echo "❌ Docker Compose not found. Please install docker-compose-plugin"
    exit 1
fi

# Create required directories
echo "📁 Creating directories..."
mkdir -p data target_project

# Extract Claude config if exists
if [[ -f "claude-config.tar.gz" ]]; then
    echo "🔐 Extracting Claude configuration..."
    tar -xzf claude-config.tar.gz
    echo "✅ Claude config extracted"
else
    echo "⚠️  claude-config.tar.gz not found"
    echo "   Please ensure you have transferred your Claude CLI authentication"
fi

# Setup environment file
if [[ ! -f ".env" ]]; then
    if [[ -f ".env.template" ]]; then
        cp .env.template .env
        echo "📝 Environment template copied to .env"
        echo "⚠️  IMPORTANT: Edit .env file with your configuration before starting!"
    else
        echo "❌ .env.template not found"
        exit 1
    fi
fi

echo "✅ Setup completed!"
echo ""
echo "Next steps:"
echo "1. Edit .env file with your Telegram bot token and settings"
echo "2. Run: docker compose up -d"
echo "3. Check logs: docker compose logs -f claude_bot"
echo ""
echo "See DEPLOYMENT.md for detailed instructions."
EOF

chmod +x "$DEPLOY_DIR/quick-setup.sh"

# Create a summary file
cat > "$DEPLOY_DIR/README.txt" << EOF
Claude Telegram Bot - Deployment Package
========================================

This package contains everything needed to deploy the Claude Telegram Bot on a new server.

Files included:
- docker-compose.yml: Production Docker Compose configuration
- .env.template: Environment variables template
- DEPLOYMENT.md: Detailed deployment guide
- claude-config.tar.gz: Claude CLI authentication (if available)
- quick-setup.sh: Automated setup script

Quick start:
1. Transfer this entire directory to your new server
2. Run: ./quick-setup.sh
3. Edit .env file with your configuration
4. Run: docker compose up -d

Docker image: kroschu/claude-code-telegram:v0.1.2-working

For detailed instructions, see DEPLOYMENT.md
EOF

echo "✅ Deployment package created in '$DEPLOY_DIR/'"
echo ""
echo "📋 Package contents:"
ls -la "$DEPLOY_DIR/"
echo ""
echo "🚀 Ready for deployment!"
echo "   Transfer the '$DEPLOY_DIR' directory to your new server"
echo "   ⚠️  ВАЖЛИВО: Потрібна тільки папка ~/.claude (БЕЗ API токенів!)"
echo "   Follow the instructions in DEPLOYMENT.md"