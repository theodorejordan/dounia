import requests
import re
from urllib.parse import urlparse, parse_qs
from django.core.files.base import ContentFile
from io import BytesIO


def resolve_deezer_short_link(url):
    """
    Resolves shortened Deezer links (link.deezer.com) to their full URL.

    Shortened links like https://link.deezer.com/s/33wBRE8Bi8XZJHeAWP3gD
    redirect to an intermediate URL with the real album URL in query params:
    https://link.deezer.com/?dest=https%3A%2F%2Fwww.deezer.com%2Falbum%2F223930672...

    Returns the resolved URL, or the original URL if it's not a short link.
    """
    # Check if it's a shortened link
    if 'link.deezer.com' not in url:
        return url

    try:
        # Get the redirect location
        response = requests.head(url, allow_redirects=False, timeout=10)

        if response.status_code in (301, 302, 303, 307, 308):
            location = response.headers.get('Location')
            if location:
                # The redirect URL contains the real album URL in query params
                # Parse query params and extract 'dest' or 'awf' parameter
                parsed = urlparse(location)
                params = parse_qs(parsed.query)

                # Try 'dest' first, then 'awf' as fallback
                for param in ('dest', 'awf'):
                    if param in params:
                        return params[param][0]

                # If no query params, return the location directly
                return location

        # Fallback: follow redirects and return final URL
        response = requests.get(url, allow_redirects=True, timeout=10)
        return response.url

    except requests.exceptions.RequestException:
        # If we can't resolve it, return the original URL
        # The caller will handle the invalid URL error
        return url


def extract_deezer_album_id(url):
    """Extrait l'ID de l'album depuis une URL Deezer"""
    # Formats possibles :
    # https://www.deezer.com/album/302127
    # https://deezer.com/album/302127
    # https://www.deezer.com/fr/album/302127
    # https://link.deezer.com/s/33wBRE8Bi8XZJHeAWP3gD (shortened links)

    # First, resolve shortened links to their full URL
    url = resolve_deezer_short_link(url)

    patterns = [
        r'deezer\.com/(?:\w+/)?album/(\d+)',
        r'^(\d+)$',  # Si l'utilisateur colle juste l'ID
    ]

    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)

    return None


def fetch_album_from_deezer(album_id):
    """Récupère les infos d'un album depuis l'API Deezer"""
    try:
        # Appel à l'API Deezer
        response = requests.get(f'https://api.deezer.com/album/{album_id}', timeout=10)
        
        if response.status_code != 200:
            return {'error': 'Album not found on Deezer'}
        
        data = response.json()
        
        # Vérifier si l'album existe
        if 'error' in data:
            return {'error': 'Album not found on Deezer'}
        
        # Extraire les infos
        album_info = {
            'name': data.get('title', ''),
            'artist': data.get('artist', {}).get('name', ''),
            'year': None,
            'cover_url': data.get('cover_xl') or data.get('cover_big') or data.get('cover_medium'),
        }
        
        # Extraire l'année depuis release_date (format: YYYY-MM-DD)
        release_date = data.get('release_date', '')
        if release_date:
            try:
                album_info['year'] = int(release_date.split('-')[0])
            except (ValueError, IndexError):
                pass
        
        return album_info
    
    except requests.exceptions.Timeout:
        return {'error': 'Connection to Deezer timed out'}
    except requests.exceptions.RequestException as e:
        return {'error': f'Connection error: {str(e)}'}
    except Exception as e:
        return {'error': f'Unexpected error: {str(e)}'}


def download_cover_from_url(cover_url):
    """Télécharge une image depuis une URL et retourne un objet File Django"""
    try:
        headers = {'User-Agent': 'DouniaMusicApp/1.0'}
        # Discogs image servers require authentication
        if 'discogs.com' in cover_url:
            from django.conf import settings
            token = getattr(settings, 'DISCOGS_TOKEN', '')
            if token:
                headers['Authorization'] = f'Discogs token={token}'
        response = requests.get(cover_url, headers=headers, timeout=10)
        if response.status_code == 200:
            image_content = ContentFile(response.content)
            return image_content
        return None
    except Exception:
        return None