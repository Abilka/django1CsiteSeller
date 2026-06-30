from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ToolMeta:
    slug: str
    name: str
    description: str
    url_name: str
    tag: str
    icon: str = 'tool'


TOOL_REGISTRY: dict[str, ToolMeta] = {
    'platform-check': ToolMeta(
        slug='platform-check',
        name='Проверка платформы 1С',
        description='Совместимость версии платформы с релизом конфигурации.',
        url_name='landing:platform_check',
        tag='Администрирование',
    ),
    'release-feed': ToolMeta(
        slug='release-feed',
        name='Лента релизов 1С',
        description='Новые релизы типовых конфигураций за выбранный период.',
        url_name='landing:release_feed',
        tag='Обновления',
    ),
    'task-estimator': ToolMeta(
        slug='task-estimator',
        name='Оценщик типовых задач',
        description='Соберите чеклист работ и получите ориентировочную стоимость.',
        url_name='landing:task_estimator',
        tag='Внедрение',
    ),
    'query-formatter': ToolMeta(
        slug='query-formatter',
        name='Форматтер запросов 1С',
        description='Форматирование и базовая проверка текста запроса.',
        url_name='landing:query_formatter',
        tag='Разработка',
    ),
    'migration-calc': ToolMeta(
        slug='migration-calc',
        name='Калькулятор миграции',
        description='Оценка этапов и стоимости перехода между конфигурациями.',
        url_name='landing:migration_calculator',
        tag='Миграция',
    ),
}


def get_tool(slug: str) -> ToolMeta | None:
    return TOOL_REGISTRY.get(slug)


def list_tools() -> list[ToolMeta]:
    return list(TOOL_REGISTRY.values())
