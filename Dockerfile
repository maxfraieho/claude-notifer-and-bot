FROM python:3.11-slim AS builder

# Install OS dependencies, including nodejs/npm for Claude CLI
RUN apt-get update && apt-get install -y \
    curl \
    git \
    jq \
    gcc \
    nodejs \
    npm \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN useradd -m -u 1001 -s /bin/bash claudebot

# Create target project directory and set permissions (under root)
RUN mkdir -p /app/target_project && chown claudebot:claudebot /app/target_project

# Set HOME environment variable - critical for Claude CLI to find ~/.claude
ENV HOME=/home/claudebot

# Switch to user
USER claudebot
WORKDIR /home/claudebot

# Copy dependency files for Poetry
COPY --chown=claudebot:claudebot pyproject.toml poetry.lock ./

# Install Poetry and Python dependencies
RUN curl -sSL https://install.python-poetry.org | python3 -
ENV PATH="/home/claudebot/.local/bin:${PATH}"
RUN poetry config virtualenvs.create false && poetry install --only=main --no-root

# Install Claude CLI locally for the user (not globally)
RUN mkdir -p ~/.local/bin ~/.claude/plugins/repos && \
    npm install @anthropic-ai/claude-code && \
    ln -s "$(pwd)/node_modules/.bin/claude" ~/.local/bin/claude

# Ensure ~/.local/bin is in PATH (should already be, but double-check)
ENV PATH="/home/claudebot/.local/bin:${PATH}"

# ✅ Ключова зміна: Копіюємо ВЕСЬ код проєкту у /app, а не в /home/claudebot
COPY --chown=claudebot:claudebot . /app/

# ✅ Ключова зміна: Встановлюємо робочу директорію на /app
WORKDIR /app

# Entry point
ENTRYPOINT ["python", "-m", "src.main"]