import re

from django import template
from django.utils.safestring import mark_safe

register = template.Library()

# Thin space: visually like a thousands separator but breaks phone-number heuristics in Safari.
_THIN_SPACE = '\u2009'


@register.filter
def get_item(dictionary, key):
    if dictionary is None:
        return None
    return dictionary.get(key)


@register.filter
def format_price(value):
    """Format a price for display without mobile browsers turning it into a phone link."""
    if value is None or value == '':
        return ''

    if isinstance(value, str):
        text = re.sub(r'(?<=\d) (?=\d)', _THIN_SPACE, value)
    else:
        try:
            text = f'{int(value):,}'.replace(',', _THIN_SPACE)
        except (TypeError, ValueError):
            return value

    return mark_safe(f'<span class="price" x-apple-data-detectors="false">{text}</span>')
