from django.conf import settings
from django.http import HttpResponse
from django.views.decorators.http import require_GET


@require_GET
def robots_txt(request):
  lines = [
      'User-agent: *',
      'Allow: /',
      'Disallow: /admin/',
      'Disallow: /api/',
      'Disallow: /spasibo/',
  ]
  if settings.SITE_URL:
      lines.append(f'Sitemap: {settings.SITE_URL.rstrip("/")}/sitemap.xml')
  return HttpResponse('\n'.join(lines) + '\n', content_type='text/plain; charset=utf-8')


@require_GET
def indexnow_key(request, key):
    if not settings.INDEXNOW_KEY or key != settings.INDEXNOW_KEY:
        return HttpResponse(status=404)
    return HttpResponse(settings.INDEXNOW_KEY, content_type='text/plain; charset=utf-8')
