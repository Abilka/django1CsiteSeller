from django.conf import settings
from django.core.paginator import Paginator
from django.http import Http404
from django.shortcuts import get_object_or_404, render

from config.seo import blog_posting_schema, breadcrumb_schema, collection_page_schema
from .models import BlogPost

POSTS_PER_PAGE = 12


def _absolute_url(path: str, request) -> str:
    site_url = settings.SITE_URL.rstrip('/') if settings.SITE_URL else ''
    if site_url:
        return f'{site_url}{path}'
    return request.build_absolute_uri(path)


def post_list(request):
    posts = BlogPost.published.all()
    paginator = Paginator(posts, POSTS_PER_PAGE)
    page = paginator.get_page(request.GET.get('page'))

    canonical_url = _absolute_url(request.path, request)
    if page.number > 1:
        canonical_url = _absolute_url(f'{request.path}?page={page.number}', request)

    pagination_prev = ''
    pagination_next = ''
    if page.has_previous():
        prev_page = page.previous_page_number()
        prev_query = f'?page={prev_page}' if prev_page > 1 else ''
        pagination_prev = _absolute_url(f'{request.path}{prev_query}', request)
    if page.has_next():
        pagination_next = _absolute_url(f'{request.path}?page={page.next_page_number()}', request)

    page_title = f'Блог о 1С — статьи и инструкции | {settings.SITE_NAME}'
    page_description = (
        'Полезные статьи о настройке, доработке и обновлении 1С:Предприятие 8. '
        'Инструкции, советы и разбор типовых задач.'
    )

    return render(request, 'blog/list.html', {
        'page': page,
        'posts': page.object_list,
        'active_nav': 'blog',
        'canonical_url': canonical_url,
        'pagination_prev': pagination_prev,
        'pagination_next': pagination_next,
        'page_title': page_title,
        'page_description': page_description,
        'schema_items': [
            collection_page_schema(page_title, page_description, canonical_url),
        ],
    })


def post_detail(request, slug):
    post = get_object_or_404(BlogPost, slug=slug)
    if not post.is_visible and not request.user.is_staff:
        raise Http404

    canonical_url = _absolute_url(request.path, request)
    image_url = ''
    if post.cover_image:
        image_url = _absolute_url(post.cover_image.url, request)

    page_title = f'{post.seo_title} | {settings.SITE_NAME}'
    schema_items = [
        blog_posting_schema(
            headline=post.title,
            description=post.seo_description,
            date_published=post.published_at.isoformat() if post.published_at else '',
            date_modified=post.updated_at.isoformat(),
            site_name=settings.SITE_NAME,
            page_url=canonical_url,
            image_url=image_url,
        ),
        breadcrumb_schema([
            ('Главная', _absolute_url('/', request)),
            ('Блог', _absolute_url('/blog/', request)),
            (post.title, canonical_url),
        ]),
    ]

    return render(request, 'blog/detail.html', {
        'post': post,
        'active_nav': 'blog',
        'canonical_url': canonical_url,
        'page_title': page_title,
        'page_description': post.seo_description,
        'og_image': image_url or None,
        'schema_items': schema_items,
    })
