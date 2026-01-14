from django.contrib import admin
from .models import Tag, Artist, Album

@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = ['name', 'category', 'parent', 'created_at']
    list_filter = ['category']
    search_fields = ['name']
    ordering = ['category', 'name']

@admin.register(Artist)
class ArtistAdmin(admin.ModelAdmin):
    list_display = ['name', 'slug', 'created_at']
    search_fields = ['name']
    prepopulated_fields = {'slug': ('name',)}
    ordering = ['name']

@admin.register(Album)
class AlbumAdmin(admin.ModelAdmin):
    list_display = ['name', 'artist', 'year', 'created_at']
    list_filter = ['year', 'tags']
    search_fields = ['name', 'artist__name']
    filter_horizontal = ['tags']
    ordering = ['-created_at']
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        ('Informations principales', {
            'fields': ('name', 'artist', 'cover', 'year')
        }),
        ('Contenu', {
            'fields': ('notes', 'tags')
        }),
        ('Métadonnées', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )