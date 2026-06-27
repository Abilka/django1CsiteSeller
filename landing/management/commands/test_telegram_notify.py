from django.core.management.base import BaseCommand

from landing.models import SiteSettings
from landing.telegram_notify import send_telegram_message


class Command(BaseCommand):
    help = 'Проверить отправку уведомлений в Telegram'

    def handle(self, *args, **options):
        settings = SiteSettings.load()
        self.stdout.write(f'Уведомления включены: {settings.telegram_notify_enabled}')
        self.stdout.write(f'Токен задан: {bool((settings.telegram_bot_token or "").strip())}')
        self.stdout.write(f'Chat ID: {repr((settings.telegram_chat_id or "").strip())}')

        ok, error = send_telegram_message('✅ Тестовое уведомление с сайта. Если вы видите это сообщение — настройки верны.')
        if ok:
            self.stdout.write(self.style.SUCCESS('Сообщение отправлено успешно.'))
        else:
            self.stdout.write(self.style.ERROR(f'Ошибка: {error}'))
