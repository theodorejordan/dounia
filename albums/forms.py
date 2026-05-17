from django import forms
from django.contrib.auth.forms import UserCreationForm, PasswordChangeForm  # noqa: F401 (re-exported)
from django.contrib.auth.models import User
from .models import Album, Artist, Tag, UserProfile, Submission
from .services import (
    get_or_create_artist,
    download_and_attach_cover,
    sync_album_tags,
    sync_submission_tags,
    download_and_attach_cover_to_submission,
)


class RegisterForm(UserCreationForm):
    email = forms.EmailField(required=True, label="Email")

    class Meta:
        model = User
        fields = ['username', 'email', 'password1', 'password2']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['username'].label = "Username (pseudo)"
        self.fields['password1'].label = "Password"
        self.fields['password2'].label = "Confirm password"


class ProfileForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['username', 'email']
        labels = {'username': 'Username (pseudo)', 'email': 'Email'}


class AvatarForm(forms.ModelForm):
    class Meta:
        model = UserProfile
        fields = ['avatar']
        labels = {'avatar': 'Avatar'}
        widgets = {'avatar': forms.FileInput(attrs={'accept': 'image/*'})}


class AlbumForm(forms.ModelForm):
    # Champ pour le mode Deezer
    deezer_url = forms.CharField(
        required=False,
        label="Deezer link",
        widget=forms.TextInput(attrs={
            'class': 'w-full px-4 py-2 border border-gray-300 rounded outline-none',
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
        label="Artist",
        widget=forms.TextInput(attrs={
            'class': 'w-full px-4 py-2 border border-gray-300 rounded outline-none',
            'placeholder': 'Artist name'
        })
    )
    
    tags_input = forms.CharField(
        required=False,
        label="Tags",
        widget=forms.TextInput(attrs={
            'id': 'tags-input',
            'placeholder': 'Add tags...'
        })
    )
    
    class Meta:
        model = Album
        fields = ['name', 'cover', 'year', 'notes']
        labels = {
            'name': 'Album name',
            'cover': 'Cover',
            'year': 'Year',
            'notes': 'Notes'
        }
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'w-full px-4 py-2 border border-gray-300 rounded outline-none',
                'placeholder': 'Album name'
            }),
            'cover': forms.FileInput(attrs={
                'class': 'w-full px-4 py-2 border border-gray-300 rounded',
                'accept': 'image/*'
            }),
            'year': forms.NumberInput(attrs={
                'class': 'w-full px-4 py-2 border border-gray-300 rounded outline-none',
                'placeholder': '2024',
                'min': 1900,
                'max': 2100
            }),
            'notes': forms.Textarea(attrs={
                'class': 'w-full px-4 py-2 border border-gray-300 rounded outline-none',
                'placeholder': 'Notes about this album...',
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
            raise forms.ValidationError("Artist name is required")
        if not name:
            raise forms.ValidationError("Album name is required")

        if not cover and not cover_url:
            raise forms.ValidationError("A cover is required (file or imported link)")
        
        return cleaned_data
    
    def save(self, commit=True):
        # Get or create artist using service layer
        artist_name = self.cleaned_data.get('artist_name')
        artist = get_or_create_artist(artist_name)

        # Create album instance (not saved yet)
        album = super().save(commit=False)
        album.artist = artist

        # Download cover from URL if provided (using service layer)
        cover_url = self.cleaned_data.get('cover_url')
        if cover_url:
            download_and_attach_cover(album, cover_url)

        if commit:
            album.save()

            # Sync tags using service layer
            tags_input = self.cleaned_data.get('tags_input', '')
            sync_album_tags(album, tags_input)

        return album


class SubmissionForm(forms.ModelForm):
    """Form for user album submissions. Tags are select-only (no creation)."""

    # URL import field (Deezer, Discogs, Bandcamp)
    deezer_url = forms.CharField(
        required=False,
        label="Import link",
        widget=forms.TextInput(attrs={
            'class': 'w-full px-4 py-2 border border-gray-300 rounded outline-none',
            'placeholder': 'https://www.deezer.com/album/302127'
        })
    )

    # URL of the cover for import mode
    cover_url = forms.CharField(
        required=False,
        widget=forms.HiddenInput()
    )

    artist_name = forms.CharField(
        max_length=200,
        required=False,
        label="Artist",
        widget=forms.TextInput(attrs={
            'class': 'w-full px-4 py-2 border border-gray-300 rounded outline-none',
            'placeholder': 'Artist name'
        })
    )

    tags_input = forms.CharField(
        required=False,
        label="Tags",
        widget=forms.TextInput(attrs={
            'id': 'tags-input',
            'placeholder': 'Select tags...'
        })
    )

    class Meta:
        model = Submission
        fields = ['name', 'cover', 'year', 'notes']
        labels = {
            'name': 'Album name',
            'cover': 'Cover',
            'year': 'Year',
            'notes': 'Notes'
        }
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'w-full px-4 py-2 border border-gray-300 rounded outline-none',
                'placeholder': 'Album name'
            }),
            'cover': forms.FileInput(attrs={
                'class': 'w-full px-4 py-2 border border-gray-300 rounded',
                'accept': 'image/*'
            }),
            'year': forms.NumberInput(attrs={
                'class': 'w-full px-4 py-2 border border-gray-300 rounded outline-none',
                'placeholder': '2024',
                'min': 1900,
                'max': 2100
            }),
            'notes': forms.Textarea(attrs={
                'class': 'w-full px-4 py-2 border border-gray-300 rounded outline-none',
                'placeholder': 'Notes about this album...',
                'rows': 4
            })
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['cover'].required = False

    def clean(self):
        cleaned_data = super().clean()
        cover = cleaned_data.get('cover')
        cover_url = cleaned_data.get('cover_url')
        artist_name = cleaned_data.get('artist_name')
        name = cleaned_data.get('name')

        if not artist_name:
            raise forms.ValidationError("Artist name is required")
        if not name:
            raise forms.ValidationError("Album name is required")
        if not cover and not cover_url:
            raise forms.ValidationError("A cover is required (file or imported link)")

        return cleaned_data

    def save(self, user, commit=True):
        """Save submission with the submitting user."""
        submission = super().save(commit=False)
        submission.artist_name = self.cleaned_data.get('artist_name')
        submission.submitted_by = user

        # Download cover from URL if provided
        cover_url = self.cleaned_data.get('cover_url')
        if cover_url:
            download_and_attach_cover_to_submission(submission, cover_url)

        if commit:
            submission.save()

            # Sync tags (existing only, no creation)
            tags_input = self.cleaned_data.get('tags_input', '')
            sync_submission_tags(submission, tags_input)

        return submission