# 🎨 Smart Diary — Frontend

Мобильно-ориентированное SPA «Умного дневника» на **React 19 + TypeScript + Vite**. Работает как mini-app внутри мессенджера **MAX** и в обычном браузере.

← [Главный README](../../README.md) · [Backend](../../backend/README.md)

<p align="center">
  <img src="src/assets/mascots/math.png" width="120" alt="Математика"/>
  <img src="src/assets/mascots/informatics.png" width="120" alt="Информатика"/>
  <img src="src/assets/mascots/PE.png" width="120" alt="Физкультура"/>
  <img src="src/assets/mascots/default.png" width="120" alt="Маскот"/>
</p>

## 🧰 Стек

| Назначение | Библиотека |
|---|---|
| Фреймворк | React 19, TypeScript |
| Сборка | Vite |
| Стили | Tailwind CSS 4 (`@tailwindcss/vite`), `tw-animate-css` |
| UI-компоненты | shadcn/ui (стиль `radix-nova`) на Radix UI, `class-variance-authority` |
| Иконки / шрифт | lucide-react, Geist Variable |
| Анимации | Framer Motion |
| Drag-and-drop | dnd-kit (рассадка класса) |
| Роутинг | React Router 7 |
| Линтер | Oxlint |

## 🚀 Запуск

### Вместе со всем проектом (рекомендуется)

Из корня репозитория: `docker compose up --build` → http://localhost

Образ собирается в два этапа (Node 20 → Nginx). Nginx раздаёт статику, делает SPA-fallback на `index.html` и **проксирует `/api/` на `backend:8080`** — поэтому фронтенд обращается к API по относительным путям `/api/v1/...`.

### Режим разработки (HMR)

```bash
cd frontend/smart-diary
npm ci
npm run dev          # http://localhost:5173
```

В Vite-конфиге нужен прокси на бэкенд (в Docker это делает Nginx). Добавьте в `vite.config.ts`:

```ts
export default defineConfig({
  plugins: [react(), tailwindcss()],
  resolve: { alias: { "@": path.resolve(__dirname, "./src") } },
  server: {
    proxy: { "/api": "http://localhost:8080" },
  },
})
```

И запустите бэкенд: `docker compose up postgres_db redis_container backend` из корня.

### Скрипты

| Команда | Действие |
|---|---|
| `npm run dev` | Dev-сервер Vite |
| `npm run build` | Проверка типов (`tsc -b`) и production-сборка в `dist/` |
| `npm run preview` | Локальный просмотр сборки |
| `npm run lint` | Oxlint |

## 🗺️ Маршруты

| Путь | Страница | Роль |
|---|---|---|
| `/` | `Login` — вход | все |
| `/student` | `StudentDashboard` — предметы, отчёт, рейтинг | ученик |
| `/student/mascot` | `StudentMascot` — маскот предмета и огонёк 🔥 | ученик |
| `/student/debts` | `StudentDebtsPage` — задолженности | ученик |
| `/student/tests` | `StudentTestsPage` — список тестов | ученик |
| `/student/tests/:testId` | `StudentTestTakePage` — прохождение | ученик |
| `/student/tests/:testId/review` | `StudentTestReviewPage` — разбор ошибок | ученик |
| `/teacher` | `TeacherDashboard` — плитки классов | учитель |
| `/teacher/classes/:classId` | `ClassPage` — аналитика и ИИ-рекомендация | учитель |
| `/teacher/classes/:classId/journal` | `JournalPage` — журнал | учитель |
| `/teacher/classes/:classId/seating` | `SeatingPage` — рассадка (drag-and-drop, PNG) | учитель |
| `/teacher/tests` | `TeacherTestsPage` — тесты учителя | учитель |
| `/teacher/tests/create` · `/edit/:testId` | `TestCreatePage` — создание/правка ИИ-теста | учитель |

Навигация по схемам: [site map ученика](../../docs/images/03-sitemap-student.png) · [site map учителя](../../docs/images/04-sitemap-teacher.png).

## 📁 Структура

```
frontend/smart-diary/
├── src/
│   ├── main.tsx · App.tsx      # вход и маршрутизация
│   ├── index.css               # Tailwind + токены темы shadcn
│   ├── pages/                  # 13 страниц (см. таблицу маршрутов)
│   └── assets/
│       ├── mascots/            # маскоты предметов
│       ├── bg.png · *.svg      # фон, логотипы, «огонёк»
├── @/components/ui/            # shadcn: button, card
├── @/lib/utils.ts              # cn()
├── public/                     # favicon, иконки
├── Dockerfile · nginx.conf     # production-образ
└── components.json             # конфиг shadcn
```

## 🔌 Работа с API

- Базовый путь — относительный `/api/v1` (проксируется Nginx / Vite)
- После входа `access_token` сохраняется в `localStorage`, дальше уходит как `Authorization: Bearer …`
- Размер сетки рассадки берётся из ответа сервера (`layout_json.grid`) — в клиенте не зашит
- Если `ai_recommendation` пришёл `null`, показывается шаблонный текст

## 🐣 Маскоты

Бэкенд (`GET /student/mascot`) отдаёт только **тип** маскота по названию предмета, а картинки лежат на фронтенде в `src/assets/mascots/`.

| `mascot_type` | Файл |
|---|---|
| `math` | `math.png` |
| `russian` | `russian.png` |
| `literature` | `literature.png` |
| `history` | `history.png` |
| `geography` | `geography.png` |
| `chemistry` | `chemistry.png` |
| `physics` | `phisycs.png` |
| `informatics` | `informatics.png` |
| `pe` | `PE.png` |
| `trud` | `trud.png` |
| *остальные* | `default.png` |

<p align="center">
  <img src="src/assets/mascots/russian.png" width="90"/>
  <img src="src/assets/mascots/phisycs.png" width="90"/>
  <img src="src/assets/mascots/history.png" width="90"/>
  <img src="src/assets/mascots/geography.png" width="90"/>
  <img src="src/assets/mascots/chemistry.png" width="90"/>
  <img src="src/assets/mascots/phisycs.png" width="90"/>
  <img src="src/assets/mascots/trud.png" width="90"/>
</p>

> Для биологии и английского бэкенд возвращает типы `biology` / `english`, но отдельных картинок пока нет — подставляется `default.png`.

## 🧱 Известные ограничения

- Токен хранится в `localStorage`
- Вход на странице `/` использует демо-строки (`dev_student_string` / `dev_teacher_string`); для MAX нужно передавать `window.WebApp.initData`
