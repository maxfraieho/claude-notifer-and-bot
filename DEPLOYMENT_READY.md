# 🚀 Claude Telegram Bot - Production Ready

## ✅ Статус деплойменту: ГОТОВИЙ

**Docker Hub:** `kroschu/claude-code-telegram:latest`
**Версія:** v2.0.0-working

---

## 🎯 Швидкий запуск на будь-якому сервері

### Одна команда запуску:

```bash
curl -sSL https://raw.githubusercontent.com/maxfraieho/claude-notifer-and-bot/main/deploy.sh | bash
```

### Ручний запуск:

```bash
# 1. Завантажити скрипт
wget https://raw.githubusercontent.com/maxfraieho/claude-notifer-and-bot/main/deploy.sh
chmod +x deploy.sh

# 2. Запустити (створить .env для редагування)
./deploy.sh

# 3. Відредагувати .env з вашими налаштуваннями

# 4. Запустити знову (запустить бота)
./deploy.sh
```

---

## 📋 Необхідні налаштування у .env:

```bash
# ОБОВ'ЯЗКОВО змініть ці значення:
TELEGRAM_BOT_TOKEN=your_bot_token_from_botfather
TELEGRAM_BOT_USERNAME=your_bot_username  
ALLOWED_USERS=your_telegram_user_id

# Решта працює зі стандартними налаштуваннями
USE_SDK=false
CLAUDE_MODEL=claude-3-5-sonnet-20241022
APPROVED_DIRECTORY=/app/target_project
```

---

## ✨ Особливості готового образу:

- ✅ **Вбудована Claude CLI аутентифікація** - працює одразу
- ✅ **Повна підтримка всіх Claude Code інструментів**
- ✅ **Автоматичне налаштування** - ніяких ручних дій
- ✅ **Моніторинг доступності Claude**
- ✅ **Безпека та rate limiting**
- ✅ **Логування та health checks**

---

## 🔧 Корисні команди:

```bash
# Дивитись логи
docker-compose logs -f claude_bot

# Перезапуск
docker-compose restart claude_bot

# Зупинити
docker-compose down

# Оновити до нової версії
docker-compose pull && docker-compose up -d

# Статус
docker-compose ps
```

---

## 🎯 Тестування:

1. Запустіть бота за допомогою скрипту
2. Знайдіть бота в Telegram: `@your_bot_username`
3. Надішліть `/start`
4. Надішліть будь-який запит до Claude
5. ✅ Має працювати одразу!

---

## 🚨 Support:

- **GitHub:** https://github.com/maxfraieho/claude-notifer-and-bot
- **Docker Hub:** https://hub.docker.com/r/kroschu/claude-code-telegram
- **Issues:** https://github.com/maxfraieho/claude-notifer-and-bot/issues

---

**🎉 Бот готовий до production використання!**