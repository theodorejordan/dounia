from django.views.static import serve as django_serve
from django.conf import settings
import os

def serve_media(request, path):
    """Serve media files from the volume in production"""
    return django_serve(request, path, document_root=settings.MEDIA_ROOT)