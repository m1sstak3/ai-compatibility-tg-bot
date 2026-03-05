<div align="center">
  <h1>🤖💕 ИИ Тест на совместимость (Telegram Bot)</h1>
  <p><b>Продвинутый бот-ведущий для проверки совместимости пар с динамической генерацией вопросов через LLM и алгоритмом «психологической мимикрии».</b></p>

  <div>
    <img src="https://img.shields.io/badge/Python_3.10+-3776AB?style=for-the-badge&logo=python&logoColor=white" alt="Python" />
    <img src="https://img.shields.io/badge/Aiogram_3.x-2CA5E0?style=for-the-badge&logo=telegram&logoColor=white" alt="Aiogram" />
    <img src="https://img.shields.io/badge/SQLAlchemy_Async-CC2927?style=for-the-badge&logo=sqlite&logoColor=white" alt="SQLAlchemy" />
    <img src="https://img.shields.io/badge/OpenRouter_LLM-4A90E2?style=for-the-badge&logo=openai&logoColor=white" alt="OpenRouter" />
  </div>
</div>

---

## 📱 Демонстрация интерфейса

<table align="center">
  <tr>
    <td align="center">
      <b>🎮 Создание комнаты</b><br>
      <img src="https://github.com/user-attachments/assets/ec0ae142-df1b-4990-96c0-314e7f02e8ea" width="280" />
    </td>
    <td align="center">
      <b>🧠 Процесс игры</b><br>
      <img src="https://github.com/user-attachments/assets/81d66416-f9a5-4e88-bdf6-1b9cecfb1eb2" width="280" />
    </td>
    <td align="center">
      <b>📊 Вердикт ИИ</b><br>
      <img src="https://github.com/user-attachments/assets/ced94155-bba4-4dd2-a7cf-3be7e3bf9abd" width="280" />
    </td>
  </tr>
</table>

---

## ✨ Ключевые особенности (Value Proposition)

Этот проект демонстрирует современную backend-разработку, объединяя асинхронное программирование, конечные автоматы (FSM) и сложную интеграцию с большими языковыми моделями (LLM).

* 🧠 **Динамическая генерация контента:** Использование OpenRouter (Qwen/Trinity) для создания уникальных раундов вопросов, адаптированных под пол игроков и их жизненную ситуацию (живут вместе или на расстоянии).
* 🎭 **Алгоритм психологической мимикрии:** Генерация крайне правдоподобных «фейковых» ответов, которые копируют стиль общения партнера, но в корне отличаются по смыслу — превращает тест в захватывающую игру.
* ⚡ **Асинхронная архитектура:** Построено на `aiogram 3.x` с полностью неблокирующими обработчиками и собственным надежным ограничителем частоты запросов (Semaphore) для внешних API.
* 🧩 **Модульный дизайн:** Строгое разделение на слои архитектуры (`core`, `bot`, `services`, `database`), обеспечивающее принципы SOLID и высокую поддерживаемость кода.
* 🔒 **Управление сессиями:** Безопасная обработка сессий в памяти для изоляции состояний игр между разными пользователями, защита от утечек памяти и состояния гонки (Race Conditions).

---

## 🏗 Архитектура и под капотом

Проект следует чистой модульной структуре для обеспечения легкого масштабирования и тестирования.

<details>
<summary><b>📂 Посмотреть структуру проекта</b></summary>
<br>

```text
src/
├── core/
│   └── config.py          # Переменные окружения и центральный логгер
├── database/
│   ├── connection.py      # Асинхронный движок SQLAlchemy и DAL слой
│   └── models.py          # Декларативные ORM модели
├── bot/
│   ├── fsm.py             # Конечные автоматы (State Machines) Aiogram
│   └── handlers.py        # Маршрутизация Telegram и логика представления
├── services/
│   ├── llm.py             # API-клиент LLM с авто-повторами и лимитами
│   └── session_manager.py # Потокобезопасное отслеживание состояния игры
└── main.py                # Точка входа в приложение
```
</details>

---

## 🚀 Быстрый старт

### 1. Требования
* Python 3.10+
* Токен Telegram бота (от @BotFather)
* API ключ OpenRouter

### 2. Установка и запуск (Локально)
```bash
git clone [https://github.com/m1sstak3/ai-compatibility-bot.git](https://github.com/m1sstak3/ai-compatibility-bot.git)
cd ai-compatibility-bot

# Создание виртуального окружения
python -m venv venv
source venv/bin/activate  # На Windows: venv\Scripts\activate
pip install -r requirements.txt

# Настройка переменных окружения
cp .env.example .env
# Отредактируйте .env и вставьте ваши API ключи

# Запуск бота
python -m src.main
```

---

## 📈 Масштабирование и Roadmap
* 🔴 **Интеграция Redis:** Замена `InMemorySessionManager` на Redis для распределенного, отказоустойчивого хранения состояний FSM и активных игр.
* 🐘 **PostgreSQL:** Простая миграция с SQLite на PostgreSQL путем изменения строки подключения в `config.py` благодаря абстракциям SQLAlchemy.
* 🔄 **Alembic:** Добавление миграций базы данных для бесшовного обновления схемы в production-среде.

---

<div align="center">
  <b>Developed with ❤️ by m1sstak3</b>
</div>
