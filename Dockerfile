# Production-ready Dockerfile for Claude Telegram Bot
# Built for remote server deployment with user: kroschu
# Image: kroschu/claude-code-telegram:latest

FROM python:3.11-slim

# Build arguments for flexibility
ARG USER_UID=1000
ARG USER_GID=1000
ARG USERNAME=claudebot

# Install system dependencies including Node.js for Claude CLI
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    git \
    jq \
    gcc \
    g++ \
    ca-certificates \
    gnupg \
    && curl -fsSL https://deb.nodesource.com/gpgkey/nodesource-repo.gpg.key | gpg --dearmor -o /etc/apt/keyrings/nodesource.gpg \
    && echo "deb [signed-by=/etc/apt/keyrings/nodesource.gpg] https://deb.nodesource.com/node_20.x nodistro main" | tee /etc/apt/sources.list.d/nodesource.list \
    && apt-get update \
    && apt-get install -y --no-install-recommends nodejs \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/* \
    && rm -rf /tmp/* /var/tmp/*

# Create non-root user with consistent UID/GID for volume mounting
RUN groupadd -g ${USER_GID} ${USERNAME} \
    && useradd -m -u ${USER_UID} -g ${USER_GID} -s /bin/bash ${USERNAME}

# Create application and data directories with proper ownership
RUN mkdir -p /app/data /app/target_project \
    && chown -R ${USERNAME}:${USERNAME} /app

# Set environment variables
ENV HOME=/home/${USERNAME}
ENV PATH="/home/${USERNAME}/.local/bin:$PATH"
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV TZ=Europe/Kiev

# Switch to non-root user
USER ${USERNAME}
WORKDIR /home/${USERNAME}

# Install Poetry
RUN curl -sSL https://install.python-poetry.org | python3 -
ENV PATH="/home/${USERNAME}/.local/bin:${PATH}"

# Copy dependency files for Poetry
COPY --chown=${USERNAME}:${USERNAME} pyproject.toml poetry.lock README.md ./

# Configure Poetry and install Python dependencies
RUN poetry config virtualenvs.create false \
    && poetry config virtualenvs.in-project false \
    && poetry install --only=main --no-root --no-cache

# Install Claude CLI and create necessary directories
RUN mkdir -p ~/.local/bin ~/.claude/plugins/repos \
    && npm install @anthropic-ai/claude-code \
    && ln -s "$(pwd)/node_modules/.bin/claude" ~/.local/bin/claude

# Copy application code to /app
COPY --chown=${USERNAME}:${USERNAME} src/ /app/src/
COPY --chown=${USERNAME}:${USERNAME} CLAUDE.md /app/

# Set working directory to /app
WORKDIR /app

# Create simple entrypoint script (relies on mounted .claude directory)
RUN echo '#!/bin/bash\n\
# Create Claude CLI directory structure if not mounted\n\
mkdir -p ~/.claude/plugins/repos\n\
\n\
# Start the application\n\
exec python -m src.main "$@"\n' > /home/${USERNAME}/entrypoint.sh \
    && chmod +x /home/${USERNAME}/entrypoint.sh

# Health check with comprehensive validation
HEALTHCHECK --interval=60s --timeout=15s --start-period=45s --retries=3 \
    CMD python -c "try: import src.main; from src.config.settings import Settings; Settings(); print('✓ Health check passed'); exit(0)\nexcept Exception as e: print(f'✗ Health check failed: {e}'); exit(1)"

# Labels for container management
LABEL maintainer="kroschu" \
      version="1.0.4-standalone" \
      description="Claude Code Telegram Bot - Remote access to Claude CLI via Telegram" \
      org.label-schema.vcs-url="https://github.com/maxfraieho/claude-notifer-and-bot"

# Default command with authentication setup
ENTRYPOINT ["/home/claudebot/entrypoint.sh"]