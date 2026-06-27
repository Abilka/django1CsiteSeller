import json
import logging
import urllib.error
import urllib.request

from django.conf import settings

logger = logging.getLogger(__name__)

INDEXNOW_ENDPOINT = 'https://api.indexnow.org/indexnow'


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
