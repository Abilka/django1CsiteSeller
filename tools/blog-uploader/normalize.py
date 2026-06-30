#!/usr/bin/env python3
"""
Приведение статей к единому формату .md с YAML frontmatter.

Поддерживаемые входные форматы:
- .md с frontmatter (как article_test)
- .txt со старым форматом: keyword, заголовок, SEO title/description, текст

Результат для каждой статьи:
    ---
    title: "Заголовок"
    keyword: "ключевое слово"
    category: "1С для бизнеса"
    meta_title: "SEO title, если отличается"
    ---

    # Заголовок

    Текст статьи...

Примеры:
    python normalize.py --input "C:\\Users\\Alexey\\Documents\\1c alex"
    python normalize.py --input ./articles --output ./articles-normalized
    python normalize.py --input ./articles --in-place
    python normalize.py --input ./articles --dry-run
"""

from __future__ import annotations

import argparse
import shutil
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

try:
    from article_parser import NormalizedArticle, parse_article_file, render_markdown
except ImportError:
    from .article_parser import NormalizedArticle, parse_article_file, render_markdown


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description='Приведение статей (.txt / .md) к единому формату Markdown.',
    )
    parser.add_argument(
        '--input',
        required=True,
        type=Path,
        help='Папка с исходными статьями',
    )
    parser.add_argument(
        '--output',
        type=Path,
        help='Папка для нормализованных .md (по умолчанию: <input>/normalized)',
    )
    parser.add_argument(
        '--in-place',
        action='store_true',
        help='Заменить исходники: .txt -> .md, старые .txt в backup/',
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Только показать, что будет сделано',
    )
    parser.add_argument(
        '--workers',
        type=int,
        default=4,
        help='Число потоков (по умолчанию: 4)',
    )
    return parser.parse_args()


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


def output_path_for(article: NormalizedArticle, source: Path, output_dir: Path) -> Path:
    stem = source.stem
    hash_suffix = ''
    if '-' in stem:
        maybe_hash = stem.rsplit('-', 1)[-1]
        if len(maybe_hash) == 8 and maybe_hash.isalnum():
            hash_suffix = f'-{maybe_hash}'
    filename = f'{article.slug}{hash_suffix}.md'
    return output_dir / filename


def normalize_file(source: Path, output_dir: Path, dry_run: bool) -> tuple[str, str | None]:
    article = parse_article_file(source)
    target = output_path_for(article, source, output_dir)
    message = f'{source.name} -> {target.name}'

    if dry_run:
        return message, None

    output_dir.mkdir(parents=True, exist_ok=True)
    target.write_text(render_markdown(article), encoding='utf-8')
    return message, str(target)


def main() -> int:
    args = parse_args()
    if args.workers < 1:
        print('Параметр --workers должен быть >= 1', file=sys.stderr)
        return 1

    source_files = iter_source_files(args.input)
    if args.in_place:
        output_dir = args.input
        backup_dir = args.input / 'backup'
    else:
        output_dir = args.output or (args.input / 'normalized')

    print(f'Файлов: {len(source_files)}, выход: {output_dir}')
    errors = 0
    converted = 0
    workers = min(args.workers, len(source_files))

    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = {
            executor.submit(normalize_file, source, output_dir, args.dry_run): source
            for source in source_files
        }
        for future in as_completed(futures):
            source = futures[future]
            try:
                message, _ = future.result()
                print(message)
                converted += 1
            except Exception as exc:
                errors += 1
                print(f'ОШИБКА [{source.name}]: {exc}', file=sys.stderr)

    if args.in_place and not args.dry_run and converted:
        backup_dir.mkdir(exist_ok=True)
        for source in source_files:
            if source.suffix.lower() == '.txt':
                shutil.move(str(source), backup_dir / source.name)

    if errors:
        print(f'\nГотово с ошибками: {errors}', file=sys.stderr)
        return 1

    print(f'\nГотово: {converted} статей.')
    if not args.in_place and not args.dry_run:
        print(f'Нормализованные файлы: {output_dir}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
