# CI/CD и деплой на сервер

Проект деплоится через **GitHub Actions**: при пуше в `main`/`master` запускаются тесты, код копируется на сервер по SSH (rsync) и пересобирается Docker-контейнер.

**Приватный репозиторий поддерживается из коробки** — GitHub Actions сам читает код, серверу доступ к GitHub не нужен.

## Схема

```text
git push → GitHub Actions (тесты) → rsync на сервер → docker compose up
```

На сервер **не попадают**: `.env`, `data/`, `persistent/` — они остаются только на VPS.

База SQLite: `data/db.sqlite3` на диске сервера (не внутри анонимного Docker volume).

## 1. Подготовка репозитория

```bash
git init
git add .
git commit -m "Initial commit"
git branch -M main
git remote add origin git@github.com:YOUR_USER/django1CsiteSeller.git
git push -u origin main
```

## 2. Подготовка сервера (один раз)

На VPS (Ubuntu/Debian). **Клонировать репозиторий на сервер не нужно** — код доставляет GitHub Actions.

```bash
# Установка Docker и базовой настройки
sudo DEPLOY_USER=deploy DEPLOY_PATH=/opt/django1CsiteSeller bash scripts/server-setup.sh

# Создайте .env до первого деплоя (файл не перезаписывается при обновлениях)
sudo -u deploy cp /opt/django1CsiteSeller/.env.example /opt/django1CsiteSeller/.env 2>/dev/null || true
sudo -u deploy nano /opt/django1CsiteSeller/.env
```

Если каталог пустой и `.env.example` ещё нет — скопируйте его с локальной машины:

```bash
scp .env.example deploy@YOUR_SERVER_IP:/opt/django1CsiteSeller/.env.example
ssh deploy@YOUR_SERVER_IP "cp /opt/django1CsiteSeller/.env.example /opt/django1CsiteSeller/.env"
```

Настройте секреты GitHub (шаг 4), затем сделайте `git push` — первый деплой скопирует код и соберёт контейнер.

### Обязательные переменные в `.env` на сервере

| Переменная | Пример |
|---|---|
| `SECRET_KEY` | длинная случайная строка |
| `DEBUG` | `False` |
| `ALLOWED_HOSTS` | `your-domain.ru,www.your-domain.ru,127.0.0.1` |
| `CSRF_TRUSTED_ORIGINS` | `https://example.com,https://www.example.com` |
| `SITE_URL` | `https://example.com` |
| `WEB_PORT` | `8000` (только localhost, за nginx) |

## 3. SSH-ключ для GitHub Actions

На **локальной машине** (не на сервере):

```bash
ssh-keygen -t ed25519 -C "github-actions-deploy" -f deploy_key -N ""
```

- Публичный ключ `deploy_key.pub` → на сервер в `~deploy/.ssh/authorized_keys`
- Приватный ключ `deploy_key` → секрет GitHub `SSH_PRIVATE_KEY`

Проверка:

```bash
ssh -i deploy_key deploy@YOUR_SERVER_IP
```

## 4. Секреты в GitHub

Для **приватного** репозитория: **Settings → Actions → General → Workflow permissions** → включите **Read and write permissions** (или минимум read для checkout — обычно достаточно дефолтных настроек).

**Settings → Secrets and variables → Actions → New repository secret**:

| Секрет | Значение |
|---|---|
| `SSH_HOST` | IP или домен сервера |
| `SSH_USER` | `deploy` |
| `SSH_PRIVATE_KEY` | содержимое `deploy_key` |
| `SSH_PORT` | `22` (если стандартный — можно не добавлять) |
| `DEPLOY_PATH` | `/opt/django1CsiteSeller` |

## 5. HTTPS (nginx + Let's Encrypt)

```bash
sudo apt install nginx certbot python3-certbot-nginx
sudo cp deploy/nginx.conf.example /etc/nginx/sites-available/your-site
# отредактируйте server_name и пути
sudo ln -s /etc/nginx/sites-available/your-site /etc/nginx/sites-enabled/
sudo certbot --nginx -d example.com -d www.example.com
sudo nginx -t && sudo systemctl reload nginx
```

## 6. Ручной деплой

На сервере:

```bash
cd /opt/django1CsiteSeller
bash scripts/deploy.sh
```

Или из GitHub: **Actions → Deploy → Run workflow**.

## 7. Локальная разработка vs production

| Файл | Назначение |
|---|---|
| `docker-compose.yml` | локальная разработка |
| `docker-compose.prod.yml` | production (порт только на 127.0.0.1, healthcheck) |

## Приватный репозиторий — FAQ

| Вопрос | Ответ |
|---|---|
| Нужен ли deploy key на сервере? | **Нет.** Код копируется через rsync из Actions. |
| Работают ли Actions на private repo? | **Да.** На бесплатном плане — 2000 минут/мес. |
| Перезапишется ли `.env` при деплое? | **Нет**, он в списке исключений rsync. |
| Где лежит база на сервере? | `DEPLOY_PATH/data/db.sqlite3` |
| Нужен ли `git` на сервере? | Нет для автодеплоя. Только Docker и SSH. |

## База данных: почему могла «пропасть»

Раньше `docker-compose.prod.yml` хранил SQLite в **именованном Docker volume** (`sqlite_data`). При этом:

1. Файл `db.sqlite3` в корне проекта на сервере **не использовался** production-контейнером.
2. При смене имени папки/проекта Docker создавал **новый пустой volume** (например `tortugasite_sqlite_data` вместо старого).
3. При `migrate` на пустой БД срабатывали **seed-миграции** — сайт выглядел «как после переустановки».

**Сейчас** БД монтируется в `./data/db.sqlite3` на диске сервера и не зависит от имени Docker-проекта.

### Восстановить старую БД из Docker volume

На сервере:

```bash
cd /opt/django1CsiteSeller   # ваш DEPLOY_PATH
docker volume ls             # ищите *sqlite* или старое имя проекта
bash scripts/recover-db-from-volume.sh
docker compose -f docker-compose.prod.yml up -d
```

Или вручную, если volume назывался `tortugasite_sqlite_data`:

```bash
mkdir -p data
docker run --rm \
  -v tortugasite_sqlite_data:/from:ro \
  -v "$(pwd)/data:/to" \
  alpine cp /from/db.sqlite3 /to/db.sqlite3
```

### Бэкап перед деплоем

```bash
cp data/db.sqlite3 "data/db.sqlite3.bak.$(date +%Y%m%d-%H%M)"
```

## Troubleshooting

**`Permission denied` при rsync**

Убедитесь, что `deploy` владеет каталогом: `sudo chown -R deploy:deploy /opt/django1CsiteSeller`.

**Деплой завис на `Container ... Waiting`**

`docker compose up --wait` ждёт healthcheck. Чаще всего:

1. Ещё идут `migrate` / `collectstatic` (подождите до 2 мин)
2. Gunicorn упал при старте — смотрите логи:

```bash
docker compose -f docker-compose.prod.yml logs --tail=100 web
```

3. В `.env` нет домена в `ALLOWED_HOSTS` — сайт не откроется (но healthcheck теперь проверяет только порт)

**Деплой упал на healthcheck**

```bash
cd /opt/django1CsiteSeller
docker compose -f docker-compose.prod.yml logs --tail=100 web
```

**Проверить, что контейнер жив**

```bash
docker compose -f docker-compose.prod.yml ps
curl -I http://127.0.0.1:8000/
```

**Откатиться на предыдущий коммит**

```bash
cd /opt/django1CsiteSeller
git log --oneline -5
git reset --hard <commit>
bash scripts/deploy.sh
```
