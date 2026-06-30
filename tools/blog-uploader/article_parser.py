from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from slugify import slugify as make_slug

FRONTMATTER_RE = re.compile(r'^---\r?\n(.*?)\r?\n---\r?\n', re.DOTALL)
SETEXT_HEADER_RE = re.compile(r'^[=-]{3,}\s*$')
SEO_INLINE_RE = re.compile(
    r'^SEO\s+[Tt]itle:\s*"?(.+?)"?\s*$',
    re.IGNORECASE,
)
META_INLINE_RE = re.compile(
    r'^Meta\s+[Dd]escrip\w*:\s*"?(.+?)"?\s*$',
    re.IGNORECASE,
)
H1_PREFIX_RE = re.compile(r'^H1:\s*', re.IGNORECASE)
DEFAULT_CATEGORY = '1С для бизнеса'
SKIP_BODY_LABELS = frozenset({
    'содержание',
    'содержание:',
    'описание',
    'описание:',
})


@dataclass
class NormalizedArticle:
    title: str
    keyword: str
    category: str
    meta_title: str
    body: str
    source_path: Path | None = None

    @property
    def slug(self) -> str:
        slug = make_slug(self.title, max_length=220)
        if not slug and self.source_path is not None:
            slug = self.source_path.stem
        return slug


def parse_article_file(path: Path) -> NormalizedArticle:
    text = path.read_text(encoding='utf-8')
    article = parse_article_text(text)
    article.source_path = path
    return article


def parse_article_text(text: str) -> NormalizedArticle:
    if FRONTMATTER_RE.match(text):
        return _parse_markdown(text)
    return _parse_legacy_text(text)


def render_markdown(article: NormalizedArticle) -> str:
    lines = [
        '---',
        f'title: {_yaml_quote(article.title)}',
        f'keyword: {_yaml_quote(article.keyword)}',
        f'category: {_yaml_quote(article.category)}',
    ]
    if article.meta_title and article.meta_title != article.title:
        lines.append(f'meta_title: {_yaml_quote(article.meta_title)}')
    lines.extend(['---', '', article.body.rstrip(), ''])
    return '\n'.join(lines)


def _yaml_quote(value: str) -> str:
    value = value.replace('\r', ' ').replace('\n', ' ').strip()
    if not value:
        return '""'
    if re.search(r'[:#\[\]{},&*?|>!%@`"\']', value):
        return '"' + value.replace('\\', '\\\\').replace('"', '\\"') + '"'
    return f'"{value}"'


def _parse_markdown(text: str) -> NormalizedArticle:
    match = FRONTMATTER_RE.match(text)
    if not match:
        raise ValueError('Некорректный frontmatter')

    raw_meta = _parse_frontmatter_block(match.group(1))
    body = _normalize_body(raw_meta.get('title', ''), text[match.end():])
    title = raw_meta.get('title', '').strip() or _guess_title_from_body(body)
    if not title:
        raise ValueError('Не удалось определить title')

    return NormalizedArticle(
        title=title,
        keyword=raw_meta.get('keyword', '').strip() or title,
        category=raw_meta.get('category', '').strip() or DEFAULT_CATEGORY,
        meta_title=raw_meta.get('meta_title', '').strip(),
        body=body,
    )


def _parse_legacy_text(text: str) -> NormalizedArticle:
    lines = text.replace('\r\n', '\n').replace('\r', '\n').split('\n')
    non_empty = [index for index, line in enumerate(lines) if line.strip()]
    if not non_empty:
        raise ValueError('Пустой файл')

    keyword = lines[non_empty[0]].strip()
    index = non_empty[0] + 1
    while index < len(lines) and not lines[index].strip():
        index += 1
    if index >= len(lines):
        raise ValueError('Не найден заголовок')

    title = H1_PREFIX_RE.sub('', lines[index].strip())
    index += 1
    if index < len(lines) and SETEXT_HEADER_RE.match(lines[index].strip()):
        index += 1

    meta_title = ''
    while index < len(lines):
        line = lines[index].strip()
        if not line:
            index += 1
            continue

        seo_match = SEO_INLINE_RE.match(line)
        if seo_match:
            meta_title = _strip_quotes(seo_match.group(1))
            index += 1
            continue

        if line.lower() in {'seo title', 'seo title:'}:
            index += 1
            while index < len(lines) and not lines[index].strip():
                index += 1
            if index < len(lines):
                meta_title = lines[index].strip()
                index += 1
            continue

        if META_INLINE_RE.match(line):
            index += 1
            continue

        if line.lower().startswith('meta '):
            index += 1
            if index < len(lines) and lines[index].strip() and not lines[index].strip().startswith('Meta '):
                index += 1
            continue

        if line.lower() in SKIP_BODY_LABELS:
            index += 1
            continue

        break

    body = '\n'.join(lines[index:])
    body = _normalize_body(title, body)

    return NormalizedArticle(
        title=title,
        keyword=keyword or title,
        category=DEFAULT_CATEGORY,
        meta_title=meta_title,
        body=body,
    )


def _parse_frontmatter_block(block: str) -> dict[str, str]:
    meta: dict[str, str] = {}
    for line in block.splitlines():
        line = line.strip()
        if not line or line.startswith('#') or ':' not in line:
            continue
        key, _, value = line.partition(':')
        meta[key.strip()] = _strip_quotes(value.strip())
    return meta


def _strip_quotes(value: str) -> str:
    value = value.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in ('"', "'"):
        return value[1:-1]
    return value


def _guess_title_from_body(body: str) -> str:
    for line in body.splitlines():
        stripped = line.strip()
        if stripped.startswith('# '):
            return stripped[2:].strip()
    return ''


def _normalize_body(title: str, body: str) -> str:
    body = body.lstrip('\n')
    body = _strip_duplicate_heading(title, body)
    body = _convert_setext_headers(body)
    body = _ensure_leading_h1(title, body)
    return body.strip() + '\n'


def _strip_duplicate_heading(title: str, body: str) -> str:
    lines = body.splitlines()
    while lines:
        first = lines[0].strip()
        if not first:
            lines.pop(0)
            continue
        normalized = H1_PREFIX_RE.sub('', first).strip()
        if normalized == title or first == f'# {title}':
            lines.pop(0)
            if lines and SETEXT_HEADER_RE.match(lines[0].strip()):
                lines.pop(0)
            while lines and not lines[0].strip():
                lines.pop(0)
            continue
        break
    return '\n'.join(lines)


def _convert_setext_headers(body: str) -> str:
    lines = body.splitlines()
    result: list[str] = []
    index = 0
    while index < len(lines):
        if (
            index + 1 < len(lines)
            and lines[index].strip()
            and SETEXT_HEADER_RE.match(lines[index + 1].strip())
        ):
            underline = lines[index + 1].strip()
            prefix = '#' if underline.startswith('=') else '##'
            result.append(f'{prefix} {lines[index].strip()}')
            index += 2
            continue
        result.append(lines[index])
        index += 1
    return '\n'.join(result)


def _ensure_leading_h1(title: str, body: str) -> str:
    for line in body.splitlines():
        if line.strip():
            if line.strip().startswith('# '):
                return body
            break
    return f'# {title}\n\n{body}'.strip()
