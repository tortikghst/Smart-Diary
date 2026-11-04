<div align="center">

<img src="docs/logo.jpg" width="180" alt="Маскот Умного дневника"/>

# 📓 Умный дневник

**Электронный дневник нового поколения: ИИ-тесты, закрытие долгов, рассадка класса и геймификация — прямо в мессенджере MAX.**

*Хакатонный MVP команды **«Совёнки»***

![FastAPI](https://img.shields.io/badge/FastAPI-009688?logo=fastapi&logoColor=white)
![React](https://img.shields.io/badge/React_19-20232A?logo=react&logoColor=61DAFB)
![TypeScript](https://img.shields.io/badge/TypeScript-3178C6?logo=typescript&logoColor=white)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL_16-4169E1?logo=postgresql&logoColor=white)
![Redis](https://img.shields.io/badge/Redis-DC382D?logo=redis&logoColor=white)
![Docker](https://img.shields.io/badge/Docker_Compose-2496ED?logo=docker&logoColor=white)
![LLM](https://img.shields.io/badge/LLM-Caila%20%2F%20OpenRouter-orange)

</div>

---

## 🎯 Проблема и идея

Школьный электронный журнал показывает оценки, но не помогает **учиться** и **преподавать**:

| Учитель | Ученик |
|---|---|
| Тратит часы на тесты, рассадку и разбор «проблемных» тем | Не видит, что именно нужно «дотянуть» |
| Не видит пробелы класса по темам | Долги копятся и теряются |
| Данные живут в ЕРИСО КО и Excel-выгрузках | Нет мотивации делать ДЗ регулярно |

**Умный дневник** превращает выгрузку журнала в живой инструмент: ИИ находит слабые темы класса, генерирует тесты и рекомендации, а ученик получает понятные долги, тренировочные тесты и мотивацию в виде огоньках и маскоте.

## ✨ Возможности

### 👩‍🏫 Учитель
- **Вход через MAX** — без паролей, по подписанному `initData`
- **Дашборд классов** — средний балл, горящие долги, «проблемные» классы подсвечиваются автоматически (ср. балл < 3.5 или > 3 долгов)
- **Электронный журнал** класса с пагинацией
- **Импорт Excel-выгрузки ЕРИСО КО** — оценки, уроки, темы, ДЗ (парсер)
- **Аналитика класса** — распределение оценок, «карта пробелов» по темам, **ИИ-рекомендация** к следующему уроку
- **Умная рассадка** — генерация по маркерам  **экспорт в PNG**, загрузка фото класса
- **ИИ-тесты** — генерация по теме → проверка и редактирование → публикация; ручное создание

### 🧒 Ученик
- **Тесты**  частичные баллы, порог сдачи 70 %
- **Разбор ошибок** с ИИ-объяснением после сдачи
- **«Мои задолженности»** → тренировочный тест по теме долга
- **Серия ДЗ «Огонёк»** 🔥 и **маскот предмета** — у каждого предмета свой "Соволудь"
- **Отчёт по предмету** — средний балл и процент выполненных ДЗ
- **Рейтинг классов** параллели (КР/ВПР)

### 🐣 Маскоты предметов

Каждый предмет получает своего персонажа — он живёт рядом с «огоньком» и поддерживает ученика.

<p align="center">
  <img src="frontend/smart-diary/src/assets/mascots/math.png" width="110" alt="Математика"/>
  <img src="frontend/smart-diary/src/assets/mascots/russian.png" width="110" alt="Русский язык"/>
  <img src="frontend/smart-diary/src/assets/mascots/history.png" width="110" alt="История"/>
  <img src="frontend/smart-diary/src/assets/mascots/geography.png" width="110" alt="География"/>
  <img src="frontend/smart-diary/src/assets/mascots/chemistry.png" width="110" alt="Химия"/>
</p>
<p align="center">
  <img src="frontend/smart-diary/src/assets/mascots/phisycs.png" width="110" alt="Физика"/>
  <img src="frontend/smart-diary/src/assets/mascots/informatics.png" width="110" alt="Информатика"/>
  <img src="frontend/smart-diary/src/assets/mascots/PE.png" width="110" alt="Физкультура"/>
  <img src="frontend/smart-diary/src/assets/mascots/trud.png" width="110" alt="Труд"/>
  <img src="frontend/smart-diary/src/assets/mascots/default.png" width="110" alt="По умолчанию"/>
</p>

---

## 🚀 Быстрый старт

Нужны только **Docker** и **Docker Compose**.

```bash
# 1. Клонируем репозиторий
git clone <URL-репозитория> smart-diary && cd smart-diary

# 2. Создаём конфиг (мок-ИИ включён — ключи не нужны)
cp .env.example backend/.env

# 3. Поднимаем всё
docker compose up --build
```

После запуска:

| Сервис | Адрес |
|---|---|
| 🖥️ Приложение (frontend) | `localhost` |
| 📡 Swagger / OpenAPI | `localhost:8080/docs` |
| 🗄️ pgAdmin | `localhost:5050` |
| 🐘 PostgreSQL | `localhost:5433` |
| ⚡ Redis | `localhost:6378` |

### 🔑 Демо-вход для жюри

Поскольку "Умный дневник" - закрытая платформа для ученика и учителя: на стартовой странице две кнопки — **«Ученик»** и **«Учитель»**. Они входят под демо-профилями:

| Роль | Кто | Что посмотреть |
|---|---|---|
| 👩‍🏫 Учитель | Иванов Иван Иванович (математика, `vk_id=12345`) | классы 7А–9Б, журнал, аналитика, рассадка, создание ИИ-теста |
| 🧒 Ученик | первый ученик 7А (`vk_id=23456`) | долги, тесты, огонёк, маскот, рейтинг |

> При старте бэкенд **автоматически наполняет БД демо-данными**: 12 предметов, 12 учителей, 6 классов (7А–9Б), по 10 учеников, уроки, оценки, долги, стрики.

### Сквозной сценарий демонстрации (5 минут)

1. **Учитель** → дашборд → класс 7А → **аналитика**: слабая тема + рекомендация ИИ
2. **Рассадка** → «Сгенерировать» → перетащить пару карточек → **скачать PNG**
3. **Тесты** → «Создать» → тема → «Сгенерировать ИИ» → правка → публикация
4. Выйти → **Ученик** → «Тесты» → пройти → **разбор ошибок**
5. «Мои задолженности» → тренировочный тест по долгу
6. **Огонёк и маскот** предмета → **рейтинг классов**

---

## 🏗️ Архитектура

![Architecture](docs/architecture.png)

### Поток прохождения теста

![Test](docs/TestMap.png)

> 🔒 Правильные ответы **никогда не отдаются** клиенту до сдачи теста — списать через DevTools нельзя.

---

## 📐 Проектная документация

### Use case
Роли и сценарии, в которых участвует ИИ (LLM).

![Use case](docs/UseCase.png)

### User flow
Пять ключевых сценариев для каждой из двух персон.

| Ученик | Учитель |
|:---:|:---:|
| ![User flow ученика](docs/StudentFlow.png) | ![User flow учителя](docs/TeacherFlow.png) |

### Site map

| Ученик | Учитель |
|:---:|:---:|
| ![Site map ученика](docs/StudentSiteMap.png) | ![Site map учителя](docs/TeacherSiteMap.png) |

### Логика проверки тестов и начисления баллов

![Логика проверки](docs/proverka.png)

Для каждого вопроса считается `score_i ∈ [0; 1]`, итог — `percent = floor(Σ score_i / N · 100)`. Для множественного выбора — частичный балл `max(0, (верных − неверных) / всего_верных)`. Результат пишется в `test_attempts`.

### Автоматическое закрытие долгов

![Автозакрытие долгов](docs/Debts.png)

Долг закрывается при появлении оценки ≥ 3 в новой выгрузке ЕРИСО КО или вручную учителем; операция идемпотентна (`SELECT … FOR UPDATE`), каждое действие пишется в `audit_log` / `sync_log`.

### Сервисная карта

![Сервисная карта](docs/ServiceCard.png)

---

## 🧰 Технологический стек

| Слой | Технологии |
|---|---|
| **Backend** | Python 3.12, FastAPI, SQLAlchemy 2 (async) + asyncpg, Pydantic v2, python-jose (JWT), openpyxl, Pillow, httpx |
| **Frontend** | React 19, TypeScript, Vite, Tailwind CSS 4, shadcn/ui (Radix), Framer Motion, dnd-kit, React Router 7 |
| **Данные** | PostgreSQL 16, Redis |
| **ИИ** | Caila / OpenRouter (qwen), структурированный JSON-вывод, мок-режим |
| **Инфраструктура** | Docker Compose, Nginx, pgAdmin |
| **Интеграции** | MAX (авторизация `initData`, бот с webhook), ЕРИСО КО (Excel) |

## 📁 Структура репозитория

```
.
├── backend/                  # FastAPI-сервис  → см. backend/README.md
│   └── scr/
│       ├── api/              # роутеры (auth, teacher, student, journal, tests, seating, bot)
│       ├── services/         # JWT, LLM, импорт ЕРИСО, PNG-рассадка
│       ├── repositories/     # работа с БД и бизнес-логика
│       ├── schemas/          # Pydantic-схемы
│       ├── model/            # SQLAlchemy-модели (21 таблица)
│       └── seed_big_demo.py  # демо-данные
├── frontend/smart-diary/     # React-приложение → см. frontend/smart-diary/README.md
├── docs/images/              # схемы проекта
├── docker-compose.yml
└── .env.example
```

## 📚 Подробнее

- 📡 **[Backend README](backend/README.md)** — API, модель данных, ИИ, безопасность, тесты
- 🎨 **[Frontend README](frontend/smart-diary/README.md)** — страницы, маршруты, запуск, структура

## 🔐 Безопасность

- JWT (access 24 ч / refresh 30 дн), роли `student` / `teacher` / `admin` (RBAC)
- Проверка подписи `initData` по HMAC-SHA256 (алгоритм MAX Bridge)
- Учитель видит только **свои** классы
- Правильные ответы тестов не уходят на клиент
- Секреты — только через `.env`, файл в `.gitignore`

> ⚠️ **Демо-вход** (`initData` содержит `teacher`/`student`) включён для хакатона. Перед продом его необходимо отключить — см. [backend/README.md](backend/README.md#-безопасность-и-переход-в-прод).

## 👥 Команда «Совёнки»

Проект создан на хакатоне "Идея Фикс" командой **«Совёнки»** 🦉

<!-- TODO: добавьте участников и роли, например: -->
<!-- | Имя | Роль | -->
<!-- |---|---| -->
<!-- | … | Backend | -->
