# Development Guide

This document provides guidance for developing the Claude Code Telegram Bot using both Docker and virtual environment approaches.

## Development Approaches

### 1. Docker Development (Production-like)

**Pros:**
- Consistent environment across systems
- Isolated dependencies
- Production-ready containers
- Easy deployment

**Cons:**
- Slower iteration cycle (rebuild required for changes)
- Larger resource usage
- Build time overhead

**Usage:**
```bash
# Build and start
docker compose up -d --build

# View logs
docker compose logs claude_bot -f

# Restart after code changes
docker compose restart claude_bot

# Full rebuild (when dependencies change)
docker compose down
docker compose up -d --build
```

### 2. Virtual Environment Development (Replit-style)

**Pros:**
- Instant code changes (no rebuild)
- Faster iteration cycle
- Lower resource usage
- Direct debugging access

**Cons:**
- System dependency management
- Environment consistency challenges
- Manual setup required

**Setup:**
```bash
# One-time setup
./setup-venv.sh

# Configure environment
nano .env

# Start development
./run-dev.sh
```

## Quick Start for venv Development

1. **Initial Setup:**
```bash
./setup-venv.sh
```

2. **Configure Environment:**
```bash
# Edit .env with your bot token and settings
nano .env
```

3. **Start Development:**
```bash
# For normal operation
./run-bot.sh

# For debugging
./run-dev.sh
```

## Development Scripts

After running `setup-venv.sh`, you'll have these scripts:

- `./run-bot.sh` - Start the bot in production mode
- `./run-dev.sh` - Start with debug logging
- `./run-tests.sh` - Run test suite
- `./run-lint.sh` - Code quality checks (black, isort, flake8, mypy)

## Development Workflow Comparison

### Docker Workflow
```bash
# Make code changes
nano src/bot/handlers/command.py

# Rebuild and restart (slow)
docker compose up -d --build

# Check logs
docker compose logs claude_bot -f
```

### venv Workflow
```bash
# Make code changes
nano src/bot/handlers/command.py

# Restart immediately (fast)
./run-dev.sh

# No rebuild needed!
```

## Authentication Setup

### Docker (Automated)
- Uses `claude-auth.tar.gz` archive
- Automatic extraction in container
- Consistent authentication state

### venv (Manual)
```bash
# Authenticate Claude CLI
claude auth login

# Verify authentication
claude auth status
```

## Code Quality

Both approaches support the same quality tools:

```bash
# In Docker
docker exec claude-code-bot poetry run black src/

# In venv
./run-lint.sh
```

## Debugging

### Docker Debugging
```bash
# Access container shell
docker exec -it claude-code-bot bash

# Check Claude CLI
docker exec claude-code-bot claude auth status

# View detailed logs
docker compose logs claude_bot --tail=100
```

### venv Debugging
```bash
# Direct Python debugging
poetry shell
python -m src.main --debug

# Interactive debugging with pdb
python -c "import pdb; pdb.set_trace(); import src.main"
```

## When to Use Which Approach

### Use Docker When:
- Preparing for production deployment
- Need consistent environment
- Working with complex system dependencies
- Sharing with team (same environment)

### Use venv When:
- Active development and testing
- Rapid iteration needed
- Debugging complex issues
- Local development only

## Migration Between Approaches

### From Docker to venv:
```bash
# Stop Docker
docker compose down

# Setup venv
./setup-venv.sh

# Copy environment settings
cp .env .env.backup  # if you have custom settings

# Start development
./run-dev.sh
```

### From venv to Docker:
```bash
# Stop venv bot (Ctrl+C)

# Update dependencies if changed
poetry export -f requirements.txt --output requirements.txt

# Start Docker
docker compose up -d --build
```

## Best Practices

1. **Development**: Use venv for faster iteration
2. **Testing**: Test in both environments before deployment
3. **Production**: Always use Docker for deployment
4. **Authentication**: Keep Claude CLI auth up to date in both environments
5. **Dependencies**: Test dependency changes in Docker before deploying

## Troubleshooting

### Common venv Issues:
- **Poetry not found**: Install poetry and add to PATH
- **Claude CLI auth**: Run `claude auth login`
- **Python version**: Ensure Python 3.11+

### Common Docker Issues:
- **Auth missing**: Recreate `claude-auth.tar.gz` archive
- **Code not updating**: Full rebuild with `--no-cache`
- **Port conflicts**: Check if other services use same ports

## Performance Comparison

| Aspect | Docker | venv |
|--------|--------|------|
| Startup time | 30-60s (build) | 2-3s |
| Code change cycle | 30-60s (rebuild) | 2-3s (restart) |
| Memory usage | ~500MB | ~200MB |
| Debugging | Limited | Full access |
| Deployment ready | ✅ Yes | ❌ No |

Choose the approach that fits your current development phase and requirements.