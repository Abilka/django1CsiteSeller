import json

from django import template
from django.utils.safestring import mark_safe

from config.seo import (
    breadcrumb_schema,
    collection_page_schema,
    professional_service_schema,
    software_application_schema,
    webpage_schema,
)

register = template.Library()


@register.filter
def json_ld(value):
    if not value:
        return ''
    return mark_safe(json.dumps(value, ensure_ascii=False))


@register.simple_tag(takes_context=True)
def webpage_schema_tag(context, name, description):
    return webpage_schema(name, description, context.get('canonical_url', ''))


@register.simple_tag(takes_context=True)
def collection_page_schema_tag(context, name, description):
    return collection_page_schema(name, description, context.get('canonical_url', ''))


@register.simple_tag(takes_context=True)
def software_application_schema_tag(context, name, description):
    return software_application_schema(name, description, context.get('canonical_url', ''))


@register.simple_tag(takes_context=True)
def professional_service_schema_tag(context, description, price_range=''):
    site_settings = context.get('settings')
    return professional_service_schema(
        site_name=context['SITE_NAME'],
        description=description,
        url=context.get('SITE_URL', ''),
        email=context.get('SITE_CONTACT_EMAIL', ''),
        phone=getattr(site_settings, 'contact_phone', '') if site_settings else '',
        price_range=price_range,
    )


@register.simple_tag(takes_context=True)
def breadcrumb_schema_tag(context, *items):
    pairs = []
    for index in range(0, len(items), 2):
        name = items[index]
        url = items[index + 1] if index + 1 < len(items) else context.get('canonical_url', '')
        pairs.append((name, url))
    return breadcrumb_schema(pairs)
