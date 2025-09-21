# DRACON - Документація

DRACON (Дружелюбные Русские Алгоритмы, Которые Обеспечивают Надежность) - професійна система візуального моделювання логіки Telegram бота.

## 📚 Огляд системи

DRACON дозволяє моделювати логіку бота за допомогою візуальних схем у форматі YAML, які автоматично перетворюються на повнофункціональний код бота.

### 🎯 Ключові можливості

- **Візуальне моделювання** - створення схем логіки бота у вигляді графів
- **Автоматична генерація коду** - повна генерація Python коду з схем
- **Професійні діаграми** - SVG/PNG візуалізація з різними темами
- **Реверс-інжиніринг** - створення схем з існуючого коду
- **DRAKON Hub сумісність** - підтримка промислового стандарту

### 📁 Структура документації

```
docs/dracon/
├── README.md              # Цей файл - огляд системи
├── user-guide.md          # Посібник користувача
├── installation.md        # Інструкції з встановлення
├── commands.md            # Довідник команд
├── schema-format.md       # Формат DRACON схем
├── examples/              # Приклади використання
│   ├── simple-bot.yaml    # Простий бот
│   ├── complex-flow.yaml  # Складний воркфлоу
│   └── real-world.yaml    # Реальний проект
├── api/                   # API документація
│   ├── types.md           # Типи даних
│   ├── parser.md          # Парсер
│   ├── renderer.md        # Рендерер
│   └── generator.md       # Генератор коду
└── troubleshooting.md     # Усунення проблем
```

## 🚀 Швидкий старт

### 1. Базові команди

```bash
# Показати довідку
/dracon help

# Список збережених схем
/dracon list

# Створити візуальну діаграму
/dracon diagram library simple_bot_schema.yaml

# Аналіз схеми
/dracon analyze my_schema.yaml
```

### 2. Приклад простої схеми

```yaml
version: "1.0"
name: "Simple Bot Example"
description: "Приклад простого бота"

metadata:
  author: "Claude DRACON System"
  created: "2024-12-19"

nodes:
  - id: "start"
    type: "title"
    name: "Bot Start"
    description: "Початок роботи бота"
    position: [0, 0]
    properties:
      text: "🚀 Вітаємо в боті!"
      command: "start"

  - id: "main_menu"
    type: "action"
    name: "Main Menu"
    description: "Головне меню"
    position: [200, 0]
    properties:
      template: "🏠 **Головне меню**\n\nОберіть опцію:"

  - id: "end"
    type: "end"
    name: "End"
    description: "Завершення"
    position: [400, 0]

edges:
  - id: "start_to_menu"
    from_node: "start"
    to_node: "main_menu"
    type: "sequence"

  - id: "menu_to_end"
    from_node: "main_menu"
    to_node: "end"
    type: "sequence"
```

### 3. Створення візуальної діаграми

```bash
# Збережіть схему у файл
/dracon save library my_first_bot

# Створіть діаграму
/dracon diagram library my_first_bot_YYYYMMDD_HHMMSS.yaml
```

## 📖 Детальна документація

- **[Посібник користувача](user-guide.md)** - покрокові інструкції
- **[Формат схем](schema-format.md)** - повний опис YAML формату
- **[Команди](commands.md)** - всі доступні команди
- **[Приклади](examples/)** - готові схеми для навчання

## 🛠️ Для розробників

- **[API документація](api/)** - програмний інтерфейс
- **[Типи даних](api/types.md)** - структури даних DRACON
- **[Розширення](troubleshooting.md#extending)** - додавання нових можливостей

## 🆘 Допомога

Якщо у вас виникли проблеми:

1. Перевірте **[Усунення проблем](troubleshooting.md)**
2. Скористайтеся командою `/dracon help`
3. Перегляньте **[Приклади](examples/)**

## 🔄 Оновлення

Система DRACON регулярно оновлюється. Перевіряйте нові можливості командою:

```bash
/dracon stats
```

---

*Документація створена автоматично системою Claude DRACON*