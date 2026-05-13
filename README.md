# Dounia

An album collection manager built with Django. Browse, organize, and tag music albums with cover art, categorized by visual elements like colors, shapes, and styles.

## Features

### Current (v0.4.0)

- **Album Collection**: Visual grid of album covers with artist, title, and year
- **Smart Import**: Add albums via Deezer, Discogs, or Bandcamp links — metadata and cover art fetched automatically
- **Tag System**: Categorize albums by visual elements (colors, shapes, humans, landscapes, etc.) with hierarchical tags
- **HTMX Filtering**: Instant filter by artist, category, or tags — no page reloads, URL persists for bookmarking
- **User Accounts**: Register, login, profile with avatar upload and submission history
- **Album Submissions**: Registered users can submit albums for admin review
- **Changelog**: Track site updates

See [ROADMAP.md](ROADMAP.md) for the full roadmap.

## Tech Stack

- **Backend**: Django 5, SQLite
- **Frontend**: Tailwind CSS (CDN), HTMX, Tagify
- **APIs**: Deezer, Discogs, Bandcamp (scraping)

## Quick Start

```bash
# Clone and setup
git clone https://github.com/theodorejordan/dounia.git
cd dounia
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Run
python manage.py migrate
python manage.py runserver
```

Visit `http://localhost:8000`

## License

Private project.
