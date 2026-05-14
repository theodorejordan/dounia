from django.db.models import prefetch_related_objects
from .models import Submission


def user_profile(request):
    if request.user.is_authenticated:
        prefetch_related_objects([request.user], 'userprofile')

    pending_submissions_count = 0
    if request.user.is_authenticated:
        if request.user.is_staff:
            pending_submissions_count = Submission.objects.filter(status='pending').count()
        else:
            pending_submissions_count = Submission.objects.filter(
                submitted_by=request.user, status='pending'
            ).count()

    return {'pending_submissions_count': pending_submissions_count}
