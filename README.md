# django1CsiteSeller

Сайт компании-партнёра 1С на Django: лендинг с прайсом и заявками, калькулятор обновлений конфигураций, блог и REST API для интеграций.

## Возможности

- **Лендинг** — типовые задачи, прайс-лист, команда, форма заявки с уведомлениями в Telegram
- **Калькулятор обновлений** — расчёт пути обновления 1С по релизам с оценкой стоимости
- **Синхронизация релизов** — автоматическая загрузка данных с [freesc.ru](https://freesc.ru) (вручную или по расписанию)
- **Блог** — статьи с SEO-полями, sitemap и IndexNow
- **Админка Django** — контент, заявки, настройки сайта, конфигурации и релизы 1С
- **REST API** — конфигурации, релизы и расчёт обновлений (`/api/v1/`)
- **Деплой** — Docker, GitHub Actions CI/CD, nginx (см. [DEPLOY.md](DEPLOY.md))

## Стек

| Компонент | Технология |
|---|---|
| Backend | Django 5.2, Django REST Framework |
| База данных | SQLite |
| Статика | WhiteNoise |
| Планировщик | django-apscheduler |
| Production | Gunicorn, Docker |
| CI | GitHub Actions |

## Структура проекта

```text
django1CsiteSeller/
├── config/              # Настройки Django, sitemap, SEO
├── landing/             # Лендинг, калькулятор, модели 1С, API
│   ├── api/             # REST API (/api/v1/)
│   ├── management/      # Management-команды
│   ├── services/        # Калькулятор, парсер и синхронизация freesc.ru
│   └── tests/
├── blog/                # Блог и IndexNow
├── templates/           # HTML-шаблоны
├── static/              # CSS, JS, изображения
├── deploy/              # Пример конфигурации nginx
├── scripts/             # Скрипты деплоя и настройки сервера
├── docker-compose.yml   # Локальная разработка
├── docker-compose.prod.yml
├── Dockerfile
├── DEPLOY.md            # Подробная инструкция по CI/CD и production
└── requirements.txt
```

## Быстрый старт (локально)

### Требования

- Python 3.12+
- pip

### Установка

```bash
# Клонировать репозиторий
git clone git@github.com:YOUR_USER/django1CsiteSeller.git
cd django1CsiteSeller

# Виртуальное окружение
python -m venv venv
# Windows
venv\Scripts\activate
# Linux/macOS
source venv/bin/activate

pip install -r requirements.txt

# Переменные окружения
copy .env.example .env   # Windows
# cp .env.example .env   # Linux/macOS
```

Для локальной разработки в `.env` удобно включить `DEBUG=True`.

### Миграции и запуск

```bash
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

Сайт: [http://127.0.0.1:8000/](http://127.0.0.1:8000/)  
Админка: [http://127.0.0.1:8000/admin/](http://127.0.0.1:8000/admin/)

При первом запуске применяются миграции с начальным контентом (типовые задачи, прайс, конфигурации 1С).

## Docker

```bash
copy .env.example .env
docker compose up --build
```

Приложение будет доступно на порту из `WEB_PORT` (по умолчанию `8000`). База SQLite и медиафайлы сохраняются в Docker volumes.

Production-конфигурация:

```bash
docker compose -f docker-compose.prod.yml up -d --build
```

## Переменные окружения

Скопируйте [.env.example](.env.example) в `.env`. Основные параметры:

| Переменная | Описание |
|---|---|
| `SECRET_KEY` | Секретный ключ Django (обязательно сменить в production) |
| `DEBUG` | Режим отладки (`True` — локально, `False` — production) |
| `ALLOWED_HOSTS` | Разрешённые хосты через запятую |
| `CSRF_TRUSTED_ORIGINS` | Origins для HTTPS (с протоколом) |
| `SITE_URL` | Публичный URL сайта (sitemap, canonical, юридические документы) |
| `SITE_CONTACT_EMAIL` | Email в контактах и юридических документах |
| `WEB_PORT` | Порт на хосте (Docker) |
| `YANDEX_METRICA_ID` | Яндекс.Метрика (загружается после согласия на cookies) |
| `GOOGLE_ANALYTICS_ID` | Google Analytics (после согласия на cookies) |
| `FREESC_RUN_SCHEDULER` | Автосинхронизация релизов с freesc.ru (`True` на production) |
| `FREESC_SYNC_CHECK_INTERVAL_HOURS` | Интервал проверки синхронизации, часы |
| `INDEXNOW_ENABLED` | Отправка URL в IndexNow при публикации статей |
| `INDEXNOW_KEY` | Ключ IndexNow (файл `{key}.txt` в корне сайта) |

Telegram-уведомления о заявках настраиваются в админке: **Настройки сайта** → токен бота, chat ID и флаг «Дублировать заявки в Telegram».

## Страницы сайта

| URL | Описание |
|---|---|
| `/` | Главная, форма заявки |
| `/kalkulyator-obnovlenij/` | Калькулятор обновлений 1С |
| `/kak-uznat-reliz/` | Как узнать текущий релиз |
| `/blog/` | Список статей |
| `/blog/<slug>/` | Статья |
| `/legal/user-agreement/` | Пользовательское соглашение |
| `/legal/privacy-policy/` | Политика конфиденциальности |
| `/spasibo/` | Страница после отправки заявки |
| `/sitemap.xml` | Sitemap |
| `/robots.txt` | Robots |

## REST API

Базовый префикс: `/api/v1/`

| Метод | Endpoint | Описание |
|---|---|---|
| GET | `/configurations/` | Список конфигураций 1С |
| GET | `/configurations/<slug>/` | Конфигурация с релизами |
| GET | `/configurations/<slug>/versions/` | Список версий конфигурации |
| POST | `/configurations/<slug>/calculate/` | Расчёт пути обновления |
| POST | `/calculate/` | Расчёт по slug и текущей версии |
| GET/POST | `/releases/` | Релизы (запись — для staff) |

Публичное чтение доступно без авторизации. Изменение данных — через Token-аутентификацию DRF (для staff).

Пример расчёта:

```bash
curl -X POST http://127.0.0.1:8000/api/v1/calculate/ \
  -H "Content-Type: application/json" \
  -d '{"configuration": "rel_1c_ut11", "current_version": "11.5.25.123"}'
```

## Management-команды

```bash
# Синхронизация релизов с freesc.ru
python manage.py sync_freesc_releases --all
python manage.py sync_freesc_releases --config rel_1c_ut11
python manage.py sync_freesc_releases --sync-configs   # обновить список конфигураций
python manage.py sync_freesc_releases --dry-run        # без записи в БД

# Импорт релизов одной конфигурации
python manage.py import_1c_releases rel_1c_ut11

# Проверка Telegram-уведомлений
python manage.py test_telegram_notify

# Отправка URL в IndexNow
python manage.py submit_indexnow
```

На Windows для синхронизации есть bat-скрипт: `scripts/sync_freesc_releases.bat`.

## Тесты

```bash
python manage.py test landing.tests --verbosity=2
```

CI также выполняет `manage.py check --deploy` и проверяет сборку Docker-образа (см. [.github/workflows/ci.yml](.github/workflows/ci.yml)).

## Деплой

Подробная инструкция: **[DEPLOY.md](DEPLOY.md)**

Кратко: push в `main`/`master` → GitHub Actions (тесты) → rsync на сервер → `docker compose -f docker-compose.prod.yml up`.

На сервере не перезаписываются `.env`, `db.sqlite3` и `media/`.

## Лицензия

Проприетарный проект. Использование — по согласованию с владельцем репозитория.
