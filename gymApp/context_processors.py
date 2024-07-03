# gymApp/context_processors.py

from django.contrib.auth.models import Group

def user_groups(request):
    if request.user.is_authenticated:
        user_groups = list(request.user.groups.values_list('name', flat=True))
    else:
        user_groups = []
    return {'user_groups': user_groups}
