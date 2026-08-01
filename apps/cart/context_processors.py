from django.db.models import Sum

from apps.cart.models import Cart

SESSION_CART_COUNT_KEY = "cart_item_count"


def refresh_cart_item_count(request, cart=None):
    """Store the badge count in the session so every page avoids a DB hit."""
    try:
        if cart is None:
            qs = Cart.objects.all()
            if request.user.is_authenticated:
                qs = qs.filter(user=request.user)
            elif request.session.session_key:
                qs = qs.filter(session_key=request.session.session_key, user__isnull=True)
            else:
                return 0
            cart = qs.first()
        count = 0
        if cart is not None:
            count = cart.items.aggregate(total=Sum("quantity"))["total"] or 0
        request.session[SESSION_CART_COUNT_KEY] = count
        return count
    except Exception:
        return 0


def cart_context(request):
    """Avoid creating or loading sessions for anonymous browsers with empty carts."""
    user = getattr(request, "user", None)
    authenticated = bool(getattr(user, "is_authenticated", False))
    session = getattr(request, "session", None)
    if session is None:
        return {"CART_ITEM_COUNT": 0}

    # No cookie yet and not signed in — zero without touching the DB.
    if not authenticated and not session.session_key:
        return {"CART_ITEM_COUNT": 0}

    if SESSION_CART_COUNT_KEY in session:
        return {"CART_ITEM_COUNT": session.get(SESSION_CART_COUNT_KEY) or 0}
    return {"CART_ITEM_COUNT": refresh_cart_item_count(request)}
