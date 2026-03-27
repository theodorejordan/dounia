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
        return {'error': 'URL Bandcamp invalide (doit pointer vers un album)'}

    try:
        headers = {'User-Agent': 'DouniaMusicApp/1.0'}
        response = requests.get(url, headers=headers, timeout=10)

        if response.status_code != 200:
            return {'error': 'Album introuvable sur Bandcamp'}

        soup = BeautifulSoup(response.text, 'html.parser')

        # Find the JSON-LD block typed as MusicAlbum
        ld_tag = soup.find('script', type='application/ld+json')
        if not ld_tag:
            return {'error': 'Données introuvables sur cette page Bandcamp'}

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
            return {'error': 'Données manquantes sur cette page Bandcamp'}

        return {
            'name': name,
            'artist': artist,
            'year': year,
            'cover_url': cover_url,
        }

    except json.JSONDecodeError:
        return {'error': 'Erreur lors de la lecture des données Bandcamp'}
    except requests.exceptions.Timeout:
        return {'error': 'Timeout lors de la connexion à Bandcamp'}
    except requests.exceptions.RequestException as e:
        return {'error': f'Erreur de connexion : {str(e)}'}
    except Exception as e:
        return {'error': f'Erreur inattendue : {str(e)}'}
