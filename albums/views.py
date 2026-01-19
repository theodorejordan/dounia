from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.db.models import Q, Count
from .models import Album, Artist, Tag
from .forms import AlbumForm
from .deezer_api import extract_deezer_album_id, fetch_album_from_deezer


def collection_view(request):
    """Vue de la collection avec filtres"""
    albums = Album.objects.select_related('artist').prefetch_related('tags').all()

    # Récupérer la recherche par artiste
    artist_search = request.GET.get('artist', '').strip()

    # Filtrer par nom d'artiste si présent
    if artist_search:
        albums = albums.filter(artist__name__icontains=artist_search)

    # Récupérer les tags sélectionnés depuis l'URL
    selected_tags = request.GET.getlist('tags')

    # Filtrer par tags si présents
    if selected_tags:
        for tag_id in selected_tags:
            albums = albums.filter(tags__id=tag_id)
        albums = albums.distinct()
    
    # Récupérer tous les tags pour les filtres
    all_tags = Tag.objects.all().order_by('category', 'name')
    
    context = {
        'albums': albums,
        'all_tags': all_tags,
        'selected_tags': [int(t) for t in selected_tags if t.isdigit()],
        'albums_count': albums.count(),
        'artist_search': artist_search,
    }
    
    return render(request, 'albums/collection.html', context)


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
            return JsonResponse({'error': 'URL Deezer manquante'}, status=400)
        
        # Extraire l'ID de l'album
        album_id = extract_deezer_album_id(deezer_url)
        
        if not album_id:
            return JsonResponse({'error': 'URL Deezer invalide'}, status=400)
        
        # Récupérer les infos depuis Deezer
        album_info = fetch_album_from_deezer(album_id)
        
        if 'error' in album_info:
            return JsonResponse(album_info, status=400)
        
        return JsonResponse(album_info)
    
    return JsonResponse({'error': 'Méthode non autorisée'}, status=405)


def tags_autocomplete(request):
    """API pour l'autocomplétion des tags"""
    query = request.GET.get('q', '')

    if query:
        tags = Tag.objects.filter(name__icontains=query).values('id', 'name', 'category')[:10]
    else:
        tags = Tag.objects.all().values('id', 'name', 'category')[:20]

    return JsonResponse(list(tags), safe=False)


def delete_album_view(request, album_id):
    """Vue pour supprimer un album"""
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