"""
Tests for albums app - models, services, and forms.
"""

from django.test import TestCase
from django.core.files.uploadedfile import SimpleUploadedFile
from unittest.mock import patch, MagicMock

from .models import Album, Artist, Tag
from .services import get_or_create_artist, download_and_attach_cover, sync_album_tags
from .forms import AlbumForm


class ArtistServiceTests(TestCase):
    """Tests for get_or_create_artist service function"""

    def test_create_new_artist(self):
        """Should create a new artist if it doesn't exist"""
        artist = get_or_create_artist("Pink Floyd")

        self.assertEqual(artist.name, "Pink Floyd")
        self.assertEqual(Artist.objects.count(), 1)

    def test_get_existing_artist(self):
        """Should return existing artist instead of creating duplicate"""
        # Create artist
        existing = Artist.objects.create(name="The Beatles")

        # Try to get/create with same name
        artist = get_or_create_artist("The Beatles")

        self.assertEqual(artist.id, existing.id)
        self.assertEqual(Artist.objects.count(), 1)

    def test_case_insensitive_lookup(self):
        """Should find artist regardless of case"""
        existing = Artist.objects.create(name="Pink Floyd")

        # Try different cases
        artist1 = get_or_create_artist("pink floyd")
        artist2 = get_or_create_artist("PINK FLOYD")
        artist3 = get_or_create_artist("PiNk FlOyD")

        self.assertEqual(artist1.id, existing.id)
        self.assertEqual(artist2.id, existing.id)
        self.assertEqual(artist3.id, existing.id)
        self.assertEqual(Artist.objects.count(), 1)


class CoverDownloadServiceTests(TestCase):
    """Tests for download_and_attach_cover service function"""

    def setUp(self):
        self.artist = Artist.objects.create(name="Test Artist")

    @patch('albums.services.download_cover_from_url')
    def test_download_and_attach_cover(self, mock_download):
        """Should download cover and attach to album"""
        # Mock the download function to return fake image content (ContentFile)
        from django.core.files.base import ContentFile
        fake_image = ContentFile(b'fake image data', name='test.jpg')
        mock_download.return_value = fake_image

        album = Album(name="Test Album", artist=self.artist)
        result = download_and_attach_cover(album, "https://example.com/cover.jpg")

        self.assertTrue(result)
        mock_download.assert_called_once_with("https://example.com/cover.jpg")
        # Check that cover was attached (exact filename may vary)
        self.assertTrue(album.cover)

    @patch('albums.services.download_cover_from_url')
    def test_skip_if_cover_already_exists(self, mock_download):
        """Should not download if album already has a cover"""
        album = Album(
            name="Test Album",
            artist=self.artist,
            cover="existing_cover.jpg"
        )

        result = download_and_attach_cover(album, "https://example.com/cover.jpg")

        self.assertFalse(result)
        mock_download.assert_not_called()

    @patch('albums.services.download_cover_from_url')
    def test_handle_download_failure(self, mock_download):
        """Should return False if download fails"""
        mock_download.return_value = None  # Simulate download failure

        album = Album(name="Test Album", artist=self.artist)
        result = download_and_attach_cover(album, "https://example.com/cover.jpg")

        self.assertFalse(result)
        self.assertFalse(album.cover)


class TagSyncServiceTests(TestCase):
    """Tests for sync_album_tags service function"""

    def setUp(self):
        self.artist = Artist.objects.create(name="Test Artist")
        # Create a proper minimal 1x1 PNG image (valid PNG format)
        png_data = (
            b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01'
            b'\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\nIDATx\x9cc\x00\x01'
            b'\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82'
        )
        self.image = SimpleUploadedFile(
            name='test.png',
            content=png_data,
            content_type='image/png'
        )
        self.album = Album.objects.create(
            name="Test Album",
            artist=self.artist,
            cover=self.image
        )

    def test_sync_tags_from_json(self):
        """Should parse JSON and create/attach tags"""
        tags_json = '[{"value": "rock"}, {"value": "classic"}]'
        sync_album_tags(self.album, tags_json)

        tag_names = list(self.album.tags.values_list('name', flat=True))
        self.assertEqual(len(tag_names), 2)
        self.assertIn("rock", tag_names)
        self.assertIn("classic", tag_names)

    def test_clear_existing_tags(self):
        """Should clear existing tags before adding new ones"""
        # Add initial tags
        tag1 = Tag.objects.create(name="old_tag")
        self.album.tags.add(tag1)

        # Sync new tags
        tags_json = '[{"value": "new_tag"}]'
        sync_album_tags(self.album, tags_json)

        tag_names = list(self.album.tags.values_list('name', flat=True))
        self.assertEqual(tag_names, ["new_tag"])

    def test_create_tags_if_not_exist(self):
        """Should create tags that don't exist yet"""
        initial_count = Tag.objects.count()

        tags_json = '[{"value": "new_tag_1"}, {"value": "new_tag_2"}]'
        sync_album_tags(self.album, tags_json)

        self.assertEqual(Tag.objects.count(), initial_count + 2)

    def test_reuse_existing_tags(self):
        """Should reuse existing tags instead of creating duplicates"""
        # Create existing tag
        existing_tag = Tag.objects.create(name="existing")

        tags_json = '[{"value": "existing"}, {"value": "new"}]'
        sync_album_tags(self.album, tags_json)

        # Should have only 2 tags total (existing + new)
        self.assertEqual(Tag.objects.count(), 2)
        # Album should have both tags
        self.assertEqual(self.album.tags.count(), 2)

    def test_handle_invalid_json(self):
        """Should handle invalid JSON gracefully"""
        tags_json = 'not valid json'
        sync_album_tags(self.album, tags_json)

        # Should not raise exception, tags should remain empty
        self.assertEqual(self.album.tags.count(), 0)

    def test_handle_empty_string(self):
        """Should handle empty string gracefully"""
        sync_album_tags(self.album, '')
        self.assertEqual(self.album.tags.count(), 0)


class AlbumFormTests(TestCase):
    """Integration tests for AlbumForm using the service layer"""

    def setUp(self):
        # Create a proper minimal 1x1 PNG image (valid PNG format)
        png_data = (
            b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01'
            b'\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\nIDATx\x9cc\x00\x01'
            b'\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82'
        )
        self.image = SimpleUploadedFile(
            name='test.png',
            content=png_data,
            content_type='image/png'
        )

    def test_form_creates_artist_and_album(self):
        """Should create both artist and album"""
        form_data = {
            'name': 'The Wall',
            'artist_name': 'Pink Floyd',
            'year': 1979,
            'notes': 'Classic album'
        }
        form = AlbumForm(data=form_data, files={'cover': self.image})

        self.assertTrue(form.is_valid())
        album = form.save()

        # Check album was created
        self.assertEqual(album.name, 'The Wall')
        self.assertEqual(album.year, 1979)

        # Check artist was created
        self.assertEqual(Artist.objects.count(), 1)
        self.assertEqual(album.artist.name, 'Pink Floyd')

    def test_form_reuses_existing_artist(self):
        """Should reuse existing artist instead of creating duplicate"""
        # Create existing artist
        existing = Artist.objects.create(name="The Beatles")

        form_data = {
            'name': 'Abbey Road',
            'artist_name': 'The Beatles'  # Same name
        }
        form = AlbumForm(data=form_data, files={'cover': self.image})

        self.assertTrue(form.is_valid())
        album = form.save()

        # Should still have only 1 artist
        self.assertEqual(Artist.objects.count(), 1)
        self.assertEqual(album.artist.id, existing.id)

    @patch('albums.services.download_cover_from_url')
    def test_form_downloads_cover_from_url(self, mock_download):
        """Should download cover if cover_url is provided"""
        from django.core.files.base import ContentFile
        fake_image = ContentFile(b'fake image data', name='test.jpg')
        mock_download.return_value = fake_image

        form_data = {
            'name': 'Test Album',
            'artist_name': 'Test Artist',
            'cover_url': 'https://example.com/cover.jpg'
        }
        form = AlbumForm(data=form_data)

        self.assertTrue(form.is_valid())
        album = form.save()

        mock_download.assert_called_once()
        self.assertTrue(album.cover)

    def test_form_syncs_tags(self):
        """Should sync tags from JSON input"""
        form_data = {
            'name': 'Test Album',
            'artist_name': 'Test Artist',
            'tags_input': '[{"value": "rock"}, {"value": "progressive"}]'
        }
        form = AlbumForm(data=form_data, files={'cover': self.image})

        self.assertTrue(form.is_valid())
        album = form.save()

        tag_names = list(album.tags.values_list('name', flat=True))
        self.assertEqual(len(tag_names), 2)
        self.assertIn("rock", tag_names)
        self.assertIn("progressive", tag_names)

    def test_form_validation_requires_artist(self):
        """Should fail validation if artist_name is missing"""
        form_data = {
            'name': 'Test Album',
            # Missing artist_name
        }
        form = AlbumForm(data=form_data, files={'cover': self.image})

        self.assertFalse(form.is_valid())
        self.assertIn('Artist name is required', str(form.errors))

    def test_form_validation_requires_cover(self):
        """Should fail validation if neither cover nor cover_url provided"""
        form_data = {
            'name': 'Test Album',
            'artist_name': 'Test Artist',
            # No cover or cover_url
        }
        form = AlbumForm(data=form_data)

        self.assertFalse(form.is_valid())
        self.assertIn('cover is required', str(form.errors))
