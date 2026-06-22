import re
import requests
from bs4 import BeautifulSoup


def is_rateyourmusic_url(url):
    return bool(re.search(r'rateyourmusic\.com/release/', url))


def _unslugify(slug):
    """Convert a RYM URL slug to a human-readable name."""
    # Remove disambiguation suffix (e.g. "ok-computer_1997" → "ok-computer")
    slug = re.sub(r'_[^_-]*$', '', slug)
    slug = slug.replace('-', ' ').replace('_', ' ')
    return ' '.join(w.capitalize() for w in slug.split())


def _extract_from_url(url):
    """Extract artist and title from the URL slug as a fallback."""
    match = re.search(r'rateyourmusic\.com/release/[^/]+/([^/?#]+)/([^/?#]+)', url)
    if not match:
        return None, None
    return _unslugify(match.group(1)), _unslugify(match.group(2))


def _fetch_from_itunes(artist, name):
    """
    Search the iTunes API for a matching album and return (cover_url, year).
    Free, no auth required. Returns ('', None) if nothing found.
    """
    try:
        query = f'{artist} {name}'
        resp = requests.get(
            'https://itunes.apple.com/search',
            params={'term': query, 'entity': 'album', 'limit': 5, 'media': 'music'},
            timeout=8,
        )
        if resp.status_code != 200:
            return '', None
        results = resp.json().get('results', [])
        if not results:
            return '', None
        # Prefer exact artist match if available
        lower_artist = artist.lower()
        match = next((r for r in results if r.get('artistName', '').lower() == lower_artist), results[0])
        artwork = match.get('artworkUrl100', '')
        cover_url = artwork.replace('100x100bb', '600x600bb') if artwork else ''
        year = None
        date_str = match.get('releaseDate', '')
        if date_str:
            m = re.search(r'\b(19|20)\d{2}\b', date_str)
            if m:
                year = int(m.group(0))
        return cover_url, year
    except Exception:
        return '', None


def fetch_album_from_rateyourmusic(url):
    """
    Fetch album metadata from a RateYourMusic release URL.

    RYM is behind Cloudflare and blocks automated requests, so we extract
    artist/title from the URL slug and then look up cover art via the iTunes
    Search API (free, no auth required).
    """
    if not is_rateyourmusic_url(url):
        return {'error': 'Invalid RateYourMusic URL (must point to a release page)'}

    artist, name = _extract_from_url(url)
    if not artist or not name:
        return {'error': 'Could not parse artist or album from this RateYourMusic URL'}

    # Attempt to scrape the page for year (and cover as a bonus, though Cloudflare
    # almost always blocks this — we fall back to iTunes for the cover regardless).
    year = None
    cover_url = ''

    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
        }
        response = requests.get(url, headers=headers, timeout=12)

        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')

            # Year
            for sel in ['.issue_year', '.year', '[itemprop="datePublished"]', '.album_release_date']:
                el = soup.select_one(sel)
                if el:
                    m = re.search(r'\b(19|20)\d{2}\b', el.get_text())
                    if m:
                        year = int(m.group(0))
                        break

            # Cover (og:image is most reliable when page loads)
            og = soup.find('meta', property='og:image')
            if og:
                src = og.get('content', '')
                if src:
                    cover_url = 'https:' + src if src.startswith('//') else src
            if not cover_url:
                for sel in ['img.coverart', '.coverart img', '#cover_art img']:
                    el = soup.select_one(sel)
                    if el:
                        src = el.get('src', '')
                        if src:
                            cover_url = 'https:' + src if src.startswith('//') else src
                            break
    except Exception:
        pass  # network error or parse error — fall through to iTunes fallback

    # Always try iTunes for missing cover or year
    if not cover_url or year is None:
        itunes_cover, itunes_year = _fetch_from_itunes(artist, name)
        cover_url = cover_url or itunes_cover
        year = year if year is not None else itunes_year

    return {'name': name, 'artist': artist, 'year': year, 'cover_url': cover_url}
