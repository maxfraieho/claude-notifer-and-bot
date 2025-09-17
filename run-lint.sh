#!/bin/bash
set -e

echo "🔍 Running code quality checks..."

# Activate virtual environment
source $(poetry env info --path)/bin/activate

echo "📝 Formatting code with black..."
poetry run black src/

echo "📝 Sorting imports with isort..."
poetry run isort src/

echo "🔍 Linting with flake8..."
poetry run flake8 src/

echo "🔍 Type checking with mypy..."
poetry run mypy src/

echo "✅ All checks passed!"
