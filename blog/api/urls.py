from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import BlogPostImportView, BlogPostViewSet

router = DefaultRouter()
router.register('posts', BlogPostViewSet, basename='blog-post')

urlpatterns = [
    path('import/', BlogPostImportView.as_view(), name='blog-post-import'),
    *router.urls,
]
