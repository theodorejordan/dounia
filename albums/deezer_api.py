import requests
import re
from django.core.files.base import ContentFile
from io import BytesIO


def extract_deezer_album_id(url):
    """Extrait l'ID de l'album depuis une URL Deezer"""
    # Formats possibles :
    # https://www.deezer.com/album/302127
    # https://deezer.com/album/302127
    # https://www.deezer.com/fr/album/302127
    
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
            return {'error': 'Album introuvable sur Deezer'}
        
        data = response.json()
        
        # Vérifier si l'album existe
        if 'error' in data:
            return {'error': 'Album introuvable sur Deezer'}
        
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
        return {'error': 'Timeout lors de la connexion à Deezer'}
    except requests.exceptions.RequestException as e:
        return {'error': f'Erreur de connexion : {str(e)}'}
    except Exception as e:
        return {'error': f'Erreur inattendue : {str(e)}'}


def download_cover_from_url(cover_url):
    """Télécharge une image depuis une URL et retourne un objet File Django"""
    try:
        response = requests.get(cover_url, timeout=10)
        if response.status_code == 200:
            # Créer un fichier Django depuis les bytes
            image_content = ContentFile(response.content)
            return image_content
        return None
    except Exception:
        return None