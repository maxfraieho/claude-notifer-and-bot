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

# Switch to user
USER claudebot
WORKDIR /home/claudebot

# Set HOME environment variable - critical for Claude CLI to find ~/.claude
ENV HOME=/home/claudebot

# ✅ Create target project directory and set permissions
RUN mkdir -p /app/target_project && chown claudebot:claudebot /app/target_project

# Copy dependency files
COPY --chown=claudebot:claudebot pyproject.toml poetry.lock ./

# Install Poetry and Python dependencies
RUN curl -sSL https://install.python-poetry.org | python3 -
ENV PATH="/home/claudebot/.local/bin:${PATH}"
RUN poetry config virtualenvs.create false && poetry install --only=main

# Install Claude CLI globally via npm
# (Uses token from ~/.claude which is mounted from the host)
RUN npm install -g @anthropic-ai/claude-code

# Copy the rest of the bot code
COPY --chown=claudebot:claudebot . .

# Entry point
ENTRYPOINT ["python", "-m", "src.main"]