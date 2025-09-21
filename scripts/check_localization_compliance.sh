#!/bin/bash

# Швидка перевірка відповідності локалізації для CI/CD
# Блокує merge якщо знайдено критичні проблеми локалізації

set -e

echo "🔍 Локалізаційна перевірка CI/CD..."

# Перевірити чи є Python
if ! command -v python3 &> /dev/null; then
    echo "❌ Python3 не знайдено"
    exit 1
fi

# Запустити швидку перевірку
echo "🚀 Запуск швидкої перевірки локалізації..."
python3 tests/quick_localization_check.py

exit_code=$?

if [ $exit_code -eq 0 ]; then
    echo "✅ ПРОЙДЕНО: Локалізаційна перевірка успішна"
    echo "🎉 Merge дозволено!"
    exit 0
else
    echo "❌ НЕ ПРОЙДЕНО: Знайдено проблеми локалізації"
    echo "🚫 Merge заблоковано!"
    echo ""
    echo "💡 Для виправлення:"
    echo "1. Замініть hardcoded UI strings на await t() виклики"
    echo "2. Додайте необхідні ключі до uk.json та en.json"
    echo "3. Запустіть 'python3 tests/quick_localization_check.py' для перевірки"
    exit 1
fi