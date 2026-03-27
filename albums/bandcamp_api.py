import json
import re
import requests
from datetime import datetime
from bs4 import BeautifulSoup


def is_bandcamp_album_url(url):
    """Check the URL points to a Bandcamp album page"""
    return bool(re.search(r'bandcamp\.com/album/', url))


def fetch_album_from_bandcamp(url):
    """Fetch album metadata from a Bandcamp album page via JSON-LD"""
    if not is_bandcamp_album_url(url):
        return {'error': 'Invalid Bandcamp URL (must point to an album)'}

    try:
        headers = {'User-Agent': 'DouniaMusicApp/1.0'}
        response = requests.get(url, headers=headers, timeout=10)

        if response.status_code != 200:
            return {'error': 'Album not found on Bandcamp'}

        soup = BeautifulSoup(response.text, 'html.parser')

        # Find the JSON-LD block typed as MusicAlbum
        ld_tag = soup.find('script', type='application/ld+json')
        if not ld_tag:
            return {'error': 'No data found on this Bandcamp page'}

        data = json.loads(ld_tag.string)

        name = data.get('name', '')
        artist = data.get('byArtist', {}).get('name', '')
        cover_url = data.get('image', '')

        # datePublished format: "05 Dec 2025 00:00:00 GMT"
        year = None
        date_str = data.get('datePublished', '')
        if date_str:
            try:
                year = datetime.strptime(date_str, '%d %b %Y %H:%M:%S %Z').year
            except ValueError:
                # Fallback: just grab the 4-digit year
                match = re.search(r'\b(\d{4})\b', date_str)
                if match:
                    year = int(match.group(1))

        if not name or not artist:
            return {'error': 'Missing data on this Bandcamp page'}

        return {
            'name': name,
            'artist': artist,
            'year': year,
            'cover_url': cover_url,
        }

    except json.JSONDecodeError:
        return {'error': 'Error reading Bandcamp data'}
    except requests.exceptions.Timeout:
        return {'error': 'Connection to Bandcamp timed out'}
    except requests.exceptions.RequestException as e:
        return {'error': f'Connection error: {str(e)}'}
    except Exception as e:
        return {'error': f'Unexpected error: {str(e)}'}
