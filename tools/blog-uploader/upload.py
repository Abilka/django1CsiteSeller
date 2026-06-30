#!/usr/bin/env python3
"""
Загрузка статей блога из папки на удалённый сайт через REST API.

Формат статей — один .md файл с YAML frontmatter:
    articles/
        0020-avtomatizaciya-na-baze-1s-c37a729b.md
        0021-perehod-na-novye-versii-1s-c2757265.md

Пример файла:
    ---
    title: "Заголовок статьи"
    keyword: "ключевое слово"
    category: "Категория"
    ---

    # Заголовок статьи

    Текст в Markdown...

Slug формируется автоматически из title (транслитерация кириллицы).
Поддерживаются .md и .txt (старый формат с SEO title/description в тексте).

Сначала можно привести папку к единому виду:
    python normalize.py --input "C:\\path\\to\\articles" --output "C:\\path\\to\\normalized"

Пример запуска:
    python upload.py --url https://example.com --token YOUR_TOKEN --folder ./article_test
    python upload.py --url https://example.com --token YOUR_TOKEN --folder ./article_test --dry-run
    python upload.py --url https://example.com --token YOUR_TOKEN --folder ./article_test --workers 6
"""

from __future__ import annotations

import argparse
import mimetypes
import sys
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

try:
    import requests
except ImportError:
    print('Установите зависимость: pip install requests', file=sys.stderr)
    sys.exit(1)

try:
    from article_parser import parse_article_file
except ImportError:
    from .article_parser import parse_article_file

COVER_NAMES = ('cover.jpg', 'cover.jpeg', 'cover.png', 'cover.webp')
# Безопасный размер части для серверов с nginx client_max_body_size ~4K.
CHUNK_MAX_BYTES = 1200
DIRECT_UPLOAD_MAX_BYTES = 2500
DEFAULT_WORKERS = 4
_print_lock = threading.Lock()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description='Загрузка статей блога (.md с YAML frontmatter) через REST API.',
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
        help='Папка с .md или .txt файлами статей',
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Только проверить файлы, без отправки на сервер',
    )
    parser.add_argument(
        '--draft',
        action='store_true',
        help='Загрузить как черновик (is_published=false)',
    )
    parser.add_argument(
        '--workers',
        type=int,
        default=DEFAULT_WORKERS,
        help=f'Число параллельных загрузок статей (по умолчанию: {DEFAULT_WORKERS})',
    )
    return parser.parse_args()


def load_article(md_path: Path, as_draft: bool) -> tuple[dict, str, Path | None]:
    article = parse_article_file(md_path)

    is_published = not as_draft
    meta = {
        'title': article.title,
        'slug': article.slug,
        'excerpt': '',
        'meta_title': _truncate(article.meta_title, 70),
        'meta_description': '',
        'is_published': is_published,
    }

    cover_path = find_cover(md_path)
    return meta, article.body, cover_path


def _truncate(value: str, max_len: int) -> str:
    if len(value) <= max_len:
        return value
    return value[: max_len - 1].rstrip() + '…'


def find_cover(md_path: Path) -> Path | None:
    for name in COVER_NAMES:
        candidate = md_path.parent / name
        if candidate.is_file():
            return candidate
    for suffix in ('.jpg', '.jpeg', '.png', '.webp'):
        candidate = md_path.with_suffix(suffix)
        if candidate.is_file():
            return candidate
    return None


def split_body(body: str, max_bytes: int = CHUNK_MAX_BYTES) -> list[str]:
    if not body:
        return ['']

    chunks: list[str] = []
    current: list[str] = []
    current_size = 0

    for char in body:
        char_size = len(char.encode('utf-8'))
        if current and current_size + char_size > max_bytes:
            chunks.append(''.join(current))
            current = [char]
            current_size = char_size
        else:
            current.append(char)
            current_size += char_size

    if current:
        chunks.append(''.join(current))
    return chunks


def build_import_payload(meta: dict, body_chunk: str, chunk_index: int, chunk_total: int) -> dict:
    payload = {
        'title': meta['title'],
        'slug': meta['slug'],
        'excerpt': meta.get('excerpt', ''),
        'meta_title': meta.get('meta_title', ''),
        'meta_description': meta.get('meta_description', ''),
        'is_published': bool(meta.get('is_published', False)),
        'chunk_index': chunk_index,
        'chunk_total': chunk_total,
        'body_chunk': body_chunk,
    }
    published_at = meta.get('published_at')
    if published_at:
        payload['published_at'] = published_at
    return payload


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


def _raise_for_response(response: requests.Response) -> None:
    if response.status_code < 400:
        return
    detail = response.text.strip() or response.reason
    if response.status_code == 500 and '<html>' in detail.lower():
        detail = (
            'HTTP 500 от nginx — вероятно, слишком большой запрос. '
            'Обновите скрипт (chunked import) или увеличьте client_max_body_size на сервере.'
        )
    raise RuntimeError(f'HTTP {response.status_code}: {detail}')


def upload_cover(
    session: requests.Session,
    api_base: str,
    slug: str,
    cover_path: Path,
) -> None:
    mime_type = mimetypes.guess_type(cover_path.name)[0] or 'application/octet-stream'
    with cover_path.open('rb') as cover_file:
        response = session.patch(
            f'{api_base}/posts/{slug}/',
            files={'cover_image': (cover_path.name, cover_file, mime_type)},
        )
    _raise_for_response(response)


def upload_article_chunked(
    session: requests.Session,
    api_base: str,
    meta: dict,
    body: str,
) -> tuple[str, dict, bool]:
    chunks = split_body(body)
    result: dict = {}
    created = False

    for index, chunk in enumerate(chunks):
        payload = build_import_payload(meta, chunk, index, len(chunks))
        response = session.post(f'{api_base}/import/', json=payload, timeout=120)
        _raise_for_response(response)
        if index + 1 == len(chunks):
            result = response.json()
            created = response.status_code == 201
        elif response.status_code != 202:
            _raise_for_response(response)

    slug = result.get('slug', meta['slug'])
    return slug, result, created


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
        status = 'черновик' if not payload['is_published'] else 'публикация'
        chunks = split_body(body)
        chunk_note = f', частей: {len(chunks)}' if len(chunks) > 1 else ''
        return f'[dry-run] «{payload["title"]}» ({slug}), {status}{cover_note}{chunk_note}'

    body_bytes = len(body.encode('utf-8'))
    use_chunked = body_bytes > DIRECT_UPLOAD_MAX_BYTES or cover_path is not None

    if use_chunked:
        slug, result, created = upload_article_chunked(session, api_base, meta, body)
        if cover_path:
            upload_cover(session, api_base, slug, cover_path)
        action = 'создание' if created else 'обновление'
        return f'OK: {action} «{result.get("title", slug)}» → {result.get("url", slug)}'

    exists = article_exists(session, api_base, slug)
    action = 'обновление' if exists else 'создание'

    if exists:
        response = session.patch(f'{api_base}/posts/{slug}/', json=payload)
    else:
        response = session.post(f'{api_base}/posts/', json=payload)

    _raise_for_response(response)
    result = response.json()
    return f'OK: {action} «{result.get("title", slug)}» → {result.get("url", slug)}'


def iter_source_files(folder: Path) -> list[Path]:
    if not folder.is_dir():
        raise NotADirectoryError(f'Папка не найдена: {folder}')
    files = sorted(
        path for path in folder.iterdir()
        if path.is_file() and path.suffix.lower() in {'.md', '.txt'}
    )
    if not files:
        raise FileNotFoundError(f'В {folder} нет .md или .txt файлов')
    return files


def make_session(token: str) -> requests.Session:
    session = requests.Session()
    session.headers.update({
        'Authorization': f'Token {token}',
        'Accept': 'application/json',
    })
    return session


def upload_file(
    md_path: Path,
    api_base: str,
    token: str,
    as_draft: bool,
    dry_run: bool,
) -> str:
    session = make_session(token)
    try:
        meta, body, cover_path = load_article(md_path, as_draft=as_draft)
        return upload_article(session, api_base, meta, body, cover_path, dry_run)
    finally:
        session.close()


def main() -> int:
    args = parse_args()
    if args.workers < 1:
        print('Параметр --workers должен быть >= 1', file=sys.stderr)
        return 1

    api_base = args.url.rstrip('/') + '/api/v1/blog'
    md_files = iter_source_files(args.folder)
    workers = min(args.workers, len(md_files))

    print(f'Статей: {len(md_files)}, потоков: {workers}')
    errors = 0

    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = {
            executor.submit(
                upload_file,
                md_path,
                api_base,
                args.token,
                args.draft,
                args.dry_run,
            ): md_path
            for md_path in md_files
        }
        for future in as_completed(futures):
            md_path = futures[future]
            try:
                message = future.result()
            except Exception as exc:
                errors += 1
                with _print_lock:
                    print(f'ОШИБКА [{md_path.name}]: {exc}', file=sys.stderr)
            else:
                with _print_lock:
                    print(message)

    if errors:
        print(f'\nГотово с ошибками: {errors}', file=sys.stderr)
        return 1

    print('\nГотово.')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
