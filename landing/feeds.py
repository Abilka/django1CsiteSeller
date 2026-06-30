from django.contrib.syndication.views import Feed
from django.urls import reverse

from landing.tools.release_feed import get_release_feed


class ReleaseFeed(Feed):
    title = 'Новые релизы типовых конфигураций 1С'
    link = '/novye-relizy/'
    description = 'Лента новых релизов типовых конфигураций 1С:Предприятие 8.'

    def items(self):
        return get_release_feed(days=90, limit=50)

    def item_title(self, item):
        return f'{item.configuration_name} — {item.version}'

    def item_description(self, item):
        parts = [f'Конфигурация: {item.configuration_name}', f'Релиз: {item.version}']
        if item.min_platform:
            parts.append(f'Мин. платформа: {item.min_platform}')
        return '. '.join(parts)

    def item_link(self, item):
        return reverse('landing:release_feed') + f'?configuration={item.configuration_slug}'

    def item_pubdate(self, item):
        if item.release_date:
            from datetime import datetime
            from django.utils import timezone
            return timezone.make_aware(datetime.combine(item.release_date, datetime.min.time()))
        return None
