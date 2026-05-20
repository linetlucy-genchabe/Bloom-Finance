from datetime import date
from .models import UserProfile, Subscription

def global_context(request):
    try:
        profile = UserProfile.objects.get(pk=1)
    except UserProfile.DoesNotExist:
        profile = None

    upcoming = []
    if profile:
        subs = Subscription.objects.filter(is_active=True)
        upcoming = [s for s in subs if 0 <= s.days_until_renewal <= 7]

    return {'profile': profile, 'upcoming_renewals': upcoming}
