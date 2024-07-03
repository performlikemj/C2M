from django.http import HttpResponseForbidden
from functools import wraps

def kiosk_only(view_func):
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        # Check if the current user is the 'kiosk' user
        if not request.user.is_authenticated or request.user.username != 'kiosk':
            return HttpResponseForbidden("You do not have permission to view this page.")
        return view_func(request, *args, **kwargs)
    return _wrapped_view
