import mimetypes

from django.conf import settings


def absolute_url(path: str, request=None) -> str:
    if not path.startswith('/'):
        path = f'/{path}'
    site_url = settings.SITE_URL.rstrip('/')
    if site_url:
        return f'{site_url}{path}'
    if request is not None:
        return request.build_absolute_uri(path)
    return path


def image_mime_type(url: str) -> str:
    mime_type, _ = mimetypes.guess_type(url)
    return mime_type or 'image/jpeg'
