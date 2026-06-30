import json
import logging
import urllib.error
import urllib.request

from django.conf import settings

logger = logging.getLogger(__name__)

INDEXNOW_ENDPOINT = 'https://api.indexnow.org/indexnow'
INDEXNOW_BATCH_SIZE = 25


def _chunked(items: list, batch_size: int):
    for index in range(0, len(items), batch_size):
        yield items[index:index + batch_size]


def build_absolute_url(path: str) -> str:
    base = settings.SITE_URL.rstrip('/')
    if not path.startswith('/'):
        path = f'/{path}'
    return f'{base}{path}'


def notify_indexnow(urls: list[str]) -> bool:
    if not settings.INDEXNOW_ENABLED:
        return False
    if not settings.SITE_URL or not settings.INDEXNOW_KEY:
        logger.warning('IndexNow skipped: SITE_URL or INDEXNOW_KEY is not configured')
        return False

    absolute_urls = []
    for url in urls:
        if url.startswith('http://') or url.startswith('https://'):
            absolute_urls.append(url)
        else:
            absolute_urls.append(build_absolute_url(url))

    host = settings.SITE_HOST
    if not host:
        logger.warning('IndexNow skipped: SITE_HOST is not configured')
        return False

    payload = {
        'host': host,
        'key': settings.INDEXNOW_KEY,
        'keyLocation': build_absolute_url(f'/{settings.INDEXNOW_KEY}.txt'),
        'urlList': absolute_urls,
    }

    data = json.dumps(payload).encode('utf-8')
    request = urllib.request.Request(
        INDEXNOW_ENDPOINT,
        data=data,
        headers={'Content-Type': 'application/json; charset=utf-8'},
        method='POST',
    )

    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            logger.info('IndexNow notified (%s): %s', response.status, absolute_urls)
            return True
    except urllib.error.HTTPError as exc:
        logger.warning('IndexNow HTTP error %s: %s', exc.code, exc.read())
    except urllib.error.URLError as exc:
        logger.warning('IndexNow network error: %s', exc.reason)
    except Exception:
        logger.exception('IndexNow unexpected error')

    return False


def submit_urls_batched(urls: list[str], batch_size: int = INDEXNOW_BATCH_SIZE) -> dict:
    unique_urls = list(dict.fromkeys(urls))
    if not unique_urls:
        return {
            'total': 0,
            'batches_total': 0,
            'batches_ok': 0,
            'batches_failed': 0,
            'failed_batches': [],
        }

    batches_ok = 0
    batches_failed = 0
    failed_batches = []
    batches = list(_chunked(unique_urls, batch_size))

    for batch_number, batch in enumerate(batches, start=1):
        if notify_indexnow(list(batch)):
            batches_ok += 1
        else:
            batches_failed += 1
            failed_batches.append(batch_number)

    return {
        'total': len(unique_urls),
        'batches_total': len(batches),
        'batches_ok': batches_ok,
        'batches_failed': batches_failed,
        'failed_batches': failed_batches,
    }


def build_indexnow_admin_messages(result: dict, *, skipped: int = 0) -> list[tuple[str, str]]:
    messages_out: list[tuple[str, str]] = []

    if not result['total']:
        messages_out.append(('warning', 'Нет URL для отправки в IndexNow.'))
        return messages_out

    if skipped:
        messages_out.append(('warning', f'Пропущено неопубликованных статей: {skipped}.'))

    if result['batches_failed']:
        messages_out.append((
            'error',
            (
                f'IndexNow: отправлено {result["total"]} URL в {result["batches_total"]} '
                f'пачках по {INDEXNOW_BATCH_SIZE}, но {result["batches_failed"]} '
                f'пачек не удалось (№ {", ".join(map(str, result["failed_batches"]))}). '
                'Проверьте SITE_URL, SITE_HOST, INDEXNOW_KEY и логи.'
            ),
        ))
    else:
        messages_out.append((
            'success',
            (
                f'IndexNow: отправлено {result["total"]} URL '
                f'({result["batches_total"]} пачек по {INDEXNOW_BATCH_SIZE}).'
            ),
        ))

    return messages_out


def submit_blog_posts(posts, batch_size: int = INDEXNOW_BATCH_SIZE) -> dict:
    urls = [build_absolute_url(post.get_absolute_url()) for post in posts]
    return submit_urls_batched(urls, batch_size=batch_size)
