"""Client session rules: one device at a time, 20-minute idle timeout.

Store admins are exempt from both policies.
"""

from __future__ import annotations

import time

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import logout
from django.contrib.sessions.models import Session

from apps.accounts.models import CustomerProfile
from apps.accounts.roles import is_store_admin

LAST_ACTIVITY_KEY = "client_last_activity"


def idle_timeout_seconds() -> int:
    return int(getattr(settings, "CLIENT_IDLE_TIMEOUT_SECONDS", 20 * 60))


def claim_exclusive_session(request, user) -> None:
    """Make this request the only active client session for ``user``."""
    if not getattr(user, "is_authenticated", False) or is_store_admin(user):
        return

    if not request.session.session_key:
        request.session.save()

    current = request.session.session_key
    _delete_other_sessions(user_id=user.pk, keep=current)

    profile, _ = CustomerProfile.objects.get_or_create(user=user)
    if profile.active_session_key != current:
        profile.active_session_key = current
        profile.save(update_fields=["active_session_key", "updated_at"])

    request.session[LAST_ACTIVITY_KEY] = time.time()
    request.session.modified = True


def release_exclusive_session(request, user) -> None:
    """Clear the stored key when this device signs out."""
    if not getattr(user, "is_authenticated", False) or is_store_admin(user):
        return
    current = getattr(request.session, "session_key", None)
    profile = CustomerProfile.objects.filter(user=user).first()
    if not profile or not profile.active_session_key:
        return
    if current and profile.active_session_key != current:
        return
    profile.active_session_key = ""
    profile.save(update_fields=["active_session_key", "updated_at"])


def enforce_client_session_policy(request) -> None:
    """Logout clients who lost the exclusive seat or went idle."""
    user = getattr(request, "user", None)
    if not user or not user.is_authenticated or is_store_admin(user):
        return

    profile = CustomerProfile.objects.filter(user=user).first()
    current = request.session.session_key
    if profile and profile.active_session_key and current:
        if profile.active_session_key != current:
            logout(request)
            messages.warning(
                request,
                "You were signed out because your account signed in on another device.",
            )
            return

    timeout = idle_timeout_seconds()
    now = time.time()
    last = request.session.get(LAST_ACTIVITY_KEY)
    if last is not None:
        try:
            idle_for = now - float(last)
        except (TypeError, ValueError):
            idle_for = 0
        if idle_for > timeout:
            logout(request)
            messages.info(
                request,
                "You were signed out after 20 minutes of inactivity.",
            )
            return

    request.session[LAST_ACTIVITY_KEY] = now
    request.session.modified = True


def _delete_other_sessions(*, user_id: int, keep: str | None) -> None:
    uid = str(user_id)
    to_delete = []
    for session in Session.objects.iterator(chunk_size=200):
        if keep and session.session_key == keep:
            continue
        try:
            data = session.get_decoded()
        except Exception:
            continue
        if data.get("_auth_user_id") == uid:
            to_delete.append(session.session_key)
    if to_delete:
        Session.objects.filter(session_key__in=to_delete).delete()
