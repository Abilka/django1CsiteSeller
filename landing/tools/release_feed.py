from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta

from django.db.models import QuerySet

from landing.models import OneCConfiguration, OneCRelease


@dataclass
class ReleaseFeedItem:
    configuration_slug: str
    configuration_name: str
    version: str
    release_date: date | None
    min_platform: str


def get_release_feed(
    days: int = 90,
    configuration_slug: str | None = None,
    limit: int = 100,
) -> list[ReleaseFeedItem]:
    since = date.today() - timedelta(days=max(days, 1))
    queryset: QuerySet[OneCRelease] = (
        OneCRelease.objects.select_related('configuration')
        .filter(
            configuration__is_published=True,
            release_date__gte=since,
        )
        .order_by('-release_date', 'sort_order', '-id')
    )
    if configuration_slug:
        queryset = queryset.filter(configuration__slug=configuration_slug)

    items: list[ReleaseFeedItem] = []
    for release in queryset[:limit]:
        items.append(
            ReleaseFeedItem(
                configuration_slug=release.configuration.slug,
                configuration_name=release.configuration.name,
                version=release.version,
                release_date=release.release_date,
                min_platform=release.min_platform.strip().strip(';').strip(),
            )
        )
    return items


def get_feed_configurations() -> list[OneCConfiguration]:
    return list(OneCConfiguration.objects.filter(is_published=True).order_by('sort_order', 'name'))
