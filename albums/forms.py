from django import forms
from .models import Album, Artist, Tag
from .deezer_api import download_cover_from_url
from django.core.files.base import ContentFile


class AlbumForm(forms.ModelForm):
    # Champ pour le mode Deezer
    deezer_url = forms.CharField(
        required=False,
        label="Lien Deezer",
        widget=forms.TextInput(attrs={
            'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent',
            'placeholder': 'https://www.deezer.com/album/302127'
        })
    )
    
    # URL de la cover pour le mode Deezer
    cover_url = forms.CharField(
        required=False,
        widget=forms.HiddenInput()
    )
    
    artist_name = forms.CharField(
        max_length=200,
        required=False,
        label="Artiste",
        widget=forms.TextInput(attrs={
            'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent',
            'placeholder': 'Nom de l\'artiste'
        })
    )
    
    tags_input = forms.CharField(
        required=False,
        label="Tags",
        widget=forms.TextInput(attrs={
            'id': 'tags-input',
            'placeholder': 'Ajouter des tags...'
        })
    )
    
    class Meta:
        model = Album
        fields = ['name', 'cover', 'year', 'notes']
        labels = {
            'name': 'Nom de l\'album',
            'cover': 'Couverture',
            'year': 'Année',
            'notes': 'Notes'
        }
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent',
                'placeholder': 'Nom de l\'album'
            }),
            'cover': forms.FileInput(attrs={
                'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg',
                'accept': 'image/*'
            }),
            'year': forms.NumberInput(attrs={
                'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent',
                'placeholder': '2024',
                'min': 1900,
                'max': 2100
            }),
            'notes': forms.Textarea(attrs={
                'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent',
                'placeholder': 'Notes sur cet album...',
                'rows': 4
            })
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Rendre le champ cover non-obligatoire
        self.fields['cover'].required = False
    
    def clean(self):
        cleaned_data = super().clean()
        cover = cleaned_data.get('cover')
        cover_url = cleaned_data.get('cover_url')
        artist_name = cleaned_data.get('artist_name')
        name = cleaned_data.get('name')
        
        # Vérifier qu'on a au moins un artiste et un nom
        if not artist_name:
            raise forms.ValidationError("Le nom de l'artiste est requis")
        if not name:
            raise forms.ValidationError("Le nom de l'album est requis")
        
        # Vérifier qu'on a au moins une cover (fichier OU url)
        if not cover and not cover_url:
            raise forms.ValidationError("Une couverture est requise (fichier ou depuis Deezer)")
        
        return cleaned_data
    
    def save(self, commit=True):
        # Gérer l'artiste (créer ou récupérer)
        artist_name = self.cleaned_data.get('artist_name')
        artist, _ = Artist.objects.get_or_create(name=artist_name)
        
        album = super().save(commit=False)
        album.artist = artist
        
        # Si on a une URL de cover (mode Deezer), télécharger l'image
        cover_url = self.cleaned_data.get('cover_url')
        if cover_url and not album.cover:
            cover_content = download_cover_from_url(cover_url)
            if cover_content:
                # Extraire le nom de fichier depuis l'URL ou utiliser un nom par défaut
                filename = f"{artist.slug}_{album.name[:50]}.jpg"
                album.cover.save(filename, cover_content, save=False)
        
        if commit:
            album.save()
            
            # Gérer les tags
            tags_input = self.cleaned_data.get('tags_input', '')
            if tags_input:
                import json
                try:
                    tags_data = json.loads(tags_input)
                    album.tags.clear()
                    for tag_data in tags_data:
                        tag_name = tag_data.get('value')
                        if tag_name:
                            tag, _ = Tag.objects.get_or_create(name=tag_name)
                            album.tags.add(tag)
                except json.JSONDecodeError:
                    pass
        
        return album