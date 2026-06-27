from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import CalculateUpdateView, ConfigurationVersionsView, OneCConfigurationViewSet, OneCReleaseViewSet

router = DefaultRouter()
router.register('configurations', OneCConfigurationViewSet, basename='onec-configuration')
router.register('releases', OneCReleaseViewSet, basename='onec-release')

urlpatterns = [
    path('calculate/', CalculateUpdateView.as_view(), name='onec-calculate'),
    path('configurations/<slug:slug>/versions/', ConfigurationVersionsView.as_view(), name='onec-versions'),
    path('', include(router.urls)),
]
