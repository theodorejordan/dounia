from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse, HttpResponseForbidden
from django.db.models import Q, Count
from django.core.paginator import Paginator
from django.contrib.auth import login, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib.auth.models import User
from .models import Album, Artist, Tag
from .forms import AlbumForm, RegisterForm, ProfileForm
from .deezer_api import extract_deezer_album_id, fetch_album_from_deezer
from .discogs_api import extract_discogs_release_id, fetch_release_from_discogs
from .bandcamp_api import fetch_album_from_bandcamp


def collection_view(request):
    """Vue de la collection avec filtres"""
    # Get filter parameters
    artist_search = request.GET.get('artist', '').strip()
    selected_category = request.GET.get('category', '').strip()
    selected_tags = request.GET.getlist('tags')

    # Apply filters using custom manager
    albums = Album.objects.select_related('artist').prefetch_related('tags').with_filters(
        artist_search=artist_search,
        category=selected_category,
        tags=selected_tags
    )

    # Paginate: show only first 50 albums
    total_count = albums.count()
    paginator = Paginator(albums, 50)
    page_obj = paginator.get_page(1)  # Always load page 1 on initial view

    # Récupérer tous les tags pour les filtres
    all_tags = Tag.objects.all().order_by('category', 'name')

    context = {
        'albums': page_obj,
        'all_tags': all_tags,
        'selected_tags': [int(t) for t in selected_tags if t.isdigit()],
        'albums_count': total_count,
        'has_more': page_obj.has_next(),
        'artist_search': artist_search,
        'selected_category': selected_category,
        'tag_categories': Tag.CATEGORY_CHOICES,
    }

    return render(request, 'albums/collection.html', context)


@login_required
def add_album_view(request):
    """Vue pour ajouter un album"""
    if request.method == 'POST':
        form = AlbumForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            return redirect('collection')
    else:
        form = AlbumForm()
    
    # Récupérer tous les tags pour l'autocomplétion
    all_tags = Tag.objects.all().values('id', 'name', 'category')
    
    context = {
        'form': form,
        'all_tags': list(all_tags),
    }
    
    return render(request, 'albums/add_album.html', context)


def fetch_deezer_album(request):
    """API endpoint pour récupérer les infos depuis Deezer"""
    if request.method == 'GET':
        deezer_url = request.GET.get('url', '').strip()
        
        if not deezer_url:
            return JsonResponse({'error': 'Missing Deezer URL'}, status=400)
        
        # Extraire l'ID de l'album
        album_id = extract_deezer_album_id(deezer_url)
        
        if not album_id:
            return JsonResponse({'error': 'Invalid Deezer URL'}, status=400)
        
        # Récupérer les infos depuis Deezer
        album_info = fetch_album_from_deezer(album_id)
        
        if 'error' in album_info:
            return JsonResponse(album_info, status=400)
        
        return JsonResponse(album_info)
    
    return JsonResponse({'error': 'Method not allowed'}, status=405)


def fetch_discogs_release(request):
    """API endpoint to fetch a Discogs release from a URL or bare ID"""
    url = request.GET.get('url', '').strip()
    if not url:
        return JsonResponse({'error': 'Missing Discogs URL'}, status=400)

    release_id = extract_discogs_release_id(url)
    if not release_id:
        return JsonResponse({'error': 'Invalid Discogs URL'}, status=400)

    result = fetch_release_from_discogs(release_id)
    if 'error' in result:
        return JsonResponse(result, status=400)
    return JsonResponse(result)


def fetch_bandcamp_album(request):
    """API endpoint to fetch album info from a Bandcamp URL"""
    url = request.GET.get('url', '').strip()
    if not url:
        return JsonResponse({'error': 'Missing Bandcamp URL'}, status=400)

    result = fetch_album_from_bandcamp(url)
    if 'error' in result:
        return JsonResponse(result, status=400)
    return JsonResponse(result)


def fetch_album_from_link(request):
    """Unified endpoint — detects platform from URL and routes to the right API"""
    url = request.GET.get('url', '').strip()
    if not url:
        return JsonResponse({'error': 'Missing link'}, status=400)

    if 'deezer.com' in url:
        album_id = extract_deezer_album_id(url)
        if not album_id:
            return JsonResponse({'error': 'Invalid Deezer URL'}, status=400)
        result = fetch_album_from_deezer(album_id)
    elif 'discogs.com' in url:
        release_id = extract_discogs_release_id(url)
        if not release_id:
            return JsonResponse({'error': 'Invalid Discogs URL'}, status=400)
        result = fetch_release_from_discogs(release_id)
    elif 'bandcamp.com' in url:
        result = fetch_album_from_bandcamp(url)
    else:
        return JsonResponse({'error': 'Unrecognised link — paste a Deezer, Discogs or Bandcamp URL'}, status=400)

    if 'error' in result:
        return JsonResponse(result, status=400)
    return JsonResponse(result)


def tags_autocomplete(request):
    """API pour l'autocomplétion des tags"""
    query = request.GET.get('q', '')

    if query:
        tags = Tag.objects.filter(name__icontains=query).values('id', 'name', 'category')[:10]
    else:
        tags = Tag.objects.all().values('id', 'name', 'category')[:20]

    return JsonResponse(list(tags), safe=False)


@login_required
def delete_album_view(request, album_id):
    """Vue pour supprimer un album"""
    if not request.user.is_staff:
        return HttpResponseForbidden()
    if request.method == 'POST':
        album = get_object_or_404(Album, id=album_id)
        album.delete()
        return redirect('collection')
    return redirect('collection')


def artists_autocomplete(request):
    """API pour l'autocomplétion des artistes avec nombre d'albums"""
    query = request.GET.get('q', '').strip()

    artists = Artist.objects.annotate(album_count=Count('albums'))

    if query:
        artists = artists.filter(name__icontains=query)

    artists = artists.order_by('-album_count', 'name')[:15]

    result = [
        {'name': artist.name, 'album_count': artist.album_count}
        for artist in artists
    ]

    return JsonResponse(result, safe=False)


def check_duplicate_album(request):
    """API to check if an album with the same name and artist already exists"""
    name = request.GET.get('name', '').strip()
    artist = request.GET.get('artist', '').strip()

    match = Album.objects.filter(
        name__iexact=name,
        artist__name__iexact=artist
    ).select_related('artist').first()

    if match:
        return JsonResponse({
            'exists': True,
            'album': {'id': match.id, 'name': match.name, 'artist': match.artist.name}
        })

    return JsonResponse({'exists': False})


def albums_paginated_api(request):
    """API endpoint for paginated albums (returns JSON)"""
    # Get filter parameters
    artist_search = request.GET.get('artist', '').strip()
    selected_category = request.GET.get('category', '').strip()
    selected_tags = request.GET.getlist('tags')

    # Apply filters using custom manager
    albums = Album.objects.select_related('artist').prefetch_related('tags').with_filters(
        artist_search=artist_search,
        category=selected_category,
        tags=selected_tags
    )

    # Paginate the results (50 per page)
    page_number = request.GET.get('page', 1)
    paginator = Paginator(albums, 50)
    page_obj = paginator.get_page(page_number)

    # Build the JSON response
    albums_data = []
    for album in page_obj:
        albums_data.append({
            'id': album.id,
            'name': album.name,
            'artist': {'name': album.artist.name},
            'year': album.year,
            'cover_url': album.cover.url if album.cover else None,
            'tags': [
                {'id': tag.id, 'name': tag.name, 'category': tag.get_category_display()}
                for tag in album.tags.all()
            ]
        })

    return JsonResponse({
        'albums': albums_data,
        'page': page_obj.number,
        'total': paginator.count,
        'has_more': page_obj.has_next()
    })


def album_grid_partial(request):
    """HTMX endpoint - returns just the album grid HTML"""
    # Get filter parameters
    artist_search = request.GET.get('artist', '').strip()
    selected_category = request.GET.get('category', '').strip()
    selected_tags = request.GET.getlist('tags')

    # Apply filters using custom manager
    albums = Album.objects.select_related('artist').prefetch_related('tags').with_filters(
        artist_search=artist_search,
        category=selected_category,
        tags=selected_tags
    )

    # Get total count before pagination
    total_count = albums.count()

    # Paginate
    paginator = Paginator(albums, 50)
    page_obj = paginator.get_page(1)

    context = {
        'albums': page_obj,
        'has_more': page_obj.has_next(),
        'albums_count': total_count,
    }

    return render(request, 'albums/_album_grid.html', context)


def register_view(request):
    if request.user.is_authenticated:
        return redirect('collection')
    if request.method == 'POST':
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect('collection')
    else:
        form = RegisterForm()
    return render(request, 'albums/register.html', {'form': form})


@login_required
def profile_view(request):
    profile_updated = False
    password_updated = False
    profile_form = ProfileForm(instance=request.user)
    password_form = PasswordChangeForm(user=request.user)

    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'profile':
            profile_form = ProfileForm(request.POST, instance=request.user)
            if profile_form.is_valid():
                profile_form.save()
                profile_updated = True
        elif action == 'password':
            password_form = PasswordChangeForm(user=request.user, data=request.POST)
            if password_form.is_valid():
                password_form.save()
                update_session_auth_hash(request, password_form.user)
                password_updated = True

    return render(request, 'albums/profile.html', {
        'profile_form': profile_form,
        'password_form': password_form,
        'profile_updated': profile_updated,
        'password_updated': password_updated,
    })


def public_profile_view(request, username):
    profile_user = get_object_or_404(User, username=username)
    return render(request, 'albums/public_profile.html', {
        'profile_user': profile_user,
    })