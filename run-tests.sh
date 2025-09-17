#!/bin/bash
set -e

echo "🧪 Running tests..."

# Activate virtual environment
source $(poetry env info --path)/bin/activate

# Run tests
poetry run pytest "$@"
