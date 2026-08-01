from functools import wraps

from django.contrib.auth.views import redirect_to_login
from django.http import HttpResponseForbidden

from apps.accounts.roles import is_store_admin


def store_manager_required(view_func):
    """Only signed-in store staff may use the Store Manager desk."""

    @wraps(view_func)
    def _wrapped(request, *args, **kwargs):
        user = request.user
        if not user.is_authenticated:
            return redirect_to_login(request.get_full_path())
        if not is_store_admin(user):
            return HttpResponseForbidden("Store Manager is only for store staff.")
        return view_func(request, *args, **kwargs)

    return _wrapped
