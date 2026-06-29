from rest_framework.routers import DefaultRouter

from .views import BlogPostViewSet

router = DefaultRouter()
router.register('posts', BlogPostViewSet, basename='blog-post')

urlpatterns = router.urls
