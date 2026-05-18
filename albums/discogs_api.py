import re
import requests
from django.conf import settings


def clean_artist_name(name):
    """Remove Discogs disambiguation suffix: 'The Beatles (2)' → 'The Beatles'"""
    return re.sub(r'\s*\(\d+\)\s*$', '', name).strip()


def extract_discogs_id(url):
    """Extract ID and type from a Discogs URL or bare ID.

    Handles:
      https://www.discogs.com/release/1234567
      https://www.discogs.com/release/1234567-Album-Name
      https://www.discogs.com/fr/release/1234567
      https://www.discogs.com/master/1234567
      https://www.discogs.com/master/1234567-Album-Name
      https://www.discogs.com/fr/master/1234567
      1234567  (bare ID - assumed to be release)

    Returns:
      tuple: (id, type) where type is 'release' or 'master', or (None, None) if invalid
    """
    # Check for master URL first
    master_match = re.search(r'discogs\.com/(?:\w+/)?master/(\d+)', url)
    if master_match:
        return master_match.group(1), 'master'

    # Check for release URL
    release_match = re.search(r'discogs\.com/(?:\w+/)?release/(\d+)', url)
    if release_match:
        return release_match.group(1), 'release'

    # Bare ID (assume release for backwards compatibility)
    bare_match = re.search(r'^(\d+)$', url)
    if bare_match:
        return bare_match.group(1), 'release'

    return None, None


def extract_discogs_release_id(url):
    """Extract release ID from a Discogs URL or bare ID (legacy wrapper)."""
    discogs_id, discogs_type = extract_discogs_id(url)
    if discogs_type == 'release':
        return discogs_id
    return None


def _get_discogs_headers_and_params():
    """Return common headers and params for Discogs API calls."""
    token = getattr(settings, 'DISCOGS_TOKEN', '')
    headers = {'User-Agent': 'DouniaMusicApp/1.0'}
    params = {'token': token} if token else {}
    return headers, params


def fetch_master_main_release_id(master_id):
    """Fetch the main release ID from a Discogs master.

    Returns:
      str: The main release ID, or None if not found
      dict: Error dict if something went wrong
    """
    headers, params = _get_discogs_headers_and_params()

    try:
        response = requests.get(
            f'https://api.discogs.com/masters/{master_id}',
            params=params,
            headers=headers,
            timeout=10,
        )
        if response.status_code != 200:
            return {'error': 'Master not found on Discogs'}

        data = response.json()
        main_release_id = data.get('main_release')
        if not main_release_id:
            return {'error': 'No main release found for this master'}

        return str(main_release_id)

    except requests.exceptions.Timeout:
        return {'error': 'Connection to Discogs timed out'}
    except requests.exceptions.RequestException as e:
        return {'error': f'Connection error: {str(e)}'}
    except Exception as e:
        return {'error': f'Unexpected error: {str(e)}'}


def fetch_release_from_discogs(release_id):
    """Fetch full release details from Discogs by release ID."""
    headers, params = _get_discogs_headers_and_params()

    try:
        response = requests.get(
            f'https://api.discogs.com/releases/{release_id}',
            params=params,
            headers=headers,
            timeout=10,
        )
        if response.status_code != 200:
            return {'error': 'Release not found on Discogs'}

        data = response.json()

        # Extract and clean artist name
        artists = data.get('artists', [])
        artist_name = clean_artist_name(artists[0].get('name', '')) if artists else ''

        # Best cover image (first primary, fallback to thumb)
        images = data.get('images', [])
        cover_url = images[0].get('uri', '') if images else ''
        if not cover_url:
            cover_url = data.get('thumb', '')

        return {
            'name': data.get('title', ''),
            'artist': artist_name,
            'year': data.get('year') or None,
            'cover_url': cover_url,
        }

    except requests.exceptions.Timeout:
        return {'error': 'Connection to Discogs timed out'}
    except requests.exceptions.RequestException as e:
        return {'error': f'Connection error: {str(e)}'}
    except Exception as e:
        return {'error': f'Unexpected error: {str(e)}'}


def fetch_from_discogs(url):
    """Fetch album details from a Discogs URL (release or master).

    This is the main entry point that handles both release and master URLs.
    For master URLs, it fetches the main release automatically.
    """
    discogs_id, discogs_type = extract_discogs_id(url)

    if not discogs_id:
        return {'error': 'Invalid Discogs URL'}

    if discogs_type == 'master':
        # Fetch the main release ID from the master
        result = fetch_master_main_release_id(discogs_id)
        if isinstance(result, dict) and 'error' in result:
            return result
        release_id = result
    else:
        release_id = discogs_id

    return fetch_release_from_discogs(release_id)

