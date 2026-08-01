RECENTLY_VIEWED_KEY = "recently_viewed"
MAX_RECENT = 12


def track_product_view(request, product_id):
    """Record recently viewed IDs without forcing a session for first-time browsers.

    Only writes when a session already exists (signed-in or cart/auth cookie).
    """
    session = getattr(request, "session", None)
    if session is None:
        return
    if not session.session_key and not getattr(request.user, "is_authenticated", False):
        return
    viewed = session.get(RECENTLY_VIEWED_KEY, [])
    product_id = int(product_id)
    viewed = [pid for pid in viewed if pid != product_id]
    viewed.insert(0, product_id)
    session[RECENTLY_VIEWED_KEY] = viewed[:MAX_RECENT]
    session.modified = True


def get_recently_viewed_ids(request):
    return request.session.get(RECENTLY_VIEWED_KEY, [])
