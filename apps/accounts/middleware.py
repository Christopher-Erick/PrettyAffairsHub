"""Enforce one-device and idle timeout for client shoppers."""

from __future__ import annotations

from apps.accounts.session_policy import enforce_client_session_policy


class ClientSessionPolicyMiddleware:
    """After auth: kick superseded or idle client sessions (admins exempt)."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        enforce_client_session_policy(request)
        return self.get_response(request)
