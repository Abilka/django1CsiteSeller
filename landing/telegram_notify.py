import html
import json
import logging
import urllib.error
import urllib.request

from .models import SiteSettings

logger = logging.getLogger(__name__)


def _telegram_settings():
    settings = SiteSettings.load()
    token = (settings.telegram_bot_token or '').strip()
    chat_id = (settings.telegram_chat_id or '').strip()
    return settings, token, chat_id


def _format_lead_message(lead) -> str:
    lines = [
        '🆕 <b>Новая заявка с сайта</b>',
        '',
        f'<b>Имя:</b> {html.escape(lead.name)}',
        f'<b>Телефон:</b> {html.escape(lead.phone)}',
    ]
    if lead.email:
        lines.append(f'<b>Email:</b> {html.escape(lead.email)}')
    lines.append(f'<b>Услуга:</b> {html.escape(lead.get_service_display())}')
    if lead.message:
        lines.append('')
        lines.append(f'<b>Задача:</b>\n{html.escape(lead.message)}')
    return '\n'.join(lines)


def send_telegram_message(text: str, *, chat_id: str | None = None) -> tuple[bool, str]:
    settings, token, resolved_chat_id = _telegram_settings()
    target_chat_id = (chat_id or resolved_chat_id).strip()
    if not settings.telegram_notify_enabled:
        return False, 'Уведомления отключены: включите «Дублировать заявки в Telegram» в настройках сайта.'
    if not token:
        return False, 'Не указан токен Telegram-бота.'
    if not target_chat_id:
        return False, 'Не указан Chat ID для уведомлений.'

    payload = {
        'chat_id': target_chat_id,
        'text': text,
        'parse_mode': 'HTML',
        'disable_web_page_preview': True,
    }

    url = f'https://api.telegram.org/bot{token}/sendMessage'
    data = json.dumps(payload).encode('utf-8')
    request = urllib.request.Request(
        url,
        data=data,
        headers={'Content-Type': 'application/json'},
        method='POST',
    )

    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            if response.status == 200:
                return True, ''
            body = response.read().decode('utf-8', errors='replace')
            logger.error('Telegram API unexpected status %s: %s', response.status, body)
            return False, f'Telegram API вернул статус {response.status}.'
    except urllib.error.HTTPError as exc:
        body = exc.read().decode('utf-8', errors='replace')
        logger.error('Telegram API HTTP error %s: %s', exc.code, body)
        try:
            description = json.loads(body).get('description', body)
        except json.JSONDecodeError:
            description = body
        return False, f'Telegram API: {description}'
    except urllib.error.URLError as exc:
        logger.exception('Failed to send message to Telegram: %s', exc)
        return False, f'Сетевая ошибка: {exc.reason}'


def send_lead_to_telegram(lead) -> bool:
    ok, error = send_telegram_message(_format_lead_message(lead))
    if not ok:
        logger.warning('Lead %s was not sent to Telegram: %s', lead.pk, error)
    return ok
