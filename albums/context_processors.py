from django.db.models import prefetch_related_objects


def user_profile(request):
    if request.user.is_authenticated:
        prefetch_related_objects([request.user], 'userprofile')
    return {}
