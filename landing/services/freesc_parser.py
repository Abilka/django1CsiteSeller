from __future__ import annotations

import re
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from datetime import date, datetime
from html import unescape

from landing.services.update_calculator import parse_from_versions

FREESC_BASE_URL = 'https://www.freesc.ru'
FREESC_CALC_URL = f'{FREESC_BASE_URL}/1spredpriyatie/calc-update.html'
FREESC_LIST_URL = f'{FREESC_BASE_URL}/1spredpriyatie/spisok-rel.html'
DEFAULT_TIMEOUT = 90
USER_AGENT = '1CsiteSeller/1.0 (+release-sync)'

ROW_PATTERN = re.compile(
    r'<tr>\s*'
    r'<td[^>]*>(?P<version>[^<]*)</td>\s*'
    r'<td[^>]*>(?P<date>[^<]*)</td>\s*'
    r'<td[^>]*>(?P<from_versions>[^<]*)</td>\s*'
    r'<td[^>]*>(?P<platform>[^<]*)</td>\s*'
    r'</tr>',
    re.IGNORECASE,
)
TABLE_PATTERN = re.compile(
    r'<table class="table1"[^>]*>(?P<body>.*?)</table>',
    re.IGNORECASE | re.DOTALL,
)
CONFIG_OPTION_PATTERN = re.compile(
    r'<option\s+(?:selected\s+)?value=\s*([^\s>]+)\s*>([^<]+)</option>',
    re.IGNORECASE,
)
CELL_CLEANUP = re.compile(r'&nbsp;')
VERSION_PATTERN = re.compile(r'^\d+(?:\.\d+)+$')


class FreescFetchError(Exception):
    pass


@dataclass
class FreescConfiguration:
    slug: str
    name: str
    sort_order: int = 0


@dataclass
class FreescReleaseRow:
    version: str
    release_date: date | None
    from_versions: list[str]
    min_platform: str
    sort_order: int


def _clean_cell(value: str) -> str:
    return unescape(CELL_CLEANUP.sub(' ', value)).strip()


def fetch_url(url: str, data: dict | None = None, timeout: int = DEFAULT_TIMEOUT) -> str:
    payload = None
    headers = {'User-Agent': USER_AGENT}
    if data is not None:
        payload = urllib.parse.urlencode(data).encode()
        headers['Content-Type'] = 'application/x-www-form-urlencoded'
    request = urllib.request.Request(url, data=payload, method='POST' if payload else 'GET', headers=headers)
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return response.read().decode('utf-8', errors='replace')
    except urllib.error.URLError as exc:
        raise FreescFetchError(f'Не удалось загрузить {url}: {exc}') from exc


def fetch_calc_update_page(configuration_slug: str | None = None) -> str:
    data = {'operation': 'Обновления'}
    if configuration_slug:
        data['cur_conf'] = configuration_slug
    return fetch_url(FREESC_CALC_URL, data=data)


def fetch_release_list_page(configuration_slug: str) -> str:
    return fetch_url(FREESC_LIST_URL, data={'cur_conf': configuration_slug})


def parse_configurations(html: str) -> list[FreescConfiguration]:
    configurations: list[FreescConfiguration] = []
    seen: set[str] = set()
    for index, match in enumerate(CONFIG_OPTION_PATTERN.finditer(html)):
        slug = _clean_cell(match.group(1))
        name = _clean_cell(match.group(2))
        if not slug or slug == '0' or slug in seen:
            continue
        if not slug.startswith('rel_1c_'):
            continue
        seen.add(slug)
        configurations.append(FreescConfiguration(slug=slug, name=name, sort_order=index))
    return configurations


def parse_release_table(html: str) -> list[FreescReleaseRow]:
    table_match = TABLE_PATTERN.search(html)
    source = table_match.group('body') if table_match else html
    rows: list[FreescReleaseRow] = []
    for index, match in enumerate(ROW_PATTERN.finditer(source)):
        version = _clean_cell(match.group('version'))
        if not VERSION_PATTERN.match(version):
            continue
        date_raw = _clean_cell(match.group('date'))
        from_raw = _clean_cell(match.group('from_versions'))
        platform = _clean_cell(match.group('platform'))
        release_date = None
        if date_raw:
            try:
                release_date = datetime.strptime(date_raw, '%Y-%m-%d').date()
            except ValueError:
                release_date = None
        rows.append(
            FreescReleaseRow(
                version=version,
                release_date=release_date,
                from_versions=parse_from_versions(from_raw),
                min_platform=platform.strip('; ').strip(),
                sort_order=index,
            )
        )
    return rows


def parse_configuration_releases(html: str) -> list[str]:
    versions: list[str] = []
    for match in CONFIG_OPTION_PATTERN.finditer(html):
        value = _clean_cell(match.group(1))
        if VERSION_PATTERN.match(value):
            versions.append(value)
    return versions
