from datetime import datetime

from django.contrib.syndication.views import Feed
from django.urls import reverse
from django.utils import timezone

from config.feed_utils import absolute_url
from landing.models import OneCConfiguration
from landing.tools.release_feed import get_release_feed


class ReleaseFeed(Feed):
    description = 'Лента новых релизов типовых конфигураций 1С:Предприятие 8.'

    def get_object(self, request, *args, **kwargs):
        configuration = request.GET.get('configuration', '').strip()
        try:
            days = int(request.GET.get('days', 90))
        except (TypeError, ValueError):
            days = 90
        days = max(1, min(days, 365))
        return {'configuration': configuration, 'days': days}

    def title(self, obj):
        title = 'Новые релизы типовых конфигураций 1С'
        if obj and obj.get('configuration'):
            config = OneCConfiguration.objects.filter(
                slug=obj['configuration'],
                is_published=True,
            ).first()
            if config:
                title = f'Новые релизы {config.name}'
        return title

    def link(self, obj):
        path = reverse('landing:release_feed')
        if not obj:
            return path
        params = []
        if obj.get('configuration'):
            params.append(f'configuration={obj["configuration"]}')
        if obj.get('days') != 90:
            params.append(f'days={obj["days"]}')
        if params:
            path = f'{path}?{"&".join(params)}'
        return path

    def items(self, obj):
        configuration_slug = obj.get('configuration') or None if obj else None
        days = obj.get('days', 90) if obj else 90
        return get_release_feed(
            days=days,
            configuration_slug=configuration_slug,
            limit=50,
        )

    def item_title(self, item):
        return f'{item.configuration_name} — {item.version}'

    def item_description(self, item):
        parts = [f'Конфигурация: {item.configuration_name}', f'Релиз: {item.version}']
        if item.min_platform:
            parts.append(f'Мин. платформа: {item.min_platform}')
        return '. '.join(parts)

    def item_link(self, item):
        return absolute_url(
            reverse('landing:release_feed') + f'?configuration={item.configuration_slug}'
        )

    def item_pubdate(self, item):
        if item.release_date:
            return timezone.make_aware(datetime.combine(item.release_date, datetime.min.time()))
        return None
