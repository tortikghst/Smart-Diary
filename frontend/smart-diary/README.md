<div align="center">

# 🎨 Smart Diary — Frontend

**Мобильное SPA «Умного дневника» на React 19 + TypeScript + Vite.**
Работает как mini-app внутри мессенджера **MAX** и в обычном браузере.

![React](https://img.shields.io/badge/React_19-20232A?logo=react&logoColor=61DAFB)
![TypeScript](https://img.shields.io/badge/TypeScript-3178C6?logo=typescript&logoColor=white)
![Vite](https://img.shields.io/badge/Vite-646CFF?logo=vite&logoColor=white)
![Tailwind](https://img.shields.io/badge/Tailwind_CSS_4-06B6D4?logo=tailwindcss&logoColor=white)

[← Главный README](../../README.md) · [Backend →](../../backend/README.md)

<p>
  <img src="src/assets/mascots/math.webp" width="80" alt="Математика" />
  <img src="src/assets/mascots/informatics.webp" width="80" alt="Информатика" />
  <img src="src/assets/mascots/PE.webp" width="80" alt="Физкультура" />
  <img src="src/assets/mascots/default.webp" width="80" alt="Маскот" />
</p>

</div>

---

## 📑 Содержание

[Стек](#-стек) · [Запуск](#-запуск) · [Маршруты](#️-маршруты) · [Структура](#-структура) · [Работа с API](#-работа-с-api) · [Маскоты](#-маскоты) · [Ограничения](#-известные-ограничения)

---

## 🧰 Стек

| Назначение | Библиотека |
|---|---|
| Фреймворк | React 19, TypeScript |
| Сборка | Vite |
| Стили | Tailwind CSS 4 (`@tailwindcss/vite`), `tw-animate-css` |
| UI-компоненты | shadcn/ui (стиль `radix-nova`) на Radix UI, `class-variance-authority` |
| Иконки и шрифт | lucide-react, Geist Variable |
| Анимации | Framer Motion |
| Drag-and-drop | dnd-kit (рассадка класса) |
| Роутинг | React Router 7 |
| Линтер | Oxlint |

---

## 🚀 Запуск

### Вместе со всем проектом (рекомендуется)

Из корня репозитория:

```bash
docker compose up --build
```

Откройте http://localhost.

Образ собирается в два этапа (Node 20 → Nginx). Nginx раздаёт статику, делает SPA-fallback на `index.html` и **проксирует `/api/` на `backend:8080`**. Поэтому фронтенд обращается к API по относительным путям `/api/v1/...`.

### Режим разработки (HMR)

```bash
cd frontend/smart-diary
npm ci
npm run dev          # http://localhost:5173
```

В Docker прокси на бэкенд делает Nginx, а в dev-режиме он нужен в `vite.config.ts`:

```ts
export default defineConfig({
  plugins: [react(), tailwindcss()],
  resolve: { alias: { "@": path.resolve(__dirname, "./src") } },
  server: {
    proxy: { "/api": "http://localhost:8080" },
  },
})
```

Затем запустите бэкенд из корня репозитория:

```bash
docker compose up postgres_db redis_container backend
```

### Скрипты

| Команда | Действие |
|---|---|
| `npm run dev` | Dev-сервер Vite |
| `npm run build` | Проверка типов (`tsc -b`) и production-сборка в `dist/` |
| `npm run preview` | Локальный просмотр сборки |
| `npm run lint` | Oxlint |

---

## 🗺️ Маршруты

| Путь | Страница | Роль |
|---|---|---|
| `/` | `Login` — вход | все |
| `/student` | `StudentDashboard` — предметы, отчёт, рейтинг | 🧒 ученик |
| `/student/mascot` | `StudentMascot` — маскот предмета и огонёк 🔥 | 🧒 ученик |
| `/student/debts` | `StudentDebtsPage` — задолженности | 🧒 ученик |
| `/student/tests` | `StudentTestsPage` — список тестов | 🧒 ученик |
| `/student/tests/:testId` | `StudentTestTakePage` — прохождение | 🧒 ученик |
| `/student/tests/:testId/review` | `StudentTestReviewPage` — разбор ошибок | 🧒 ученик |
| `/teacher` | `TeacherDashboard` — плитки классов | 👩‍🏫 учитель |
| `/teacher/classes/:classId` | `ClassPage` — аналитика и ИИ-рекомендация | 👩‍🏫 учитель |
| `/teacher/classes/:classId/journal` | `JournalPage` — журнал | 👩‍🏫 учитель |
| `/teacher/classes/:classId/seating` | `SeatingPage` — рассадка (drag-and-drop, PNG) | 👩‍🏫 учитель |
| `/teacher/tests` | `TeacherTestsPage` — тесты учителя | 👩‍🏫 учитель |
| `/teacher/tests/create` · `/edit/:testId` | `TestCreatePage` — создание и правка ИИ-теста | 👩‍🏫 учитель |

Схемы навигации: [site map ученика](../../docs/StudentSiteMap.png) · [site map учителя](../../docs/TeacherSiteMap.png).

---

## 📁 Структура

```text
frontend/smart-diary/
├── src/
│   ├── main.tsx · App.tsx      # вход и маршрутизация
│   ├── index.css               # Tailwind + токены темы shadcn
│   ├── pages/                  # 13 страниц (см. таблицу маршрутов)
│   └── assets/
│       ├── mascots/            # маскоты предметов
│       └── bg.png · *.svg      # фон, логотипы, «огонёк»
├── public/                     # favicon, иконки
├── Dockerfile · nginx.conf     # production-образ
└── components.json             # конфиг shadcn
```

> UI-компоненты shadcn (`button`, `card`) лежат в алиасе `@/components/ui/`, утилита `cn()` — в `@/lib/utils.ts`. Проверьте, куда алиас `@` указывает у вас, и поправьте строку, если нужно.

---

## 🔌 Работа с API

- Базовый путь относительный: `/api/v1` (проксируется Nginx или Vite).
- После входа `access_token` сохраняется в `localStorage` и уходит как `Authorization: Bearer …`.
- Размер сетки рассадки берётся из ответа сервера (`layout_json.grid`), в клиенте он не зашит.
- Если `ai_recommendation` пришёл `null`, показывается шаблонный текст.

---

## 🐣 Маскоты

Бэкенд (`GET /student/mascot`) отдаёт только **тип** маскота по названию предмета, а картинки лежат на фронтенде в `src/assets/mascots/`.

| `mascot_type` | Файл |
|---|---|
| `math` | `math.webp` |
| `russian` | `russian.webp` |
| `literature` | `literature.webp` |
| `history` | `history.webp` |
| `geography` | `geography.webp` |
| `chemistry` | `chemistry.webp` |
| `physics` | `phisycs.webp` |
| `informatics` | `informatics.webp` |
| `pe` | `PE.webp` |
| `biology` | `biology.webp` |
| `english` | `english.webp` |
| `trud` | `trud.webp` |
| *остальные* | `default.webp` |

<p align="center">
  <img src="src/assets/mascots/russian.webp" width="80" alt="Русский язык" />
  <img src="src/assets/mascots/phisycs.webp" width="80" alt="Физика" />
  <img src="src/assets/mascots/history.webp" width="80" alt="История" />
  <img src="src/assets/mascots/geography.webp" width="80" alt="География" />
  <img src="src/assets/mascots/chemistry.webp" width="80" alt="Химия" />
  <img src="src/assets/mascots/trud.webp" width="80" alt="Труд" />
  <img src="src/assets/mascots/biology.webp" width="80" alt="Биология" />
  <img src="src/assets/mascots/english.webp" width="80" alt="Английский" />
</p>


---

## 🧱 Известные ограничения

- Токен хранится в `localStorage`.
- Вход на странице `/` использует демо-строки (`dev_student_string` / `dev_teacher_string`). Для MAX нужно передавать `window.WebApp.initData`.
