from django.urls import reverse

from landing.tools.registry import get_tool, list_tools


def build_tool_context(slug: str, **extra):
    tool = get_tool(slug)
    if tool is None:
        raise ValueError(f'Unknown tool slug: {slug}')
    return {
        'tool_name': tool.name,
        'tool_description': tool.description,
        'tool_tag': tool.tag,
        'tool_page_title': f'{tool.name} — ',
        'other_tools': [item for item in list_tools() if item.slug != slug],
        'tools_index_url': reverse('landing:tools_index'),
        **extra,
    }
