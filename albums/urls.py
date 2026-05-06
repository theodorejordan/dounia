from django.urls import path
from . import views

urlpatterns = [
    path('', views.collection_view, name='collection'),
    path('add/', views.add_album_view, name='add_album'),
    path('delete/<int:album_id>/', views.delete_album_view, name='delete_album'),
    path('api/tags/', views.tags_autocomplete, name='tags_autocomplete'),
    path('api/artists/', views.artists_autocomplete, name='artists_autocomplete'),
    path('api/deezer/', views.fetch_deezer_album, name='fetch_deezer_album'),
    path('api/discogs/', views.fetch_discogs_release, name='fetch_discogs_release'),
    path('api/bandcamp/', views.fetch_bandcamp_album, name='fetch_bandcamp_album'),
    path('api/import/', views.fetch_album_from_link, name='fetch_album_from_link'),
    path('api/albums/', views.albums_paginated_api, name='albums_api'),
    path('api/check-duplicate/', views.check_duplicate_album, name='check_duplicate_album'),
    path('partials/album-grid/', views.album_grid_partial, name='album_grid_partial'),
    path('register/', views.register_view, name='register'),
    path('profile/', views.profile_view, name='profile'),
    path('profile/<str:username>/', views.public_profile_view, name='public_profile'),
    path('delete-account/', views.delete_account_view, name='delete_account'),
]