from django.urls import path

from . import views

app_name = 'landing'

urlpatterns = [
    path('', views.index, name='index'),
    path('spasibo/', views.thanks, name='thanks'),
    path('kalkulyator-obnovlenij/', views.update_calculator, name='update_calculator'),
    path('kak-uznat-reliz/', views.release_version_help, name='release_version_help'),
    path('legal/user-agreement/', views.user_agreement, name='user_agreement'),
    path('legal/privacy-policy/', views.privacy_policy, name='privacy_policy'),
]
