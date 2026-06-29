import markdown
from django import template
from django.utils.safestring import mark_safe

register = template.Library()

MARKDOWN_EXTENSIONS = [
    'markdown.extensions.fenced_code',
    'markdown.extensions.tables',
    'markdown.extensions.nl2br',
    'markdown.extensions.sane_lists',
    'markdown.extensions.smarty',
]


@register.filter
def render_markdown(text):
    if not text:
        return ''
    html = markdown.markdown(text, extensions=MARKDOWN_EXTENSIONS)
    return mark_safe(html)
