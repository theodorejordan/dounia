import re
import requests
from django.conf import settings


def clean_artist_name(name):
    """Remove Discogs disambiguation suffix: 'The Beatles (2)' → 'The Beatles'"""
    return re.sub(r'\s*\(\d+\)\s*$', '', name).strip()


def extract_discogs_release_id(url):
    """Extract release ID from a Discogs URL or bare ID.

    Handles:
      https://www.discogs.com/release/1234567
      https://www.discogs.com/release/1234567-Album-Name
      https://www.discogs.com/fr/release/1234567
      1234567  (bare ID)
    """
    patterns = [
        r'discogs\.com/(?:\w+/)?release/(\d+)',
        r'^(\d+)$',
    ]
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    return None


def fetch_release_from_discogs(release_id):
    """Fetch full release details from Discogs by release ID"""
    token = getattr(settings, 'DISCOGS_TOKEN', '')
    headers = {'User-Agent': 'DouniaMusicApp/1.0'}
    params = {}
    if token:
        params['token'] = token

    try:
        response = requests.get(
            f'https://api.discogs.com/releases/{release_id}',
            params=params,
            headers=headers,
            timeout=10,
        )
        if response.status_code != 200:
            return {'error': 'Release introuvable sur Discogs'}

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
        return {'error': 'Timeout lors de la connexion à Discogs'}
    except requests.exceptions.RequestException as e:
        return {'error': f'Erreur de connexion : {str(e)}'}
    except Exception as e:
        return {'error': f'Erreur inattendue : {str(e)}'}

