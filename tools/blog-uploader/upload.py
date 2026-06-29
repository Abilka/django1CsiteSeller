#!/usr/bin/env python3
"""
Загрузка статей блога из папки на удалённый сайт через REST API.

Структура папки со статьями:
    articles/
        my-article-slug/
            article.json   # метаданные (title обязателен)
            body.md        # текст в Markdown
            cover.jpg      # необязательно (cover.png / cover.webp тоже подойдут)

article.json:
    {
        "title": "Заголовок статьи",
        "slug": "my-article-slug",
        "excerpt": "Краткое описание",
        "meta_title": "",
        "meta_description": "",
        "is_published": true,
        "published_at": "2026-06-29T12:00:00+03:00"
    }

Токен создаётся в Django admin или командой:
    python manage.py drf_create_token <username>

Пример запуска:
    python upload.py --url https://example.com --token YOUR_TOKEN --folder ./articles
    python upload.py --url https://example.com --token YOUR_TOKEN --folder ./articles --dry-run
"""

from __future__ import annotations

import argparse
import json
import mimetypes
import sys
from pathlib import Path

try:
    import requests
except ImportError:
    print('Установите зависимость: pip install requests', file=sys.stderr)
    sys.exit(1)

COVER_NAMES = ('cover.jpg', 'cover.jpeg', 'cover.png', 'cover.webp')
META_FILENAME = 'article.json'
BODY_FILENAME = 'body.md'


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description='Загрузка статей блога из папки через REST API.',
    )
    parser.add_argument(
        '--url',
        required=True,
        help='Базовый URL сайта, например https://example.com',
    )
    parser.add_argument(
        '--token',
        required=True,
        help='DRF Token для staff-пользователя',
    )
    parser.add_argument(
        '--folder',
        required=True,
        type=Path,
        help='Папка со статьями (подпапка = одна статья)',
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Только проверить файлы, без отправки на сервер',
    )
    return parser.parse_args()


def load_article(article_dir: Path) -> tuple[dict, str, Path | None]:
    meta_path = article_dir / META_FILENAME
    body_path = article_dir / BODY_FILENAME

    if not meta_path.is_file():
        raise FileNotFoundError(f'Нет {META_FILENAME} в {article_dir}')
    if not body_path.is_file():
        raise FileNotFoundError(f'Нет {BODY_FILENAME} в {article_dir}')

    meta = json.loads(meta_path.read_text(encoding='utf-8'))
    body = body_path.read_text(encoding='utf-8')

    if not meta.get('title'):
        raise ValueError(f'Поле "title" обязательно в {meta_path}')

    if not meta.get('slug'):
        meta['slug'] = article_dir.name

    cover_path = next((article_dir / name for name in COVER_NAMES if (article_dir / name).is_file()), None)
    return meta, body, cover_path


def build_payload(meta: dict, body: str) -> dict:
    payload = {
        'title': meta['title'],
        'slug': meta['slug'],
        'body': body,
        'excerpt': meta.get('excerpt', ''),
        'meta_title': meta.get('meta_title', ''),
        'meta_description': meta.get('meta_description', ''),
        'is_published': bool(meta.get('is_published', False)),
    }
    published_at = meta.get('published_at')
    if published_at:
        payload['published_at'] = published_at
    return payload


def article_exists(session: requests.Session, api_base: str, slug: str) -> bool:
    response = session.get(f'{api_base}/posts/{slug}/')
    return response.status_code == 200


def upload_article(
    session: requests.Session,
    api_base: str,
    meta: dict,
    body: str,
    cover_path: Path | None,
    dry_run: bool,
) -> str:
    slug = meta['slug']
    payload = build_payload(meta, body)

    if dry_run:
        cover_note = f', обложка: {cover_path.name}' if cover_path else ''
        return f'[dry-run] «{payload["title"]}» ({slug}){cover_note}'

    exists = article_exists(session, api_base, slug)
    action = 'обновление' if exists else 'создание'

    if cover_path:
        data = {key: _form_value(value) for key, value in payload.items()}
        mime_type = mimetypes.guess_type(cover_path.name)[0] or 'application/octet-stream'
        with cover_path.open('rb') as cover_file:
            files = {'cover_image': (cover_path.name, cover_file, mime_type)}
            if exists:
                response = session.patch(f'{api_base}/posts/{slug}/', data=data, files=files)
            else:
                response = session.post(f'{api_base}/posts/', data=data, files=files)
    elif exists:
        response = session.patch(f'{api_base}/posts/{slug}/', json=payload)
    else:
        response = session.post(f'{api_base}/posts/', json=payload)

    if response.status_code >= 400:
        detail = response.text.strip() or response.reason
        raise RuntimeError(f'HTTP {response.status_code}: {detail}')

    result = response.json()
    return f'OK: {action} «{result.get("title", slug)}» → {result.get("url", slug)}'


def _form_value(value) -> str:
    if isinstance(value, bool):
        return 'true' if value else 'false'
    if value is None:
        return ''
    return str(value)


def iter_article_dirs(folder: Path) -> list[Path]:
    if not folder.is_dir():
        raise NotADirectoryError(f'Папка не найдена: {folder}')
    dirs = sorted(path for path in folder.iterdir() if path.is_dir())
    if not dirs:
        raise FileNotFoundError(f'В {folder} нет подпапок со статьями')
    return dirs


def main() -> int:
    args = parse_args()
    api_base = args.url.rstrip('/') + '/api/v1/blog'
    session = requests.Session()
    session.headers.update({
        'Authorization': f'Token {args.token}',
        'Accept': 'application/json',
    })

    errors = 0
    for article_dir in iter_article_dirs(args.folder):
        try:
            meta, body, cover_path = load_article(article_dir)
            message = upload_article(session, api_base, meta, body, cover_path, args.dry_run)
            print(message)
        except Exception as exc:
            errors += 1
            print(f'ОШИБКА [{article_dir.name}]: {exc}', file=sys.stderr)

    if errors:
        print(f'\nГотово с ошибками: {errors}', file=sys.stderr)
        return 1

    print('\nГотово.')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
