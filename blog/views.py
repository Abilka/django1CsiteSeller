from django.core.paginator import Paginator
from django.http import Http404
from django.shortcuts import get_object_or_404, render

from .models import BlogPost

POSTS_PER_PAGE = 12


def post_list(request):
    posts = BlogPost.published.all()
    paginator = Paginator(posts, POSTS_PER_PAGE)
    page = paginator.get_page(request.GET.get('page'))
    return render(request, 'blog/list.html', {
        'page': page,
        'posts': page.object_list,
        'active_nav': 'blog',
    })


def post_detail(request, slug):
    post = get_object_or_404(BlogPost, slug=slug)
    if not post.is_visible and not request.user.is_staff:
        raise Http404
    return render(request, 'blog/detail.html', {
        'post': post,
        'active_nav': 'blog',
    })
