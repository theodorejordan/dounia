import zipfile
from io import BytesIO
from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse, HttpResponse, HttpResponseForbidden
from django.db.models import Q, Count
from django.core.paginator import Paginator
from django.contrib.auth import login, logout, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib.auth.models import User
from .models import Album, Artist, Tag, UserProfile, Submission, Comment
from .forms import AlbumForm, RegisterForm, ProfileForm, AvatarForm, SubmissionForm
from .services import create_album_from_submission, sync_album_tags
import json
from .deezer_api import extract_deezer_album_id, fetch_album_from_deezer
from .discogs_api import fetch_from_discogs
from .bandcamp_api import fetch_album_from_bandcamp


def collection_view(request):
    """Vue de la collection avec filtres"""
    # Get filter parameters
    artist_search = request.GET.get('artist', '').strip()
    contributor_search = request.GET.get('contributor', '').strip()
    selected_category = request.GET.get('category', '').strip()
    selected_tags = request.GET.getlist('tags')

    # Apply filters using custom manager
    albums = Album.objects.select_related('artist', 'submitted_by__userprofile').prefetch_related('tags').with_filters(
        artist_search=artist_search,
        contributor=contributor_search,
        category=selected_category,
        tags=selected_tags
    )

    # Paginate: show only first 50 albums
    total_count = albums.count()
    paginator = Paginator(albums, 40)
    page_obj = paginator.get_page(1)  # Always load page 1 on initial view

    # Récupérer tous les tags pour les filtres (avec nombre d'albums)
    all_tags = Tag.objects.annotate(album_count=Count('albums')).order_by('category', 'name')

    # Get all artists and contributors for unified filter whitelist
    all_artists = Artist.objects.annotate(album_count=Count('albums')).order_by('-album_count', 'name')
    all_contributors = User.objects.filter(
        submitted_albums__isnull=False
    ).annotate(album_count=Count('submitted_albums')).distinct().order_by('-album_count', 'username')

    has_active_filters = bool(artist_search or contributor_search or selected_category or selected_tags)

    context = {
        'albums': page_obj,
        'all_tags': all_tags,
        'all_artists': all_artists,
        'all_contributors': all_contributors,
        'selected_tags': [int(t) for t in selected_tags if t.isdigit()],
        'selected_artist': artist_search,
        'selected_contributor': contributor_search,
        'albums_count': total_count,
        'has_more': page_obj.has_next(),
        'selected_category': selected_category,
        'tag_categories': Tag.CATEGORY_CHOICES,
        'has_active_filters': has_active_filters,
    }

    return render(request, 'albums/collection.html', context)


@login_required
def add_album_view(request):
    """Vue pour ajouter un album"""
    if request.method == 'POST':
        form = AlbumForm(request.POST, request.FILES)
        if form.is_valid():
            album = form.save(commit=False)
            album.submitted_by = request.user
            album.save()
            sync_album_tags(album, form.cleaned_data.get('tags_input', ''))
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
    """API endpoint to fetch a Discogs release or master from a URL or bare ID"""
    url = request.GET.get('url', '').strip()
    if not url:
        return JsonResponse({'error': 'Missing Discogs URL'}, status=400)

    result = fetch_from_discogs(url)
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
        result = fetch_from_discogs(url)
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
        # Return all tags (for Tagify whitelist)
        tags = Tag.objects.all().values('id', 'name', 'category')

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


def contributors_autocomplete(request):
    """API for contributor autocomplete with album count"""
    query = request.GET.get('q', '').strip()

    # Get users who have submitted at least one album
    contributors = User.objects.filter(
        submitted_albums__isnull=False
    ).annotate(
        album_count=Count('submitted_albums')
    ).distinct()

    if query:
        contributors = contributors.filter(username__icontains=query)

    contributors = contributors.order_by('-album_count', 'username')[:15]

    result = [
        {'username': user.username, 'album_count': user.album_count}
        for user in contributors
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
    contributor_search = request.GET.get('contributor', '').strip()
    selected_category = request.GET.get('category', '').strip()
    selected_tags = request.GET.getlist('tags')

    # Apply filters using custom manager
    albums = Album.objects.select_related('artist', 'submitted_by__userprofile').prefetch_related('tags').with_filters(
        artist_search=artist_search,
        contributor=contributor_search,
        category=selected_category,
        tags=selected_tags
    )

    # Paginate the results (40 per page)
    page_number = request.GET.get('page', 1)
    paginator = Paginator(albums, 40)
    page_obj = paginator.get_page(page_number)

    # Build the JSON response
    albums_data = []
    for album in page_obj:
        submitted_by = None
        if album.submitted_by:
            submitted_by = {
                'id': album.submitted_by.id,
                'username': album.submitted_by.username,
                'avatar_url': album.submitted_by.userprofile.avatar.url if album.submitted_by.userprofile.avatar else None
            }
        albums_data.append({
            'id': album.id,
            'name': album.name,
            'artist': {'id': album.artist.id, 'name': album.artist.name},
            'year': album.year,
            'cover_url': album.cover.url if album.cover else None,
            'tags': [
                {'id': tag.id, 'name': tag.name, 'category': tag.get_category_display()}
                for tag in album.tags.all()
            ],
            'submitted_by': submitted_by
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
    contributor_search = request.GET.get('contributor', '').strip()
    selected_category = request.GET.get('category', '').strip()
    selected_tags = request.GET.getlist('tags')

    # Apply filters using custom manager
    albums = Album.objects.select_related('artist', 'submitted_by__userprofile').prefetch_related('tags').with_filters(
        artist_search=artist_search,
        contributor=contributor_search,
        category=selected_category,
        tags=selected_tags
    )

    # Get total count before pagination
    total_count = albums.count()

    # Paginate
    paginator = Paginator(albums, 40)
    page_obj = paginator.get_page(1)

    has_active_filters = bool(artist_search or contributor_search or selected_category or selected_tags)

    context = {
        'albums': page_obj,
        'has_more': page_obj.has_next(),
        'albums_count': total_count,
        'has_active_filters': has_active_filters,
    }

    return render(request, 'albums/_album_grid.html', context)


def download_covers_zip(request):
    """Generate and return a ZIP file containing album covers matching current filters"""
    # Get filter parameters (same as collection_view)
    artist_search = request.GET.get('artist', '').strip()
    contributor_search = request.GET.get('contributor', '').strip()
    selected_category = request.GET.get('category', '').strip()
    selected_tags = request.GET.getlist('tags')

    # Require at least one filter to be active
    if not any([artist_search, contributor_search, selected_category, selected_tags]):
        return HttpResponse("No filters selected", status=400)

    # Apply filters using existing manager method
    albums = Album.objects.select_related('artist').with_filters(
        artist_search=artist_search,
        contributor=contributor_search,
        category=selected_category,
        tags=selected_tags
    )

    # Limit to prevent abuse
    albums = albums[:500]

    # Create ZIP in memory
    buffer = BytesIO()
    with zipfile.ZipFile(buffer, 'w', zipfile.ZIP_DEFLATED) as zf:
        for album in albums:
            if album.cover:
                # Generate filename: "Artist - Album.ext"
                ext = album.cover.name.split('.')[-1]
                filename = f"{album.artist.name} - {album.name}.{ext}"
                # Sanitize filename (remove invalid characters)
                filename = "".join(c for c in filename if c not in r'\/:*?"<>|')

                try:
                    zf.writestr(filename, album.cover.read())
                except Exception:
                    # Skip files that can't be read
                    continue

    buffer.seek(0)

    response = HttpResponse(buffer.read(), content_type='application/zip')
    response['Content-Disposition'] = 'attachment; filename="album-covers.zip"'
    return response


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
    password_updated = False
    user_profile = request.user.userprofile
    profile_form = ProfileForm(instance=request.user)
    password_form = PasswordChangeForm(user=request.user)
    avatar_form = AvatarForm(instance=user_profile)

    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'profile':
            profile_form = ProfileForm(request.POST, instance=request.user)
            avatar_form = AvatarForm(request.POST, request.FILES, instance=user_profile)
            if profile_form.is_valid() and avatar_form.is_valid():
                profile_form.save()
                avatar_form.save()
        elif action == 'password':
            password_form = PasswordChangeForm(user=request.user, data=request.POST)
            if password_form.is_valid():
                password_form.save()
                update_session_auth_hash(request, password_form.user)
                password_updated = True

    return render(request, 'albums/profile.html', {
        'profile_form': profile_form,
        'password_form': password_form,
        'user_profile': user_profile,
        'password_updated': password_updated,
    })


def public_profile_view(request, username):
    profile_user = get_object_or_404(User, username=username)
    return render(request, 'albums/public_profile.html', {
        'profile_user': profile_user,
    })


@login_required
def delete_account_view(request):
    if request.method == 'POST':
        user = request.user
        logout(request)
        user.delete()
        return redirect('collection')
    return redirect('profile')


def changelog_view(request):
    return render(request, 'albums/changelog.html')


@login_required
def user_submissions_view(request):
    user_submissions = Submission.objects.filter(submitted_by=request.user).prefetch_related('tags')
    return render(request, 'albums/my_submissions.html', {
        'user_submissions': user_submissions,
    })


@login_required
def submit_album_view(request):
    """View for users to submit albums for review"""
    if request.method == 'POST':
        form = SubmissionForm(request.POST, request.FILES)
        if form.is_valid():
            form.save(user=request.user)
            return redirect('profile_submissions')
    else:
        form = SubmissionForm()

    # Get all tags for autocomplete (whitelist-only selection)
    all_tags = Tag.objects.all().values('id', 'name', 'category')

    return render(request, 'albums/submit_album.html', {
        'form': form,
        'all_tags': list(all_tags),
    })


@login_required
def submissions_admin_view(request):
    """Staff-only view to manage pending submissions"""
    if not request.user.is_staff:
        return HttpResponseForbidden()

    submissions = Submission.objects.filter(
        status='pending'
    ).select_related('submitted_by').prefetch_related('tags')

    return render(request, 'albums/submissions_admin.html', {
        'submissions': submissions,
    })


@login_required
def approve_submission_view(request, pk):
    """Staff action to approve a submission and create an album"""
    if not request.user.is_staff:
        return HttpResponseForbidden()

    if request.method == 'POST':
        submission = get_object_or_404(Submission, pk=pk, status='pending')
        create_album_from_submission(submission, reviewed_by=request.user)
        return redirect('submissions_admin')

    return redirect('submissions_admin')


@login_required
def delete_submission_view(request, pk):
    """Staff action to delete a submission"""
    if not request.user.is_staff:
        return HttpResponseForbidden()

    if request.method == 'POST':
        submission = get_object_or_404(Submission, pk=pk)
        submission.delete()
        return redirect('submissions_admin')

    return redirect('submissions_admin')


def album_drawer_view(request, album_id):
    """Main drawer view with header and tabs"""
    album = get_object_or_404(
        Album.objects.select_related('artist', 'submitted_by__userprofile').prefetch_related('tags'),
        id=album_id
    )
    return render(request, 'albums/_drawer.html', {
        'album': album,
    })


def drawer_info_view(request, album_id):
    """Info tab content"""
    album = get_object_or_404(
        Album.objects.select_related('artist', 'submitted_by__userprofile').prefetch_related('tags'),
        id=album_id
    )
    return render(request, 'albums/_drawer_info.html', {
        'album': album,
    })


def drawer_similar_view(request, album_id):
    """Similar tab content"""
    album = get_object_or_404(
        Album.objects.select_related('artist').prefetch_related('tags'),
        id=album_id
    )

    # Albums by the same artist (excluding current)
    same_artist = Album.objects.filter(artist_id=album.artist_id).exclude(id=album_id).only('id', 'name', 'cover', 'year')[:2]

    # Albums with exactly the same tags (excluding current)
    tag_ids = list(album.tags.values_list('id', flat=True))
    tag_count = len(tag_ids)
    same_tags = []
    if tag_ids:
        same_tags = (
            Album.objects
            .exclude(id=album_id)
            .annotate(
                matching_tags=Count('tags', filter=Q(tags__id__in=tag_ids)),
                total_tags=Count('tags')
            )
            .filter(matching_tags=tag_count, total_tags=tag_count)
            .select_related('artist')
            .only('id', 'name', 'cover', 'artist')[:2]
        )

    return render(request, 'albums/_drawer_similar.html', {
        'album': album,
        'same_artist': same_artist,
        'same_tags': same_tags,
    })


def drawer_comments_view(request, album_id):
    """Comments tab content"""
    album = get_object_or_404(Album, id=album_id)

    if request.method == 'POST' and request.user.is_authenticated:
        text = request.POST.get('text', '').strip()
        parent_id = request.POST.get('parent_id')
        if text:
            parent = None
            if parent_id:
                parent = Comment.objects.filter(id=parent_id, album=album).first()
            Comment.objects.create(
                album=album,
                author=request.user,
                text=text,
                parent=parent
            )

    # Get top-level comments with replies
    comments = Comment.objects.filter(album=album, parent__isnull=True).select_related('author__userprofile').prefetch_related('replies__author__userprofile')

    return render(request, 'albums/_drawer_comments.html', {
        'album': album,
        'comments': comments,
    })


@login_required
def update_album_tags(request, album_id):
    """API to update album tags (staff only)"""
    if not request.user.is_staff:
        return HttpResponseForbidden()

    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)

    album = get_object_or_404(Album, id=album_id)

    try:
        data = json.loads(request.body)
        tags_json = data.get('tags', '[]')
        sync_album_tags(album, tags_json)
        return JsonResponse({'success': True})
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)


@login_required
def update_album_notes(request, album_id):
    """API to update album notes (staff only)"""
    if not request.user.is_staff:
        return HttpResponseForbidden()

    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)

    album = get_object_or_404(Album, id=album_id)

    try:
        data = json.loads(request.body)
        album.notes = data.get('notes', '')
        album.save()
        return JsonResponse({'success': True})
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)