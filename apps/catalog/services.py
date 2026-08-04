RECENTLY_VIEWED_KEY = "recently_viewed"
RECENT_SEARCHES_KEY = "recent_searches"
MAX_RECENT = 12
MAX_SEARCHES = 8


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


def track_shop_search(request, term: str):
    """Remember recent shop search terms for ritual personalization."""
    term = (term or "").strip().lower()[:64]
    if len(term) < 2:
        return
    session = getattr(request, "session", None)
    if session is None:
        return
    # Create a session if needed so anonymous browsers still get personalization.
    if not session.session_key:
        session.save()
    searches = [s for s in session.get(RECENT_SEARCHES_KEY, []) if s != term]
    searches.insert(0, term)
    session[RECENT_SEARCHES_KEY] = searches[:MAX_SEARCHES]
    session.modified = True


def get_recent_searches(request):
    return list(request.session.get(RECENT_SEARCHES_KEY, []) or [])
