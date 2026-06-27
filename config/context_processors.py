from django.conf import settings

from landing.models import SiteSettings, TeamMember


def site(request):
    site_url = settings.SITE_URL.rstrip('/') if settings.SITE_URL else ''
    canonical_url = ''
    if site_url:
        canonical_url = site_url + request.path
    elif request:
        canonical_url = request.build_absolute_uri(request.path)

    site_settings = SiteSettings.load()

    return {
        'SITE_URL': site_url,
        'SITE_NAME': 'Тортуга Дев',
        'LOGO_MARK': 'Тортуга',
        'LOGO_TEXT': 'Дев',
        'SITE_CONTACT_EMAIL': site_settings.contact_email or settings.SITE_CONTACT_EMAIL,
        'YANDEX_METRICA_ID': settings.YANDEX_METRICA_ID,
        'GOOGLE_ANALYTICS_ID': settings.GOOGLE_ANALYTICS_ID,
        'canonical_url': canonical_url,
        'INDEXNOW_KEY': settings.INDEXNOW_KEY,
        'settings': site_settings,
        'has_team_members': TeamMember.objects.filter(is_published=True).exists(),
    }
