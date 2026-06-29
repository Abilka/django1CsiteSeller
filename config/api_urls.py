from django.urls import include, path

urlpatterns = [
    path('', include('landing.api.urls')),
    path('blog/', include('blog.api.urls')),
]
