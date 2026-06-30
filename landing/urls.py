from django.urls import path

from . import views
from .feeds import ReleaseFeed

app_name = 'landing'

urlpatterns = [
    path('', views.index, name='index'),
    path('spasibo/', views.thanks, name='thanks'),
    path('kalkulyator-obnovlenij/', views.update_calculator, name='update_calculator'),
    path('kak-uznat-reliz/', views.release_version_help, name='release_version_help'),
    path('instrumenty/', views.tools_index, name='tools_index'),
    path('proverka-platformy/', views.platform_check, name='platform_check'),
    path('novye-relizy/', views.release_feed, name='release_feed'),
    path('novye-relizy/rss/', ReleaseFeed(), name='release_feed_rss'),
    path('otsenka-zadach/', views.task_estimator, name='task_estimator'),
    path('format-zaprosov/', views.query_formatter, name='query_formatter'),
    path('kalkulyator-migracii/', views.migration_calculator, name='migration_calculator'),
    path('legal/user-agreement/', views.user_agreement, name='user_agreement'),
    path('legal/privacy-policy/', views.privacy_policy, name='privacy_policy'),
]
