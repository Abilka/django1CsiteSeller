from django.conf import settings
from django.templatetags.static import static

from config.seo import organization_schema, website_schema
from landing.models import SiteSettings, TeamMember


def _static_url(path: str) -> str:
    try:
        return static(path)
    except ValueError:
        prefix = settings.STATIC_URL
        if not prefix.endswith('/'):
            prefix += '/'
        if not prefix.startswith('/'):
            prefix = f'/{prefix}'
        return prefix + path


def _absolute_url(path: str, request, site_url: str) -> str:
    if not path:
        return ''
    if path.startswith(('http://', 'https://')):
        return path
    if site_url:
        return f'{site_url}{path}'
    if request:
        return request.build_absolute_uri(path)
    return path


def site(request):
    site_url = settings.SITE_URL.rstrip('/') if settings.SITE_URL else ''
    canonical_url = ''
    if site_url:
        canonical_url = site_url + request.path
    elif request:
        canonical_url = request.build_absolute_uri(request.path)

    site_settings = SiteSettings.load()
    site_name = settings.SITE_NAME
    default_title = settings.SITE_DEFAULT_TITLE
    if '{site_name}' in default_title:
        default_title = default_title.format(site_name=site_name)
    default_description = settings.SEO_DEFAULT_DESCRIPTION

    og_image = _absolute_url(_static_url('web-app-manifest-512x512.png'), request, site_url)
    logo_url = og_image
    if site_settings.favicon:
        logo_url = _absolute_url(site_settings.favicon.url, request, site_url)

    contact_email = site_settings.contact_email or settings.SITE_CONTACT_EMAIL
    contact_phone = site_settings.contact_phone or ''

    seo_global_schemas = [
        organization_schema(
            site_name=site_name,
            url=site_url,
            email=contact_email,
            phone=contact_phone,
            logo_url=logo_url,
        ),
        website_schema(site_name=site_name, url=site_url),
    ]

    return {
        'SITE_URL': site_url,
        'SITE_NAME': site_name,
        'LOGO_MARK': 'Тортуга',
        'LOGO_TEXT': 'Дев',
        'SITE_DEFAULT_TITLE': default_title,
        'SEO_DEFAULT_DESCRIPTION': default_description,
        'SEO_OG_IMAGE': og_image,
        'SITE_CONTACT_EMAIL': contact_email,
        'YANDEX_METRICA_ID': settings.YANDEX_METRICA_ID,
        'GOOGLE_ANALYTICS_ID': settings.GOOGLE_ANALYTICS_ID,
        'canonical_url': canonical_url,
        'INDEXNOW_KEY': settings.INDEXNOW_KEY,
        'settings': site_settings,
        'has_team_members': TeamMember.objects.filter(is_published=True).exists(),
        'seo_global_schemas': seo_global_schemas,
    }
