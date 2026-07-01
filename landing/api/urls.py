from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .tools_views import (
    MigrationCalcToolView,
    PlatformCheckToolView,
    QueryFormatterToolView,
    ReleaseFeedToolView,
    TaskEstimatorToolView,
)
from .lead_views import LeadPollView
from .views import CalculateUpdateView, ConfigurationVersionsView, OneCConfigurationViewSet, OneCReleaseViewSet

router = DefaultRouter()
router.register('configurations', OneCConfigurationViewSet, basename='onec-configuration')
router.register('releases', OneCReleaseViewSet, basename='onec-release')

urlpatterns = [
    path('leads/poll/', LeadPollView.as_view(), name='lead-poll'),
    path('calculate/', CalculateUpdateView.as_view(), name='onec-calculate'),
    path('configurations/<slug:slug>/versions/', ConfigurationVersionsView.as_view(), name='onec-versions'),
    path('tools/platform-check/', PlatformCheckToolView.as_view(), name='tool-platform-check'),
    path('tools/task-estimator/', TaskEstimatorToolView.as_view(), name='tool-task-estimator'),
    path('tools/query-formatter/', QueryFormatterToolView.as_view(), name='tool-query-formatter'),
    path('tools/migration-calc/', MigrationCalcToolView.as_view(), name='tool-migration-calc'),
    path('tools/release-feed/', ReleaseFeedToolView.as_view(), name='tool-release-feed'),
    path('', include(router.urls)),
]
