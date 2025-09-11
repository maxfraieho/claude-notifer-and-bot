#!/bin/bash

echo "Fixing Claude authentication..."

# Stop the container
docker-compose stop claude_bot

# Remove expired credentials
docker exec claude-code-bot-prod rm -f /home/claudebot/.claude/.credentials.json 2>/dev/null || true

# Try to create a simple working state
docker-compose up -d claude_bot

echo "Authentication fix attempted. Please test the bot."