from django.contrib import admin
from django.urls import path, include, re_path
from django.conf import settings
from django.conf.urls.static import static
from .media_serve import serve_media

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('albums.urls')),
    # Explicitly serve media files in production
    re_path(r'^media/(?P<path>.*)$', serve_media),
]