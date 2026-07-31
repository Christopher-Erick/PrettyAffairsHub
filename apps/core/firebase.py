"""Optional Firebase client scaffolding.

No-op until FIREBASE_PROJECT_ID and a credentials path are configured.
Does not invent keys or initialize a fake app.
"""

from __future__ import annotations

from django.conf import settings


def firebase_configured() -> bool:
    return bool(getattr(settings, "FIREBASE_PROJECT_ID", ""))


def get_firebase_app():
    """Return a firebase_admin app when credentials exist; otherwise None."""
    if not firebase_configured():
        return None
    try:
        import firebase_admin
        from firebase_admin import credentials
    except ImportError:
        return None

    if firebase_admin._apps:
        return firebase_admin.get_app()

    cred_path = getattr(settings, "FIREBASE_CREDENTIALS", "") or ""
    if not cred_path:
        return None
    cred = credentials.Certificate(cred_path)
    return firebase_admin.initialize_app(
        cred,
        {
            "projectId": settings.FIREBASE_PROJECT_ID,
            "storageBucket": getattr(settings, "FIREBASE_STORAGE_BUCKET", "") or None,
        },
    )
