#!/bin/bash
# Claude Bot Permission Fix Script
# This script fixes the EACCES permission error for Claude CLI configuration

set -e

echo "🔧 Claude Bot Permission Fix Script"
echo "=================================="

# Define paths
DEPLOY_DIR="${HOME}/claude-bot-deploy"
CLAUDE_CONFIG_DIR="${DEPLOY_DIR}/claude_config"
HOST_CLAUDE_DIR="${HOME}/.claude"

# Create deployment directory if it doesn't exist
echo "📁 Setting up deployment directory..."
mkdir -p "$DEPLOY_DIR"
cd "$DEPLOY_DIR"

# Create required directories with correct permissions
echo "📁 Creating required directories..."
mkdir -p data target_project claude_config

# Copy Claude CLI configuration with proper permissions
if [ -d "$HOST_CLAUDE_DIR" ]; then
    echo "📋 Copying Claude CLI configuration..."
    # Copy all files from ~/.claude to ./claude_config
    cp -r "$HOST_CLAUDE_DIR/"* "$CLAUDE_CONFIG_DIR/" 2>/dev/null || true
    
    # Set proper ownership and permissions for container user (UID 1001)
    echo "🔐 Setting correct permissions..."
    sudo chown -R 1001:1001 "$CLAUDE_CONFIG_DIR"
    
    # Ensure directories are writable
    find "$CLAUDE_CONFIG_DIR" -type d -exec chmod 755 {} \;
    find "$CLAUDE_CONFIG_DIR" -type f -exec chmod 644 {} \;
    
    # Make plugins directory writable (this is where the error occurs)
    mkdir -p "$CLAUDE_CONFIG_DIR/plugins"
    chmod 755 "$CLAUDE_CONFIG_DIR/plugins"
    
    echo "✅ Claude CLI configuration copied and permissions set"
else
    echo "⚠️  WARNING: ${HOST_CLAUDE_DIR} not found!"
    echo "   Please run 'claude auth login' on the host first"
    echo "   Then re-run this script"
    exit 1
fi

# Set permissions for other directories
echo "🔐 Setting permissions for data directories..."
sudo chown -R 1001:1001 data/ target_project/

# Download production files if they don't exist
if [ ! -f "docker-compose.prod.yml" ]; then
    echo "📥 Downloading production configuration..."
    curl -O https://raw.githubusercontent.com/maxfraieho/claude-notifer-and-bot/main/docker-compose.prod.yml
fi

if [ ! -f ".env" ]; then
    echo "📥 Downloading environment template..."
    curl -O https://raw.githubusercontent.com/maxfraieho/claude-notifer-and-bot/main/.env.example
    cp .env.example .env
    echo "⚠️  Please edit .env file with your configuration before starting the bot"
fi

# Verify permissions
echo "🔍 Verifying permissions..."
ls -la claude_config/
echo ""
echo "✅ Permission fix completed successfully!"
echo ""
echo "Next steps:"
echo "1. Edit .env file with your configuration"
echo "2. Run: docker-compose -f docker-compose.prod.yml up -d"
echo "3. Check logs: docker-compose -f docker-compose.prod.yml logs -f claude_bot"
echo ""
echo "🚀 Your bot should now start without permission errors!"
