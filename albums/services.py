"""
Service layer for album-related business logic.

This module contains reusable functions for operations like:
- Artist creation/retrieval
- Cover image downloading
- Tag synchronization

These functions can be used by forms, views, management commands, etc.
"""

import json
from typing import Optional
from django.core.files.base import ContentFile

from django.utils import timezone

from .models import Album, Artist, Tag, Submission
from .deezer_api import download_cover_from_url


def get_or_create_artist(name: str) -> Artist:
    """
    Get existing artist or create a new one (case-insensitive lookup).

    Args:
        name: Artist name

    Returns:
        Artist instance

    Example:
        >>> artist = get_or_create_artist("Pink Floyd")
        >>> artist.name
        'Pink Floyd'
    """
    # Case-insensitive lookup to avoid duplicates
    artist = Artist.objects.filter(name__iexact=name).first()
    if not artist:
        artist = Artist.objects.create(name=name)
    return artist


def download_and_attach_cover(album: Album, cover_url: str) -> bool:
    """
    Download cover image from URL and attach it to the album.

    Args:
        album: Album instance (must have artist set)
        cover_url: URL of the cover image

    Returns:
        True if cover was downloaded and attached, False otherwise

    Example:
        >>> album = Album(name="The Wall", artist=artist)
        >>> success = download_and_attach_cover(album, "https://example.com/cover.jpg")
    """
    if not cover_url or album.cover:
        return False

    cover_content = download_cover_from_url(cover_url)
    if not cover_content:
        return False

    # Generate filename from artist slug and album name
    filename = f"{album.artist.slug}_{album.name[:50]}.jpg"
    album.cover.save(filename, cover_content, save=False)
    return True


def sync_album_tags(album: Album, tags_json: str) -> None:
    """
    Parse tags JSON and sync them to the album.

    Clears existing tags and replaces them with the new ones.
    Creates tags if they don't exist.

    Args:
        album: Album instance (must be saved)
        tags_json: JSON string in format: [{"value": "tag_name"}, ...]

    Example:
        >>> album = Album.objects.get(id=1)
        >>> sync_album_tags(album, '[{"value": "rock"}, {"value": "classic"}]')
        >>> list(album.tags.values_list('name', flat=True))
        ['rock', 'classic']
    """
    if not tags_json:
        return

    try:
        tags_data = json.loads(tags_json)
        album.tags.clear()

        for tag_data in tags_data:
            tag_name = tag_data.get('value')
            if tag_name:
                tag, _ = Tag.objects.get_or_create(name=tag_name)
                album.tags.add(tag)
    except json.JSONDecodeError:
        # Silently ignore invalid JSON
        pass


def sync_submission_tags(submission: Submission, tags_json: str) -> None:
    """
    Parse tags JSON and sync existing tags to the submission.

    Unlike sync_album_tags, this only adds tags that already exist.
    Users cannot create new tags through submissions.

    Args:
        submission: Submission instance (must be saved)
        tags_json: JSON string in format: [{"value": "tag_name"}, ...]
    """
    if not tags_json:
        return

    try:
        tags_data = json.loads(tags_json)
        submission.tags.clear()

        for tag_data in tags_data:
            tag_name = tag_data.get('value')
            if tag_name:
                # Only add existing tags, don't create new ones
                tag = Tag.objects.filter(name=tag_name).first()
                if tag:
                    submission.tags.add(tag)
    except json.JSONDecodeError:
        pass


def download_and_attach_cover_to_submission(submission: Submission, cover_url: str) -> bool:
    """
    Download cover image from URL and attach it to the submission.

    Args:
        submission: Submission instance
        cover_url: URL of the cover image

    Returns:
        True if cover was downloaded and attached, False otherwise
    """
    if not cover_url or submission.cover:
        return False

    cover_content = download_cover_from_url(cover_url)
    if not cover_content:
        return False

    # Generate filename from artist name and album name
    safe_artist = submission.artist_name[:30].replace(' ', '_').lower()
    safe_name = submission.name[:30].replace(' ', '_').lower()
    filename = f"{safe_artist}_{safe_name}.jpg"
    submission.cover.save(filename, cover_content, save=False)
    return True


def create_album_from_submission(submission: Submission, reviewed_by) -> Album:
    """
    Convert an approved submission into an Album.

    Creates the Artist if needed, creates the Album, copies tags,
    and updates the submission status.

    Args:
        submission: Submission instance to approve
        reviewed_by: User who approved it

    Returns:
        The created Album instance
    """
    # Get or create artist using existing service
    artist = get_or_create_artist(submission.artist_name)

    # Create album
    album = Album.objects.create(
        name=submission.name,
        artist=artist,
        cover=submission.cover,
        year=submission.year,
        notes=submission.notes,
        submitted_by=submission.submitted_by,
        source_url=submission.source_url,
        source_type=submission.source_type,
    )

    # Copy tags
    album.tags.set(submission.tags.all())

    # Update submission status
    submission.status = 'approved'
    submission.reviewed_at = timezone.now()
    submission.reviewed_by = reviewed_by
    submission.save()

    return album
