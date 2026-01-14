from django.urls import path
from . import views

urlpatterns = [
    path('', views.collection_view, name='collection'),
    path('add/', views.add_album_view, name='add_album'),
    path('delete/<int:album_id>/', views.delete_album_view, name='delete_album'),
    path('api/tags/', views.tags_autocomplete, name='tags_autocomplete'),
    path('api/deezer/', views.fetch_deezer_album, name='fetch_deezer_album'),  # Nouvelle route
]