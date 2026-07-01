from __future__ import annotations

import json
import re
import urllib.error
import urllib.request
from dataclasses import dataclass
from datetime import date, datetime
from html import unescape

from landing.services.version_utils import normalize_version

ITS_BASE_URL = 'https://its.1c.ru'
ITS_UPDINFO_URL = f'{ITS_BASE_URL}/db/updinfo'
ITS_CONTENT_BASE = f'{ITS_BASE_URL}/db/content/updinfo/'
ITS_TOC_JSON_URL = f'{ITS_BASE_URL}/db/metadata/updinfo/toc/3.json'
DEFAULT_TIMEOUT = 90
USER_AGENT = '1CsiteSeller/1.0 (+its-release-sync)'

VERSION_PATTERN = re.compile(r'^\d+(?:\.\d+)+$')
CONFIG_LINK_PATTERN = re.compile(
    r'<a\s+href="/db/updinfo/content/(\d+)/hdoc"[^>]*>([^<]+)</a>',
    re.IGNORECASE,
)
VERSION_LINK_PATTERN = re.compile(
    r'<a\s+href="/db/updinfo/content/(\d+)/hdoc"[^>]*>\s*Новое в версии\s+([^<]+?)\s*</a>',
    re.IGNORECASE,
)
DATE_PATTERN = re.compile(r'^(\d{2})\.(\d{2})\.(\d{4})$')

# Соответствие разделов updinfo на ИТС основному slug конфигурации в базе.
# Несколько записей в БД (например, ПРОФ и базовая) могут ссылаться на один its_doc_id.
ITS_DOC_ID_TO_SLUG: dict[int, str] = {
    4: 'rel_1c_bp30',
    210: 'rel_1c_zup30',
    284: 'rel_1c_ut11',
}

ITS_DOC_ID_EXTRA_SLUGS: dict[int, list[str]] = {
    4: ['rel_1c_bp30b'],
}

ITS_NAME_TO_SLUG: dict[str, str] = {
    '1С:Бухгалтерия 8': 'rel_1c_bp30',
    '1С:Зарплата и Управление Персоналом, ред. 3': 'rel_1c_zup30',
    '1С:Управление торговлей 11': 'rel_1c_ut11',
}


class ItsFetchError(Exception):
    pass


@dataclass
class ItsConfiguration:
    doc_id: int
    name: str
    content_path: str
    slug: str | None = None


@dataclass
class ItsVersion:
    doc_id: int
    version: str
    url: str
    release_date: date | None = None


def build_its_version_url(doc_id: int) -> str:
    return f'{ITS_UPDINFO_URL}/content/{doc_id}/hdoc'


def _clean_text(value: str) -> str:
    return unescape(value).strip()


def fetch_url(url: str, timeout: int = DEFAULT_TIMEOUT) -> str:
    request = urllib.request.Request(url, headers={'User-Agent': USER_AGENT})
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return response.read().decode('cp1251', errors='replace')
    except urllib.error.URLError as exc:
        raise ItsFetchError(f'Не удалось загрузить {url}: {exc}') from exc


def resolve_configuration_slug(doc_id: int, name: str) -> str | None:
    slug = ITS_DOC_ID_TO_SLUG.get(doc_id)
    if slug:
        return slug
    return ITS_NAME_TO_SLUG.get(_clean_text(name))


def parse_configurations(html: str) -> list[ItsConfiguration]:
    configurations: list[ItsConfiguration] = []
    seen: set[int] = set()
    for match in CONFIG_LINK_PATTERN.finditer(html):
        doc_id = int(match.group(1))
        if doc_id in seen:
            continue
        name = _clean_text(match.group(2))
        if name.lower() == 'архив':
            continue
        seen.add(doc_id)
        configurations.append(
            ItsConfiguration(
                doc_id=doc_id,
                name=name,
                content_path='',
                slug=resolve_configuration_slug(doc_id, name),
            )
        )
    return configurations


def parse_configuration_versions(html: str) -> list[ItsVersion]:
    versions: list[ItsVersion] = []
    seen: set[str] = set()
    for index, match in enumerate(VERSION_LINK_PATTERN.finditer(html)):
        version = normalize_version(match.group(2))
        if not version or not VERSION_PATTERN.match(version) or version in seen:
            continue
        seen.add(version)
        doc_id = int(match.group(1))
        versions.append(
            ItsVersion(
                doc_id=doc_id,
                version=version,
                url=build_its_version_url(doc_id),
                release_date=None,
            )
        )
    return versions


def _parse_release_date(raw: str | None) -> date | None:
    if not raw:
        return None
    match = DATE_PATTERN.match(raw.strip())
    if not match:
        return None
    day, month, year = match.groups()
    try:
        return datetime.strptime(f'{day}.{month}.{year}', '%d.%m.%Y').date()
    except ValueError:
        return None


def fetch_version_release_date(doc_id: int) -> date | None:
    url = f'{ITS_BASE_URL}/db/metadata/updinfo/searchattributes/{doc_id}/hdoc.json'
    try:
        payload = json.loads(fetch_url(url, timeout=30))
    except (ItsFetchError, json.JSONDecodeError):
        return None
    return _parse_release_date(payload.get('datetime'))


def enrich_versions_with_dates(
    versions: list[ItsVersion],
    *,
    fetch_dates: bool = True,
) -> list[ItsVersion]:
    if not fetch_dates:
        return versions
    enriched: list[ItsVersion] = []
    for item in versions:
        release_date = fetch_version_release_date(item.doc_id)
        enriched.append(
            ItsVersion(
                doc_id=item.doc_id,
                version=item.version,
                url=item.url,
                release_date=release_date or item.release_date,
            )
        )
    return enriched


def fetch_updinfo_index() -> str:
    return fetch_url(f'{ITS_CONTENT_BASE}src/index.htm')


def fetch_configuration_index(content_path: str) -> str:
    path = content_path.lstrip('/')
    if not path:
        raise ItsFetchError('Не указан путь к разделу конфигурации на ИТС.')
    if path.startswith('http'):
        return fetch_url(path)
    return fetch_url(f'{ITS_CONTENT_BASE}{path}')


def resolve_configuration_content_path(doc_id: int, toc_html: str | None = None) -> str:
    if toc_html is None:
        toc_html = fetch_url(ITS_TOC_JSON_URL)
    data = json.loads(toc_html)

    def walk(node: dict) -> str | None:
        if node.get('doc_id') == doc_id:
            path = node.get('path')
            if path:
                return path
        for child in node.get('children', []):
            found = walk(child)
            if found:
                return found
        return None

    path = walk(data['data']['toc'])
    if not path:
        raise ItsFetchError(f'Не найден путь к конфигурации doc_id={doc_id} в оглавлении ИТС.')
    return path


def fetch_configuration_versions(
    configuration: ItsConfiguration,
    *,
    fetch_dates: bool = False,
) -> list[ItsVersion]:
    content_path = configuration.content_path
    if not content_path:
        content_path = resolve_configuration_content_path(configuration.doc_id)
    html = fetch_configuration_index(content_path)
    versions = parse_configuration_versions(html)
    return enrich_versions_with_dates(versions, fetch_dates=fetch_dates)
