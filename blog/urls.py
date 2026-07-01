from django.urls import path

from . import views
from .feeds import BlogPostFeed

app_name = 'blog'

urlpatterns = [
    path('rss/', BlogPostFeed(), name='rss'),
    path('', views.post_list, name='list'),
    path('<slug:slug>/', views.post_detail, name='detail'),
]
