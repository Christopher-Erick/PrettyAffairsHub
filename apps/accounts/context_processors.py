from django.conf import settings

from apps.accounts.roles import is_store_admin
from apps.accounts.session_policy import idle_timeout_seconds


def account_session(request):
    user = getattr(request, "user", None)
    admin = is_store_admin(user) if user else False
    client_idle = bool(user and user.is_authenticated and not admin)
    return {
        "is_store_admin": admin,
        "CLIENT_IDLE_ENABLED": client_idle,
        "CLIENT_IDLE_TIMEOUT_MS": idle_timeout_seconds() * 1000 if client_idle else 0,
        "CLIENT_IDLE_TIMEOUT_SECONDS": getattr(
            settings, "CLIENT_IDLE_TIMEOUT_SECONDS", 20 * 60
        ),
    }
